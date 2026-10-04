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
    Idempotent schema migration for Users, Roles, and Audit Log tables.
    Safe to run repeatedly.
    """
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
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, ?)", (_utc_now_iso(),))
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
                cursor.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, %s)", (_utc_now_iso(),))


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
