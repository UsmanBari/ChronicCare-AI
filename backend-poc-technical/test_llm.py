"""
Unit Tests for Groq LLM Client & Health Endpoints.

All tests are strictly hermetic and mock the Groq client to prevent any network calls.
CI runs without GROQ_API_KEY and must remain green.
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from llm.groq_client import chat, is_configured, get_configured_model, get_api_key

client = TestClient(app)


def test_missing_api_key_raises_error(monkeypatch):
    """Verifies that missing GROQ_API_KEY raises a clear ValueError."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        chat(messages=[{"role": "user", "content": "hello"}])


def test_missing_model_raises_error(monkeypatch):
    """Verifies that missing GROQ_MODEL without explicit parameter raises ValueError."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    
    with pytest.raises(ValueError, match="GROQ_MODEL"):
        chat(messages=[{"role": "user", "content": "hello"}], model=None)


@patch("llm.groq_client.get_client")
def test_successful_chat_mocked(mock_get_client, monkeypatch):
    """Verifies that chat() calls Groq completions and returns text content."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "mock-model")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "  Hello from Groq!  "
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = chat(messages=[{"role": "user", "content": "ping"}])
    assert result == "Hello from Groq!"
    mock_client.chat.completions.create.assert_called_once()


@patch("llm.groq_client.get_client")
def test_retry_on_transient_error(mock_get_client, monkeypatch):
    """Verifies that transient errors trigger retries up to max_retries."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "mock-model")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Success after retry"
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    # Fail on first attempt with 503 / connection error, succeed on second attempt
    mock_client.chat.completions.create.side_effect = [
        Exception("503 Service Unavailable"),
        mock_response,
    ]
    mock_get_client.return_value = mock_client

    result = chat(
        messages=[{"role": "user", "content": "retry test"}],
        max_retries=2,
    )
    assert result == "Success after retry"
    assert mock_client.chat.completions.create.call_count == 2


@patch("llm.groq_client.get_client")
def test_retry_exhaustion_raises_error(mock_get_client, monkeypatch):
    """Verifies that persistent transient errors raise an exception after retries are exhausted."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "mock-model")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
    mock_get_client.return_value = mock_client

    with pytest.raises(Exception):
        chat(
            messages=[{"role": "user", "content": "fail test"}],
            max_retries=2,
        )
    # Initial attempt + 2 retries = 3 calls
    assert mock_client.chat.completions.create.call_count == 3


def test_health_endpoint_not_configured(monkeypatch):
    """Verifies /api/llm/health when env vars are missing."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    response = client.get("/api/llm/health")
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is False
    assert data["model"] is None


def test_health_endpoint_configured(monkeypatch):
    """Verifies /api/llm/health when env vars are configured."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-model-test")

    response = client.get("/api/llm/health")
    assert response.status_code == 200
    data = response.json()
    assert data["configured"] is True
    assert data["model"] == "llama-model-test"


@patch("main.chat")
def test_health_endpoint_ping_success(mock_chat, monkeypatch):
    """Verifies /api/llm/health?ping=true makes a ping completion."""
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.setenv("GROQ_MODEL", "llama-model-test")
    mock_chat.return_value = "pong"

    response = client.get("/api/llm/health?ping=true")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert isinstance(data["latency_ms"], int)
    mock_chat.assert_called_once()
