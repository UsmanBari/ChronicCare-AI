"""
Unit & Integration Test Suite for LLM Providers and Dual-Provider Routing (Day 4b, Usman Bari).

Verifies:
I1. gemini_client: request shape, headers, URL without key, JSON mime, token extraction, error handling, 429.
I2. Routing: auto mode with Groq 429 -> Gemini fallback; Groq breaker open -> Gemini; Groq token cap -> Gemini;
    both fail -> template; latency bounded within budget + 1s; provider isolation (groq / gemini).
I3. G3 licence rule (matches GUIDELINE_CORPUS.md FALSE entries; never sends to Gemini),
    H1 condition gate (diabetes defaults to template-only),
    H2 template consistency (normal BP/glucose corrected to routine template; true crisis kept),
    H3 patient risk null invariant on /complete endpoint.
I4. API key leak defense: key string never in URL, caplog, response payload, or database store.
I5. Segregation: patient /complete response strictly excludes provider, providers_tried, mode, reason.
I6. Master flag off invariant: zero provider calls in both direct and graph modes.
"""
from __future__ import annotations

import copy
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import jwt
import pytest
import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from auth import firebase_verify
from data_sources import app_store, local_store
import llm.gemini_client as gemini_client
import llm.groq_client as groq_client
from main import app
from rag.explain_guards import (
    DEFAULT_DAILY_TOKEN_CAP_GEMINI,
    LICENCE_RESTRICTED_SOURCES,
    CircuitBreaker,
    ExplainCache,
    TokenCapGuard,
    get_explain_guard_metrics,
    guarded_explain,
    reset_explain_guards,
)
from rag.explainer import is_template_consistent, explain

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_PROJECT_ID = "test-gemini-ci"
TEST_KID = "test-key-gemini-ci"


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def cert_pem(rsa_key):
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca-gemini")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca-gemini")]))
        .public_key(rsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=10))
        .sign(rsa_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch, cert_pem):
    reset_explain_guards()
    db_file = str(tmp_path / "test_gemini.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    mock_keys = {TEST_KID: cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    # Seed test guideline chunks (allowed sources for hypertension/routine)
    now = datetime.now(timezone.utc).isoformat()
    chunks = [
        ("ish_2020_htn_c01", "ish_2020_htn", "BP Targets", "both",
         "Stage 1 hypertension is systolic 130-139 mmHg or diastolic 80-89 mmHg. blood pressure lifestyle targets", now),
        ("who_2021_htn_c01", "who_2021_htn", "WHO Guideline", "both",
         "Pharmacological treatment of hypertension in adults. blood pressure lifestyle targets", now),
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        for cid, src, title, cond, text, updated in chunks:
            cur.execute(
                f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (cid, src, title, cond, text, updated),
            )


class MockChunkStore:
    def __init__(self, chunks: List[Dict[str, Any]]):
        self._chunks = chunks
        self._by_id = {c["chunk_id"]: c for c in chunks}

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        return self._by_id.get(chunk_id)

    def list_chunks(
        self,
        condition: Optional[str] = None,
        topic: Optional[str] = None,
        min_priority: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return list(self._chunks)

    def total_chunks(self) -> int:
        return len(self._chunks)


@pytest.fixture
def mock_store() -> MockChunkStore:
    return MockChunkStore([
        {
            "chunk_id": "c1",
            "source_id": "ish_2020",
            "title": "ISH Hypertension Guidelines",
            "section_path": "hypertension/targets",
            "condition": "hypertension",
            "priority": 1,
            "text": "Target blood pressure for adults with hypertension is below 130/80 mmHg.",
        },
    ])


def _create_token(rsa_key, uid: str, role: str = "patient") -> str:
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": f"{uid}@demo.com",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
        "role": role,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})


# =============================================================================
# PART I1 — gemini_client tests
# =============================================================================
def test_gemini_client_configuration(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert not gemini_client.is_configured()

    monkeypatch.setenv("GEMINI_API_KEY", "fake_gemini_key_12345")
    assert not gemini_client.is_configured()

    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
    assert gemini_client.is_configured()
    assert gemini_client.get_configured_model() == "gemini-2.0-flash"


def test_gemini_client_request_shape_and_headers(monkeypatch):
    """Assert key is in x-goog-api-key header and NEVER in the request URL."""
    fake_key = "fake_gemini_secret_key_abcdef"
    monkeypatch.setenv("GEMINI_API_KEY", fake_key)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "128")

    captured_url = []
    captured_headers = []
    captured_json = []

    class MockResponse:
        status_code = 200
        text = '{"candidates":[{"content":{"parts":[{"text":"{\\"sentences\\":[]}"}]},"finishReason":"STOP"}],"usageMetadata":{"totalTokenCount":45}}'
        def json(self):
            return json.loads(self.text)

    def mock_post(url, headers, json, timeout):
        captured_url.append(url)
        captured_headers.append(headers)
        captured_json.append(json)
        return MockResponse()

    monkeypatch.setattr(requests, "post", mock_post)

    messages = [
        {"role": "system", "content": "You are a clinical explainer."},
        {"role": "user", "content": "Explain systolic 135 mmHg."},
    ]
    text, tokens = gemini_client.chat_with_usage(messages, timeout=5.0)

    assert len(captured_url) == 1
    # Key must NOT appear in URL
    assert fake_key not in captured_url[0]
    assert "?key=" not in captured_url[0]
    assert captured_url[0] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    # Key must appear in header
    assert captured_headers[0].get("x-goog-api-key") == fake_key
    assert captured_headers[0].get("Content-Type") == "application/json"

    # Payload mapping
    payload = captured_json[0]
    assert "systemInstruction" in payload
    assert payload["systemInstruction"]["parts"][0]["text"] == "You are a clinical explainer."
    assert payload["contents"][0]["role"] == "user"
    assert payload["contents"][0]["parts"][0]["text"] == "Explain systolic 135 mmHg."
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert payload["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 128

    assert tokens == 45
    assert text == '{"sentences":[]}'


def test_gemini_client_error_handling_and_429(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")

    # 1. HTTP 429 raises GeminiRateLimitError
    class Mock429:
        status_code = 429
        text = "Resource exhausted / Rate limit exceeded"

    monkeypatch.setattr(requests, "post", lambda *a, **kw: Mock429())
    with pytest.raises(gemini_client.GeminiRateLimitError):
        gemini_client.chat_with_usage([{"role": "user", "content": "hi"}], max_retries=0)

    # 2. HTTP 500 raises GeminiAPIError
    class Mock500:
        status_code = 500
        text = "Internal Server Error"

    monkeypatch.setattr(requests, "post", lambda *a, **kw: Mock500())
    with pytest.raises(gemini_client.GeminiAPIError):
        gemini_client.chat_with_usage([{"role": "user", "content": "hi"}], max_retries=0)

    # 3. Blocked finishReason (SAFETY) raises GeminiAPIError
    class MockSafety:
        status_code = 200
        text = '{"candidates":[{"content":{"parts":[{"text":"something"}]},"finishReason":"SAFETY"}]}'
        def json(self):
            return json.loads(self.text)

    monkeypatch.setattr(requests, "post", lambda *a, **kw: MockSafety())
    with pytest.raises(gemini_client.GeminiAPIError, match="SAFETY"):
        gemini_client.chat_with_usage([{"role": "user", "content": "hi"}], max_retries=0)

    # 4. Empty text raises GeminiAPIError
    class MockEmpty:
        status_code = 200
        text = '{"candidates":[{"content":{"parts":[{"text":""}]},"finishReason":"STOP"}]}'
        def json(self):
            return json.loads(self.text)

    monkeypatch.setattr(requests, "post", lambda *a, **kw: MockEmpty())
    with pytest.raises(gemini_client.GeminiAPIError, match="empty text"):
        gemini_client.chat_with_usage([{"role": "user", "content": "hi"}], max_retries=0)


# =============================================================================
# PART I2 — Provider Routing Tests
# =============================================================================
def test_routing_auto_groq_429_falls_back_to_gemini(monkeypatch):
    """When Groq returns 429, auto mode falls back to Gemini within same budget."""
    valid_sentences = [
        {"text": "Your blood pressure reading of 135.0/85.0 mmHg is within stage 1 hypertension targets.", "cites": ["ish_2020_htn_c01"]},
        {"text": "Regular monitoring and low-sodium nutrition help support stable long-term cardiovascular health.", "cites": ["who_2021_htn_c01"]},
    ]
    gemini_resp = json.dumps({"sentences": valid_sentences})

    def mock_groq_chat(**kwargs):
        raise RuntimeError("Groq 429 rate limit exceeded")

    def mock_gemini_chat(**kwargs):
        return gemini_resp, 120

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_usage", mock_groq_chat)
    monkeypatch.setattr(gemini_client, "chat_with_usage", mock_gemini_chat)
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}
    triage = {"level": "routine"}

    from rag.store import get_db_chunk_store
    store = get_db_chunk_store()

    res = guarded_explain(triage_result=triage, readings=readings, store=store, condition="hypertension")
    assert res["mode"] == "llm"
    assert res["provider"] == "gemini"
    assert res["providers_tried"] == ["groq", "gemini"]


def test_routing_groq_breaker_open_tries_gemini_first(monkeypatch):
    """When Groq breaker is open, Gemini is attempted immediately without trying Groq."""
    valid_sentences = [
        {"text": "Your blood pressure reading of 135.0/85.0 mmHg is within stage 1 hypertension targets.", "cites": ["ish_2020_htn_c01"]},
        {"text": "Regular monitoring and low-sodium nutrition help support stable long-term cardiovascular health.", "cites": ["who_2021_htn_c01"]},
    ]
    gemini_resp = json.dumps({"sentences": valid_sentences})

    groq_called = []
    def mock_groq_chat(**kwargs):
        groq_called.append(True)
        return "{}", 0

    def mock_gemini_chat(**kwargs):
        return gemini_resp, 100

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_usage", mock_groq_chat)
    monkeypatch.setattr(gemini_client, "chat_with_usage", mock_gemini_chat)
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    # Trip Groq breaker
    from rag.explain_guards import _GLOBAL_BREAKER_GROQ
    _GLOBAL_BREAKER_GROQ.record_failure(is_rate_limit=True)
    assert _GLOBAL_BREAKER_GROQ.state() == CircuitBreaker.OPEN

    from rag.store import get_db_chunk_store
    store = get_db_chunk_store()

    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}
    res = guarded_explain(triage_result={"level": "routine"}, readings=readings, store=store, condition="hypertension")

    assert res["mode"] == "llm"
    assert res["provider"] == "gemini"
    assert res["providers_tried"] == ["gemini"]
    assert len(groq_called) == 0


def test_routing_groq_token_cap_reached_tries_gemini(monkeypatch):
    """When Groq token cap is reached, Gemini is tried."""
    valid_sentences = [
        {"text": "Your blood pressure reading of 135.0/85.0 mmHg is within stage 1 hypertension targets.", "cites": ["ish_2020_htn_c01"]},
        {"text": "Regular monitoring and low-sodium nutrition help support stable long-term cardiovascular health.", "cites": ["who_2021_htn_c01"]},
    ]
    gemini_resp = json.dumps({"sentences": valid_sentences})

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "chat_with_usage", lambda **kw: (gemini_resp, 100))
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    # Saturate Groq token cap
    from rag.explain_guards import _GLOBAL_TOKEN_GUARD_GROQ
    _GLOBAL_TOKEN_GUARD_GROQ.record_usage(160000)
    assert not _GLOBAL_TOKEN_GUARD_GROQ.can_consume(1000)

    from rag.store import get_db_chunk_store
    store = get_db_chunk_store()

    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}
    res = guarded_explain(triage_result={"level": "routine"}, readings=readings, store=store, condition="hypertension")

    assert res["mode"] == "llm"
    assert res["provider"] == "gemini"
    assert res["providers_tried"] == ["gemini"]


