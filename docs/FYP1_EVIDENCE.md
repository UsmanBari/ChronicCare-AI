# ChronicCare AI — FYP-1 Official Evidence Pack

> **Checked Evidence for FYP-1 Evaluation, Viva, and Report**  
> **Evaluation Date:** 17 November 2026  
> **Guiding Principle:** *"The model proposes, the rules decide. Doctor review is not clinical validation."*  
> Every number, metric, and finding in this document is traced directly to an existing repository file, test suite execution, or benchmark run. If evidence does not exist in the repository, it is explicitly excluded or marked as missing.

---

## 1. Test Suite Verification & Code Health

All automated verification gates pass completely on both Linux CI and local Windows execution environments:

| Test Suite | Count / Status | Details / Modes | Evidence Source | Command to Reproduce |
| :--- | :---: | :--- | :--- | :--- |
| **Backend Hermetic Pytest Suite** | **2,245+ passed** | Direct orchestrator (`ORCHESTRATOR=direct`) and Graph orchestrator (`ORCHESTRATOR=graph`); zero failures | `.github/workflows/ci.yml:46` | `pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q` |
| **Frontend Unit & Component Suite** | **361 passed** (45 files) | Vitest component testing, role mapping, mock-mode fallbacks, accessibility hooks | `package.json:11`, `tests/` | `npm test` |
| **Machine Learning Test Suite** | **91 passed** | Model loading, feature mapping, threshold validation, SHAP explainer parity | `backend-poc-technical/ml/tests/` | `python -m pytest backend-poc-technical/ml/tests -q` |
| **Automated Mutation Proofs** | **60 / 60 killed** (100.0%) | 60 deliberate clinical and safety rule mutations; 0 survived, 0 invalid | `scripts/verify_mutations.py:12` | `python scripts/verify_mutations.py` |
| **Playwright E2E Demo Journeys** | **12 passed, 2 skipped** | Journeys J-a through J-i + J1-J3; zero failures; 18 screenshots captured | `tests-e2e/journeys.playwright.ts` | `npx playwright test tests-e2e/journeys.playwright.ts` |
| **WCAG 2.1 AA Accessibility Audit** | **9 / 9 screens passed** | 0 critical, 0 serious axe-core violations across desktop (1280px) and mobile (360/375px) | `tests-e2e/accessibility.playwright.ts` | `npx playwright test tests-e2e/accessibility.playwright.ts` |
| **Orchestrator Mode Equivalence** | **78 / 78 cases identical** | 64 personas + 7 engine scenarios + 7 defense scenarios identical between Direct and Graph | `scripts/orchestrator_equivalence.py:423` | `python scripts/orchestrator_equivalence.py` |
| **Frontend TypeScript Typecheck** | **0 errors** | Strict TypeScript compilation (`tsc --noEmit`) | `tsconfig.json` | `npx tsc --noEmit` |
| **Frontend Production Build** | **Success** (4/4 pages) | Next.js optimized static export with zero prerender errors | `app/` | `npm run build` |
| **Python Code Quality (Ruff)** | **All checks passed** | Syntax and syntax error checks across `backend-poc-technical` and `scripts` | `.github/workflows/ci.yml:37` | `ruff check backend-poc-technical scripts --select E9,F63,F7,F82` |

---

## 2. Machine Learning Risk Models Evidence

Models evaluate 10-year cardiometabolic risk to support clinical provider reviews. In accordance with proposal safety invariants, models run as advisory inputs and cannot lower an elevated triage level.

### 2.1 Benchmark Performance Matrix (Held-Out Test Sets)
*Source:* `docs/ml/EXPERIMENTS_SUMMARY.md:14-20`, `docs/ml/experiments/`

