"""
Integration tests for get_user_reading_history in data_sources/app_store.py (Iteration 2 - Day 4).

Validates:
- User isolation: only the requested user's readings appear
- Excludes emergency check-ins (emergency == 1)
- Excludes incomplete check-ins (status != 'complete')
- Respects the configurable day window (e.g. 30 vs 40 days)
- Includes isolated-mode Local Store observations with source='local_store' and checkin_id=None
- Excludes CHECKIN- copies in Local Store to prevent double-counting
- Preserves glucose_context when present
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sqlite3
import pytest

from data_sources import app_store, local_store


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Sets up a clean temporary SQLite database with app_store and local_store schemas."""
    db_file = str(tmp_path / "test_reading_hist.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    return db_file


def _insert_checkin(
    db_path: str,
    user_id: str,
    checkin_id: str,
    completed_at: str,
    status: str = "complete",
    emergency: int = 0,
    intakes: list | None = None,
):
    """Helper to insert a check-in and its result directly into SQLite tables."""
    if intakes is None:
        intakes = []
    intakes_json = json.dumps(intakes)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Insert user if not exists
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, email, role, created_at) VALUES (?, ?, 'patient', ?)",
        (user_id, f"{user_id}@demo.com", completed_at),
    )
    # Insert checkin
    cur.execute(
        """
        INSERT INTO checkins (
            checkin_id, user_id, mode, record_patient_id, status,
            state_json, version, started_at, completed_at
        )
        VALUES (?, ?, 'isolated', 'rec-1', ?, '{}', 1, ?, ?)
        """,
        (checkin_id, user_id, status, completed_at, completed_at if status == "complete" else None),
    )
    # Insert checkin_result
    cur.execute(
        """
        INSERT INTO checkin_results (
            checkin_id, emergency, intakes_json, requires_review, review_status, created_at
        )
        VALUES (?, ?, ?, 0, 'open', ?)
        """,
        (checkin_id, emergency, intakes_json, completed_at),
    )
    conn.commit()
    conn.close()


def test_user_scoping_isolation(temp_db):
    """Verify that User A sees only User A's readings, and User B sees only User B's readings."""
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    intakes_a = [{
        "condition": "hypertension",
        "readings": [{"observation_type": "blood_pressure_systolic", "value": 125.0}],
    }]
    intakes_b = [{
        "condition": "hypertension",
        "readings": [{"observation_type": "blood_pressure_systolic", "value": 155.0}],
    }]

    _insert_checkin(temp_db, "usr-alice", "chk-a1", now_ts, status="complete", emergency=0, intakes=intakes_a)
    _insert_checkin(temp_db, "usr-bob", "chk-b1", now_ts, status="complete", emergency=0, intakes=intakes_b)

    hist_a = app_store.get_user_reading_history("usr-alice", db_path=temp_db, backend="sqlite")
    hist_b = app_store.get_user_reading_history("usr-bob", db_path=temp_db, backend="sqlite")

    assert len(hist_a) == 1
    assert hist_a[0]["value"] == 125.0
    assert hist_a[0]["source"] == "checkin"
    assert hist_a[0]["checkin_id"] == "chk-a1"

    assert len(hist_b) == 1
    assert hist_b[0]["value"] == 155.0
    assert hist_b[0]["source"] == "checkin"
    assert hist_b[0]["checkin_id"] == "chk-b1"


def test_emergency_and_incomplete_checkins_excluded(temp_db):
    """Verify that emergency check-ins and incomplete check-ins are excluded."""
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Normal completed check-in
    _insert_checkin(temp_db, "usr-1", "chk-valid", now_ts, status="complete", emergency=0, intakes=[{
        "readings": [{"observation_type": "glucose", "value": 110.0}],
    }])
    # 2. Emergency completed check-in (emergency == 1)
    _insert_checkin(temp_db, "usr-1", "chk-em", now_ts, status="complete", emergency=1, intakes=[{
        "readings": [{"observation_type": "glucose", "value": 450.0}],
    }])
    # 3. In-progress / incomplete check-in (status != 'complete')
    _insert_checkin(temp_db, "usr-1", "chk-inprog", now_ts, status="in_progress", emergency=0, intakes=[{
        "readings": [{"observation_type": "glucose", "value": 200.0}],
    }])

    hist = app_store.get_user_reading_history("usr-1", db_path=temp_db, backend="sqlite")
    assert len(hist) == 1
    assert hist[0]["value"] == 110.0
    assert hist[0]["checkin_id"] == "chk-valid"


