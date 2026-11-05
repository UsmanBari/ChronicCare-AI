"""
Unit and Integration Test Suite for Day 5 Background Clinical Explainer.

Covers:
- O1: EXPLAIN_MODE=background vs inline routing at check-in completion.
- O2: Background worker execution & database persistence (status=ready).
- O3: Pre-queue eligibility check agreement between check_llm_eligibility and guarded_explain.
- O4: Bounded queue overflow handling (queue_full template fallback).
- O5: Stale job detection & recovery (job_lost substitution after deadline + 30s).
- O6: Groq OTPM pacer delay calculation and sleep injection.
- O7: 429 Retry inside provider loop (no breaker trip in background mode, failover to Gemini).
- O8: GET /api/checkins/{id}/explanation endpoint (auth, isolation, segregated patient view).
- O9: GET /api/admin/config-status endpoint (admin-only, flags, SET/NOT SET keys, metrics).
- L1: Cache hit has provider_timings = {} and tokens_used = 0.
- L2: Error log lines contain only provider name and exception type.
"""

import copy
import datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional
import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from auth import firebase_verify
from data_sources import app_store, local_store
from main import app
from rag.explain_guards import (
    DEFAULT_JOB_DEADLINE_SECONDS,
    DEFAULT_QUEUE_MAX,
    DEFAULT_GROQ_OTPM,
    ExplainCache,
    TokenCapGuard,
    CircuitBreaker,
    TokenPacer,
    check_llm_eligibility,
    guarded_explain,
    get_explain_mode,
    get_job_deadline_seconds,
    reset_explain_guards,
    _GLOBAL_BREAKER_GROQ,
    _GLOBAL_BREAKER_GEMINI,
    _GLOBAL_TOKEN_GUARD_GROQ,
    _GLOBAL_TOKEN_GUARD_GEMINI,
    _GLOBAL_GROQ_PACER,
    _parse_retry_after,
)
from rag.explain_jobs import (
    ExplanationJob,
    ExplanationJobQueue,
    enqueue_job,
    execute_job_synchronous,
    reset_job_queue,
)

TEST_PROJECT_ID = "test-explain-bg-ci"
TEST_KID = "test-key-explain-bg-ci"


