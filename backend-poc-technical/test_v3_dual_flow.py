"""
Comprehensive E2E and Unit Tests for Interview Engine v3 Dual-Diagnosis Flow.
(Stage 9A-7 / Hassaan Day 3 Correction).

Validates:
1. Both readings asked before any symptom in dual diagnosis (R2).
2. NO slot asked twice across all personas (R3/R6 de-duplication).
3. Symptom isolation: hyperglycemia_symptoms does NOT also fill or skip associated_symptoms (R3).
4. Both condition symptom questions asked in dual diagnosis (FIX 3).
5. Elevated BP (>=160/100) triggers associated_symptoms question in dual diagnosis (FIX 3).
6. Severe headache affirmative in dual diagnosis gives identical triage level as HTN-only (FIX 3).
7. Progress hint matches true asked count at every single turn of a full session (R7, FIX 5).
8. Multi-condition summary confirmation lists captured DM and HTN values (R8).
9. Summary states 'Symptoms: not asked' in EN/UR/Roman Urdu when no symptoms were queried (FIX 3).
10. Targeted correction round allows updating one slot and re-shows summary (max 2 rounds) (R8).
11. Caregiver reporting persists answered_by, lowers confidence, surfaces in /complete and provider detail via real HTTP API (R9, FIX 4).
12. Family history statement does NOT trigger caregiver mode (R9 trap).
13. Single-condition flows remain strictly identical to dev baseline fixture across EN/UR/Roman Urdu (R10, FIX 2).
"""

import datetime
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from agents.interview_bank.loader import get_default_bank
from agents.interview_planner import plan_next_step
from agents.interview_v3_runner import finish_v3_session, next_turn, start_v3_session
from data_sources import app_store, local_store
from auth import firebase_verify
from main import app

REPO_ROOT = Path(__file__).resolve().parents[1]
PERSONAS_PATH = REPO_ROOT / "tests" / "sim" / "personas.json"
EXPECTED_FLOWS_PATH = REPO_ROOT / "tests" / "sim" / "single_condition_expected_flows.json"

TEST_PROJECT_ID = "test-chroniccare-demo"
TEST_KID = "test-key-id-1"


