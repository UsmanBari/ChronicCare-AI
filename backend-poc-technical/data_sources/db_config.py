"""
Database Configuration & Backend Selector for ChronicCare AI.

Supports SQLite (default) and MySQL backends via environment variables:
- DB_BACKEND: "sqlite" (default) or "mysql"
- LOCAL_DB_PATH: Path to SQLite database file (default: local_store.db)
- MYSQL_URL: MySQL connection URI (format: standard MySQL connection string)
- MYSQL_SSL_CA: Path to SSL CA certificate (relative to backend-poc-technical/ or absolute)
"""

import os
from urllib.parse import urlparse, unquote
from typing import Dict, Any, Optional

DEFAULT_SQLITE_PATH = "local_store.db"


def get_backend_root_dir() -> str:
    """Returns the absolute path to backend-poc-technical directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_db_backend() -> str:
    """Returns 'sqlite' or 'mysql', defaulting to 'sqlite'."""
    return os.environ.get("DB_BACKEND", "sqlite").strip().lower()


def get_sqlite_path(db_path: Optional[str] = None) -> str:
    """Returns resolved path to SQLite database."""
    if db_path:
        return db_path
    raw = os.environ.get("LOCAL_DB_PATH", DEFAULT_SQLITE_PATH).strip()
    if not raw:
        return os.path.join(get_backend_root_dir(), DEFAULT_SQLITE_PATH)
    if os.path.isabs(raw):
        return raw
    return os.path.abspath(os.path.join(get_backend_root_dir(), raw))


def resolve_ssl_ca_path(ssl_ca_path: Optional[str] = None) -> Optional[str]:
    """Resolves CA cert path relative to backend-poc-technical root if not absolute."""
    path = ssl_ca_path or os.environ.get("MYSQL_SSL_CA")
    if not path:
        return None
    if os.path.isabs(path):
        return path if os.path.exists(path) else None
    
    resolved = os.path.abspath(os.path.join(get_backend_root_dir(), path))
    return resolved if os.path.exists(resolved) else None


def get_mysql_connection_params(mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses MYSQL_URL and returns connection parameters suitable for PyMySQL.
    """
    raw_url = mysql_url or os.environ.get("MYSQL_URL")
    if not raw_url:
        raise ValueError("MYSQL_URL environment variable is required when using MySQL backend.")

    parsed = urlparse(raw_url)
    
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    user = unquote(parsed.username) if parsed.username else "root"
    password = unquote(parsed.password) if parsed.password else ""
    db = parsed.path.lstrip("/")
    
    if not db:
        raise ValueError("MYSQL_URL must specify a database name in the URL path.")

    params: Dict[str, Any] = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": db,
        "charset": "utf8mb4",
        "cursorclass": None,
    }

    ca_resolved = resolve_ssl_ca_path(ssl_ca)
    if ca_resolved:
        params["ssl"] = {"ca": ca_resolved}

    return params
