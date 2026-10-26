"""
Hermetic test suite for EHR Test Patients, Synthea gap fill, Doctor on Record,
and EHR Allergies (Day 1 Part G).
"""

import os
import re
import json
import datetime
from typing import Dict, Any, List
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
from data_sources import fhir_sim
from data_sources import fhir_adapter
from data_sources import fhir_client
from data_sources import ehr_test_patients


TEST_PROJECT_ID = "test-chroniccare-ai"
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
    test_db_path = str(tmp_path / "test_ehr_app_store.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")

    import time
    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)
    yield test_db_path


def create_test_token(rsa_key_pair, sub: str, email: str, role: str = "patient") -> str:
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    payload = {
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "aud": TEST_PROJECT_ID,
        "auth_time": now,
        "user_id": sub,
        "sub": sub,
        "iat": now,
        "exp": now + 3600,
        "email": email,
        "email_verified": True,
        "role": role,
    }
    pem_bytes = rsa_key_pair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, pem_bytes, algorithm="RS256", headers={"kid": TEST_KID})


def auth_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# 1. SINGLE PATIENT LIST MODULE IS THE ONLY SOURCE
# =============================================================================

def test_single_patient_list_is_only_source():
    """Grep-style test: verify main.py and app_store.py import suggested/sample lists

    from data_sources.ehr_test_patients rather than declaring their own duplicate literals.
    """
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(backend_dir, "main.py")
    app_store_py = os.path.join(backend_dir, "data_sources", "app_store.py")

    with open(main_py, "r", encoding="utf-8") as f:
        main_content = f.read()

    with open(app_store_py, "r", encoding="utf-8") as f:
        app_store_content = f.read()

    # Assert both import from ehr_test_patients
    assert "ehr_test_patients" in main_content, "main.py must import from ehr_test_patients"
    assert "ehr_test_patients" in app_store_content, "app_store.py must import from ehr_test_patients"

    # Assert neither defines duplicate literal lists of public sandbox IDs
    sandbox_id_1 = "d48ac962-78c6-46cf-ba33-a24771bfa0e4"
    sandbox_id_2 = "b85d7e00-3690-4e2a-87a0-f3d2dfc908b3"

    assert sandbox_id_1 not in main_content, f"main.py should not hardcode {sandbox_id_1}"
    assert sandbox_id_1 not in app_store_content, f"app_store.py should not hardcode {sandbox_id_1}"
    assert sandbox_id_2 not in main_content, f"main.py should not hardcode {sandbox_id_2}"
    assert sandbox_id_2 not in app_store_content, f"app_store.py should not hardcode {sandbox_id_2}"


# =============================================================================
# 2. /api/ehr/systems RESPONSE IS UNCHANGED FOR EXISTING SYSTEMS
# =============================================================================

def test_api_ehr_systems_unchanged_for_existing(client):
    res = client.get("/api/ehr/systems")
    assert res.status_code == 200
    systems = res.json()
    assert len(systems) >= 2

    sys_map = {s["ehr_system_id"]: s for s in systems}
    assert "demo-hospital" in sys_map
    assert "smart-sandbox" in sys_map

    demo = sys_map["demo-hospital"]
    assert demo["display_name"] == "Demo hospital (simulated, synthetic data)"
    assert demo["kind"] == "simulated"

    demo_sample_ids = [p["id"] for p in demo["sample_patients"]]
    expected_demo_ids = ["sim-ayesha", "sim-bilal", "sim-sana", "sim-imran", "sim-newpatient"]
    for eid in expected_demo_ids:
        assert eid in demo_sample_ids, f"Expected {eid} in demo-hospital sample patients"

    smart = sys_map["smart-sandbox"]
    assert smart["display_name"] == "SMART Health IT Sandbox"
    assert smart["kind"] == "public_sandbox"
    expected_smart_ids = [
        "d48ac962-78c6-46cf-ba33-a24771bfa0e4",
        "b85d7e00-3690-4e2a-87a0-f3d2dfc908b3",
        "4551370c-c3eb-4164-a2ff-b528f73a4e0f",
    ]
    assert smart["suggested_patient_ids"] == expected_smart_ids