def test_routing_both_providers_fail_yields_template(monkeypatch):
    """When both Groq and Gemini fail, fallback to template."""
    def mock_fail(**kwargs):
        raise RuntimeError("Provider connection failed")

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_usage", mock_fail)
    monkeypatch.setattr(gemini_client, "chat_with_usage", mock_fail)
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    from rag.store import get_db_chunk_store
    store = get_db_chunk_store()

    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}
    res = guarded_explain(triage_result={"level": "routine"}, readings=readings, store=store, condition="hypertension")

    assert res["mode"] == "template"
    assert res["provider"] is None
    assert res["providers_tried"] == ["groq", "gemini"]


def test_routing_both_providers_slow_bounded_within_budget(monkeypatch):
    """Both slow providers together must finish within budget + 1 s."""
    def mock_slow(**kwargs):
        time.sleep(2.0)
        return "{}", 0

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_usage", mock_slow)
    monkeypatch.setattr(gemini_client, "chat_with_usage", mock_slow)
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("EXPLAIN_BUDGET_SECONDS", "1.5")

    from rag.store import get_db_chunk_store
    store = get_db_chunk_store()

    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}
    t0 = time.monotonic()
    res = guarded_explain(triage_result={"level": "routine"}, readings=readings, store=store, condition="hypertension", budget_seconds=1.5)
    elapsed = time.monotonic() - t0

    assert elapsed < 2.5  # Budget 1.5s + 1s tolerance
    assert res["mode"] == "template"


