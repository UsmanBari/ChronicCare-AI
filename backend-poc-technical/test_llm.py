"""
Unit Tests for Groq LLM Client & Health Endpoints.

All tests are strictly hermetic and mock the Groq client to prevent any network calls.
CI runs without GROQ_API_KEY and must remain green.
"""

import os
import sys
import time
import datetime
from typing import Dict, Any, Optional
import pytest
import jwt
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

# Ensure root backend dir is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from auth import firebase_verify
from data_sources import app_store
from llm.groq_client import chat, is_configured, get_configured_model, get_api_key


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
    """Sets up a clean temporary SQLite database and mocks Firebase project environment."""
    test_db_path = str(tmp_path / "test_llm_store.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")

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


def get_role_headers(client, rsa_key_pair, role: str) -> Dict[str, str]:
    if role == "admin":
        token = create_test_token(rsa_key_pair, sub="uid-admin-1", email="admin@demo.com", name="Admin User")
    elif role == "provider":
        token = create_test_token(rsa_key_pair, sub="uid-provider-1", email="provider@demo.com", name="Dr. Provider")
    else:
        token = create_test_token(rsa_key_pair, sub="uid-patient-1", email="patient@demo.com", name="Patient User")
    
    headers = auth_header(token)
    res = client.post("/api/auth/session", headers=headers)
    assert res.status_code == 200
    return headers


# -----------------------------------------------------------------------------
# LLM Client Tests
# -----------------------------------------------------------------------------

def test_missing_api_key_raises_error(monkeypatch):
    """Verifies that missing GROQ_API_KEY raises a clear ValueError."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        chat(messages=[{"role": "user", "content": "hello"}])


def test_missing_model_raises_error(monkeypatch):
    """Verifies that missing GROQ_MODEL without explicit parameter raises ValueError."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    
    with pytest.raises(ValueError, match="GROQ_MODEL"):
        chat(messages=[{"role": "user", "content": "hello"}], model=None)


@patch("llm.groq_client.get_client")
def test_successful_chat_mocked(mock_get_client, monkeypatch):
    """Verifies that chat() calls Groq completions and returns text content."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "mock-model")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "  Hello from Groq!  "
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = chat(messages=[{"role": "user", "content": "ping"}])
    assert result == "Hello from Groq!"
    mock_client.chat.completions.create.assert_called_once()


@patch("llm.groq_client.get_client")
def test_retry_on_transient_error(mock_get_client, monkeypatch):
    """Verifies that transient errors trigger retries up to max_retries."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "mock-model")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Success after retry"
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        Exception("503 Service Unavailable"),
        mock_response,
    ]
    mock_get_client.return_value = mock_client

    result = chat(
        messages=[{"role": "user", "content": "retry test"}],
        max_retries=2,
    )
    assert result == "Success after retry"
    assert mock_client.chat.completions.create.call_count == 2


@patch("llm.groq_client.get_client")
def test_retry_exhaustion_raises_error(mock_get_client, monkeypatch):
    """Verifies that persistent transient errors raise an exception after retries are exhausted."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "mock-model")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
    mock_get_client.return_value = mock_client

    with pytest.raises(Exception):
        chat(
            messages=[{"role": "user", "content": "fail test"}],
            max_retries=2,
        )
    assert mock_client.chat.completions.create.call_count == 3


# -----------------------------------------------------------------------------
# LLM Health Endpoint Tests (Admin-Protected)
# -----------------------------------------------------------------------------

def test_health_endpoint_not_configured(client, rsa_key_pair, monkeypatch):
    """Verifies /api/llm/health when env vars are missing with admin token."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    admin_headers = get_role_headers(client, rsa_key_pair, "admin")
    response = client.get("/api/llm/health", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False
    assert data["model"] is None


def test_health_endpoint_configured(client, rsa_key_pair, monkeypatch):
    """Verifies /api/llm/health when env vars are configured with admin token."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-model-test")

    admin_headers = get_role_headers(client, rsa_key_pair, "admin")
    response = client.get("/api/llm/health", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["model"] == "llama-model-test"


@patch("main.chat")
def test_health_endpoint_ping_success(mock_chat, client, rsa_key_pair, monkeypatch):
    """Verifies /api/llm/health?ping=true makes a ping completion with admin token."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-model-test")
    mock_chat.return_value = "pong"

    admin_headers = get_role_headers(client, rsa_key_pair, "admin")
    response = client.get("/api/llm/health?ping=true", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert isinstance(data["latency_ms"], int)
    mock_chat.assert_called_once()


def test_llm_health_auth_gaps(client, rsa_key_pair):
    """Verifies 401 on unauthenticated call and 403 on non-admin roles."""
    # 1. No token -> 401
    res_no_auth = client.get("/api/llm/health")
    assert res_no_auth.status_code == 401

    # 2. Patient token -> 403
    pat_headers = get_role_headers(client, rsa_key_pair, "patient")
    res_pat = client.get("/api/llm/health", headers=pat_headers)
    assert res_pat.status_code == 403

    # 3. Provider token -> 403
    prov_headers = get_role_headers(client, rsa_key_pair, "provider")
    res_prov = client.get("/api/llm/health", headers=prov_headers)
    assert res_prov.status_code == 403
