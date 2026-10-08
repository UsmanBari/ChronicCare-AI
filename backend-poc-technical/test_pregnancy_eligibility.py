"""
Hermetic Tests for Pregnancy Screening, Sex at Birth, and Ineligibility Safety Halts.
"""

import os
import datetime
import time
from typing import Dict, Any
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

pytestmark = pytest.mark.inclusion

TEST_PROJECT_ID = "test-chroniccare-ai-pregnancy"
TEST_KID = "test-key-id-pregnancy"


@pytest.fixture(scope="session")
def rsa_key_pair():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="session")
def x509_cert_pem(rsa_key_pair) -> str:
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test ChronicCare AI"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Test Auth Cert"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        rsa_key_pair.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    ).sign(rsa_key_pair, hashes.SHA256())

    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.fixture(autouse=True)
def setup_auth_and_db(monkeypatch, tmp_path, rsa_key_pair, x509_cert_pem):
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("REQUIRE_INCLUSION", "1")
    monkeypatch.delenv("DB_BACKEND", raising=False)

    db_file = str(tmp_path / "test_pregnancy_app.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    app_store.migrate(backend="sqlite", db_path=db_file)
    local_store.init_db(backend="sqlite", db_path=db_file)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)


def make_token(user_id: str, email: str, rsa_key_pair) -> str:
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
        "firebase": {"sign_in_provider": "password"},
    }
    headers = {"kid": TEST_KID, "alg": "RS256"}
    return jwt.encode(payload, rsa_key_pair, algorithm="RS256", headers=headers)


def make_patient_headers(user_id: str, email: str, rsa_key_pair, client: TestClient) -> Dict[str, str]:
    token = make_token(user_id, email, rsa_key_pair)
    r = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Session init failed: {r.text}"
    return {"Authorization": f"Bearer {token}"}


def test_male_patient_auto_not_applicable(rsa_key_pair):
    client = TestClient(app)
    headers = make_patient_headers("user_male_1", "male@test.com", rsa_key_pair, client)

    # 1. Update profile with male sex and DOB
    r_prof = client.put(
        "/api/me/profile",
        json={
            "conditions": ["diabetes"],
            "date_of_birth": "1990-05-15",
            "inclusion_confirmed": True,
            "sex_at_birth": "male",
        },
        headers=headers,
    )
    assert r_prof.status_code == 200
    data = r_prof.json()
    assert data["sex_at_birth"] == "male"
    assert data["pregnancy_status"] == "not_applicable"

    # 2. Grant consents
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)

    # 3. Start checkin -> 200 allowed
    r_start = client.post("/api/checkins/start", headers=headers)
    assert r_start.status_code == 200
    assert "checkin_id" in r_start.json()


def test_female_patient_eligible_when_not_pregnant(rsa_key_pair):
    client = TestClient(app)
    headers = make_patient_headers("user_female_not_preg", "female_np@test.com", rsa_key_pair, client)

    # 1. Update profile with female sex, not pregnant
    r_prof = client.put(
        "/api/me/profile",
        json={
            "conditions": ["diabetes"],
            "date_of_birth": "1995-03-20",
            "inclusion_confirmed": True,
            "sex_at_birth": "female",
            "pregnancy_status": "no",
        },
        headers=headers,
    )
    assert r_prof.status_code == 200
    assert r_prof.json()["pregnancy_status"] == "no"

    # 2. Grant consents
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)

    # 3. Start checkin -> 200 allowed
    r_start = client.post("/api/checkins/start", headers=headers)
    assert r_start.status_code == 200


def test_pregnant_patient_blocked_at_checkin_start(rsa_key_pair):
    client = TestClient(app)
    headers = make_patient_headers("user_pregnant_1", "preg@test.com", rsa_key_pair, client)

    # 1. Update profile with pregnancy_status = "yes"
    r_prof = client.put(
        "/api/me/profile",
        json={
            "conditions": ["diabetes"],
            "date_of_birth": "1992-07-10",
            "inclusion_confirmed": True,
            "sex_at_birth": "female",
            "pregnancy_status": "yes",
        },
        headers=headers,
    )
    assert r_prof.status_code == 200
    assert r_prof.json()["pregnancy_status"] == "yes"

    # 2. Grant consents
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)

    # 3. Start checkin -> 403 not_eligible (reason: pregnant)
    r_start = client.post("/api/checkins/start", headers=headers)
    assert r_start.status_code == 403
    err = r_start.json()
    assert err["detail"] == "not_eligible"
    assert err["reason"] == "pregnant"


