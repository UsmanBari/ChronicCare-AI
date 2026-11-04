"""
Guardrails and Resiliency Layer for ChronicCare AI Guideline Explanations.

Enforces:
1. Hard time budget (EXPLAIN_BUDGET_SECONDS, default 3.0s) with worker-thread hard stop.
2. Daily Groq token cap (EXPLAIN_DAILY_TOKEN_CAP, default 150,000) resetting per UTC day.
3. In-memory LRU cache with clinical reading bands and strict re-validation
   (chunk existence, citations, number grounding, banned patterns, level consistency).
4. Circuit breaker (3 consecutive timeouts/errors or 429 rate limit trips; 600s cooldown; half-open trial).
5. Retriever caching (BM25Retriever built once per store, reused while count unchanged).
6. Result metadata (mode: "llm"|"cache"|"template", reason on template fallback).
7. Guard metrics for monitoring and Day 5 admin view.
"""
from __future__ import annotations

import copy
import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from rag.explainer import (
    EXPLAINER_VERSION,
    get_allowed_numbers,
    get_template_explanation,
    validate_banned_patterns,
    validate_citations,
    validate_level_consistency,
    validate_number_grounding,
)
from rag.query_map import build_query_from_triage
from rag.retriever import BM25Retriever
from rag.store import ChunkStore

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration & Defaults
# =============================================================================
DEFAULT_BUDGET_SECONDS: float = 3.0
DEFAULT_DAILY_TOKEN_CAP: int = 150000
DEFAULT_CACHE_MAX: int = 500
DEFAULT_CACHE_TTL_SECONDS: float = 86400.0  # 24 hours
DEFAULT_BREAKER_FAILURES: int = 3
DEFAULT_BREAKER_COOLDOWN_SECONDS: float = 600.0  # 10 minutes
DEFAULT_MAX_WORKERS: int = 8


def get_budget_seconds() -> float:
    try:
        return float(os.environ.get("EXPLAIN_BUDGET_SECONDS", str(DEFAULT_BUDGET_SECONDS)))
    except (ValueError, TypeError):
        return DEFAULT_BUDGET_SECONDS


def get_daily_token_cap() -> int:
    try:
        return int(os.environ.get("EXPLAIN_DAILY_TOKEN_CAP", str(DEFAULT_DAILY_TOKEN_CAP)))
    except (ValueError, TypeError):
        return DEFAULT_DAILY_TOKEN_CAP


def get_cache_max() -> int:
    try:
        return int(os.environ.get("EXPLAIN_CACHE_MAX", str(DEFAULT_CACHE_MAX)))
    except (ValueError, TypeError):
        return DEFAULT_CACHE_MAX