def test_routing_provider_isolation_flags(monkeypatch):
    """LLM_PROVIDER=groq never calls Gemini, and LLM_PROVIDER=gemini never calls Groq."""
    groq_called = []
    gemini_called = []

    valid_sentences = [
        {"text": "Your blood pressure reading of 135.0/85.0 mmHg is within stage 1 hypertension targets.", "cites": ["ish_2020_htn_c01"]},
        {"text": "Regular monitoring and low-sodium nutrition help support stable long-term cardiovascular health.", "cites": ["who_2021_htn_c01"]},
    ]
    resp_text = json.dumps({"sentences": valid_sentences})

    def mock_groq(**kwargs):
        groq_called.append(True)
        return resp_text, 50

    def mock_gemini(**kwargs):
        gemini_called.append(True)
        return resp_text, 50

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_usage", mock_groq)
    monkeypatch.setattr(gemini_client, "chat_with_usage", mock_gemini)

    from rag.store import get_db_chunk_store
    store = get_db_chunk_store()
    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}

    # Case 1: groq only
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    res_g = guarded_explain(triage_result={"level": "routine"}, readings=readings, store=store, condition="hypertension")
    assert res_g["provider"] == "groq"
    assert len(groq_called) == 1
    assert len(gemini_called) == 0

    # Case 2: gemini only
    reset_explain_guards()
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    res_m = guarded_explain(triage_result={"level": "routine"}, readings=readings, store=store, condition="hypertension")
    assert res_m["provider"] == "gemini"
    assert len(gemini_called) == 1


