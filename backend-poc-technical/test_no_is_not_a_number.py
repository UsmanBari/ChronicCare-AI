"""
Hermetic Tests for P0 Fix: a bare 'no' is never a glucose reading.

Verifies:
1. Direct unit parsing:
   - 'no' is not in _ROMAN_URDU_NUMBERS dictionary.
   - 'no', 'No.', 'NO', ' no ', 'na', 'nahi' return value None.
   - Deliberately preserved tokens: 'nau' -> 9.0, 'do' -> 2.0, 'ek sau bees' -> 120.0.
2. End-to-end v2 interview:
   - Answering 'no' to every question never stores a glucose reading of 9.
   - Check-in does not trigger emergency or glucose_low protocol.
   - Neither 'fast-acting sugar' nor 'emergency number' appears in guidance or response.
3. End-to-end v3 interview:
   - 'Did you mean 9 mmol/L or 9 mg/dL?' clarification is never asked.
   - Recap shows 'Blood Glucose: Not provided' (never '9 mg/dL').
"""

import os
import time
import datetime
import sqlite3
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
from agents.answer_understanding import parse_number, _ROMAN_URDU_NUMBERS


# =============================================================================
# 1. Direct Unit Tests
# =============================================================================

def test_no_not_in_roman_urdu_numbers():
    """Assert 'no' is not defined as a number in _ROMAN_URDU_NUMBERS (kills re-introducing 'no': 9)."""
    assert "no" not in _ROMAN_URDU_NUMBERS, "'no' must never be mapped in _ROMAN_URDU_NUMBERS"


@pytest.mark.parametrize(
    "token",
    [
        "no",
        "No",
        "No.",
        "NO",
        " no ",
        "na",
        "nahi",
        "nahin",
        "nope",
        "nah",
        "yes",
        "haan",
        "ji",
        "jee",
    ],
)
def test_parse_number_no_and_negatives_are_none(token):
    res = parse_number(token)
    assert res["value"] is None, f"Expected None for {token!r}, got {res['value']}"


def test_parse_number_preserved_values():
    # 'nau' is 9 in Roman Urdu
    assert parse_number("nau")["value"] == 9.0
    # 'do' is 2 in Roman Urdu (kept per prompt instructions)
    assert parse_number("do")["value"] == 2.0
    # Compound numbers
    assert parse_number("ek sau bees")["value"] == 120.0


# =============================================================================
# 2. End-to-End Interview Tests (v2 and v3)
# =============================================================================

@pytest.fixture
def auth_setup(tmp_path, monkeypatch):
    """Hermetic SQLite database and RSA Firebase auth setup."""
    test_db = str(tmp_path / "test_no_p0.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-chroniccare-ai")
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider")

    app_store.migrate(db_path=test_db, backend="sqlite")
    local_store.init_db(db_path=test_db)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": {"test-key-id-1": cert_pem}, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: {"test-key-id-1": cert_pem})

    def make_token(user_id="pat-test-no", email="pat@demo.com"):
        now = int(time.time())
        return jwt.encode(
            {
                "sub": user_id,
                "user_id": user_id,
                "email": email,
                "name": "Patient Test",
                "aud": "test-chroniccare-ai",
                "iss": "https://securetoken.google.com/test-chroniccare-ai",
                "iat": now,
                "exp": now + 3600,
                "auth_time": now,
            },
            key,
            algorithm="RS256",
            headers={"kid": "test-key-id-1"},
        )

    return {"db_path": test_db, "make_token": make_token}


def _onboard_diabetes_patient(client, token):
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    resp = client.post("/api/me/consent", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})
    assert resp.status_code == 200, resp.text
    resp = client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "date_of_birth": "1982-06-15",
            "inclusion_confirmed": True,
            "conditions": ["diabetes"],
            "on_insulin_or_sulfonylurea": False,
            "language": "en",
        },
    )
    assert resp.status_code == 200, resp.text


def test_v2_e2e_no_is_never_a_glucose_reading(auth_setup, monkeypatch):
    """In v2 interview, answering 'no' to every question must never record 9 mg/dL or trigger hypoglycemia emergency."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v2")
    client = TestClient(app)
    token = auth_setup["make_token"]("pat-v2-no", "pat-v2@demo.com")
    _onboard_diabetes_patient(client, token)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200, start_resp.text
    checkin_id = start_resp.json()["checkin_id"]

    data = start_resp.json()
    asked_questions = [data.get("question")]

    step = 0
    while not data.get("complete", False):
        step += 1
        ans_resp = client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": "no"},
        )
        assert ans_resp.status_code == 200, f"Step {step} failed: {ans_resp.text}"
        data = ans_resp.json()
        if data.get("question"):
            asked_questions.append(data.get("question"))
        if step > 20:
            pytest.fail("v2 interview exceeded 20 steps answering 'no'")

    comp_resp = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp_resp.status_code == 200, comp_resp.text
    comp = comp_resp.json()

    # Safety invariants
    assert comp["emergency"] is False, f"Emergency should be False, got {comp['emergency']}"
    triage = comp.get("triage") or {}
    assert triage.get("protocol") != "glucose_low", f"Triage protocol must not be glucose_low, got {triage.get('protocol')}"

    # Guidance/summary checks
    comp_str = str(comp).lower()
    assert "fast-acting sugar" not in comp_str, "Fast-acting sugar guidance must not appear"
    assert "emergency number" not in comp_str, "Emergency number guidance must not appear"

    # Readings check
    intakes = comp.get("intakes") or []
    for intake in intakes:
        readings = intake.get("readings") or []
        for r in readings:
            if r.get("observation_type") == "glucose":
                assert r.get("value") != 9.0, "Glucose reading must not be 9.0"

    # Stored DB row check
    conn = sqlite3.connect(auth_setup["db_path"])
    cur = conn.cursor()
    cur.execute("SELECT emergency, triage_json FROM checkin_results WHERE checkin_id = ?", (checkin_id,))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == 0, f"checkin_results.emergency must be 0, got {row[0]}"
    conn.close()


def test_v3_e2e_no_is_never_a_glucose_reading(auth_setup, monkeypatch):
    """In v3 interview, answering 'no' must not prompt for 9 mmol/L vs 9 mg/dL and recap must show Not provided."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    client = TestClient(app)
    token = auth_setup["make_token"]("pat-v3-no", "pat-v3@demo.com")
    _onboard_diabetes_patient(client, token)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200, start_resp.text
    checkin_id = start_resp.json()["checkin_id"]

    data = start_resp.json()
    asked_questions = [data.get("question")]

    step = 0
    while not data.get("complete", False):
        step += 1
        ans_resp = client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": "no"},
        )
        assert ans_resp.status_code == 200, f"Step {step} failed: {ans_resp.text}"
        data = ans_resp.json()
        if data.get("question"):
            asked_questions.append(data.get("question"))
        if step > 20:
            pytest.fail("v3 interview exceeded 20 steps answering 'no'")

    # Invariant: "Did you mean 9 mmol/L or 9 mg/dL?" was never asked
    for q in asked_questions:
        if q:
            assert "did you mean 9" not in q.lower(), f"Unexpected 9 clarification asked: {q}"
            if "here is what we recorded today" in q.lower():
                assert "blood glucose: not provided" in q.lower(), f"Expected 'Not provided' in recap, got: {q}"
                assert "9 mg/dl" not in q.lower(), f"Found '9 mg/dL' in recap: {q}"

    comp_resp = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp_resp.status_code == 200, comp_resp.text
    comp = comp_resp.json()

    assert comp["emergency"] is False
    triage = comp.get("triage") or {}
    assert triage.get("protocol") != "glucose_low"
