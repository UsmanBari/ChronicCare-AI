"""
Hermetic Integration Tests for Check-in Medication Confirmation Phase (P1).

Covers:
(a) a patient with two active medications in the record: after the interview the next questions are
    the two medication questions in record order with the right `step` strings, then `complete: true`.
(b) answering "no" for one produces a HIGH-severity medication conflict in /complete and an open review item.
(c) all "yes" -> auto-resolved against a FHIR-sourced record.
(d) no active medications -> no medication phase at all.
(e) a duplicate medication answer with the same `step` -> 409 and the check advanced once.
(f) "I have chest pain" typed as a medication answer -> emergency persisted with `escalation_recorded` true
    and the provider queue shows it WITHOUT calling /complete.
(g) two unclear answers -> the medication is "not reported today" and not in the bundle.
(h) /complete before the medication check is finished -> 409.
(i) a historical (stopped) medication in the record raises no review item.
(j) the medication state survives being stored and reloaded.
(k) a changed dose gives a moderate item.
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
from data_sources.models import NormalizedObservation, NormalizedMedication, NormalizedPatient


TEST_PROJECT_ID = "test-chroniccare-ai"
TEST_KID = "test-key-id-meds-1"


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
    test_db_path = str(tmp_path / "test_chroniccare_meds.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield test_db_path


def create_test_token(
    private_key,
    sub: str = "uid-patient-1",
    email: str = "patient1@demo.com",
    name: str = "Patient One",
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


def _setup_patient(client, rsa_key_pair, user_id="patient-med-1", email="patient_med@demo.com", conditions=None):
    token = create_test_token(rsa_key_pair, sub=user_id, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True})
    client.put("/api/me/profile", headers=headers, json={
        "conditions": conditions or ["diabetes"],
        "on_insulin_or_sulfonylurea": False,
        "language": "en",
    })
    return headers


def _mock_bundle(monkeypatch, medications=None, observations=None, patient_name="Patient One"):
    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    def mock_get_patient_bundle(patient_id: str, mode: str, base_url: Optional[str] = None, db_path: Optional[str] = None):
        return {
            "patient": NormalizedPatient(patient_id=patient_id, name=patient_name),
            "observations": observations or [
                NormalizedObservation(
                    patient_id=patient_id,
                    observation_type="glucose",
                    value=120.0,
                    unit="mg/dL",
                    timestamp=now_ts,
                    source="local" if mode == "isolated" else "fhir",
                    source_record_id="OBS-BASE-1",
                )
            ],
            "medications": medications or [],
            "mode": mode,
        }
    monkeypatch.setattr("main.get_patient_bundle", mock_get_patient_bundle)


def _answer_interview_to_med_phase(client, chk_id, headers):
    """Answers diabetes interview questions until medication confirmation phase begins."""
    steps_and_answers = [
        ("greeting", "I feel fine"),
        ("glucose_reading", "120 mg/dL"),
        ("hyperglycemia_symptoms", "No symptoms"),
        ("adherence", "Yes, taking everything"),
        ("lifestyle", "Eating well, no changes"),
    ]
    last_data = None
    for step, ans in steps_and_answers:
        r = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": ans, "step": step})
        assert r.status_code == 200, f"Failed at step {step}: {r.text}"
        last_data = r.json()
    return last_data


def test_a_patient_with_two_active_medications(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-two-meds", "p_two_meds@demo.com", ["diabetes"])

    med1 = NormalizedMedication("local-p-two-meds", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    med2 = NormalizedMedication("local-p-two-meds", "Lisinopril 10mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "local", "MED-2")
    _mock_bundle(monkeypatch, medications=[med1, med2])

    resp = client.post("/api/checkins/start", headers=headers)
    assert resp.status_code == 200, resp.text
    chk_id = resp.json()["checkin_id"]

    # Complete interview part
    med_intro = _answer_interview_to_med_phase(client, chk_id, headers)
    assert med_intro["complete"] is False
    assert med_intro["step"] == "medication_check:0:0"
    assert "Metformin 500mg" in med_intro["question"]

    # Medication 1 question answer: yes
    ans3 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    assert ans3.status_code == 200
    data3 = ans3.json()
    assert data3["complete"] is False
    assert data3["step"] == "medication_check:1:0"
    assert "Lisinopril 10mg" in data3["question"]

    # Medication 2 question answer: yes
    ans4 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:1:0"})
    assert ans4.status_code == 200
    data4 = ans4.json()
    assert data4["complete"] is True
    assert data4["question"] is None


def test_b_stopped_medication_produces_high_severity_conflict(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-stopped-med", "p_stopped@demo.com", ["diabetes"])

    med1 = NormalizedMedication("local-p-stopped-med", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    med2 = NormalizedMedication("local-p-stopped-med", "Lisinopril 10mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "local", "MED-2")
    _mock_bundle(monkeypatch, medications=[med1, med2])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "no, stopped last week", "step": "medication_check:1:0"})

    comp_resp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp_resp.status_code == 200
    data = comp_resp.json()
    assert data["requires_review"] is True
    assert data["max_severity"] == "high"

    recon = data["reconciliation"]
    med_comps = recon["medication_comparisons"]
    lisinopril_comp = [c for c in med_comps if "Lisinopril" in c["medication_name"]][0]
    assert lisinopril_comp["comparison_status"] == "conflict"


def test_c_all_yes_auto_resolved_against_fhir_record(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-fhir-yes", "p_fhir_yes@demo.com", ["diabetes"])

    # Setup active EHR connection to mock connected mode
    user_id = "p-fhir-yes"
    app_store.record_ehr_connection(
        connection_id="conn-1",
        user_id=user_id,
        ehr_system_id="smart-sandbox",
        external_patient_id="EXT-1",
        status="active",
    )

    med1 = NormalizedMedication("EXT-1", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "fhir", "MED-1")
    _mock_bundle(monkeypatch, medications=[med1])

    resp = client.post("/api/checkins/start", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["mode"] == "connected"
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})

    comp_resp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp_resp.status_code == 200
    data = comp_resp.json()
    assert data["requires_review"] is False
    assert data["max_severity"] == "none"


def test_d_no_active_medications_no_medication_phase(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-no-meds", "p_no_meds@demo.com", ["diabetes"])

    _mock_bundle(monkeypatch, medications=[])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    ans = _answer_interview_to_med_phase(client, chk_id, headers)
    assert ans["complete"] is True
    assert ans["step"] == "interview_complete"


def test_e_duplicate_medication_answer_returns_409(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-dup-step", "p_dup@demo.com", ["diabetes"])

    med1 = NormalizedMedication("local-p-dup-step", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    med2 = NormalizedMedication("local-p-dup-step", "Lisinopril 10mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "local", "MED-2")
    _mock_bundle(monkeypatch, medications=[med1, med2])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)

    # Answer medication step 0:0
    ans1 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    assert ans1.status_code == 200
    assert ans1.json()["step"] == "medication_check:1:0"
    assert ans1.json()["complete"] is False

    # Repeat answer with stale step 0:0 while session is in_progress
    ans2 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    assert ans2.status_code == 409
    assert ans2.json()["detail"] == "stale_step"
    assert ans2.json()["step"] == "medication_check:1:0"


def test_f_chest_pain_during_medication_check_persists_emergency(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-chest-pain", "p_pain@demo.com", ["diabetes"])

    med1 = NormalizedMedication("local-p-chest-pain", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    _mock_bundle(monkeypatch, medications=[med1])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)

    # Emergency phrased during medication check
    emg_resp = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "I have severe chest pain", "step": "medication_check:0:0"})
    assert emg_resp.status_code == 200
    data = emg_resp.json()
    assert data["emergency"] is True
    assert data["escalation_recorded"] is True
    assert data["complete"] is True

    # Provider review queue shows it without calling /complete
    prov_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")
    prov_headers = {"Authorization": f"Bearer {prov_token}"}
    client.post("/api/auth/session", headers=prov_headers)
    q_resp = client.get("/api/provider/review-queue", headers=prov_headers)
    assert q_resp.status_code == 200
    items = q_resp.json()
    matching = [i for i in items if i["checkin_id"] == chk_id]
    assert len(matching) == 1
    assert matching[0]["emergency"] is True


def test_g_two_unclear_answers_medication_is_unknown(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-unclear", "p_unclear@demo.com", ["diabetes"])

    med1 = NormalizedMedication("local-p-unclear", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    _mock_bundle(monkeypatch, medications=[med1])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)

    # First unclear answer
    u1 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "maybe", "step": "medication_check:0:0"})
    assert u1.status_code == 200
    assert u1.json()["step"] == "medication_check:0:1"
    assert u1.json()["complete"] is False

    # Second unclear answer
    u2 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "maybe", "step": "medication_check:0:1"})
    assert u2.status_code == 200
    assert u2.json()["complete"] is True

    # Complete checkin -> Metformin not in checkin bundle (missing_in_b)
    comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp.status_code == 200
    recon = comp.json()["reconciliation"]
    assert recon["summary"]["missing_in_b"] == 1


def test_h_complete_before_medication_check_finished_returns_409(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-early-comp", "p_early@demo.com", ["diabetes"])

    med1 = NormalizedMedication("local-p-early-comp", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    _mock_bundle(monkeypatch, medications=[med1])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)

    # Now in medication check phase, attempt to complete early
    comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp.status_code == 409
    assert comp.json()["detail"] == "medication_check_incomplete"


def test_i_historical_stopped_medication_raises_no_review_item(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-hist-med", "p_hist@demo.com", ["diabetes"])

    # Active EHR connection for connected mode
    app_store.record_ehr_connection(
        connection_id="conn-hist",
        user_id="p-hist-med",
        ehr_system_id="smart-sandbox",
        external_patient_id="EXT-HIST",
        status="active",
    )

    med_active = NormalizedMedication("EXT-HIST", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "fhir", "MED-1")
    med_stopped = NormalizedMedication("EXT-HIST", "Glibenclamide 5mg", "stopped", "5mg", "2025-01-01T09:00:00Z", "fhir", "MED-2")
    _mock_bundle(monkeypatch, medications=[med_active, med_stopped])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)
    ans = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    assert ans.json()["complete"] is True  # Only 1 question asked!

    comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp.status_code == 200
    data = comp.json()
    assert data["requires_review"] is False
    assert data["reconciliation"]["summary"]["missing_in_b"] == 0


def test_j_medication_state_survives_store_and_reload(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-reload", "p_reload@demo.com", ["diabetes"])

    med1 = NormalizedMedication("local-p-reload", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    med2 = NormalizedMedication("local-p-reload", "Lisinopril 10mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "local", "MED-2")
    _mock_bundle(monkeypatch, medications=[med1, med2])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)

    # Answer 1st med question
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})

    # Fetch from store directly
    chk = app_store.get_checkin_by_id(chk_id)
    assert chk is not None
    assert chk["med_state"]["index"] == 1
    assert chk["med_state"]["results"][0]["name"] == "Metformin 500mg"
    assert chk["med_state"]["results"][0]["status"] == "active"


def test_k_changed_dose_gives_moderate_review_item(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-dose-change", "p_dose@demo.com", ["diabetes"])

    app_store.record_ehr_connection(
        connection_id="conn-dose",
        user_id="p-dose-change",
        ehr_system_id="smart-sandbox",
        external_patient_id="EXT-DOSE",
        status="active",
    )

    med1 = NormalizedMedication("EXT-DOSE", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "fhir", "MED-1")
    _mock_bundle(monkeypatch, medications=[med1])

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes but only half a tablet", "step": "medication_check:0:0"})

    comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp.status_code == 200
    data = comp.json()
    assert data["requires_review"] is True
    assert data["max_severity"] == "moderate"


def test_l_isolated_mode_self_reported_medication_requires_review(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-isolated-med", "p_iso@demo.com", ["diabetes"])

    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    local_store.add_local_medication(
        id="MED-ISO-1",
        patient_id="local-p-isolated-med",
        medication_name="Metformin 500mg",
        status="active",
        dosage="1 tablet twice daily",
        timestamp=now_ts,
        source="local",
        origin="self_reported",
    )

    resp = client.post("/api/checkins/start", headers=headers)
    chk_id = resp.json()["checkin_id"]

    _answer_interview_to_med_phase(client, chk_id, headers)
    ans = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    assert ans.json()["complete"] is True

    comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp.status_code == 200
    data = comp.json()
    # In isolated mode where prior and check-in are self-reported, verification requires review even on agreement
    assert data["reconciliation"]["summary"]["agreements"] == 1
    med_verifs = data["verification"]["medication_verifications"]
    metformin_verif = [v for v in med_verifs if v["medication_name"] == "Metformin 500mg"][0]
    assert metformin_verif["trust_level_a"] == "low"
    assert metformin_verif["trust_level_b"] == "low"
    assert metformin_verif["requires_human_review"] is True


def _answer_v3_dual_to_med_phase(client, chk_id, headers):
    """Walks v3 dual interview until medication check phase begins."""
    curr_res = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "I feel fine", "step": "greeting"})
    assert curr_res.status_code == 200, curr_res.text
    curr = curr_res.json()
    for _ in range(25):
        step = curr.get("step")
        if step == "summary_confirmation":
            conf_res = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "Confirm and submit", "step": step})
            assert conf_res.status_code == 200, conf_res.text
            return conf_res.json()
        elif step == "glucose_reading":
            ans = "115"
        elif step == "bp_reading":
            ans = "120/80"
        elif step == "glucose_context":
            ans = "fasting"
        elif step == "bp_technique":
            ans = "seated"
        elif any(k in (step or "") for k in ["symptom", "headache", "vision", "chest", "hypo", "foot"]):
            ans = "no"
        elif "adherence" in (step or ""):
            ans = "yes"
        else:
            ans = "no"
        curr_res = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": ans, "step": step})
        assert curr_res.status_code == 200, curr_res.text
        curr = curr_res.json()
    raise RuntimeError("Did not reach summary confirmation within 25 turns")


def test_v3_dual_patient_three_meds_flow_isolated(rsa_key_pair, monkeypatch):
    """P0-1 API Test: v3 dual patient with 3 meds: yes / changed dose / stopped -> completes with reconciliation & triage."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    monkeypatch.setenv("ORCHESTRATOR", "direct")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-v3-dual-3m", "p_v3_dual_3m@demo.com", ["diabetes", "hypertension"])

    med1 = NormalizedMedication("local-p-v3-dual-3m", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    med2 = NormalizedMedication("local-p-v3-dual-3m", "Lisinopril 10mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "local", "MED-2")
    med3 = NormalizedMedication("local-p-v3-dual-3m", "Amlodipine 5mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "local", "MED-3")
    _mock_bundle(monkeypatch, medications=[med1, med2, med3])

    resp = client.post("/api/checkins/start", headers=headers)
    assert resp.status_code == 200, resp.text
    chk_id = resp.json()["checkin_id"]

    # 1. Walk interview to medication phase
    med_intro = _answer_v3_dual_to_med_phase(client, chk_id, headers)
    assert med_intro["complete"] is False
    assert med_intro["step"] == "medication_check:0:0"
    assert med_intro["phase"] == "medication"
    assert med_intro["why_text"] is not None
    assert med_intro["options"] is not None
    assert "Metformin" in med_intro["question"]

    # Early complete returns 409
    early_comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert early_comp.status_code == 409
    assert early_comp.json()["detail"] == "medication_check_incomplete"

    # 2. Med 1 answer: yes
    ans1 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    assert ans1.status_code == 200, ans1.text
    d1 = ans1.json()
    assert d1["complete"] is False
    assert d1["step"] == "medication_check:1:0"
    assert "Lisinopril" in d1["question"]

    # 3. Med 2 answer: changed dose
    ans2 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "now I take 1 mg once daily", "step": "medication_check:1:0"})
    assert ans2.status_code == 200, ans2.text
    d2 = ans2.json()
    assert d2["complete"] is False
    assert d2["step"] == "medication_check:2:0"
    assert "Amlodipine" in d2["question"]

    # 4. Med 3 answer: stopped
    ans3 = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "No, I stopped it", "step": "medication_check:2:0"})
    assert ans3.status_code == 200, ans3.text
    d3 = ans3.json()
    assert d3["complete"] is True
    assert d3["question"] is None

    # 5. Complete check-in
    comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp.status_code == 200, comp.text
    data = comp.json()
    assert data["triage_level"] is not None
    assert data["requires_review"] is True

    recon = data["reconciliation"]
    med_comps = recon["medication_comparisons"]
    met_comp = [c for c in med_comps if "Metformin" in c["medication_name"]][0]
    assert met_comp["comparison_status"] in ("agree", "agreement")

    lis_comp = [c for c in med_comps if "Lisinopril" in c["medication_name"]][0]
    assert lis_comp["comparison_status"] == "conflict"
    assert lis_comp["dosage_a"] != lis_comp["dosage_b"]

    amlo_comp = [c for c in med_comps if "Amlodipine" in c["medication_name"]][0]
    assert amlo_comp["comparison_status"] == "conflict"
    assert amlo_comp["status_b"] == "stopped"