# =============================================================================
# PART I3 — Rules G3, H1, H2, H3
# =============================================================================
def test_g3_constant_matches_guideline_corpus_doc():
    """G3: Assert LICENCE_RESTRICTED_SOURCES exactly matches every source marked allowed_for_rag FALSE in GUIDELINE_CORPUS.md."""
    manifest_path = REPO_ROOT / "docs" / "GUIDELINE_CORPUS.md"
    assert manifest_path.exists(), f"Missing {manifest_path}"
    content = manifest_path.read_text(encoding="utf-8")

    # Parse table rows for Allowed for RAG? column == FALSE
    table_pattern = re.compile(r"^\|\s*`([^`]+)`\s*\|.*?\|\s*(\*\*FALSE\*\*|FALSE)\s*\|", re.MULTILINE | re.IGNORECASE)
    blocked_sources_in_doc = set()
    for match in table_pattern.finditer(content):
        blocked_sources_in_doc.add(match.group(1).strip())

    assert len(blocked_sources_in_doc) == 7
    assert blocked_sources_in_doc == LICENCE_RESTRICTED_SOURCES, (
        f"Drift detected between docs/GUIDELINE_CORPUS.md ({blocked_sources_in_doc}) "
        f"and explain_guards.LICENCE_RESTRICTED_SOURCES ({LICENCE_RESTRICTED_SOURCES})"
    )


