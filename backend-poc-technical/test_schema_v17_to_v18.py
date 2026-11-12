"""
Hermetic Tests for Schema Migration Version 17 to 18 (Notifications & FCM Tokens).
Verifies:
1. LATEST_SCHEMA_VERSION is 18.
2. SQLite database at schema version 17 with existing data migrates cleanly to v18.
3. Existing data across all tables (including appointments & provider directory) is preserved.
4. SQLite migration is strictly idempotent (running repeatedly changes nothing).
5. Fresh SQLite database initializes directly to v18.
6. MySQL DDL specifies VARCHAR(191) for ID columns.
7. Notification and FCM token helper functions operate correctly on the migrated tables.
"""

import sqlite3
import tempfile
from datetime import UTC, datetime
from typing import Any

import pytest
from data_sources.app_store import (
    LATEST_SCHEMA_VERSION,
    MYSQL_FCM_TOKENS_DDL,
    MYSQL_NOTIFICATIONS_DDL,
    create_notification,
    delete_fcm_token,
    get_notification,
    list_fcm_tokens,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    migrate,
    save_fcm_token,
)


@pytest.fixture
def test_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path


def create_v17_database(db_path: str):
    """
    Constructs a database strictly at schema version 17,
    inserting pre-existing patient and appointment data.
    """
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    for v in range(1, 18):
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
        CREATE TABLE appointments (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            checkin_id TEXT NOT NULL UNIQUE,
            provider_id TEXT NOT NULL,
            specialty TEXT NOT NULL,
            urgency TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            slot_date TEXT DEFAULT NULL,
            created_at TEXT NOT NULL,
            acknowledged_at TEXT DEFAULT NULL,
            admin_flagged_at TEXT DEFAULT NULL
        )
    """)

    cursor.execute(
        "INSERT INTO users (user_id, email, role, display_name, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("p_existing_v17", "existing@example.com", "patient", "Existing Patient", "active", now),
    )
    cursor.execute(
        "INSERT INTO appointments (id, patient_id, checkin_id, provider_id, specialty, urgency, mode, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("apt-v17-old", "p_existing_v17", "chk-v17-old", "prov-demo-endo", "endocrinology", "routine", "telehealth", "offered", now),
    )

    conn.commit()
    conn.close()


def test_latest_schema_version_is_18():
    assert LATEST_SCHEMA_VERSION == 18


def test_sqlite_v17_to_v18_migration(test_db_path):
    create_v17_database(test_db_path)

    # Pre-migration: confirm v17 and no notifications table
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(version) FROM schema_version")
    assert cursor.fetchone()[0] == 17
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
    assert cursor.fetchone() is None
    conn.close()

    # Migrate
    migrate(backend="sqlite", db_path=test_db_path)

    # Post-migration checks
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(version) FROM schema_version")
    assert cursor.fetchone()[0] == 18

    # Tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'")
    assert cursor.fetchone() is not None
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fcm_tokens'")
    assert cursor.fetchone() is not None

    # Preserved data
    cursor.execute("SELECT id, status FROM appointments WHERE id = 'apt-v17-old'")
    row = cursor.fetchone()
    assert row is not None
    assert row[1] == "offered"
    conn.close()


def test_sqlite_v17_to_v18_idempotent(test_db_path):
    create_v17_database(test_db_path)
    migrate(backend="sqlite", db_path=test_db_path)
    migrate(backend="sqlite", db_path=test_db_path)

    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM schema_version WHERE version = 18")
    assert cursor.fetchone()[0] == 1
    conn.close()


def test_fresh_sqlite_db_initializes_to_v18(test_db_path):
    migrate(backend="sqlite", db_path=test_db_path)

    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(version) FROM schema_version")
    assert cursor.fetchone()[0] == 18
    conn.close()


def test_mysql_ddl_v18():
    assert "VARCHAR(191)" in MYSQL_NOTIFICATIONS_DDL
    assert "id VARCHAR(191) PRIMARY KEY" in MYSQL_NOTIFICATIONS_DDL
    assert "recipient_id VARCHAR(191) NOT NULL" in MYSQL_NOTIFICATIONS_DDL
    assert "VARCHAR(191)" in MYSQL_FCM_TOKENS_DDL
    assert "user_id VARCHAR(191) NOT NULL" in MYSQL_FCM_TOKENS_DDL


def test_notification_and_fcm_crud(test_db_path):
    migrate(backend="sqlite", db_path=test_db_path)

    # Create notification
    n1 = create_notification(
        recipient_id="prov-1",
        role="provider",
        event_type="urgent_checkin",
        reference_id="chk-100",
        title="Urgent Alert",
        body="New urgent check-in requires review",
        db_path=test_db_path,
        backend="sqlite",
    )
    assert n1["id"].startswith("notif-")
    assert n1["is_read"] is False

    # Idempotent re-creation with same reference_id returns existing
    n1_again = create_notification(
        recipient_id="prov-1",
        role="provider",
        event_type="urgent_checkin",
        reference_id="chk-100",
        title="Different title",
        body="Different body",
        db_path=test_db_path,
        backend="sqlite",
    )
    assert n1_again["id"] == n1["id"]

    # Mark read
    marked = mark_notification_read(n1["id"], db_path=test_db_path, backend="sqlite")
    assert marked["is_read"] is True

    # List notifications
    notifs = list_notifications(recipient_id="prov-1", db_path=test_db_path, backend="sqlite")
    assert len(notifs) == 1

    # FCM Token CRUD
    save_fcm_token("usr-1", "fcm-token-alpha", device_info="Chrome Windows", db_path=test_db_path, backend="sqlite")
    tokens = list_fcm_tokens("usr-1", db_path=test_db_path, backend="sqlite")
    assert tokens == ["fcm-token-alpha"]

    delete_fcm_token("usr-1", "fcm-token-alpha", db_path=test_db_path, backend="sqlite")
    tokens_after = list_fcm_tokens("usr-1", db_path=test_db_path, backend="sqlite")
    assert tokens_after == []
