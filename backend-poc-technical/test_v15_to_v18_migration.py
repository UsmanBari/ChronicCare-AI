"""
Unit and integration test: upgrades a v15-shaped fake SQLite database to v18.
Verifies that:
1. Migrations 16, 17, and 18 apply cleanly.
2. Existing data in users, profiles, checkins, etc. is 100% preserved.
3. Appointments, notifications, and provider_directory tables are created.
4. Schema version reaches 18.
"""

import os
import sqlite3
import tempfile
import pytest

from data_sources import app_store


@pytest.fixture
def fake_v15_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create v15 schema_version table
    cur.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 16):
        cur.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, '2026-11-01T00:00:00Z')", (v,))

    # Create core v15 tables with test rows
    cur.execute("""
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'patient',
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("INSERT INTO users VALUES ('u-v15-01', 'patient15@demo.care', 'patient', '2026-11-01T00:00:00Z')")

    cur.execute("""
        CREATE TABLE patient_profiles (
            user_id TEXT PRIMARY KEY,
            conditions_json TEXT NOT NULL DEFAULT '[]',
            on_insulin_or_sulfonylurea INTEGER NOT NULL DEFAULT 0,
            waist_cm REAL
        )
    """)
    cur.execute("INSERT INTO patient_profiles VALUES ('u-v15-01', '[\"hypertension\"]', 0, 84.5)")

    cur.execute("""
        CREATE TABLE checkins (
            checkin_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'isolated',
            version INTEGER NOT NULL DEFAULT 0,
            answers_json TEXT NOT NULL DEFAULT '{}'
        )
    """)
    cur.execute("INSERT INTO checkins VALUES ('chk-v15-01', 'u-v15-01', '2026-11-01T12:00:00Z', 'complete', 'isolated', 1, '{}')")

    cur.execute("""
        CREATE TABLE checkin_results (
            checkin_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            triage_level TEXT NOT NULL,
            risk_json TEXT,
            explanation_json TEXT,
            trace_json TEXT
        )
    """)
    cur.execute("INSERT INTO checkin_results VALUES ('chk-v15-01', 'u-v15-01', '2026-11-01T12:01:00Z', 'review', '{}', '{}', '{}')")

    conn.commit()
    conn.close()

    yield db_path

    if os.path.exists(db_path):
        os.unlink(db_path)


def test_v15_to_v18_upgrade_preserves_data(fake_v15_db):
    """Proves that a v15 SQLite database upgrades cleanly to v18 and keeps all existing data."""
    # Run the application migration
    app_store.migrate(backend="sqlite", db_path=fake_v15_db)

    conn = sqlite3.connect(fake_v15_db)
    cur = conn.cursor()

    # 1. Schema version must reach 18
    cur.execute("SELECT MAX(version), COUNT(*) FROM schema_version")
    max_ver, count_ver = cur.fetchone()
    assert max_ver == 18
    assert count_ver == 18

    # 2. Existing data must be preserved
    cur.execute("SELECT email, role FROM users WHERE user_id = 'u-v15-01'")
    u_row = cur.fetchone()
    assert u_row == ("patient15@demo.care", "patient")

    cur.execute("SELECT conditions_json, waist_cm FROM patient_profiles WHERE user_id = 'u-v15-01'")
    p_row = cur.fetchone()
    assert p_row == ('["hypertension"]', 84.5)

    cur.execute("SELECT status FROM checkins WHERE checkin_id = 'chk-v15-01'")
    assert cur.fetchone()[0] == "complete"

    cur.execute("SELECT triage_level FROM checkin_results WHERE checkin_id = 'chk-v15-01'")
    assert cur.fetchone()[0] == "review"

    # 3. New v17 tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('appointments', 'provider_directory')")
    v17_tables = {r[0] for r in cur.fetchall()}
    assert "appointments" in v17_tables
    assert "provider_directory" in v17_tables

    # 4. Provider directory is seeded with synthetic providers
    cur.execute("SELECT COUNT(*) FROM provider_directory")
    provider_count = cur.fetchone()[0]
    assert provider_count >= 5

    # 5. New v18 tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('notifications', 'fcm_tokens')")
    v18_tables = {r[0] for r in cur.fetchall()}
    assert "notifications" in v18_tables
    assert "fcm_tokens" in v18_tables

    conn.close()

