"""
Live Smoke Test Script for Explainer Guards (D2 / Day 4b / Day 5).

For USMAN to run (with real API keys):
- Supports --provider groq|gemini|auto (default auto)
- Supports --mode background|inline (default background)
- Supports --pause SECONDS (pause between calls; default 2 for Groq, 0 for Gemini/auto)
- Checks API keys presence; if missing for chosen provider, prints a clear message and exits 0
- Prints keys strictly as SET or NOT SET (never prints key characters or masked strings)
- Runs 10 fake check-ins (hypertension only, en/ur/roman_ur)
- In background mode: check-in returns pending, script polls /api/checkins/{id}/explanation until ready or timeout (default 60s), then reports final status, mode, reason, provider, tokens, latency-to-pending, latency-to-ready
- Stops early if token usage reaches 20,000 per provider
"""
import argparse
from collections import defaultdict
import copy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
import jwt

from auth import firebase_verify
from data_sources import app_store, local_store
from data_sources.db_config import get_sqlite_path
from main import app
from rag.explain_guards import get_explain_guard_metrics, reset_explain_guards

TEST_PROJECT_ID = "live-smoke-test-project"
TEST_KID = "live-smoke-test-kid"
MAX_TOKEN_BUDGET_PER_PROVIDER = 20000

HTN_CHECKINS = [
    {"cond": "hypertension", "bp_sys": 135.0, "bp_dia": 85.0, "glucose": None, "lang": "en"},
    {"cond": "hypertension", "bp_sys": 135.0, "bp_dia": 85.0, "glucose": None, "lang": "en"},        # Cache hit
    {"cond": "hypertension", "bp_sys": 145.0, "bp_dia": 92.0, "glucose": None, "lang": "en"},
    {"cond": "hypertension", "bp_sys": 132.0, "bp_dia": 84.0, "glucose": None, "lang": "ur"},
    {"cond": "hypertension", "bp_sys": 132.0, "bp_dia": 84.0, "glucose": None, "lang": "ur"},        # Cache hit
    {"cond": "hypertension", "bp_sys": 150.0, "bp_dia": 95.0, "glucose": None, "lang": "ur"},
    {"cond": "hypertension", "bp_sys": 125.0, "bp_dia": 82.0, "glucose": None, "lang": "roman_ur"},
    {"cond": "hypertension", "bp_sys": 125.0, "bp_dia": 82.0, "glucose": None, "lang": "roman_ur"},  # Cache hit
    {"cond": "hypertension", "bp_sys": 142.0, "bp_dia": 91.0, "glucose": None, "lang": "roman_ur"},
    {"cond": "hypertension", "bp_sys": 135.0, "bp_dia": 85.0, "glucose": None, "lang": "en"},        # Cache hit
]

DIABETES_CHECKINS = [
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 115.0, "lang": "en"},
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 115.0, "lang": "en"},        # Cache hit
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 195.0, "lang": "en"},
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 145.0, "lang": "ur"},
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 145.0, "lang": "ur"},        # Cache hit
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 260.0, "lang": "ur"},
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 125.0, "lang": "roman_ur"},
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 125.0, "lang": "roman_ur"},  # Cache hit
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 65.0, "lang": "roman_ur"},
    {"cond": "diabetes", "bp_sys": None, "bp_dia": None, "glucose": 115.0, "lang": "en"},        # Cache hit
]

htn_checkins = HTN_CHECKINS
diabetes_checkins = DIABETES_CHECKINS


