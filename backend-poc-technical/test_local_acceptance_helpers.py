"""
Hermetic unit tests for scripts/local_acceptance.py pure helper functions.

Covers:
1. Target URL validation (accepts localhost:8000 / 127.0.0.1:8000 only; refuses external/remote hosts).
2. MySQL safety check (refuses MySQL DB_BACKEND or SET MySQL credentials; allows pure SQLite).
3. Secret masking (returns SET / NOT SET only; never exposes values).
4. Markdown summary table generation.
"""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

# Add repo root to sys.path to import local_acceptance
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.local_acceptance import (
    LocalAcceptanceRunner,
    check_mysql_safety,
    format_acceptance_table,
    mask_secret,
    validate_target_host,
)


def test_validate_target_host_accepts_localhost():
    """Accepts only localhost:8000 and 127.0.0.1:8000."""
    validate_target_host("http://localhost:8000")
    validate_target_host("http://localhost:8000/")
    validate_target_host("http://127.0.0.1:8000")
    validate_target_host("http://127.0.0.1:8000/")


def test_validate_target_host_refuses_remote():
    """Refuses any remote or non-8000 host."""
    with pytest.raises(ValueError, match="Refusing to talk to non-localhost target"):
        validate_target_host("https://chroniccare-backend-w568.onrender.com")

    with pytest.raises(ValueError, match="Refusing to talk to non-localhost target"):
        validate_target_host("http://localhost:3000")

    with pytest.raises(ValueError, match="Refusing to talk to non-localhost target"):
        validate_target_host("https://example.com")


def test_check_mysql_safety_allows_pure_sqlite():
    """Pure SQLite config status passes safety check without exception."""
    safe_config = {
        "settings": [
            {"name": "FIREBASE_PROJECT_ID", "set": True},
            {"name": "DB_BACKEND", "set": True},
            {"name": "DEMO_ROLE_MAP", "set": True},
        ],
        "flags": {
            "DB_BACKEND": "sqlite",
            "ORCHESTRATOR": "graph",
        },
    }
    # Must not raise
    check_mysql_safety(safe_config)


def test_check_mysql_safety_aborts_on_mysql_flag():
    """Aborts if DB_BACKEND is reported as mysql."""
    unsafe_config = {
        "settings": [
            {"name": "DB_BACKEND", "set": True},
        ],
        "flags": {
            "DB_BACKEND": "mysql",
        },
    }
    with pytest.raises(RuntimeError, match="FATAL: MySQL detected"):
        check_mysql_safety(unsafe_config)


def test_check_mysql_safety_aborts_on_mysql_credentials():
    """Aborts if any setting with MYSQL_ has set=True."""
    unsafe_config = {
        "settings": [
            {"name": "DB_BACKEND", "set": True},
            {"name": "MYSQL_URL", "set": True},
        ],
        "flags": {
            "DB_BACKEND": "sqlite",
        },
    }
    with pytest.raises(RuntimeError, match="FATAL: MySQL detected"):
        check_mysql_safety(unsafe_config)


def test_mask_secret():
    """Returns SET if string is non-empty, NOT SET otherwise."""
    assert mask_secret("super_secret_token_123") == "SET"
    assert mask_secret("") == "NOT SET"
    assert mask_secret(None) == "NOT SET"
    assert mask_secret("   ") == "NOT SET"


def test_format_acceptance_table():
    """Verifies markdown table formatting for results."""
    records = [
        {
            "id": "LA-01",
            "feature": "Health and admin config status (Sec 13.2)",
            "status": "PASS",
            "evidence": "HTTP 200, DB_BACKEND=sqlite",
        },
        {
            "id": "LA-20",
            "feature": "Green/Yellow/Red triage colors (Sec 15)",
            "status": "NOT BUILT YET",
            "evidence": "Planned in PR A",
        },
    ]
    table = format_acceptance_table(records)
    assert "| ID | Feature (Proposal Section) | Status | Evidence |" in table
    assert "| LA-01 | Health and admin config status (Sec 13.2) | PASS | HTTP 200, DB_BACKEND=sqlite |" in table
    assert "| LA-20 | Green/Yellow/Red triage colors (Sec 15) | NOT BUILT YET | Planned in PR A |" in table


def test_backend_session_auth_sends_bearer_header():
    """Hermetic unit test: asserts _backend_session_auth sends Authorization Bearer header."""
    from unittest.mock import MagicMock, patch

    runner = LocalAcceptanceRunner()
    fake_token = "mock-firebase-id-token-xyz"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "ok"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        headers = runner._backend_session_auth(fake_token)
        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert "headers" in call_kwargs
        assert call_kwargs["headers"].get("Authorization") == f"Bearer {fake_token}"
        assert headers.get("Authorization") == f"Bearer {fake_token}"

