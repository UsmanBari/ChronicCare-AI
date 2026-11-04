"""
Guardrails and Resiliency Layer for ChronicCare AI Guideline Explanations.

Enforces:
1. Hard time budget (EXPLAIN_BUDGET_SECONDS, default 3.0s) with worker-thread hard stop.
   Dynamic budget split (60% to primary provider when fallback available).
2. Daily token caps resetting per UTC day:
   - Groq: EXPLAIN_DAILY_TOKEN_CAP (default 150,000)
   - Gemini: EXPLAIN_DAILY_TOKEN_CAP_GEMINI (default 150,000)
3. Multi-provider routing (LLM_PROVIDER = auto | groq | gemini; LLM_PROVIDER_ORDER = "groq,gemini").
4. In-memory LRU cache with clinical reading bands and strict re-validation.
5. Circuit breakers per provider (3 consecutive timeouts/errors or 429 rate limit trips; 600s cooldown).
6. Guideline corpus licensing rule (G3): restricted sources never sent to Gemini.
7. Condition filtering (H1): EXPLAIN_LLM_CONDITIONS (default "hypertension").
8. Template consistency guard (H2): neutral routine fallback if template contradicts readings.
9. Audit segregation: provider and providers_tried recorded for provider review, excluded from patient view.
"""
from __future__ import annotations

import copy
import inspect
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
    is_template_consistent,
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
# Guideline Corpus Licensing Restrictions (G3)
# Source IDs with allowed_for_rag == FALSE in docs/GUIDELINE_CORPUS.md.
# These guidelines carry text/data mining prohibitions or copyright restrictions.
# Chunks derived from these sources must NEVER be sent to Google Gemini under any circumstances.
# =============================================================================
LICENCE_RESTRICTED_SOURCES: Set[str] = {
    "ada_2026_sec02",
    "ada_2026_sec05",
    "ada_2026_sec06",
    "ada_2026_sec10",
    "ada_2026_sec11",
    "ada_2026_sec13",
    "aha_acc_2025",
}

# =============================================================================
# Configuration & Defaults
# =============================================================================
DEFAULT_BUDGET_SECONDS: float = 3.0
DEFAULT_DAILY_TOKEN_CAP: int = 150000
DEFAULT_DAILY_TOKEN_CAP_GEMINI: int = 150000
DEFAULT_CACHE_MAX: int = 500
DEFAULT_CACHE_TTL_SECONDS: float = 86400.0  # 24 hours
DEFAULT_BREAKER_FAILURES: int = 3
DEFAULT_BREAKER_COOLDOWN_SECONDS: float = 600.0  # 10 minutes
DEFAULT_MAX_WORKERS: int = 8
DEFAULT_LLM_PROVIDER: str = "auto"
DEFAULT_LLM_PROVIDER_ORDER: str = "groq,gemini"
DEFAULT_LLM_CONDITIONS: str = "hypertension"


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


def get_daily_token_cap_gemini() -> int:
    try:
        return int(os.environ.get("EXPLAIN_DAILY_TOKEN_CAP_GEMINI", str(DEFAULT_DAILY_TOKEN_CAP_GEMINI)))
    except (ValueError, TypeError):
        return DEFAULT_DAILY_TOKEN_CAP_GEMINI


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


def get_llm_provider() -> str:
    prov = os.environ.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).strip().lower()
    return prov if prov in ("auto", "groq", "gemini") else DEFAULT_LLM_PROVIDER


def get_llm_provider_order() -> List[str]:
    order_str = os.environ.get("LLM_PROVIDER_ORDER", DEFAULT_LLM_PROVIDER_ORDER).strip().lower()
    items = [p.strip() for p in order_str.split(",") if p.strip() in ("groq", "gemini")]
    return items if items else ["groq", "gemini"]


def get_explain_llm_conditions() -> Set[str]:
    cond_str = os.environ.get("EXPLAIN_LLM_CONDITIONS", DEFAULT_LLM_CONDITIONS).strip().lower()
    return {c.strip() for c in cond_str.split(",") if c.strip()}


def is_condition_allowed_for_llm(condition: str, trigger_category: str) -> bool:
    """
    Checks if condition is permitted to call LLMs (H1).
    Default is 'hypertension' only.
    For dual condition check-in ('both'), only permitted if trigger is a blood pressure one.
    """
    allowed = get_explain_llm_conditions()
    cond = (condition or "").strip().lower()

    if cond == "both":
        bp_triggers = {
            "bp_severe",
            "bp_crisis",
            "bp_urgent",
            "bp_low",
            "bp_change",
            "pregnancy_hypertension",
        }
        return trigger_category in bp_triggers and "hypertension" in allowed

    return cond in allowed


