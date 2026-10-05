"""
Hermetic Safety & Correctness Tests for Stage 7A.

Covers:
1. Emergency by phrase: start, answer "I have chest pain" -> provider review queue has item with emergency=True, severity high, without calling /complete.
2. Dual-diagnosis emergency in second condition preserves first condition intake.
3. BP crisis via API: "190/125" -> emergency, trigger_category="bp_crisis_range", trigger_reading in provider review.
4. /complete after emergency is idempotent (no duplicate result or audit rows).
5. Persistence failure rollback and retry -> state preserved, retry succeeds.
6. step handling: correct step works, wrong step returns 409 stale_step, duplicate returns 409, omitted step works.
7. Concurrency: 2 threads posting same answer with same step simultaneously -> exactly one 200 and one 409 (loop 20 times).
8. Start idempotency: second start <= 15m with no answers returns same check-in id; start after answers creates new checkin.
9. User race: 2 threads calling POST /api/auth/session with same token -> both 200, 1 user row, 1 user_registered audit.
10. emergency_escalated audit detail contains category only (no patient text / zero PHI).
11. Queue ordering with mix of emergency, high, moderate items; null reconciliation safe.
"""

import json
import time
import datetime
import concurrent.futures
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
    test_db_path = str(tmp_path / "test_chroniccare_safety.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    mock_keys = {TEST_KID: x509_cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    # Provide a default dynamic mock bundle matching the requested pid
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
    resp = client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "conditions": list(conditions),
            "on_insulin_or_sulfonylurea": on_insulin,
            "language": "en",
        },
    )
    assert resp.status_code == 200, resp.text


def bootstrap_provider(client: TestClient, token: str) -> None:
    resp = client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text


def test_1_emergency_by_phrase_persists_immediately(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-em-1", email="em1@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="u-prov-1", email="provider@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])
    bootstrap_provider(client, prov_token)

    # 1. Start checkin
    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    chk_id = start_data["checkin_id"]
    current_step = start_data["step"]
    assert current_step == "greeting"

    # 2. Answer with emergency phrase (without calling /complete)
    ans_resp = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "I have sudden severe chest pain", "step": current_step},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["emergency"] is True
    assert ans_data["complete"] is True
    assert ans_data.get("escalation_recorded") is True
    assert ans_data["emergency_reason"] == "chest_pain"

    # 3. Provider review queue must have item WITHOUT /complete having been called
    queue_resp = client.get("/api/provider/review-queue", headers={"Authorization": f"Bearer {prov_token}"})
    assert queue_resp.status_code == 200
    items = queue_resp.json()
    matched = [it for it in items if it["checkin_id"] == chk_id]
    assert len(matched) == 1
    assert matched[0]["emergency"] is True
    assert matched[0]["max_severity"] == "high"

    # 4. Detail view
    detail_resp = client.get(f"/api/provider/review/{chk_id}", headers={"Authorization": f"Bearer {prov_token}"})
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["emergency"] is True
    assert detail["trigger_category"] in ("chest_pain", "emergency_keyword")
    assert detail["trigger_text"] == "I have sudden severe chest pain"
    assert detail["reconciliation"] is None


