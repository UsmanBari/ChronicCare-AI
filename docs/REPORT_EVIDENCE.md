# ChronicCare AI — FYP-1 Report & Paper Evidence Pack

> **Checked Evidence Source for FYP-1 Report, Research Paper, and Demo (Week 3, 5 Nov 2026)**  
> All numbers, claims, and benchmark results in this document are strictly traced to real repository files, test scripts, or command executions.
>
> "Doctor review is not clinical validation."

---

## 1. Pending Upstream Inputs (Saad)

`docs/EVALUATION_NUMBERS.md` does not currently exist on branch `dev`. Per project protocol, all evaluation numbers reserved for that document are marked:
`PENDING: docs/EVALUATION_NUMBERS.md (Saad)`.

Per Saad's Day 4 prompt in `docs/tasks/WEEK3_SAAD.md` (Part A, lines 621–633), the script `scripts/collect_eval_numbers.py` must re-compute and provide:
1. **Tests Suite Counts**: Backend CI suite count (both direct and graph orchestrator modes), ML tests count, vitest count, and mutation proofs killed / total.
2. **Safety Persona Simulations (64 Personas)**: Evaluated per engine (v2 and v3): triage level distributions, demotions vs expected (must be 0), and emergency recall on the gold set.
3. **Danger Phrases Benchmark**: Performance across every set $\times$ engine (`scripts/eval_all_phrase_sets.py`), including exact set sizes.
4. **Orchestrator Equivalence**: Total cases identical / total cases across personas, engine scenarios, and defense scenarios (`scripts/orchestrator_equivalence.py`).
5. **Machine Learning Model Metrics**: `diabetes_full_nhanes` test AUROC with 95% CI, sensitivity/specificity at locked operating threshold, calibration slope, card-population AUROC (from `docs/ml/EXPERIMENTS_SUMMARY.md`), and external validation rows (from `docs/ML_EXTERNAL_VALIDATION.md`, preserving "different target" labels).
6. **RAG Retrieval & Explanation Summaries**: Metrics summarized from Day 1 (`docs/RAG_EVAL.md`) and Day 2 (`docs/EXPLAIN_EVAL.md`).
7. **Load and Memory Footprint**: Latency and RSS memory measurements from Day 3 (`docs/LOAD_TEST_W3.md`).
8. **Statement Coverage**: Fresh statement coverage percentage from `pytest-cov`.

---

## 2. Safety Evidence

