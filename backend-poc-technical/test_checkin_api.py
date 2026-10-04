"""
Hermetic Unit & Integration Tests for Authenticated Check-in Pipeline, Persistence, and Provider Review Queue.

Covers:
1. Full normal flow (start -> answer questions -> complete -> reconcile & verify).
2. Demo conflict: patient reports 180 mg/dL, record says 140 mg/dL -> conflict, severity high, requires_review true.
3. Emergency flow: reporting red flag -> status emergency, urgent open review item, bypasses reconciliation.
4. Cold start: prior record empty -> intake confidence Medium.
5. Missing reading: missing data checkpoint -> intake confidence Low, baseline kept without review.
6. Ownership check: User B cannot access or answer User A's check-in (404).
7. Consent check: start check-in with revoked/missing consent returns 403.
8. Idempotency: repeated POST /api/checkins/{id}/complete returns identical stored result.
9. Unreachable record source: returns 502 with no details, retry works when source recovers.
10. Provider review queue ordering (emergency first, high severity, oldest first) and action lifecycle (acknowledge, resolve, escalate).
11. Role matrix: patient cannot call provider review endpoints (403); provider cannot start check-ins (403).
12. Payload protection: extra fields rejected with 422 (extra="forbid"), no body field can set patient_id or mode.
13. Isolated mode baseline trust: second check-in sees first check-in's readings with origin self_reported and trust level LOW.
14. State privacy: client never sees record_patient_id of another user.
15. Abandonment: starting a new check-in marks older in-progress check-ins as abandoned.
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
TEST_KID = "test-key-id-1"


@pytest.fixture(scope="session")
def rsa_key_pair():
    """Generates an RSA private/public key pair for test token signing."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="session")
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
    test_db_path = str(tmp_path / "test_chroniccare.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")

    # Run migrations on clean DB
    app_store.migrate(db_path=test_db_path, backend="sqlite")
    local_store.init_db(db_path=test_db_path)

    # Mock public certs
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
    kid: str = TEST_KID,
    exp_delta: int = 3600,
) -> str:
    """Helper to generate signed JWT tokens for tests."""
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
    """Helper to initialize session, consent and profile for a patient."""
    # 0. Initialize session and user record
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    # 1. Grant consent
    resp = client.post(
        "/api/me/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={"granted": True},
    )
    assert resp.status_code == 200, resp.text

    # 2. Set profile
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


# =============================================================================
# TEST CASES
# =============================================================================