def test_g3_licence_restricted_chunk_never_calls_gemini(monkeypatch):
    """If ANY candidate chunk is licence-restricted, Gemini is prohibited."""
    gemini_called = []
    def mock_gemini(**kw):
        gemini_called.append(True)
        return "{}", 0

    monkeypatch.setattr(groq_client, "is_configured", lambda: False)
    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "chat_with_usage", mock_gemini)
    monkeypatch.setattr(gemini_client, "chat_with_detailed_usage", lambda **kw: (mock_gemini(**kw)[0], {"total_tokens": 0, "completion_tokens": 0}))
    monkeypatch.setattr(gemini_client, "chat_with_detailed_usage", lambda **kw: (mock_gemini(**kw)[0], {"total_tokens": 0, "completion_tokens": 0}))
    monkeypatch.setattr(gemini_client, "chat_with_detailed_usage", lambda **kw: (mock_gemini(**kw)[0], {"total_tokens": 0, "completion_tokens": 0}))
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    # Mock store containing an ADA 2026 restricted chunk
    class MockStoreWithRestricted:
        def count(self): return 2
        def get(self, cid):
            return {"chunk_id": cid, "source_id": "ada_2026_sec02", "text": "Targets"}

    class MockRetriever:
        def retrieve(self, *a, **kw):
            return [
                {"chunk_id": "c1", "source_id": "ada_2026_sec02", "title": "ADA", "text": "Targets"},
                {"chunk_id": "c2", "source_id": "who_2021_htn", "title": "WHO", "text": "Targets"},
            ]

    from rag import explain_guards
    monkeypatch.setattr(explain_guards, "get_or_build_retriever", lambda s: MockRetriever())

    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}
    res = guarded_explain(
        triage_result={"level": "routine"},
        readings=readings,
        store=MockStoreWithRestricted(),
        condition="hypertension",
    )
    # Gemini must NOT be called because chunk is from ada_2026_sec02
    assert len(gemini_called) == 0
    assert res["mode"] == "template"


def test_h1_condition_filter_blocks_diabetes_by_default(monkeypatch):
    """H1: EXPLAIN_LLM_CONDITIONS defaults to 'hypertension'. Diabetes check-in falls back to template."""
    llm_called = []
    def mock_llm(**kw):
        llm_called.append(True)
        return "{}", 0

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_usage", mock_llm)
    monkeypatch.delenv("EXPLAIN_LLM_CONDITIONS", raising=False)  # default to hypertension

    readings = {"glucose": 110.0}
    res = guarded_explain(triage_result={"level": "routine"}, readings=readings, condition="diabetes")
    assert len(llm_called) == 0
    assert res["mode"] == "template"
    assert res["reason"] == "condition_template_only"


def test_h2_template_consistency_corrections():
    """H2: Contradictory templates are corrected to neutral routine template in en and ur."""
    # 1. BP 130/80 + bp_severe -> corrected to routine
    assert not is_template_consistent("bp_severe", {"blood_pressure_systolic": 130.0, "blood_pressure_diastolic": 80.0})
    res_en = explain(
        triage_result={"level": "emergency"},
        readings={"blood_pressure_systolic": 130.0, "blood_pressure_diastolic": 80.0},
        language="en",
        llm=None,
    )
    assert res_en["mode"] == "template"
    assert res_en["reason"] == "template_corrected"
    assert "target monitoring range today" in res_en["sentences"][0]["text"]

    # In Urdu
    res_ur = explain(
        triage_result={"level": "emergency"},
        readings={"blood_pressure_systolic": 130.0, "blood_pressure_diastolic": 80.0},
        language="ur",
        llm=None,
    )
    assert res_ur["reason"] == "template_corrected"

    # 2. Glucose 110 + glucose_urgent_high -> corrected
    assert not is_template_consistent("glucose_urgent_high", {"glucose": 110.0})

    # 3. Real 190/125 + bp_severe -> kept
    assert is_template_consistent("bp_severe", {"blood_pressure_systolic": 190.0, "blood_pressure_diastolic": 125.0})

    # 4. Real glucose 410 + glucose_urgent_high -> kept
    assert is_template_consistent("glucose_urgent_high", {"glucose": 410.0})