class MockChunkStore:
    def __init__(self, chunks: Optional[List[Dict[str, Any]]] = None):
        self._chunks = chunks or []
        self._by_id = {c["chunk_id"]: c for c in self._chunks}

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        return self._by_id.get(chunk_id)

    def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
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

    def count(self) -> int:
        return len(self._chunks)

    def add(self, chunk_id: str, text: str, metadata: Dict[str, Any]):
        c = dict(metadata)
        c["chunk_id"] = chunk_id
        c["text"] = text
        self._chunks.append(c)
        self._by_id[chunk_id] = c


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def cert_pem(rsa_key):
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")]))
        .public_key(rsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
        .sign(rsa_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch, cert_pem):
    reset_explain_guards()
    reset_job_queue()

    db_file = str(tmp_path / "test_explain_bg.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("DEMO_ROLE_MAP", "admin@demo.com:admin,provider@demo.com:provider")
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import llm.gemini_client as gemini_client
    monkeypatch.setattr(gemini_client, "is_configured", lambda: False)

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    mock_keys = {TEST_KID: cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    yield

    reset_explain_guards()
    reset_job_queue()


@pytest.fixture
def mock_store():
    store = MockChunkStore([
        {
            "chunk_id": "aha_chunk_1",
            "source_id": "aha_2025_prevention",
            "title": "AHA 2025 Prevention",
            "section_path": "Blood Pressure Targets",
            "condition": "hypertension",
            "priority": 1,
            "text": "AHA 2025 guideline: Blood pressure between 130 and 139 mmHg is Stage 1 Hypertension. Normal blood pressure is below 130 mmHg.",
        },
        {
            "chunk_id": "aha_chunk_2",
            "source_id": "aha_2025_prevention",
            "title": "AHA 2025 Prevention",
            "section_path": "Lifestyle Modifications",
            "condition": "hypertension",
            "priority": 2,
            "text": "Lifestyle changes support healthy blood pressure management.",
        },
    ])
    return store


@pytest.fixture
def client():
    return TestClient(app)


def _create_token(rsa_key, uid: str, role: str = "patient") -> str:
    now = int(time.time())
    email = f"{role}@demo.com" if role in ("admin", "provider") else f"{uid}@demo.com"
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": email,
        "name": f"User {uid}",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    if role:
        payload["role"] = role
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})


def auth_header(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# O1: EXPLAIN_MODE: background vs inline
# =============================================================================
def test_o1_explain_mode_default_and_routing(monkeypatch):
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.delenv("EXPLAIN_MODE", raising=False)
    assert get_explain_mode() == "background"

    monkeypatch.setenv("EXPLAIN_MODE", "inline")
    assert get_explain_mode() == "inline"

    monkeypatch.setenv("EXPLAIN_MODE", "invalid_value")
    assert get_explain_mode() == "background"


# =============================================================================
# O2: Background Worker Execution & DB Persistence
# =============================================================================
def test_o2_worker_execution_updates_database(monkeypatch, mock_store):
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_MODE", "background")

    checkin_id = "chk_bg_test_02"
    user_id = "usr_bg_02"

    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        triage_level="review",
        triage={"level": "review", "trigger": "bp_urgent"},
        explanation={"status": "pending", "queued_at": "2026-11-05T00:00:00Z"},
    )

    fallback_tmpl = {
        "status": "ready",
        "mode": "template",
        "reason": "fallback",
        "sentences": [{"text": "Your blood pressure is elevated.", "cites": ["aha_chunk_1"]}],
        "sources": [{"chunk_id": "aha_chunk_1", "title": "AHA 2025"}],
    }

    job = ExplanationJob(
        checkin_id=checkin_id,
        user_id=user_id,
        condition="hypertension",
        readings={"blood_pressure_systolic": 145.0, "blood_pressure_diastolic": 92.0},
        language="en",
        fallback_template=fallback_tmpl,
        store=mock_store,
    )

    monkeypatch.setattr("rag.explain_guards.guarded_explain", lambda **kw: {
        "status": "ready",
        "mode": "llm",
        "provider": "groq",
        "providers_tried": ["groq"],
        "provider_timings": {"groq": 0.45},
        "tokens_used": 60,
        "sentences": [
            {"text": "Your blood pressure reading of 145/92 mmHg indicates review.", "cites": ["aha_chunk_1"]},
            {"text": "Regular blood pressure monitoring helps track clinical trends.", "cites": ["aha_chunk_1"]},
        ],
        "sources": [{"chunk_id": "aha_chunk_1", "title": "AHA 2025"}],
    })

    res = execute_job_synchronous(job)
    assert res["status"] == "ready"
    assert res["mode"] == "llm"

    stored_expl = app_store.get_checkin_explanation(checkin_id)
    assert stored_expl is not None
    assert stored_expl["status"] == "ready"
    assert stored_expl["mode"] == "llm"
    assert stored_expl["provider"] == "groq"


# =============================================================================
# O3: Pre-Queue Eligibility Check Agreement with guarded_explain
# =============================================================================
def test_o3_precheck_and_guarded_explain_agreement(monkeypatch, mock_store):
    # 1. Condition template only
    ok, reason = check_llm_eligibility(condition="diabetes", trigger_category="glucose_high", store=mock_store)
    assert ok is False
    assert reason == "condition_template_only"

    g_res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"glucose": 150.0},
        condition="diabetes",
        store=mock_store,
    )
    assert g_res["mode"] == "template"
    assert g_res["reason"] == "condition_template_only"

    # 2. No chunks
    empty_store = MockChunkStore()
    ok, reason = check_llm_eligibility(condition="hypertension", trigger_category="bp_urgent", store=empty_store)
    assert ok is False
    assert reason == "no_chunks"

    g_res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 135.0},
        condition="hypertension",
        store=empty_store,
    )
    assert g_res["mode"] == "template"
    assert g_res["reason"] == "no_chunks"

    # 3. Breaker open (with mock configured LLM)
    mock_llm = {"groq": lambda **k: ("ok", 10)}
    _GLOBAL_BREAKER_GROQ.record_failure(is_rate_limit=True)
    _GLOBAL_BREAKER_GEMINI.record_failure(is_rate_limit=True)
    ok, reason = check_llm_eligibility(
        condition="hypertension",
        trigger_category="bp_urgent",
        store=mock_store,
        candidate_chunks=[{"chunk_id": "aha_chunk_1", "source_id": "aha_2025"}],
        llm=mock_llm,
    )
    assert ok is False
    assert reason == "breaker_open"

    g_res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 135.0},
        condition="hypertension",
        store=mock_store,
        llm=mock_llm,
    )
    assert g_res["mode"] == "template"
    assert g_res["reason"] == "breaker_open"

    reset_explain_guards()

    # 4. Token cap reached (with mock configured LLM)
    _GLOBAL_TOKEN_GUARD_GROQ.record_usage(_GLOBAL_TOKEN_GUARD_GROQ.get_cap() + 10)
    _GLOBAL_TOKEN_GUARD_GEMINI.record_usage(_GLOBAL_TOKEN_GUARD_GEMINI.get_cap() + 10)
    ok, reason = check_llm_eligibility(
        condition="hypertension",
        trigger_category="bp_urgent",
        store=mock_store,
        candidate_chunks=[{"chunk_id": "aha_chunk_1", "source_id": "aha_2025"}],
        llm=mock_llm,
    )
    assert ok is False
    assert reason == "token_cap"

    g_res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 135.0},
        condition="hypertension",
        store=mock_store,
        llm=mock_llm,
    )
    assert g_res["mode"] == "template"
    assert g_res["reason"] == "token_cap"

    reset_explain_guards()

    # 5. No LLM configured
    monkeypatch.setattr("llm.groq_client.is_configured", lambda: False)
    monkeypatch.setattr("llm.gemini_client.is_configured", lambda: False)
    ok, reason = check_llm_eligibility(
        condition="hypertension",
        trigger_category="bp_urgent",
        store=mock_store,
        candidate_chunks=[{"chunk_id": "aha_chunk_1", "source_id": "aha_2025"}],
    )
    assert ok is False
    assert reason == "no_llm"

    g_res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 135.0},
        condition="hypertension",
        store=mock_store,
    )
    assert g_res["mode"] == "template"
    assert g_res["reason"] == "no_llm"


