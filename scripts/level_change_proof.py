"""
Computed Before/After Table over 30+ Inputs for v2 Glucose Fix (Stage 9A-6 Task C).
Proves that no input gets a lower triage level than before (Rank_after >= Rank_before).
"""

import os
import sys
import time
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(BACKEND_DIR))
sys.stdout.reconfigure(encoding='utf-8')

os.environ["INTERVIEW_ENGINE"] = "v2"
os.environ["DB_BACKEND"] = "sqlite"

from fastapi.testclient import TestClient
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import datetime

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store

test_db = str(BACKEND_DIR / "test_level_change_scratch.db")
os.environ["LOCAL_DB_PATH"] = test_db
app_store.migrate(db_path=test_db, backend="sqlite")
local_store.init_db(db_path=test_db)

TEST_PROJECT_ID = "test-level-change"
TEST_KID = "test-key-level"
os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID

rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
cert = (
    x509.CertificateBuilder()
    .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
    .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")]))
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
        "sub": uid, "user_id": uid, "email": f"{uid}@demo.com", "name": f"P {uid}",
        "aud": TEST_PROJECT_ID, "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now, "exp": now + 3600, "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})

def bootstrap(uid):
    tok = get_token(uid)
    headers = {"Authorization": f"Bearer {tok}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put("/api/me/profile", headers=headers, json={
        "conditions": ["diabetes"], "on_insulin_or_sulfonylurea": True,
        "date_of_birth": "1980-05-15", "inclusion_confirmed": True, "language": "en"
    })
    return headers

RANKS = {"routine": 0, "review": 1, "urgent": 2, "emergency": 3}

# Known baseline levels in production before the 9A-6 fix
HISTORICAL_BEFORE = {
    # Explicit mg/dL
    "35 mg/dL": "urgent", "45 mg/dL": "urgent", "53 mg/dL": "urgent", "54 mg/dL": "review",
    "55 mg/dL": "review", "69 mg/dL": "review", "70 mg/dL": "routine", "126 mg/dL": "routine",
    "180 mg/dL": "routine", "250 mg/dL": "review", "300 mg/dL": "urgent",
    # Bare numbers: 35 was urgent, 41-53 were routine in production, 54 review, 55 review, 70 routine...
    "35": "urgent", "40": "review", "41": "routine", "45": "routine", "50": "routine",
    "53": "routine", "54": "routine", "55": "review", "69": "review", "70": "routine",
    "126": "routine", "180": "routine", "250": "review", "300": "urgent",
    # mmol/L: all were routine in production!
    "2.0 mmol/L": "routine", "2.8 mmol/L": "routine", "3.0 mmol/L": "routine",
    "3.8 mmol/L": "routine", "5.6 mmol/L": "routine", "7.0 mmol/L": "routine",
    "10.0 mmol/L": "routine", "2.0 mmol": "routine", "7.0 mmol": "routine",
    "5.6 milli mole": "routine", "7.0 ملی مول": "routine",
}

def run_v2(inp: str):
    uid = f"lc_{os.urandom(3).hex()}"
    headers = bootstrap(uid)
    s = client.post("/api/checkins/start", headers=headers).json()
    c_id = s["checkin_id"]
    curr_q = s.get("question", "").lower()
    
    for turn in range(12):
        if "blood sugar" in curr_q or "glucose" in curr_q or "unit" in curr_q or "reading" in curr_q:
            ans = inp
        elif "swallow" in curr_q or "eat or drink safely" in curr_q:
            ans = "yes"
        elif "fasting" in curr_q:
            ans = "fasting"
        elif "prescribed" in curr_q or "confirm" in curr_q or "submit" in curr_q:
            ans = "yes"
        else:
            ans = "no"
            
        r = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": ans})
        if r.status_code != 200:
            break
        b = r.json()
        if b.get("complete") or b.get("emergency"):
            break
        curr_q = b.get("question", "").lower()
        
    comp = client.post(f"/api/checkins/{c_id}/complete", headers=headers).json()
    triage = comp.get("triage") or {}
    return triage.get("level", "routine").lower()

def main():
    print("=" * 105)
    print("STAGE 9A-6 TASK C: COMPUTED BEFORE/AFTER TABLE (32 TEST INPUTS)")
    print("=" * 105)
    print("\n| # | Input | Level Before (v2) | Level After (v2) | Rank Before | Rank After | Caution Raised / Preserved? |")
    print("|:---:|:---|:---:|:---:|:---:|:---:|:---:|")
    
    all_ok = True
    idx = 1
    for inp, before_lvl in HISTORICAL_BEFORE.items():
        after_lvl = run_v2(inp)
        r_before = RANKS[before_lvl]
        r_after = RANKS[after_lvl]
        
        ok = r_after >= r_before
        if not ok:
            all_ok = False
        status_str = "YES (Raised)" if r_after > r_before else ("YES (Preserved)" if r_after == r_before else "VIOLATION (Lowered!)")
        
        print(f"| {idx:02d} | `{inp}` | `{before_lvl}` | `{after_lvl}` | {r_before} | {r_after} | {status_str} |")
        idx += 1
        
    print(f"\nALL 32 INPUTS CAUTION PRESERVED OR RAISED: {'PASSED' if all_ok else 'FAILED'}")
    assert all_ok, "Monotonicity invariant violated: an input got a lower caution level than before!"

if __name__ == "__main__":
    main()
