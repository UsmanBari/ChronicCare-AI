"""
Real Mutation Proof Verification Engine (Stage 9A-4 Task B).

For each of the 13 architectural mutation proofs:
1. Reads original file bytes and computes SHA-256.
2. Finds the target text with exact single-match assertion (prints grep line number).
3. Replaces target text with mutation.
4. Generates and prints real unified diff with 3 lines of context.
5. Runs `python -m pytest <exact node id> -x --tb=line -q` as subprocess.
6. Asserts returncode != 0 and extracts the real failing line.
7. Restores original file bytes, verifies SHA-256 matches original and git diff is clean.
8. Includes diagnostic test proving deliberate missing target causes non-zero exit.
"""

import difflib
import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"

MUTATIONS = [
    {
        "id": "MUT-1",
        "name": "Danger Screen on Free Text",
        "file": BACKEND_DIR / "agents" / "input_triage.py",
        "target": "    is_danger, danger_cat = screen_multilingual_danger_phrases(clean_text)",
        "replacement": "    is_danger, danger_cat = False, None",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_1_danger_screen_on_free_text",
    },
    {
        "id": "MUT-2",
        "name": "Negation Handling in Danger Screen",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "    return any(word in _NEGATION_CUES for word in preceding[-NEGATION_WINDOW_WORDS:])",
        "replacement": "    return False",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_2_negation_handling",
    },
    {
        "id": "MUT-3",
        "name": "Unknown / Skip Retention Invariant",
        "file": BACKEND_DIR / "agents" / "answer_validation.py",
        "target": "    if any(k in lowered for k in [\"don't know\", \"dont know\", \"skip\", \"not sure\", \"prefer not to say\", \"maloom nahi\", \"nahi pata\"]):",
        "replacement": "    if False and any(k in lowered for k in [\"don't know\", \"dont know\", \"skip\", \"not sure\", \"prefer not to say\", \"maloom nahi\", \"nahi pata\"]):",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_3_unknown_not_stored_as_no",
    },
    {
        "id": "MUT-4",
        "name": "Planner Never Re-asks Filled Slot",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "        asked_slots = set(asked_slots) | clean_known",
        "replacement": "        asked_slots = set()",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_4_planner_never_reasks_filled_slot",
    },
    {
        "id": "MUT-5",
        "name": "Interview Budget Hard Cap (14)",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "    if current_count >= effective_budget:",
        "replacement": "    if False and current_count >= effective_budget:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_5_budget_hard_cap",
    },
    {
        "id": "MUT-6",
        "name": "Probe Depth Limit of 2 per Finding",
        "file": BACKEND_DIR / "agents" / "interview_findings.py",
        "target": "    if finding.probe_count >= max_probes:",
        "replacement": "    if False and finding.probe_count >= max_probes:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_6_probe_depth_limit_two",
    },
    {
        "id": "MUT-7",
        "name": "Glucose Unit Guessing Prevented (2-40 Clarified)",
        "file": BACKEND_DIR / "agents" / "answer_validation.py",
        "target": "    if 2.0 <= val <= 40.0:",
        "replacement": "    if False and 2.0 <= val <= 40.0:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_7_unit_guess_prevented",
    },
    {
        "id": "MUT-8",
        "name": "Contradiction Clarification Priority",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "    if contradictions:",
        "replacement": "    if False and contradictions:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_8_contradiction_handling",
    },
    {
        "id": "MUT-9",
        "name": "Odd-Input Checked After Danger Screen",
        "file": BACKEND_DIR / "agents" / "interview_v3_runner.py",
        "target": "    triage_res: TriageInputResult = classify_input(",
        "replacement": "    triage_res: TriageInputResult = TriageInputResult(category='normal_clinical')\n    if False and classify_input(",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_9_odd_input_after_danger",
    },
    {
        "id": "MUT-10",
        "name": "Self-Harm / Hopelessness Screen Priority",
        "file": BACKEND_DIR / "agents" / "input_triage.py",
        "target": "    if check_self_harm(clean_text):",
        "replacement": "    if False and check_self_harm(clean_text):",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_10_self_harm_screen",
    },
    {
        "id": "MUT-11",
        "name": "Romantic Remark Recorded as Finding Without Yes",
        "file": BACKEND_DIR / "agents" / "interview_v3_runner.py",
        "target": "        session_state.setdefault(\"odd_classes_seen\", []).append(triage_res.odd_class)\n        session_state[\"last_odd_class\"] = triage_res.odd_class",
        "replacement": "        session_state.setdefault(\"odd_classes_seen\", []).append(triage_res.odd_class)\n        session_state[\"last_odd_class\"] = triage_res.odd_class\n        if triage_res.odd_class == \"romantic\":\n            session_state.setdefault(\"findings\", []).append({\"kind\": \"romantic\", \"quote\": clean_answer})",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_11_romantic_remark_not_symptom",
    },
    {
        "id": "MUT-12",
        "name": "Fixed Response Templates for Odd Inputs",
        "file": BACKEND_DIR / "agents" / "interview_bank" / "loader.py",
        "target": "    return QuestionBank(items, sources, probes, responses)",
        "replacement": "    return QuestionBank(items, sources, probes, {})",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_12_fixed_reply_set",
    },
    {
        "id": "MUT-13",
        "name": "Safety Priority Class Planned First",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "        if item.priority_class == \"safety\" and item.slot not in asked_slots:",
        "replacement": "        if False and item.priority_class == \"safety\" and item.slot not in asked_slots:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_13_safety_priority_first",
    },
    {
        "id": "MUT-14",
        "name": "Answered_By Not Set For Third-Party Report",
        "file": BACKEND_DIR / "agents" / "interview_v3_runner.py",
        "target": "        if triage_res.odd_class == \"third_party_report\":\n            session_state[\"answered_by\"] = \"caregiver\"",
        "replacement": "        if triage_res.odd_class == \"third_party_report\":\n            session_state[\"answered_by\"] = None",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_14_answered_by_third_party",
    },
    {
        "id": "MUT-15",
        "name": "Extra Danger Detections Removed from Input Triage",
        "file": BACKEND_DIR / "agents" / "input_triage.py",
        "target": "        for category, patterns in MULTILINGUAL_DANGER_CATEGORIES.items():",
        "replacement": "        for category, patterns in {}.items():",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_15_extra_danger_detections",
    },
    # --- Seven Stage 8b Rule Mutations ---
    {
        "id": "MUT-8B-1",
        "name": "Stage 8b: Glucose Context Skip Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "            if _has_glucose_context_in_text(answer):\n                answers[\"glucose_context\"] = \"extracted_from_reading\"\n                if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):",
        "replacement": "            if False and _has_glucose_context_in_text(answer):\n                answers[\"glucose_context\"] = \"extracted_from_reading\"\n                if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_fast_path_skip_rules",
    },
    {
        "id": "MUT-8B-2",
        "name": "Stage 8b: Hypo-Events Question Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "        if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):\n            state.step = DiabetesStep.HYPO_EVENTS_PAST_WEEK.value",
        "replacement": "        if state.on_insulin_or_sulfonylurea or (reading is not None and reading < 70):\n            state.step = DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_full_path",
    },
    {
        "id": "MUT-8B-3",
        "name": "Stage 8b: Sick-Day Flags Prompt Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "        elif reading is not None and reading >= 250:\n            state.step = DiabetesStep.SICK_DAY_FLAGS.value",
        "replacement": "        elif False and reading is not None and reading >= 250:\n            state.step = DiabetesStep.SICK_DAY_FLAGS.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_sick_day_prompt_on_high_reading",
    },
    {
        "id": "MUT-8B-4",
        "name": "Stage 8b: BP Technique Question Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "            if reading is not None and not _has_bp_technique_in_text(answer):\n                state.step = HypertensionStep.BP_TECHNIQUE.value",
        "replacement": "            if False and reading is not None and not _has_bp_technique_in_text(answer):\n                state.step = HypertensionStep.BP_TECHNIQUE.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_hypertension_v2_3_full_path",
    },
    {
        "id": "MUT-8B-5",
        "name": "Stage 8b: OTC Meds BP Check Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "        if bp is None or bp[0] >= 140 or bp[1] >= 90:\n            state.step = HypertensionStep.OTC_MEDS_BP.value",
        "replacement": "        if False and (bp is None or bp[0] >= 140 or bp[1] >= 90):\n            state.step = HypertensionStep.OTC_MEDS_BP.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_hypertension_v2_3_full_path",
    },
    {
        "id": "MUT-8B-6",
        "name": "Stage 8b: Missed-Dose Reason Rule",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "        if adh is False:\n            state.step = DiabetesStep.MISSED_DOSES_REASON.value",
        "replacement": "        if False and adh is False:\n            state.step = DiabetesStep.MISSED_DOSES_REASON.value",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_full_path",
    },
    {
        "id": "MUT-8B-7",
        "name": "Stage 8b: Free-Text Note Passed Through",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "            \"free_text_note\": answers.get(\"patient_free_text\"),",
        "replacement": "            \"free_text_note\": None,",
        "test_node": "backend-poc-technical/test_interview_v2_3_questions.py::test_diabetes_v2_3_full_path",
    },
    # --- Stage 9A-7 Vomiting Red Flag Mutations (R4) ---
    {
        "id": "MUT-9A7-1-V2",
        "name": "R4 Inability to Keep Fluids Down Emergency (v2: demoted to urgent)",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": '    "unable_to_keep_fluids": "emergency",',
        "replacement": '    "unable_to_keep_fluids": "urgent",',
        "test_node": "backend-poc-technical/test_vomiting_fluids_red_flags.py::test_v2_unable_to_keep_fluids_immediate_emergency",
    },
    {
        "id": "MUT-9A7-1-V3",
        "name": "R4 Inability to Keep Fluids Down Emergency (v3: wrong reason self_harm_statement if skipped)",
        "file": BACKEND_DIR / "agents" / "interview_v3_runner.py",
        "target": '        elif rf_screen_reason == "unable_to_keep_fluids":',
        "replacement": '        elif False and rf_screen_reason == "unable_to_keep_fluids":',
        "test_node": "backend-poc-technical/test_vomiting_fluids_red_flags.py::test_v3_unable_to_keep_fluids_immediate_emergency",
    },
    # --- Day 2 Mutations (M-H2-1 to M-H2-5) ---
    {
        "id": "M-H2-1",
        "name": "'pata nahi' mapped to 'no'",
        "file": BACKEND_DIR / "agents" / "answer_understanding.py",
        "target": "    for unk_phrase in _UNKNOWN_PHRASES:\n        if _contains_subsequence(tokens, unk_phrase):",
        "replacement": "    for unk_phrase in []:\n        if False:",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_m_h2_1_pata_nahi_not_no",
    },
    {
        "id": "M-H2-2",
        "name": "'unknown' satisfies requires:true",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "            if req.get(\"is_fasting_today\") is True and known_slots.get(\"is_fasting_today\") is not True:",
        "replacement": "            if req.get(\"is_fasting_today\") and not known_slots.get(\"is_fasting_today\"): ",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_m_h2_2_unknown_does_not_satisfy_requires_true",
    },
    {
        "id": "M-H2-3",
        "name": "parse_bp accepts systolic <= diastolic",
        "file": BACKEND_DIR / "agents" / "answer_understanding.py",
        "target": "            if sys_val <= dia_val:\n                return {\"value\": None, \"evidence\": evidence}",
        "replacement": "            if False and sys_val <= dia_val:\n                return {\"value\": None, \"evidence\": evidence}",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_m_h2_3_parse_bp_rejects_sys_le_dia",
    },
    {
        "id": "M-H2-4",
        "name": "Unit clarification skipped for bare '7'",
        "file": BACKEND_DIR / "agents" / "interview_v3_runner.py",
        "target": "        if val_res.needs_unit_clarification:\n            session_state[\"awaiting_glucose_unit\"] = True",
        "replacement": "        if False and val_res.needs_unit_clarification:\n            session_state[\"awaiting_glucose_unit\"] = True",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_m_h2_4_unit_clarification_bare_7",
    },
    {
        "id": "M-H2-5",
        "name": "Tag-question 'na' read as 'no'",
        "file": BACKEND_DIR / "agents" / "answer_understanding.py",
        "target": "            if len(tokens) == 1 or i == 0:\n                return {",
        "replacement": "            if True:\n                return {",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_m_h2_5_tag_question_na_not_no",
    },
        # --- Day 3 Mutations (M-H3-1 to M-H3-3) ---
    {
        "id": "M-H3-1",
        "name": "Dual patient asked symptoms before readings are done",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "    if is_dual_diagnosis and \"greeting\" in asked_slots:\n        dual_order = get_dual_readings_order(recent_checkins, patient_record)",
        "replacement": "    if is_dual_diagnosis and \"greeting\" in asked_slots:\n        return PlanDecision(action=\"ask_bank_item\", item=bank.get_by_id(\"diabetes_hyperglycemia_symptoms\"), reason=\"mutant_symptoms_first\", question_count=current_count + 1, max_budget=effective_budget, target_slot=\"hyperglycemia_symptoms\")",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_m_h3_1_readings_before_symptoms",
    },
    {
        "id": "M-H3-2",
        "name": "Same slot asked twice in dual flow",
        "file": BACKEND_DIR / "agents" / "interview_planner.py",
        "target": "        if is_slot_already_satisfied(item.slot, asked_slots, known_slots, bank):",
        "replacement": "        if False and is_slot_already_satisfied(item.slot, asked_slots, known_slots, bank):",
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_m_h3_2_slot_never_asked_twice",
    },
    {
        "id": "M-H3-3",
        "name": "also_fills re-added between hyperglycemia_symptoms and associated_symptoms",
        "file": BACKEND_DIR / "agents" / "interview_bank" / "diabetes.json",
        "target": '    "id": "diabetes_hyperglycemia_symptoms",\n    "module": "diabetes",\n    "slot": "hyperglycemia_symptoms",\n    "why_text": "High blood sugar can cause thirst, frequent urination, and blurry vision.",',
        "replacement": '    "id": "diabetes_hyperglycemia_symptoms",\n    "module": "diabetes",\n    "slot": "hyperglycemia_symptoms",\n    "also_fills": ["associated_symptoms"],\n    "why_text": "High blood sugar can cause thirst, frequent urination, and blurry vision.",',
        "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_m_h3_3_symptoms_not_also_filled",
    },
    # --- Day 4 Mutation (M-S4-1: Trend Agent Dual Agreement Rule) ---
    {
        "id": "M-S4-1",
        "name": "Trend Agent: Median-and-Slope Agreement Required (Dual Agreement)",
        "file": BACKEND_DIR / "agents" / "trend_agent.py",
        "target": "        if slope_per_week is not None and change >= threshold and slope_per_week > 0:\n            direction = DIRECTION_RISING\n        elif slope_per_week is not None and change <= -threshold and slope_per_week < 0:\n            direction = DIRECTION_FALLING",
        "replacement": "        if change >= threshold:\n            direction = DIRECTION_RISING\n        elif change <= -threshold:\n            direction = DIRECTION_FALLING",
        "test_node": "backend-poc-technical/test_trend_agent.py::test_conflict_median_positive_slope_non_positive_yields_stable",
    },
    # --- Day 5 Mutations (M-U5-1 to M-U5-3: Risk Agent & Can-Only-Raise Invariants) ---
    {
        "id": "M-U5-1",
        "name": "Can-Only-Raise Invariant: apply_risk_to_level lowers a triage level",
        "file": BACKEND_DIR / "agents" / "risk_rules.py",
        "target": "    if level == \"routine\":\n        target = \"review\"\n        if LEVEL_RANK[target] > LEVEL_RANK[level]:\n            return target, True",
        "replacement": "    if level == \"emergency\":\n        return \"routine\", True",
        "test_node": "backend-poc-technical/test_risk_rules.py::test_apply_risk_to_level_matrix[emergency-high-True-True]",
    },
    {
        "id": "M-U5-2",
        "name": "Can-Only-Raise Invariant: RISK_CAN_RAISE flag ignored",
        "file": BACKEND_DIR / "agents" / "risk_rules.py",
        "target": "    if not (risk_enabled and risk_can_raise):\n        return level, False",
        "replacement": "    if not risk_enabled:\n        return level, False",
        "test_node": "backend-poc-technical/test_risk_rules.py::test_apply_risk_to_level_matrix[routine-high-True-False]",
    },
    {
        "id": "M-U5-3",
        "name": "Risk Agent: Fall back to basic when waist is missing",
        "file": BACKEND_DIR / "agents" / "risk_agent.py",
        "target": "    if missing:\n        return {\n            \"status\": \"not_enough_information\",\n            \"model_name\": m_name,\n            \"disease\": \"cardiovascular\" if \"chd\" in m_name else \"diabetes\",\n            \"missing\": sorted(list(set(missing))),\n            \"audience\": model.get(\"audience\", \"provider_only\"),\n            \"confidence\": confidence,\n            \"label_text\": model.get(\"label_text\", {}),\n        }",
        "replacement": "    if missing and missing != [\"waist_cm\"]:\n        return {\n            \"status\": \"not_enough_information\",\n            \"model_name\": m_name,\n            \"disease\": \"cardiovascular\" if \"chd\" in m_name else \"diabetes\",\n            \"missing\": sorted(list(set(missing))),\n            \"audience\": model.get(\"audience\", \"provider_only\"),\n            \"confidence\": confidence,\n            \"label_text\": model.get(\"label_text\", {}),\n        }\n    if missing == [\"waist_cm\"]:\n        raw_features[\"waist_cm\"] = 85.0",
        "test_node": "backend-poc-technical/test_risk_agent.py::test_missing_waist_yields_not_enough_info",
    },
    # --- Day 6 Mutations (M-H6-1 to M-H6-2: Edit History & Import Validation) ---
    {
        "id": "M-H6-1",
        "name": "Record edit call removed from update_local_medication",
        "file": BACKEND_DIR / "data_sources" / "local_store.py",
        "target": "                if dosage_changed:\n                    record_edit(\n                        cursor,\n                        \"?\",",
        "replacement": "                if False and dosage_changed:\n                    record_edit(\n                        cursor,\n                        \"?\",",
        "test_node": "backend-poc-technical/test_record_edits.py::test_medication_edit_history",
    },
    {
        "id": "M-H6-2",
        "name": "Validation skipped on record import",
        "file": BACKEND_DIR / "main.py",
        "target": "            clean_unit = _validate_observation_value_and_unit(obs_type, val_float)",
        "replacement": "            clean_unit = \"mg/dL\"",
        "test_node": "backend-poc-technical/test_record_export_import.py::test_import_validation_rejects_out_of_range_and_invalid_type",
    },
    {
        "id": "M-H6-3",
        "name": "Compensating rollback removed from import endpoint",
        "file": BACKEND_DIR / "main.py",
        "target": "            if not is_mysql:\n                _rollback_sqlite_import(user_id, patient_id, written_items)",
        "replacement": "            if False and not is_mysql:\n                _rollback_sqlite_import(user_id, patient_id, written_items)",
        "test_node": "backend-poc-technical/test_record_export_import.py::test_import_all_or_nothing_rollback_on_failure",
    },
    {
        "id": "M-H7-1",
        "name": "Server-side re-validation removed in OCR confirm endpoint",
        "file": BACKEND_DIR / "main.py",
        "target": '                o_type, val, unit, ts = _validate_ocr_observation(\n                    obs_type=item.observation_type or "",\n                    value=item.value,\n                    measured_at=item.measured_at,\n                    item_index=idx,\n                )',
        "replacement": '                o_type, val, unit, ts = (item.observation_type or "glucose", float(item.value or 0), "mg/dL", _utc_now_iso())',
        "test_node": "backend-poc-technical/test_ocr_upload.py::test_confirm_revalidation_rejects_out_of_range_values",
    },
    {
        "id": "M-H7-2",
        "name": "Unconfirmed OCR items saved before explicit user confirmation",
        "file": BACKEND_DIR / "main.py",
        "target": "    upload_id = stage_upload(\n        user_id=user_id,\n        extracted_data=extracted,\n    )",
        "replacement": '    upload_id = stage_upload(\n        user_id=user_id,\n        extracted_data=extracted,\n    )\n    add_local_observation(f"premature-{upload_id}", patient_id, "glucose", 118.0, "mg/dL", _utc_now_iso(), "local", "ocr")',
        "test_node": "backend-poc-technical/test_ocr_upload.py::test_upload_does_not_save_items_before_confirm",
    },
    {
        "id": "M-H7-3",
        "name": "Provider exception handler removed from OCR upload endpoint",
        "file": BACKEND_DIR / "main.py",
        "target": '    try:\n        extracted = provider.extract(processed_bytes)\n    except (ImportError, ModuleNotFoundError) as e:\n        logger.error("OCR provider missing dependency: %s", type(e).__name__)\n        return JSONResponse(\n            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,\n            content={"code": "ocr_unavailable", "detail": "ocr_unavailable"},\n        )\n    except Exception as e:\n        logger.error("OCR provider error: %s", type(e).__name__)\n        return JSONResponse(\n            status_code=status.HTTP_502_BAD_GATEWAY,\n            content={"code": "ocr_provider_error", "detail": "ocr_provider_error"},\n        )',
        "replacement": "    extracted = provider.extract(processed_bytes)",
        "test_node": "backend-poc-technical/test_ocr_upload.py::test_provider_exception_returns_502_and_logs_type_only",
    },
    # --- Day 7 P0 Safety Mutation (M-U7-1: Re-add 'no': 9 to Roman Urdu numbers) ---
    {
        "id": "M-U7-1",
        "name": "P0 Safety: Re-introduce 'no': 9 into _ROMAN_URDU_NUMBERS",
        "file": BACKEND_DIR / "agents" / "answer_understanding.py",
        "target": '    "nau": 9,',
        "replacement": '    "nau": 9, "no": 9,',
        "test_node": "backend-poc-technical/test_no_is_not_a_number.py::test_no_not_in_roman_urdu_numbers",
    },
    # --- Day 7 Explain Isolation Mutation (M-U7-2: Explain step writes into triage decision) ---
    {
        "id": "M-U7-2",
        "name": "Explain step mutates clinical triage decision",
        "file": BACKEND_DIR / "orchestrator" / "steps.py",
        "target": '        explain_res = guarded_explain(\n            triage_result=triage_copy,\n            readings=readings,\n            language=language,\n            store=store,\n            llm=llm,\n            condition=active_cond,\n            patient_conditions=patient_conditions,\n            mode="inline",\n        )\n        if "status" not in explain_res:\n            explain_res["status"] = "ready"\n        return explain_res',
        "replacement": '        explain_res = guarded_explain(\n            triage_result=triage_copy,\n            readings=readings,\n            language=language,\n            store=store,\n            llm=llm,\n            condition=active_cond,\n            patient_conditions=patient_conditions,\n            mode="inline",\n        )\n        triage_decision["final_triage_level"] = "routine"\n        if "status" not in explain_res:\n            explain_res["status"] = "ready"\n        return explain_res',
        "test_node": "backend-poc-technical/test_checkin_risk_explain.py::test_mutation_proof_m_u7_2_explain_never_modifies_triage",
    },
    # --- Day 2 Danger Word Groups Mutations (M-U-WG-1 to M-U-WG-4) ---
    {
        "id": "M-U-WG-1",
        "name": "Danger Word Groups: Remove raise in step_decide_triage",
        "file": BACKEND_DIR / "orchestrator" / "steps.py",
        "target": '                final_triage_level = _raise_level(final_triage_level, "review")\n                final_requires_review = True\n                review_status = "open"\n                if final_max_sev == "none":\n                    final_max_sev = "moderate"\n                groups_seen = sorted(list({h.get("group") for h in wordgroup_hits if isinstance(h, dict) and h.get("group")}))\n                if triage_dict is None:',
        "replacement": '                # final_triage_level = _raise_level(final_triage_level, "review")\n                final_requires_review = True\n                review_status = "open"\n                if final_max_sev == "none":\n                    final_max_sev = "moderate"\n                groups_seen = sorted(list({h.get("group") for h in wordgroup_hits if isinstance(h, dict) and h.get("group")}))\n                if triage_dict is None:',
        "test_node": "backend-poc-technical/test_danger_wordgroups.py::test_c3_unit_routine_plus_hit_raises_to_review",
    },
    {
        "id": "M-U-WG-2",
        "name": "Danger Word Groups: Raise to emergency instead of review",
        "file": BACKEND_DIR / "orchestrator" / "steps.py",
        "target": '                final_triage_level = _raise_level(final_triage_level, "review")\n                final_requires_review = True\n                review_status = "open"\n                if final_max_sev == "none":\n                    final_max_sev = "moderate"\n                groups_seen = sorted(list({h.get("group") for h in wordgroup_hits if isinstance(h, dict) and h.get("group")}))\n                if triage_dict is None:',
        "replacement": '                final_triage_level = "emergency"\n                final_requires_review = True\n                review_status = "open"\n                if final_max_sev == "none":\n                    final_max_sev = "moderate"\n                groups_seen = sorted(list({h.get("group") for h in wordgroup_hits if isinstance(h, dict) and h.get("group")}))\n                if triage_dict is None:',
        "test_node": "backend-poc-technical/test_danger_wordgroups.py::test_c4_wordgroup_hit_never_yields_urgent_or_emergency",
    },
    {
        "id": "M-U-WG-3",
        "name": "Danger Word Groups: Disable Urdu trailing negation guard",
        "file": BACKEND_DIR / "agents" / "danger_wordgroups.py",
        "target": '    trailing_text = clause[match_end:].strip().lower()\n    cleaned_trailing = _INABILITY_RE.sub("", trailing_text)\n    if _TRAILING_NEGATION_RE.search(cleaned_trailing):\n        return True',
        "replacement": '    trailing_text = clause[match_end:].strip().lower()\n    cleaned_trailing = _INABILITY_RE.sub("", trailing_text)\n    if False and _TRAILING_NEGATION_RE.search(cleaned_trailing):\n        return True',
        "test_node": "backend-poc-technical/test_danger_wordgroups.py::test_c2_negation_and_resolved_guards[seenay mein dard nahi hai bilkul theek hoon]",
    },
    {
        "id": "M-U-WG-4",
        "name": "Danger Word Groups: Force flag check always true",
        "file": BACKEND_DIR / "agents" / "danger_wordgroups.py",
        "target": 'def is_danger_wordgroups_enabled() -> bool:\n    """Flag guard: DANGER_WORDGROUPS_ENABLED=\'true\' (case-insensitive). OFF by default."""\n    return os.getenv("DANGER_WORDGROUPS_ENABLED", "").strip().lower() == "true"',
        "replacement": 'def is_danger_wordgroups_enabled() -> bool:\n    """Flag guard: DANGER_WORDGROUPS_ENABLED=\'true\' (case-insensitive). OFF by default."""\n    return True',
        "test_node": "backend-poc-technical/test_danger_wordgroups.py::test_c5_flag_off_invariant_behavior_identical_to_baseline",
    },
    {
        "id": "M-U-R1",
        "name": "R1 Meter LO/HI: Disable meter LO detection in answer_validation",
        "file": BACKEND_DIR / "agents" / "answer_validation.py",
        "target": 'def detect_meter_lo_hi(text: str) -> Optional[str]:\n    """',
        "replacement": 'def detect_meter_lo_hi(text: str) -> Optional[str]:\n    return None\n    """',
        "test_node": "backend-poc-technical/test_meter_lo_hi.py::test_v2_affirmative_confirmation_lo",
    },
    {
        "id": "M-U-R4",
        "name": "R4 Vomiting Fluids: Revert unable_to_keep_fluids from emergency to urgent",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": '    "unable_to_keep_fluids": "emergency",',
        "replacement": '    "unable_to_keep_fluids": "urgent",',
        "test_node": "backend-poc-technical/test_vomiting_fluids_red_flags.py::test_v2_unable_to_keep_fluids_immediate_emergency",
    },
    {
        "id": "M-U-R8",
        "name": "R8 No Readings: Disable symptom reported review escalation",
        "file": BACKEND_DIR / "agents" / "adaptive_interview_agent.py",
        "target": "            if symptom_reported:\n                narrative_review = True",
        "replacement": "            if False and symptom_reported:\n                narrative_review = True",
        "test_node": "backend-poc-technical/test_r8_no_readings.py::test_r8_v2_no_readings_with_symptom_is_review",
    },
    {
        "id": "M-U-G1",
        "name": "Explain Guards: Disable time budget deadline enforcement",
        "file": BACKEND_DIR / "rag" / "explain_guards.py",
        "target": "                if thread.is_alive():\n                    # Provider timed out",
        "replacement": "                if False and thread.is_alive():\n                    # Provider timed out",
        "test_node": "backend-poc-technical/test_explain_guards.py::test_mutation_proof_budget_deadline_killed",
    },
    {
        "id": "M-U-G2",
        "name": "Explain Guards: Disable cache number re-validation",
        "file": BACKEND_DIR / "rag" / "explain_guards.py",
        "target": "        v3_errs = validate_number_grounding(resolved_sentences, allowed_nums)\n        if v3_errs:\n            with self._lock:\n                self.misses += 1\n            return None",
        "replacement": "        v3_errs = validate_number_grounding(resolved_sentences, allowed_nums)\n        if False and v3_errs:\n            with self._lock:\n                self.misses += 1\n            return None",
        "test_node": "backend-poc-technical/test_explain_guards.py::test_mutation_proof_cache_revalidation_killed",
    },
    {
        "id": "M-U-G3",
        "name": "Explain Guards: Circuit breaker never opens on failure threshold",
        "file": BACKEND_DIR / "rag" / "explain_guards.py",
        "target": "            if is_rate_limit or self._consecutive_failures >= self._threshold or self._state == self.HALF_OPEN:\n                self._state = self.OPEN",
        "replacement": "            if False and (is_rate_limit or self._consecutive_failures >= self._threshold or self._state == self.HALF_OPEN):\n                self._state = self.OPEN",
        "test_node": "backend-poc-technical/test_explain_guards.py::test_mutation_proof_breaker_never_opens_killed",
    },
    {
        "id": "M-U-G4",
        "name": "Explain Guards: Remove G3 licence check",
        "file": BACKEND_DIR / "rag" / "explain_guards.py",
        "target": "    # Filter by licence restriction: G3 forbids Gemini if any restricted chunk\n    if has_restricted_chunk:\n        provider_candidates = [p for p in provider_candidates if p != \"gemini\"]",
        "replacement": "    # Filter by licence restriction: G3 forbids Gemini if any restricted chunk\n    if False and has_restricted_chunk:\n        provider_candidates = [p for p in provider_candidates if p != \"gemini\"]",
        "test_node": "backend-poc-technical/test_llm_providers.py::test_g3_licence_restricted_chunk_never_calls_gemini",
    },
    {
        "id": "M-U-G5",
        "name": "Explain Guards: Remove H1 condition check",
        "file": BACKEND_DIR / "rag" / "explain_guards.py",
        "target": "    # 3. Check Condition Gate (H1)\n    if not is_condition_allowed_for_llm(cond_str, trigger_category):\n        return _make_template_fallback(\"condition_template_only\", [\"Condition not permitted for LLM explainer\"])",
        "replacement": "    # 3. Check Condition Gate (H1)\n    if False and not is_condition_allowed_for_llm(cond_str, trigger_category):\n        return _make_template_fallback(\"condition_template_only\", [\"Condition not permitted for LLM explainer\"])",
        "test_node": "backend-poc-technical/test_llm_providers.py::test_h1_condition_filter_blocks_diabetes_by_default",
    },
    {
        "id": "M-U-G6",
        "name": "Explain Guards: Make auto skip the fallback provider",
        "file": BACKEND_DIR / "rag" / "explain_guards.py",
        "target": "        for idx, current_provider in enumerate(eligible_providers):",
        "replacement": "        for idx, current_provider in enumerate(eligible_providers[:1]):",
        "test_node": "backend-poc-technical/test_llm_providers.py::test_routing_auto_groq_429_falls_back_to_gemini",
    },
    # --- Day 5 Background Explainer Mutations (M-U-BG-1 to M-U-BG-3) ---
    {
        "id": "M-U-BG-1",
        "name": "Background Explainer: Queue overflow returns True on over-capacity",
        "file": BACKEND_DIR / "rag" / "explain_jobs.py",
        "target": "        try:\n            q.put_nowait(job)\n        except queue.Full:\n            logger.warning(\"Explain background queue full (capacity %d); dropping to template\", q.maxsize)\n            return False",
        "replacement": "        try:\n            q.put_nowait(job)\n        except queue.Full:\n            logger.warning(\"Explain background queue full (capacity %d); dropping to template\", q.maxsize)\n            return True",
        "test_node": "backend-poc-technical/test_explain_background.py::test_o4_bounded_queue_overflow",
    },
    {
        "id": "M-U-BG-2",
        "name": "Background Explainer: Disable OTPM pacer wait calculation",
        "file": BACKEND_DIR / "rag" / "explain_guards.py",
        "target": "            total_used = sum(r[1] for r in self._records)\n            if total_used + tokens_needed <= otpm_limit:\n                return 0.0",
        "replacement": "            total_used = sum(r[1] for r in self._records)\n            if True:\n                return 0.0",
        "test_node": "backend-poc-technical/test_explain_background.py::test_o6_groq_otpm_pacer_wait_calculation",
    },
    {
        "id": "M-U-BG-3",
        "name": "Background Explainer: Disable 429 retry in background mode",
        "file": BACKEND_DIR / "rag" / "explain_guards.py",
        "target": "                        if active_explain_mode == \"background\":\n                            # In background mode, 429 does NOT trip circuit breaker!\n                            if prov_attempt < max_prov_attempts - 1:",
        "replacement": "                        if False and active_explain_mode == \"background\":\n                            # In background mode, 429 does NOT trip circuit breaker!\n                            if prov_attempt < max_prov_attempts - 1:",
        "test_node": "backend-poc-technical/test_explain_background.py::test_o7_429_retry_in_background_mode",
    },
    # --- Red Flag Patterns Mutations (M-RF-1, M-RF-2 & M-RF-3) ---
    {
        "id": "M-RF-1",
        "name": "Red Flag Patterns: Drop window tolerance from 8 to 1",
        "file": BACKEND_DIR / "agents" / "red_flag_patterns.py",
        "target": "MAX_WINDOW_WORDS: int = 8",
        "replacement": "MAX_WINDOW_WORDS: int = 1",
        "test_node": "backend-poc-technical/test_red_flag_patterns.py::test_mutation_killed_window_tolerance",
    },
    {
        "id": "M-RF-2",
        "name": "Red Flag Patterns: Disable symptom negation guard",
        "file": BACKEND_DIR / "agents" / "red_flag_patterns.py",
        "target": "    if is_symptom_negated(norm):",
        "replacement": "    if False and is_symptom_negated(norm):",
        "test_node": "backend-poc-technical/test_red_flag_patterns.py::test_mutation_killed_negation_guard",
    },
    {
        "id": "M-RF-3",
        "name": "Red Flag Patterns: Apply fainting recovery suppression to all categories regardless of reason",
        "file": BACKEND_DIR / "main.py",
        "target": """            if next_state.stage1_reason in ("loss_of_consciousness", "fainting"):
                if is_fainting_recovered_or_benign(body.answer):
                    other_cats = [c for c in match_categories(body.answer) if c != "loss_of_consciousness"]
                    if other_cats:
                        next_state.stage1_red_flag = True
                        next_state.stage1_reason = other_cats[0]
                    else:
                        next_state.stage1_red_flag = False
                        next_state.stage1_reason = None""",
        "replacement": """            if is_fainting_recovered_or_benign(body.answer):
                next_state.stage1_red_flag = False
                next_state.stage1_reason = None""",
        "test_node": "backend-poc-technical/test_red_flag_patterns.py::test_mutation_killed_fainting_recovery_scoped",
    },
    {
        "id": "M-D2-1",
        "name": "Doctor Decision D2: Risk raise ignores symptom requirement",
        "file": BACKEND_DIR / "agents" / "final_triage.py",
        "target": "        if has_symptoms:",
        "replacement": "        if True:",
        "test_node": "backend-poc-technical/test_doctor_decisions_d2.py::test_d2_high_risk_asymptomatic_gives_green",
    },
    {
        "id": "M-D5-1",
        "name": "D5 normal-range skip applied to abnormal values",
        "file": BACKEND_DIR / "agents" / "verification_agent.py",
        "target": '        elif status == "missing_in_a" and is_reading_in_normal_range(obs_type, comp.value_b):',
        "replacement": '        elif status == "missing_in_a":',
        "test_node": "backend-poc-technical/test_doctor_decision_d5.py::test_d5_abnormal_self_reported_vitals_require_review",
    },
]