def generate_cert(rsa_key):
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "smoke-test")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "smoke-test")]))
        .public_key(rsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc))
        .sign(rsa_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def get_token(rsa_key, uid: str) -> str:
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": f"{uid}@demo.com",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})


def setup_db(db_file: str, cert_pem: str):
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass

    os.environ["LOCAL_DB_PATH"] = db_file
    os.environ["DB_BACKEND"] = "sqlite"
    os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID
    os.environ["REQUIRE_INCLUSION"] = "0"

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    mock_keys = {TEST_KID: cert_pem}
    firebase_verify._KEY_CACHE = {"keys": mock_keys, "expires_at": time.time() + 3600}
    firebase_verify.fetch_google_public_keys = lambda force_refresh=False: mock_keys

    now = datetime.now(timezone.utc).isoformat()
    chunks = [
        ("c_htn_1", "ish_2020_htn", "BP Targets", "hypertension",
         "Target blood pressure for adults with hypertension is below 130/80 mmHg.", now),
        ("c_htn_2", "who_2021_htn", "Stage 2 Targets", "hypertension",
         "Blood pressure 140/90 mmHg or higher requires clinical management.", now),
        ("c_dm_1", "ada_2026_sec02", "Classification and Diagnosis", "diabetes",
         "Fasting plasma glucose 126 mg/dL or higher or HbA1c 6.5 percent or higher confirms diabetes.", now),
        ("c_dm_2", "ada_2026_sec06", "Glycemic Goals", "diabetes",
         "Target fasting blood glucose for nonpregnant adults is 80-130 mg/dL.", now),
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        for cid, src, title, cond, text, updated in chunks:
            cur.execute(
                f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (cid, src, title, cond, text, updated),
            )


def main():
    parser = argparse.ArgumentParser(description="Live Smoke Test for Explainer LLM Providers")
    parser.add_argument(
        "--provider",
        choices=["groq", "gemini", "auto"],
        default="auto",
        help="LLM provider routing mode (default: auto)",
    )
    parser.add_argument(
        "--mode",
        choices=["background", "inline"],
        default="background",
        help="Explain execution mode (default: background)",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=3.0,
        help="Time budget in seconds per check-in for inline LLM explanations (default: 3.0)",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=None,
        help="Pause between calls in seconds (default: 2.0 for Groq, 0.0 for Gemini/auto)",
    )
    parser.add_argument(
        "--poll-timeout",
        type=float,
        default=float(os.getenv("EXPLAIN_JOB_DEADLINE_SECONDS", "45.0")) + 15.0,
        help="Poll timeout for background explanation in seconds (default: job deadline + 15s, 60.0)",
    )
    parser.add_argument(
        "--condition",
        choices=["hypertension", "diabetes", "both"],
        default="hypertension",
        help="Condition focus for smoke test check-ins (default: hypertension)",
    )
    parser.add_argument(
        "--real-chunks",
        action="store_true",
        default=False,
        help="Run against a copy of the real loaded guideline chunks store instead of 4 synthetic test chunks",
    )
    args = parser.parse_args()

    pause = args.pause if args.pause is not None else (2.0 if args.provider == "groq" else 0.0)

    print("=" * 115)
    print("CHRONICCARE AI - LIVE EXPLAINER SMOKE TEST (Groq & Gemini Dual Provider)")
    print("=" * 115)

    backend_conf = os.environ.get("DB_BACKEND", "sqlite").strip().lower()
    raw_db_path = os.environ.get("LOCAL_DB_PATH", "local_store.db")
    resolved_db_path = get_sqlite_path()

    print(f"Provider mode requested: {args.provider}")
    print(f"Condition:               {args.condition}")
    print(f"Explain mode:            {args.mode}")
    if args.mode == "background":
        job_deadline = float(os.getenv("EXPLAIN_JOB_DEADLINE_SECONDS", "45.0"))
        print(f"Job Deadline:            {job_deadline:.1f} s")
    else:
        print(f"Time Budget:             {args.budget:.1f} s")
    print(f"Pause between calls:     {pause:.1f} s")
    print(f"Poll timeout:            {args.poll_timeout:.1f} s")
    print(f"Backend configured:      {backend_conf}")
    print(f"LOCAL_DB_PATH (env):     {raw_db_path}")
    print(f"Resolved SQLite path:    {resolved_db_path}")

    groq_set = "SET" if os.getenv("GROQ_API_KEY", "").strip() else "NOT SET"
    gemini_set = "SET" if os.getenv("GEMINI_API_KEY", "").strip() else "NOT SET"
    print(f"GROQ_API_KEY:            {groq_set}")
    print(f"GEMINI_API_KEY:          {gemini_set}")

    if args.real_chunks and backend_conf == "mysql":
        print("[ERROR] --real-chunks only supports the local SQLite store", file=sys.stderr)
        return 1

    if args.provider == "groq" and groq_set != "SET":
        print("[INFO] GROQ_API_KEY is NOT SET. Exiting cleanly (code 0).")
        return 0
    if args.provider == "gemini" and gemini_set != "SET":
        print("[INFO] GEMINI_API_KEY is NOT SET. Exiting cleanly (code 0).")
        return 0
    if args.provider == "auto" and groq_set != "SET" and gemini_set != "SET":
        print("[INFO] Neither GROQ_API_KEY nor GEMINI_API_KEY is SET. Exiting cleanly (code 0).")
        return 0

    os.environ["EXPLAIN_ENABLED"] = "true"
    os.environ["EXPLAIN_MODE"] = args.mode
    os.environ["LLM_PROVIDER"] = args.provider
    os.environ["EXPLAIN_BUDGET_SECONDS"] = str(args.budget)
    os.environ["EXPLAIN_LLM_CONDITIONS"] = "hypertension,diabetes" if args.condition in ("diabetes", "both") else "hypertension"
    reset_explain_guards()

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_pem = generate_cert(rsa_key)
    db_file = None

    try:
        if args.real_chunks:
            if not os.path.exists(resolved_db_path):
                print(f"[ERROR] Local store not found at {resolved_db_path}. Run python scripts/rag/load_chunks.py first.", file=sys.stderr)
                return 1

            fd, db_file = tempfile.mkstemp(prefix="chroniccare_smoke_", suffix=".db")
            os.close(fd)

            # Use SQLite backup API for consistent atomic copy (including WAL data)
            src_conn = sqlite3.connect(resolved_db_path)
            dst_conn = sqlite3.connect(db_file)
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

            os.environ["LOCAL_DB_PATH"] = db_file
            os.environ["DB_BACKEND"] = "sqlite"
            os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID
            os.environ["REQUIRE_INCLUSION"] = "0"

            app_store.migrate(db_path=db_file, backend="sqlite")
            local_store.init_db(db_path=db_file)

            mock_keys = {TEST_KID: cert_pem}
            firebase_verify._KEY_CACHE = {"keys": mock_keys, "expires_at": time.time() + 3600}
            firebase_verify.fetch_google_public_keys = lambda force_refresh=False: mock_keys

            with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
                cur.execute("SELECT chunk_id, source_id, condition FROM guideline_chunks")
                all_chunks = cur.fetchall()

            total_chunks = len(all_chunks)
            chunks_by_source = defaultdict(int)
            chunks_by_cond = defaultdict(int)
            ada_chunks_count = 0
            for row in all_chunks:
                c_id, s_id, cond = row[0], row[1], row[2]
                chunks_by_source[s_id] += 1
                chunks_by_cond[cond] += 1
                if s_id and s_id.startswith("ada_2026"):
                    ada_chunks_count += 1

            if args.condition == "hypertension":
                if chunks_by_cond["hypertension"] == 0:
                    print("[ERROR] Hypertension condition selected but 0 hypertension chunks found in store.", file=sys.stderr)
                    return 1
            elif args.condition == "diabetes":
                if chunks_by_cond["diabetes"] == 0:
                    print("[ERROR] Diabetes condition selected but 0 diabetes chunks found in store.", file=sys.stderr)
                    return 1
                if ada_chunks_count == 0:
                    print("[ERROR] Diabetes condition selected but no ADA 2026 chunks found in store. Follow the permission steps in docs/tasks/WEEK3_USMAN.md before running with --real-chunks.", file=sys.stderr)
                    return 1
            elif args.condition == "both":
                if chunks_by_cond["hypertension"] == 0 and chunks_by_cond["diabetes"] == 0:
                    print("[ERROR] Both conditions selected but no hypertension or diabetes chunks found in store.", file=sys.stderr)
                    return 1
                if ada_chunks_count == 0:
                    print("[ERROR] Diabetes condition selected but no ADA 2026 chunks found in store. Follow the permission steps in docs/tasks/WEEK3_USMAN.md before running with --real-chunks.", file=sys.stderr)
                    return 1

            print(f"\nCHUNKS: real loaded corpus (copy of {resolved_db_path})")
            print(f"Total chunks in store: {total_chunks}")
            print("Chunks per source:")
            for s_id in sorted(chunks_by_source.keys()):
                print(f"  - {s_id}: {chunks_by_source[s_id]}")
        else:
            db_file = str(REPO_ROOT / "temp_live_smoke.db")
            setup_db(db_file, cert_pem)
            print("\nCHUNKS: 4 synthetic test chunks (not the real corpus)")

        chunk_to_source = {}
        with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
            cur.execute("SELECT chunk_id, source_id FROM guideline_chunks")
            for r in cur.fetchall():
                chunk_to_source[r[0]] = r[1]

        client = TestClient(app)

        if args.condition == "hypertension":
            test_checkins = list(htn_checkins)
        elif args.condition == "diabetes":
            test_checkins = list(diabetes_checkins)
        else:
            test_checkins = [
                htn_checkins[i] if i % 2 == 0 else diabetes_checkins[i]
                for i in range(min(len(htn_checkins), len(diabetes_checkins)))
            ]

        print(f"\nRunning {len(test_checkins)} pipeline check-ins (Condition: {args.condition}, en / ur / roman_ur)...\n")
        if args.mode == "background":
            print(f"{'#':<3} | {'Lang':<8} | {'Category':<16} | {'Level':<10} | {'Provider':<10} | {'Mode':<10} | {'Reason':<16} | {'Tokens':<8} | {'Lat.Pend':<10} | {'Lat.Ready':<10} | {'Provider Latency':<20} | {'Cited (Chunk / Source)':<32}")
            print("-" * 180)
        else:
            print(f"{'#':<3} | {'Lang':<8} | {'Category':<16} | {'Level':<10} | {'Provider':<10} | {'Mode':<10} | {'Reason':<16} | {'Tokens':<8} | {'Elapsed':<10} | {'Provider Latency':<20} | {'Cited (Chunk / Source)':<32}")
            print("-" * 165)

        run_id = int(time.time())
        prev_tokens_groq = 0
        prev_tokens_gemini = 0
        cited_sources_by_source_id = defaultdict(int)

        for idx, item in enumerate(test_checkins, start=1):
            metrics = get_explain_guard_metrics()
            used_groq = metrics.get("groq", {}).get("tokens_used_today", 0) if "groq" in metrics else metrics.get("tokens_used_by_provider", {}).get("groq", 0)
            used_gemini = metrics.get("gemini", {}).get("tokens_used_today", 0) if "gemini" in metrics else metrics.get("tokens_used_by_provider", {}).get("gemini", 0)

            if used_groq >= MAX_TOKEN_BUDGET_PER_PROVIDER or used_gemini >= MAX_TOKEN_BUDGET_PER_PROVIDER:
                print(f"\n[ALERT] Reached token safety cap ({MAX_TOKEN_BUDGET_PER_PROVIDER}). Stopping early.")
                break

            uid = f"smoke_{run_id}_{idx}"
            cid = f"smoke_chk_{run_id}_{idx}"
            token = get_token(rsa_key, uid)
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            client.post("/api/auth/session", headers=headers)
            local_store.add_local_patient_if_missing(f"local-{uid}", name=f"Smoke User {idx}", date_of_birth="1980-01-01")
            client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
            client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
            cond = item.get("cond", "hypertension")
            client.put(
                "/api/me/profile",
                headers=headers,
                json={
                    "conditions": [cond],
                    "date_of_birth": "1980-01-01",
                    "inclusion_confirmed": True,
                    "language": item["lang"],
                },
            )

            readings_dict = {}
            if item.get("bp_sys") is not None:
                readings_dict["blood_pressure_systolic"] = item["bp_sys"]
                readings_dict["blood_pressure_diastolic"] = item["bp_dia"]
            if item.get("glucose") is not None:
                readings_dict["glucose"] = item["glucose"]

            raw_state = {
                "engine": "v3",
                "completed": True,
                "conditions_on_file": [cond],
                "readings": readings_dict,
                "findings": [],
            }
            app_store.create_checkin(
                checkin_id=cid,
                user_id=uid,
                mode="isolated",
                record_patient_id=f"local-{uid}",
                state_dict=raw_state,
                status="in_progress",
            )

            t0 = time.monotonic()
            resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
            lat_pending = time.monotonic() - t0

            if resp.status_code != 200:
                print(f"{idx:<3} | ERROR {resp.status_code}: {resp.text[:40]}")
                continue

            data = resp.json()
            triage_val = data.get("triage")
            triage_level = triage_val.get("level", "routine") if isinstance(triage_val, dict) else ("emergency" if data.get("emergency") else ("review" if data.get("requires_review") else "routine"))

            lat_ready = lat_pending
            if args.mode == "background":
                # Poll explanation until ready or timeout
                poll_start = time.monotonic()
                while time.monotonic() - poll_start < args.poll_timeout:
                    poll_resp = client.get(f"/api/checkins/{cid}/explanation", headers=headers)
                    if poll_resp.status_code == 200:
                        poll_data = poll_resp.json()
                        st = poll_data.get("status")
                        if st in ("ready", "error"):
                            lat_ready = time.monotonic() - t0
                            break
                    time.sleep(1.0)
                else:
                    lat_ready = time.monotonic() - t0

            # Provider audit info retrieved from store
            chk_res = app_store.get_checkin_result(cid)
            chk_row = app_store.get_checkin_by_id(cid)
            state_dict = chk_row.get("state_dict", {}) if chk_row else {}
            explanation = (chk_res.get("explanation") if chk_res else None) or state_dict.get("explanation") or {}

            mode = explanation.get("mode", "-")
            reason = explanation.get("reason", "-")
            provider_used = explanation.get("provider", "-") or "-"

            curr_metrics = get_explain_guard_metrics()
            curr_groq = curr_metrics.get("groq", {}).get("tokens_used_today", 0) if "groq" in curr_metrics else curr_metrics.get("tokens_used_by_provider", {}).get("groq", 0)
            curr_gemini = curr_metrics.get("gemini", {}).get("tokens_used_today", 0) if "gemini" in curr_metrics else curr_metrics.get("tokens_used_by_provider", {}).get("gemini", 0)
            tokens_delta = (curr_groq - prev_tokens_groq) + (curr_gemini - prev_tokens_gemini)
            prev_tokens_groq = curr_groq
            prev_tokens_gemini = curr_gemini

            timings = explanation.get("provider_timings", {})
            if timings:
                prov_timing_str = ", ".join(f"{p}: {t:.2f}s" for p, t in timings.items())
            else:
                prov_timing_str = "-"

            sources_list = explanation.get("sources", [])
            cited_chunk_ids = sorted(set(str(s.get("chunk_id", "")) for s in sources_list if s.get("chunk_id")))
            cited_src_ids = sorted(set(str(s.get("source_id") or chunk_to_source.get(s.get("chunk_id", ""), "")) for s in sources_list if (s.get("source_id") or chunk_to_source.get(s.get("chunk_id", "")))))

            for src in cited_src_ids:
                cited_sources_by_source_id[src] += 1

            chunk_str = ", ".join(cited_chunk_ids) if cited_chunk_ids else "-"
            src_str = ", ".join(cited_src_ids) if cited_src_ids else "-"
            if cited_chunk_ids or src_str != "-":
                cited_display = f"{chunk_str} [{src_str}]"
            else:
                cited_display = "-"

            from rag.query_map import build_query_from_triage
            q_map = build_query_from_triage(
                {"level": triage_level, "symptom": item.get("symptom")},
                readings_dict,
            )
            trigger_cat = q_map.trigger_category

            if args.mode == "background":
                print(
                    f"{idx:<3} | {item['lang']:<8} | {trigger_cat:<16} | {triage_level:<10} | {provider_used:<10} | "
                    f"{mode:<10} | {str(reason):<16} | {tokens_delta:<8} | {lat_pending:<10.3f} | {lat_ready:<10.3f} | {prov_timing_str:<20} | {cited_display:<32}"
                )
            else:
                print(
                    f"{idx:<3} | {item['lang']:<8} | {trigger_cat:<16} | {triage_level:<10} | {provider_used:<10} | "
                    f"{mode:<10} | {str(reason):<16} | {tokens_delta:<8} | {lat_pending:<10.3f} | {prov_timing_str:<20} | {cited_display:<32}"
                )

            if mode == "template" and str(reason) in ("budget_timeout", "error"):
                rej_reasons = explanation.get("rejected_reasons", [])
                if rej_reasons:
                    raw_rej = str(rej_reasons[0])[:120]
                    print(f"    ↳ Rejected reason: {raw_rej}")

            if pause > 0 and idx < len(test_checkins):
                time.sleep(pause)

        final_metrics = get_explain_guard_metrics()
        final_groq_calls = final_metrics.get("groq", {}).get("llm_calls", 0) if "groq" in final_metrics else final_metrics.get("llm_calls_by_provider", {}).get("groq", 0)
        final_groq_tokens = final_metrics.get("groq", {}).get("tokens_used_today", 0) if "groq" in final_metrics else final_metrics.get("tokens_used_by_provider", {}).get("groq", 0)
        final_groq_breaker = final_metrics.get("groq", {}).get("breaker_state", "-") if "groq" in final_metrics else final_metrics.get("breaker_states", {}).get("groq", "-")
        final_gemini_calls = final_metrics.get("gemini", {}).get("llm_calls", 0) if "gemini" in final_metrics else final_metrics.get("llm_calls_by_provider", {}).get("gemini", 0)
        final_gemini_tokens = final_metrics.get("gemini", {}).get("tokens_used_today", 0) if "gemini" in final_metrics else final_metrics.get("tokens_used_by_provider", {}).get("gemini", 0)
        final_gemini_breaker = final_metrics.get("gemini", {}).get("breaker_state", "-") if "gemini" in final_metrics else final_metrics.get("breaker_states", {}).get("gemini", "-")

        print("\n" + "=" * 105)
        print("LIVE SMOKE TEST SUMMARY")
        print("=" * 105)
        print(f"Explain Mode:          {args.mode}")
        print(f"Cache Hits:            {final_metrics.get('cache_hits', 0)}")
        print(f"Cache Misses:          {final_metrics.get('cache_misses', 0)}")
        print(f"Groq LLM Calls:        {final_groq_calls}")
        print(f"Groq Tokens Used:      {final_groq_tokens} / {MAX_TOKEN_BUDGET_PER_PROVIDER}")
        print(f"Groq Breaker State:    {final_groq_breaker}")
        print(f"Gemini LLM Calls:      {final_gemini_calls}")
        print(f"Gemini Tokens Used:    {final_gemini_tokens} / {MAX_TOKEN_BUDGET_PER_PROVIDER}")
        print(f"Gemini Breaker State:  {final_gemini_breaker}")
        print(f"Template Fallbacks:    {final_metrics.get('template_fallbacks_by_reason', {})}")
        print(f"Cited Sources by ID:   {dict(sorted(cited_sources_by_source_id.items()))}")
        print("=" * 105)

        if args.real_chunks and db_file:
            print(f"\nTemp Database: {db_file}")
            print("This file contains licensed guideline text: delete it after review.")
            print(f"Review with:   python scripts/print_recent_explanations.py --db {db_file}")
        return 0

    finally:
        if db_file and not args.real_chunks and os.path.exists(db_file):
            import gc
            gc.collect()
            for _ in range(5):
                try:
                    os.remove(db_file)
                    break
                except OSError:
                    time.sleep(0.1)


if __name__ == "__main__":
    sys.exit(main())
