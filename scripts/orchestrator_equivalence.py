"""
Orchestrator Equivalence Verification Suite (Day 6, Usman Bari).
Proves 100% bit-for-bit behavioral equivalence between direct in-process execution
and the compiled LangGraph StateGraph check-in completion orchestrator.

Runs:
1. Every persona from tests/sim/personas.json (run_v3_personas.py runner)
2. All 7 Engine-Equivalence scenarios (CS-1 to CS-7)
3. All 7 Defense / POC scenarios (Milestones 1-5)

Compares:
- HTTP API response JSON (field-by-field, normalizing IDs/timestamps)
- Database checkin_results persisted rows (field-by-field, normalizing IDs/timestamps)
- Clinical triage levels and review requirements
"""

import os
import sys
import time
import json
import re
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ["INTERVIEW_ENGINE"] = "v3"

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import jwt

from main import app, get_patient_bundle
from auth import firebase_verify
from data_sources import app_store, local_store
import scripts.run_v3_personas as persona_runner
from scripts.engine_equivalence import SCENARIOS as CS_SCENARIOS, answer_for_scenario
from scenarios.run_all_scenarios import (
    OFFICIAL_SCENARIOS,
    ADVERSARIAL_SCENARIOS,
)

# Setup isolated test database for equivalence runs
test_db = str(BACKEND_DIR / "test_orchestrator_equiv_run.db")
if os.path.exists(test_db):
    try:
        os.remove(test_db)
    except Exception:
        pass

os.environ["LOCAL_DB_PATH"] = test_db
os.environ["DB_BACKEND"] = "sqlite"
TEST_PROJECT_ID = "test-orchestrator-equiv"
TEST_KID = "test-key-orchestrator-equiv"
os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID

app_store.migrate(db_path=test_db, backend="sqlite")
local_store.init_db(db_path=test_db)

# Mock Firebase Auth
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


def get_token(uid: str) -> str:
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": f"{uid}@demo.com",
        "name": f"Equiv {uid}",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})


def bootstrap_patient(uid: str, conditions: list, lang: str = "en", on_insulin: bool = False) -> Dict[str, str]:
    tok = get_token(uid)
    headers = {"Authorization": f"Bearer {tok}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    prof_lang = "ur" if lang in ("ur", "roman_ur") else "en"
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": conditions,
            "on_insulin_or_sulfonylurea": on_insulin,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": prof_lang,
        },
    )
    return headers


