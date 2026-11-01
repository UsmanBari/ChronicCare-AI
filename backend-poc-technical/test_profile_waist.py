"""
Hermetic Tests for Patient Profile Waist Circumference Field (Part H).
Verifies:
1. Valid waist values (40.0 - 200.0 cm) are accepted and rounded to 1 decimal place.
2. Values below 40.0 or above 200.0 are rejected with 422 Unprocessable Entity
   and state '(needs doctor review)'.
3. Non-numeric waist values are rejected.
4. Waist circumference is optional (None or omitted does not block profile update or inclusion).
5. GET /api/me/profile and PUT /api/me/profile round-trip waist_cm accurately.
6. _build_patient_background includes waist_cm.
"""

import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch

from data_sources.app_store import (
    migrate,
    create_user,
    upsert_patient_profile,
    get_patient_profile,
)
from main import app, WAIST_MIN_CM, WAIST_MAX_CM, _build_patient_background, get_current_user


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    """Provides a TestClient connected to a hermetic SQLite database at schema v13."""
    db_file = str(tmp_path / "test_profile_waist.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")
    migrate(backend="sqlite", db_path=db_file)

    now = datetime.now(timezone.utc).isoformat()
    create_user(
        user_id="usr-waist-tester",
        email="waist_tester@example.com",
        role="patient",
        display_name="Waist Tester",
        backend="sqlite",
        db_path=db_file,
    )
    upsert_patient_profile(
        user_id="usr-waist-tester",
        conditions=["hypertension"],
        on_insulin_or_sulfonylurea=False,
        language="en",
        date_of_birth="1980-01-01",
        inclusion_confirmed=True,
        sex_at_birth="female",
        pregnancy_status="no",
        backend="sqlite",
        db_path=db_file,
    )

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "usr-waist-tester",
        "email": "waist_tester@example.com",
        "role": "patient",
        "status": "active",
    }
    with TestClient(app) as client:
        yield client, db_file
    app.dependency_overrides.clear()


def test_waist_constants():
    """Verifies adult waist circumference range constants."""
    assert WAIST_MIN_CM == 40.0
    assert WAIST_MAX_CM == 200.0


def test_profile_waist_valid_round_trip(client_with_db):
    """Tests updating and reading valid waist_cm values."""
    client, db_path = client_with_db

    # Initially None
    res = client.get("/api/me/profile")
    assert res.status_code == 200
    assert res.json()["waist_cm"] is None

    # Update with 88.54 -> rounds to 88.5
    res = client.put("/api/me/profile", json={"waist_cm": 88.54})
    assert res.status_code == 200
    data = res.json()
    assert data["waist_cm"] == 88.5

    # Verify persistent in DB
    prof = get_patient_profile("usr-waist-tester", backend="sqlite", db_path=db_path)
    assert prof["waist_cm"] == 88.5

    # Verify _build_patient_background includes it
    with patch("main.get_patient_profile", return_value=prof):
        bg = _build_patient_background("usr-waist-tester")
        assert bg is not None
        assert bg["waist_cm"] == 88.5


@pytest.mark.parametrize("invalid_waist", [39.9, 20.0, 0.0, -10.0, 200.1, 250.0, 999.0])
def test_profile_waist_out_of_bounds_rejected(client_with_db, invalid_waist):
    """Tests that out-of-bounds waist values return 422 with doctor review message."""
    client, _ = client_with_db
    res = client.put("/api/me/profile", json={"waist_cm": invalid_waist})
    assert res.status_code == 422
    err_msg = res.text
    assert "needs doctor review" in err_msg


def test_profile_waist_non_numeric_rejected(client_with_db):
    """Tests that non-numeric waist values return 422."""
    client, _ = client_with_db
    res = client.put("/api/me/profile", json={"waist_cm": "very_large"})
    assert res.status_code == 422


def test_profile_waist_optional(client_with_db):
    """Tests that waist_cm is purely optional and omittable."""
    client, _ = client_with_db

    # Updating other fields without waist_cm does not clear or fail
    res = client.put("/api/me/profile", json={"waist_cm": 92.0})
    assert res.status_code == 200
    assert res.json()["waist_cm"] == 92.0

    res = client.put("/api/me/profile", json={"language": "ur"})
    assert res.status_code == 200
    assert res.json()["language"] == "ur"
    assert res.json()["waist_cm"] == 92.0  # preserved
