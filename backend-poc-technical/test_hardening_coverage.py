"""
Iteration 2 Day 7 Hardening & Coverage Expansion Test Suite.

Targeting least-covered non-safety modules:
1. data_sources/fhir_adapter.py (missing units, incomplete BP panels, unknown LOINC)
2. data_sources/medication_scope.py (status filtering, deduplication, 8-cap, ordering)
3. auth/firebase_verify.py (error paths: expired, wrong audience, missing kid, algorithm)
4. data_sources/local_store.py (boundary queries, non-existent patients, CRUD integrity)
5. main.py (input validation and HTTP error response contracts)
"""
import jwt
import pytest
from auth.firebase_verify import AuthError, _parse_max_age, verify_firebase_token
from cryptography.hazmat.primitives.asymmetric import rsa
from data_sources.fhir_adapter import (
    _convert_unit_and_value,
    fhir_to_normalized_observations,
)
from data_sources.local_store import (
    add_local_medication,
    add_local_observation,
    add_local_patient_if_missing,
    get_local_medication_by_id,
    get_local_medications,
    get_local_observation_by_id,
    get_local_observations,
    get_local_patient,
)
from data_sources.medication_scope import (
    DEFAULT_MEDICATION_LIMIT,
    select_chronic_care_medications,
)
from data_sources.models import NormalizedMedication
from fastapi.testclient import TestClient
from main import app

# ---------------------------------------------------------------------------
# 1. MEDICATION SCOPE TESTS
# ---------------------------------------------------------------------------

def test_medication_scope_status_filtering():
    """Verify that non-active medications (stopped, on-hold, cancelled) are filtered out."""
    meds = [
        {"medication_name": "Metformin 500mg", "status": "active", "timestamp": "2026-01-01"},
        {"medication_name": "Lisinopril 10mg", "status": "stopped", "timestamp": "2026-01-01"},
        {"medication_name": "Amlodipine 5mg", "status": "on-hold", "timestamp": "2026-01-01"},
        {"medication_name": "Glimepiride 2mg", "status": "entered-in-error", "timestamp": "2026-01-01"},
    ]
    res = select_chronic_care_medications(meds)
    assert len(res) == 1
    assert res[0]["medication_name"] == "Metformin 500mg"


def test_medication_scope_irrelevant_medication_filtering():
    """Verify that medications unrelated to diabetes or hypertension are excluded."""
    meds = [
        {"medication_name": "Metformin 500mg", "status": "active"},
        {"medication_name": "Amoxicillin 500mg", "status": "active"},
        {"medication_name": "Ibuprofen 400mg", "status": "active"},
        {"medication_name": "Atorvastatin 20mg", "status": "active"},
    ]
    res = select_chronic_care_medications(meds)
    assert len(res) == 1
    assert res[0]["medication_name"] == "Metformin 500mg"


def test_medication_scope_deduplication_by_canonical_name():
    """Verify that duplicate entries of the same medication are deduplicated."""
    meds = [
        {"medication_name": "Metformin 500mg Tablet", "status": "active", "timestamp": "2026-02-01"},
        {"medication_name": "metformin 500mg tablet", "status": "active", "timestamp": "2026-01-01"},
        {"medication_name": "Amlodipine 5mg", "status": "active", "timestamp": "2026-02-01"},
    ]
    res = select_chronic_care_medications(meds)
    assert len(res) == 2
    names = [m["medication_name"] for m in res]
    assert "Amlodipine 5mg" in names
    assert any("Metformin" in n for n in names)


def test_medication_scope_timestamp_priority():
    """Verify that more recent timestamps are prioritized during deduplication."""
    meds = [
        {"medication_name": "Metformin 500mg", "status": "active", "timestamp": "2026-01-10"},
        {"medication_name": "Metformin 500mg", "status": "active", "timestamp": "2026-03-15"},
    ]
    res = select_chronic_care_medications(meds)
    assert len(res) == 1
    assert res[0]["timestamp"] == "2026-03-15"


def test_medication_scope_strict_cap_limit():
    """Verify that the chronic care filter caps results at limit (default 8)."""
    med_names = [
        "Metformin", "Glimepiride", "Gliclazide", "Sitagliptin",
        "Empagliflozin", "Lisinopril", "Amlodipine", "Losartan",
        "Valsartan", "Atenolol", "Hydrochlorothiazide"
    ]
    meds = [{"medication_name": f"{name} 10mg", "status": "active", "timestamp": "2026-01-01"} for name in med_names]
    res = select_chronic_care_medications(meds, limit=DEFAULT_MEDICATION_LIMIT)
    assert len(res) == 8


