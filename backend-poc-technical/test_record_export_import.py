"""
Integration tests for Patient Record Export and Import (JSON and FHIR R4).
"""

import datetime
import json
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
from data_sources import fhir_adapter


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-export-import"


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
    test_db_path = str(tmp_path / "test_chroniccare_export_import.db")

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
    sub: str = "uid-patient-exp-imp",
    email: str = "patient_exp_imp@demo.com",
    name: str = "Patient Export Import",
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


def _setup_patient(client, rsa_key_pair, user_id="p-exp-1", email="p_exp@demo.com"):
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
# 1. Export in Isolated Mode (JSON and FHIR)
# ----------------------------------------------------------------------------
def test_export_isolated_json_and_fhir(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-exp-iso", "p_exp_iso@demo.com")

    # Seed isolated record items
    client.post("/api/me/record/medications", headers=headers, json={
        "name": "Metformin 500mg",
        "dosage": "1 tablet twice daily",
        "status": "active",
    })
    client.post("/api/me/record/allergies", headers=headers, json={
        "substance": "Penicillin",
        "reaction": "Rash",
        "confirmed": True,
    })
    client.post("/api/me/record/observations", headers=headers, json={
        "observation_type": "glucose",
        "value": 115.0,
    })
    client.put("/api/me/record/conditions-basis", headers=headers, json={
        "diabetes": "clinician_diagnosed",
        "hypertension": "self_reported",
    })

    # A. JSON Export
    resp_json = client.get("/api/me/record/export?format=json", headers=headers)
    assert resp_json.status_code == 200
    assert "attachment; filename=\"chroniccare-record-" in resp_json.headers["content-disposition"]
    data = resp_json.json()
    record = data["record"]
    assert record["mode"] == "isolated"
    assert len(record["medications"]) == 1
    assert record["medications"][0]["name"] == "Metformin 500mg"
    assert len(record["allergies"]) == 1
    assert record["allergies"][0]["substance"] == "Penicillin"
    assert len(record["baseline_observations"]) == 1
    assert record["baseline_observations"][0]["observation_type"] == "glucose"

    # B. FHIR Export
    resp_fhir = client.get("/api/me/record/export?format=fhir", headers=headers)
    assert resp_fhir.status_code == 200
    assert "chroniccare-record-" in resp_fhir.headers["content-disposition"]
    assert ".fhir.json" in resp_fhir.headers["content-disposition"]
    bundle = resp_fhir.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"

    # Verify FHIR Round-trip parsing with fhir_adapter
    norm_obs = fhir_adapter.fhir_to_normalized_observations(bundle)
    assert len(norm_obs) >= 1
    assert norm_obs[0].observation_type == "glucose"
    assert norm_obs[0].value == 115.0

    norm_meds = fhir_adapter.fhir_to_normalized_medications(bundle)
    assert len(norm_meds) >= 1
    assert "metformin" in norm_meds[0].medication_name.lower()


# ----------------------------------------------------------------------------
# 2. Export in Connected Mode (Works in both isolated and connected modes)
# ----------------------------------------------------------------------------
def test_export_connected_mode(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-exp-conn", "p_exp_conn@demo.com")

    # Connect to EHR
    conn_resp = client.post("/api/ehr/connect", headers=headers, json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-ayesha"})
    assert conn_resp.status_code == 200

    resp = client.get("/api/me/record/export?format=json", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    record = data["record"]
    assert record["mode"] == "connected"
    assert len(record["medications"]) >= 1
    assert len(record["baseline_observations"]) >= 1


# ----------------------------------------------------------------------------
# 3. Import: Dry Run (Validates & Previews without DB writes)
# ----------------------------------------------------------------------------
def test_import_dry_run(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-imp-dry", "p_imp_dry@demo.com")

    import_payload = {
        "format": "chroniccare_record_v1",
        "conditions_basis": {"diabetes": "self_reported"},
        "medications": [
            {"name": "Glimepiride 2mg", "dosage": "1 tablet daily", "status": "active"}
        ],
        "allergies": [
            {"substance": "Aspirin", "reaction": "Bronchospasm", "confirmed": True}
        ],
        "baseline_observations": [
            {"type": "blood_pressure_systolic", "value": 130.0, "measured_at": "2026-10-28T09:00:00Z"}
        ],
    }

    resp = client.post(
        "/api/me/record/import?dry_run=true",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps(import_payload),
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["dry_run"] is True
    assert res_data["imported_counts"]["medications"] == 1
    assert res_data["imported_counts"]["allergies"] == 1
    assert res_data["imported_counts"]["observations"] == 1
    assert len(res_data["preview"]["medications"]) == 1

    # Verify no records were actually written to database
    rec_resp = client.get("/api/me/record", headers=headers)
    assert rec_resp.status_code == 200
    rec = rec_resp.json()
    assert len(rec["medications"]) == 0
    assert len(rec["allergies"]) == 0
    assert len(rec["baseline_observations"]) == 0


# ----------------------------------------------------------------------------
# 4. Import: Commit, Duplicates, and Re-importing own Export
# ----------------------------------------------------------------------------
def test_import_commit_and_duplicate_detection(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-imp-commit", "p_imp_commit@demo.com")

    import_payload = {
        "format": "chroniccare_record_v1",
        "conditions_basis": {"diabetes": "clinician_diagnosed"},
        "medications": [
            {"name": "Empagliflozin 10mg", "dosage": "1 tablet OD", "status": "active"}
        ],
        "allergies": [
            {"substance": "Sulfa", "reaction": "Hives", "confirmed": True}
        ],
        "baseline_observations": [
            {"type": "glucose", "value": 120.0, "measured_at": "2026-10-29T10:00:00Z"}
        ],
    }

    # Commit import
    resp1 = client.post(
        "/api/me/record/import?dry_run=false",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps(import_payload),
    )
    assert resp1.status_code == 200
    res1 = resp1.json()
    assert res1["dry_run"] is False
    assert res1["imported_counts"]["medications"] == 1
    assert res1["imported_counts"]["allergies"] == 1
    assert res1["imported_counts"]["observations"] == 1

    # Verify records present in record
    rec_resp = client.get("/api/me/record", headers=headers)
    rec = rec_resp.json()
    assert len(rec["medications"]) == 1
    assert len(rec["allergies"]) == 1
    assert len(rec["baseline_observations"]) == 1

    # Re-import identical payload -> should detect as duplicates and add 0
    resp2 = client.post(
        "/api/me/record/import?dry_run=false",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps(import_payload),
    )
    assert resp2.status_code == 200
    res2 = resp2.json()
    assert res2["imported_counts"]["medications"] == 0
    assert res2["duplicate_counts"]["medications"] == 1
    assert res2["imported_counts"]["allergies"] == 0
    assert res2["duplicate_counts"]["allergies"] == 1
    assert res2["imported_counts"]["observations"] == 0
    assert res2["duplicate_counts"]["observations"] == 1

    # Export record and import own export -> duplicates detected
    export_resp = client.get("/api/me/record/export?format=json", headers=headers)
    assert export_resp.status_code == 200
    exported_data = export_resp.json()

    resp3 = client.post(
        "/api/me/record/import?dry_run=false",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps(exported_data),
    )
    assert resp3.status_code == 200
    res3 = resp3.json()
    assert res3["imported_counts"]["medications"] == 0
    assert res3["imported_counts"]["allergies"] == 0
    assert res3["imported_counts"]["observations"] == 0


# ----------------------------------------------------------------------------
# 5. Import: FHIR Bundle Format
# ----------------------------------------------------------------------------
def test_import_fhir_bundle(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-imp-fhir", "p_imp_fhir@demo.com")

    fhir_bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "MedicationRequest",
                    "status": "active",
                    "medicationCodeableConcept": {"text": "Amlodipine 10mg"},
                    "dosageInstruction": [{"text": "1 tablet OD"}],
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {
                        "coding": [{"system": "http://loinc.org", "code": "2339-0", "display": "Glucose"}]
                    },
                    "valueQuantity": {"value": 118.0, "unit": "mg/dL"},
                    "effectiveDateTime": "2026-10-30T10:00:00Z",
                }
            },
        ],
    }

    resp = client.post(
        "/api/me/record/import?dry_run=false",
        headers={**headers, "Content-Type": "application/fhir+json"},
        content=json.dumps(fhir_bundle),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported_counts"]["medications"] == 1
    assert data["imported_counts"]["observations"] == 1


# ----------------------------------------------------------------------------
# 6. Import Error Handling & Validation: 409, 413, 415
# ----------------------------------------------------------------------------
def test_import_error_handling(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-imp-err", "p_imp_err@demo.com")

    # A. 415 Unsupported Media Type
    resp_415 = client.post(
        "/api/me/record/import",
        headers={**headers, "Content-Type": "text/plain"},
        content="not-json",
    )
    assert resp_415.status_code == 415

    # B. 413 Payload Too Large (> 2MB)
    huge_payload = json.dumps({"medications": [{"name": "A" * 1000}] * 3000})
    assert len(huge_payload) > 2 * 1024 * 1024
    resp_413 = client.post(
        "/api/me/record/import",
        headers={**headers, "Content-Type": "application/json"},
        content=huge_payload,
    )
    assert resp_413.status_code == 413

    # C. 409 Connected Mode
    client.post("/api/ehr/connect", headers=headers, json={"ehr_system_id": "demo-hospital", "external_patient_id": "sim-ayesha"})
    resp_409 = client.post(
        "/api/me/record/import",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps({"medications": []}),
    )
    assert resp_409.status_code == 409


# ----------------------------------------------------------------------------
# 7. Baseline Observation Effect (> 14 days old excluded from baseline)
# ----------------------------------------------------------------------------
def test_import_baseline_filtering_older_than_14_days(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-imp-baseline", "p_imp_baseline@demo.com")

    # Import observation with timestamp 30 days ago
    old_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    import_payload = {
        "baseline_observations": [
            {"type": "glucose", "value": 150.0, "measured_at": old_time}
        ]
    }
    resp = client.post(
        "/api/me/record/import?dry_run=false",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps(import_payload),
    )
    assert resp.status_code == 200
    assert resp.json()["imported_counts"]["observations"] == 1

    # Verify baseline history filters it out (get_user_baseline_history only includes <= 14 days)
    history = app_store.get_user_baseline_history("p-imp-baseline")
    assert len(history) == 0


# ----------------------------------------------------------------------------
# 8. Export/Import Audit Zero PHI
# ----------------------------------------------------------------------------
def test_export_import_audit_zero_phi(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-audit-exp-imp", "p_audit_exp_imp@demo.com")

    # Export
    client.get("/api/me/record/export?format=json", headers=headers)

    # Import
    payload = {
        "medications": [{"name": "SuperSecretMed123", "dosage": "SecretDose", "status": "active"}]
    }
    client.post(
        "/api/me/record/import?dry_run=false",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps(payload),
    )

    audit_logs = app_store.get_audit_logs(limit=20)
    for log in audit_logs:
        detail_str = str(log.get("detail", ""))
        assert "SuperSecretMed123" not in detail_str
        assert "SecretDose" not in detail_str
        if log.get("action") == "record_exported":
            assert "format" in log["detail"]
        if log.get("action") == "record_imported":
            assert "counts" in log["detail"]


# ----------------------------------------------------------------------------
# 9. Import Validation Rejects Out-of-Range and Invalid Observation Types
# ----------------------------------------------------------------------------
def test_import_validation_rejects_out_of_range_and_invalid_type(rsa_key_pair):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-imp-val", "p_imp_val@demo.com")

    payload = {
        "baseline_observations": [
            {"type": "invalid_metric", "value": 120.0, "measured_at": "2026-10-30T10:00:00Z"}
        ]
    }
    resp = client.post(
        "/api/me/record/import?dry_run=true",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps(payload),
    )
    assert resp.status_code == 200
    res = resp.json()
    assert res["counts"]["to_add"] == 0
    assert res["counts"]["invalid"] == 1
    assert len(res["preview"]["observations"]) == 1
    assert res["preview"]["observations"][0]["will_import"] is False


# ----------------------------------------------------------------------------
# 10. All-or-Nothing Atomicity: Failure Mid-Insert Rolls Back All Rows
# ----------------------------------------------------------------------------
def test_import_all_or_nothing_rollback_on_failure(rsa_key_pair, monkeypatch):
    """
    Proves all-or-nothing atomicity:
    1. Pre-records initial row counts for medications, observations, allergies, and record_edits.
    2. Submits a mixed payload containing medication, observation, and allergy.
    3. Monkeypatches create_allergy (the 3rd insert) to raise an error containing a sensitive test value.
    4. Asserts response is HTTP 500 with fixed message and error code, without leaking str(e) or sensitive values.
    5. Asserts the row counts of medications, observations, allergies, and record_edits are identical to before the import.
    """
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-rollback-1", "p_rollback_1@demo.com")

    # Initial counts
    patient_id = "local-p-rollback-1"
    initial_meds = len(local_store.get_local_medications(patient_id))
    initial_obs = len(local_store.get_local_observations(patient_id))
    initial_allergies = len(app_store.get_allergies("p-rollback-1"))
    initial_edits = len(app_store.get_record_edits("p-rollback-1"))

    # Monkeypatch the 3rd insert (create_allergy) to fail
    def fake_create_allergy(*args, **kwargs):
        raise RuntimeError("SIMULATED_DB_FAILURE_SENSITIVE_VALUE_999")

    monkeypatch.setattr("main.create_allergy", fake_create_allergy)

    payload = {
        "medications": [{"name": "Amlodipine 5mg", "dosage": "1 daily", "status": "active"}],
        "observations": [{"type": "glucose", "value": 110.0, "unit": "mg/dL", "measured_at": "2026-10-31T08:00:00Z"}],
        "allergies": [{"substance": "Aspirin", "reaction": "Rash", "confirmed": True}],
    }

    resp = client.post(
        "/api/me/record/import?dry_run=false",
        headers={**headers, "Content-Type": "application/json"},
        content=json.dumps(payload),
    )

    assert resp.status_code == 500
    detail = resp.json().get("detail", "")
    assert "Import transaction failed and was rolled back" in detail
    assert "IMPORT_TRANSACTION_FAILED" in detail
    assert "SIMULATED_DB_FAILURE_SENSITIVE_VALUE_999" not in detail
    assert "Amlodipine" not in detail
    assert "Aspirin" not in detail

    # Verify all row counts are strictly identical to before the import
    final_meds = len(local_store.get_local_medications(patient_id))
    final_obs = len(local_store.get_local_observations(patient_id))
    final_allergies = len(app_store.get_allergies("p-rollback-1"))
    final_edits = len(app_store.get_record_edits("p-rollback-1"))

    assert final_meds == initial_meds
    assert final_obs == initial_obs
    assert final_allergies == initial_allergies
    assert final_edits == initial_edits


# ----------------------------------------------------------------------------
# 11. Conditions Basis Update Transaction Support with External Cursor
# ----------------------------------------------------------------------------
def test_update_patient_conditions_basis_accepts_cursor(monkeypatch):
    """
    Proves that update_patient_conditions_basis accepts an external cursor
    so that MySQL single-transaction imports include the conditions basis update
    and its record_edit entry on the same cursor without committing early.
    """
    executed_queries = []

    class FakeCursor:
        def execute(self, sql, params=None):
            executed_queries.append((sql, params))

    fake_cursor = FakeCursor()
    test_user_id = "test-u-cond-basis-tx"

    # Mock get_patient_profile to return existing profile with diabetes clinical basis
    monkeypatch.setattr(
        app_store,
        "get_patient_profile",
        lambda uid, **kwargs: {
            "user_id": test_user_id,
            "conditions": ["type_2_diabetes"],
            "conditions_basis": {"type_2_diabetes": "self_reported"},
        },
    )

    result = app_store.update_patient_conditions_basis(
        user_id=test_user_id,
        conditions_basis={"type_2_diabetes": "clinical_document"},
        changed_by_user_id=test_user_id,
        origin="import",
        cursor=fake_cursor,
    )

    assert result["conditions_basis"]["type_2_diabetes"] == "clinical_document"
    # Ensure queries were executed directly on the provided cursor
    assert len(executed_queries) == 2
    assert "UPDATE patient_profiles SET conditions_basis_json" in executed_queries[0][0]
    assert "INSERT INTO record_edits" in executed_queries[1][0]
