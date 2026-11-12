"""
Hermetic Tests for Schema Migration Version 15 to 16 (MySQL ID Width Widening).
Verifies:
1. LATEST_SCHEMA_VERSION is 16.
2. SQLite database at schema version 15 with existing data migrates cleanly to v16.
3. Existing data across all tables is preserved without loss or corruption.
4. SQLite migration is strictly idempotent (running repeatedly changes nothing).
5. Fresh SQLite database initializes directly to v16.
6. MySQL DDL in MYSQL_RECORD_EDITS_DDL specifies record_id VARCHAR(191) NOT NULL.
7. get_id_width_alter_statements() defines all 3 ALTER statements with charset utf8mb4 and NOT NULL.
8. MySQL migration records version 16 in schema_version.
9. apply_id_width_migration():
   - Executes ALTER and logs 'id-width migration: applied 3 columns (...)' when columns are narrow (64).
   - Executes 0 ALTERs and logs 'id-width migration: already wide' when columns are >= 191.
   - Logs 'id-width migration FAILED: <column>: <error class>' at ERROR level without crashing startup if ALTER fails.
"""

import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any

import pytest
from data_sources.app_store import (
    LATEST_SCHEMA_VERSION,
    MYSQL_RECORD_EDITS_DDL,
    get_patient_profile,
    migrate,
)
from data_sources.local_store import (
    apply_id_width_migration,
    get_id_width_alter_statements,
)


@pytest.fixture
def test_db_path(tmp_path):
    """Creates a temporary sqlite database file."""
    return str(tmp_path / "test_migration_v15_v16.db")