def test_medication_scope_custom_limit():
    """Verify custom limit parameter overrides default cap."""
    meds = [
        {"medication_name": "Metformin 500mg", "status": "active"},
        {"medication_name": "Lisinopril 10mg", "status": "active"},
        {"medication_name": "Amlodipine 5mg", "status": "active"},
    ]
    res = select_chronic_care_medications(meds, limit=2)
    assert len(res) == 2


def test_medication_scope_empty_input():
    """Verify that an empty list returns an empty list safely."""
    assert select_chronic_care_medications([]) == []


def test_medication_scope_normalized_medication_objects():
    """Verify that NormalizedMedication instances are supported alongside dicts."""
    med = NormalizedMedication(
        patient_id="PAT-1",
        medication_name="Lisinopril 10mg",
        status="active",
        dosage="1 tab daily",
        timestamp="2026-01-01T00:00:00Z",
        source="local",
        source_record_id="rec-1",
    )
    res = select_chronic_care_medications([med])
    assert len(res) == 1
    assert res[0].medication_name == "Lisinopril 10mg"


# ---------------------------------------------------------------------------
# 2. FHIR ADAPTER TESTS
# ---------------------------------------------------------------------------

def test_fhir_adapter_blood_pressure_panel_systolic_only():
    """Verify BP panel observation when diastolic component is absent."""
    raw_obs = [{
        "resourceType": "Observation",
        "id": "bp-sys-only",
        "code": {"coding": [{"code": "85354-9", "display": "Blood Pressure"}]},
        "effectiveDateTime": "2026-01-01T10:00:00Z",
        "component": [
            {
                "code": {"coding": [{"code": "8480-6", "display": "Systolic BP"}]},
                "valueQuantity": {"value": 130, "unit": "mmHg"}
            }
        ]
    }]
    norm = fhir_to_normalized_observations(raw_obs, patient_id="P1")
    assert len(norm) == 1
    assert norm[0].observation_type == "blood_pressure_systolic"
    assert norm[0].value == 130.0
    assert norm[0].unit == "mmHg"


def test_fhir_adapter_blood_pressure_panel_diastolic_only():
    """Verify BP panel observation when systolic component is absent."""
    raw_obs = [{
        "resourceType": "Observation",
        "id": "bp-dia-only",
        "code": {"coding": [{"code": "85354-9", "display": "Blood Pressure"}]},
        "effectiveDateTime": "2026-01-01T10:00:00Z",
        "component": [
            {
                "code": {"coding": [{"code": "8462-4", "display": "Diastolic BP"}]},
                "valueQuantity": {"value": 85, "unit": "mmHg"}
            }
        ]
    }]
    norm = fhir_to_normalized_observations(raw_obs, patient_id="P1")
    assert len(norm) == 1
    assert norm[0].observation_type == "blood_pressure_diastolic"
    assert norm[0].value == 85.0
    assert norm[0].unit == "mmHg"


def test_fhir_adapter_blood_pressure_component_invalid_value():
    """Verify non-numeric BP component value is ignored without crashing."""
    raw_obs = [{
        "resourceType": "Observation",
        "id": "bp-corrupt",
        "code": {"coding": [{"code": "85354-9", "display": "Blood Pressure"}]},
        "effectiveDateTime": "2026-01-01T10:00:00Z",
        "component": [
            {
                "code": {"coding": [{"code": "8480-6", "display": "Systolic BP"}]},
                "valueQuantity": {"value": "invalid_number", "unit": "mmHg"}
            }
        ]
    }]
    norm = fhir_to_normalized_observations(raw_obs, patient_id="P1")
    assert len(norm) == 0


def test_fhir_adapter_unknown_loinc_falls_back_to_text():
    """Verify unknown LOINC with 'glucose' in display falls back to glucose type."""
    raw_obs = [{
        "resourceType": "Observation",
        "id": "obs-custom-gluc",
        "code": {"coding": [{"code": "99999-9", "display": "Blood Glucose Level"}]},
        "effectiveDateTime": "2026-01-01T10:00:00Z",
        "valueQuantity": {"value": 115, "unit": "mg/dL"}
    }]
    norm = fhir_to_normalized_observations(raw_obs, patient_id="P1")
    assert len(norm) == 1
    assert norm[0].observation_type == "glucose"
    assert norm[0].value == 115.0


def test_fhir_adapter_unknown_loinc_and_text_snake_case():
    """Verify completely unmapped LOINC falls back to sanitized snake_case string."""
    raw_obs = [{
        "resourceType": "Observation",
        "id": "obs-unmapped",
        "code": {"coding": [{"code": "88888-8", "display": "Total Cholesterol / HDL Ratio"}]},
        "effectiveDateTime": "2026-01-01T10:00:00Z",
        "valueQuantity": {"value": 4.2, "unit": "ratio"}
    }]
    norm = fhir_to_normalized_observations(raw_obs, patient_id="P1")
    assert len(norm) == 1
    assert norm[0].observation_type == "total_cholesterol_hdl_ratio"
    assert norm[0].value == 4.2


