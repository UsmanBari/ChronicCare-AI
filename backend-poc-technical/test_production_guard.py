"""
Unit tests for Production Configuration Guard and CORS Configuration (Stage 6 D1).
"""

import os
import pytest
from fastapi.testclient import TestClient
from main import app, validate_production_config, get_cors_allowed_origins


def test_cors_allowed_origins_default_when_unset(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    origins = get_cors_allowed_origins()
    assert origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_cors_allowed_origins_parsing_and_no_wildcard(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.chroniccare.ai/, https://admin.chroniccare.ai, *")
    origins = get_cors_allowed_origins()
    assert origins == ["https://app.chroniccare.ai", "https://admin.chroniccare.ai"]
    assert "*" not in origins


def test_cors_preflight_allowed_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://my-deployed-frontend.netlify.app")
    client = TestClient(app)
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://my-deployed-frontend.netlify.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers.get("access-control-allow-origin") == "https://my-deployed-frontend.netlify.app"


def test_cors_preflight_disallowed_origin(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://my-deployed-frontend.netlify.app")
    client = TestClient(app)
    res = client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("access-control-allow-origin") != "https://malicious-site.com"


def test_production_guard_refuses_when_db_backend_not_mysql(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_config()
    assert "DB_BACKEND must be set to 'mysql'" in str(exc_info.value)


def test_production_guard_refuses_when_firebase_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_config()
    assert "FIREBASE_PROJECT_ID is required" in str(exc_info.value)


def test_production_guard_refuses_when_cors_unset(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        validate_production_config()
    assert "CORS_ALLOWED_ORIGINS is required" in str(exc_info.value)


def test_production_guard_passes_when_all_set(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_BACKEND", "mysql")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com")

    # Should not raise
    validate_production_config()


def test_production_guard_inactive_for_dev_or_unset(monkeypatch):
    # Unset APP_ENV
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    validate_production_config()

    # Development APP_ENV
    monkeypatch.setenv("APP_ENV", "development")
    validate_production_config()
