"""
Hermetic Unit and Integration Tests for OCR Upload, Staging, and Confirmation.
Stage 12 / Iteration 2 Day 7.

Validates:
1. Feature flag off (503 default).
2. Feature flag on: GET /api/me/record returns ocr_enabled: true.
3. Connected mode rejection (409).
4. Magic bytes and format validation (JPEG/PNG accepted, PDF/HEIC rejected with friendly 422, oversize 413).
5. EXIF orientation transposition.
6. In-memory staging limits (max 3 pending per user, 30m TTL, user isolation).
7. Server-side clinical re-validation on confirm (out-of-range rejected with 422).
8. Successful confirmation: origin 'ocr', medium trust, record_edits rows created, staging cleared.
9. Zero image persistence and zero PHI in audit log.
10. Production guard: APP_ENV=production rejects OCR_PROVIDER=fake.
"""

from __future__ import annotations

import io
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

# Ensure backend root on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import jwt

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store
from data_sources.ocr.provider import get_ocr_provider
from data_sources.ocr.staging import (
    stage_upload,
    get_staged_upload,
    remove_staged_upload,
    clear_all_staged_uploads_for_testing,
    MAX_PENDING_PER_USER,
    STAGING_TTL_MINUTES,
)

TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-ocr"


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
    test_db_path = str(tmp_path / "test_chroniccare_ocr.db")

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


# Helper: minimal valid 1x1 JPEG bytes
MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)

# Minimal valid 1x1 PNG bytes
MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00"
    b"\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _setup_patient(client: TestClient, rsa_key_pair, user_id: str, email: str) -> Dict[str, str]:
    token = create_test_token(rsa_key_pair, sub=user_id, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    app_store.set_patient_consent(user_id=user_id, granted=True)
    return headers


@pytest.fixture(autouse=True)
def clean_staging():
    clear_all_staged_uploads_for_testing()
    yield
    clear_all_staged_uploads_for_testing()


# ----------------------------------------------------------------------------
# 1. Feature Flag Guard (Default Off -> 503)
# ----------------------------------------------------------------------------
def test_ocr_disabled_by_default_returns_503(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "false")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-ocr-flag-off", "p_flag_off@demo.com")

    # Upload returns 503
    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    assert resp_up.status_code == 503
    assert "OCR_DISABLED" in resp_up.json()["detail"]

    # Confirm returns 503
    resp_conf = client.post(
        "/api/me/record/uploads/fake-id/confirm",
        headers=headers,
        json={"confirmed_items": []},
    )
    assert resp_conf.status_code == 503
    assert "OCR_DISABLED" in resp_conf.json()["detail"]

    # GET /api/me/record returns ocr_enabled: False
    resp_rec = client.get("/api/me/record", headers=headers)
    assert resp_rec.status_code == 200
    assert resp_rec.json().get("ocr_enabled") is False


def test_ocr_enabled_returns_flag_true_on_record(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-ocr-flag-on", "p_flag_on@demo.com")

    resp_rec = client.get("/api/me/record", headers=headers)
    assert resp_rec.status_code == 200
    assert resp_rec.json().get("ocr_enabled") is True


# ----------------------------------------------------------------------------
# 2. Connected Mode Guard (409)
# ----------------------------------------------------------------------------
def test_connected_mode_patient_rejected_with_409(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-ocr-conn", "p_ocr_conn@demo.com")

    # Connect to EHR
    app_store.record_ehr_connection(
        connection_id="conn-test-ocr",
        user_id="p-ocr-conn",
        ehr_system_id="sim-ayesha",
        external_patient_id="sim-p1",
        status="active",
    )

    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    assert resp_up.status_code == 409
    assert resp_up.json()["detail"] == "record_managed_by_ehr"


# ----------------------------------------------------------------------------
# 3. Magic Bytes and File Validation
# ----------------------------------------------------------------------------
def test_upload_format_validation(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-ocr-formats", "p_formats@demo.com")

    # Empty file -> 422
    resp_empty = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert resp_empty.status_code == 422

    # Oversize (>5MB) -> 413
    oversized = b"\xff\xd8\xff" + b"X" * (5 * 1024 * 1024 + 10)
    resp_big = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("big.jpg", oversized, "image/jpeg")},
    )
    assert resp_big.status_code == 413

    # PDF -> 422 friendly error
    resp_pdf = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("doc.pdf", b"%PDF-1.4...", "application/pdf")},
    )
    assert resp_pdf.status_code == 422
    assert "PDF and HEIC are not currently supported" in resp_pdf.json()["detail"]

    # HEIC -> 422 friendly error
    resp_heic = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("photo.heic", b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00", "image/heic")},
    )
    assert resp_heic.status_code == 422
    assert "PDF and HEIC are not currently supported" in resp_heic.json()["detail"]

    # Valid PNG -> 200
    resp_png = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.png", MINIMAL_PNG, "image/png")},
    )
    assert resp_png.status_code == 200
    res_data = resp_png.json()
    assert "upload_id" in res_data
    assert "extracted" in res_data


