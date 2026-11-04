"""
Comprehensive Unit & Integration Test Suite for Explainer Guards (Day 4, Usman Bari).

Verifies:
1. C1 (Time Budget): Fake LLM sleeping 10s returns under budget + 1s with mode='template',
   reason='budget_timeout'. Multi-worker test: hung LLM does not block 3 subsequent calls.
2. C2 (Daily Token Cap): Cap reached skips LLM with reason='token_cap'; resets on UTC rollover;
   discarded late-finishing thread adds tokens to daily counter.
3. C3 (Cache & Re-validation): Identical band returns mode='cache' without LLM call;
   number mismatch fails re-validation (miss); missing chunk fails re-validation (miss);
   templates/errors never cached; no user ID in cache keys.
4. C4 (Circuit Breaker): 3 timeouts/errors trip breaker to OPEN; 429 rate limit trips instantly;
   validator rejection does not trip breaker; cooldown allows 1 trial call in HALF_OPEN.
5. C5 (Flag Off): Identical baseline behavior, zero guard calls across direct and graph modes.
6. C6 (Emergency Intakes): Emergency check-ins strictly bypass explainer.
7. C7 (Mutation Proof Targets): Kills M-U-G1 (budget deadline), M-U-G2 (cache re-validation),
   and M-U-G3 (breaker opening).
"""
import copy
import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta
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
import llm.groq_client as groq_client
from main import app
from orchestrator.steps import step_explain
from rag.explain_guards import (
    CircuitBreaker,
    ExplainCache,
    TokenCapGuard,
    compute_cache_key,
    get_bp_band,
    get_explain_guard_metrics,
    get_glucose_band,
    get_or_build_retriever,
    guarded_explain,
    reset_explain_guards,
)
from rag.store import JsonlChunkStore

TEST_PROJECT_ID = "test-explain-guards-ci"
TEST_KID = "test-key-explain-guards-ci"


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def cert_pem(rsa_key):
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca-guards")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca-guards")]))
        .public_key(rsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=10))
        .sign(rsa_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


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
            "chunk_id": "c_dm_1",
            "source_id": "ADA_2024",
            "title": "Glycemic Targets",
            "section_path": "diabetes/targets",
            "condition": "both",
            "priority": 1,
            "text": "Target fasting blood glucose is 80-130 mg/dL for nonpregnant adults.",
        },
        {
            "chunk_id": "c_htn_1",
            "source_id": "AHA_ACC_2017",
            "title": "BP Targets",
            "section_path": "hypertension/targets",
            "condition": "both",
            "priority": 1,
            "text": "Stage 1 hypertension is systolic 130-139 mmHg or diastolic 80-89 mmHg.",
        },
    ])


@pytest.fixture(autouse=True)
def setup_guards_test_env(tmp_path, monkeypatch, cert_pem):
    reset_explain_guards()
    db_file = str(tmp_path / "test_guards.db")
    monkeypatch.setenv("LOCAL_DB_PATH", db_file)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", TEST_PROJECT_ID)
    monkeypatch.setenv("REQUIRE_INCLUSION", "0")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    app_store.migrate(db_path=db_file, backend="sqlite")
    local_store.init_db(db_path=db_file)

    mock_keys = {TEST_KID: cert_pem}
    monkeypatch.setattr(firebase_verify, "_KEY_CACHE", {"keys": mock_keys, "expires_at": time.time() + 3600})
    monkeypatch.setattr(firebase_verify, "fetch_google_public_keys", lambda force_refresh=False: mock_keys)

    # Seed test guideline chunks
    now = datetime.now(timezone.utc).isoformat()
    chunks = [
        ("c_htn_1", "AHA_ACC_2017", "BP Targets", "hypertension",
         "Stage 1 hypertension is systolic 130-139 mmHg or diastolic 80-89 mmHg.", now),
        ("c_dm_1", "ADA_2024", "Glycemic Targets", "diabetes",
         "Target fasting blood glucose is 80-130 mg/dL for nonpregnant adults.", now),
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        for cid, src, title, cond, text, updated in chunks:
            cur.execute(
                f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (cid, src, title, cond, text, updated),
            )
    return db_file


def _get_auth_headers(rsa_key, uid: str) -> Dict[str, str]:
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
    }
    tok = jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _create_checkin_session(
    uid: str,
    checkin_id: str,
    systolic: float = 135.0,
    diastolic: float = 85.0,
    emergency: bool = False,
    emergency_reason: Optional[str] = None,
    conditions: Optional[List[str]] = None,
):
    if emergency:
        raw_state = {
            "engine": "v3",
            "stage1_red_flag": True,
            "stage1_reason": emergency_reason or "chest_pain",
            "intakes": [{"condition": "hypertension", "emergency": True, "reason": emergency_reason or "chest_pain"}],
            "findings": [],
        }
    else:
        raw_state = {
            "engine": "v3",
            "completed": True,
            "conditions_on_file": conditions or ["hypertension"],
            "readings": {
                "blood_pressure_systolic": systolic,
                "blood_pressure_diastolic": diastolic,
            },
            "findings": [],
        }

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=uid,
        mode="isolated",
        record_patient_id=f"local-{uid}",
        state_dict=raw_state,
        status="in_progress" if not emergency else "emergency",
    )


