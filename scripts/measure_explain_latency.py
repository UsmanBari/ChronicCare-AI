"""
Latency Benchmark for Explainer Guards (D1 / Day 4b / Day 5).

Simulates 50 check-ins through real endpoints with a fake LLM injected with realistic delays:
- 40 calls with 200-400 ms response
- 5 calls with 2-3 s response (edge of budget)
- 3 calls with 10 s hang (hits budget)
- 2 calls that raise an exception

Measures and prints clean table comparing:
- Mode (EXPLAIN OFF vs EXPLAIN INLINE vs EXPLAIN BACKGROUND)
- p50, p95, max latency for /complete
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


def make_simulated_llm(profile_sequence: List[str]):
    call_idx = 0

    def _mock_chat(messages, **kwargs):
        nonlocal call_idx
        idx = call_idx
        call_idx += 1
        cat = profile_sequence[idx % len(profile_sequence)]

        if cat == "fast":
            delay = random.uniform(0.20, 0.40)
        elif cat == "edge":
            delay = random.uniform(2.0, 2.5)
        elif cat == "hang":
            delay = 10.0
        elif cat == "error":
            raise RuntimeError("Simulated Groq provider 500 internal error")
        else:
            delay = 0.25

        timeout = kwargs.get("timeout", 3.0)
        actual_sleep = min(delay, timeout)
        time.sleep(actual_sleep)

        if delay > timeout:
            raise TimeoutError(f"Simulated timeout after {timeout:.2f}s")

        user_msg = ""
        for m in messages:
            if m.get("role") == "user":
                user_msg += m.get("content", "")

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


def run_benchmark(explain_enabled: bool, explain_mode: str, rsa_key, client: TestClient) -> Dict[str, Any]:
    reset_explain_guards()
    os.environ["EXPLAIN_ENABLED"] = "true" if explain_enabled else "false"
    os.environ["EXPLAIN_MODE"] = explain_mode

    # Profile: 40 fast, 5 edge, 3 hang, 2 error
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
        mode_tag = f"{explain_mode}_{i}" if explain_enabled else f"off_{i}"
        uid = f"bench_{mode_tag}"
        cid = f"chk_{mode_tag}"
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

        stored = app_store.get_checkin_result(cid)
        if stored and stored.get("explanation"):
            expl = stored["explanation"]
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
    llm_calls = metrics.get("llm_calls", 0) if "llm_calls" in metrics else sum(metrics.get("llm_calls_by_provider", {}).values())
    return {
        "explain_enabled": explain_enabled,
        "explain_mode": explain_mode,
        "p50": p50,
        "p95": p95,
        "max": max_lat,
        "llm_calls": llm_calls,
        "cache_hits": metrics.get("cache_hits", 0),
        "cache_misses": metrics.get("cache_misses", 0),
        "mode_counts": mode_counts,
        "template_reasons": template_reasons,
        "fallbacks": metrics.get("template_fallbacks_by_reason", {}),
    }


def main():
    print("=" * 85)
    print("EXPLAINER LATENCY BENCHMARK (50 Check-ins per mode)")
    print("=" * 85)

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_pem = generate_cert(rsa_key)
    db_file = str(REPO_ROOT / "temp_latency_bench.db")
    setup_db(db_file, cert_pem)

    client = TestClient(app)

    try:
        print("1. Running EXPLAIN=OFF baseline...")
        res_off = run_benchmark(explain_enabled=False, explain_mode="inline", rsa_key=rsa_key, client=client)

        print("2. Running EXPLAIN=ON (INLINE)...")
        res_inline = run_benchmark(explain_enabled=True, explain_mode="inline", rsa_key=rsa_key, client=client)

        print("3. Running EXPLAIN=ON (BACKGROUND)...")
        res_bg = run_benchmark(explain_enabled=True, explain_mode="background", rsa_key=rsa_key, client=client)

        # Print results table
        print("\n" + "=" * 115)
        print(f"{'Mode':<18} | {'p50 (s)':<10} | {'p95 (s)':<10} | {'max (s)':<10} | {'LLM calls':<10} | {'Cache hits':<10} | {'Fallbacks by Reason'}")
        print("-" * 115)
        for r in (res_off, res_inline, res_bg):
            if not r["explain_enabled"]:
                mode_str = "EXPLAIN OFF"
            elif r["explain_mode"] == "inline":
                mode_str = "EXPLAIN INLINE"
            else:
                mode_str = "EXPLAIN BG (/comp)"
            fb_str = ", ".join(f"{k}:{v}" for k, v in r["fallbacks"].items() if v > 0) or "none"
            print(f"{mode_str:<18} | {r['p50']:<10.3f} | {r['p95']:<10.3f} | {r['max']:<10.3f} | {r['llm_calls']:<10} | {r['cache_hits']:<10} | {fb_str}")
        print("=" * 115)

        # In background mode, /complete latency overhead over EXPLAIN OFF is < 0.5s
        bg_overhead_p50 = res_bg["p50"] - res_off["p50"]
        print(f"\nBackground /complete p50 overhead over baseline: {bg_overhead_p50*1000:.1f} ms")
        assert res_inline["p95"] < 3.0, f"inline p95 violated: {res_inline['p95']:.2f}s >= 3.0s"
        assert res_bg["p95"] < 1.0, f"background /complete p95 violated: {res_bg['p95']:.2f}s >= 1.0s"
        assert bg_overhead_p50 < 0.5, f"background overhead violated: {bg_overhead_p50:.2f}s >= 0.5s"
        print("All latency assertions PASSED: inline p95 < 3.0s, background /complete p95 < 1.0s, overhead < 0.5s.")
        return 0

    finally:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())
