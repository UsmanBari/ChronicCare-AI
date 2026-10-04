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
        conn = sqlite3.connect(path)
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
    EHR Systems, and EHR Connections tables.
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
    """Creates a new user row."""
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
    }


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

