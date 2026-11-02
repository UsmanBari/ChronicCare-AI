"""
Read-only schema and row tally inspector for production database.
Checks schema version and row counts without executing writes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    pymysql = None


def resolve_ssl_ca(path_or_content: Optional[str]) -> Optional[str]:
    if not path_or_content:
        return None
    p = Path(path_or_content)
    if p.is_file():
        return str(p.resolve())
    return None


def get_params(raw_url: Optional[str], raw_ca: Optional[str]) -> Dict[str, Any]:
    if not raw_url:
        raise ValueError("Missing database URL")
    parsed = urlparse(raw_url)
    h = parsed.hostname or "localhost"
    pt = parsed.port or 3306
    u = unquote(parsed.username) if parsed.username else "root"
    pwd = unquote(parsed.password) if parsed.password else ""
    db = parsed.path.lstrip("/")
    if not db:
        raise ValueError("Missing database name")
    cfg: Dict[str, Any] = {
        "host": h,
        "port": pt,
        "user": u,
        "password": pwd,
        "database": db,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor if pymysql else None,
    }
    ca = resolve_ssl_ca(raw_ca)
    if ca:
        cfg["ssl"] = {"ca": ca}
    return cfg


def inspect_production(conn: Any) -> Dict[str, Any]:
    with conn.cursor() as cursor:
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
        cursor.execute("SELECT MAX(version) AS max_v FROM schema_version")
        v_row = cursor.fetchone()
        current_v = v_row["max_v"] if v_row else None

        cursor.execute("SHOW TABLES")
        table_rows = cursor.fetchall()

        table_names: List[str] = []
        for r in table_rows:
            if isinstance(r, dict):
                table_names.append(list(r.values())[0])
            else:
                table_names.append(r[0])

        tallies: Dict[str, int] = {}
        for t in sorted(table_names):
            if not t.isidentifier():
                continue
            cursor.execute(f"SELECT COUNT(*) AS total FROM `{t}`")
            c_row = cursor.fetchone()
            tallies[t] = c_row["total"] if c_row else 0

        conn.rollback()

    return {
        "version": current_v,
        "tables": sorted(table_names),
        "counts": tallies,
    }


def main() -> None:
    raw_url = os.environ.get("MYSQL_URL")
    raw_ca = os.environ.get("MYSQL_SSL_CA")

    print(f"MYSQL_URL: {'SET' if raw_url else 'NOT SET'}")
    print(f"MYSQL_SSL_CA: {'SET' if raw_ca else 'NOT SET'}")

    if not raw_url:
        print("ERROR: MYSQL_URL is not set.")
        sys.exit(1)

    if pymysql is None:
        print("ERROR: pymysql is not installed.")
        sys.exit(1)

    cfg = get_params(raw_url, raw_ca)
    conn = pymysql.connect(**cfg)
    try:
        data = inspect_production(conn)
        print("--- PRODUCTION READ-ONLY INSPECTION ---")
        print(f"Schema Version: {data['version']}")
        print(f"Total Tables: {len(data['tables'])}")
        print("Table Row Tallies:")
        for t, cnt in data["counts"].items():
            print(f"  - {t}: {cnt}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

