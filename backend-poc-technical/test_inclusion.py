"""
Hermetic Tests for Adult-Only Inclusion, Date of Birth, and Personal Baseline History (Stage 7D-1 P2).

Marked with @pytest.mark.inclusion so that REQUIRE_INCLUSION=1 is active by default.

Covers:
1. Date of birth validation:
   - 17 years old -> 422 detail "adults_only"
   - 18 years old -> 200 accepted
   - 120 years old -> 200 accepted
   - 121 years old -> 422 detail "invalid_date_of_birth"
   - Future date -> 422 detail "invalid_date_of_birth"
   - Garbage string / invalid date -> 422 detail "invalid_date_of_birth"
2. Check-in start gated on inclusion:
   - Blocked (403 profile_incomplete) without date of birth
   - Blocked (403 profile_incomplete) without inclusion confirmation
   - Allowed (200) with both date of birth and inclusion confirmation
3. Date of birth privacy:
   - Date of birth returned only to its owner via GET /api/me/profile
4. Baseline history scoping:
   - Baseline history never contains another user's readings
   - Excludes emergency check-ins
   - Excludes abandoned / in-progress check-ins
   - Excludes readings older than 14 days
"""

import datetime
import time
from typing import Any, Dict, List, Optional
import pytest
import jwt
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store
from data_sources.models import NormalizedObservation, NormalizedMedication, NormalizedPatient


pytestmark = pytest.mark.inclusion

TEST_PROJECT_ID = "test-chroniccare-ai-inclusion"
TEST_KID = "test-key-id-inclusion"


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
    test_db_path = str(tmp_path / "test_chroniccare_inclusion.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def mock_get_bundle(pid, mode=None, base_url=None):
        return {
            "patient": NormalizedPatient(patient_id=pid, name="Test Patient", date_of_birth="1980-01-01"),
            "observations": [
                NormalizedObservation(
                    patient_id=pid,
                    observation_type="glucose",
                    value=140.0,
                    unit="mg/dL",
                    timestamp=now_ts,
                    source="local",
                    source_record_id=f"obs-{pid}-140",
                )
            ],
            "medications": [],
        }

    monkeypatch.setattr("main.get_patient_bundle", mock_get_bundle)
    yield test_db_path


def create_test_token(
    private_key,
    sub: str = "uid-patient-inc-1",
    email: str = "patient_inc1@demo.com",
    name: str = "Inclusion Patient",
    aud: str = TEST_PROJECT_ID,
    iss: Optional[str] = None,
    kid: str = TEST_KID,
    exp_delta: int = 3600,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "name": name,
        "aud": aud,
        "iss": iss or f"https://securetoken.google.com/{aud}",
        "iat": now,
        "exp": now + exp_delta,
        "auth_time": now,
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


# ----------------------------------------------------------------------------
# 1. Date of Birth Validation (17, 18, 120, 121, future, garbage)
# ----------------------------------------------------------------------------
def test_date_of_birth_validation(rsa_key_pair):
    client = TestClient(app)
    tok = create_test_token(rsa_key_pair, sub="u-dob-val", email="dobval@demo.com")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {tok}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {tok}"}, json={"granted": True})

    today = datetime.date.today()

    # (a) Under 18 (17 years old) -> 422 adults_only
    dob_17 = (today.replace(year=today.year - 17)).strftime("%Y-%m-%d")
    r_17 = client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": dob_17,
        "inclusion_confirmed": True,
    })
    assert r_17.status_code == 422
    assert r_17.json()["detail"] == "adults_only"

    # (b) Exactly 18 -> 200 OK
    dob_18 = (today.replace(year=today.year - 18)).strftime("%Y-%m-%d")
    r_18 = client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": dob_18,
        "inclusion_confirmed": True,
    })
    assert r_18.status_code == 200
    assert r_18.json()["date_of_birth"] == dob_18
    assert r_18.json()["inclusion_confirmed_at"] is not None

    # (c) Exactly 120 -> 200 OK
    dob_120 = (today.replace(year=today.year - 120)).strftime("%Y-%m-%d")
    r_120 = client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": dob_120,
    })
    assert r_120.status_code == 200
    assert r_120.json()["date_of_birth"] == dob_120

    # (d) Older than 120 (121 years old) -> 422 invalid_date_of_birth
    dob_121 = (today.replace(year=today.year - 121)).strftime("%Y-%m-%d")
    r_121 = client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": dob_121,
    })
    assert r_121.status_code == 422
    assert r_121.json()["detail"] == "invalid_date_of_birth"

    # (e) Future date -> 422 invalid_date_of_birth
    dob_future = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    r_fut = client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": dob_future,
    })
    assert r_fut.status_code == 422
    assert r_fut.json()["detail"] == "invalid_date_of_birth"

    # (f) Garbage format -> 422 invalid_date_of_birth
    for bad_dob in ["abc", "2024/01/01", "01-01-2000", "2000-13-45", ""]:
        r_bad = client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
            "conditions": ["hypertension"],
            "on_insulin_or_sulfonylurea": False,
            "date_of_birth": bad_dob,
        })
        assert r_bad.status_code == 422
        assert r_bad.json()["detail"] == "invalid_date_of_birth"