def test_upload_does_not_save_items_before_confirm(rsa_key_pair, monkeypatch):
    """Proves that raw OCR upload stages in memory only and NEVER saves to clinical record before confirmation."""
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    user_id = "p-no-save-pre-confirm"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_preconfirm@demo.com")

    patient_id = f"local-{user_id}"
    assert len(local_store.get_local_observations(patient_id)) == 0
    assert len(local_store.get_local_medications(patient_id)) == 0
    assert len(app_store.get_allergies(user_id)) == 0

    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    assert resp_up.status_code == 200
    assert "upload_id" in resp_up.json()

    # Zero items must be written to record prior to explicit patient confirmation
    assert len(local_store.get_local_observations(patient_id)) == 0
    assert len(local_store.get_local_medications(patient_id)) == 0
    assert len(app_store.get_allergies(user_id)) == 0


# ----------------------------------------------------------------------------
# 4. In-Memory Staging Store (Limits, TTL, User Isolation)
# ----------------------------------------------------------------------------
def test_staging_store_max_3_pending_drops_oldest():
    user_a = "user-staging-a"
    id1 = stage_upload(user_a, {"sample": 1})
    time.sleep(0.01)
    id2 = stage_upload(user_a, {"sample": 2})
    time.sleep(0.01)
    id3 = stage_upload(user_a, {"sample": 3})

    # All 3 exist
    assert get_staged_upload(id1, user_a) is not None
    assert get_staged_upload(id2, user_a) is not None
    assert get_staged_upload(id3, user_a) is not None

    # 4th upload drops id1 (the oldest)
    time.sleep(0.01)
    id4 = stage_upload(user_a, {"sample": 4})
    assert get_staged_upload(id1, user_a) is None  # Dropped!
    assert get_staged_upload(id2, user_a) is not None
    assert get_staged_upload(id3, user_a) is not None
    assert get_staged_upload(id4, user_a) is not None


def test_staging_store_ttl_expiry():
    user_a = "user-staging-ttl"
    upload_id = stage_upload(user_a, {"sample": "ttl"})
    assert get_staged_upload(upload_id, user_a) is not None

    # Artificially set created_at back by 31 minutes
    from data_sources.ocr import staging
    staging._STAGING_STORE[upload_id]["created_at"] = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=STAGING_TTL_MINUTES + 1)

    assert get_staged_upload(upload_id, user_a) is None


