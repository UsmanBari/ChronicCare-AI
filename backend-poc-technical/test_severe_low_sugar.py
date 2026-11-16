"""
Hermetic Integration Tests for Severe Low Sugar with Neuro Symptoms (P0-2).

Clinical Safety Invariant:
After EVERY turn (and the opening note):
1. If glucose < 54 mg/dL (or < 3.0 mmol/L) is known AND the same or earlier answer reports
   confusion/disorientation/can't think straight/unable to eat or drink/fainting/seizure
   (across English, Urdu script, and Roman Urdu):
   End interview IMMEDIATELY with the emergency response (1122) using the exact rule
   and wording from agents.triage_protocol._decide_glucose_low without duplicating thresholds.
2. If glucose < 70 mg/dL without neuro symptoms:
   Show the approved neutral low-sugar guidance ("Take quick sugar such as fruit juice or glucose...")
   immediately and CONTINUE the interview.
3. Historical/past readings ("my sugar was 45 last week, today 120 and I feel fine"):
   Must NOT trigger Red emergency; today's reading (120) takes precedence.
"""

import os
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

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store
from agents.triage_protocol import GLUCOSE_VERY_LOW_MG_DL, GLUCOSE_LOW_MG_DL, _decide_glucose_low, TriageProtocolState, GLUCOSE


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-severe-low-sugar-1"


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
    test_db_path = str(tmp_path / "test_severe_low_sugar.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


def create_test_token(
    private_key,
    sub: str = "uid-patient-low-sugar",
    email: str = "patient_low_sugar@demo.com",
    name: str = "Low Sugar Patient",
    aud: str = TEST_PROJECT_ID,
    kid: str = TEST_KID,
) -> str:
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
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def setup_verified_patient(client: TestClient, rsa_key_pair, user_id: str, email: str, lang: str = "en"):
    token = create_test_token(rsa_key_pair, sub=user_id, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    prof_res = client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": ["diabetes"],
            "on_insulin_or_sulfonylurea": True,
            "language": lang,
            "date_of_birth": "1980-01-01",
            "inclusion_confirmed": True,
            "sex_at_birth": "male",
        },
    )
    assert prof_res.status_code == 200, f"Profile setup failed {prof_res.status_code}: {prof_res.text}"
    return headers


# -----------------------------------------------------------------------------
# 1. 3 Languages Severe Low Sugar Emergencies on that Exact Turn
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "lang,phrase",
    [
        ("en", "my sugar is 45 and I am confused and sweating, can't think straight"),
        ("roman_ur", "sugar 45 hai aur mujhe kuch samajh nahi aa raha"),
        ("ur", "شوگر 45 ہے اور میں الجھن میں ہوں"),
    ],
)
def test_severe_low_sugar_emergency_across_languages(rsa_key_pair, lang, phrase):
    client = TestClient(app)
    uid = f"p-low-turn-{lang}"
    headers = setup_verified_patient(client, rsa_key_pair, uid, f"{uid}@demo.com", lang=lang)

    start_resp = client.post("/api/checkins/start", headers=headers, json={})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    checkin_id = start_data["checkin_id"]
    initial_step = start_data["step"]
    assert start_data["emergency"] is False

    # Patient answers first question with severe low sugar + confusion
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": phrase, "step": initial_step},
    )
    assert ans_resp.status_code == 200, ans_resp.text
    ans_data = ans_resp.json()

    assert ans_data["emergency"] is True, f"Failed for {lang}: {phrase}"
    assert ans_data["complete"] is True
    assert ans_data["step"] == "COMPLETE"
    assert ans_data["escalation_recorded"] is True
    assert "Low glucose with disorientation or acute confusion" in ans_data["emergency_reason"]

    # Verify checkin row in DB is marked emergency
    stored = app_store.get_checkin_by_id(checkin_id)
    assert stored["status"] == "emergency"

    # Verify emergency audit event logged
    audit_rows = app_store.get_audit_logs(limit=50)
    escalated_logs = [r for r in audit_rows if r.get("action") == "emergency_escalated" and r.get("target") == checkin_id]
    assert len(escalated_logs) >= 1, "Expected emergency_escalated audit row"


# -----------------------------------------------------------------------------
# 2. Historical/Past 45 last week, today 120 and feeling fine -> NOT Red
# -----------------------------------------------------------------------------
def test_past_severe_low_today_normal_not_red(rsa_key_pair):
    client = TestClient(app)
    uid = "p-past-low-normal-today"
    headers = setup_verified_patient(client, rsa_key_pair, uid, f"{uid}@demo.com")

    start_resp = client.post("/api/checkins/start", headers=headers, json={})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    checkin_id = start_data["checkin_id"]
    initial_step = start_data["step"]

    phrase = "my sugar was 45 last week, today 120 and I feel fine"
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": phrase, "step": initial_step},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()

    # Invariant: Must NOT be Red
    assert ans_data["emergency"] is False
    assert ans_data["complete"] is False
    assert ans_data["step"] != "COMPLETE"

    # Invariant: Today's reading in state is 120, not 45
    stored = app_store.get_checkin_by_id(checkin_id)
    st = stored.get("state", {})
    readings = st.get("readings", {})
    assert readings.get("glucose") == 120.0


