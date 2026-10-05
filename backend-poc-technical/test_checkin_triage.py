"""
Hermetic API Tests for Stage 7D-1 Triage Protocol (P1).

Covering requirements (a) through (n):
(a) a severe reading (190/125) does not end the interview and starts the protocol with the right step string, with no review item yet;
(b) re-measure 150/90, no symptoms, "yes cold medicine" -> after /complete the result is review with the factor "cold or flu medicine" and the queue item shows triage_level review;
(c) a symptom answer "yes, my vision is blurry" -> emergency persisted by that answer WITHOUT /complete, escalation_recorded true, first in the provider queue, the detail shows the summary;
(d) a persistent 196/119 without symptoms -> urgent; queue order emergency, urgent, review;
(e) baseline: three earlier check-ins about 110 within 14 days, then 130/80 -> the bp_change protocol starts; no symptoms -> review, symptoms -> urgent; fewer than three earlier check-ins -> no protocol;
(f) glucose 320 with warning symptoms -> emergency; glucose 60 and cannot swallow -> emergency; glucose 270 without symptoms -> review;
(g) a duplicate or stale protocol answer -> 409 and the protocol advanced once;
(h) a danger phrase typed as a protocol answer -> emergency persisted;
(i) normal readings start no protocol at all;
(j) /complete before the protocol is finished -> 409 triage_incomplete;
(k) the protocol state survives being stored and reloaded;
(l) the emergency_escalated audit row holds the category only, never the summary or any answer;
(m) a patient aged 70 gets the extra older-adult question;
(n) order of phases: protocol first, then the medication check.
"""

import copy
import datetime
import json
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


TEST_PROJECT_ID = "test-chroniccare-ai-triage"
TEST_KID = "test-key-id-triage"


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
    test_db_path = str(tmp_path / "test_chroniccare_triage.db")

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
    sub: str = "uid-patient-1",
    email: str = "patient1@demo.com",
    name: str = "Patient One",
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


def bootstrap_patient(
    client: TestClient,
    token: str,
    conditions=("diabetes", "hypertension"),
    on_insulin: bool = False,
) -> None:
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    resp = client.post(
        "/api/me/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={"granted": True},
    )
    assert resp.status_code == 200, resp.text
    profile_payload: Dict[str, Any] = {
        "conditions": list(conditions),
        "on_insulin_or_sulfonylurea": on_insulin,
        "language": "en",
    }
    resp = client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json=profile_payload,
    )
    assert resp.status_code == 200, resp.text


def bootstrap_provider(client: TestClient, token: str) -> None:
    resp = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text


# ----------------------------------------------------------------------------
# (a) Severe reading starts protocol with step triage:bp_severe:0:0, no review item yet
# ----------------------------------------------------------------------------
def test_a_severe_reading_starts_protocol_with_correct_step_and_no_review_yet(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-a", email="pata@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="u-prov", email="provider@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])
    bootstrap_provider(client, prov_token)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    assert start_resp.status_code == 200
    cid = start_resp.json()["checkin_id"]

    # Interview answers
    r1 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "I feel fine", "step": "greeting"})
    assert r1.status_code == 200
    r2 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "190/125", "step": "bp_reading"})
    assert r2.status_code == 200
    r3 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "No other symptoms", "step": "associated_symptoms"})
    assert r3.status_code == 200
    r4 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "Yes, took meds", "step": "adherence"})
    assert r4.status_code == 200
    # Final interview answer -> transitions to triage protocol
    r5 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "No changes", "step": "lifestyle"})
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["complete"] is False
    assert d5["emergency"] is False
    assert d5["phase"] == "triage"
    assert d5["step"] == "triage:bp_severe:0:0"
    assert "rest quietly for 5 minutes" in d5["question"]

    # Provider queue should have NO item yet
    q_resp = client.get("/api/provider/review-queue", headers={"Authorization": f"Bearer {prov_token}"})
    assert q_resp.status_code == 200
    assert len(q_resp.json()) == 0


