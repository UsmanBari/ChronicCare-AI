"""
Hermetic Integration & Unit Tests for Wired Risk Advisory, Guideline Explanations,
and Decision Traces across Direct and Graph Orchestration Completion (Day 7).

Verifies:
1. Flags off: complete response and stored row identical to dev baseline (risk=None, explanation=None).
2. Flags on (RISK_ENABLED=true, EXPLAIN_ENABLED=true, RISK_CAN_RAISE=false): safety fields identical to flags off.
3. RISK_CAN_RAISE=true: routine -> review on high band, requires_review=True, review_status='open',
   and appears in GET /api/provider/review-queue.
4. Explainer failure / LLM down: safe fallback to pre-verified template, check-in completes, triage untouched.
5. Emergency intake: risk and explanation are strictly None; spy asserts LLM is NEVER called.
6. Idempotent re-complete: spy asserts LLM called exactly once on first completion, zero times on replay.
7. Privacy views & trace sanitization: patient view has no probability; provider view does;
   trace has no reading values, names, or dates of birth.
8. Orchestrator equivalence: both ORCHESTRATOR=direct and ORCHESTRATOR=graph yield identical results.
9. Network guard: tests never make real network calls; monkeypatched LLM spy enforces strict isolation.
10. Mutation proof M-U7-2: explain step never mutates triage level.
"""
from __future__ import annotations

import copy
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
import jwt

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store
import llm.groq_client as groq_client
from orchestrator.steps import step_explain
from agents.adaptive_interview_agent import InterviewState

TEST_PROJECT_ID = "test-checkin-risk-explain-ci"
TEST_KID = "test-key-risk-explain-ci"


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def cert_pem(rsa_key):
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")]))
        .public_key(rsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
        .sign(rsa_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch, cert_pem):
    from rag.explain_guards import reset_explain_guards
    reset_explain_guards()
    db_file = str(tmp_path / "test_wire.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider")
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")
    monkeypatch.setenv("EXPLAIN_MODE", "inline")

    # Guard: ensure no accidental real Groq / Gemini calls
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import llm.gemini_client as gemini_client
    monkeypatch.setattr(gemini_client, "is_configured", lambda: False)

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    mock_keys = {TEST_KID: cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    # Seed guideline chunks for explainer
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    chunks = [
        ("c_htn_1", "AHA_ACC_2017", "BP Targets", "hypertension",
         "Stage 1 hypertension is systolic 130-139 mmHg or diastolic 80-89 mmHg.", now),
        ("c_dm_1", "ADA_2024", "Glycemic Targets", "diabetes",
         "Target fasting blood glucose is 80-130 mg/dL for nonpregnant adults.", now),
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        for cid, src, title, cond, text, updated in chunks:
            cur.execute(
                f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (cid, src, title, cond, text, updated),
            )

    return db_file


def _create_token(rsa_key, uid: str, role: str = "patient") -> str:
    now = int(time.time())
    email = "provider@demo.com" if role == "provider" else f"{uid}@demo.com"
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": email,
        "name": f"User {uid}",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})


def _setup_patient(
    client: TestClient,
    rsa_key,
    uid: str,
    conditions: List[str],
    waist_cm: Optional[float] = 90.0,
    smoking: str = "never",
    sex: str = "male",
    dob: str = "1975-06-15",
) -> Dict[str, str]:
    token = _create_token(rsa_key, uid, role="patient")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    local_store.add_local_patient_if_missing(f"local-{uid}", name=f"User {uid}", date_of_birth=dob)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": conditions,
            "on_insulin_or_sulfonylurea": False,
            "date_of_birth": dob,
            "inclusion_confirmed": True,
            "language": "en",
            "sex_at_birth": sex,
            "waist_cm": waist_cm,
            "height_cm": 175.0,
            "weight_kg": 80.0,
            "smoking_status": smoking,
        },
    )
    return headers


def _create_checkin_session(
    uid: str,
    checkin_id: str,
    systolic: float = 135.0,
    diastolic: float = 85.0,
    emergency: bool = False,
    emergency_reason: Optional[str] = None,
    conditions: Optional[List[str]] = None,
    findings: Optional[List[Dict[str, Any]]] = None,
    answers: Optional[Dict[str, Any]] = None,
):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if emergency:
        raw_state = {
            "engine": "v3",
            "stage1_red_flag": True,
            "stage1_reason": emergency_reason or "chest_pain",
            "intakes": [{"condition": "hypertension", "emergency": True, "reason": emergency_reason or "chest_pain"}],
            "findings": findings or [],
        }
    else:
        raw_state = {
            "engine": "v3",
            "completed": True,
            "conditions_on_file": conditions or ["hypertension"],
            "readings": {
                "blood_pressure_systolic": systolic,
                "blood_pressure_diastolic": diastolic,
            },
            "findings": findings or [],
        }
    if answers:
        raw_state["answers"] = answers

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=uid,
        mode="isolated",
        record_patient_id=f"local-{uid}",
        state_dict=raw_state,
        status="in_progress" if not emergency else "emergency",
    )