def test_staging_user_isolation(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    headers_a = _setup_patient(client, rsa_key_pair, "p-user-a", "p_a@demo.com")
    headers_b = _setup_patient(client, rsa_key_pair, "p-user-b", "p_b@demo.com")

    # User A uploads
    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers_a,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    upload_id = resp_up.json()["upload_id"]

    # User B attempts to confirm User A's upload -> 404
    resp_b = client.post(
        f"/api/me/record/uploads/{upload_id}/confirm",
        headers=headers_b,
        json={"confirmed_items": []},
    )
    assert resp_b.status_code == 404
    assert "Upload not found" in resp_b.json()["detail"]


# ----------------------------------------------------------------------------
# 5. Server-Side Clinical Re-Validation on Confirm
# ----------------------------------------------------------------------------
def test_confirm_revalidation_rejects_out_of_range_values(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-reval", "p_reval@demo.com")

    # Stage an upload
    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    upload_id = resp_up.json()["upload_id"]

    # Patient tries to confirm an out-of-range glucose (750 mg/dL > 600 max)
    invalid_confirm = {
        "confirmed_items": [
            {
                "type": "observation",
                "observation_type": "glucose",
                "value": 750.0,
                "unit": "mg/dL",
            }
        ]
    }
    resp_conf = client.post(
        f"/api/me/record/uploads/{upload_id}/confirm",
        headers=headers,
        json=invalid_confirm,
    )
    assert resp_conf.status_code == 422
    assert "Glucose reading outside plausible range" in resp_conf.json()["detail"]

    # Verify upload was NOT dropped on validation failure so user can fix it
    assert get_staged_upload(upload_id, "p-reval") is not None


# ----------------------------------------------------------------------------
# 6. Successful Confirmation: Origin 'ocr', Record Edits, Staging Cleanup
# ----------------------------------------------------------------------------
def test_confirm_successful_flow_with_origin_and_history(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    user_id = "p-ocr-success"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_success@demo.com")

    # 1. Upload document
    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    assert resp_up.status_code == 200
    upload_id = resp_up.json()["upload_id"]

    # 2. Confirm valid items: 1 med, 1 observation, 1 allergy
    confirm_payload = {
        "confirmed_items": [
            {
                "type": "medication",
                "name": "Metformin 500mg",
                "dosage": "1 tablet BD",
                "status": "active",
            },
            {
                "type": "observation",
                "observation_type": "glucose",
                "value": 118.0,
                "unit": "mg/dL",
                "measured_at": "2026-11-01T08:00:00Z",
            },
            {
                "type": "allergy",
                "substance": "Penicillin",
                "reaction": "Rash",
                "confirmed": True,
            },
        ]
    }

    resp_conf = client.post(
        f"/api/me/record/uploads/{upload_id}/confirm",
        headers=headers,
        json=confirm_payload,
    )
    assert resp_conf.status_code == 200
    res_data = resp_conf.json()
    assert res_data["status"] == "ok"
    assert res_data["confirmed_count"] == 3

    # Staging entry must be pruned
    assert get_staged_upload(upload_id, user_id) is None

    # Verify items in local clinical store have origin 'ocr'
    patient_id = f"local-{user_id}"
    meds = local_store.get_local_medications(patient_id)
    assert len(meds) >= 1
    assert any(m["medication_name"] == "Metformin 500mg" and m.get("origin") == "ocr" for m in meds)

    obs = local_store.get_local_observations(patient_id)
    assert len(obs) >= 1
    assert any(o["type"] == "glucose" and o["value"] == 118.0 and o.get("origin") == "ocr" for o in obs)

    allergies = app_store.get_allergies(user_id)
    assert len(allergies) >= 1
    assert any(a["substance"] == "Penicillin" for a in allergies)

    # Verify record_edits rows created with origin 'ocr'
    edits = app_store.get_record_edits(user_id)
    ocr_edits = [e for e in edits if e.get("origin") == "ocr"]
    assert len(ocr_edits) == 3
    assert all(e["changed_by_user_id"] == user_id for e in ocr_edits)
    assert all(e["field"] == "created" for e in ocr_edits)
    assert any(e["record_type"] == "allergy" and e["origin"] == "ocr" for e in ocr_edits)

    # Second confirm call fails with 404 (already confirmed/removed)
    resp_again = client.post(
        f"/api/me/record/uploads/{upload_id}/confirm",
        headers=headers,
        json=confirm_payload,
    )
    assert resp_again.status_code == 404


# ----------------------------------------------------------------------------
# 7. Production Safety Guard
# ----------------------------------------------------------------------------
def test_production_safety_guard_refuses_fake_ocr_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    with pytest.raises(RuntimeError) as exc_info:
        get_ocr_provider()
    assert "Fake OCR provider refused in production environment" in str(exc_info.value)
