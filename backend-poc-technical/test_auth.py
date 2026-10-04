"""
Hermetic Unit & Integration Tests for Server-Side Authentication, Roles & Audit Logging.

Tests token verification, role enforcement, session lifecycle, error safety, and audit logging
without external network calls or persistent database state.
"""

import os
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
from data_sources import app_store, db_config


# -----------------------------------------------------------------------------
# Fixtures & Key Generation
# -----------------------------------------------------------------------------

TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-1"
TEST_KID_2 = "test-key-id-2"


@pytest.fixture(scope="session")
def rsa_key_pair():
    """Generates an RSA private/public key pair for test token signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key


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
    """Sets up a clean temporary SQLite database and mocks Firebase project environment."""
    test_db_path = str(tmp_path / "test_app_store.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    # Initialize tables in temporary database
    app_store.migrate(db_path=test_db_path, backend="sqlite")

    # Mock public certs cache
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
    iat_delta: int = 0,
    auth_time_delta: int = 0,
    algorithm: str = "RS256",
    headers: Optional[Dict[str, Any]] = None,
) -> str:
    """Helper to generate JWT tokens with arbitrary headers and claims."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "aud": aud,
        "iss": iss or f"https://securetoken.google.com/{aud}",
        "iat": now + iat_delta,
        "exp": now + exp_delta,
        "auth_time": now + auth_time_delta,
    }
    jwt_headers = headers or {"kid": kid, "alg": algorithm}
    return jwt.encode(payload, private_key, algorithm=algorithm, headers=jwt_headers)


# -----------------------------------------------------------------------------
# Test Cases
# -----------------------------------------------------------------------------

def test_valid_token_creates_patient_and_registers_audit(rsa_key_pair):
    """Verifies that a valid token for an unseeded user creates a patient and registers audit."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-001", email="john@example.com", name="John Doe")
    client = TestClient(app)

    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "uid-pat-001"
    assert data["email"] == "john@example.com"
    assert data["role"] == "patient"
    assert data["status"] == "active"

    # Verify audit row created
    logs = app_store.get_audit_logs(limit=10)
    assert any(log["action"] == "user_registered" and log["actor_user_id"] == "uid-pat-001" for log in logs)


def test_demo_role_map_seeds_provider_and_admin(rsa_key_pair):
    """Verifies that emails matching DEMO_ROLE_MAP are assigned provider or admin roles."""
    client = TestClient(app)

    # Provider
    prov_token = create_test_token(rsa_key_pair, sub="uid-prov-1", email="provider@demo.com", name="Dr. Provider")
    resp_prov = client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})
    assert resp_prov.status_code == 200
    assert resp_prov.json()["role"] == "provider"

    # Admin
    admin_token = create_test_token(rsa_key_pair, sub="uid-admin-1", email="admin@demo.com", name="Admin User")
    resp_admin = client.post("/api/auth/session", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_admin.status_code == 200
    assert resp_admin.json()["role"] == "admin"


def test_session_endpoint_is_idempotent(rsa_key_pair):
    """Verifies that calling session endpoint repeatedly updates last_login_at without error."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-002", email="patient2@example.com")
    client = TestClient(app)

    # First call -> user_registered
    r1 = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200

    # Second call -> login
    r2 = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["user_id"] == "uid-pat-002"

    logs = app_store.get_audit_logs(limit=10)
    actions = [l["action"] for l in logs if l["actor_user_id"] == "uid-pat-002"]
    assert "user_registered" in actions
    assert "login" in actions


def test_expired_token_rejected(rsa_key_pair):
    """Verifies that expired tokens receive 401."""
    token = create_test_token(rsa_key_pair, exp_delta=-120)  # Expired 2 min ago
    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_wrong_audience_rejected(rsa_key_pair):
    """Verifies that mismatched audience receives 401."""
    token = create_test_token(rsa_key_pair, aud="wrong-project-id")
    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_wrong_issuer_rejected(rsa_key_pair):
    """Verifies that mismatched issuer receives 401."""
    token = create_test_token(rsa_key_pair, iss="https://securetoken.google.com/other-project")
    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_tampered_signature_rejected(rsa_key_pair):
    """Verifies that token with altered payload / invalid signature receives 401."""
    token = create_test_token(rsa_key_pair)
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}xyz.{parts[2]}"
    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {tampered}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_unknown_kid_refetches_then_rejects(rsa_key_pair, monkeypatch):
    """Verifies that token with unknown kid triggers a single refetch and rejects if still missing."""
    refetch_count = {"count": 0}

    def mock_fetch(force_refresh=False):
        if force_refresh:
            refetch_count["count"] += 1
        return {TEST_KID: "dummy-cert"}

    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", mock_fetch)

    token = create_test_token(rsa_key_pair, kid="unknown-kid")
    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert refetch_count["count"] == 1