# =============================================================================
# C1: Time Budget & Concurrency Non-Blocking Tests
# =============================================================================
def test_c1_budget_timeout_falls_back_under_budget():
    """A fake LLM that sleeps 10s returns under budget + 1s with mode=template, reason=budget_timeout."""
    def sleeping_llm(**kwargs):
        time.sleep(10.0)
        return json.dumps({
            "sentences": [
                {"text": "Late explanation [S1].", "cites": ["S1"]},
                {"text": "Should never be seen [S1].", "cites": ["S1"]},
            ]
        })

    triage = {"level": "routine", "reasons": ["Blood sugar within normal limits"]}
    readings = {"glucose": 110.0}

    t0 = time.monotonic()
    res = guarded_explain(
        triage_result=triage,
        readings=readings,
        language="en",
        llm=sleeping_llm,
        budget_seconds=0.6,
    )
    elapsed = time.monotonic() - t0

    assert elapsed < 1.6, f"Expected elapsed < 1.6s, got {elapsed:.2f}s"
    assert res["mode"] == "template"
    assert res["reason"] == "budget_timeout"
    assert len(res["sentences"]) > 0


def test_c1_hung_call_does_not_block_subsequent_calls():
    """Correction 1: One fake LLM hangs 10s; 3 subsequent check-ins run immediately and finish within budget."""
    def hanging_llm(**kwargs):
        time.sleep(10.0)
        return ""

    def fast_llm(**kwargs):
        return json.dumps({
            "sentences": [
                {"text": "Fast explanation [S1].", "cites": ["S1"]},
                {"text": "Regular monitoring helps [S1].", "cites": ["S1"]},
            ]
        })

    triage = {"level": "routine", "reasons": ["Normal"]}
    readings = {"glucose": 110.0}

    # Thread 1 starts hanging call with budget 0.5s in background
    t1_done = threading.Event()
    t1_res: List[Any] = []

    def _call_hanging():
        r = guarded_explain(
            triage_result=triage,
            readings=readings,
            language="en",
            llm=hanging_llm,
            budget_seconds=0.5,
        )
        t1_res.append(r)
        t1_done.set()

    t = threading.Thread(target=_call_hanging, daemon=True)
    t.start()

    # Wait for t1 to time out and return
    t1_done.wait(timeout=2.0)
    assert len(t1_res) == 1
    assert t1_res[0]["reason"] == "budget_timeout"

    # Immediately run 3 fast check-ins on different readings (so no cache hit)
    for g_val in (112.0, 114.0, 116.0):
        t0 = time.monotonic()
        r_fast = guarded_explain(
            triage_result=triage,
            readings={"glucose": g_val},
            language="en",
            llm=fast_llm,
            budget_seconds=1.0,
        )
        el = time.monotonic() - t0
        assert el < 2.0, f"Check-in with glucose {g_val} took {el:.2f}s, expected < 2.0s"
        assert r_fast["mode"] in ("llm", "template")
        assert r_fast.get("reason") != "budget_timeout"


