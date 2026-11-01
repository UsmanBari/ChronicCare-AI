"""
Hermetic Tests for Schema Migration Version 14 to 15 (Risk, Guideline Explanations, Trace & Chunks).
Verifies:
1. SQLite database at version 14 with existing v14 data (waist_cm, record_edits, checkin_results) migrates to v15 cleanly.
2. checkin_results gains risk_json, explanation_json, and trace_json columns.
3. New table guideline_chunks appears with all expected columns and indexes.
4. Existing v14 data is preserved without data loss or corruption.
5. Migration is strictly idempotent (running twice changes nothing).
6. Fresh database migration initializes directly to v15.
7. MySQL migration DDL defines correct syntax and expected columns.
8. LATEST_SCHEMA_VERSION is 15.
"""

import sqlite3
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from data_sources.app_store import (
    migrate,
    get_patient_profile,
    get_checkin_result,
    LATEST_SCHEMA_VERSION,
    MYSQL_GUIDELINE_CHUNKS_DDL,
    SQLITE_RECORD_EDITS_DDL,
    SQLITE_RECORD_EDITS_LOOKUP_INDEX,
    SQLITE_RECORD_EDITS_TIMELINE_INDEX,
)


@pytest.fixture
def test_db_path(tmp_path):
    """Creates a temporary sqlite database file."""
    return str(tmp_path / "test_migration_v14_v15.db")


def create_v14_database(db_path: str):
    """
    Constructs a database strictly at schema version 14 (including waist_cm and record_edits),
    without v15 columns/tables, and inserts pre-existing patient and checkin result data.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Schema version table at v14
    cursor.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 15):
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

    # patient_profiles strictly at version 14 (has waist_cm)
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

    # checkin_results strictly at v14 (has triage_level, triage_json, but NO risk_json, explanation_json, trace_json)
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

    cursor.execute("""
        CREATE TABLE review_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkin_id TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            action TEXT NOT NULL,
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

    # record_edits strictly at v14
    cursor.execute(SQLITE_RECORD_EDITS_DDL)
    cursor.execute(SQLITE_RECORD_EDITS_LOOKUP_INDEX)
    cursor.execute(SQLITE_RECORD_EDITS_TIMELINE_INDEX)

    # Pre-seed patient at v14 WITH waist_cm=89.0
    cursor.execute("""
        INSERT INTO users (user_id, email, role, display_name, status, created_at)
        VALUES ('usr-v14-patient', 'v14patient@test.local', 'patient', 'V14 Patient', 'active', ?)
    """, (now,))

    cursor.execute("""
        INSERT INTO patient_profiles (
            user_id, conditions_json, on_insulin_or_sulfonylurea, language,
            consent_granted_at, inclusion_confirmed_at, sex_at_birth,
            voice_enabled, height_cm, weight_kg, waist_cm,
            diagnosis_year_hypertension, smoking_status, updated_at
        )
        VALUES (
            'usr-v14-patient', '[\"hypertension\"]', 0, 'en',
            ?, ?, 'female',
            1, 162.0, 68.0, 89.0,
            2019, 'never', ?
        )
    """, (now, now, now))

    # Pre-seed a record edit row at v14
    cursor.execute("""
        INSERT INTO record_edits (
            edit_id, user_id, record_type, record_id, field,
            old_value, new_value, origin, changed_by_user_id, changed_at, reason
        ) VALUES (
            'edit-v14-001', 'usr-v14-patient', 'medication', 'med-123', 'dose',
            '5mg', '10mg', 'patient_self_report', 'usr-v14-patient', ?, 'Dose adjusted'
        )
    """, (now,))

    # Pre-seed a check-in and checkin_result at v14
    cursor.execute("""
        INSERT INTO checkins (checkin_id, user_id, started_at, completed_at, status, answers_json, mode)
        VALUES ('chk-v14-001', 'usr-v14-patient', ?, ?, 'completed', '{}', 'isolated')
    """, (now, now))

    cursor.execute("""
        INSERT INTO checkin_results (
            checkin_id, emergency, intakes_json, requires_review, max_severity,
            review_status, triage_level, triage_json, created_at
        ) VALUES (
            'chk-v14-001', 0, '[]', 0, 'none', 'resolved', 'routine', '{\"level\": \"routine\"}', ?
        )
    """, (now,))

    conn.commit()
    conn.close()


