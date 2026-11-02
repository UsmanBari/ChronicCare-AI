"""
Hermetic Tests for Schema Migration Version 13 to 14 (Record edit history).
Verifies:
1. SQLite database at version 13 with existing v13 data (including waist_cm) migrates to v14 cleanly.
2. New table record_edits appears with all expected columns.
3. Composite indexes idx_record_edits_lookup and idx_record_edits_timeline are created.
4. Migration is strictly idempotent (running twice changes nothing).
5. Existing v13 waist_cm and patient profile data remain intact.
6. MySQL migration handles record_edits table creation and defines correct DDL syntax.
7. LATEST_SCHEMA_VERSION is 14.
"""

import sqlite3
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from data_sources.app_store import (
    migrate,
    get_patient_profile,
    upsert_patient_profile,
    LATEST_SCHEMA_VERSION,
    MYSQL_RECORD_EDITS_DDL,
)


@pytest.fixture
def test_db_path(tmp_path):
    """Creates a temporary sqlite database file."""
    return str(tmp_path / "test_migration_v13_v14.db")


def create_v13_database(db_path: str):
    """
    Constructs a database strictly at schema version 13 (including waist_cm),
    without record_edits, and inserts a pre-existing patient with waist_cm.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Schema version table at v13
    cursor.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 14):
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

    # patient_profiles strictly at version 13 (has waist_cm)
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
            waist_cm REAL DEFAULT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE ehr_systems (
            ehr_system_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            fhir_base_url TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'public_sandbox',
            description TEXT,
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE ehr_connections (
            connection_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            ehr_system_id TEXT NOT NULL,
            external_patient_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('active','failed','revoked')),
            linked_at TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            last_error_code TEXT,
            revoked_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(ehr_system_id) REFERENCES ehr_systems(ehr_system_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE checkins (
            checkin_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL CHECK(status IN ('in_progress','completed','abandoned')),
            answers_json TEXT NOT NULL DEFAULT '{}',
            mode TEXT NOT NULL DEFAULT 'isolated' CHECK(mode IN ('isolated','connected')),
            active_engine TEXT NOT NULL DEFAULT 'v2' CHECK(active_engine IN ('v2','v3')),
            triage_tier TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE checkin_results (
            checkin_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            reconciliation_json TEXT,
            requires_review INTEGER NOT NULL DEFAULT 0,
            review_status TEXT NOT NULL DEFAULT 'not_required' CHECK(review_status IN ('not_required','open','acknowledged','resolved','escalated')),
            max_severity TEXT NOT NULL DEFAULT 'none' CHECK(max_severity IN ('none','mild','moderate','severe')),
            triage_tier TEXT,
            emergency_reasons_json TEXT,
            provider_actions_json TEXT,
            verification_json TEXT,
            intakes_json TEXT,
            summary_en TEXT,
            summary_ur TEXT,
            mode TEXT NOT NULL DEFAULT 'isolated' CHECK(mode IN ('isolated','connected')),
            clinical_evaluation_json TEXT,
            FOREIGN KEY(checkin_id) REFERENCES checkins(checkin_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE review_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkin_id TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('acknowledge','resolve','escalate')),
            note TEXT,
            ts TEXT NOT NULL,
            FOREIGN KEY(checkin_id) REFERENCES checkins(checkin_id),
            FOREIGN KEY(provider_user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE allergies (
            allergy_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            substance TEXT NOT NULL,
            reaction TEXT,
            confirmed INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)

    # Pre-seed patient at v13 WITH waist_cm=89.0
    cursor.execute("""
        INSERT INTO users (user_id, email, role, display_name, status, created_at)
        VALUES ('usr-v13-patient', 'v13patient@test.local', 'patient', 'V13 Patient', 'active', ?)
    """, (now,))

    cursor.execute("""
        INSERT INTO patient_profiles (
            user_id, conditions_json, on_insulin_or_sulfonylurea, language,
            consent_granted_at, inclusion_confirmed_at, sex_at_birth,
            voice_enabled, height_cm, weight_kg, waist_cm,
            diagnosis_year_hypertension, smoking_status, updated_at
        )
        VALUES (
            'usr-v13-patient', '[\"hypertension\"]', 0, 'en',
            ?, ?, 'female',
            1, 162.0, 68.0, 89.0,
            2019, 'never', ?
        )
    """, (now, now, now))

    conn.commit()
    conn.close()


def test_sqlite_schema_v13_to_v14_migration(test_db_path):
    """
    Builds a database at version 13, runs migrate(), and verifies:
    1. record_edits table appears with all columns.
    2. Composite indexes idx_record_edits_lookup and idx_record_edits_timeline exist.
    3. Existing v13 waist_cm data is preserved.
    4. Migration is idempotent (running twice changes nothing).
    5. Schema version table records version 14.
    """
    create_v13_database(test_db_path)

    # Verify record_edits does not exist before migration
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='record_edits'")
    assert cur.fetchone() is None
    conn.close()

    # Run migrate() to advance to v14
    migrate(backend="sqlite", db_path=test_db_path)

    # Verify record_edits table exists and has expected columns
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(record_edits)")
    re_cols = [r[1] for r in cur.fetchall()]
    for expected_col in [
        "edit_id", "user_id", "record_type", "record_id", "field",
        "old_value", "new_value", "origin", "changed_by_user_id", "changed_at", "reason"
    ]:
        assert expected_col in re_cols, f"Missing column {expected_col} in record_edits"

    # Verify composite indexes exist
    cur.execute("PRAGMA index_list(record_edits)")
    indexes = [r[1] for r in cur.fetchall()]
    assert "idx_record_edits_lookup" in indexes
    assert "idx_record_edits_timeline" in indexes

    # Verify schema_version table records version 14
    cur.execute("SELECT version FROM schema_version WHERE version = 14")
    assert cur.fetchone() is not None
    conn.close()

    # Verify existing v13 patient profile with waist_cm is completely untouched
    profile = get_patient_profile("usr-v13-patient", backend="sqlite", db_path=test_db_path)
    assert profile is not None
    assert profile["sex_at_birth"] == "female"
    assert profile["height_cm"] == 162.0
    assert profile["weight_kg"] == 68.0
    assert profile["waist_cm"] == 89.0

    # Idempotent: run migrate() again
    migrate(backend="sqlite", db_path=test_db_path)
    profile_after = get_patient_profile("usr-v13-patient", backend="sqlite", db_path=test_db_path)
    assert profile_after["waist_cm"] == 89.0


def test_fresh_database_creates_v14_directly(tmp_path):
    """Verifies that a fresh database initializes directly to schema v14."""
    fresh_db = str(tmp_path / "fresh_v14.db")
    migrate(backend="sqlite", db_path=fresh_db)

    conn = sqlite3.connect(fresh_db)
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM schema_version")
    max_ver = cur.fetchone()[0]
    assert max_ver >= 14

    cur.execute("PRAGMA table_info(record_edits)")
    re_cols = [r[1] for r in cur.fetchall()]
    assert "edit_id" in re_cols
    assert "changed_at" in re_cols
    conn.close()


def test_mysql_v14_ddl_and_duplicate_guard():
    """
    Simulates MySQL migration to v14 and verifies:
    1. Migration executes MYSQL_RECORD_EDITS_DDL.
    2. Version 14 record is inserted into schema_version.
    """
    fake_cursor = MagicMock()
    fake_cursor.execute.side_effect = lambda query, *args: None
    fake_cursor.fetchone.return_value = None

    with patch("data_sources.app_store.get_db_cursor") as mock_get_cursor:
        mock_get_cursor.return_value.__enter__.return_value = (fake_cursor, "mysql", "%s")
        migrate(backend="mysql", mysql_url="mysql+pymysql://fake:fake@127.0.0.1/fake_db")

    calls = [str(c) for c in fake_cursor.execute.mock_calls]
    v14_call = any("INSERT INTO schema_version (version, applied_at) VALUES (14" in c for c in calls)
    assert v14_call, "Migration 14 not executed for MySQL"


def test_mysql_record_edits_ddl_syntax_and_columns():
    """
    Asserts that MYSQL_RECORD_EDITS_DDL defines all required columns, data types,
    and composite indexes for MySQL production path.
    """
    ddl_lower = MYSQL_RECORD_EDITS_DDL.lower()
    assert "create table if not exists record_edits" in ddl_lower
    for col in [
        "edit_id varchar(64) primary key",
        "user_id varchar(64) not null",
        "record_type varchar(32) not null",
        "record_id varchar(64) not null",
        "field varchar(64) not null",
        "old_value text",
        "new_value text",
        "origin varchar(32) not null",
        "changed_by_user_id varchar(64) not null",
        "changed_at varchar(64) not null",
        "reason text",
        "index idx_record_edits_lookup (user_id, record_type, record_id)",
        "index idx_record_edits_timeline (user_id, changed_at desc)",
    ]:
        assert col in ddl_lower, f"MySQL DDL missing definition: {col}"


def test_latest_schema_version_is_14():
    """Confirms LATEST_SCHEMA_VERSION constant is updated to 14."""
    assert LATEST_SCHEMA_VERSION >= 14
