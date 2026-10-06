"""
Hermetic Unit Tests for MySQL Pre-flight Script (Stage 6 D2).
"""

import os
import subprocess
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT_PATH = os.path.join(ROOT_DIR, "scripts", "mysql_preflight.py")
PYTHON_EXE = os.environ.get("PYTHON_EXE", "python")


def test_mysql_preflight_refuses_when_mysql_url_missing(monkeypatch, capsys):
    # Import run_preflight from scripts.mysql_preflight
    import sys
    scripts_dir = os.path.join(ROOT_DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    
    from mysql_preflight import run_preflight

    monkeypatch.delenv("MYSQL_URL", raising=False)
    exit_code = run_preflight()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Missing required environment variable: MYSQL_URL" in captured.out
    # Confirm no credentials or private strings printed
    assert "password" not in captured.out.lower()
    assert "mysql://" not in captured.out.lower()


def test_mysql_preflight_handles_invalid_url(monkeypatch, capsys):
    import sys
    scripts_dir = os.path.join(ROOT_DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from mysql_preflight import run_preflight

    monkeypatch.setenv("MYSQL_URL", "mysql://invalid_host_no_db")
    exit_code = run_preflight()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Failed to parse MySQL connection parameters" in captured.out

