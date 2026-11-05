# ChronicCare AI — FYP-1 Report & Paper Evidence Pack

> **Checked Evidence Source for FYP-1 Report, Research Paper, and Demo (Week 3, 5 Nov 2026)**  
> All numbers, claims, and benchmark results in this document are strictly traced to real repository files, test scripts, or command executions.
>
> "Doctor review is not clinical validation."

---

## 1. Pending Upstream Inputs (Saad)

`docs/EVALUATION_NUMBERS.md` does not currently exist on branch `dev`. Per project protocol, all evaluation numbers reserved for that document are marked:
`PENDING: docs/EVALUATION_NUMBERS.md (Saad)`.

The report and paper require the following specific figures once Saad completes his evaluation PR:
1. **Risk Classifier Metrics (NHANES test split)**:
   - Diabetes model: AUROC, Sensitivity, Specificity, Brier score, Expected Calibration Error (ECE).
   - Hypertension model: AUROC, Sensitivity, Specificity, Brier score, ECE.
2. **External Validation Metrics**:
   - Concordance / AUROC proxy on external survey datasets (BRFSS ranking, Framingham/Pima proxies).
3. **End-to-End RAG Faithfulness & Groundedness**:
   - Automated faithfulness scores across the 60-item RAG test set.
4. **Independent Clinician Rating of Bilingual Generated Explanations**:
   - Blinded clinical ratings (accuracy, clarity, patient suitability) on LLM-generated explanations across Urdu and English.

---

## 2. Safety Evidence

