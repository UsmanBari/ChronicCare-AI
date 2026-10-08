"""
Hermetic Unit & Integration Tests for Voice Input Transcription (Stage 8 Part A).

Covers:
- Success path: audio forwarded to Groq, transcript returned.
- 429 Too Many Requests from Groq: friendly "voice is busy, please type".
- Timeout from Groq: handled with 504 Gateway Timeout.
- 5xx Server Error retry: retries once on 5xx before failing or succeeding.
- Oversize audio (> 5 MB): rejected with 413.
- Empty audio (0 bytes): rejected with 400.
- Wrong content type: rejected with 400.
- Unauthenticated request: rejected with 401.
- Voice disabled in profile: rejected with 403.
- GROQ_API_KEY missing / unconfigured: returns 503 with clear code/message.
- Rate limit per user (10 requests/min): 11th request rejected with 429.
- Zero secret leaks: asserts GROQ_API_KEY never appears in response body, logs, or errors.
"""

import os
import time
import logging
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

from main import app, _voice_rate_limit_store
from auth import firebase_verify
from data_sources import app_store


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-1"
TEST_GROQ_KEY = "FAKE_STT_KEY_FOR_TESTS"


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
    monkeypatch.setenv("GROQ_API_KEY", TEST_GROQ_KEY)
    monkeypatch.setenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")

    _voice_rate_limit_store.clear()
    app_store.migrate(db_path=test_db_path, backend="sqlite")

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


@pytest.fixture
def client():
    return TestClient(app)


def create_test_token(
    private_key,
    sub: str = "uid-patient-voice",
    email: str = "patient_voice@demo.com",
    name: str = "Voice Patient",
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "name": name,
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


def _setup_patient_user(client, token, voice_enabled=True):
    # Session init
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    # Set profile
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "conditions": ["diabetes"],
        "on_insulin_or_sulfonylurea": False,
        "language": "en",
        "voice_enabled": voice_enabled,
    })


class MockResponse:
    def __init__(self, status_code: int, json_data: dict):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


def test_voice_transcribe_success(client, rsa_key_pair, monkeypatch):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    calls = []
    def mock_post(url, headers=None, data=None, files=None, timeout=None):
        calls.append({"url": url, "headers": headers, "data": data, "files": files, "timeout": timeout})
        return MockResponse(200, {"text": "My blood pressure is 140 over 90"})

    monkeypatch.setattr(requests, "post", mock_post)

    audio_data = b"fake-webm-audio-bytes-12345"
    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
        content=audio_data,
    )
    assert resp.status_code == 200
    assert resp.json() == {"text": "My blood pressure is 140 over 90"}
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert calls[0]["headers"]["Authorization"] == f"Bearer {TEST_GROQ_KEY}"
    assert calls[0]["data"]["model"] == "whisper-large-v3-turbo"
    assert calls[0]["data"]["language"] == "en"


def test_voice_transcribe_429_friendly_message(client, rsa_key_pair, monkeypatch):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    def mock_post(url, headers=None, data=None, files=None, timeout=None):
        return MockResponse(429, {"error": "Rate limit exceeded"})

    monkeypatch.setattr(requests, "post", mock_post)

    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
        content=b"sample-audio",
    )
    assert resp.status_code == 429
    assert resp.json()["detail"] == "voice is busy, please type"


def test_voice_transcribe_timeout(client, rsa_key_pair, monkeypatch):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    def mock_post(url, headers=None, data=None, files=None, timeout=None):
        raise requests.Timeout("Connection timed out")

    monkeypatch.setattr(requests, "post", mock_post)

    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
        content=b"sample-audio",
    )
    assert resp.status_code == 504
    assert "timed out" in resp.json()["detail"]


def test_voice_transcribe_5xx_retry_then_success(client, rsa_key_pair, monkeypatch):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    attempts = 0
    def mock_post(url, headers=None, data=None, files=None, timeout=None):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return MockResponse(500, {"error": "Internal Server Error"})
        return MockResponse(200, {"text": "one thirty over eighty"})

    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
        content=b"sample-audio",
    )
    assert resp.status_code == 200
    assert resp.json() == {"text": "one thirty over eighty"}
    assert attempts == 2


def test_voice_transcribe_oversize_rejected(client, rsa_key_pair):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    # > 5 MB
    large_audio = b"0" * (5 * 1024 * 1024 + 10)
    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
        content=large_audio,
    )
    assert resp.status_code == 413
    assert "too large" in resp.json()["detail"].lower()


def test_voice_transcribe_empty_file_rejected(client, rsa_key_pair):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
        content=b"",
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_voice_transcribe_wrong_content_type(client, rsa_key_pair):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "text/plain",
        },
        content=b"some-text",
    )
    assert resp.status_code == 400
    assert "invalid audio content type" in resp.json()["detail"].lower()


def test_voice_transcribe_unauthenticated(client):
    resp = client.post(
        "/api/voice/transcribe",
        headers={"Content-Type": "audio/webm"},
        content=b"sample-audio",
    )
    assert resp.status_code == 401


def test_voice_transcribe_disabled_in_profile(client, rsa_key_pair):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=False)

    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
        content=b"sample-audio",
    )
    assert resp.status_code == 403
    assert "not enabled" in resp.json()["detail"].lower()


def test_voice_transcribe_no_key_configured(client, rsa_key_pair, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    resp = client.post(
        "/api/voice/transcribe",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/webm",
        },
        content=b"sample-audio",
    )
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"].lower()


def test_voice_transcribe_per_user_rate_limit(client, rsa_key_pair, monkeypatch):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    def mock_post(url, headers=None, data=None, files=None, timeout=None):
        return MockResponse(200, {"text": "hello"})

    monkeypatch.setattr(requests, "post", mock_post)

    # Make 10 requests within 60s
    for _ in range(10):
        r = client.post(
            "/api/voice/transcribe",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "audio/webm"},
            content=b"audio-bytes",
        )
        assert r.status_code == 200

    # 11th request is rejected by per-user rate limiter
    r11 = client.post(
        "/api/voice/transcribe",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "audio/webm"},
        content=b"audio-bytes",
    )
    assert r11.status_code == 429
    assert r11.json()["detail"] == "voice is busy, please type"


def test_voice_secret_key_never_leaked_in_responses_or_logs(client, rsa_key_pair, monkeypatch, caplog):
    token = create_test_token(rsa_key_pair)
    _setup_patient_user(client, token, voice_enabled=True)

    def mock_post(url, headers=None, data=None, files=None, timeout=None):
        return MockResponse(500, {"error": "Simulated error"})

    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    with caplog.at_level(logging.DEBUG):
        resp = client.post(
            "/api/voice/transcribe",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "audio/webm",
            },
            content=b"sample-audio",
        )

    # Assert secret never appears in HTTP response text or headers
    assert TEST_GROQ_KEY not in resp.text
    for h, v in resp.headers.items():
        assert TEST_GROQ_KEY not in v

    # Assert secret never appears in captured log output
    assert TEST_GROQ_KEY not in caplog.text
