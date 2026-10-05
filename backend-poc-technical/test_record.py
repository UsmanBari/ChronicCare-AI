"""
Hermetic Integration Tests for Isolated-Mode Patient Record Endpoints (P2).

Covers:
- Full CRUD for each item type (conditions basis, medications, allergies, baseline observations)
- Validation (empty, too long, control characters, out-of-range values, future/too-old dates, duplicates, caps)
- Extra fields rejected (422)
- Active EHR connection returns 409 ('record_managed_by_ehr')
- User B cannot read, change, or delete User A's items (404)
- Origins are 'self_reported' in local store
- Missing/revoked consent returns 403
- Baseline observation or medication makes first check-in not a cold start (is_cold_start is False), empty is True
- Audit rows contain only item TYPE and counts (no PHI, names, doses, values)
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
TEST_KID = "test-key-id-record-1"


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
    test_db_path = str(tmp_path / "test_chroniccare_record.db")

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
    sub: str = "uid-patient-rec",
    email: str = "patient_rec@demo.com",
    name: str = "Patient Record",
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


def _setup_patient(client, rsa_key_pair, user_id="p-rec-1", email="p_rec@demo.com", conditions=None):
    token = create_test_token(rsa_key_pair, sub=user_id, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True})
    client.put("/api/me/profile", headers=headers, json={
        "conditions": conditions or ["diabetes", "hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "language": "en",
    })
    return headers


# ----------------------------------------------------------------------------
# 1. Full CRUD for Each Item Type
# ----------------------------------------------------------------------------
def test_full_crud_record_items(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-crud-1", "p_crud1@demo.com")

    # A. Conditions Basis
    cb_resp = client.put("/api/me/record/conditions-basis", headers=headers, json={
        "diabetes": "clinician_diagnosed",
        "hypertension": "self_reported",
    })
    assert cb_resp.status_code == 200
    assert cb_resp.json()["conditions_basis"]["diabetes"] == "clinician_diagnosed"
    assert cb_resp.json()["conditions_basis"]["hypertension"] == "self_reported"

    # B. Medication CRUD
    med_resp = client.post("/api/me/record/medications", headers=headers, json={
        "name": "Metformin 500mg",
        "dosage": "1 tablet twice daily",
        "status": "active",
    })
    assert med_resp.status_code == 200
    med_data = med_resp.json()
    med_id = med_data["id"]
    assert med_data["name"] == "Metformin 500mg"
    assert med_data["status"] == "active"

    # Patch medication
    patch_med = client.patch(f"/api/me/record/medications/{med_id}", headers=headers, json={
        "dosage": "1 tablet daily",
        "status": "stopped",
    })
    assert patch_med.status_code == 200
    assert patch_med.json()["dosage"] == "1 tablet daily"
    assert patch_med.json()["status"] == "stopped"

    # C. Allergy CRUD
    alg_resp = client.post("/api/me/record/allergies", headers=headers, json={
        "substance": "Penicillin",
        "reaction": "Rash and hives",
        "confirmed": True,
    })
    assert alg_resp.status_code == 200
    alg_data = alg_resp.json()
    alg_id = alg_data["id"]
    assert alg_data["substance"] == "Penicillin"
    assert alg_data["confirmed"] is True

    # D. Baseline Observation CRUD
    obs_resp = client.post("/api/me/record/observations", headers=headers, json={
        "observation_type": "glucose",
        "value": 115.0,
    })
    assert obs_resp.status_code == 200
    obs_data = obs_resp.json()
    obs_id = obs_data["id"]
    assert obs_data["unit"] == "mg/dL"
    assert obs_data["value"] == 115.0

    # Read full record
    rec_resp = client.get("/api/me/record", headers=headers)
    assert rec_resp.status_code == 200
    rec = rec_resp.json()
    assert rec["mode"] == "isolated"
    assert len(rec["conditions"]) == 2
    assert len(rec["medications"]) == 1
    assert len(rec["allergies"]) == 1
    assert len(rec["baseline_observations"]) == 1

    # Delete Medication, Allergy, Observation
    del_med = client.delete(f"/api/me/record/medications/{med_id}", headers=headers)
    assert del_med.status_code == 200

    del_alg = client.delete(f"/api/me/record/allergies/{alg_id}", headers=headers)
    assert del_alg.status_code == 200

    del_obs = client.delete(f"/api/me/record/observations/{obs_id}", headers=headers)
    assert del_obs.status_code == 200

    # Verify empty record lists
    rec_after = client.get("/api/me/record", headers=headers).json()
    assert len(rec_after["medications"]) == 0
    assert len(rec_after["allergies"]) == 0
    assert len(rec_after["baseline_observations"]) == 0


# ----------------------------------------------------------------------------
# 2. Validation Checks
# ----------------------------------------------------------------------------
def test_medication_validation(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-val-med", "p_val_med@demo.com")

    # Empty name or dosage
    assert client.post("/api/me/record/medications", headers=headers, json={
        "name": "   ", "dosage": "10mg", "status": "active"
    }).status_code in (400, 422)

    # Name too long (>80)
    assert client.post("/api/me/record/medications", headers=headers, json={
        "name": "A" * 81, "dosage": "10mg", "status": "active"
    }).status_code == 422

    # Dosage too long (>100)
    assert client.post("/api/me/record/medications", headers=headers, json={
        "name": "Aspirin", "dosage": "B" * 101, "status": "active"
    }).status_code == 422

    # Control characters rejected
    assert client.post("/api/me/record/medications", headers=headers, json={
        "name": "Aspirin\x00", "dosage": "10mg", "status": "active"
    }).status_code in (400, 422)

    # Invalid status
    assert client.post("/api/me/record/medications", headers=headers, json={
        "name": "Aspirin", "dosage": "10mg", "status": "unknown"
    }).status_code in (400, 422)

    # Duplicate normalized name returns 409
    r1 = client.post("/api/me/record/medications", headers=headers, json={
        "name": "Metformin 500mg", "dosage": "1 daily", "status": "active"
    })
    assert r1.status_code == 200
    r2 = client.post("/api/me/record/medications", headers=headers, json={
        "name": "  metformin 500MG  ", "dosage": "2 daily", "status": "active"
    })
    assert r2.status_code == 409
    assert r2.json()["detail"] == "duplicate_medication"


def test_allergies_validation(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-val-alg", "p_val_alg@demo.com")

    # Empty substance
    assert client.post("/api/me/record/allergies", headers=headers, json={
        "substance": "  ", "reaction": "rash", "confirmed": True
    }).status_code in (400, 422)

    # Substance too long (>80)
    assert client.post("/api/me/record/allergies", headers=headers, json={
        "substance": "S" * 81, "reaction": "rash", "confirmed": True
    }).status_code == 422

    # Reaction too long (>120)
    assert client.post("/api/me/record/allergies", headers=headers, json={
        "substance": "Peanuts", "reaction": "R" * 121, "confirmed": True
    }).status_code == 422

    # Control character rejected
    assert client.post("/api/me/record/allergies", headers=headers, json={
        "substance": "Peanuts\x1f", "reaction": "rash", "confirmed": True
    }).status_code in (400, 422)


def test_observations_range_and_date_validation(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-val-obs", "p_val_obs@demo.com")

    # Glucose range: 20 to 600
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 15.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 650.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 120.0}).status_code == 200

    # Systolic BP: 60 to 260
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "blood_pressure_systolic", "value": 50.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "blood_pressure_systolic", "value": 280.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "blood_pressure_systolic", "value": 130.0}).status_code == 200

    # Diastolic BP: 30 to 160
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "blood_pressure_diastolic", "value": 20.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "blood_pressure_diastolic", "value": 170.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "blood_pressure_diastolic", "value": 85.0}).status_code == 200

    # Weight: 20 to 300
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "weight", "value": 10.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "weight", "value": 350.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "weight", "value": 75.0}).status_code == 200

    # HbA1c: 3 to 20
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "hba1c", "value": 2.5}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "hba1c", "value": 25.0}).status_code == 400
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "hba1c", "value": 6.5}).status_code == 200

    # Future date (> now + 60s)
    future_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 120.0, "measured_at": future_iso}).status_code == 400

    # Too old date (> 365 days)
    old_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 120.0, "measured_at": old_iso}).status_code == 400


def test_conditions_basis_validation(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-cond-b", "p_cond_b@demo.com", conditions=["diabetes"])

    # Condition not in profile
    assert client.put("/api/me/record/conditions-basis", headers=headers, json={"hypertension": "self_reported"}).status_code == 400

    # Invalid basis
    assert client.put("/api/me/record/conditions-basis", headers=headers, json={"diabetes": "guessed"}).status_code == 400


# ----------------------------------------------------------------------------
# 3. Maximum Caps
# ----------------------------------------------------------------------------
def test_caps_medications_allergies_observations(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-caps", "p_caps@demo.com")

    # Medications cap = 30
    for i in range(30):
        r = client.post("/api/me/record/medications", headers=headers, json={"name": f"Drug {i}", "dosage": "1", "status": "active"})
        assert r.status_code == 200
    assert client.post("/api/me/record/medications", headers=headers, json={"name": "Drug 31", "dosage": "1", "status": "active"}).status_code == 400

    # Allergies cap = 30
    for i in range(30):
        r = client.post("/api/me/record/allergies", headers=headers, json={"substance": f"Allergen {i}", "confirmed": True})
        assert r.status_code == 200
    assert client.post("/api/me/record/allergies", headers=headers, json={"substance": "Allergen 31", "confirmed": True}).status_code == 400

    # Observations cap = 20
    for i in range(20):
        r = client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 100.0 + i})
        assert r.status_code == 200
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 150.0}).status_code == 400


# ----------------------------------------------------------------------------
# 4. Extra fields rejected (422)
# ----------------------------------------------------------------------------
def test_extra_fields_forbidden(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-extra", "p_extra@demo.com")

    assert client.post("/api/me/record/medications", headers=headers, json={
        "name": "Aspirin", "dosage": "81mg", "status": "active", "extra_field": "oops"
    }).status_code == 422

    assert client.post("/api/me/record/allergies", headers=headers, json={
        "substance": "Latex", "confirmed": True, "extra_field": "oops"
    }).status_code == 422

    assert client.post("/api/me/record/observations", headers=headers, json={
        "observation_type": "glucose", "value": 100.0, "extra_field": "oops"
    }).status_code == 422


# ----------------------------------------------------------------------------
# 5. Connected Mode returns 409 'record_managed_by_ehr'
# ----------------------------------------------------------------------------
def test_connected_mode_blocks_record_endpoints(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-connected", "p_conn@demo.com")

    app_store.record_ehr_connection(
        connection_id="conn-rec-block",
        user_id="p-connected",
        ehr_system_id="smart-sandbox",
        external_patient_id="EXT-CONN-1",
        status="active",
    )

    assert client.get("/api/me/record", headers=headers).status_code == 409
    assert client.get("/api/me/record", headers=headers).json()["detail"] == "record_managed_by_ehr"
    assert client.put("/api/me/record/conditions-basis", headers=headers, json={"diabetes": "self_reported"}).status_code == 409
    assert client.post("/api/me/record/medications", headers=headers, json={"name": "Aspirin", "dosage": "1", "status": "active"}).status_code == 409
    assert client.post("/api/me/record/allergies", headers=headers, json={"substance": "Latex", "confirmed": True}).status_code == 409
    assert client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 100.0}).status_code == 409


# ----------------------------------------------------------------------------
# 6. User Isolation (User B cannot read, patch or delete User A's items -> 404)
# ----------------------------------------------------------------------------
def test_user_ownership_isolation(rsa_key_pair):
    client = TestClient(app)
    headers_a = _setup_patient(client, rsa_key_pair, "p-user-a", "p_usera@demo.com")
    headers_b = _setup_patient(client, rsa_key_pair, "p-user-b", "p_userb@demo.com")

    # User A creates items
    med_a = client.post("/api/me/record/medications", headers=headers_a, json={"name": "Metformin 500mg", "dosage": "1", "status": "active"}).json()["id"]
    alg_a = client.post("/api/me/record/allergies", headers=headers_a, json={"substance": "Pollen", "confirmed": True}).json()["id"]
    obs_a = client.post("/api/me/record/observations", headers=headers_a, json={"observation_type": "glucose", "value": 120.0}).json()["id"]

    # User B cannot see User A's items
    rec_b = client.get("/api/me/record", headers=headers_b).json()
    assert len(rec_b["medications"]) == 0
    assert len(rec_b["allergies"]) == 0
    assert len(rec_b["baseline_observations"]) == 0

    # User B cannot patch or delete User A's medication
    assert client.patch(f"/api/me/record/medications/{med_a}", headers=headers_b, json={"dosage": "2"}).status_code == 404
    assert client.delete(f"/api/me/record/medications/{med_a}", headers=headers_b).status_code == 404

    # User B cannot delete User A's allergy
    assert client.delete(f"/api/me/record/allergies/{alg_a}", headers=headers_b).status_code == 404

    # User B cannot delete User A's observation
    assert client.delete(f"/api/me/record/observations/{obs_a}", headers=headers_b).status_code == 404


# ----------------------------------------------------------------------------
# 7. Origins and Local Store Provenance
# ----------------------------------------------------------------------------
def test_origins_are_self_reported(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-origins", "p_origins@demo.com")

    client.post("/api/me/record/medications", headers=headers, json={"name": "Metformin 500mg", "dosage": "1", "status": "active"})
    client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 110.0})

    patient_id = "local-p-origins"
    med_origins = local_store.get_local_medication_origins(patient_id)
    obs_origins = local_store.get_local_observation_origins(patient_id)

    assert len(med_origins) == 1 and list(med_origins.values())[0] == "self_reported"
    assert len(obs_origins) == 1 and list(obs_origins.values())[0] == "self_reported"


# ----------------------------------------------------------------------------
# 8. Missing Consent Returns 403
# ----------------------------------------------------------------------------
def test_missing_or_revoked_consent_returns_403(rsa_key_pair):
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="p-no-consent", email="p_noconsent@demo.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)

    # Without granting consent
    assert client.get("/api/me/record", headers=headers).status_code == 403
    assert client.post("/api/me/record/medications", headers=headers, json={"name": "Metformin", "dosage": "1", "status": "active"}).status_code == 403

    # Grant then revoke
    client.post("/api/me/consent", headers=headers, json={"granted": True})
    client.post("/api/me/consent", headers=headers, json={"granted": False})
    assert client.get("/api/me/record", headers=headers).status_code == 403


# ----------------------------------------------------------------------------
# 9. Cold Start Determination Based on Baseline Data
# ----------------------------------------------------------------------------
def test_cold_start_determination(rsa_key_pair):
    client = TestClient(app)
    
    # Patient 1: completely empty -> cold start
    h1 = _setup_patient(client, rsa_key_pair, "p-empty-start", "p_emp@demo.com")
    r1 = client.post("/api/checkins/start", headers=h1)
    assert r1.status_code == 200
    assert r1.json()["is_cold_start"] is True

    # Patient 2: has a baseline observation -> not cold start
    h2 = _setup_patient(client, rsa_key_pair, "p-obs-start", "p_obs@demo.com")
    client.post("/api/me/record/observations", headers=h2, json={"observation_type": "glucose", "value": 120.0})
    r2 = client.post("/api/checkins/start", headers=h2)
    assert r2.status_code == 200
    assert r2.json()["is_cold_start"] is False

    # Patient 3: has a medication -> not cold start
    h3 = _setup_patient(client, rsa_key_pair, "p-med-start", "p_med@demo.com")
    client.post("/api/me/record/medications", headers=h3, json={"name": "Metformin 500mg", "dosage": "1", "status": "active"})
    r3 = client.post("/api/checkins/start", headers=h3)
    assert r3.status_code == 200
    assert r3.json()["is_cold_start"] is False


# ----------------------------------------------------------------------------
# 10. Audit Rows Contain No PHI
# ----------------------------------------------------------------------------
def test_audit_rows_contain_no_phi(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-audit-phi", "p_audit_phi@demo.com")

    client.post("/api/me/record/medications", headers=headers, json={"name": "SpecialDrugName123", "dosage": "500mgSecretDose", "status": "active"})
    client.post("/api/me/record/allergies", headers=headers, json={"substance": "SuperRareAllergen456", "reaction": "SevereReaction789", "confirmed": True})
    client.post("/api/me/record/observations", headers=headers, json={"observation_type": "glucose", "value": 142.7})

    audit_logs = app_store.get_audit_logs(limit=20)
    for log in audit_logs:
        detail_str = str(log["detail"])
        assert "SpecialDrugName123" not in detail_str
        assert "500mgSecretDose" not in detail_str
        assert "SuperRareAllergen456" not in detail_str
        assert "SevereReaction789" not in detail_str
        assert "142.7" not in detail_str
        if log["action"].startswith("record_"):
            assert "type" in log["detail"]
            assert "count" in log["detail"]
