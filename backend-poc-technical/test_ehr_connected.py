"""
Integration and end-to-end hermetic tests for EHR Connected Mode (test_ehr_connected.py).
Tests the simulated hospital, medication scoping, connection test, connected check-ins,
EHR baseline evaluation, and admin config visibility.
"""

import os
import time
import datetime
from typing import Dict, Any, Optional
import pytest
import jwt
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

from main import app
from auth import firebase_verify
from data_sources import app_store
from data_sources.models import NormalizedMedication
from data_sources.medication_scope import (
    select_chronic_care_medications,
    DIABETES_MEDICATIONS,
    HYPERTENSION_MEDICATIONS,
    DEFAULT_MEDICATION_LIMIT,
)


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-1"


@pytest.fixture(scope="session")
def rsa_key_pair():
    """Generates an RSA private/public key pair for test token signing."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="session")
def x509_cert_pem(rsa_key_pair) -> str:
    """Generates a self-signed x509 certificate for the RSA public key."""
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
    """Sets up a clean temporary SQLite database and mocks Firebase verification."""
    test_db_path = str(tmp_path / "test_app_store.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin,admin.cfg@demo.com:admin")

    # Run migrations on clean DB
    app_store.migrate(db_path=test_db_path, backend="sqlite")

    # Mock public certs
    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


def create_test_token(
    private_key,
    sub: str = "uid-patient-1",
    email: str = "patient@demo.com",
    name: str = "Patient One",
    role: Optional[str] = None,
    aud: str = TEST_PROJECT_ID,
    iss: Optional[str] = None,
    kid: str = TEST_KID,
    exp_delta: int = 3600,
) -> str:
    """Helper to generate valid JWT tokens."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "email_verified": True,
        "name": name,
        "aud": aud,
        "iss": iss or f"https://securetoken.google.com/{aud}",
        "iat": now,
        "exp": now + exp_delta,
        "auth_time": now,
    }
    if role:
        payload["role"] = role
    headers = {"kid": kid, "alg": "RS256"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


@pytest.fixture
def client():
    return TestClient(app)


def auth_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 1. MEDICATION SCOPE PURE FUNCTION TESTS
# =============================================================================

def test_medication_scope_constants_defined():
    assert len(DIABETES_MEDICATIONS) >= 15
    assert len(HYPERTENSION_MEDICATIONS) >= 20
    assert DEFAULT_MEDICATION_LIMIT == 8
    assert "metformin" in DIABETES_MEDICATIONS
    assert "lisinopril" in HYPERTENSION_MEDICATIONS
    assert "amlodipine" in HYPERTENSION_MEDICATIONS


def test_medication_scope_filters_and_caps():
    # 20 active medications: 3 relevant, 17 unrelated
    meds = [
        NormalizedMedication("p1", "Metformin 500mg", "active", "500mg", "2026-10-01T00:00:00Z", "fhir", "m1"),
        NormalizedMedication("p1", "Lisinopril 10mg", "active", "10mg", "2026-10-02T00:00:00Z", "fhir", "m2"),
        NormalizedMedication("p1", "Amlodipine 5mg", "active", "5mg", "2026-10-03T00:00:00Z", "fhir", "m3"),
    ]
    for i in range(4, 21):
        meds.append(NormalizedMedication("p1", f"Eye Drop #{i}", "active", "1 drop", "2026-10-01T00:00:00Z", "fhir", f"m{i}"))

    scoped = select_chronic_care_medications(meds)
    assert len(scoped) == 3
    names = {m.medication_name for m in scoped}
    assert names == {"Metformin 500mg", "Lisinopril 10mg", "Amlodipine 5mg"}


def test_medication_scope_excludes_stopped_and_deduplicates():
    meds = [
        NormalizedMedication("p1", "Metformin 500mg", "active", "500mg", "2026-10-01T00:00:00Z", "fhir", "m1"),
        NormalizedMedication("p1", "Metformin 1000mg", "active", "1000mg", "2026-10-05T00:00:00Z", "fhir", "m2"),  # newer duplicate
        NormalizedMedication("p1", "Lisinopril 10mg", "stopped", "10mg", "2026-10-04T00:00:00Z", "fhir", "m3"),   # stopped
        NormalizedMedication("p1", "Aspirin 81mg", "active", "81mg", "2026-10-01T00:00:00Z", "fhir", "m4"),       # unrelated
    ]
    scoped = select_chronic_care_medications(meds)
    assert len(scoped) == 1
    assert scoped[0].medication_name == "Metformin 1000mg"


def test_medication_scope_cap_of_8():
    # 12 active relevant medications
    relevant_names = [
        "Metformin", "Lisinopril", "Amlodipine", "Losartan", "Glimepiride",
        "Empagliflozin", "Sitagliptin", "Doxazosin", "Ramipril",
        "Valsartan", "Telmisartan", "Bisoprolol"
    ]
    meds = [
        NormalizedMedication("p1", name, "active", "10mg", f"2026-10-{i+1:02d}T00:00:00Z", "fhir", f"m{i}")
        for i, name in enumerate(relevant_names)
    ]
    scoped = select_chronic_care_medications(meds)
    assert len(scoped) == 8


# =============================================================================
# 2. REGISTRY AND CONNECTION TESTING ENDPOINTS
# =============================================================================

def test_get_ehr_systems_returns_no_urls(client):
    res = client.get("/api/ehr/systems")
    assert res.status_code == 200
    systems = res.json()
    assert len(systems) >= 2
    for s in systems:
        assert "fhir_base_url" not in s
        assert "base_url" not in s
        assert "url" not in s
        assert "ehr_system_id" in s
        assert "display_name" in s
        assert "kind" in s
        if s["kind"] == "simulated":
            assert s["sample_patients"] is not None
            assert len(s["sample_patients"]) >= 5
        elif s["kind"] == "public_sandbox":
            assert s["suggested_patient_ids"] is not None
            assert len(s["suggested_patient_ids"]) >= 3


def test_ehr_test_endpoint(client, rsa_key_pair):
    token = create_test_token(rsa_key_pair, sub="uid-pat-test", email="pattest@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)

    # 1. Test simulated hospital (succeeds)
    res = client.post("/api/ehr/test", json={"ehr_system_id": "demo-hospital"}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["kind"] == "simulated"
    assert isinstance(body["latency_ms"], int)

    # 2. Test unknown system
    res_404 = client.post("/api/ehr/test", json={"ehr_system_id": "unknown-sys"}, headers=headers)
    assert res_404.status_code == 404


# =============================================================================
# 3. CONNECT ENDPOINT WITH SIMULATED HOSPITAL AND ADULT CHECK
# =============================================================================

def test_connect_simulated_patients(client, rsa_key_pair):
    token = create_test_token(rsa_key_pair, sub="uid-pat-ayesha", email="ayesha@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    # Connect sim-ayesha
    res = client.post("/api/ehr/connect", json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-ayesha"}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "connected"
    assert body["system_id"] == "demo-hospital"
    assert body["kind"] == "simulated"
    assert body["record_source_label"] == "Simulated hospital record (synthetic data)"
    assert body["summary"]["recent_observations"] > 0
    assert body["summary"]["active_medications"] >= 2
    assert body["warning"] is None


def test_connect_sim_newpatient_empty_record_warning(client, rsa_key_pair):
    token = create_test_token(rsa_key_pair, sub="uid-pat-new", email="newpat@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    res = client.post("/api/ehr/connect", json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-newpatient"}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "connected"
    assert body["warning"] == "ehr_empty_record"


def test_connect_child_record_refused_422(client, rsa_key_pair):
    token = create_test_token(rsa_key_pair, sub="uid-pat-child", email="childpat@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    res = client.post("/api/ehr/connect", json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-child"}, headers=headers)
    assert res.status_code == 422
    assert "under 18" in res.json()["detail"]
    assert "ehr_patient_not_adult" in res.json()["detail"]


# =============================================================================
# 4. FULL CONNECTED CHECK-IN WORKFLOWS ON SIMULATOR
# =============================================================================

def _setup_patient(client, rsa_key_pair, uid, email, conditions, dob="1975-01-01"):
    tok = create_test_token(rsa_key_pair, sub=uid, email=email)
    h = auth_header(tok)
    client.post("/api/auth/session", headers=h)
    client.post("/api/me/consent", json={"granted": True}, headers=h)
    client.post("/api/me/provider-notification-consent", json={"granted": True}, headers=h)
    client.put("/api/me/profile", json={"conditions": conditions, "date_of_birth": dob, "inclusion_confirmed": True, "on_insulin_or_sulfonylurea": False}, headers=h)
    return h


def _drive_checkin_to_completion(client, cid, headers, glucose_val="145", bp_val="128/82"):
    ans_res = None
    for _ in range(20):
        q_text = ""
        step = ""
        if ans_res:
            body = ans_res.json()
            if body.get("complete"):
                break
            q_text = (body.get("question") or "").lower()
            step = (body.get("step") or "").lower()
        else:
            step = "greeting"

        if "glucose" in step or "sugar" in q_text or "glucose" in q_text:
            val = glucose_val
        elif "bp" in step or "blood pressure" in q_text or "pressure" in q_text:
            val = bp_val
        elif "symptom" in step or "symptom" in q_text:
            val = "none"
        elif "greeting" in step:
            val = "feeling fine"
        else:
            val = "yes"

        ans_res = client.post(f"/api/checkins/{cid}/answer", headers=headers, json={"answer": val})
        if ans_res.json().get("complete"):
            break


def test_connected_checkin_sim_ayesha_glucose_agree(client, rsa_key_pair):
    """Ayesha has glucose ~145 in EHR. Patient enters 145 -> auto-resolves with agree."""
    h = _setup_patient(client, rsa_key_pair, "uid-ayesha-agree", "ayesha.agree@demo.com", ["diabetes", "hypertension"])
    client.post("/api/ehr/connect", json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-ayesha"}, headers=h)

    start_res = client.post("/api/checkins/start", headers=h)
    assert start_res.status_code == 200
    cid = start_res.json()["checkin_id"]

    _drive_checkin_to_completion(client, cid, h, glucose_val="145", bp_val="128/82")

    comp_res = client.post(f"/api/checkins/{cid}/complete", headers=h)
    assert comp_res.status_code == 200
    comp = comp_res.json()
    assert comp["record_source_label"] == "Simulated hospital record (synthetic data)"

    # Verify reconciliation auto-resolved
    assert comp["reconciliation"] is not None
    assert comp["verification"] is not None
    assert comp["requires_review"] is False


def test_connected_checkin_sim_ayesha_glucose_conflict(client, rsa_key_pair):
    """Ayesha has glucose ~145 in EHR. Patient enters 200 -> generates conflict requiring review."""
    h = _setup_patient(client, rsa_key_pair, "uid-ayesha-conf", "ayesha.conf@demo.com", ["diabetes", "hypertension"])
    client.post("/api/ehr/connect", json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-ayesha"}, headers=h)

    start_res = client.post("/api/checkins/start", headers=h)
    cid = start_res.json()["checkin_id"]

    _drive_checkin_to_completion(client, cid, h, glucose_val="200", bp_val="128/82")

    comp_res = client.post(f"/api/checkins/{cid}/complete", headers=h)
    assert comp_res.status_code == 200
    comp = comp_res.json()
    assert comp["requires_review"] is True


def test_connected_checkin_sim_bilal_bp_change_protocol_from_ehr_baseline(client, rsa_key_pair):
    """
    Bilal has low personal baseline in EHR (110-116/70-74).
    Patient enters 135/85 -> rise >= 20 mmHg over personal baseline starts bp_change triage protocol.
    """
    h = _setup_patient(client, rsa_key_pair, "uid-bilal-bp", "bilal.bp@demo.com", ["hypertension"])
    client.post("/api/ehr/connect", json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-bilal"}, headers=h)

    start_res = client.post("/api/checkins/start", headers=h)
    cid = start_res.json()["checkin_id"]

    client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "fine", "step": "greeting"})
    ans_bp = client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "135/85", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "yes", "step": "adherence"})
    ans_life = client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "none", "step": "lifestyle"})

    # Because 135 is >= 20 mmHg above Bilal's baseline of ~113, bp_change protocol triggers!
    body = ans_life.json()
    assert body["phase"] == "triage"
    assert "bp_change" in body["step"]


def test_connected_checkin_sim_bilal_normal_bp_no_protocol(client, rsa_key_pair):
    """Bilal enters 114/72 -> matches personal baseline, starts no triage protocol."""
    h = _setup_patient(client, rsa_key_pair, "uid-bilal-norm", "bilal.norm@demo.com", ["hypertension"])
    client.post("/api/ehr/connect", json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-bilal"}, headers=h)

    start_res = client.post("/api/checkins/start", headers=h)
    cid = start_res.json()["checkin_id"]

    client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "114/72", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "yes", "step": "adherence"})
    ans_life = client.post(f"/api/checkins/{cid}/answer", headers=h, json={"answer": "none", "step": "lifestyle"})

    # Does not trigger bp_change
    body = ans_life.json()
    assert body["phase"] == "medication" or body["complete"] is True


