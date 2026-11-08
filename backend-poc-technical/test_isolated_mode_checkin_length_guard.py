"""
Integration Tests with MySQL Column Width Insert Guard (Part C2).
Proves that isolated-mode check-ins with readings and medication confirmations
overflow MySQL VARCHAR(64) column limits during /complete.

Runs under both ORCHESTRATOR=direct and ORCHESTRATOR=graph.
"""

import time
import datetime
import pytest
from datetime import timezone
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from main import app
from auth import firebase_verify
import orchestrator.steps
from data_sources import local_store, app_store
from test_mysql_id_width_contract import parse_mysql_column_width, get_local_store_ddl


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-iso-1"


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
        .not_valid_before(datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(timezone.utc) + datetime.timedelta(days=10))
        .sign(rsa_key_pair, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def create_test_token(
    private_key,
    sub: str = "uid-patient-1",
    email: str = "patient1@demo.com",
    name: str = "Patient One",
    aud: str = TEST_PROJECT_ID,
) -> str:
    import jwt
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "aud": aud,
        "iss": f"https://securetoken.google.com/{aud}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
        "user_id": sub,
    }
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, pem_bytes, algorithm="RS256", headers={"kid": TEST_KID})


def _get_declared_widths():
    local_ddl = get_local_store_ddl()
    obs_id_w = parse_mysql_column_width(local_ddl, "observations", "id")
    med_id_w = parse_mysql_column_width(local_ddl, "medications", "id")
    edit_ddl = app_store.MYSQL_RECORD_EDITS_DDL
    rec_id_w = parse_mysql_column_width(edit_ddl, "record_edits", "record_id")
    return obs_id_w, med_id_w, rec_id_w


@pytest.fixture(autouse=True)
def setup_isolated_db(tmp_path, monkeypatch, x509_cert_pem):
    """Hermetic SQLite environment for isolated-mode check-in testing."""
    test_db = str(tmp_path / "test_iso_guard.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider")
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")
    
    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    app_store.migrate(db_path=test_db, backend="sqlite")
    local_store.init_db(db_path=test_db)
    return test_db


@pytest.mark.parametrize("orch_mode", ["direct", "graph"])
def test_isolated_mode_checkin_enforces_mysql_widths(rsa_key_pair, monkeypatch, orch_mode):
    """
    Isolated-mode check-in with BP reading + medication confirmation.
    Fails on dev (where MySQL width is 64) and passes when widened to 191.
    """
    monkeypatch.setenv("ORCHESTRATOR", orch_mode)
    obs_w, med_w, rec_w = _get_declared_widths()
    
    # Install length guard that mimics MySQL strict mode truncation errors
    orig_add_obs = local_store.add_local_observation
    orig_record_edit = app_store.record_edit
    
    def guarded_add_obs(*args, **kwargs):
        oid = kwargs.get("id") or (args[0] if len(args) > 0 else "")
        if len(str(oid)) > obs_w:
            raise ValueError(
                f"Data truncation: observations.id '{oid}' (length {len(str(oid))}) "
                f"exceeds MySQL column width {obs_w}"
            )
        return orig_add_obs(*args, **kwargs)
        
    def guarded_record_edit(cursor, ph, *args, **kwargs):
        rid = kwargs.get("record_id") or ""
        if len(str(rid)) > rec_w:
            raise ValueError(
                f"Data truncation: record_edits.record_id '{rid}' (length {len(str(rid))}) "
                f"exceeds MySQL column width {rec_w}"
            )
        return orig_record_edit(cursor, ph, *args, **kwargs)
        
    monkeypatch.setattr(local_store, "add_local_observation", guarded_add_obs)
    monkeypatch.setattr(orchestrator.steps, "add_local_observation", guarded_add_obs)
    monkeypatch.setattr(app_store, "record_edit", guarded_record_edit)
    
    client = TestClient(app)
    
    # 28-character Firebase-length user ID
    user_id_28 = "usr_firebase_28_chars_long12"
    assert len(user_id_28) == 28
    
    token = create_test_token(
        rsa_key_pair,
        sub=user_id_28,
        email="patient_iso@demo.com",
        name="Isolated Patient",
    )
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Onboarding
    resp = client.post("/api/auth/session", headers=headers)
    assert resp.status_code == 200
    client.post("/api/me/consent", headers=headers, json={"granted": True})
    client.put("/api/me/profile", headers=headers, json={
        "conditions": ["hypertension"],
        "language": "en",
        "date_of_birth": "1980-01-01",
        "inclusion_confirmed": True,
    })
    
    # Seed baseline medication in isolated local store
    now_ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    local_store.add_local_medication(
        id="med-amlodipine-init",
        patient_id=f"local-{user_id_28}",
        medication_name="Amlodipine 5mg",
        status="active",
        dosage="5mg daily",
        timestamp=now_ts,
        source="local",
        origin="self_reported",
    )
    
    # 2. Start check-in (isolated mode)
    start_resp = client.post("/api/checkins/start", headers=headers)
    assert start_resp.status_code == 200, f"start failed: {start_resp.text}"
    start_data = start_resp.json()
    chk_id = start_data["checkin_id"]
    assert start_data["mode"] == "isolated"
    
    # 3. Complete interview answers including BP reading and medication confirmation
    # Standard flow: greeting, bp_reading, associated_symptoms, adherence, lifestyle
    answers = ["fine", "120/80", "none", "yes", "none", "yes"]
    for ans in answers:
        chk = app_store.get_checkin_by_id(chk_id)
        if chk and chk.get("status") in ("complete", "emergency"):
            break
        a_resp = client.post(
            f"/api/checkins/{chk_id}/answer",
            headers=headers,
            json={"answer": ans},
        )
        if a_resp.status_code != 200:
            break
        a_data = a_resp.json()
        if a_data.get("can_complete") or a_data.get("question") is None:
            break
        
    # 4. Finalize check-in via POST /complete
    # This executes step_persist_local_observations which writes to observations and record_edits
    complete_resp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    
    # In dev, the length guard causes /complete to fail (500) due to truncation
    # In fixed branch, complete succeeds with 200
    assert complete_resp.status_code == 200, (
        f"Expected HTTP 200 on /complete, got {complete_resp.status_code}: {complete_resp.text}"
    )
