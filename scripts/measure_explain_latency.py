"""
Latency Benchmark for Explainer Guards (D1).

Simulates 50 check-ins through real endpoints with a fake LLM injected with realistic delays:
- 40 calls with 200-400 ms response
- 5 calls with 2-3 s response (edge of budget)
- 3 calls with 10 s hang (hits budget)
- 2 calls that raise an exception

Measures and prints clean table comparing:
- Mode (EXPLAIN off vs on)
- p50, p95, max latency
- LLM calls
- Mode counts (llm, cache, template by reason)
- Template fallbacks (by reason)
"""
import copy
import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

TEST_PROJECT_ID = "test-latency-bench"
TEST_KID = "test-key-latency-bench"


def generate_cert(rsa_key):
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-bench")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-bench")]))
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
    os.environ["EXPLAIN_BUDGET_SECONDS"] = "3.0"

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    mock_keys = {TEST_KID: cert_pem}
    firebase_verify._KEY_CACHE = {"keys": mock_keys, "expires_at": time.time() + 3600}
    firebase_verify.fetch_google_public_keys = lambda force_refresh=False: mock_keys

    now = datetime.now(timezone.utc).isoformat()
    chunks = [
        ("c_htn_1", "AHA_ACC_2017", "BP Targets", "hypertension",
         "Stage 1 hypertension is systolic 130-139 mmHg or diastolic 80-89 mmHg.", now),
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


def make_simulated_llm(plan: List[str]):
    """
    Creates an LLM mock that follows the specified call plan:
    - 'fast': 200-400 ms
    - 'edge': 2.0-2.3 s
    - 'hang': 10 s (budget timeout)
    - 'error': raises RuntimeError

    Grounded to patient SBP and cites [S1] without level conflict words.
    """
    call_index = [0]

    def _mock_chat(**kwargs) -> Tuple[str, int]:
        idx = call_index[0]
        call_index[0] += 1
        kind = plan[idx % len(plan)]

        if kind == "error":
            raise RuntimeError("Simulated LLM upstream failure")
        elif kind == "hang":
            time.sleep(10.0)
            text = json.dumps({
                "sentences": [
                    {"text": "Late reading text [S1].", "cites": ["S1"]},
                    {"text": "Regular tracking helps [S1].", "cites": ["S1"]},
                ]
            })
            return (text, 60)
        elif kind == "edge":
            time.sleep(random.uniform(2.0, 2.3))
        else:  # fast
            time.sleep(random.uniform(0.20, 0.40))

        # Extract patient's SBP from user prompt so number validator V3 passes
        user_msg = kwargs.get("messages", [])[-1]["content"] if kwargs.get("messages") else ""
        sbp_match = re.search(r'"blood_pressure_systolic":\s*(\d+(?:\.\d+)?)', user_msg)
        sbp = sbp_match.group(1) if sbp_match else "135"

        text = json.dumps({
            "sentences": [
                {"text": f"Your blood pressure reading of {sbp} mmHg has been recorded for review [S1].", "cites": ["S1"]},
                {"text": "Consistent monitoring supports cardiovascular health [S1].", "cites": ["S1"]},
            ]
        })
        return (text, 60)

    return _mock_chat


def run_benchmark(explain_enabled: bool, rsa_key, client: TestClient) -> Dict[str, Any]:
    reset_explain_guards()
    os.environ["EXPLAIN_ENABLED"] = "true" if explain_enabled else "false"

    # Construct the 50-call profile:
    # 40 fast, 5 edge, 3 hang, 2 error
    profile = ["fast"] * 40 + ["edge"] * 5 + ["hang"] * 3 + ["error"] * 2
    random.seed(42)
    random.shuffle(profile)

    mock_llm = make_simulated_llm(profile)
    groq_client.chat_with_usage = mock_llm
    groq_client.chat = lambda **kw: mock_llm(**kw)[0]
    groq_client.is_configured = lambda: True

    latencies: List[float] = []
    mode_counts: Dict[str, int] = {"llm": 0, "cache": 0, "template": 0}
    template_reasons: Dict[str, int] = {}

    for i in range(50):
        uid = f"bench_{'on' if explain_enabled else 'off'}_{i}"
        cid = f"chk_{'on' if explain_enabled else 'off'}_{i}"
        token = get_token(rsa_key, uid)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        client.post("/api/auth/session", headers=headers)
        local_store.add_local_patient_if_missing(f"local-{uid}", name=f"User {uid}", date_of_birth="1980-01-01")
        client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
        client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
        client.put(
            "/api/me/profile",
            headers=headers,
            json={
                "conditions": ["hypertension"],
                "date_of_birth": "1980-01-01",
                "inclusion_confirmed": True,
                "language": "en",
            },
        )

        # Vary systolic so we exercise both cache hits and misses
        # 10 values repeated across 50 check-ins
        sbp = 125.0 + (i % 10) * 2.0
        raw_state = {
            "engine": "v3",
            "completed": True,
            "conditions_on_file": ["hypertension"],
            "readings": {"blood_pressure_systolic": sbp, "blood_pressure_diastolic": 80.0},
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
        assert resp.status_code == 200, f"Checkin failed with {resp.status_code}: {resp.text}"
        latencies.append(elapsed)

        expl = resp.json().get("explanation")
        if expl:
            m = expl.get("mode", "unknown")
            mode_counts[m] = mode_counts.get(m, 0) + 1
            if m == "template":
                r = expl.get("reason", "unknown")
                template_reasons[r] = template_reasons.get(r, 0) + 1

    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.50)]
    p95 = latencies[min(int(n * 0.95), n - 1)]
    max_lat = latencies[-1]

    metrics = get_explain_guard_metrics()
    return {
        "explain_enabled": explain_enabled,
        "p50": p50,
        "p95": p95,
        "max": max_lat,
        "llm_calls": metrics["llm_calls"],
        "cache_hits": metrics["cache_hits"],
        "cache_misses": metrics["cache_misses"],
        "mode_counts": mode_counts,
        "template_reasons": template_reasons,
        "fallbacks": metrics["template_fallbacks_by_reason"],
    }


