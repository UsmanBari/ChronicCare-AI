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
| `qwen/qwen3.8-27b` | Alibaba Cloud / Qwen | Generative Chat LLM | YES | Apache 2.0 | **Evaluated**: Strong instruction-following and multilingual translation. |
| `openai/gpt-oss-20b` | OpenAI / Community | Generative Chat LLM (Reasoning) | YES | Apache 2.0 | **Evaluated**: Open-weight reasoning model hosted on Groq. |
| `allam-2-7b` | SDAIA | Bilingual LLM | YES | CHECK (Permissive) | **Evaluated**: Regional Arabic/English foundation model. |
| `llama-3.1-8b-instant` | Meta | Generative Chat LLM | YES | Llama 3.1 Community | **Unavailable**: Returns 404 `model_not_found` on this Groq account key. |
| `openai/gpt-oss-120b` | OpenAI / Community | Large Generative LLM | YES | Apache 2.0 | Excluded: Exceeds rate limits and token quotas on free tier. |
| `openai/gpt-oss-safeguard-20b` | OpenAI | Moderation Classifier | YES | Apache 2.0 | Excluded: Moderation classifier, not a generative chat model. |
| `meta-llama/llama-prompt-guard-2-86m` | Meta | Moderation Classifier | YES | Llama Community | Excluded: Prompt injection / jailbreak guard classifier. |
| `meta-llama/llama-prompt-guard-2-22m` | Meta | Moderation Classifier | YES | Llama Community | Excluded: Prompt injection guard classifier. |
| `whisper-large-v3-turbo` | OpenAI | Audio Transcription | YES | MIT | Excluded: Speech recognition only. |
| `whisper-large-v3` | OpenAI | Audio Transcription | YES | MIT | Excluded: Speech recognition only. |
| `canopylabs/orpheus-arabic-saudi` | Canopy Labs | Audio / TTS | YES | CHECK | Excluded: Audio/speech synthesis. |
| `canopylabs/orpheus-v1-english` | Canopy Labs | Audio / TTS | YES | CHECK | Excluded: Audio/speech synthesis. |

**Default Model in `groq_client.py`:** `None` (dynamically configured via `GROQ_MODEL` environment variable, preserving modularity and avoiding hardcoded vendor lock-in).

---

## 3. Empirical Benchmark Results (Verbatim from `logs/day3/model_comparison.txt`)

We benchmarked candidate models across **12 standardized clinical triage scenarios** (emergency crisis, severe hypertension, stage 2 urgent, hypotension, systolic variation, hypoglycemia, severe hypoglycemia, hyperglycemia, acute hyperglycemia, Ramadan fasting glucose drop, pregnancy-induced hypertension, and routine baseline) across **three languages** (English, Urdu, Roman Urdu), executing **36 full evaluations per model** with internal rate-limit backoff.

Results are saved to `Chroniccare-data/rag/model_comparison_results.json`:

```text
================================================================================
FAIR OPEN-WEIGHT MODEL COMPARISON SUMMARY REPORT
================================================================================

Model: llama-3.1-8b-instant
  • Status:                   UNAVAILABLE
  • Note/Error:               404 model_not_found / not entitled on this Groq API key

Model: qwen/qwen3.8-27b
  • Status:                   COMPLETE
  • LLM Success Rate:         100.0% (36/36)
  • Template Fallbacks:       0.0% (0/36)
  • Urdu Pass Rate:           100.0% (12/12)
  • Roman Urdu Pass Rate:     100.0% (12/12)
  • Latency:                  p50 = 18.85s, p95 = 32.72s (Gate <= 8s: False)
  • Validator Failures:       {'V1': 0, 'V2': 0, 'V3': 0, 'V4': 0, 'V5': 0}

Model: openai/gpt-oss-20b
  • Status:                   COMPLETE
  • LLM Success Rate:         69.4% (25/36)
  • Template Fallbacks:       30.6% (11/36)
  • Urdu Pass Rate:           75.0% (9/12)
  • Roman Urdu Pass Rate:     58.3% (7/12)
  • Latency:                  p50 = 19.57s, p95 = 30.08s (Gate <= 8s: False)
  • Validator Failures:       {'V1': 2, 'V2': 0, 'V3': 0, 'V4': 0, 'V5': 1}
  • Diagnosis & Fix Applied:  Reasoning tokens exhausted 400 token limit. Resolved by increasing max_tokens to 1200.

Model: allam-2-7b
  • Status:                   COMPLETE
  • LLM Success Rate:         0.0% (0/36)
  • Template Fallbacks:       100.0% (36/36)
  • Urdu Pass Rate:           0.0% (0/12)
  • Roman Urdu Pass Rate:     0.0% (0/12)
  • Latency:                  p50 = 21.6s, p95 = 31.55s (Gate <= 8s: False)
  • Validator Failures:       {'V1': 0, 'V2': 0, 'V3': 0, 'V4': 0, 'V5': 0}
  • Diagnosis & Fix Applied:  Model failed JSON schema adherence and generated conversational plain text.
```

### Comparative Analysis Table

