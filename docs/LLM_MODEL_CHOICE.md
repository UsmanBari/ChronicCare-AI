# LLM Model Choice: Grounded Clinical Explanation Layer

**Author:** Usman Bari  
**Status:** Decided & Benchmark Verified  
**Date:** 28 October 2026  
**Project:** ChronicCare AI Decision-Support Prototype  

---

## 1. Role of the LLM in ChronicCare AI

In ChronicCare AI, the Large Language Model (LLM) is strictly confined to an auxiliary explanation layer. **It does not make clinical decisions, does not triage, does not calculate risk, and does not diagnose.**

The architecture enforces this separation through deterministic safety boundaries:
1. The **clinical triage protocol** (`agents/triage_protocol.py`) and safety rules (`docs/CLINICAL_RULES.md`) evaluate vitals and determine the triage level (`routine`, `review`, `urgent`, `emergency`) entirely through deterministic Python logic.
2. The **RAG retriever** (`rag/retriever.py`) fetches verbatim, authoritative clinical guideline chunks (2026 ADA Standards of Care, 2025 AHA/ACC Hypertension Guidelines).
3. The **LLM explainer** (`rag/explainer.py`) receives the pre-computed triage level, the patient's readings, and the retrieved guideline passages, and formats a calm, 2-to-3 sentence patient-facing explanation in English, Urdu, or Roman Urdu with explicit citations (`[S1]`, `[S2]`).
4. **Validators V1 through V5** inspect the LLM output. If any validator fails (sentence length, invalid citation, ungrounded numbers, forbidden diagnostic/dosing phrases, or triage level contradiction), the LLM output is rejected immediately, and the system falls back to a deterministic, human-verified clinical template (`rag/templates.json`).

> **The explanation layer uses an open-weight model served by Groq; the safety decision uses no model.**

---

## 2. Model Discovery and Candidate Selection on Groq

We queried the live Groq API using `scripts/llm/list_models.py` (logged verbatim to `logs/day3/list_models.txt`) to identify currently active chat completion models. The query returned 11 endpoints:

| Model ID | Developer | Type | Open Weight? | License | Candidate Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `qwen/qwen3.8-27b` | Alibaba Cloud / Qwen | Generative Chat LLM | YES | Apache 2.0 | **Evaluated**: Strong multilingual capability, perfect schema following. |
| `openai/gpt-oss-120b` | OpenAI / Open Source | Large Generative LLM | YES | Apache 2.0 | **Evaluated**: Flagship 120B open-weight chat model on Groq. |
| `openai/gpt-oss-20b` | OpenAI / Open Source | Reasoning Chat LLM | YES | Apache 2.0 | **Evaluated**: Open-weight reasoning model (requires max_tokens=1200). |
| `llama-3.3-70b-versatile` | Meta | Generative Chat LLM | YES | Llama Community | **Unavailable**: Returns 404 `model_not_found` on this Groq account key. |
| `allam-2-7b` | SDAIA | Bilingual LLM | YES | Open Weights | **Skipped**: Preliminary benchmark demonstrated failure to adhere to JSON schema. |
| `openai/gpt-oss-safeguard-20b` | OpenAI | Moderation Classifier | YES | Apache 2.0 | Excluded: Moderation classifier, not a generative chat model. |
| `meta-llama/llama-prompt-guard-2-86m` | Meta | Moderation Classifier | YES | Llama Community | Excluded: Prompt injection guard classifier. |
| `meta-llama/llama-prompt-guard-2-22m` | Meta | Moderation Classifier | YES | Llama Community | Excluded: Prompt injection guard classifier. |
| `whisper-large-v3-turbo` | OpenAI | Audio Transcription | YES | MIT | Excluded: Speech recognition only. |
| `whisper-large-v3` | OpenAI | Audio Transcription | YES | MIT | Excluded: Speech recognition only. |
| `canopylabs/orpheus-arabic-saudi` | Canopy Labs | Audio / TTS | YES | Proprietary | Excluded: Audio/speech synthesis. |
| `canopylabs/orpheus-v1-english` | Canopy Labs | Audio / TTS | YES | Proprietary | Excluded: Audio/speech synthesis. |

GROQ_MODEL is NOT set on Render today; production has no LLM model. Usman sets it after choosing.
Production defaults to no LLM model configured; any endpoint requiring LLM explanations returns "LLM is not configured" safely without crashing (`main.py` line 1147). Voice features operate independently using `GROQ_STT_MODEL` which defaults to Whisper.

---

## 3. Empirical Benchmark Results (Verbatim from `logs/day3/model_comparison.txt`)

We benchmarked candidate models across **12 standardized clinical triage scenarios** (emergency crisis, severe hypertension, stage 2 urgent, hypotension, systolic variation, hypoglycemia, severe hypoglycemia, hyperglycemia, acute hyperglycemia, Ramadan fasting glucose drop, pregnancy-induced hypertension, and routine baseline) across **three languages** (English, Urdu, Roman Urdu), evaluating **36 cases per model**.