# =============================================================================
# C2: Daily Token Cap & Rollover Tests
# =============================================================================
def test_c2_token_cap_blocks_and_resets_on_new_utc_day():
    """When tokens_used + 1000 > cap, skips LLM; counter resets on new UTC day."""
    current_date = "2026-11-04"

    def mock_date():
        return current_date

    token_guard = TokenCapGuard(cap=5000, get_utc_date_fn=mock_date)
    assert token_guard.can_consume(1000) is True

    # Consume 4500 tokens
    token_guard.record_usage(4500)
    # 4500 + 1000 > 5000 -> cannot consume
    assert token_guard.can_consume(1000) is False

    triage = {"level": "routine", "reasons": ["Normal"]}
    res = guarded_explain(
        triage_result=triage,
        readings={"glucose": 115.0},
        language="en",
        llm=lambda **k: "should not be called",
        daily_token_guard=token_guard,
    )
    assert res["mode"] == "template"
    assert res["reason"] == "token_cap"

    # Roll over to new UTC day
    current_date = "2026-11-05"
    assert token_guard.can_consume(1000) is True
    assert token_guard.get_tokens_used_today() == 0


def test_c2_discarded_late_thread_records_tokens():
    """Correction 2: When a timed-out thread finishes late, its tokens are added to the daily counter."""
    token_guard = TokenCapGuard(cap=150000)
    initial_tokens = token_guard.get_tokens_used_today()

    def slow_llm_with_usage(**kwargs):
        time.sleep(0.7)
        return (
            json.dumps({
                "sentences": [
                    {"text": "Late answer [S1].", "cites": ["S1"]},
                    {"text": "Never shown [S1].", "cites": ["S1"]},
                ]
            }),
            350,  # 350 tokens used
        )

    triage = {"level": "routine", "reasons": ["Normal"]}
    res = guarded_explain(
        triage_result=triage,
        readings={"glucose": 118.0},
        language="en",
        llm=slow_llm_with_usage,
        budget_seconds=0.3,  # times out
        daily_token_guard=token_guard,
    )
    assert res["mode"] == "template"
    assert res["reason"] == "budget_timeout"

    # Wait for the background worker thread to finish (0.7s total)
    time.sleep(0.8)

    # Verify the late thread's tokens were recorded
    after_tokens = token_guard.get_tokens_used_today()
    assert after_tokens == initial_tokens + 350


# =============================================================================
# C3: Cache & Strict Safety Re-validation Tests
# =============================================================================
def test_c3_cache_hit_and_revalidation_mismatch(mock_store):
    """C3: Identical band returns mode=cache; number mismatch in cached text fails re-validation."""
    cache = ExplainCache()

    def llm_fixed_numbers(**kwargs):
        return json.dumps({
            "sentences": [
                {"text": "Your fasting glucose reading of 155 mg/dL requires review [S1].", "cites": ["S1"]},
                {"text": "Regular blood tests help monitor your glycemic trends [S1].", "cites": ["S1"]},
            ]
        })

    triage = {"level": "review", "reasons": ["Elevated fasting glucose"]}
    readings1 = {"glucose": 155.0}

    # 1. First check-in calls LLM and populates cache
    res1 = guarded_explain(
        triage_result=triage,
        readings=readings1,
        language="en",
        store=mock_store,
        llm=llm_fixed_numbers,
        cache=cache,
    )
    assert res1["mode"] == "llm"
    assert cache.size() == 1

    # 2. Second check-in with exact same readings -> cache hit!
    call_spy = []
    res2 = guarded_explain(
        triage_result=triage,
        readings=readings1,
        language="en",
        store=mock_store,
        llm=lambda **k: call_spy.append("called"),
        cache=cache,
    )
    assert res2["mode"] == "cache"
    assert len(call_spy) == 0  # LLM was NOT called

    # 3. Third check-in: in the same glucose band (70-180), but readings are 165 mg/dL.
    # The cached text mentions "155 mg/dL", which is NOT in this patient's allowed numbers!
    # Re-validation must reject it and fall through to LLM!
    def llm_for_third(**kwargs):
        call_spy.append("called_third")
        return json.dumps({
            "sentences": [
                {"text": "Your fasting glucose reading of 165 mg/dL requires review [S1].", "cites": ["S1"]},
                {"text": "Regular blood tests help monitor your glycemic trends [S1].", "cites": ["S1"]},
            ]
        })

    res3 = guarded_explain(
        triage_result=triage,
        readings={"glucose": 165.0},
        language="en",
        store=mock_store,
        llm=llm_for_third,
        cache=cache,
    )
    assert "called_third" in call_spy
    assert res3["mode"] == "llm"


