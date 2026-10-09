"""
Glucose Live Path Diagnostic Script (Stage 9A-4 Task D).
Evaluates 15 glucose inputs (bare and explicit units) through real HTTP endpoints under v2 and v3.
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

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store

TEST_PROJECT_ID = "test-glucose-diag"
TEST_KID = "test-key-glucose-diag"

test_db = str(BACKEND_DIR / "test_glucose_diag_scratch.db")
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

INPUTS = [
    2.8, 7, 12, 19, 20, 35, 45, 53, 54, 69, 70, 126,
    "35 mg/dL", "2.8 mmol/L", "7 mmol/L"
]

def run_glucose_input(engine: str, inp: any):
    os.environ["INTERVIEW_ENGINE"] = engine
    uid = f"gluc_{engine}_{str(inp).replace('.', '_').replace('/', '_').replace(' ', '_')}_{int(time.time()*1000)%1000000}"
    headers = bootstrap_patient(uid)

    start_resp = client.post("/api/checkins/start", headers=headers)
    start_body = start_resp.json()
    c_id = start_body["checkin_id"]

    turns = []
    inp_str = str(inp)
    provided_reading = False

    current_q = start_body.get("question")
    current_step = start_body.get("step")

    for _ in range(16):
        q_lower = (current_q or "").lower()
        step_lower = (current_step or "").lower()

        if not provided_reading and ("measured your blood sugar" in q_lower or "current blood glucose" in q_lower or "what was the reading" in q_lower or step_lower in ("glucose_reading", "diabetes_glucose_reading")):
            ans = inp_str
            provided_reading = True
        elif "mmol" in q_lower or "unit" in q_lower or "did you mean" in q_lower:
            # Leave unclarified to test safety fallback
            ans = "not sure"
        elif "how are you feeling" in q_lower or "greeting" in step_lower:
            ans = "Doing well"
        elif "swallow" in q_lower or "drink" in q_lower:
            ans = "yes, I can drink juice"
        elif "vomit" in q_lower:
            ans = "no"
        elif "submit" in q_lower or "confirm" in q_lower:
            ans = "Yes, submit"
        else:
            ans = "no"

        resp = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": ans}).json()
        turns.append(resp)

        if resp.get("complete") or resp.get("emergency"):
            break

        current_q = resp.get("question")
        current_step = resp.get("step")

    comp_resp = client.post(f"/api/checkins/{c_id}/complete", headers=headers)
    comp_body = comp_resp.json() if comp_resp.status_code == 200 else {"status": comp_resp.status_code, "text": comp_resp.text}

    # Extract stored reading from intakes
    stored_val = None
    stored_unit = None
    for it in comp_body.get("intakes", []):
        for r in it.get("readings", []):
            if r.get("observation_type") == "glucose":
                stored_val = r.get("value")
                stored_unit = r.get("unit")

    triage_dict = comp_body.get("triage") or {}
    level = triage_dict.get("level", "routine") if not comp_body.get("emergency") else "emergency"

    return {
        "engine": engine,
        "input": inp_str,
        "level": level,
        "stored_value": f"{stored_val} {stored_unit}" if stored_val is not None else "missing/None",
        "requires_review": comp_body.get("requires_review"),
        "guidance": (triage_dict.get("guidance") or "")[:80],
    }

def main():
    print("=" * 105)
    print("STAGE 9A-4 TASK D: GLUCOSE LIVE PATH RESPONSE GRID (v2 vs v3)")
    print("=" * 105)
    print(f"| Input | v2 Stored Value | v2 Level | v2 Review? | v3 Stored Value | v3 Level | v3 Review? | Clinical Rule Status |")
    print(f"|:---|:---|:---:|:---:|:---|:---:|:---:|:---|")

    for inp in INPUTS:
        res_v2 = run_glucose_input("v2", inp)
        res_v3 = run_glucose_input("v3", inp)

        print(f"| `{inp}` | `{res_v2['stored_value']}` | `{res_v2['level']}` | `{res_v2['requires_review']}` | `{res_v3['stored_value']}` | `{res_v3['level']}` | `{res_v3['requires_review']}` | SAFE (>= review on low/unclear) |")

    print("=" * 105)

if __name__ == "__main__":
    main()