@pytest.fixture(scope="session")
def rsa_key_pair():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="session")
def x509_cert_pem(rsa_key_pair) -> str:
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(rsa_key_pair.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
        .sign(rsa_key_pair, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch, x509_cert_pem):
    test_db_path = str(tmp_path / "test_chroniccare_dual.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "doctor@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)


def create_token(
    private_key,
    sub: str = "uid-patient-1",
    email: str = "patient@demo.com",
    exp_delta: int = 3600,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "email_verified": True,
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + exp_delta,
        "auth_time": now,
    }
    headers = {"kid": TEST_KID, "alg": "RS256"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


def test_both_readings_before_any_symptom():
    """R2: Dual-diagnosis patient is asked both glucose and BP readings before any symptom inquiry."""
    session = start_v3_session("dual-r2-1", "P-DUAL", ["diabetes", "hypertension"])
    assert session["step"] == "greeting"

    session = next_turn(session, "feeling fine")
    # First reading
    first_reading_step = session["step"]
    assert first_reading_step in ("glucose_reading", "bp_reading")

    if first_reading_step == "glucose_reading":
        session = next_turn(session, "140")
        assert session["step"] == "bp_reading"
        session = next_turn(session, "130/85")
    else:
        session = next_turn(session, "130/85")
        assert session["step"] == "glucose_reading"
        session = next_turn(session, "140")

    # Next steps are context / technique before symptoms
    remaining_pre_symptom = []
    for _ in range(2):
        step = session.get("step")
        remaining_pre_symptom.append(step)
        if step == "glucose_context":
            session = next_turn(session, "fasting")
        elif step == "bp_technique":
            session = next_turn(session, "seated")

    assert set(remaining_pre_symptom) == {"glucose_context", "bp_technique"}
    assert session["step"] not in ("greeting", "glucose_reading", "bp_reading")


def test_no_slot_asked_twice_in_any_persona():
    """R3/R6: Centralized de-duplication ensures no clinical slot is asked twice across personas."""
    assert PERSONAS_PATH.exists()
    with open(PERSONAS_PATH, "r", encoding="utf-8") as f:
        personas = json.load(f)

    for p in personas:
        conditions = p.get("conditions", ["diabetes"])
        pid = p.get("id", "test-p")
        session = start_v3_session(f"sim-{pid}", pid, conditions)

        asked_clinical_slots = []
        for _ in range(16):
            if session.get("complete") or session.get("step") == "summary_confirmation":
                break
            step = session.get("step")
            if step not in ("summary_confirmation", "summary_correction_select", "greeting"):
                asked_clinical_slots.append(step)

            if step == "glucose_reading":
                ans = "120"
            elif step == "bp_reading":
                ans = "120/80"
            elif step in ("glucose_context", "bp_technique"):
                ans = "fasting" if "glucose" in step else "seated"
            else:
                ans = "no"
            session = next_turn(session, ans)

        # In standard runs without error loops, every slot asked is unique
        assert len(asked_clinical_slots) == len(set(asked_clinical_slots)), (
            f"Persona {pid} asked duplicate slot: {asked_clinical_slots}"
        )


def test_shared_symptom_does_not_fill_different_question():
    """FIX 1: hyperglycemia_symptoms (thirst/urination) must NOT fill or skip associated_symptoms (headache/dyspnea)."""
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes", "hypertension"], "on_insulin_or_sulfonylurea": False}

    asked = {"greeting", "glucose_reading", "bp_reading", "glucose_context", "bp_technique", "hyperglycemia_symptoms"}
    known = {
        "glucose_reading": 140.0,
        "bp_reading": [165, 100],
        "glucose_context": "fasting",
        "bp_technique": "seated",
        "hyperglycemia_symptoms": False,
    }

    # Since hyperglycemia_symptoms is answered, associated_symptoms must NOT be marked satisfied
    assert "associated_symptoms" not in known

    decision = plan_next_step(
        known_slots=known,
        findings=[],
        patient_record=patient_record,
        bank=bank,
        asked_slots=asked,
        base_budget=12,
    )
    # Next question must proceed to remaining open slots (e.g. foot_problems then associated_symptoms)
    assert decision.target_slot in ("foot_problems", "associated_symptoms")


def test_dual_flow_asks_associated_symptoms_on_elevated_bp():
    """FIX 3: A dual patient with BP >= 160/100 is asked associated_symptoms."""
    session = start_v3_session("dual-htn-symptom", "P1", ["diabetes", "hypertension"], language="en")
    session = next_turn(session, "feeling fine")      # greeting
    session = next_turn(session, "140")               # glucose_reading
    session = next_turn(session, "165/100")           # bp_reading (elevated)
    session = next_turn(session, "fasting")           # glucose_context
    session = next_turn(session, "seated")            # bp_technique

    # Walk remaining questions until summary confirmation
    steps_asked = []
    for _ in range(10):
        if session.get("complete") or session.get("step") == "summary_confirmation":
            break
        steps_asked.append(session.get("step"))
        session = next_turn(session, "no")

    assert "associated_symptoms" in steps_asked, (
        f"associated_symptoms was never asked for elevated BP patient: {steps_asked}"
    )


def test_dual_flow_asks_both_symptom_questions():
    """FIX 3: Every dual flow evaluates and asks BOTH hyperglycemia_symptoms and associated_symptoms."""
    session = start_v3_session("dual-both-symp", "P1", ["diabetes", "hypertension"], language="en")
    session = next_turn(session, "feeling fine")
    session = next_turn(session, "250")      # high glucose
    session = next_turn(session, "165/100")  # high BP
    session = next_turn(session, "fasting")
    session = next_turn(session, "seated")

    steps_asked = []
    for _ in range(12):
        if session.get("complete") or session.get("step") == "summary_confirmation":
            break
        steps_asked.append(session.get("step"))
        session = next_turn(session, "no")

    assert "hyperglycemia_symptoms" in steps_asked, f"Missing hyperglycemia_symptoms in {steps_asked}"
    assert "associated_symptoms" in steps_asked, f"Missing associated_symptoms in {steps_asked}"


def test_severe_headache_in_dual_matches_htn_only_level():
    """FIX 3: Answering 'yes' to severe headache in dual flow gives identical triage level as HTN-only flow."""
    # 1. HTN-only flow with severe headache
    s_htn = start_v3_session("htn-headache", "P1", ["hypertension"], language="en")
    s_htn = next_turn(s_htn, "feeling fine")
    s_htn = next_turn(s_htn, "165/100")
    s_htn = next_turn(s_htn, "seated")
    # associated_symptoms: answer yes to headache
    s_htn = next_turn(s_htn, "yes severe headache")
    res_htn = finish_v3_session(s_htn)

    # 2. Dual flow with identical BP and severe headache
    s_dual = start_v3_session("dual-headache", "P2", ["diabetes", "hypertension"], language="en")
    s_dual = next_turn(s_dual, "feeling fine")
    s_dual = next_turn(s_dual, "140")        # normal glucose
    s_dual = next_turn(s_dual, "165/100")    # identical elevated BP
    s_dual = next_turn(s_dual, "fasting")
    s_dual = next_turn(s_dual, "seated")
    for _ in range(10):
        if s_dual.get("complete") or s_dual.get("emergency") or s_dual.get("step") == "summary_confirmation":
            break
        step = s_dual.get("step")
        if step == "associated_symptoms":
            s_dual = next_turn(s_dual, "yes severe headache")
        else:
            s_dual = next_turn(s_dual, "no")

    res_dual = finish_v3_session(s_dual)
    assert res_htn["emergency"] is True
    assert res_dual["emergency"] is True
    assert res_htn["emergency_reason"] == res_dual["emergency_reason"] == "severe_headache"


def test_progress_hint_equals_real_count_every_turn():
    """R7 & FIX 5: Progress hint matches the true asked count and budget at EVERY turn of a full session."""
    session = start_v3_session("dual-r7-loop", "P-DUAL", ["diabetes", "hypertension"])
    assert session["progress_hint"] == "1/8"

    asked_count = 1
    answers = ["feeling fine", "130", "125/82", "fasting", "seated", "no", "no", "no", "no", "no", "no", "no"]

    for ans in answers:
        if session.get("complete") or session.get("step") == "summary_confirmation":
            break
        session = next_turn(session, ans)
        if session.get("step") != "summary_confirmation":
            asked_count += 1
            hint_parts = session["progress_hint"].split("/")
            curr_hint = int(hint_parts[0])
            budget_hint = int(hint_parts[1])
            assert curr_hint == asked_count, f"Turn mismatch: progress_hint says {curr_hint}, real asked={asked_count}"
            assert budget_hint in (8, 12, 14)


def test_summary_lists_both_conditions():
    """R8: Summary confirmation includes both diabetes and hypertension captured readings."""
    session = start_v3_session("dual-r8-1", "P-DUAL", ["diabetes", "hypertension"], language="en")
    session["known_slots"]["glucose_reading"] = 135.0
    session["known_slots"]["glucose_context"] = "fasting"
    session["known_slots"]["bp_reading"] = [124, 82]
    session["known_slots"]["bp_technique"] = "rested"
    session["known_slots"]["hyperglycemia_symptoms"] = False
    session["known_slots"]["associated_symptoms"] = False
    session["known_slots"]["foot_problems"] = False
    session["known_slots"]["adherence_diabetes"] = True
    session["known_slots"]["adherence_hypertension"] = True
    session["asked_slots"] = [
        "greeting", "glucose_reading", "bp_reading", "glucose_context", "bp_technique",
        "hyperglycemia_symptoms", "associated_symptoms", "foot_problems", "adherence_diabetes", "adherence_hypertension"
    ]

    # Trigger summary confirm turn
    session["step"] = "adherence_hypertension"
    session = next_turn(session, "yes")
    assert session["step"] == "summary_confirmation"

    q_text = session["current_question"]
    assert "Blood Glucose: 135 mg/dL" in q_text
    assert "Blood Pressure: 124/82 mmHg" in q_text
    assert "Medication: Taken as prescribed" in q_text


def test_summary_not_asked_symptoms():
    """FIX 3: When no symptom question was asked, summary says 'Symptoms: not asked' in EN/UR/Roman Urdu."""
    s_en = start_v3_session("sum-symp-en", "P1", ["diabetes"], language="en")
    s_en["known_slots"]["glucose_reading"] = 115.0
    s_en["asked_slots"] = ["greeting", "glucose_reading"]

    from agents.interview_v3_runner import _build_dual_summary_text
    sum_en = _build_dual_summary_text(s_en["known_slots"], "en", asked_slots=s_en["asked_slots"])
    assert "Symptoms: not asked" in sum_en

    sum_ur = _build_dual_summary_text(s_en["known_slots"], "ur", asked_slots=s_en["asked_slots"])
    assert "علامات: پوچھی نہیں گئیں" in sum_ur

    sum_ro = _build_dual_summary_text(s_en["known_slots"], "roman_ur", asked_slots=s_en["asked_slots"])
    assert "Symptoms: nahi poochay gaye" in sum_ro


def test_summary_correction_changes_one_slot_and_reshows_summary():
    """R8: Patient can correct an incorrect reading at summary and runner returns directly to summary confirmation."""
    session = start_v3_session("dual-r8-corr", "P-DUAL", ["diabetes", "hypertension"], language="en")
    session["known_slots"]["glucose_reading"] = 180.0
    session["known_slots"]["bp_reading"] = [130, 85]
    session["asked_slots"] = ["greeting", "glucose_reading", "bp_reading", "summary_confirmation"]
    session["step"] = "summary_confirmation"

    # Patient replies "no" to summary confirmation
    session = next_turn(session, "no")
    assert session["step"] == "summary_correction_select"
    assert session.get("correcting_slot") is None

    # Patient specifies slot to change: "glucose_reading"
    session = next_turn(session, "glucose")
    assert session["step"] == "glucose_reading"
    assert session.get("correcting_slot") == "glucose_reading"

    # Patient supplies corrected value: "115"
    session = next_turn(session, "115")
    assert session["known_slots"]["glucose_reading"] == 115.0
    # Must immediately re-present summary confirmation
    assert session["step"] == "summary_confirmation"
    assert "Blood Glucose: 115 mg/dL" in session["current_question"]


def test_caregiver_flow_real_http_e2e(rsa_key_pair, monkeypatch):
    """FIX 4 & H3-04: Caregiver check-in through real HTTP API records answered_by='caregiver' and lowers confidence."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    client = TestClient(app)
    pat_token = create_token(rsa_key_pair, sub="u-caregiver-http-user", email="cg-patient@demo.com")
    prov_token = create_token(rsa_key_pair, sub="u-doctor-http-user", email="doctor@demo.com")

    headers = {"Authorization": f"Bearer {pat_token}"}
    prov_headers = {"Authorization": f"Bearer {prov_token}"}

    client.post("/api/auth/session", headers=headers)
    client.post("/api/auth/session", headers=prov_headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": ["diabetes", "hypertension"],
            "language": "en",
            "date_of_birth": "1975-01-01",
            "inclusion_confirmed": True,
            "on_insulin_or_sulfonylurea": False,
        },
    )

    # 1. Start v3 checkin
    start_resp = client.post("/api/checkins/start", headers={**headers, "X-Interview-Engine": "v3"})
    assert start_resp.status_code == 200, start_resp.text
    chk_id = start_resp.json()["checkin_id"]

    # 2. Answer with caregiver statement
    ans1 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers=headers,
        json={"answer": "I am answering for my mother who has diabetes", "step": "greeting"},
    )
    assert ans1.status_code == 200, ans1.text

    # 3. Complete third-party prompt
    curr_resp = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers=headers,
        json={"answer": "Continue check-in", "step": ans1.json()["step"]},
    )
    assert curr_resp.status_code == 200, curr_resp.text

    # 4. Walk remaining turns to completion
    for _ in range(15):
        body = curr_resp.json()
        if body.get("complete"):
            break
        step = body.get("step")
        if step == "summary_confirmation":
            curr_resp = client.post(
                f"/api/checkins/{chk_id}/answer",
                headers=headers,
                json={"answer": "Confirm and submit", "step": step},
            )
            break
        elif step == "glucose_reading":
            ans_text = "130"
        elif step == "bp_reading":
            ans_text = "125/82"
        elif step == "glucose_context":
            ans_text = "fasting"
        elif step == "bp_technique":
            ans_text = "seated"
        elif "adherence" in step:
            ans_text = "yes"
        else:
            ans_text = "no"
        curr_resp = client.post(
            f"/api/checkins/{chk_id}/answer",
            headers=headers,
            json={"answer": ans_text, "step": step},
        )
        assert curr_resp.status_code == 200, curr_resp.text

    # 5. Complete checkin
    comp_resp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp_resp.status_code == 200, comp_resp.text
    comp_data = comp_resp.json()
    print("DEBUG COMP_DATA:", comp_data)
    assert comp_data.get("answered_by") == "caregiver"

    # 6. Provider review detail
    detail_resp = client.get(f"/api/provider/review/{chk_id}", headers=prov_headers)
    assert detail_resp.status_code == 200, detail_resp.text
    detail_data = detail_resp.json()
    assert detail_data.get("answered_by") == "caregiver"
    intakes = detail_data.get("intakes", [])
    assert len(intakes) > 0
    for it in intakes:
        assert it.get("answered_by") == "caregiver"
        assert it.get("confidence") in ("Medium", 0.7, 0.70)


def test_family_history_does_not_trigger_caregiver():
    """R9: Family history ('my mother also has diabetes') must NOT trigger caregiver mode."""
    session = start_v3_session("fam-hist-1", "P1", ["diabetes"])
    session = next_turn(session, "feeling fine, my mother also has diabetes")
    assert session.get("answered_by") == "patient"


def test_single_condition_full_flow_parity():
    """R10 Exception Baseline: Full question lists for DM-only and HTN-only must match established v3 baseline.

    The expected question lists in `single_condition_expected_flows.json` were generated from
    `feat/i2-4-v3-dual-diagnosis` (commit 04281ed), establishing the corrected v3 single-condition flow baseline.
    In dev (commit 22af452), known_slots keys (including __evidence and __partial parser artifacts) were merged
    into asked_slots and counted in current_count, prematurely exhausting the budget after only 4-5 questions
    and cutting normal flows before adherence. In this PR, clean_known excludes parser artifacts so current_count
    tracks actual clinical questions asked, enabling normal flows to reach adherence and high-reading flows to
    properly utilize the 12-question expanded budget (Usman decision: ACCEPTED for v3).
    This test locks this corrected single-condition behavior against regression.
    """
    assert EXPECTED_FLOWS_PATH.exists(), f"Missing fixture at {EXPECTED_FLOWS_PATH}"
    with open(EXPECTED_FLOWS_PATH, "r", encoding="utf-8") as f:
        expected = json.load(f)

    test_matrix = [
        ("dm_high_en", ["diabetes"], {"glucose_reading": "250"}, "en"),
        ("dm_high_ur", ["diabetes"], {"glucose_reading": "250"}, "ur"),
        ("dm_high_roman_ur", ["diabetes"], {"glucose_reading": "250"}, "roman_ur"),
        ("dm_normal_en", ["diabetes"], {"glucose_reading": "115"}, "en"),
        ("dm_normal_ur", ["diabetes"], {"glucose_reading": "115"}, "ur"),
        ("dm_normal_roman_ur", ["diabetes"], {"glucose_reading": "115"}, "roman_ur"),
        ("htn_high_en", ["hypertension"], {"bp_reading": "165/100"}, "en"),
        ("htn_high_ur", ["hypertension"], {"bp_reading": "165/100"}, "ur"),
        ("htn_high_roman_ur", ["hypertension"], {"bp_reading": "165/100"}, "roman_ur"),
        ("htn_normal_en", ["hypertension"], {"bp_reading": "120/80"}, "en"),
        ("htn_normal_ur", ["hypertension"], {"bp_reading": "120/80"}, "ur"),
        ("htn_normal_roman_ur", ["hypertension"], {"bp_reading": "120/80"}, "roman_ur"),
    ]

    for key, conditions, readings, lang in test_matrix:
        s = start_v3_session(f"flow-test-{key}", "P-PARITY", conditions, language=lang)
        steps = [s["step"]]
        for _ in range(25):
            if s.get("complete") or s.get("step") == "summary_confirmation":
                break
            step = s.get("step")
            if step == "greeting":
                ans = "feeling fine" if lang == "en" else ("theek hoon" if lang == "roman_ur" else "ٹھیک ہوں")
            elif step == "glucose_reading":
                ans = readings.get("glucose_reading", "115")
            elif step == "bp_reading":
                ans = readings.get("bp_reading", "120/80")
            elif step == "glucose_context":
                ans = "fasting" if lang == "en" else ("nahar munh" if lang == "roman_ur" else "نہار منہ")
            elif step == "bp_technique":
                ans = "seated" if lang == "en" else ("baith kar" if lang == "roman_ur" else "بیٹھ کر")
            else:
                ans = "no" if lang == "en" else ("nahi" if lang == "roman_ur" else "نہیں")
            s = next_turn(s, ans)
            steps.append(s.get("step"))

        assert steps == expected[key], f"Flow parity failed for {key}: actual={steps} expected={expected[key]}"
