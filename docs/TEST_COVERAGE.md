# Test Coverage Report (Iteration 2 Day 7)

**Generated:** 2026-11-01  
**Target:** Backend test suite statement coverage (`backend-poc-technical`)  
**Suite Invocation:** `python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test" --cov=backend-poc-technical --cov-report=term-missing`  

---

## 1. Overall Coverage Summary

| Metric | Baseline Count | Target / Status |
| --- | --- | --- |
| **Total Statements Evaluated** | 18,468 | Comprehensive backend scope |
| **Statements Missed** | 2,114 | Concentrated in database adapters and error branches |
| **Overall Statement Coverage** | **89%** | Exceeds 80% project quality gate |
| **Total Tests Executed** | 1,353 passed | 5 skipped (external live services), 1 deselected |
| **Frontend Coverage** | **NOT RUN** | `@vitest/coverage-v8` dependency not installed; adding heavy frontend build packages is prohibited |

---

## 2. Top 10 Least-Covered Non-Test Backend Modules

Below are the 10 least-covered production modules in `backend-poc-technical` (excluding test harnesses, mock scenarios, and schema migrations):

| Rank | Module Path | Total Stmts | Missed | Coverage | Key Untested Behaviors (Function & Branch) |
| --- | --- | --- | --- | --- | --- |
| 1 | `backend-poc-technical/rag/query_map.py` | 55 | 29 | **47%** | `map_query_to_section()`: query routing when input does not contain recognized keywords (lines 135–144); empty string fallback (lines 154–175). |
| 2 | `backend-poc-technical/data_sources/local_store.py` | 366 | 171 | **53%** | `get_patient()`: nonexistent patient ID returning `None` (line 125); `list_observations()`: filtering by observation codes when observations list is empty (lines 151–172); query date sorting edge cases (lines 189–246). |
| 3 | `backend-poc-technical/auth/firebase_verify.py` | 94 | 35 | **63%** | `verify_firebase_token()`: expired token exception branch (`ExpiredSignatureError`, lines 53–63); mismatched audience claim (lines 72–93); token header missing key ID (`kid`, line 115). |
| 4 | `backend-poc-technical/data_sources/fhir_client.py` | 218 | 66 | **70%** | `get_patient_observations()`: HTTP error responses from FHIR server (line 58); malformed bundle JSON without `entry` key (lines 99–101); pagination token handling (lines 136–139). |
| 5 | `backend-poc-technical/llm/groq_client.py` | 71 | 19 | **73%** | `generate_completion()`: missing `GROQ_API_KEY` configuration error branch (lines 25–30); API 429 rate limit fallback (line 110); retry backoff timeout (lines 118–126). |
| 6 | `backend-poc-technical/data_sources/medication_scope.py` | 49 | 11 | **78%** | `filter_relevant_medications()`: exclusion of status `entered-in-error` / `cancelled` (lines 73–77); duplicate canonical name suppression (lines 83–85); 8-medication cap truncation (lines 91–93). |
| 7 | `backend-poc-technical/data_sources/db_config.py` | 42 | 9 | **79%** | `get_db_engine()`: unsupported SQL dialect URI parsing error (line 20); remote MySQL connection failure handling (lines 45–49). |
| 8 | `backend-poc-technical/agents/interview_planner.py` | 183 | 37 | **80%** | `plan_next_step()`: dynamic slot exhaustion branch (lines 78–81); fallback probe when all condition slots are satisfied (lines 135–144). |
| 9 | `backend-poc-technical/agents/screening_reminder.py` | 53 | 9 | **83%** | `evaluate_screening_due()`: patient with zero prior tests on record (lines 26–31); custom interval calculation when last test date is in the future (line 90). |
| 10 | `backend-poc-technical/data_sources/fhir_adapter.py` | 208 | 24 | **88%** | `parse_observation()`: blood pressure panel with missing systolic or diastolic sub-component (lines 192–193); unknown LOINC code falling through mapping table (lines 233–236); unmapped unit string fallback (lines 52–64). |

---

## 3. Module-by-Module Statement Coverage (Core Pipeline)

| Category | Module Path | Statements | Missed | Coverage |
| --- | --- | --- | --- | --- |
| **API & Routing** | `backend-poc-technical/main.py` | 1,963 | 207 | 89% |
| **Store & Persistence** | `backend-poc-technical/data_sources/app_store.py` | 871 | 101 | 88% |
| **Store & Persistence** | `backend-poc-technical/data_sources/local_store.py` | 366 | 171 | 53% |
| **Store & Persistence** | `backend-poc-technical/data_sources/db_config.py` | 42 | 9 | 79% |
| **FHIR Integration** | `backend-poc-technical/data_sources/fhir_adapter.py` | 208 | 24 | 88% |
| **FHIR Integration** | `backend-poc-technical/data_sources/fhir_client.py` | 218 | 66 | 70% |
| **FHIR Integration** | `backend-poc-technical/data_sources/medication_scope.py` | 49 | 11 | 78% |
| **Auth & Security** | `backend-poc-technical/auth/firebase_verify.py` | 94 | 35 | 63% |
| **Clinical Reasoning** | `backend-poc-technical/agents/triage_protocol.py` | 217 | 0 | **100%** |
| **Clinical Reasoning** | `backend-poc-technical/agents/input_triage.py` | 124 | 1 | 99% |
| **Clinical Reasoning** | `backend-poc-technical/agents/answer_validation.py` | 65 | 0 | **100%** |
| **Clinical Reasoning** | `backend-poc-technical/agents/trend_agent.py` | 205 | 1 | 99% |
| **Clinical Reasoning** | `backend-poc-technical/agents/risk_agent.py` | 201 | 28 | 86% |
| **Clinical Reasoning** | `backend-poc-technical/agents/risk_rules.py` | 34 | 0 | **100%** |
| **RAG & Explanations** | `backend-poc-technical/rag/explainer.py` | 249 | 37 | 85% |
| **RAG & Explanations** | `backend-poc-technical/rag/query_map.py` | 55 | 29 | 47% |
| **RAG & Explanations** | `backend-poc-technical/rag/retriever.py` | 89 | 0 | **100%** |
| **RAG & Explanations** | `backend-poc-technical/rag/chunking.py` | 89 | 0 | **100%** |

---

## 4. Hardening Plan for Day 7
To improve resilience in non-safety modules, Part B introduces **`backend-poc-technical/test_hardening_coverage.py`** containing $\ge 30$ targeted unit tests:
1. **FHIR Adapter Edge Cases:** Incomplete blood pressure components (systolic present without diastolic), unsupported units, unknown LOINC codes, malformed status.
2. **Medication Scope Filtering:** Inactive medications (`stopped`, `on-hold`, `cancelled`), duplicate entries by active ingredient, strict 8-item cap preservation, alphabetical tie-breaking.
3. **Local Store Robustness:** Negative queries, missing patient lookups, invalid dates, and SQLite session rollback recovery.
4. **Auth Error Paths:** Expired token simulation, audience mismatch, header without `kid`.
5. **Main API HTTP Error Responses:** 404 on missing patient, 403 on tenant ID mismatch, 422 on invalid vital boundaries, 409 on duplicate records.