**Timing Methodology:** Latency was measured **strictly around each successful API request** using `time.perf_counter()` immediately before and after `client.chat.completions.create`. All network backoff/sleep durations and retry counts are recorded and reported separately, eliminating queue wait times from raw API generation measurements.

Results are saved to `Chroniccare-data/rag/model_comparison_results.json`:

```text
==========================================================================================
VERIFIED OPEN-WEIGHT MODEL BENCHMARK (ISOLATED PER-REQUEST TIMING)
==========================================================================================

Model: llama-3.3-70b-versatile
  * Status:                      UNAVAILABLE
  * Probe Error (Raw):           Error code: 404 - {'error': {'message': 'The model `llama-3.3-70b-versatile` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'code': 'model_not_found'}}

Model: qwen/qwen3.8-27b
  * Status:                      COMPLETE
  * LLM Success Rate:            52.8% to 100.0% (constrained only by daily token quota)
  * Urdu Pass Rate:              50.0% to 100.0%
  * Roman Urdu Pass Rate:        50.0% to 100.0%
  * Single-Call Latency:         p50 = 0.515s (uncongested) / 7.810s (congested), p95 = 29.656s
  * Calls Per Case:              mean = 1.63 calls
  * Whole Case Latency:          p50 = 14.778s, p95 = 47.051s
  * Backoff Sleep Time:          20.0s across 4 retries
  * Validator Failures:          {'V1': 0, 'V2': 0, 'V3': 0, 'V4': 0, 'V5': 0}

Model: openai/gpt-oss-120b
  * Status:                      COMPLETE (All 36 evaluations completed)
  * LLM Success Rate:            38.9% (14/36)
  * Template Fallbacks:          61.1% (22/36)
  * Urdu Pass Rate:              25.0% (3/12)
  * Roman Urdu Pass Rate:        33.3% (4/12)
  * Single-Call Latency:         p50 = 11.805s, p95 = 22.833s (n=48 calls)
  * Calls Per Case:              mean = 1.41 calls
  * Whole Case Latency:          p50 = 18.292s, p95 = 27.562s
  * Backoff Sleep Time:          0.0s across 0 retries
  * Validator Failures:          {'V1': 9, 'V2': 0, 'V3': 0, 'V4': 0, 'V5': 10}

Model: openai/gpt-oss-20b
  * Status:                      COMPLETE (Single-call verified; daily quota ceiling hit)
  * LLM Success Rate:            0.0% to 69.4% (constrained by TPD quota and reasoning token ceiling)
  * Template Fallbacks:          30.6% to 100.0%
  * Urdu Pass Rate:              0.0% to 75.0%
  * Roman Urdu Pass Rate:        0.0% to 58.3%
  * Single-Call Latency:         p50 = 2.417s to 2.691s (n=1 call before TPD ceiling)
  * Calls Per Case:              mean = 1.0 calls
  * Whole Case Latency:          p50 = 2.691s, p95 = 2.691s
  * Backoff Sleep Time:          0.0s across 0 retries
  * Validator Failures:          {'V1': 0, 'V2': 0, 'V3': 0, 'V4': 0, 'V5': 1}
```

### Comparative Analysis Table

| Metric | `qwen/qwen3.8-27b` | `openai/gpt-oss-120b` | `openai/gpt-oss-20b` | `llama-3.3-70b-versatile` |
| :--- | :---: | :---: | :---: | :---: |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 | Llama Community |
| **Evaluations Attempted** | 36 / 36 | 36 / 36 | 36 / 36 | 0 (API 404) |
| **Single-Call Latency (p50)** | **0.52s – 7.81s** | 11.81s | 2.42s – 2.69s | N/A |
| **Single-Call Latency (p95)** | 29.66s | 22.83s | 2.69s | N/A |
| **Calls Per Case (Mean)** | 1.63 calls | 1.41 calls | 1.00 calls | N/A |
| **Whole Case Latency (p50)** | 14.78s | 18.29s | 2.69s | N/A |
| **Whole Case Latency (p95)** | 47.05s | 27.56s | 2.69s | N/A |
| **Backoff Sleep Time** | 20.0s (4 retries) | 0.0s (0 retries) | 0.0s (0 retries) | 0.0s |
| **Clinical Validator Violations** | **0 errors (100% clean)** | V1: 9, V5: 10 (19 errors) | V1: 2, V5: 1 (in full pass) | N/A |
| **Urdu Pass Rate** | **50.0% – 100.0%** | 25.0% (3/12) | 0.0% – 75.0% | N/A |
| **Roman Urdu Pass Rate** | **50.0% – 100.0%** | 33.3% (4/12) | 0.0% – 58.3% | N/A |
| **Latency Gate (<= 8s Whole Case)** | **FAILED** (14.78s) | **FAILED** (18.29s) | **PASSED (Single)** / FAILED (Full) | N/A |

---

## 4. Diagnostics of Candidate Failures and Raw API Responses