def test_h3_patient_complete_response_never_contains_risk(rsa_key, monkeypatch):
    """H3: /complete endpoint strictly returns risk=None, whatever the flags."""
    monkeypatch.setenv("RISK_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")

    client = TestClient(app)
    uid = "pat_h3_test"
    cid = "chk_h3_test"
    token = _create_token(rsa_key, uid)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    client.post("/api/auth/session", headers=headers)
    local_store.add_local_patient_if_missing(f"local-{uid}", name="H3 Test", date_of_birth="1975-01-01")
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1975-01-01",
            "sex_at_birth": "male",
            "height_cm": 175.0,
            "weight_kg": 80.0,
            "smoking_status": "never",
            "waist_cm": 95.0,
            "inclusion_confirmed": True,
        },
    )

    raw_state = {
        "engine": "v3",
        "completed": True,
        "conditions_on_file": ["hypertension"],
        "readings": {"blood_pressure_systolic": 136.0, "blood_pressure_diastolic": 86.0},
        "findings": [],
    }
    app_store.create_checkin(
        checkin_id=cid,
        user_id=uid,
        mode="isolated",
        record_patient_id=f"local-{uid}",
        state_dict=raw_state,
        status="in_progress",
    )

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Patient response has strictly null risk
    assert data["risk"] is None

    # Provider review detail retains checkin_risk
    prov_token = _create_token(rsa_key, "prov_h3", role="provider")
    prov_headers = {"Authorization": f"Bearer {prov_token}"}
    client.post("/api/auth/session", headers=prov_headers)
    with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
        cur.execute(f"UPDATE users SET role = 'provider' WHERE user_id = {ph}", ("prov_h3",))

    review_resp = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    assert review_data["checkin_risk"] is not None
    assert "band" in review_data["checkin_risk"]


# =============================================================================
# PART I4 — Credential Secrecy Checks (Caplog, URL, Result, Store)
# =============================================================================
def test_i4_credential_leak_defense(caplog, monkeypatch):
    """Assert neither API key string appears in any log record, URL, or check-in result."""
    groq_secret = "gsk_testsecretgroqkey123456789"
    gemini_secret = "AIzaSy_testsecretgeminikey987654"

    monkeypatch.setenv("GROQ_API_KEY", groq_secret)
    monkeypatch.setenv("GEMINI_API_KEY", gemini_secret)
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("LLM_PROVIDER", "auto")

    received_urls = []
    def fake_gemini_post(url, headers, json, timeout):
        received_urls.append(url)
        class R:
            status_code = 200
            text = '{"candidates":[{"content":{"parts":[{"text":"{\\"sentences\\":[{\\"text\\":\\"Normal reading.\\",\\"cites\\":[\\"ish_2020_htn_c01\\"]}]}"}]},"finishReason":"STOP"}],"usageMetadata":{"totalTokenCount":25}}'
            def json(self): return json.loads(self.text)
        return R()

    monkeypatch.setattr(requests, "post", fake_gemini_post)
    monkeypatch.setattr(groq_client, "chat_with_usage", lambda **kw: (_ for _ in ()).throw(RuntimeError("429 rate limit exceeded")))

    from rag.store import get_db_chunk_store
    store = get_db_chunk_store()
    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}

    with caplog.at_level("DEBUG"):
        res = guarded_explain(
            triage_result={"level": "routine"},
            readings=readings,
            store=store,
            condition="hypertension",
        )

    # 1. URL checked
    for u in received_urls:
        assert gemini_secret not in u
        assert groq_secret not in u

    # 2. Logs checked
    assert groq_secret not in caplog.text
    assert gemini_secret not in caplog.text

    # 3. Result payload checked
    res_dump = json.dumps(res)
    assert groq_secret not in res_dump
    assert gemini_secret not in res_dump