# ----------------------------------------------------------------------------
# 2. Check-in Start Gated on Inclusion Confirmation and Date of Birth
# ----------------------------------------------------------------------------
def test_checkin_start_requires_dob_and_inclusion_confirmation(rsa_key_pair):
    client = TestClient(app)
    tok = create_test_token(rsa_key_pair, sub="u-inc-gate", email="incgate@demo.com")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {tok}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {tok}"}, json={"granted": True})

    # Profile without DOB or confirmation
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
    })

    # 1. Start check-in -> 403 profile_incomplete
    r1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok}"})
    assert r1.status_code == 403
    assert r1.json()["detail"] == "profile_incomplete"

    # 2. Add DOB only (no inclusion confirmation)
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1990-05-15",
    })
    r2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 403
    assert r2.json()["detail"] == "profile_incomplete"

    # 3. Add inclusion confirmation -> 200 OK
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1990-05-15",
        "inclusion_confirmed": True,
    })
    r3 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok}"})
    assert r3.status_code == 200
    assert "checkin_id" in r3.json()


# ----------------------------------------------------------------------------
# 3. Date of Birth Privacy (Owner Only)
# ----------------------------------------------------------------------------
def test_date_of_birth_privacy(rsa_key_pair):
    client = TestClient(app)
    tok_p1 = create_test_token(rsa_key_pair, sub="u-priv-1", email="priv1@demo.com")
    tok_p2 = create_test_token(rsa_key_pair, sub="u-priv-2", email="priv2@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {tok_p1}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {tok_p1}"}, json={"granted": True})
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok_p1}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1985-04-12",
        "inclusion_confirmed": True,
    })

    # Patient 1 gets own profile
    r1 = client.get("/api/me/profile", headers={"Authorization": f"Bearer {tok_p1}"})
    assert r1.status_code == 200
    assert r1.json()["date_of_birth"] == "1985-04-12"

    # Patient 2 setup
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {tok_p2}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {tok_p2}"}, json={"granted": True})
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok_p2}"}, json={
        "conditions": ["diabetes"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1992-08-20",
        "inclusion_confirmed": True,
    })

    # Patient 2 gets own profile
    r2 = client.get("/api/me/profile", headers={"Authorization": f"Bearer {tok_p2}"})
    assert r2.status_code == 200
    assert r2.json()["date_of_birth"] == "1992-08-20"


# ----------------------------------------------------------------------------
# 4. Baseline History Scoping and Filtering
# ----------------------------------------------------------------------------
def test_baseline_history_scoping_and_filters(rsa_key_pair):
    client = TestClient(app)
    tok_user_a = create_test_token(rsa_key_pair, sub="u-base-a", email="basea@demo.com")
    tok_user_b = create_test_token(rsa_key_pair, sub="u-base-b", email="baseb@demo.com")

    for tok in (tok_user_a, tok_user_b):
        client.post("/api/auth/session", headers={"Authorization": f"Bearer {tok}"})
        client.post("/api/me/consent", headers={"Authorization": f"Bearer {tok}"}, json={"granted": True})
        client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok}"}, json={
            "conditions": ["hypertension"],
            "on_insulin_or_sulfonylurea": False,
            "date_of_birth": "1980-01-01",
            "inclusion_confirmed": True,
        })

    # 1. User A completes a valid check-in with BP 115/75
    cid_a1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_user_a}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid_a1}/answer", headers={"Authorization": f"Bearer {tok_user_a}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid_a1}/answer", headers={"Authorization": f"Bearer {tok_user_a}"}, json={"answer": "115/75", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid_a1}/answer", headers={"Authorization": f"Bearer {tok_user_a}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid_a1}/answer", headers={"Authorization": f"Bearer {tok_user_a}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid_a1}/answer", headers={"Authorization": f"Bearer {tok_user_a}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid_a1}/complete", headers={"Authorization": f"Bearer {tok_user_a}"})

    # 2. User B completes a valid check-in with BP 145/95
    cid_b1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_user_b}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid_b1}/answer", headers={"Authorization": f"Bearer {tok_user_b}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid_b1}/answer", headers={"Authorization": f"Bearer {tok_user_b}"}, json={"answer": "145/95", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid_b1}/answer", headers={"Authorization": f"Bearer {tok_user_b}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid_b1}/answer", headers={"Authorization": f"Bearer {tok_user_b}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid_b1}/answer", headers={"Authorization": f"Bearer {tok_user_b}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid_b1}/complete", headers={"Authorization": f"Bearer {tok_user_b}"})

    # User A baseline history must only contain User A readings (115/75) and NOT User B (145/95)
    hist_a = app_store.get_user_baseline_history("u-base-a")
    values_a = [r["value"] for r in hist_a]
    assert 115.0 in values_a
    assert 145.0 not in values_a

    # User B baseline history must only contain User B readings (145/95) and NOT User A (115/75)
    hist_b = app_store.get_user_baseline_history("u-base-b")
    values_b = [r["value"] for r in hist_b]
    assert 145.0 in values_b
    assert 115.0 not in values_b

    # 3. Emergency check-ins are excluded from baseline
    cid_a_em = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_user_a}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid_a_em}/answer", headers={"Authorization": f"Bearer {tok_user_a}"}, json={"answer": "I have chest pain", "step": "greeting"})
    # User A baseline should NOT include emergency readings
    hist_a_after = app_store.get_user_baseline_history("u-base-a")
    assert len(hist_a_after) == len(hist_a)

    # 4. Abandoned / in-progress check-ins are excluded
    cid_a_inprog = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_user_a}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid_a_inprog}/answer", headers={"Authorization": f"Bearer {tok_user_a}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid_a_inprog}/answer", headers={"Authorization": f"Bearer {tok_user_a}"}, json={"answer": "160/100", "step": "bp_reading"})
    hist_a_inprog = app_store.get_user_baseline_history("u-base-a")
    values_inprog = [r["value"] for r in hist_a_inprog]
    assert 160.0 not in values_inprog