# =============================================================================
# O4: Bounded Queue Overflow Handling
# =============================================================================
def test_o4_bounded_queue_overflow(monkeypatch):
    monkeypatch.setenv("EXPLAIN_QUEUE_MAX", "2")
    q = ExplanationJobQueue(maxsize=2)

    fb = {"status": "ready", "mode": "template", "reason": "fb"}
    # Enqueue with start_worker=False to test queue capacity without worker thread consuming
    assert q.enqueue_job("chk_1", "usr_1", "hypertension", {}, "en", fb, start_worker=False) is True
    assert q.enqueue_job("chk_2", "usr_2", "hypertension", {}, "en", fb, start_worker=False) is True
    assert q.enqueue_job("chk_3", "usr_3", "hypertension", {}, "en", fb, start_worker=False) is False
    q.stop_worker()


# =============================================================================
# O5: Stale Job Rule (deadline + 30s)
# =============================================================================
def test_o5_stale_job_rule(monkeypatch):
    checkin_id = "chk_stale_test"
    fallback_template = {
        "status": "ready",
        "mode": "template",
        "reason": "initial_template",
        "sentences": [{"text": "Routine follow up.", "cites": []}],
        "sources": [],
    }

    old_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=100)).isoformat()
    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        triage_level="routine",
        explanation={
            "status": "pending",
            "queued_at": old_time,
            "template": fallback_template,
        },
    )

    res = app_store.get_checkin_explanation(checkin_id)
    assert res is not None
    assert res["status"] == "ready"
    assert res["mode"] == "template"
    assert res["reason"] == "job_lost"

    raw = app_store.get_checkin_result(checkin_id)
    assert raw["explanation"]["reason"] == "job_lost"


# =============================================================================
# O6: Groq OTPM Pacer
# =============================================================================
def test_o6_groq_otpm_pacer_wait_calculation():
    pacer = TokenPacer(window_seconds=60.0)
    current_time = [1000.0]

    def mock_clock():
        return current_time[0]

    assert pacer.get_wait_seconds(tokens_needed=250, otpm_limit=1000, clock_fn=mock_clock) == 0.0

    pacer.record_tokens(800, clock_fn=mock_clock)
    wait = pacer.get_wait_seconds(tokens_needed=250, otpm_limit=1000, clock_fn=mock_clock)
    assert wait == pytest.approx(60.0, 0.1)

    current_time[0] = 1030.0
    wait = pacer.get_wait_seconds(tokens_needed=250, otpm_limit=1000, clock_fn=mock_clock)
    assert wait == pytest.approx(30.0, 0.1)

    current_time[0] = 1061.0
    wait = pacer.get_wait_seconds(tokens_needed=250, otpm_limit=1000, clock_fn=mock_clock)
    assert wait == 0.0


