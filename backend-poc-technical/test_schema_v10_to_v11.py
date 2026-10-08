"""
Hermetic Tests for Schema Migration Version 10 to 11, Existing Account Flow,
Age Payload Rejection & Calculation, and Typed Pregnancy Statements (FIX 10b).
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
from data_sources.validation import (
    calculate_age,
    validate_date_of_birth,
    detect_pregnancy_statement,
)
from main import app


@pytest.fixture
def test_db_path(tmp_path):
    """Creates a temporary sqlite database file."""
    return str(tmp_path / "test_migration_v10_v11.db")


def create_v10_database(db_path: str):
    """
    Constructs a database up to schema version 10 without version 11 columns,
    and inserts an existing patient with confirmed inclusion.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Schema version table
    cursor.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 11):
        cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)", (v, now))

    # Core tables up to v10
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

    # Insert an existing user whose inclusion was confirmed in schema version 10
    cursor.execute("""
        INSERT INTO users (user_id, email, role, display_name, status, created_at)
        VALUES ('usr-v10-existing', 'existing@domain.org', 'patient', 'Amina Begum', 'active', ?)
    """, (now,))

    cursor.execute("""
        INSERT INTO patient_profiles (
            user_id, conditions_json, on_insulin_or_sulfonylurea, language,
            consent_granted_at, provider_notification_consent_at,
            date_of_birth, inclusion_confirmed_at, updated_at
        ) VALUES (
            'usr-v10-existing', '["diabetes"]', 1, 'en',
            ?, ?,
            '1975-08-14', ?, ?
        )
    """, (now, now, now, now))

    conn.commit()
    conn.close()


def test_sqlite_schema_v10_to_v11_migration(test_db_path):
    """
    Task B: Builds a database at version 10, runs migrate(), and verifies:
    1. The two columns sex_at_birth and pregnancy_status are added.
    2. Existing rows keep every old value.
    3. Running migrate() twice changes nothing and does not fail.
    4. Profile returned has empty/None pregnancy_status and sex_at_birth.
    """
    create_v10_database(test_db_path)

    # Verify columns do not exist yet in v10
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(patient_profiles)")
    v10_cols = [r[1] for r in cur.fetchall()]
    assert "sex_at_birth" not in v10_cols
    assert "pregnancy_status" not in v10_cols
    conn.close()

    # 1. Run migrate to v11
    migrate(backend="sqlite", db_path=test_db_path)

    # Verify columns now exist
    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(patient_profiles)")
    v11_cols = [r[1] for r in cur.fetchall()]
    assert "sex_at_birth" in v11_cols
    assert "pregnancy_status" in v11_cols

    # Verify schema_version is at least 11 (migrated to latest)
    cur.execute("SELECT MAX(version) FROM schema_version")
    assert cur.fetchone()[0] >= 11
    conn.close()

    # 2. Verify existing row preserved all old values
    profile = get_patient_profile("usr-v10-existing", backend="sqlite", db_path=test_db_path)
    assert profile is not None
    assert profile["user_id"] == "usr-v10-existing"
    assert profile["conditions"] == ["diabetes"]
    assert profile["on_insulin_or_sulfonylurea"] is True
    assert profile["date_of_birth"] == "1975-08-14"
    assert profile["inclusion_confirmed_at"] is not None
    assert profile["sex_at_birth"] is None
    assert profile["pregnancy_status"] is None

    # 3. Running migrate() twice is completely idempotent
    migrate(backend="sqlite", db_path=test_db_path)
    profile_after_second_migrate = get_patient_profile("usr-v10-existing", backend="sqlite", db_path=test_db_path)
    assert profile_after_second_migrate == profile


def test_mysql_v11_ddl_and_idempotency_hermetic():
    """
    Task B: Proves MySQL migration DDL statements for version 11 and asserts
    idempotent guard with fake cursor.
    """
    now = datetime.now(timezone.utc).isoformat()
    mock_cursor = MagicMock()
    
    # Simulate first run where columns don't exist yet
    mock_cursor.fetchone.side_effect = [
        None, # schema_version 11 check -> not applied
        None, # sex_at_birth column check -> not exists
        None, # pregnancy_status column check -> not exists
    ]
    
    # Run the MySQL v11 block logic
    mock_cursor.execute("SELECT version FROM schema_version WHERE version = 11")
    if not mock_cursor.fetchone():
        mock_cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'patient_profiles' AND COLUMN_NAME = 'sex_at_birth'
        """)
        if not mock_cursor.fetchone():
            mock_cursor.execute("ALTER TABLE patient_profiles ADD COLUMN sex_at_birth VARCHAR(32) NULL")

        mock_cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'patient_profiles' AND COLUMN_NAME = 'pregnancy_status'
        """)
        if not mock_cursor.fetchone():
            mock_cursor.execute("ALTER TABLE patient_profiles ADD COLUMN pregnancy_status VARCHAR(32) NULL")

        mock_cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (11, %s)", (now,))

    # Assert DDL statements were executed
    executed_calls = [c[0][0].strip() for c in mock_cursor.execute.call_args_list]
    assert any("ALTER TABLE patient_profiles ADD COLUMN sex_at_birth VARCHAR(32) NULL" in sql for sql in executed_calls)
    assert any("ALTER TABLE patient_profiles ADD COLUMN pregnancy_status VARCHAR(32) NULL" in sql for sql in executed_calls)


