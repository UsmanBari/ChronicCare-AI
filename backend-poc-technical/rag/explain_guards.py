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

import llm.gemini_client as gemini_client
import llm.groq_client as groq_client
from rag.explainer import (
    EXPLAINER_VERSION,
    explain,
    get_allowed_numbers,
    get_template_explanation,
    is_template_consistent,
    validate_banned_patterns,
    validate_citations,
    validate_level_consistency,
    validate_number_grounding,
)
from rag.licences import (
    get_restricted_gemini_sources,
    has_complete_attribution,
    is_llm_allowed_for_source,
    is_source_expired,
)
from rag.query_map import build_query_from_triage, is_ramadan_text
from rag.retriever import BM25Retriever
from rag.store import ChunkStore

logger = logging.getLogger(__name__)

# =============================================================================
# Guideline Corpus Licensing Restrictions (G3)
# Source IDs that must NEVER be sent to Google Gemini under any circumstances.
# Backed by single machine-readable source of truth in rag.licences.
# =============================================================================
LICENCE_RESTRICTED_SOURCES: Set[str] = get_restricted_gemini_sources()

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
DEFAULT_LLM_LANGUAGES: str = "en,ur,roman_ur"
ALLOWED_LLM_LANGUAGES: tuple[str, ...] = ("en", "ur", "roman_ur")
DEFAULT_EXPLAIN_MODE: str = "background"
DEFAULT_QUEUE_MAX: int = 50
DEFAULT_JOB_DEADLINE_SECONDS: float = 45.0
DEFAULT_CALL_TIMEOUT_SECONDS: float = 20.0
DEFAULT_GROQ_OTPM: int = 1000

DIABETES_ONLY_SOURCE_PREFIXES: tuple[str, ...] = ("ada_2026", "idf_dar", "aku_diabetes")


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


def get_explain_llm_languages() -> Set[str]:
    raw = os.environ.get("EXPLAIN_LLM_LANGUAGES", DEFAULT_LLM_LANGUAGES).strip().lower()
    parsed = {lang.strip() for lang in raw.split(",") if lang.strip() in ALLOWED_LLM_LANGUAGES}
    return parsed if parsed else {"en"}


def is_language_allowed_for_llm(language: str) -> bool:
    allowed = get_explain_llm_languages()
    lang = (language or "en").strip().lower()
    return lang in allowed


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


def is_patient_diabetic(
    patient_conditions: Optional[List[str]] = None,
    condition: Optional[str] = None,
) -> bool:
    """
    Returns True if the patient is considered diabetic based on patient_conditions
    or fallback single condition string.
    """
    if patient_conditions is not None:
        p_conds = {str(c).lower().strip() for c in patient_conditions}
        return bool(p_conds & {"diabetes", "t2d", "type 2 diabetes", "both"})
    c_clean = str(condition or "").lower().strip()
    return c_clean in ("diabetes", "both") or "diabetes" in c_clean


def get_explain_mode() -> str:
    m = os.environ.get("EXPLAIN_MODE", DEFAULT_EXPLAIN_MODE).strip().lower()
    return m if m in ("background", "inline") else DEFAULT_EXPLAIN_MODE


def get_queue_max() -> int:
    try:
        return int(os.environ.get("EXPLAIN_QUEUE_MAX", str(DEFAULT_QUEUE_MAX)))
    except (ValueError, TypeError):
        return DEFAULT_QUEUE_MAX


def get_job_deadline_seconds() -> float:
    try:
        return float(os.environ.get("EXPLAIN_JOB_DEADLINE_SECONDS", str(DEFAULT_JOB_DEADLINE_SECONDS)))
    except (ValueError, TypeError):
        return DEFAULT_JOB_DEADLINE_SECONDS


def get_call_timeout_seconds() -> float:
    try:
        return float(os.environ.get("EXPLAIN_CALL_TIMEOUT_SECONDS", str(DEFAULT_CALL_TIMEOUT_SECONDS)))
    except (ValueError, TypeError):
        return DEFAULT_CALL_TIMEOUT_SECONDS


