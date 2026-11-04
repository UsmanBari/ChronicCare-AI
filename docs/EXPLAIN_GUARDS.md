# Explainer Safety Guards Architecture & Operations Guide

**Audience:** Backend Engineers, System Operators, Clinicians, and QA.  
**Feature Flag:** `EXPLAIN_ENABLED` (Default: `false` / OFF).  
**Status:** Active in v1.0.  

---

## 1. Architectural Overview & Motto

> **Motto:** *"The model proposes, the rules decide."*

In ChronicCare AI, clinical decisions (such as triage levels `routine`, `review`, `urgent`, `emergency`) are strictly determined by deterministic clinical rule engines. LLMs **never** determine triage levels, and an explanation **never** alters or overrides a triage decision.

When `EXPLAIN_ENABLED=true`, the Guideline Explainer provides patients with concise, plain-language clinical context derived from verified clinical guidelines (e.g. ADA, ACC/AHA). To ensure patient safety, uptime, and strict cost controls, the explainer is wrapped by five hermetic safety guards:

```mermaid
flowchart TD
    Req[Check-in Completion] --> ChkFlag{EXPLAIN_ENABLED?}
    ChkFlag -- false --> RetNone[Return explanation = null]
    ChkFlag -- true --> Emerg{Emergency Check-in?}
    Emerg -- true --> RetNone
    Emerg -- false --> CacheChk{In-Memory Cache & Re-validation}
    CacheChk -- Hit & Valid --> RetCache[Return mode='cache']
    CacheChk -- Miss --> BreakerChk{Circuit Breaker Closed?}
    BreakerChk -- Open --> FallbackBreaker[Return mode='template', reason='breaker_open']
    BreakerChk -- Closed/Trial --> TokenCapChk{Daily Token Cap Available?}
    TokenCapChk -- Exceeded --> FallbackCap[Return mode='template', reason='token_cap']
    TokenCapChk -- OK --> BudgetChk{Time Budget Remaining?}
    BudgetChk -- Timeout --> FallbackBudget[Return mode='template', reason='budget_timeout']
    BudgetChk -- OK --> WorkerPool{Worker Semaphore Free?}
    WorkerPool -- Saturated --> FallbackBusy[Return mode='template', reason='busy']
    WorkerPool -- Slot Acquired --> LLMDispatch[Spawn Thread & Call Groq LLM]
    LLMDispatch --> HardWait{Hard Join Within Budget?}
    HardWait -- Timed Out --> FallbackTimeout[Return mode='template', reason='budget_timeout']
    HardWait -- Finished --> Validators{Validators V1-V5 Pass?}
    Validators -- Failed --> FallbackVal[Return mode='template', reason='validation_failed']
    Validators -- Passed --> CachePut[Populate LRU Cache] --> RetLLM[Return mode='llm']
```

---

## 2. Safety Guards Specification

### Guard 1: Hard Time Budget (`EXPLAIN_BUDGET_SECONDS`)
- **Default:** `3.0` s. Bounds: `1.0` s – `10.0` s.
- **Behavior:** The entire explainer pipeline (retrieval, prompt construction, LLM generation, JSON parsing, and safety validation) must complete within the wall-clock budget.
- **Timeout Isolation:** The worker thread executes as a daemon. If `join()` reaches the deadline, the main request thread aborts waiting immediately and returns the pre-verified deterministic template with `mode='template'`, `reason='budget_timeout'`. The patient **never waits longer than budget + 1 s**.
- **Late Thread Accounting:** If a worker thread times out but finishes upstream execution in the background, its token usage is safely credited to the daily token counter under a lock with `recorded` / `consumed_by_caller` flag, while its generated text is permanently discarded.
- **Concurrency Isolation:** A hung LLM thread does not block subsequent check-ins because each check-in uses independent thread isolation bounded by a concurrency semaphore.
- **No Background Retries:** Calls into `chat_with_usage` strictly pass `max_retries=0` and `sdk_max_retries=0` alongside `timeout <= budget` so a timed-out call never retries in the background.

### Guard 2: Daily Token Cap (`EXPLAIN_DAILY_TOKEN_CAP`)
- **Default:** `150,000` tokens per UTC day (~$0.07–$0.15/day on Groq `llama-3.3-70b-versatile`). Bounds: `10,000` – `1,000,000`.
- **Behavior:** Tracks cumulative prompt and completion tokens. When `used_tokens + 1,000 > cap`, all LLM dispatch is skipped and instantaneous template explanations are returned with `mode='template'`, `reason='token_cap'`.
- **Rollover:** The counter resets automatically at 00:00:00 UTC.