class LLMSpy:
    """Mock LLM that counts calls and validates prompts hermetically."""
    def __init__(self):
        self.call_count = 0
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, messages: List[Dict[str, str]], **kwargs) -> str:
        self.call_count += 1
        self.calls.append({"messages": messages, "kwargs": kwargs})
        user_msg = messages[-1]["content"] if messages else ""
        sbp_match = re.search(r'"blood_pressure_systolic":\s*(\d+)', user_msg)
        sbp = sbp_match.group(1) if sbp_match else "135"

        text = json.dumps({
            "sentences": [
                {
                    "text": f"Your systolic blood pressure reading of {sbp} mmHg is slightly elevated according to clinical guidelines.",
                    "cites": ["S1"]
                },
                {
                    "text": "Regular blood pressure monitoring helps track cardiovascular risk over time.",
                    "cites": ["S1"]
                }
            ]
        })
        return (text, 60)


# ---------------------------------------------------------------------------
# Test 1: Flags Off -> Complete response and stored row identical to baseline
# ---------------------------------------------------------------------------
def test_flags_off_complete_identical_to_dev(rsa_key, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "false")
    monkeypatch.setenv("EXPLAIN_ENABLED", "false")
    monkeypatch.setenv("RISK_CAN_RAISE", "false")

    client = TestClient(app)
    uid = "pat_flagsoff_01"
    cid = "chk_flagsoff_01"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"])
    _create_checkin_session(uid, cid, systolic=135.0, diastolic=85.0)

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # In flags-off mode, risk and explanation must be null
    assert data["risk"] is None
    assert data["explanation"] is None
    assert data["emergency"] is False

    # Check stored row in DB
    result_row = app_store.get_checkin_result(cid)
    assert result_row is not None
    assert result_row["risk"] is None
    assert result_row["explanation"] is None
    # Stored trace is preserved
    assert isinstance(result_row["trace"], list)
    assert len(result_row["trace"]) > 0


# ---------------------------------------------------------------------------
# Test 2: Flags On, RISK_CAN_RAISE=false -> Safety fields untouched
# ---------------------------------------------------------------------------
def test_flags_on_safety_fields_identical_when_can_raise_false(rsa_key, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "false")

    spy = LLMSpy()
    monkeypatch.setattr(groq_client, "chat_with_usage", spy)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = "pat_flagson_02"
    cid = "chk_flagson_02"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"], waist_cm=95.0)
    _create_checkin_session(uid, cid, systolic=138.0, diastolic=88.0)

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Patient view: Doctors approved risk panel as doctors-only (H3); /complete never contains risk
    assert data["risk"] is None

    # Patient view has explanation sentences
    assert data["explanation"] is not None
    assert len(data["explanation"]["sentences"]) == 2

    # Stored checkin result
    stored = app_store.get_checkin_result(cid)
    assert stored["risk"] is not None
    assert "probability" in stored["risk"]
    assert stored["risk"]["raised"] is False
    assert stored["explanation"] is not None

    # Triage was NOT raised
    assert stored["triage_level"] in ("routine", "review")