def test_fhir_adapter_glucose_conversion_mmol_to_mgdl():
    """Verify glucose in mmol/L is converted to mg/dL (* 18.016)."""
    val, unit = _convert_unit_and_value("glucose", 10.0, "mmol/L")
    assert unit == "mg/dL"
    assert val == 180.2


def test_fhir_adapter_glucose_mgdl_preservation():
    """Verify glucose in mg/dL is preserved."""
    val, unit = _convert_unit_and_value("glucose", 140.0, "mg/dL")
    assert unit == "mg/dL"
    assert val == 140.0


def test_fhir_adapter_hba1c_conversion_mmol_mol_to_percent():
    """Verify HbA1c in mmol/mol is converted to % using IFCC formula."""
    val, unit = _convert_unit_and_value("hba1c", 53.0, "mmol/mol")
    assert unit == "%"
    assert val == 7.0


def test_fhir_adapter_weight_conversion_lbs_to_kg():
    """Verify weight in lbs is converted to kg."""
    val, unit = _convert_unit_and_value("weight", 154.32, "lbs")
    assert unit == "kg"
    assert val == 70.0


def test_fhir_adapter_unrecognized_unit_preservation():
    """Verify unmapped unit for non-standard lab is preserved as-is."""
    val, unit = _convert_unit_and_value("serum_creatinine", 1.2, "mg/dL")
    assert unit == "mg/dL"
    assert val == 1.2


# ---------------------------------------------------------------------------
# 3. AUTH & FIREBASE VERIFY ERROR PATH TESTS
# ---------------------------------------------------------------------------

def test_auth_parse_max_age_clamping():
    """Verify Cache-Control max-age header parser clamps between 300 and 86400s."""
    assert _parse_max_age("max-age=100") == 300       # Clamped to min 5m
    assert _parse_max_age("max-age=100000") == 86400  # Clamped to max 24h
    assert _parse_max_age("max-age=3600") == 3600     # Preserved
    assert _parse_max_age(None) == 3600               # Default
    assert _parse_max_age("invalid-header") == 3600   # Fallback


def test_auth_verify_token_missing_project_id(monkeypatch):
    """Verify 503 AuthError when FIREBASE_PROJECT_ID is not configured."""
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    with pytest.raises(AuthError) as exc_info:
        verify_firebase_token("fake.token.string", project_id=None)
    assert exc_info.value.status_code == 503
    assert "not configured" in exc_info.value.message


def test_auth_verify_token_empty_or_non_string():
    """Verify 401 AuthError on empty or invalid token type."""
    with pytest.raises(AuthError) as exc_info:
        verify_firebase_token("", project_id="test-proj")
    assert exc_info.value.status_code == 401

    with pytest.raises(AuthError) as exc_info2:
        verify_firebase_token(None, project_id="test-proj")  # type: ignore
    assert exc_info2.value.status_code == 401


def test_auth_verify_token_invalid_jwt_format():
    """Verify 401 AuthError when token is not a valid JWT."""
    with pytest.raises(AuthError) as exc_info:
        verify_firebase_token("not-a-valid-jwt", project_id="test-proj")
    assert exc_info.value.status_code == 401


def test_auth_verify_token_disallowed_algorithm():
    """Verify 401 AuthError when token uses symmetric HS256 instead of RS256."""
    token = jwt.encode({"sub": "user1"}, "super-secret-key-32-bytes-long!!!", algorithm="HS256")
    with pytest.raises(AuthError) as exc_info:
        verify_firebase_token(token, project_id="test-proj")
    assert exc_info.value.status_code == 401