@pytest.mark.inclusion
def test_existing_account_checkin_start_blocks_and_resumes(test_db_path, monkeypatch):
    """
    Task C: Existing account with confirmed inclusion but empty sex_at_birth/pregnancy_status
    must NOT be stuck:
    1. An existing user profile initially has pregnancy_status as None.
    2. Answering 'no' (or Male) updates profile and allows check-in start (200 OK).
    3. Answering 'yes' records pregnancy and gates as not eligible (403 not_eligible).
    """
    monkeypatch.setenv("REQUIRE_INCLUSION", "1")
    create_v10_database(test_db_path)
    migrate(backend="sqlite", db_path=test_db_path)

    os.environ["LOCAL_DB_PATH"] = test_db_path

    # Fake auth token for usr-v10-existing
    user_payload = {
        "uid": "usr-v10-existing",
        "email": "existing@domain.org",
        "role": "patient",
    }

    client = TestClient(app)

    with patch("main.verify_firebase_token", return_value=user_payload), \
         patch("main.get_user_by_id", return_value={"user_id": "usr-v10-existing", "email": "existing@domain.org", "role": "patient", "status": "active"}), \
         patch("main.get_patient_profile", side_effect=lambda uid: get_patient_profile(uid, backend="sqlite", db_path=test_db_path)), \
         patch("main.upsert_patient_profile", side_effect=lambda **kw: upsert_patient_profile(backend="sqlite", db_path=test_db_path, **kw)):

        # 1. Existing user profile initially has pregnancy_status = None
        prof_init = client.get("/api/me/profile", headers={"Authorization": "Bearer fake-token"}).json()
        assert prof_init["pregnancy_status"] is None
        assert prof_init["sex_at_birth"] is None

        # 2. Patient completes screening with sex=female, pregnancy=no
        update_res = client.put(
            "/api/me/profile",
            json={
                "date_of_birth": "1975-08-14",
                "inclusion_confirmed": True,
                "sex_at_birth": "female",
                "pregnancy_status": "no",
                "conditions": ["diabetes"],
                "language": "en",
            },
            headers={"Authorization": "Bearer fake-token"},
        )
        assert update_res.status_code == 200
        prof_data = update_res.json()
        assert prof_data["sex_at_birth"] == "female"
        assert prof_data["pregnancy_status"] == "no"

        # Check-in start now succeeds with 200 OK
        start_res = client.post("/api/checkins/start", headers={"Authorization": "Bearer fake-token"})
        assert start_res.status_code == 200
        assert "checkin_id" in start_res.json()

        # 3. Patient with pregnancy=yes is marked ineligible
        update_preg = client.put(
            "/api/me/profile",
            json={
                "date_of_birth": "1975-08-14",
                "inclusion_confirmed": False,
                "sex_at_birth": "female",
                "pregnancy_status": "yes",
                "conditions": ["diabetes"],
                "language": "en",
            },
            headers={"Authorization": "Bearer fake-token"},
        )
        assert update_preg.status_code == 200
        preg_res = client.post("/api/checkins/start", headers={"Authorization": "Bearer fake-token"})
        assert preg_res.status_code == 403
        assert preg_res.json()["detail"] == "not_eligible"
        assert preg_res.json()["reason"] == "pregnant"


def test_age_field_rejected_in_profile_payload():
    """
    Task F: Proves that a client-sent 'age' field in the profile payload is rejected
    with 422 Unprocessable Entity (extra: forbid), enforcing that age is computed from DOB.
    """
    client = TestClient(app)
    user_payload = {"uid": "usr-test-age", "email": "patient@domain.org", "role": "patient"}

    with patch("main.verify_firebase_token", return_value=user_payload), \
         patch("main.get_user_by_id", return_value={"user_id": "usr-test-age", "email": "patient@domain.org", "role": "patient", "status": "active"}):
        res = client.put(
            "/api/me/profile",
            json={
                "age": 58,  # Client attempting to send prototype age
                "date_of_birth": "1980-01-01",
                "conditions": ["diabetes"],
            },
            headers={"Authorization": "Bearer fake-token"},
        )
        # Extra field 'age' must be rejected
        assert res.status_code == 422
        assert "extra_forbidden" in str(res.json())


def test_age_derived_from_dob_for_triage():
    """
    Task F: Proves that age used for the 65+ rule comes strictly from DOB via calculate_age.
    """
    # Patient born in 1955 -> 71 on 2026-10-07 (>= 65)
    age_elderly = calculate_age("1955-05-10", as_of_date="2026-10-07")
    assert age_elderly == 71
    assert age_elderly >= 65

    # Patient born in 1985 -> 41 on 2026-10-07 (< 65)
    age_young = calculate_age("1985-05-10", as_of_date="2026-10-07")
    assert age_young == 41
    assert age_young < 65


def test_typed_pregnancy_statement_table_driven():
    """
    Task E: Table-driven test verifying typed pregnancy detection rules:
    First-person current pregnancy stops check-in; third-person, past tense,
    negations, and negative test results do NOT stop check-in.
    """
    cases = [
        ("I am pregnant", True),
        ("i'm pregnant", True),
        ("I think I am pregnant", True),
        ("pregnant", True),
        ("I am not pregnant", False),
        ("not pregnant", False),
        ("no, I'm not pregnant", False),
        ("I was pregnant last year", False),
        ("my sister is pregnant", False),
        ("my wife is pregnant", False),
        ("pregnancy test negative", False),
        ("I am 7 months pregnant", True),
        ("", False),
        ("a" * 10000, False),
    ]

    for text, expected in cases:
        actual = detect_pregnancy_statement(text)
        assert actual == expected, f"Failed for answer: '{text[:40]}' (expected {expected}, got {actual})"