def test_v3_dual_patient_connected_fhir(rsa_key_pair, monkeypatch):
    """P0-1 API Test: Connected mode with FHIR meds on v3 dual patient."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    monkeypatch.setenv("ORCHESTRATOR", "direct")
    client = TestClient(app)
    user_id = "p-v3-fhir-dual"
    headers = _setup_patient(client, rsa_key_pair, user_id, "p_v3_fhir_dual@demo.com", ["diabetes", "hypertension"])

    app_store.record_ehr_connection(
        connection_id="conn-v3-fhir",
        user_id=user_id,
        ehr_system_id="smart-sandbox",
        external_patient_id="EXT-V3-1",
        status="active",
    )

    med1 = NormalizedMedication("EXT-V3-1", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "fhir", "FHIR-M1")
    med2 = NormalizedMedication("EXT-V3-1", "Lisinopril 10mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "fhir", "FHIR-M2")
    med3 = NormalizedMedication("EXT-V3-1", "Amlodipine 5mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "fhir", "FHIR-M3")
    _mock_bundle(monkeypatch, medications=[med1, med2, med3])

    resp = client.post("/api/checkins/start", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["mode"] == "connected"
    chk_id = resp.json()["checkin_id"]

    med_intro = _answer_v3_dual_to_med_phase(client, chk_id, headers)
    assert med_intro["step"] == "medication_check:0:0"

    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "now I take 1 mg once daily", "step": "medication_check:1:0"})
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "No, I stopped it", "step": "medication_check:2:0"})

    comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp.status_code == 200, comp.text
    data = comp.json()
    assert data["triage_level"] is not None
    assert data["requires_review"] is True


def test_v3_dual_patient_graph_orchestrator(rsa_key_pair, monkeypatch):
    """P0-1 API Test: Same flow on ORCHESTRATOR=graph."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    monkeypatch.setenv("ORCHESTRATOR", "graph")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-v3-graph", "p_v3_graph@demo.com", ["diabetes", "hypertension"])

    med1 = NormalizedMedication("local-p-v3-graph", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    med2 = NormalizedMedication("local-p-v3-graph", "Lisinopril 10mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "local", "MED-2")
    med3 = NormalizedMedication("local-p-v3-graph", "Amlodipine 5mg", "active", "1 tablet daily", "2026-10-01T09:00:00Z", "local", "MED-3")
    _mock_bundle(monkeypatch, medications=[med1, med2, med3])

    resp = client.post("/api/checkins/start", headers=headers)
    assert resp.status_code == 200
    chk_id = resp.json()["checkin_id"]

    med_intro = _answer_v3_dual_to_med_phase(client, chk_id, headers)
    assert med_intro["step"] == "medication_check:0:0"

    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "now I take 1 mg once daily", "step": "medication_check:1:0"})
    client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "No, I stopped it", "step": "medication_check:2:0"})

    comp = client.post(f"/api/checkins/{chk_id}/complete", headers=headers)
    assert comp.status_code == 200, comp.text
    data = comp.json()
    assert data["triage_level"] is not None
    assert data["requires_review"] is True


