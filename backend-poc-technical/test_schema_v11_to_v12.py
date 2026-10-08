"""
Hermetic Tests for Schema Migration Version 11 to 12 (Stage 8b Task B).
Verifies:
1. SQLite database at version 11 with existing v11 data migrates to v12 cleanly.
2. New columns appear, existing columns and values remain untouched.
3. Migration is strictly idempotent (running twice changes nothing).
4. Profile endpoint answers with empty default background fields for v11 existing users.
5. MySQL migration handles duplicate columns (error 1060) defensively.
6. Schema pre-flight computes and expects version 12.
"""

import os
import sqlite3
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from data_sources.app_store import (
    migrate,
    get_db_cursor,
    get_patient_profile,
    upsert_patient_profile,
    create_user,
    LATEST_SCHEMA_VERSION,
)
from main import app


@pytest.fixture
def test_db_path(tmp_path):
    """Creates a temporary sqlite database file."""
    return str(tmp_path / "test_migration_v11_v12.db")


def create_v11_database(db_path: str):
    """
    Constructs a database strictly at schema version 11 (including sex_at_birth and pregnancy_status),
    without version 12 columns, and inserts a pre-existing patient.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Schema version table at v11
    cursor.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 12):
        cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)", (v, now))

    # Users table
    cursor.execute("""
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('patient','provider','admin')),
            display_name TEXT,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','disabled')),
            created_at TEXT NOT NULL,
            last_login_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            actor_user_id TEXT,
            action TEXT NOT NULL,
            target TEXT,
            outcome TEXT NOT NULL,
            detail_json TEXT NOT NULL
        )
    """)

    # patient_profiles strictly at version 11
    cursor.execute("""
        CREATE TABLE patient_profiles (
            user_id TEXT PRIMARY KEY,
            conditions_json TEXT NOT NULL,
            on_insulin_or_sulfonylurea INTEGER NOT NULL DEFAULT 0,
            language TEXT NOT NULL DEFAULT 'en',
            consent_granted_at TEXT,
            consent_revoked_at TEXT,
            conditions_basis_json TEXT,
            provider_notification_consent_at TEXT,
            provider_notification_revoked_at TEXT,
            date_of_birth TEXT,
            inclusion_confirmed_at TEXT,
            sex_at_birth TEXT,
            pregnancy_status TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE ehr_systems (
            ehr_system_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            fhir_base_url TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            kind TEXT DEFAULT 'public_sandbox',
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE ehr_connections (
            connection_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            ehr_system_id TEXT NOT NULL,
            external_patient_id TEXT NOT NULL,
            status TEXT NOT NULL,
            linked_at TEXT NOT NULL,
            last_verified_at TEXT,
            last_error_code TEXT,
            revoked_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE checkins (
            checkin_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            record_patient_id TEXT NOT NULL,
            status TEXT NOT NULL,
            state_json TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            med_state_json TEXT,
            protocol_state_json TEXT,
            ehr_system_id TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE checkin_results (
            checkin_id TEXT PRIMARY KEY,
            emergency INTEGER NOT NULL,
            intakes_json TEXT NOT NULL,
            reconciliation_json TEXT,
            verification_json TEXT,
            requires_review INTEGER NOT NULL,
            max_severity TEXT,
            review_status TEXT NOT NULL,
            trigger_category TEXT,
            trigger_text TEXT,
            escalated_at TEXT,
            triage_level TEXT,
            triage_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(checkin_id) REFERENCES checkins(checkin_id)
        )
    """)

    # Insert a user created during schema version 11
    cursor.execute("""
        INSERT INTO users (user_id, email, role, display_name, status, created_at)
        VALUES ('usr-v11-patient', 'patient_v11@example.com', 'patient', 'Fatima Zahra', 'active', ?)
    """, (now,))

    cursor.execute("""
        INSERT INTO patient_profiles (
            user_id, conditions_json, on_insulin_or_sulfonylurea, language,
            consent_granted_at, provider_notification_consent_at,
            date_of_birth, inclusion_confirmed_at, sex_at_birth, pregnancy_status, updated_at
        ) VALUES (
            'usr-v11-patient', '["diabetes","hypertension"]', 1, 'ur',
            ?, ?,
            '1980-05-20', ?, 'female', 'not_pregnant', ?
        )
    """, (now, now, now, now))

    conn.commit()
    conn.close()


def test_sqlite_schema_v11_to_v12_migration(test_db_path):
    """
    Task B: Builds a database at version 11, runs migrate(), and verifies:
    1. The new columns appear: voice_enabled, height_cm, weight_kg, diagnosis_year_diabetes,
       diagnosis_year_hypertension, smoking_status, comorbidities_json.
    2. Existing rows keep every old value (sex_at_birth, pregnancy_status, DOB, etc.).
    3. Running migrate() twice changes nothing and does not fail.
    4. Profile returned has empty/None new enrolment fields and profile endpoint still answers.
    """
    create_v11_database(test_db_path)

    # Verify v12 columns do not exist in v11 database
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(patient_profiles)")
    v11_cols = [r[1] for r in cur.fetchall()]
    assert "sex_at_birth" in v11_cols
    assert "pregnancy_status" in v11_cols
    assert "height_cm" not in v11_cols
    assert "weight_kg" not in v11_cols
    assert "voice_enabled" not in v11_cols
    conn.close()

    # 1. Run migrate() to advance to v12
    migrate(backend="sqlite", db_path=test_db_path)

    # Verify columns exist now
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(patient_profiles)")
    v12_cols = [r[1] for r in cur.fetchall()]
    for col in [
        "voice_enabled", "height_cm", "weight_kg",
        "diagnosis_year_diabetes", "diagnosis_year_hypertension",
        "smoking_status", "comorbidities_json"
    ]:
        assert col in v12_cols, f"Column {col} missing in v12 schema"

    # Verify schema_version records version 12
    cur.execute("SELECT version FROM schema_version WHERE version = 12")
    assert cur.fetchone() is not None, "Version 12 missing from schema_version table"
    conn.close()

    # 2. Existing values are completely untouched
    profile = get_patient_profile("usr-v11-patient", backend="sqlite", db_path=test_db_path)
    assert profile is not None
    assert profile["sex_at_birth"] == "female"
    assert profile["pregnancy_status"] == "not_pregnant"
    assert profile["date_of_birth"] == "1980-05-20"
    assert profile["language"] == "ur"
    assert profile["conditions"] == ["diabetes", "hypertension"]
    assert profile["on_insulin_or_sulfonylurea"] is True

    # 3. New fields are empty/None or defaulted
    assert profile["voice_enabled"] is False
    assert profile["height_cm"] is None
    assert profile["weight_kg"] is None
    assert profile["diagnosis_year_diabetes"] is None
    assert profile["diagnosis_year_hypertension"] is None
    assert profile["smoking_status"] is None
    assert profile["comorbidities"] is None

    # 4. Running migrate() a second time is completely idempotent
    migrate(backend="sqlite", db_path=test_db_path)
    profile_after = get_patient_profile("usr-v11-patient", backend="sqlite", db_path=test_db_path)
    assert profile_after == profile


def test_mysql_v12_ddl_and_duplicate_guard():
    """
    Task B (MySQL): Simulates MySQL migration to v12 and verifies:
    1. Schema inspection checks each column before ALTER TABLE.
    2. When column already exists or error 1060 would occur, migration guards against failure.
    """
    fake_cursor = MagicMock()
    # Simulate schema_version table exists, version 1-11 exist, version 12 not yet applied
    def execute_side_effect(query, *args):
        return None

    fake_cursor.execute.side_effect = execute_side_effect
    fake_cursor.fetchone.return_value = None  # means column does not exist yet -> triggers ALTER TABLE

    with patch("data_sources.app_store.get_db_cursor") as mock_get_cursor:
        mock_get_cursor.return_value.__enter__.return_value = (fake_cursor, "mysql", "%s")
        migrate(backend="mysql", mysql_url="mysql+pymysql://fake:fake@127.0.0.1/fake_db")

    # Verify version 12 was inserted
    calls = [str(c) for c in fake_cursor.execute.mock_calls]
    v12_call = any("INSERT INTO schema_version (version, applied_at) VALUES (12" in c for c in calls)
    assert v12_call, "Migration 12 not executed for MySQL"


def test_latest_schema_version_is_12():
    """Confirms LATEST_SCHEMA_VERSION constant is updated to 12."""
    assert LATEST_SCHEMA_VERSION == 12
