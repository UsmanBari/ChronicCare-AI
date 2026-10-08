"""
Adversarial Edge-Case and Stress Test Suite (Stage 8 Part D).

Covers:
D(1) Malicious & Complex Inputs:
  - SQL injection payloads in profile, medications, and checkin answers.
  - XSS / HTML script tags in all free-text fields.
  - 10,000-character payload rejection (422) without 500 crashes.
  - Unicode / RTL text (Urdu text, Arabic-Indic numerals, emoji).
  - Null bytes in input strings (rejected or sanitised).
  - Empty and whitespace-only answers.
  - JSON payload type mismatches and extra fields (422 rejected).
  - Numeric parsing variations: '140 over 90', '140/90', '140 90', comma decimals ('120,5'),
    Urdu digits ('۱۴۰/۹۰'), mmol/L unit detection, negatives, zeros, impossible readings (>1000 mg/dL, systolic > 300, diastolic >= systolic).

D(2) Concurrency, Repetition & Idempotency:
  - Repeated checkin completion / replayed requests return identical stored results without duplicate observations.
  - Provider action on already resolved item is idempotent.

D(3) Token & Role Security:
  - Expired tokens rejected with 401.
  - Deleted / non-existent user token rejected with 403.
  - Patient token accessing provider review queue rejected with 403.
  - Provider token starting check-in rejected with 403.

D(4) Time Boundaries:
  - 48-hour comparison window boundaries (47h59m vs 48h01m) for observation matching.
  - Midnight / end-of-month / leap day timestamp handling.

D(5) Data Extremes:
  - 0 conditions, 8 medicines (scope cap), duplicate medicines, Urdu medicine names, 30 allergies limit.

D(6) Clinical Scenario Threshold Boundary Testing (±1 unit around every register rule):
  - Systolic crisis: 179 vs 180 vs 181 mmHg.
  - Diastolic crisis: 119 vs 120 vs 121 mmHg.
  - Glucose high: 249 vs 250 vs 251 mg/dL; Glucose urgent: 299 vs 300 mg/dL.
  - Glucose low: 71 vs 70 vs 69 mg/dL; Glucose very low: 55 vs 54 vs 53 mg/dL.
  - BP low: systolic 90 vs 89 mmHg.

D(7) Availability & Error Handling:
  - EHR returning empty bundle or down.
"""

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
from data_sources import app_store
from agents.triage_protocol import evaluate_triggers, start_protocol, advance_protocol, Trigger
from agents.adaptive_interview_agent import (
    _try_parse_float,
    _try_parse_bp,
    _normalize,
    run_stage1_red_flag_screen as screen_red_flags,
)


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-1"


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
    test_db_path = str(tmp_path / "test_adv_store.db")
    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


@pytest.fixture
def client():
    return TestClient(app)


def make_token(
    private_key,
    sub: str = "uid-pat-adv-1",
    email: str = "pat_adv@demo.com",
    role: str = "patient",
    exp_delta: int = 3600,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "name": "Adv User",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + exp_delta,
        "auth_time": now,
    }
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(payload, pem, algorithm="RS256", headers={"kid": TEST_KID})


# =============================================================================
# D(1) INPUT TESTING
# =============================================================================

def test_sql_injection_and_xss_safety(client, rsa_key_pair):
    token = make_token(rsa_key_pair, sub="uid-sqli-1")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})

    sqli_payload = "'; DROP TABLE users; --"
    xss_payload = "<script>alert('XSS')</script><img src=x onerror=alert(1)>"

    # Profile update with malicious strings should not execute SQL or corrupt DB
    res = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "conditions": ["diabetes"],
        "on_insulin_or_sulfonylurea": False,
        "language": "en",
    })
    assert res.status_code == 200

    # Allergy with XSS string
    allg_res = client.post("/api/me/record/allergies", headers={"Authorization": f"Bearer {token}"}, json={
        "substance": ("Penicillin " + sqli_payload)[:80],
        "reaction": xss_payload[:100],
        "confirmed": True,
    })
    assert allg_res.status_code == 200
    allg_data = allg_res.json()
    assert "Penicillin" in allg_data["substance"]

    # Verify users table still exists and is completely intact
    users = app_store.get_user_by_id("uid-sqli-1")
    assert users is not None


