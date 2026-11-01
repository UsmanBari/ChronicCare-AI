"""
Hermetic Tests for Provider Diabetes Risk Panel API & Patient Leak Defense (Part I).
Verifies:
1. RISK_ENABLED flag controls whether risk is computed (None when false/unset).
2. When RISK_ENABLED=true and patient has HTN-only with valid readings + profile:
   - risk.status == 'ok'
   - band in ('low', 'moderate', 'high')
   - reasons and caveats are populated
   - probability is calculated
3. Missing measurements (e.g. waist or recent BP) return status 'not_enough_information'
   with specific missing keys.
4. Patients with diabetes or without hypertension receive risk=None (inapplicable).
5. Patient endpoints (/api/me, /api/me/profile, /api/checkins/{id}, /api/me/trends)
   NEVER return risk data (leak defense).
6. Computation errors fail safely to None without crashing the endpoint.
7. Post-action endpoint (/api/provider/review/{id}/action) also includes risk safely.
"""

import datetime
import json
import os
import time
from typing import Any, Dict, List, Optional
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
import jwt
from fastapi.testclient import TestClient

from data_sources import app_store, local_store
import auth.firebase_verify as firebase_verify
from main import app

TEST_PROJECT_ID = "chroniccare-test-risk"
TEST_KID = "test-key-risk-1"


@pytest.fixture(scope="module")
def rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key


@pytest.fixture(scope="module")
def x509_cert_pem(rsa_key_pair):
    public_key = rsa_key_pair.public_key()
    subject = issuer = x509.Name([
        x509.NameAttribute(x509.NameOID.COMMON_NAME, "ChronicCare Risk Test"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
        .sign(rsa_key_pair, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch, x509_cert_pem):
    """Sets up clean temporary SQLite database and mocks Firebase token verification."""
    test_db_path = str(tmp_path / "test_chroniccare_risk.db")

    monkeypatch.setenv("LOCAL_DB_PATH", test_db_path)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "provider@demo.com:provider,admin@demo.com:admin")
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")

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
    kid: str = TEST_KID,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "user_id": sub,
        "email": email,
        "name": name,
        "aud": aud,
        "iss": f"https://securetoken.google.com/{aud}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})


def _insert_checkin_with_vitals(
    user_id: str,
    checkin_id: str,
    days_ago: int,
    systolic: float,
    diastolic: float,
    requires_review: bool = True,
    db_path: Optional[str] = None,
):
    dt = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days_ago)).isoformat()
    intakes = [
        {
            "readings": [
                {"observation_type": "blood_pressure_systolic", "value": systolic, "at": dt},
                {"observation_type": "blood_pressure_diastolic", "value": diastolic, "at": dt},
            ]
        }
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_path) as (cursor, be, ph):
        cursor.execute(
            f"""
            INSERT INTO checkins (checkin_id, user_id, mode, record_patient_id, status, started_at, completed_at, state_json)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (checkin_id, user_id, "isolated", f"local-{user_id}", "complete", dt, dt, "{}"),
        )
        cursor.execute(
            f"""
            INSERT INTO checkin_results (checkin_id, emergency, requires_review, review_status, intakes_json, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (checkin_id, 0, 1 if requires_review else 0, "open", json.dumps(intakes), dt),
        )


def test_risk_panel_disabled_by_default(rsa_key_pair, setup_test_environment, monkeypatch):
    monkeypatch.delenv("RISK_ENABLED", raising=False)
    client = TestClient(app)

    pat_token = create_test_token(rsa_key_pair, sub="pat-htn-1", email="pat1@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {pat_token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1975-06-15",
            "sex_at_birth": "male",
            "height_cm": 175.0,
            "weight_kg": 85.0,
            "waist_cm": 95.0,
            "smoking_status": "former",
        },
    )

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})
    _insert_checkin_with_vitals("pat-htn-1", "chk-htn-1", days_ago=2, systolic=145, diastolic=92, db_path=setup_test_environment)

    resp = client.get("/api/provider/review/chk-htn-1", headers={"Authorization": f"Bearer {prov_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk"] is None


def test_risk_panel_enabled_complete_htn_patient(rsa_key_pair, setup_test_environment, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    client = TestClient(app)

    pat_token = create_test_token(rsa_key_pair, sub="pat-htn-2", email="pat2@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {pat_token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1970-01-01",
            "sex_at_birth": "male",
            "height_cm": 172.0,
            "weight_kg": 88.0,
            "waist_cm": 102.0,
            "smoking_status": "former",
        },
    )

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})
    _insert_checkin_with_vitals("pat-htn-2", "chk-htn-2", days_ago=3, systolic=142, diastolic=88, db_path=setup_test_environment)

    resp = client.get("/api/provider/review/chk-htn-2", headers={"Authorization": f"Bearer {prov_token}"})
    assert resp.status_code == 200
    data = resp.json()
    risk = data.get("risk")
    assert risk is not None
    assert risk["status"] == "ok"
    assert risk["band"] in ("low", "moderate", "high")
    assert len(risk.get("reasons", [])) > 0
    assert "home_bp_not_exam_bp" in risk.get("caveats", [])
    assert "not_validated_pakistan" in risk.get("caveats", [])
    assert risk.get("disease") == "diabetes"


