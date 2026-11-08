# Explainer Safety Guards Architecture & Operations Guide

**Audience:** Backend Engineers, System Operators, Clinicians, and QA.  
**Feature Flag:** `EXPLAIN_ENABLED` (Default: `false` / OFF).  
**Status:** Active in v1.0.  

---

## 1. Architectural Overview & Motto

> **Motto:** *"The model proposes, the rules decide."*

In ChronicCare AI, clinical decisions (such as triage levels `routine`, `review`, `urgent`, `emergency`) are strictly determined by deterministic clinical rule engines. LLMs **never** determine triage levels, and an explanation **never** alters or overrides a triage decision.

When `EXPLAIN_ENABLED=true`, the Guideline Explainer provides patients with concise, plain-language clinical context derived from verified clinical guidelines (e.g. ADA, ACC/AHA). To ensure patient safety, uptime, and strict cost controls, the explainer is wrapped by hermetic safety guards with dual LLM provider support (Groq and Google Gemini):

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
    WorkerPool -- Slot Acquired --> LLMDispatch[Spawn Thread & Call LLM Provider]
    LLMDispatch --> HardWait{Hard Join Within Budget?}
    HardWait -- Timed Out --> FallbackTimeout[Return mode='template', reason='budget_timeout']
    HardWait -- Finished --> Validators{Validators V1-V5 Pass?}
    Validators -- Failed --> FallbackVal[Return mode='template', reason='validation_failed']
    Validators -- Passed --> CachePut[Populate LRU Cache] --> RetLLM[Return mode='llm']
```

### 1.1 Background Explainer Architecture & Groq OTPM Pacer (Day 5)

Under Usman's Day 5 directive—*"Best answer, not fastest answer"*—the explainer runs asynchronously by default (`EXPLAIN_MODE=background`):

```mermaid
sequenceDiagram
    autonumber
    actor Patient
    participant API as FastAPI /complete
    participant Store as SQLite DB
    participant Queue as Job Queue (max 50)
    participant Worker as Background Worker
    participant Guards as guarded_explain (bg)
    participant Pacer as TokenPacer (60s)
    participant LLM as Groq / Gemini

    Patient->>API: POST /api/checkins/{id}/complete
    API->>Store: Persist checkin_result (triage decided)
    API->>Queue: Enqueue ExplanationJob
    API-->>Patient: 200 OK (triage decided, explanation: status="pending")
    Patient->>API: GET /api/checkins/{id}/explanation (poll every 3s)
    API-->>Patient: status="pending"

    Queue->>Worker: Dequeue job
    Worker->>Guards: guarded_explain(mode="background", deadline=45s)
    Guards->>Pacer: acquire() (Groq OTPM check)
    Pacer-->>Guards: wait_sec (if rolling 60s usage > 1000 OTPM)
    Guards->>LLM: Call Groq / Gemini
    LLM-->>Guards: Validated sentences + usage
    Guards-->>Worker: Explanation result
    Worker->>Store: update_checkin_explanation(status="ready")
    Patient->>API: GET /api/checkins/{id}/explanation
    API-->>Patient: 200 OK (status="ready", sentences, sources)
