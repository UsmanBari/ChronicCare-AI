# ChronicCare AI — Requirements Traceability Matrix

> **Traceability Verification Record (Part U, Week 3)**  
> Traces each core proposal objective (Handbook Part A6) and engineering requirement to its concrete codebase implementation, automated regression test node, and evidentiary documentation.
>
> Automated CI Verification: `backend-poc-technical/test_traceability_links.py` asserts that every file path and test node in this table exists and is valid.

---

| Objective / Requirement | Where Built (File) | Test (file::test_name) | Evidence Doc | Status |
| :--- | :--- | :--- | :--- | :--- |
| Multi-agent, dual-mode reconciliation pipeline with adaptive interview | `backend-poc-technical/agents/reconciliation_agent.py` | `backend-poc-technical/test_adaptive_interview_agent.py::test_conflicting_glucose_is_routed_to_review_with_high_severity` | `docs/REPORT_EVIDENCE.md` | BUILT |
| Clinically structured multi-condition adaptive interview | `backend-poc-technical/agents/adaptive_interview_agent.py` | `backend-poc-technical/test_adaptive_interview_agent.py::test_dual_diagnosis_asks_both_and_keeps_both_intakes` | `docs/INTERVIEW_AUDIT.md` | BUILT |
| Red-flag danger phrase screening with immediate emergency escalation | `backend-poc-technical/agents/input_triage.py` | `backend-poc-technical/test_adaptive_interview_agent.py::test_every_red_flag_phrase_triggers_its_own_category` | `docs/REPORT_EVIDENCE.md` | BUILT |
| Negation and historical cue handling in red-flag screening | `backend-poc-technical/agents/adaptive_interview_agent.py` | `backend-poc-technical/test_adaptive_interview_agent.py::test_negated_red_flag_is_not_flagged` | `docs/DANGER_PHRASE_PLAN.md` | BUILT |
| Composable vernacular Urdu danger word groups detector | `backend-poc-technical/agents/danger_wordgroups.py` | `backend-poc-technical/test_danger_wordgroups.py::test_c1_all_five_groups_detected` | `docs/V3_READINESS.md` | BUILT |
| Two explainable risk classifiers with SHAP (diabetes model only, no SHAP) | `backend-poc-technical/agents/risk_agent.py` | `backend-poc-technical/test_risk_agent.py::test_golden_file_parity_1000_rows` | `docs/RISK_PANEL.md` | PENDING |
| Verification step checking reconciliation trust and clinical severity | `backend-poc-technical/agents/verification_agent.py` | `backend-poc-technical/test_adaptive_interview_agent.py::test_agreeing_checkin_is_auto_resolved` | `docs/REPORT_EVIDENCE.md` | BUILT |
| Grounding and safety guardrails for clinical explanations | `backend-poc-technical/rag/explain_guards.py` | `backend-poc-technical/test_explain_guards.py::test_c1_budget_timeout_falls_back_under_budget` | `docs/EXPLAIN_GUARDS.md` | BUILT |
| Plain-language explanations in English and Urdu | `backend-poc-technical/rag/templates.json` | `backend-poc-technical/test_explain_background.py::test_o1_explain_mode_default_and_routing` | `docs/EXPLAIN_EVAL.md` | BUILT |
| Dual-mode data retrieval: EHR FHIR sandbox vs local-store fallback | `backend-poc-technical/data_sources/fhir_client.py` | `backend-poc-technical/test_fhir.py::test_connectivity_and_save_evidence` | `docs/EHR_SANDBOX.md` | BUILT |
| Isolated offline operation with local SQLite database store | `backend-poc-technical/data_sources/local_store.py` | `backend-poc-technical/test_adaptive_interview_agent.py::test_isolated_mode_pipeline_works_with_the_local_source` | `docs/ARCHITECTURE.md` | BUILT |
| Longitudinal trend evaluation across historical check-ins | `backend-poc-technical/agents/trend_agent.py` | `backend-poc-technical/test_trend_agent.py::test_clear_directions_for_all_types` | `docs/TREND_AGENT.md` | BUILT |
| Active medication confirmation protocol | `backend-poc-technical/agents/medication_confirmation.py` | `backend-poc-technical/test_medication_confirmation.py::test_only_active_medications_are_asked_in_record_order` | `docs/CLINICAL_RULES.md` | BUILT |
| Provider-only review queue with audit-safe event logging | `backend-poc-technical/main.py` | `backend-poc-technical/test_checkin_triage.py::test_l_emergency_escalated_audit_row_holds_category_only` | `docs/API_RISK_EXPLAIN.md` | BUILT |
| LangGraph orchestrator equivalent to direct execution | `backend-poc-technical/orchestrator/graph.py` | `backend-poc-technical/test_orchestrator_equivalence.py::test_representative_scenarios_equivalence` | `docs/ORCHESTRATOR.md` | BUILT |
| Falsifiable safety evidence via automated mutation proofs | `scripts/verify_mutations.py` | `backend-poc-technical/test_mutation_runner.py::test_mutation_runner_executes_and_kills_in_ci` | `docs/REPORT_EVIDENCE.md` | BUILT |
| Multilingual Roman Urdu and Urdu script user interface | `app/translations/index.ts` | `backend-poc-technical/test_meter_lo_hi.py::test_detect_meter_lo_hi_roman_urdu` | `docs/ROMAN_URDU_GLOSSARY.md` | BUILT |
| Server-side prescription and lab OCR pipeline | `backend-poc-technical/main.py` | `backend-poc-technical/test_ocr_upload.py::test_ocr_disabled_by_default_returns_503` | `docs/OCR_DESIGN.md` | PENDING |
| Single-LLM baseline ablation benchmark (RQ3) | `docs/tasks/WEEK3_USMAN.md` | `backend-poc-technical/test_engine_equivalence.py::test_engine_equivalence_scenarios` | `docs/LIMITATIONS.md` | CUT |
| Real-patient clinical evaluation pilot in Pakistani cohort (RQ1-4) | `docs/tasks/WEEK3_USMAN.md` | `backend-poc-technical/test_clinical_rules_doc.py::test_all_clinical_constants_documented_in_rules_register` | `docs/LIMITATIONS.md` | CUT |