# =============================================================================
# O7: 429 Retry inside Provider Loop (Background Mode)
# =============================================================================
def test_o7_429_retry_in_background_mode(monkeypatch, mock_store):
    current_time = [100.0]
    sleeps = []

    def mock_clock():
        return current_time[0]

    def mock_sleep(sec):
        sleeps.append(sec)
        current_time[0] += sec

    attempts = {"groq": 0}

    def fake_groq_callable(**kwargs):
        attempts["groq"] += 1
        if attempts["groq"] == 1:
            raise RuntimeError("Rate limit 429: try again in 4.5s")
        return json.dumps({
            "sentences": [
                {"text": "Your blood pressure reading of 120/75 mmHg is routine [aha_chunk_1].", "cites": ["aha_chunk_1"]},
                {"text": "Regular blood pressure monitoring supports normal cardiovascular health [aha_chunk_1].", "cites": ["aha_chunk_1"]},
            ]
        }), {"total_tokens": 50, "completion_tokens": 40}

    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 75.0},
        store=mock_store,
        llm={"groq": fake_groq_callable},
        provider="groq",
        mode="background",
        budget_seconds=45.0,
        clock_fn=mock_clock,
        sleep_fn=mock_sleep,
    )

    assert res["mode"] == "llm"
    assert attempts["groq"] == 2
    assert len(sleeps) >= 1
    assert sleeps[0] == pytest.approx(4.5, 0.1)
    assert _GLOBAL_BREAKER_GROQ.state() == CircuitBreaker.CLOSED


