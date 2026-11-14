"""
Tests for Check-in with No Readings Explanation & Template (Day 7b).

Validates:
1. build_query_from_triage mapping for no-readings routine vs routine with readings.
2. check_llm_eligibility returns (False, 'no_readings_template') for routine_no_readings.
3. guarded_explain returns routine_no_readings template with mode 'template',
   reason 'no_readings_template', tokens_used 0, and 0 LLM calls across en, ur, roman_ur.
4. With >= 1 reading, old routine template behaviour is completely unchanged.
5. End-to-end FastAPI testclient check-in completes with level 'routine',
   patient explanation displaying the new template in en, ur, and roman_ur,
   and provider view storing reason 'no_readings_template'.
"""
import datetime
import os
import sys
import time
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
from rag.query_map import build_query_from_triage
from rag.explain_guards import check_llm_eligibility, guarded_explain

TEST_PROJECT_ID = "test-r8-explain-proj"
TEST_KID = "test-r8-explain-kid"


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
    db_file = str(tmp_path / "test_r8_explain.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("ORCHESTRATOR", "direct")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
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


def _bootstrap(client, token, condition="hypertension", lang="en"):
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})
    client.post("/api/me/consent/provider-notification", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "conditions": [condition],
            "on_insulin_or_sulfonylurea": False,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": lang,
        },
    )


# =============================================================================
# 1. Query Map & Eligibility Unit Tests
# =============================================================================
def test_build_query_from_triage_no_readings():
    """Verify build_query_from_triage maps routine check-in without readings to routine_no_readings."""
    # When readings is empty or None
    q1 = build_query_from_triage({"level": "routine"}, readings={})
    assert q1.trigger_category == "routine_no_readings"
    assert q1.condition == "both"

    q2 = build_query_from_triage({"level": "routine"}, readings=None)
    assert q2.trigger_category == "routine_no_readings"

    # When all reading values are None
    q3 = build_query_from_triage(
        {"level": "routine"},
        readings={"blood_pressure_systolic": None, "blood_pressure_diastolic": None, "glucose": None},
    )
    assert q3.trigger_category == "routine_no_readings"

    # When at least 1 reading is present, maps to regular routine
    q4 = build_query_from_triage(
        {"level": "routine"},
        readings={"blood_pressure_systolic": 118.0, "blood_pressure_diastolic": 76.0},
    )
    assert q4.trigger_category == "routine"

    q5 = build_query_from_triage(
        {"level": "routine"},
        readings={"glucose": 110.0},
    )
    assert q5.trigger_category == "routine"


def test_check_llm_eligibility_routine_no_readings():
    """Verify check_llm_eligibility rejects routine_no_readings with reason no_readings_template."""
    ok, reason = check_llm_eligibility(
        condition="hypertension",
        trigger_category="routine_no_readings",
        language="en",
    )
    assert ok is False
    assert reason == "no_readings_template"


# =============================================================================
# 2. Guarded Explainer Unit Tests across en, ur, roman_ur
# =============================================================================
def test_guarded_explain_no_readings_english():
    """Verify guarded_explain returns the new routine_no_readings template in English."""
    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={},
        language="en",
        condition="hypertension",
    )
    assert res["mode"] == "template"
    assert res["reason"] == "no_readings_template"
    assert res["tokens_used"] == 0
    assert res["provider"] is None
    assert res["providers_tried"] == []

    expected_en = [
        "You did not enter a blood sugar or blood pressure reading today.",
        "You did not report any warning signs today.",
        "Adding a reading next time helps track your health over time.",
    ]
    texts = [s["text"] for s in res["sentences"]]
    assert texts == expected_en


def test_guarded_explain_no_readings_urdu():
    """Verify guarded_explain returns the new routine_no_readings template in Urdu."""
    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={},
        language="ur",
        condition="hypertension",
    )
    assert res["mode"] == "template"
    assert res["reason"] == "no_readings_template"
    assert res["tokens_used"] == 0

    expected_ur = [
        "آپ نے آج بلڈ شوگر یا بلڈ پریشر کی کوئی ریڈنگ درج نہیں کی۔",
        "آپ نے آج کسی خطرے کی علامت کی اطلاع نہیں دی۔",
        "اگلی بار ریڈنگ شامل کرنا وقت کے ساتھ آپ کی صحت کی نگرانی میں مدد کرتا ہے۔"
    ]
    texts = [s["text"] for s in res["sentences"]]
    assert texts == expected_ur


