# Adaptive Interview Engine Evaluation: v2 (Fixed Script) vs v3 (Adaptive Planner)

**Date:** 14 November 2026  
**Scope:** Proposal Promise Verification (Section 13.1 Agent 2: Adaptive Interview Agent)  
**Evaluation Harnesses:**
- Triage Metrics: `scripts/eval/single_llm_baseline.py --pipeline-only` (51 evaluated non-excluded personas)
- Flow & Question Metrics: `scripts/eval/eval_v2_vs_v3_personas.py`, `scripts/run_v3_personas.py`
**Test Sets:** 52 Clinical Personas (`tests/sim/personas.json`), 13 Nov Browser Rehearsal Test Set  

---

## 1. Executive Summary

The transition from Interview Engine v2 to v3 replaces a fixed linear step sequence (`adaptive_interview_agent.py`) with a dynamic slot-filling and priority DAG planner (`interview_planner.py`, `interview_v3_runner.py`).

In the v2 baseline, the fixed sequence resulted in question repetitions when findings or slots were already addressed in earlier answers (such as being asked acute hypoglycemia questions three times or being re-asked about medications already reported). Under Engine v3, multi-intent extraction parses values and symptoms across English, Urdu script, and Roman Urdu; mutually exclusive physiological branches ensure acute hypoglycemia (< 70 mg/dL) suppresses hyperglycemia/ketone questions and vice versa; condition isolation prevents presenting irrelevant questions across diagnoses; and slot tracking ensures already-filled slots are not re-asked, while preserving identical emergency recall and enforcing the 14-question hard budget cap.

---

## 2. Before / After Comparison Table

The triage figures below reflect the reviewer-verified baseline from `scripts/eval/single_llm_baseline.py --pipeline-only` across the 51 evaluated non-excluded personas. Conversational turn and repeat counts reflect topic-aware execution from `scripts/eval/eval_v2_vs_v3_personas.py`.

| Metric / Dimension | Engine v2 (Fixed Script Baseline) | Engine v3 (Adaptive Clinical Planner) | Verification Evidence |
| :--- | :---: | :---: | :--- |
| **Architecture** | Static linear step sequence (`adaptive_interview_agent.py`) | Dynamic slot filler + Priority DAG planner (`interview_planner.py`, `interview_v3_runner.py`) | Architectural refactor |
| **Emergency Recall** | **3/3 (100.0%)** | **3/3 (100.0%)** | `single_llm_baseline.py --pipeline-only` |
| **Under-Triage Rate** | **1/51 (2.0%)** | **1/51 (2.0%)** | `single_llm_baseline.py --pipeline-only` |
| **Over-Triage Rate** | **24/51 (47.1%)** | **24/51 (47.1%)** | `single_llm_baseline.py --pipeline-only` |
| **Exact Match Accuracy** | **26/51 (51.0%)** | **26/51 (51.0%)** | `single_llm_baseline.py --pipeline-only` |
| **Incomplete Interviews** | **0/51 (0.0%)** | **0/51 (0.0%)** | `single_llm_baseline.py --pipeline-only` |
| **Repeated Questions** (Already filled slot re-asked) | **31 occurrences** | **0 occurrences** | `eval_v2_vs_v3_personas.py` & `MUT-4` |
| **Average Turns per Interview** | **6.1 turns** | **9.0 turns** | `eval_v2_vs_v3_personas.py` |
| **Reading Contradictions** (e.g. DKA/hyper asked after glucose < 70) | Observed in rehearsal (DKA asked after 58 mg/dL) | **0 occurrences** | Mutually exclusive clinical branches in planner |
| **Interview Budget Hard Cap** | Variable | **Hard cap at 14 questions** | Enforced by planner invariant; verified by `MUT-5` |
| **Early Multi-Intent Extraction** (e.g. *"sugar 180 and took metformin"*) | Not supported (re-asked adherence on subsequent turn) | **Supported** (extracts reading and adherence; skips next step) | Regex extractor (`en`, `ur`, `roman_ur`) in runner |
| **Clarification Handling** | Generic repetition | **Targeted yes/no confirmation** | Clarifies ambiguous safety answers without state reset |

---

## 3. 13 November Browser Test Breakdown: Identified Issues & Resolutions

| Issue Identified in 13 Nov Browser Rehearsal | Engine v2 Behavior | Engine v3 Invariant & Implementation |
| :--- | :--- | :--- |
| **Hypoglycemia Re-asking Loop** | Engine repeatedly queried hypo symptoms 3 times across check-in. | Planner marks `insulin_hypo_symptoms_acute` and `insulin_hypo_events_past_week` as satisfied; never re-asks. |
| **Clinical Contradiction on 58 mg/dL Reading** | Engine asked high-sugar/DKA symptom questions right after glucose reading of 58 mg/dL. | When `glucose < 70`, planner suppresses `diabetes_hyperglycemia_symptoms` and prioritizes acute hypo recovery food. |
| **Redundant Medication Question** | Patient reported *"Took my medicines today"* in greeting, but engine still prompted for adherence. | Runner extracts adherence keywords into `known_slots["adherence"]`; planner skips adherence item. |
| **Cross-Condition Irrelevance** | Hypertension-only patient was queried about blood glucose monitor and testing. | Planner filters available items by `patient_conditions`; condition-specific slots strictly isolated. |

---

## 4. Verification Suite & Proofs

- **Unit Tests:** `backend-poc-technical/test_adaptive_flow.py` (7/7 tests passing in 1.05s).
- **Equivalence & Personas Suite:** `scripts/run_v3_personas.py` (52/52 personas passing within budget).
- **Comparative Persona Evaluation:** `scripts/eval/eval_v2_vs_v3_personas.py` (v2 vs v3 run with 0 incomplete interviews).
- **Mutation Proofs Killed:**
  - `MUT-4` (Planner Never Re-asks Filled Slot): KILLED.
  - `MUT-5` (Interview Budget Hard Cap 14): KILLED.
  - `MUT-13` (Safety Priority Class Planned First): KILLED.
  - `M-H3-1` through `M-H3-16` (Planner and Findings Invariants): 16/16 KILLED.
