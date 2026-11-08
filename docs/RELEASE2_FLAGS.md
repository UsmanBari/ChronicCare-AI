# Release 2 Runtime Feature Flags & Configuration

This document specifies the exact configuration of environment variables and feature flags for **Release 2** (Week 3). Every code default is derived directly from application code (`backend-poc-technical/main.py`, `rag/`, `llm/`, `orchestrator/`, `agents/`).

---

## 1. Release 2 Flag Specification Table

| Environment Variable | Code Default | Release 2 Value | Justification / Source Reference | Rollback Value |
|---|---|---|---|---|
| `INTERVIEW_ENGINE` | `v2` | `v2` | Deterministic interview engine remains active; v3 is NO-GO ([docs/V3_DECISION.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/V3_DECISION.md)) | `v2` |
| `ORCHESTRATOR` | `direct` | `direct` | In-process execution mode; proven byte-equivalent to LangGraph ([scripts/orchestrator_equivalence.py](file:///c:/Users/usmanbari/Desktop/Chronicare/scripts/orchestrator_equivalence.py)) | `direct` |
| `OCR_ENABLED` | `false` | `false` | Stays OFF in production due to RapidOCR Linux memory footprint (>512 MB) ([docs/OCR_DESIGN.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/OCR_DESIGN.md) 6.3) | `false` |
| `RISK_ENABLED` | `false` | `true` | Enables provider risk panel advisory calculation (PR #108, PR #114) | `false` |
| `RISK_CAN_RAISE` | `false` | `false` | Strictly advisory for provider; cannot raise patient triage level ([docs/CLINICAL_RULES.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/CLINICAL_RULES.md)) | `false` |
| `DANGER_WORDGROUPS_ENABLED` | `false` | `true` | Enables red-flag danger word group screen caught in blind set 3 (20/25 caught) (PR #103, PR #130) | `false` |
| `EXPLAIN_MODE` | `background` | `background` | Bounded-queue asynchronous background explainer with worker thread (PR #114) | `background` |
| `LLM_PROVIDER` | `auto` | `groq` | Groq only (Gemini had 3 requests in testing on 8 Nov, all HTTP 503, 0 successful responses; templates are the fallback) (PR #110) | `groq` |
| `EXPLAIN_LLM_CONDITIONS` | `hypertension` | `hypertension,diabetes` | Allows LLM explanations for both hypertension and diabetes check-ins (PR #110, PR #125) | `hypertension` |
| `EXPLAIN_LLM_LANGUAGES` | `en,ur,roman_ur` | `en` | Restricts LLM generation to English; Urdu/Roman Urdu get safe reviewed templates (PR #131) | `en` *(never code default: Urdu/Roman Urdu failed human read)* |
| `EXPLAIN_ENABLED` | `false` | `false` (initially) &rarr; `true` (after D5 passes) | Master explainer switch. Set `false` during deploy; enabled only after live smoke D5 passes | `false` |
| `GROQ_API_KEY` | *(unset / None)* | `SET` *(secret)* | Production Groq API credentials for primary explainer provider | *(unset)* |
| `GROQ_MODEL` | *(none / None)* | `qwen/qwen3.8-27b` | MUST be set; `llama-3.3-70b-versatile` returned model_not_found on this account; `qwen/qwen3.8-27b` validated in 8 Nov smokes | *(unset)* |
| `GEMINI_API_KEY` | *(unset / None)* | `NOT SET` | Unset in production (Gemini free tier returned HTTP 503 in testing) | *(unset)* |
| `GEMINI_MODEL` | *(none / None)* | `NOT SET` | Unset in production | *(unset)* |
| `GEMINI_THINKING_BUDGET` | *(unset)* | *(leave unset)* (`0`) | Disables thinking overhead for Gemini 2.5 Flash | *(unset)* |
| `EXPLAIN_BUDGET_SECONDS` | `3.0` (inline) / `45.0` (bg) | *(leave unset)* (`45.0`) | Overall explanation budget cap (PR #107, PR #114) | Code default |
| `EXPLAIN_CALL_TIMEOUT_SECONDS` | `20.0` | *(leave unset)* (`20.0`) | Provider timeout before Groq pacer check / Gemini fallback (PR #126) | Code default |
| `EXPLAIN_DAILY_TOKEN_CAP` | `150000` | *(leave unset)* (`150000`) | Daily Groq token circuit breaker cap (PR #107) | Code default |
| `EXPLAIN_DAILY_TOKEN_CAP_GEMINI` | `150000` | *(leave unset)* (`150000`) | Daily Gemini token circuit breaker cap (PR #110) | Code default |
| `EXPLAIN_CACHE_MAX` | `500` | *(leave unset)* (`500`) | In-memory LRU explanation cache capacity (PR #107) | Code default |
| `EXPLAIN_CACHE_TTL_SECONDS` | `86400.0` | *(leave unset)* (`86400.0`) | 24-hour cache entry time-to-live (PR #107) | Code default |
| `EXPLAIN_BREAKER_FAILURES` | `3` | *(leave unset)* (`3`) | Consecutive provider failures before circuit breaker trip (PR #107) | Code default |
| `EXPLAIN_BREAKER_COOLDOWN_SECONDS`| `600.0` | *(leave unset)* (`600.0`) | 10-minute circuit breaker recovery cooldown (PR #107) | Code default |
| `EXPLAIN_POOL_MAX_WORKERS` | `8` | *(leave unset)* (`8`) | Explainer thread pool worker count (PR #107) | Code default |
| `EXPLAIN_QUEUE_MAX` | `50` | *(leave unset)* (`50`) | Max queue capacity for background explainer jobs (PR #114) | Code default |
| `EXPLAIN_JOB_DEADLINE_SECONDS` | `45.0` | *(leave unset)* (`45.0`) | Background worker job execution deadline (PR #114) | Code default |
| `EXPLAIN_GROQ_OTPM` | `1000` | *(leave unset)* (`1000`) | Groq free-tier tokens-per-minute pacer rate limit (PR #114) | Code default |
| `EXPLAIN_MAX_TOKENS` | `250` | *(leave unset)* (`250`) | Token limit for English clinical explanation generation (PR #107, PR #112) | Code default |
| `EXPLAIN_TRANSLATION_MAX_TOKENS` | `700` | *(leave unset)* (`700`) | Token reservation for translation (PR #123) | Code default |
| `LLM_PROVIDER_ORDER` | `groq,gemini` | *(leave unset)* (`groq,gemini`) | Multi-provider failover sequence (PR #110) | Code default |
| `SCREENING_REMINDER_INTERVAL_DAYS` | *(unset / dormant)* | *(leave unset)* | Feature remains dormant when unset (returns None in `agents/screening_reminder.py`). Admin status view defaults to `"90"` display | *(leave unset)* |

---

## 2. Rollback Triggers & Procedures

1. **Explanation Fault / Hallucination / Provider Downtime**:
   - Primary rollback: Set `EXPLAIN_ENABLED=false` in Render dashboard.
   - All check-ins immediately route to deterministic, clinician-reviewed templates. Zero clinical risk.
   - Note: If `EXPLAIN_LLM_LANGUAGES` is ever adjusted, its rollback value is strictly `en` (never the code default, since Urdu/Roman Urdu LLM output failed human clinical review).
2. **Major Regression / Core Triage Anomaly**:
   - Revert release merge commit on `main`.
   - Redeploy Release 1 state.
   - Schema remains at v15 (no migration in this release; v15 is identical on Release 1 and Release 2).
   - Guideline chunks table rows remain dormant (`EXPLAIN_ENABLED=false`) or can be cleared with:
     ```bash
     python scripts/rag/delete_source.py --licence ada_2026 --yes
     ```