| Model Identifier | Training Cohort | Target Condition | Test AUROC [95% CI] | Sensitivity | Specificity | PPV | Cal Slope | Locked Threshold | Card Pop AUROC | Gate Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`diabetes_full_nhanes`** | US NHANES (1999–2023)<br>n=27,448 train / 8,681 test | Undiagnosed Type 2 Diabetes | **0.7527**<br>[0.7293–0.7748] | **85.28%** | 52.23% | 7.17% | 0.848 | 0.038 | **0.6640** | **SHIP CANDIDATE**<br>(All D11 gates passed) |
| **`chd10_framingham`** | Framingham Heart Study<br>n=2,499 train / 834 test | 10-Year Coronary Heart Disease | **0.7241**<br>[0.6732–0.7659] | **84.80%** | 39.07% | 19.70% | 1.142 | 0.125 | **0.6488** | **SHIP CANDIDATE**<br>(All G1–G5 gates passed) |
| `diabetes_basic_nhanes` | US NHANES<br>n=29,084 train / 9,117 test | Undiagnosed Type 2 Diabetes | 0.7403<br>[0.7182–0.7616] | 85.05% | 51.40% | 7.22% | 0.820 | 0.038 | 0.6561 | Not Shipped (AUROC < 0.75) |
| `htn_full_nhanes` | US NHANES<br>n=20,766 train / 6,537 test | Undiagnosed Hypertension | 0.7105<br>[0.6983–0.7230] | 80.49% | 52.08% | 42.62% | 0.858 | 0.280 | 0.5317 | Not Shipped (Subgroup sens < 60%) |
| `htn_basic_nhanes` | US NHANES<br>n=22,061 train / 7,037 test | Undiagnosed Hypertension | 0.7148<br>[0.7022–0.7262] | 80.40% | 52.65% | 42.89% | 0.869 | 0.280 | 0.5442 | Not Shipped (Subgroup sens < 60%) |

### 2.2 Key Clinical ML Insights
1. **Operating Threshold Selection**: Operating thresholds were strictly pre-locked on validation cohorts targeting $\ge 80\%$ sensitivity (`min_sensitivity >= 0.80`) to prioritize catching undiagnosed cases in screening.
2. **Card-Population Discrimination**: When evaluated on the specific patient population viewing the risk panel (reciprocal diagnosis, e.g., screening hypertensive patients for diabetes), AUROC drops to **0.6640** for diabetes and **0.5317** for hypertension. This finding justified keeping risk estimates advisory in provider review and displaying only qualitative bands to patients.
3. **Subgroup Disparities**: In adults under 40, tabular models exhibit lower sensitivity (63.8% in `diabetes_full_nhanes`, 38.4% in `htn_basic_nhanes`), reflecting the dominant coefficient weight of chronological age in cardiovascular risk equations.

---

## 3. Safety & Danger Phrase Detection Evidence

*Source:* `docs/BLIND_SET_3_RESULTS.md`, `docs/V3_READINESS.md`, `docs/CLINICIAN_RESPONSES.md`

### 3.1 Blind Danger Phrase Benchmark (Set #3 — 50 items: 25 Danger, 25 Safe)
Held outside the repository and executed without post-hoc tuning (`scripts/eval_all_phrase_sets.py --heldout-counts-only`):

| Evaluation Engine | Danger Sensitivity | False Alarm Rate | Specificity | Architecture Mechanism |
| :--- | :---: | :---: | :---: | :--- |
| **Legacy Substring Engine (v2)** | 4 / 25 (**16.0%**) | **0.0%** (0/25) | **100.0%** | Exact substring matching on `RED_FLAG_PATTERNS` |
| **Slot Classifier Engine (v3)** | 7 / 25 (**28.0%**) | **0.0%** (0/25) | **100.0%** | Multilingual slot filling & regex dictionary |
| **Danger Word Groups v1 (WG_V1)** | **20 / 25 (80.0%)** | 16.0% (4/25) | **84.0%** | Composable symptom word groups with negation boundaries |
| **Hybrid Pipeline (v2 + Word Groups)** | **20 / 25 (80.0%)** | 16.0% (4/25) | **84.0%** | Active live configuration (`DANGER_WORDGROUPS_ENABLED=true`) |

### 3.2 Independent Clinical Phrase Sets
- **Hassaan Urdu Independent Set (20 items):** Word Groups caught **13 / 20 (65.0%)** vs v2 **4 / 20 (20.0%)** (`docs/V3_READINESS.md:38`).
- **Saad Independent Set (15 items):** Word Groups caught **6 / 15 (40.0%)** vs v2 **3 / 15 (20.0%)** (`docs/V3_READINESS.md:39`).
- **Saad Blind Urdu Set (20 items):** Word Groups caught **7 / 20 (35.0%)** vs v2 **2 / 20 (10.0%)** (`docs/V3_READINESS.md:40`).
- **Saad Independent R2 Set (15 items):** Word Groups caught **9 / 15 (60.0%)** vs v2 **1 / 15 (6.7%)** (`docs/V3_READINESS.md:41`).

