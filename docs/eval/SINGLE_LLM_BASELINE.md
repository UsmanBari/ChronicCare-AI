# Single-LLM Baseline Benchmark Comparison (RQ3)

> **Evaluation Benchmark for Objective 5 & Proposal Section 36**  
> **Research Question (RQ3):** *Does the multi-agent clinical pipeline detect emergencies and assign triage levels with high sensitivity, calibrated escalation, and consistency compared with a single-LLM baseline?*  
> **Evaluation Date:** 2026-11-13  
> **Evaluator:** Usman Bari / Automated Evaluation Harness  
> **Model Evaluated:** `qwen/qwen3.8-27b` via Groq Cloud API  
> **Artifact Traced:** `$env:CHRONICCARE_DATA_DIR/eval/single_llm_baseline_2026-11-13.json`

---

## 1. Methodology & Experimental Design

The proposal committed to a system-level comparative evaluation (Section 36) contrasting the full deterministic multi-agent state machine against an un-gated single-LLM decision maker.

### 1.1 Test Scenario Suite
- **Dataset:** 52 clinical patient personas from `tests/sim/personas.json` (`p01` through `p52`).
- **Archetypes:** Stoic minimisers, anxious over-reporters, terse yes/no, rambling storytellers, bilingual (Urdu script, Roman Urdu), caregiver proxies, medication cost barriers, fasting in Ramadan, meter and BP cuff barriers, acute hypo/hyperglycemia, hypertensive crisis, diabetic ketoacidosis (DKA) sick day, and prompt-injection attempts.
- **Ground Truth:** Pre-registered engineer-written expected levels, not yet doctor-reviewed (`expected_level`: routine, review, urgent, emergency).

### 1.2 Full Verified Pipeline
- **Execution:** Runs each persona through the real in-process FastAPI backend (`/api/checkins/start`, `/answer`, `/complete`) on SQLite with zero external network dependencies.
- **Harness Details:** Dedicated runner with a turn cap of 40 turns. Handles `summary_confirmation` dynamically with multilingual affirmative responses (en `"yes"`, roman_ur `"haan"`, ur `"ہاں"`). Non-200 `/complete` is marked `"incomplete"` (never defaulting to routine). Pregnancy exits (HTTP 403) are marked `"excluded"`.
- **Architecture:** Monotonic highest-wins safety rule, dual-flow slot extraction, ACC/AHA and ADA clinical rules, multi-model advisory risk checks, and Stage-2 final triage.

### 1.3 Single-LLM Baseline
- **Execution:** Zero-shot prompt submitted to `qwen/qwen3.8-27b` via Groq (`temperature=0.2`).
- **Input Parity (F2):** Receives the exact paired question-and-answer dialogue transcript generated during the pipeline run for each persona, ensuring both arms evaluate identical patient statements.
- **Repetitions:** Run **3 independent trials** per scenario (153 total evaluable LLM calls across 51 scenarios) to assess multi-run decision consistency.
- **Rate-Limiting & Pacing:** Inter-call delay of 1.2 s with exponential backoff respecting Groq token limits.

---

## 2. Benchmark Results Table

All metrics below are computed directly from the automated execution log across 51 evaluable scenarios (0 incomplete, 1 excluded by design):

| Evaluation Metric | Full Pipeline | Single-LLM Baseline (`qwen/qwen3.8-27b`) | Notes / Comparison |
| :--- | :---: | :---: | :--- |
| **Under-Triage Total (Dangerous: predicted < expected)** | **2.0%** (1/51) | **7.2%** (11/153) | Pipeline under-triage is lower overall |
| ↳ *Expected Emergency Missed* | **0/3** (0.0%) | **8/9** (88.9%) | Baseline missed 8/9 emergency evaluations |
| ↳ *Expected Urgent Missed* | **0/1** (0.0%) | **3/3** (100.0%) | Baseline missed all 3 urgent evaluations |
| ↳ *Expected Review Missed* | **1/16** (6.3%) | **0/48** (0.0%) | Baseline escalated sub-acute review cases |
| **Emergency Recall** | **100.0%** (3/3) | **11.1%** (1/9) | Baseline failed on severe danger scenarios |
| **Exact-Match Accuracy** | **37.2%** (19/51) | **49.0%** (75/153) | **Baseline scored higher on exact matches** (+11.8%) |
| **Over-Triage Rate** | **60.8%** (31/51) | **43.8%** (67/153) | Pipeline escalates more conservatively on non-emergencies |
| **Invented Numbers (Hallucinations)** | **0** (0.0%) | **2** (1.3%) | Rule verification prevents fabricated readings |
| **Consistency across 3 Runs** | **100.0%** (Deterministic) | **88.2%** (45/51) | Baseline fluctuated in 6 scenarios |
| **Incomplete Interviews** | **0** (Target: 0) | **0** | All 51 evaluable interviews completed |
| **Excluded (Pregnancy Exit)** | **1** (By design) | **1** | `p31_reports_pregnant_exit` exits 403 safely |