def test_guarded_explain_no_readings_roman_urdu():
    """Verify guarded_explain returns the new routine_no_readings template in Roman Urdu."""
    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={},
        language="roman_ur",
        condition="hypertension",
    )
    assert res["mode"] == "template"
    assert res["reason"] == "no_readings_template"
    assert res["tokens_used"] == 0

    expected_roman_ur = [
        "Aap ne aaj blood sugar ya blood pressure ki koi reading darj nahi ki.",
        "Aap ne aaj kisi khatray ki alamat ki ittila nahi di.",
        "Agli baar reading shamil karna waqt ke sath aap ki sehat ki nigrani mein madad karta hai."
    ]
    texts = [s["text"] for s in res["sentences"]]
    assert texts == expected_roman_ur


def test_guarded_explain_with_reading_uses_regular_routine_template():
    """Verify guarded_explain preserves regular routine template when readings are present."""
    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 118.0, "blood_pressure_diastolic": 76.0},
        language="en",
        condition="hypertension",
    )
    assert res["mode"] == "template"
    # When readings are provided, it must NOT use no_readings_template
    assert res["reason"] != "no_readings_template"
    first_sentence = res["sentences"][0]["text"]
    assert first_sentence == "Your reported readings are within your agreed target monitoring range today."


# =============================================================================
# 3. End-to-End API Integration Tests (v2 engine, no readings vs 1 reading)
# =============================================================================
@pytest.mark.parametrize("lang,expected_first_sentence", [
    ("en", "You did not enter a blood sugar or blood pressure reading today."),
    ("ur", "آپ نے آج بلڈ شوگر یا بلڈ پریشر کی کوئی ریڈنگ درج نہیں کی۔"),
    ("roman_ur", "Aap ne aaj blood sugar ya blood pressure ki koi reading darj nahi ki."),
])
def test_e2e_checkin_complete_no_readings_template(rsa_key_pair, monkeypatch, lang, expected_first_sentence):
    """Rule R8: Check-in with no readings routes to routine and gets new template in target language."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v2")
    token = _get_token(rsa_key_pair, uid=f"u-r8-{lang}", email=f"r8-{lang}@demo.care")

    client = TestClient(app)
    _bootstrap(client, token, condition="hypertension", lang=lang)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    cid = start_resp.json()["checkin_id"]

    # Flow: greeting -> no reading -> checkpoint: no reading -> symptoms: no -> adherence: yes -> fine
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

    # Clinical Invariant: Triage is routine and no doctor review required
    assert data["requires_review"] is False
    assert data["triage"]["level"] == "routine"

    # Patient Explanation View: matches new template
    assert data["explanation"] is not None
    assert data["explanation"]["status"] == "ready"
    sentences = [s["text"] for s in data["explanation"]["sentences"]]
    assert len(sentences) == 3
    assert sentences[0] == expected_first_sentence

    # Provider View: stores reason "no_readings_template" with 0 tokens used
    stored = app_store.get_checkin_result(cid)
    assert stored is not None
    expl = stored["explanation"]
    assert expl["mode"] == "template"
    assert expl["reason"] == "no_readings_template"
    assert expl["tokens_used"] == 0
    assert expl["provider"] is None
    assert expl["providers_tried"] == []


def test_e2e_checkin_complete_with_one_reading_unchanged(rsa_key_pair, monkeypatch):
    """Check-in with a reading and no symptoms keeps original routine template."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v2")
    token = _get_token(rsa_key_pair, uid="u-r8-with-reading", email="r8-with-reading@demo.care")

    client = TestClient(app)
    _bootstrap(client, token, condition="hypertension", lang="en")

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    cid = start_resp.json()["checkin_id"]

    # Answer flow with BP reading: 118/76
    answers = [
        "Feeling fine",
        "My BP is 118/76",
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

    assert data["explanation"] is not None
    assert data["explanation"]["status"] == "ready"
    sentences = [s["text"] for s in data["explanation"]["sentences"]]
    # Must use original routine template
    assert sentences[0] == "Your reported readings are within your agreed target monitoring range today."