---

## 4. RAG Retrieval & Clinical Explanation Quality

*Source:* `docs/RAG_EVAL.md`, `docs/EXPLAIN_EVAL.md`, `docs/REPORT_EVIDENCE.md`

### 4.1 Retrieval Quality (60 Clinical Queries on Held-Out Guidelines)
Evaluated on 498 open guideline chunks (`docs/RAG_EVAL.md:23-27`):
- **English Query Retrieval:** Source Hit@1: **77.8%**, Source Hit@3: **94.4%**, Source Hit@5: **97.2%**, Mean Reciprocal Rank (MRR): **0.862**.
- **Roman Urdu Query Retrieval:** Source Hit@1: **80.6%**, Source Hit@3: **94.4%**, Source Hit@5: **97.2%**, MRR: **0.882**.
- **Urdu Script Query Retrieval (Free text):** Source Hit@1: **33.3%**, Source Hit@3: **47.2%**, Source Hit@5: **52.8%**, MRR: **0.409** (In production, search queries are mapped from English triage keys, bypassing script degradation).
- **Passage-Level Topical Precision:** Manual review of top-1 retrieved passages across diverse English queries demonstrated **6 / 10 (60.0%)** clinical relevance.

### 4.2 Explainer Safety & Latency
- **Deterministic Template Explainer:** 40 / 40 passed clinical verification (100.0%); latency $p50 = 0.0\text{ ms}$, $p95 = 0.8\text{ ms}$; 98.7% Urdu script characters (`docs/EXPLAIN_EVAL.md:21-27`).
- **Background Mode Latency Overhead:** In isolated benchmarks across 50 check-ins (`scripts/measure_explain_latency.py`), background mode returned `/complete` with **0.0 ms $p50$ overhead** over baseline (both $p50 = 188.0\text{ ms}$).
- **Human Clinical Read (8 Nov):** English LLM explanations rated 4/4 acceptable (100.0%). Urdu/Roman Urdu LLM translations had 1 critical translation error altering clinical meaning. **Decision:** Release 2 locked LLM explanations to English only (`EXPLAIN_LLM_LANGUAGES=en`), routing Urdu and Roman Urdu check-ins to vetted deterministic templates (`docs/REPORT_EVIDENCE.md:84`).

---

## 5. System-Level Pipeline vs Single-LLM Baseline (Objective 5 / Section 36)

*Source:* `docs/eval/SINGLE_LLM_BASELINE.md`, PR #144 (*pending merge to dev*)  
Evaluated across 52 simulated patient personas (`tests/sim/personas.json`), with 51 evaluable scenarios (0 incomplete, 1 excluded pregnancy exit by design) and 3 independent zero-shot LLM trials per persona (153 total trials on `qwen/qwen3.8-27b` via Groq):

| Comparative Metric | Full Multi-Agent Pipeline | Single-LLM Baseline (`qwen/qwen3.8-27b`) | Finding & Clinical Impact |
| :--- | :---: | :---: | :--- |
| **Dangerous Under-Triage Rate** | **2.0%** (1/51) | **7.2%** (11/153) | Pipeline reduces dangerous under-triage by 72% |
| ↳ *Expected Emergency Missed* | **0 / 3 (0.0%)** | **8 / 9 (88.9%)** | Baseline missed 8 of 9 emergency evaluations |
| ↳ *Expected Urgent Missed* | **0 / 1 (0.0%)** | **3 / 3 (100.0%)** | Baseline missed all 3 urgent evaluations |
| ↳ *Expected Review Missed* | **1 / 16 (6.3%)** | **0 / 48 (0.0%)** | Baseline escalated sub-acute review cases |
| **Emergency Recall** | **100.0%** (3/3) | **11.1%** (1/9) | Pipeline guarantees emergency safety invariants |
| **Exact-Match Accuracy** | **37.2%** (19/51) | **49.0%** (75/153) | **Baseline scored higher on exact matches** (+11.8%) |
| **Over-Triage Rate** | **60.8%** (31/51) | **43.8%** (67/153) | Pipeline escalates conservatively on non-emergencies |
| **Hallucinated / Invented Numbers** | **0** (0.0%) | **2** (1.3%) | Pipeline verification prevents invented numbers |
| **Multi-Run Decision Consistency** | **100.0%** (Deterministic) | **88.2%** (45/51) | Baseline fluctuated in 6 scenarios across 3 runs |
| **Incomplete Interviews** | **0** (Target: 0) | **0** | Both arms completed all 51 evaluable cases |
| **Under-Triage Audit: Category B (App Gaps)** | **0 cases** | — | Single under-triage (`p30`) was harness mismatch (Category A) |