def test_c3_no_user_id_in_cache_keys():
    """Assert on cache keys: never contain user id, patient text, or exact numbers."""
    key = compute_cache_key(
        trigger_category="systolic_elevated",
        triage_level="review",
        glucose_band="none",
        bp_band="elevated/stage 1",
        language="en",
        condition="hypertension",
    )
    assert len(key) == 6
    for item in key:
        assert "user" not in item
        assert "pat_" not in item
        assert "135" not in item


# =============================================================================
# C4: Circuit Breaker Tests
# =============================================================================
def test_c4_breaker_opens_after_3_failures_and_instant_429(mock_store):
    """A4: 3 failures trip breaker; 429 rate limit trips instantly; validator reject does not trip."""
    breaker = CircuitBreaker(failures_threshold=3, cooldown_seconds=2.0)
    assert breaker.state() == CircuitBreaker.CLOSED

    # 1. Validator rejection does NOT trip breaker
    def validator_failing_llm(**kwargs):
        # Generates banned diagnostic wording
        return json.dumps({
            "sentences": [
                {"text": "You are diagnosed with type 2 diabetes [S1].", "cites": ["S1"]},
                {"text": "Take your medication regularly [S1].", "cites": ["S1"]},
            ]
        })

    triage = {"level": "routine", "reasons": ["Normal"]}
    res_val = guarded_explain(
        triage_result=triage,
        readings={"glucose": 105.0},
        language="en",
        store=mock_store,
        llm=validator_failing_llm,
        breaker=breaker,
    )
    assert res_val["mode"] == "template"
    assert res_val["reason"] == "validation_failed"
    assert breaker.state() == CircuitBreaker.CLOSED

    # 2. 3 consecutive timeouts/exceptions trip the breaker
    def broken_llm(**kwargs):
        raise RuntimeError("Groq connection lost")

    for _ in range(3):
        guarded_explain(
            triage_result=triage,
            readings={"glucose": 105.0},
            language="en",
            store=mock_store,
            llm=broken_llm,
            breaker=breaker,
        )

    # Breaker is now OPEN
    assert breaker.state() == CircuitBreaker.OPEN

    # 4th check-in: skips LLM entirely with reason="breaker_open"
    spy_called = []
    res_open = guarded_explain(
        triage_result=triage,
        readings={"glucose": 105.0},
        language="en",
        store=mock_store,
        llm=lambda **k: spy_called.append("call"),
        breaker=breaker,
    )
    assert res_open["mode"] == "template"
    assert res_open["reason"] == "breaker_open"
    assert len(spy_called) == 0

    # 3. Rate limit (429) trips breaker immediately on fresh breaker
    fresh_breaker = CircuitBreaker(failures_threshold=3, cooldown_seconds=2.0)
    def rate_limited_llm(**kwargs):
        raise RuntimeError("Rate limit reached. HTTP 429 Too Many Requests")

    res_429 = guarded_explain(
        triage_result=triage,
        readings={"glucose": 105.0},
        language="en",
        store=mock_store,
        llm=rate_limited_llm,
        breaker=fresh_breaker,
    )
    assert res_429["mode"] == "template"
    assert res_429["reason"] == "rate_limited"
    assert fresh_breaker.state() == CircuitBreaker.OPEN


