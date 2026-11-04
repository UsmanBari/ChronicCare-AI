"""
Live Smoke Test Script for Explainer Guards (D2).

Can be run with a real GROQ_API_KEY when chosen:
- Checks GROQ_API_KEY is present; if not, prints a clear message and exits 0
- Sets EXPLAIN_ENABLED=true
- Runs 10 fake check-ins through the pipeline (different reading values, some repeated to exercise cache)
- Prints for each: level, mode (llm/cache/template), reason (if template), citations, latency
- Prints token usage reported by Groq
- Stops early if total tokens reach 20,000 (safety token limit)
- NEVER prints the key or patient data
"""
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
import llm.groq_client as groq_client
from main import app
from rag.explain_guards import get_explain_guard_metrics, reset_explain_guards

TEST_PROJECT_ID = "live-smoke-test-project"
TEST_KID = "live-smoke-test-kid"
MAX_TOKEN_BUDGET = 20000


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
        ("c_htn_1", "AHA_ACC_2017", "BP Targets", "hypertension",
         "Stage 1 hypertension is systolic 130-139 mmHg or diastolic 80-89 mmHg.", now),
        ("c_htn_2", "AHA_ACC_2017", "Stage 2 Targets", "hypertension",
         "Stage 2 hypertension is systolic 140 mmHg or higher, or diastolic 90 mmHg or higher.", now),
        ("c_dm_1", "ADA_2024", "Glycemic Targets", "diabetes",
         "Target fasting blood glucose is 80-130 mg/dL for nonpregnant adults.", now),
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        for cid, src, title, cond, text, updated in chunks:
            cur.execute(
                f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (cid, src, title, cond, text, updated),
            )


def main():
    print("=" * 80)
    print("CHRONICCARE AI - LIVE EXPLAINER SMOKE TEST (D2)")
    print("=" * 80)

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key:
        print("[INFO] GROQ_API_KEY environment variable is not set.")
        print("[INFO] To run live smoke tests against Groq LLM, set GROQ_API_KEY and re-run.")
        print("[INFO] Exiting cleanly (exit code 0).")
        return 0

    # Ensure key is never printed
    masked_key = groq_key[:4] + "..." + groq_key[-4:] if len(groq_key) > 8 else "***"
    print(f"[OK] GROQ_API_KEY detected ({masked_key}). Initializing smoke test suite...")

    os.environ["EXPLAIN_ENABLED"] = "true"
    reset_explain_guards()

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_pem = generate_cert(rsa_key)
    db_file = str(REPO_ROOT / "temp_live_smoke.db")
    setup_db(db_file, cert_pem)

    client = TestClient(app)

    # 10 test check-ins with repeated readings to test cache hits
    test_readings = [
        {"bp_sys": 135.0, "bp_dia": 85.0, "cond": "hypertension"},  # 1. new call (stage 1)
        {"bp_sys": 135.0, "bp_dia": 85.0, "cond": "hypertension"},  # 2. same band (cache hit)
        {"bp_sys": 145.0, "bp_dia": 92.0, "cond": "hypertension"},  # 3. new call (stage 2)
        {"bp_sys": 145.0, "bp_dia": 92.0, "cond": "hypertension"},  # 4. same band (cache hit)
        {"bp_sys": 122.0, "bp_dia": 78.0, "cond": "hypertension"},  # 5. routine/elevated
        {"bp_sys": 122.0, "bp_dia": 78.0, "cond": "hypertension"},  # 6. same band (cache hit)
        {"bp_sys": 138.0, "bp_dia": 86.0, "cond": "hypertension"},  # 7. stage 1 band repeat
        {"bp_sys": 150.0, "bp_dia": 95.0, "cond": "hypertension"},  # 8. stage 2 band repeat
        {"bp_sys": 120.0, "bp_dia": 80.0, "cond": "hypertension"},  # 9. normal/elevated
        {"bp_sys": 135.0, "bp_dia": 85.0, "cond": "hypertension"},  # 10. stage 1 repeat
    ]

    print("\nRunning 10 pipeline check-ins...\n")
    print(f"{'#':<3} | {'Level':<10} | {'Mode':<10} | {'Reason':<16} | {'Citations':<14} | {'Latency (s)':<12}")
    print("-" * 75)

    try:
        for idx, item in enumerate(test_readings, start=1):
            # Check token budget safety cap
            metrics = get_explain_guard_metrics()
            used_tokens = metrics["tokens_used_today"]
            if used_tokens >= MAX_TOKEN_BUDGET:
                print(f"\n[ALERT] Reached token safety ceiling ({used_tokens} >= {MAX_TOKEN_BUDGET}). Stopping early.")
                break

            uid = f"smoke_user_{idx}"
            cid = f"smoke_chk_{idx}"
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
                    "conditions": [item["cond"]],
                    "date_of_birth": "1980-01-01",
                    "inclusion_confirmed": True,
                    "language": "en",
                },
            )

            raw_state = {
                "engine": "v3",
                "completed": True,
                "conditions_on_file": [item["cond"]],
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
            elapsed = time.monotonic() - t0

            if resp.status_code != 200:
                print(f"{idx:<3} | ERROR {resp.status_code}: {resp.text[:40]}")
                continue

            data = resp.json()
            triage_level = data.get("triage", {}).get("level", "unknown")
            explanation = data.get("explanation") or {}
            mode = explanation.get("mode", "none")
            reason = explanation.get("reason", "-")
            sources = explanation.get("sources", [])
            citations_str = ",".join(s.get("source_id", "") for s in sources) or "-"

            print(f"{idx:<3} | {triage_level:<10} | {mode:<10} | {reason:<16} | {citations_str:<14} | {elapsed:<12.3f}")

        final_metrics = get_explain_guard_metrics()
        print("\n" + "=" * 80)
        print("SMOKE TEST SUMMARY")
        print("=" * 80)
        print(f"Total LLM calls:   {final_metrics['llm_calls']}")
        print(f"Cache hits:        {final_metrics['cache_hits']}")
        print(f"Cache misses:      {final_metrics['cache_misses']}")
        print(f"Tokens consumed:   {final_metrics['tokens_used_today']} / {MAX_TOKEN_BUDGET} cap")
        print(f"Circuit Breaker:   {final_metrics['breaker_state']}")
        print(f"Fallbacks:         {final_metrics['template_fallbacks_by_reason']}")
        print("=" * 80)
        return 0

    finally:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())