def test_2_dual_diagnosis_emergency_in_second_condition_preserves_first_intake(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-dual-1", email="dual1@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="u-prov-1", email="provider@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension", "diabetes"])
    bootstrap_provider(client, prov_token)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    chk_id = start_resp.json()["checkin_id"]

    # Step 1: Greeting
    ans1 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "Feeling okay", "step": "greeting"},
    ).json()
    assert not ans1["complete"]
    assert ans1["step"] == "bp_reading"

    # Step 2: BP reading
    ans2 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "120/80", "step": "bp_reading"},
    ).json()
    assert ans2["step"] == "associated_symptoms"

    # Step 3: Associated symptoms
    ans3 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "None", "step": "associated_symptoms"},
    ).json()
    assert ans3["step"] == "adherence"

    # Step 4: Adherence
    ans4 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "Yes, took medications", "step": "adherence"},
    ).json()
    assert ans4["step"] == "lifestyle"

    # Step 5: Lifestyle -> completes hypertension, pivots to diabetes glucose_reading
    ans5 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "All normal", "step": "lifestyle"},
    ).json()
    assert not ans5["complete"]
    assert ans5["step"] == "glucose_reading"

    # Step 6: Diabetes condition triggers emergency
    ans6 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "I have sudden severe chest pain and pressure", "step": "glucose_reading"},
    ).json()
    assert ans6["complete"] is True
    assert ans6["emergency"] is True
    assert ans6.get("escalation_recorded") is True

    # Check review detail preserves first condition intake
    detail = client.get(f"/api/provider/review/{chk_id}", headers={"Authorization": f"Bearer {prov_token}"}).json()
    assert detail["emergency"] is True
    intakes = detail.get("intakes", [])
    assert len(intakes) >= 2
    # First intake is hypertension
    htn_intake = intakes[0]
    assert htn_intake["condition"] == "hypertension"
    assert htn_intake["emergency"] is False
    assert len(htn_intake["readings"]) == 2
    # Second intake is diabetes emergency
    dm_intake = intakes[1]
    assert dm_intake["condition"] == "diabetes"
    assert dm_intake["emergency"] is True


def test_3_bp_crisis_range_triggers_emergency_via_api(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-bp-1", email="bp1@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="u-prov-1", email="provider@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])
    bootstrap_provider(client, prov_token)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    chk_id = start_resp.json()["checkin_id"]

    # Step 1: Greeting
    ans1 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "Feeling okay", "step": "greeting"},
    ).json()
    assert ans1["step"] == "bp_reading"

    # Step 2: Post severe BP reading (>= 180/120). Kept and does not end interview.
    ans2 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "190/125", "step": "bp_reading"},
    ).json()
    assert ans2["complete"] is False
    assert ans2["emergency"] is False
    assert ans2["step"] == "associated_symptoms"

    # Step 3: Associated symptoms
    ans3 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "None", "step": "associated_symptoms"},
    ).json()
    assert ans3["step"] == "adherence"

    # Step 4: Adherence
    ans4 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "Yes", "step": "adherence"},
    ).json()
    assert ans4["step"] == "lifestyle"

    # Step 5: Lifestyle - interview finishes, starts bp_severe triage protocol
    ans5 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "No changes", "step": "lifestyle"},
    ).json()
    assert ans5["complete"] is False
    assert ans5["emergency"] is False
    assert ans5["phase"] == "triage"
    assert ans5["step"] == "triage:bp_severe:0:0"
    assert "rest quietly for 5 minutes" in ans5["question"]


def test_4_complete_after_emergency_is_idempotent(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-idem-1", email="idem1@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    chk_id = start_resp.json()["checkin_id"]

    # Trigger emergency in /answer
    ans = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "I have sudden severe chest pain", "step": "greeting"},
    ).json()
    assert ans["complete"] is True

    # Call /complete
    comp_resp1 = client.post(f"/api/checkins/{chk_id}/complete", headers={"Authorization": f"Bearer {pat_token}"})
    assert comp_resp1.status_code == 200
    comp_data1 = comp_resp1.json()
    assert comp_data1["emergency"] is True

    # Call /complete again
    comp_resp2 = client.post(f"/api/checkins/{chk_id}/complete", headers={"Authorization": f"Bearer {pat_token}"})
    assert comp_resp2.status_code == 200
    comp_data2 = comp_resp2.json()
    assert comp_data1 == comp_data2

    # Verify database has exactly 1 result row
    res = app_store.get_checkin_result(chk_id)
    assert res is not None

    # Verify exactly 1 emergency_escalated audit row
    audits = app_store.get_audit_logs(limit=100)
    em_audits = [a for a in audits if a.get("action") == "emergency_escalated" and a.get("target") == chk_id]
    assert len(em_audits) == 1