| Claim | Number / Finding | Source File & Section | Command to Regenerate | Date |
| :--- | :--- | :--- | :--- | :--- |
| **Danger Word Groups: Hassaan Urdu Independent Set** | 13 / 20 (65.0%) WG vs 4 / 20 (20.0%) v2 | `docs/V3_READINESS.md:38`, `tests/sim/danger_phrases_independent_hassaan_ur.json` | `python scripts/eval_all_phrase_sets.py` | 2026-11-05 |
| **Danger Word Groups: Saad Independent Set** | 6 / 15 (40.0%) WG vs 3 / 15 (20.0%) v2 | `docs/V3_READINESS.md:39`, `tests/sim/danger_phrases_independent_saad.json` | `python scripts/eval_all_phrase_sets.py` | 2026-11-05 |
| **Danger Word Groups: Saad Blind Urdu Set** | 7 / 20 (35.0%) WG vs 2 / 20 (10.0%) v2 | `docs/V3_READINESS.md:40`, `docs/DANGER_PHRASE_PLAN.md:120` | `python scripts/eval_all_phrase_sets.py` | 2026-11-05 |
| **Danger Word Groups: Saad Independent R2 Set** | 9 / 15 (60.0%) WG vs 1 / 15 (6.7%) v2 | `docs/V3_READINESS.md:41`, `tests/sim/danger_phrases_independent_saad_r2.json` | `python scripts/eval_all_phrase_sets.py` | 2026-11-05 |
| **Doctor Decision R1: Meter LO/HI Text Readings** | Immediate confirmation; escalates directly to emergency | `docs/CLINICIAN_RESPONSES.md`, PR #106 | `pytest backend-poc-technical/test_meter_lo_hi.py` | 2026-11-05 |
| **Doctor Decision R2: Fast-Acting Sugar Guidance** | Unanimous: neutral guidance without fixed grams/tablets dosage | `docs/CLINICIAN_RESPONSES.md`, PR #106 | `pytest backend-poc-technical/test_r2_sugar_guidance.py` | 2026-11-05 |
| **Doctor Decision R3: Blood Pressure Guidelines** | Unanimous: cite 2025 AHA/ACC edition; thresholds unchanged | `docs/CLINICIAN_RESPONSES.md`, PR #106 | `pytest backend-poc-technical/test_clinician_rule_changes.py` | 2026-11-05 |
| **Doctor Decision R4: Non-Stop Vomiting** | Unable to keep fluids down is EMERGENCY; other vomiting URGENT | `docs/CLINICIAN_RESPONSES.md`, PR #106 | `pytest backend-poc-technical/test_vomiting_fluids_red_flags.py` | 2026-11-05 |
| **Doctor Decision R5: HbA1c Screening Reminder** | Unanimous: 365-day annual reminder interval for stable HTN adults | `docs/CLINICIAN_RESPONSES.md`, PR #106 | `pytest backend-poc-technical/test_screening_reminder.py` | 2026-11-05 |
| **Doctor Decision R6: Experimental Risk Panel** | Doctors approve provider-only view; never patient-facing | `docs/CLINICIAN_RESPONSES.md`, PR #106 | `pytest backend-poc-technical/test_risk_panel_api.py` | 2026-11-05 |
| **Doctor Decision R7: Bare Glucose 2-40 Unit Re-Ask** | Re-ask unit once before routing to possible low sugar | `docs/CLINICIAN_RESPONSES.md`, PR #106 | `pytest backend-poc-technical/test_r7_glucose_unit_reask.py` | 2026-11-05 |
| **Doctor Decision R8: Check-in With No Readings** | Unanimous: routine if symptom-free; review if symptoms reported | `docs/CLINICIAN_RESPONSES.md`, PR #106 | `pytest backend-poc-technical/test_r8_no_readings.py` | 2026-11-05 |
| **P0 Fix G-14: Caregiver Proxy Readings** | Proxy-entered readings preserved and passed to triage | `backend-poc-technical/agents/interview_v3_runner.py:326`, PR #106 | `pytest backend-poc-technical/test_v3_personas.py` | 2026-11-05 |
| **P0 Fix G-02: Adherence Ambiguity Handling** | Ambiguous adherence marked low confidence instead of silent pass | `backend-poc-technical/agents/answer_validation.py:214`, PR #106 | `pytest backend-poc-technical/test_answer_validation_strings_unchanged.py` | 2026-11-05 |
| **P0 Fix H2: Explanation Template Consistency** | Templates match clinical protocol text across all levels | `backend-poc-technical/rag/templates.json`, PR #110 | `pytest backend-poc-technical/test_explain_templates.py` | 2026-11-05 |
| **P0 Fix H1: Diabetes Explanations Template-Only** | Diabetes condition forced to deterministic templates | `backend-poc-technical/rag/explain_guards.py:188`, PR #110 | `pytest backend-poc-technical/test_explain_guards.py` | 2026-11-05 |
| **P0 Safety Invariant: Emergency Never Calls LLM** | Emergency triage level bypasses explainer queue and LLM entirely | `backend-poc-technical/rag/explain_guards.py:175`, PR #110 | `pytest backend-poc-technical/test_llm_providers.py` | 2026-11-05 |

> **Guideline Permission Status (ADA & AHA/ACC)**:  
> ADA Standards of Care 2026, Sections 2, 5, 6, 10, 11 and 13: written permission received on 5 Nov 2026 for academic evaluation (Nov 2026 to Jun 2027), with conditions; integration is a separate PR (Day 6b). Until it is merged and evaluated, diabetes explanations are templates. AHA/ACC 2025: not permitted, blocked.

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
| **Live Smoke (5 Nov): Total Check-ins** | 10 / 10 review level (100.0%) | `scripts/explain_live_smoke.py`, Day 5 | `python scripts/explain_live_smoke.py` | 2026-11-05 |
| **Live Smoke (5 Nov): Resolution Breakdown** | 6 LLM generated, 4 cache hits, 0 fallbacks, 0 validation failures | `scripts/explain_live_smoke.py`, Day 5 | `python scripts/explain_live_smoke.py` | 2026-11-05 |
| **Live Smoke (5 Nov): Circuit Breakers** | Groq breaker closed; Gemini not needed | `scripts/explain_live_smoke.py`, Day 5 | `python scripts/explain_live_smoke.py` | 2026-11-05 |
| **Live Smoke (5 Nov): API & Job Latency** | `/complete` returned in 0.08–0.22 s; explanation ready in 1.1–3.3 s | `scripts/explain_live_smoke.py`, Day 5 | `python scripts/explain_live_smoke.py` | 2026-11-05 |
| **Live Smoke (5 Nov): Token Consumption** | 5,862 Groq completion tokens recorded | `scripts/explain_live_smoke.py`, Day 5 | `python scripts/explain_live_smoke.py` | 2026-11-05 |

