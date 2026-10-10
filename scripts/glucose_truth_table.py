"""
Glucose Truth Table Generator (Stage 9A-5 Task B).
Tests full check-in completion under v2 and v3, with otherwise normal answers
and with symptoms ("shaky and sweating") for:
- 35, 45, 53, 54, 55, 69, 70, 126 mg/dL explicit
- same bare
- 2.0, 2.8, 3.0, 3.8, 7 mmol/L explicit
Computes monotonicity: is level non-increasing as glucose rises?
"""

import os
import sys
import time
import json
import jwt
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store

TEST_PROJECT_ID = "test-glucose-truth"
TEST_KID = "test-key-glucose-truth"

test_db = str(BACKEND_DIR / "test_glucose_truth_scratch.db")
os.environ["LOCAL_DB_PATH"] = test_db
os.environ["DB_BACKEND"] = "sqlite"
os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID

app_store.migrate(db_path=test_db, backend="sqlite")
local_store.init_db(db_path=test_db)

rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com"),
])
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(rsa_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
    .sign(rsa_key, hashes.SHA256())
)
cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
mock_keys = {TEST_KID: cert_pem}
firebase_verify._KEY_CACHE = {"keys": mock_keys, "expires_at": time.time() + 3600}
firebase_verify.fetch_google_public_keys = lambda force_refresh=False: mock_keys

client = TestClient(app)

def get_token(uid: str):
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": f"{uid}@demo.com",
        "name": "Glucose Test Patient",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})

def bootstrap_patient(uid: str):
    tok = get_token(uid)
    headers = {"Authorization": f"Bearer {tok}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": ["diabetes"],
            "on_insulin_or_sulfonylurea": True,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": "en",
        },
    )
    return headers

LEVEL_RANKS = {"routine": 0, "review": 1, "urgent": 2, "emergency": 3}

TEST_INPUTS = [
    # Explicit mg/dL
    ("explicit_mgdl", "35 mg/dL", 35.0),
    ("explicit_mgdl", "45 mg/dL", 45.0),
    ("explicit_mgdl", "53 mg/dL", 53.0),
    ("explicit_mgdl", "54 mg/dL", 54.0),
    ("explicit_mgdl", "55 mg/dL", 55.0),
    ("explicit_mgdl", "69 mg/dL", 69.0),
    ("explicit_mgdl", "70 mg/dL", 70.0),
    ("explicit_mgdl", "126 mg/dL", 126.0),
    # Bare numbers
    ("bare_number", "35", 35.0),
    ("bare_number", "45", 45.0),
    ("bare_number", "53", 53.0),
    ("bare_number", "54", 54.0),
    ("bare_number", "55", 55.0),
    ("bare_number", "69", 69.0),
    ("bare_number", "70", 70.0),
    ("bare_number", "126", 126.0),
    # Explicit mmol/L (converted with x18.0)
    ("explicit_mmol", "2.0 mmol/L", 2.0 * 18.0),
    ("explicit_mmol", "2.8 mmol/L", 2.8 * 18.0),
    ("explicit_mmol", "3.0 mmol/L", 3.0 * 18.0),
    ("explicit_mmol", "3.8 mmol/L", 3.8 * 18.0),
    ("explicit_mmol", "7.0 mmol/L", 7.0 * 18.0),
]

def run_glucose_checkin(engine: str, glucose_str: str, has_symptoms: bool):
    os.environ["INTERVIEW_ENGINE"] = engine
    uid = f"gt_{engine}_{int(time.time()*1000)%1000000}_{os.urandom(2).hex()}"
    headers = bootstrap_patient(uid)

    start_resp = client.post("/api/checkins/start", headers=headers)
    start_body = start_resp.json()
    c_id = start_body["checkin_id"]

    curr_q = start_body.get("question") or ""
    curr_s = start_body.get("step") or ""
    completed = False
    emergency = False
    emergency_reason = None

    for turn in range(16):
        q_low = curr_q.lower()
        s_low = curr_s.lower()

        # Decide answer
        if "blood sugar" in q_low or "glucose" in q_low or "glucose_reading" in s_low or "unit" in q_low or "mmol" in q_low:
            ans = glucose_str
        elif "swallow" in q_low or "eat or drink safely" in q_low:
            ans = "yes"
        elif "feeling" in q_low or "greeting" in s_low or "symptom" in q_low or "hypo_symptoms" in s_low or "shakiness" in q_low:
            if has_symptoms:
                ans = "I feel shaky and sweating"
            else:
                ans = "I am feeling fine, no symptoms"
        elif "fasting" in q_low or "glucose_context" in s_low:
            ans = "fasting"
        elif "prescribed" in q_low or "adherence" in s_low:
            ans = "yes"
        elif "submit" in q_low or "confirm" in q_low or "summary_confirmation" in s_low:
            ans = "yes submit"
        else:
            if has_symptoms and ("episode" in q_low or "low" in q_low or "shakiness" in q_low):
                ans = "shaky and sweating"
            else:
                ans = "no"

        ans_resp = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": ans})
        ans_body = ans_resp.json()

        if ans_body.get("emergency"):
            emergency = True
            emergency_reason = ans_body.get("emergency_reason")
            break
        if ans_body.get("complete"):
            completed = True
            break
        curr_q = ans_body.get("question") or ""
        curr_s = ans_body.get("step") or ""

    comp_resp = client.post(f"/api/checkins/{c_id}/complete", headers=headers)
    comp_body = comp_resp.json() if comp_resp.status_code == 200 else {}

    if emergency:
        lvl = "emergency"
        reasons = [emergency_reason or "emergency"]
    else:
        triage = comp_body.get("triage") or {}
        lvl = triage.get("level", "routine")
        reasons = triage.get("reasons", [])
        if not reasons and triage.get("summary"):
            reasons = [triage.get("summary")]

    return {
        "engine": engine,
        "input_str": glucose_str,
        "has_symptoms": has_symptoms,
        "final_level": lvl,
        "rank": LEVEL_RANKS.get(lvl, 0),
        "reasons": reasons,
        "comp_status": comp_resp.status_code,
        "raw_response": comp_body,
    }

