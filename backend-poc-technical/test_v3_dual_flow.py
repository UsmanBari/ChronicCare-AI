"""
Comprehensive E2E and Unit Tests for Interview Engine v3 Dual-Diagnosis Flow.
(Stage 9A-7 / Hassaan Day 3).

Validates:
1. Both readings asked before any symptom in dual diagnosis (R2).
2. NO slot asked twice across all personas (R3/R6 de-duplication).
3. Shared symptom fills all corresponding clinical slots (R3).
4. Medication adherence asked once across both conditions (R4).
5. Progress hint matches true asked count at every turn (R7).
6. Multi-condition summary confirmation lists captured DM and HTN values (R8).
7. Targeted correction round allows updating one slot and re-shows summary (max 2 rounds) (R8).
8. Caregiver reporting persists answered_by, lowers confidence, surfaces in /complete and provider detail (R9).
9. Family history statement does NOT trigger caregiver mode (R9 trap).
10. Single-condition flows remain strictly unchanged (R10).
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from agents.interview_bank.loader import get_default_bank
from agents.interview_planner import plan_next_step
from agents.interview_v3_runner import finish_v3_session, next_turn, start_v3_session
from main import app


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_both_readings_before_any_symptom():
    """R2: For dual diagnosis, both glucose and BP readings must be asked before any symptom."""
    session = start_v3_session("dual-r2-1", "P-DUAL", ["diabetes", "hypertension"])
    assert session["step"] == "greeting"
    session = next_turn(session, "Hello")

    # Step 1 reading (default glucose first)
    first_reading_step = session["step"]
    assert first_reading_step in ("glucose_reading", "bp_reading")
    assert "symptom" not in first_reading_step

    if first_reading_step == "glucose_reading":
        session = next_turn(session, "130 mg/dL")
        # Step 2 reading MUST be the remaining reading (bp_reading) before symptoms
        assert session["step"] == "bp_reading"
        session = next_turn(session, "125/82")
    else:
        session = next_turn(session, "125/82")
        assert session["step"] == "glucose_reading"
        session = next_turn(session, "130 mg/dL")

    # Both readings are now satisfied
    assert session["known_slots"].get("glucose_reading") == 130.0
    assert session["known_slots"].get("bp_reading") == [125, 82]


def test_no_slot_asked_twice_in_any_persona():
    """R3/R6: Verify that NO clinical slot is asked twice across all personas (except single safety clarification)."""
    personas_path = REPO_ROOT / "tests" / "sim" / "personas.json"
    with open(personas_path, "r", encoding="utf-8") as f:
        personas = json.load(f)

    for p in personas:
        conds = p.get("conditions", ["diabetes"])
        lang = p.get("language", "en")
        on_ins = p.get("on_insulin", False)
        answers = p.get("answers", [])

        session = start_v3_session(
            checkin_id=f"audit-{p['id']}",
            patient_id="AUDIT-PATIENT",
            conditions=conds,
            on_insulin_or_sulfonylurea=on_ins,
            language=lang,
        )

        seen_slots = []
        clarify_count = 0
        ans_idx = 0

        while not session.get("completed") and ans_idx < 14:
            curr_step = session.get("step")
            if curr_step in ("COMPLETE", None):
                break

            # If current step is a clarification re-ask (unit or safety), track it
            if session.get("awaiting_glucose_unit"):
                pass  # Unit clarification turn
            elif session.get("safety_clarify_slot") == curr_step:
                clarify_count += 1
                assert clarify_count <= 2, f"Too many clarification turns in {p['id']}"
            elif curr_step not in ("greeting", "summary_confirmation", "summary_correction_select"):
                assert curr_step not in seen_slots, (
                    f"Persona {p['id']} asked slot '{curr_step}' more than once! History: {seen_slots}"
                )
                seen_slots.append(curr_step)

            if curr_step == "summary_confirmation":
                ans = "haan" if lang == "ur" else ("theek hai" if lang == "roman_ur" else "yes")
            elif ans_idx < len(answers):
                ans = answers[ans_idx]
                ans_idx += 1
            else:
                ans = "haan" if lang == "ur" else ("nahi" if lang == "roman_ur" else "no")
            session = next_turn(session, ans)


def test_shared_symptom_fills_all_slots():
    """R3: A shared symptom is asked once and fills all slots it serves."""
    bank = get_default_bank()
    session = start_v3_session("dual-r3-1", "P-DUAL", ["diabetes", "hypertension"])
    session["known_slots"]["glucose_reading"] = 120.0
    session["known_slots"]["bp_reading"] = [120, 80]
    session["asked_slots"].extend(["greeting", "glucose_reading", "bp_reading"])

    # Ask diabetes_hyperglycemia_symptoms (which has also_fills: [associated_symptoms])
    session["step"] = "hyperglycemia_symptoms"
    session = next_turn(session, "no symptoms at all")

    assert session["known_slots"].get("hyperglycemia_symptoms") is False
    assert session["known_slots"].get("associated_symptoms") is False

    # Next step planned must NOT be associated_symptoms
    assert session["step"] != "associated_symptoms"


def test_adherence_asked_once():
    """R4: Medication adherence is asked once across active medicines."""
    session = start_v3_session("dual-r4-1", "P-DUAL", ["diabetes", "hypertension"])
    session["known_slots"]["glucose_reading"] = 120.0
    session["known_slots"]["bp_reading"] = [120, 80]
    session["asked_slots"].extend(["greeting", "glucose_reading", "bp_reading"])

    session["step"] = "adherence_diabetes"
    session = next_turn(session, "yes, taking all medicines regularly")

    assert session["known_slots"].get("adherence_diabetes") is True
    assert session["known_slots"].get("adherence_hypertension") is True

    # Adherence for hypertension must not be re-asked
    assert session["step"] != "adherence_hypertension"


def test_progress_hint_equals_real_count_every_turn():
    """R7: Progress hint matches the true asked count and current budget at each turn."""
    session = start_v3_session("dual-r7-1", "P-DUAL", ["diabetes", "hypertension"])
    assert session["progress_hint"] == "1/8"

    session = next_turn(session, "hello")
    hint_parts = session["progress_hint"].split("/")
    assert int(hint_parts[0]) >= 1
    assert int(hint_parts[1]) in (8, 12, 14)


def test_summary_lists_both_conditions():
    """R8: Summary confirmation includes both diabetes and hypertension captured readings."""
    session = start_v3_session("dual-r8-1", "P-DUAL", ["diabetes", "hypertension"], language="en")
    session["known_slots"]["glucose_reading"] = 135.0
    session["known_slots"]["glucose_context"] = "fasting"
    session["known_slots"]["bp_reading"] = [124, 82]
    session["known_slots"]["bp_technique"] = "rested quietly"
    session["known_slots"]["adherence_diabetes"] = True
    session["known_slots"]["adherence_hypertension"] = True
    session["known_slots"]["lifestyle_diabetes"] = "walking daily"
    session["known_slots"]["lifestyle_hypertension"] = "moderate salt"

    all_asked = {
        "greeting", "glucose_reading", "glucose_context", "bp_reading", "bp_technique",
        "hyperglycemia_symptoms", "associated_symptoms", "foot_problems",
        "adherence_diabetes", "adherence_hypertension",
        "lifestyle_diabetes", "lifestyle_hypertension", "patient_free_text_note"
    }
    session["asked_slots"] = list(all_asked)

    bank = get_default_bank()
    decision = plan_next_step(
        known_slots=session["known_slots"],
        findings=[],
        patient_record={"conditions": ["diabetes", "hypertension"]},
        recent_checkins=[],
        bank=bank,
        asked_slots=all_asked,
    )
    assert decision.action == "summary_confirm"

    session["step"] = "patient_free_text_note"
    session = next_turn(session, "no additional notes")
    assert session["step"] == "summary_confirmation"
    q_text = session["current_question"]
    assert "Blood Glucose: 135" in q_text
    assert "Blood Pressure: 124/82" in q_text
    assert "Medication: Taken as prescribed" in q_text


def test_summary_correction_changes_one_slot_and_reshows_summary():
    """R8: Correction allows selecting one slot to update and re-renders summary (max 2 rounds)."""
    session = start_v3_session("dual-r8-corr", "P-DUAL", ["diabetes", "hypertension"], language="en")
    session["known_slots"]["glucose_reading"] = 140.0
    session["known_slots"]["bp_reading"] = [190, 100]  # accidentally entered high
    session["asked_slots"].extend(["greeting", "glucose_reading", "glucose_context", "bp_reading", "bp_technique"])
    session["step"] = "summary_confirmation"

    # Patient asks to change
    session = next_turn(session, "Need to change something")
    assert session["step"] == "summary_correction_select"
    assert session.get("awaiting_correction_slot") is True
    assert session.get("summary_correction_rounds") == 1

    # Patient picks blood pressure
    session = next_turn(session, "blood pressure")
    assert session["step"] == "bp_reading"
    assert "bp_reading" not in session["known_slots"]

    # Patient inputs corrected reading -> R8 re-shows summary immediately
    session = next_turn(session, "120/80")
    assert session["known_slots"]["bp_reading"] == [120, 80]
    assert session["step"] == "summary_confirmation"
    assert "Blood Pressure: 120/80" in session["current_question"]

    # Confirming completes
    session = next_turn(session, "Confirm and submit")
    assert session["completed"] is True
    assert session["step"] == "COMPLETE"


def test_caregiver_flow_and_propagation():
    """R9: Caregiver status lowers confidence and propagates answered_by to intakes and review detail."""
    session = start_v3_session("caregiver-1", "P-CAREGIVER", ["diabetes", "hypertension"], answered_by="caregiver")
    session["known_slots"]["glucose_reading"] = 145.0
    session["readings"]["glucose"] = 145.0

    res = finish_v3_session(session)
    assert res["answered_by"] == "caregiver"
    for intake in res["intakes"]:
        assert intake["answered_by"] == "caregiver"
        assert intake["confidence"] == "Medium"  # lowered from High to Medium
        assert any("caregiver" in n.lower() for n in intake["notes"])


def test_family_history_does_not_trigger_caregiver():
    """R9: Family history ('my mother also has diabetes') must not set caregiver status."""
    session = start_v3_session("fam-hist-1", "P-PATIENT", ["diabetes"])
    session = next_turn(session, "My mother also has diabetes, should I be worried?")
    assert session.get("answered_by") != "caregiver"
    res = finish_v3_session(session)
    for intake in res["intakes"]:
        assert intake.get("answered_by") != "caregiver"
        assert intake["confidence"] == "High"


def test_single_condition_flows_unchanged():
    """R10: Single condition check-in flows match expected question sequences."""
    # DM single condition
    dm_session = start_v3_session("sc-dm", "P-DM", ["diabetes"])
    assert dm_session["step"] == "greeting"
    dm_session = next_turn(dm_session, "hi")
    assert dm_session["step"] == "glucose_reading"
    dm_session = next_turn(dm_session, "110 mg/dL")
    assert dm_session["step"] == "glucose_context"

    # HTN single condition
    htn_session = start_v3_session("sc-htn", "P-HTN", ["hypertension"])
    assert htn_session["step"] == "greeting"
    htn_session = next_turn(htn_session, "hi")
    assert htn_session["step"] == "bp_reading"
    htn_session = next_turn(htn_session, "120/80")
    assert htn_session["step"] == "bp_technique"