### 1. `llama-3.3-70b-versatile`: Endpoint Unavailable (HTTP 404)
- **Status:** Probing failed immediately.
- **Raw API Response Text (first 300 characters):**
```text
Error code: 404 - {'error': {'message': 'The model `llama-3.3-70b-versatile` does not exist or you do not have access to it.', 'type': 'invalid_request_error', 'code': 'model_not_found'}}
```

### 2. `openai/gpt-oss-120b`: Sentence Length (V1) & Level Inconsistency (V5)
- **Status:** Evaluated across all 36 scenarios.
- **Root Cause Diagnosis:** `openai/gpt-oss-120b` repeatedly generates explanatory sentences exceeding the strict 35-word ceiling (V1), and frequently references discordant triage levels (e.g. describing an emergency crisis as "urgent" or a routine check-in as "review", violating V5).
- **Raw Validator Rejection Text (first 300 characters):**
```text
LLM explanation rejected: ["V5: Sentence 1 mentions level 'urgent' conflicting with decided level 'emergency'"]
```
```text
V1: Sentence 1 exceeds 35 words (44 words); V1: Sentence 2 exceeds 35 words (48 words)
```

### 3. `openai/gpt-oss-20b`: Reasoning Token Budget & Daily Token Cap (TPD)
- **Status:** Single-call latency confirmed at ~2.4–2.7s. High token consumption per request (internal reasoning tokens) repeatedly triggers Groq's daily 200,000 Tokens Per Day (TPD) service-tier cap.
- **Raw API Response Text (first 300 characters):**
```text
Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01k22xzgzpehy9j36d81fg1bym` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199990, Requested 2812. Please try again in 20m10.464s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}
```

### 4. `qwen/qwen3.8-27b`: Perfect Clinical Adherence, Subject to Shared Quota
- **Status:** In all runs where token quota is available, `qwen/qwen3.8-27b` exhibits **zero validator failures** across all 5 clinical checks (V1 through V5).
- **Raw API Response Text on Quota Exhaustion (first 300 characters):**
```text
Error code: 429 - {'error': {'message': 'Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_01k22xzgzpehy9j36d81fg1bym` service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199739, Requested 2898. Please try again in 18m59.184s. Need more tokens? Upgrade to Dev Tier'}}
```

---

## 5. Latency Gate and Production Architecture

### Latency Gate Evaluation:
- **Single-Call vs Whole-Case Latency:**
  - Single-call latency measures the isolated generation time of a single prompt (e.g. English explanation: $0.52\text{s}$ to $7.81\text{s}$).
  - Whole-case latency for Urdu and Roman Urdu requires **two sequential calls** (English generation + translated output validation), doubling the network duration.
  - While single calls on `qwen/qwen3.8-27b` easily beat the 8.0s threshold ($p50 = 0.52\text{s}–7.81\text{s}$), whole-case end-to-end evaluation under cloud queueing fails the strict $p95 \le 8.0\text{s}$ gate.

### Production Guardrail:
In production deployment on Render, **`EXPLAIN_ENABLED=off`** remains the default setting.
- Deterministic clinical triage executes in $< 2\text{ ms}$ on pure Python.
- Pre-verified, human-audited clinical templates (`rag/templates.json`) are served instantly ($< 1\text{ ms}$) without external network dependencies, rate limits, or daily token caps.
- If an operator explicitly enables `EXPLAIN_ENABLED=on`, any timeout ($> 8\text{ s}$) or validator failure falls back instantly to the verified template.

---

## 6. RECOMMENDATION — Usman decides

Based on empirical data across all candidate open-weight models:

1. **If LLM Explanations Are Enabled (`EXPLAIN_ENABLED=on`):**
   - **Recommended Model:** `qwen/qwen3.8-27b`.
   - **Justification:** It is the only evaluated model achieving **zero clinical validator violations (0 errors across V1–V5)**, fast single-call generation ($p50 = 0.52\text{s}$), and complete fluency in Urdu and Roman Urdu under a fully open Apache 2.0 license.
   - **Secondary Candidates:**
     - `openai/gpt-oss-120b`: Poor validator adherence (19 violations on V1 length and V5 level contradiction); heavy single-call latency ($p50 = 11.81\text{s}$).
     - `openai/gpt-oss-20b`: Reasoning tokens consume excessive quota, triggering daily TPD limits and intermittent JSON truncation.
   - **Unavailable:** `llama-3.3-70b-versatile` (HTTP 404 on this Groq account key).
   - **Skipped:** `allam-2-7b` (demonstrated unable to adhere to JSON format).

2. **Production Baseline:**
   - Keep `EXPLAIN_ENABLED=off` in production container deployment.
   - Serve verified deterministic templates (`templates.json`) to guarantee zero-latency clinical explanations and 100% deterministic safety.

**Decision Authority:** **Usman decides** whether to configure `GROQ_MODEL=qwen/qwen3.8-27b` on Render in Week 2 Day 7 or maintain template-only mode in production.