```

1. **Immediate Check-in Return:** `POST /api/checkins/{id}/complete` returns immediately with the decided triage level and `explanation: {"status": "pending"}`. Extra `/complete` latency is under 10 ms.
2. **Bounded Job Queue (`EXPLAIN_QUEUE_MAX`):** Capacity 50 (`EXPLAIN_QUEUE_MAX=50`). If the queue overflows, the check-in immediately stores the pre-computed template fallback with `reason="queue_full"`.
3. **Lazy Worker Thread:** The background daemon worker thread starts lazily upon arrival of the first job.
4. **Groq Rolling 60s OTPM Pacer (`TokenPacer`):** Groq allows 1,000 output tokens per minute on its free tier. `TokenPacer` maintains a sliding 60-second window of recorded completion tokens. Before each LLM call, the pacer checks rolling completion tokens against `EXPLAIN_GROQ_OTPM` (1,000). It reserves the exact tokens needed for the specific call: `EXPLAIN_MAX_TOKENS` (default 250) for English generation, and `EXPLAIN_TRANSLATION_MAX_TOKENS` (default 700) for Urdu / Roman Urdu translation (which requires more tokens due to non-Latin script tokenization in JSON). If generating the needed completion tokens would exceed 1,000 OTPM, the worker thread sleeps for the exact seconds required for older tokens to roll out of the window.
   - **Waiting Against Job Deadline (Rule A2, Day 6g):** In background mode, Groq pacer waits are evaluated against the overall job deadline (`EXPLAIN_JOB_DEADLINE_SECONDS`, default 45 s), not against the 20 s per-call provider timeout (`EXPLAIN_CALL_TIMEOUT_SECONDS`). When the wait fits within the job deadline (`now + wait + 1.0 <= deadline`), the worker thread sleeps and extends the provider's join deadline accordingly (`prov_deadline_ref[0] = min(deadline, prov_deadline_ref[0] + wait)`), while capping the subsequent HTTP call timeout to `min(call_timeout, rem_budget)`. If the wait exceeds the job deadline, Groq raises `TimeoutError('Pacer wait exceeds deadline')` and falls back to Gemini. Inline mode bypasses pacer sleeping entirely.
5. **Non-Tripping 429 Retries in Background:** In background mode, an HTTP 429 does **not** trip the circuit breaker. It parses the upstream `retry-after` header and sleeps (default 5.0s, capped at 30.0s), retrying once before failing over to Gemini.
6. **Stale Job Protection:** If an explanation remains in `status="pending"` for longer than `EXPLAIN_JOB_DEADLINE_SECONDS + 30.0s` (75.0 s), `app_store.get_checkin_explanation` automatically replaces it with the stored fallback template with `reason="job_lost"`.

---

## 2. Safety Guards Specification

### Guard 1: Hard Time Budget (`EXPLAIN_BUDGET_SECONDS`)
- **Default:** `3.0` s. Bounds: `1.0` s – `10.0` s.
- **Behavior:** The entire explainer pipeline (retrieval, prompt construction, LLM generation, JSON parsing, and safety validation) must complete within the wall-clock budget.
- **Timeout Isolation:** The worker thread executes as a daemon. If `join()` reaches the deadline, the main request thread aborts waiting immediately and returns the pre-verified deterministic template with `mode='template'`, `reason='budget_timeout'`. The patient **never waits longer than budget + 1 s**.
- **Late Thread Accounting:** If a worker thread times out but finishes upstream execution in the background, its token usage is safely credited to the daily token counter under a lock with `recorded` / `consumed_by_caller` flag, while its generated text is permanently discarded.
- **Concurrency Isolation:** A hung LLM thread does not block subsequent check-ins because each check-in uses independent thread isolation bounded by a concurrency semaphore.
- **No Background Retries:** Calls into `chat_with_usage` strictly pass `max_retries=0` and `sdk_max_retries=0` alongside `timeout <= budget` so a timed-out call never retries in the background.

### Guard 2: Daily Token Cap (`EXPLAIN_DAILY_TOKEN_CAP`, `EXPLAIN_DAILY_TOKEN_CAP_GEMINI`)
- **Default:** `150,000` tokens per UTC day (~$0.07–$0.15/day on Groq `llama-3.3-70b-versatile`). Bounds: `10,000` – `1,000,000`.
- **Separate Per-Provider Caps:** Groq and Gemini track cumulative prompt and completion tokens separately. When `used_tokens + 1,000 > cap` for a provider, that provider is skipped.
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
- **Per-Provider Breakers:** Groq and Gemini maintain independent circuit breaker instances (`_GLOBAL_BREAKER_GROQ` and `_GLOBAL_BREAKER_GEMINI`).

### Guard 5: BM25 Retriever Reuse & Thread-Safe Caching (A5)
- **Behavior:** The Okapi BM25 retriever index is built once and cached in memory. Subsequent check-ins reuse the pre-indexed structure in $\mathcal{O}(1)$ time rather than re-indexing guideline text on every check-in. If the underlying chunk store changes (detected by store instance ID or total chunk count), the cache invalidates and rebuilds automatically.

### Guard 6: Dual LLM Providers & Failover Routing (`LLM_PROVIDER`, `LLM_PROVIDER_ORDER`)
- **Dual Providers:** ChronicCare AI supports two production-grade LLM providers for the explainer: **Groq** (configured via `GROQ_MODEL`, e.g. `qwen/qwen3.8-27b`) and **Google Gemini** (configured via `GEMINI_MODEL`, e.g. `gemini-2.5-flash`).
- **Failover Routing:** When `LLM_PROVIDER=auto` (default), the system attempts providers in the sequence defined by `LLM_PROVIDER_ORDER` (default `groq,gemini`). If the primary provider encounters an HTTP 429 rate limit, network timeout, or connection error, the system immediately fails over to the next candidate provider.
- **Budget Splitting:** When a fallback provider is available in auto mode, the primary provider is allocated 60% of the remaining `EXPLAIN_BUDGET_SECONDS` (at least 1.0 s), reserving the remaining 40% (at least 1.0 s) for the fallback candidate. If a single provider is configured or no fallback remains, the active provider receives 100% of the remaining budget.
- **Independent Breakers & Caps:** Groq and Gemini maintain completely independent daily token counters (`EXPLAIN_DAILY_TOKEN_CAP` and `EXPLAIN_DAILY_TOKEN_CAP_GEMINI`, both default 150,000 tokens) and independent circuit breaker instances (`_GLOBAL_BREAKER_GROQ` and `_GLOBAL_BREAKER_GEMINI`). Saturating or tripping one provider does not affect the other.
- **Free Tier Data Advisory:**
  > [!IMPORTANT]
  > Gemini free tier: Google may use prompts and responses to improve its products and human reviewers may read them. Fake/test data only. Real patient data requires the paid tier.

### Guard 7: Guideline Licence Restrictions (G3)
- **Zero-Leak Licence Enforcement:** Certain proprietary clinical guidelines (e.g. ADA Standards of Care, ACC/AHA) carry distribution licences that forbid transmitting text to third-party generative models that may retain prompt data. These sources are marked `allowed_for_rag == FALSE` in `docs/GUIDELINE_CORPUS.md` (`ada_2026_sec02`, `ada_2026_sec05`, `ada_2026_sec06`, `ada_2026_sec10`, `ada_2026_sec11`, `ada_2026_sec13`, `aha_acc_2025`).
- **Provider Filtering:** If ANY candidate retrieved chunk originates from a licence-restricted source, Google Gemini is strictly disallowed for that request. In `auto` mode, Gemini is quietly pruned from the candidate list (Groq is attempted); if Gemini was explicitly requested (`LLM_PROVIDER=gemini`), the system immediately falls back to verified deterministic templates with `reason='licence_restricted'`.

### Guard 8: Condition Safety Filter (H1)
- **Diabetes Template-Only:** Based on clinical review, diabetes clinical explanations are restricted to pre-verified deterministic templates (`reason='condition_template_only'`).
- **Eligible Conditions:** Only conditions configured in `EXPLAIN_LLM_CONDITIONS` (default `hypertension`) are permitted to invoke generative LLMs.
- **Dual-Condition Handling:** For patients diagnosed with both diabetes and hypertension, the LLM is invoked ONLY if the primary trigger for the check-in is an elevated blood pressure trigger (`bp_systolic_urgent`, `bp_diastolic_urgent`, `bp_both_urgent`, `bp_systolic_elevated`, `bp_diastolic_elevated`, `bp_both_elevated`, `bp_normal`). If the trigger is glucose-related or routine, deterministic templates are returned.
- **Pre-Ranking Guideline Exclusion:** Diabetes guidelines (ADA, IDF-DAR, AKU) are left out before ranking for patients without diabetes (`exclude_source_prefixes=("ada_2026", "idf_dar", "aku_diabetes")`). Diabetic and dual-condition patients retain full access to diabetes guidelines.

### Guard 8b: Language Safety Filter
- **Language Eligibility:** Only check-in languages configured in `EXPLAIN_LLM_LANGUAGES` (code default `en,ur,roman_ur`) are permitted to invoke generative LLMs.
- **Release 2 English-Only:** For Release 2 (`EXPLAIN_LLM_LANGUAGES=en`), Urdu and Roman Urdu check-ins route immediately to human-reviewed deterministic templates (`reason='language_template_only'`), bypassing LLM generation, translation, OTPM pacer waiting, and cache lookups/writes.

### Guard 9: Deterministic Template Consistency Guard (H2)
- **Reading-Template Alignment:** Whenever a deterministic template is selected, `is_template_consistent` validates that the template language does not contradict actual numerical vitals (e.g., normal BP or normal glucose paired with an urgent/high template).
- **Automatic Correction:** If an inconsistency is detected (e.g. a routine check-in paired with a high-blood-pressure template due to trigger misalignment), the system automatically substitutes a neutral routine template for that language with `reason='template_corrected'`.

---

## 3. Environment Variables Reference

| Variable | Type | Default | Valid Range | Purpose |
|---|---|---|---|---|
| `EXPLAIN_ENABLED` | bool | `false` | `true`, `false` | Master feature flag. When `false`, zero guard or LLM code runs and `explanation` is `null`. |
| `EXPLAIN_BUDGET_SECONDS` | float | `3.0` | `1.0` – `10.0` | Hard wall-clock execution budget in seconds. |
| `EXPLAIN_DAILY_TOKEN_CAP` | int | `150000` | `10000` – `1000000` | Maximum Groq total tokens allowed per UTC calendar day. |
| `EXPLAIN_DAILY_TOKEN_CAP_GEMINI` | int | `150000` | `10000` – `1000000` | Maximum Gemini total tokens allowed per UTC calendar day. |
| `EXPLAIN_CACHE_MAX` | int | `500` | `50` – `5000` | Maximum number of entries stored in the LRU explanation cache. |
| `EXPLAIN_CACHE_TTL_SECONDS` | float | `86400.0` | `60.0` – `604800.0` | Time-to-live for cached validated explanations in seconds. |
| `EXPLAIN_BREAKER_FAILURES` | int | `3` | `1` – `10` | Number of consecutive upstream errors before opening circuit breaker. |
| `EXPLAIN_BREAKER_COOLDOWN_SECONDS` | float | `600.0` | `5.0` – `3600.0` | Cooldown duration before attempting a trial call in half-open state. |
| `EXPLAIN_POOL_MAX_WORKERS` | int | `8` | `4` – `32` | Maximum concurrent background LLM worker threads. |
| `LLM_PROVIDER` | str | `auto` | `auto`, `groq`, `gemini` | Explainer LLM provider routing mode (`auto` falls back through `LLM_PROVIDER_ORDER`). |
| `LLM_PROVIDER_ORDER` | str | `groq,gemini` | comma-separated list | Provider failover order when `LLM_PROVIDER=auto`. |
| `GEMINI_MODEL` | str | `""` | string | Google Gemini model ID (e.g. `gemini-2.5-flash`). Required if using Gemini. |
| `GEMINI_THINKING_BUDGET` | str | `""` | int string (e.g. `0`) or `none` | Optional Gemini thinking budget. Defaults to `0` (disables thinking for speed) when unset; set to `none` to omit `thinkingConfig`. |
| `EXPLAIN_LLM_CONDITIONS` | str | `hypertension` | comma-separated list | Clinical conditions eligible for LLM explanations (diabetes is template-only). |
| `EXPLAIN_LLM_LANGUAGES` | str | `en,ur,roman_ur` | comma-separated list | Languages eligible for LLM explanations (`en`, `ur`, `roman_ur`). Non-eligible languages fall back to reviewed deterministic templates (`language_template_only`). |
| `EXPLAIN_MODE` | str | `background` | `background`, `inline` | Job execution mode: `background` worker or synchronous `inline`. |
| `EXPLAIN_QUEUE_MAX` | int | `50` | `1` - `500` | Bounded capacity for background explanation job queue. |
| `EXPLAIN_JOB_DEADLINE_SECONDS` | float | `45.0` | `10.0` - `120.0` | Total wall-clock deadline for background explanation job. |
| `EXPLAIN_CALL_TIMEOUT_SECONDS` | float | `20.0` | `5.0` - `60.0` | Per-provider call timeout for background explanation job. |
| `EXPLAIN_GROQ_OTPM` | int | `1000` | `100` - `10000` | Groq output tokens per minute pacer limit (60s rolling window). |
| `EXPLAIN_MODE` | str | `background` | `background`, `inline` | Job execution mode: `background` worker or synchronous `inline`. |
| `EXPLAIN_QUEUE_MAX` | int | `50` | `1` - `500` | Bounded capacity for background explanation job queue. |
| `EXPLAIN_JOB_DEADLINE_SECONDS` | float | `45.0` | `10.0` - `120.0` | Total wall-clock deadline for background explanation job. |
| `EXPLAIN_CALL_TIMEOUT_SECONDS` | float | `20.0` | `5.0` - `60.0` | Per-provider call timeout for background explanation job. |
| `EXPLAIN_GROQ_OTPM` | int | `1000` | `100` - `10000` | Groq output tokens per minute pacer limit (60s rolling window). |
| `EXPLAIN_MAX_TOKENS` | int | `250` | `100` - `1000` | Maximum completion tokens for English LLM generation call. |
| `EXPLAIN_TRANSLATION_MAX_TOKENS` | int | `700` | `250` - `2000` | Maximum completion tokens for Urdu / Roman Urdu translation LLM call (higher token density in JSON). |

> [!NOTE]
> **Gemini Thinking Budget:** To avoid budget timeouts on reasoning models (`gemini-flash-latest`), `GEMINI_THINKING_BUDGET` defaults to `0` (`thinkingConfig.thinkingBudget = 0`) when unset or empty. Set `GEMINI_THINKING_BUDGET=none` only if calling a legacy model that rejects `thinkingConfig`.

---

## 4. In-Memory vs. Persistent State Justification

In the ChronicCare AI prototype, all guard states (token counters, circuit breaker states, LRU cache, worker semaphores) are stored **in-memory**:
1. **Zero Database Migrations:** Requires no extra tables, Redis clusters, or foreign keys in SQLite / MySQL.
2. **Hermetic Resilience:** Process restarts safely reset counters and circuit breakers. If a deployment had an unhealthy upstream connection that is resolved during a deploy, the circuit breaker resets cleanly.
3. **Low Latency:** In-memory checks complete in under 5 microseconds ($\\mu\\text{s}$), adding zero overhead to the check-in completion path.
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
| **Mode & Reason** | **Strictly absent.** (sentences + sources only). | Full explainer metadata including delivery mode and reason code. |
| **Provider Trace** | **Strictly absent.** | `provider` and `providers_tried` audit trails recorded. |

---

### 5.1 Patient Excerpt Policy & Licence Caps (Rule X5)

In ChronicCare AI, patients never see raw, unformatted chunk text:
1. **Plain Language Synthesis:** Explanations are either synthesized in patient-friendly plain language by authorized LLMs (Groq) or generated from pre-verified clinical templates.
2. **Attribution and Citation:** When guideline sources are shown to patients, only verified academic citations and external DOI links are displayed.
3. **Future Excerpt Cap:** If brief verbatim excerpts are ever introduced in a future release, the maximum number of excerpts per check-in is strictly capped by the guideline's licence specification (`max_excerpts_per_checkin` in `rag/licences.json` — strictly capped at **3 excerpts** for ADA 2026).

---

## 6. Troubleshooting & Fallback Reason Codes

Whenever `mode == "template"`, the `reason` field indicates why deterministic fallback was selected:

| Reason Code | Root Cause | Operator Action |
|---|---|---|
| `budget_timeout` | LLM latency exceeded `EXPLAIN_BUDGET_SECONDS` (3.0 s). | Check provider API status. If network latency is elevated, increase `EXPLAIN_BUDGET_SECONDS` to 5.0 s. |
| `token_cap` | Daily token usage reached provider token cap (150,000). | Normal cost-cap operation. Check token usage via `get_explain_guard_metrics()`. Reset occurs at 00:00 UTC. If traffic has grown, increase cap. |
| `breaker_open` | 3 consecutive timeouts or connection errors tripped circuit breaker. | Inspect upstream provider logs. The breaker will test a trial call after 600 seconds. |
| `rate_limited` | HTTP 429 Too Many Requests received from provider. | Rate tier saturated. Breaker opened immediately for 600 s cooldown to allow token bucket refill. |
| `validation_failed` | Generated text failed clinical validator (V1 structure, V2 citation, V3 numbers, V4 forbidden phrase, or V5 level mismatch). | Normal safety behavior. The system safely suppressed ungrounded text and delivered deterministic clinical guidance. |
| `no_llm` | API key is not configured or LLM client initialization failed. | Configure `GROQ_API_KEY` and/or `GEMINI_API_KEY` in environment. |
| `no_chunks` | Retrieval returned 0 relevant guideline chunks for this condition. | Check database seeding (`init_local_db.py`). |
| `busy` | All worker semaphore slots (`EXPLAIN_POOL_MAX_WORKERS`) are in use. | High concurrent traffic spike. Increase `EXPLAIN_POOL_MAX_WORKERS` (default 8). |
| `licence_restricted` | Retrieved guideline chunk is restricted by licence terms (G3/X3), lacks required attribution (X4), or provider is prohibited (e.g. Gemini prohibited for ADA 2026; AHA/ACC blocked). | Normal safety behavior. The system safely falls back to verified deterministic templates or alternative permitted providers. |
| `condition_template_only` | Check-in condition is not in `EXPLAIN_LLM_CONDITIONS` (e.g. diabetes). | Normal clinical safety behavior. Diabetes explanations are deterministic template-only. |
| `language_template_only` | Check-in language is not in `EXPLAIN_LLM_LANGUAGES` (e.g. `ur` or `roman_ur`). | Normal clinical safety behavior. Urdu and Roman Urdu explanations use reviewed deterministic templates for Release 2. |
| `template_corrected` | Deterministic template contradicted actual vitals and was replaced with neutral routine template. | Normal safety invariant enforcement. Check trigger mapping logic. |
| `error` | Upstream JSON deserialization or network socket exception. | Inspect backend application error logs. |

---

## 7. Go-Live Checklist (When Flipping `EXPLAIN_ENABLED=true` in Production)

Before enabling the patient-facing explainer in production:

- [ ] **1. Guideline Chunks Loaded:** Verified that clinical guideline chunks are loaded and seeded in production database (`init_local_db.py` / migrations).
- [ ] **2. Explainer Evaluation Reviewed:** Saad's explainer clinical evaluation has been reviewed and signed off by the clinical team.
- [ ] **3. Live Smoke Output Verified:** Usman's live smoke output for `groq` AND `gemini` pasted and verified (`python scripts/explain_live_smoke.py --provider auto`).
- [ ] **4. Production Environment Variables Provisioned (Render):**
  - `EXPLAIN_ENABLED=true`
  - `LLM_PROVIDER=auto`
  - `GROQ_API_KEY` (configured in Render secret environment)
  - `GROQ_MODEL` (configured in Render environment)
  - `GEMINI_API_KEY` (configured in Render secret environment)
  - `GEMINI_MODEL` (configured in Render environment)
  - `EXPLAIN_LLM_CONDITIONS=hypertension`
- [ ] **5. Token Caps and Budget Verified:**
  - `EXPLAIN_BUDGET_SECONDS` is set to `3.0` (p95 latency under 3.5 s verified via `measure_explain_latency.py`).
  - `EXPLAIN_DAILY_TOKEN_CAP` set (default 150,000 tokens).
  - `EXPLAIN_DAILY_TOKEN_CAP_GEMINI` set (default 150,000 tokens).
- [ ] **6. Gemini Free Tier Advisory Confirmed:** Confirmed team awareness:
  *"Gemini free tier: Google may use prompts and responses to improve its products and human reviewers may read them. Fake/test data only. Real patient data requires the paid tier."*
- [ ] **7. Cache & Breaker Monitoring:** Verify observability checks on `/api/health` or metrics output alert when any `breaker_state != "closed"`.
- [ ] **8. Emergency Invariant Confirmed:** Verify that emergency check-ins always receive `explanation = null`.\n