# =============================================================================
# Reading Bands & Cache Key Computation
# =============================================================================
def get_glucose_band(glucose: Optional[float]) -> str:
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
    """Thread-safe in-memory LRU cache with TTL and safety re-validation."""
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

        # 3. Re-validate number grounding
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

        with self._lock:
            self.hits += 1

        hit_result = copy.deepcopy(data["result"])
        hit_result["mode"] = "cache"
        hit_result["rejected_reasons"] = []
        return hit_result

    def put(self, key: Tuple[str, ...], result: Dict[str, Any], cited_chunk_ids: List[str]) -> None:
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
    """In-memory daily token counter resetting on UTC day boundary."""
    def __init__(self, cap: Optional[int] = None, cap_fn: Optional[Callable[[], int]] = None, get_utc_date_fn: Optional[Callable[[], str]] = None):
        self._cap = cap
        self._cap_fn = cap_fn
        self._get_date = get_utc_date_fn or (lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        self._current_date: str = self._get_date()
        self._tokens_used: int = 0
        self._lock = threading.Lock()

    def get_cap(self) -> int:
        if self._cap is not None:
            return self._cap
        if self._cap_fn is not None:
            return self._cap_fn()
        return DEFAULT_DAILY_TOKEN_CAP

    def _sync_date(self) -> None:
        today = self._get_date()
        if today != self._current_date:
            self._current_date = today
            self._tokens_used = 0

    def can_consume(self, estimated_tokens: int = 1000) -> bool:
        with self._lock:
            self._sync_date()
            return (self._tokens_used + estimated_tokens) <= self.get_cap()

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
    """Circuit breaker for LLM explainer calls."""
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
_GLOBAL_TOKEN_GUARD_GROQ = TokenCapGuard(cap_fn=get_daily_token_cap)
_GLOBAL_TOKEN_GUARD_GEMINI = TokenCapGuard(cap_fn=get_daily_token_cap_gemini)
_GLOBAL_BREAKER_GROQ = CircuitBreaker()
_GLOBAL_BREAKER_GEMINI = CircuitBreaker()
_WORKER_SEMAPHORE = threading.Semaphore(get_max_workers())

_METRICS_LOCK = threading.Lock()
_LLM_CALLS_BY_PROVIDER: Dict[str, int] = {"groq": 0, "gemini": 0}
_FALLBACK_COUNTS: Dict[str, int] = {
    "budget_timeout": 0,
    "token_cap": 0,
    "breaker_open": 0,
    "rate_limited": 0,
    "validation_failed": 0,
    "no_llm": 0,
    "no_chunks": 0,
    "busy": 0,
    "condition_template_only": 0,
    "template_corrected": 0,
    "error": 0,
}


def record_llm_call(provider: str) -> None:
    with _METRICS_LOCK:
        _LLM_CALLS_BY_PROVIDER[provider] = _LLM_CALLS_BY_PROVIDER.get(provider, 0) + 1


def record_fallback(reason: str) -> None:
    with _METRICS_LOCK:
        _FALLBACK_COUNTS[reason] = _FALLBACK_COUNTS.get(reason, 0) + 1


def get_explain_guard_metrics() -> Dict[str, Any]:
    with _METRICS_LOCK:
        fallbacks = dict(_FALLBACK_COUNTS)
        calls_groq = _LLM_CALLS_BY_PROVIDER.get("groq", 0)
        calls_gemini = _LLM_CALLS_BY_PROVIDER.get("gemini", 0)
        total_calls = calls_groq + calls_gemini

    tokens_groq = _GLOBAL_TOKEN_GUARD_GROQ.get_tokens_used_today()
    tokens_gemini = _GLOBAL_TOKEN_GUARD_GEMINI.get_tokens_used_today()

    return {
        "tokens_used_today": tokens_groq + tokens_gemini,
        "tokens_used_by_provider": {
            "groq": tokens_groq,
            "gemini": tokens_gemini,
        },
        "cap": _GLOBAL_TOKEN_GUARD_GROQ.get_cap(),
        "caps": {
            "groq": _GLOBAL_TOKEN_GUARD_GROQ.get_cap(),
            "gemini": _GLOBAL_TOKEN_GUARD_GEMINI.get_cap(),
        },
        "breaker_state": _GLOBAL_BREAKER_GROQ.state(),
        "breaker_states": {
            "groq": _GLOBAL_BREAKER_GROQ.state(),
            "gemini": _GLOBAL_BREAKER_GEMINI.state(),
        },
        "cache_size": _GLOBAL_CACHE.size(),
        "cache_hits": _GLOBAL_CACHE.hits,
        "cache_misses": _GLOBAL_CACHE.misses,
        "llm_calls": total_calls,
        "llm_calls_by_provider": {
            "groq": calls_groq,
            "gemini": calls_gemini,
        },
        "groq": {
            "tokens_used_today": tokens_groq,
            "breaker_state": _GLOBAL_BREAKER_GROQ.state(),
            "llm_calls": calls_groq,
            "cap": _GLOBAL_TOKEN_GUARD_GROQ.get_cap(),
        },
        "gemini": {
            "tokens_used_today": tokens_gemini,
            "breaker_state": _GLOBAL_BREAKER_GEMINI.state(),
            "llm_calls": calls_gemini,
            "cap": _GLOBAL_TOKEN_GUARD_GEMINI.get_cap(),
        },
        "template_fallbacks_by_reason": fallbacks,
    }


def reset_explain_guards() -> None:
    """Helper for hermetic test suites to reset all guards to pristine state."""
    global _CACHED_RETRIEVER, _CACHED_CHUNK_COUNT, _CACHED_STORE_ID
    _GLOBAL_CACHE.clear()
    _GLOBAL_TOKEN_GUARD_GROQ.reset()
    _GLOBAL_TOKEN_GUARD_GEMINI.reset()
    _GLOBAL_BREAKER_GROQ.reset()
    _GLOBAL_BREAKER_GEMINI.reset()
    with _METRICS_LOCK:
        _LLM_CALLS_BY_PROVIDER["groq"] = 0
        _LLM_CALLS_BY_PROVIDER["gemini"] = 0
        for k in _FALLBACK_COUNTS:
            _FALLBACK_COUNTS[k] = 0
    _CACHED_RETRIEVER = None
    _CACHED_CHUNK_COUNT = None
    _CACHED_STORE_ID = None
    try:
        import rag.store as rag_store
        rag_store._GLOBAL_DB_CHUNK_STORE = None
    except Exception:
        pass


# =============================================================================
# Cached Retriever Builder (A5)
# =============================================================================
_CACHED_RETRIEVER: Optional[BM25Retriever] = None
_CACHED_CHUNK_COUNT: Optional[int] = None
_CACHED_STORE_ID: Optional[int] = None
_RETRIEVER_LOCK = threading.Lock()


def get_or_build_retriever(store: Optional[ChunkStore]) -> Optional[BM25Retriever]:
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
def _call_with_supported_kwargs(func: Any, **call_kwargs: Any) -> Any:
    try:
        sig = inspect.signature(func)
        has_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if has_var_kwargs:
            return func(**call_kwargs)
        filtered = {k: v for k, v in call_kwargs.items() if k in sig.parameters}
        return func(**filtered)
    except (ValueError, TypeError):
        return func(**call_kwargs)


def guarded_explain(
    triage_result: Dict[str, Any],
    readings: Dict[str, Any],
    language: str = "en",
    store: Optional[ChunkStore] = None,
    llm: Any = None,
    condition: str = "hypertension",
    budget_seconds: Optional[float] = None,
    daily_token_guard: Optional[TokenCapGuard] = None,
    cache: Optional[ExplainCache] = None,
    breaker: Optional[CircuitBreaker] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a fully guarded clinical explanation:
    - Multi-provider routing (auto, groq, gemini).
    - 60% budget allocation to first provider when fallback is available.
    - G3 licence restriction check (blocks Gemini on restricted chunks).
    - H1 condition filter (diabetes check-ins default to template-only).
    - H2 template consistency check (substitutes routine template if reading contradicts).
    - Provider review fields: provider, providers_tried (strictly excluded from patient view).
    """
    start_time = time.monotonic()
    budget = budget_seconds if budget_seconds is not None else get_budget_seconds()
    deadline = start_time + budget

    exp_cache = cache or _GLOBAL_CACHE

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
    cond_str = condition or query_mapping.condition or "hypertension"

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
        cached_hit.setdefault("provider", None)
        cached_hit.setdefault("providers_tried", [])
        return cached_hit

    providers_tried: List[str] = []
    provider_timings: Dict[str, float] = {}

    # Helper for template fallback
    def _make_template_fallback(reason: str, rejected: Optional[List[str]] = None) -> Dict[str, Any]:
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
        final_reason = tmpl.get("reason") or reason
        tmpl["mode"] = "template"
        tmpl["reason"] = final_reason
        tmpl["provider"] = None
        tmpl["providers_tried"] = list(providers_tried)
        tmpl["provider_timings"] = dict(provider_timings)
        record_fallback(final_reason)
        return tmpl

    # 3. Check Condition Gate (H1)
    if not is_condition_allowed_for_llm(cond_str, trigger_category):
        return _make_template_fallback("condition_template_only", ["Condition not permitted for LLM explainer"])

    # 4. Check Guideline Chunks Existence
    if not candidate_chunks and store is not None:
        return _make_template_fallback("no_chunks", ["No matching clinical guideline chunks found"])

    # 5. Check G3 Licence Restriction across chunks
    has_restricted_chunk = any(
        str(c.get("source_id", "")).strip().lower() in LICENCE_RESTRICTED_SOURCES
        for c in candidate_chunks
    )

    # 6. Resolve Candidate Providers
    active_mode = (provider or get_llm_provider()).strip().lower()
    if active_mode == "groq":
        provider_candidates = ["groq"]
    elif active_mode == "gemini":
        provider_candidates = ["gemini"]
    else:
        provider_candidates = get_llm_provider_order()

    # Filter by licence restriction: G3 forbids Gemini if any restricted chunk
    if has_restricted_chunk:
        provider_candidates = [p for p in provider_candidates if p != "gemini"]

    # Filter by configuration, breakers, and token caps
    eligible_providers: List[str] = []
    skipped_reasons: Dict[str, str] = {}

    import llm.groq_client as groq_client
    import llm.gemini_client as gemini_client

    for p in provider_candidates:
        # Determine client callable
        p_configured = False
        if llm is not None:
            if isinstance(llm, dict):
                p_configured = p in llm and llm[p] is not None
            else:
                p_configured = True
        else:
            if p == "groq":
                p_configured = groq_client.is_configured()
            elif p == "gemini":
                p_configured = gemini_client.is_configured()

        if not p_configured:
            skipped_reasons[p] = "no_llm"
            continue

        # Breaker check
        p_breaker = breaker if breaker is not None else (_GLOBAL_BREAKER_GROQ if p == "groq" else _GLOBAL_BREAKER_GEMINI)
        if not p_breaker.allow_call():
            skipped_reasons[p] = "breaker_open"
            continue

        # Token cap check
        p_cap = daily_token_guard if daily_token_guard is not None else (_GLOBAL_TOKEN_GUARD_GROQ if p == "groq" else _GLOBAL_TOKEN_GUARD_GEMINI)
        if not p_cap.can_consume(1000):
            skipped_reasons[p] = "token_cap"
            continue

        eligible_providers.append(p)

    if not eligible_providers:
        # Determine fallback reason from skipped
        if any(r == "breaker_open" for r in skipped_reasons.values()):
            return _make_template_fallback("breaker_open", ["Circuit breaker is OPEN"])
        if any(r == "token_cap" for r in skipped_reasons.values()):
            return _make_template_fallback("token_cap", ["Daily token cap reached"])
        return _make_template_fallback("no_llm", ["No configured LLM provider available"])

    # 7. Check Concurrency Limit (Worker Semaphore)
    acquired = _WORKER_SEMAPHORE.acquire(blocking=False)
    if not acquired:
        return _make_template_fallback("busy", ["Worker pool at maximum capacity"])

    # 8. Multi-Provider Execution Loop
    try:
        from rag.explainer import explain

        for idx, current_provider in enumerate(eligible_providers):
            time_now = time.monotonic()
            time_left = deadline - time_now
            if time_left <= 0.0:
                p_breaker = breaker if breaker is not None else (_GLOBAL_BREAKER_GROQ if current_provider == "groq" else _GLOBAL_BREAKER_GEMINI)
                p_breaker.record_failure(is_rate_limit=False)
                return _make_template_fallback("budget_timeout", ["Total time budget exhausted"])

            has_next = (idx < len(eligible_providers) - 1)
            if has_next:
                # Primary provider gets at most 60% of the remaining time
                prov_budget = min(0.6 * time_left, time_left)
            else:
                prov_budget = time_left

            prov_deadline = time_now + prov_budget
            prov_t0 = time.monotonic()
            providers_tried.append(current_provider)
            record_llm_call(current_provider)

            p_breaker = breaker if breaker is not None else (_GLOBAL_BREAKER_GROQ if current_provider == "groq" else _GLOBAL_BREAKER_GEMINI)
            p_cap = daily_token_guard if daily_token_guard is not None else (_GLOBAL_TOKEN_GUARD_GROQ if current_provider == "groq" else _GLOBAL_TOKEN_GUARD_GEMINI)

            # Resolve provider callable
            prov_callable: Any = None
            if llm is not None:
                if isinstance(llm, dict):
                    prov_callable = llm.get(current_provider)
                else:
                    prov_callable = llm
            else:
                if current_provider == "groq":
                    prov_callable = groq_client.chat_with_usage
                else:
                    prov_callable = gemini_client.chat_with_usage

            worker_result: Dict[str, Any] = {}
            worker_error: Dict[str, Any] = {}
            worker_tokens: Dict[str, int] = {"count": 0}
            token_lock = threading.Lock()
            token_state: Dict[str, bool] = {"recorded": False}

            def _record_tokens_locked() -> None:
                with token_lock:
                    if not token_state["recorded"]:
                        cnt = worker_tokens["count"]
                        if cnt > 0:
                            p_cap.record_usage(cnt)
                        token_state["recorded"] = True

            def _worker():
                try:
                    def _timed_llm(**kwargs):
                        try:
                            kwargs["timeout"] = max(0.1, prov_deadline - time.monotonic())
                            kwargs["max_retries"] = 0
                            kwargs["sdk_max_retries"] = 0
                            if hasattr(prov_callable, "chat_with_usage"):
                                text, tokens = _call_with_supported_kwargs(prov_callable.chat_with_usage, **kwargs)
                                worker_tokens["count"] += tokens
                                return text
                            elif callable(prov_callable):
                                res = _call_with_supported_kwargs(prov_callable, **kwargs)
                                if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], int):
                                    worker_tokens["count"] += res[1]
                                    return res[0]
                                return res
                            elif hasattr(prov_callable, "chat"):
                                return _call_with_supported_kwargs(prov_callable.chat, **kwargs)
                            raise TypeError(f"Invalid callable for provider {current_provider}")
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
                    _record_tokens_locked()

            thread = threading.Thread(target=_worker, daemon=True)
            thread.start()

            # Wait at most prov_budget
            thread.join(timeout=max(0.0, prov_deadline - time.monotonic()))
            prov_duration = time.monotonic() - prov_t0
            provider_timings[current_provider] = round(prov_duration, 3)

            if thread.is_alive():
                # Provider timed out
                p_breaker.record_failure(is_rate_limit=False)
                if has_next:
                    continue
                return _make_template_fallback("budget_timeout", ["LLM execution exceeded time budget"])

            # Check error
            if "error" in worker_error:
                err = worker_error["error"]
                err_str = str(err).lower()
                is_429 = "rate limit" in err_str or "429" in err_str or type(err).__name__ in ("RateLimitError", "GeminiRateLimitError")
                p_breaker.record_failure(is_rate_limit=is_429)
                if has_next:
                    continue
                reason = "rate_limited" if is_429 else "error"
                return _make_template_fallback(reason, [f"LLM exception: {type(err).__name__}"])

            res_data = worker_result.get("data")
            if not res_data:
                p_breaker.record_failure(is_rate_limit=False)
                if has_next:
                    continue
                return _make_template_fallback("error", ["No response received from explainer worker"])

            # Check template fallback from explain()
            if res_data.get("mode") == "template":
                rej_list = res_data.get("rejected_reasons", [])
                if any("LLM execution error" in r for r in rej_list):
                    is_429 = any("rate limit" in r.lower() or "429" in r.lower() for r in rej_list)
                    p_breaker.record_failure(is_rate_limit=is_429)
                    if has_next:
                        continue
                    reason = "rate_limited" if is_429 else "error"
                    res_data["reason"] = reason
                    res_data["provider"] = None
                    res_data["providers_tried"] = list(providers_tried)
                    res_data["provider_timings"] = dict(provider_timings)
                    record_fallback(reason)
                    return res_data

                # Validator rejection: does not trip breaker
                res_data["reason"] = "validation_failed"
                res_data["provider"] = None
                res_data["providers_tried"] = list(providers_tried)
                res_data["provider_timings"] = dict(provider_timings)
                record_fallback("validation_failed")
                return res_data

            # Successful LLM generation!
            p_breaker.record_success()
            res_data["mode"] = "llm"
            res_data["provider"] = current_provider
            res_data["providers_tried"] = list(providers_tried)
            res_data["provider_timings"] = dict(provider_timings)
            res_data["tokens_used"] = worker_tokens["count"]

            # Extract cited chunk ids to populate cache
            cited_cids: List[str] = []
            for s in res_data.get("sentences", []):
                for c in s.get("cites", []):
                    cited_cids.append(str(c))

            exp_cache.put(cache_key, res_data, cited_cids)
            return res_data

        # Fallback if loop finishes without returning
        return _make_template_fallback("error", ["All eligible LLM providers exhausted"])

    finally:
        _WORKER_SEMAPHORE.release()
