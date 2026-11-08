"""
Unit & Integration Tests for Live Smoke --real-chunks mode and DB preservation.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from data_sources import app_store, local_store
import llm.groq_client as groq_client
import scripts.explain_live_smoke as explain_smoke
import scripts.print_recent_explanations as print_exp


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_real_chunks_refuses_on_mysql(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "mysql")
    test_args = ["explain_live_smoke.py", "--real-chunks"]
    monkeypatch.setattr(sys, "argv", test_args)

    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with patch("sys.stderr", err_buf), patch("sys.stdout", out_buf):
        ret = explain_smoke.main()

    assert ret == 1
    assert "--real-chunks only supports the local SQLite store" in err_buf.getvalue()


def test_real_chunks_refuses_when_db_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    missing_db = str(tmp_path / "missing_guidelines.db")
    monkeypatch.setenv("LOCAL_DB_PATH", missing_db)
    monkeypatch.setenv("GROQ_API_KEY", "dummy_groq_key")

    test_args = ["explain_live_smoke.py", "--real-chunks"]
    monkeypatch.setattr(sys, "argv", test_args)

    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with patch("sys.stderr", err_buf), patch("sys.stdout", out_buf):
        ret = explain_smoke.main()

    assert ret == 1
    assert f"Local store not found at {missing_db}" in err_buf.getvalue()


def test_real_chunks_refuses_when_no_chunks_for_condition(monkeypatch, tmp_path):
    db_file = str(tmp_path / "empty_chunks.db")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("GROQ_API_KEY", "dummy_groq_key")

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    test_args = ["explain_live_smoke.py", "--real-chunks", "--condition", "hypertension"]
    monkeypatch.setattr(sys, "argv", test_args)

    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with patch("sys.stderr", err_buf), patch("sys.stdout", out_buf):
        ret = explain_smoke.main()

    assert ret == 1
    assert "0 hypertension chunks found in store" in err_buf.getvalue()


def test_real_chunks_refuses_when_diabetes_has_no_ada_chunks(monkeypatch, tmp_path):
    db_file = str(tmp_path / "idf_only_chunks.db")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("GROQ_API_KEY", "dummy_groq_key")

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        cur.execute(
            f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            ("c_idf_1", "idf_dar_2021", "IDF Ramadan", "diabetes", "Fasting glucose management in Ramadan.", "2026-11-06T00:00:00Z"),
        )

    test_args = ["explain_live_smoke.py", "--real-chunks", "--condition", "diabetes"]
    monkeypatch.setattr(sys, "argv", test_args)

    err_buf = io.StringIO()
    out_buf = io.StringIO()
    with patch("sys.stderr", err_buf), patch("sys.stdout", out_buf):
        ret = explain_smoke.main()

    assert ret == 1
    assert "Diabetes condition selected but no ADA 2026 chunks found in store" in err_buf.getvalue()
    assert "Follow the permission steps in docs/tasks/WEEK3_USMAN.md" in err_buf.getvalue()


def test_real_chunks_execution_and_preservation(monkeypatch, tmp_path):
    source_db = str(tmp_path / "valid_guidelines.db")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("LOCAL_DB_PATH", source_db)
    monkeypatch.setenv("GROQ_API_KEY", "dummy_groq_key")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    app_store.migrate(db_path=source_db, backend="sqlite")
    local_store.init_db(db_path=source_db)

    with app_store.get_db_cursor(backend="sqlite", db_path=source_db) as (cur, be, ph):
        cur.execute(
            f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            ("c_real_htn_1", "ish_2020_htn", "BP Targets", "hypertension", "Target blood pressure for adults is below 130/80 mmHg.", "2026-11-06T00:00:00Z"),
        )

    # Checkpoint pending WAL writes before recording initial hash
    import sqlite3
    with sqlite3.connect(source_db) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    hash_before = _file_hash(source_db)

    # Use 1 single check-in for fast test execution
    single_checkin = [
        {"cond": "hypertension", "bp_sys": 135.0, "bp_dia": 85.0, "glucose": None, "lang": "en"}
    ]
    monkeypatch.setattr(explain_smoke, "htn_checkins", single_checkin)

    # Mock groq client so no network/LLM calls happen
    fake_llm_json = json.dumps({
        "sentences": [
            {"text": "Target blood pressure for adults is below 130/80 mmHg according to clinical guidelines.", "cites": ["S1"]},
            {"text": "Regular blood pressure monitoring helps ensure your treatment remains safe and effective.", "cites": ["S1"]},
        ]
    })
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_detailed_usage", lambda **k: (fake_llm_json, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}))

    test_args = ["explain_live_smoke.py", "--real-chunks", "--condition", "hypertension", "--pause", "0.0", "--mode", "inline"]
    monkeypatch.setattr(sys, "argv", test_args)

    out_buf = io.StringIO()
    with patch("sys.stdout", out_buf):
        ret = explain_smoke.main()

    assert ret == 0
    output = out_buf.getvalue()

    # Invariant: source DB was never modified (exact hash match)
    hash_after = _file_hash(source_db)
    assert hash_after == hash_before, "Original database file was mutated during --real-chunks run!"

    # Header and diagnostics checks
    assert "CHUNKS: real loaded corpus (copy of " in output
    assert "Total chunks in store: 1" in output
    assert "- ish_2020_htn: 1" in output

    # S3: Chunk & Source IDs in row and summary
    assert "c_real_htn_1 [ish_2020_htn]" in output
    assert "'ish_2020_htn': 1" in output

    # S4 & Temp DB outside repo assertions
    match = re.search(r"Temp Database:\s+(.+)", output)
    assert match is not None, "Temp Database path not printed in output"
    raw_temp_db_str = match.group(1).strip()
    temp_db_path = Path(raw_temp_db_str).resolve()

    assert temp_db_path.exists(), f"Temp database {temp_db_path} should be preserved with --real-chunks"
    assert not temp_db_path.is_relative_to(REPO_ROOT.resolve()), f"Temp database {temp_db_path} must be outside repo root {REPO_ROOT}"
    assert "This file contains licensed guideline text: delete it after review." in output
    assert f"Review with:   python scripts/print_recent_explanations.py --db {raw_temp_db_str}" in output

    # Cleanup temp db created by test
    try:
        temp_db_path.unlink(missing_ok=True)
    except OSError:
        pass


def test_synthetic_mode_behavior(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("GROQ_API_KEY", "dummy_groq_key")
    monkeypatch.setenv("GEMINI_API_KEY", "")

    single_checkin = [
        {"cond": "hypertension", "bp_sys": 135.0, "bp_dia": 85.0, "glucose": None, "lang": "en"}
    ]
    monkeypatch.setattr(explain_smoke, "htn_checkins", single_checkin)

    fake_llm_json = json.dumps({
        "sentences": [
            {"text": "Target blood pressure for adults with hypertension is below 130/80 mmHg.", "cites": ["S1"]},
            {"text": "Regular blood pressure monitoring helps ensure your treatment remains safe and effective.", "cites": ["S1"]},
        ]
    })
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_detailed_usage", lambda **k: (fake_llm_json, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}))

    test_args = ["explain_live_smoke.py", "--condition", "hypertension", "--pause", "0.0", "--mode", "inline"]
    monkeypatch.setattr(sys, "argv", test_args)

    out_buf = io.StringIO()
    with patch("sys.stdout", out_buf):
        ret = explain_smoke.main()

    assert ret == 0
    output = out_buf.getvalue()
    assert "CHUNKS: 4 synthetic test chunks (not the real corpus)" in output

    # In synthetic mode, temp_live_smoke.db must be deleted automatically
    temp_file = REPO_ROOT / "temp_live_smoke.db"
    assert not temp_file.exists(), "temp_live_smoke.db should be automatically cleaned up in synthetic mode"


def test_print_recent_explanations_cli(tmp_path, monkeypatch):
    db_file = str(tmp_path / "cli_expl_test.db")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    app_store.migrate(db_path=db_file, backend="sqlite")

    fake_exp = {
        "status": "ready",
        "mode": "llm",
        "provider": "groq",
        "reason": "llm_validated",
        "language": "en",
        "sentences": [
            {"text": "Sample sentence 1.", "cites": ["S1"]},
        ],
    }
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        cur.execute(
            f"INSERT INTO checkin_results (checkin_id, emergency, intakes_json, requires_review, review_status, triage_level, explanation_json, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            ("chk_cli_01", 0, "[]", 0, "open", "routine", json.dumps(fake_exp), "2026-11-06T12:00:00Z"),
        )

    test_args = ["print_recent_explanations.py", "--db", db_file, "--limit", "5"]
    monkeypatch.setattr(sys, "argv", test_args)

    out_buf = io.StringIO()
    with patch("sys.stdout", out_buf):
        ret = print_exp.main()

    assert ret == 0
    out = out_buf.getvalue()
    assert "chk_cli_01" in out
    assert "Mode: llm" in out
    assert "Provider: groq" in out
    assert "Sample sentence 1." in out