# -----------------------------------------------------------------------------
# 3. Glucose 65 without symptoms -> guidance shown, interview continues
# -----------------------------------------------------------------------------
def test_glucose_65_without_symptoms_shows_guidance_and_continues(rsa_key_pair):
    client = TestClient(app)
    uid = "p-low-65-no-symptoms"
    headers = setup_verified_patient(client, rsa_key_pair, uid, f"{uid}@demo.com")

    start_resp = client.post("/api/checkins/start", headers=headers, json={})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    checkin_id = start_data["checkin_id"]
    initial_step = start_data["step"]

    phrase = "glucose 65 without symptoms"
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": phrase, "step": initial_step},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()

    # Must NOT be emergency
    assert ans_data["emergency"] is False
    assert ans_data["complete"] is False
    assert ans_data["step"] != "COMPLETE"

    # Low-sugar guidance must be returned immediately in banner / system note
    note = ans_data.get("safety_note") or ans_data.get("system_note")
    assert note is not None
    assert "Take quick sugar" in note or "quick sugar" in note.lower()


# -----------------------------------------------------------------------------
# 4. Two-turn severe low sugar: Turn 1 value 45, Turn 2 confusion reported
# -----------------------------------------------------------------------------
def test_two_turn_severe_low_sugar(rsa_key_pair):
    client = TestClient(app)
    uid = "p-two-turn-low"
    headers = setup_verified_patient(client, rsa_key_pair, uid, f"{uid}@demo.com")

    start_resp = client.post("/api/checkins/start", headers=headers, json={})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    checkin_id = start_data["checkin_id"]
    step1 = start_data["step"]

    # Turn 1: Patient gives value only (45)
    ans1_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "my sugar is 45 mg/dL", "step": step1},
    )
    assert ans1_resp.status_code == 200
    ans1_data = ans1_resp.json()
    assert ans1_data["emergency"] is False
    assert ans1_data["complete"] is False
    step2 = ans1_data["step"]

    # Turn 2: Patient reports confusion
    ans2_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "I feel very confused and dizzy, can't think straight", "step": step2},
    )
    assert ans2_resp.status_code == 200
    ans2_data = ans2_resp.json()

    # Emergency must be triggered on Turn 2
    assert ans2_data["emergency"] is True
    assert ans2_data["complete"] is True
    assert ans2_data["step"] == "COMPLETE"
    assert "Low glucose with disorientation or acute confusion" in ans2_data["emergency_reason"]


# -----------------------------------------------------------------------------
# 5. Opening Note with Severe Low Sugar + Confusion -> Immediate Emergency
# -----------------------------------------------------------------------------
def test_opening_note_severe_low_sugar_confusion(rsa_key_pair):
    client = TestClient(app)
    uid = "p-opening-low-sugar"
    headers = setup_verified_patient(client, rsa_key_pair, uid, f"{uid}@demo.com")

    start_resp = client.post(
        "/api/checkins/start",
        headers=headers,
        json={"note": "my sugar is 45 and I am confused and sweating, can't think straight"},
    )
    assert start_resp.status_code == 200
    data = start_resp.json()

    assert data["emergency"] is True
    assert data["step"] == "COMPLETE"
    assert data["question"] is None
    assert "Low glucose with disorientation or acute confusion" in data["emergency_reason"]


# -----------------------------------------------------------------------------
# 6. mmol/L Unit Low Sugar Evaluation
# -----------------------------------------------------------------------------
def test_mmol_unit_severe_low_sugar(rsa_key_pair):
    client = TestClient(app)
    uid = "p-mmol-low-sugar"
    headers = setup_verified_patient(client, rsa_key_pair, uid, f"{uid}@demo.com")

    start_resp = client.post("/api/checkins/start", headers=headers, json={})
    checkin_id = start_resp.json()["checkin_id"]
    step1 = start_resp.json()["step"]

    # 2.5 mmol/L = 45 mg/dL (< 54) + confused
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "sugar is 2.5 mmol/L and I feel disoriented and confused", "step": step1},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["emergency"] is True
    assert ans_data["complete"] is True
    assert ans_data["step"] == "COMPLETE"


# -----------------------------------------------------------------------------
# 7. Mutation Proof: Severe low only checked at complete
# -----------------------------------------------------------------------------
def test_mutation_killed_severe_low_only_at_complete(rsa_key_pair):
    """
    Proves that severe low sugar with confusion MUST be checked turn-by-turn.
    If the immediate turn emergency check is disabled, this test fails.
    """
    client = TestClient(app)
    uid = "p-mutant-severe-low"
    headers = setup_verified_patient(client, rsa_key_pair, uid, f"{uid}@demo.com")

    start_resp = client.post("/api/checkins/start", headers=headers, json={})
    checkin_id = start_resp.json()["checkin_id"]
    step1 = start_resp.json()["step"]

    phrase = "my sugar is 45 and I am confused and sweating, can't think straight"
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": phrase, "step": step1},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()

    # Mutation assertion: Must trigger emergency on THIS turn, not deferred to complete
    assert ans_data["emergency"] is True
    assert ans_data["complete"] is True
    assert ans_data["step"] == "COMPLETE"
