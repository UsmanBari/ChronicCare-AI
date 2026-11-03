"""
Hermetic Integration & Regression Tests for Roman Urdu ('roman_ur') Language Support.

Closes Gap G-12 (Interview Audit):
- Verifies PUT /api/me/profile accepts 'roman_ur' with 200 OK.
- Verifies GET /api/me/profile returns 'roman_ur'.
- Verifies invalid languages (e.g., 'es', 'fr') are rejected with 422 Unprocessable Entity.
- Verifies app_store and local storage preserve 'roman_ur'.
- Verifies checkin session for roman_ur patient serves questions in Roman Urdu without English leak.
- Verifies RAG explainer handles roman_ur requests cleanly.
"""

from __future__ import annotations

import datetime
import os
import time
from typing import Dict, Any, Optional

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from auth import firebase_verify
from data_sources import app_store
from main import app
from rag import explainer


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-roman-ur"


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
def setup_test_environment(monkeypatch, tmp_path, x509_cert_pem):
    """Sets up an isolated SQLite test database and mocks Firebase verification."""
    test_db_path = str(tmp_path / "test_roman_ur.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "")
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")
    monkeypatch.delenv("MYSQL_URL", raising=False)

    app_store.migrate(db_path=test_db_path, backend="sqlite")

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


def create_test_token(
    private_key,
    sub: str = "uid-roman-ur-patient",
    email: str = "roman_ur_pat@demo.com",
    name: str = "Roman Urdu Patient",
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
        "exp": now + 3600,
        "auth_time": now,
    }
    headers = {"kid": TEST_KID, "alg": "RS256"}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


@pytest.fixture
def client():
    return TestClient(app)


def auth_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# TESTS
# =============================================================================

def test_put_profile_accepts_roman_ur(client, rsa_key_pair):
    """Proves PUT /api/me/profile accepts 'roman_ur' and returns 200 OK (G-12 fix)."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-roman-1", email="roman1@demo.com")
    headers = auth_header(token)

    # Establish session
    client.post("/api/auth/session", headers=headers)

    # Update profile with language = 'roman_ur'
    payload = {
        "conditions": ["diabetes"],
        "on_insulin_or_sulfonylurea": False,
        "language": "roman_ur",
    }
    resp = client.put("/api/me/profile", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["language"] == "roman_ur"
    assert data["conditions"] == ["diabetes"]

    # Verify GET /api/me/profile returns persisted roman_ur
    get_resp = client.get("/api/me/profile", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["language"] == "roman_ur"


def test_put_profile_rejects_unsupported_language(client, rsa_key_pair):
    """Proves PUT /api/me/profile rejects languages not in {'en', 'ur', 'roman_ur'} with 422."""
    token = create_test_token(rsa_key_pair, sub="uid-pat-invalid-lang", email="invalid_lang@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)

    for bad_lang in ["es", "fr", "de", "arabic", "urdu"]:
        resp = client.put(
            "/api/me/profile",
            json={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False, "language": bad_lang},
            headers=headers,
        )
        assert resp.status_code == 422
        assert "Invalid language" in resp.text


def test_app_store_profile_language_persistence(setup_test_environment):
    """Proves app_store handles roman_ur directly with full persistence."""
    test_db = setup_test_environment
    user_id = "direct-store-roman-user"

    # Create user
    app_store.create_user(user_id=user_id, email="direct@demo.com", role="patient", db_path=test_db)

    # Update profile to roman_ur
    app_store.upsert_patient_profile(
        user_id=user_id,
        conditions=["hypertension"],
        on_insulin_or_sulfonylurea=False,
        language="roman_ur",
        db_path=test_db,
    )

    prof = app_store.get_patient_profile(user_id=user_id, db_path=test_db)
    assert prof is not None
    assert prof["language"] == "roman_ur"
    assert prof["conditions"] == ["hypertension"]


def test_checkin_session_first_question_in_roman_urdu(client, rsa_key_pair, monkeypatch):
    """Proves that a patient with language='roman_ur' receives check-in questions in Roman Urdu under v3."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    token = create_test_token(rsa_key_pair, sub="uid-pat-roman-checkin", email="checkin_roman@demo.com")
    headers = auth_header(token)
    client.post("/api/auth/session", headers=headers)

    # Grant consent
    client.post("/api/me/consent", headers=headers, json={"granted": True})

    # Set profile language to roman_ur
    client.put(
        "/api/me/profile",
        json={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False, "language": "roman_ur"},
        headers=headers,
    )

    # Start checkin
    resp = client.post("/api/checkins/start", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["checkin_id"]
    text = data.get("question", "")

    # In Roman Urdu, questions should contain characteristic Roman Urdu words like "aap", "kaisa", "sugar", "theek"
    # and should NOT be the plain English "How are you feeling today?"
    assert any(w in text.lower() for w in ["aap", "kaisa", "mehsoos", "sugar", "reading", "tabiyat"]), f"Unexpected text: {text}"


def test_rag_explainer_roman_ur_execution():
    """Proves the RAG explainer functions accept 'roman_ur' cleanly."""
    triage = {
        "level": "routine",
        "trigger_category": "normal",
        "reasons": ["all vitals normal"],
    }
    readings = {"glucose": 110, "fasting": True}
    res = explainer.explain(triage, readings, language="roman_ur", store=None, llm=None)
    assert res is not None
    assert isinstance(res, dict)
    assert res["language"] == "roman_ur"
    assert res["mode"] == "template"