def test_pregnancy_unconfirmed_patient_blocked_at_checkin_start(rsa_key_pair):
    client = TestClient(app)
    headers = make_patient_headers("user_preg_notsure", "notsure@test.com", rsa_key_pair, client)

    # 1. Update profile with pregnancy_status = "not_sure"
    r_prof = client.put(
        "/api/me/profile",
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1988-11-25",
            "inclusion_confirmed": True,
            "sex_at_birth": "prefer_not_to_say",
            "pregnancy_status": "not_sure",
        },
        headers=headers,
    )
    assert r_prof.status_code == 200

    # 2. Grant consents
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)

    # 3. Start checkin -> 403 not_eligible (reason: pregnancy_unconfirmed)
    r_start = client.post("/api/checkins/start", headers=headers)
    assert r_start.status_code == 403
    err = r_start.json()
    assert err["detail"] == "not_eligible"
    assert err["reason"] == "pregnancy_unconfirmed"


def test_typed_pregnancy_statement_halts_interview(rsa_key_pair):
    client = TestClient(app)
    headers = make_patient_headers("user_typed_preg", "typed_preg@test.com", rsa_key_pair, client)

    # Initially answered 'no'
    client.put(
        "/api/me/profile",
        json={
            "conditions": ["diabetes"],
            "date_of_birth": "1994-01-15",
            "inclusion_confirmed": True,
            "sex_at_birth": "female",
            "pregnancy_status": "no",
        },
        headers=headers,
    )
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)

    # Start check-in session
    r_start = client.post("/api/checkins/start", headers=headers)
    assert r_start.status_code == 200
    checkin_id = r_start.json()["checkin_id"]

    # In interview: Patient types "I took a test and I am pregnant"
    r_ans = client.post(
        f"/api/checkins/{checkin_id}/answer",
        json={"answer": "I took a test this morning and I am pregnant", "step": "greeting"},
        headers=headers,
    )
    assert r_ans.status_code == 403
    err = r_ans.json()
    assert err["detail"] == "not_eligible"
    assert err["reason"] == "pregnant"

    # Profile updated to pregnant
    r_prof = client.get("/api/me/profile", headers=headers)
    assert r_prof.status_code == 200
    assert r_prof.json()["pregnancy_status"] == "yes"

    # Next checkin start is now also refused
    r_start_again = client.post("/api/checkins/start", headers=headers)
    assert r_start_again.status_code == 403
    assert r_start_again.json()["reason"] == "pregnant"


def test_typed_negated_pregnancy_statement_does_not_halt(rsa_key_pair):
    client = TestClient(app)
    headers = make_patient_headers("user_typed_not_preg", "typed_not_preg@test.com", rsa_key_pair, client)

    client.put(
        "/api/me/profile",
        json={
            "conditions": ["diabetes"],
            "date_of_birth": "1994-01-15",
            "inclusion_confirmed": True,
            "sex_at_birth": "female",
            "pregnancy_status": "no",
        },
        headers=headers,
    )
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)

    r_start = client.post("/api/checkins/start", headers=headers)
    assert r_start.status_code == 200
    checkin_id = r_start.json()["checkin_id"]

    # Patient types "I am not pregnant, just feel tired"
    r_ans = client.post(
        f"/api/checkins/{checkin_id}/answer",
        json={"answer": "I am not pregnant, just feel tired", "step": "greeting"},
        headers=headers,
    )
    # Must NOT return 403 not_eligible
    assert r_ans.status_code == 200
    ans_data = r_ans.json()
    assert ans_data["complete"] is False


def test_re_answering_pregnancy_status_unblocks_checkins(rsa_key_pair):
    client = TestClient(app)
    headers = make_patient_headers("user_re_answer", "reanswer@test.com", rsa_key_pair, client)

    # 1. Initially set to pregnancy_status = "yes" -> blocked
    client.put(
        "/api/me/profile",
        json={
            "conditions": ["diabetes"],
            "date_of_birth": "1991-04-10",
            "inclusion_confirmed": True,
            "sex_at_birth": "female",
            "pregnancy_status": "yes",
        },
        headers=headers,
    )
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)
    assert client.post("/api/checkins/start", headers=headers).status_code == 403

    # 2. Later, patient updates in Settings / My details to "no"
    r_prof_update = client.put(
        "/api/me/profile",
        json={
            "pregnancy_status": "no",
        },
        headers=headers,
    )
    assert r_prof_update.status_code == 200
    assert r_prof_update.json()["pregnancy_status"] == "no"

    # 3. Check-in is now unblocked
    r_start = client.post("/api/checkins/start", headers=headers)
    assert r_start.status_code == 200
    assert "checkin_id" in r_start.json()