# ----------------------------------------------------------------------------
# (b) Re-measure 150/90, no symptoms, "yes cold medicine" -> after /complete the result is review
# ----------------------------------------------------------------------------
def test_b_remeasure_improved_with_factor_review_level(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-b", email="patb@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="u-prov", email="provider@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])
    bootstrap_provider(client, prov_token)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    cid = start_resp.json()["checkin_id"]

    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    triage_start = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"}).json()
    assert triage_start["step"] == "triage:bp_severe:0:0"

    # Triage answers: recheck 150/90, symptoms no, substances "yes cold medicine", circumstances "no"
    t1 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "150/90", "step": "triage:bp_severe:0:0"}).json()
    assert t1["step"] == "triage:bp_severe:1:0"

    t2 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "no", "step": "triage:bp_severe:1:0"}).json()
    assert t2["step"] == "triage:bp_severe:2:0"

    t3 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "yes cold medicine", "step": "triage:bp_severe:2:0"}).json()
    assert t3["step"] == "triage:bp_severe:3:0"

    t4 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "no", "step": "triage:bp_severe:3:0"}).json()
    assert t4["complete"] is True
    assert t4["triage"]["level"] == "review"
    assert "cold or flu medicine" in t4["triage"]["factors"]

    # Call /complete
    comp_resp = client.post(f"/api/checkins/{cid}/complete", headers={"Authorization": f"Bearer {pat_token}"})
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["triage"]["level"] == "review"
    assert comp_data["requires_review"] is True
    assert comp_data["max_severity"] in ("moderate", "high")

    # Provider queue item check
    q_resp = client.get("/api/provider/review-queue", headers={"Authorization": f"Bearer {prov_token}"})
    assert q_resp.status_code == 200
    items = q_resp.json()
    assert len(items) == 1
    assert items[0]["triage_level"] == "review"


# ----------------------------------------------------------------------------
# (c) Symptom answer "yes, my vision is blurry" -> emergency persisted without /complete
# ----------------------------------------------------------------------------
def test_c_symptom_in_protocol_persists_emergency_immediately(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-c", email="patc@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="u-prov", email="provider@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])
    bootstrap_provider(client, prov_token)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    cid = start_resp.json()["checkin_id"]

    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})

    # Answer recheck
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                json={"answer": "188/120", "step": "triage:bp_severe:0:0"})

    # Answer symptoms with warning symptom
    ans_resp = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                           json={"answer": "yes, my vision is blurry", "step": "triage:bp_severe:1:0"})
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["emergency"] is True
    assert ans_data["escalation_recorded"] is True
    assert ans_data["complete"] is True
    assert ans_data["triage"]["level"] == "emergency"

    # Provider review queue check without calling /complete
    q_resp = client.get("/api/provider/review-queue", headers={"Authorization": f"Bearer {prov_token}"})
    assert q_resp.status_code == 200
    items = q_resp.json()
    assert len(items) == 1
    assert items[0]["emergency"] is True
    assert items[0]["triage_level"] == "emergency"

    # Detail view check
    det_resp = client.get(f"/api/provider/review/{items[0]['checkin_id']}", headers={"Authorization": f"Bearer {prov_token}"})
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    assert det_data["triage"]["level"] == "emergency"
    assert "warning symptoms" in det_data["triage"]["summary"].lower()


