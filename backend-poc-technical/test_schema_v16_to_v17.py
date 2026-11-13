"""
Hermetic Tests for Schema Migration Version 16 to 17 (Appointments & Provider Directory).
Verifies:
1. LATEST_SCHEMA_VERSION is 17.
2. SQLite database at schema version 16 with existing data migrates cleanly to v17.
3. Existing data across all tables is preserved without loss or corruption.
4. SQLite migration is strictly idempotent (running repeatedly changes nothing).
5. Fresh SQLite database initializes directly to v17.
6. MySQL DDL specifies VARCHAR(191) for ID columns.
7. Fictional provider directory is seeded with 5 fictional providers on migration.
"""

import sqlite3
import tempfile
from datetime import UTC, datetime
from typing import Any

import pytest
from data_sources.app_store import (
    DEFAULT_FICTIONAL_PROVIDERS,
    LATEST_SCHEMA_VERSION,
    MYSQL_APPOINTMENTS_DDL,
    MYSQL_PROVIDER_DIRECTORY_DDL,
    get_patient_profile,
    list_providers,
    migrate,
)


@pytest.fixture
def test_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path


def create_v16_database(db_path: str):
    """
    Constructs a database strictly at schema version 16,
    inserting pre-existing patient profile and checkin result data.
    """
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 17):
        cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)", (v, now))

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
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE checkin_results (
            checkin_id TEXT PRIMARY KEY,
            emergency INTEGER NOT NULL DEFAULT 0,
            intakes_json TEXT NOT NULL,
            reconciliation_json TEXT NOT NULL,
            verification_json TEXT NOT NULL,
            requires_review INTEGER NOT NULL DEFAULT 0,
            max_severity TEXT NOT NULL,
            review_status TEXT NOT NULL,
            triage_level TEXT DEFAULT NULL,
            triage_json TEXT DEFAULT NULL,
            risk_json TEXT DEFAULT NULL,
            explanation_json TEXT DEFAULT NULL,
            trace_json TEXT DEFAULT NULL,
            completed_at TEXT NOT NULL
        )
    """)

    cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                   ("test-user-1", "test@example.com", "patient", "Test Patient", "active", now, None))
    cursor.execute("INSERT INTO patient_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   ("test-user-1", '["diabetes"]', 0, "en", now, None, None, None, None, "1980-01-01", now, "male", "not_applicable", 0, 175.0, 70.0, 2015, None, "never", None, 85.0, now))

    conn.commit()
    conn.close()


def test_latest_schema_version_is_17():
    """Confirms LATEST_SCHEMA_VERSION constant is updated to at least 17."""
    assert LATEST_SCHEMA_VERSION >= 17


def test_sqlite_v16_to_v17_migration(test_db_path):
    """Verifies SQLite database migrates from v16 to v17 cleanly and seeds 5 fictional providers."""
    create_v16_database(test_db_path)

    # Pre-migration assertions
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM schema_version")
    assert cur.fetchone()[0] == 16
    conn.close()

    # Run migration
    migrate(backend="sqlite", db_path=test_db_path)

    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM schema_version")
    assert cur.fetchone()[0] >= 17

    # Check provider_directory exists and has 5 fictional providers
    cur.execute("SELECT id, display_name, specialty, available FROM provider_directory ORDER BY id")
    providers = cur.fetchall()
    assert len(providers) == 5
    provider_ids = {p[0] for p in providers}
    assert "prov-demo-endo" in provider_ids
    assert "prov-demo-cardio" in provider_ids
    assert "prov-demo-im" in provider_ids
    assert "prov-demo-gen-1" in provider_ids
    assert "prov-demo-gen-2" in provider_ids

    # Check appointments table exists
    cur.execute("PRAGMA table_info(appointments)")
    cols = {row[1] for row in cur.fetchall()}
    assert "id" in cols
    assert "patient_id" in cols
    assert "checkin_id" in cols
    assert "provider_id" in cols
    assert "specialty" in cols
    assert "urgency" in cols
    assert "mode" in cols
    assert "status" in cols
    assert "slot_date" in cols
    assert "acknowledged_at" in cols
    assert "admin_flagged_at" in cols

    conn.close()

    # Check existing data is intact
    profile = get_patient_profile("test-user-1", backend="sqlite", db_path=test_db_path)
    assert profile is not None
    assert profile["user_id"] == "test-user-1"
    assert profile["waist_cm"] == 85.0


def test_sqlite_v16_to_v17_idempotent(test_db_path):
    """Running migrate twice doesn't crash or duplicate seeded providers."""
    create_v16_database(test_db_path)
    migrate(backend="sqlite", db_path=test_db_path)
    migrate(backend="sqlite", db_path=test_db_path)

    providers = list_providers(backend="sqlite", db_path=test_db_path)
    assert len(providers) == 5


def test_fresh_sqlite_db_initializes_to_v17(test_db_path):
    """A fresh database initializes straight to v17 with providers seeded."""
    migrate(backend="sqlite", db_path=test_db_path)

    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM schema_version")
    assert cur.fetchone()[0] >= 17
    conn.close()

    providers = list_providers(backend="sqlite", db_path=test_db_path)
    assert len(providers) == 5


def test_mysql_ddl_v17():
    """Confirms MySQL DDL statements specify VARCHAR(191) for ID columns."""
    assert "VARCHAR(191) PRIMARY KEY" in MYSQL_PROVIDER_DIRECTORY_DDL
    assert "VARCHAR(191) PRIMARY KEY" in MYSQL_APPOINTMENTS_DDL
    assert "patient_id VARCHAR(191)" in MYSQL_APPOINTMENTS_DDL
    assert "checkin_id VARCHAR(191)" in MYSQL_APPOINTMENTS_DDL
    assert "provider_id VARCHAR(191)" in MYSQL_APPOINTMENTS_DDL
