"""
Hermetic Integration Test: Full New User Journey on an Empty Database (FIX 9).

Tests the complete end-to-end journey of a brand-new patient on a clean database
with production defaults (REQUIRE_INCLUSION unset = enabled):
1. Session creation on empty database.
2. Check-in start refused before consent.
3. Consent grant (data & provider notification).
4. Check-in start refused with 403 'profile_incomplete' and structured 'missing' list.
5. Under-18 date of birth rejected with 422 adults_only.
6. Adult DOB and inclusion confirmation accepted.
7. Check-in start refused with 403 'profile_incomplete' missing conditions.
8. Clinical conditions saved.
9. Isolated mode record retrieval on empty database (proves table creation).
10. Add medication, allergy, and baseline observation.
11. Start check-in successfully.
12. Complete full diabetes check-in.
13. Hypertension check-in with 190/125 triage.
14. Emergency phrase 'I have chest pain' persistence and flagging.
15. Provider queue review of the escalated check-in.
"""

import os
import json
import time
import pytest
import jwt
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import datetime

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store, db_config


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-journey"


@pytest.fixture(scope="module")
def rsa_key_pair():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="module")
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
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .sign(rsa_key_pair, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def create_test_token(rsa_key_pair, sub: str, email: str) -> str:
    now = int(time.time())
    payload = {
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "aud": TEST_PROJECT_ID,
        "auth_time": now,
        "sub": sub,
        "iat": now,
        "exp": now + 3600,
        "email": email,
        "email_verified": True,
        "firebase": {
            "identities": {"email": [email]},
            "sign_in_provider": "password",
        },
    }
    priv_pem = rsa_key_pair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, priv_pem, algorithm="RS256", headers={"kid": TEST_KID})


@pytest.fixture
def journey_env(monkeypatch, tmp_path, x509_cert_pem):
    # Set up clean temporary database files
    app_db = str(tmp_path / "journey_app.db")
    local_db = str(tmp_path / "journey_local.db")

    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("LOCAL_DB_PATH", app_db)
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    # Production default: REQUIRE_INCLUSION is enabled (unset or '1')
    monkeypatch.delenv("REQUIRE_INCLUSION", raising=False)

    monkeypatch.setenv("DEMO_ROLE_MAP", "clinician.lead@hospital.org:provider")

    # Mock certs
    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    # Initialize schema on clean empty DBs without seeding any fixtures
    app_store.migrate(backend="sqlite", db_path=app_db)
    local_store.init_db(backend="sqlite", db_path=local_db)

    # Patch local_store get_connection default to use local_db
    monkeypatch.setattr(local_store, "DEFAULT_DB_PATH", local_db)
    monkeypatch.setattr(db_config, "get_sqlite_path", lambda custom_path=None: custom_path or app_db)

    return {"app_db": app_db, "local_db": local_db}


