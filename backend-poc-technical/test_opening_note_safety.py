"""
Hermetic Integration Tests for Opening Note Safety & Red-Flag Screening (P0-1).

Tests:
1. API emergencies via the opening note:
   - 3 per language (English, Urdu script, Roman Urdu) across >= 3 clinical categories (cardiac, breathing, stroke).
   - Verifies response has emergency=True, step='COMPLETE', escalation_recorded=True, and emergency_reason.
   - Verifies status='emergency' is persisted in database and audit log contains emergency_escalated.
2. Home flow where an in-progress check-in already exists with 0 answers:
   - Starting check-in first without note creates check-in C1.
   - Starting check-in with emergency note reuses C1 (no orphan check-in created), transitions to emergency.
3. Negated opening note ("no chest pain today, feeling fine") is NOT Red:
   - Downgrades conservatively to review/routine, does not return emergency=True.
4. Multi-intent opening in 3 languages (EN, Urdu, Roman Urdu):
   - Fills glucose, BP, adherence; planner does not re-ask them.
5. Mutation proof test:
   - test_mutation_killed_opening_note_skips_red_flag proves that skipping red flag screen in opening note fails.
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


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-opening-note-1"


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
    test_db_path = str(tmp_path / "test_opening_note.db")

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
    sub: str = "uid-patient-opening",
    email: str = "patient_opening@demo.com",
    name: str = "Opening Patient",
    aud: str = TEST_PROJECT_ID,
    iss: Optional[str] = None,
    exp: Optional[int] = None,
    iat: Optional[int] = None,
    kid: str = TEST_KID,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "aud": aud,
        "iss": iss or f"https://securetoken.google.com/{aud}",
        "iat": iat or now,
        "exp": exp or (now + 3600),
        "auth_time": now,
    }
    headers = {"kid": kid}
    return jwt.encode(payload, private_key, algorithm="RS256", headers=headers)


def _setup_patient(client, rsa_key_pair, user_id="patient-on-1", email="patient_on@demo.com", conditions=None, language="en"):
    token = create_test_token(rsa_key_pair, sub=user_id, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    prof_res = client.put("/api/me/profile", headers=headers, json={
        "conditions": conditions or ["diabetes", "hypertension"],
        "on_insulin_or_sulfonylurea": False,
        "language": language,
        "date_of_birth": "1980-01-01",
        "inclusion_confirmed": True,
        "sex_at_birth": "male",
    })
    assert prof_res.status_code == 200, f"Profile setup failed {prof_res.status_code}: {prof_res.text}"
    return headers


# =============================================================================
# 1. EMERGENCIES VIA OPENING NOTE: 3 LANGUAGES x 3 CATEGORIES (9 CASES)
# =============================================================================

EMERGENCY_OPENING_CASES = [
    # English
    ("en", "cardiac", "I have severe crushing chest pain spreading to my left arm and I am sweating a lot"),
    ("en", "breathing", "I cannot breathe, gasping for air and suffocating"),
    ("en", "stroke", "My right side is suddenly paralyzed and my speech is slurred"),
    # Urdu script
    ("ur", "cardiac", "سینے میں شدید درد اور بائیں بازو میں کھنچاؤ ہے اور پسینہ آ رہا ہے"),
    ("ur", "breathing", "سانس لینا بالکل نا ممکن ہو گیا ہے اور دم گھٹ رہا ہے"),
    ("ur", "stroke", "ابا کا چہرہ ایک طرف ڈھلک گیا ہے اور اچانک زبان لڑکھڑا گئی ہے"),
    # Roman Urdu
    ("roman_ur", "cardiac", "seene mein shadeed dabao aur dard baen baazu mein phail raha hai"),
    ("roman_ur", "breathing", "saans bilkul band ho rahi hai aur ghutan mehsoos ho rahi hai"),
    ("roman_ur", "stroke", "achanak zaban larkhara gayi aur daayan baazu kaam nahi kar raha"),
]


@pytest.mark.parametrize("lang,category,opening_text", EMERGENCY_OPENING_CASES)
def test_opening_note_emergency_across_languages(rsa_key_pair, lang, category, opening_text):
    client = TestClient(app)
    uid = f"pat-{lang}-{category}-{int(time.time()*1000)%100000}"
    headers = _setup_patient(client, rsa_key_pair, user_id=uid, email=f"{uid}@demo.com", language=lang)

    resp = client.post("/api/checkins/start", headers=headers, json={"note": opening_text})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert data["emergency"] is True, f"Failed for {lang} {category}: {opening_text}"
    assert data["step"] == "COMPLETE"
    assert data["escalation_recorded"] is True
    assert data["emergency_reason"] is not None

    # Verify persisted in database as emergency
    checkin_id = data["checkin_id"]
    detail = app_store.get_checkin_by_id(checkin_id)
    assert detail is not None
    assert detail["status"] == "emergency"

    # Verify audit log contains emergency_escalated
    audit_rows = app_store.get_audit_logs(limit=20)
    escalated_logs = [r for r in audit_rows if r.get("action") == "emergency_escalated" and r.get("target") == checkin_id]
    assert len(escalated_logs) >= 1, "Expected emergency_escalated audit row"


# =============================================================================
# 2. HOME FLOW WITH PRE-EXISTING IN-PROGRESS CHECK-IN (REUSE, NO ORPHANS)
# =============================================================================

def test_home_flow_reuses_existing_checkin_with_emergency_opening(rsa_key_pair):
    client = TestClient(app)
    uid = f"pat-reuse-{int(time.time()*1000)%100000}"
    headers = _setup_patient(client, rsa_key_pair, user_id=uid, email=f"{uid}@demo.com")

    # Step 1: Patient clicks Start Check-in on Home screen -> calls startCheckin with NO note
    resp1 = client.post("/api/checkins/start", headers=headers, json={})
    assert resp1.status_code == 200
    data1 = resp1.json()
    initial_checkin_id = data1["checkin_id"]
    assert data1["emergency"] is False

    # Step 2: Patient types emergency in opening box and continues -> calls startCheckin with note
    emergency_text = "I have severe crushing chest pain spreading to my left arm and I am sweating a lot"
    resp2 = client.post("/api/checkins/start", headers=headers, json={"note": emergency_text})
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Must reuse the same checkin_id (no orphan check-in)
    assert data2["checkin_id"] == initial_checkin_id
    assert data2["emergency"] is True
    assert data2["step"] == "COMPLETE"
    assert data2["escalation_recorded"] is True

    # Verify DB status is emergency
    detail = app_store.get_checkin_by_id(initial_checkin_id)
    assert detail["status"] == "emergency"

    # Verify user only has 1 checkin, not 2
    user_checkins = app_store.get_user_checkins(uid, limit=10)
    assert len(user_checkins) == 1


# =============================================================================
# 3. NEGATED OPENING NOTE IS NOT RED
# =============================================================================

@pytest.mark.parametrize("lang,note_text", [
    ("en", "no chest pain today, feeling fine"),
    ("roman_ur", "sar mein dard nahi hai, tabiyat theek hai"),
    ("ur", "کوئی سینے میں درد نہیں ہے، بالکل ٹھیک ہوں"),
])
def test_negated_opening_note_not_red(rsa_key_pair, lang, note_text):
    client = TestClient(app)
    uid = f"pat-neg-{lang}-{int(time.time()*1000)%100000}"
    headers = _setup_patient(client, rsa_key_pair, user_id=uid, email=f"{uid}@demo.com", language=lang)

    resp = client.post("/api/checkins/start", headers=headers, json={"note": note_text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["emergency"] is False, f"Negated opening should not be emergency: {note_text}"
    assert data["step"] != "COMPLETE"
    assert data["question"] is not None


# =============================================================================
# 4. MULTI-INTENT OPENING IN 3 LANGUAGES (GLUCOSE, BP, ADHERENCE EXTRACTED)
# =============================================================================

MULTI_INTENT_CASES = [
    ("en", "Fasting sugar this morning was 110, BP 124/80. I took all my medicines."),
    ("roman_ur", "Subah fasting sugar 110 thi, BP 124/80. Sab dawai kha li."),
    ("ur", "صبح نہار منہ شوگر 110 تھی، بی پی 124/80 تھا۔ تمام ادویات لے لی ہیں۔"),
]


@pytest.mark.parametrize("lang,multi_text", MULTI_INTENT_CASES)
def test_multi_intent_opening_extracts_slots_and_skips_questions(rsa_key_pair, lang, multi_text):
    client = TestClient(app)
    uid = f"pat-mi-{lang}-{int(time.time()*1000)%100000}"
    headers = _setup_patient(client, rsa_key_pair, user_id=uid, email=f"{uid}@demo.com", language=lang)

    resp = client.post("/api/checkins/start", headers=headers, json={"note": multi_text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["emergency"] is False

    # Checkin state in DB should have extracted readings and known slots
    checkin_id = data["checkin_id"]
    detail = app_store.get_checkin_by_id(checkin_id)
    state = detail["state"]
    known_slots = state.get("known_slots", {})
    readings = state.get("readings", {})

    assert "glucose_reading" in known_slots
    assert known_slots["glucose_reading"] == 110.0
    assert "bp_reading" in known_slots
    assert known_slots["bp_reading"] == [124, 80]
    assert known_slots.get("adherence") is True or known_slots.get("adherence_diabetes") is True

    # Planner first question should not ask glucose or BP reading
    first_step = data["step"]
    assert first_step not in ("glucose_reading", "bp_reading", "diabetes_glucose_reading", "hypertension_bp_reading")


# =============================================================================
# 5. MUTATION TEST: OPENING NOTE SKIPS RED-FLAG SCREEN
# =============================================================================

def test_mutation_killed_opening_note_skips_red_flag(rsa_key_pair):
    """
    Kills mutant where start_checkin_endpoint skips evaluate_text_safety on opening note.
    """
    client = TestClient(app)
    uid = "pat-mutant-opening-proof"
    headers = _setup_patient(client, rsa_key_pair, user_id=uid, email=f"{uid}@demo.com")

    emergency_text = "I have severe crushing chest pain spreading to my left arm and I am sweating a lot"
    resp = client.post("/api/checkins/start", headers=headers, json={"note": emergency_text})
    assert resp.status_code == 200, f"Error {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["emergency"] is True, "Mutant survived: opening note was not red-flag screened"
    assert data["step"] == "COMPLETE"