| Metric | `qwen/qwen3.8-27b` | `openai/gpt-oss-20b` | `allam-2-7b` | `llama-3.1-8b-instant` |
| :--- | :---: | :---: | :---: | :---: |
| **License** | Apache 2.0 | Apache 2.0 | CHECK (Permissive) | Llama Community |
| **Evaluations Attempted** | 36 / 36 | 36 / 36 | 36 / 36 | 0 (API 404) |
| **LLM Success Rate** | **100.0% (36/36)** | 69.4% (25/36) | 0.0% (0/36) | N/A |
| **Template Fallback Rate** | **0.0% (0/36)** | 30.6% (11/36) | 100.0% (36/36) | N/A |
| **Urdu Pass Rate** | **100.0% (12/12)** | 75.0% (9/12) | 0.0% (0/12) | N/A |
| **Roman Urdu Pass Rate** | **100.0% (12/12)** | 58.3% (7/12) | 0.0% (0/12) | N/A |
| **Validator Violations** | None (0 errors) | V1: 2, V5: 1 | None (pre-JSON fail) | N/A |
| **p50 Latency** | 18.85s | 19.57s | 21.60s | N/A |
| **p95 Latency** | 32.72s | 30.08s | 31.55s | N/A |
| **Latency Gate (<= 8s)** | **FAILED** (32.72s) | **FAILED** (30.08s) | **FAILED** (31.55s) | N/A |

---

## 4. Diagnostics of Candidate Failures

### 1. `openai/gpt-oss-20b`: Reasoning Token Truncation
- **Initial Run Failure:** 0% success (all 36 cases fell back to templates).
- **Raw Error (First 300 Chars):** `[CASE_01_BP_SEVERE][en] LLM execution error: JSONDecodeError`
- **Root Cause Diagnosis:** `openai/gpt-oss-20b` is an internal reasoning model. The hardcoded 400 `max_tokens` ceiling was entirely consumed by internal reasoning tokens before completion generation, yielding `finish_reason='length'`, an empty `content` string, and immediate `JSONDecodeError`.
- **Applied Fix:** Adjusted token budget to `max_tokens=1200` to allow reasoning to finish before emitting JSON.
- **Re-Run Outcome:** LLM success jumped to 69.4% (25/36). The remaining 11 fallbacks were due to validator catches: V1 sentence length violations (2 cases), V5 triage level contradiction (1 case: on severe emergency crisis, model asserted "this is an urgent level"), and intermittent JSON truncation.

### 2. `allam-2-7b`: JSON Schema Non-Compliance
- **Initial Run Failure:** 0% success (all 36 cases fell back to templates).
- **Raw Error (First 300 Chars):** `[CASE_01_BP_SEVERE][en] LLM execution error: JSONDecodeError`
- **Root Cause Diagnosis:** When prompted for JSON, `allam-2-7b` generates conversational English prose (e.g., *"Dear patient, based on your blood pressure readings, our Chronic Care AI system has determined..."*). When forced with Groq's `response_format={"type": "json_object"}`, Groq returns HTTP 400 `json_validate_failed`.
- **Applied Fix:** Appended explicit schema reminder instructions to the user prompt.
- **Re-Run Outcome:** 0% success (model persistently outputs unstructured prose).

---

## 5. Latency Gate and Production Architecture

### Latency Gate Evaluation:
- **Threshold:** $p95 \le 8.0\text{ seconds}$.
- **Result:** **ALL MODELS FAILED THE LATENCY GATE.**
  - `qwen/qwen3.8-27b`: $p95 = 32.72\text{ s}$
  - `openai/gpt-oss-20b`: $p95 = 30.08\text{ s}$
  - `allam-2-7b`: $p95 = 31.55\text{ s}$
- **Architectural Consequence:** Cloud-hosted LLM generation on Groq free/tier keys experiences significant queue and network variability, especially when generating multi-sentence English explanations followed by validated Urdu translation.

### Production Guardrail:
In production deployment, **`EXPLAIN_ENABLED=off`** remains the default setting.
- Deterministic clinical triage runs in $< 2\text{ ms}$ on pure Python.
- Pre-verified, human-audited clinical templates (`rag/templates.json`) are served instantly ($< 1\text{ ms}$) without external network dependencies.
- If an operator explicitly enables `EXPLAIN_ENABLED=on`, any timeout ($> 8\text{ s}$) or validator failure falls back instantly to the verified template.

---

## 6. RECOMMENDATION — Usman decides

Based on empirical data across all candidate open-weight models:

1. **If LLM Explanations Are Enabled (`EXPLAIN_ENABLED=on`):**
   - **Recommended Model:** `qwen/qwen3.8-27b`.
   - **Justification:** It is the only model achieving **100% LLM success rate (36/36)**, **zero validator errors**, and **100% pass rates in both Urdu and Roman Urdu** under an Apache 2.0 open-weight license.
   - **Secondary Candidate:** `openai/gpt-oss-20b` requires `max_tokens >= 1200` to prevent reasoning truncation, but only reaches 69.4% pass rate with intermittent V1/V5 clinical validator rejections.
   - **Rejected:** `allam-2-7b` (fails JSON schema adherence); `llama-3.1-8b-instant` (unavailable on account).

2. **Production Baseline:**
   - Keep `EXPLAIN_ENABLED=off` in production container deployment.
   - Serve verified deterministic templates (`templates.json`) to guarantee zero-latency clinical explanations and 100% deterministic safety.

**Decision Authority:** **Usman decides** whether to activate `qwen/qwen3.8-27b` in staging/testing or maintain template-only mode in production.
