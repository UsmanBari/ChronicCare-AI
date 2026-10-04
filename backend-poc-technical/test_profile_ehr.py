"""
Hermetic Unit & Integration Tests for Patient Profile, Consent, EHR Registry & EHR Connection.

Covers:
- Profile CRUD and validation (allowed conditions, non-empty, allowed languages, extra field rejection).
- Explicit consent lifecycle (grant, revoke, audit logs).
- EHR Registry (listing enabled EHRs without exposing raw URLs).
- EHR Connection (success, 404 not found, 502 unavailable, invalid ID regex, 409 conflict, reconnect replaces prior).
- Disconnect (revocation, return to isolated mode).
- Consent enforcement on connect (403 if consent not granted/revoked).
- Role matrix (provider/admin tokens rejected with 403 on patient endpoints).
- SSRF / payload protection (rejection of client-supplied URL or unknown fields with 422).
- Privacy in audit logs (zero full external patient IDs in audit rows, masked only).
"""

import os
import time
import datetime
from typing import Dict, Any, Optional
import pytest
import requests
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
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

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
    headers = {"kid": kid, "alg": "RS256"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


@pytest.fixture
def client():
    return TestClient(app)


def auth_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# PROFILE & CONSENT TESTS
# -----------------------------------------------------------------------------

def test_patient_profile_defaults_and_upsert(client, rsa_key_pair):
    """Test retrieving default profile and updating valid profile fields."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-profile-1", email="pat1@demo.com")
    headers = auth_header(token)

    # Initialize session
    res_sess = client.post("/api/auth/session", headers=headers)
    assert res_sess.status_code == 200
    assert res_sess.json()["role"] == "patient"

    # GET default profile
    res_prof = client.get("/api/me/profile", headers=headers)
    assert res_prof.status_code == 200
    data = res_prof.json()
    assert data["user_id"] == "uid-pat-profile-1"
    assert data["conditions"] == []
    assert data["on_insulin_or_sulfonylurea"] is False
    assert data["language"] == "en"

    # PUT valid profile update
    update_payload = {
        "conditions": ["diabetes", "hypertension"],
        "on_insulin_or_sulfonylurea": True,
        "language": "ur",
    }
    res_put = client.put("/api/me/profile", json=update_payload, headers=headers)
    assert res_put.status_code == 200
    put_data = res_put.json()
    assert sorted(put_data["conditions"]) == ["diabetes", "hypertension"]
    assert put_data["on_insulin_or_sulfonylurea"] is True
    assert put_data["language"] == "ur"
    assert put_data["updated_at"] is not None

    # Verify audit row created
    audits = app_store.get_audit_logs(limit=10)
    profile_audit = next((a for a in audits if a["action"] == "profile_updated"), None)
    assert profile_audit is not None
    assert profile_audit["actor_user_id"] == "uid-pat-profile-1"
    assert profile_audit["outcome"] == "ok"


def test_patient_profile_validation(client, rsa_key_pair):
    """Test validation errors for empty conditions, invalid condition, invalid language, and unknown fields."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-profile-val", email="patval@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)

    # Empty conditions list -> 422
    res_empty = client.put("/api/me/profile", json={"conditions": [], "on_insulin_or_sulfonylurea": False, "language": "en"}, headers=headers)
    assert res_empty.status_code == 422

    # Invalid condition -> 422
    res_invalid_cond = client.put("/api/me/profile", json={"conditions": ["asthma"], "on_insulin_or_sulfonylurea": False, "language": "en"}, headers=headers)
    assert res_invalid_cond.status_code == 422

    # Invalid language -> 422
    res_invalid_lang = client.put("/api/me/profile", json={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False, "language": "fr"}, headers=headers)
    assert res_invalid_lang.status_code == 422

    # Unknown field -> 422 (extra="forbid")
    res_extra = client.put("/api/me/profile", json={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False, "language": "en", "unknown_field": "test"}, headers=headers)
    assert res_extra.status_code == 422


def test_patient_consent_grant_and_revoke(client, rsa_key_pair):
    """Test granting and revoking consent, verifying timestamps and audit records."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-consent", email="patconsent@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)

    # Grant consent
    res_grant = client.post("/api/me/consent", json={"granted": True}, headers=headers)
    assert res_grant.status_code == 200
    grant_data = res_grant.json()
    assert grant_data["consent_granted_at"] is not None
    assert grant_data["consent_revoked_at"] is None

    # Revoke consent
    res_revoke = client.post("/api/me/consent", json={"granted": False}, headers=headers)
    assert res_revoke.status_code == 200
    revoke_data = res_revoke.json()
    assert revoke_data["consent_granted_at"] is not None
    assert revoke_data["consent_revoked_at"] is not None

    # Verify audit logs
    audits = app_store.get_audit_logs(limit=10)
    grant_audit = next((a for a in audits if a["action"] == "consent_granted"), None)
    revoke_audit = next((a for a in audits if a["action"] == "consent_revoked"), None)
    assert grant_audit is not None
    assert revoke_audit is not None


# -----------------------------------------------------------------------------
# EHR REGISTRY & CONNECTION TESTS
# -----------------------------------------------------------------------------

def test_get_ehr_systems(client, rsa_key_pair):
    """Test EHR systems list returns id and display name only, never fhir_base_url."""
    res = client.get("/api/ehr/systems")
    assert res.status_code == 200
    systems = res.json()
    assert len(systems) >= 1
    sandbox = next((s for s in systems if s["ehr_system_id"] == "smart-sandbox"), None)
    assert sandbox is not None
    assert sandbox["display_name"] == "SMART Health IT Sandbox"
    assert "fhir_base_url" not in sandbox
    assert "url" not in sandbox


def test_connect_ehr_consent_required(client, rsa_key_pair):
    """Test connecting without consent fails with 403."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-no-consent", email="patnoconsent@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)

    # Attempt connect before granting consent -> 403
    res_conn = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "patient-1234"}, headers=headers)
    assert res_conn.status_code == 403
    assert "consent" in res_conn.json()["detail"].lower()


