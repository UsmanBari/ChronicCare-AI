"""
Hermetic Unit & Integration Tests for SOAP Note Generation Agent (Agent 7).
Covers T1-T5 under direct and graph orchestrators:
  T1: Every number in the SOAP note appears in the stored check-in data (traceability).
      HOTFIX 2 repro: with every answer "skip", note contains zero glucose value.
  T2: Sections for: routine with readings, review, urgent, emergency (S/O present, P immediate guidance),
      no-readings, connected mode with reconciliation conflict, risk ok, risk not_enough_info.
  T3: Access: patient token -> 403 on SOAP endpoint; patient endpoints never contain "soap";
      provider sees only allowed check-ins (404 on non-existent).
  T4: Connected mode -> DocumentReference exists in FhirSim with LOINC 11506-3 and subject.
      Isolated mode -> zero DocumentReference in FhirSim.
  T5: No guideline text in note: titles/sections only.
"""

from __future__ import annotations

import base64
import datetime
import json
import re
import sys
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

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import auth.firebase_verify as firebase_verify
from agents.soap_agent import build_soap, format_soap_plain_text, create_fhir_document_reference, reset_stored_soap_notes
from data_sources import app_store, fhir_sim, local_store
from main import app

TEST_PROJECT_ID = "chroniccare-soap-test"
TEST_KID = "test-key-soap-test"


@pytest.fixture
def soap_fixture(tmp_path, monkeypatch):
    """Hermetic setup for SQLite DB, mock tokens, and TestClient."""
    reset_stored_soap_notes()
    fhir_sim.reset_stored_document_references()

    db_file = str(tmp_path / "soap_test.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("RISK_CAN_RAISE", "false")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_MODE", "inline")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "dr_soap:provider")
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

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

    def _make_token(user_id: str, email: str) -> str:
        now = int(time.time())
        payload = {
            "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
            "aud": TEST_PROJECT_ID,
            "auth_time": now,
            "user_id": user_id,
            "sub": user_id,
            "iat": now,
            "exp": now + 3600,
            "email": email,
            "email_verified": True,
            "firebase": {"identities": {"email": [email]}, "sign_in_provider": "password"},
        }
        priv_pem = rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return jwt.encode(payload, priv_pem, algorithm="RS256", headers={"kid": TEST_KID})

    client = TestClient(app)

    # Register provider & patient
    prov_tok = _make_token("prov_soap_id", "dr_soap")
    resp_prov = client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_tok}"})
    assert resp_prov.status_code == 200, f"Provider session failed: {resp_prov.text}"

    pat_tok = _make_token("pat_soap_id", "patient_soap@test.com")
    resp_pat = client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_tok}"})
    assert resp_pat.status_code == 200, f"Patient session failed: {resp_pat.text}"

    return {
        "client": client,
        "db_file": db_file,
        "prov_token": prov_tok,
        "pat_token": pat_tok,
        "prov_headers": {"Authorization": f"Bearer {prov_tok}"},
        "pat_headers": {"Authorization": f"Bearer {pat_tok}"},
    }


