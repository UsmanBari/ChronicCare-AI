"""
Live API Before/After Table for Vomiting & Inability to Keep Fluids Red Flags (Stage 9A-7 Task B).
Evaluates 32 sentences (positives, negations, near-misses) through the real FastAPI TestClient.
Proves that no sentence gets a lower triage level (Rank_after >= Rank_before).
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
if hasattr(sys.stdout, 'reconfigure'):
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

test_db = str(BACKEND_DIR / "test_vomiting_scratch.db")
os.environ["LOCAL_DB_PATH"] = test_db
app_store.migrate(db_path=test_db, backend="sqlite")
local_store.init_db(db_path=test_db)

TEST_PROJECT_ID = "test-vomiting-flags"
TEST_KID = "test-key-vomiting"
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

def bootstrap(uid: str):
    tok = get_token(uid)
    headers = {"Authorization": f"Bearer {tok}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put("/api/me/profile", headers=headers, json={
        "conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1980-05-15", "inclusion_confirmed": True, "language": "en"
    })
    return headers

RANKS = {"routine": 0, "review": 1, "urgent": 2, "emergency": 3}

# 32 Test sentences
SENTENCES = [
    # --- Positives (Should trigger emergency red-flag stop) ---
    ("I have been vomiting and cannot keep fluids down", "positive", "routine"),
    ("cannot keep fluids down", "positive", "routine"),
    ("can not keep fluids down", "positive", "routine"),
    ("unable to keep fluids down", "positive", "routine"),
    ("not able to keep fluids down", "positive", "routine"),
    ("can't keep fluids down", "positive", "emergency"),
    ("cant keep fluids down", "positive", "emergency"),
    ("cannot keep anything down", "positive", "routine"),
    ("can not keep anything down", "positive", "routine"),
    ("unable to keep anything down", "positive", "routine"),
    ("not able to keep anything down", "positive", "routine"),
    ("can't keep anything down", "positive", "emergency"),
    ("cant keep anything down", "positive", "emergency"),
    ("throwing up everything", "positive", "routine"),
    ("won't stay down", "positive", "routine"),
    ("wont stay down", "positive", "routine"),
    ("keep nothing down", "positive", "routine"),
    ("vomiting all day", "positive", "routine"),
    ("vomiting nonstop", "positive", "emergency"),
    ("vomiting non-stop", "positive", "emergency"),
    ("musalsal ultiyan", "positive", "routine"),
    ("ulti ruk nahi rahi", "positive", "routine"),
    ("paani bhi nahi rukta", "positive", "routine"),

    # --- Negations (Must NOT trigger red flag, stay routine) ---
    ("I am not vomiting", "negation", "routine"),
    ("no vomiting, I can keep fluids down", "negation", "routine"),
    ("I do not have vomiting and can keep fluids down", "negation", "routine"),
    ("denies vomiting all day", "negation", "routine"),
    ("without vomiting and able to keep fluids down", "negation", "routine"),
    ("never had vomiting, keeping fluids down fine", "negation", "routine"),

    # --- Near Misses / Benign (Must NOT trigger red flag, stay routine) ---
    ("felt slightly nauseous this morning", "near_miss", "routine"),
    ("I feel like throwing up but haven't", "near_miss", "routine"),
    ("drank plenty of fluids today", "near_miss", "routine"),
]

def run_sentence(sentence: str) -> str:
    uid = f"vom_{os.urandom(3).hex()}"
    headers = bootstrap(uid)
    s = client.post("/api/checkins/start", headers=headers).json()
    c_id = s["checkin_id"]

    # Provide the sentence at turn 1 (symptom free-text / greeting response)
    r = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": sentence})
    res_data = r.json()
    curr_step = res_data.get("current_step") or res_data.get("step")

    # If safety danger stop triggered immediately
    if res_data.get("emergency") or curr_step == "safety_danger_stop" or res_data.get("safety_danger_stop"):
        return "emergency"

    # Otherwise complete check-in with normal responses to determine final triage level
    for turn in range(10):
        curr_q = (res_data.get("question") or "").lower()
        if "blood sugar" in curr_q or "glucose" in curr_q or "unit" in curr_q or "reading" in curr_q:
            ans = "120"
        elif "fasting" in curr_q:
            ans = "fasting"
        elif "prescribed" in curr_q or "confirm" in curr_q or "submit" in curr_q:
            ans = "yes"
        else:
            ans = "no"

        r = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": ans})
        res_data = r.json()
        if res_data.get("emergency"):
            return "emergency"
        if res_data.get("is_complete") or res_data.get("complete") or res_data.get("interview_complete"):
            break

    # Get final checkin record
    summary = client.get(f"/api/checkins/{c_id}", headers=headers).json()
    res_lvl = (summary.get("result") or {}).get("triage_level")
    stat = summary.get("status")
    if stat == "emergency" or res_lvl == "emergency":
        return "emergency"
    if stat == "urgent" or res_lvl == "urgent":
        return "urgent"
    if stat == "review" or res_lvl == "review":
        return "review"
    return "routine"

def main():
    print("# Generated Before/After Evaluation Table for Vomiting & Fluids Red Flags")
    print(f"Total Sentences: {len(SENTENCES)}")
    print(f"Engine: v2 (default) through live FastAPI TestClient\n")

    print("| # | Input Sentence | Category | Before Level | After Level | Shift | Rank (Before -> After) | Safe? |")
    print("|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|")

    no_downgrade = True
    for i, (sent, cat, before_lvl) in enumerate(SENTENCES, 1):
        after_lvl = run_sentence(sent)
        r_before = RANKS[before_lvl]
        r_after = RANKS[after_lvl]
        if r_after < r_before:
            no_downgrade = False
            safe_str = "DOWNGRADE (UNSAFE)"
        elif r_after > r_before:
            safe_str = "UPGRADE (CAUTION)"
        else:
            safe_str = "PRESERVED"

        shift = f"{before_lvl} -> {after_lvl}"
        rank_str = f"{r_before} -> {r_after}"
        print(f"| {i} | \"{sent}\" | `{cat}` | `{before_lvl}` | `{after_lvl}` | {shift} | {rank_str} | **{safe_str}** |")

    print("\n" + "=" * 90)
    print(f"PROVE NO SENTENCE GOT A LOWER LEVEL: {'PASSED (All Rank_after >= Rank_before)' if no_downgrade else 'FAILED'}")
    print("=" * 90)

if __name__ == "__main__":
    main()