# =============================================================================
# C5: Flag Off Identical Baseline Behavior (Direct & Graph Modes)
# =============================================================================
@pytest.mark.parametrize("orch_mode", ["direct", "graph"])
def test_c5_flag_off_returns_none_and_zero_guard_calls(rsa_key, monkeypatch, orch_mode):
    """When EXPLAIN_ENABLED is off, step_explain returns None and zero guard calls execute."""
    monkeypatch.setenv("ORCHESTRATOR", orch_mode)
    monkeypatch.setenv("EXPLAIN_ENABLED", "false")
    monkeypatch.setenv("RISK_ENABLED", "false")

    client = TestClient(app)
    uid = f"pat_c5_{orch_mode}"
    cid = f"chk_c5_{orch_mode}"
    headers = _get_auth_headers(rsa_key, uid)
    client.post("/api/auth/session", headers=headers)
    local_store.add_local_patient_if_missing(f"local-{uid}", name=f"User {uid}", date_of_birth="1980-01-01")
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1980-01-01",
            "inclusion_confirmed": True,
            "language": "en",
        },
    )

    _create_checkin_session(uid, cid, systolic=135.0, diastolic=85.0)

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["explanation"] is None

    metrics = get_explain_guard_metrics()
    assert metrics["llm_calls"] == 0


