"""
Rule Truth Table Generator (Stage 9A-5 Task A).
Executes check-ins for normal baseline and for every Stage 8b step x answer class
through real live HTTP endpoints under v2 and v3.
Completes through /api/checkins/{id}/complete and extracts the API's actual triage level,
reasons, and factors.
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

TEST_PROJECT_ID = "test-rule-truth"
TEST_KID = "test-key-rule-truth"

test_db = str(BACKEND_DIR / "test_rule_truth_scratch.db")
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
        "name": "Normal Baseline Patient",
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
            "conditions": ["diabetes", "hypertension"],
            "on_insulin_or_sulfonylurea": True,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": "en",
        },
    )
    return headers

STEPS_TO_TEST = [
    "glucose_context",
    "hypo_events_past_week",
    "sick_day_flags",
    "foot_problems",
    "bp_technique",
    "associated_symptoms",
    "otc_meds_bp",
    "missed_doses_reason",
    "patient_free_text_note",
]

ANSWER_CLASSES = {
    "yes": "yes",
    "no": "no",
    "unknown": "I am not sure, don't know",
    "skip": "skip",
    "danger_phrase": "I have crushing chest pain right now",
}

def get_answer_for_turn(target_step: str, target_answer: str, current_q: str, current_step: str) -> str:
    q_low = (current_q or "").lower()
    step_low = (current_step or "").lower()

    # If this step matches the target step under test, return target answer
    is_target = False
    if target_step == "glucose_context" and ("fasting" in q_low or "before a meal" in q_low or "glucose_context" in step_low):
        is_target = True
    elif target_step == "hypo_events_past_week" and ("hypo" in q_low or "low blood sugar episodes" in q_low or "hypo_events" in step_low):
        is_target = True
    elif target_step == "sick_day_flags" and ("vomiting" in q_low or "sick" in q_low or "fluids" in q_low or "sick_day" in step_low):
        is_target = True
    elif target_step == "foot_problems" and ("feet" in q_low or "sores" in q_low or "foot" in step_low):
        is_target = True
    elif target_step == "bp_technique" and ("rest quietly" in q_low or "technique" in step_low or "supported" in q_low):
        is_target = True
    elif target_step == "associated_symptoms" and ("severe headache" in q_low or "shortness of breath" in q_low or "associated_symptoms" in step_low):
        is_target = True
    elif target_step == "otc_meds_bp" and ("anti-inflammatory" in q_low or "ibuprofen" in q_low or "otc_meds" in step_low):
        is_target = True
    elif target_step == "missed_doses_reason" and ("miss" in q_low or "reason" in step_low):
        is_target = True
    elif target_step == "patient_free_text_note" and ("anything else" in q_low or "clinician to know" in q_low or "patient_free_text" in step_low):
        is_target = True

    if is_target:
        return target_answer

    # Normal answers for all other steps
    if "how are you feeling" in q_low or "greeting" in step_low:
        return "I am feeling well, no complaints"
    if "blood sugar" in q_low or "glucose" in q_low or "glucose_reading" in step_low:
        return "120 mg/dL"
    if "systolic" in q_low or "blood pressure" in q_low or "bp_reading" in step_low:
        return "120/80"
    if "fasting" in q_low or "glucose_context" in step_low:
        return "fasting"
    if "rest quietly" in q_low or "technique" in step_low:
        return "yes rested 5 minutes"
    if "prescribed" in q_low or "adherence" in step_low:
        return "yes took all medicines"
    if "submit" in q_low or "confirm" in q_low or "summary_confirm" in step_low:
        return "Yes, submit"
    return "no"

def run_single_checkin(engine: str, target_step: str = None, target_answer_class: str = None):
    os.environ["INTERVIEW_ENGINE"] = engine
    uid = f"rt_{engine}_{target_step or 'base'}_{target_answer_class or 'base'}_{int(time.time()*1000)%1000000}_{os.urandom(2).hex()}"
    headers = bootstrap_patient(uid)

    start_resp = client.post("/api/checkins/start", headers=headers)
    start_body = start_resp.json()
    c_id = start_body["checkin_id"]

    is_emergency = False
    emergency_reason = None
    target_ans_val = ANSWER_CLASSES.get(target_answer_class, "no") if target_answer_class else "no"

    curr_q = start_body.get("question")
    curr_s = start_body.get("step")

    for _ in range(16):
        ans = get_answer_for_turn(target_step, target_ans_val, curr_q, curr_s)
        ans_resp = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": ans})
        body = ans_resp.json()

        if body.get("emergency"):
            is_emergency = True
            emergency_reason = body.get("emergency_reason")
            break
        if body.get("complete"):
            break
        curr_q = body.get("question")
        curr_s = body.get("step")

    comp_resp = client.post(f"/api/checkins/{c_id}/complete", headers=headers)
    comp_body = comp_resp.json() if comp_resp.status_code == 200 else {}

    if is_emergency:
        final_level = "emergency"
        reasons = [emergency_reason or "danger_phrase"]
        factors = []
    else:
        triage_dict = comp_body.get("triage") or {}
        final_level = triage_dict.get("level", "routine")
        reasons = triage_dict.get("reasons", [])
        factors = triage_dict.get("factors", [])

    return {
        "engine": engine,
        "target_step": target_step or "baseline",
        "answer_class": target_answer_class or "baseline",
        "final_level": final_level,
        "reasons": reasons,
        "factors": factors,
    }

def main():
    print("=" * 110)
    print("STAGE 9A-5 TASK A: RULE TRUTH TABLE THROUGH FULL CHECKIN COMPLETION")
    print("=" * 110)

    # 1. Baseline runs
    base_v2 = run_single_checkin("v2")
    base_v3 = run_single_checkin("v3")
    print(f"BASELINE ALL-NORMAL: v2 Level = `{base_v2['final_level']}`, v3 Level = `{base_v3['final_level']}`\n")

    results = []

    print("| Engine | Step | Answer Class | Final Level | Baseline Level | Level Differs? | API Reasons | API Factors | Rule Triggered? |")
    print("|:---:|:---|:---:|:---:|:---:|:---:|:---|:---|:---:|")

    for engine in ["v2", "v3"]:
        base_lvl = base_v2["final_level"] if engine == "v2" else base_v3["final_level"]
        for step in STEPS_TO_TEST:
            for ans_cls in ["yes", "no", "unknown", "skip", "danger_phrase"]:
                res = run_single_checkin(engine, step, ans_cls)
                differs = (res["final_level"] != base_lvl)
                r_str = "; ".join(res["reasons"]) if res["reasons"] else "(none)"
                f_str = "; ".join(res["factors"]) if res["factors"] else "(none)"
                rule_trig = "YES (Level Raised)" if differs else "NO (Level Unchanged)"
                print(f"| {engine} | `{step}` | `{ans_cls}` | `{res['final_level']}` | `{base_lvl}` | {'YES' if differs else 'NO'} | {r_str} | {f_str} | {rule_trig} |")
                results.append(res)

    print("=" * 110)

if __name__ == "__main__":
    main()