def test_connect_ehr_success_and_masked_id(client, rsa_key_pair, monkeypatch):
    """Test successful EHR connection with mocked FHIR client, verifying mode and masking."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-connect-ok", email="patconnok@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    # Mock FHIR live verification
    mock_called = {}
    def mock_get_fhir_patient(patient_id: str, base_url: Optional[str] = None, timeout: int = 10):
        mock_called["patient_id"] = patient_id
        mock_called["base_url"] = base_url
        mock_called["timeout"] = timeout
        return {"resourceType": "Patient", "id": patient_id}

    monkeypatch.setattr("main.get_fhir_patient", mock_get_fhir_patient)

    # Connect
    res = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "pat-record-9988"}, headers=headers)
    assert res.status_code == 200
    conn_data = res.json()
    assert conn_data["mode"] == "connected"
    assert conn_data["connection"]["ehr_system_id"] == "smart-sandbox"
    assert conn_data["connection"]["display_name"] == "SMART Health IT Sandbox"
    assert conn_data["connection"]["masked_patient_id"] == "...9988"
    assert conn_data["connection"]["last_verified_at"] is not None

    # Check that URL passed to mock came from DB, timeout is <= 10
    assert mock_called["patient_id"] == "pat-record-9988"
    assert mock_called["base_url"] == "https://r4.smarthealthit.org"
    assert mock_called["timeout"] <= 10

    # Verify GET /api/ehr/connection
    res_get = client.get("/api/ehr/connection", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["mode"] == "connected"
    assert res_get.json()["connection"]["masked_patient_id"] == "...9988"

    # Verify GET /api/me reflects connected mode
    res_me = client.get("/api/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["mode"] == "connected"


def test_connect_ehr_404_patient_not_found(client, rsa_key_pair, monkeypatch):
    """Test 404 response when patient does not exist in EHR."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-404", email="pat404@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    def mock_get_fhir_patient_404(patient_id: str, base_url: Optional[str] = None, timeout: int = 10):
        resp = requests.Response()
        resp.status_code = 404
        raise requests.exceptions.HTTPError("Patient not found", response=resp)

    monkeypatch.setattr("main.get_fhir_patient", mock_get_fhir_patient_404)

    res = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "nonexistent-0000"}, headers=headers)
    assert res.status_code == 404
    assert "Patient not found" in res.json()["detail"]

    # Verify failed attempt recorded in DB
    with app_store.get_db_cursor() as (cursor, be, ph):
        cursor.execute(f"SELECT status, last_error_code FROM ehr_connections WHERE user_id = {ph}", ("uid-pat-404",))
        row = cursor.fetchone()
        assert row is not None
        assert dict(row)["status"] == "failed"
        assert dict(row)["last_error_code"] == "not_found"


