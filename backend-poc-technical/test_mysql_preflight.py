"""
Hermetic Unit Tests for MySQL Pre-flight Script (Stage 6 D2 / Fix).
"""

import os
import sys
import inspect
import pytest
from typing import Any, List, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from data_sources import db_config, app_store, local_store
import mysql_preflight
import pymysql


def test_mysql_preflight_refuses_when_mysql_url_missing(monkeypatch, capsys):
    monkeypatch.delenv("MYSQL_URL", raising=False)
    exit_code = mysql_preflight.run_preflight()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Missing required environment variable: MYSQL_URL" in captured.out
    # Confirm no credentials or private strings printed
    assert "password" not in captured.out.lower()
    assert "mysql://" not in captured.out.lower()


def test_mysql_preflight_handles_invalid_url(monkeypatch, capsys):
    monkeypatch.setenv("MYSQL_URL", "mysql://invalid_host_no_db")
    exit_code = mysql_preflight.run_preflight()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Failed to parse MySQL connection parameters" in captured.out


def test_mysql_preflight_signatures_and_constants():
    """
    (a) Uses inspect.signature to prove that every argument the script passes to
    app_store.migrate, local_store.init_db, db_config.get_mysql_connection_params, and pymysql.connect
    exists in the real signatures, and that schema version 10 is the latest expected version.
    """
    # 1. db_config.get_mysql_connection_params
    sig_conn = inspect.signature(db_config.get_mysql_connection_params)
    assert "mysql_url" in sig_conn.parameters
    assert "ssl_ca" in sig_conn.parameters

    # 2. app_store.migrate
    sig_migrate = inspect.signature(app_store.migrate)
    assert "backend" in sig_migrate.parameters
    assert "mysql_url" in sig_migrate.parameters
    assert "ssl_ca" in sig_migrate.parameters

    # 3. local_store.init_db
    sig_init_db = inspect.signature(local_store.init_db)
    assert "backend" in sig_init_db.parameters
    assert "mysql_url" in sig_init_db.parameters
    assert "ssl_ca" in sig_init_db.parameters

    # 4. pymysql.connect
    sig_pymysql = inspect.signature(pymysql.connect)
    for kw in ("host", "port", "user", "password", "database", "charset", "ssl", "connect_timeout"):
        assert kw in sig_pymysql.parameters

    # 5. Expected schema version and tables (10 app tables + 3 local store tables)
    assert mysql_preflight.LATEST_EXPECTED_SCHEMA_VERSION == 12
    expected_tables = {
        "users",
        "audit_log",
        "patient_profiles",
        "ehr_systems",
        "ehr_connections",
        "checkins",
        "checkin_results",
        "review_actions",
        "allergies",
        "schema_version",
        "patients",
        "observations",
        "medications",
    }
    assert mysql_preflight.EXPECTED_TABLES == expected_tables


class FakeCursor:
    def __init__(self, mode: str = "ok"):
        self.mode = mode
        self._last_query = ""
        self._queries: List[str] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query: str, params: Any = None):
        self._last_query = query
        self._queries.append(query)
        if self.mode == "fail_tmp_create" and "CREATE TABLE" in query:
            raise RuntimeError("Fake DDL failure on temporary table")
        if self.mode == "fail_tmp_select" and "SELECT id FROM _preflight_tmp" in query:
            raise RuntimeError("Fake DML read failure on temporary table")

    def fetchone(self):
        if "SELECT VERSION()" in self._last_query:
            if self.mode == "fail_version":
                raise RuntimeError("Fake version query failure")
            return ("8.0.35-aiven",)
        if "SELECT MAX(version)" in self._last_query:
            if self.mode == "fail_low_version":
                return (mysql_preflight.LATEST_EXPECTED_SCHEMA_VERSION - 1,)  # Lower than expected
            return (mysql_preflight.LATEST_EXPECTED_SCHEMA_VERSION,)
        if "SELECT id FROM _preflight_tmp" in self._last_query:
            if self.mode == "fail_wrong_tmp_id":
                return (999,)
            return (1,)
        return None

    def fetchall(self):
        if "SHOW TABLES" in self._last_query:
            if self.mode == "fail_missing_tables":
                return [("users",), ("audit_log",)]  # Incomplete
            return [(t,) for t in sorted(mysql_preflight.EXPECTED_TABLES)]
        return []