def test_sqlite_schema_v14_to_v15_migration(test_db_path):
    """
    Builds a database at version 14, runs migrate(), and verifies:
    1. checkin_results gains risk_json, explanation_json, and trace_json columns.
    2. guideline_chunks table appears with all columns and indexes.
    3. Existing v14 data (waist_cm, record_edits, checkin_results) is preserved.
    4. Migration is strictly idempotent.
    5. Schema version table records version 15.
    """
    create_v14_database(test_db_path)

    # Verify guideline_chunks does not exist before migration
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guideline_chunks'")
    assert cur.fetchone() is None

    cur.execute("PRAGMA table_info(checkin_results)")
    cr_cols_before = [row[1] for row in cur.fetchall()]
    assert "risk_json" not in cr_cols_before
    assert "explanation_json" not in cr_cols_before
    assert "trace_json" not in cr_cols_before
    conn.close()

    # Run migrate() to advance to v15
    migrate(backend="sqlite", db_path=test_db_path)

    # Verify checkin_results columns
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(checkin_results)")
    cr_cols_after = [row[1] for row in cur.fetchall()]
    assert "risk_json" in cr_cols_after
    assert "explanation_json" in cr_cols_after
    assert "trace_json" in cr_cols_after

    # Verify guideline_chunks table exists and has all required columns
    cur.execute("PRAGMA table_info(guideline_chunks)")
    cols = {row[1]: row[2].upper() for row in cur.fetchall()}
    expected_cols = {
        "chunk_id": "TEXT",
        "source_id": "TEXT",
        "title": "TEXT",
        "edition": "TEXT",
        "priority": "INTEGER",
        "section_path": "TEXT",
        "page_start": "INTEGER",
        "page_end": "INTEGER",
        "grade": "TEXT",
        "condition": "TEXT",
        "topics_json": "TEXT",
        "text": "TEXT",
        "loaded_at": "TEXT",
    }
    for c_name, c_type in expected_cols.items():
        assert c_name in cols, f"Column {c_name} missing from guideline_chunks"
        assert cols[c_name] == c_type, f"Column {c_name} type {cols[c_name]} != {c_type}"

    # Verify indexes
    cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='guideline_chunks'")
    indexes = [row[0] for row in cur.fetchall()]
    assert "idx_guideline_chunks_condition" in indexes
    assert "idx_guideline_chunks_source" in indexes

    # Verify schema version
    cur.execute("SELECT MAX(version) FROM schema_version")
    assert cur.fetchone()[0] == 15
    conn.close()

    # Verify existing v14 data was preserved
    prof = get_patient_profile("usr-v14-patient", backend="sqlite", db_path=test_db_path)
    assert prof is not None
    assert prof["waist_cm"] == 89.0

    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT edit_id, field, new_value FROM record_edits WHERE edit_id='edit-v14-001'")
    edit_row = cur.fetchone()
    assert edit_row == ("edit-v14-001", "dose", "10mg")

    cur.execute("SELECT checkin_id, triage_level, risk_json, explanation_json, trace_json FROM checkin_results WHERE checkin_id='chk-v14-001'")
    res_row = cur.fetchone()
    assert res_row == ("chk-v14-001", "routine", None, None, None)
    conn.close()

    # Verify idempotence: run migrate() again
    migrate(backend="sqlite", db_path=test_db_path)
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM schema_version WHERE version = 15")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_sqlite_fresh_database_is_v15(test_db_path):
    """
    Verifies that running migrate() on an empty database brings it directly to v15.
    """
    migrate(backend="sqlite", db_path=test_db_path)

    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM schema_version")
    assert cur.fetchone()[0] == 15

    cur.execute("PRAGMA table_info(checkin_results)")
    cr_cols = [row[1] for row in cur.fetchall()]
    assert "risk_json" in cr_cols
    assert "explanation_json" in cr_cols
    assert "trace_json" in cr_cols

    cur.execute("PRAGMA table_info(guideline_chunks)")
    gc_cols = [row[1] for row in cur.fetchall()]
    assert "chunk_id" in gc_cols
    assert "condition" in gc_cols
    assert "text" in gc_cols
    conn.close()


def test_mysql_migration_v15_ddl_and_columns():
    """
    Verifies that MySQL migration v15 includes all expected DDL statements and column additions.
    """
    assert "CREATE TABLE IF NOT EXISTS guideline_chunks" in MYSQL_GUIDELINE_CHUNKS_DDL
    assert "`condition` VARCHAR(64) NOT NULL" in MYSQL_GUIDELINE_CHUNKS_DDL
    assert "text MEDIUMTEXT NOT NULL" in MYSQL_GUIDELINE_CHUNKS_DDL
    assert "loaded_at VARCHAR(64) NOT NULL" in MYSQL_GUIDELINE_CHUNKS_DDL
    assert "INDEX idx_guideline_chunks_condition (`condition`)" in MYSQL_GUIDELINE_CHUNKS_DDL
    assert "INDEX idx_guideline_chunks_source (source_id)" in MYSQL_GUIDELINE_CHUNKS_DDL


def test_latest_schema_version_is_15():
    """Confirms LATEST_SCHEMA_VERSION constant is strictly 15."""
    assert LATEST_SCHEMA_VERSION == 15