def test_v3_medication_check_in_med_phase(rsa_key_pair, monkeypatch):
    """Mutant killer test: v3 sessions enter medication phase once complete and can answer med check."""
    monkeypatch.setenv("INTERVIEW_ENGINE", "v3")
    client = TestClient(app)
    headers = _setup_patient(client, rsa_key_pair, "p-v3-mutant-check", "p_v3_mutant@demo.com", ["diabetes", "hypertension"])

    med1 = NormalizedMedication("local-p-v3-mutant-check", "Metformin 500mg", "active", "1 tablet twice daily", "2026-10-01T09:00:00Z", "local", "MED-1")
    _mock_bundle(monkeypatch, medications=[med1])

    resp = client.post("/api/checkins/start", headers=headers)
    assert resp.status_code == 200
    chk_id = resp.json()["checkin_id"]

    med_intro = _answer_v3_dual_to_med_phase(client, chk_id, headers)
    assert med_intro["step"] == "medication_check:0:0"

    # Answering the medication question MUST be processed in medication phase (returns 200, not 409 stale_step)
    ans = client.post(f"/api/checkins/{chk_id}/answer", headers=headers, json={"answer": "yes", "step": "medication_check:0:0"})
    assert ans.status_code == 200, f"Expected 200 but got {ans.status_code}: {ans.text}"
    assert ans.json()["complete"] is True
    assert ans.json()["phase"] == "medication"