### Explainer Latency Benchmark (`scripts/measure_explain_latency.py`)
Run on 5 November 2026 across 50 check-ins per mode:

| Mode | $p50\text{ (s)}$ | $p95\text{ (s)}$ | $\max\text{ (s)}$ | LLM Calls | Cache Hits | Fallbacks by Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EXPLAIN OFF** | 0.192 | 0.277 | 0.344 | 0 | 0 | none |
| **EXPLAIN INLINE** | 0.543 | 3.167 | 3.299 | 50 | 0 | error: 5 |
| **EXPLAIN BG (/complete)** | 0.275 | 0.567 | 2.634 | 13 | 2 | budget_timeout: 10 |

#### Background Mode: Latency & Extra Time per Delay Profile (50 Check-ins)
*Baseline (EXPLAIN OFF) `/complete` $p50$: 191.8 ms*

| Profile | Count | Simulated Delay | `/complete` Latency ($p50$ / $p95$ / $\max$) | Extra-Time vs Baseline ($p50$ / $p95$ / $\max$) |
| :--- | :--- | :--- | :--- | :--- |
| **fast** | 40 | 200–400 ms | 274.7 ms / 684.2 ms / 2633.9 ms | 82.9 ms / 492.4 ms / 2442.1 ms |
| **edge** | 5 | 2.0–2.5 s | 273.6 ms / 331.1 ms / 331.1 ms | 81.7 ms / 139.3 ms / 139.3 ms |
| **hang** | 3 | 10.0 s (hang) | 330.1 ms / 566.6 ms / 566.6 ms | 138.3 ms / 374.8 ms / 374.8 ms |
| **error** | 2 | exception (500) | 295.4 ms / 295.4 ms / 295.4 ms | 103.6 ms / 103.6 ms / 103.6 ms |
| **Overall** | 50 | mixed | 274.7 ms / 566.6 ms / 2633.9 ms | 82.9 ms / 374.8 ms / 2442.1 ms |

*Background `/complete` $p50$ overhead over baseline: **82.9 ms**.*

---

## 4. Interview Engine Evidence

| Claim | Number / Finding | Source File & Section | Command to Regenerate | Date |
| :--- | :--- | :--- | :--- | :--- |
| **v3 Evaluation: v3 Misses** | 4 misses out of 64 personas (6.25%) | `docs/V3_READINESS.md:20` | `python scripts/run_v3_personas.py` | 2026-11-05 |
| **v3 Evaluation: Both-Misses** | 8 complex personas missed by both v2 and v3 (12.5%) | `docs/V3_READINESS.md:21` | `python scripts/run_v3_personas.py` | 2026-11-05 |
| **v3 Evaluation: Demotions** | 1 demotion from clinician-expected level | `docs/V3_READINESS.md:22` | `python scripts/run_v3_personas.py` | 2026-11-05 |
| **v3 Evaluation: Incomplete Check-ins** | 0 incomplete check-ins (100% completion) | `docs/V3_READINESS.md:23` | `python scripts/run_v3_personas.py` | 2026-11-05 |
| **v3 Evaluation: v2 Over-Triages Resolved** | 7 v2 false-alarm over-triages resolved by v3 | `docs/V3_READINESS.md:24` | `python scripts/run_v3_personas.py` | 2026-11-05 |
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