# =============================================================================
# 5. ADMIN CONFIG STATUS VISIBILITY (NO SECRETS)
# =============================================================================

def test_admin_config_status_no_secret_leak(client, rsa_key_pair, x509_cert_pem, monkeypatch):
    # Set recognizable fake secrets in environment
    secret_marker = "SUPER_SECRET_KEY_NEVER_PRINT_XYZ987"
    monkeypatch.setenv("FIREBASE_PROJECT_ID", secret_marker)
    monkeypatch.setenv("FHIR_BASE_URL", f"https://secret.org/{secret_marker}")

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    admin_token = create_test_token(rsa_key_pair, sub="uid-admin-cfg", email="admin.cfg@demo.com", role="admin", aud=secret_marker)
    admin_headers = auth_header(admin_token)
    client.post("/api/auth/session", headers=admin_headers)

    res = client.get("/api/admin/config-status", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "settings" in data

    # Verify names and set booleans
    names = {s["name"]: s["set"] for s in data["settings"]}
    assert names["FIREBASE_PROJECT_ID"] is True
    assert names["FHIR_BASE_URL"] is True
    assert names["DB_BACKEND"] is False or names["DB_BACKEND"] is True

    # Critical security assertion: secret string NEVER appears in raw response body
    raw_response_text = res.text
    assert secret_marker not in raw_response_text


def test_admin_config_status_role_guard(client, rsa_key_pair):
    # Anonymous: 401
    assert client.get("/api/admin/config-status").status_code == 401

    # Patient: 403
    pat_token = create_test_token(rsa_key_pair, sub="uid-pat-cfg", email="pat.cfg@demo.com", role="patient")
    pat_headers = auth_header(pat_token)
    client.post("/api/auth/session", headers=pat_headers)
    assert client.get("/api/admin/config-status", headers=pat_headers).status_code == 403