def main():
    print("=" * 110)
    print("STAGE 9A-6 TASK B: GLUCOSE TRUTH TABLE & MONOTONICITY CHECKER")
    print("=" * 110)

    total_failures = 0

    for engine in ["v2", "v3"]:
        for ctx_name, has_symp in [("Normal Answers (No Symptoms)", False), ("With Symptoms ('shaky and sweating')", True)]:
            print(f"\n### Engine: `{engine}` | Context: {ctx_name}\n")
            print("| Series | Glucose Input | Converted mg/dL | Final Level | Rank | Monotonic / Valid? | API Reasons |")
            print("|:---|:---|:---:|:---:|:---:|:---:|:---|")

            # Collect results for all inputs
            evaluated = []
            for series_id, inp_str, conv_val in TEST_INPUTS:
                res = run_glucose_checkin(engine, inp_str, has_symp)
                res["series"] = series_id
                res["conv_val"] = conv_val
                evaluated.append(res)

            # Sort ALL rows across ALL series by converted mg/dL
            evaluated.sort(key=lambda x: (x["conv_val"], x["series"]))

            # Evaluate monotonicity across the unified sorted series
            prev_item = None
            for item in evaluated:
                status_notes = []
                is_violation = False

                if prev_item is not None:
                    # Check identical converted values (e.g. 126 mg/dL vs 7.0 mmol/L)
                    if abs(item["conv_val"] - prev_item["conv_val"]) < 0.2:
                        if item["rank"] != prev_item["rank"]:
                            is_violation = True
                            status_notes.append(
                                f"EQUIVALENCE VIOLATION ({prev_item['input_str']}={prev_item['final_level']} vs {item['input_str']}={item['final_level']})"
                            )
                        else:
                            status_notes.append("EQUIVALENT (OK)")

                    # Low range (< 70 mg/dL): higher glucose must NOT give higher severity (rank <= prev_rank)
                    if item["conv_val"] < 70.0:
                        if item["rank"] > prev_item["rank"] and item["conv_val"] > prev_item["conv_val"]:
                            is_violation = True
                            status_notes.append(
                                f"LOW-RANGE VIOLATION (glucose rose {prev_item['conv_val']:.1f}->{item['conv_val']:.1f} but severity rose {prev_item['final_level']}->{item['final_level']})"
                            )

                    # High range (>= 250 mg/dL): higher glucose must NOT give lower severity (rank >= prev_rank)
                    if prev_item["conv_val"] >= 250.0:
                        if item["rank"] < prev_item["rank"]:
                            is_violation = True
                            status_notes.append(
                                f"HIGH-RANGE VIOLATION (glucose rose {prev_item['conv_val']:.1f}->{item['conv_val']:.1f} but severity dropped {prev_item['final_level']}->{item['final_level']})"
                            )

                if is_violation:
                    total_failures += 1
                    mono_str = "**FAIL**: " + "; ".join(status_notes)
                elif status_notes:
                    mono_str = "; ".join(status_notes)
                else:
                    mono_str = "OK"

                r_str = "; ".join(item["reasons"]) if item["reasons"] else "(none)"
                print(f"| `{item['series']}` | `{item['input_str']}` | {item['conv_val']:.1f} | `{item['final_level']}` | {item['rank']} | {mono_str} | {r_str} |")
                prev_item = item

    print(f"\nMONOTONICITY & EQUIVALENCE SUMMARY: Total Violations = {total_failures}")
    if total_failures > 0:
        print(f"[FAIL] Monotonicity check failed with {total_failures} violations!")
        sys.exit(1)
    else:
        print("[PASS] Monotonicity check passed with 0 violations across all engines and contexts.")

if __name__ == "__main__":
    main()