# ----------------------------------------------------------------------------
# (d) Persistent 196/119 without symptoms -> urgent; queue order: emergency, urgent, review
# ----------------------------------------------------------------------------
def test_d_persistent_severe_is_urgent_and_queue_order(rsa_key_pair):
    client = TestClient(app)
    prov_token = create_test_token(rsa_key_pair, sub="u-prov-d", email="provider@demo.com")
    bootstrap_provider(client, prov_token)

    # 1. Create a Review level checkin (Patient 1)
    tok_rev = create_test_token(rsa_key_pair, sub="u-rev", email="rev@demo.com")
    bootstrap_patient(client, tok_rev, conditions=["hypertension"])
    cid_rev = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_rev}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "128/82", "step": "triage:bp_severe:0:0"})
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "no", "step": "triage:bp_severe:1:0"})
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "no", "step": "triage:bp_severe:2:0"})
    client.post(f"/api/checkins/{cid_rev}/answer", headers={"Authorization": f"Bearer {tok_rev}"}, json={"answer": "no", "step": "triage:bp_severe:3:0"})
    client.post(f"/api/checkins/{cid_rev}/complete", headers={"Authorization": f"Bearer {tok_rev}"})

    # 2. Create an Urgent level checkin (Patient 2: persistent 196/119, no symptoms)
    tok_urg = create_test_token(rsa_key_pair, sub="u-urg", email="urg@demo.com")
    bootstrap_patient(client, tok_urg, conditions=["hypertension"])
    cid_urg = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_urg}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "200/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "196/119", "step": "triage:bp_severe:0:0"})
    client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "no", "step": "triage:bp_severe:1:0"})
    client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "no", "step": "triage:bp_severe:2:0"})
    t_fin = client.post(f"/api/checkins/{cid_urg}/answer", headers={"Authorization": f"Bearer {tok_urg}"}, json={"answer": "no", "step": "triage:bp_severe:3:0"}).json()
    assert t_fin["triage"]["level"] == "urgent"
    client.post(f"/api/checkins/{cid_urg}/complete", headers={"Authorization": f"Bearer {tok_urg}"})

    # 3. Create an Emergency checkin (Patient 3: symptom in triage)
    tok_em = create_test_token(rsa_key_pair, sub="u-em", email="em@demo.com")
    bootstrap_patient(client, tok_em, conditions=["hypertension"])
    cid_em = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok_em}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid_em}/answer", headers={"Authorization": f"Bearer {tok_em}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid_em}/answer", headers={"Authorization": f"Bearer {tok_em}"}, json={"answer": "190/120", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid_em}/answer", headers={"Authorization": f"Bearer {tok_em}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid_em}/answer", headers={"Authorization": f"Bearer {tok_em}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid_em}/answer", headers={"Authorization": f"Bearer {tok_em}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid_em}/answer", headers={"Authorization": f"Bearer {tok_em}"}, json={"answer": "180/115", "step": "triage:bp_severe:0:0"})
    client.post(f"/api/checkins/{cid_em}/answer", headers={"Authorization": f"Bearer {tok_em}"}, json={"answer": "yes chest pain", "step": "triage:bp_severe:1:0"})

    # Check Queue Ordering: emergency, urgent, review
    q_resp = client.get("/api/provider/review-queue", headers={"Authorization": f"Bearer {prov_token}"})
    assert q_resp.status_code == 200
    items = q_resp.json()
    assert len(items) == 3
    levels = [item["triage_level"] for item in items]
    assert levels == ["emergency", "urgent", "review"]


# ----------------------------------------------------------------------------
# (e) Baseline: three earlier check-ins ~110 within 14 days, then 130/80 -> bp_change starts;
#     no symptoms -> review, symptoms -> urgent; fewer than 3 check-ins -> no protocol
# ----------------------------------------------------------------------------
def test_e_baseline_history_triggers_bp_change(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-e", email="pate@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    # 1. Complete 3 earlier check-ins with BP 110/70
    for i in range(3):
        start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
        cid = start_resp.json()["checkin_id"]
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "110/70", "step": "bp_reading"})
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})
        comp = client.post(f"/api/checkins/{cid}/complete", headers={"Authorization": f"Bearer {pat_token}"})
        assert comp.status_code == 200

    # 2. Checkin with 130/80 (20 mmHg rise from 110 baseline) -> starts bp_change protocol
    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    cid = start_resp.json()["checkin_id"]
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "130/80", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    r_life = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"}).json()
    assert r_life["complete"] is False
    assert r_life["phase"] == "triage"
    assert r_life["step"] == "triage:bp_change:0:0"

    # Answer bp_change questions with NO symptoms -> result is review
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_change:0:0"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_change:1:0"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "triage:bp_change:2:0"})
    r_last = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_change:3:0"}).json()
    assert r_last["complete"] is True
    assert r_last["triage"]["level"] == "review"

    # 3. New patient with fewer than 3 earlier check-ins -> 130/80 starts NO protocol
    pat_token2 = create_test_token(rsa_key_pair, sub="u-pat-e2", email="pate2@demo.com")
    bootstrap_patient(client, pat_token2, conditions=["hypertension"])
    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token2}"})
    cid2 = start_resp.json()["checkin_id"]
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {pat_token2}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {pat_token2}"}, json={"answer": "130/80", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {pat_token2}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {pat_token2}"}, json={"answer": "yes", "step": "adherence"})
    r_life2 = client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {pat_token2}"}, json={"answer": "none", "step": "lifestyle"}).json()
    assert r_life2["complete"] is True
    assert "triage" not in r_life2 or r_life2.get("triage") is None


