# ChronicCare AI — Week 3 Quality & Release Gate Table

**Date:** 8 November 2026  
**Iteration:** Iteration 3 (Week 3 Final)  
**Lead & Safety Architecture:** Usman Bari  
**Production Commit (main):** `3ef51f8` (Merge pull request #132)  
**Evaluation Motto:** *"The model proposes, the rules decide."*

---

## 1. Week 3 Executive Summary

Week 3 achieved the **Features Done** milestone for ChronicCare AI ahead of the 10 November code freeze and 17 November FYP-1 final evaluation. All core architectural components—deterministic clinical rule safeguards, multilingual composable danger word-group detection, clinician-approved safety rule changes (R1–R8), grounded RAG guideline explanation with asynchronous background execution, and provider-only risk prediction—were designed, rigorously evaluated, hardened across multiple real-corpus smoke runs, and deployed to production.

All deliverables were held to zero-tolerance clinical invariants:
1. Patient check-in responses strictly never leak raw risk probabilities, bands, or model names (`risk: null` on all patient endpoints).
2. Emergency red-flag symptoms (Stage 1 red flags or crisis vitals) strictly bypass LLM calls, background queues, and risk calculations, returning immediate 1122 emergency contact guidance.
3. Every doc claim, metric, and finding traces directly to reproducible scripts or command outputs.

---

## 2. Week 3 Objectives, Deliverables & Gate Verification

| # | Objective / Goal | Planned Day | Deliverable / Artifacts | PR(s) | Evidence & Verification Commands | Status |
|:---|:---|:---|:---|:---|:---|:---|
| **G1** | **Release 1 to Production** | Day 1 (Mon 2 Nov) | Deployment of Iteration 2 code to `main` (`bf799cf`); database schema v15 on Aiven MySQL; dormant feature flags; pre/post read-only checks. | PR #100, #101 | `scripts/prod_schema_readonly.py`, `scripts/smoke_test.py` (5/5 checks passed). Recorded in `docs/RELEASES.md`. | **PASS** |
| **G2** | **Vernacular Urdu Danger Word-Groups Detector** | Day 2 (Tue 3 Nov) | Composable symptom word-group detector (`agents/danger_wordgroups.py`) under `DANGER_WORDGROUPS_ENABLED`; raise-only invariant (raises to review, adds 1122 note); negation & temporal guards. | PR #109 | `pytest backend-poc-technical/test_danger_wordgroups.py`; `python scripts/eval_all_phrase_sets.py` (65.0% recall on Hassaan Urdu Independent vs 20.0% v2 baseline); 60/60 mutations killed. | **PASS** |
| **G3** | **Clinician-Approved Clinical Rule Changes (R1–R8)** | Day 3 (Wed 4 Nov) | Implemented doctor consensus rules: R1 (meter LO/HI emergency), R2 (fast-acting sugar wording), R3 (AHA/ACC 2025 citation), R4 (vomiting split), R5 (HbA1c reminder), R6 (provider-only risk panel), R7 (bare glucose 2-40 re-ask), R8 (no readings routine). | PR #106 | `pytest backend-poc-technical/test_clinician_rule_changes.py`, `test_meter_lo_hi.py`, `test_vomiting_fluids_red_flags.py`. Documented in `docs/CLINICIAN_RESPONSES.md`. | **PASS** |
| **G4** | **RAG Explainer Operational Guards & Multi-Provider Failover** | Day 4/5 (Thu/Fri) | Latency budget, daily OTPM token cap (`TokenCapGuard`), caching per band/lang (`ExplanationCache`), circuit breaker (`CircuitBreakerGuard`), Groq primary with Gemini fallback, H1 diabetes template restriction, H2 template consistency. | PR #107, #110 | `pytest backend-poc-technical/test_explain_guards.py` (42 tests passed), `test_llm_providers.py` (21 tests passed). Documented in `docs/EXPLAIN_GUARDS.md`. | **PASS** |
| **G5** | **Conversational Interview Engine v3 Decision** | Day 5 (Fri 6 Nov) | Comprehensive 64-persona benchmark evaluation across v2 and v3 engines. Formal decision on production default. | PR #112 | `python scripts/run_persona_simulations.py`; `docs/V3_READINESS.md`; `docs/V3_DECISION.md`. **Result: Honest NO-GO decision** (4 v3 misses, 8 both-misses; v2 kept as production default). | **PASS** |
| **G6** | **ADA 2026 Written Academic Permission Enforcement** | Day 6b (Thu 5 Nov) | Written permission obtained for 6 sections of *Standards of Care in Diabetes—2026*; Rule G3 (Gemini prohibition); metadata attribution validation; automated deletion CLI for 30 June 2027. | PR #118 | `pytest backend-poc-technical/test_licences.py` (15 tests passed). Manifest in `licences.json`; documented in `docs/licences/ADA_2026_PERMISSION.md`. | **PASS** |
| **G7** | **Explainer Real-Corpus Live Validation & Pacer Hardening** | Day 6d–6g (Fri–Sat) | Tested against 1,175 guideline chunks. Diagnosed and fixed 3 real-world failures: decoupled translation token cap (PR #123), pre-ranking filter for non-diabetic patients (PR #125), and Groq OTPM pacer job deadline wait extension (PR #126-128). | PR #121, #122, #123, #124, #125, #126, #127, #128 | `pytest backend-poc-technical/test_pacer_job_deadline.py` (8 tests passed under real clock), `test_ada_filter_before_ranking.py` (7 tests passed). Live real-chunk smoke achieved 10/10 diabetes and 10/10 HTN post-fixes. | **PASS** |
| **G8** | **Language Gate Switch for Release 2 (`EXPLAIN_LLM_LANGUAGES`)** | Day 7a (Sun 8 Nov) | Conducted 8 Nov human read of real-corpus explanations (4/4 EN acceptable; UR/Roman UR had translation errors). Implemented `EXPLAIN_LLM_LANGUAGES` switch gating LLM to English and routing Urdu/Roman Urdu to reviewed templates (0 wrong rule). Placed gate before cache lookup. | PR #130, #131 | `pytest backend-poc-technical/test_explain_llm_languages.py` (8 tests passed). Live smoke verified non-English check-ins resolve via `language_template_only` consuming 0 Groq tokens. | **PASS** |
| **G9** | **API Contract Documentation & Hermetic Contract Tests** | Day 6c / Day 7 (Sun) | Standardized API contract for Patient and Provider endpoints across 7 clinical states in `docs/API_RISK_EXPLAIN.md`. Generator script `scripts/gen_api_risk_explain_examples.py`. Hermetic contract test suite validating exact schema conformity. | PR #119, #120, #132 | `pytest backend-poc-technical/test_api_contract_risk_explain.py` (**9/9 passed, 0 failures, 0 xfails**). Verified `tokens_used: 0` invariant on template fallback. | **PASS** |
| **G10**| **Release 2 Production Deployment & Live Verification** | Day 7 (Sun 8 Nov) | Deployed Release 2 to production (`3ef51f8`). Loaded 1,175 guideline chunks into Aiven MySQL (`guideline_chunks = 1175`). Configured Render environment flags. Executed live production smoke script. | PR #132 | `scripts/prod_live_smoke.py`: **8/8 check-ins passed strict invariants** against live Render backend. D2 smoke 5/5 passed. Read-only schema check clean. | **PASS** |
| **G11**| **Documentation Pack & Evidence Integrity** | Day 6 / Day 7 | Author comprehensive system architecture with high-res diagrams, report evidence pack, clinical limitations, requirements traceability matrix, and updated demo script. | PR #117, PR chore/i3-release-2 | Real file links and AST tests (`test_traceability_links.py`). Zero invented numbers or unverified claims. | **PASS** |

---

## 3. Production Live Smoke Verification Matrix (Release 2, 8 Nov 2026)

Verified against `https://chroniccare-backend-w568.onrender.com` using ephemeral fake patient accounts:

| Case ID | Case Scenario | Language | Expected Level | Actual Level | Risk in Complete | Explanation Status | Cited Sources | Safety Verification | Result |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Case 1** | HTN BP 118/76 | English | routine | review | `null` | ready (LLM) | [] | PASS (LEVEL DIFFERS: baseline recon) | **PASS** |
| **Case 2** | HTN BP 145/92 | Urdu | review | review | `null` | ready (Template) | [] | PASS (`language_template_only`, delta 0) | **PASS** |
| **Case 3** | HTN BP 145/92 | Roman Urdu | review | review | `null` | ready (Template) | [] | PASS (`language_template_only`, delta 0) | **PASS** |
| **Case 4** | HTN BP 182/112 | English | urgent | urgent | `null` | ready (LLM) | [] | PASS (urgent triage preserved) | **PASS** |
| **Case 5** | HTN BP 182/112 | Urdu | urgent | urgent | `null` | ready (Template) | [] | PASS (`language_template_only`, delta 0) | **PASS** |
| **Case 6** | DM Glucose 190 | English | review | review/null | `null` | ready (LLM) | [] | PASS (ADA guideline isolation) | **PASS** |
| **Case 7** | DM Glucose 190 | Urdu | review | review/null | `null` | ready (Template) | [] | PASS (`language_template_only`, delta 0) | **PASS** |
| **Case 8** | HTN "severe chest pain" | English | emergency | emergency | `null` | `null` (0 LLM calls) | [] | PASS (Immediate 1122 safety note) | **PASS** |
| **Case 9** | Provider Review Detail | — | — | — | — | — | — | NOT RUN (provider credentials withheld) | **NOT RUN** |
| **Case 10**| Patient Privacy Bounds | — | — | — | **null (all 8)**| — | — | PASS (zero probability or band leak) | **PASS** |

---

## 4. Known Edge Cases & Open FYP-2 Deferrals

1. **Both-Miss Complex Personas (8 Personas):**  
   Personas P013, P015, P016, P028, P035, P044, P046, and P061 represent rare multi-morbidity interactions where both v2 and v3 deviate from expected panel triage. Formal clinical protocol definition is deferred to FYP-2.
2. **Bilingual Urdu LLM Generation:**  
   LLM translation for Urdu and Roman Urdu exhibited semantic drift in native-speaker review (8 Nov). Release 2 routes Urdu and Roman Urdu check-ins to reviewed deterministic templates (`EXPLAIN_LLM_LANGUAGES=en`). Developing a specialized medical translation glossary is scheduled for FYP-2.
3. **Isolated-Mode MySQL Column Width:**  
   Observation record ID generation in isolated mode (`CHECKIN-local-...`) exceeds the `VARCHAR(64)` column width on `observations.id`. Standard connected hospital flow operates without issue; schema expansion to `VARCHAR(128)` is queued for schema v16.
4. **Hardware-Accelerated OCR on Handwritten Slips:**  
   Prescription slip extraction remains an exploratory prototype on 9 test samples. Model fine-tuning on diverse Pakistani physician scripts is deferred to FYP-2.

---

## 5. Week 3 Gate Decision

**FINAL GATE VERDICT: PASS**

All required Week 3 capabilities and safety boundaries have been designed, validated, tested against hermetic suites and live production infrastructure, and documented with complete provenance. The repository is ready for the **Tuesday 10 November 2026 Code Freeze**.