def test_algorithm_none_rejected(rsa_key_pair):
    """Verifies that 'none' algorithm is rejected (prevents alg=none attacks)."""
    payload = {
        "sub": "attacker",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    # Manually craft token with alg: none
    header_b64 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0"
    import base64, json
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    unsigned_token = f"{header_b64}.{payload_b64}."

    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {unsigned_token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_algorithm_confusion_hs256_rejected(rsa_key_pair, x509_cert_pem):
    """Verifies that HS256 signed with public certificate text is rejected (algorithm confusion)."""
    import base64, hmac, hashlib, json
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": TEST_KID}
    payload = {
        "sub": "attacker",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
    }
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    sig = hmac.new(x509_cert_pem.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    hs256_token = f"{h_b64}.{p_b64}.{sig_b64}"

    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {hs256_token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_missing_sub_claim_rejected(rsa_key_pair):
    """Verifies that token with empty sub claim is rejected."""
    now = int(time.time())
    payload = {
        "sub": "",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(payload, rsa_key_pair, algorithm="RS256", headers={"kid": TEST_KID})
    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_malformed_or_oversized_authorization_header():
    """Verifies that malformed or > 4 KB Authorization headers are rejected."""
    client = TestClient(app)

    # Missing header
    assert client.get("/api/me").status_code == 401

    # Not Bearer
    assert client.get("/api/me", headers={"Authorization": "Basic 12345"}).status_code == 401

    # Oversized header (> 4096 bytes)
    huge_header = "Bearer " + ("A" * 4100)
    assert client.get("/api/me", headers={"Authorization": huge_header}).status_code == 401


def test_firebase_project_id_unset_returns_503(rsa_key_pair, monkeypatch):
    """Verifies that if FIREBASE_PROJECT_ID is unset, protected endpoints fail closed with 503."""
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    token = create_test_token(rsa_key_pair)
    client = TestClient(app)

    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication not configured"


def test_key_fetch_failure_with_empty_cache_returns_503(rsa_key_pair, monkeypatch):
    """Verifies that if Google certs endpoint fails and cache is empty, 503 is returned."""
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": {}, "expires_at": 0.0})

    def failing_fetch(force_refresh=False):
        raise firebase_verify.AuthError("Authentication service unavailable", status_code=503)

    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", failing_fetch)

    token = create_test_token(rsa_key_pair)
    client = TestClient(app)
    response = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication service unavailable"


def test_disabled_user_access_blocked(rsa_key_pair):
    """Verifies that disabled user cannot access protected endpoints or start sessions."""
    token = create_test_token(rsa_key_pair, sub="uid-disabled-1", email="disabled@example.com")
    client = TestClient(app)

    # Register first
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    # Disable the user in database
    with app_store.get_db_cursor() as (cursor, be, ph):
        cursor.execute(f"UPDATE users SET status = {ph} WHERE user_id = {ph}", ("disabled", "uid-disabled-1"))

    # Attempt session -> 403
    resp_session = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert resp_session.status_code == 403
    assert resp_session.json()["detail"] == "User account is disabled"

    # Attempt /api/me -> 403
    resp_me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_me.status_code == 403
    assert resp_me.json()["detail"] == "User account is disabled"


def test_role_guard_matrix_and_denial_audit(rsa_key_pair):
    """Verifies patient cannot access admin endpoints and that role denial is audited."""
    pat_token = create_test_token(rsa_key_pair, sub="uid-pat-003", email="patient3@example.com")
    client = TestClient(app)

    # Register patient
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})

    # Patient attempts to access /api/admin/audit -> 403
    response = client.get("/api/admin/audit", headers={"Authorization": f"Bearer {pat_token}"})
    assert response.status_code == 403

    # Check audit log for role_denied event
    logs = app_store.get_audit_logs(limit=10)
    denied_events = [l for l in logs if l["action"] == "role_denied" and l["actor_user_id"] == "uid-pat-003"]
    assert len(denied_events) >= 1
    assert denied_events[0]["outcome"] == "denied"


def test_admin_role_change_and_self_demote_protection(rsa_key_pair):
    """Verifies admin can change other user roles and cannot change own role."""
    admin_token = create_test_token(rsa_key_pair, sub="uid-admin-1", email="admin@demo.com")
    pat_token = create_test_token(rsa_key_pair, sub="uid-pat-004", email="pat4@example.com")
    client = TestClient(app)

    # Register both
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {admin_token}"})
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})

    # 1. Admin updates patient role to provider -> 200
    update_resp = client.post(
        "/api/admin/users/uid-pat-004/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "provider"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["role"] == "provider"

    # Verify audit
    logs = app_store.get_audit_logs(limit=5)
    role_updates = [l for l in logs if l["action"] == "role_updated" and l["target"] == "uid-pat-004"]
    assert len(role_updates) == 1
    assert role_updates[0]["detail"]["new_role"] == "provider"

    # 2. Admin attempts to change own role -> 400
    self_resp = client.post(
        "/api/admin/users/uid-admin-1/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "patient"},
    )
    assert self_resp.status_code == 400
    assert self_resp.json()["detail"] == "Admin cannot change their own role"

    # 3. Extra fields in request rejected (extra="forbid")
    extra_resp = client.post(
        "/api/admin/users/uid-pat-004/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "patient", "extra_field": 123},
    )
    assert extra_resp.status_code == 422


def test_audit_logs_contain_no_tokens_or_raw_emails(rsa_key_pair):
    """Privacy verification: asserts no audit row stores credentials or full emails."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-999", email="sensitive_patient@example.com")
    client = TestClient(app)
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    logs = app_store.get_audit_logs(limit=100)
    for log in logs:
        # Assert no token fragment in detail
        detail_str = str(log.get("detail", {}))
        assert "Bearer" not in detail_str
        assert "eyJ" not in detail_str
        assert "sensitive_patient@example.com" not in detail_str