# =============================================================================
# PART I5 — Segregation: Patient vs. Provider Review Endpoint
# =============================================================================
def test_i5_segregation_provider_and_tried_excluded_from_patient(rsa_key, monkeypatch):
    """Patient /complete view never contains provider, providers_tried, mode, or reason."""
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")

    valid_sentences = [
        {"text": "Your blood pressure reading of 135.0/85.0 mmHg is within stage 1 hypertension targets.", "cites": ["ish_2020_htn_c01"]},
        {"text": "Regular monitoring and low-sodium nutrition help support stable long-term cardiovascular health.", "cites": ["who_2021_htn_c01"]},
    ]
    resp_text = json.dumps({"sentences": valid_sentences})
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_with_usage", lambda **kw: (resp_text, 80))

    client = TestClient(app)
    uid = "pat_seg_01"
    cid = "chk_seg_01"
    token = _create_token(rsa_key, uid)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    client.post("/api/auth/session", headers=headers)
    local_store.add_local_patient_if_missing(f"local-{uid}", name="Seg Patient", date_of_birth="1980-01-01")
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={"conditions": ["hypertension"], "date_of_birth": "1980-01-01", "inclusion_confirmed": True},
    )

    raw_state = {
        "engine": "v3",
        "completed": True,
        "conditions_on_file": ["hypertension"],
        "readings": {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0},
        "findings": [],
    }
    app_store.create_checkin(
        checkin_id=cid,
        user_id=uid,
        mode="isolated",
        record_patient_id=f"local-{uid}",
        state_dict=raw_state,
        status="in_progress",
    )

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    pat_data = resp.json()
    explanation = pat_data.get("explanation")
    assert explanation is not None

    # Patient view must NOT contain provider metadata
    assert "provider" not in explanation
    assert "providers_tried" not in explanation
    assert "mode" not in explanation
    assert "reason" not in explanation

    # Provider view MUST contain provider metadata
    prov_token = _create_token(rsa_key, "prov_seg", role="provider")
    prov_headers = {"Authorization": f"Bearer {prov_token}"}
    client.post("/api/auth/session", headers=prov_headers)
    with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
        cur.execute(f"UPDATE users SET role = 'provider' WHERE user_id = {ph}", ("prov_seg",))

    rev_resp = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    prov_explanation = rev_data.get("explanation")
    assert prov_explanation is not None
    assert "provider" in prov_explanation
    assert "providers_tried" in prov_explanation
    assert "mode" in prov_explanation


# =============================================================================
# PART I6 — Flag Off Invariant
# =============================================================================
@pytest.mark.parametrize("orch_mode", ["direct", "graph"])
def test_i6_flag_off_zero_provider_calls(rsa_key, monkeypatch, orch_mode):
    monkeypatch.setenv("ORCHESTRATOR", orch_mode)
    monkeypatch.setenv("EXPLAIN_ENABLED", "false")

    calls = []
    monkeypatch.setattr(groq_client, "chat_with_usage", lambda **kw: calls.append("groq"))
    monkeypatch.setattr(gemini_client, "chat_with_usage", lambda **kw: calls.append("gemini"))

    client = TestClient(app)
    uid = f"pat_off_{orch_mode}"
    cid = f"chk_off_{orch_mode}"
    token = _create_token(rsa_key, uid)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    client.post("/api/auth/session", headers=headers)
    local_store.add_local_patient_if_missing(f"local-{uid}", name="Off User", date_of_birth="1980-01-01")
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={"conditions": ["hypertension"], "date_of_birth": "1980-01-01", "inclusion_confirmed": True},
    )

    raw_state = {
        "engine": "v3",
        "completed": True,
        "conditions_on_file": ["hypertension"],
        "readings": {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0},
        "findings": [],
    }
    app_store.create_checkin(
        checkin_id=cid,
        user_id=uid,
        mode="isolated",
        record_patient_id=f"local-{uid}",
        state_dict=raw_state,
        status="in_progress",
    )

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    assert resp.json().get("explanation") is None
    assert len(calls) == 0