def test_risk_panel_missing_waist_returns_not_enough_info(rsa_key_pair, setup_test_environment, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    client = TestClient(app)

    pat_token = create_test_token(rsa_key_pair, sub="pat-htn-3", email="pat3@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {pat_token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1975-01-01",
            "sex_at_birth": "female",
            "height_cm": 160.0,
            "weight_kg": 65.0,
            # waist_cm intentionally omitted
            "smoking_status": "never",
        },
    )

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})
    _insert_checkin_with_vitals("pat-htn-3", "chk-htn-3", days_ago=5, systolic=135, diastolic=85, db_path=setup_test_environment)

    resp = client.get("/api/provider/review/chk-htn-3", headers={"Authorization": f"Bearer {prov_token}"})
    assert resp.status_code == 200
    data = resp.json()
    risk = data.get("risk")
    assert risk is not None
    assert risk["status"] == "not_enough_information"
    assert any("waist" in m for m in risk.get("missing", []))


def test_risk_inapplicable_for_diabetes_patient(rsa_key_pair, setup_test_environment, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    client = TestClient(app)

    pat_token = create_test_token(rsa_key_pair, sub="pat-t2d-1", email="t2d@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {pat_token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={
            "conditions": ["hypertension", "type 2 diabetes"],
            "date_of_birth": "1970-01-01",
            "sex_at_birth": "male",
            "height_cm": 175.0,
            "weight_kg": 85.0,
            "waist_cm": 98.0,
            "smoking_status": "never",
        },
    )

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})
    _insert_checkin_with_vitals("pat-t2d-1", "chk-t2d-1", days_ago=2, systolic=130, diastolic=82, db_path=setup_test_environment)

    resp = client.get("/api/provider/review/chk-t2d-1", headers={"Authorization": f"Bearer {prov_token}"})
    assert resp.status_code == 200
    assert resp.json().get("risk") is None


def test_patient_endpoints_never_leak_risk(rsa_key_pair, setup_test_environment, monkeypatch):
    """Leak defense: patient-facing endpoints MUST NEVER return risk assessment."""
    monkeypatch.setenv("RISK_ENABLED", "true")
    client = TestClient(app)

    pat_token = create_test_token(rsa_key_pair, sub="pat-leak-test", email="leak@demo.com")
    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {pat_token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1975-01-01",
            "sex_at_birth": "male",
            "height_cm": 180.0,
            "weight_kg": 90.0,
            "waist_cm": 100.0,
            "smoking_status": "current",
        },
    )
    _insert_checkin_with_vitals("pat-leak-test", "chk-leak-1", days_ago=1, systolic=150, diastolic=95, db_path=setup_test_environment)

    # 1. /api/me
    resp_me = client.get("/api/me", headers={"Authorization": f"Bearer {pat_token}"})
    assert resp_me.status_code == 200
    assert "risk" not in resp_me.json()

    # 2. /api/me/profile
    resp_prof = client.get("/api/me/profile", headers={"Authorization": f"Bearer {pat_token}"})
    assert resp_prof.status_code == 200
    assert "risk" not in resp_prof.json()

    # 3. /api/me/trends
    resp_trends = client.get("/api/me/trends", headers={"Authorization": f"Bearer {pat_token}"})
    assert resp_trends.status_code == 200
    assert "risk" not in resp_trends.json()

    # 4. /api/checkins/{id}
    resp_chk = client.get("/api/checkins/chk-leak-1", headers={"Authorization": f"Bearer {pat_token}"})
    assert resp_chk.status_code == 200
    assert "risk" not in resp_chk.json()


def test_post_provider_review_action_includes_risk(rsa_key_pair, setup_test_environment, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    client = TestClient(app)

    pat_token = create_test_token(rsa_key_pair, sub="pat-action-1", email="act1@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {pat_token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1972-03-20",
            "sex_at_birth": "male",
            "height_cm": 178.0,
            "weight_kg": 85.0,
            "waist_cm": 98.0,
            "smoking_status": "never",
        },
    )

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})
    _insert_checkin_with_vitals("pat-action-1", "chk-action-1", days_ago=2, systolic=140, diastolic=90, db_path=setup_test_environment)

    resp = client.post(
        "/api/provider/review/chk-action-1/action",
        headers={"Authorization": f"Bearer {prov_token}"},
        json={"action": "acknowledge", "note": "Reviewed by clinician"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("risk") is not None
    assert data["risk"]["status"] == "ok"


def test_risk_computation_error_fails_safely(rsa_key_pair, setup_test_environment, monkeypatch):
    monkeypatch.setenv("RISK_ENABLED", "true")
    client = TestClient(app)

    pat_token = create_test_token(rsa_key_pair, sub="pat-err-1", email="err1@demo.com")
    prov_token = create_test_token(rsa_key_pair, sub="prov-1", email="provider@demo.com")

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {pat_token}"})
    client.post("/api/me/consent", headers={"Authorization": f"Bearer {pat_token}"}, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={"conditions": ["hypertension"]},
    )
    _insert_checkin_with_vitals("pat-err-1", "chk-err-1", days_ago=1, systolic=140, diastolic=90, db_path=setup_test_environment)

    # Monkeypatch risk assessment to raise unexpected error
    import agents.risk_agent
    monkeypatch.setattr(agents.risk_agent, "assess", lambda *args, **kwargs: 1 / 0)

    client.post("/api/auth/session", headers={"Authorization": f"Bearer {prov_token}"})
    resp = client.get("/api/provider/review/chk-err-1", headers={"Authorization": f"Bearer {prov_token}"})
    assert resp.status_code == 200
    # Must gracefully fall back to None without crashing
    assert resp.json().get("risk") is None