def test_connect_ehr_502_unavailable(client, rsa_key_pair, monkeypatch):
    """Test 502 response when EHR returns 5xx or network connection fails."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-502", email="pat502@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    # 1. Test 500 HTTPError
    def mock_500(patient_id: str, base_url: Optional[str] = None, timeout: int = 10):
        resp = requests.Response()
        resp.status_code = 500
        raise requests.exceptions.HTTPError("Internal Server Error", response=resp)

    monkeypatch.setattr("main.get_fhir_patient", mock_500)
    res_500 = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "fail-1234"}, headers=headers)
    assert res_500.status_code == 502
    assert "EHR unavailable" in res_500.json()["detail"]

    # 2. Test ConnectionError
    def mock_conn_err(patient_id: str, base_url: Optional[str] = None, timeout: int = 10):
        raise requests.exceptions.ConnectionError("Failed to connect")

    monkeypatch.setattr("main.get_fhir_patient", mock_conn_err)
    res_conn_err = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "fail-5678"}, headers=headers)
    assert res_conn_err.status_code == 502
    assert "EHR unavailable" in res_conn_err.json()["detail"]


def test_connect_ehr_invalid_patient_id(client, rsa_key_pair):
    """Test external_patient_id regex validation."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-regex", email="patregex@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    # Invalid special characters
    res_bad_chars = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "patient!@#$"}, headers=headers)
    assert res_bad_chars.status_code == 422

    # Exceeding 64 characters
    res_too_long = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "a" * 65}, headers=headers)
    assert res_too_long.status_code == 422


def test_connect_ehr_duplicate_link_409(client, rsa_key_pair, monkeypatch):
    """Test 409 Conflict when linking to an EHR patient id already active on another account."""
    monkeypatch.setattr("main.get_fhir_patient", lambda patient_id, base_url=None, timeout=10: {"resourceType": "Patient", "id": patient_id})

    # Patient 1 connects to 'shared-patient-100'
    token1 = create_test_token(rsa_key_pair, sub="uid-pat-dup-1", email="patdup1@demo.com")
    headers1 = auth_header(token1)
    client.post("/api/auth/session", headers=headers1)
    client.post("/api/me/consent", json={"granted": True}, headers=headers1)
    res1 = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "shared-patient-100"}, headers=headers1)
    assert res1.status_code == 200

    # Patient 2 attempts connecting to same patient ID
    token2 = create_test_token(rsa_key_pair, sub="uid-pat-dup-2", email="patdup2@demo.com")
    headers2 = auth_header(token2)
    client.post("/api/auth/session", headers=headers2)
    client.post("/api/me/consent", json={"granted": True}, headers=headers2)
    res2 = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "shared-patient-100"}, headers=headers2)
    assert res2.status_code == 409
    assert "already linked" in res2.json()["detail"].lower()


def test_reconnecting_replaces_previous_connection(client, rsa_key_pair, monkeypatch):
    """Test that connecting a new EHR patient revokes prior active connection."""
    monkeypatch.setattr("main.get_fhir_patient", lambda patient_id, base_url=None, timeout=10: {"resourceType": "Patient", "id": patient_id})

    token = create_test_token(rsa_key_pair, sub="uid-pat-reconnect", email="patrecon@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    # First connection
    res1 = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "first-patient-1111"}, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["connection"]["masked_patient_id"] == "...1111"

    # Second connection
    res2 = client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "second-patient-2222"}, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["connection"]["masked_patient_id"] == "...2222"

    # Check DB state: only 1 active connection, first one revoked
    with app_store.get_db_cursor() as (cursor, be, ph):
        cursor.execute(f"SELECT external_patient_id, status FROM ehr_connections WHERE user_id = {ph} ORDER BY linked_at ASC", ("uid-pat-reconnect",))
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert dict(rows[0])["external_patient_id"] == "first-patient-1111"
        assert dict(rows[0])["status"] == "revoked"
        assert dict(rows[1])["external_patient_id"] == "second-patient-2222"
        assert dict(rows[1])["status"] == "active"