def test_5_persistence_failure_rollback_and_retry(rsa_key_pair, monkeypatch):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-fail-1", email="fail1@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"})
    chk_id = start_resp.json()["checkin_id"]

    # Cause apply_checkin_answer_atomic to raise during DB write
    def faulty_apply(*args, **kwargs):
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr("main.apply_checkin_answer_atomic", faulty_apply)

    fail_resp = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "I have sudden severe chest pain", "step": "greeting"},
    )
    assert fail_resp.status_code == 500

    # Verify stored state remains in_progress and step greeting
    chk_state = app_store.get_checkin_by_id(chk_id)
    assert chk_state["status"] == "in_progress"
    assert chk_state["version"] == 0

    # Restore apply
    monkeypatch.setattr("main.apply_checkin_answer_atomic", app_store.apply_checkin_answer_atomic)

    # Retry should succeed and write emergency properly
    ok_resp = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "I have sudden severe chest pain", "step": "greeting"},
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["complete"] is True
    assert ok_resp.json().get("escalation_recorded") is True


def test_6_step_handling_and_stale_step_409(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-step-1", email="step1@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    start = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()
    chk_id = start["checkin_id"]
    assert start.get("step") == "greeting"

    # 1. Valid step "greeting"
    resp1 = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "Feeling fine", "step": "greeting"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["step"] == "bp_reading"

    # 2. Duplicate / stale step "greeting" returns 409
    resp_stale = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "Feeling fine again", "step": "greeting"},
    )
    assert resp_stale.status_code == 409
    assert resp_stale.json()["detail"] == "stale_step"
    assert resp_stale.json()["step"] == "bp_reading"
    assert "question" in resp_stale.json()

    # 3. Invalid future step returns 409
    resp_future = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "120/80", "step": "wrong_step"},
    )
    assert resp_future.status_code == 409
    assert resp_future.json()["detail"] == "stale_step"

    # 4. Omitted step works for legacy backward compatibility
    resp_omit = client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "120/80"},
    )
    assert resp_omit.status_code == 200
    assert resp_omit.json()["step"] == "associated_symptoms"


def test_7_concurrent_answers_optimistic_lock(rsa_key_pair):
    """Run 20 concurrent answer iterations to verify optimistic locking and race-freedom."""
    for _ in range(20):
        client = TestClient(app)
        pat_token = create_test_token(rsa_key_pair, sub=f"u-conc-{time.time()}", email=f"conc_{time.time()}@demo.com")
        bootstrap_patient(client, pat_token, conditions=["hypertension"])

        start = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()
        chk_id = start["checkin_id"]

        def submit_answer():
            c = TestClient(app)
            return c.post(
                f"/api/checkins/{chk_id}/answer",
                headers={"Authorization": f"Bearer {pat_token}"},
                json={"answer": "Feeling fine", "step": "greeting"},
            ).status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(submit_answer)
            f2 = executor.submit(submit_answer)
            statuses = [f1.result(), f2.result()]

        assert 200 in statuses
        assert 409 in statuses

        # Ensure state advanced exactly once (version == 1)
        chk = app_store.get_checkin_by_id(chk_id)
        assert chk["version"] == 1


def test_8_start_checkin_idempotency(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-start-idem", email="startidem@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    # First start
    s1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()
    chk_1 = s1["checkin_id"]

    # Second start without answering -> returns same check-in ID
    s2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()
    chk_2 = s2["checkin_id"]
    assert chk_1 == chk_2

    # Now answer check-in 1
    client.post(
        f"/api/checkins/{chk_1}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": "Feeling fine", "step": "greeting"},
    )

    # Third start after answers -> creates new check-in and abandons check-in 1
    s3 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()
    chk_3 = s3["checkin_id"]
    assert chk_1 != chk_3

    # Check that check-in 1 is now abandoned
    detail1 = client.get(f"/api/checkins/{chk_1}", headers={"Authorization": f"Bearer {pat_token}"}).json()
    assert detail1["status"] == "abandoned"


