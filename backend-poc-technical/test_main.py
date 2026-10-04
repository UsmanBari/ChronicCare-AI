"""
API Endpoint Tests for ChronicCare AI FastAPI backend
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
from data_sources import app_store
from scenarios.fixtures import CLEAN_AGREE_PAIR, CONFLICT_PAIR


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
    test_db_path = str(tmp_path / "test_main_store.db")
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
    if role == "provider":
        token = create_test_token(rsa_key_pair, sub="uid-provider-1", email="provider@demo.com", name="Dr. Provider")
    elif role == "admin":
        token = create_test_token(rsa_key_pair, sub="uid-admin-1", email="admin@demo.com", name="Admin User")
    else:
        token = create_test_token(rsa_key_pair, sub="uid-patient-1", email="patient@demo.com", name="Patient User")
    
    headers = auth_header(token)
    res = client.post("/api/auth/session", headers=headers)
    assert res.status_code == 200
    return headers


# -----------------------------------------------------------------------------
# Endpoint Tests
# -----------------------------------------------------------------------------

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "chroniccare-backend"


def test_reconcile_endpoint_clean_pair(client, rsa_key_pair):
    headers = get_role_headers(client, rsa_key_pair, "provider")
    bundle_a = {
        "patient": CLEAN_AGREE_PAIR["bundle_a"]["patient"].to_dict(),
        "observations": [o.to_dict() for o in CLEAN_AGREE_PAIR["bundle_a"]["observations"]],
        "medications": [m.to_dict() for m in CLEAN_AGREE_PAIR["bundle_a"]["medications"]],
    }
    bundle_b = {
        "patient": CLEAN_AGREE_PAIR["bundle_b"]["patient"].to_dict(),
        "observations": [o.to_dict() for o in CLEAN_AGREE_PAIR["bundle_b"]["observations"]],
        "medications": [m.to_dict() for m in CLEAN_AGREE_PAIR["bundle_b"]["medications"]],
    }
    
    payload = {
        "bundle_a": bundle_a,
        "bundle_b": bundle_b,
    }
    
    response = client.post("/api/reconcile", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "SYNTHETIC-PATIENT-MATCH-001"
    assert data["summary"]["conflicts"] == 0
    assert data["summary"]["agreements"] == 5


def test_verify_endpoint_conflict_pair(client, rsa_key_pair):
    headers = get_role_headers(client, rsa_key_pair, "provider")
    bundle_a = {
        "patient": CONFLICT_PAIR["bundle_a"]["patient"].to_dict(),
        "observations": [o.to_dict() for o in CONFLICT_PAIR["bundle_a"]["observations"]],
        "medications": [m.to_dict() for m in CONFLICT_PAIR["bundle_a"]["medications"]],
    }
    bundle_b = {
        "patient": CONFLICT_PAIR["bundle_b"]["patient"].to_dict(),
        "observations": [o.to_dict() for o in CONFLICT_PAIR["bundle_b"]["observations"]],
        "medications": [m.to_dict() for m in CONFLICT_PAIR["bundle_b"]["medications"]],
    }
    
    # 1. Reconcile
    recon_response = client.post("/api/reconcile", json={"bundle_a": bundle_a, "bundle_b": bundle_b}, headers=headers)
    assert recon_response.status_code == 200
    recon_data = recon_response.json()

    # 2. Verify with reconciliation_result
    verify_response = client.post("/api/verify", json={"reconciliation_result": recon_data}, headers=headers)
    assert verify_response.status_code == 200
    v_data = verify_response.json()
    assert v_data["patient_id"] == "SYNTHETIC-PATIENT-MATCH-002"
    assert v_data["summary"]["requires_review"] > 0
    assert v_data["summary"]["severity_high"] > 0


def test_reconcile_identity_mismatch_error(client, rsa_key_pair):
    headers = get_role_headers(client, rsa_key_pair, "provider")
    bundle_a = {
        "patient": {"patient_id": "PATIENT-A", "name": "Alice"},
        "observations": [],
        "medications": [],
    }
    bundle_b = {
        "patient": {"patient_id": "PATIENT-B", "name": "Bob"},
        "observations": [],
        "medications": [],
    }
    
    response = client.post("/api/reconcile", json={"bundle_a": bundle_a, "bundle_b": bundle_b}, headers=headers)
    assert response.status_code == 400
    assert "Patient Identity Contract Violation" in response.json()["detail"]


def test_reconcile_auth_gaps(client, rsa_key_pair):
    bundle_a = {
        "patient": {"patient_id": "PATIENT-A", "name": "Alice"},
        "observations": [],
        "medications": [],
    }
    bundle_b = {
        "patient": {"patient_id": "PATIENT-A", "name": "Alice"},
        "observations": [],
        "medications": [],
    }
    payload = {"bundle_a": bundle_a, "bundle_b": bundle_b}

    # 1. No token -> 401
    res_no_auth = client.post("/api/reconcile", json=payload)
    assert res_no_auth.status_code == 401

    # 2. Patient token -> 403
    patient_headers = get_role_headers(client, rsa_key_pair, "patient")
    res_patient = client.post("/api/reconcile", json=payload, headers=patient_headers)
    assert res_patient.status_code == 403

    # 3. Admin token -> 200
    admin_headers = get_role_headers(client, rsa_key_pair, "admin")
    res_admin = client.post("/api/reconcile", json=payload, headers=admin_headers)
    assert res_admin.status_code == 200


def test_verify_auth_gaps(client, rsa_key_pair):
    bundle_a = {
        "patient": {"patient_id": "PATIENT-A", "name": "Alice"},
        "observations": [],
        "medications": [],
    }
    bundle_b = {
        "patient": {"patient_id": "PATIENT-A", "name": "Alice"},
        "observations": [],
        "medications": [],
    }
    payload = {"bundle_a": bundle_a, "bundle_b": bundle_b}

    # 1. No token -> 401
    res_no_auth = client.post("/api/verify", json=payload)
    assert res_no_auth.status_code == 401

    # 2. Patient token -> 403
    patient_headers = get_role_headers(client, rsa_key_pair, "patient")
    res_patient = client.post("/api/verify", json=payload, headers=patient_headers)
    assert res_patient.status_code == 403

    # 3. Admin token -> 200
    admin_headers = get_role_headers(client, rsa_key_pair, "admin")
    res_admin = client.post("/api/verify", json=payload, headers=admin_headers)
    assert res_admin.status_code == 200