def test_disconnect_returns_to_isolated_mode(client, rsa_key_pair, monkeypatch):
    """Test revoking connection via DELETE /api/ehr/connection returns mode to isolated."""
    monkeypatch.setattr("main.get_fhir_patient", lambda patient_id, base_url=None, timeout=10: {"resourceType": "Patient", "id": patient_id})

    token = create_test_token(rsa_key_pair, sub="uid-pat-disconnect", email="patdisc@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)
    client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "active-patient-3333"}, headers=headers)

    # DELETE /api/ehr/connection
    res_del = client.delete("/api/ehr/connection", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["mode"] == "isolated"
    assert res_del.json()["connection"] is None

    # Check GET /api/ehr/connection and GET /api/me
    res_conn = client.get("/api/ehr/connection", headers=headers)
    assert res_conn.json()["mode"] == "isolated"
    assert res_conn.json()["connection"] is None

    res_me = client.get("/api/me", headers=headers)
    assert res_me.json()["mode"] == "isolated"


def test_client_supplied_url_or_extra_field_rejected(client, rsa_key_pair):
    """Test that extra fields or client-supplied URLs are strictly rejected with 422."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-ssrf-probe", email="patssrf@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)

    payload_with_url = {
        "ehr_system_id": "smart-sandbox",
        "external_patient_id": "pat-1234",
        "fhir_base_url": "https://malicious-site.example.com",
    }
    res = client.post("/api/ehr/connect", json=payload_with_url, headers=headers)
    assert res.status_code == 422


def test_role_matrix_provider_admin_rejected_on_patient_endpoints(client, rsa_key_pair):
    """Test that provider and admin tokens are rejected with 403 on patient-specific endpoints."""
    token_provider = create_test_token(rsa_key_pair, sub="uid-provider-1", email="provider@demo.com")
    token_admin = create_test_token(rsa_key_pair, sub="uid-admin-1", email="admin@demo.com")

    for token in [token_provider, token_admin]:
        headers = auth_header(token)
        client.post("/api/auth/session", headers=headers)

        assert client.get("/api/me/profile", headers=headers).status_code == 403
        assert client.put("/api/me/profile", json={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False}, headers=headers).status_code == 403
        assert client.post("/api/me/consent", json={"granted": True}, headers=headers).status_code == 403
        assert client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": "pat-1234"}, headers=headers).status_code == 403
        assert client.delete("/api/ehr/connection", headers=headers).status_code == 403


def test_audit_logs_contain_no_full_external_patient_id(client, rsa_key_pair, monkeypatch):
    """Test that audit log records never contain full external patient ID or PHI."""
    monkeypatch.setattr("main.get_fhir_patient", lambda patient_id, base_url=None, timeout=10: {"resourceType": "Patient", "id": patient_id})

    full_id = "sensitive-ehr-patient-id-xyz-7788"
    token = create_test_token(rsa_key_pair, sub="uid-pat-audit-privacy", email="pataudit@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", json={"granted": True}, headers=headers)
    client.post("/api/ehr/connect", json={"ehr_system_id": "smart-sandbox", "external_patient_id": full_id}, headers=headers)

    audits = app_store.get_audit_logs(limit=50)
    assert len(audits) >= 3

    for row in audits:
        detail_text = str(row.get("detail", {}))
        # Ensure full ID never appears in audit detail or target
        assert full_id not in detail_text
        assert full_id not in str(row.get("target", ""))
        # Verify masking appears if it's an EHR connect action
        if row["action"] == "ehr_connected":
            assert row["detail"]["masked_patient_id"] == "...7788"