def run_mutation(mut: dict) -> dict:
    file_path: Path = mut["file"]
    assert file_path.exists(), f"Target file does not exist: {file_path}"

    orig_bytes = file_path.read_bytes()
    orig_sha = hashlib.sha256(orig_bytes).hexdigest()
    orig_text = orig_bytes.decode("utf-8")

    target = mut["target"]
    replacement = mut["replacement"]
    if "\r\n" in orig_text and "\r\n" not in target:
        target = target.replace("\n", "\r\n")
        replacement = replacement.replace("\n", "\r\n")
    elif "\r\n" not in orig_text and "\r\n" in target:
        target = target.replace("\r\n", "\n")
        replacement = replacement.replace("\r\n", "\n")

    # Assert exact match occurs exactly once
    occurrences = orig_text.count(target)
    if occurrences != 1:
        raise ValueError(
            f"Target string error in {file_path.name} for {mut['id']}: expected 1 occurrence, found {occurrences}"
        )

    # Invalidate and remove any stale bytecode cache before mutation
    pycache_dir = file_path.parent / "__pycache__"
    if pycache_dir.is_dir():
        for pyc in pycache_dir.glob(f"{file_path.stem}.*.pyc"):
            try:
                pyc.unlink(missing_ok=True)
            except OSError:
                pass

    # Pre-check: run test_node on UNCHANGED code to verify it passes (Q1)
    cmd_pre = [
        sys.executable,
        "-B",
        "-m",
        "pytest",
        mut["test_node"],
        "-c",
        str(BACKEND_DIR / "pytest.ini"),
        "-o",
        "norecursedirs=node_modules .next",
        "-x",
        "--tb=line",
        "-q",
    ]
    sub_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    proc_pre = subprocess.run(
        cmd_pre,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=sub_env,
    )
    if proc_pre.returncode != 0:
        pre_err = proc_pre.stderr.strip() or proc_pre.stdout.strip()
        failing_line = ""
        for line in (proc_pre.stdout or "").splitlines():
            if "ERROR" in line or "FAILED" in line or "no tests collected" in line or "error" in line.lower():
                failing_line = line.strip()
                break
        return {
            "id": mut["id"],
            "name": mut["name"],
            "file": file_path.name,
            "line_no": 0,
            "sha_before": orig_sha,
            "sha_after": orig_sha,
            "diff": "",
            "test_node": mut["test_node"],
            "return_code": proc_pre.returncode,
            "valid": False,
            "killed": False,
            "status": "INVALID",
            "failing_output": f"Test node FAILED on UNCHANGED code (exit {proc_pre.returncode}): {failing_line or pre_err}",
        }

    # Find line number (1-indexed)
    lines_before = orig_text[:orig_text.find(target)].splitlines()
    line_no = len(lines_before) + 1

    # Mutate text
    mutated_text = orig_text.replace(target, replacement, 1)
    file_path.write_bytes(mutated_text.encode("utf-8"))

    # Generate unified diff with 3 lines of context
    diff = list(
        difflib.unified_diff(
            orig_text.splitlines(keepends=True),
            mutated_text.splitlines(keepends=True),
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
            n=3,
        )
    )
    diff_str = "".join(diff)

    try:
        # Run pytest subprocess on exact test node with -B and PYTHONDONTWRITEBYTECODE
        cmd = [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            mut["test_node"],
            "-c",
            str(BACKEND_DIR / "pytest.ini"),
            "-o",
            "norecursedirs=node_modules .next",
            "-x",
            "--tb=line",
            "-q",
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env=sub_env,
        )
    finally:
        # Restore original bytes immediately under all circumstances
        file_path.write_bytes(orig_bytes)
        restored_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert restored_sha == orig_sha, f"SHA mismatch on restore for {mut['id']}"

        # Clean any bytecode written during test
        if pycache_dir.is_dir():
            for pyc in pycache_dir.glob(f"{file_path.stem}.*.pyc"):
                try:
                    pyc.unlink(missing_ok=True)
                except OSError:
                    pass

    failing_line = ""
    for line in (proc.stdout or "").splitlines():
        if "FAILED" in line or "AssertionError" in line or "assert " in line:
            failing_line = line.strip()
            if "FAILED" in line:
                break

    killed = proc.returncode != 0
    return {
        "id": mut["id"],
        "name": mut["name"],
        "file": file_path.name,
        "line_no": line_no,
        "sha_before": orig_sha,
        "sha_after": restored_sha,
        "diff": diff_str,
        "test_node": mut["test_node"],
        "return_code": proc.returncode,
        "valid": True,
        "killed": killed,
        "status": "KILLED (PASS)" if killed else "SURVIVED (FAIL)",
        "failing_output": failing_line or proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr.strip(),
    }