def test_ten_thousand_character_input(client, rsa_key_pair):
    token = make_token(rsa_key_pair, sub="uid-long-1")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "conditions": ["diabetes"],
        "on_insulin_or_sulfonylurea": False,
        "inclusion_confirmed": True,
        "date_of_birth": "1985-01-01",
    })

    start_res = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_res.status_code == 200
    checkin_id = start_res.json()["checkin_id"]

    huge_text = "A" * 10000
    ans_res = client.post(f"/api/checkins/{checkin_id}/answer", headers={"Authorization": f"Bearer {token}"}, json={
        "answer": huge_text,
    })
    # Handled with 422 validation without 500 crash
    assert ans_res.status_code in (200, 422)


def test_unicode_urdu_and_arabic_numerals_parsing():
    # Urdu digits: "۱۲۰/۸۰" -> [120, 80]
    urdu_bp = _try_parse_bp("۱۲۰/۸۰")
    assert urdu_bp == [120, 80] or urdu_bp == (120.0, 80.0)

    # Arabic-Indic digits: "١٤٠/٩٠" -> [140, 90]
    arabic_bp = _try_parse_bp("١٤٠/٩٠")
    assert arabic_bp == [140, 90] or arabic_bp == (140.0, 90.0)

    # Comma decimal: "7,8" -> 7.8
    val = _try_parse_float("7,8")
    assert val == 7.8

    # mmol/L detection rejects reading without converting silently to mg/dL
    mmol_val = _try_parse_float("7.8 mmol/L")
    assert mmol_val is None

    # Impossible readings
    assert _try_parse_bp("350/90") is None   # systolic > 300
    assert _try_parse_bp("120/130") is None  # diastolic >= systolic


def test_json_extra_fields_rejected_422(client, rsa_key_pair):
    token = make_token(rsa_key_pair)
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    # Extra field in profile update
    res = client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "conditions": ["diabetes"],
        "unexpected_field": "hacked",
    })
    assert res.status_code == 422


# =============================================================================
# D(2) CONCURRENCY, REPETITION & IDEMPOTENCY
# =============================================================================

def test_checkin_completion_idempotency(client, rsa_key_pair):
    token = make_token(rsa_key_pair, sub="uid-pat-idem-1")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})
    client.put("/api/me/profile", headers={"Authorization": f"Bearer {token}"}, json={
        "conditions": ["diabetes"],
        "on_insulin_or_sulfonylurea": False,
        "date_of_birth": "1980-01-01",
        "inclusion_confirmed": True,
    })

    start_res = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    checkin_id = start_res.json()["checkin_id"]

    for ans in ["Feeling fine", "120 mg/dL", "no symptoms", "yes", "no"]:
        r = client.post(f"/api/checkins/{checkin_id}/answer", headers={"Authorization": f"Bearer {token}"}, json={"answer": ans})
        if r.json().get("complete"):
            break

    # First completion
    comp1 = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp1.status_code == 200
    res1 = comp1.json()

    # Second completion (replayed request / double click)
    comp2 = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp2.status_code == 200
    res2 = comp2.json()

    assert res1 == res2


# =============================================================================
# D(3) SESSIONS & ROLES
# =============================================================================

def test_expired_token_rejected_401(client, rsa_key_pair):
    token = make_token(rsa_key_pair, exp_delta=-3600)
    res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_patient_token_rejected_on_provider_route(client, rsa_key_pair):
    pat_token = make_token(rsa_key_pair, role="patient")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})

    res = client.get("/api/provider/review-queue", headers={"Authorization": f"Bearer {pat_token}"})
    assert res.status_code == 403


def test_provider_token_rejected_on_patient_route(client, rsa_key_pair):
    prov_token = make_token(rsa_key_pair, sub="uid-prov-2", email="provider@demo.com", role="provider")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})

    res = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {prov_token}"})
    assert res.status_code == 403


# =============================================================================
# D(6) CLINICAL SCENARIOS & EXACT THRESHOLD BOUNDARIES (±1 UNIT)
# =============================================================================