| Claim | Number / Finding | Source File & Section | Command to Regenerate | Date |
| :--- | :--- | :--- | :--- | :--- |
| **Danger Word Groups: Hassaan Urdu Independent Set** | 13 / 20 (65.0%) WG vs 4 / 20 (20.0%) v2 | `docs/V3_READINESS.md:38`, `tests/sim/danger_phrases_independent_hassaan_ur.json` | `python scripts/eval_all_phrase_sets.py` | 2026-11-05 |
| **Danger Word Groups: Saad Independent Set** | 6 / 15 (40.0%) WG vs 3 / 15 (20.0%) v2 | `docs/V3_READINESS.md:39`, `tests/sim/danger_phrases_independent_saad.json` | `python scripts/eval_all_phrase_sets.py` | 2026-11-05 |
| **Danger Word Groups: Saad Blind Urdu Set** | 7 / 20 (35.0%) WG vs 2 / 20 (10.0%) v2 | `docs/V3_READINESS.md:40`, `docs/DANGER_PHRASE_PLAN.md:120` | `python scripts/eval_all_phrase_sets.py` | 2026-11-05 |
| **Danger Word Groups: Saad Independent R2 Set** | 9 / 15 (60.0%) WG vs 1 / 15 (6.7%) v2 | `docs/V3_READINESS.md:41`, `tests/sim/danger_phrases_independent_saad_r2.json` | `python scripts/eval_all_phrase_sets.py` | 2026-11-05 |
| **Doctor Decision R1: Meter LO/HI Text Readings** | Immediate confirmation; escalates directly to emergency | `docs/CLINICIAN_RESPONSES.md:144-150`, PR #106 | `pytest backend-poc-technical/test_meter_lo_hi.py` | 2026-11-05 |
| **Doctor Decision R2: Fast-Acting Sugar Guidance** | Unanimous: neutral guidance without fixed grams/tablets dosage | `docs/CLINICIAN_RESPONSES.md:152-156`, PR #106 | `pytest backend-poc-technical/test_r2_sugar_guidance.py` | 2026-11-05 |
| **Doctor Decision R3: Blood Pressure Guidelines** | Unanimous: cite 2025 AHA/ACC edition; thresholds unchanged | `docs/CLINICIAN_RESPONSES.md:158-162`, PR #106 | `pytest backend-poc-technical/test_clinician_rule_changes.py` | 2026-11-05 |
| **Doctor Decision R4: Non-Stop Vomiting** | Unable to keep fluids down is EMERGENCY; other vomiting URGENT | `docs/CLINICIAN_RESPONSES.md:164-172`, PR #106 | `pytest backend-poc-technical/test_vomiting_fluids_red_flags.py` | 2026-11-05 |
| **Doctor Decision R5: HbA1c Screening Reminder** | Unanimous: 365-day annual reminder interval for stable HTN adults | `docs/CLINICIAN_RESPONSES.md:174-178`, PR #106 | `pytest backend-poc-technical/test_screening_reminder.py` | 2026-11-05 |
| **Doctor Decision R6: Experimental Risk Panel** | Doctors approve provider-only view; never patient-facing | `docs/CLINICIAN_RESPONSES.md:180-184`, PR #106 | `pytest backend-poc-technical/test_risk_panel_api.py` | 2026-11-05 |
| **Doctor Decision R7: Bare Glucose 2-40 Unit Re-Ask** | Re-ask unit once before routing to possible low sugar | `docs/CLINICIAN_RESPONSES.md:186-192`, PR #106 | `pytest backend-poc-technical/test_r7_glucose_unit_reask.py` | 2026-11-05 |
| **Doctor Decision R8: Check-in With No Readings** | Unanimous: routine if symptom-free; review if symptoms reported | `docs/CLINICIAN_RESPONSES.md:194-202`, PR #106 | `pytest backend-poc-technical/test_r8_no_readings.py` | 2026-11-05 |
| **P0 Fix G-14: Caregiver Proxy Readings** | Proxy-entered readings preserved and passed through to triage | `backend-poc-technical/agents/interview_v3_runner.py:326-340`, PR #113 | `pytest backend-poc-technical/test_v3_caregiver_roman_ur.py::test_caregiver_prefix_on_every_answer_whole_checkin` | 2026-11-05 |
| **P0 Fix G-02: Adherence Clarification Flow** | Unclear answer $\rightarrow$ one clarification $\rightarrow$ still unclear $\rightarrow$ 'unclear' + review | `backend-poc-technical/agents/interview_v3_runner.py:702-744`, `backend-poc-technical/agents/answer_understanding.py:886-932`, PR #113 | `pytest backend-poc-technical/test_v3_adherence_unclear.py::test_v3_flow_still_unclear_after_clarification_sets_unclear_and_requires_review` | 2026-11-05 |
| **P0 Fix H2: Template Consistency Guard** | Template never contradicts readings (`is_template_consistent`) | `backend-poc-technical/rag/explainer.py:285-375`, PR #110 | `pytest backend-poc-technical/test_llm_providers.py::test_h2_template_consistency_corrections` | 2026-11-05 |
| **P0 Fix H1: Diabetes Explanations Template-Only** | Diabetes condition forced to deterministic templates | `backend-poc-technical/rag/explain_guards.py:1060-1063`, PR #110 | `pytest backend-poc-technical/test_llm_providers.py::test_h1_condition_filter_blocks_diabetes_by_default` | 2026-11-05 |
| **P0 Safety Invariant: Emergency Never Calls LLM** | Emergency early return bypasses step 10 explainer & queue entirely | `backend-poc-technical/orchestrator/steps.py:166-211,286-324`, `backend-poc-technical/orchestrator/graph.py:81`, `backend-poc-technical/main.py:4839-4841` | `pytest backend-poc-technical/test_explain_guards.py::test_c6_emergency_intakes_bypass_explainer` | 2026-11-05 |

> **Guideline Permission Status (ADA & AHA/ACC)**:  
> ADA Standards of Care in Diabetes—2026, Sections 2, 5, 6, 10, 11 and 13: written permission received on 5 Nov 2026 for academic evaluation (Nov 2026 to Jun 2027) with conditions (details in `docs/licences/ADA_2026_PERMISSION.md`). Plain-language explanations are generated from these sections exclusively via Groq and never sent to Google Gemini (G3); all stored ADA material is scheduled for permanent deletion on 30 June 2027. AHA/ACC 2025: not permitted, blocked.