def get_cache_ttl_seconds() -> float:
    try:
        return float(os.environ.get("EXPLAIN_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS)))
    except (ValueError, TypeError):
        return DEFAULT_CACHE_TTL_SECONDS


def get_breaker_failures() -> int:
    try:
        return int(os.environ.get("EXPLAIN_BREAKER_FAILURES", str(DEFAULT_BREAKER_FAILURES)))
    except (ValueError, TypeError):
        return DEFAULT_BREAKER_FAILURES


def get_breaker_cooldown_seconds() -> float:
    try:
        return float(os.environ.get("EXPLAIN_BREAKER_COOLDOWN_SECONDS", str(DEFAULT_BREAKER_COOLDOWN_SECONDS)))
    except (ValueError, TypeError):
        return DEFAULT_BREAKER_COOLDOWN_SECONDS


def get_max_workers() -> int:
    try:
        return max(4, int(os.environ.get("EXPLAIN_POOL_MAX_WORKERS", str(DEFAULT_MAX_WORKERS))))
    except (ValueError, TypeError):
        return DEFAULT_MAX_WORKERS


# =============================================================================
# Reading Bands & Cache Key Computation
# =============================================================================
def get_glucose_band(glucose: Optional[float]) -> str:
    """
    Categorize glucose into bands:
    <54, 54-69, 70-180, 181-250, 251-400, >400 mg/dL; 'none' when absent.
    """
    if glucose is None:
        return "none"
    try:
        g = float(glucose)
    except (ValueError, TypeError):
        return "none"

    if g < 54.0:
        return "<54"
    elif 54.0 <= g < 70.0:
        return "54-69"
    elif 70.0 <= g <= 180.0:
        return "70-180"
    elif 180.0 < g <= 250.0:
        return "181-250"
    elif 250.0 < g <= 400.0:
        return "251-400"
    else:
        return ">400"


def get_bp_band(systolic: Optional[float], diastolic: Optional[float]) -> str:
    """
    Categorize BP into bands:
    normal (<130/80), elevated/stage 1 (130-139 or 80-89),
    stage 2 (>=140 or >=90), crisis (>=180 or >=120); 'none' when absent.
    """
    sbp: Optional[float] = None
    dbp: Optional[float] = None
    if systolic is not None:
        try:
            sbp = float(systolic)
        except (ValueError, TypeError):
            sbp = None
    if diastolic is not None:
        try:
            dbp = float(diastolic)
        except (ValueError, TypeError):
            dbp = None

    if sbp is None and dbp is None:
        return "none"

    # Crisis check first
    if (sbp is not None and sbp >= 180.0) or (dbp is not None and dbp >= 120.0):
        return "crisis"

    # Stage 2 check
    if (sbp is not None and sbp >= 140.0) or (dbp is not None and dbp >= 90.0):
        return "stage 2"

    # Elevated / Stage 1 check
    if (sbp is not None and 130.0 <= sbp <= 139.0) or (dbp is not None and 80.0 <= dbp <= 89.0):
        return "elevated/stage 1"

    # Normal check
    sbp_norm = sbp is None or sbp < 130.0
    dbp_norm = dbp is None or dbp < 80.0
    if sbp_norm and dbp_norm:
        return "normal"

    return "elevated/stage 1"


def compute_cache_key(
    trigger_category: str,
    triage_level: str,
    glucose_band: str,
    bp_band: str,
    language: str,
    condition: str,
) -> Tuple[str, str, str, str, str, str]:
    """
    Build coarse-grained cache key without user id, free text, or exact numbers.
    """
    return (
        trigger_category.strip().lower(),
        triage_level.strip().lower(),
        glucose_band,
        bp_band,
        language.strip().lower(),
        condition.strip().lower(),
    )


# =============================================================================
# In-Memory LRU Cache with Re-validation
# =============================================================================
class ExplainCache:
    """
    Thread-safe in-memory LRU cache with TTL and safety re-validation.
    """
    def __init__(self, max_size: int = DEFAULT_CACHE_MAX, ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS):
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[Tuple[str, ...], Tuple[Dict[str, Any], float]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits: int = 0
        self.misses: int = 0

    def get(
        self,
        key: Tuple[str, ...],
        readings: Dict[str, Any],
        triage_result: Dict[str, Any],
        decided_level: str,
        store: Optional[ChunkStore] = None,
        candidate_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None
            data, ts = self._cache[key]
            now = time.monotonic()
            if now - ts > self._ttl_seconds:
                del self._cache[key]
                self.misses += 1
                return None
            self._cache.move_to_end(key)

        # Re-validation outside lock:
        # A3: store with each cached explanation the chunk ids it cited.
        # On a hit, re-run citations (chunk ids must still exist in current store),
        # number grounding against THIS check-in's allowed numbers, banned patterns,
        # and level consistency. Any failure = miss.
        cited_cids: List[str] = data.get("cited_chunk_ids", [])
        sentences: List[Dict[str, Any]] = data.get("sentences", [])

        # 1. Verify cited chunks exist in store or candidates
        existing_chunks_by_id: Dict[str, Dict[str, Any]] = {}
        if candidate_chunks:
            for c in candidate_chunks:
                existing_chunks_by_id[c["chunk_id"]] = c

        if store is not None:
            for cid in cited_cids:
                if cid not in existing_chunks_by_id:
                    chunk = store.get(cid)
                    if not chunk:
                        with self._lock:
                            self.misses += 1
                        return None
                    existing_chunks_by_id[cid] = chunk

        verified_candidate_chunks = list(existing_chunks_by_id.values())

        # 2. Re-validate citations
        v2_errs, resolved_sentences = validate_citations(sentences, verified_candidate_chunks)
        if v2_errs:
            with self._lock:
                self.misses += 1
            return None

        # 3. Re-validate number grounding against THIS check-in's readings & level
        allowed_nums = get_allowed_numbers(readings, triage_result, verified_candidate_chunks)
        v3_errs = validate_number_grounding(resolved_sentences, allowed_nums)
        if v3_errs:
            with self._lock:
                self.misses += 1
            return None

        # 4. Re-validate banned patterns
        v4_errs = validate_banned_patterns(resolved_sentences, decided_level)
        if v4_errs:
            with self._lock:
                self.misses += 1
            return None

        # 5. Re-validate level consistency
        v5_errs = validate_level_consistency(resolved_sentences, decided_level)
        if v5_errs:
            with self._lock:
                self.misses += 1
            return None

        # All validators passed: record hit and return deep copy
        with self._lock:
            self.hits += 1

        hit_result = copy.deepcopy(data["result"])
        hit_result["mode"] = "cache"
        hit_result["rejected_reasons"] = []
        return hit_result

    def put(self, key: Tuple[str, ...], result: Dict[str, Any], cited_chunk_ids: List[str]) -> None:
        # Never cache template results or errors
        if result.get("mode") != "llm":
            return
        if result.get("rejected_reasons"):
            return

        with self._lock:
            if key in self._cache:
                del self._cache[key]
            self._cache[key] = (
                {
                    "result": copy.deepcopy(result),
                    "cited_chunk_ids": list(dict.fromkeys(cited_chunk_ids)),
                    "sentences": copy.deepcopy(result.get("sentences", [])),
                },
                time.monotonic(),
            )
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0


# =============================================================================
# Daily Token Cap Guard
# =============================================================================
class TokenCapGuard:
    """
    In-memory daily Groq token counter resetting on UTC day boundary.
    """
    def __init__(self, cap: Optional[int] = None, get_utc_date_fn: Optional[Callable[[], str]] = None):
        self._cap = cap if cap is not None else get_daily_token_cap()
        self._get_date = get_utc_date_fn or (lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        self._current_date: str = self._get_date()
        self._tokens_used: int = 0
        self._lock = threading.Lock()

    def get_cap(self) -> int:
        return self._cap

    def _sync_date(self) -> None:
        today = self._get_date()
        if today != self._current_date:
            self._current_date = today
            self._tokens_used = 0

    def can_consume(self, estimated_tokens: int = 1000) -> bool:
        with self._lock:
            self._sync_date()
            return (self._tokens_used + estimated_tokens) <= self._cap

    def record_usage(self, tokens: int) -> None:
        if tokens <= 0:
            return
        with self._lock:
            self._sync_date()
            self._tokens_used += int(tokens)

    def get_tokens_used_today(self) -> int:
        with self._lock:
            self._sync_date()
            return self._tokens_used

    def reset(self) -> None:
        with self._lock:
            self._current_date = self._get_date()
            self._tokens_used = 0


# =============================================================================
# Circuit Breaker Guard
# =============================================================================
class CircuitBreaker:
    """
    Circuit breaker for LLM explainer calls.
    Trips on consecutive timeouts/errors or instant 429 rate limits.
    Validator rejections do NOT trip the breaker.
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failures_threshold: int = DEFAULT_BREAKER_FAILURES,
        cooldown_seconds: float = DEFAULT_BREAKER_COOLDOWN_SECONDS,
    ):
        self._threshold = failures_threshold
        self._cooldown = cooldown_seconds
        self._state: str = self.CLOSED
        self._consecutive_failures: int = 0
        self._opened_at: float = 0.0
        self._trial_in_progress: bool = False
        self._lock = threading.Lock()

    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN:
                if time.monotonic() - self._opened_at >= self._cooldown:
                    self._state = self.HALF_OPEN
                    self._trial_in_progress = False
            return self._state

    def allow_call(self) -> bool:
        with self._lock:
            if self._state == self.CLOSED:
                return True
            if self._state == self.OPEN:
                if time.monotonic() - self._opened_at >= self._cooldown:
                    self._state = self.HALF_OPEN
                    self._trial_in_progress = True
                    return True
                return False
            if self._state == self.HALF_OPEN:
                if not self._trial_in_progress:
                    self._trial_in_progress = True
                    return True
                return False
            return False

    def record_success(self) -> None:
        with self._lock:
            self._state = self.CLOSED
            self._consecutive_failures = 0
            self._trial_in_progress = False

    def record_failure(self, is_rate_limit: bool = False) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if is_rate_limit or self._consecutive_failures >= self._threshold or self._state == self.HALF_OPEN:
                self._state = self.OPEN
                self._opened_at = time.monotonic()
                self._trial_in_progress = False

    def reset(self) -> None:
        with self._lock:
            self._state = self.CLOSED
            self._consecutive_failures = 0
            self._opened_at = 0.0
            self._trial_in_progress = False


# =============================================================================
# Global Guard Instances & Metrics
# =============================================================================
_GLOBAL_CACHE = ExplainCache()
_GLOBAL_TOKEN_GUARD = TokenCapGuard()
_GLOBAL_BREAKER = CircuitBreaker()
_WORKER_SEMAPHORE = threading.Semaphore(get_max_workers())

_METRICS_LOCK = threading.Lock()
_TOTAL_LLM_CALLS: int = 0
_FALLBACK_COUNTS: Dict[str, int] = {
    "budget_timeout": 0,
    "token_cap": 0,
    "breaker_open": 0,
    "rate_limited": 0,
    "validation_failed": 0,
    "no_llm": 0,
    "no_chunks": 0,
    "busy": 0,
    "error": 0,
}


def record_llm_call() -> None:
    global _TOTAL_LLM_CALLS
    with _METRICS_LOCK:
        _TOTAL_LLM_CALLS += 1


def record_fallback(reason: str) -> None:
    with _METRICS_LOCK:
        _FALLBACK_COUNTS[reason] = _FALLBACK_COUNTS.get(reason, 0) + 1


def get_explain_guard_metrics() -> Dict[str, Any]:
    with _METRICS_LOCK:
        fallbacks = dict(_FALLBACK_COUNTS)
        llm_calls = _TOTAL_LLM_CALLS
    return {
        "tokens_used_today": _GLOBAL_TOKEN_GUARD.get_tokens_used_today(),
        "cap": _GLOBAL_TOKEN_GUARD.get_cap(),
        "breaker_state": _GLOBAL_BREAKER.state(),
        "cache_size": _GLOBAL_CACHE.size(),
        "cache_hits": _GLOBAL_CACHE.hits,
        "cache_misses": _GLOBAL_CACHE.misses,
        "llm_calls": llm_calls,
        "template_fallbacks_by_reason": fallbacks,
    }


def reset_explain_guards() -> None:
    """Helper for hermetic test suites to reset all guards to pristine state."""
    global _TOTAL_LLM_CALLS, _FALLBACK_COUNTS, _CACHED_RETRIEVER, _CACHED_CHUNK_COUNT, _CACHED_STORE_ID
    _GLOBAL_CACHE.clear()
    _GLOBAL_TOKEN_GUARD.reset()
    _GLOBAL_BREAKER.reset()
    with _METRICS_LOCK:
        _TOTAL_LLM_CALLS = 0
        for k in _FALLBACK_COUNTS:
            _FALLBACK_COUNTS[k] = 0
    _CACHED_RETRIEVER = None
    _CACHED_CHUNK_COUNT = None
    _CACHED_STORE_ID = None


# =============================================================================
# Cached Retriever Builder (A5)
# =============================================================================
_CACHED_RETRIEVER: Optional[BM25Retriever] = None
_CACHED_CHUNK_COUNT: Optional[int] = None
_CACHED_STORE_ID: Optional[int] = None
_RETRIEVER_LOCK = threading.Lock()


def get_or_build_retriever(store: Optional[ChunkStore]) -> Optional[BM25Retriever]:
    """
    Builds BM25 index once per store and reuses it; rebuilds only if count changes.
    """
    global _CACHED_RETRIEVER, _CACHED_CHUNK_COUNT, _CACHED_STORE_ID
    if store is None:
        return None

    with _RETRIEVER_LOCK:
        try:
            current_count = store.count()
        except Exception:
            current_count = -1

        store_id = id(store)
        if (
            _CACHED_RETRIEVER is not None
            and _CACHED_CHUNK_COUNT == current_count
            and _CACHED_STORE_ID == store_id
        ):
            return _CACHED_RETRIEVER

        retriever = BM25Retriever(store)
        _CACHED_RETRIEVER = retriever
        _CACHED_CHUNK_COUNT = current_count
        _CACHED_STORE_ID = store_id
        return retriever


# =============================================================================
# Guarded Explanation Runner
# =============================================================================
def guarded_explain(
    triage_result: Dict[str, Any],
    readings: Dict[str, Any],
    language: str = "en",
    store: Optional[ChunkStore] = None,
    llm: Any = None,
    condition: str = "diabetes",
    budget_seconds: Optional[float] = None,
    daily_token_guard: Optional[TokenCapGuard] = None,
    cache: Optional[ExplainCache] = None,
    breaker: Optional[CircuitBreaker] = None,
) -> Dict[str, Any]:
    """
    Executes a fully guarded clinical explanation:
    - Time budget deadline with worker-thread hard stop.
    - Daily token cap checking.
    - Cache lookup with rigorous safety re-validation.
    - Circuit breaker failure and 429 rate-limit tracking.
    - Concurrency worker pool limit with safe "busy" fallback.
    - Additive mode and reason metadata.
    """
    start_time = time.monotonic()
    budget = budget_seconds if budget_seconds is not None else get_budget_seconds()
    deadline = start_time + budget

    token_guard = daily_token_guard or _GLOBAL_TOKEN_GUARD
    exp_cache = cache or _GLOBAL_CACHE
    circ_breaker = breaker or _GLOBAL_BREAKER

    triage_copy = copy.deepcopy(triage_result)
    readings_copy = copy.deepcopy(readings)
    target_lang = language if language in ("en", "ur", "roman_ur") else "en"
    decided_level = str(triage_copy.get("level", "routine")).lower().strip()

    # Determine query mapping
    query_mapping = build_query_from_triage(triage_copy, readings_copy)
    trigger_category = query_mapping.trigger_category

    # Compute reading bands & cache key
    glucose_val = readings_copy.get("glucose") or readings_copy.get("fasting_glucose") or readings_copy.get("random_glucose")
    systolic_val = readings_copy.get("blood_pressure_systolic")
    diastolic_val = readings_copy.get("blood_pressure_diastolic")

    glucose_band = get_glucose_band(glucose_val)
    bp_band = get_bp_band(systolic_val, diastolic_val)
    cond_str = condition or query_mapping.condition or "diabetes"

    cache_key = compute_cache_key(
        trigger_category=trigger_category,
        triage_level=decided_level,
        glucose_band=glucose_band,
        bp_band=bp_band,
        language=target_lang,
        condition=cond_str,
    )

    # 1. Retrieve Candidate Chunks (reusing cached retriever)
    candidate_chunks: List[Dict[str, Any]] = []
    if store is not None:
        retriever = get_or_build_retriever(store)
        if retriever is not None:
            candidate_chunks = retriever.retrieve(
                query=query_mapping.query_text,
                top_k=3,
                condition=query_mapping.condition,
                min_priority=query_mapping.min_priority,
            )
            if len(candidate_chunks) < 2:
                candidate_chunks = retriever.retrieve(
                    query=query_mapping.query_text,
                    top_k=3,
                    min_priority=query_mapping.min_priority,
                )

    # 2. Check Cache with Safety Re-Validation
    cached_hit = exp_cache.get(
        key=cache_key,
        readings=readings_copy,
        triage_result=triage_copy,
        decided_level=decided_level,
        store=store,
        candidate_chunks=candidate_chunks,
    )
    if cached_hit is not None:
        return cached_hit

    # Helper for template fallback
    def _make_template_fallback(reason: str, rejected: Optional[List[str]] = None) -> Dict[str, Any]:
        record_fallback(reason)
        reasons_list = [f"Guard fallback: {reason}"]
        if rejected:
            reasons_list.extend(rejected)
        tmpl = get_template_explanation(
            trigger_category=trigger_category,
            readings=readings_copy,
            triage_result=triage_copy,
            language=target_lang,
            candidate_chunks=candidate_chunks,
            rejected_reasons=reasons_list,
        )
        tmpl["mode"] = "template"
        tmpl["reason"] = reason
        return tmpl

    # 3. Check No LLM or No Chunks
    if llm is None:
        return _make_template_fallback("no_llm", ["No LLM configured"])
    if not candidate_chunks and store is not None:
        return _make_template_fallback("no_chunks", ["No matching clinical guideline chunks found"])

    # 4. Check Circuit Breaker
    if not circ_breaker.allow_call():
        return _make_template_fallback("breaker_open", ["Circuit breaker is OPEN"])

    # 5. Check Daily Token Cap
    if not token_guard.can_consume(1000):
        return _make_template_fallback("token_cap", ["Daily token cap reached"])

    # 6. Check Time Budget before spawning worker
    time_left = deadline - time.monotonic()
    if time_left <= 0.0:
        circ_breaker.record_failure(is_rate_limit=False)
        return _make_template_fallback("budget_timeout", ["Insufficient budget before LLM dispatch"])

    # 7. Check Concurrency Limit (Worker Semaphore)
    acquired = _WORKER_SEMAPHORE.acquire(blocking=False)
    if not acquired:
        return _make_template_fallback("busy", ["Worker pool at maximum capacity"])

    # 8. Execute LLM Call in Thread with Hard Budget Join
    record_llm_call()

    worker_result: Dict[str, Any] = {}
    worker_error: Dict[str, Any] = {}
    worker_tokens: Dict[str, int] = {"count": 0}
    timed_out_flag = threading.Event()

    def _worker():
        try:
            from rag.explainer import explain

            def _timed_llm(**kwargs):
                try:
                    kwargs["timeout"] = max(0.1, deadline - time.monotonic())
                    if hasattr(llm, "chat_with_usage"):
                        text, tokens = llm.chat_with_usage(**kwargs)
                        worker_tokens["count"] += tokens
                        return text
                    elif callable(llm):
                        res = llm(**kwargs)
                        if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], int):
                            worker_tokens["count"] += res[1]
                            return res[0]
                        return res
                    elif hasattr(llm, "chat"):
                        return llm.chat(**kwargs)
                    raise TypeError("Invalid LLM callable")
                except Exception as exc:
                    worker_error["error"] = exc
                    raise

            res = explain(
                triage_result=triage_copy,
                readings=readings_copy,
                language=target_lang,
                store=store,
                llm=_timed_llm,
            )
            worker_result["data"] = res
        except Exception as exc:
            worker_error["error"] = exc
        finally:
            _WORKER_SEMAPHORE.release()
            # User Correction 2: Discarded late result still costs tokens
            if timed_out_flag.is_set():
                if worker_tokens["count"] > 0:
                    token_guard.record_usage(worker_tokens["count"])

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    # Hard wait at most time_left
    thread.join(timeout=max(0.0, deadline - time.monotonic()))

    if thread.is_alive():
        # Hard budget timeout
        timed_out_flag.set()
        circ_breaker.record_failure(is_rate_limit=False)
        return _make_template_fallback("budget_timeout", ["LLM execution exceeded time budget"])

    # Worker finished within budget; record token usage
    token_guard.record_usage(worker_tokens["count"])

    # Check worker exception
    if "error" in worker_error:
        err = worker_error["error"]
        err_str = str(err).lower()
        is_429 = "rate limit" in err_str or "429" in err_str or type(err).__name__ == "RateLimitError"
        circ_breaker.record_failure(is_rate_limit=is_429)
        reason = "rate_limited" if is_429 else "error"
        return _make_template_fallback(reason, [f"LLM exception: {type(err).__name__}"])

    res_data = worker_result.get("data")
    if not res_data:
        circ_breaker.record_failure(is_rate_limit=False)
        return _make_template_fallback("error", ["No response received from explainer worker"])

    # Check if explanation was rejected by clinical validators or failed due to LLM error
    if res_data.get("mode") == "template":
        if "error" in worker_error:
            err = worker_error["error"]
            err_str = str(err).lower()
            is_429 = "rate limit" in err_str or "429" in err_str or type(err).__name__ == "RateLimitError"
            circ_breaker.record_failure(is_rate_limit=is_429)
            reason = "rate_limited" if is_429 else "error"
            res_data["reason"] = reason
            record_fallback(reason)
            return res_data

        rej_list = res_data.get("rejected_reasons", [])
        if any("LLM execution error" in r for r in rej_list):
            is_429 = any("rate limit" in r.lower() or "429" in r.lower() for r in rej_list)
            circ_breaker.record_failure(is_rate_limit=is_429)
            reason = "rate_limited" if is_429 else "error"
            res_data["reason"] = reason
            record_fallback(reason)
            return res_data

        # Clinical validator rejection does NOT count as breaker failure
        res_data["reason"] = "validation_failed"
        record_fallback("validation_failed")
        return res_data

    # Successful LLM generation!
    circ_breaker.record_success()
    res_data["mode"] = "llm"

    # Extract cited chunk ids to populate cache
    cited_cids: List[str] = []
    for s in res_data.get("sentences", []):
        for c in s.get("cites", []):
            cited_cids.append(str(c))

    exp_cache.put(cache_key, res_data, cited_cids)
    return res_data

