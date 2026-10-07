#!/usr/bin/env python3
"""
MySQL Pre-flight & Migration Verification Script.
Standard library + project db modules only. Never prints secrets, credentials or row data.

Usage:
    python scripts/mysql_preflight.py
"""

import os
import sys
from typing import Set

# Add backend directory to sys.path to import project modules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "backend-poc-technical"))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    import pymysql
    from data_sources import db_config, app_store, local_store
except ImportError as e:
    print(f"[FAIL] Missing required module: {e}")
    sys.exit(1)


# Schema version 10 is the latest migration version defined in app_store.migrate()
LATEST_EXPECTED_SCHEMA_VERSION = 10

# All tables created by application migrations and local store initialization
EXPECTED_TABLES: Set[str] = set(app_store.APP_STORE_TABLES) | set(local_store.LOCAL_STORE_TABLES)


def run_preflight() -> int:
    print("=" * 60)
    print("CHRONICCARE AI - MYSQL PRE-FLIGHT & MIGRATION CHECK")
    print("=" * 60)

    # 1. Environment & Parameter Validation
    mysql_url = os.environ.get("MYSQL_URL", "").strip()
    if not mysql_url:
        print("[FAIL] Missing required environment variable: MYSQL_URL")
        return 1

    ssl_ca = os.environ.get("MYSQL_SSL_CA", "").strip() or None
    try:
        conn_params = db_config.get_mysql_connection_params(mysql_url=mysql_url, ssl_ca=ssl_ca)
    except Exception as e:
        print(f"[FAIL] Failed to parse MySQL connection parameters: {type(e).__name__}")
        return 1

    # 2. Connection & TLS Check
    print("\n[STEP 1/4] Establishing secure connection to MySQL database...")
    try:
        conn = pymysql.connect(
            host=conn_params["host"],
            port=conn_params["port"],
            user=conn_params["user"],
            password=conn_params["password"],
            database=conn_params["database"],
            charset=conn_params.get("charset", "utf8mb4"),
            ssl=conn_params.get("ssl"),
            connect_timeout=15,
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            ver_row = cursor.fetchone()
            server_version = ver_row[0] if isinstance(ver_row, (tuple, list)) else list(ver_row.values())[0]
        print(f"  -> Server Version: {server_version}")
        print("  -> Status: PASS")
    except Exception as e:
        print(f"  -> Connection error: {type(e).__name__}")
        print("  -> Status: FAIL")
        return 1

    # 3. Schema Migrations & Local Store Check
    print("\n[STEP 2/4] Executing schema migrations & local store initialization...")
    try:
        app_store.migrate(backend="mysql", mysql_url=mysql_url, ssl_ca=ssl_ca)
        local_store.init_db(backend="mysql", mysql_url=mysql_url, ssl_ca=ssl_ca)
        with conn.cursor() as cursor:
            cursor.execute("SELECT MAX(version) AS max_v FROM schema_version")
            row = cursor.fetchone()
            if row is None:
                current_version = 0
            elif isinstance(row, (tuple, list)):
                current_version = row[0] if row[0] is not None else 0
            elif isinstance(row, dict):
                current_version = row.get("max_v") or 0
            else:
                current_version = int(row)

        print(f"  -> Schema Version Reached: {current_version} (Expected: {LATEST_EXPECTED_SCHEMA_VERSION})")
        if current_version < LATEST_EXPECTED_SCHEMA_VERSION:
            print("  -> Status: FAIL (Migration did not reach expected version)")
            conn.close()
            return 1
        print("  -> Status: PASS")
    except Exception as e:
        print(f"  -> Migration error: {type(e).__name__}")
        print("  -> Status: FAIL")
        conn.close()
        return 1

    # 4. Table Structure Verification
    print("\n[STEP 3/4] Verifying registered tables...")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            rows = cursor.fetchall()
            tables = sorted([r[0] if isinstance(r, (tuple, list)) else list(r.values())[0] for r in rows])
        print(f"  -> Total Tables: {len(tables)}")
        print(f"  -> Table List: {', '.join(tables)}")
        missing = EXPECTED_TABLES - set(tables)
        if missing:
            print(f"  -> Missing required tables: {missing}")
            print("  -> Status: FAIL")
            conn.close()
            return 1
        print("  -> Status: PASS")
    except Exception as e:
        print(f"  -> Table query error: {type(e).__name__}")
        print("  -> Status: FAIL")
        conn.close()
        return 1

    # 5. DDL & DML Round-Trip on Temporary Table
    print("\n[STEP 4/4] Testing table creation, write, read, and drop (_preflight_tmp)...")
    try:
        with conn.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS _preflight_tmp (id INT PRIMARY KEY, test_val VARCHAR(50))")
            cursor.execute("INSERT INTO _preflight_tmp (id, test_val) VALUES (1, 'probe')")
            conn.commit()
            cursor.execute("SELECT id FROM _preflight_tmp WHERE id = 1")
            found = cursor.fetchone()
            found_id = found[0] if isinstance(found, (tuple, list)) else list(found.values())[0]
            if found_id != 1:
                raise ValueError("Verification read on temporary table failed")
            cursor.execute("DROP TABLE _preflight_tmp")
            conn.commit()
        print("  -> Temporary Table Round-Trip: Complete")
        print("  -> Status: PASS")
    except Exception as e:
        print(f"  -> Temporary table error: {type(e).__name__}")
        print("  -> Status: FAIL")
        conn.close()
        return 1

    conn.close()
    print("\n" + "=" * 60)
    print("PRE-FLIGHT CHECK SUMMARY: ALL STEPS PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(run_preflight())