---

## 3. Explainer & RAG Evidence

| Claim | Number / Finding | Source File & Section | Command to Regenerate | Date |
| :--- | :--- | :--- | :--- | :--- |
| **Template Explainer Pass Rate** | 40 / 40 passed (100.0%) | `docs/EXPLAIN_EVAL.md:21` (templates only) | `python scripts/eval_explainer.py` | 2026-11-04 |
| **Template Latency Profile** | $p50 = 0.0\text{ ms}$, $p95 = 0.8\text{ ms}$ | `docs/EXPLAIN_EVAL.md:21` (templates only) | `python scripts/eval_explainer.py` | 2026-11-04 |
| **Template Urdu Character Share** | 98.7% Urdu script characters | `docs/EXPLAIN_EVAL.md:27` | `python scripts/eval_explainer.py` | 2026-11-04 |
| **Template Blind Review Clarity** | 20 / 20 clarity score (Hassaan & Saad) | `docs/EXPLAIN_EVAL.md:28` | Manual human evaluation | 2026-11-04 |
| **RAG Open Primary Sources** | 0 / 60 cite allowed primary source (0.0%) | `docs/RAG_EVAL.md:19` | `python scripts/eval_retrieval.py` | 2026-11-04 |
| **RAG Open Diabetes Coverage** | 1 / 25 diabetes questions open (4.0%) | `docs/RAG_EVAL.md:20` | `python scripts/eval_retrieval.py` | 2026-11-04 |
| **RAG Open HTN Coverage** | 25 / 25 HTN questions open (100.0%) | `docs/RAG_EVAL.md:21` | `python scripts/eval_retrieval.py` | 2026-11-04 |
| **RAG Top-1 Retrieval Relevance** | 6 / 10 sample queries relevant (60.0%) | `docs/RAG_EVAL.md:22` | `python scripts/eval_retrieval.py` | 2026-11-04 |
| **Live Smoke (5 Nov): Total Check-ins** | 10 / 10 review level (100.0%) | Usman's live run 5 Nov (raw output with Usman), SUMMARY | `python scripts/explain_live_smoke.py` | 2026-11-05 |
| **Live Smoke (5 Nov): Resolution Breakdown** | 6 LLM generated, 4 cache hits, 0 fallbacks, 0 validation failures | Usman's live run 5 Nov (raw output with Usman), SUMMARY | `python scripts/explain_live_smoke.py` | 2026-11-05 |
| **Live Smoke (5 Nov): Circuit Breakers** | Groq breaker closed; Gemini not needed | Usman's live run 5 Nov (raw output with Usman), SUMMARY | `python scripts/explain_live_smoke.py` | 2026-11-05 |
| **Live Smoke (5 Nov): API & Job Latency** | `/complete` returned in 0.08–0.22 s; explanation ready in 1.1–3.3 s | Usman's live run 5 Nov (raw output with Usman), SUMMARY | `python scripts/explain_live_smoke.py` | 2026-11-05 |
| **Live Smoke (5 Nov): Token Consumption** | 5,862 Groq TOTAL tokens recorded | Usman's live run 5 Nov (raw output with Usman), SUMMARY | `python scripts/explain_live_smoke.py` | 2026-11-05 |

### Explainer Latency Benchmark (`scripts/measure_explain_latency.py`)
Run on 5 November 2026 in an isolated benchmark session across 50 check-ins per mode:

| Mode | $p50\text{ (s)}$ | $p95\text{ (s)}$ | $\max\text{ (s)}$ | LLM Calls | Cache Hits | Fallbacks by Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EXPLAIN OFF** | 0.188 | 0.375 | 0.734 | 0 | 0 | none |
| **EXPLAIN INLINE** | 0.516 | 3.188 | 3.203 | 50 | 0 | budget_timeout: 1, error: 4 |
| **EXPLAIN BG (/complete)** | 0.188 | 0.312 | 0.359 | 13 | 4 | budget_timeout: 16 |

#### Background Mode: Latency & Extra Time per Delay Profile (50 Check-ins)
*Baseline (EXPLAIN OFF) `/complete` $p50$: 188.0 ms. Isolated benchmark run.*