def test_full_normal_flow(rsa_key_pair, monkeypatch):
    """Test standard normal check-in flow from start to completion."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-normal-1", email="pat1@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])

    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Mock baseline data source
    mock_bundle = {
        "patient": NormalizedPatient(patient_id="local-pat-normal-1", name="Patient One", date_of_birth="1980-01-01"),
        "observations": [
            NormalizedObservation(
                patient_id="local-pat-normal-1",
                observation_type="glucose",
                value=120.0,
                unit="mg/dL",
                timestamp=now_ts,
                source="local",
                source_record_id="obs-bs-1",
            )
        ],
        "medications": [],
    }
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)

    # 1. Start check-in
    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200, start_resp.text
    start_data = start_resp.json()
    checkin_id = start_data["checkin_id"]
    assert start_data["mode"] == "isolated"
    assert start_data["is_cold_start"] is False
    assert "feeling today" in start_data["question"].lower()

    # 2. Answer questions
    answers = [
        "I feel good today",
        "120 mg/dL",
        "No new symptoms",
        "Yes, took my metformin as prescribed",
        "No changes",
    ]
    for ans in answers:
        ans_resp = client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": ans},
        )
        assert ans_resp.status_code == 200, ans_resp.text

    # 3. Complete check-in
    comp_resp = client.post(
        f"/api/checkins/{checkin_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comp_resp.status_code == 200, comp_resp.text
    comp_data = comp_resp.json()
    assert comp_data["emergency"] is False
    assert comp_data["requires_review"] is False
    assert comp_data["max_severity"] == "none"
    assert len(comp_data["intakes"]) > 0
    assert comp_data["reconciliation"] is not None
    assert comp_data["verification"] is not None


def test_demo_conflict_high_severity_requires_review(rsa_key_pair, monkeypatch):
    """Test demo conflict: patient reports 180, record says 140 -> conflict, high severity, requires review."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-conflict-1", email="patconflict@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])

    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_bundle = {
        "patient": NormalizedPatient(patient_id="local-pat-conflict-1", name="Patient Conflict", date_of_birth="1980-01-01"),
        "observations": [
            NormalizedObservation(
                patient_id="local-pat-conflict-1",
                observation_type="glucose",
                value=140.0,
                unit="mg/dL",
                timestamp=now_ts,
                source="local",
                source_record_id="obs-bs-140",
            )
        ],
        "medications": [],
    }
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    checkin_id = start_resp.json()["checkin_id"]

    answers = [
        "A bit tired",
        "180 fasting",  # 180 vs 140 (delta 40 > 30 mg/dL -> conflict, high severity)
        "Thirsty",
        "Yes",
        "None",
    ]
    for ans in answers:
        client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": ans},
        )

    comp_resp = client.post(
        f"/api/checkins/{checkin_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comp_resp.status_code == 200, comp_resp.text
    data = comp_resp.json()
    assert data["emergency"] is False
    assert data["requires_review"] is True
    assert data["max_severity"] == "high"


def test_emergency_flow_bypasses_reconciliation(rsa_key_pair, monkeypatch):
    """Test emergency answer halts interview, creates urgent open review item, and bypasses reconciliation."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-emergency-1", email="patemergency@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes", "hypertension"])

    mock_bundle = {
        "patient": NormalizedPatient(patient_id="local-pat-emergency-1", name="Emergency Patient", date_of_birth="1980-01-01"),
        "observations": [],
        "medications": [],
    }
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    checkin_id = start_resp.json()["checkin_id"]

    # Patient triggers red flag
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer": "I have sudden severe chest pain"},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["emergency"] is True
    assert ans_data["complete"] is True
    assert ans_data["emergency_reason"] == "chest_pain"

    # Complete emergency checkin
    comp_resp = client.post(
        f"/api/checkins/{checkin_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["emergency"] is True
    assert comp_data["requires_review"] is True
    assert comp_data["max_severity"] == "high"
    assert comp_data["reconciliation"] is None
    assert comp_data["verification"] is None


def test_cold_start_intake_medium_confidence(rsa_key_pair, monkeypatch):
    """Test cold start (no prior observations or meds) sets confidence to Medium."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-cold-1", email="patcold@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])

    mock_bundle = {
        "patient": NormalizedPatient(patient_id="local-pat-cold-1", name="Cold Patient", date_of_birth="1980-01-01"),
        "observations": [],
        "medications": [],
    }
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["is_cold_start"] is True
    checkin_id = start_data["checkin_id"]

    answers = ["Okay", "110", "None", "Yes", "None"]
    for ans in answers:
        client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": ans},
        )

    comp_resp = client.post(
        f"/api/checkins/{checkin_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comp_resp.status_code == 200
    intakes = comp_resp.json()["intakes"]
    assert len(intakes) > 0
    # Cold start baseline intake should be Medium confidence
    assert intakes[0]["confidence"] == "Medium"


def test_missing_reading_low_confidence_trusted_baseline(rsa_key_pair, monkeypatch):
    """Test missing reading sets intake confidence to Low and preserves trusted baseline."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-missing-1", email="patmissing@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])

    now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Seed trusted baseline in local store with origin clinician_entered (high trust)
    local_store.add_local_observation(
        id="obs-bs-baseline",
        patient_id="local-pat-missing-1",
        observation_type="glucose",
        value=115.0,
        unit="mg/dL",
        timestamp=now_ts,
        source="local",
        origin="clinician_entered",
    )

    mock_bundle = {
        "patient": NormalizedPatient(patient_id="local-pat-missing-1", name="Missing Patient", date_of_birth="1980-01-01"),
        "observations": [
            NormalizedObservation(
                patient_id="local-pat-missing-1",
                observation_type="glucose",
                value=115.0,
                unit="mg/dL",
                timestamp=now_ts,
                source="local",
                source_record_id="obs-bs-baseline",
            )
        ],
        "medications": [],
    }
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert start_resp.status_code == 200
    checkin_id = start_resp.json()["checkin_id"]

    # Answers: greeting -> reading missing -> checkpoint confirmation -> symptoms -> adherence -> lifestyle
    answers = ["Good", "I didn't take my reading today", "No meter", "None", "Yes", "None"]
    for ans in answers:
        client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": ans},
        )

    comp_resp = client.post(
        f"/api/checkins/{checkin_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comp_resp.status_code == 200, comp_resp.text
    data = comp_resp.json()
    assert data["intakes"][0]["confidence"] == "Low"
    # Verification with trusted baseline missing does not trigger human review (auto-resolved)
    assert data["requires_review"] is False


def test_ownership_isolation_user_b_cannot_access_user_a(rsa_key_pair, monkeypatch):
    """Test user isolation: User B gets 404 when attempting to view or answer User A's checkin."""
    client = TestClient(app)
    token_a = create_test_token(rsa_key_pair, sub="user-a", email="usera@demo.com")
    token_b = create_test_token(rsa_key_pair, sub="user-b", email="userb@demo.com")

    bootstrap_patient(client, token_a, conditions=["diabetes"])
    bootstrap_patient(client, token_b, conditions=["hypertension"])

    mock_bundle = {
        "patient": NormalizedPatient(patient_id="local-user-a", name="User A", date_of_birth="1980-01-01"),
        "observations": [],
        "medications": [],
    }
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)

    # User A starts check-in
    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token_a}"})
    assert start_resp.status_code == 200
    checkin_id = start_resp.json()["checkin_id"]

    # User B attempts to answer User A's check-in -> 404
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"answer": "Hacking answer"},
    )
    assert ans_resp.status_code == 404
    assert ans_resp.json()["detail"] == "Check-in session not found"

    # User B attempts to view User A's check-in -> 404
    get_resp = client.get(
        f"/api/checkins/{checkin_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_resp.status_code == 404

    # User B attempts to complete User A's check-in -> 404
    comp_resp = client.post(
        f"/api/checkins/{checkin_id}/complete",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert comp_resp.status_code == 404


def test_consent_enforcement_on_start(rsa_key_pair):
    """Test check-in start is forbidden (403) without active consent."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="user-noconsent", email="noconsent@demo.com")

    # Initialize user session
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})

    # Set profile without consent
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False, "language": "en"},
    )

    resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert "consent is required" in resp.json()["detail"].lower()

    # Grant then revoke consent
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {token}"}, json={"granted": True})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {token}"}, json={"granted": False})

    resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_complete_is_idempotent(rsa_key_pair, monkeypatch):
    """Test repeated calls to POST /api/checkins/{id}/complete return the same stored result."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-idem-1", email="patidem@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])

    mock_bundle = {
        "patient": NormalizedPatient(patient_id="local-pat-idem-1", name="Patient Idem", date_of_birth="1980-01-01"),
        "observations": [],
        "medications": [],
    }
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    checkin_id = start_resp.json()["checkin_id"]

    for ans in ["Good", "115", "None", "Yes", "None"]:
        client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": ans},
        )

    # First complete
    resp1 = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert resp1.status_code == 200, resp1.text

    # Second complete returns identical body
    resp2 = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()


def test_unreachable_record_source_502_and_retry(rsa_key_pair, monkeypatch):
    """Test upstream failure returns 502 with no details, leaving check-in completable on retry."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-retry-1", email="patretry@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])

    mock_bundle = {
        "patient": NormalizedPatient(patient_id="local-pat-retry-1", name="Patient Retry", date_of_birth="1980-01-01"),
        "observations": [],
        "medications": [],
    }
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"})
    checkin_id = start_resp.json()["checkin_id"]

    for ans in ["Good", "115", "None", "Yes", "None"]:
        client.post(
            f"/api/checkins/{checkin_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": ans},
        )

    # Simulate upstream network failure
    def failing_get_bundle(pid, mode=None, base_url=None):
        raise ConnectionError("Upstream FHIR server unreachable")

    monkeypatch.setattr("main.get_patient_bundle", failing_get_bundle)

    fail_resp = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert fail_resp.status_code == 502
    assert fail_resp.json()["detail"] == "Record source unavailable"

    # Restore data source and retry
    monkeypatch.setattr("main.get_patient_bundle", lambda pid, mode=None, base_url=None: mock_bundle)
    success_resp = client.post(f"/api/checkins/{checkin_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert success_resp.status_code == 200, success_resp.text
    assert success_resp.json()["emergency"] is False


def test_provider_review_queue_ordering_and_actions(rsa_key_pair, monkeypatch):
    """Test provider review queue ordering (emergency first, severity, oldest) and action lifecycle."""
    client = TestClient(app)
    provider_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")

    # Initialize provider session
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {provider_token}"})

    # Seed checkin results directly via app_store with varying severities and timestamps
    app_store.create_user("user-p1", "p1@demo.com", role="patient", display_name="Patient Normal")
    app_store.create_user("user-p2", "p2@demo.com", role="patient", display_name="Patient High")
    app_store.create_user("user-p3", "p3@demo.com", role="patient", display_name="Patient Emergency")

    # Item 1: Normal / low severity (oldest)
    app_store.create_checkin("chk-1", "user-p1", "isolated", "local-user-p1", {}, "complete", started_at="2026-10-01T10:00:00Z")
    app_store.create_checkin_result("chk-1", emergency=False, intakes=[], reconciliation={}, verification={}, requires_review=True, max_severity="low", review_status="open", created_at="2026-10-01T10:05:00Z")

    # Item 2: High severity (middle)
    app_store.create_checkin("chk-2", "user-p2", "isolated", "local-user-p2", {}, "complete", started_at="2026-10-01T11:00:00Z")
    app_store.create_checkin_result("chk-2", emergency=False, intakes=[], reconciliation={}, verification={}, requires_review=True, max_severity="high", review_status="open", created_at="2026-10-01T11:05:00Z")

    # Item 3: Emergency (newest)
    app_store.create_checkin("chk-3", "user-p3", "isolated", "local-user-p3", {}, "emergency", started_at="2026-10-01T12:00:00Z")
    app_store.create_checkin_result("chk-3", emergency=True, intakes=[], reconciliation=None, verification=None, requires_review=True, max_severity="high", review_status="open", created_at="2026-10-01T12:05:00Z")

    # 1. Fetch review queue
    queue_resp = client.get("/api/provider/review-queue?status=open", headers={"Authorization": f"Bearer {provider_token}"})
    assert queue_resp.status_code == 200, queue_resp.text
    queue = queue_resp.json()
    assert len(queue) == 3

    # Ordering check: Emergency (chk-3) -> High severity (chk-2) -> Low severity (chk-1)
    assert queue[0]["checkin_id"] == "chk-3"
    assert queue[0]["emergency"] is True
    assert queue[1]["checkin_id"] == "chk-2"
    assert queue[1]["max_severity"] == "high"
    assert queue[2]["checkin_id"] == "chk-1"

    # 2. View detail
    detail_resp = client.get("/api/provider/review/chk-2", headers={"Authorization": f"Bearer {provider_token}"})
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["checkin_id"] == "chk-2"
    assert detail["review_status"] == "open"
    assert len(detail["actions"]) == 0

    # 3. Provider Acknowledge Action
    ack_resp = client.post(
        "/api/provider/review/chk-2/action",
        headers={"Authorization": f"Bearer {provider_token}"},
        json={"action": "acknowledge", "note": "Reviewing with attending physician"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["review_status"] == "acknowledged"
    assert len(ack_resp.json()["actions"]) == 1
    assert ack_resp.json()["actions"][0]["action"] == "acknowledge"

    # 4. Provider Resolve Action
    res_resp = client.post(
        "/api/provider/review/chk-2/action",
        headers={"Authorization": f"Bearer {provider_token}"},
        json={"action": "resolve", "note": "Adjusted medication dosage in EHR"},
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["review_status"] == "resolved"
    assert len(res_resp.json()["actions"]) == 2

    # 5. Check queue filtering for resolved
    resolved_queue = client.get("/api/provider/review-queue?status=resolved", headers={"Authorization": f"Bearer {provider_token}"}).json()
    assert any(item["checkin_id"] == "chk-2" for item in resolved_queue)


def test_role_matrix_enforcement(rsa_key_pair):
    """Test RBAC role matrix: patient cannot access provider endpoints, provider cannot start check-in."""
    client = TestClient(app)
    patient_token = create_test_token(rsa_key_pair, sub="patient-rbac", email="patient@demo.com")
    provider_token = create_test_token(rsa_key_pair, sub="provider-rbac", email="provider@demo.com")

    # Initialize sessions
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {patient_token}"})
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {provider_token}"})

    # Patient calls provider endpoints -> 403
    resp = client.get("/api/provider/review-queue", headers={"Authorization": f"Bearer {patient_token}"})
    assert resp.status_code == 403

    resp = client.get("/api/provider/review/dummy-id", headers={"Authorization": f"Bearer {patient_token}"})
    assert resp.status_code == 403

    resp = client.post("/api/provider/review/dummy-id/action", headers={"Authorization": f"Bearer {patient_token}"}, json={"action": "resolve"})
    assert resp.status_code == 403

    # Provider calls patient check-in start -> 403
    resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {provider_token}"})
    assert resp.status_code == 403


def test_payload_protection_extra_fields_forbidden(rsa_key_pair):
    """Test request payloads forbid extra fields to prevent patient_id or mode spoofing (422)."""
    client = TestClient(app)
    patient_token = create_test_token(rsa_key_pair, sub="pat-extra-1", email="patextra@demo.com")
    provider_token = create_test_token(rsa_key_pair, sub="prov-extra-1", email="provider@demo.com")

    bootstrap_patient(client, patient_token, conditions=["diabetes"])
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {provider_token}"})

    start_resp = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {patient_token}"})
    checkin_id = start_resp.json()["checkin_id"]

    # Extra field in answer request -> 422
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers={"Authorization": f"Bearer {patient_token}"},
        json={"answer": "Good", "patient_id": "spoofed-id", "mode": "connected"},
    )
    assert ans_resp.status_code == 422

    # Extra field in provider action request -> 422
    act_resp = client.post(
        f"/api/provider/review/{checkin_id}/action",
        headers={"Authorization": f"Bearer {provider_token}"},
        json={"action": "resolve", "status": "spoofed_status"},
    )
    assert act_resp.status_code == 422


def test_isolated_mode_second_checkin_sees_baseline_low_trust(rsa_key_pair):
    """Test that in isolated mode, check-in 1 writes self_reported observations, and check-in 2 verifies them with LOW trust."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-iso-trust", email="patisotrust@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])

    # 1. First Check-in (Cold Start)
    start_1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"}).json()
    chk_1_id = start_1["checkin_id"]

    for ans in ["Feeling okay", "130 fasting", "None", "Yes", "None"]:
        client.post(
            f"/api/checkins/{chk_1_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": ans},
        )

    comp_1 = client.post(f"/api/checkins/{chk_1_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp_1.status_code == 200

    # Verify that local store now has the observation with origin='self_reported'
    record_pid = "local-pat-iso-trust"
    origins = local_store.get_local_observation_origins(record_pid)
    assert len(origins) > 0
    for obs_id, origin in origins.items():
        assert origin == "self_reported"

    # 2. Second Check-in: report conflicting blood sugar (160 vs 130)
    start_2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"}).json()
    chk_2_id = start_2["checkin_id"]
    assert start_2["is_cold_start"] is False

    for ans in ["Feeling okay", "160 fasting", "None", "Yes", "None"]:
        client.post(
            f"/api/checkins/{chk_2_id}/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"answer": ans},
        )

    comp_2 = client.post(f"/api/checkins/{chk_2_id}/complete", headers={"Authorization": f"Bearer {token}"})
    assert comp_2.status_code == 200
    comp_2_data = comp_2.json()

    # The verification result should evaluate trust level low for baseline and incoming observation
    verif = comp_2_data["verification"]
    assert verif is not None
    obs_list = verif.get("observation_verifications", [])
    assert len(obs_list) > 0
    assert any(obs.get("trust_level_a") == "low" and obs.get("trust_level_b") == "low" for obs in obs_list)


def test_state_privacy_no_other_patient_data_exposed(rsa_key_pair):
    """Test that patient check-in listing returns only the authenticated patient's records."""
    client = TestClient(app)
    token_1 = create_test_token(rsa_key_pair, sub="user-priv-1", email="priv1@demo.com")
    token_2 = create_test_token(rsa_key_pair, sub="user-priv-2", email="priv2@demo.com")

    bootstrap_patient(client, token_1, conditions=["diabetes"])
    bootstrap_patient(client, token_2, conditions=["hypertension"])

    # Patient 1 creates check-in
    start_1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token_1}"}).json()

    # Patient 2 creates check-in
    start_2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token_2}"}).json()

    # Patient 1 queries list
    list_1 = client.get("/api/checkins", headers={"Authorization": f"Bearer {token_1}"}).json()
    assert len(list_1) == 1
    assert list_1[0]["checkin_id"] == start_1["checkin_id"]
    assert list_1[0]["record_patient_id"] == "local-user-priv-1"
    assert "user-priv-2" not in str(list_1)


def test_starting_new_checkin_abandons_older_in_progress(rsa_key_pair):
    """Test that starting a new check-in automatically marks previous in_progress check-in as abandoned."""
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="user-abandon", email="abandon@demo.com")
    bootstrap_patient(client, token, conditions=["diabetes"])

    # Start check-in 1
    start_1 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"}).json()
    chk_1_id = start_1["checkin_id"]

    # Start check-in 2 without completing check-in 1
    start_2 = client.post("/api/checkins/start", headers={"Authorization": f"Bearer {token}"}).json()
    chk_2_id = start_2["checkin_id"]
    assert chk_1_id != chk_2_id

    # Check-in 1 should now be abandoned
    chk_1_detail = client.get(f"/api/checkins/{chk_1_id}", headers={"Authorization": f"Bearer {token}"}).json()
    assert chk_1_detail["status"] == "abandoned"

    # Answering check-in 1 returns 409 Conflict
    ans_resp = client.post(
        f"/api/checkins/{chk_1_id}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer": "Too late"},
    )
    assert ans_resp.status_code == 409
