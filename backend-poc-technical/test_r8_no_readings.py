import os
import sys
import time
import datetime
import jwt
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store

TEST_PROJECT_ID = "test-r8-project"
TEST_KID = "test-key-id-r8"


@pytest.fixture(scope="session")
def rsa_key_pair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


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
def setup_test_env(tmp_path, monkeypatch, x509_cert_pem):
    db_file = str(tmp_path / "test_r8.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("ORCHESTRATOR", "direct")
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)
    return db_file


def _get_token(rsa_key_pair, uid: str, email: str = "patient@demo.com") -> str:
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": email,
        "name": "Test Patient",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key_pair, algorithm="RS256", headers={"kid": TEST_KID})


def _bootstrap(client, token, conditions=["diabetes"]):
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})
    client.post("/api/me/consent/provider-notification", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "conditions": list(conditions),
            "on_insulin_or_sulfonylurea": False,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": "en",
        },
    )


def test_r8_v2_no_readings_no_symptoms_is_routine(rsa_key_pair, monkeypatch):
    """Rule R8: Check-in with no readings and NO symptoms routes to ROUTINE (requires_review=False)."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v2")
    token = _get_token(rsa_key_pair, uid="u-r8-v2-nosymp", email="r8v2nosymp@demo.com")

    client = TestClient(app)
    _bootstrap(client, token, conditions=["diabetes"])

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    cid = start_resp.json()["checkin_id"]

    # Answer flow: greeting -> no reading -> checkpoint: no meter -> symptoms: no -> adherence: yes -> lifestyle: fine
    answers = [
        "Feeling fine, no symptoms",
        "I didn't take any reading",
        "No meter available",
        "No symptoms at all",
        "Yes, taken as prescribed",
        "No changes",
    ]
    for ans in answers:
        r = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {token}"}, json={"answer": ans})
        if r.json().get("complete"):
            break

    comp_resp = client.post(f"/api/checkins/{cid}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp_resp.status_code == 200
    data = comp_resp.json()

    assert data["requires_review"] is False
    assert data["triage"] is not None
    assert data["triage"]["level"] == "routine"


def test_r8_v2_no_readings_with_symptom_is_review(rsa_key_pair, monkeypatch):
    """Rule R8: Check-in with no readings and reported symptoms routes to REVIEW (requires_review=True)."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v2")
    token = _get_token(rsa_key_pair, uid="u-r8-v2-symp", email="r8v2symp@demo.com")

    client = TestClient(app)
    _bootstrap(client, token, conditions=["diabetes"])

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    cid = start_resp.json()["checkin_id"]

    # Answer flow: greeting -> no reading -> checkpoint: no reading -> symptoms: yes thirsty -> adherence: yes -> lifestyle: fine
    answers = [
        "Feeling fine",
        "I didn't take any reading",
        "I don't have my meter",
        "Yes, I have been feeling very thirsty and fatigued",
        "Yes",
        "No",
    ]
    for ans in answers:
        r = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {token}"}, json={"answer": ans})
        if r.json().get("complete"):
            break

    comp_resp = client.post(f"/api/checkins/{cid}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp_resp.status_code == 200
    data = comp_resp.json()

    assert data["requires_review"] is True
    assert data["triage"] is not None
    assert data["triage"]["level"] == "review"


def test_r8_v3_no_readings_no_symptoms_is_routine(rsa_key_pair, monkeypatch):
    """Rule R8: v3 check-in with no readings and NO symptoms routes to ROUTINE (requires_review=False)."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    token = _get_token(rsa_key_pair, uid="u-r8-v3-nosymp", email="r8v3nosymp@demo.com")

    client = TestClient(app)
    _bootstrap(client, token, conditions=["diabetes"])

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    cid = start_resp.json()["checkin_id"]

    for _ in range(20):
        ans_resp = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {token}"}, json={"answer": "no"})
        if ans_resp.json().get("complete"):
            break

    comp_resp = client.post(f"/api/checkins/{cid}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp_resp.status_code == 200
    data = comp_resp.json()

    assert data["requires_review"] is False
    assert data["triage"] is not None
    assert data["triage"]["level"] == "routine"


def test_r8_v3_no_readings_with_symptom_is_review(rsa_key_pair, monkeypatch):
    """Rule R8: v3 check-in with no readings and reported symptoms routes to REVIEW (requires_review=True)."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    token = _get_token(rsa_key_pair, uid="u-r8-v3-symp", email="r8v3symp@demo.com")

    client = TestClient(app)
    _bootstrap(client, token, conditions=["diabetes"])

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    cid = start_resp.json()["checkin_id"]

    ans_resp = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {token}"}, json={"answer": "I have been feeling very thirsty"})
    for _ in range(20):
        if ans_resp.json().get("complete"):
            break
        q = ans_resp.json().get("question", "").lower()
        if "everything look right" in q or "does this look right" in q:
            ans = "Yes"
        elif "sugar" in q or "glucose" in q:
            ans = "No reading"
        else:
            ans = "No"
        ans_resp = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {token}"}, json={"answer": ans})

    comp_resp = client.post(f"/api/checkins/{cid}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp_resp.status_code == 200
    data = comp_resp.json()

    assert data["requires_review"] is True
    assert data["triage"] is not None
    assert data["triage"]["level"] == "review"