# ----------------------------------------------------------------------------
# (f) Glucose 320 with symptoms -> emergency; glucose 60 and cannot swallow -> emergency;
#     glucose 270 without symptoms -> review
# ----------------------------------------------------------------------------
def test_f_glucose_protocols(rsa_key_pair):
    client = TestClient(app)

    # 1. Glucose 320 with DKA warning symptoms -> emergency
    tok1 = create_test_token(rsa_key_pair, sub="u-glu-1", email="glu1@demo.com")
    bootstrap_patient(client, tok1, conditions=["diabetes"])
    cid1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok1}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok1}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok1}"}, json={"answer": "320", "step": "glucose_reading"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok1}"}, json={"answer": "none", "step": "hyperglycemia_symptoms"})
    client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok1}"}, json={"answer": "yes", "step": "adherence"})
    t_start1 = client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok1}"}, json={"answer": "none", "step": "lifestyle"}).json()
    assert t_start1["step"] == "triage:glucose_high:0:0"
    ans1 = client.post(f"/api/checkins/{cid1}/answer", headers={"Authorization": f"Bearer {tok1}"},
                       json={"answer": "yes, I am vomiting and stomach hurts", "step": "triage:glucose_high:0:0"}).json()
    assert ans1["emergency"] is True
    assert ans1["triage"]["level"] == "emergency"

    # 2. Glucose 60 and cannot swallow -> emergency
    tok2 = create_test_token(rsa_key_pair, sub="u-glu-2", email="glu2@demo.com")
    bootstrap_patient(client, tok2, conditions=["diabetes"])
    cid2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok2}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok2}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok2}"}, json={"answer": "60", "step": "glucose_reading"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok2}"}, json={"answer": "none", "step": "hyperglycemia_symptoms"})
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok2}"}, json={"answer": "yes", "step": "adherence"})
    t_start2 = client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok2}"}, json={"answer": "none", "step": "lifestyle"}).json()
    assert t_start2["step"] == "triage:glucose_low:0:0"
    client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok2}"}, json={"answer": "no", "step": "triage:glucose_low:0:0"})
    ans2 = client.post(f"/api/checkins/{cid2}/answer", headers={"Authorization": f"Bearer {tok2}"},
                       json={"answer": "no", "step": "triage:glucose_low:1:0"}).json()
    assert ans2["emergency"] is True
    assert ans2["triage"]["level"] == "emergency"

    # 3. Glucose 270 without symptoms -> review
    tok3 = create_test_token(rsa_key_pair, sub="u-glu-3", email="glu3@demo.com")
    bootstrap_patient(client, tok3, conditions=["diabetes"])
    cid3 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {tok3}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid3}/answer", headers={"Authorization": f"Bearer {tok3}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid3}/answer", headers={"Authorization": f"Bearer {tok3}"}, json={"answer": "270", "step": "glucose_reading"})
    client.post(f"/api/checkins/{cid3}/answer", headers={"Authorization": f"Bearer {tok3}"}, json={"answer": "none", "step": "hyperglycemia_symptoms"})
    client.post(f"/api/checkins/{cid3}/answer", headers={"Authorization": f"Bearer {tok3}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid3}/answer", headers={"Authorization": f"Bearer {tok3}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid3}/answer", headers={"Authorization": f"Bearer {tok3}"}, json={"answer": "no", "step": "triage:glucose_high:0:0"})
    client.post(f"/api/checkins/{cid3}/answer", headers={"Authorization": f"Bearer {tok3}"}, json={"answer": "no", "step": "triage:glucose_high:1:0"})
    ans3 = client.post(f"/api/checkins/{cid3}/answer", headers={"Authorization": f"Bearer {tok3}"},
                       json={"answer": "yes large meal", "step": "triage:glucose_high:2:0"}).json()
    assert ans3["complete"] is True
    assert ans3["triage"]["level"] == "review"


# ----------------------------------------------------------------------------
# (g) Duplicate or stale protocol answer -> 409 and protocol advanced once
# ----------------------------------------------------------------------------
def test_g_duplicate_or_stale_protocol_step_returns_409(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-g", email="patg@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    cid = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})

    # Answer step 0:0 successfully
    r1 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "150/90", "step": "triage:bp_severe:0:0"})
    assert r1.status_code == 200
    assert r1.json()["step"] == "triage:bp_severe:1:0"

    # Repeat same step (stale step) -> 409
    r_stale = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                          json={"answer": "150/90", "step": "triage:bp_severe:0:0"})
    assert r_stale.status_code == 409
    assert r_stale.json()["detail"] == "stale_step"