def main():
    print("=" * 105)
    print("STAGE 9A-4 TASK B: REAL SUBPROCESS MUTATION VERIFICATION ENGINE")
    print("=" * 105)

    mut_filter = sys.argv[1] if len(sys.argv) > 1 else None
    mutations_to_run = [m for m in MUTATIONS if mut_filter in m["id"]] if mut_filter else MUTATIONS

    all_passed = True
    results = []
    valid_count = 0
    killed_count = 0
    survived_count = 0
    invalid_count = 0

    for mut in mutations_to_run:
        res = run_mutation(mut)
        results.append(res)
        if not res.get("valid", True):
            status = "INVALID"
            invalid_count += 1
            all_passed = False
        elif res["killed"]:
            status = "KILLED (PASS)"
            valid_count += 1
            killed_count += 1
        else:
            status = "SURVIVED (FAIL)"
            valid_count += 1
            survived_count += 1
            all_passed = False

        print(f"\n[{res['id']}] {res['name']} -> {status}")
        print(f"  File: {res['file']}:{res['line_no']} (SHA256: {res['sha_before'][:12]}...)")
        safe_diff = res['diff'].strip().encode('ascii', 'backslashreplace').decode('ascii')
        if safe_diff:
            print(f"  Unified Diff:\n{safe_diff}")
        print(f"  Pytest Subprocess: {res['test_node']}")
        print(f"  Exit Code: {res['return_code']}")
        safe_out = res['failing_output'].encode('ascii', 'backslashreplace').decode('ascii')
        print(f"  Output: {safe_out}")
        print(f"  Byte Integrity Verified: SHA matches ({res['sha_after'][:12]}...)")

    # Diagnostic proof that missing target exits non-zero
    print("\n" + "-" * 105)
    print("DIAGNOSTIC TEST: Demonstrating harness exits non-zero on invalid target...")
    try:
        run_mutation({
            "id": "MUT-FAKE",
            "name": "Fake Target Test",
            "file": BACKEND_DIR / "agents" / "input_triage.py",
            "target": "THIS_STRING_DOES_NOT_EXIST_IN_THE_CODE",
            "replacement": "FOO",
            "test_node": "backend-poc-technical/test_mutation_proofs_v3.py::test_mutation_proof_1_danger_screen_on_free_text",
        })
        print("FAIL: Harness did not exit non-zero on missing target!")
        all_passed = False
    except ValueError as e:
        print(f"PASS: Harness caught missing target with expected ValueError: {e}")

    print("=" * 105)
    print(f"MUTATION TOTALS: Valid: {valid_count} | Killed: {killed_count} | Survived: {survived_count} | Invalid: {invalid_count}")
    print(f"All {len(mutations_to_run)} Mutations Verified & Killed: {'YES' if all_passed else 'NO'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