| Profile | Count | Simulated Delay | `/complete` Latency ($p50$ / $p95$ / $\max$) | Extra-Time vs Baseline ($p50$ / $p95$ / $\max$) |
| :--- | :--- | :--- | :--- | :--- |
| **fast** | 40 | 200–400 ms | 188.0 ms / 328.0 ms / 359.0 ms | 0.0 ms / 140.0 ms / 171.0 ms |
| **edge** | 5 | 2.0–2.5 s | 157.0 ms / 188.0 ms / 188.0 ms | 0.0 ms / 0.0 ms / 0.0 ms |
| **hang** | 3 | 10.0 s (hang) | 172.0 ms / 266.0 ms / 266.0 ms | 0.0 ms / 78.0 ms / 78.0 ms |
| **error** | 2 | exception (500) | 281.0 ms / 281.0 ms / 281.0 ms | 93.0 ms / 93.0 ms / 93.0 ms |
| **Overall** | 50 | mixed | 188.0 ms / 312.0 ms / 359.0 ms | 0.0 ms / 124.0 ms / 171.0 ms |

*Background `/complete` $p50$ overhead over baseline: **0.0 ms**.*  
*(Note: An earlier concurrent run executed alongside `scripts/orchestrator_equivalence.py` yielded baseline $p50 = 191.8\text{ ms}$ and background $p50 = 274.7\text{ ms}$, reflecting local CPU contention from concurrent SQLite table migrations).*

---

## 4. Interview Engine Evidence

| Claim | Number / Finding | Source File & Section | Command to Regenerate | Date |
| :--- | :--- | :--- | :--- | :--- |
| **v3 Evaluation: v3 Misses** | 4 misses out of 64 personas (6.25%) | `docs/V3_READINESS.md:20` | `python scripts/v3_readiness_report.py` | 2026-11-05 |
| **v3 Evaluation: Both-Misses** | 8 complex personas missed by both v2 and v3 (12.5%) | `docs/V3_READINESS.md:21` | `python scripts/v3_readiness_report.py` | 2026-11-05 |
| **v3 Evaluation: Demotions** | 1 demotion (v3 lower than v2) | `docs/V3_READINESS.md:22` | `python scripts/v3_readiness_report.py` | 2026-11-05 |
| **v3 Evaluation: Incomplete Check-ins** | 0 incomplete check-ins (100% completion) | `docs/V3_READINESS.md:23` | `python scripts/v3_readiness_report.py` | 2026-11-05 |
| **v3 Evaluation: v2 Over-Triages Resolved** | 7 v2 false-alarm over-triages resolved by v3 | `docs/V3_READINESS.md:24` | `python scripts/v3_readiness_report.py` | 2026-11-05 |
| **Engine Default Decision** | v2 remains the default engine for Release 2 | `docs/V3_DECISION.md:12` | Review configuration | 2026-11-05 |

---

## 5. Engineering & System Verification Evidence

| Claim | Number / Finding | Source File & Section | Command to Regenerate | Date |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Hermetic Suite (Direct Mode)** | 1,797 passed, 1 deselected, 12 warnings | `.github/workflows/ci.yml` | `$env:ORCHESTRATOR="direct"; pytest ...` | 2026-11-05 |
| **Backend Hermetic Suite (Graph Mode)** | 1,797 passed, 1 deselected, 12 warnings | `.github/workflows/ci.yml` | `$env:ORCHESTRATOR="graph"; pytest ...` | 2026-11-05 |
| **Frontend Test Suite** | 300 passed across 35 test files | `package.json` | `npm test` | 2026-11-05 |
| **Mutation Testing Harness Totals** | Valid: 60 \| Killed: 60 \| Survived: 0 \| Invalid: 0 | `scripts/verify_mutations.py` | `python scripts/verify_mutations.py` | 2026-11-05 |
| **Orchestrator Equivalence: Personas** | 64 / 64 cases 100% identical | `scripts/orchestrator_equivalence.py:328` | `python scripts/orchestrator_equivalence.py` | 2026-11-05 |
| **Orchestrator Equivalence: Engine Scenarios**| 7 / 7 cases 100% identical | `scripts/orchestrator_equivalence.py:355` | `python scripts/orchestrator_equivalence.py` | 2026-11-05 |
| **Orchestrator Equivalence: Defense Scenarios**| 7 / 7 cases 100% identical | `scripts/orchestrator_equivalence.py:378` | `python scripts/orchestrator_equivalence.py` | 2026-11-05 |
| **Orchestrator Equivalence Overall** | 78 / 78 cases 100% identical (100.0%) | `scripts/orchestrator_equivalence.py:423` | `python scripts/orchestrator_equivalence.py` | 2026-11-05 |