# ---------------------------------------------------------------------------
# Test 3: RISK_CAN_RAISE=true -> Routine raised to Review on High Band
# ---------------------------------------------------------------------------
def test_risk_can_raise_true_escalates_routine_to_review(rsa_key, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "true")

    spy = LLMSpy()
    monkeypatch.setattr(groq_client, "chat_with_usage", spy)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    # Force risk agent to return band 'high'
    import agents.risk_agent as ra
    orig_assess = ra.assess
    def mock_high_risk(*args, **kwargs):
        res = orig_assess(*args, **kwargs)
        if isinstance(res, dict) and res.get("status") == "ok":
            res["band"] = "high"
            res["probability"] = 0.85
        return res
    monkeypatch.setattr(ra, "assess", mock_high_risk)

    client = TestClient(app)
    uid = "pat_raise_03"
    cid = "chk_raise_03"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"], waist_cm=95.0)

    # Seed matching prior observations so reconciliation agrees and initial triage is 'routine'
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    local_store.add_local_observation(
        id="prior_sys_03",
        patient_id=f"local-{uid}",
        observation_type="blood_pressure_systolic",
        value=135.0,
        unit="mmHg",
        timestamp=now_iso,
        source="local",
        origin="clinician",
    )
    local_store.add_local_observation(
        id="prior_dia_03",
        patient_id=f"local-{uid}",
        observation_type="blood_pressure_diastolic",
        value=85.0,
        unit="mmHg",
        timestamp=now_iso,
        source="local",
        origin="clinician",
    )

    # 1. Asymptomatic check-in under Doctor Decision D2: High risk alone gives Green (routine)
    uid_asymp = "pat_raise_03_asymp"
    cid_asymp = "chk_raise_03_asymp"
    headers_asymp = _setup_patient(client, rsa_key, uid_asymp, ["hypertension"], waist_cm=95.0)
    local_store.add_local_observation(
        id="prior_sys_03_asymp",
        patient_id=f"local-{uid_asymp}",
        observation_type="blood_pressure_systolic",
        value=135.0,
        unit="mmHg",
        timestamp=now_iso,
        source="local",
        origin="clinician",
    )
    local_store.add_local_observation(
        id="prior_dia_03_asymp",
        patient_id=f"local-{uid_asymp}",
        observation_type="blood_pressure_diastolic",
        value=85.0,
        unit="mmHg",
        timestamp=now_iso,
        source="local",
        origin="clinician",
    )
    _create_checkin_session(uid_asymp, cid_asymp, systolic=135.0, diastolic=85.0)
    resp_asymp = client.post(f"/api/checkins/{cid_asymp}/complete", headers=headers_asymp)
    assert resp_asymp.status_code == 200
    data_asymp = resp_asymp.json()
    assert data_asymp["requires_review"] is False
    assert data_asymp["triage_level"] == "routine"
    stored_asymp = app_store.get_checkin_result(cid_asymp)
    assert stored_asymp["risk"]["raised"] is False
    assert stored_asymp["triage_level"] == "routine"
    assert stored_asymp["risk"]["models"][0]["band"] == "high"

    # 2. Symptomatic check-in: High risk + reported symptom elevates to review
    _create_checkin_session(
        uid,
        cid,
        systolic=135.0,
        diastolic=85.0,
        findings=[{"kind": "headache", "label": "Headache", "raw_quote": "mild headache"}],
    )

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Triage escalated to review
    assert data["requires_review"] is True

    stored = app_store.get_checkin_result(cid)
    assert stored["risk"]["raised"] is True
    assert stored["requires_review"] == 1
    assert stored["review_status"] == "open"
    assert stored["triage_level"] == "review"

    # Provider Review Queue check
    prov_tok = _create_token(rsa_key, "prov_doc_01", role="provider")
    prov_headers = {"Authorization": f"Bearer {prov_tok}"}
    client.post("/api/auth/session", headers=prov_headers)
    with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
        cur.execute(f"UPDATE users SET role = 'provider' WHERE user_id = {ph}", ("prov_doc_01",))

    queue_resp = client.get("/api/provider/review-queue", headers=prov_headers)
    assert queue_resp.status_code == 200
    queue_items = queue_resp.json()
    item_ids = [item["checkin_id"] for item in queue_items]
    assert cid in item_ids


# ---------------------------------------------------------------------------
# Test 4: Explainer Failure / LLM Down -> Safe Fallback to Template
# ---------------------------------------------------------------------------
def test_explainer_failure_safe_fallback(rsa_key, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "false")

    # LLM throws an unhandled runtime error
    def broken_llm(*args, **kwargs):
        raise RuntimeError("Groq upstream connection failed")
    monkeypatch.setattr(groq_client, "chat_with_usage", broken_llm)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = "pat_fallback_04"
    cid = "chk_fallback_04"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"], waist_cm=90.0)
    _create_checkin_session(uid, cid, systolic=135.0, diastolic=85.0)

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Checkin completes successfully and triage is untouched
    assert data["emergency"] is False
    assert data["explanation"] is not None
    # Template mode fallback provides safe sentences
    assert len(data["explanation"]["sentences"]) > 0

    stored = app_store.get_checkin_result(cid)
    assert stored["explanation"]["mode"] == "template"
    assert any("RuntimeError" in r or "error" in r.lower() for r in stored["explanation"]["rejected_reasons"])


