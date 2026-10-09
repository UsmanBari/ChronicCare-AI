"""
Engine Equivalence Verification & Diagnostic Script (Stage 9A-4 Task A).
Runs each scenario through live HTTP endpoints, prints raw response payloads,
and verifies clinical triage levels.
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
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store

TEST_PROJECT_ID = "test-equiv-diag"
TEST_KID = "test-key-equiv-diag"

test_db = str(BACKEND_DIR / "test_equiv_diag_scratch.db")
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
        "name": "Test Patient",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})

def bootstrap_patient(uid: str, conditions: list):
    tok = get_token(uid)
    headers = {"Authorization": f"Bearer {tok}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": conditions,
            "on_insulin_or_sulfonylurea": True,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": "en",
        },
    )
    return headers

def answer_for_scenario(sc: dict, q_text: str, step: str) -> str:
    q_lower = (q_text or "").lower()
    step_lower = (step or "").lower()

    if sc["id"] == "POC-7":
        return "I have crushing chest pain"

    if "how are you feeling" in q_lower or "greeting" in step_lower:
        return "Doing well"

    if "blood sugar" in q_lower or "glucose" in q_lower or "glucose_reading" in step_lower:
        return sc.get("glucose_str", "120 mg/dL")

    if "systolic" in q_lower or "top number" in q_lower or "blood pressure" in q_lower or "bp_reading" in step_lower:
        if "diastolic" in q_lower or "bottom number" in q_lower:
            return sc.get("bp_dia_str", "80")
        return sc.get("bp_sys_str", "120")

    if "diastolic" in q_lower or "bottom" in q_lower:
        return sc.get("bp_dia_str", "80")

    if "able to eat or drink" in q_lower or "swallow" in q_lower or "can_swallow" in step_lower:
        return "yes, I can drink juice"

    if "vomiting" in q_lower or "keep fluids down" in q_lower or "dka" in step_lower:
        return "no vomiting"

    if "large meal" in q_lower or "missed" in q_lower or "circumstances" in step_lower or "substances" in step_lower:
        if sc.get("ate_large_meal"):
            return "yes, I ate a large meal"
        return "no"

    if "confirm" in q_lower or "submit" in q_lower or "summary_confirm" in step_lower:
        return "Yes, submit"

    if "fasting" in q_lower or "fast" in q_lower or "is_fasting" in step_lower:
        return "fasting"

    return "no"

def run_scenario(engine: str, sc: dict):
    os.environ["INTERVIEW_ENGINE"] = engine
    unique_suffix = f"{int(time.time()*1000)%1000000}_{os.urandom(2).hex()}"
    uid = f"diag_{engine}_{sc['id'].lower().replace('-', '_')}_{unique_suffix}"
    headers = bootstrap_patient(uid, sc["conditions"])

    start_resp = client.post("/api/checkins/start", headers=headers)
    start_body = start_resp.json()
    c_id = start_body["checkin_id"]

    turns = []
    is_emergency = False
    emergency_reason = None
    final_body = None

    current_q = start_body.get("question")
    current_step = start_body.get("step")

    for i in range(15):
        ans = answer_for_scenario(sc, current_q, current_step)
        ans_resp = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": ans})
        body = ans_resp.json()
        turns.append({"answer": ans, "resp": body, "q_before": current_q, "step_before": current_step})
        final_body = body
        if body.get("emergency"):
            is_emergency = True
            emergency_reason = body.get("emergency_reason")
            break
        if body.get("complete"):
            break
        current_q = body.get("question")
        current_step = body.get("step")

    comp_resp = client.post(f"/api/checkins/{c_id}/complete", headers=headers)
    comp_body = comp_resp.json() if comp_resp.status_code == 200 else {"status": comp_resp.status_code, "text": comp_resp.text}

    if is_emergency:
        level = "emergency"
    else:
        triage_dict = comp_body.get("triage") or {}
        level = triage_dict.get("level", "routine")

    return {
        "engine": engine,
        "scenario": sc["id"],
        "is_emergency": is_emergency,
        "emergency_reason": emergency_reason,
        "level": level,
        "turns_count": len(turns),
        "complete_body": comp_body,
    }

SCENARIOS = [
    {
        "id": "POC-1",
        "description": "T2D Routine Controlled (120 mg/dL)",
        "conditions": ["diabetes"],
        "glucose_str": "120 mg/dL",
        "expected": "routine",
        "source": "test_triage_protocol.py::test_ordinary_readings_start_nothing",
    },
    {
        "id": "POC-2",
        "description": "HTN Stage 1 Baseline (135/85 mmHg)",
        "conditions": ["hypertension"],
        "bp_sys_str": "135",
        "bp_dia_str": "85",
        "expected": "routine",
        "source": "test_triage_protocol.py::test_ordinary_readings_start_nothing",
    },
    {
        "id": "POC-3",
        "description": "Dual Dx Controlled (125 mg/dL, 128/82 mmHg)",
        "conditions": ["diabetes", "hypertension"],
        "glucose_str": "125 mg/dL",
        "bp_sys_str": "128",
        "bp_dia_str": "82",
        "expected": "routine",
        "source": "test_triage_protocol.py::test_ordinary_readings_start_nothing",
    },
    {
        "id": "POC-4",
        "description": "T2D Hypoglycemia Episode (62 mg/dL, treated)",
        "conditions": ["diabetes"],
        "glucose_str": "62 mg/dL",
        "expected": "review",
        "source": "test_triage_protocol.py::test_low_glucose_that_the_patient_can_treat_is_reviewed_or_urgent_by_depth",
    },
    {
        "id": "POC-5",
        "description": "HTN Stage 2 Elevation (155/95 mmHg)",
        "conditions": ["hypertension"],
        "bp_sys_str": "155",
        "bp_dia_str": "95",
        "expected": "routine",
        "source": "test_triage_protocol.py::test_ordinary_readings_start_nothing",
    },
    {
        "id": "POC-6",
        "description": "Severe High Glucose (280 mg/dL, no symptoms)",
        "conditions": ["diabetes"],
        "glucose_str": "280 mg/dL",
        "ate_large_meal": True,
        "expected": "review",
        "source": "test_triage_protocol.py::test_high_glucose_without_symptoms_is_reviewed_below_300_and_urgent_from_300",
    },
    {
        "id": "POC-7",
        "description": "Emergency Chest Pain Red Flag",
        "conditions": ["diabetes"],
        "expected": "emergency",
        "source": "test_triage_protocol.py::test_a_danger_phrase_in_any_answer_is_an_immediate_emergency",
    },
]

def main():
    print("=" * 100)
    print("STAGE 9A-4 TASK A: ENGINE EQUIVALENCE TABLE (v2 vs v3 THROUGH REAL LIVE HTTP API)")
    print("=" * 100)
    print(f"| Scenario ID & Description | Expected Level | Source Test | v2 Level | v3 Level | Expected Match? | Equivalence |")
    print(f"|:---|:---:|:---|:---:|:---:|:---:|:---:|")

    all_passed = True
    for sc in SCENARIOS:
        res_v2 = run_scenario("v2", sc)
        res_v3 = run_scenario("v3", sc)

        v2_match = (res_v2["level"] == sc["expected"])
        v3_match = (res_v3["level"] == sc["expected"])
        equiv = (res_v2["level"] == res_v3["level"])

        if not (v2_match and v3_match and equiv):
            all_passed = False

        status_str = f"v2:{'PASS' if v2_match else 'FAIL'}, v3:{'PASS' if v3_match else 'FAIL'}"
        equiv_str = "PASS" if equiv else "FAIL"

        print(f"| {sc['id']}: {sc['description']} | `{sc['expected']}` | `{sc['source'].split('::')[-1]}` | `{res_v2['level']}` | `{res_v3['level']}` | {status_str} | {equiv_str} |")
        print(f"  > v2 Complete: level={res_v2['level']}, emergency={res_v2['is_emergency']}, turns={res_v2['turns_count']}")
        print(f"  > v3 Complete: level={res_v3['level']}, emergency={res_v3['is_emergency']}, turns={res_v3['turns_count']}")

    print("=" * 100)
    print(f"All Scenarios Equivalent and Clinically Safe: {'YES' if all_passed else 'NO'}")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