---

## 6. Optical Character Recognition (OCR) Intake

*Source:* `docs/ocr/compare_results.md:12-34`  
Evaluated across 13 synthetic clinical reports and 4 real phone-photographed doctor prescriptions (9 prescribed medicines total):

| Benchmark Group | Engine | Latency | Character Error Rate (CER) | Field Recall | Medicine Recall | Architecture Finding |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Clean Synthetic Reports (10 samples)** | Tesseract.js (Client) | 462.0 ms | 24.9% | 100.0% (24/24) | 100.0% (7/7) | 0 MB server footprint |
| | RapidOCR (Server ONNX) | 2047.2 ms | 24.4% | 95.8% (23/24) | 100.0% (7/7) | 108.99 MB RAM footprint |
| **Noisy & Rotated Documents (3 samples)** | RapidOCR | 1833.3 ms | 20.4% | 87.5% (7/8) | 100.0% (3/3) | Robust orientation detection |
| **Real Handwritten Prescriptions (4 photos)** | Tesseract.js | 1643.8 ms | 75.8% | 11.1% (1/9) | 11.1% (1/9) | Severe handwriting degradation |
| | RapidOCR | 2998.0 ms | 22.3% | 100.0% (9/9) | 100.0% (9/9) | Word joiner extracts medicines |

**Safety Invariant:** Because handwriting varies widely, OCR output is **never** committed directly to records. All extractions are staged to an interactive confirmation screen (`app/components/OcrConfirmScreen.tsx`) where patients verify, edit, or reject items, and are assigned Medium trust (`unverified`) in the health record (`LA-15`).

---

## 7. Local Acceptance Suite Summary (`scripts/local_acceptance.py`)

*Source:* `scripts/local_acceptance.py`, executed on local SQLite baseline:

| ID | Verified Feature | Proposal Section | Local Status | Verification Method |
| :--- | :--- | :---: | :---: | :--- |
| **LA-00** | Authentication smoke check (Firebase token session) | Sec 13.2 | **PASS** | Session cookie issued |
| **LA-01** | System health check & SQLite configuration status | Sec 13.2 | **PASS** | Health 200, DB=sqlite |
| **LA-02** | Isolated check-in with BP 118/76 -> Routine | Sec 13.1 | **PASS** | Triage: routine |
| **LA-03** | Isolated BP 145/92 triage -> Review | Sec 15 | **PASS** | Triage: review |
| **LA-04** | Isolated BP 182/112 triage -> Urgent | Sec 15 | **PASS** | Triage: urgent |
| **LA-05** | Acute emergency bypass with 1122 hotline | Sec 13.2 | **PASS** | Emergency screen; 1122 only |
| **LA-06** | Diabetes glucose 190 mg/dL -> Review | Sec 15 | **PASS** | Triage: review |
| **LA-07** | Medication confirmation check-in -> 200 | Sec 13.1 | **PASS** | Medication verified |
| **LA-08** | No readings entered, all answers 'no' -> Routine (Rule R8) | Sec 13.2 | **PASS** | Rule R8 wording template |
| **LA-09** | EHR reconciliation conflict -> Yellow review | Sec 13.1 | **PASS** | Discrepancy flagged |
| **LA-10** | English plain-language explanation | Sec 13.2 | **PASS** | ADA citation present |
| **LA-11** | Urdu template explanation | Sec 13.2 | **PASS** | Urdu script template |
| **LA-12** | Guideline source citation attribution | Sec 13.2 | **PASS** | Chunk citation intact |
| **LA-13** | Advisory risk models evaluated in provider review | Sec 13.1 | **PASS** | Risk object present |
| **LA-14** | Longitudinal observation series retrieval | Sec 16 | **PASS** | Historical series retrieved |
| **LA-15** | Server-side OCR prescription intake & confirmation | Sec 21.1 | **PASS** | Staged extraction confirmed |
| **LA-15b**| OCR intake in isolated onboarding flow | Sec 18, 21.1 | **PASS** | Medium trust badge saved |
| **LA-16** | Voice transcription input endpoint | Sec 23 | **PASS** | Audio transcription returned |
| **LA-17** | Record edit history audit & export/import | Sec 13.2 | **PASS** | Export JSON valid |
| **LA-18** | Zero-PHI append-only audit logging | Sec 13.2 | **PASS** | Audit events recorded |
| **LA-20** | Triage severity colors (Green / Yellow / Red) | Sec 15 | **PASS** | Single source chip |
| **LA-21** | Stage-2 risk elevation (High risk -> Review) | Sec 15 | **PASS** | Routine raised to Review |
| **LA-21b**| Risk raise cooldown (`RISK_RAISE_COOLDOWN_DAYS`) | Sec 15 | **PASS** | Suppressed within 30d |
| **LA-21c**| Ambiguous symptoms without readings | Sec 15 | **PASS** | Pending doctor sign-off |
| **LA-22** | Longitudinal trend escalation (5 check-ins worsening) | Sec 16 | **PASS** | Review triggered + BP chart |
| **LA-23** | Patient-facing risk band display | Sec 15 | **PASS** | Qualitative sentence only |
| **LA-23b**| Section 17 trust & confidence hierarchy | Sec 17 | **PASS** | 5 hierarchies verified |
| **LA-24** | 10-year heart disease model (`chd10_framingham`) | Sec 13.1 | **PASS** | Framingham evaluated |
| **LA-25** | Appointment booking & specialty routing | Sec 15 | **PASS** | Specialties mapped (*PR #145*) |
| **LA-26** | Provider SOAP clinical summary generator | Sec 13.1 | **PASS** | S/O/A/P summary exported |
| **LA-29** | In-app notification center & reminders | Sec 13.2, 15 | **PASS** | Notifications listed (*PR #146*) |
| **LA-30** | Speech synthesis voice output (Meta MMS-TTS Urdu) | Sec 23 | **PASS** | Urdu WAV synthesized (*PR #147*) |
| **LA-27** | Diabetes control model (`diabetes_control_nhanes`) | Sec 13.1 | *Open in PR #142* | Saad draft PR F |
| **LA-28** | Hybrid BM25 + dense retrieval with ChromaDB | Sec 13.2 | *Built in PR #148* | Usman PR G (flagged) |
| **LA-31** | Single-LLM baseline benchmark comparison | Sec 36 | *Built in PR #144* | Usman PR J |
| **LA-32** | Demo-ready seed script & one-command launcher | Sec 35 | *Built in PR #149* | Usman PR R |

---

## 8. Honest Known Limitations & Governance

1. **Research Prototype Status**: ChronicCare AI is an academic university research prototype. It has not undergone randomized clinical trials or medical device conformity assessment. **Doctor review is not clinical validation.**
2. **Engineer-Authored Simulation Labels**: The 52 scenario labels in `tests/sim/personas.json` were authored by engineers. While calibrated to published ACC/AHA and ADA guidelines, they have not been independently validated by a multi-physician panel.
3. **Training Population Shift**: Risk models were trained on US NHANES (1999–2023) and Framingham Heart Study data. They have **not been validated on a Pakistani population**, where type 2 diabetes and premature coronary disease manifest at younger ages and lower BMI thresholds.
4. **Third-Party LLM Dependencies**: Explanation generation relies on external cloud APIs (Groq Cloud). Rate limits (1,000 output tokens/minute) require strict token budgeting and fallback to deterministic templates.
5. **OCR Dataset Sample Size**: Handwritten prescription benchmarking was conducted on 4 sample doctor prescriptions (9 medicines). While RapidOCR achieved 100% medicine recall on this sample, wide handwriting variation necessitates mandatory patient review before saving.
6. **Single Doctor Review**: Clinical review decisions (R1 through R8) reflect consensus from initial doctor review packs. Broad multi-center clinical validation remains an FYP-2 objective.

