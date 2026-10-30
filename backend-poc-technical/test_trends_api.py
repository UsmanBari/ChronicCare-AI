"""
Unit and integration tests for GET /api/me/trends and Provider Review Trends (Iteration 2 - Day 5).
Validates authentication, role enforcement, patient isolation, days parameter bounds,
emergency checkin exclusion, response schemas, and resilient failure handling in provider review detail.
"""
from __future__ import annotations

import datetime
import json
import time
from typing import Any, Dict, List, Optional
import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from auth import firebase_verify
from data_sources import app_store, local_store
from main import app
import agents.trend_agent as trend_agent_module

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
) -> None:
    """Helper to initialize session, consent, and profile for a patient."""
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
    client.post(
        "/api/me/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={"granted": True},
    )
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"conditions": list(conditions), "on_insulin_or_sulfonylurea": False},
    )


def bootstrap_provider(
    client: TestClient,
    token: str,
) -> None:
    """Helper to initialize session for a clinical provider."""
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {token}"})


def _insert_completed_checkin(
    user_id: str,
    checkin_id: str,
    completed_at: str,
    intakes: List[Dict[str, Any]],
    emergency: bool = False,
    requires_review: bool = False,
    db_path: Optional[str] = None,
):
    with app_store.get_db_cursor(backend="sqlite", db_path=db_path) as (cursor, be, ph):
        cursor.execute(
            f"""
            INSERT INTO checkins (checkin_id, user_id, mode, record_patient_id, status, started_at, completed_at, state_json)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (checkin_id, user_id, "isolated", f"local-{user_id}", "complete", completed_at, completed_at, "{}"),
        )
        cursor.execute(
            f"""
            INSERT INTO checkin_results (checkin_id, emergency, requires_review, review_status, intakes_json, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (checkin_id, 1 if emergency else 0, 1 if requires_review else 0, "open", json.dumps(intakes), completed_at),
        )


def _utc_ts(days_ago: int, hours_ago: int = 0) -> str:
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago, hours=hours_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# =============================================================================
# 1. Authentication & Role Enforcement (401, 403)
# =============================================================================
def test_trends_endpoint_unauthenticated_returns_401():
    client = TestClient(app)
    resp = client.get("/api/me/trends")
    assert resp.status_code == 401


def test_trends_endpoint_provider_role_returns_403(rsa_key_pair):
    client = TestClient(app)
    provider_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")
    bootstrap_provider(client, provider_token)

    resp = client.get("/api/me/trends", headers={"Authorization": f"Bearer {provider_token}"})
    assert resp.status_code == 403


# =============================================================================
# 2. Patient Isolation (Patient sees ONLY their own trends)
# =============================================================================
def test_patient_isolation_trends(rsa_key_pair, setup_test_environment):
    client = TestClient(app)
    pat1_token = create_test_token(rsa_key_pair, sub="pat-1", email="pat1@demo.com")
    pat2_token = create_test_token(rsa_key_pair, sub="pat-2", email="pat2@demo.com")
    bootstrap_patient(client, pat1_token)
    bootstrap_patient(client, pat2_token)

    # Insert 3 completed readings for patient 1 (over last 10 days)
    for i, val in enumerate([120.0, 124.0, 128.0], start=1):
        intakes = [{
            "condition": "diabetes",
            "readings": [{"observation_type": "glucose", "value": val, "glucose_context": "fasting"}]
        }]
        _insert_completed_checkin(
            user_id="pat-1",
            checkin_id=f"chk-pat1-{i}",
            completed_at=_utc_ts(days_ago=15 - i * 3),
            intakes=intakes,
            db_path=setup_test_environment,
        )

    # Patient 1 gets evaluated direction
    resp1 = client.get("/api/me/trends", headers={"Authorization": f"Bearer {pat1_token}"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["trends"]["glucose"]["n"] == 3
    assert data1["trends"]["glucose"]["direction"] != "not_enough_history"

    # Patient 2 has zero readings -> not_enough_history
    resp2 = client.get("/api/me/trends", headers={"Authorization": f"Bearer {pat2_token}"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["trends"]["glucose"]["n"] == 0
    assert data2["trends"]["glucose"]["direction"] == "not_enough_history"


# =============================================================================
# 3. Days Parameter Validation (7 <= days <= 90, else 422)
# =============================================================================
def test_trends_days_parameter_validation(rsa_key_pair):
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-val-1", email="patval@demo.com")
    bootstrap_patient(client, token)

    # Below 7 -> 422
    resp_low = client.get("/api/me/trends?days=6", headers={"Authorization": f"Bearer {token}"})
    assert resp_low.status_code == 422

    # Above 90 -> 422
    resp_high = client.get("/api/me/trends?days=91", headers={"Authorization": f"Bearer {token}"})
    assert resp_high.status_code == 422

    # Boundary 7 -> 200
    resp_7 = client.get("/api/me/trends?days=7", headers={"Authorization": f"Bearer {token}"})
    assert resp_7.status_code == 200
    assert resp_7.json()["window_days"] == 7

    # Boundary 90 -> 200
    resp_90 = client.get("/api/me/trends?days=90", headers={"Authorization": f"Bearer {token}"})
    assert resp_90.status_code == 200
    assert resp_90.json()["window_days"] == 90


# =============================================================================
# 4. No Readings Returns not_enough_history for All Monitored Types
# =============================================================================
def test_no_readings_returns_not_enough_history_for_all_types(rsa_key_pair):
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-empty", email="patempty@demo.com")
    bootstrap_patient(client, token)

    resp = client.get("/api/me/trends", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    for obs_type in ["blood_pressure_systolic", "blood_pressure_diastolic", "glucose"]:
        assert obs_type in data["trends"]
        assert data["trends"][obs_type]["direction"] == "not_enough_history"
        assert data["trends"][obs_type]["n"] == 0
        assert data["trends"][obs_type]["values"] == []


# =============================================================================
# 5. Mixed Types Properly Segregated and Evaluated
# =============================================================================
def test_mixed_types_properly_segregated_and_evaluated(rsa_key_pair, setup_test_environment):
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-mixed", email="patmixed@demo.com")
    bootstrap_patient(client, token)

    # 3 check-ins each with BP and Glucose
    for i in range(1, 4):
        intakes = [
            {
                "condition": "hypertension",
                "readings": [
                    {"observation_type": "blood_pressure_systolic", "value": 130.0 + i * 5},
                    {"observation_type": "blood_pressure_diastolic", "value": 80.0 + i * 2},
                ],
            },
            {
                "condition": "diabetes",
                "readings": [
                    {"observation_type": "glucose", "value": 110.0 + i * 10, "glucose_context": "fasting"},
                ],
            },
        ]
        _insert_completed_checkin(
            user_id="pat-mixed",
            checkin_id=f"chk-mix-{i}",
            completed_at=_utc_ts(days_ago=10 - i * 2),
            intakes=intakes,
            db_path=setup_test_environment,
        )

    resp = client.get("/api/me/trends", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()

    # Systolic: 135, 140, 145 -> n=3
    sys_trend = data["trends"]["blood_pressure_systolic"]
    assert sys_trend["n"] == 3
    assert len(sys_trend["values"]) == 3

    # Diastolic: 82, 84, 86 -> n=3
    dia_trend = data["trends"]["blood_pressure_diastolic"]
    assert dia_trend["n"] == 3
    assert len(dia_trend["values"]) == 3

    # Glucose: 120, 130, 140 -> n=3
    glu_trend = data["trends"]["glucose"]
    assert glu_trend["n"] == 3
    assert glu_trend["contexts_seen"] == ["fasting"]
    assert glu_trend["mixed_contexts"] is False


# =============================================================================
# 6. Emergency Check-ins Excluded from Trends
# =============================================================================
def test_emergency_checkins_excluded_from_trends(rsa_key_pair, setup_test_environment):
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-emerg", email="patemerg@demo.com")
    bootstrap_patient(client, token)

    # Insert 2 normal checkins with glucose 110, 115
    for i, val in enumerate([110.0, 115.0], start=1):
        _insert_completed_checkin(
            user_id="pat-emerg",
            checkin_id=f"chk-norm-{i}",
            completed_at=_utc_ts(days_ago=10 - i * 2),
            intakes=[{"readings": [{"observation_type": "glucose", "value": val}]}],
            emergency=False,
            db_path=setup_test_environment,
        )

    # Insert 1 EMERGENCY checkin with glucose 500
    _insert_completed_checkin(
        user_id="pat-emerg",
        checkin_id="chk-emerg-3",
        completed_at=_utc_ts(days_ago=2),
        intakes=[{"readings": [{"observation_type": "glucose", "value": 500.0}]}],
        emergency=True,
        db_path=setup_test_environment,
    )

    resp = client.get("/api/me/trends", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    glu_trend = data["trends"]["glucose"]

    # Only the 2 non-emergency readings should be present; n=2 means not_enough_history
    assert glu_trend["n"] == 2
    assert glu_trend["direction"] == "not_enough_history"
    assert all(item["value"] != 500.0 for item in glu_trend["values"])


# =============================================================================
# 7. Exact Response Shape Matching TREND_AGENT.md Schema
# =============================================================================
def test_trends_exact_response_shape(rsa_key_pair, setup_test_environment):
    client = TestClient(app)
    token = create_test_token(rsa_key_pair, sub="pat-shape", email="patshape@demo.com")
    bootstrap_patient(client, token)

    # Insert 4 completed readings
    for i, val in enumerate([120.0, 122.0, 125.0, 138.0], start=1):
        _insert_completed_checkin(
            user_id="pat-shape",
            checkin_id=f"chk-shape-{i}",
            completed_at=_utc_ts(days_ago=12 - i * 2),
            intakes=[{
                "readings": [
                    {"observation_type": "blood_pressure_systolic", "value": val},
                    {"observation_type": "blood_pressure_diastolic", "value": 80.0},
                ]
            }],
            db_path=setup_test_environment,
        )

    resp = client.get("/api/me/trends?days=30", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()

    # Top-level keys
    assert set(data.keys()) == {"generated_at", "advisory", "window_days", "excluded_count", "trends"}
    assert data["advisory"] is True
    assert data["window_days"] == 30
    assert isinstance(data["generated_at"], str)
    assert isinstance(data["excluded_count"], int)

    # Trend series keys
    sys_trend = data["trends"]["blood_pressure_systolic"]
    expected_series_keys = {
        "direction",
        "n",
        "window_days",
        "few_readings",
        "first_at",
        "last_at",
        "median_earlier",
        "median_recent",
        "change",
        "slope_per_week",
        "values",
        "contexts_seen",
        "mixed_contexts",
    }
    assert set(sys_trend.keys()).issubset(expected_series_keys)
    assert sys_trend["few_readings"] is True
    assert isinstance(sys_trend["values"], list)
    assert len(sys_trend["values"]) == 4
    for v in sys_trend["values"]:
        assert "value" in v and "at" in v


# =============================================================================
# 8. Provider Review Detail Contains Trends & Graceful Degradation on Failure
# =============================================================================
def test_provider_review_detail_contains_patient_trends_and_resilient_null(
    rsa_key_pair, monkeypatch, setup_test_environment
):
    client = TestClient(app)
    provider_token = create_test_token(rsa_key_pair, sub="prov-trends-1", email="provider@demo.com")
    bootstrap_provider(client, provider_token)

    # Create user and checkin for patient
    patient_id = "pat-review-trends"
    with app_store.get_db_cursor(backend="sqlite", db_path=setup_test_environment) as (cursor, be, ph):
        cursor.execute(
            f"INSERT OR IGNORE INTO users (user_id, email, display_name, role) VALUES ({ph}, {ph}, {ph}, {ph})",
            (patient_id, "patreview@demo.com", "Patient Review", "patient"),
        )

    # Insert 3 completed readings
    for i, val in enumerate([110.0, 115.0, 120.0], start=1):
        _insert_completed_checkin(
            user_id=patient_id,
            checkin_id=f"chk-prev-{i}",
            completed_at=_utc_ts(days_ago=15 - i * 3),
            intakes=[{"readings": [{"observation_type": "glucose", "value": val, "glucose_context": "fasting"}]}],
            db_path=setup_test_environment,
        )

    # Review check-in requiring review
    target_checkin_id = "chk-target-review"
    _insert_completed_checkin(
        user_id=patient_id,
        checkin_id=target_checkin_id,
        completed_at=_utc_ts(days_ago=1),
        intakes=[{"readings": [{"observation_type": "glucose", "value": 125.0, "glucose_context": "fasting"}]}],
        requires_review=True,
        db_path=setup_test_environment,
    )

    # 1. Normal call: trends present and populated
    resp = client.get(
        f"/api/provider/review/{target_checkin_id}",
        headers={"Authorization": f"Bearer {provider_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "trends" in data
    assert data["trends"] is not None
    assert data["trends"]["trends"]["glucose"]["n"] >= 3

    # 2. Monkeypatch exception in compute_trends -> trends becomes null, endpoint still succeeds (200)
    def broken_compute_trends(*args, **kwargs):
        raise RuntimeError("Simulated trend computation crash")

    import main
    monkeypatch.setattr(main, "compute_trends", broken_compute_trends)

    resp_broken = client.get(
        f"/api/provider/review/{target_checkin_id}",
        headers={"Authorization": f"Bearer {provider_token}"},
    )
    assert resp_broken.status_code == 200
    data_broken = resp_broken.json()
    assert data_broken["trends"] is None
    assert data_broken["checkin_id"] == target_checkin_id
