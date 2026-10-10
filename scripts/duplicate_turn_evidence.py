"""
Demonstrates exact evidence for same_turn_twice (Stage 9A-5 Task F).
Verifies that:
1. When a client submits a turn with `step`, the first call advances the interview (200 OK).
2. The identical second call (replayed turn / double submit) returns 409 Conflict ('stale_step')
   and DOES NOT advance the interview.
Prints raw HTTP responses and state steps before and after each call.
"""

import os
import sys
import time
from pathlib import Path

TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-dup-turn"
os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID
os.environ["DB_BACKEND"] = "sqlite"

BACKEND_DIR = Path("backend-poc-technical").resolve()
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from main import app
from data_sources import app_store, local_store
from auth import firebase_verify
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

test_db = str(Path("tests/sim/test_dup_turn.db").resolve())
os.environ["LOCAL_DB_PATH"] = test_db
app_store.migrate(db_path=test_db, backend="sqlite")
local_store.init_db(db_path=test_db)

rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
import datetime

now_dt = datetime.datetime.now(datetime.timezone.utc)
cert = (
    x509.CertificateBuilder()
    .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com")]))
    .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com")]))
    .public_key(rsa_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now_dt - datetime.timedelta(days=1))
    .not_valid_after(now_dt + datetime.timedelta(days=10))
    .sign(rsa_key, hashes.SHA256())
)
cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
mock_keys = {TEST_KID: cert_pem}
firebase_verify._KEY_CACHE = {"keys": mock_keys, "expires_at": time.time() + 3600}
firebase_verify.fetch_google_public_keys = lambda force_refresh=False: mock_keys

client = TestClient(app)

def main():
    now = int(time.time())
    uid = "pat-dup-turn-1"
    token = jwt.encode({
        "sub": uid, "user_id": uid, "email": f"{uid}@demo.com",
        "aud": TEST_PROJECT_ID, "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now, "exp": now + 3600, "auth_time": now,
    }, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put("/api/me/profile", headers=headers, json={
        "conditions": ["hypertension"],
        "date_of_birth": "1980-01-01",
        "inclusion_confirmed": True
    })

    # Start check-in
    r_start = client.post("/api/checkins/start", headers=headers)
    checkin_id = r_start.json()["checkin_id"]
    step_0 = r_start.json().get("step")
    q_0 = r_start.json().get("question")
    print(f"=== CHECKIN STARTED ===")
    print(f"Checkin ID: {checkin_id}")
    print(f"Initial Step: {step_0}")
    print(f"Initial Question: {q_0}\n")

    # Turn 1: Valid answer with step='greeting'
    payload_t1 = {"answer": "Feeling good today", "step": "greeting"}
    print(f"--- CALL 1: First submission of Turn 1 ---")
    print(f"Payload: {payload_t1}")
    print(f"Step BEFORE Call 1: {step_0}")
    r_t1 = client.post(f"/api/checkins/{checkin_id}/answer", headers=headers, json=payload_t1)
    print(f"HTTP Status: {r_t1.status_code}")
    print(f"Raw Response: {r_t1.json()}")
    step_after_call1 = r_t1.json().get("step")
    print(f"Step AFTER Call 1: {step_after_call1}\n")

    # Turn 2 (DUPLICATE): Replayed request with the SAME turn payload (step='greeting')
    payload_t1_dup = {"answer": "Feeling good today", "step": "greeting"}
    print(f"--- CALL 2: Duplicate submission of Turn 1 (same_turn_twice) ---")
    print(f"Payload: {payload_t1_dup}")
    print(f"Step BEFORE Call 2: {step_after_call1}")
    r_t1_dup = client.post(f"/api/checkins/{checkin_id}/answer", headers=headers, json=payload_t1_dup)
    print(f"HTTP Status: {r_t1_dup.status_code}")
    print(f"Raw Response: {r_t1_dup.json()}")
    step_after_call2 = r_t1_dup.json().get("step")
    print(f"Step AFTER Call 2: {step_after_call2}\n")

    # Verify interview did not advance on duplicate call
    assert r_t1.status_code == 200, f"Call 1 failed with {r_t1.status_code}"
    assert r_t1_dup.status_code == 409, f"Call 2 expected 409, got {r_t1_dup.status_code}"
    assert r_t1_dup.json().get("detail") == "stale_step"
    assert step_after_call1 == step_after_call2, f"Interview advanced on duplicate call! {step_after_call1} != {step_after_call2}"
    print("=== EVIDENCE VERIFIED: Duplicate turn returned 409 stale_step and did NOT advance state ===")

if __name__ == "__main__":
    main()