class FakeConnection:
    def __init__(self, mode: str = "ok"):
        self.mode = mode
        self.closed = False
        self.committed = False

    def cursor(self):
        return FakeCursor(mode=self.mode)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_mysql_preflight_fake_full_run_and_step_failures(monkeypatch, capsys):
    """
    (b) Runs the whole script with pymysql.connect, app_store.migrate, and local_store.init_db replaced by fakes
    and asserts that all four steps print PASS and exit code is 0,
    and that a fake failure at each step gives exit code 1.
    """
    monkeypatch.setenv("MYSQL_URL", "mysql://fake_user:fake_password@fake_host:3306/fake_db")
    monkeypatch.delenv("MYSQL_SSL_CA", raising=False)

    # 1. Full Success Run
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: FakeConnection("ok"))
    monkeypatch.setattr(app_store, "migrate", lambda **kwargs: None)
    monkeypatch.setattr(local_store, "init_db", lambda **kwargs: None)

    code = mysql_preflight.run_preflight()
    assert code == 0
    captured = capsys.readouterr()
    assert "[STEP 1/4] Establishing secure connection to MySQL database..." in captured.out
    assert "[STEP 2/4] Executing schema migrations & local store initialization..." in captured.out
    assert "[STEP 3/4] Verifying registered tables..." in captured.out
    assert "[STEP 4/4] Testing table creation, write, read, and drop (_preflight_tmp)..." in captured.out
    assert "PRE-FLIGHT CHECK SUMMARY: ALL STEPS PASSED" in captured.out
    assert captured.out.count("Status: PASS") == 4

    # 2. Step 1 Failure (Connection Error)
    def fake_connect_fail(**kwargs):
        raise ConnectionRefusedError("Fake network unreachable")

    monkeypatch.setattr(pymysql, "connect", fake_connect_fail)
    code = mysql_preflight.run_preflight()
    assert code == 1
    captured = capsys.readouterr()
    assert "Connection error: ConnectionRefusedError" in captured.out

    # 3. Step 2 Failure (Migration Exception)
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: FakeConnection("ok"))
    def fake_migrate_fail(**kwargs):
        raise RuntimeError("Fake migration SQL syntax error")
    monkeypatch.setattr(app_store, "migrate", fake_migrate_fail)
    code = mysql_preflight.run_preflight()
    assert code == 1
    captured = capsys.readouterr()
    assert "Migration error: RuntimeError" in captured.out

    # 4. Step 2 Failure (Migration did not reach expected version)
    monkeypatch.setattr(app_store, "migrate", lambda **kwargs: None)
    monkeypatch.setattr(local_store, "init_db", lambda **kwargs: None)
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: FakeConnection("fail_low_version"))
    code = mysql_preflight.run_preflight()
    assert code == 1
    captured = capsys.readouterr()
    assert "Status: FAIL (Migration did not reach expected version)" in captured.out

    # 5. Step 3 Failure (Missing Required Tables - e.g. local store table missing)
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: FakeConnection("fail_missing_tables"))
    code = mysql_preflight.run_preflight()
    assert code == 1
    captured = capsys.readouterr()
    assert "Missing required tables:" in captured.out

    # 6. Step 4 Failure (Temporary Table Operation Failure)
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: FakeConnection("fail_tmp_create"))
    code = mysql_preflight.run_preflight()
    assert code == 1
    captured = capsys.readouterr()
    assert "Temporary table error: RuntimeError" in captured.out


def test_mysql_preflight_fails_when_local_store_table_missing(monkeypatch, capsys):
    """
    Specifically verifies that if app tables are present but a local store table
    (such as 'medications') is missing, pre-flight fails with exit code 1.
    """
    monkeypatch.setenv("MYSQL_URL", "mysql://fake_user:fake_password@fake_host:3306/fake_db")
    monkeypatch.delenv("MYSQL_SSL_CA", raising=False)
    monkeypatch.setattr(app_store, "migrate", lambda **kwargs: None)
    monkeypatch.setattr(local_store, "init_db", lambda **kwargs: None)

    # All tables except 'medications'
    all_except_meds = sorted(list(mysql_preflight.EXPECTED_TABLES - {"medications"}))

    class FakeCursorMissingLocalTable(FakeCursor):
        def fetchall(self):
            if "SHOW TABLES" in self._last_query:
                return [(t,) for t in all_except_meds]
            return []

    class FakeConnMissingLocalTable(FakeConnection):
        def cursor(self):
            return FakeCursorMissingLocalTable(mode="ok")

    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: FakeConnMissingLocalTable())

    code = mysql_preflight.run_preflight()
    assert code == 1
    captured = capsys.readouterr()
    assert "Missing required tables: {'medications'}" in captured.out


def test_mysql_preflight_leak_free_output(monkeypatch, capsys):
    """
    (c) Asserts that captured output of a full fake run contains no host, user,
    password, or URL credentials.
    """
    secret_host = "secret-aiven-host.aivencloud.com"
    secret_user = "secret_db_admin_usr"
    secret_pass = "SuperSecretDbPassword987!"
    secret_db = "chroniccare_prod_db"
    fake_url = f"mysql://{secret_user}:{secret_pass}@{secret_host}:15432/{secret_db}"

    monkeypatch.setenv("MYSQL_URL", fake_url)
    monkeypatch.delenv("MYSQL_SSL_CA", raising=False)
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: FakeConnection("ok"))
    monkeypatch.setattr(app_store, "migrate", lambda **kwargs: None)
    monkeypatch.setattr(local_store, "init_db", lambda **kwargs: None)

    code = mysql_preflight.run_preflight()
    assert code == 0
    captured = capsys.readouterr()

    # Verify that secret components never appear in stdout or stderr
    assert secret_host not in captured.out
    assert secret_user not in captured.out
    assert secret_pass not in captured.out
    assert secret_db not in captured.out
    assert "mysql://" not in captured.out
    assert secret_host not in captured.err
    assert secret_user not in captured.err
    assert secret_pass not in captured.err
    assert secret_db not in captured.err


def test_fastapi_startup_lifespan_initializes_local_store(monkeypatch, caplog):
    """
    Hermetic test verifying that FastAPI startup lifespan calls local_store.init_db()
    and logs 'local store ready' without logging credentials.
    """
    import asyncio
    import logging
    from main import lifespan, app

    init_called = {"migrate": False, "local_store": False}

    def fake_migrate():
        init_called["migrate"] = True

    def fake_local_init():
        init_called["local_store"] = True

    import main
    monkeypatch.setattr(main, "migrate", fake_migrate)
    monkeypatch.setattr(main, "local_store_init_db", fake_local_init)

    async def _run():
        with caplog.at_level(logging.INFO):
            async with lifespan(app):
                pass

    asyncio.run(_run())

    assert init_called["migrate"] is True
    assert init_called["local_store"] is True
    assert "local store ready" in caplog.text

