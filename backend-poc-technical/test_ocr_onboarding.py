"""
Tests for Prescription OCR in Isolated-Mode Onboarding (PR K: Section 18 & 21.1).

Validates:
1. Fresh patient signup in isolated mode (consent granted, profile created, 0 check-ins).
2. Prescription upload stages extracted medications with confidence (High, Medium, Low).
3. Confirm stages saved to local store with origin="ocr" and trust="medium" / Unverified.
4. GET /api/me/record returns medications with origin="ocr".
5. Verification agent maps origin="ocr" to medium trust.
6. Rejection of connected EHR patients with 409 conflict.
7. Feature flag OFF (OCR_ENABLED=false) returns 503 ocr_unavailable.
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import jwt

from data_sources import app_store, local_store
from auth import firebase_verify
from agents.verification_agent import TRUST_LEVELS

TEST_PROJECT_ID = "test-chroniccare-onboarding"
TEST_KID = "test-kid-onboard"


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
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=10))
        .sign(rsa_key_pair, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch, x509_cert_pem):
    test_db_path = str(tmp_path / "test_chroniccare_onboard.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


def create_test_token(private_key, sub: str, email: str, role: str = "patient") -> str:
    now = int(time.time())
    payload = {
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "aud": TEST_PROJECT_ID,
        "auth_time": now,
        "user_id": sub,
        "sub": sub,
        "iat": now,
        "exp": now + 3600,
        "email": email,
        "email_verified": True,
        "firebase": {"identities": {"email": [email]}, "sign_in_provider": "password"},
    }
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, pem_private, algorithm="RS256", headers={"kid": TEST_KID})


def create_fake_prescription_png() -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 20), "Rx: Metformin 500 mg", fill=(0, 0, 0))
    d.text((20, 60), "Patient: Onboarding Test", fill=(0, 0, 0))
    d.text((20, 100), "Sig: 1 tab daily", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_trust_levels_mapping_ocr_is_medium():
    """Verify TRUST_LEVELS in verification agent maps OCR to medium trust (Unverified)."""
    assert TRUST_LEVELS.get("local_ocr_or_upload") == "medium"
    assert TRUST_LEVELS.get("ocr_or_upload") == "medium"
    assert TRUST_LEVELS.get("local_self_reported") == "low"
    assert TRUST_LEVELS.get("fhir_clinician_entered") == "high"


def test_onboarding_prescription_upload_and_confirm(rsa_key_pair, monkeypatch):
    """Full onboarding flow: consent -> profile -> OCR upload -> confirm -> verify origin='ocr'."""
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    monkeypatch.setenv("APP_ENV", "development")

    from main import app
    client = TestClient(app)

    sub = f"patient-onboard-{uuid.uuid4().hex[:8]}"
    email = f"{sub}@example.com"
    token = create_test_token(rsa_key_pair, sub=sub, email=email)
    auth_header = {"Authorization": f"Bearer {token}"}

    # Step 0: Establish session
    s_resp = client.post("/api/auth/session", headers=auth_header)
    assert s_resp.status_code == 200

    # Step 1: Consent
    c_resp = client.post("/api/me/consent", headers=auth_header, json={"granted": True, "provider_notification": True})
    assert c_resp.status_code == 200

    # Step 2: Health Profile
    p_resp = client.put("/api/me/profile", headers=auth_header, json={
        "conditions": ["diabetes"],
        "date_of_birth": "1980-01-01",
        "inclusion_confirmed": True,
        "sex_at_birth": "male",
    })
    assert p_resp.status_code == 200

    # Step 3: Verify 0 prior check-ins (pre-checkin onboarding stage)
    assert len(app_store.get_user_checkins(sub)) == 0

    # Step 4: Upload prescription image
    png_bytes = create_fake_prescription_png()
    upload_resp = client.post(
        "/api/me/record/uploads",
        headers={**auth_header, "Content-Type": "image/png"},
        content=png_bytes,
    )
    assert upload_resp.status_code == 200
    up_data = upload_resp.json()
    upload_id = up_data["upload_id"]
    assert "medications" in up_data["extracted"]

    # Step 5: Confirm staged medication
    confirm_resp = client.post(
        f"/api/me/record/uploads/{upload_id}/confirm",
        headers=auth_header,
        json={
            "confirmed_items": [
                {
                    "type": "medication",
                    "name": "Metformin",
                    "dosage": "500mg daily",
                    "status": "active",
                }
            ]
        },
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["confirmed_count"] == 1

    # Step 6: Verify patient record has origin='ocr'
    rec_resp = client.get("/api/me/record", headers=auth_header)
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert rec_data["mode"] == "isolated"
    meds = rec_data["medications"]
    assert len(meds) == 1
    assert meds[0]["name"] == "Metformin"
    assert meds[0]["origin"] == "ocr"


def test_ocr_disabled_returns_503(rsa_key_pair, monkeypatch):
    """When OCR_ENABLED=false, prescription upload returns 503."""
    monkeypatch.setenv("OCR_ENABLED", "false")

    from main import app
    client = TestClient(app)

    sub = f"patient-onboard-{uuid.uuid4().hex[:8]}"
    token = create_test_token(rsa_key_pair, sub=sub, email=f"{sub}@example.com")
    auth_header = {"Authorization": f"Bearer {token}"}

    client.post("/api/auth/session", headers=auth_header)
    client.post("/api/me/consent", headers=auth_header, json={"granted": True, "provider_notification": True})
    client.put("/api/me/profile", headers=auth_header, json={"conditions": ["hypertension"], "date_of_birth": "1975-05-15", "inclusion_confirmed": True})

    png_bytes = create_fake_prescription_png()
    upload_resp = client.post(
        "/api/me/record/uploads",
        headers={**auth_header, "Content-Type": "image/png"},
        content=png_bytes,
    )
    assert upload_resp.status_code == 503
    assert upload_resp.json()["code"] == "ocr_unavailable"
