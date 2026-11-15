import pytest
from agents.interview_bank.loader import get_default_bank
from agents.interview_planner import plan_next_step
from agents.interview_v3_runner import (
    _build_dual_summary_text,
    _extract_early_slots,
    next_turn,
    start_v3_session,
)


def test_bp_extraction_multi_intent_english():
    """P1-3: Multi-intent opening message in English extracts BP and glucose."""
    session_state = {"known_slots": {}, "readings": {}}
    text = "Feeling fine today. Fasting sugar this morning was 110, BP 124/80. I took all my medicines."
    _extract_early_slots(text, session_state, "en")

    assert session_state["known_slots"].get("bp_reading") == [124, 80]
    assert session_state["known_slots"].get("glucose_reading") == 110.0
    assert session_state["known_slots"].get("glucose_context") == "fasting"
    assert session_state["known_slots"].get("adherence_diabetes") is True
    assert session_state["readings"].get("bp") == "124/80"

    # Check summary rendering
    summary = _build_dual_summary_text(session_state["known_slots"], "en")
    assert "Blood Pressure: 124/80 mmHg" in summary
    assert "Blood Glucose: 110 mg/dL (fasting)" in summary


def test_bp_extraction_multi_intent_roman_urdu():
    """P1-3: Multi-intent opening message in Roman Urdu extracts BP and glucose."""
    session_state = {"known_slots": {}, "readings": {}}
    text = "aaj sugar 120 thi aur BP 130 over 85 tha, sab dawai le li"
    _extract_early_slots(text, session_state, "roman_ur")

    assert session_state["known_slots"].get("bp_reading") == [130, 85]
    assert session_state["known_slots"].get("glucose_reading") == 120.0
    assert session_state["readings"].get("bp") == "130/85"

    summary = _build_dual_summary_text(session_state["known_slots"], "roman_ur")
    assert "Blood Pressure: 130/85 mmHg" in summary


def test_bp_extraction_multi_intent_urdu_script():
    """P1-3: Multi-intent opening message in Urdu script extracts BP and glucose."""
    session_state = {"known_slots": {}, "readings": {}}
    text = "آج شوگر 110 اور بلڈ پریشر 124/80 ہے، تمام دوائیاں لے لیں"
    _extract_early_slots(text, session_state, "ur")

    assert session_state["known_slots"].get("bp_reading") == [124, 80]
    assert session_state["known_slots"].get("glucose_reading") == 110.0
    assert session_state["readings"].get("bp") == "124/80"

    summary = _build_dual_summary_text(session_state["known_slots"], "ur")
    assert "بلڈ پریشر: 124/80 mmHg" in summary


def test_bp_extraction_eastern_arabic_numerals():
    """P1-3: Urdu script with Eastern Arabic numerals (۱۲۴/۸۰)."""
    session_state = {"known_slots": {}, "readings": {}}
    text = "بلڈ پریشر ۱۲۴/۸۰ ہے اور شوگر ۱۱۵ ہے"
    _extract_early_slots(text, session_state, "ur")

    assert session_state["known_slots"].get("bp_reading") == [124, 80]
    assert session_state["readings"].get("bp") == "124/80"


def test_planner_missing_bp_checkpoint_dual_patient():
    """P1-3: Dual patient omitting BP must be asked BP reading before summary."""
    bank = get_default_bank()
    patient = {"conditions": ["diabetes", "hypertension"]}
    # All slots except BP have been asked/satisfied, reaching budget cap
    asked_slots = {"greeting", "diabetes_glucose_reading", "diabetes_adherence", "q1", "q2", "q3", "q4", "q5"}
    known_slots = {"glucose_reading": 110, "adherence_diabetes": True}

    decision = plan_next_step(
        known_slots=known_slots,
        findings=[],
        patient_record=patient,
        bank=bank,
        asked_slots=asked_slots,
        base_budget=8,
    )

    assert decision.action == "ask_bank_item"
    assert decision.item is not None
    assert decision.item.id == "hypertension_bp_reading"
    assert decision.reason == "missing_data_checkpoint_bp_required"


def test_planner_missing_bp_checkpoint_htn_only():
    """P1-3: Hypertension-only patient omitting BP must be asked BP before summary."""
    bank = get_default_bank()
    patient = {"conditions": ["hypertension"]}
    asked_slots = {"greeting", "hypertension_symptoms", "hypertension_adherence", "q1", "q2", "q3", "q4", "q5"}
    known_slots = {"greeting": True, "adherence_hypertension": True}

    decision = plan_next_step(
        known_slots=known_slots,
        findings=[],
        patient_record=patient,
        bank=bank,
        asked_slots=asked_slots,
        base_budget=8,
    )

    assert decision.action == "ask_bank_item"
    assert decision.item is not None
    assert decision.item.id == "hypertension_bp_reading"
    assert decision.reason == "missing_data_checkpoint_bp_required"


def test_planner_proceeds_to_summary_when_bp_known():
    """P1-3: When BP is known, planner can proceed to summary confirmation."""
    bank = get_default_bank()
    patient = {"conditions": ["diabetes", "hypertension"]}
    asked_slots = {"greeting", "diabetes_glucose_reading", "diabetes_adherence", "q1", "q2", "q3", "q4", "q5"}
    known_slots = {"glucose_reading": 110, "bp_reading": [124, 80], "adherence_diabetes": True}

    decision = plan_next_step(
        known_slots=known_slots,
        findings=[],
        patient_record=patient,
        bank=bank,
        asked_slots=asked_slots,
        base_budget=8,
    )

    assert decision.action == "summary_confirm"
    assert decision.item is not None
    assert decision.item.id == "core_summary_confirm"