### Guard 3: In-Memory Bounded LRU Cache & Strict Safety Re-validation (`EXPLAIN_CACHE_MAX`, `EXPLAIN_CACHE_TTL_SECONDS`)
- **Capacity & TTL:** Bounded 500-item LRU cache (`EXPLAIN_CACHE_MAX=500`), 24-hour TTL (`EXPLAIN_CACHE_TTL_SECONDS=86400.0`).
- **Privacy Preservation:** Cache keys are strictly abstract categorical tuples:
  `[trigger_category, triage_level, glucose_band, bp_band, language, condition]`
  **Cache keys never contain user IDs, patient names, dates of birth, or raw vital reading values.**
- **Strict Safety Re-validation (A3):** Cached entries are **never blindly reused**. On every cache hit, the entry undergoes rigorous re-validation against the current check-in context:
  1. **Source Existence:** All cited chunk IDs must exist in the active guideline store.
  2. **Citation Grounding:** Re-runs citation validator V2.
  3. **Number Grounding:** Re-runs numerical grounding V3 against the **current** patient's allowed numbers. If the cached text mentions a numerical value not present in the current readings, re-validation rejects the hit as a miss and dispatches to the LLM.
  4. **Banned Patterns & Level Consistency:** Re-runs validators V4 and V5 against the decided triage level.
- **Template Exclusion:** Errors and template fallbacks are never cached.

### Guard 4: Circuit Breaker (`EXPLAIN_BREAKER_FAILURES`, `EXPLAIN_BREAKER_COOLDOWN_SECONDS`)
- **Threshold & Cooldown:** 3 consecutive failures (`EXPLAIN_BREAKER_FAILURES=3`) trip the breaker to `OPEN` for a 600.0-second cooldown (`EXPLAIN_BREAKER_COOLDOWN_SECONDS=600.0`).
- **Instant Rate-Limit Trip:** Any HTTP 429 (`RateLimitError` or `"rate limit"`) trips the breaker immediately on the first occurrence.
- **Validator Independence:** Rejection by clinical safety validators (V1–V5) indicates correct validator function, **not** upstream infrastructure failure; validator rejections do **not** record breaker failures.
- **Half-Open Trial:** Once cooldown expires, the breaker transitions to `HALF_OPEN` and permits exactly 1 trial call. If the trial succeeds, the breaker resets to `CLOSED`. If it fails, the breaker trips back to `OPEN`.

### Guard 5: BM25 Retriever Reuse & Thread-Safe Caching (A5)
- **Behavior:** The Okapi BM25 retriever index is built once and cached in memory. Subsequent check-ins reuse the pre-indexed structure in $\mathcal{O}(1)$ time rather than re-indexing guideline text on every check-in. If the underlying chunk store changes (detected by store instance ID or total chunk count), the cache invalidates and rebuilds automatically.

---

## 3. Environment Variables Reference

| Variable | Type | Default | Valid Range | Purpose |
|---|---|---|---|---|
| `EXPLAIN_ENABLED` | bool | `false` | `true`, `false` | Master feature flag. When `false`, zero guard or LLM code runs and `explanation` is `null`. |
| `EXPLAIN_BUDGET_SECONDS` | float | `3.0` | `1.0` – `10.0` | Hard wall-clock execution budget in seconds. |
| `EXPLAIN_DAILY_TOKEN_CAP` | int | `150000` | `10000` – `1000000` | Maximum Groq total tokens allowed per UTC calendar day. |
| `EXPLAIN_CACHE_MAX` | int | `500` | `50` – `5000` | Maximum number of entries stored in the LRU explanation cache. |
| `EXPLAIN_CACHE_TTL_SECONDS` | float | `86400.0` | `60.0` – `604800.0` | Time-to-live for cached validated explanations in seconds. |
| `EXPLAIN_BREAKER_FAILURES` | int | `3` | `1` – `10` | Number of consecutive upstream errors before opening circuit breaker. |
| `EXPLAIN_BREAKER_COOLDOWN_SECONDS` | float | `600.0` | `5.0` – `3600.0` | Cooldown duration before attempting a trial call in half-open state. |
| `EXPLAIN_POOL_MAX_WORKERS` | int | `8` | `4` – `32` | Maximum concurrent background LLM worker threads. |

---

## 4. In-Memory vs. Persistent State Justification

