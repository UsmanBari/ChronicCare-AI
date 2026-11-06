"""
Unit Tests for Reviewer Utility scripts/print_recent_explanations.py (Q5).
"""
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_sources import app_store
from scripts.print_recent_explanations import print_recent_explanations


def test_refuses_to_run_on_mysql(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "mysql")
    ret = print_recent_explanations()
    assert ret == 1, "Script must refuse to run on MySQL backend and return non-zero"


def test_successful_run_on_sqlite(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_expl_review.db")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)

    app_store.migrate(db_path=db_file, backend="sqlite")

    # Insert fake checkin result with explanation
    fake_cid = "chk-review-001"
    fake_uid = "secret-user-id-do-not-print-12345"
    fake_email = "secret-patient@test.com"
    fake_res = {"level": "review", "language": "en"}
    fake_exp = {
        "status": "ready",
        "mode": "llm",
        "provider": "groq",
        "reason": "llm_validated",
        "language": "en",
        "sentences": [
            {"text": "Your blood pressure of 145/92 mmHg has been recorded for clinical review.", "cites": ["S1"]},
            {"text": "Regular monitoring helps optimize cardiovascular therapy.", "cites": ["S1"]},
        ],
    }

    fake_intakes = [{"condition": "hypertension", "level": "review"}]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        cur.execute(
            f"INSERT INTO checkin_results (checkin_id, emergency, intakes_json, requires_review, review_status, triage_level, explanation_json, created_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            (fake_cid, 0, json.dumps(fake_intakes), 1, "open", "review", json.dumps(fake_exp), "2026-11-05T10:00:00Z"),
        )

    buf = io.StringIO()
    with patch("sys.stdout", buf):
        ret = print_recent_explanations(limit=5, db_path=db_file)

    assert ret == 0
    output = buf.getvalue()
    assert "chk-review-001" in output
    assert "Mode: llm" in output
    assert "Provider: groq" in output
    assert "145/92 mmHg" in output
    assert "[Cites: S1]" in output

    # Invariant: Never print user IDs or emails
    assert fake_uid not in output
    assert fake_email not in output
