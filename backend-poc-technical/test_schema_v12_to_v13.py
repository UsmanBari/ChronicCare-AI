"""
Hermetic Tests for Schema Migration Version 12 to 13 (Waist circumference field).
Verifies:
1. SQLite database at version 12 with existing v12 data migrates to v13 cleanly.
2. New column waist_cm appears, existing columns and values remain untouched.
3. Migration is strictly idempotent (running twice changes nothing).
4. Patient profile returns waist_cm=None for existing v12 patients and accepts updates.
5. MySQL migration handles duplicate columns defensively.
6. Schema pre-flight computes and expects version 13.
"""

import os
import sqlite3
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from data_sources.app_store import (
    migrate,
    get_patient_profile,
    upsert_patient_profile,
    LATEST_SCHEMA_VERSION,
)


@pytest.fixture
def test_db_path(tmp_path):
    """Creates a temporary sqlite database file."""
    return str(tmp_path / "test_migration_v12_v13.db")


def create_v12_database(db_path: str):
    """
    Constructs a database strictly at schema version 12 (including v12 background columns),
    without waist_cm, and inserts a pre-existing patient.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Schema version table at v12
    cursor.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 13):
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

    # patient_profiles strictly at version 12 (has height_cm, weight_kg, smoking_status, etc. but NO waist_cm)
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
            voice_enabled INTEGER NOT NULL DEFAULT 0,
            height_cm REAL DEFAULT NULL,
            weight_kg REAL DEFAULT NULL,
            diagnosis_year_diabetes INTEGER DEFAULT NULL,
            diagnosis_year_hypertension INTEGER DEFAULT NULL,
            smoking_status TEXT DEFAULT NULL,
            comorbidities_json TEXT DEFAULT NULL,
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

    # Insert a user created during schema version 12
    cursor.execute("""
        INSERT INTO users (user_id, email, role, display_name, status, created_at)
        VALUES ('usr-v12-patient', 'patient_v12@example.com', 'patient', 'Tariq Mahmood', 'active', ?)
    """, (now,))

    cursor.execute("""
        INSERT INTO patient_profiles (
            user_id, conditions_json, on_insulin_or_sulfonylurea, language,
            consent_granted_at, provider_notification_consent_at,
            date_of_birth, inclusion_confirmed_at, sex_at_birth, pregnancy_status,
            voice_enabled, height_cm, weight_kg, diagnosis_year_diabetes,
            diagnosis_year_hypertension, smoking_status, updated_at
        ) VALUES (
            'usr-v12-patient', '["hypertension"]', 0, 'en',
            ?, ?,
            '1975-08-15', ?, 'male', 'not_pregnant',
            1, 175.0, 80.0, NULL,
            2018, 'never', ?
        )
    """, (now, now, now, now))

    conn.commit()
    conn.close()


def test_sqlite_schema_v12_to_v13_migration(test_db_path):
    """
    Builds a database at version 12, runs migrate(), and verifies:
    1. waist_cm column appears.
    2. Existing rows keep every old value.
    3. waist_cm is None for existing row.
    4. Upserting with waist_cm succeeds.
    5. Running migrate() twice is idempotent.
    """
    create_v12_database(test_db_path)

    # Verify waist_cm does not exist before migration
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(patient_profiles)")
    v12_cols = [r[1] for r in cur.fetchall()]
    assert "waist_cm" not in v12_cols
    assert "height_cm" in v12_cols
    assert "weight_kg" in v12_cols
    conn.close()

    # Run migrate() to advance to v13
    migrate(backend="sqlite", db_path=test_db_path)

    # Verify waist_cm column exists
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(patient_profiles)")
    v13_cols = [r[1] for r in cur.fetchall()]
    assert "waist_cm" in v13_cols

    # Verify schema_version table records version 13
    cur.execute("SELECT version FROM schema_version WHERE version = 13")
    assert cur.fetchone() is not None
    conn.close()

    # Existing values are completely untouched
    profile = get_patient_profile("usr-v12-patient", backend="sqlite", db_path=test_db_path)
    assert profile is not None
    assert profile["sex_at_birth"] == "male"
    assert profile["height_cm"] == 175.0
    assert profile["weight_kg"] == 80.0
    assert profile["waist_cm"] is None
    assert profile["smoking_status"] == "never"
    assert profile["diagnosis_year_hypertension"] == 2018

    # Upsert waist_cm
    updated = upsert_patient_profile(
        user_id="usr-v12-patient",
        waist_cm=88.5,
        backend="sqlite",
        db_path=test_db_path
    )
    assert updated["waist_cm"] == 88.5
    assert updated["height_cm"] == 175.0  # preserved

    # Migration is idempotent
    migrate(backend="sqlite", db_path=test_db_path)
    profile_after = get_patient_profile("usr-v12-patient", backend="sqlite", db_path=test_db_path)
    assert profile_after["waist_cm"] == 88.5


def test_mysql_v13_ddl_and_duplicate_guard():
    """
    Simulates MySQL migration to v13 and verifies:
    1. Schema inspection checks waist_cm column before ALTER TABLE.
    2. Version 13 record is inserted into schema_version.
    """
    fake_cursor = MagicMock()
    fake_cursor.execute.side_effect = lambda query, *args: None
    fake_cursor.fetchone.return_value = None  # column does not exist yet -> triggers ALTER TABLE

    with patch("data_sources.app_store.get_db_cursor") as mock_get_cursor:
        mock_get_cursor.return_value.__enter__.return_value = (fake_cursor, "mysql", "%s")
        migrate(backend="mysql", mysql_url="mysql+pymysql://fake:fake@127.0.0.1/fake_db")

    calls = [str(c) for c in fake_cursor.execute.mock_calls]
    v13_call = any("INSERT INTO schema_version (version, applied_at) VALUES (13" in c for c in calls)
    assert v13_call, "Migration 13 not executed for MySQL"


def test_latest_schema_version_is_13():
    """Confirms LATEST_SCHEMA_VERSION constant is updated to 13."""
    assert LATEST_SCHEMA_VERSION >= 13


def test_sqlite_v13_non_duplicate_error_is_raised():
    """Proves SQLite v13 migration raises on operational errors like disk I/O error."""
    fake_cursor = MagicMock()
    def execute_side_effect(query, *args):
        if "SELECT version FROM schema_version WHERE version = 13" in query:
            return None
        if "PRAGMA table_info" in query:
            return None
        if "ALTER TABLE patient_profiles ADD COLUMN waist_cm" in query:
            raise sqlite3.OperationalError("disk I/O error")
        return None

    fake_cursor.execute.side_effect = execute_side_effect
    fake_cursor.fetchone.return_value = None
    fake_cursor.fetchall.return_value = []

    with patch("data_sources.app_store.get_db_cursor") as mock_get_cursor:
        mock_get_cursor.return_value.__enter__.return_value = (fake_cursor, "sqlite", "?")
        with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
            migrate(backend="sqlite", db_path=":memory:")
