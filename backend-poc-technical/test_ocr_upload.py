"""
Hermetic Unit and Integration Tests for OCR Upload, Staging, and Confirmation.
Stage 12 / Iteration 2 Day 7.

Validates:
1. Feature flag off (503 default).
2. Feature flag on: GET /api/me/record returns ocr_enabled: true only when provider available.
3. Connected mode rejection (409).
4. Magic bytes and format validation (JPEG/PNG accepted, PDF/HEIC rejected with 415, unreadable 415, oversize 413).
5. In-memory staging limits (max 3 pending per user, 30m TTL, user isolation).
6. Server-side clinical re-validation on confirm (out-of-range rejected with structured 422).
7. Successful confirmation: origin 'ocr', medium trust, record_edits rows created, staging cleared.
8. Fixed vs Unchanged: fixed value records staged extracted value in old_value and reason 'patient corrected OCR value'; unchanged records old_value null and reason 'ocr_confirmed'.
9. All-or-nothing atomicity on confirm failure: zero rows written if any item fails.
10. Double confirm rejected with 404.
11. User isolation: cross-user confirm rejected with 404.
12. Zero image bytes persisted in any DB column (scanned for binary & base64).
13. Audit logs hold counts only (no filenames, no clinical values).
14. Provider failure handling: import failure -> 503 ocr_unavailable; provider extract error -> 502 ocr_provider_error (logging type only).
15. Production guard: APP_ENV=production rejects OCR_PROVIDER=fake.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import sqlite3
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

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
import jwt

import main
from main import app
from auth import firebase_verify
from data_sources import app_store, local_store
from data_sources.ocr.provider import get_ocr_provider
from data_sources.ocr.fake_provider import FakeOcrProvider
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
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=10))
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
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)

# Helper: minimal valid 1x1 PNG bytes (decodable without PIL dependency at import time)
MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?"
    b"\x00\x05\xfe\x02\xfe\r\xefF\xb8\x00\x00\x00\x00IEND\xaeB`\x82"
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
    assert resp_up.json().get("code") == "ocr_unavailable"

    # Confirm returns 503
    resp_conf = client.post(
        "/api/me/record/uploads/fake-id/confirm",
        headers=headers,
        json={"confirmed_items": []},
    )
    assert resp_conf.status_code == 503
    assert resp_conf.json().get("code") == "ocr_unavailable"

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
# FIX 1: Provider Errors Handled (503 on uninstalled provider, 502 on extract failure)
# ----------------------------------------------------------------------------
def test_provider_import_failure_returns_503_and_record_ocr_disabled(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "rapidocr")
    # Simulate RapidOCR not installed
    import data_sources.ocr.provider as ocr_provider_mod
    monkeypatch.setattr(ocr_provider_mod, "check_ocr_provider_available", lambda p=None: False)

    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-ocr-no-rapid", "p_norapid@demo.com")

    # GET /api/me/record must report ocr_enabled: False because engine can't be loaded
    resp_rec = client.get("/api/me/record", headers=headers)
    assert resp_rec.status_code == 200
    assert resp_rec.json().get("ocr_enabled") is False

    # POST /api/me/record/uploads returns 503 ocr_unavailable
    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    assert resp_up.status_code == 503
    assert resp_up.json().get("code") == "ocr_unavailable"


def test_provider_exception_returns_502_and_logs_type_only(rsa_key_pair, monkeypatch, caplog):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-ocr-prov-err", "p_proverr@demo.com")

    # Monkeypatch the provider's extract method to raise an unexpected runtime error containing secret text
    secret_text = "SECRET_DATABASE_CREDENTIAL_XYZ"

    def crashing_extract(self, image_bytes):
        raise RuntimeError(f"OCR internal engine crashed: {secret_text}")

    monkeypatch.setattr(FakeOcrProvider, "extract", crashing_extract)

    with caplog.at_level(logging.ERROR):
        resp_up = client.post(
            "/api/me/record/uploads",
            headers=headers,
            files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
        )

    # Must return 502 with structured code
    assert resp_up.status_code == 502
    assert resp_up.json().get("code") == "ocr_provider_error"

    # Verify logs contain the exception TYPE but NEVER the exception message text
    log_text = caplog.text
    assert "RuntimeError" in log_text
    assert secret_text not in log_text


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
# FIX 2: Magic Bytes and File Validation (415 for unreadable, wrong type, PDF, HEIC)
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

    # PDF -> 415 friendly error
    resp_pdf = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("doc.pdf", b"%PDF-1.4...", "application/pdf")},
    )
    assert resp_pdf.status_code == 415
    assert "PDF and HEIC are not currently supported" in resp_pdf.json()["detail"]

    # HEIC -> 415 friendly error
    resp_heic = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("photo.heic", b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00", "image/heic")},
    )
    assert resp_heic.status_code == 415
    assert "PDF and HEIC are not currently supported" in resp_heic.json()["detail"]

    # Unsupported MIME / wrong type -> 415
    resp_txt = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("note.txt", b"plain text content", "text/plain")},
    )
    assert resp_txt.status_code == 415

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


def test_corrupted_image_magic_bytes_rejected_as_415(rsa_key_pair, monkeypatch):
    """Bytes that start with JPEG magic but fail Pillow decoding must be rejected with 415 image_unreadable."""
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-corrupted", "p_corrupt@demo.com")

    # Starts with JPEG magic \xff\xd8\xff followed by complete garbage
    corrupted_bytes = b"\xff\xd8\xff\xe0GARBAGE_DATA_CANNOT_BE_DECODED_BY_PILLOW"
    resp = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("corrupt.jpg", corrupted_bytes, "image/jpeg")},
    )
    assert resp.status_code == 415
    assert resp.json().get("code") == "image_unreadable"


def test_pillow_uninstalled_returns_503(rsa_key_pair, monkeypatch):
    """If Pillow is not installed, upload returns 503 ocr_unavailable."""
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-no-pil", "p_nopil@demo.com")

    # Force ImportError when importing PIL
    real_import = __import__
    def fake_import(name, *args, **kwargs):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("No module named PIL")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    resp = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    assert resp.status_code == 503
    assert resp.json().get("code") == "ocr_unavailable"


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
    staging._STAGING_STORE[upload_id]["created_at"] = datetime.now(timezone.utc) - timedelta(minutes=STAGING_TTL_MINUTES + 1)

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
# 5. Server-Side Clinical Re-Validation on Confirm (FIX 5)
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
    err_detail = resp_conf.json()
    assert err_detail.get("code") == "invalid_item"
    assert err_detail.get("reason_code") == "out_of_range"
    assert err_detail.get("item_index") == 0

    # Verify upload was NOT dropped on validation failure so user can fix it
    assert get_staged_upload(upload_id, "p-reval") is not None


# ----------------------------------------------------------------------------
# FIX 3: Fixed vs Unchanged Values in Record Edits
# ----------------------------------------------------------------------------
def test_confirm_fixed_vs_unchanged_history(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    user_id = "p-ocr-history-diff"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_diff@demo.com")

    # 1. Upload document
    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    assert resp_up.status_code == 200
    up_data = resp_up.json()
    upload_id = up_data["upload_id"]
    extracted = up_data["extracted"]

    # Extract items from extracted categories
    obs_item = next(o for o in extracted["observations"] if o["observation_type"] == "glucose")
    med_item = extracted["medications"][0]
    all_item = extracted["allergies"][0]

    # Patient changes glucose value from extracted (118.0) to 135.0 (FIXED)
    # Medication remains unchanged (UNCHANGED)
    # Allergy remains unchanged (UNCHANGED)
    confirm_payload = {
        "confirmed_items": [
            {
                "id": obs_item["id"],
                "type": "observation",
                "observation_type": obs_item["observation_type"],
                "value": 135.0,  # Fixed by patient!
                "unit": obs_item["unit"],
                "measured_at": "2026-11-01T08:00:00Z",
            },
            {
                "id": med_item["id"],
                "type": "medication",
                "name": med_item["name"],  # Unchanged!
                "dosage": med_item["dosage"],
                "status": "active",
            },
            {
                "id": all_item["id"],
                "type": "allergy",
                "substance": all_item["substance"],  # Unchanged!
                "reaction": all_item["reaction"],
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

    # Inspect record_edits rows
    edits = app_store.get_record_edits(user_id)
    assert len(edits) == 3

    # Fixed observation edit row: old_value must be the staged extracted value, reason must be patient corrected OCR value
    obs_edits = [e for e in edits if e["record_type"] == "observation"]
    assert len(obs_edits) == 1
    assert float(obs_edits[0]["old_value"]) == float(obs_item["value"])
    assert obs_edits[0]["new_value"]["value"] == 135.0
    assert obs_edits[0]["reason"] == "patient corrected OCR value"
    assert obs_edits[0]["origin"] == "ocr"

    # Unchanged medication edit row: old_value must be None, reason must be ocr_confirmed
    med_edits = [e for e in edits if e["record_type"] == "medication"]
    assert len(med_edits) == 1
    assert med_edits[0]["old_value"] is None
    assert med_edits[0]["new_value"]["name"] == med_item["name"]
    assert med_edits[0]["reason"] == "ocr_confirmed"
    assert med_edits[0]["origin"] == "ocr"

    # Unchanged allergy edit row: old_value must be None, reason must be ocr_confirmed
    all_edits = [e for e in edits if e["record_type"] == "allergy"]
    assert len(all_edits) == 1
    assert all_edits[0]["old_value"] is None
    assert all_edits[0]["new_value"]["substance"] == all_item["substance"]
    assert all_edits[0]["reason"] == "ocr_confirmed"
    assert all_edits[0]["origin"] == "ocr"


# ----------------------------------------------------------------------------
# FIX 4: All-or-Nothing Atomicity on Confirm Failure
# ----------------------------------------------------------------------------
def test_all_or_nothing_confirm_rollback_on_failure(rsa_key_pair, monkeypatch):
    """If saving any item in the batch fails, the entire transaction rolls back cleanly with 0 rows saved."""
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app, raise_server_exceptions=False)
    user_id = "p-rollback-atomic"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_rollback@demo.com")

    # Upload document
    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    upload_id = resp_up.json()["upload_id"]

    # Monkeypatch the 2nd insertion in main module to raise an unexpected error
    def failing_add_medication(*args, **kwargs):
        raise RuntimeError("Simulated DB disk failure during batch insertion")

    monkeypatch.setattr(main, "add_local_medication", failing_add_medication)

    confirm_payload = {
        "confirmed_items": [
            {
                "type": "observation",
                "observation_type": "glucose",
                "value": 110.0,
                "unit": "mg/dL",
            },
            {
                "type": "medication",
                "name": "Metformin 500mg",
                "dosage": "1 tablet BD",
            },
            {
                "type": "allergy",
                "substance": "Aspirin",
            },
        ]
    }

    resp_conf = client.post(
        f"/api/me/record/uploads/{upload_id}/confirm",
        headers=headers,
        json=confirm_payload,
    )
    assert resp_conf.status_code == 500
    assert "rolled back" in resp_conf.json()["detail"]

    # Verify atomic rollback: ZERO rows in medications, observations, allergies, AND record_edits
    patient_id = f"local-{user_id}"
    assert len(local_store.get_local_observations(patient_id)) == 0
    assert len(local_store.get_local_medications(patient_id)) == 0
    assert len(app_store.get_allergies(user_id)) == 0
    assert len(app_store.get_record_edits(user_id)) == 0

    # Staged upload is preserved so patient does not lose their session
    assert get_staged_upload(upload_id, user_id) is not None


# ----------------------------------------------------------------------------
# FIX 4: Double Confirm Rejection (404)
# ----------------------------------------------------------------------------
def test_double_confirm_returns_404(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    user_id = "p-double-conf"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_double@demo.com")

    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    upload_id = resp_up.json()["upload_id"]

    payload = {"confirmed_items": [{"type": "observation", "observation_type": "glucose", "value": 100.0, "unit": "mg/dL"}]}

    resp1 = client.post(f"/api/me/record/uploads/{upload_id}/confirm", headers=headers, json=payload)
    assert resp1.status_code == 200

    # Second confirm -> 404
    resp2 = client.post(f"/api/me/record/uploads/{upload_id}/confirm", headers=headers, json=payload)
    assert resp2.status_code == 404


# ----------------------------------------------------------------------------
# FIX 4: Zero Image Bytes Anywhere (DB text columns scanned for binary & base64)
# ----------------------------------------------------------------------------
def test_zero_image_bytes_in_database(rsa_key_pair, monkeypatch, setup_test_environment):
    db_path = setup_test_environment
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    user_id = "p-zero-bytes"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_zerobytes@demo.com")

    # Upload and confirm
    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    upload_id = resp_up.json()["upload_id"]

    payload = {"confirmed_items": [{"type": "observation", "observation_type": "glucose", "value": 115.0, "unit": "mg/dL"}]}
    resp_conf = client.post(f"/api/me/record/uploads/{upload_id}/confirm", headers=headers, json=payload)
    assert resp_conf.status_code == 200

    # Scan entire SQLite DB file content and all text columns
    b64_img = base64.b64encode(MINIMAL_JPEG).decode("ascii")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    for tbl in tables:
        cursor.execute(f"PRAGMA table_info({tbl});")
        columns = [c[1] for c in cursor.fetchall()]
        for col in columns:
            cursor.execute(f"SELECT CAST({col} AS TEXT) FROM {tbl} WHERE {col} IS NOT NULL;")
            for (val,) in cursor.fetchall():
                if val:
                    assert b64_img not in val, f"Found base64 image bytes in {tbl}.{col}"
                    assert "JFIF" not in val, f"Found JFIF signature in {tbl}.{col}"
    conn.close()


# ----------------------------------------------------------------------------
# FIX 4: Audit Logs Contain Counts Only (No Values, No Filenames)
# ----------------------------------------------------------------------------
def test_audit_logs_contain_counts_only_no_phi_no_filename(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    user_id = "p-audit-counts"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_audit@demo.com")

    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("patient_secret_lab_scan.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    upload_id = resp_up.json()["upload_id"]

    payload = {
        "confirmed_items": [
            {
                "type": "observation",
                "observation_type": "glucose",
                "value": 125.0,
                "unit": "mg/dL",
            }
        ]
    }
    resp_conf = client.post(f"/api/me/record/uploads/{upload_id}/confirm", headers=headers, json=payload)
    assert resp_conf.status_code == 200

    # Verify audit logs in app_store
    logs = app_store.get_audit_logs(limit=50)
    ocr_logs = [l for l in logs if l.get("actor_user_id") == user_id and l.get("action") in ("record_ocr_upload_processed", "record_ocr_upload_confirmed")]
    assert len(ocr_logs) >= 2

    for l in ocr_logs:
        details_str = json.dumps(l.get("detail", {}))
        # Must NOT contain uploaded filename
        assert "patient_secret_lab_scan" not in details_str
        # Must NOT contain clinical measurement value 125.0
        assert "125.0" not in details_str
        assert "125" not in details_str
        # Must contain counts
        if l["action"] == "record_ocr_upload_processed":
            assert "obs_count" in details_str or "med_count" in details_str
        elif l["action"] == "record_ocr_upload_confirmed":
            assert "confirmed_count" in details_str


# ----------------------------------------------------------------------------
# FIX 4: Expired Staged Upload Message
# ----------------------------------------------------------------------------
def test_expired_upload_returns_friendly_message(rsa_key_pair, monkeypatch):
    monkeypatch.setenv("OCR_ENABLED", "true")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    client = TestClient(app)
    user_id = "p-expired-friendly"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_exp@demo.com")

    resp_up = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("report.jpg", MINIMAL_JPEG, "image/jpeg")},
    )
    upload_id = resp_up.json()["upload_id"]

    # Fast forward staging TTL (+31 minutes)
    from data_sources.ocr import staging
    staging._STAGING_STORE[upload_id]["created_at"] = datetime.now(timezone.utc) - timedelta(minutes=STAGING_TTL_MINUTES + 1)

    payload = {"confirmed_items": []}
    resp_conf = client.post(f"/api/me/record/uploads/{upload_id}/confirm", headers=headers, json=payload)
    assert resp_conf.status_code == 404
    assert "Upload not found or expired. Please upload the document again." in resp_conf.json()["detail"]


# ----------------------------------------------------------------------------
# 7. Production Safety Guard
# ----------------------------------------------------------------------------
def test_production_safety_guard_refuses_fake_ocr_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("OCR_PROVIDER", "fake")
    with pytest.raises(RuntimeError) as exc_info:
        get_ocr_provider()
    assert "Fake OCR provider refused in production environment" in str(exc_info.value)
