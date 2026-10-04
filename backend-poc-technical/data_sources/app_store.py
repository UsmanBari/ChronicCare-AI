"""
Application Data Store for Users, Roles, and Append-Only Audit Log.

Supports dual SQLite (default) and MySQL backends with idempotent migrations.
Guarantees:
- Parameterized queries only.
- Strict append-only audit log (no update or delete functions exist for audit rows).
- UTC ISO 8601 timestamps.
- Zero PHI or credential storage in audit records.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

from data_sources.db_config import (
    get_db_backend,
    get_sqlite_path,
    get_mysql_connection_params,
)

# Optional PyMySQL import
try:
    import pymysql
    import pymysql.cursors
except ImportError:
    pymysql = None


VALID_ROLES = ("patient", "provider", "admin")
VALID_STATUSES = ("active", "disabled")
VALID_OUTCOMES = ("ok", "denied", "error")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def get_db_cursor(backend: Optional[str] = None, db_path: Optional[str] = None,
                  mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None):
    """
    Context manager that yields a cursor and manages connection commits/closes.
    Yields (cursor, backend_name, param_placeholder).
    """
    selected_backend = (backend or get_db_backend()).lower()

    if selected_backend == "mysql":
        if pymysql is None:
            raise RuntimeError("PyMySQL is not installed. Please install PyMySQL>=1.1.0.")
        params = get_mysql_connection_params(mysql_url=mysql_url, ssl_ca=ssl_ca)
        params["cursorclass"] = pymysql.cursors.DictCursor
        conn = pymysql.connect(**params)
        try:
            with conn.cursor() as cursor:
                yield cursor, "mysql", "%s"
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        path = get_sqlite_path(db_path)
        db_dir = os.path.dirname(path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            yield cursor, "sqlite", "?"
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def migrate(backend: Optional[str] = None, db_path: Optional[str] = None,
            mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> None:
    """
    Idempotent schema migration for Users, Roles, Audit Log, Patient Profiles,
    EHR Systems, EHR Connections, Check-ins, and Review tables.
    Safe to run repeatedly.
    """
    now = _utc_now_iso()
    default_fhir_url = (os.environ.get("FHIR_BASE_URL") or "https://r4.smarthealthit.org").strip()

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        if be == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            cursor.execute("SELECT version FROM schema_version WHERE version = 1")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
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
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts TEXT NOT NULL,
                        actor_user_id TEXT,
                        action TEXT NOT NULL,
                        target TEXT,
                        outcome TEXT NOT NULL CHECK(outcome IN ('ok','denied','error')),
                        detail_json TEXT NOT NULL
                    )
                """)
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, ?)", (now,))

            cursor.execute("SELECT version FROM schema_version WHERE version = 2")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS patient_profiles (
                        user_id TEXT PRIMARY KEY,
                        conditions_json TEXT NOT NULL DEFAULT '[]',
                        on_insulin_or_sulfonylurea INTEGER NOT NULL DEFAULT 0,
                        language TEXT NOT NULL DEFAULT 'en',
                        consent_granted_at TEXT,
                        consent_revoked_at TEXT,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(user_id)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ehr_systems (
                        ehr_system_id TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        fhir_base_url TEXT NOT NULL,
                        enabled INTEGER NOT NULL DEFAULT 1
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ehr_connections (
                        connection_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        ehr_system_id TEXT NOT NULL,
                        external_patient_id TEXT NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('active','failed','revoked')),
                        linked_at TEXT NOT NULL,
                        last_verified_at TEXT,
                        last_error_code TEXT,
                        revoked_at TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(user_id),
                        FOREIGN KEY(ehr_system_id) REFERENCES ehr_systems(ehr_system_id)
                    )
                """)
                cursor.execute("""
                    INSERT OR IGNORE INTO ehr_systems (ehr_system_id, display_name, fhir_base_url, enabled)
                    VALUES (?, ?, ?, 1)
                """, ("smart-sandbox", "SMART Health IT Sandbox", default_fhir_url))
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (2, ?)", (now,))

            cursor.execute("SELECT version FROM schema_version WHERE version = 3")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checkins (
                        checkin_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        mode TEXT NOT NULL CHECK(mode IN ('connected','isolated')),
                        record_patient_id TEXT NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('in_progress','complete','emergency','abandoned')),
                        state_json TEXT NOT NULL,
                        version INTEGER NOT NULL DEFAULT 0,
                        started_at TEXT NOT NULL,
                        completed_at TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(user_id)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checkin_results (
                        checkin_id TEXT PRIMARY KEY,
                        emergency INTEGER NOT NULL,
                        intakes_json TEXT NOT NULL,
                        reconciliation_json TEXT,
                        verification_json TEXT,
                        requires_review INTEGER NOT NULL,
                        max_severity TEXT CHECK(max_severity IN ('none','low','moderate','high') OR max_severity IS NULL),
                        review_status TEXT NOT NULL CHECK(review_status IN ('open','acknowledged','resolved','escalated')),
                        trigger_category TEXT,
                        trigger_text TEXT,
                        escalated_at TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(checkin_id) REFERENCES checkins(checkin_id)
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS review_actions (
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
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (3, ?)", (now,))

            cursor.execute("SELECT version FROM schema_version WHERE version = 4")
            if not cursor.fetchone():
                cursor.execute("PRAGMA table_info(checkins)")
                c_cols = [row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in cursor.fetchall()]
                if "version" not in c_cols:
                    cursor.execute("ALTER TABLE checkins ADD COLUMN version INTEGER NOT NULL DEFAULT 0")

                cursor.execute("PRAGMA table_info(checkin_results)")
                cr_cols = [row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in cursor.fetchall()]
                if "trigger_category" not in cr_cols:
                    cursor.execute("ALTER TABLE checkin_results ADD COLUMN trigger_category TEXT")
                if "trigger_text" not in cr_cols:
                    cursor.execute("ALTER TABLE checkin_results ADD COLUMN trigger_text TEXT")
                if "escalated_at" not in cr_cols:
                    cursor.execute("ALTER TABLE checkin_results ADD COLUMN escalated_at TEXT")

                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (4, ?)", (now,))
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INT PRIMARY KEY,
                    applied_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            cursor.execute("SELECT version FROM schema_version WHERE version = 1")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id VARCHAR(128) PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        role VARCHAR(32) NOT NULL,
                        display_name VARCHAR(255),
                        status VARCHAR(32) NOT NULL DEFAULT 'active',
                        created_at VARCHAR(64) NOT NULL,
                        last_login_at VARCHAR(64)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        ts VARCHAR(64) NOT NULL,
                        actor_user_id VARCHAR(128),
                        action VARCHAR(64) NOT NULL,
                        target VARCHAR(128),
                        outcome VARCHAR(16) NOT NULL,
                        detail_json TEXT NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, %s)", (now,))

            cursor.execute("SELECT version FROM schema_version WHERE version = 2")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS patient_profiles (
                        user_id VARCHAR(128) PRIMARY KEY,
                        conditions_json TEXT NOT NULL,
                        on_insulin_or_sulfonylurea TINYINT(1) NOT NULL DEFAULT 0,
                        language VARCHAR(8) NOT NULL DEFAULT 'en',
                        consent_granted_at VARCHAR(64),
                        consent_revoked_at VARCHAR(64),
                        updated_at VARCHAR(64) NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ehr_systems (
                        ehr_system_id VARCHAR(64) PRIMARY KEY,
                        display_name VARCHAR(128) NOT NULL,
                        fhir_base_url VARCHAR(255) NOT NULL,
                        enabled TINYINT(1) NOT NULL DEFAULT 1
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ehr_connections (
                        connection_id VARCHAR(64) PRIMARY KEY,
                        user_id VARCHAR(128) NOT NULL,
                        ehr_system_id VARCHAR(64) NOT NULL,
                        external_patient_id VARCHAR(128) NOT NULL,
                        status VARCHAR(32) NOT NULL,
                        linked_at VARCHAR(64) NOT NULL,
                        last_verified_at VARCHAR(64),
                        last_error_code VARCHAR(64),
                        revoked_at VARCHAR(64),
                        INDEX idx_user_status (user_id, status),
                        INDEX idx_ehr_ext_status (ehr_system_id, external_patient_id, status),
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY (ehr_system_id) REFERENCES ehr_systems(ehr_system_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("""
                    INSERT INTO ehr_systems (ehr_system_id, display_name, fhir_base_url, enabled)
                    VALUES (%s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE display_name = VALUES(display_name)
                """, ("smart-sandbox", "SMART Health IT Sandbox", default_fhir_url))
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (2, %s)", (now,))

            cursor.execute("SELECT version FROM schema_version WHERE version = 3")
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checkins (
                        checkin_id VARCHAR(64) PRIMARY KEY,
                        user_id VARCHAR(128) NOT NULL,
                        mode VARCHAR(32) NOT NULL,
                        record_patient_id VARCHAR(128) NOT NULL,
                        status VARCHAR(32) NOT NULL,
                        state_json MEDIUMTEXT NOT NULL,
                        version INT NOT NULL DEFAULT 0,
                        started_at VARCHAR(64) NOT NULL,
                        completed_at VARCHAR(64),
                        INDEX idx_user_checkin (user_id, status),
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checkin_results (
                        checkin_id VARCHAR(64) PRIMARY KEY,
                        emergency TINYINT(1) NOT NULL,
                        intakes_json MEDIUMTEXT NOT NULL,
                        reconciliation_json MEDIUMTEXT,
                        verification_json MEDIUMTEXT,
                        requires_review TINYINT(1) NOT NULL,
                        max_severity VARCHAR(16),
                        review_status VARCHAR(32) NOT NULL,
                        trigger_category VARCHAR(64),
                        trigger_text VARCHAR(500),
                        escalated_at VARCHAR(64),
                        created_at VARCHAR(64) NOT NULL,
                        INDEX idx_review_status (review_status),
                        FOREIGN KEY (checkin_id) REFERENCES checkins(checkin_id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS review_actions (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        checkin_id VARCHAR(64) NOT NULL,
                        provider_user_id VARCHAR(128) NOT NULL,
                        action VARCHAR(32) NOT NULL,
                        note VARCHAR(500),
                        ts VARCHAR(64) NOT NULL,
                        INDEX idx_checkin_act (checkin_id),
                        FOREIGN KEY (checkin_id) REFERENCES checkins(checkin_id) ON DELETE CASCADE,
                        FOREIGN KEY (provider_user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (3, %s)", (now,))

            cursor.execute("SELECT version FROM schema_version WHERE version = 4")
            if not cursor.fetchone():
                cursor.execute("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'checkins' AND COLUMN_NAME = 'version'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE checkins ADD COLUMN version INT NOT NULL DEFAULT 0")

                cursor.execute("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'checkin_results' AND COLUMN_NAME = 'trigger_category'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE checkin_results ADD COLUMN trigger_category VARCHAR(64) NULL")

                cursor.execute("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'checkin_results' AND COLUMN_NAME = 'trigger_text'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE checkin_results ADD COLUMN trigger_text VARCHAR(500) NULL")

                cursor.execute("""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'checkin_results' AND COLUMN_NAME = 'escalated_at'
                """)
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE checkin_results ADD COLUMN escalated_at VARCHAR(64) NULL")

                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (4, %s)", (now,))


def get_user_by_id(user_id: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                   mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a user row by user_id."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(f"SELECT user_id, email, role, display_name, status, created_at, last_login_at FROM users WHERE user_id = {ph}", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                      mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a user row by lowercase email."""
    clean_email = (email or "").strip().lower()
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(f"SELECT user_id, email, role, display_name, status, created_at, last_login_at FROM users WHERE email = {ph}", (clean_email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_user(user_id: str, email: str, role: str, display_name: Optional[str] = None,
                status: str = "active", backend: Optional[str] = None, db_path: Optional[str] = None,
                mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new user row, or returns existing user if already registered concurrently."""
    clean_id = str(user_id).strip()
    clean_email = str(email).strip().lower()
    clean_role = str(role).strip().lower()
    clean_status = str(status).strip().lower()

    if not clean_id:
        raise ValueError("user_id cannot be empty.")
    if not clean_email:
        raise ValueError("email cannot be empty.")
    if clean_role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{clean_role}'. Must be one of {VALID_ROLES}.")
    if clean_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{clean_status}'. Must be one of {VALID_STATUSES}.")

    now = _utc_now_iso()
    try:
        with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
            cursor.execute(
                f"INSERT INTO users (user_id, email, role, display_name, status, created_at, last_login_at) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (clean_id, clean_email, clean_role, display_name, clean_status, now, now)
            )
        return {
            "user_id": clean_id,
            "email": clean_email,
            "role": clean_role,
            "display_name": display_name,
            "status": clean_status,
            "created_at": now,
            "last_login_at": now,
            "_is_new": True,
        }
    except Exception as e:
        is_unique_violation = False
        if isinstance(e, sqlite3.IntegrityError):
            is_unique_violation = True
        elif pymysql and isinstance(e, pymysql.MySQLError) and len(e.args) > 0 and e.args[0] == 1062:
            is_unique_violation = True
        elif "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
            is_unique_violation = True

        if is_unique_violation:
            existing = get_user_by_id(clean_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)
            if not existing:
                existing = get_user_by_email(clean_email, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)
            if existing:
                existing["_is_new"] = False
                return existing
        raise


def update_user_role(user_id: str, role: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                     mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Updates a user's role."""
    clean_role = str(role).strip().lower()
    if clean_role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{clean_role}'. Must be one of {VALID_ROLES}.")

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(f"UPDATE users SET role = {ph} WHERE user_id = {ph}", (clean_role, user_id))
    return get_user_by_id(user_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)


def update_user_last_login(user_id: str, timestamp: Optional[str] = None, backend: Optional[str] = None,
                           db_path: Optional[str] = None, mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Updates last_login_at timestamp for a user."""
    ts = timestamp or _utc_now_iso()
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(f"UPDATE users SET last_login_at = {ph} WHERE user_id = {ph}", (ts, user_id))
    return get_user_by_id(user_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)


def append_audit(actor_user_id: Optional[str], action: str, target: Optional[str] = None,
                 outcome: str = "ok", detail: Optional[Dict[str, Any]] = None,
                 backend: Optional[str] = None, db_path: Optional[str] = None,
                 mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> int:
    """
    Appends an immutable audit log record.
    Detail JSON must never contain tokens, credentials, or PHI.
    """
    clean_action = str(action).strip()
    clean_outcome = str(outcome).strip().lower()
    if clean_outcome not in VALID_OUTCOMES:
        clean_outcome = "error"

    now = _utc_now_iso()
    detail_str = json.dumps(detail or {}, separators=(",", ":"))

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"INSERT INTO audit_log (ts, actor_user_id, action, target, outcome, detail_json) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            (now, actor_user_id, clean_action, target, clean_outcome, detail_str)
        )
        return cursor.lastrowid or 0


def get_audit_logs(limit: int = 50, backend: Optional[str] = None, db_path: Optional[str] = None,
                   mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves newest audit log records up to limit (clamped between 1 and 200).
    """
    clamped_limit = max(1, min(limit, 200))
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"SELECT id, ts, actor_user_id, action, target, outcome, detail_json FROM audit_log ORDER BY id DESC LIMIT {ph}",
            (clamped_limit,)
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["detail"] = json.loads(d.pop("detail_json", "{}"))
            except Exception:
                d["detail"] = {}
            result.append(d)
        return result


# =============================================================================
# PATIENT PROFILE & CONSENT HELPERS
# =============================================================================

ALLOWED_CONDITIONS = {"diabetes", "hypertension"}
ALLOWED_LANGUAGES = {"en", "ur"}


def get_patient_profile(user_id: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                        mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves patient profile row if present."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"""
            SELECT user_id, conditions_json, on_insulin_or_sulfonylurea, language,
                   consent_granted_at, consent_revoked_at, updated_at
            FROM patient_profiles
            WHERE user_id = {ph}
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["conditions"] = json.loads(d.pop("conditions_json", "[]"))
        except Exception:
            d["conditions"] = []
        d["on_insulin_or_sulfonylurea"] = bool(d["on_insulin_or_sulfonylurea"])
        return d


def upsert_patient_profile(user_id: str, conditions: List[str], on_insulin_or_sulfonylurea: bool,
                           language: str = "en", backend: Optional[str] = None, db_path: Optional[str] = None,
                           mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Dict[str, Any]:
    """Upserts conditions, medication flag, and language for a patient."""
    clean_conditions = [str(c).strip().lower() for c in conditions]
    clean_lang = str(language).strip().lower()
    if clean_lang not in ALLOWED_LANGUAGES:
        clean_lang = "en"
    cond_json = json.dumps(clean_conditions)
    insulin_val = 1 if on_insulin_or_sulfonylurea else 0
    now = _utc_now_iso()

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        if be == "sqlite":
            cursor.execute(
                f"""
                INSERT INTO patient_profiles (user_id, conditions_json, on_insulin_or_sulfonylurea, language, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                ON CONFLICT(user_id) DO UPDATE SET
                    conditions_json = excluded.conditions_json,
                    on_insulin_or_sulfonylurea = excluded.on_insulin_or_sulfonylurea,
                    language = excluded.language,
                    updated_at = excluded.updated_at
                """,
                (user_id, cond_json, insulin_val, clean_lang, now)
            )
        else:
            cursor.execute(
                f"""
                INSERT INTO patient_profiles (user_id, conditions_json, on_insulin_or_sulfonylurea, language, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                ON DUPLICATE KEY UPDATE
                    conditions_json = VALUES(conditions_json),
                    on_insulin_or_sulfonylurea = VALUES(on_insulin_or_sulfonylurea),
                    language = VALUES(language),
                    updated_at = VALUES(updated_at)
                """,
                (user_id, cond_json, insulin_val, clean_lang, now)
            )
    return get_patient_profile(user_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)


def set_patient_consent(user_id: str, granted: bool, backend: Optional[str] = None, db_path: Optional[str] = None,
                        mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Dict[str, Any]:
    """Records explicit consent grant or revocation."""
    now = _utc_now_iso()
    existing = get_patient_profile(user_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        if not existing:
            cond_json = json.dumps([])
            if granted:
                cursor.execute(
                    f"""
                    INSERT INTO patient_profiles (user_id, conditions_json, on_insulin_or_sulfonylurea, language, consent_granted_at, consent_revoked_at, updated_at)
                    VALUES ({ph}, {ph}, 0, 'en', {ph}, NULL, {ph})
                    """,
                    (user_id, cond_json, now, now)
                )
            else:
                cursor.execute(
                    f"""
                    INSERT INTO patient_profiles (user_id, conditions_json, on_insulin_or_sulfonylurea, language, consent_granted_at, consent_revoked_at, updated_at)
                    VALUES ({ph}, {ph}, 0, 'en', NULL, {ph}, {ph})
                    """,
                    (user_id, cond_json, now, now)
                )
        else:
            if granted:
                cursor.execute(
                    f"UPDATE patient_profiles SET consent_granted_at = {ph}, consent_revoked_at = NULL, updated_at = {ph} WHERE user_id = {ph}",
                    (now, now, user_id)
                )
            else:
                cursor.execute(
                    f"UPDATE patient_profiles SET consent_revoked_at = {ph}, updated_at = {ph} WHERE user_id = {ph}",
                    (now, now, user_id)
                )
    return get_patient_profile(user_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)


# =============================================================================
# EHR REGISTRY & CONNECTION HELPERS
# =============================================================================

def get_enabled_ehr_systems(backend: Optional[str] = None, db_path: Optional[str] = None,
                            mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all active registered EHR systems (id and display name only, never URLs)."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute("SELECT ehr_system_id, display_name FROM ehr_systems WHERE enabled = 1")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_ehr_system_by_id(ehr_system_id: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                         mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves full EHR system config (internal use only for resolving FHIR base URL)."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"SELECT ehr_system_id, display_name, fhir_base_url, enabled FROM ehr_systems WHERE ehr_system_id = {ph}",
            (ehr_system_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["enabled"] = bool(d["enabled"])
        return d


def get_active_ehr_connection(user_id: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                              mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves current active EHR connection for a user."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"""
            SELECT c.connection_id, c.user_id, c.ehr_system_id, c.external_patient_id, c.status,
                   c.linked_at, c.last_verified_at, c.last_error_code, c.revoked_at,
                   s.display_name AS display_name
            FROM ehr_connections c
            LEFT JOIN ehr_systems s ON c.ehr_system_id = s.ehr_system_id
            WHERE c.user_id = {ph} AND c.status = 'active'
            ORDER BY c.linked_at DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_active_connection_by_external_id(ehr_system_id: str, external_patient_id: str,
                                         backend: Optional[str] = None, db_path: Optional[str] = None,
                                         mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Finds any existing active connection using the given external patient id in an EHR."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"""
            SELECT connection_id, user_id, ehr_system_id, external_patient_id, status, linked_at, last_verified_at
            FROM ehr_connections
            WHERE ehr_system_id = {ph} AND external_patient_id = {ph} AND status = 'active'
            LIMIT 1
            """,
            (ehr_system_id, external_patient_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def record_ehr_connection(connection_id: str, user_id: str, ehr_system_id: str, external_patient_id: str,
                          status: str, last_error_code: Optional[str] = None, last_verified_at: Optional[str] = None,
                          backend: Optional[str] = None, db_path: Optional[str] = None,
                          mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Dict[str, Any]:
    """
    Records an EHR connection attempt or active link.
    If status is 'active', revokes any previous active connection for this user.
    """
    now = _utc_now_iso()
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        if status == "active":
            cursor.execute(
                f"UPDATE ehr_connections SET status = 'revoked', revoked_at = {ph} WHERE user_id = {ph} AND status = 'active'",
                (now, user_id)
            )
        cursor.execute(
            f"""
            INSERT INTO ehr_connections (connection_id, user_id, ehr_system_id, external_patient_id, status, linked_at, last_verified_at, last_error_code, revoked_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, NULL)
            """,
            (connection_id, user_id, ehr_system_id, external_patient_id, status, now, last_verified_at, last_error_code)
        )
    return {
        "connection_id": connection_id,
        "user_id": user_id,
        "ehr_system_id": ehr_system_id,
        "external_patient_id": external_patient_id,
        "status": status,
        "linked_at": now,
        "last_verified_at": last_verified_at,
        "last_error_code": last_error_code,
    }


def revoke_ehr_connection(user_id: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                          mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> int:
    """Revokes any active EHR connection for the given user."""
    now = _utc_now_iso()
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"UPDATE ehr_connections SET status = 'revoked', revoked_at = {ph} WHERE user_id = {ph} AND status = 'active'",
            (now, user_id)
        )
        return cursor.rowcount


# =============================================================================
# CHECK-IN SESSION & PIPELINE HELPERS
# =============================================================================

def create_checkin(checkin_id: str, user_id: str, mode: str, record_patient_id: str,
                   state_dict: Dict[str, Any], status: str = "in_progress",
                   started_at: Optional[str] = None,
                   backend: Optional[str] = None, db_path: Optional[str] = None,
                   mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Dict[str, Any]:
    """Creates a new check-in session and marks older in_progress sessions for this user as abandoned."""
    now = started_at or _utc_now_iso()
    state_str = json.dumps(state_dict)
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"UPDATE checkins SET status = 'abandoned', completed_at = {ph} WHERE user_id = {ph} AND status = 'in_progress'",
            (now, user_id)
        )
        cursor.execute(
            f"""
            INSERT INTO checkins (checkin_id, user_id, mode, record_patient_id, status, state_json, version, started_at, completed_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 0, {ph}, NULL)
            """,
            (checkin_id, user_id, mode, record_patient_id, status, state_str, now)
        )
    return {
        "checkin_id": checkin_id,
        "user_id": user_id,
        "mode": mode,
        "record_patient_id": record_patient_id,
        "status": status,
        "state": state_dict,
        "version": 0,
        "started_at": now,
        "completed_at": None,
    }


def get_checkin_by_id(checkin_id: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                      mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves check-in row and parsed state dictionary by checkin_id."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"SELECT checkin_id, user_id, mode, record_patient_id, status, state_json, version, started_at, completed_at FROM checkins WHERE checkin_id = {ph}",
            (checkin_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["state"] = json.loads(d.pop("state_json", "{}"))
        except Exception:
            d["state"] = {}
        d["version"] = int(d.get("version", 0)) if d.get("version") is not None else 0
        return d


def update_checkin_state(checkin_id: str, state_dict: Dict[str, Any], status: str = "in_progress",
                         completed_at: Optional[str] = None, backend: Optional[str] = None,
                         db_path: Optional[str] = None, mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Updates interview state, status, and completion timestamp."""
    state_str = json.dumps(state_dict)
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"UPDATE checkins SET state_json = {ph}, status = {ph}, completed_at = {ph}, version = version + 1 WHERE checkin_id = {ph}",
            (state_str, status, completed_at, checkin_id)
        )
    return get_checkin_by_id(checkin_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)


def apply_checkin_answer_atomic(
    checkin_id: str,
    expected_version: int,
    state_dict: Dict[str, Any],
    status: str = "in_progress",
    completed_at: Optional[str] = None,
    emergency: bool = False,
    trigger_category: Optional[str] = None,
    trigger_text: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> bool:
    """
    Atomically updates check-in state with optimistic locking (version match + increment).
    When emergency=True:
      - Sets status='emergency'
      - Creates checkin_results row if not exists
      - Appends emergency_escalated audit row if not exists (category only)
    Returns True on success, False on concurrent update version mismatch.
    """
    now = _utc_now_iso()
    state_str = json.dumps(state_dict)
    clean_trigger_text = trigger_text[:500] if trigger_text else None

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"UPDATE checkins SET state_json = {ph}, status = {ph}, completed_at = {ph}, version = version + 1 WHERE checkin_id = {ph} AND version = {ph}",
            (state_str, status, completed_at, checkin_id, expected_version)
        )
        if cursor.rowcount == 0:
            return False

        if emergency:
            # Check if checkin_results already exists
            cursor.execute(f"SELECT checkin_id FROM checkin_results WHERE checkin_id = {ph}", (checkin_id,))
            if not cursor.fetchone():
                intakes_list = state_dict.get("intakes", [])
                if not intakes_list and state_dict.get("intake"):
                    intakes_list = [state_dict["intake"]]
                intakes_str = json.dumps(intakes_list)
                emg_val = 1
                req_rev_val = 1
                max_sev = "high"
                rev_status = "open"

                cursor.execute(
                    f"""
                    INSERT INTO checkin_results (
                        checkin_id, emergency, intakes_json, reconciliation_json, verification_json,
                        requires_review, max_severity, review_status, trigger_category, trigger_text,
                        escalated_at, created_at
                    ) VALUES ({ph}, {ph}, {ph}, NULL, NULL, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                    """,
                    (checkin_id, emg_val, intakes_str, req_rev_val, max_sev, rev_status, trigger_category, clean_trigger_text, now, now)
                )

            # Check if audit row exists
            cursor.execute(
                f"SELECT id FROM audit_log WHERE action = 'emergency_escalated' AND target = {ph}",
                (checkin_id,)
            )
            if not cursor.fetchone():
                audit_detail = json.dumps({"category": trigger_category or "unknown"}, separators=(",", ":"))
                cursor.execute(
                    f"INSERT INTO audit_log (ts, actor_user_id, action, target, outcome, detail_json) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                    (now, actor_user_id, "emergency_escalated", checkin_id, "ok", audit_detail)
                )

        return True


def create_checkin_result(
    checkin_id: str,
    emergency: bool,
    intakes: List[Dict[str, Any]],
    reconciliation: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
    requires_review: bool = False,
    max_severity: Optional[str] = "none",
    review_status: str = "open",
    trigger_category: Optional[str] = None,
    trigger_text: Optional[str] = None,
    escalated_at: Optional[str] = None,
    created_at: Optional[str] = None,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> Dict[str, Any]:
    """Stores or updates clinical results for a completed check-in."""
    now = created_at or _utc_now_iso()
    intakes_str = json.dumps(intakes)
    recon_str = json.dumps(reconciliation) if reconciliation else None
    verif_str = json.dumps(verification) if verification else None
    emg_val = 1 if emergency else 0
    req_rev_val = 1 if requires_review else 0
    clean_trigger_text = trigger_text[:500] if trigger_text else None

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        if be == "sqlite":
            cursor.execute(
                f"""
                INSERT INTO checkin_results (
                    checkin_id, emergency, intakes_json, reconciliation_json, verification_json,
                    requires_review, max_severity, review_status, trigger_category, trigger_text,
                    escalated_at, created_at
                )
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                ON CONFLICT(checkin_id) DO UPDATE SET
                    emergency = excluded.emergency,
                    intakes_json = excluded.intakes_json,
                    reconciliation_json = excluded.reconciliation_json,
                    verification_json = excluded.verification_json,
                    requires_review = excluded.requires_review,
                    max_severity = excluded.max_severity,
                    review_status = excluded.review_status,
                    trigger_category = excluded.trigger_category,
                    trigger_text = excluded.trigger_text,
                    escalated_at = excluded.escalated_at
                """,
                (checkin_id, emg_val, intakes_str, recon_str, verif_str, req_rev_val, max_severity, review_status, trigger_category, clean_trigger_text, escalated_at, now)
            )
        else:
            cursor.execute(
                f"""
                INSERT INTO checkin_results (
                    checkin_id, emergency, intakes_json, reconciliation_json, verification_json,
                    requires_review, max_severity, review_status, trigger_category, trigger_text,
                    escalated_at, created_at
                )
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                ON DUPLICATE KEY UPDATE
                    emergency = VALUES(emergency),
                    intakes_json = VALUES(intakes_json),
                    reconciliation_json = VALUES(reconciliation_json),
                    verification_json = VALUES(verification_json),
                    requires_review = VALUES(requires_review),
                    max_severity = VALUES(max_severity),
                    review_status = VALUES(review_status),
                    trigger_category = VALUES(trigger_category),
                    trigger_text = VALUES(trigger_text),
                    escalated_at = VALUES(escalated_at)
                """,
                (checkin_id, emg_val, intakes_str, recon_str, verif_str, req_rev_val, max_severity, review_status, trigger_category, clean_trigger_text, escalated_at, now)
            )
    return get_checkin_result(checkin_id, backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)


def get_checkin_result(checkin_id: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                       mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves check-in result details by checkin_id."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"""
            SELECT checkin_id, emergency, intakes_json, reconciliation_json, verification_json,
                   requires_review, max_severity, review_status, trigger_category, trigger_text,
                   escalated_at, created_at
            FROM checkin_results
            WHERE checkin_id = {ph}
            """,
            (checkin_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["emergency"] = bool(d["emergency"])
        d["requires_review"] = bool(d["requires_review"])
        d["intakes"] = json.loads(d.pop("intakes_json", "[]"))
        recon_raw = d.pop("reconciliation_json", None)
        d["reconciliation"] = json.loads(recon_raw) if recon_raw else None
        verif_raw = d.pop("verification_json", None)
        d["verification"] = json.loads(verif_raw) if verif_raw else None
        return d


def get_user_checkins(user_id: str, limit: int = 20, backend: Optional[str] = None, db_path: Optional[str] = None,
                      mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves list of user's check-ins with result summary."""
    clamped_limit = max(1, min(limit, 100))
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"""
            SELECT c.checkin_id, c.user_id, c.mode, c.record_patient_id, c.status, c.version, c.started_at, c.completed_at,
                   r.emergency, r.requires_review, r.max_severity, r.review_status
            FROM checkins c
            LEFT JOIN checkin_results r ON c.checkin_id = r.checkin_id
            WHERE c.user_id = {ph}
            ORDER BY c.started_at DESC
            LIMIT {ph}
            """,
            (user_id, clamped_limit)
        )
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["emergency"] = bool(d["emergency"]) if d.get("emergency") is not None else False
            d["requires_review"] = bool(d["requires_review"]) if d.get("requires_review") is not None else False
            d["version"] = int(d.get("version", 0)) if d.get("version") is not None else 0
            results.append(d)
        return results


# =============================================================================
# PROVIDER REVIEW QUEUE & ACTION HELPERS
# =============================================================================

def get_provider_review_queue(review_status: str = "open", backend: Optional[str] = None, db_path: Optional[str] = None,
                              mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves review queue ordered by emergency (desc), max_severity (desc), and created_at (asc)."""
    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"""
            SELECT r.checkin_id, r.emergency, r.max_severity, r.review_status, r.created_at,
                   r.intakes_json, r.reconciliation_json, r.verification_json,
                   r.trigger_category, r.trigger_text, r.escalated_at,
                   c.mode, c.user_id,
                   u.display_name, u.email
            FROM checkin_results r
            JOIN checkins c ON r.checkin_id = c.checkin_id
            JOIN users u ON c.user_id = u.user_id
            WHERE r.review_status = {ph}
            ORDER BY r.emergency DESC,
                     CASE r.max_severity
                         WHEN 'high' THEN 1
                         WHEN 'moderate' THEN 2
                         WHEN 'low' THEN 3
                         ELSE 4
                     END ASC,
                     r.created_at ASC
            """,
            (review_status,)
        )
        rows = cursor.fetchall()
        items = []
        for row in rows:
            d = dict(row)
            emergency = bool(d["emergency"])
            max_severity = d.get("max_severity")
            created_at_str = d["created_at"]
            
            # Compute overdue: emergency or high severity older than 2 hours
            overdue = False
            try:
                created_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                age_seconds = (now_dt - created_dt).total_seconds()
                if (emergency or max_severity == "high") and age_seconds > 7200:
                    overdue = True
            except Exception:
                overdue = False

            # Compute summary counts
            counts = {"observations": 0, "discrepancies": 0, "medications": 0}
            try:
                recon = json.loads(d.get("reconciliation_json") or "{}")
                if recon:
                    summary = recon.get("summary", {})
                    counts["observations"] = len(recon.get("observation_comparisons", []))
                    counts["discrepancies"] = summary.get("conflicts", 0) + summary.get("missing", 0)
                    counts["medications"] = len(recon.get("medication_comparisons", []))
            except Exception:
                pass

            # Extract trigger_reading if present in intakes
            trigger_reading = None
            try:
                intakes = json.loads(d.get("intakes_json") or "[]")
                for intake in intakes:
                    if intake.get("trigger_reading"):
                        trigger_reading = intake["trigger_reading"]
                        break
            except Exception:
                pass

            patient_display = d.get("display_name") or d.get("email") or "Patient"

            items.append({
                "checkin_id": d["checkin_id"],
                "patient_display": patient_display,
                "mode": d["mode"],
                "created_at": created_at_str,
                "max_severity": max_severity,
                "emergency": emergency,
                "overdue": overdue,
                "counts": counts,
                "trigger_category": d.get("trigger_category"),
                "trigger_text": d.get("trigger_text"),
                "trigger_reading": trigger_reading,
                "escalated_at": d.get("escalated_at"),
            })
        return items


def append_review_action(checkin_id: str, provider_user_id: str, action: str,
                         note: Optional[str] = None, backend: Optional[str] = None,
                         db_path: Optional[str] = None, mysql_url: Optional[str] = None,
                         ssl_ca: Optional[str] = None) -> Dict[str, Any]:
    """Appends an immutable review action and updates review_status."""
    now = _utc_now_iso()
    clean_action = str(action).strip().lower()
    clean_note = str(note).strip()[:500] if note else None

    status_map = {
        "acknowledge": "acknowledged",
        "resolve": "resolved",
        "escalate": "escalated",
    }
    new_status = status_map.get(clean_action, "open")

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"INSERT INTO review_actions (checkin_id, provider_user_id, action, note, ts) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
            (checkin_id, provider_user_id, clean_action, clean_note, now)
        )
        cursor.execute(
            f"UPDATE checkin_results SET review_status = {ph} WHERE checkin_id = {ph}",
            (new_status, checkin_id)
        )

    return {
        "checkin_id": checkin_id,
        "provider_user_id": provider_user_id,
        "action": clean_action,
        "note": clean_note,
        "ts": now,
        "new_review_status": new_status,
    }


def get_review_actions(checkin_id: str, backend: Optional[str] = None, db_path: Optional[str] = None,
                       mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all review action history rows for a check-in."""
    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
        cursor.execute(
            f"""
            SELECT id, checkin_id, provider_user_id, action, note, ts
            FROM review_actions
            WHERE checkin_id = {ph}
            ORDER BY id ASC
            """,
            (checkin_id,)
        )
        return [dict(r) for r in cursor.fetchall()]