In the ChronicCare AI prototype, all guard states (token counters, circuit breaker states, LRU cache, worker semaphores) are stored **in-memory**:
1. **Zero Database Migrations:** Requires no extra tables, Redis clusters, or foreign keys in SQLite / MySQL.
2. **Hermetic Resilience:** Process restarts safely reset counters and circuit breakers. If a deployment had an unhealthy upstream connection that is resolved during a deploy, the circuit breaker resets cleanly.
3. **Low Latency:** In-memory checks complete in under 5 microseconds ($\mu\text{s}$), adding zero overhead to the check-in completion path.
4. **Safety Invariance:** In-memory cache re-validation guarantees that even if state is restored or warmed, no patient can ever receive mismatched numerical readings.

---

## 5. Patient View vs. Provider Review View

The presentation of the explanation is strictly segregated between patient and provider endpoints:

| Dimension | Patient View (`POST /api/checkins/{id}/complete`) | Provider View (`GET /api/provider/review/{id}`) |
|---|---|---|
| **Tone & Style** | Reassuring, calm, plain-language (max 35 words/sentence). | Formal clinical summary with audit metadata. |
| **Citations** | Shown with public titles (e.g. ADA 2024 Glycemic Targets). | Includes full chunk IDs, section paths, and guideline editions. |
| **Probability & ML** | **Strictly absent.** Never includes percentages or logits. | Includes full quantitative probability, model versions, and caveats. |
| **Rejection Audit** | Not shown (returns pre-verified template without error traces). | `rejected_reasons` array details any validator checks that failed. |
| **Mode & Reason** | Present (`mode` and `reason` if fallback). | Full explainer metadata including delivery mode and reason code. |

---

## 6. Troubleshooting & Fallback Reason Codes

Whenever `mode == "template"`, the `reason` field indicates why deterministic fallback was selected:

| Reason Code | Root Cause | Operator Action |
|---|---|---|
| `budget_timeout` | Groq LLM latency exceeded `EXPLAIN_BUDGET_SECONDS` (3.0 s). | Check Groq API status. If network latency is elevated, increase `EXPLAIN_BUDGET_SECONDS` to 5.0 s. |
| `token_cap` | Daily token usage reached `EXPLAIN_DAILY_TOKEN_CAP` (150,000). | Normal cost-cap operation. Check token usage via `get_explain_guard_metrics()`. Reset occurs at 00:00 UTC. If traffic has grown, increase cap. |
| `breaker_open` | 3 consecutive timeouts or connection errors tripped circuit breaker. | Inspect upstream Groq logs. The breaker will test a trial call after 600 seconds. |
| `rate_limited` | HTTP 429 Too Many Requests received from Groq. | Groq rate tier saturated. Breaker opened immediately for 600 s cooldown to allow token bucket refill. |
| `validation_failed` | Generated text failed clinical validator (V1 structure, V2 citation, V3 numbers, V4 forbidden phrase, or V5 level mismatch). | Normal safety behavior. The system safely suppressed ungrounded text and delivered deterministic clinical guidance. |
| `no_llm` | `GROQ_API_KEY` is not configured or LLM client initialization failed. | Configure `GROQ_API_KEY` in environment. |
| `no_chunks` | Retrieval returned 0 relevant guideline chunks for this condition. | Check database seeding (`init_local_db.py`). |
| `busy` | All worker semaphore slots (`EXPLAIN_POOL_MAX_WORKERS`) are in use. | High concurrent traffic spike. Increase `EXPLAIN_POOL_MAX_WORKERS` (default 8). |
| `error` | Upstream JSON deserialization or network socket exception. | Inspect backend application error logs. |

---

## 7. Go-Live Checklist (When Flipping `EXPLAIN_ENABLED=true` in Production)

Before enabling the patient-facing explainer in production:

- [ ] **1. Groq Credentials Verified:** `GROQ_API_KEY` is provisioned and verified using `python scripts/explain_live_smoke.py`. Output confirms `mode: llm` with valid citations.
- [ ] **2. Daily Token Cap Set:** `EXPLAIN_DAILY_TOKEN_CAP` is configured (default 150,000 tokens ~ \$0.07–\$0.15/day).
- [ ] **3. Latency Budget Verified:** `EXPLAIN_BUDGET_SECONDS` is set to `3.0`. Verify with `python scripts/measure_explain_latency.py` that p95 latency remains under 3.5 seconds.
- [ ] **4. Cache Warming:** Run guideline chunk verification on startup to ensure `get_or_build_retriever()` is warmed and indexed.
- [ ] **5. Breaker Alert Monitoring:** Ensure observability checks on `/api/health` or metrics output alert when `breaker_state != "closed"`.
- [ ] **6. Clinical Safety Reminders:** Remind clinical staff that the explainer strictly reinforces deterministic triage and never proposes independent diagnoses or treatment changes.
- [ ] **7. Emergency Invariant Confirmed:** Verify that emergency check-ins always receive `explanation = null`.
