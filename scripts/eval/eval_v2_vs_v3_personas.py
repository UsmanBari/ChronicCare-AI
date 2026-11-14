"""
Evaluates the 52 personas (tests/sim/personas.json) through BOTH v2 and v3 engines.
Measures:
- Total turns and average turns
- Repeated questions (same slot asked again after being filled)
- Contradictory questions (hyper after glucose < 70, hypo after glucose >= 250, high-BP after BP < 90/60)
- Cross-condition leakage (BP questions to diabetes-only, glucose questions to HTN-only)
- Emergency recall, under-triage, over-triage, exact match, incomplete interviews
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import jwt
import datetime
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store
from scripts.run_v3_personas import build_persona_facts, pick_answer

TEST_PROJECT_ID = "test-eval-v2v3"
TEST_KID = "test-key-eval-v2v3"

test_db = str(BACKEND_DIR / "test_eval_v2v3.db")
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

def bootstrap_patient(uid: str, conditions: List[str], on_insulin: bool = False, lang: str = "en"):
    tok = get_token(uid)
    headers = {"Authorization": f"Bearer {tok}"}
    profile_lang = "ur" if lang in ("ur", "roman_ur") else "en"
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": conditions,
            "on_insulin_or_sulfonylurea": on_insulin,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": profile_lang,
        },
    )
    return headers

def evaluate_engine(engine_name: str, personas: List[Dict[str, Any]]) -> Dict[str, Any]:
    os.environ["INTERVIEW_ENGINE"] = engine_name
    
    total_turns = 0
    total_repeats = 0
    total_contradictions = 0
    total_cross_condition = 0
    
    total_personas = len(personas)
    evaluated_personas = 0
    emergency_expected = 0
    emergency_detected = 0
    exact_matches = 0
    under_triage = 0
    over_triage = 0
    incomplete_interviews = 0
    
    # Standard clinical severity ordering including urgent
    LEVEL_ORDER = {"routine": 1, "review": 2, "urgent": 3, "emergency": 4}
    
    for p in personas:
        p_id = p["id"]
        conditions = p.get("conditions", ["diabetes"])
        on_insulin = p.get("on_insulin", False)
        lang = p.get("language", "en")
        expected_level = (p.get("expected_triage_level") or p.get("expected_level") or "routine").lower()
        
        uid = f"eval_{engine_name}_{p_id}_{int(time.time()*1000)%1000000}_{os.urandom(2).hex()}"
        headers = bootstrap_patient(uid, conditions, on_insulin=on_insulin, lang=lang)
        
        start_resp = client.post("/api/checkins/start", headers=headers)
        if start_resp.status_code != 200:
            incomplete_interviews += 1
            continue
            
        body = start_resp.json()
        c_id = body.get("checkin_id")
        
        filled_slots = set()
        known_glucose = None
        known_bp = None
        
        turns = 0
        completed = False
        final_level = "routine"
        is_emergency = False
        is_excluded = False
        
        current_q = body.get("question") or body.get("current_question", "")
        current_step = body.get("step", "")
        
        facts = build_persona_facts(p)
        
        while current_q and turns < 25:
            turns += 1
            step_id = (current_step or "").strip().lower()
            
            # Check repeats: a slot ALREADY FILLED is asked again
            # Clarifications or re-prompts on an unfilled slot are not repeats.
            if step_id and step_id in filled_slots and not any(k in step_id for k in ["summary", "confirm", "closing", "triage:"]):
                total_repeats += 1
            
            # Formulate the response
            if any(k in step_id for k in ["summary", "confirm"]):
                ans = "ہاں" if lang == "ur" else ("haan" if lang == "roman_ur" else "yes")
            else:
                ans, was_default = pick_answer(facts, current_step, current_q, lang)
            
            ans_resp = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": str(ans)})
            
            # Handle clinical exclusion (e.g. pregnancy 403)
            if ans_resp.status_code == 403 and "pregnant" in ans_resp.text:
                is_excluded = True
                completed = True
                break
                
            if ans_resp.status_code != 200:
                break
                
            ans_body = ans_resp.json()
            
            # Extract readings if in response or state
            readings = ans_body.get("readings") or {}
            if "glucose" in readings and known_glucose is None:
                try:
                    known_glucose = float(readings["glucose"])
                except Exception:
                    pass
            if "bp" in readings and known_bp is None:
                try:
                    parts = str(readings["bp"]).split("/")
                    known_bp = (float(parts[0]), float(parts[1]))
                except Exception:
                    pass
            
            # Check for completed or emergency
            if ans_body.get("emergency") or ans_body.get("stage1_red_flag") or (ans_body.get("triage") or {}).get("level") == "emergency":
                completed = True
                is_emergency = True
                final_level = "emergency"
                break
                
            if ans_body.get("complete") or ans_body.get("completed"):
                completed = True
                triage_info = ans_body.get("triage") or {}
                final_level = ans_body.get("triage_level") or triage_info.get("level") or "routine"
                break
                
            next_step = ans_body.get("step", "")
            next_q = ans_body.get("question") or ans_body.get("current_question", "")
            
            # Slot advancement: if the engine advanced to a different step, mark previous step as filled
            if step_id and next_step != current_step:
                filled_slots.add(step_id)
                
            # Check clinical contradictions
            if known_glucose is not None and known_glucose < 70:
                if any(w in (next_step or "").lower() for w in ["hyper", "hyperglycemia"]):
                    total_contradictions += 1
            if known_glucose is not None and known_glucose >= 250:
                if "hypo" in (next_step or "").lower():
                    total_contradictions += 1
            if known_bp is not None and (known_bp[0] < 90 or known_bp[1] < 60):
                if any(w in (next_step or "").lower() for w in ["bp_elevated", "otc_meds_bp"]):
                    total_contradictions += 1
            
            # Check cross-condition questions
            if conditions == ["diabetes"] and any(w in (next_step or "").lower() for w in ["bp_", "hypertension"]):
                total_cross_condition += 1
            if conditions == ["hypertension"] and any(w in (next_step or "").lower() for w in ["glucose", "diabetes", "hypo", "hyper"]):
                total_cross_condition += 1
                
            current_step = next_step
            current_q = next_q
            
        if not completed and not is_excluded:
            comp_resp = client.post(f"/api/checkins/{c_id}/complete", headers=headers)
            if comp_resp.status_code == 200:
                completed = True
                c_body = comp_resp.json()
                triage_info = c_body.get("triage") or {}
                final_level = c_body.get("triage_level") or triage_info.get("level") or "routine"
                if c_body.get("emergency"):
                    final_level = "emergency"
            else:
                incomplete_interviews += 1
                
        total_turns += turns
        
        # Clinical exclusions (e.g. pregnancy) are not evaluated for standard triage accuracy
        if is_excluded or p_id == "p17_pregnancy_exclusion":
            continue
            
        evaluated_personas += 1
        if expected_level == "emergency":
            emergency_expected += 1
            
        if final_level == "emergency":
            emergency_detected += 1
            
        exp_score = LEVEL_ORDER.get(expected_level, 1)
        act_score = LEVEL_ORDER.get(final_level, 1)
        
        if exp_score == act_score:
            exact_matches += 1
        elif act_score < exp_score:
            under_triage += 1
        else:
            over_triage += 1

    recall = (emergency_detected / emergency_expected * 100) if emergency_expected else 100.0
    
    return {
        "engine": engine_name,
        "total_personas": total_personas,
        "evaluated_personas": evaluated_personas,
        "total_turns": total_turns,
        "avg_turns": round(total_turns / total_personas, 2),
        "repeated_questions": total_repeats,
        "reading_contradictions": total_contradictions,
        "cross_condition_questions": total_cross_condition,
        "emergency_recall": f"{emergency_detected}/{emergency_expected} ({recall:.1f}%)",
        "under_triage": f"{under_triage}/{evaluated_personas}",
        "over_triage": f"{over_triage}/{evaluated_personas}",
        "exact_matches": f"{exact_matches}/{evaluated_personas}",
        "incomplete_interviews": incomplete_interviews,
    }

if __name__ == "__main__":
    persona_path = REPO_ROOT / "tests" / "sim" / "personas.json"
    with open(persona_path, "r", encoding="utf-8") as f:
        personas = json.load(f)
        
    print(f"Running evaluation of {len(personas)} personas on v2 and v3...")
    res_v2 = evaluate_engine("v2", personas)
    res_v3 = evaluate_engine("v3", personas)
    
    print("\n" + "="*80)
    print("COMPARISON: INTERVIEW ENGINE v2 vs v3 (52 PERSONAS)")
    print("="*80)
    print(f"{'Metric':<35} | {'Engine v2':<18} | {'Engine v3':<18}")
    print("-" * 80)
    for k in [
        "evaluated_personas",
        "total_turns",
        "avg_turns",
        "repeated_questions",
        "reading_contradictions",
        "cross_condition_questions",
        "emergency_recall",
        "under_triage",
        "over_triage",
        "exact_matches",
        "incomplete_interviews",
    ]:
        print(f"{k:<35} | {str(res_v2[k]):<18} | {str(res_v3[k]):<18}")
    print("="*80)