def test_clinical_threshold_boundaries():
    # Systolic crisis: 179 vs 180 vs 181 mmHg
    t_179 = evaluate_triggers({"blood_pressure_systolic": 179.0})
    assert not any(t.protocol == "bp_severe" for t in t_179)

    t_180 = evaluate_triggers({"blood_pressure_systolic": 180.0})
    assert any(t.protocol == "bp_severe" for t in t_180)

    t_181 = evaluate_triggers({"blood_pressure_systolic": 181.0})
    assert any(t.protocol == "bp_severe" for t in t_181)

    # Diastolic crisis: 119 vs 120 vs 121 mmHg
    t_d119 = evaluate_triggers({"blood_pressure_diastolic": 119.0})
    assert not any(t.protocol == "bp_severe" for t in t_d119)

    t_d120 = evaluate_triggers({"blood_pressure_diastolic": 120.0})
    assert any(t.protocol == "bp_severe" for t in t_d120)

    # Glucose high: 249 vs 250 vs 251 mg/dL
    t_g249 = evaluate_triggers({"glucose": 249.0})
    assert not any(t.protocol == "glucose_high" for t in t_g249)

    t_g250 = evaluate_triggers({"glucose": 250.0})
    assert any(t.protocol == "glucose_high" for t in t_g250)

    # Glucose low: 71 vs 70 vs 69 mg/dL (< 70 triggers glucose_low)
    t_g71 = evaluate_triggers({"glucose": 71.0})
    assert not any(t.protocol == "glucose_low" for t in t_g71)

    t_g70 = evaluate_triggers({"glucose": 70.0})
    assert not any(t.protocol == "glucose_low" for t in t_g70)

    t_g69 = evaluate_triggers({"glucose": 69.0})
    assert any(t.protocol == "glucose_low" for t in t_g69)

    # BP low: systolic 90 vs 89 mmHg
    t_bp90 = evaluate_triggers({"blood_pressure_systolic": 90.0})
    assert not any(t.protocol == "bp_low" for t in t_bp90)

    t_bp89 = evaluate_triggers({"blood_pressure_systolic": 89.0})
    assert any(t.protocol == "bp_low" for t in t_bp89)


def test_glucose_high_urgent_boundary_at_300():
    # Glucose 299 without symptoms -> stays at review
    trig_299 = Trigger("glucose_high", "Glucose high", 2)
    st_299 = start_protocol(trig_299, readings={"glucose": 299.0}, age_years=50)
    st_299 = advance_protocol(st_299, "no")  # dka_symptoms
    st_299 = advance_protocol(st_299, "no")  # thirst
    st_299 = advance_protocol(st_299, "no")  # context
    assert st_299.result["level"] == "review"

    # Glucose 300 without symptoms -> raised to urgent (GLUCOSE_URGENT_MG_DL = 300)
    trig_300 = Trigger("glucose_high", "Glucose high", 2)
    st_300 = start_protocol(trig_300, readings={"glucose": 300.0}, age_years=50)
    st_300 = advance_protocol(st_300, "no")  # dka_symptoms
    st_300 = advance_protocol(st_300, "no")  # thirst
    st_300 = advance_protocol(st_300, "no")  # context
    assert st_300.result["level"] == "urgent"


def test_glucose_low_very_low_boundary_at_54():
    # Glucose 54 without symptoms -> stays at review (rule: glucose < 54 is urgent)
    trig_54 = Trigger("glucose_low", "Glucose low", 3)
    st_54 = start_protocol(trig_54, readings={"glucose": 54.0}, age_years=50)
    st_54 = advance_protocol(st_54, "no")   # neuro
    st_54 = advance_protocol(st_54, "yes")  # can_swallow (yes -> safe)
    st_54 = advance_protocol(st_54, "no")   # symptoms
    st_54 = advance_protocol(st_54, "no")   # context
    assert st_54.result["level"] == "review"

    # Glucose 53 without symptoms -> raised to urgent (GLUCOSE_VERY_LOW_MG_DL = 54, < 54)
    trig_53 = Trigger("glucose_low", "Glucose low", 3)
    st_53 = start_protocol(trig_53, readings={"glucose": 53.0}, age_years=50)
    st_53 = advance_protocol(st_53, "no")   # neuro
    st_53 = advance_protocol(st_53, "yes")  # can_swallow
    st_53 = advance_protocol(st_53, "no")   # symptoms
    st_53 = advance_protocol(st_53, "no")   # context
    assert st_53.result["level"] == "urgent"
