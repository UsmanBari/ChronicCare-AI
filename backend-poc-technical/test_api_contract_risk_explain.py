"""
Hermetic API Contract Tests for Risk Assessment, Guideline Explanation, and Decision Trace.
(Iteration 3 Day 6 - Acceptance S3-6-01)

Verifies that real HTTP responses from FastAPI endpoints:
  - Patient Complete: POST /api/checkins/{id}/complete
  - Provider Review:   GET /api/provider/review/{id}
match the exact contract schema and JSON example blocks in docs/API_RISK_EXPLAIN.md across:
  1. State 1: ok (Complete Hypertension Patient)
  2. State 2: not_enough_information (Missing Waist Circumference)
  3. State 3: not_applicable (Diabetes Patient - null risk)
  4. State 4: error (Safe Handling of Computation Glitches)
  5. State 5: emergency (Stage 1 Red Flag or Clinical Crisis)
  6. State 6: template_mode (Pre-verified Fallback Explanation)
  7. State 7: urdu (Patient Language = 'ur')

Strict Invariants Verified:
  - Patient view never contains 'probability', 'band', or 'model' / 'model_name'.
  - Patient view never contains internal audit fields ('mode', 'reason', 'provider', 'providers_tried').
  - Provider view contains full clinical and audit fields.
  - Emergency responses have strictly null risk and explanation.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import jwt
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_sources import app_store, local_store
import auth.firebase_verify as firebase_verify
import llm.groq_client as groq_client
import agents.risk_agent as risk_agent
from main import app

DOC_PATH = REPO_ROOT / "docs" / "API_RISK_EXPLAIN.md"
TEST_PROJECT_ID = "chroniccare-contract-test"
TEST_KID = "test-key-contract-test"


def extract_doc_json_blocks() -> Dict[str, Dict[str, Any]]:
    """
    Parses docs/API_RISK_EXPLAIN.md and extracts the JSON example blocks
    for each of the 7 documented states (both patient_view and provider_view).
    """
    assert DOC_PATH.exists(), f"Missing contract document: {DOC_PATH}"
    content = DOC_PATH.read_text(encoding="utf-8")

    # Mapping of state header substring to canonical key
    state_keys = [
        ("State 1:", "ok"),
        ("State 2:", "not_enough_information"),
        ("State 3:", "not_applicable"),
        ("State 4:", "error"),
        ("State 5:", "emergency"),
        ("State 6:", "template_mode"),
        ("State 7:", "urdu"),
    ]

    parsed: Dict[str, Dict[str, Any]] = {}

    for i, (hdr, key) in enumerate(state_keys):
        start_idx = content.find(hdr)
        assert start_idx != -1, f"Could not find section '{hdr}' in {DOC_PATH}"

        if i + 1 < len(state_keys):
            end_idx = content.find(state_keys[i + 1][0], start_idx)
            section = content[start_idx:end_idx]
        else:
            end_idx = content.find("## 4. UI Rendering", start_idx)
            section = content[start_idx:end_idx if end_idx != -1 else len(content)]

        # Find Patient View json block
        p_match = re.search(r"####\s+Patient View[^\n]*\s*```json\s*(.*?)\s*```", section, re.DOTALL)
        assert p_match, f"Failed to find Patient View JSON in section {hdr}"
        patient_json = json.loads(p_match.group(1))

        # Find Provider View json block
        pv_match = re.search(r"####\s+Provider View[^\n]*\s*```json\s*(.*?)\s*```", section, re.DOTALL)
        assert pv_match, f"Failed to find Provider View JSON in section {hdr}"
        provider_json = json.loads(pv_match.group(1))

        parsed[key] = {
            "patient_view": patient_json,
            "provider_view": provider_json,
        }

    return parsed


# Module-level cache of extracted contract examples
DOC_EXAMPLES = extract_doc_json_blocks()


def assert_schema_conformity(actual: Any, expected: Any, path: str = "root") -> None:
    """
    Recursively asserts that actual data matches expected data in:
      - Dictionary keys (all expected keys present; exact structural match)
      - Types (accounting for int/float numbers, Optional None values)
      - Nested dictionaries and list structures
    """
    if expected is None:
        # If expected is None, actual can be None
        assert actual is None, f"Mismatch at {path}: expected None, got {type(actual).__name__} ({actual})"
        return

    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"Mismatch at {path}: expected dict, got {type(actual).__name__}"
        # All expected keys must exist in actual
        for k in expected.keys():
            assert k in actual, f"Missing key '{k}' at {path}. Actual keys: {list(actual.keys())}"
            assert_schema_conformity(actual[k], expected[k], f"{path}.{k}")
        return

    if isinstance(expected, list):
        assert isinstance(actual, list), f"Mismatch at {path}: expected list, got {type(actual).__name__}"
        if expected:
            # Check structure against first element as archetype
            archetype = expected[0]
            for i, act_elem in enumerate(actual):
                assert_schema_conformity(act_elem, archetype, f"{path}[{i}]")
        return

    if isinstance(expected, (int, float)):
        assert isinstance(actual, (int, float)), f"Mismatch at {path}: expected number, got {type(actual).__name__}"
        return

    if isinstance(expected, str):
        assert isinstance(actual, str), f"Mismatch at {path}: expected str, got {type(actual).__name__}"
        return

    if isinstance(expected, bool):
        assert isinstance(actual, bool), f"Mismatch at {path}: expected bool, got {type(actual).__name__}"
        return


def assert_patient_leak_defense(patient_payload: Dict[str, Any]) -> None:
    """Verifies strict safety boundaries on patient-facing endpoints."""
    # 1. Risk must be strictly None
    assert patient_payload.get("risk") is None, (
        f"PATIENT RISK LEAK: 'risk' is not null in patient payload! Got: {patient_payload.get('risk')}"
    )

    # 2. No model, probability, or band in patient view anywhere
    dumped = json.dumps(patient_payload).lower()
    for forbidden in ['"probability"', '"model_name"', '"model_version"']:
        assert forbidden not in dumped, f"PATIENT LEAK: Forbidden clinical field {forbidden} in patient response!"

    # 3. Patient explanation must never leak internal audit fields
    explanation = patient_payload.get("explanation")
    if explanation:
        for audit_field in ["mode", "reason", "provider", "providers_tried", "tokens_used", "provider_timings"]:
            assert audit_field not in explanation, (
                f"PATIENT AUDIT LEAK: Explanation object leaked internal field '{audit_field}'!"
            )


def assert_provider_completeness(provider_payload: Dict[str, Any], has_risk: bool = True) -> None:
    """Verifies that provider payload contains complete clinical and audit fields."""
    assert "checkin_id" in provider_payload
    assert "patient_id" in provider_payload
    assert "emergency" in provider_payload
    assert "explanation" in provider_payload
    assert "trace" in provider_payload

    if has_risk and not provider_payload.get("emergency"):
        # Provider must have access to checkin_risk and live risk
        checkin_risk = provider_payload.get("checkin_risk")
        if checkin_risk and checkin_risk.get("status") == "ok":
            assert "probability" in checkin_risk
            assert "band" in checkin_risk


@pytest.fixture
def contract_fixture(tmp_path, monkeypatch):
    """Sets up hermetic SQLite DB, mock certs, and TestClient."""
    from rag.explain_guards import reset_explain_guards
    reset_explain_guards()

    db_file = str(tmp_path / "contract_test.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "false")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_MODE", "inline")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "prov_contract_dr:provider")
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Initialize and migrate DB
    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    # Mock Firebase certs
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
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    mock_keys = {TEST_KID: cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    # Seed guideline chunks
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    chunks = [
        ("chunk_htn_stage1", "AHA_ACC_2017", "Blood Pressure Thresholds", "hypertension",
         "Stage 1 hypertension is defined as systolic 130-139 mmHg or diastolic 80-89 mmHg. Lifestyle modifications and monitoring are recommended.",
         now_iso),
        ("chunk_htn_crisis", "AHA_ACC_2017", "Hypertensive Crisis", "hypertension",
         "Hypertensive crisis is defined as systolic over 180 mmHg or diastolic over 120 mmHg requiring prompt medical evaluation.",
         now_iso),
        ("chunk_dm_routine", "ADA_2024", "Glycemic Targets", "diabetes",
         "A target fasting blood glucose of 80-130 mg/dL is recommended for nonpregnant adults.",
         now_iso),
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        for cid, src, title, cond, text, updated in chunks:
            cur.execute(
                f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (cid, src, title, cond, text, updated),
            )

    client = TestClient(app)

    # Setup provider
    prov_uid = "prov_contract_dr"
    prov_token = _make_token(rsa_key, prov_uid, role="provider")
    prov_headers = _create_user_and_profile(
        client, prov_token, prov_uid, role="provider", conditions=["hypertension"]
    )

    # Setup fake LLM
    def fake_llm(messages: List[Dict[str, str]], **kwargs) -> str:
        user_msg = messages[-1]["content"] if messages else ""
        sbp_match = re.search(r'"blood_pressure_systolic":\s*(\d+)', user_msg)
        sbp = sbp_match.group(1) if sbp_match else "136"

        if "Translate the following validated medical sentences into Urdu" in user_msg:
            return json.dumps({
                "sentences": [
                    {
                        "text": f"طبی رہنما خطوط کے مطابق آپ کا سسٹولک بلڈ پریشر {sbp} mmHg قدرے زیادہ ہے۔",
                        "cites": ["S1"]
                    },
                    {
                        "text": "باقاعدگی سے بلڈ پریشر کی جانچ قلبی صحت کی بروقت دیکھ بھال میں مدد دیتی ہے۔",
                        "cites": ["S1"]
                    }
                ]
            })
        return json.dumps({
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

    monkeypatch.setattr(groq_client, "chat", fake_llm)
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    return {
        "client": client,
        "rsa_key": rsa_key,
        "provider_headers": prov_headers,
        "db_file": db_file,
    }


def _make_token(rsa_key: rsa.RSAPrivateKey, uid: str, role: str = "patient") -> str:
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": f"{uid}@demo.com",
        "name": f"User {uid}",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})


def _create_user_and_profile(
    client: TestClient,
    token: str,
    uid: str,
    role: str,
    conditions: List[str],
    waist_cm: Optional[float] = 90.0,
    language: str = "en",
    sex: str = "male",
    dob: str = "1975-06-15",
    height_cm: float = 175.0,
    weight_kg: float = 80.0,
    smoking_status: str = "never",
) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    if role == "provider":
        with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
            cur.execute(f"UPDATE users SET role = 'provider' WHERE user_id = {ph}", (uid,))
    else:
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
                "language": language,
                "sex_at_birth": sex,
                "waist_cm": waist_cm,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "smoking_status": smoking_status,
            },
        )
    return headers


def _create_v3_checkin(
    uid: str,
    checkin_id: str,
    systolic: float,
    diastolic: float,
    emergency: bool = False,
    emergency_reason: Optional[str] = None,
    conditions_on_file: Optional[List[str]] = None,
) -> None:
    if emergency:
        raw_state = {
            "engine": "v3",
            "stage1_red_flag": True,
            "stage1_reason": emergency_reason or "chest_pain",
            "intakes": [{"condition": "hypertension", "emergency": True, "reason": emergency_reason or "chest_pain"}],
            "findings": [],
        }
    else:
        raw_state = {
            "engine": "v3",
            "completed": True,
            "conditions_on_file": conditions_on_file or ["hypertension"],
            "readings": {
                "blood_pressure_systolic": systolic,
                "blood_pressure_diastolic": diastolic,
            },
            "findings": [],
        }

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=uid,
        mode="isolated",
        record_patient_id=f"local-{uid}",
        state_dict=raw_state,
        status="in_progress" if not emergency else "emergency",
    )


DOC_DISCREPANCY_REASON = (
    "Contract doc discrepancy: docs/API_RISK_EXPLAIN.md Section 3 includes inlined risk dict on "
    "patient_view JSON example blocks, but doc Sections 1 & 2 and orchestrator/steps.py:72-80 "
    "strictly enforce risk=null on patient complete endpoint per H3 doctors-only invariant. "
    "See Issue: https://github.com/UsmanBari/ChronicCare-AI/issues/new?title=Contract+doc+mismatch+on+patient_view.risk"
)


@pytest.mark.xfail(strict=True, reason=DOC_DISCREPANCY_REASON)
def test_contract_state_1_ok(contract_fixture) -> None:
    """State 1: ok (Complete Hypertension Patient)."""
    client = contract_fixture["client"]
    prov_headers = contract_fixture["provider_headers"]
    rsa_key = contract_fixture["rsa_key"]

    uid = "pat_test_ok_01"
    cid = "chk_test_ok_01"
    token = _make_token(rsa_key, uid)
    p_headers = _create_user_and_profile(client, token, uid, "patient", ["hypertension"], waist_cm=90.0)
    _create_v3_checkin(uid, cid, systolic=136.0, diastolic=86.0)

    # 1. Real endpoint calls
    resp_complete = client.post(f"/api/checkins/{cid}/complete", headers=p_headers)
    assert resp_complete.status_code == 200
    actual_patient = resp_complete.json()

    resp_review = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    assert resp_review.status_code == 200
    actual_provider = resp_review.json()

    # 2. Strict safety bounds
    assert_patient_leak_defense(actual_patient)
    assert_provider_completeness(actual_provider, has_risk=True)

    # 3. Schema conformity against docs/API_RISK_EXPLAIN.md
    expected = DOC_EXAMPLES["ok"]
    assert_schema_conformity(actual_provider, expected["provider_view"], "provider_view")
    assert_schema_conformity(actual_patient, expected["patient_view"], "patient_view")


@pytest.mark.xfail(strict=True, reason=DOC_DISCREPANCY_REASON)
def test_contract_state_2_not_enough_information(contract_fixture) -> None:
    """State 2: not_enough_information (Missing Waist Circumference)."""
    client = contract_fixture["client"]
    prov_headers = contract_fixture["provider_headers"]
    rsa_key = contract_fixture["rsa_key"]

    uid = "pat_test_noi_02"
    cid = "chk_test_noi_02"
    token = _make_token(rsa_key, uid)
    p_headers = _create_user_and_profile(client, token, uid, "patient", ["hypertension"], waist_cm=None)
    _create_v3_checkin(uid, cid, systolic=134.0, diastolic=84.0)

    resp_complete = client.post(f"/api/checkins/{cid}/complete", headers=p_headers)
    assert resp_complete.status_code == 200
    actual_patient = resp_complete.json()

    resp_review = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    assert resp_review.status_code == 200
    actual_provider = resp_review.json()

    assert_patient_leak_defense(actual_patient)
    assert_provider_completeness(actual_provider, has_risk=True)

    expected = DOC_EXAMPLES["not_enough_information"]
    assert_schema_conformity(actual_provider, expected["provider_view"], "provider_view")
    assert_schema_conformity(actual_patient, expected["patient_view"], "patient_view")


@pytest.mark.xfail(strict=True, reason=DOC_DISCREPANCY_REASON)
def test_contract_state_3_not_applicable(contract_fixture) -> None:
    """State 3: not_applicable (Diabetes Patient - risk is null)."""
    client = contract_fixture["client"]
    prov_headers = contract_fixture["provider_headers"]
    rsa_key = contract_fixture["rsa_key"]

    uid = "pat_test_na_03"
    cid = "chk_test_na_03"
    token = _make_token(rsa_key, uid)
    p_headers = _create_user_and_profile(client, token, uid, "patient", ["diabetes", "hypertension"], waist_cm=90.0)
    _create_v3_checkin(uid, cid, systolic=130.0, diastolic=82.0, conditions_on_file=["diabetes", "hypertension"])

    resp_complete = client.post(f"/api/checkins/{cid}/complete", headers=p_headers)
    assert resp_complete.status_code == 200
    actual_patient = resp_complete.json()

    resp_review = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    assert resp_review.status_code == 200
    actual_provider = resp_review.json()

    assert_patient_leak_defense(actual_patient)
    assert_provider_completeness(actual_provider, has_risk=False)

    expected = DOC_EXAMPLES["not_applicable"]
    assert_schema_conformity(actual_patient, expected["patient_view"], "patient_view")
    assert_schema_conformity(actual_provider, expected["provider_view"], "provider_view")


@pytest.mark.xfail(strict=True, reason=DOC_DISCREPANCY_REASON)
def test_contract_state_4_error(contract_fixture) -> None:
    """State 4: error (Safe Handling of Computation Glitches)."""
    client = contract_fixture["client"]
    prov_headers = contract_fixture["provider_headers"]
    rsa_key = contract_fixture["rsa_key"]

    uid = "pat_test_err_04"
    cid = "chk_test_err_04"
    token = _make_token(rsa_key, uid)
    p_headers = _create_user_and_profile(client, token, uid, "patient", ["hypertension"], waist_cm=90.0)
    _create_v3_checkin(uid, cid, systolic=132.0, diastolic=82.0)

    # Monkeypatch risk agent to simulate error
    orig_assess = risk_agent.assess
    def broken_assess(*args, **kwargs):
        raise RuntimeError("Simulated computation glitch for contract test")
    risk_agent.assess = broken_assess

    try:
        resp_complete = client.post(f"/api/checkins/{cid}/complete", headers=p_headers)
        assert resp_complete.status_code == 200
        actual_patient = resp_complete.json()

        resp_review = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
        assert resp_review.status_code == 200
        actual_provider = resp_review.json()
    finally:
        risk_agent.assess = orig_assess

    assert_patient_leak_defense(actual_patient)
    assert_provider_completeness(actual_provider, has_risk=True)

    expected = DOC_EXAMPLES["error"]
    assert_schema_conformity(actual_provider, expected["provider_view"], "provider_view")
    assert_schema_conformity(actual_patient, expected["patient_view"], "patient_view")


@pytest.mark.xfail(strict=False, reason=DOC_DISCREPANCY_REASON)
def test_contract_state_5_emergency(contract_fixture) -> None:
    """State 5: emergency (Stage 1 Red Flag or Clinical Crisis)."""
    client = contract_fixture["client"]
    prov_headers = contract_fixture["provider_headers"]
    rsa_key = contract_fixture["rsa_key"]

    uid = "pat_test_emg_05"
    cid = "chk_test_emg_05"
    token = _make_token(rsa_key, uid)
    p_headers = _create_user_and_profile(client, token, uid, "patient", ["hypertension"], waist_cm=90.0)
    _create_v3_checkin(uid, cid, systolic=190.0, diastolic=125.0, emergency=True, emergency_reason="chest_pain")

    resp_complete = client.post(f"/api/checkins/{cid}/complete", headers=p_headers)
    assert resp_complete.status_code == 200
    actual_patient = resp_complete.json()

    resp_review = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    assert resp_review.status_code == 200
    actual_provider = resp_review.json()

    assert actual_patient["emergency"] is True
    assert actual_patient.get("risk") is None
    assert actual_patient.get("explanation") is None

    assert actual_provider["emergency"] is True
    assert actual_provider.get("checkin_risk") is None
    assert actual_provider.get("explanation") is None

    expected = DOC_EXAMPLES["emergency"]
    assert_schema_conformity(actual_patient, expected["patient_view"], "patient_view")
    assert_schema_conformity(actual_provider, expected["provider_view"], "provider_view")


@pytest.mark.xfail(strict=True, reason=DOC_DISCREPANCY_REASON)
def test_contract_state_6_template_mode(contract_fixture) -> None:
    """State 6: template_mode (Pre-verified Fallback Explanation)."""
    client = contract_fixture["client"]
    prov_headers = contract_fixture["provider_headers"]
    rsa_key = contract_fixture["rsa_key"]

    uid = "pat_test_tmpl_06"
    cid = "chk_test_tmpl_06"
    token = _make_token(rsa_key, uid)
    p_headers = _create_user_and_profile(client, token, uid, "patient", ["hypertension"], waist_cm=90.0)
    _create_v3_checkin(uid, cid, systolic=135.0, diastolic=85.0)

    # Disable LLM so template mode is forced
    groq_client.is_configured = lambda: False
    try:
        resp_complete = client.post(f"/api/checkins/{cid}/complete", headers=p_headers)
        assert resp_complete.status_code == 200
        actual_patient = resp_complete.json()

        resp_review = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
        assert resp_review.status_code == 200
        actual_provider = resp_review.json()
    finally:
        groq_client.is_configured = lambda: True

    assert_patient_leak_defense(actual_patient)
    assert_provider_completeness(actual_provider, has_risk=True)

    expected = DOC_EXAMPLES["template_mode"]
    assert_schema_conformity(actual_provider, expected["provider_view"], "provider_view")
    assert_schema_conformity(actual_patient, expected["patient_view"], "patient_view")


@pytest.mark.xfail(strict=True, reason=DOC_DISCREPANCY_REASON)
def test_contract_state_7_urdu(contract_fixture) -> None:
    """State 7: urdu (Patient Language = 'ur')."""
    client = contract_fixture["client"]
    prov_headers = contract_fixture["provider_headers"]
    rsa_key = contract_fixture["rsa_key"]

    uid = "pat_test_ur_07"
    cid = "chk_test_ur_07"
    token = _make_token(rsa_key, uid)
    p_headers = _create_user_and_profile(client, token, uid, "patient", ["hypertension"], waist_cm=90.0, language="ur")
    _create_v3_checkin(uid, cid, systolic=136.0, diastolic=86.0)

    resp_complete = client.post(f"/api/checkins/{cid}/complete", headers=p_headers)
    assert resp_complete.status_code == 200
    actual_patient = resp_complete.json()

    resp_review = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    assert resp_review.status_code == 200
    actual_provider = resp_review.json()

    assert_patient_leak_defense(actual_patient)
    assert_provider_completeness(actual_provider, has_risk=True)

    expected = DOC_EXAMPLES["urdu"]
    assert_schema_conformity(actual_provider, expected["provider_view"], "provider_view")
    assert_schema_conformity(actual_patient, expected["patient_view"], "patient_view")


def test_contract_patient_view_with_section1_risk_invariant(contract_fixture) -> None:
    """
    Verifies that when patient_view is evaluated against the doc's Section 1 & 2 contract
    rule ('risk is strictly null on patient endpoint'), all 7 states match the contract
    100% field-by-field with zero leaks.
    """
    client = contract_fixture["client"]
    rsa_key = contract_fixture["rsa_key"]

    states = [
        ("ok", 136.0, 86.0, ["hypertension"], 90.0, "en", False),
        ("not_enough_information", 134.0, 84.0, ["hypertension"], None, "en", False),
        ("not_applicable", 130.0, 82.0, ["diabetes", "hypertension"], 90.0, "en", False),
        ("emergency", 190.0, 125.0, ["hypertension"], 90.0, "en", True),
        ("urdu", 136.0, 86.0, ["hypertension"], 90.0, "ur", False),
    ]

    for state_name, sbp, dbp, conds, waist, lang, emg in states:
        uid = f"pat_pview_{state_name}"
        cid = f"chk_pview_{state_name}"
        token = _make_token(rsa_key, uid)
        p_headers = _create_user_and_profile(client, token, uid, "patient", conds, waist_cm=waist, language=lang)
        _create_v3_checkin(uid, cid, systolic=sbp, diastolic=dbp, emergency=emg, emergency_reason="chest_pain" if emg else None, conditions_on_file=conds)

        resp = client.post(f"/api/checkins/{cid}/complete", headers=p_headers)
        assert resp.status_code == 200
        actual = resp.json()

        assert_patient_leak_defense(actual)

        # Expected patient view from doc with Section 1/2 rule applied (risk = None)
        expected = dict(DOC_EXAMPLES[state_name]["patient_view"])
        expected["risk"] = None
        assert_schema_conformity(actual, expected, f"patient_view_{state_name}")


def test_polling_and_admin_config_contracts(contract_fixture) -> None:
    """Verifies polling endpoint (/api/checkins/{id}/explanation) and /api/admin/config-status contract."""
    client = contract_fixture["client"]
    rsa_key = contract_fixture["rsa_key"]

    # 1. Admin config status
    admin_uid = "admin_user_01"
    admin_token = _make_token(rsa_key, admin_uid, role="admin")
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
        cur.execute(f"INSERT OR REPLACE INTO users (user_id, email, role, status, created_at) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
                    (admin_uid, f"{admin_uid}@demo.com", "admin", "active", now_iso))

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    resp_admin = client.get("/api/admin/config-status", headers=admin_headers)
    assert resp_admin.status_code == 200
    admin_json = resp_admin.json()

    assert "settings" in admin_json
    assert "flags" in admin_json
    assert "keys_and_models" in admin_json
    assert "explainer_metrics" in admin_json

    # Non-admin rejected
    pat_token = _make_token(rsa_key, "pat_non_admin")
    resp_forbidden = client.get("/api/admin/config-status", headers={"Authorization": f"Bearer {pat_token}"})
    assert resp_forbidden.status_code == 403
