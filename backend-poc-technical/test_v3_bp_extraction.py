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


def test_p2_4_opening_note_slot_extraction_asks_first_unanswered_question():
    """P2-4: Opening message handled as free text slot extraction; first unanswered question asked normally."""
    note = "Fasting sugar this morning was 110, BP 124/80."
    state = start_v3_session(
        checkin_id="test-p2-4-start",
        patient_id="p-dual",
        conditions=["diabetes", "hypertension"],
        on_insulin_or_sulfonylurea=True,
        opening_note=note,
    )

    # Slots extracted from note
    assert state["known_slots"].get("glucose_reading") == 110.0
    assert state["known_slots"].get("glucose_context") == "fasting"
    assert state["known_slots"].get("bp_reading") == [124, 80]
    assert state["known_slots"].get("greeting") is True

    # First unanswered question is asked normally (hypo history for insulin patient)
    assert state["step"] == "hypo_events_past_week"
    assert "low blood sugar episodes" in state["current_question"].lower()
    assert state["options"] == ["yes", "no"]
    assert "safety question. Could you please clarify" not in state["current_question"]

    # Answering "no" proceeds to next question normally
    next_st = next_turn(state, "no")
    assert next_st["step"] == "hypo_symptoms_acute"
    assert next_st["completed"] is False


def test_p2_4_opening_message_in_next_turn_handles_free_text():
    """P2-4: Opening free-text message in next_turn extracts slots and asks question normally."""
    state = start_v3_session(
        checkin_id="test-p2-4-turn1",
        patient_id="p-dual",
        conditions=["diabetes", "hypertension"],
        on_insulin_or_sulfonylurea=True,
    )
    assert state["step"] == "hypo_events_past_week"

    # Patient sends multi-intent opening note as turn 1
    reply = "Feeling fine today. Fasting sugar this morning was 110, BP 124/80. I took all my medicines."
    state2 = next_turn(state, reply)

    # Must extract slots and ask hypo question normally without safety clarification error
    assert state2["known_slots"].get("glucose_reading") == 110.0
    assert state2["known_slots"].get("bp_reading") == [124, 80]
    assert state2["step"] == "hypo_events_past_week"
    assert "safety question. Could you please clarify" not in state2["current_question"]


def test_p2_5_summary_symptoms_none_reported():
    """P2-5: Summary says 'Symptoms: None reported' after answering 'No symptoms, all good'."""
    # 1. English
    session_state = {"known_slots": {}, "readings": {}}
    _extract_early_slots("No symptoms, all good", session_state, "en")
    assert session_state["known_slots"].get("symptoms_denied") is True

    summary_en = _build_dual_summary_text(session_state["known_slots"], "en")
    assert "Symptoms: None reported" in summary_en

    # 2. Urdu Script
    session_state_ur = {"known_slots": {}, "readings": {}}
    _extract_early_slots("سب ٹھیک ہے، کوئی علامت نہیں", session_state_ur, "ur")
    assert session_state_ur["known_slots"].get("symptoms_denied") is True

    summary_ur = _build_dual_summary_text(session_state_ur["known_slots"], "ur")
    assert "علامات: کوئی نہیں" in summary_ur

    # 3. Roman Urdu
    session_state_ro = {"known_slots": {}, "readings": {}}
    _extract_early_slots("koi alamaat nahi, theek hoon", session_state_ro, "roman_ur")
    assert session_state_ro["known_slots"].get("symptoms_denied") is True

    summary_ro = _build_dual_summary_text(session_state_ro["known_slots"], "roman_ur")
    assert "Alamaat: Koi nahi" in summary_ro


def test_p2_5_summary_symptoms_reported_and_not_asked():
    """P2-5: Summary distinguishes between reported, not asked, and none reported."""
    # Symptoms reported
    reported_slots = {"hyperglycemia_symptoms": True}
    sum_reported = _build_dual_summary_text(reported_slots, "en")
    assert "Symptoms: reported symptoms" in sum_reported

    # Symptoms not asked
    empty_slots = {}
    sum_not_asked = _build_dual_summary_text(empty_slots, "en")
    assert "Symptoms: not asked" in sum_not_asked