def get_groq_otpm() -> int:
    try:
        return int(os.environ.get("EXPLAIN_GROQ_OTPM", str(DEFAULT_GROQ_OTPM)))
    except (ValueError, TypeError):
        return DEFAULT_GROQ_OTPM


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
                    chunk = store.get_chunk(cid) if hasattr(store, "get_chunk") else store.get(cid)
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


# =============================================================================
# Groq Output Token Pacer (Sliding 60-second window)
# =============================================================================
class TokenPacer:
    """Sliding-window pacer tracking output tokens to avoid rate limits."""
    def __init__(self, window_seconds: float = 60.0):
        self._window = window_seconds
        self._records: List[Tuple[float, int]] = []
        self._lock = threading.Lock()

    def get_wait_seconds(self, tokens_needed: int, otpm_limit: int, clock_fn: Optional[Callable[[], float]] = None) -> float:
        now = (clock_fn or time.monotonic)()
        with self._lock:
            cutoff = now - self._window
            self._records = [r for r in self._records if r[0] > cutoff]
            total_used = sum(r[1] for r in self._records)
            if total_used + tokens_needed <= otpm_limit:
                return 0.0
            tokens_to_drop = (total_used + tokens_needed) - otpm_limit
            dropped = 0
            wait_time = 0.0
            for ts, cnt in self._records:
                dropped += cnt
                wait_time = max(wait_time, (ts + self._window) - now)
                if dropped >= tokens_to_drop:
                    break
            return max(0.0, wait_time)

    def record_tokens(self, tokens: int, clock_fn: Optional[Callable[[], float]] = None) -> None:
        if tokens <= 0:
            return
        now = (clock_fn or time.monotonic)()
        with self._lock:
            self._records.append((now, int(tokens)))

    def get_current_usage(self, clock_fn: Optional[Callable[[], float]] = None) -> int:
        now = (clock_fn or time.monotonic)()
        with self._lock:
            cutoff = now - self._window
            return sum(r[1] for r in self._records if r[0] > cutoff)

    def reset(self) -> None:
        with self._lock:
            self._records.clear()


_GLOBAL_GROQ_PACER = TokenPacer()


def _parse_retry_after(error_text: str) -> float:
    import re
    if not error_text:
        return 5.0

    # 1. Match milliseconds format first: e.g. "600ms", "500 ms", "1200 milliseconds" -> min 1.0s
    m_ms = re.search(
        r"(?:try again in|retry after|wait|in)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:ms|milliseconds?)(?:\b|$)",
        error_text,
        re.IGNORECASE,
    )
    if m_ms:
        val_sec = float(m_ms.group(1)) / 1000.0
        return max(1.0, min(val_sec, 30.0))

    # 2. Match minutes and optional seconds: e.g. "1m30s", "1m 30s", "2m", "1 minute 30 seconds"
    m_min = re.search(
        r"(?:try again in|retry after|wait|in)\s*([0-9]+)\s*(?:m(?!s)|min|minutes?)\s*(?:([0-9]+(?:\.[0-9]+)?)\s*(?:s|sec|seconds?)?)?",
        error_text,
        re.IGNORECASE,
    )
    if m_min:
        mins = float(m_min.group(1) or 0)
        secs = float(m_min.group(2) or 0)
        total = mins * 60.0 + secs
        return max(1.0, min(total, 30.0))

    # 3. Match seconds format: e.g. "4.5s", "5 seconds", "10"
    m_sec = re.search(r"(?:try again in|retry after|wait|in)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:s|sec|seconds)?(?:\b|$)", error_text, re.IGNORECASE)
    if m_sec:
        try:
            val = float(m_sec.group(1))
            return max(1.0, min(val, 30.0))
        except (ValueError, TypeError):
            pass
    return 5.0

    # 1. Match minutes and optional seconds: e.g. "1m30s", "1m 30s", "2m", "1 minute 30 seconds"
    m_min = re.search(
        r"(?:try again in|retry after|wait|in)\s*([0-9]+)\s*(?:m|min|minutes?)\s*(?:([0-9]+(?:\.[0-9]+)?)\s*(?:s|sec|seconds?)?)?",
        error_text,
        re.IGNORECASE,
    )
    if m_min:
        mins = float(m_min.group(1) or 0)
        secs = float(m_min.group(2) or 0)
        total = mins * 60.0 + secs
        return max(1.0, min(total, 30.0))

    # 2. Match milliseconds format: e.g. "600ms", "500 ms", "1200 milliseconds" -> min 1.0s
    m_ms = re.search(
        r"(?:try again in|retry after|wait|in)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:ms|milliseconds?)(?:\b|$)",
        error_text,
        re.IGNORECASE,
    )
    if m_ms:
        val_sec = float(m_ms.group(1)) / 1000.0
        return max(1.0, min(val_sec, 30.0))

    # 3. Match seconds format: e.g. "4.5s", "5 seconds", "10"
    m = re.search(r"(?:try again in|retry after|wait|in)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:s|sec|seconds)?(?:\b|$)", error_text, re.IGNORECASE)
    if m:
        try:
            val = float(m.group(1))
            return max(1.0, min(val, 30.0))
        except (ValueError, TypeError):
            pass
    return 5.0

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
    "language_template_only": 0,
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
        "queue_length": _get_safe_queue_length(),
        "mode": get_explain_mode(),
    }