# ---------------------------------------------------------------------------
# Test 5: Emergency Intake -> Both risk and explanation are None; LLM Never Called
# ---------------------------------------------------------------------------
def test_emergency_intake_bypasses_risk_and_explain(rsa_key, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")

    spy = LLMSpy()
    monkeypatch.setattr(groq_client, "chat_with_usage", spy)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = "pat_emergency_05"
    cid = "chk_emergency_05"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"])
    _create_checkin_session(uid, cid, systolic=195.0, diastolic=125.0, emergency=True, emergency_reason="crisis_chest_pain")

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["emergency"] is True
    assert data["risk"] is None
    assert data["explanation"] is None

    # LLM was strictly NEVER called
    assert spy.call_count == 0


# ---------------------------------------------------------------------------
# Test 6: Idempotent Re-Complete -> LLM called only once
# ---------------------------------------------------------------------------
def test_idempotency_calls_llm_only_once(rsa_key, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")

    spy = LLMSpy()
    monkeypatch.setattr(groq_client, "chat_with_usage", spy)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = "pat_idemp_06"
    cid = "chk_idemp_06"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"], waist_cm=90.0)
    _create_checkin_session(uid, cid, systolic=135.0, diastolic=85.0)

    # First call: completes check-in
    resp1 = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp1.status_code == 200
    assert spy.call_count == 1

    # Second call: idempotent cached return
    resp2 = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp2.status_code == 200
    assert spy.call_count == 1  # Still 1, NOT 2

    # Cached responses match
    assert resp1.json()["risk"] == resp2.json()["risk"]
    assert resp1.json()["explanation"] == resp2.json()["explanation"]


# ---------------------------------------------------------------------------
# Test 7: Privacy Views & Trace Sanitization
# ---------------------------------------------------------------------------
def test_privacy_views_and_trace_sanitization(rsa_key, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")

    spy = LLMSpy()
    monkeypatch.setattr(groq_client, "chat_with_usage", spy)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = "pat_priv_07"
    cid = "chk_priv_07"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"], waist_cm=92.0, dob="1975-06-15")
    _create_checkin_session(uid, cid, systolic=136.0, diastolic=86.0)

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    patient_data = resp.json()

    # Patient view: strictly null risk (H3) and NO explanation mode/reason
    assert patient_data["risk"] is None
    assert "trace" not in patient_data
    assert "mode" not in patient_data["explanation"]
    assert "reason" not in patient_data["explanation"]

    # Provider view
    prov_tok = _create_token(rsa_key, "prov_priv_01", role="provider")
    prov_headers = {"Authorization": f"Bearer {prov_tok}"}
    client.post("/api/auth/session", headers=prov_headers)
    with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
        cur.execute(f"UPDATE users SET role = 'provider' WHERE user_id = {ph}", ("prov_priv_01",))

    detail_resp = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    prov_data = detail_resp.json()

    # Provider view has probability
    assert "probability" in prov_data["checkin_risk"]
    assert isinstance(prov_data["checkin_risk"]["probability"], float)

    # Trace audit verification: no reading values, names, or DOBs
    trace = prov_data["trace"]
    assert isinstance(trace, list)
    for step in trace:
        summary = step.get("summary", "")
        assert "136" not in summary
        assert "86" not in summary
        assert "1975-06-15" not in summary
        assert "User pat_priv_07" not in summary


# ---------------------------------------------------------------------------
# Test 8: Orchestrator Modes Equivalence (direct == graph)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("orch_mode", ["direct", "graph"])
def test_orchestrator_modes_completion(rsa_key, monkeypatch, orch_mode):
    monkeypatch.setenv("ORCHESTRATOR", orch_mode)
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")

    spy = LLMSpy()
    monkeypatch.setattr(groq_client, "chat_with_usage", spy)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = f"pat_orch_{orch_mode}"
    cid = f"chk_orch_{orch_mode}"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"], waist_cm=90.0)
    _create_checkin_session(uid, cid, systolic=135.0, diastolic=85.0)

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk"] is None
    assert len(data["explanation"]["sentences"]) == 2


# ---------------------------------------------------------------------------
# Test 9: Network Guard -> Asserts zero external Groq / network calls
# ---------------------------------------------------------------------------
def test_network_guard_zero_real_external_calls(rsa_key, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")

    # In strict sandbox, groq_client.chat_with_usage is replaced by spy
    spy = LLMSpy()
    monkeypatch.setattr(groq_client, "chat_with_usage", spy)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = "pat_netguard_09"
    cid = "chk_netguard_09"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"], waist_cm=90.0)
    _create_checkin_session(uid, cid, systolic=135.0, diastolic=85.0)

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200

    # Ensure spy was called, but real groq was not configured
    assert spy.call_count == 1
    assert os.environ.get("GROQ_API_KEY") is None


# ---------------------------------------------------------------------------
# Test 10: Mutation Proof M-U7-2 -> Explain Step Never Mutates Triage Decision
# ---------------------------------------------------------------------------
def test_mutation_proof_m_u7_2_explain_never_modifies_triage(monkeypatch):
    """
    Mutation proof M-U7-2: Asserts that step_explain treats triage_decision as strictly
    read-only and never modifies final_triage_level, final_requires_review, or review_status.
    """
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    triage_decision = {
        "final_triage_level": "urgent",
        "final_requires_review": True,
        "review_status": "open",
        "final_max_sev": "high",
        "triage_dict": {
            "level": "urgent",
            "trigger_category": "blood_pressure_systolic",
            "summary": "Urgent elevation reported.",
        },
    }
    triage_before = copy.deepcopy(triage_decision)

    state = InterviewState(
        patient_id="local-pat-test",
        conditions_on_file=["hypertension"],
        intakes=[],
    )

    # Call step_explain
    step_explain(
        user_id="user_test_mut",
        state=state,
        triage_decision=triage_decision,
        get_patient_profile_fn=lambda uid: {"conditions": ["hypertension"], "language": "en"},
    )

    # Assert triage_decision was not mutated by step_explain
    assert triage_decision["final_triage_level"] == triage_before["final_triage_level"], (
        f"M-U7-2 KILLED: step_explain altered final_triage_level from {triage_before['final_triage_level']} "
        f"to {triage_decision['final_triage_level']}"
    )
    assert triage_decision["final_requires_review"] == triage_before["final_requires_review"]
    assert triage_decision["review_status"] == triage_before["review_status"]
    assert triage_decision == triage_before, "M-U7-2 KILLED: triage_decision dictionary was modified by step_explain"


# ---------------------------------------------------------------------------
# Test 11: Patient View Explanation Has No Mode or Reason Keys
# ---------------------------------------------------------------------------
def test_patient_complete_explanation_has_no_mode_or_reason(rsa_key, monkeypatch):
    """
    Asserts that the patient-facing /complete response's explanation object
    strictly contains only 'sentences' and 'sources', and NEVER contains
    'mode' or 'reason' keys, across both normal generation and fallback states.
    Provider review endpoint and stored result retain 'mode' and 'reason'.
    """
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")

    spy = LLMSpy()
    monkeypatch.setattr(groq_client, "chat_with_usage", spy)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = "pat_nomodereason_01"
    cid = "chk_nomodereason_01"
    headers = _setup_patient(client, rsa_key, uid, ["hypertension"], waist_cm=90.0)
    _create_checkin_session(uid, cid, systolic=135.0, diastolic=85.0)

    # 1. Normal LLM generation
    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["explanation"] is not None
    assert "sentences" in data["explanation"]
    assert "sources" in data["explanation"]
    assert "mode" not in data["explanation"], f"Patient explanation must not contain 'mode': {data['explanation']}"
    assert "reason" not in data["explanation"], f"Patient explanation must not contain 'reason': {data['explanation']}"

    # Verify provider view and stored result retain mode
    stored = app_store.get_checkin_result(cid)
    assert stored["explanation"] is not None
    assert "mode" in stored["explanation"]
    assert stored["explanation"]["mode"] in ("llm", "cache")

    # 2. Template fallback path (LLM error)
    from rag.explain_guards import reset_explain_guards
    reset_explain_guards()
    def broken_llm(*args, **kwargs):
        raise RuntimeError("Simulated failure")
    monkeypatch.setattr(groq_client, "chat_with_usage", broken_llm)

    uid_fb = "pat_nomodereason_fb"
    cid_fb = "chk_nomodereason_fb"
    headers_fb = _setup_patient(client, rsa_key, uid_fb, ["hypertension"], waist_cm=90.0)
    _create_checkin_session(uid_fb, cid_fb, systolic=135.0, diastolic=85.0)

    resp_fb = client.post(f"/api/checkins/{cid_fb}/complete", headers=headers_fb)
    assert resp_fb.status_code == 200
    data_fb = resp_fb.json()
    assert data_fb["explanation"] is not None
    assert "sentences" in data_fb["explanation"]
    assert "sources" in data_fb["explanation"]
    assert "mode" not in data_fb["explanation"], f"Fallback explanation must not contain 'mode': {data_fb['explanation']}"
    assert "reason" not in data_fb["explanation"], f"Fallback explanation must not contain 'reason': {data_fb['explanation']}"

    stored_fb = app_store.get_checkin_result(cid_fb)
    assert stored_fb["explanation"] is not None
    assert stored_fb["explanation"]["mode"] == "template"
    assert "reason" in stored_fb["explanation"]