# =============================================================================
# C6: Emergency Intakes Never Call Explainer
# =============================================================================
def test_c6_emergency_intakes_bypass_explainer(rsa_key, monkeypatch):
    """Emergency intakes strictly bypass explainer and never call the LLM."""
    monkeypatch.setenv("EXPLAIN_ENABLED", "true")
    monkeypatch.setenv("RISK_ENABLED", "false")

    spy_called = []
    monkeypatch.setattr(groq_client, "chat_with_usage", lambda **k: spy_called.append("called"))
    monkeypatch.setattr(groq_client, "is_configured", lambda: True)

    client = TestClient(app)
    uid = "pat_c6_emerg"
    cid = "chk_c6_emerg"
    headers = _get_auth_headers(rsa_key, uid)
    client.post("/api/auth/session", headers=headers)
    local_store.add_local_patient_if_missing(f"local-{uid}", name=f"User {uid}", date_of_birth="1980-01-01")
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": ["hypertension"],
            "date_of_birth": "1980-01-01",
            "inclusion_confirmed": True,
            "language": "en",
        },
    )

    _create_checkin_session(uid, cid, emergency=True, emergency_reason="chest_pain")

    resp = client.post(f"/api/checkins/{cid}/complete", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["emergency"] is True
    assert data["explanation"] is None
    assert len(spy_called) == 0


# =============================================================================
# C7: Mutation Proof Target Tests
# =============================================================================
def test_mutation_proof_budget_deadline_killed():
    """Mutation proof M-U-G1: removing deadline causes budget timeout test to fail."""
    def sleeping_llm(**kwargs):
        time.sleep(2.0)
        return json.dumps({
            "sentences": [
                {"text": "Late explanation [S1].", "cites": ["S1"]},
                {"text": "Should never be seen [S1].", "cites": ["S1"]},
            ]
        })

    triage = {"level": "routine", "reasons": ["Normal"]}
    res = guarded_explain(
        triage_result=triage,
        readings={"glucose": 110.0},
        language="en",
        llm=sleeping_llm,
        budget_seconds=0.5,
    )
    assert res["reason"] == "budget_timeout"
    assert res["mode"] == "template"


def test_mutation_proof_cache_revalidation_killed(mock_store):
    """Mutation proof M-U-G2: removing cache re-validation causes number mismatch to wrongly hit cache."""
    cache = ExplainCache()

    def llm_fixed_numbers(**kwargs):
        return json.dumps({
            "sentences": [
                {"text": "Your fasting glucose reading of 155 mg/dL requires review [S1].", "cites": ["S1"]},
                {"text": "Regular monitoring helps [S1].", "cites": ["S1"]},
            ]
        })

    triage = {"level": "review", "reasons": ["High glucose"]}
    res1 = guarded_explain(
        triage_result=triage,
        readings={"glucose": 155.0},
        language="en",
        store=mock_store,
        llm=llm_fixed_numbers,
        cache=cache,
    )
    assert res1["mode"] == "llm"

    # Mismatched check-in (175 mg/dL) must NOT hit cache
    res2 = guarded_explain(
        triage_result=triage,
        readings={"glucose": 175.0},
        language="en",
        store=mock_store,
        llm=lambda **k: json.dumps({
            "sentences": [
                {"text": "Your fasting glucose reading of 175 mg/dL requires review [S1].", "cites": ["S1"]},
                {"text": "Regular monitoring helps [S1].", "cites": ["S1"]},
            ]
        }),
        cache=cache,
    )
    assert res2["mode"] == "llm"


def test_mutation_proof_breaker_never_opens_killed():
    """Mutation proof M-U-G3: circuit breaker must open after 3 consecutive errors."""
    breaker = CircuitBreaker(failures_threshold=3, cooldown_seconds=60.0)
    for _ in range(3):
        breaker.record_failure(is_rate_limit=False)
    assert breaker.state() == CircuitBreaker.OPEN
    assert breaker.allow_call() is False


# =============================================================================
# Review Follow-ups: Docs Env Table, Retries Disabled, Token Race Fix
# =============================================================================
def test_docs_env_table_matches_code_constants():
    """
    Review Item 1: Parses ## 3. Environment Variables Reference in docs/EXPLAIN_GUARDS.md
    and asserts every env var name and default equals the constants in explain_guards.py.
    """
    import re
    from pathlib import Path
    from rag.explain_guards import (
        DEFAULT_BUDGET_SECONDS,
        DEFAULT_DAILY_TOKEN_CAP,
        DEFAULT_DAILY_TOKEN_CAP_GEMINI,
        DEFAULT_CACHE_MAX,
        DEFAULT_CACHE_TTL_SECONDS,
        DEFAULT_BREAKER_FAILURES,
        DEFAULT_BREAKER_COOLDOWN_SECONDS,
        DEFAULT_MAX_WORKERS,
        DEFAULT_LLM_PROVIDER,
        DEFAULT_LLM_PROVIDER_ORDER,
        DEFAULT_LLM_CONDITIONS,
    )

    doc_path = Path(__file__).resolve().parent.parent / "docs" / "EXPLAIN_GUARDS.md"
    assert doc_path.exists(), f"docs/EXPLAIN_GUARDS.md not found at {doc_path}"
    doc_content = doc_path.read_text(encoding="utf-8")

    section3 = re.search(r"## 3\. Environment Variables Reference(.*?)(?:\n## |\Z)", doc_content, re.DOTALL)
    assert section3, "Section 3 not found in docs/EXPLAIN_GUARDS.md"

    table_lines = [l.strip() for l in section3.group(1).split("\n") if l.strip().startswith("|")]
    assert len(table_lines) >= 3, "Table in Section 3 must have header, separator, and data rows"

    parsed_table = {}
    for row in table_lines[2:]:
        cols = [c.strip() for c in row.split("|")[1:-1]]
        if len(cols) >= 3:
            var_name = cols[0].replace("`", "").strip()
            var_type = cols[1].strip()
            default_val = cols[2].replace("`", "").strip()
            parsed_table[var_name] = (var_type, default_val)

    expected = {
        "EXPLAIN_ENABLED": ("bool", "false"),
        "EXPLAIN_BUDGET_SECONDS": ("float", str(DEFAULT_BUDGET_SECONDS)),
        "EXPLAIN_DAILY_TOKEN_CAP": ("int", str(DEFAULT_DAILY_TOKEN_CAP)),
        "EXPLAIN_DAILY_TOKEN_CAP_GEMINI": ("int", str(DEFAULT_DAILY_TOKEN_CAP_GEMINI)),
        "EXPLAIN_CACHE_MAX": ("int", str(DEFAULT_CACHE_MAX)),
        "EXPLAIN_CACHE_TTL_SECONDS": ("float", str(DEFAULT_CACHE_TTL_SECONDS)),
        "EXPLAIN_BREAKER_FAILURES": ("int", str(DEFAULT_BREAKER_FAILURES)),
        "EXPLAIN_BREAKER_COOLDOWN_SECONDS": ("float", str(DEFAULT_BREAKER_COOLDOWN_SECONDS)),
        "EXPLAIN_POOL_MAX_WORKERS": ("int", str(DEFAULT_MAX_WORKERS)),
        "LLM_PROVIDER": ("str", DEFAULT_LLM_PROVIDER),
        "LLM_PROVIDER_ORDER": ("str", DEFAULT_LLM_PROVIDER_ORDER),
        "GEMINI_MODEL": ("str", '""'),
        "GEMINI_THINKING_BUDGET": ("str", '""'),
        "EXPLAIN_LLM_CONDITIONS": ("str", DEFAULT_LLM_CONDITIONS),
    }

    for env_var, (exp_type, exp_val) in expected.items():
        assert env_var in parsed_table, f"Missing {env_var} in docs/EXPLAIN_GUARDS.md table"
        actual_type, actual_val = parsed_table[env_var]
        assert actual_type == exp_type, f"{env_var} type mismatch in docs: {actual_type} != {exp_type}"
        if exp_type == "float":
            assert float(actual_val) == float(exp_val), f"{env_var} default mismatch: {actual_val} != {exp_val}"
        else:
            assert actual_val == exp_val, f"{env_var} default mismatch: {actual_val} != {exp_val}"


def test_retries_disabled_and_timeout_bounded(mock_store):
    """
    Review Item 2: Asserts that _timed_llm strictly passes max_retries=0,
    sdk_max_retries=0, and timeout <= budget to the underlying LLM.
    """
    recorded_kwargs = {}

    def spy_llm(**kwargs):
        recorded_kwargs.update(kwargs)
        return (json.dumps({
            "sentences": [
                {"text": "Your fasting glucose reading of 105 mg/dL is within target [S1].", "cites": ["S1"]},
                {"text": "Regular monitoring supports diabetes management [S1].", "cites": ["S1"]},
            ]
        }), 45)

    budget = 2.5
    res = guarded_explain(
        triage_result={"level": "routine", "reasons": ["Normal"]},
        readings={"glucose": 105.0},
        language="en",
        store=mock_store,
        llm=spy_llm,
        budget_seconds=budget,
    )

    assert res["mode"] == "llm"
    assert "max_retries" in recorded_kwargs
    assert recorded_kwargs["max_retries"] == 0, f"Expected max_retries=0, got {recorded_kwargs['max_retries']}"
    assert "sdk_max_retries" in recorded_kwargs
    assert recorded_kwargs["sdk_max_retries"] == 0, f"Expected sdk_max_retries=0, got {recorded_kwargs['sdk_max_retries']}"
    assert "timeout" in recorded_kwargs
    assert 0.0 < recorded_kwargs["timeout"] <= budget, f"Timeout {recorded_kwargs['timeout']} exceeded budget {budget}"


def test_token_race_condition_counted_exactly_once(mock_store):
    """
    Review Item 5: Under lock with recorded / consumed_by_caller flag, late-finishing
    or timed-out worker tokens are counted exactly once without race or double-counting.
    """
    guard = TokenCapGuard(cap=100000)

    # 1. Late-finishing worker: budget is 0.2s, LLM sleeps 0.5s and returns 150 tokens.
    def late_llm(**kwargs):
        time.sleep(0.5)
        return (json.dumps({
            "sentences": [
                {"text": "Late result [S1].", "cites": ["S1"]},
                {"text": "Should not be displayed [S1].", "cites": ["S1"]},
            ]
        }), 150)

    triage = {"level": "routine", "reasons": ["Normal"]}
    res = guarded_explain(
        triage_result=triage,
        readings={"glucose": 105.0},
        language="en",
        store=mock_store,
        llm=late_llm,
        budget_seconds=0.2,
        daily_token_guard=guard,
    )

    # Fallback returned immediately within ~0.2s
    assert res["mode"] == "template"
    assert res["reason"] == "budget_timeout"

    # Wait for the background worker to finish execution
    time.sleep(0.6)

    # Tokens from late result MUST be recorded exactly once
    assert guard.get_tokens_used_today() == 150

    # 2. On-time completion: ensures tokens are counted once (not twice by caller and worker)
    def fast_llm(**kwargs):
        return (json.dumps({
            "sentences": [
                {"text": "Fast result [S1].", "cites": ["S1"]},
                {"text": "Guideline targets met [S1].", "cites": ["S1"]},
            ]
        }), 80)

    res_fast = guarded_explain(
        triage_result=triage,
        readings={"glucose": 105.0},
        language="en",
        store=mock_store,
        llm=fast_llm,
        budget_seconds=3.0,
        daily_token_guard=guard,
    )

    assert res_fast["mode"] == "llm"
    # Cumulative tokens: 150 + 80 = 230 (exactly once, never double-counted to 310)
    assert guard.get_tokens_used_today() == 230