# =============================================================================
# 3. SYNTHEA FIXTURES LOAD, TIMESTAMPS RECENT, OBSERVATIONS NORMALIZE
# =============================================================================

def test_synthea_fixtures_valid_and_recent():
    fixtures_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data_sources",
        "fhir_sim_fixtures"
    )
    assert os.path.isdir(fixtures_dir), "fhir_sim_fixtures directory must exist"

    fixture_files = [f for f in os.listdir(fixtures_dir) if f.startswith("sim-syn-") and f.endswith(".json")]
    assert len(fixture_files) >= 3, f"Expected at least 3 Synthea fixtures, found {len(fixture_files)}"

    now = datetime.datetime.now(datetime.timezone.utc)
    thirty_days_ago = now - datetime.timedelta(days=30)

    for fname in fixture_files:
        fpath = os.path.join(fixtures_dir, fname)
        file_size = os.path.getsize(fpath)
        assert file_size < 50 * 1024, f"{fname} is {file_size} bytes, must be under 50 KB"

        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "patient" in data, f"{fname} missing patient"
        assert "observations" in data, f"{fname} missing observations"
        assert "medications" in data, f"{fname} missing medications"
        assert "practitioner" in data, f"{fname} missing practitioner"

        obs_list = data["observations"]
        assert len(obs_list) > 0, f"{fname} has no observations"

        for obs in obs_list:
            dt_str = obs.get("effectiveDateTime")
            assert dt_str is not None, f"Observation {obs.get('id')} in {fname} missing effectiveDateTime"
            obs_dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            assert obs_dt >= thirty_days_ago, f"Observation {obs.get('id')} is older than 30 days ({dt_str})"
            assert obs_dt <= now + datetime.timedelta(minutes=5), f"Observation {obs.get('id')} is in future ({dt_str})"

        # Verify normalization through fhir_adapter
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [{"resource": o} for o in obs_list]
        }
        normalized = fhir_adapter.fhir_to_normalized_observations(bundle)
        assert len(normalized) > 0, f"Observations in {fname} failed to normalize"
        for norm_obs in normalized:
            assert norm_obs.observation_type in {"glucose", "blood_pressure_systolic", "blood_pressure_diastolic", "hba1c"}
            assert norm_obs.value > 0
            assert norm_obs.unit in {"mg/dL", "mmHg", "%"}
            assert norm_obs.source == "fhir"


# =============================================================================
# 4. PRACTITIONER FOUND FOR EVERY SIM PATIENT EXCEPT sim-newpatient
# =============================================================================

def test_practitioner_found_for_all_sim_patients_except_newpatient():
    sim_patients_with_practitioner = [
        "sim-ayesha",
        "sim-bilal",
        "sim-sana",
        "sim-imran",
        "sim-syn-recent-t2d-htn",
        "sim-syn-recent-t2d-insulin",
        "sim-syn-recent-htn-multidrug",
        "sim-syn-recent-geriatric",
    ]

    for pid in sim_patients_with_practitioner:
        prac = fhir_client.get_fhir_practitioner_for_patient(pid, base_url="sim://demo")
        assert prac is not None, f"Expected practitioner for {pid}"
        assert "name" in prac and len(prac["name"]) > 0
        assert prac["source"] in {"ehr_general_practitioner", "ehr_encounter"}

    # sim-newpatient has no practitioner
    prac_new = fhir_client.get_fhir_practitioner_for_patient("sim-newpatient", base_url="sim://demo")
    assert prac_new is None, "sim-newpatient should have no practitioner (None)"


# =============================================================================
# 5. ALLERGIES NORMALIZE AND ENTERED-IN-ERROR IS EXCLUDED
# =============================================================================

