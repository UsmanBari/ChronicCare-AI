"""
Tests for HOTFIX 2: No invented glucose / false emergency when the patient skips the reading.
P0 Hotfix 2 verification suite (T1, T2, T3, T4).

Verifies that:
T1. Diabetes patient skipping blood sugar reading and answering 'skip' never receives
    an invented 35.0 mg/dL reading or false EMERGENCY triage.
T2. Checkpoint answers 'not sure', 'don't know', 'maloom nahi' without a prior reading
    never create an invented reading or trigger emergency triage.
T3. Invariant: when a patient enters no digits across any answer, the final triage
    readings dict is strictly empty ({}) across diabetes, hypertension, and dual patients.
T4. Real low path still works: entering '35' followed by 'don't know' to the unit question
    preserves possible_severe_low=True, safety guidance, and review-level triage.
"""

import os
import re
import time
import datetime
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
TEST_KID = "test-key-id-hotfix2"


@pytest.fixture(scope="module")
def rsa_key_pair():
    """Generates an RSA private/public key pair for test token signing."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="module")
def x509_cert_pem(rsa_key_pair) -> str:
    """Generates a self-signed x509 certificate for the RSA public key."""
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
    """Sets up clean temporary SQLite database and mocks Firebase token verification."""
    test_db_path = str(tmp_path / "test_hotfix2.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("ISOLATED_MODE", "true")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)


def create_token(rsa_key_pair, sub: str = "uid-hotfix2-patient", email: str = "patient@demo.com") -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "name": "Hotfix2 Patient",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key_pair, algorithm="RS256", headers={"kid": TEST_KID})


def bootstrap_patient(
    client: TestClient,
    token: str,
    conditions=("diabetes",),
    on_insulin: bool = False,
    language: str = "en",
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    r_sess = client.post("/api/auth/session", headers=headers)
    assert r_sess.status_code == 200, r_sess.text
    r_cons = client.post("/api/me/consent", headers=headers, json={"granted": True})
    assert r_cons.status_code == 200, r_cons.text
    r_prof = client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": list(conditions),
            "on_insulin_or_sulfonylurea": on_insulin,
            "language": language,
        },
    )
    assert r_prof.status_code == 200, r_prof.text


def drive_checkin(client: TestClient, headers: dict, answer_sequence: list) -> dict:
    """Helper to start, answer sequentially, and complete a check-in."""
    start_resp = client.post("/api/checkins/start", headers=headers)
    assert start_resp.status_code == 200, start_resp.text
    chk = start_resp.json()
    chk_id = chk["checkin_id"]

    curr = chk
    ans_idx = 0
    while not curr.get("complete"):
        if ans_idx < len(answer_sequence):
            ans = answer_sequence[ans_idx]
            ans_idx += 1
        else:
            ans = "skip"

        ans_resp = client.post(
            f"/api/checkins/{chk_id}/answer",
            headers=headers,
            json={"answer": ans, "step": curr.get("step")},
        )
        assert ans_resp.status_code == 200, ans_resp.text
        curr = ans_resp.json()
        if curr.get("emergency"):
            break

    comp_resp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp_resp.status_code == 200, comp_resp.text
    return comp_resp.json()


# =============================================================================
# T1: Exact Repro (diabetes, "im feeling very bad", then "skip" to all)
# =============================================================================

@pytest.mark.parametrize("orchestrator", ["direct", "graph"])
def test_t1_exact_reproduction_no_emergency_no_invented_35(rsa_key_pair, monkeypatch, orchestrator):
    """
    T1: Exact repro through real API:
    diabetes patient, isolated mode ->
    Q 'How are you feeling?' answer 'im feeling very bad' ->
    Q 'Have you measured your blood sugar today?' answer 'skip' ->
    Q 'Can you tell me roughly how you've been feeling instead...?' answer 'skip' ->
    ... every other answer 'skip' ->
    Assert NOT emergency, readings contain NO glucose, no '35' anywhere in triage JSON.
    """
    monkeypatch.setenv("ORCHESTRATOR", orchestrator)
    client = TestClient(app)
    token = create_token(rsa_key_pair, sub=f"t1-pat-{orchestrator}", email=f"t1-{orchestrator}@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])
    headers = {"Authorization": f"Bearer {token}"}

    answers = ["im feeling very bad", "skip", "skip", "skip", "skip", "skip"]
    res = drive_checkin(client, headers, answers)

    # 1. Emergency must be False
    assert res.get("emergency") is False, f"Expected emergency=False, got: {res.get('emergency')}"

    # 2. Triage level must NOT be emergency
    triage = res.get("triage") or {}
    assert triage.get("level") != "emergency", f"Expected non-emergency level, got: {triage.get('level')}"

    # 3. Protocol must NOT be glucose_low
    assert triage.get("protocol") != "glucose_low", f"Unexpected glucose_low protocol: {triage.get('protocol')}"

    # 4. Readings must contain NO glucose
    readings = triage.get("readings") or {}
    assert "glucose" not in readings, f"Invented glucose reading found: {readings.get('glucose')}"

    # 5. String '35' must not appear anywhere in triage readings or summary
    assert "35" not in str(readings), f"'35' found in readings: {readings}"
    assert "35" not in (triage.get("summary") or ""), f"'35' found in summary: {triage.get('summary')}"
    assert "35" not in str(triage.get("reasons") or []), f"'35' found in reasons: {triage.get('reasons')}"

    # 6. Intakes readings must not contain any glucose reading
    for intake in res.get("intakes", []):
        for r in intake.get("readings", []):
            assert r.get("observation_type") != "glucose" or r.get("value") is None, f"Intake contains invented glucose: {r}"


# =============================================================================
# T2: Checkpoint answers 'not sure', 'don't know', 'maloom nahi'
# =============================================================================

@pytest.mark.parametrize("checkpoint_ans", ["not sure", "don't know", "dont know", "maloom nahi", "nahi pata"])
def test_t2_checkpoint_variations_no_fake_reading(rsa_key_pair, monkeypatch, checkpoint_ans):
    """
    T2: Diabetic patient skips reading, then answers checkpoint with uncertainty
    phrases ('not sure', 'don't know', 'maloom nahi'). Must not invent a reading.
    """
    monkeypatch.setenv("ORCHESTRATOR", "direct")
    client = TestClient(app)
    token = create_token(rsa_key_pair, sub=f"t2-pat-{checkpoint_ans[:6]}", email=f"t2-{checkpoint_ans[:6]}@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])
    headers = {"Authorization": f"Bearer {token}"}

    answers = ["im feeling very bad", "skip", checkpoint_ans, "skip", "skip", "skip"]
    res = drive_checkin(client, headers, answers)

    assert res.get("emergency") is False
    triage = res.get("triage") or {}
    assert triage.get("level") != "emergency"
    assert triage.get("protocol") != "glucose_low"

    readings = triage.get("readings") or {}
    assert "glucose" not in readings
    assert "35" not in str(readings)


# =============================================================================
# T3: INVARIANT test ("no invented readings")
# =============================================================================

@pytest.mark.parametrize("conds", [["diabetes"], ["hypertension"], ["diabetes", "hypertension"]])
@pytest.mark.parametrize("script_name,answers", [
    ("all_skip", ["skip", "skip", "skip", "skip", "skip", "skip", "skip"]),
    ("symptom_words_en", ["im feeling dizzy and tired", "no reading", "not sure", "no", "no changes"]),
    ("roman_urdu", ["tabiyat theek nahi", "skip", "maloom nahi", "nahi pata", "koi takleef nahi"]),
    ("urdu", ["طبیعت ناساز ہے", "معلوم نہیں", "چھوڑ دیں", "نہیں", "کوئی تکلیف نہیں"]),
])
def test_t3_invariant_no_digits_yields_empty_readings(rsa_key_pair, monkeypatch, conds, script_name, answers):
    """
    T3: Invariant test across diabetes, hypertension, and dual conditions:
    When a patient inputs zero numeric digits throughout the interview,
    the final triage readings dictionary must be strictly empty ({}).
    """
    monkeypatch.setenv("ORCHESTRATOR", "direct")
    client = TestClient(app)
    uid = f"t3-{'-'.join(conds)}-{script_name}"
    token = create_token(rsa_key_pair, sub=uid, email=f"{uid}@demo.com")
    bootstrap_patient(client, token, conditions=conds)
    headers = {"Authorization": f"Bearer {token}"}

    # Verify our test script has zero digits
    for a in answers:
        assert not re.search(r"\d", a), f"Test answer '{a}' inadvertently contains digits"

    res = drive_checkin(client, headers, answers)

    triage = res.get("triage") or {}
    readings = triage.get("readings") or {}

    assert readings == {}, f"Invariant violated: expected empty readings dict for non-digit inputs, got {readings}"

    # Also verify intake observations contain no numeric values
    for intake in res.get("intakes", []):
        for r in intake.get("readings", []):
            val = r.get("value")
            assert val is None, f"Invariant violated: intake observation has numeric value {val}"


# =============================================================================
# T4: Real severe low unit ambiguity path still works
# =============================================================================

def test_t4_real_severe_low_path_preserved(rsa_key_pair, monkeypatch):
    """
    T4: Patient actually enters '35' without unit -> asked unit clarification -> answers 'don't know'.
    The real clinical rule must be preserved:
    - possible_severe_low is True
    - safety guidance is attached (contains 'quick sugar')
    - review reason is 'glucose value unit unclear, possible low'
    - triage requires review (not routine)
    """
    monkeypatch.setenv("ORCHESTRATOR", "direct")
    client = TestClient(app)
    token = create_token(rsa_key_pair, sub="t4-pat-real-low", email="t4@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])
    headers = {"Authorization": f"Bearer {token}"}

    # Start checkin
    start_resp = client.post("/api/checkins/start", headers=headers)
    assert start_resp.status_code == 200
    chk = start_resp.json()
    chk_id = chk["checkin_id"]

    # Turn 1: feeling
    t1 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers=headers,
        json={"answer": "feeling ok", "step": chk["step"]},
    ).json()

    # Turn 2: glucose reading -> '35' (bare number in 2.0-40.0)
    t2 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers=headers,
        json={"answer": "35", "step": t1["step"]},
    ).json()

    # Verify unit clarification is triggered
    assert t2.get("step") == "missing_data_checkpoint"
    q_text = t2.get("question") or t2.get("next_question") or ""
    assert "mg/dL" in q_text or "mmol/L" in q_text or "unit" in q_text.lower()

    # Turn 3: Patient cannot clarify unit: 'don't know'
    t3 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers=headers,
        json={"answer": "don't know", "step": t2["step"]},
    ).json()

    # Finish remaining questions
    curr = t3
    while not curr.get("complete"):
        curr = client.post(
            f"/api/checkins/{chk_id}/answer",
            headers=headers,
            json={"answer": "no", "step": curr["step"]},
        ).json()
        if curr.get("emergency"):
            break

    comp_resp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp_resp.status_code == 200
    res = comp_resp.json()

    # Check that safety flags and review are preserved
    intakes = res.get("intakes", [])
    assert len(intakes) > 0
    diabetes_intake = intakes[0]
    symptoms = diabetes_intake.get("symptoms", {})

    assert symptoms.get("possible_severe_low") is True
    guidance = symptoms.get("safety_guidance") or ""
    assert "quick sugar" in guidance.lower()
    assert symptoms.get("review_reason") == "glucose value unit unclear, possible low"

    # Triage must require review
    assert res.get("requires_review") is True
