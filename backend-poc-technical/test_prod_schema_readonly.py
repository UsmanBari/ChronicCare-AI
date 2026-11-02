"""
Hermetic test for scripts/prod_schema_readonly.py:
1. Asserts no write SQL keywords (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, TRUNCATE, REPLACE, GRANT)
   exist anywhere in the file (case-insensitive, whole file including comments).
2. Asserts SET SESSION TRANSACTION READ ONLY and rollback are present.
3. Tests inspect_production and main behavior with mocks without touching any network or database.
4. Asserts no credentials or secrets can be leaked.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_main_masks_secrets(monkeypatch, capsys):
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import prod_schema_readonly

    secret_url = "mysql://admin_user:super_secret_password_123@db.example.com:3306/prod_db"
    monkeypatch.setenv("MYSQL_URL", secret_url)
    monkeypatch.setenv("MYSQL_SSL_CA", "/path/to/ca.pem")

    with patch.object(prod_schema_readonly, "inspect_production") as mock_inspect, \
         patch("pymysql.connect") as mock_connect:
        mock_inspect.return_value = {
            "version": 12,
            "tables": ["users"],
            "counts": {"users": 5},
        }
        prod_schema_readonly.main()

    captured = capsys.readouterr().out
    assert "MYSQL_URL: SET" in captured
    assert "MYSQL_SSL_CA: SET" in captured
    assert "super_secret_password_123" not in captured
    assert "admin_user" not in captured
    assert "db.example.com" not in captured
    assert "Schema Version: 12" in captured
    assert "users: 5" in captured