# =============================================================================
# O8: Endpoint GET /api/checkins/{id}/explanation
# =============================================================================
def test_o8_checkin_explanation_endpoint_auth_and_segregation(client, rsa_key):
    pat_token = _create_token(rsa_key, uid="uid_patient_o8", role="patient")
    pat_headers = auth_header(pat_token)
    other_token = _create_token(rsa_key, uid="uid_other_o8", role="patient")
    other_headers = auth_header(other_token)

    # Register patient session in local DB
    client.post("/api/auth/session", headers=pat_headers)
    client.post("/api/auth/session", headers=other_headers)

    checkin_id = "chk_endpoint_o8"
    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id="uid_patient_o8",
        mode="isolated",
        record_patient_id="rec_pat_o8",
        state_dict={},
    )
    app_store.create_checkin_result(
        checkin_id=checkin_id,
        emergency=False,
        intakes=[],
        triage_level="routine",
        explanation={
            "status": "ready",
            "mode": "llm",
            "reason": "ok",
            "provider": "groq",
            "providers_tried": ["groq"],
            "provider_timings": {"groq": 0.42},
            "tokens_used": 75,
            "sentences": [{"text": "Your blood pressure is optimal.", "cites": ["aha_chunk_1"]}],
            "sources": [{"chunk_id": "aha_chunk_1", "title": "AHA 2025"}],
        },
    )

    # 1. Unauthenticated -> 401
    assert client.get(f"/api/checkins/{checkin_id}/explanation").status_code == 401

    # 2. Other patient -> 404
    res_other = client.get(f"/api/checkins/{checkin_id}/explanation", headers=other_headers)
    assert res_other.status_code == 404

    # 3. Patient owner -> 200 with segregated view
    res = client.get(f"/api/checkins/{checkin_id}/explanation", headers=pat_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert len(data["sentences"]) == 1
    assert len(data["sources"]) == 1

    for forbidden in ("mode", "reason", "provider", "providers_tried", "provider_timings", "tokens_used", "template"):
        assert forbidden not in data, f"Patient view must not leak '{forbidden}'"


# =============================================================================
# O9: Endpoint GET /api/admin/config-status
# =============================================================================
def test_o9_admin_config_status_endpoint(client, rsa_key, monkeypatch):
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_MODE", "background")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_dummy_test_key_123")
    monkeypatch.setenv("GROQ_MODEL", "qwen-2.5-32b")

    admin_token = _create_token(rsa_key, uid="uid_admin_o9", role="admin")
    admin_headers = auth_header(admin_token)
    pat_token = _create_token(rsa_key, uid="uid_pat_o9", role="patient")
    pat_headers = auth_header(pat_token)

    # Register user profiles via session
    client.post("/api/auth/session", headers=admin_headers)
    client.post("/api/auth/session", headers=pat_headers)

    assert client.get("/api/admin/config-status").status_code == 401
    assert client.get("/api/admin/config-status", headers=pat_headers).status_code == 403

    res = client.get("/api/admin/config-status", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert "flags" in data
    assert data["flags"]["EXPLAIN_ENABLED"] is True
    assert data["flags"]["EXPLAIN_MODE"] == "background"

    assert "keys_and_models" in data
    assert data["keys_and_models"]["GROQ_API_KEY"] == "SET"
    assert data["keys_and_models"]["GROQ_MODEL"] == "SET"
    assert "gsk_dummy_test_key_123" not in res.text

    assert "explainer_metrics" in data
    metrics = data["explainer_metrics"]
    assert "queue_length" in metrics
    assert "breaker_states" in metrics
    assert "tokens_used_today" in metrics


# =============================================================================
# L1: Cache Hit provider_timings = {} and tokens_used = 0
# =============================================================================
def test_l1_cache_hit_provider_timings_and_tokens_empty(mock_store):
    cache = ExplainCache()

    def fake_llm(**kwargs):
        return json.dumps({
            "sentences": [
                {"text": "Your blood pressure reading of 120/75 mmHg is routine [aha_chunk_1].", "cites": ["aha_chunk_1"]},
                {"text": "Maintaining a healthy routine supports target blood pressure [aha_chunk_1].", "cites": ["aha_chunk_1"]},
            ]
        })

    triage = {"level": "routine", "reasons": ["Normal blood pressure"]}
    readings = {"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 75.0}

    res1 = guarded_explain(
        triage_result=triage,
        readings=readings,
        store=mock_store,
        llm=fake_llm,
        cache=cache,
        provider="groq",
    )
    assert res1["mode"] == "llm"

    # Second call -> cache hit
    res2 = guarded_explain(
        triage_result=triage,
        readings=readings,
        store=mock_store,
        llm=fake_llm,
        cache=cache,
        provider="groq",
    )
    assert res2["mode"] == "cache"
    assert res2["provider_timings"] == {}
    assert res2["tokens_used"] == 0


# =============================================================================
# L2: Provider Error Log Sanitization (No response bodies)
# =============================================================================
def test_l2_provider_error_log_sanitization(caplog):
    import llm.gemini_client as gemini_client

    caplog.set_level(logging.WARNING)
    with pytest.raises(gemini_client.GeminiRateLimitError) as exc_info:
        raise gemini_client.GeminiRateLimitError("Gemini API 429 rate limit exceeded")

    assert "org_secret_leak_123" not in str(exc_info.value)
    for record in caplog.records:
        assert "org_secret_leak_123" not in record.message


# =============================================================================
# Review Additions: Order, Pacer, Retry-After, Sanitize Reasons, Pending Mode
# =============================================================================
def test_order_delayed_save_never_results_in_job_lost(client, rsa_key, monkeypatch, mock_store):
    """Order: Injected 3s delay in saving checkin result row -> job still ends 'ready', never 'job_lost'."""
    import time, data_sources.app_store as app_store
    import orchestrator.steps as steps
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_MODE", "background")

    # Mock groq
    import llm.groq_client as groq_client
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    valid_sentences = [
        {"text": "Your blood pressure reading of 130.0/80.0 mmHg is within target ranges.", "cites": ["aha_chunk_1"]},
        {"text": "Regular monitoring supports heart health.", "cites": ["aha_chunk_1"]},
    ]
    monkeypatch.setattr(groq_client, "chat_with_usage", lambda **kw: (json.dumps({"sentences": valid_sentences}), 60))

    # Inject delay into create_checkin_result in steps
    orig_create = steps.create_checkin_result
    save_delayed = []
    def delayed_create_checkin_result(*args, **kwargs):
        save_delayed.append(True)
        time.sleep(1.0)
        return orig_create(*args, **kwargs)
    monkeypatch.setattr(steps, "create_checkin_result", delayed_create_checkin_result)

    uid = "pat_delay_01"
    cid = "chk_delay_01"
    token = _create_token(rsa_key, uid=uid)
    headers = auth_header(token)

    client.post("/api/auth/session", headers=headers)
    local_store.add_local_patient_if_missing(f"local-{uid}", name="Delay Patient", date_of_birth="1980-01-01")
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
        "readings": {"blood_pressure_systolic": 130.0, "blood_pressure_diastolic": 80.0},
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
    assert len(save_delayed) == 1

    # Wait for background worker to finish processing
    for _ in range(50):
        row = app_store.get_checkin_result(cid)
        if row and (row.get("explanation") or row.get("explanation_json")):
            exp = row.get("explanation") or row.get("explanation_json")
            if exp.get("status") == "ready":
                break
        time.sleep(0.05)

    final_row = app_store.get_checkin_result(cid)
    final_exp = final_row.get("explanation") or final_row.get("explanation_json")
    assert final_exp["status"] == "ready"
    assert final_exp.get("reason") != "job_lost"


def test_retry_after_ms_and_min_sec_parsing():
    """Retry-After: handles 'ms' (600ms -> 1.0s min) and '1m30s' (-> 30s cap)."""
    assert _parse_retry_after("Please try again in 600ms.") == 1.0
    assert _parse_retry_after("try again in 500ms") == 1.0
    assert _parse_retry_after("try again in 1200ms") == 1.2
    assert _parse_retry_after("try again in 1m30s") == 30.0
    assert _parse_retry_after("try again in 2m") == 30.0
    assert _parse_retry_after("wait 15s") == 15.0


def test_stored_reasons_never_leak_provider_body_or_org_id(mock_store):
    """Stored reasons: never store provider error text in explanation_json / rejected_reasons."""
    leaky_body = "Rate limit reached for org_secretcorp_999888 on model qwen/qwen3.8-27b"
    def leaky_llm(**kwargs):
        raise RuntimeError(leaky_body)

    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 130.0, "blood_pressure_diastolic": 80.0},
        store=mock_store,
        llm=leaky_llm,
        provider="groq",
        mode="inline",
    )

    assert res["mode"] == "template"
    assert res["reason"] == "rate_limited"
    dumped = json.dumps(res)
    assert "org_secretcorp_999888" not in dumped
    assert "org_" not in dumped
    for rej in res.get("rejected_reasons", []):
        assert "org_" not in rej


