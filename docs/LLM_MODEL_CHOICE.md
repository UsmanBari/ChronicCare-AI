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

We queried the live Groq API using `scripts/llm/list_models.py` to identify currently active chat completion models. The query returned 11 endpoints:

| Model ID | Developer | Type | Suitability for Explanation |
| :--- | :--- | :--- | :--- |
| `qwen/qwen3.8-27b` | Alibaba Cloud / Qwen | Open-Weight Chat LLM | **Candidate**: High instruction following, multilingual (Urdu support), Apache 2.0. |
| `openai/gpt-oss-20b` | OpenAI / Community | Open-Weight Chat LLM | **Candidate**: Fast open-weight foundation model hosted on Groq. |
| `allam-2-7b` | SDAIA | Open-Weight Bilingual LLM | **Candidate**: Arabic/English regional foundation model. |
| `whisper-large-v3-turbo` | OpenAI | Audio Transcription | Excluded: Speech recognition only. |
| `whisper-large-v3` | OpenAI | Audio Transcription | Excluded: Speech recognition only. |
| `meta-llama/llama-prompt-guard-2-86m` | Meta | Moderation Classifier | Excluded: Moderation classifier, not a generative chat model. |
| `meta-llama/llama-prompt-guard-2-22m` | Meta | Moderation Classifier | Excluded: Moderation classifier. |
| `openai/gpt-oss-safeguard-20b` | OpenAI | Moderation Classifier | Excluded: Safety classifier. |
| `canopylabs/orpheus-arabic-saudi` | Canopy Labs | Audio / Speech | Excluded: Audio/speech synthesis. |
| `canopylabs/orpheus-v1-english` | Canopy Labs | Audio / Speech | Excluded: Audio/speech synthesis. |
| `openai/gpt-oss-120b` | OpenAI | Large Model | Excluded: High latency / quota limits on free tier. |

*(Note: Older endpoints such as `llama-3.1-8b-instant`, `gemma2-9b-it`, and `mixtral-8x7b-32768` returned `model_not_found` / access denied on Groq's current API tier).*

---

## 3. Empirical Benchmark Results

We benchmarked candidate models across **12 realistic clinical triage scenarios** (severe hypertensive emergency, crisis, stage 2 urgent, hypotension, systolic rise, hypoglycemia, severe hypoglycemia, hyperglycemia, acute hyperglycemia, Ramadan fasting glucose drop, pregnancy-induced hypertension, and normal routine vitals) evaluated in **three languages** (English, Urdu, Roman Urdu), yielding **36 full evaluation runs per model**.

Evaluations were executed via `scripts/llm/compare_explainer_models.py` and recorded in `Chroniccare-data/rag/model_comparison_results.json`.

| Metric | `qwen/qwen3.8-27b` | `openai/gpt-oss-20b` | `allam-2-7b` |
| :--- | :---: | :---: | :---: |
| **Open-Weight License** | Apache 2.0 | Open-Weights | Open-Weights |
| **Parameters** | 27B / 32B Class | 20B | 7B |
| **Total Test Scenarios** | 36 (12 x 3 languages) | 36 (12 x 3 languages) | 36 (12 x 3 languages) |
| **LLM Success Rate** | **100.0% (36/36)** | 0.0% (0/36) | 0.0% (0/36) |
| **Template Fallback Rate** | **0.0% (0/36)** | 100.0% (36/36) | 100.0% (36/36) |
| **Urdu Pass Rate** | **100.0% (12/12)** | 0.0% (0/12) | 0.0% (0/12) |
| **Roman Urdu Pass Rate** | **100.0% (12/12)** | 0.0% (0/12) | 0.0% (0/12) |
| **Validator Failures (V1–V5)** | **0 errors across all tests** | JSON Schema Violation | JSON Schema Violation |
| **p50 Latency (Groq)** | 18.13s | 2.02s | 22.14s |
| **p95 Latency (Groq)** | 34.05s | 12.98s | 31.74s |
| **Primary Failure Mode** | None (All passed) | Fails JSON schema | Fails JSON schema |

### Key Observations:
1. **Instruction and Schema Compliance:** `qwen/qwen3.8-27b` followed the complex JSON structure (`{"sentences": [{"text": "...", "cites": ["S1"]}]}`) with 100% reliability. It never hallucinated extraneous keys or conversational prefixes.
2. **Clinical Grounding (V2, V3, V5):** `qwen/qwen3.8-27b` cited retrieved guideline passages accurately without inventing unverified numbers or altering the decided triage level.
3. **Multilingual Urdu Performance:** In Urdu (`ur`) and Roman Urdu (`roman_ur`), `qwen/qwen3.8-27b` demonstrated exceptional lexical accuracy, producing natural, culturally appropriate Urdu medical phrasing (e.g., using "خون کا دباؤ" and "فوری معائنے") while retaining the exact citation markers (`[S1]`, `[S2]`).
4. **Competitor Failures:** Both `allam-2-7b` and `openai/gpt-oss-20b` failed to output strict JSON when given system instructions, triggering `JSONDecodeError` and activating the deterministic template fallback on every test run.

---

## 4. Model Selection and Production Configuration

**Selected Model:** `qwen/qwen3.8-27b`

### Rationale:
- **Zero Validator Failures:** 100% compliance across all 5 clinical safety validators (V1 sentence structure, V2 citation resolution, V3 number grounding, V4 banned phrases, V5 triage level consistency).
- **Trilingual Parity:** Seamless translation pipeline for English, Urdu, and Roman Urdu.
- **Permissive Open-Weight License:** Released under Apache 2.0, permitting research, academic deployment, and self-hosting without proprietary lock-in.

### Production Environment Variables:
```env
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_API_KEY=<configured_server_secret>
```

---

## 5. Future Work (FYP-2): Self-Hosting Pathway

While Groq provides rapid inference during the development and prototype phase, relying on a third-party cloud API introduces external network dependencies and latency variance. For hospital deployment or clinical field trials, self-hosting is the target architectural milestone.

> **Future work (FYP-2)**: To transition ChronicCare AI to an entirely on-premise, air-gapped hospital environment, the explanation layer can be self-hosted using open-source inference runtimes such as **vLLM** or **Ollama** deployed on a local GPU server. Serving `qwen/qwen3.8-27b` at FP16 precision requires approximately 56 GB of VRAM (requiring two NVIDIA RTX 3090/4090 GPUs or an A100/H100 80GB accelerator). However, utilizing state-of-the-art 4-bit quantization (AWQ or GPTQ) reduces the memory footprint to **18–20 GB VRAM**, allowing the entire model to run comfortably on a single consumer-grade 24 GB GPU (such as an NVIDIA GeForce RTX 3090 or 4090) or a local clinical workstation. Extensive literature and empirical benchmarks confirm that 4-bit AWQ incurs virtually zero degradation in perplexity and structured JSON instruction-following. Alternatively, for ultra-low-resource clinic environments (e.g., single 8 GB GPU or CPU-only edge deployments), quantized 7B/8B parameter models (such as Qwen 2.5 7B-Instruct or Llama 3.1 8B-Instruct quantized via GGUF in Ollama) can serve as drop-in local replacements with memory footprints under 6 GB VRAM.