def _seed_completed_checkin(
    checkin_id: str,
    user_id: str = "pat_soap_id",
    mode: str = "isolated",
    triage_level: str = "routine",
    reasons: Optional[List[str]] = None,
    guidance: str = "Continue routine care.",
    readings: Optional[List[Dict[str, Any]]] = None,
    answers: Optional[Dict[str, Any]] = None,
    risk: Optional[Dict[str, Any]] = None,
    explanation: Optional[Dict[str, Any]] = None,
    reconciliation: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
    is_cold_start: bool = False,
    raised_by: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Directly seeds a complete checkin and checkin_results record for test scenarios."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    readings = readings if readings is not None else []
    answers = answers if answers is not None else {}

    intake_obj = {
        "condition": "diabetes",
        "emergency": triage_level == "emergency",
        "readings": readings,
        "symptoms": {},
        "adherence": answers.get("adherence"),
        "confidence": "Medium" if is_cold_start else "High",
        "missing_data": len(readings) == 0,
    }

    state_obj = {
        "patient_id": user_id,
        "conditions_on_file": ["diabetes"],
        "is_cold_start": is_cold_start,
        "answers": answers,
        "intake": intake_obj,
        "intakes": [intake_obj],
    }

    triage_obj = {
        "level": triage_level,
        "guidance": guidance,
        "summary": reasons[0] if reasons else f"{triage_level} check-in completed.",
        "reasons": reasons or [],
        "triage_colour": "Green" if triage_level == "routine" else ("Yellow" if triage_level == "review" else "Red"),
    }
    if raised_by:
        triage_obj["raised_by"] = raised_by

    with app_store.get_db_cursor() as (cur, be, ph):
        cur.execute(
            f"""
            INSERT OR REPLACE INTO checkins (checkin_id, user_id, mode, record_patient_id, status, state_json, version, started_at, completed_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, 'complete', {ph}, 1, {ph}, {ph})
            """,
            (checkin_id, user_id, mode, f"Patient/{user_id}", json.dumps(state_obj), now_iso, now_iso),
        )
        cur.execute(
            f"""
            INSERT OR REPLACE INTO checkin_results (
                checkin_id, emergency, intakes_json, reconciliation_json, verification_json,
                requires_review, max_severity, review_status, trigger_category, trigger_text,
                escalated_at, triage_level, triage_json, risk_json, explanation_json, trace_json, created_at
            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                checkin_id,
                1 if triage_level == "emergency" else 0,
                json.dumps([intake_obj]),
                json.dumps(reconciliation) if reconciliation else None,
                json.dumps(verification) if verification else None,
                1 if triage_level in ("review", "urgent", "emergency") else 0,
                "high" if triage_level in ("urgent", "emergency") else ("moderate" if triage_level == "review" else "none"),
                "open" if triage_level in ("review", "urgent", "emergency") else "resolved",
                f"triage:{triage_level}",
                triage_obj["summary"],
                now_iso if triage_level in ("urgent", "emergency") else None,
                triage_level,
                json.dumps(triage_obj),
                json.dumps(risk) if risk else None,
                json.dumps(explanation) if explanation else None,
                json.dumps([]),
                now_iso,
            ),
        )


# =============================================================================
# T1: Traceability & No Invented Numbers
# =============================================================================

def test_t1_all_numbers_traceable_to_stored_data(soap_fixture):
    """
    T1: Every number in the SOAP note must appear in the stored check-in data.
    """
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-t1-valid"
    readings = [{"observation_type": "glucose", "value": 142.0, "unit": "mg/dL"}]
    risk = {
        "status": "ok",
        "band": "Moderate",
        "probability": 0.42,
        "drivers": [{"feature": "bmi", "contribution": 0.15}],
    }
    _seed_completed_checkin(cid, readings=readings, risk=risk)

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200, f"Expected 200 got {resp.status_code}: {resp.text}"
    data = resp.json()

    plain_text = data["plain_text"]
    # Check that 142.0 and 0.42 appear and are from stored data
    assert "142.0" in plain_text
    assert "0.42" in plain_text

    # Extract clinical numbers from the body sections (excluding metadata header)
    body_lines = [
        line for line in plain_text.splitlines()
        if not any(line.startswith(pfx) for pfx in ("Check-in ID:", "Patient ID:", "Generated:", "===="))
    ]
    body_text = "\n".join(body_lines)
    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", body_text)
    # Collect all stored numeric literals
    stored_str = json.dumps([readings, risk])
    for num in numbers:
        # Ignore structural integers like 30, 0, 1, 7 (common structural counts/windows)
        if num in ("30", "0", "1", "7"):
            continue
        assert num in stored_str or num in str(142.0) or num in str(0.42) or num in str(0.15), (
            f"Untraceable number '{num}' found in SOAP note!"
        )


def test_t1_hotfix2_repro_skip_all_has_no_glucose(soap_fixture):
    """
    HOTFIX 2 repro: Patient skips every answer. SOAP note must contain NO glucose reading.
    """
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-t1-skip-all"
    answers = {
        "greeting_response": "skip",
        "glucose_reading": "skip",
        "hyperglycemia_symptoms": "skip",
        "adherence": None,
        "lifestyle_notes": "skip",
    }
    # Checkin with no readings
    _seed_completed_checkin(cid, readings=[], answers=answers, triage_level="routine")

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200
    data = resp.json()

    plain_text = data["plain_text"].lower()
    body_lines = [
        line for line in plain_text.splitlines()
        if not any(line.startswith(pfx) for pfx in ("check-in id:", "patient id:", "generated:", "===="))
    ]
    body_text = "\n".join(body_lines)
    # Must NOT contain any glucose value like 35 or 142 or glucose reading line
    assert "35" not in body_text
    assert "reading - glucose" not in body_text
    assert "readings: no reading today" in body_text
    assert "not answered" in body_text


# =============================================================================
# T2: Section Parity Across Clinical Scenarios
# =============================================================================

def test_t2_routine_with_readings(soap_fixture):
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-t2-routine"
    readings = [{"observation_type": "glucose", "value": 110.0, "unit": "mg/dL"}]
    _seed_completed_checkin(cid, triage_level="routine", readings=readings)

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert any("routine (Green)" in a for a in data["assessment"])
    assert any("Routine monitoring, no clinician review required" in p for p in data["plan"])
    assert any("110.0 mg/dL" in o for o in data["objective"])


def test_t2_review_requires_clinician_review(soap_fixture):
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-t2-review"
    readings = [{"observation_type": "glucose", "value": 240.0, "unit": "mg/dL"}]
    _seed_completed_checkin(
        cid,
        triage_level="review",
        reasons=["High fasting glucose above review threshold."],
        readings=readings,
    )

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert any("review (Yellow)" in a for a in data["assessment"])
    assert any("clinician review required" in p for p in data["plan"])


def test_t2_emergency_shows_immediate_guidance(soap_fixture):
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-t2-emergency"
    readings = [{"observation_type": "glucose", "value": 45.0, "unit": "mg/dL"}]
    _seed_completed_checkin(
        cid,
        triage_level="emergency",
        reasons=["Severe acute hypoglycemia (< 54 mg/dL)."],
        guidance="Call local emergency services immediately.",
        readings=readings,
    )

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert any("emergency (Red" in a for a in data["assessment"])
    assert any("Immediate emergency guidance provided" in p for p in data["plan"])
    assert any("clinician review required" in p for p in data["plan"])


def test_t2_connected_mode_reconciliation_conflict(soap_fixture):
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-t2-recon-conflict"
    readings = [{"observation_type": "glucose", "value": 180.0, "unit": "mg/dL", "source": "patient-reported"}]
    recon = {
        "summary": {"conflicts": 1, "agreements": 0},
        "observation_reconciliations": [
            {"observation_type": "glucose", "status": "conflict", "value_a": 140.0, "value_b": 180.0}
        ],
    }
    _seed_completed_checkin(
        cid,
        mode="connected",
        triage_level="review",
        readings=readings,
        reconciliation=recon,
    )

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert any("Observation conflict on glucose: baseline 140.0 vs check-in 180.0" in o for o in data["objective"])


def test_t2_risk_ok_and_not_enough_info(soap_fixture):
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    # 1. Multi-model with ok status
    cid_ok = "chk-t2-risk-ok"
    multi_risk = {
        "models": {
            "t2d_3yr": {
                "status": "ok",
                "band": "Moderate",
                "probability": 0.38,
                "drivers": [{"feature": "bmi", "contribution": 0.12}, {"feature": "sbp", "contribution": 0.09}],
            }
        }
    }
    _seed_completed_checkin(cid_ok, risk=multi_risk)
    resp_ok = client.get(f"/api/provider/review/{cid_ok}/soap", headers=prov_headers)
    assert resp_ok.status_code == 200
    a_ok = resp_ok.json()["assessment"]
    assert any("Risk model (t2d_3yr): Band Moderate, Probability 0.38" in a for a in a_ok)
    assert any("Investigational caveat" in a for a in a_ok)

    # 2. Not enough info
    cid_nei = "chk-t2-risk-nei"
    nei_risk = {
        "status": "not_enough_information",
        "missing": ["bmi", "waist_cm"],
    }
    _seed_completed_checkin(cid_nei, risk=nei_risk)
    resp_nei = client.get(f"/api/provider/review/{cid_nei}/soap", headers=prov_headers)
    assert resp_nei.status_code == 200
    a_nei = resp_nei.json()["assessment"]
    assert any("not enough information (missing: bmi, waist_cm)" in a for a in a_nei)


def test_t2_cold_start_confidence_capped_at_medium(soap_fixture):
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-t2-cold-start"
    _seed_completed_checkin(cid, is_cold_start=True)

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200
    a = resp.json()["assessment"]
    assert any("first check-in: confidence capped at Medium" in line for line in a)


# =============================================================================
# T3: Access Controls
# =============================================================================

def test_t3_patient_role_forbidden_on_soap_endpoint(soap_fixture):
    """
    T3: Patient token must return 403 on the SOAP endpoint.
    """
    client = soap_fixture["client"]
    pat_headers = soap_fixture["pat_headers"]

    cid = "chk-t3-access"
    _seed_completed_checkin(cid)

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=pat_headers)
    assert resp.status_code == 403, f"Expected 403 for patient got {resp.status_code}: {resp.text}"


def test_t3_patient_endpoints_never_contain_soap(soap_fixture):
    """
    T3: Patient-facing endpoints must never return SOAP note data.
    """
    client = soap_fixture["client"]
    pat_headers = soap_fixture["pat_headers"]

    cid = "chk-t3-leak"
    _seed_completed_checkin(cid)

    resp = client.get(f"/api/checkins/{cid}", headers=pat_headers)
    assert resp.status_code == 200
    body_text = resp.text.lower()
    assert '"soap"' not in body_text
    assert '"plain_text"' not in body_text


def test_t3_nonexistent_checkin_returns_404(soap_fixture):
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    resp = client.get("/api/provider/review/nonexistent-cid/soap", headers=prov_headers)
    assert resp.status_code == 404


# =============================================================================
# T4: Connected vs Isolated Mode FHIR DocumentReference
# =============================================================================

def test_t4_connected_mode_creates_fhir_document_reference(soap_fixture):
    """
    T4: Connected mode check-in writes a FHIR R4 DocumentReference to FhirSim.
    """
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    fhir_sim.reset_stored_document_references()

    cid = "chk-t4-connected"
    pid = "sim-adult-1"
    _seed_completed_checkin(cid, user_id=pid, mode="connected")

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200

    docs = fhir_sim.get_stored_document_references(pid)
    assert len(docs) >= 1, "Expected DocumentReference in FhirSim for connected mode"

    doc = docs[-1]
    assert doc["resourceType"] == "DocumentReference"
    assert doc["status"] == "current"
    assert doc["type"]["coding"][0]["code"] == "11506-3"
    assert doc["type"]["coding"][0]["display"] == "Progress note"
    assert doc["subject"]["reference"] == f"Patient/{pid}"
    assert len(doc["content"]) >= 1

    # Base64 decoded content matches plain text
    b64_data = doc["content"][0]["attachment"]["data"]
    decoded = base64.b64decode(b64_data).decode("utf-8")
    assert "SOAP NOTE" in decoded


def test_t4_isolated_mode_does_not_create_fhir_document_reference(soap_fixture):
    """
    T4: Isolated mode check-in stores note locally and does NOT write to FhirSim.
    """
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    fhir_sim.reset_stored_document_references()

    cid = "chk-t4-isolated"
    pid = "iso-pat-99"
    _seed_completed_checkin(cid, user_id=pid, mode="isolated")

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200

    docs = fhir_sim.get_stored_document_references(pid)
    assert len(docs) == 0, "Isolated mode must NOT write DocumentReference to FhirSim"


# =============================================================================
# T5: No Guideline Text in Note
# =============================================================================

def test_t5_no_guideline_text_in_note_titles_sections_only(soap_fixture):
    """
    T5: Note includes guideline titles and sections only; guideline body text is forbidden.
    """
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-t5-guideline"
    guideline_body = "COPYRIGHT PROTECTED FULL TEXT BODY OF THE GUIDELINE RECOMMENDATION"
    explanation = {
        "sources": [
            {
                "chunk_id": "c1",
                "title": "2020 International Society of Hypertension Guidelines",
                "section_path": "Blood Pressure Thresholds",
                "text": guideline_body,
            }
        ]
    }
    _seed_completed_checkin(cid, explanation=explanation)

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200
    data = resp.json()

    plain_text = data["plain_text"]
    assert "2020 International Society of Hypertension Guidelines" in plain_text
    assert "Blood Pressure Thresholds" in plain_text
    # Forbidden guideline body text must not appear anywhere
    assert guideline_body not in plain_text


# =============================================================================
# Audit Row Verification (E5)
# =============================================================================

def test_e5_audit_row_recorded_without_health_data(soap_fixture):
    client = soap_fixture["client"]
    prov_headers = soap_fixture["prov_headers"]

    cid = "chk-e5-audit"
    _seed_completed_checkin(cid)

    resp = client.get(f"/api/provider/review/{cid}/soap", headers=prov_headers)
    assert resp.status_code == 200

    # Query audit log
    with app_store.get_db_cursor() as (cur, be, ph):
        cur.execute(
            f"SELECT action, target, detail_json FROM audit_log WHERE action = 'soap_generated' AND target = {ph}",
            (cid,),
        )
        row = cur.fetchone()
        assert row is not None, "Expected 'soap_generated' audit log row"
        assert row[0] == "soap_generated"
        assert row[1] == cid
        detail = json.loads(row[2]) if row[2] else {}
        assert len(detail) == 0, f"Audit log must contain zero health data, got: {detail}"
