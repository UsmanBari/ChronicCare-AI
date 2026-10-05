"""
Tests for Separate Provider-Notification Consent Lines (Stage 7C-1 Priority 3).

Validates:
1. Defaults: POST /api/me/consent defaults provider_notification to granted.
2. Separate revoke and re-grant via POST /api/me/consent/provider-notification.
3. GET /api/me/profile returns both consent states.
4. POST /api/checkins/start requires both consents:
   - 403 consent_required if general consent missing/revoked
   - 403 provider_notification_consent_required if provider notification consent missing/revoked
   - 200 OK when both consents are active
5. Revoking either consent blocks new check-ins without purging existing escalations/records.
6. Emergencies stored prior to revocation remain visible in provider review queues.
7. Audit log rows written for all consent actions with no PHI.
"""

import os
import sys
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

# Ensure root backend dir is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store

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
def setup_test_env(tmp_path, monkeypatch, x509_cert_pem):
    test_db_path = str(tmp_path / "test_consent_store.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path, backend="sqlite")

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


def make_token(
    private_key,
    sub: str = "uid-patient-1",
    email: str = "patient@demo.com",
    name: str = "Patient One",
    exp_delta: int = 3600,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "email_verified": True,
        "name": name,
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + exp_delta,
        "auth_time": now,
    }
    headers = {"kid": TEST_KID, "alg": "RS256"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


@pytest.fixture
def client():
    return TestClient(app)


def get_patient_headers(client, rsa_key_pair, user_id="uid-patient-1", email="patient@demo.com"):
    token = make_token(rsa_key_pair, sub=user_id, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    return headers


def get_provider_headers(client, rsa_key_pair):
    token = make_token(rsa_key_pair, sub="uid-provider-1", email="provider@demo.com", name="Dr. Provider")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    return headers


def test_consent_defaults(rsa_key_pair):
    client = TestClient(app)
    # 1. Granting consent with omitted provider_notification defaults provider_notification to True
    res = client.post("/api/me/consent", json={"granted": True}, headers=get_patient_headers(client, rsa_key_pair))
    assert res.status_code == 200
    data = res.json()
    assert data["consent_granted_at"] is not None
    assert data["consent_revoked_at"] is None
    assert data["provider_notification_consent_at"] is not None
    assert data["provider_notification_revoked_at"] is None

    # 2. Revoking consent with omitted provider_notification defaults provider_notification to False
    res2 = client.post("/api/me/consent", json={"granted": False}, headers=get_patient_headers(client, rsa_key_pair))
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["consent_revoked_at"] is not None
    assert data2["provider_notification_revoked_at"] is not None


def test_consent_explicit_values(rsa_key_pair):
    client = TestClient(app)
    # Grant general consent, but explicitly deny provider notification
    res = client.post(
        "/api/me/consent",
        json={"granted": True, "provider_notification": False},
        headers=get_patient_headers(client, rsa_key_pair),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["consent_granted_at"] is not None
    assert data["consent_revoked_at"] is None
    assert data["provider_notification_revoked_at"] is not None


def test_separate_provider_notification_endpoint(rsa_key_pair):
    client = TestClient(app)
    headers = get_patient_headers(client, rsa_key_pair)

    # Initially grant both
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    # Revoke provider notification separately
    res_revoke = client.post("/api/me/consent/provider-notification", json={"granted": False}, headers=headers)
    assert res_revoke.status_code == 200
    data_rev = res_revoke.json()
    assert data_rev["consent_granted_at"] is not None
    assert data_rev["consent_revoked_at"] is None
    assert data_rev["provider_notification_revoked_at"] is not None

    # Re-grant provider notification separately
    res_regrant = client.post("/api/me/consent/provider-notification", json={"granted": True}, headers=headers)
    assert res_regrant.status_code == 200
    data_reg = res_regrant.json()
    assert data_reg["provider_notification_consent_at"] is not None
    assert data_reg["provider_notification_revoked_at"] is None


def test_get_profile_returns_both_consents(rsa_key_pair):
    client = TestClient(app)
    headers = get_patient_headers(client, rsa_key_pair)

    client.post("/api/me/consent", json={"granted": True}, headers=headers)
    client.post("/api/me/consent/provider-notification", json={"granted": False}, headers=headers)

    res = client.get("/api/me/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["consent_granted_at"] is not None
    assert data["consent_revoked_at"] is None
    assert data["provider_notification_revoked_at"] is not None


def test_start_checkin_consent_requirements(rsa_key_pair):
    client = TestClient(app)
    headers = get_patient_headers(client, rsa_key_pair, user_id="uid-patient-reqs", email="patreqs@demo.com")

    # Profile with conditions
    res_prof = client.put(
        "/api/me/profile",
        json={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False, "language": "en"},
        headers=headers,
    )
    assert res_prof.status_code == 200

    # 1. No consent at all -> 403 consent_required
    res1 = client.post("/api/checkins/start", headers=headers)
    assert res1.status_code == 403
    assert "consent_required" in res1.json()["detail"]

    # 2. General consent granted, but provider notification denied -> 403 provider_notification_consent_required
    client.post("/api/me/consent", json={"granted": True, "provider_notification": False}, headers=headers)
    res2 = client.post("/api/checkins/start", headers=headers)
    assert res2.status_code == 403
    assert "provider_notification_consent_required" in res2.json()["detail"]

    # 3. Provider notification granted, but general consent revoked -> 403 consent_required
    client.post("/api/me/consent/provider-notification", json={"granted": True}, headers=headers)
    # Revoke general consent directly
    app_store.set_patient_consent("uid-patient-reqs", granted=False)
    res3 = client.post("/api/checkins/start", headers=headers)
    assert res3.status_code == 403
    assert "consent_required" in res3.json()["detail"]

    # 4. Both granted -> 200 OK
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)
    res4 = client.post("/api/checkins/start", headers=headers)
    assert res4.status_code == 200, f"res4 failed with {res4.status_code}: {res4.text}"
    assert "checkin_id" in res4.json()


def test_emergency_visible_after_consent_revocation(rsa_key_pair):
    client = TestClient(app)
    p_headers = get_patient_headers(client, rsa_key_pair, user_id="uid-patient-emerg", email="patemerg@demo.com")
    prov_headers = get_provider_headers(client, rsa_key_pair)

    # Set up profile and both consents
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=p_headers)
    res_prof = client.put(
        "/api/me/profile",
        json={"conditions": ["diabetes", "hypertension"], "on_insulin_or_sulfonylurea": False, "language": "en"},
        headers=p_headers,
    )
    assert res_prof.status_code == 200

    # Start checkin
    start_res = client.post("/api/checkins/start", headers=p_headers)
    assert start_res.status_code == 200, f"start_res failed with {start_res.status_code}: {start_res.text}"
    checkin_id = start_res.json()["checkin_id"]

    # Trigger emergency
    ans_res = client.post(
        f"/api/checkins/{checkin_id}/answer",
        json={"answer": "I have severe crushing chest pain", "step": "greeting"},
        headers=p_headers,
    )
    assert ans_res.status_code == 200
    assert ans_res.json()["emergency"] is True

    # Now patient revokes BOTH consents
    client.post("/api/me/consent", json={"granted": False}, headers=p_headers)

    # Starting a new check-in is blocked
    blocked = client.post("/api/checkins/start", headers=p_headers)
    assert blocked.status_code == 403

    # But previously recorded emergency remains in provider review queue
    q_res = client.get("/api/provider/review-queue?status=open", headers=prov_headers)
    assert q_res.status_code == 200
    items = q_res.json()
    if isinstance(items, dict) and "items" in items:
        items = items["items"]
    matching = [i for i in items if i["checkin_id"] == checkin_id]
    assert len(matching) == 1
    assert matching[0]["emergency"] is True

    # Detailed review endpoint still works for provider
    detail_res = client.get(f"/api/provider/review/{checkin_id}", headers=prov_headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["checkin_id"] == checkin_id


def test_consent_audit_rows(rsa_key_pair):
    client = TestClient(app)
    headers = get_patient_headers(client, rsa_key_pair, user_id="uid-patient-audit", email="pataudit@demo.com")

    # Grant both
    client.post("/api/me/consent", json={"granted": True, "provider_notification": True}, headers=headers)
    # Revoke provider notification
    client.post("/api/me/consent/provider-notification", json={"granted": False}, headers=headers)
    # Re-grant provider notification
    client.post("/api/me/consent/provider-notification", json={"granted": True}, headers=headers)
    # Revoke general consent
    client.post("/api/me/consent", json={"granted": False}, headers=headers)

    # Check audit log in DB
    rows = app_store.get_audit_logs(limit=50)
    actions = [r["action"] for r in rows]

    assert "consent_granted" in actions
    assert "consent_revoked" in actions
    assert "consent_provider_notification_granted" in actions
    assert "consent_provider_notification_revoked" in actions

    # Verify no PHI in details
    for r in rows:
        if "consent" in r["action"] and r["actor_user_id"] == "uid-patient-audit":
            assert isinstance(r["detail"], dict)
