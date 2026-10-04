"""
Database Configuration & Backend Selector for Isolated Mode Local Store.

Supports SQLite (default) and MySQL backends via environment variables:
- DB_BACKEND: "sqlite" (default) or "mysql"
- MYSQL_URL: MySQL connection URI (e.g. mysql://<user>:<password>@<host>:<port>/<dbname>?ssl-mode=REQUIRED)
- MYSQL_SSL_CA: Path to SSL CA certificate (relative to backend-poc-technical/ or absolute)
"""

import os
from urllib.parse import urlparse, unquote
from typing import Dict, Any, Optional

def get_backend_root_dir() -> str:
    """Returns the absolute path to backend-poc-technical directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_db_backend() -> str:
    """Returns 'sqlite' or 'mysql', defaulting to 'sqlite'."""
    return os.environ.get("DB_BACKEND", "sqlite").strip().lower()

def resolve_ssl_ca_path(ssl_ca_path: Optional[str]) -> Optional[str]:
    """Resolves CA cert path relative to backend-poc-technical root if not absolute."""
    if not ssl_ca_path:
        return None
    if os.path.isabs(ssl_ca_path):
        return ssl_ca_path if os.path.exists(ssl_ca_path) else None
    
    resolved = os.path.abspath(os.path.join(get_backend_root_dir(), ssl_ca_path))
    return resolved if os.path.exists(resolved) else None

def get_mysql_connection_params(mysql_url: Optional[str] = None, ssl_ca: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses MYSQL_URL and returns connection parameters suitable for PyMySQL.
    Does NOT pass ssl-mode query parameter directly to PyMySQL; resolves ssl={'ca': path}.
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
        "cursorclass": None,  # Specified by callers (e.g. DictCursor)
    }

    # Resolve SSL CA
    ca_env = ssl_ca or os.environ.get("MYSQL_SSL_CA")
    ca_resolved = resolve_ssl_ca_path(ca_env)
    if ca_resolved:
        params["ssl"] = {"ca": ca_resolved}

    return params