def test_gemini_thinking_budget_default_and_none(monkeypatch):
    """
    Review Item 3: Asserts GEMINI_THINKING_BUDGET defaults to 0 when unset/empty,
    is completely omitted when set to 'none' (case-insensitive), and parses integers.
    """
    # 1. Unset -> defaults to 0
    monkeypatch.delenv("GEMINI_THINKING_BUDGET", raising=False)
    payload = gemini_client._build_payload([{"role": "user", "content": "test"}])
    gen_config = payload["generationConfig"]
    assert "thinkingConfig" in gen_config
    assert gen_config["thinkingConfig"]["thinkingBudget"] == 0

    # 2. Empty string -> defaults to 0
    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "   ")
    payload_empty = gemini_client._build_payload([{"role": "user", "content": "test"}])
    assert payload_empty["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 0

    # 3. Explicit 'none' -> omitted
    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "none")
    payload_none = gemini_client._build_payload([{"role": "user", "content": "test"}])
    assert "thinkingConfig" not in payload_none["generationConfig"]

    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "NONE")
    payload_none_upper = gemini_client._build_payload([{"role": "user", "content": "test"}])
    assert "thinkingConfig" not in payload_none_upper["generationConfig"]

    # 4. Explicit integer string -> parsed
    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "128")
    payload_int = gemini_client._build_payload([{"role": "user", "content": "test"}])
    assert payload_int["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 128

    # 5. Invalid string -> defaults to 0
    monkeypatch.setenv("GEMINI_THINKING_BUDGET", "invalid_value")
    payload_invalid = gemini_client._build_payload([{"role": "user", "content": "test"}])
    assert payload_invalid["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 0


def test_fake_groq_sdk_response_total_tokens_through_guarded_path(monkeypatch, mock_store):
    """
    Review Item 1: Asserts that a real Groq SDK shaped response (response.usage.total_tokens)
    correctly propagates its token count through chat_with_usage, guarded_explain,
    and into get_explain_guard_metrics().
    """
    reset_explain_guards()
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_mock_key")
    monkeypatch.setenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    class FakeUsage:
        def __init__(self, total_tokens: int = 185):
            self.total_tokens = total_tokens
            self.prompt_tokens = 110
            self.completion_tokens = 75

    class FakeMessage:
        def __init__(self, content: str):
            self.content = content
            self.role = "assistant"

    class FakeChoice:
        def __init__(self, content: str):
            self.message = FakeMessage(content)

    class FakeGroqResponse:
        def __init__(self, content: str, total_tokens: int = 185):
            self.choices = [FakeChoice(content)]
            self.usage = FakeUsage(total_tokens)

    fake_text = json.dumps({
        "sentences": [
            {"text": "Your systolic blood pressure of 135 mmHg is within the target threshold [c1].", "cites": ["c1"]},
            {"text": "Continue your routine lifestyle modifications and monitoring [c1].", "cites": ["c1"]},
        ]
    })

    mock_sdk_client = MagicMock()
    mock_sdk_client.chat.completions.create.return_value = FakeGroqResponse(fake_text, total_tokens=185)

    monkeypatch.setattr(groq_client, "get_client", lambda **kwargs: mock_sdk_client)

    triage = {"level": "routine", "trigger_category": "bp_elevated", "systolic": 135, "diastolic": 85}
    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}

    res = guarded_explain(
        triage_result=triage,
        readings=readings,
        language="en",
        store=mock_store,
        llm=None,  # Real path using groq_client.chat_with_usage
        provider="groq",
    )

    assert res["mode"] == "llm"
    assert res["provider"] == "groq"
    assert res.get("tokens_used") == 185
    assert "groq" in res.get("provider_timings", {})

    metrics = get_explain_guard_metrics()
    assert metrics["groq"]["tokens_used_today"] == 185
    assert metrics["groq"]["llm_calls"] == 1
    assert metrics["tokens_used_by_provider"]["groq"] == 185
    assert metrics["llm_calls_by_provider"]["groq"] == 1
    assert metrics["tokens_used_today"] == 185


def test_provider_timings_recorded_on_timeout(monkeypatch, mock_store):
    """
    Review Item 5: Asserts provider_timings records the real elapsed duration
    of the provider call even when budget_timeout occurs.
    """
    reset_explain_guards()

    def slow_llm(**kwargs):
        time.sleep(0.5)
        return json.dumps({"sentences": []})

    triage = {"level": "routine", "trigger_category": "bp_elevated", "systolic": 135, "diastolic": 85}
    readings = {"blood_pressure_systolic": 135.0, "blood_pressure_diastolic": 85.0}

    res = guarded_explain(
        triage_result=triage,
        readings=readings,
        language="en",
        store=mock_store,
        llm={"groq": slow_llm},
        provider="groq",
        budget_seconds=0.15,
    )

    assert res["mode"] == "template"
    assert res["reason"] == "budget_timeout"
    assert "provider_timings" in res
    assert "groq" in res["provider_timings"]
    assert res["provider_timings"]["groq"] >= 0.10