def test_full_new_user_journey_on_empty_db(journey_env, rsa_key_pair, monkeypatch):
    """
    Simulates a brand new patient signing up on an empty database and walking
    every onboarding gate to completing their first check-in and provider review.
    """
    client = TestClient(app)

    patient_email = "newpatient.test@chroniccare.org"
    patient_sub = "user-journey-patient-001"
    patient_token = create_test_token(rsa_key_pair, sub=patient_sub, email=patient_email)
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    provider_email = "clinician.lead@hospital.org"
    provider_sub = "user-journey-provider-001"
    provider_token = create_test_token(rsa_key_pair, sub=provider_sub, email=provider_email)
    provider_headers = {"Authorization": f"Bearer {provider_token}"}

    # -------------------------------------------------------------------------
    # Step 1: Session creation on brand new empty database
    # -------------------------------------------------------------------------
    res_sess = client.post("/api/auth/session", headers=patient_headers)
    assert res_sess.status_code == 200
    sess_data = res_sess.json()
    assert sess_data["email"] == patient_email
    assert sess_data["role"] == "patient"
    assert sess_data["status"] == "active"

    # Profile is initially unpopulated
    res_prof = client.get("/api/me/profile", headers=patient_headers)
    assert res_prof.status_code == 200
    prof_data = res_prof.json()
    assert prof_data["conditions"] == []
    assert prof_data["consent_granted_at"] is None
    assert prof_data["date_of_birth"] is None
    assert prof_data["inclusion_confirmed_at"] is None

    # -------------------------------------------------------------------------
    # Step 2: Starting check-in before consent is refused with 403
    # -------------------------------------------------------------------------
    r_start_no_consent = client.post("/api/checkins/start", headers=patient_headers)
    assert r_start_no_consent.status_code == 403
    assert "consent" in r_start_no_consent.json()["detail"].lower()

    # -------------------------------------------------------------------------
    # Step 3: Grant consent (both data and provider notification)
    # -------------------------------------------------------------------------
    r_consent1 = client.post("/api/me/consent", headers=patient_headers, json={"granted": True})
    assert r_consent1.status_code == 200
    assert r_consent1.json()["consent_granted_at"] is not None

    r_consent2 = client.post("/api/me/consent/provider-notification", headers=patient_headers, json={"granted": True})
    assert r_consent2.status_code == 200
    assert r_consent2.json()["provider_notification_consent_at"] is not None

    # -------------------------------------------------------------------------
    # Step 4: Starting check-in now returns 403 profile_incomplete with missing list
    # -------------------------------------------------------------------------
    r_start_inc = client.post("/api/checkins/start", headers=patient_headers)
    assert r_start_inc.status_code == 403
    inc_json = r_start_inc.json()
    assert inc_json["detail"] == "profile_incomplete"
    assert "date_of_birth" in inc_json["missing"]
    assert "inclusion_confirmed" in inc_json["missing"]

    # -------------------------------------------------------------------------
    # Step 5: Under-18 DOB rejected with 422 adults_only
    # -------------------------------------------------------------------------
    r_under18 = client.put("/api/me/profile", headers=patient_headers, json={
        "date_of_birth": "2018-01-01",
        "inclusion_confirmed": True,
    })
    assert r_under18.status_code == 422
    assert r_under18.json()["detail"] == "adults_only"

    # Save valid adult DOB + inclusion confirmation
    r_valid_inc = client.put("/api/me/profile", headers=patient_headers, json={
        "date_of_birth": "1982-06-15",
        "inclusion_confirmed": True,
    })
    assert r_valid_inc.status_code == 200
    assert r_valid_inc.json()["date_of_birth"] == "1982-06-15"
    assert r_valid_inc.json()["inclusion_confirmed_at"] is not None

    # -------------------------------------------------------------------------
    # Step 6: Start check-in still blocked on conditions
    # -------------------------------------------------------------------------
    r_start_cond = client.post("/api/checkins/start", headers=patient_headers)
    assert r_start_cond.status_code == 403
    cond_json = r_start_cond.json()
    assert cond_json["detail"] == "profile_incomplete"
    assert cond_json["missing"] == ["conditions"]

    # Save conditions
    r_save_cond = client.put("/api/me/profile", headers=patient_headers, json={
        "conditions": ["diabetes", "hypertension"],
        "on_insulin_or_sulfonylurea": False,
    })
    assert r_save_cond.status_code == 200
    assert "diabetes" in r_save_cond.json()["conditions"]

    # -------------------------------------------------------------------------
    # Step 7: Isolated Mode & Local Record on Empty Database
    # -------------------------------------------------------------------------
    r_rec = client.get("/api/me/record", headers=patient_headers)
    assert r_rec.status_code == 200
    rec_data = r_rec.json()
    assert rec_data["mode"] == "isolated"
    assert rec_data["medications"] == []
    assert rec_data["allergies"] == []
    assert rec_data["baseline_observations"] == []

    # Add medication, allergy, observation
    r_add_med = client.post("/api/me/record/medications", headers=patient_headers, json={
        "name": "Metformin 500mg",
        "dosage": "1 tablet twice daily",
        "status": "active",
    })
    assert r_add_med.status_code == 200
    assert r_add_med.json()["name"] == "Metformin 500mg"

    r_add_alg = client.post("/api/me/record/allergies", headers=patient_headers, json={
        "substance": "Penicillin",
        "reaction": "Rash",
        "confirmed": True,
    })
    assert r_add_alg.status_code == 200
    assert r_add_alg.json()["substance"] == "Penicillin"

    r_add_obs = client.post("/api/me/record/observations", headers=patient_headers, json={
        "observation_type": "glucose",
        "value": 115.0,
    })
    assert r_add_obs.status_code == 200

    # -------------------------------------------------------------------------
    # Step 8: Start Check-in Successfully
    # -------------------------------------------------------------------------
    r_start_ok = client.post("/api/checkins/start", headers=patient_headers)
    assert r_start_ok.status_code == 200
    start_data = r_start_ok.json()
    checkin_id = start_data["checkin_id"]
    assert checkin_id is not None
    assert start_data["question"] is not None

    # Complete diabetes check-in questions until fully complete
    while True:
        ans_resp = client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers=patient_headers,
            json={"answer": "No, I am taking 1 tablet twice daily as prescribed"},
        )
        assert ans_resp.status_code == 200
        if ans_resp.json().get("complete"):
            break

    # Complete check-in
    r_comp = client.post(f"/api/checkins/{checkin_id}/complete", headers=patient_headers)
    assert r_comp.status_code == 200
    comp_data = r_comp.json()
    assert "emergency" in comp_data
    assert "verification" in comp_data

    # -------------------------------------------------------------------------
    # Step 9: Hypertension check-in with 190/125 reaching safety questions
    # -------------------------------------------------------------------------
    r_start_htn = client.post("/api/checkins/start", headers=patient_headers)
    assert r_start_htn.status_code == 200
    checkin_id_htn = r_start_htn.json()["checkin_id"]

    r_htn_ans = client.post(
        f"/api/checkins/{checkin_id_htn}/answer",
        headers=patient_headers,
        json={"answer": "190/125"},
    )
    assert r_htn_ans.status_code == 200

    # -------------------------------------------------------------------------
    # Step 10: Emergency phrase 'I have chest pain' in a new check-in
    # -------------------------------------------------------------------------
    r_start2 = client.post("/api/checkins/start", headers=patient_headers)
    assert r_start2.status_code == 200
    checkin_id2 = r_start2.json()["checkin_id"]

    r_emerg = client.post(f"/api/checkins/{checkin_id2}/answer", headers=patient_headers, json={
        "answer": "I have severe chest pain and shortness of breath",
    })
    assert r_emerg.status_code == 200
    emerg_data = r_emerg.json()
    assert emerg_data["emergency"] is True
    assert emerg_data["complete"] is True
    assert emerg_data["escalation_recorded"] is True

    # -------------------------------------------------------------------------
    # Step 11: Provider signs in and views escalated queue
    # -------------------------------------------------------------------------
    res_prov_sess = client.post("/api/auth/session", headers=provider_headers)
    assert res_prov_sess.status_code == 200
    assert res_prov_sess.json()["role"] == "provider"

    r_queue = client.get("/api/provider/review-queue", headers=provider_headers)
    assert r_queue.status_code == 200
    queue_items = r_queue.json()
    assert len(queue_items) > 0
    # The emergency check-in is in the queue with emergency True
    assert any(item["checkin_id"] == checkin_id2 and item["emergency"] is True for item in queue_items)