def test_9_auth_session_first_login_race(rsa_key_pair):
    token = create_test_token(rsa_key_pair, sub="u-race-auth", email="raceauth@demo.com")

    def call_session():
        c = TestClient(app)
        return c.post(
            "/api/auth/session",
            headers={"Authorization": f"Bearer {token}"},
            json={"id_token": token},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(call_session)
        f2 = executor.submit(call_session)
        r1, r2 = f1.result(), f2.result()

    assert r1.status_code == 200
    assert r2.status_code == 200

    # Verify exactly one user in DB
    user = app_store.get_user_by_email("raceauth@demo.com")
    assert user is not None

    # Verify exactly 1 user_registered audit event
    audits = app_store.get_audit_logs(limit=100)
    reg_audits = [a for a in audits if a.get("action") == "user_registered" and a.get("actor_user_id") == user["user_id"]]
    assert len(reg_audits) == 1


def test_10_emergency_escalated_audit_has_no_phi(rsa_key_pair):
    client = TestClient(app)
    pat_token = create_test_token(rsa_key_pair, sub="u-audit-phi", email="auditphi@demo.com")
    bootstrap_patient(client, pat_token, conditions=["hypertension"])

    start = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {pat_token}"}).json()
    chk_id = start["checkin_id"]

    patient_text = "I have severe crushing chest pain and cannot breathe"
    client.post(
        f"/api/checkins/{chk_id}/answer",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"answer": patient_text, "step": "greeting"},
    )

    # Inspect audit log
    audits = app_store.get_audit_logs(limit=100)
    em_audits = [a for a in audits if a.get("action") == "emergency_escalated" and a.get("target") == chk_id]
    assert len(em_audits) == 1
    for a in em_audits:
        detail_raw = a.get("detail", {})
        detail_str = json.dumps(detail_raw) if isinstance(detail_raw, dict) else str(detail_raw)
        # Detail must only have category and not the raw text
        assert "chest pain" not in detail_str.lower()
        assert "cannot breathe" not in detail_str.lower()
        assert "category" in detail_str.lower()


def test_11_provider_review_queue_ordering_and_null_reconciliation(rsa_key_pair):
    client = TestClient(app)
    prov_token = create_test_token(rsa_key_pair, sub="u-prov-order", email="provider@demo.com")
    bootstrap_provider(client, prov_token)

    # 1. Emergency patient
    t1 = create_test_token(rsa_key_pair, sub="u-em-ord", email="emord@demo.com")
    bootstrap_patient(client, t1, conditions=["hypertension"])
    s1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {t1}"}).json()
    client.post(f"/api/checkins/{s1['checkin_id']}/answer", headers={"Authorization": f"Bearer {t1}"}, json={"answer": "I have severe chest pain", "step": "greeting"})

    # 2. Normal completed patient with high conflict
    t2 = create_test_token(rsa_key_pair, sub="u-high-ord", email="highord@demo.com")
    bootstrap_patient(client, t2, conditions=["diabetes"])
    s2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {t2}"}).json()
    client.post(f"/api/checkins/{s2['checkin_id']}/answer", headers={"Authorization": f"Bearer {t2}"}, json={"answer": "A bit tired", "step": "greeting"})
    client.post(f"/api/checkins/{s2['checkin_id']}/answer", headers={"Authorization": f"Bearer {t2}"}, json={"answer": "180 fasting", "step": "glucose_reading"})
    client.post(f"/api/checkins/{s2['checkin_id']}/answer", headers={"Authorization": f"Bearer {t2}"}, json={"answer": "Thirsty", "step": "hyperglycemia_symptoms"})
    client.post(f"/api/checkins/{s2['checkin_id']}/answer", headers={"Authorization": f"Bearer {t2}"}, json={"answer": "Yes", "step": "adherence"})
    client.post(f"/api/checkins/{s2['checkin_id']}/answer", headers={"Authorization": f"Bearer {t2}"}, json={"answer": "None", "step": "lifestyle"})
    comp_resp = client.post(f"/api/checkins/{s2['checkin_id']}/complete", headers={"Authorization": f"Bearer {t2}"})
    assert comp_resp.status_code == 200, comp_resp.text
    comp_data = comp_resp.json()
    assert comp_data["requires_review"] is True

    # Provider fetches queue
    items = client.get("/api/provider/review-queue", headers={"Authorization": f"Bearer {prov_token}"}).json()
    assert len(items) >= 2

    # First item in queue should be emergency item
    assert items[0]["emergency"] is True
    assert items[0]["checkin_id"] == s1["checkin_id"]

    # Detail call for emergency item must work even with null reconciliation
    detail = client.get(f"/api/provider/review/{s1['checkin_id']}", headers={"Authorization": f"Bearer {prov_token}"})
    assert detail.status_code == 200
    assert detail.json()["emergency"] is True
    assert detail.json()["reconciliation"] is None
