"""
Hermetic test for scripts/prod_schema_readonly.py:
1. Asserts no write SQL keywords exist anywhere in the script file.
2. Asserts SET SESSION TRANSACTION READ ONLY and rollback are present.
3. Tests inspect_production with mocks.
4. Tests main masks secrets and prints database name.
5. Tests warning when database name is defaultdb.
6. Tests missing CA file causes exit 1 without connecting.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "prod_schema_readonly.py"


def test_no_write_sql_keywords_in_file():
    text = SCRIPT_PATH.read_text(encoding="utf-8").upper()
    banned_words = [
        "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER",
        "DROP", "TRUNCATE", "REPLACE", "GRANT",
    ]
    for word in banned_words:
        assert word not in text, f"Banned write SQL keyword '{word}' found in {SCRIPT_PATH}"


def test_session_transaction_read_only_and_rollback():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "SET SESSION TRANSACTION READ ONLY" in text
    assert "conn.rollback()" in text


def test_inspect_production_mock():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import prod_schema_readonly

    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"max_v": 15},
        {"total": 10},
        {"total": 42},
    ]
    mock_cursor.fetchall.return_value = [
        {"Tables_in_db": "users"},
        {"Tables_in_db": "checkins"},
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    res = prod_schema_readonly.inspect_production(mock_conn)

    assert res["version"] == 15
    assert res["tables"] == ["checkins", "users"]
    assert res["counts"] == {"checkins": 10, "users": 42}
    mock_conn.rollback.assert_called_once()


def test_main_prints_db_and_masks_secrets(monkeypatch, capsys, tmp_path):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import prod_schema_readonly

    ca_file = tmp_path / "test_ca.pem"
    ca_file.write_text("dummy ca content", encoding="utf-8")

    secret_url = "mysql://admin_user:super_secret_password_123@db.example.com:3306/chroniccare_demo"
    monkeypatch.setenv("MYSQL_URL", secret_url)
    monkeypatch.setenv("MYSQL_SSL_CA", str(ca_file))

    with patch.object(prod_schema_readonly, "inspect_production") as mock_inspect, \
         patch("pymysql.connect"):
        mock_inspect.return_value = {
            "version": 12,
            "tables": ["users"],
            "counts": {"users": 15},
        }
        prod_schema_readonly.main()

    captured = capsys.readouterr().out
    assert "MYSQL_URL: SET" in captured
    assert "MYSQL_SSL_CA: SET" in captured
    assert "Database: chroniccare_demo" in captured
    assert "super_secret_password_123" not in captured
    assert "admin_user" not in captured
    assert "db.example.com" not in captured
    assert "WARNING: defaultdb is NOT production" not in captured
    assert "Schema Version: 12" in captured
    assert "users: 15" in captured


def test_main_warns_on_defaultdb(monkeypatch, capsys, tmp_path):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import prod_schema_readonly

    ca_file = tmp_path / "test_ca.pem"
    ca_file.write_text("dummy ca content", encoding="utf-8")

    secret_url = "mysql://test_user:pass@db.example.com:3306/defaultdb"
    monkeypatch.setenv("MYSQL_URL", secret_url)
    monkeypatch.setenv("MYSQL_SSL_CA", str(ca_file))

    with patch.object(prod_schema_readonly, "inspect_production") as mock_inspect, \
         patch("pymysql.connect"):
        mock_inspect.return_value = {
            "version": 1,
            "tables": [],
            "counts": {},
        }
        prod_schema_readonly.main()

    captured = capsys.readouterr().out
    assert "Database: defaultdb" in captured
    assert "WARNING: defaultdb is NOT production. Production is chroniccare_demo." in captured


def test_main_missing_ssl_ca_exits(monkeypatch, capsys):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import prod_schema_readonly

    monkeypatch.setenv("MYSQL_URL", "mysql://u:p@localhost:3306/chroniccare_demo")
    monkeypatch.setenv("MYSQL_SSL_CA", "/nonexistent/path/to/missing_ca_file.pem")

    with patch("pymysql.connect") as mock_connect:
        with pytest.raises(SystemExit) as exc_info:
            prod_schema_readonly.main()

        assert exc_info.value.code == 1
        mock_connect.assert_not_called()

    captured = capsys.readouterr().out
    assert "ERROR: MYSQL_SSL_CA file not found" in captured