def _get_safe_queue_length() -> int:
    try:
        from rag.explain_jobs import get_queue_length
        return get_queue_length()
    except Exception:
        return 0


def reset_explain_guards() -> None:
    """Helper for hermetic test suites to reset all guards to pristine state."""
    global _CACHED_RETRIEVER, _CACHED_CHUNK_COUNT, _CACHED_STORE_ID
    _GLOBAL_CACHE.clear()
    _GLOBAL_TOKEN_GUARD_GROQ.reset()
    _GLOBAL_TOKEN_GUARD_GEMINI.reset()
    _GLOBAL_BREAKER_GROQ.reset()
    _GLOBAL_GROQ_PACER.reset()
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



# =============================================================================
# Pre-Queue / LLM Eligibility Check
# =============================================================================
def check_llm_eligibility(
    condition: str,
    trigger_category: str,
    store: Optional[ChunkStore] = None,
    candidate_chunks: Optional[List[Dict[str, Any]]] = None,
    provider: Optional[str] = None,
    breaker: Optional[CircuitBreaker] = None,
    daily_token_guard: Optional[TokenCapGuard] = None,
    llm: Any = None,
    language: str = "en",
) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether an LLM call can be attempted for this check-in.
    Returns (True, None) if eligible, or (False, reason) if ineligible.
    Shares identical evaluation helpers and order with guarded_explain.
    """
    # 0. Language check: if check-in language is not allowed for LLM, return template reason
    if not is_language_allowed_for_llm(language):
        return False, "language_template_only"

    cond_str = (condition or "hypertension").strip().lower()

    # 1. Condition check (H1)
    if not is_condition_allowed_for_llm(cond_str, trigger_category):
        return False, "condition_template_only"

    # 2. Guideline chunks check
    if candidate_chunks is None and store is not None:
        try:
            if store.count() == 0:
                return False, "no_chunks"
        except Exception:
            pass
    elif candidate_chunks is not None and len(candidate_chunks) == 0 and store is not None:
        return False, "no_chunks"

    # 3. Provider candidates and licensing (G3)
    has_restricted_chunk = False
    if candidate_chunks:
        has_restricted_chunk = any(
            str(c.get("source_id", "")).strip().lower() in LICENCE_RESTRICTED_SOURCES
            for c in candidate_chunks
        )

    active_mode = (provider or get_llm_provider()).strip().lower()
    if active_mode == "groq":
        provider_candidates = ["groq"]
    elif active_mode == "gemini":
        provider_candidates = ["gemini"]
    else:
        provider_candidates = get_llm_provider_order()

    if has_restricted_chunk:
        provider_candidates = [p for p in provider_candidates if p != "gemini"]

    # Providers already imported at module top-level

    skipped_reasons: Dict[str, str] = {}
    eligible: List[str] = []

    for p in provider_candidates:
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

        p_breaker = breaker if breaker is not None else (_GLOBAL_BREAKER_GROQ if p == "groq" else _GLOBAL_BREAKER_GEMINI)
        if not p_breaker.allow_call():
            skipped_reasons[p] = "breaker_open"
            continue

        p_cap = daily_token_guard if daily_token_guard is not None else (_GLOBAL_TOKEN_GUARD_GROQ if p == "groq" else _GLOBAL_TOKEN_GUARD_GEMINI)
        if not p_cap.can_consume(1000):
            skipped_reasons[p] = "token_cap"
            continue

        eligible.append(p)

    if not eligible:
        if any(r == "breaker_open" for r in skipped_reasons.values()):
            return False, "breaker_open"
        if any(r == "token_cap" for r in skipped_reasons.values()):
            return False, "token_cap"
        return False, "no_llm"

    return True, None


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
    mode: Optional[str] = None,
    clock_fn: Optional[Callable[[], float]] = None,
    sleep_fn: Optional[Callable[[float], None]] = None,
    patient_conditions: Optional[List[str]] = None,
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
    now_fn = clock_fn or time.monotonic
    nap_fn = sleep_fn or time.sleep
    active_explain_mode = (mode or "inline").strip().lower()
    start_time = now_fn()
    if budget_seconds is not None:
        budget = budget_seconds
    elif active_explain_mode == "background":
        budget = get_job_deadline_seconds()
    else:
        budget = get_budget_seconds()
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
            exclude_prefixes = (
                ()
                if is_patient_diabetic(patient_conditions=patient_conditions, condition=cond_str)
                else DIABETES_ONLY_SOURCE_PREFIXES
            )
            candidate_chunks = retriever.retrieve(
                query=query_mapping.query_text,
                top_k=3,
                condition=query_mapping.condition,
                min_priority=query_mapping.min_priority,
                exclude_source_prefixes=exclude_prefixes,
            )
            if len(candidate_chunks) < 2:
                candidate_chunks = retriever.retrieve(
                    query=query_mapping.query_text,
                    top_k=3,
                    min_priority=query_mapping.min_priority,
                    exclude_source_prefixes=exclude_prefixes,
                )

    providers_tried: List[str] = []
    provider_timings: Dict[str, float] = {}

    # Helper for template fallback
    def _make_template_fallback(reason: str, rejected: Optional[List[str]] = None) -> Dict[str, Any]:
        reasons_list = [f"Guard fallback: {reason}"]
        if rejected:
            for r in rejected:
                clean_r = str(r)
                if "org_" in clean_r or "{" in clean_r:
                    clean_r = "rate_limited: HTTP 429" if ("429" in clean_r or "rate" in clean_r.lower()) else "LLM execution error"
                reasons_list.append(clean_r)
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
        # Strip any provider bodies or org IDs from stored rejected reasons
        tmpl["rejected_reasons"] = [
            ("rate_limited: HTTP 429" if ("org_" in str(r) or "{" in str(r)) else str(r))
            for r in tmpl.get("rejected_reasons", [])
        ]
        record_fallback(final_reason)
        return tmpl

    # 1.5 Check Language Gate: if check-in language is not allowed for LLM, return template immediately (never read/write cache)
    if not is_language_allowed_for_llm(target_lang):
        return _make_template_fallback("language_template_only", ["Language not permitted for LLM explainer"])

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
        cached_hit["provider_timings"] = {}
        cached_hit["tokens_used"] = 0
        return cached_hit

    # 3. Check Condition Gate (H1)
    if not is_condition_allowed_for_llm(cond_str, trigger_category):
        return _make_template_fallback("condition_template_only", ["Condition not permitted for LLM explainer"])

    # 4. Check Guideline Chunks Existence
    if not candidate_chunks and store is not None:
        return _make_template_fallback("no_chunks", ["No matching clinical guideline chunks found"])

    # Filter expired chunks at runtime (X2)
    if candidate_chunks:
        candidate_chunks = [c for c in candidate_chunks if not is_source_expired(c.get("source_id", ""))]

    is_ramadan_checkin = (
        trigger_category == "ramadan_fasting"
        or is_ramadan_text(query_mapping.query_text)
        or any(is_ramadan_text(str(r)) for r in triage_copy.get("reasons", []))
    )

    # Point 1: IDF-DAR (idf_dar_2021) chunks may be used only for Ramadan check-ins
    if cond_str == "diabetes" and not is_ramadan_checkin and candidate_chunks:
        candidate_chunks = [
            c for c in candidate_chunks
            if not str(c.get("source_id", "")).strip().lower().startswith("idf_dar")
        ]

    # 5. Check G3 Licence Restriction across chunks (Gemini prohibited if ANY candidate chunk is restricted)
    has_restricted_chunk = any(
        str(c.get("source_id", "")).strip().lower() in LICENCE_RESTRICTED_SOURCES
        for c in candidate_chunks
    )

    # Attribution check (X4): sources requiring attribution cannot be used if citation or DOI is missing or 'TO FILL BY USMAN'
    if candidate_chunks:
        attribution_valid_chunks = [
            c for c in candidate_chunks
            if has_complete_attribution(c.get("source_id", ""), chunk=c)
        ]
        if len(attribution_valid_chunks) < len(candidate_chunks) and not attribution_valid_chunks and store is not None:
            return _make_template_fallback("licence_restricted", ["Sources require full citation and DOI attribution before use"])
        candidate_chunks = attribution_valid_chunks

    # Point 1: Diabetes, non-Ramadan check-ins: if no ADA chunk survives attribution/licence filters, do NOT send other chunks to LLM
    if cond_str == "diabetes" and not is_ramadan_checkin and store is not None:
        has_surviving_ada = any(
            str(c.get("source_id", "")).strip().lower().startswith("ada_2026")
            for c in candidate_chunks
        )
        if not has_surviving_ada:
            return _make_template_fallback(
                "licence_restricted",
                ["No valid ADA guideline chunks available for non-Ramadan diabetes explanation"]
            )

    # F6: ADA and other diabetes-only guidelines are for people with diabetes.
    # Use diabetes guidelines only when the PATIENT's conditions include diabetes (both-condition patients: allowed).
    # For a patient without diabetes, drop any diabetes-only guideline chunks (DIABETES_ONLY_SOURCE_PREFIXES).
    if not is_patient_diabetic(patient_conditions=patient_conditions, condition=cond_str) and candidate_chunks:
        candidate_chunks = [
            c for c in candidate_chunks
            if not any(
                str(c.get("source_id") or c.get("id") or c.get("chunk_id") or "").startswith(p)
                for p in DIABETES_ONLY_SOURCE_PREFIXES
            )
        ]
        if not candidate_chunks and store is not None:
            return _make_template_fallback("no_chunks", ["No matching clinical guideline chunks found"])

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

    # Filter by licence restrictions (X3 enforces provider permissions)
    filtered_provider_candidates: List[str] = []
    licence_skipped: List[str] = []

    for p in provider_candidates:
        if candidate_chunks:
            allowed_chunks = [
                c for c in candidate_chunks
                if is_llm_allowed_for_source(c.get("source_id", ""), provider=p)
            ]
            if not allowed_chunks:
                licence_skipped.append(p)
                continue

        filtered_provider_candidates.append(p)

    if (not provider_candidates and has_restricted_chunk) or (not filtered_provider_candidates and licence_skipped):
        return _make_template_fallback("licence_restricted", ["Retrieved chunks restricted by guideline licence for configured LLM provider"])

    provider_candidates = filtered_provider_candidates

    # Filter by configuration, breakers, and token caps
    eligible_providers: List[str] = []
    skipped_reasons: Dict[str, str] = {}

    # Providers already imported at module top-level

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

        for idx, current_provider in enumerate(eligible_providers):
            time_now = now_fn()
            time_left = deadline - time_now
            if time_left <= 0.0:
                p_breaker = breaker if breaker is not None else (_GLOBAL_BREAKER_GROQ if current_provider == "groq" else _GLOBAL_BREAKER_GEMINI)
                p_breaker.record_failure(is_rate_limit=False)
                return _make_template_fallback("budget_timeout", ["Total time budget exhausted"])

            has_next = (idx < len(eligible_providers) - 1)

            # Groq OTPM pacer in background mode (before the job's first Groq call)
            if active_explain_mode == "background" and current_provider == "groq":
                from rag.explainer import get_explain_max_tokens
                wait_sec = _GLOBAL_GROQ_PACER.get_wait_seconds(
                    tokens_needed=get_explain_max_tokens(),
                    otpm_limit=get_groq_otpm(),
                    clock_fn=now_fn,
                )
                if wait_sec > 0.0:
                    if (now_fn() + wait_sec + 1.0) <= deadline:
                        nap_fn(wait_sec)
                    elif has_next:
                        # Skip directly to Gemini fallback if pacer wait exceeds deadline
                        continue
                    else:
                        return _make_template_fallback("budget_timeout", ["Pacer wait exceeds deadline"])

            time_left = deadline - now_fn()
            if time_left <= 0.0:
                p_breaker = breaker if breaker is not None else (_GLOBAL_BREAKER_GROQ if current_provider == "groq" else _GLOBAL_BREAKER_GEMINI)
                p_breaker.record_failure(is_rate_limit=False)
                return _make_template_fallback("budget_timeout", ["Total time budget exhausted"])

            if active_explain_mode == "background":
                # In background mode, Groq gets up to call timeout; Gemini gets remaining time
                if current_provider == "groq" and has_next:
                    prov_budget = min(time_left, get_call_timeout_seconds())
                else:
                    prov_budget = time_left
            else:
                if has_next:
                    # Primary provider gets at most 60% of the remaining time
                    prov_budget = min(0.6 * time_left, time_left)
                else:
                    prov_budget = time_left

            prov_deadline = now_fn() + prov_budget
            prov_deadline_ref = [prov_deadline]
            prov_t0 = now_fn()
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
                    prov_callable = groq_client.chat_with_detailed_usage
                else:
                    prov_callable = gemini_client.chat_with_detailed_usage

            max_prov_attempts = 2 if active_explain_mode == "background" else 1
            prov_attempt_succeeded = False
            prov_res_final: Optional[Dict[str, Any]] = None

            for prov_attempt in range(max_prov_attempts):
                worker_result: Dict[str, Any] = {}
                worker_error: Dict[str, Any] = {}
                worker_tokens: Dict[str, int] = {"count": 0, "completion": 0}
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
                                # Check pacer before every Groq call (English and translation) in background mode
                                call_max_tokens = int(kwargs.get("max_tokens") or 250)
                                if active_explain_mode == "background" and current_provider == "groq":
                                    wait_sec = _GLOBAL_GROQ_PACER.get_wait_seconds(
                                        tokens_needed=call_max_tokens,
                                        otpm_limit=get_groq_otpm(),
                                        clock_fn=now_fn,
                                    )
                                    if wait_sec > 0.0:
                                        if (now_fn() + wait_sec + 1.0) <= deadline:
                                            prov_deadline_ref[0] = min(deadline, prov_deadline_ref[0] + wait_sec)
                                            nap_fn(wait_sec)
                                        else:
                                            raise TimeoutError("Pacer wait exceeds deadline")

                                if active_explain_mode == "background":
                                    kwargs["timeout"] = min(
                                        get_call_timeout_seconds(),
                                        max(0.1, prov_deadline_ref[0] - now_fn()),
                                    )
                                else:
                                    kwargs["timeout"] = max(0.1, prov_deadline - now_fn())
                                kwargs["max_retries"] = 0
                                kwargs["sdk_max_retries"] = 0

                                text_out = None
                                c_tok = 0
                                tot_tok = 0

                                if hasattr(prov_callable, "chat_with_detailed_usage"):
                                    text_out, u_dict = _call_with_supported_kwargs(prov_callable.chat_with_detailed_usage, **kwargs)
                                    tot_tok = u_dict.get("total_tokens", 0)
                                    c_tok = u_dict.get("completion_tokens", 0)
                                elif hasattr(prov_callable, "chat_with_usage"):
                                    text_out, tokens = _call_with_supported_kwargs(prov_callable.chat_with_usage, **kwargs)
                                    tot_tok = tokens
                                    c_tok = tokens
                                elif callable(prov_callable):
                                    res = _call_with_supported_kwargs(prov_callable, **kwargs)
                                    if isinstance(res, tuple) and len(res) == 2:
                                        if isinstance(res[1], dict):
                                            tot_tok = res[1].get("total_tokens", 0)
                                            c_tok = res[1].get("completion_tokens", 0)
                                        elif isinstance(res[1], int):
                                            tot_tok = res[1]
                                            c_tok = res[1]
                                        text_out = res[0]
                                    else:
                                        text_out = res
                                elif hasattr(prov_callable, "chat"):
                                    text_out = _call_with_supported_kwargs(prov_callable.chat, **kwargs)
                                else:
                                    raise TypeError(f"Invalid callable for provider {current_provider}")

                                # Record tokens immediately on EVERY call that returned usage
                                worker_tokens["count"] += tot_tok
                                worker_tokens["completion"] += c_tok
                                if current_provider == "groq" and c_tok > 0:
                                    _GLOBAL_GROQ_PACER.record_tokens(c_tok, clock_fn=now_fn)

                                return text_out
                            except Exception as exc:
                                worker_error["error"] = exc
                                raise

                        allowed_for_curr = [
                            c for c in candidate_chunks
                            if is_llm_allowed_for_source(c.get("source_id", ""), provider=current_provider)
                        ]
                        res = explain(
                            triage_result=triage_copy,
                            readings=readings_copy,
                            language=target_lang,
                            store=store,
                            llm=_timed_llm,
                            candidate_chunks=allowed_for_curr,
                            provider=current_provider,
                        )
                        worker_result["data"] = res
                    except Exception as exc:
                        worker_error["error"] = exc
                    finally:
                        _record_tokens_locked()

                thread = threading.Thread(target=_worker, daemon=True)
                thread.start()

                wall_t0 = time.monotonic()
                wall_limit = (deadline - start_time) + 5.0

                if active_explain_mode == "background":
                    while thread.is_alive():
                        rem_prov = prov_deadline_ref[0] - now_fn()
                        if rem_prov <= 0.0:
                            break
                        if (time.monotonic() - wall_t0) > wall_limit:
                            break
                        thread.join(timeout=min(0.2, max(0.05, rem_prov)))
                else:
                    thread.join(timeout=max(0.0, prov_deadline - now_fn()))
                prov_duration = now_fn() - prov_t0
                provider_timings[current_provider] = round(prov_duration, 3)

                if thread.is_alive():
                    # Provider timed out
                    p_breaker.record_failure(is_rate_limit=False)
                    if has_next:
                        break
                    return _make_template_fallback("budget_timeout", ["LLM execution exceeded time budget"])

                # Check error
                if "error" in worker_error:
                    err = worker_error["error"]
                    err_str = str(err).lower()
                    is_429 = "rate limit" in err_str or "429" in err_str or type(err).__name__ in ("RateLimitError", "GeminiRateLimitError")
                    is_parse = type(err).__name__ in ("JSONDecodeError",) or "jsondecodeerror" in err_str or "parse_error" in err_str
                    exc_type = type(err).__name__
                    if is_parse:
                        # Malformed model answer is a validation failure, not an outage: do not trip breaker
                        if has_next:
                            break
                        return _make_template_fallback("validation_failed", [f"parse_error: {exc_type}"])
                    elif is_429:
                        sanitized_reason = f"rate_limited: {exc_type}: HTTP 429"
                        if active_explain_mode == "background":
                            # In background mode, 429 does NOT trip circuit breaker!
                            if prov_attempt < max_prov_attempts - 1:
                                wait_dur = _parse_retry_after(str(err))
                                if (now_fn() + wait_dur + 1.0) <= deadline:
                                    nap_fn(wait_dur)
                                    continue
                            # If already retried or not enough time:
                            if has_next:
                                break
                            return _make_template_fallback("rate_limited", [sanitized_reason])
                        else:
                            p_breaker.record_failure(is_rate_limit=True)
                            if has_next:
                                break
                            return _make_template_fallback("rate_limited", [sanitized_reason])
                    else:
                        p_breaker.record_failure(is_rate_limit=False)
                        if has_next:
                            break
                        code = getattr(err, "status_code", None) or getattr(err, "status", None)
                        code_str = f": HTTP {code}" if code else ""
                        return _make_template_fallback("error", [f"error: {exc_type}{code_str}"])

                res_data = worker_result.get("data")
                if not res_data:
                    p_breaker.record_failure(is_rate_limit=False)
                    if has_next:
                        break
                    return _make_template_fallback("error", ["No response received from explainer worker"])

                # Check template fallback from explain()
                if res_data.get("mode") == "template":
                    rej_list = res_data.get("rejected_reasons", [])
                    # F4: Parse error is a bad answer, not an outage: validation_failed without tripping breaker
                    if any("parse_error" in str(r).lower() for r in rej_list) or res_data.get("reason") == "validation_failed":
                        res_data["reason"] = "validation_failed"
                        res_data["provider"] = None
                        res_data["providers_tried"] = list(providers_tried)
                        res_data["provider_timings"] = dict(provider_timings)
                        record_fallback("validation_failed")
                        return res_data

                    if any("LLM execution error" in r for r in rej_list):
                        is_429 = any("rate limit" in r.lower() or "429" in r.lower() for r in rej_list)
                        if is_429:
                            if active_explain_mode == "background":
                                if prov_attempt < max_prov_attempts - 1:
                                    err_msg = str(worker_error.get("error", "")) or " ".join(rej_list)
                                    wait_dur = _parse_retry_after(err_msg)
                                    if (now_fn() + wait_dur + 1.0) <= deadline:
                                        nap_fn(wait_dur)
                                        continue
                                if has_next:
                                    break
                                res_data["reason"] = "rate_limited"
                                res_data["provider"] = None
                                res_data["providers_tried"] = list(providers_tried)
                                res_data["provider_timings"] = dict(provider_timings)
                                record_fallback("rate_limited")
                                return res_data
                            else:
                                p_breaker.record_failure(is_rate_limit=True)
                                if has_next:
                                    break
                                res_data["reason"] = "rate_limited"
                                res_data["provider"] = None
                                res_data["providers_tried"] = list(providers_tried)
                                res_data["provider_timings"] = dict(provider_timings)
                                record_fallback("rate_limited")
                                return res_data
                        else:
                            p_breaker.record_failure(is_rate_limit=False)
                            if has_next:
                                break
                            res_data["reason"] = "error"
                            res_data["provider"] = None
                            res_data["providers_tried"] = list(providers_tried)
                            res_data["provider_timings"] = dict(provider_timings)
                            record_fallback("error")
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

            # If attempt failed and has_next, loop continues to next provider (e.g. Gemini)
            if has_next:
                continue

        # Fallback if loop finishes without returning
        return _make_template_fallback("error", ["All eligible LLM providers exhausted"])

    finally:
        _WORKER_SEMAPHORE.release()
