"""
Integration tests for Record Edit History (schema v13, API, atomicity, isolation).
"""

import datetime
import os
import time
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
from data_sources import app_store, local_store


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-record-edits"


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
    test_db_path = str(tmp_path / "test_chroniccare_edits.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


def create_test_token(
    private_key,
    sub: str = "uid-patient-rec-edits",
    email: str = "patient_edits@demo.com",
    name: str = "Patient Edits",
    aud: str = TEST_PROJECT_ID,
    kid: str = TEST_KID,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "aud": aud,
        "iss": f"https://securetoken.google.com/{aud}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    headers = {"kid": kid}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


def _setup_patient(client, rsa_key_pair, user_id="p-edit-1", email="p_edit@demo.com"):
    token = create_test_token(rsa_key_pair, sub=user_id, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True})
    client.put("/api/me/profile", headers=headers, json={
        "conditions": ["diabetes", "hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "language": "en",
    })
    return headers


# ----------------------------------------------------------------------------
# 1. Medication Edit History: Create, Update (fields), Delete, No-Op
# ----------------------------------------------------------------------------
def test_medication_edit_history(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-med-edit", "p_med_edit@demo.com")

    # Create medication
    med_resp = client.post("/api/me/record/medications", headers=headers, json={
        "name": "Metformin 500mg",
        "dosage": "1 tablet twice daily",
        "status": "active",
    })
    assert med_resp.status_code == 200
    med_id = med_resp.json()["id"]

    # History should contain "created"
    hist_resp = client.get(f"/api/me/record/history?record_type=medication&record_id={med_id}", headers=headers)
    assert hist_resp.status_code == 200
    edits = hist_resp.json()["edits"]
    assert len(edits) == 1
    assert edits[0]["field"] == "created"
    assert edits[0]["old_value"] is None
    assert edits[0]["new_value"]["name"] == "Metformin 500mg"
    assert edits[0]["origin"] == "self_reported"

    # Update dosage
    patch_resp = client.patch(f"/api/me/record/medications/{med_id}", headers=headers, json={
        "dosage": "1 tablet once daily",
    })
    assert patch_resp.status_code == 200

    hist_resp = client.get(f"/api/me/record/history?record_type=medication&record_id={med_id}", headers=headers)
    assert hist_resp.status_code == 200
    edits = hist_resp.json()["edits"]
    assert len(edits) == 2
    # newest first
    assert edits[0]["field"] == "dosage"
    assert edits[0]["old_value"] == "1 tablet twice daily"
    assert edits[0]["new_value"] == "1 tablet once daily"

    # No-op update (patch with exact same dosage)
    patch_resp_noop = client.patch(f"/api/me/record/medications/{med_id}", headers=headers, json={
        "dosage": "1 tablet once daily",
    })
    assert patch_resp_noop.status_code == 200
    hist_resp_noop = client.get(f"/api/me/record/history?record_type=medication&record_id={med_id}", headers=headers)
    assert len(hist_resp_noop.json()["edits"]) == 2  # unchanged, 0 rows added

    # Delete medication
    del_resp = client.delete(f"/api/me/record/medications/{med_id}", headers=headers)
    assert del_resp.status_code == 200

    hist_resp_after_del = client.get(f"/api/me/record/history?record_type=medication&record_id={med_id}", headers=headers)
    assert hist_resp_after_del.status_code == 200
    edits_after_del = hist_resp_after_del.json()["edits"]
    assert len(edits_after_del) == 3
    assert edits_after_del[0]["field"] == "deleted"
    assert edits_after_del[0]["new_value"] is None


# ----------------------------------------------------------------------------
# 2. Observation Edit History: Create, Delete
# ----------------------------------------------------------------------------
def test_observation_edit_history(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-obs-edit", "p_obs_edit@demo.com")

    # Add baseline observation
    obs_resp = client.post("/api/me/record/observations", headers=headers, json={
        "observation_type": "glucose",
        "value": 115.0,
    })
    assert obs_resp.status_code == 200
    obs_id = obs_resp.json()["id"]

    hist_resp = client.get(f"/api/me/record/history?record_type=observation&record_id={obs_id}", headers=headers)
    assert hist_resp.status_code == 200
    edits = hist_resp.json()["edits"]
    assert len(edits) == 1
    assert edits[0]["field"] == "created"
    assert edits[0]["new_value"]["value"] == 115.0

    # Delete observation
    del_resp = client.delete(f"/api/me/record/observations/{obs_id}", headers=headers)
    assert del_resp.status_code == 200

    hist_resp_del = client.get(f"/api/me/record/history?record_type=observation&record_id={obs_id}", headers=headers)
    edits_del = hist_resp_del.json()["edits"]
    assert len(edits_del) == 2
    assert edits_del[0]["field"] == "deleted"


# ----------------------------------------------------------------------------
# 3. Allergy Edit History: Create, Delete
# ----------------------------------------------------------------------------
def test_allergy_edit_history(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-all-edit", "p_all_edit@demo.com")

    # Create allergy
    all_resp = client.post("/api/me/record/allergies", headers=headers, json={
        "substance": "Penicillin",
        "reaction": "Rash",
        "confirmed": True,
    })
    assert all_resp.status_code == 200
    allergy_id = all_resp.json()["id"]

    hist_resp = client.get(f"/api/me/record/history?record_type=allergy&record_id={allergy_id}", headers=headers)
    assert hist_resp.status_code == 200
    edits = hist_resp.json()["edits"]
    assert len(edits) == 1
    assert edits[0]["field"] == "created"
    assert edits[0]["new_value"]["substance"] == "Penicillin"

    # Delete allergy
    del_resp = client.delete(f"/api/me/record/allergies/{allergy_id}", headers=headers)
    assert del_resp.status_code == 200

    hist_resp_del = client.get(f"/api/me/record/history?record_type=allergy&record_id={allergy_id}", headers=headers)
    assert len(hist_resp_del.json()["edits"]) == 2
    assert hist_resp_del.json()["edits"][0]["field"] == "deleted"


# ----------------------------------------------------------------------------
# 4. Conditions Basis Edit History: Update
# ----------------------------------------------------------------------------
def test_conditions_basis_edit_history(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-cb-edit", "p_cb_edit@demo.com")

    cb_resp = client.put("/api/me/record/conditions-basis", headers=headers, json={
        "diabetes": "clinician_diagnosed",
        "hypertension": "self_reported",
    })
    assert cb_resp.status_code == 200

    hist_resp = client.get("/api/me/record/history?record_type=condition", headers=headers)
    assert hist_resp.status_code == 200
    edits = hist_resp.json()["edits"]
    assert len(edits) >= 1
    assert edits[0]["record_type"] == "condition"
    assert edits[0]["field"] == "basis"


# ----------------------------------------------------------------------------
# 5. Atomicity & Rollback
# ----------------------------------------------------------------------------
def test_record_edit_atomicity_and_rollback(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-rollback", "p_rollback@demo.com")

    orig_app_edit = app_store.record_edit
    orig_local_edit = local_store.record_edit

    def failing_record_edit(*args, **kwargs):
        raise RuntimeError("Simulated DB write failure during record edit")

    try:
        app_store.record_edit = failing_record_edit
        local_store.record_edit = failing_record_edit

        # Attempt to create medication - should fail and rollback
        with pytest.raises(Exception):
            client.post("/api/me/record/medications", headers=headers, json={
                "name": "Glimepiride 2mg",
                "dosage": "1 tablet daily",
                "status": "active",
            })
    finally:
        app_store.record_edit = orig_app_edit
        local_store.record_edit = orig_local_edit

    # Verify medication was NOT created and 0 edit rows exist
    rec_resp = client.get("/api/me/record", headers=headers)
    assert rec_resp.status_code == 200
    assert len(rec_resp.json()["medications"]) == 0

    hist_resp = client.get("/api/me/record/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()["edits"]) == 0


# ----------------------------------------------------------------------------
# 6. Cross-Patient Isolation & Access Control
# ----------------------------------------------------------------------------
def test_cross_patient_isolation(rsa_key_pair):
    client = TestClient(app)
    headers_a = _setup_patient(client, rsa_key_pair, "p-iso-a", "p_iso_a@demo.com")
    headers_b = _setup_patient(client, rsa_key_pair, "p-iso-b", "p_iso_b@demo.com")

    # User A creates a medication
    med_resp_a = client.post("/api/me/record/medications", headers=headers_a, json={
        "name": "Amlodipine 5mg",
        "dosage": "1 tablet daily",
        "status": "active",
    })
    med_id_a = med_resp_a.json()["id"]

    # User B queries their own history -> sees 0 edits
    hist_resp_b = client.get("/api/me/record/history", headers=headers_b)
    assert hist_resp_b.status_code == 200
    assert len(hist_resp_b.json()["edits"]) == 0

    # User B tries to query User A's med_id directly -> 403 Forbidden
    cross_resp = client.get(f"/api/me/record/history?record_type=medication&record_id={med_id_a}", headers=headers_b)
    assert cross_resp.status_code == 403


# ----------------------------------------------------------------------------
# 7. Connected Mode returns 409 and writes 0 edit rows
# ----------------------------------------------------------------------------
def test_connected_mode_returns_409_no_edits(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-conn-edit", "p_conn_edit@demo.com")

    # Connect to EHR
    conn_resp = client.post("/api/ehr/connect", headers=headers, json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-ayesha"})
    assert conn_resp.status_code == 200

    # Attempt to add medication in connected mode -> 409
    med_resp = client.post("/api/me/record/medications", headers=headers, json={
        "name": "Insulin Glargine 10u",
        "dosage": "10 units at bedtime",
        "status": "active",
    })
    assert med_resp.status_code == 409

    # History should have 0 edit rows
    hist_resp = client.get("/api/me/record/history", headers=headers)
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()["edits"]) == 0


# ----------------------------------------------------------------------------
# 8. Zero PHI in Audit Log
# ----------------------------------------------------------------------------
def test_zero_phi_in_audit_log(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-phi-audit", "p_phi_audit@demo.com")

    client.post("/api/me/record/medications", headers=headers, json={
        "name": "SecretDrug 500mg",
        "dosage": "TopSecretDose",
        "status": "active",
    })

    audit_logs = app_store.get_audit_logs(limit=20)
    for log in audit_logs:
        detail_str = str(log.get("detail", ""))
        assert "SecretDrug" not in detail_str
        assert "TopSecretDose" not in detail_str


# ----------------------------------------------------------------------------
# 9. Provider Access Rules
# ----------------------------------------------------------------------------
def test_provider_access_rules(rsa_key_pair):
    client = TestClient(app)
    # Patient headers
    patient_headers = _setup_patient(client, rsa_key_pair, "p-prov-test", "p_prov_test@demo.com")

    # Patient adds medication
    med_resp = client.post("/api/me/record/medications", headers=patient_headers, json={
        "name": "Metformin 850mg",
        "dosage": "1 tablet daily",
        "status": "active",
    })
    assert med_resp.status_code == 200

    # Provider token
    prov_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com", name="Dr. Provider")
    prov_headers = {"Authorization": f"Bearer {prov_token}"}
    client.post("/api/auth/session", headers=prov_headers)

    # Provider calling patient endpoint directly -> 403
    p_resp = client.get("/api/me/record/history", headers=prov_headers)
    assert p_resp.status_code == 403

    # Seed checkin & checkin_result so it appears in provider review
    checkin_id = "chk-prov-test"
    app_store.create_checkin(checkin_id, "p-prov-test", "isolated", "local-p-prov-test", {}, "complete", started_at="2026-10-01T10:00:00Z")
    app_store.create_checkin_result(checkin_id, emergency=False, intakes=[], reconciliation={}, verification={}, requires_review=True, max_severity="low", review_status="open", created_at="2026-10-01T10:05:00Z")

    # Provider reviewing this checkin receives recent_record_edits
    rev_resp = client.get(f"/api/provider/review/{checkin_id}", headers=prov_headers)
    assert rev_resp.status_code == 200
    recent_edits = rev_resp.json().get("recent_record_edits")
    assert recent_edits is not None
    assert len(recent_edits) >= 1
    assert recent_edits[0]["record_type"] == "medication"
    assert recent_edits[0]["field"] == "created"