def test_window_days_respected(temp_db):
    """Verify that readings older than the specified day window are excluded."""
    now_dt = datetime.now(timezone.utc)
    ts_10_days_ago = (now_dt - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_35_days_ago = (now_dt - timedelta(days=35)).strftime("%Y-%m-%dT%H:%M:%SZ")

    _insert_checkin(temp_db, "usr-win", "chk-recent", ts_10_days_ago, status="complete", emergency=0, intakes=[{
        "readings": [{"observation_type": "blood_pressure_diastolic", "value": 75.0}],
    }])
    _insert_checkin(temp_db, "usr-win", "chk-old", ts_35_days_ago, status="complete", emergency=0, intakes=[{
        "readings": [{"observation_type": "blood_pressure_diastolic", "value": 85.0}],
    }])

    # With default 30 days window: 35-day-old check-in is excluded
    hist_30 = app_store.get_user_reading_history("usr-win", days=30, db_path=temp_db, backend="sqlite")
    assert len(hist_30) == 1
    assert hist_30[0]["value"] == 75.0

    # With expanded 40 days window: both check-ins are included
    hist_40 = app_store.get_user_reading_history("usr-win", days=40, db_path=temp_db, backend="sqlite")
    assert len(hist_40) == 2
    vals = [r["value"] for r in hist_40]
    assert 75.0 in vals and 85.0 in vals


def test_local_store_observations_included_without_checkin_copies(temp_db):
    """
    Verify:
    1. Isolated-mode Local Store observations are included with source='local_store' and checkin_id=None.
    2. CHECKIN- duplicates in Local Store are NOT double-counted.
    """
    now_dt = datetime.now(timezone.utc)
    ts_now = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Insert a check-in
    _insert_checkin(temp_db, "usr-isolated", "chk-1", ts_now, status="complete", emergency=0, intakes=[{
        "readings": [{"observation_type": "glucose", "value": 130.0}],
    }])

    # In Local Store for this patient (local-usr-isolated):
    # a) A real patient observation entered directly
    local_store.add_local_observation(
        id="OBS-DIRECT-1",
        patient_id="local-usr-isolated",
        observation_type="glucose",
        value=140.0,
        unit="mg/dL",
        timestamp=ts_now,
        db_path=temp_db,
    )
    # b) A mirrored CHECKIN- observation that must NOT be double-counted
    local_store.add_local_observation(
        id="CHECKIN-chk-1",
        patient_id="local-usr-isolated",
        observation_type="glucose",
        value=130.0,
        unit="mg/dL",
        timestamp=ts_now,
        db_path=temp_db,
    )

    hist = app_store.get_user_reading_history("usr-isolated", db_path=temp_db, backend="sqlite")
    # Should contain exactly 2 readings: check-in (130) + direct local_store (140), NOT 3
    assert len(hist) == 2

    checkin_entries = [r for r in hist if r["source"] == "checkin"]
    local_entries = [r for r in hist if r["source"] == "local_store"]

    assert len(checkin_entries) == 1
    assert checkin_entries[0]["value"] == 130.0
    assert checkin_entries[0]["checkin_id"] == "chk-1"

    assert len(local_entries) == 1
    assert local_entries[0]["value"] == 140.0
    assert local_entries[0]["checkin_id"] is None


def test_glucose_context_preserved(temp_db):
    """Verify glucose_context is preserved when present in intake answers or readings."""
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    intakes = [{
        "condition": "diabetes",
        "answers": {"glucose_context": "fasting"},
        "readings": [{"observation_type": "glucose", "value": 98.0, "glucose_context": "fasting"}],
    }]

    _insert_checkin(temp_db, "usr-ctx", "chk-ctx", now_ts, status="complete", emergency=0, intakes=intakes)

    hist = app_store.get_user_reading_history("usr-ctx", db_path=temp_db, backend="sqlite")
    assert len(hist) == 1
    assert hist[0]["glucose_context"] == "fasting"