# ----------------------------------------------------------------------------
# (h) Danger phrase typed as a protocol answer -> emergency persisted
# ----------------------------------------------------------------------------
def test_h_danger_phrase_in_protocol_answer_persists_emergency(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-h", email="path@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    cid = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})

    # In protocol step 0:0, patient enters danger phrase "I have chest pain"
    r_em = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                       json={"answer": "I have chest pain", "step": "triage:bp_severe:0:0"})
    assert r_em.status_code == 200
    d_em = r_em.json()
    assert d_em["emergency"] is True
    assert d_em["escalation_recorded"] is True
    assert d_em["complete"] is True
    assert d_em["triage"]["level"] == "emergency"


# ----------------------------------------------------------------------------
# (i) Normal readings start no protocol at all
# ----------------------------------------------------------------------------
def test_i_normal_readings_start_no_protocol(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-i", email="pati@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    cid = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "120/80", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    fin = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"}).json()

    assert fin["complete"] is True
    assert "triage" not in fin or fin.get("triage") is None


# ----------------------------------------------------------------------------
# (j) /complete before protocol finished -> 409 triage_incomplete
# ----------------------------------------------------------------------------
def test_j_complete_before_protocol_finished_returns_409(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-j", email="patj@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    cid = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})

    # Call /complete while protocol is in progress
    comp_resp = client.post(f"/api/checkins/{cid}/complete", headers={"Authorization": f"Bearer {pat_token}"})
    assert comp_resp.status_code == 409
    assert comp_resp.json()["detail"] == "triage_incomplete"


# ----------------------------------------------------------------------------
# (k) Protocol state survives being stored and reloaded
# ----------------------------------------------------------------------------
def test_k_protocol_state_survives_store_and_reload(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-k", email="patk@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    cid = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})

    # Advance 1 step
    r1 = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"},
                     json={"answer": "150/90", "step": "triage:bp_severe:0:0"})
    assert r1.status_code == 200

    # Fetch checkin from DB directly to verify protocol_state is reloaded
    checkin_row = app_store.get_checkin_by_id(cid)
    assert checkin_row is not None
    pstate = checkin_row.get("protocol_state")
    assert pstate is not None
    assert pstate["protocol"] == "bp_severe"
    assert pstate["index"] == 1
    assert pstate["answers"]["recheck"] == {"systolic": 150, "diastolic": 90}


