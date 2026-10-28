"""
End-to-end tests for v3 slot filling and answer understanding wiring.
Tests:
- fasting follow-up reachability ("haan aaj roza hai" vs "nahi" vs "pata nahi")
- sick-day follow-up reachability ("ulti aur dast ho rahe hain" or "haan" vs "nahi")
- safety-class item answered "pata nahi" twice -> unknown + needs_clinician_flag
- "ek sau bees bata assi" stored as [120, 80]; "do sau tees" glucose -> 230
- a bare "7" still triggers unit clarification (unchanged)
- requires: true satisfied ONLY by boolean True
"""

import pytest
from agents.interview_v3_runner import start_v3_session, next_turn
from agents.interview_planner import plan_next_step
from agents.interview_bank.loader import get_default_bank


def test_fasting_patient_follow_up_asked():
    """Fasting patient answering 'haan aaj roza hai' gets fasting follow-up."""
    session = start_v3_session("f-1", "P1", ["diabetes"])
    session["step"] = "is_fasting_today"
    session = next_turn(session, "haan aaj roza hai")
    assert session["known_slots"].get("is_fasting_today") is True
    assert session["step"] == "fasting_symptoms"


def test_fasting_patient_nahi_not_asked():
    """Fasting patient answering 'nahi' does not get fasting follow-up."""
    session = start_v3_session("f-2", "P1", ["diabetes"])
    session["step"] = "is_fasting_today"
    session = next_turn(session, "nahi")
    assert session["known_slots"].get("is_fasting_today") is False
    assert session["step"] != "fasting_symptoms"


def test_fasting_patient_pata_nahi_stored_unknown():
    """Fasting patient answering 'pata nahi' stored as unknown, follow-up not asked."""
    session = start_v3_session("f-3", "P1", ["diabetes"])
    session["step"] = "is_fasting_today"
    session = next_turn(session, "pata nahi")
    assert session["known_slots"].get("is_fasting_today") == "unknown"
    assert session["step"] != "fasting_symptoms"


def test_sick_day_symptom_phrase_follow_up_asked():
    """Sick day answered with symptom phrase 'ulti aur dast ho rahe hain' triggers follow-up."""
    session = start_v3_session("s-1", "P1", ["diabetes"])
    session["step"] = "sick_vomiting_diarrhea"
    session = next_turn(session, "ulti aur dast ho rahe hain")
    assert session["known_slots"].get("sick_vomiting_diarrhea") is True
    assert session["step"] == "sick_fluid_intake"


def test_sick_day_haan_follow_up_asked():
    """Sick day answered with 'haan' triggers follow-up."""
    session = start_v3_session("s-2", "P1", ["diabetes"])
    session["step"] = "sick_vomiting_diarrhea"
    session = next_turn(session, "haan")
    assert session["known_slots"].get("sick_vomiting_diarrhea") is True
    assert session["step"] == "sick_fluid_intake"


def test_sick_day_nahi_not_asked():
    """Sick day answered with 'nahi' does not trigger follow-up."""
    session = start_v3_session("s-3", "P1", ["diabetes"])
    session["step"] = "sick_vomiting_diarrhea"
    session = next_turn(session, "nahi")
    assert session["known_slots"].get("sick_vomiting_diarrhea") is False
    assert session["step"] != "sick_fluid_intake"


def test_safety_class_item_unknown_twice_sets_flag():
    """A safety priority item answered 'pata nahi' twice is stored as unknown and sets clinician flag."""
    session = start_v3_session("saf-1", "P1", ["diabetes"])
    session["step"] = "hypo_symptoms_acute"
    # First unknown -> re-asked with clarification
    session = next_turn(session, "pata nahi")
    assert session.get("safety_clarify_slot") == "hypo_symptoms_acute"
    assert "safety question" in session.get("current_question", "").lower()
    # Second unknown -> kept as unknown and clinician flag set
    session = next_turn(session, "pata nahi")
    assert session["known_slots"].get("hypo_symptoms_acute") == "unknown"
    assert session.get("needs_clinician_flag") is True


def test_bp_words_parsing():
    """'ek sau bees bata assi' is parsed into systolic 120, diastolic 80."""
    session = start_v3_session("bp-1", "P1", ["hypertension"])
    session["step"] = "bp_reading"
    session = next_turn(session, "ek sau bees bata assi")
    assert session["readings"].get("blood_pressure_systolic") == 120
    assert session["readings"].get("blood_pressure_diastolic") == 80
    assert session["known_slots"].get("bp_reading") == [120, 80]


def test_glucose_words_parsing():
    """'do sau tees' glucose is parsed into 230 mg/dL."""
    session = start_v3_session("g-1", "P1", ["diabetes"])
    session["step"] = "glucose_reading"
    session = next_turn(session, "do sau tees")
    assert session["readings"].get("glucose") == 230.0
    assert session["known_slots"].get("glucose_reading") == 230.0


def test_bare_7_triggers_unit_clarification():
    """A bare '7' still triggers unit clarification (unchanged safety invariant)."""
    session = start_v3_session("b7-1", "P1", ["diabetes"])
    session["step"] = "glucose_reading"
    session = next_turn(session, "7")
    assert session.get("awaiting_glucose_unit") is True
    assert "mmol/L or 7 mg/dL" in session.get("current_question", "")


def test_requires_true_satisfied_only_by_boolean_true():
    """In planner, 'requires: true' conditions are satisfied ONLY by boolean True, not 'unknown'."""
    bank = get_default_bank()
    patient_record = {"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False}

    # With 'unknown', fasting_symptoms must NOT be planned
    decision_unk = plan_next_step(
        known_slots={"is_fasting_today": "unknown"},
        findings=[],
        patient_record=patient_record,
        bank=bank,
        asked_slots={"is_fasting_today"},
    )
    assert decision_unk.target_slot != "fasting_symptoms"

    # With True, fasting_symptoms MUST be planned
    decision_true = plan_next_step(
        known_slots={"is_fasting_today": True},
        findings=[],
        patient_record=patient_record,
        bank=bank,
        asked_slots={"is_fasting_today"},
    )
    assert decision_true.target_slot == "fasting_symptoms"