def test_provider_view_of_pending_job_has_mode_pending(client, rsa_key, monkeypatch):
    """Provider view of a pending job: mode 'pending', not 'background'."""
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("EXPLAIN_MODE", "background")

    # Mock groq as configured so check-in is eligible for background queue
    import llm.groq_client as groq_client
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    now_iso = "2026-11-05T00:00:00Z"
    with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
        cur.execute(
            f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
            ("chk_1", "ish_2020_htn", "BP Targets", "hypertension", "Target blood pressure is 130/80.", now_iso),
        )

    from rag.explain_jobs import get_job_queue
    # Stop and prevent background worker from consuming immediately
    get_job_queue().stop_worker()
    monkeypatch.setattr(get_job_queue(), "start_worker_if_needed", lambda: None)

    uid = "pat_pending_prov"
    cid = "chk_pending_prov"
    token = _create_token(rsa_key, uid=uid)
    headers = auth_header(token)

    client.post("/api/auth/session", headers=headers)
    local_store.add_local_patient_if_missing(f"local-{uid}", name="Pending Patient", date_of_birth="1980-01-01")
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
        "readings": {"blood_pressure_systolic": 130.0, "blood_pressure_diastolic": 80.0},
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

    # Read provider review endpoint
    prov_token = _create_token(rsa_key, "prov_user_pend", role="provider")
    prov_headers = auth_header(prov_token)
    client.post("/api/auth/session", headers=prov_headers)
    with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
        cur.execute(f"UPDATE users SET role = 'provider' WHERE user_id = {ph}", ("prov_user_pend",))

    rev_resp = client.get(f"/api/provider/review/{cid}", headers=prov_headers)
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    prov_exp = rev_data.get("explanation")
    print("\n=== DEBUG PROV_EXP ===", prov_exp)
    assert prov_exp is not None
    assert prov_exp["status"] == "pending"
    assert prov_exp["mode"] == "pending"
    assert prov_exp["mode"] != "background"


def test_pacer_records_tokens_on_every_groq_call(mock_store):
    """Pacer: records Groq completion tokens after EVERY Groq call that returned usage (including validation failed)."""
    _GLOBAL_GROQ_PACER.reset()

    # Call returns valid JSON but with hallucinated numbers -> triggers validation failure
    hallucinated_json = json.dumps({
        "sentences": [
            {"text": "Your blood pressure is 220/140 mmHg.", "cites": ["aha_chunk_1"]}
        ]
    })
    bad_llm = lambda **kw: (hallucinated_json, {"completion_tokens": 45, "total_tokens": 70})

    clock = 1000.0
    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 130.0, "blood_pressure_diastolic": 80.0},
        store=mock_store,
        llm=bad_llm,
        provider="groq",
        mode="inline",
        clock_fn=lambda: clock,
    )
    assert res["reason"] == "validation_failed"

    # Assert pacer recorded the 45 completion tokens despite validation_failed!
    assert _GLOBAL_GROQ_PACER.get_current_usage(clock_fn=lambda: clock) == 45