def test_allergies_normalize_and_exclude_entered_in_error():
    bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": "alg-1",
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "verificationStatus": {"coding": [{"code": "confirmed"}]},
                    "criticality": "high",
                    "code": {"text": "Penicillin G"},
                    "reaction": [{"manifestation": [{"text": "Hives"}]}],
                }
            },
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": "alg-2",
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "verificationStatus": {"coding": [{"code": "entered-in-error"}]},
                    "criticality": "low",
                    "code": {"text": "Aspirin"},
                }
            },
            {
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": "alg-3",
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "verificationStatus": {"coding": [{"code": "unconfirmed"}]},
                    "criticality": "medium",
                    "code": {"text": "Sulfa drugs"},
                }
            }
        ]
    }

    normalized = fhir_adapter.fhir_to_normalized_allergies(bundle)
    assert len(normalized) == 2, "entered-in-error allergy must be excluded"

    substances = {a["substance"] for a in normalized}
    assert "Penicillin G" in substances
    assert "Sulfa drugs" in substances
    assert "Aspirin" not in substances

    for a in normalized:
        assert a["origin"] == "ehr"
        assert a["trust"] == "high"


# =============================================================================
# 6. E2E CONNECTED CHECK-IN ON EACH NEW sim-syn PATIENT
# =============================================================================

def _setup_patient_helper(client, rsa_key_pair, uid, email, conditions):
    tok = create_test_token(rsa_key_pair, sub=uid, email=email)
    h = auth_header(tok)
    client.post("/api/auth/session", headers=h)
    client.post("/api/me/consent", json={"granted": True}, headers=h)
    client.post("/api/me/provider-notification-consent", json={"granted": True}, headers=h)
    client.put(
        "/api/me/profile",
        json={"conditions": conditions, "date_of_birth": "1975-01-01", "inclusion_confirmed": True, "on_insulin_or_sulfonylurea": False},
        headers=h
    )
    return h


def _drive_checkin(client, cid, headers):
    for _ in range(25):
        ans_res = client.post(f"/api/checkins/{cid}/answer", headers=headers, json={"answer": "feeling fine"})
        data = ans_res.json()
        if data.get("complete"):
            break
        step = (data.get("step") or "").lower()
        q = (data.get("question") or "").lower()
        if "glucose" in step or "sugar" in q or "glucose" in q:
            ans = "140"
        elif "bp" in step or "pressure" in q:
            ans = "125/80"
        elif "symptom" in step or "symptom" in q:
            ans = "none"
        else:
            ans = "yes"
        ans_res = client.post(f"/api/checkins/{cid}/answer", headers=headers, json={"answer": ans})
        if ans_res.json().get("complete"):
            break


@pytest.mark.parametrize("syn_patient_id", [
    "sim-syn-recent-t2d-htn",
    "sim-syn-recent-t2d-insulin",
    "sim-syn-recent-htn-multidrug",
    "sim-syn-recent-geriatric",
])
def test_e2e_connected_checkin_sim_syn_patients(client, rsa_key_pair, syn_patient_id):
    """End-to-end checkin test for each new Synthea fixture patient."""
    h = _setup_patient_helper(
        client,
        rsa_key_pair,
        f"uid-{syn_patient_id}",
        f"{syn_patient_id}@demo.com",
        ["diabetes", "hypertension"]
    )

    # Connect to simulated hospital
    conn_res = client.post(
        "/api/ehr/connect",
        json={"ehr_system_id": "demo-hospital", "external_patient_id": syn_patient_id},
        headers=h
    )
    assert conn_res.status_code == 200, f"Failed to connect {syn_patient_id}: {conn_res.text}"

    # Start checkin
    start_res = client.post("/api/checkins/start", headers=h)
    assert start_res.status_code == 200, f"Failed to start checkin: {start_res.text}"
    cid = start_res.json()["checkin_id"]

    # Drive checkin
    _drive_checkin(client, cid, h)

    # Complete checkin
    comp_res = client.post(f"/api/checkins/{cid}/complete", headers=h)
    assert comp_res.status_code == 200, f"Failed to complete checkin: {comp_res.text}"
    result = comp_res.json()

    assert "emergency" in result
    assert "reconciliation" in result
    assert "verification" in result
    assert result["max_severity"] in {"none", "low", "moderate", "high"}
    assert result["record_source_label"] == "Simulated hospital record (synthetic data)"
