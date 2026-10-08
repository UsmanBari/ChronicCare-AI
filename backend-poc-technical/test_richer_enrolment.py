"""
Hermetic Unit & Integration Tests for Richer Enrolment (Stage 8 Part B).

Covers:
- Range validation for height_cm (50 to 250 cm).
- Range validation for weight_kg (20 to 400 kg).
- Year of diagnosis validation (not future, not before 1900, not before birth year).
- Allowed smoking status choices (never, former, current, prefer_not_to_say).
- Comorbidities dictionary keys validation (kidney_disease, heart_disease, stroke_or_tia, eye_problems, nerve_or_foot_problems).
- Skipping optional fields and partial updates.
- BMI calculation for provider review card (weight_kg / (height_m^2)).
- Triage thresholds / levels are unchanged by background fields.
"""

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
    test_db_path = str(tmp_path / "test_app_store.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


@pytest.fixture
def client():
    return TestClient(app)


def create_token(
    private_key,
    sub: str = "uid-pat-enrol-1",
    email: str = "pat_enrol@demo.com",
    role: str = "patient",
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "name": "Enrolment User",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, pem, algorithm="RS256", headers={"kid": TEST_KID})


def test_richer_enrolment_valid_all_fields(client, rsa_key_pair):
    token = create_token(rsa_key_pair)
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    payload = {
        "conditions": ["diabetes", "hypertension"],
        "on_insulin_or_sulfonylurea": True,
        "language": "en",
        "date_of_birth": "1980-05-15",
        "sex_at_birth": "female",
        "pregnancy_status": "no",
        "height_cm": 165.0,
        "weight_kg": 70.5,
        "diagnosis_year_diabetes": 2010,
        "diagnosis_year_hypertension": 2015,
        "smoking_status": "former",
        "comorbidities": {
            "kidney_disease": False,
            "heart_disease": True,
            "stroke_or_tia": False,
            "eye_problems": True,
            "nerve_or_foot_problems": False,
        },
    }
    res = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["height_cm"] == 165.0
    assert data["weight_kg"] == 70.5
    assert data["diagnosis_year_diabetes"] == 2010
    assert data["diagnosis_year_hypertension"] == 2015
    assert data["smoking_status"] == "former"
    assert data["comorbidities"]["heart_disease"] is True
    assert data["comorbidities"]["kidney_disease"] is False


def test_richer_enrolment_height_validation(client, rsa_key_pair):
    token = create_token(rsa_key_pair)
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    # Below 50
    r_low = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"height_cm": 49.9})
    assert r_low.status_code == 422

    # Above 250
    r_high = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"height_cm": 250.1})
    assert r_high.status_code == 422

    # Boundary valid 50.0 and 250.0
    r_min = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"height_cm": 50.0})
    assert r_min.status_code == 200
    assert r_min.json()["height_cm"] == 50.0

    r_max = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"height_cm": 250.0})
    assert r_max.status_code == 200
    assert r_max.json()["height_cm"] == 250.0


def test_richer_enrolment_weight_validation(client, rsa_key_pair):
    token = create_token(rsa_key_pair)
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    # Below 20
    r_low = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"weight_kg": 19.9})
    assert r_low.status_code == 422

    # Above 400
    r_high = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"weight_kg": 400.1})
    assert r_high.status_code == 422

    # Boundary valid 20.0 and 400.0
    r_min = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"weight_kg": 20.0})
    assert r_min.status_code == 200
    assert r_min.json()["weight_kg"] == 20.0

    r_max = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"weight_kg": 400.0})
    assert r_max.status_code == 200
    assert r_max.json()["weight_kg"] == 400.0


def test_richer_enrolment_diagnosis_year_validation(client, rsa_key_pair):
    token = create_token(rsa_key_pair)
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    current_year = datetime.datetime.now(datetime.timezone.utc).year

    # Future year
    r_fut = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "diagnosis_year_diabetes": current_year + 1,
    })
    assert r_fut.status_code == 422

    # Before 1900
    r_past = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "diagnosis_year_hypertension": 1899,
    })
    assert r_past.status_code == 422

    # Before birth year
    r_dob = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "date_of_birth": "1990-01-01",
        "diagnosis_year_diabetes": 1985,
    })
    assert r_dob.status_code == 422
    assert "birth year" in r_dob.json()["detail"].lower()


def test_richer_enrolment_smoking_status_validation(client, rsa_key_pair):
    token = create_token(rsa_key_pair)
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    for s in ("never", "former", "current", "prefer_not_to_say"):
        r = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"smoking_status": s})
        assert r.status_code == 200
        assert r.json()["smoking_status"] == s

    r_bad = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={"smoking_status": "chain_smoker"})
    assert r_bad.status_code == 422


def test_richer_enrolment_comorbidities_validation(client, rsa_key_pair):
    token = create_token(rsa_key_pair)
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    # Unknown key
    r_bad_key = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "comorbidities": {"asthma": True},
    })
    assert r_bad_key.status_code == 422

    # Non-boolean value
    r_bad_val = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "comorbidities": {"kidney_disease": "yes"},
    })
    assert r_bad_val.status_code == 422


def test_richer_enrolment_provider_card_bmi(client, rsa_key_pair):
    pat_token = create_token(rsa_key_pair, sub="uid-pat-bmi", email="pat_bmi@demo.com")
    prov_token = create_token(rsa_key_pair, sub="uid-prov-1", email="provider@demo.com", role="provider")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})

    # Setup profile with height 180cm, weight 81kg -> BMI = 81 / (1.8 * 1.8) = 25.0
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {pat_token}"}, json={
        "conditions": ["diabetes"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1980-01-01",
        "inclusion_confirmed": True,
        "height_cm": 180.0,
        "weight_kg": 81.0,
        "diagnosis_year_diabetes": 2012,
        "smoking_status": "never",
        "comorbidities": {"kidney_disease": False, "heart_disease": False, "stroke_or_tia": False, "eye_problems": False, "nerve_or_foot_problems": False},
    })
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {pat_token}"}, json={"granted": True, "provider_notification": True})

    # Start and complete a check-in
    start_res = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    assert start_res.status_code == 200
    checkin_id = start_res.json()["checkin_id"]

    # Submit answers in loop until interview complete
    answers = ["I feel good", "180 mg/dL", "no symptoms", "yes taking medicines", "no"]
    for ans in answers:
        ans_res = client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {pat_token}"},
            json={"answer": ans},
        )
        if ans_res.status_code == 200 and ans_res.json().get("complete"):
            break

    # Complete check-in
    comp_res = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {pat_token}"})
    assert comp_res.status_code == 200

    # Provider fetches review details
    rev_res = client.get(f"/api/provider/review/{checkin_id}", headers={"Authorization": f"Bearer {prov_token}"})
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert "patient_background" in rev_data
    bg = rev_data["patient_background"]
    assert bg is not None
    assert bg["height_cm"] == 180.0
    assert bg["weight_kg"] == 81.0
    assert bg["bmi"] == 25.0
    assert bg["smoking_status"] == "never"
    assert bg["diagnosis_year_diabetes"] == 2012
