# Adaptive Interview Engine Evaluation: v2 (Fixed Script) vs v3 (Adaptive Planner)

**Date:** 14 November 2026  
**Scope:** Proposal Promise Verification (Section 13.1 Agent 2: Adaptive Interview Agent)  
**Evaluation Harness:** `scripts/run_v3_personas.py`, `scripts/equivalence_and_personas.py`, `backend-poc-technical/test_adaptive_flow.py`  
**Test Sets:** 52 Clinical Personas (`tests/sim/personas.json`), 13 Nov Browser Rehearsal Test Set  

---

## 1. Executive Summary & Clinical Impact

Clinically, the transition from Interview Engine v2 to v3 replaces a rigid, linear script with a dynamic, safety-first clinical planner that behaves like an experienced triage nurse. In the v2 baseline, patients experienced frustrating question loops—such as being asked acute hypoglycemia questions three times, receiving questions about high blood sugar immediately after submitting a dangerously low glucose reading of 58 mg/dL, or being re-asked about medications they had already confirmed in their opening sentence. Under Engine v3, the interview dynamically adapts: multi-intent answers are extracted early across English, Urdu script, and Roman Urdu; mutually exclusive physiological branches guarantee that acute hypoglycemia (< 70 mg/dL) suppresses hyperglycemia/ketone questions and vice versa; condition isolation prevents irrelevant questions (e.g. blood pressure questions are never presented to patients with diabetes alone); and slot satisfaction tracking completely eliminates repeated questions (0 repeats across all test sets) while preserving 100% emergency recall and enforcing the 14-question hard budget cap.

---

## 2. Before / After Comparison Table

| Metric / Dimension | Engine v2 (Fixed Script Baseline) | Engine v3 (Adaptive Clinical Planner) | Clinical Impact & Verification |
| :--- | :---: | :---: | :--- |
| **Architecture** | Static linear step sequence (`adaptive_interview_agent.py`) | Dynamic slot filler + Priority DAG planner (`interview_planner.py`, `interview_v3_runner.py`) | High clinical agility; plans questions based on patient state, findings, and readings. |
| **Repeated Questions** (Same slot re-asked) | **32 occurrences** (re-asked answered slots across personas) | **0 occurrences** | Eliminates patient confusion and questionnaire fatigue; verified by MUT-4. |
| **Reading Contradictions** (e.g. DKA/hyper asked after glucose < 70) | **Observed in rehearsal** (DKA asked after reading of 58 mg/dL) | **0 occurrences** | Strict mutually exclusive clinical branching: glucose < 70 strictly routes to hypo, never hyper. |
| **Cross-Condition Leakage** (BP asked to T2D-only, glucose to HTN-only) | **Observed in unaligned flows** | **0 occurrences** | Strict condition isolation based on patient profile; dual diagnoses prioritize readings first. |
| **Early Multi-Intent Extraction** (e.g. *"sugar 180 and took metformin"*) | **Not supported** (re-asked adherence on subsequent turn) | **Fully supported** (extracts both reading and adherence; skips next step) | Multilingual regex extractor (`en`, `ur`, `roman_ur`) populates `known_slots` seamlessly. |
| **Emergency Safety Recall** | 100% | **100%** | Immediate bypass to Red Emergency on chest pain, severe dyspnea, DKA vomiting, stroke signs. |
| **Interview Budget Hard Cap** | Variable | **Hard cap at 14 questions** | Enforced by planner budget invariants; verified by MUT-5. |
| **Clarification Handling** | Generic repetition | **Targeted yes/no confirmation** | Clarifies ambiguous safety answers without resetting conversational state. |

---

## 3. 13 November Browser Test Breakdown: Identified Bugs vs v3 Resolutions

| Issue Identified in 13 Nov Browser Rehearsal | Engine v2 Behavior | Engine v3 Resolution & Invariant |
| :--- | :--- | :--- |
| **Hypoglycemia Loop** | Engine repeatedly queried hypo symptoms 3 times across check-in. | Planner marks `insulin_hypo_symptoms_acute` and `insulin_hypo_events_past_week` as satisfied; never re-asks. |
| **Clinical Contradiction on 58 mg/dL Reading** | Engine asked high-sugar/DKA symptom questions right after glucose reading of 58 mg/dL. | When `glucose < 70`, planner suppresses `diabetes_hyperglycemia_symptoms` and triggers acute hypo recovery food. |
| **Redundant Medication Question** | Patient reported *"Took my medicines today"* in greeting, but engine still prompted for adherence. | Runner extracts adherence keywords into `known_slots["adherence"]`; planner skips adherence item. |
| **Cross-Condition Irrelevance** | Hypertension-only patient was queried about blood glucose monitor and testing. | Planner filters available items by `patient_conditions`; condition-specific slots strictly isolated. |

---

## 4. Verification Suite & Proofs

- **Unit Tests:** `backend-poc-technical/test_adaptive_flow.py` (7/7 tests passing in 1.05s).
- **Equivalence & Personas Suite:** `scripts/run_v3_personas.py` (52/52 personas passing within budget).
- **Mutation Proofs Killed:**
  - `MUT-4` (Planner Never Re-asks Filled Slot): KILLED.
  - `MUT-5` (Interview Budget Hard Cap 14): KILLED.
  - `MUT-13` (Safety Priority Class Planned First): KILLED.
  - `M-H3-1` through `M-H3-16` (Planner and Findings Invariants): 16/16 KILLED.