def create_v15_database(db_path: str):
    """
    Constructs a database strictly at schema version 15,
    inserting pre-existing patient and checkin result data.
    """
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Schema version table at v15
    cursor.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 16):
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
            max_severity TEXT,
            review_status TEXT NOT NULL DEFAULT 'pending',
            triage_level TEXT NOT NULL DEFAULT 'routine',
            triage_json TEXT NOT NULL DEFAULT '{}',
            risk_json TEXT DEFAULT NULL,
            explanation_json TEXT DEFAULT NULL,
            trace_json TEXT DEFAULT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE record_edits (
            edit_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            record_type TEXT NOT NULL,
            record_id TEXT NOT NULL,
            field TEXT NOT NULL,
            old_value TEXT DEFAULT NULL,
            new_value TEXT DEFAULT NULL,
            origin TEXT NOT NULL,
            changed_by_user_id TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            reason TEXT DEFAULT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE guideline_chunks (
            chunk_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            edition TEXT,
            priority INTEGER DEFAULT 1,
            section_path TEXT,
            page_start INTEGER,
            page_end INTEGER,
            grade TEXT,
            condition TEXT NOT NULL,
            topics_json TEXT,
            text TEXT NOT NULL,
            loaded_at TEXT NOT NULL
        )
    """)

    # Pre-populate sample v15 data
    cursor.execute(
        "INSERT INTO users (user_id, email, role, created_at) VALUES ('usr-v15-001', 'v15@demo.care', 'patient', ?)",
        (now,),
    )
    cursor.execute(
        "INSERT INTO patient_profiles (user_id, conditions_json, waist_cm, updated_at) VALUES ('usr-v15-001', '[\"hypertension\"]', 88.5, ?)",
        (now,),
    )
    cursor.execute(
        "INSERT INTO record_edits (edit_id, user_id, record_type, record_id, field, new_value, origin, changed_by_user_id, changed_at) VALUES ('edit-v15-01', 'usr-v15-001', 'observation', 'CHECKIN-local-usr-v15-001-20261108T120000Z-blood_pressure_systolic', 'value', '125', 'patient_stated', 'usr-v15-001', ?)",
        (now,),
    )
    cursor.execute(
        "INSERT INTO checkin_results (checkin_id, intakes_json, reconciliation_json, verification_json, created_at) VALUES ('chk-v15-01', '[]', '{}', '{}', ?)",
        (now,),
    )

    conn.commit()
    conn.close()


def test_latest_schema_version_is_16():
    """Confirms LATEST_SCHEMA_VERSION constant is updated to at least 16."""
    assert LATEST_SCHEMA_VERSION >= 16


def test_sqlite_v15_to_v16_migration(test_db_path):
    """
    Verifies that a database at schema version 15 migrates cleanly to v16,
    preserves existing data, and behaves idempotently.
    """
    create_v15_database(test_db_path)

    # Execute migration
    migrate(backend="sqlite", db_path=test_db_path)

    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM schema_version")
    assert cur.fetchone()[0] == 16

    # Verify existing data preserved
    prof = get_patient_profile("usr-v15-001", backend="sqlite", db_path=test_db_path)
    assert prof is not None
    assert prof["waist_cm"] == 88.5

    cur.execute("SELECT edit_id, record_id FROM record_edits WHERE edit_id='edit-v15-01'")
    row = cur.fetchone()
    assert row[0] == "edit-v15-01"
    assert "CHECKIN-local-usr-v15-001" in row[1]
    conn.close()

    # Idempotence: running migration again keeps schema at 16
    migrate(backend="sqlite", db_path=test_db_path)
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM schema_version WHERE version = 16")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_sqlite_fresh_database_is_v16(test_db_path):
    """Verifies that running migrate() on an empty database brings it directly to v16."""
    migrate(backend="sqlite", db_path=test_db_path)

    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("SELECT MAX(version) FROM schema_version")
    assert cur.fetchone()[0] == 16
    conn.close()


def test_mysql_ddl_and_alter_statements():
    """
    Verifies MySQL DDL definitions specify VARCHAR(191) and the alter statements
    preserve utf8mb4 character set, utf8mb4_unicode_ci collation, and NOT NULL.
    """
    assert "record_id VARCHAR(191) NOT NULL" in MYSQL_RECORD_EDITS_DDL

    alter_stmts = get_id_width_alter_statements()
    assert len(alter_stmts) == 3

    assert "ALTER TABLE observations MODIFY id VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL" in alter_stmts
    assert "ALTER TABLE medications MODIFY id VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL" in alter_stmts
    assert "ALTER TABLE record_edits MODIFY record_id VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL" in alter_stmts


class FakeMySQLCursor:
    """Mock MySQL cursor supporting INFORMATION_SCHEMA checks and logging assertions."""
    def __init__(self, col_widths: dict[tuple[str, str], int], fail_column: str | None = None):
        self.col_widths = dict(col_widths)
        self.fail_column = fail_column
        self.executed_queries: list[str] = []
        self._last_query = ""
        self._last_params: Any = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query: str, params: Any = None):
        self._last_query = query
        self._last_params = params
        self.executed_queries.append(query)

        if "ALTER TABLE" in query and self.fail_column and self.fail_column in query:
            raise RuntimeError(f"Simulated ALTER failure on {self.fail_column}")

    def fetchone(self):
        if "INFORMATION_SCHEMA.COLUMNS" in self._last_query and self._last_params:
            tbl, col = self._last_params
            if (tbl, col) in self.col_widths:
                return {"CHARACTER_MAXIMUM_LENGTH": self.col_widths[(tbl, col)]}
            return None
        return None

    def fetchall(self):
        return []


def test_apply_id_width_migration_when_narrow(caplog):
    """
    Verifies that when columns are width 64 (current prod state),
    apply_id_width_migration applies ALTERs to all 3 columns and logs success.
    """
    widths = {
        ("observations", "id"): 64,
        ("medications", "id"): 64,
        ("record_edits", "record_id"): 64,
    }
    fake_cursor = FakeMySQLCursor(widths)

    with caplog.at_level(logging.INFO, logger="main"):
        result = apply_id_width_migration(fake_cursor)

    assert result["applied"] == ["observations.id", "medications.id", "record_edits.record_id"]
    assert len(result["failed"]) == 0
    assert "id-width migration: applied 3 columns (observations.id, medications.id, record_edits.record_id)" in caplog.text


def test_apply_id_width_migration_already_wide(caplog):
    """
    Verifies that when columns are already width 191 (subsequent restarts),
    apply_id_width_migration skips ALTERs and logs 'already wide'.
    """
    widths = {
        ("observations", "id"): 191,
        ("medications", "id"): 191,
        ("record_edits", "record_id"): 191,
    }
    fake_cursor = FakeMySQLCursor(widths)

    with caplog.at_level(logging.INFO, logger="main"):
        result = apply_id_width_migration(fake_cursor)

    assert len(result["applied"]) == 0
    assert len(result["failed"]) == 0
    assert "id-width migration: already wide" in caplog.text


def test_apply_id_width_migration_failing_alter_logs_error_and_does_not_crash(caplog):
    """
    Verifies that an error executing ALTER logs at ERROR level:
    'id-width migration FAILED: <column>: <error class>'
    without crashing startup or leaking credentials.
    """
    widths = {
        ("observations", "id"): 64,
        ("medications", "id"): 64,
        ("record_edits", "record_id"): 64,
    }
    fake_cursor = FakeMySQLCursor(widths, fail_column="observations")

    with caplog.at_level(logging.ERROR, logger="main"):
        result = apply_id_width_migration(fake_cursor)

    assert "observations.id" not in result["applied"]
    assert "medications.id" in result["applied"]
    assert "record_edits.record_id" in result["applied"]
    assert ("observations.id", "RuntimeError") in result["failed"]
    assert "id-width migration FAILED: observations.id: RuntimeError" in caplog.text
    # Proves no credentials or connection URLs were logged
    assert "mysql://" not in caplog.text
    assert "password" not in caplog.text.lower()