def normalize_payload(obj: Any) -> Any:
    """
    Recursively normalizes dynamic values (IDs, timestamps, ISO dates)
    for exact field-by-field equality comparison.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("checkin_id", "created_at", "completed_at", "escalated_at", "started_at"):
                continue
            out[k] = normalize_payload(v)
        return out
    elif isinstance(obj, list):
        return [normalize_payload(x) for x in obj]
    elif isinstance(obj, str):
        s = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", "<TIMESTAMP>", obj)
        s = re.sub(r"CHECKIN-[^\s\'\"]+", "<CHECKIN_RECORD_ID>", s)
        s = re.sub(r"(dir|grp)_[a-zA-Z0-9_-]+", "<UID_PATIENT>", s)
        s = re.sub(r"local-(dir|grp)_[a-zA-Z0-9_-]+", "<LOCAL_PATIENT>", s)
        return s
    return obj


def run_persona_case(p: Dict[str, Any], orchestrator_mode: str, uid_prefix: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    os.environ["ORCHESTRATOR"] = orchestrator_mode
    p_id = p["id"]
    lang = p.get("language", "en")
    conditions = p.get("conditions", ["diabetes"])
    on_insulin = p.get("on_insulin", False)

    uid = f"{uid_prefix}_{p_id}"
    headers = bootstrap_patient(uid, conditions, lang, on_insulin)

    start_resp = client.post("/api/checkins/start", headers=headers)
    start_body = start_resp.json()
    cid = start_body["checkin_id"]
    curr_q = start_body.get("question")
    curr_step = start_body.get("step")

    facts = persona_runner.build_persona_facts(p)
    turn = 0

    while curr_q and turn < 15:
        turn += 1
        ans, _ = persona_runner.pick_answer(facts, curr_step, curr_q, lang)
        ans_resp = client.post(f"/api/checkins/{cid}/answer", headers=headers, json={"answer": ans})
        if ans_resp.status_code == 403 and "pregnant" in ans_resp.text:
            break
        if ans_resp.status_code != 200:
            break
        body = ans_resp.json()
        if body.get("emergency") or body.get("complete"):
            break
        curr_q = body.get("question")
        curr_step = body.get("step")

    comp_resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    comp_body = comp_resp.json() if comp_resp.status_code == 200 else {"error": comp_resp.text}
    db_res = app_store.get_checkin_result(cid) or {}

    return comp_body, db_res


def run_engine_equiv_case(sc: Dict[str, Any], orchestrator_mode: str, uid_prefix: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    os.environ["ORCHESTRATOR"] = orchestrator_mode
    sc_id = sc["id"]
    uid = f"{uid_prefix}_{sc_id.lower().replace('-', '_')}"
    conds = ["diabetes", "hypertension"] if sc.get("needs_both") else (["hypertension"] if "bp" in sc_id.lower() or sc_id in ("CS-5", "CS-7") else ["diabetes"])

    headers = bootstrap_patient(uid, conds, "en", on_insulin=True)
    start_resp = client.post("/api/checkins/start", headers=headers)
    start_body = start_resp.json()
    cid = start_body["checkin_id"]
    curr_q = start_body.get("question")
    curr_step = start_body.get("step")

    turn = 0
    while curr_q and turn < 12:
        turn += 1
        ans = answer_for_scenario(sc, curr_q, curr_step)
        ans_resp = client.post(f"/api/checkins/{cid}/answer", headers=headers, json={"answer": ans})
        if ans_resp.status_code != 200:
            break
        body = ans_resp.json()
        if body.get("emergency") or body.get("complete"):
            break
        curr_q = body.get("question")
        curr_step = body.get("step")

    comp_resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    comp_body = comp_resp.json() if comp_resp.status_code == 200 else {"error": comp_resp.text}
    db_res = app_store.get_checkin_result(cid) or {}

    return comp_body, db_res


def run_poc_scenario_case(sc_def: Dict[str, Any], orchestrator_mode: str, uid_prefix: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    os.environ["ORCHESTRATOR"] = orchestrator_mode
    sc_id = sc_def["id"]
    uid = f"{uid_prefix}_{sc_id}"
    headers = bootstrap_patient(uid, ["diabetes", "hypertension"], "en", on_insulin=True)

    # Monkeypatch get_patient_bundle for this specific run
    prior_bundle = sc_def["bundle_a"]
    checkin_bundle_b = sc_def["bundle_b"]

    orig_fn = app_store.get_checkin_by_id

    # Create checkin session with bundle_b observation intakes
    intakes = []
    obs_readings = []
    for obs in checkin_bundle_b.get("observations", []):
        obs_readings.append({
            "observation_type": obs.observation_type,
            "value": obs.value,
            "unit": obs.unit,
            "source": "patient_checkin",
        })
    intakes.append({
        "condition": "general",
        "readings": obs_readings,
        "symptoms": [],
        "notes": [],
        "confidence": "High",
        "answered_by": "patient",
    })

    start_resp = client.post("/api/checkins/start", headers=headers)
    cid = start_resp.json()["checkin_id"]

    # Update session to completed interview with intakes from bundle_b
    state_dict = {
        "engine": "v3",
        "completed": True,
        "intakes": intakes,
        "conditions_on_file": ["diabetes", "hypertension"],
        "findings": [],
    }
    app_store.update_checkin_state(cid, state_dict=state_dict, status="in_progress")

    # Mock baseline bundle fetch on main
    import main
    orig_mock = getattr(main, "get_patient_bundle")
    setattr(main, "get_patient_bundle", lambda pid, mode=None, base_url=None: prior_bundle)

    try:
        comp_resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
        comp_body = comp_resp.json() if comp_resp.status_code == 200 else {"error": comp_resp.text}
        db_res = app_store.get_checkin_result(cid) or {}
    finally:
        setattr(main, "get_patient_bundle", orig_mock)

    return comp_body, db_res


def extract_level(resp: Dict[str, Any], db_res: Dict[str, Any]) -> str:
    if resp.get("emergency"):
        return "emergency"
    triage = resp.get("triage")
    if triage and triage.get("level"):
        return str(triage["level"])
    if db_res.get("triage_level"):
        return str(db_res["triage_level"])
    return "routine"


def main_suite():
    print("=" * 105)
    print("ORCHESTRATOR EQUIVALENCE VERIFICATION SUITE")
    print("Deterministic Proof: Direct In-Process Execution == LangGraph StateGraph Execution")
    print("=" * 105)

    cases_results = []

    # 1. Personas from run_v3_personas.py
    personas_path = REPO_ROOT / "tests" / "sim" / "personas.json"
    with open(personas_path, "r", encoding="utf-8") as f:
        personas = json.load(f)

    print(f"\n--- PART 1: Executing {len(personas)} Simulated Personas ---")
    for p in personas:
        cid_case = p["id"]
        resp_dir, db_dir = run_persona_case(p, "direct", "dir")
        resp_grp, db_grp = run_persona_case(p, "graph", "grp")

        c_dir = normalize_payload(resp_dir)
        c_grp = normalize_payload(resp_grp)
        d_dir = normalize_payload(db_dir)
        d_grp = normalize_payload(db_grp)

        lvl_dir = extract_level(resp_dir, db_dir)
        lvl_grp = extract_level(resp_grp, db_grp)

        resp_match = (c_dir == c_grp)
        db_match = (d_dir == d_grp)
        lvl_match = (lvl_dir == lvl_grp)
        is_identical = resp_match and db_match and lvl_match

        cases_results.append({
            "id": cid_case,
            "category": "Persona",
            "direct_level": lvl_dir,
            "graph_level": lvl_grp,
            "resp_match": resp_match,
            "db_match": db_match,
            "identical": is_identical,
        })

    # 2. Engine-Equivalence Scenarios (CS-1 to CS-7)
    print(f"\n--- PART 2: Executing {len(CS_SCENARIOS)} Engine-Equivalence Scenarios (CS-1 to CS-7) ---")
    for sc in CS_SCENARIOS:
        sc_id = sc["id"]
        resp_dir, db_dir = run_engine_equiv_case(sc, "direct", "dir")
        resp_grp, db_grp = run_engine_equiv_case(sc, "graph", "grp")

        c_dir = normalize_payload(resp_dir)
        c_grp = normalize_payload(resp_grp)
        d_dir = normalize_payload(db_dir)
        d_grp = normalize_payload(db_grp)

        lvl_dir = extract_level(resp_dir, db_dir)
        lvl_grp = extract_level(resp_grp, db_grp)

        resp_match = (c_dir == c_grp)
        db_match = (d_dir == d_grp)
        lvl_match = (lvl_dir == lvl_grp)
        is_identical = resp_match and db_match and lvl_match

        cases_results.append({
            "id": sc_id,
            "category": "Engine-Equiv",
            "direct_level": lvl_dir,
            "graph_level": lvl_grp,
            "resp_match": resp_match,
            "db_match": db_match,
            "identical": is_identical,
        })

    # 3. Defense / POC Scenarios (Milestones 1-5)
    poc_scenarios = OFFICIAL_SCENARIOS + ADVERSARIAL_SCENARIOS
    print(f"\n--- PART 3: Executing {len(poc_scenarios)} Defense Scenarios (M1-M5) ---")
    for sc_def in poc_scenarios:
        sc_id = sc_def["id"]
        resp_dir, db_dir = run_poc_scenario_case(sc_def, "direct", "dir")
        resp_grp, db_grp = run_poc_scenario_case(sc_def, "graph", "grp")

        c_dir = normalize_payload(resp_dir)
        c_grp = normalize_payload(resp_grp)
        d_dir = normalize_payload(db_dir)
        d_grp = normalize_payload(db_grp)

        lvl_dir = extract_level(resp_dir, db_dir)
        lvl_grp = extract_level(resp_grp, db_grp)

        resp_match = (c_dir == c_grp)
        db_match = (d_dir == d_grp)
        lvl_match = (lvl_dir == lvl_grp)
        is_identical = resp_match and db_match and lvl_match

        cases_results.append({
            "id": sc_id,
            "category": "Defense-Scenario",
            "direct_level": lvl_dir,
            "graph_level": lvl_grp,
            "resp_match": resp_match,
            "db_match": db_match,
            "identical": is_identical,
        })

    # Output Markdown Table
    print("\n" + "=" * 105)
    print("EQUIVALENCE TABLE (Direct vs LangGraph)")
    print("=" * 105)
    print(f"| {'Case ID':<35} | {'Category':<16} | {'Direct Level':<12} | {'Graph Level':<12} | {'Identical':<9} |")
    print(f"|{'-'*37}|{'-'*18}|{'-'*14}|{'-'*14}|{'-'*11}|")

    all_identical = True
    total_count = len(cases_results)
    identical_count = 0

    for r in cases_results:
        ident_str = "YES" if r["identical"] else "NO"
        if not r["identical"]:
            all_identical = False
        else:
            identical_count += 1
        print(f"| {r['id']:<35} | {r['category']:<16} | {r['direct_level']:<12} | {r['graph_level']:<12} | {ident_str:<9} |")

    print("=" * 105)
    print(f"TOTAL CASES EVALUATED : {total_count}")
    print(f"100% IDENTICAL CASES  : {identical_count} / {total_count} ({round(identical_count/total_count*100, 1)}%)")
    print("=" * 105)

    if not all_identical:
        print("\nERROR: Equivalence check FAILED! Differences detected.")
        sys.exit(1)
    else:
        print("\nSUCCESS: All test cases are 100% equivalent across Direct and LangGraph execution!")
        sys.exit(0)


if __name__ == "__main__":
    main_suite()