def main():
    print("=" * 80)
    print("EXPLAINER LATENCY BENCHMARK (50 Check-ins per mode)")
    print("=" * 80)

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_pem = generate_cert(rsa_key)
    db_file = str(REPO_ROOT / "temp_latency_bench.db")
    setup_db(db_file, cert_pem)

    client = TestClient(app)

    print("Running EXPLAIN=OFF baseline...")
    res_off = run_benchmark(explain_enabled=False, rsa_key=rsa_key, client=client)

    print("Running EXPLAIN=ON guarded...")
    res_on = run_benchmark(explain_enabled=True, rsa_key=rsa_key, client=client)

    # Clean up temp db
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass

    # Print results table
    print("\n" + "=" * 115)
    print(f"{'Mode':<14} | {'p50 (s)':<10} | {'p95 (s)':<10} | {'max (s)':<10} | {'LLM calls':<10} | {'Cache hits':<10} | {'Fallbacks by Reason'}")
    print("-" * 115)
    for r in (res_off, res_on):
        mode_str = "EXPLAIN ON" if r["explain_enabled"] else "EXPLAIN OFF"
        fb_str = ", ".join(f"{k}:{v}" for k, v in r["fallbacks"].items() if v > 0) or "none"
        print(f"{mode_str:<14} | {r['p50']:<10.3f} | {r['p95']:<10.3f} | {r['max']:<10.3f} | {r['llm_calls']:<10} | {r['cache_hits']:<10} | {fb_str}")
    print("=" * 115)

    if res_on["explain_enabled"]:
        print("\nMode Counts (EXPLAIN=ON):")
        print(f"  llm:      {res_on['mode_counts'].get('llm', 0)}")
        print(f"  cache:    {res_on['mode_counts'].get('cache', 0)}")
        print(f"  template: {res_on['mode_counts'].get('template', 0)}")
        if res_on["template_reasons"]:
            print(f"    reasons: {res_on['template_reasons']}")

    # Verification checks
    if res_on["explain_enabled"]:
        assert res_on["p95"] < 3.0, f"p95 violated: {res_on['p95']:.2f}s >= 3.0s"
        assert res_on["max"] < 4.0, f"max violated: {res_on['max']:.2f}s >= 4.0s (budget + 1s)"
        print("\nAll latency assertions PASSED: p95 < 3.0s, max < 4.0s (budget + 1s).")


if __name__ == "__main__":
    main()