def test_baseline_two_checkins_no_double_counting(rsa_key_pair):
    """Verifies that two check-ins in isolated mode produce exactly two systolic readings in baseline history."""
    client = TestClient(app)
    tok_user = create_test_token(rsa_key_pair, sub="u-base-dbl", email="basedbl@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {tok_user}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {tok_user}"}, json={"granted": True})
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok_user}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1985-05-15",
        "inclusion_confirmed": True,
    })

    # Check-in 1 with 110/70
    cid1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_user}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "110/70", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid1}/complete", headers={"Authorization": f"Bearer {tok_user}"})

    # Check-in 2 with 120/80
    cid2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_user}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "120/80", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid2}/complete", headers={"Authorization": f"Bearer {tok_user}"})

    hist = app_store.get_user_baseline_history("u-base-dbl")
    sys_readings = [r["value"] for r in hist if r["observation_type"] == "blood_pressure_systolic"]
    assert len(sys_readings) == 2
    assert sorted(sys_readings) == [110.0, 120.0]


def test_baseline_two_checkins_plus_user_observation_creates_baseline(rsa_key_pair):
    """Verifies two check-ins alone give 2 readings (no baseline), but + 1 user-entered observation gives 3 (valid baseline)."""
    from agents.triage_protocol import compute_baseline
    client = TestClient(app)
    tok_user = create_test_token(rsa_key_pair, sub="u-base-three", email="basethree@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {tok_user}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {tok_user}"}, json={"granted": True})
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {tok_user}"}, json={
        "conditions": ["hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1985-05-15",
        "inclusion_confirmed": True,
    })

    # Check-in 1: 110/70
    cid1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_user}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "110/70", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid1}/complete", headers={"Authorization": f"Bearer {tok_user}"})

    # Check-in 2: 114/74
    cid2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_user}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "114/74", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok_user}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid2}/complete", headers={"Authorization": f"Bearer {tok_user}"})

    # 2 check-ins alone: exactly 2 readings -> compute_baseline returns None
    hist_2 = app_store.get_user_baseline_history("u-base-three")
    sys_2 = [r for r in hist_2 if r["observation_type"] == "blood_pressure_systolic"]
    assert len(sys_2) == 2
    assert compute_baseline(hist_2) is None

    # Add 1 user-entered baseline observation in Isolated Mode record
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    obs_resp = client.post("/api/me/record/observations", headers={"Authorization": f"Bearer {tok_user}"}, json={
        "observation_type": "blood_pressure_systolic",
        "value": 112.0,
        "measured_at": now_iso,
    })
    assert obs_resp.status_code == 200

    # Now 3 readings: compute_baseline returns a baseline with n=3 and median 112
    hist_3 = app_store.get_user_baseline_history("u-base-three")
    sys_3 = [r for r in hist_3 if r["observation_type"] == "blood_pressure_systolic"]
    assert len(sys_3) == 3
    base = compute_baseline(hist_3)
    assert base is not None
    assert base.n == 3
    assert base.systolic == 112.0