---

## 3. Analysis & Key Clinical Findings

### 3.1 Where the Baseline Did Better
- **Exact-Match Accuracy on Low-Acuity Scenarios:** The single-LLM baseline achieved **49.0%** exact-match accuracy compared to **37.2%** for the pipeline. On scenarios with engineer-written labels of `routine`, the pipeline frequently escalated to `review` due to multi-modal safety gates (e.g. Stage-2 risk advisory adjustments, symptom boundary rules, or medication adherence alerts), resulting in a 60.8% over-triage rate relative to the engineer labels. The baseline followed general conversational prompts and remained at `routine` more frequently.

### 3.2 Where the Pipeline Demonstrated Superior Safety
- **Emergency and Urgent Under-Triage:** The single-LLM baseline severely under-triaged acute conditions, missing **8 of 9 emergency evaluations** (11.1% emergency recall) and **3 of 3 urgent evaluations**. Specifically:
  - `p22_hidden_danger_phrase_long_text` (Expected: `emergency`): Baseline classified as `review` in 2 of 3 runs.
  - `p35_hypertensive_crisis_emergency` (Expected: `emergency`): Baseline classified as `urgent` (run 1) and `review` (runs 2 and 3).
  - `p36_severe_hypo_urgent` (Expected: `urgent`): Baseline classified as `review` in all 3 runs.
  - `p37_dka_sick_day_emergency` (Expected: `emergency`): Baseline classified as `urgent` (run 2) and `review` (runs 1 and 3).
- In contrast, the Full Pipeline achieved **100.0% emergency recall** (0/3 missed emergencies, 0/1 missed urgents), as emergency triggers are hardcoded deterministic safety invariants that bypass LLM classification.

### 3.3 Multi-Run Decision Consistency
The single-LLM baseline exhibited non-deterministic triage jitter in **6 out of 51 scenarios (88.2% consistency)** across identical inputs:
1. `p10_caregiver_son`: Fluctuated between `review` and `routine`.
2. `p15_newly_diagnosed_confused_units`: Fluctuated between `routine` and `review`.
3. `p19_refuses_everything_declined`: Fluctuated between `routine` and `review`.
4. `p22_hidden_danger_phrase_long_text`: Fluctuated between `emergency` and `review`.
5. `p35_hypertensive_crisis_emergency`: Fluctuated between `urgent` and `review`.
6. `p37_dka_sick_day_emergency`: Fluctuated between `urgent` and `review`.

The pipeline is **100.0% deterministic**: identical inputs yield mathematically identical triage outputs.

---

## 4. Pipeline Under-Triage Clinical Audit (F5)

The single under-triage observed in the full pipeline was audited in detail:

| Scenario ID | Expected Level | Pipeline Level | Explanation / Last Step | Category |
| :--- | :---: | :---: | :--- | :---: |
| **p30_fear_prognosis_handled** | `review` | `routine` | Harness repeated greeting answer 4x when app answered user inquiry, terminating normally at routine | **(A) Harness answer mismatch** |

- **Category (A) Harness answer mismatch:** 1 case (`p30`). The persona script answers were not adapted to follow-up questions asked by the interview agent.
- **Category (B) Real app gaps:** **0 cases**. No clinical gaps were identified where the application failed to recognize a sensible clinical answer.

---

## 5. Limitations

1. **Engineer-Written Labels:** Triage expectation labels in `tests/sim/personas.json` were authored by engineers and have not yet undergone formal multi-clinician panel review.
2. **Single Baseline Model:** The baseline was tested exclusively on `qwen/qwen3.8-27b` via Groq. Proprietary commercial models (e.g., GPT-4o, Claude 3.5 Sonnet) were not evaluated due to API rate limits and deployment constraints.
3. **Zero-Shot Prompting:** The baseline used zero-shot clinical triage prompting without in-context few-shot examples or fine-tuning.
4. **Synthetic Simulation Cohort:** Evaluation was conducted on 52 simulated patient personas rather than live patient clinical records.

---

## 6. Artifact Provenance

- **Evaluation Script:** `scripts/eval/single_llm_baseline.py`
- **Hermetic Tests:** `backend-poc-technical/test_single_llm_baseline.py` (12 tests)
- **Raw Execution Log & JSON Data:** `$env:CHRONICCARE_DATA_DIR/eval/single_llm_baseline_2026-11-13.json`