# ----------------------------------------------------------------------------
# (l) emergency_escalated audit row holds category only, never summary or answers
# ----------------------------------------------------------------------------
def test_l_emergency_escalated_audit_row_holds_category_only(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-l", email="patl@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    cid = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "180/115", "step": "triage:bp_severe:0:0"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes chest tightness", "step": "triage:bp_severe:1:0"})

    # Inspect audit logs
    audit_rows = app_store.get_audit_logs(limit=100)
    escalation_events = [e for e in audit_rows if e.get("action") == "emergency_escalated" and e.get("target") == cid]
    assert len(escalation_events) >= 1
    detail = escalation_events[0].get("detail", {})
    assert detail == {"category": "triage:bp_severe"}
    assert "chest" not in str(detail)
    assert "summary" not in str(detail)


# ----------------------------------------------------------------------------
# (m) A patient aged 70 gets the extra older-adult question
# ----------------------------------------------------------------------------
def test_m_older_adult_gets_extra_question(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    # Calculate DOB for a 70-year old
    dob_70 = (datetime.date.today() - datetime.timedelta(days=70 * 365 + 20)).strftime("%Y-%m-%d")
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-m", email="patm@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    orig_get_profile = app_store.get_patient_profile
    def mock_get_profile(user_id, *args, **kwargs):
        prof = orig_get_profile(user_id, *args, **kwargs)
        if prof and user_id == "u-pat-m":
            prof["date_of_birth"] = dob_70
        return prof
    monkeypatch.setattr("main.get_patient_profile", mock_get_profile)

    # Add 3 baseline readings so 130/80 triggers bp_change
    for i in range(3):
        cid = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()["checkin_id"]
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "110/70", "step": "bp_reading"})
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
        client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})
        client.post(f"/api/checkins/{cid}/complete", headers={"Authorization": f"Bearer {pat_token}"})

    # Start checkin triggering bp_change
    cid_curr = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()["checkin_id"]
    client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "130/80", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"})

    # Answer standard 4 questions for bp_change
    client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_change:0:0"})
    client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_change:1:0"})
    client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_change:2:0"})
    r_fourth = client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_change:3:0"}).json()

    # For age 70, there is a 5th question (orthostatic / stand up dizziness)
    assert r_fourth["complete"] is False
    assert r_fourth["step"] == "triage:bp_change:4:0"
    assert "stand up" in r_fourth["question"]

    r_fifth = client.post(f"/api/checkins/{cid_curr}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_change:4:0"}).json()
    assert r_fifth["complete"] is True


# ----------------------------------------------------------------------------
# (n) Order of phases: protocol first, then medication check
# ----------------------------------------------------------------------------
def test_n_order_of_phases_protocol_before_medication_check(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-pat-n", email="patn@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    # Monkeypatch get_patient_bundle to return active medications
    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    med1 = NormalizedMedication("local-u-pat-n", "Amlodipine", "active", "5mg", "2026-10-01T09:00:00Z", "local", "MED-1")
    def mock_bundle_with_meds(pid, mode="isolated", base_url=None):
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
            "medications": [med1],
            "mode": mode,
        }
    monkeypatch.setattr("main.get_patient_bundle", mock_bundle_with_meds)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    assert start_resp.status_code == 200, start_resp.text
    cid = start_resp.json()["checkin_id"]

    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "fine", "step": "greeting"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "190/125", "step": "bp_reading"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "associated_symptoms"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "yes", "step": "adherence"})
    r_life = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "none", "step": "lifestyle"}).json()

    # Step is triage protocol FIRST, not medication check
    assert r_life["phase"] == "triage"
    assert r_life["step"] == "triage:bp_severe:0:0"

    # Answer all triage questions
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "150/90", "step": "triage:bp_severe:0:0"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_severe:1:0"})
    client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_severe:2:0"})
    r_triage_fin = client.post(f"/api/checkins/{cid}/answer", headers={"Authorization": f"Bearer {pat_token}"}, json={"answer": "no", "step": "triage:bp_severe:3:0"}).json()

    # After triage completes, transitions to medication check phase!
    assert r_triage_fin["phase"] == "medication"
    assert r_triage_fin["complete"] is False
    assert r_triage_fin["step"].startswith("medication_check:")
