"""
Live Smoke Test Script for Explainer Guards (D2 / Day 4b / Day 5).

For USMAN to run (with real API keys):
- Supports --provider groq|gemini|auto (default auto)
- Supports --mode background|inline (default background)
- Supports --pause SECONDS (pause between calls; default 2 for Groq, 0 for Gemini/auto)
- Checks API keys presence; if missing for chosen provider, prints a clear message and exits 0
- Prints keys strictly as SET or NOT SET (never prints key characters or masked strings)
- Runs 10 fake check-ins (hypertension only, en/ur/roman_ur)
- In background mode: check-in returns pending, script polls /api/checkins/{id}/explanation until ready or timeout (default 30s), then reports final status, mode, reason, provider, tokens, latency-to-pending, latency-to-ready
- Stops early if token usage reaches 20,000 per provider
"""
import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
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
from main import app
from rag.explain_guards import get_explain_guard_metrics, reset_explain_guards

TEST_PROJECT_ID = "live-smoke-test-project"
TEST_KID = "live-smoke-test-kid"
MAX_TOKEN_BUDGET_PER_PROVIDER = 20000


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
        default=30.0,
        help="Poll timeout for background explanation in seconds (default: 30.0)",
    )
    args = parser.parse_args()

    pause = args.pause if args.pause is not None else (2.0 if args.provider == "groq" else 0.0)

    print("=" * 105)
    print("CHRONICCARE AI - LIVE EXPLAINER SMOKE TEST (Groq & Gemini Dual Provider)")
    print("=" * 105)

    groq_set = "SET" if os.getenv("GROQ_API_KEY", "").strip() else "NOT SET"
    gemini_set = "SET" if os.getenv("GEMINI_API_KEY", "").strip() else "NOT SET"

    print(f"Provider mode requested: {args.provider}")
    print(f"Explain mode:            {args.mode}")
    if args.mode == "background":
        job_deadline = float(os.getenv("EXPLAIN_JOB_DEADLINE_SECONDS", "45.0"))
        print(f"Job Deadline:            {job_deadline:.1f} s")
    else:
        print(f"Time Budget:             {args.budget:.1f} s")
    print(f"Pause between calls:     {pause:.1f} s")
    print(f"Poll timeout:            {args.poll_timeout:.1f} s")
    print(f"GROQ_API_KEY:            {groq_set}")
    print(f"GEMINI_API_KEY:          {gemini_set}")

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
    os.environ["EXPLAIN_LLM_CONDITIONS"] = "hypertension"
    reset_explain_guards()

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_pem = generate_cert(rsa_key)
    db_file = str(REPO_ROOT / "temp_live_smoke.db")
    setup_db(db_file, cert_pem)

    client = TestClient(app)

    # 10 test check-ins across en, ur, roman_ur with repeated readings to test cache
    test_checkins = [
        {"bp_sys": 135.0, "bp_dia": 85.0, "lang": "en"},
        {"bp_sys": 135.0, "bp_dia": 85.0, "lang": "en"},        # Cache hit
        {"bp_sys": 145.0, "bp_dia": 92.0, "lang": "en"},
        {"bp_sys": 132.0, "bp_dia": 84.0, "lang": "ur"},
        {"bp_sys": 132.0, "bp_dia": 84.0, "lang": "ur"},        # Cache hit
        {"bp_sys": 150.0, "bp_dia": 95.0, "lang": "ur"},
        {"bp_sys": 125.0, "bp_dia": 82.0, "lang": "roman_ur"},
        {"bp_sys": 125.0, "bp_dia": 82.0, "lang": "roman_ur"},  # Cache hit
        {"bp_sys": 142.0, "bp_dia": 91.0, "lang": "roman_ur"},
        {"bp_sys": 135.0, "bp_dia": 85.0, "lang": "en"},        # Cache hit
    ]

    print("\nRunning 10 pipeline check-ins (Hypertension only, en / ur / roman_ur)...\n")
    if args.mode == "background":
        print(f"{'#':<3} | {'Lang':<8} | {'Level':<10} | {'Provider':<10} | {'Mode':<10} | {'Reason':<16} | {'Tokens':<8} | {'Lat.Pend':<10} | {'Lat.Ready':<10} | {'Provider Latency':<25}")
        print("-" * 130)
    else:
        print(f"{'#':<3} | {'Lang':<8} | {'Level':<10} | {'Provider':<10} | {'Mode':<10} | {'Reason':<16} | {'Tokens':<8} | {'Elapsed':<10} | {'Provider Latency':<25}")
        print("-" * 115)

    try:
        run_id = int(time.time())
        prev_tokens_groq = 0
        prev_tokens_gemini = 0

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
            client.put(
                "/api/me/profile",
                headers=headers,
                json={
                    "conditions": ["hypertension"],
                    "date_of_birth": "1980-01-01",
                    "inclusion_confirmed": True,
                    "language": item["lang"],
                },
            )

            raw_state = {
                "engine": "v3",
                "completed": True,
                "conditions_on_file": ["hypertension"],
                "readings": {"blood_pressure_systolic": item["bp_sys"], "blood_pressure_diastolic": item["bp_dia"]},
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

            if args.mode == "background":
                print(
                    f"{idx:<3} | {item['lang']:<8} | {triage_level:<10} | {provider_used:<10} | "
                    f"{mode:<10} | {str(reason):<16} | {tokens_delta:<8} | {lat_pending:<10.3f} | {lat_ready:<10.3f} | {prov_timing_str:<25}"
                )
            else:
                print(
                    f"{idx:<3} | {item['lang']:<8} | {triage_level:<10} | {provider_used:<10} | "
                    f"{mode:<10} | {str(reason):<16} | {tokens_delta:<8} | {lat_pending:<10.3f} | {prov_timing_str:<25}"
                )

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
        print("=" * 105)
        return 0

    finally:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())