def test_auth_verify_token_missing_kid_header():
    """Verify 401 AuthError when RS256 token lacks 'kid' header."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {"sub": "user1", "iss": "https://securetoken.google.com/test-proj", "aud": "test-proj"},
        private_key,
        algorithm="RS256"
        # headers={"kid": ...} omitted
    )
    with pytest.raises(AuthError) as exc_info:
        verify_firebase_token(token, project_id="test-proj")
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 4. LOCAL STORE BOUNDARY & CRUD TESTS
# ---------------------------------------------------------------------------

def test_local_store_get_nonexistent_patient():
    """Verify get_local_patient returns None for unknown patient ID."""
    p = get_local_patient("NON-EXISTENT-ID-999")
    assert p is None


def test_local_store_get_observations_empty_patient():
    """Verify get_local_observations returns empty list for unknown patient."""
    obs = get_local_observations("NON-EXISTENT-ID-999")
    assert obs == []


def test_local_store_get_medications_empty_patient():
    """Verify get_local_medications returns empty list for unknown patient."""
    meds = get_local_medications("NON-EXISTENT-ID-999")
    assert meds == []


def test_local_store_insert_and_retrieve_observation():
    """Verify custom observation insertion and retrieval round-trip."""
    obs_id = "test-obs-roundtrip-hardening"
    patient_id = "LOCAL-PATIENT-001"
    add_local_observation(
        id=obs_id,
        patient_id=patient_id,
        observation_type="glucose",
        value=155.0,
        unit="mg/dL",
        timestamp="2026-11-01T12:00:00Z",
        source="unit_test",
        origin="test"
    )
    obs = get_local_observation_by_id(obs_id)
    assert obs is not None
    assert obs["value"] == 155.0
    assert obs["unit"] == "mg/dL"


def test_local_store_insert_and_retrieve_medication():
    """Verify custom medication insertion and retrieval round-trip."""
    med_id = "test-med-roundtrip-hardening"
    patient_id = "LOCAL-PATIENT-001"
    add_local_medication(
        id=med_id,
        patient_id=patient_id,
        medication_name="Empagliflozin 10mg",
        status="active",
        dosage="1 tab daily",
        timestamp="2026-11-01T12:00:00Z",
        source="unit_test",
        origin="test"
    )
    med = get_local_medication_by_id(med_id)
    assert med is not None
    assert med["medication_name"] == "Empagliflozin 10mg"
    assert med["status"] == "active"


def test_local_store_add_patient_if_missing():
    """Verify add_local_patient_if_missing creates a new patient record."""
    test_pid = "LOCAL-PATIENT-HARDENING-999"
    add_local_patient_if_missing(
        patient_id=test_pid,
        name="Hardening Test Patient",
        date_of_birth="1980-05-15"
    )
    p = get_local_patient(test_pid)
    assert p is not None
    assert p["name"] == "Hardening Test Patient"
    assert p["date_of_birth"] == "1980-05-15"


# ---------------------------------------------------------------------------
# 5. MAIN API VALIDATION & ERROR RESPONSE CONTRACTS
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    from main import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "LOCAL-PATIENT-001",
        "role": "patient",
        "email": "patient@demo.com",
    }
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_api_profile_invalid_height_under_50(api_client):
    """Verify height < 50cm is rejected with HTTP 422 Unprocessable Content."""
    res = api_client.put("/api/me/profile", json={"height_cm": 40.0})
    assert res.status_code == 422


def test_api_profile_invalid_height_over_250(api_client):
    """Verify height > 250cm is rejected with HTTP 422 Unprocessable Content."""
    res = api_client.put("/api/me/profile", json={"height_cm": 260.0})
    assert res.status_code == 422


def test_api_profile_invalid_weight_under_20(api_client):
    """Verify weight < 20kg is rejected with HTTP 422 Unprocessable Content."""
    res = api_client.put("/api/me/profile", json={"weight_kg": 15.0})
    assert res.status_code == 422


def test_api_profile_invalid_weight_over_400(api_client):
    """Verify weight > 400kg is rejected with HTTP 422 Unprocessable Content."""
    res = api_client.put("/api/me/profile", json={"weight_kg": 450.0})
    assert res.status_code == 422


def test_api_profile_empty_conditions_list(api_client):
    """Verify empty conditions list is rejected with HTTP 422."""
    res = api_client.put("/api/me/profile", json={"conditions": []})
    assert res.status_code == 422


def test_api_profile_disallowed_condition(api_client):
    """Verify unsupported condition (e.g. asthma) is rejected with HTTP 422."""
    res = api_client.put("/api/me/profile", json={"conditions": ["asthma"]})
    assert res.status_code == 422


def test_api_profile_disallowed_language(api_client):
    """Verify unsupported language (e.g. french) is rejected with HTTP 422."""
    res = api_client.put("/api/me/profile", json={"language": "french"})
    assert res.status_code == 422


def test_api_profile_disallowed_sex_at_birth(api_client):
    """Verify invalid sex_at_birth string is rejected with HTTP 422."""
    res = api_client.put("/api/me/profile", json={"sex_at_birth": "unknown_option"})
    assert res.status_code == 422


def test_api_profile_disallowed_pregnancy_status(api_client):
    """Verify invalid pregnancy_status string is rejected with HTTP 422."""
    res = api_client.put("/api/me/profile", json={"pregnancy_status": "maybe"})
    assert res.status_code == 422
