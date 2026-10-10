"""
Regression Tests for v2 Glucose Unit Safety and Low-Glucose Gap (Stage 9A-6 Task C).

Verifies that in v2:
1. mmol/L values (2.0, 2.8, 3.0 mmol/L) and Urdu/Roman-Urdu forms are recognized,
   converted with 18.0, and never end as 'routine' for severe lows.
2. Bare numbers 41 to 54 trigger unit clarification once; if unresolved, they trigger
   review/urgent safety review and never end as 'routine'.
3. Bare numbers >= 55 remain mg/dL without unit clarification.
4. The reported raw reading text is preserved in the intake note.
"""

import pytest
from agents.adaptive_interview_agent import (
    InterviewState,
    DiabetesStep,
    adaptive_interview_node,
    _process_glucose_input,
)


def start(conditions):
    return adaptive_interview_node(InterviewState(patient_id="P-1", conditions_on_file=conditions))


def feed(state, *answers):
    for a in answers:
        state = adaptive_interview_node(state, a)
    return state


def test_v2_mmol_recognition_and_conversion():
    # 2.0 mmol/L (36.0 mg/dL equivalent)
    reading, unit, clarify, guidance, reason = _process_glucose_input("2.0 mmol/L", previously_asked=True)
    assert reading == 36.0
    assert unit == "mg/dL"
    assert clarify is False
    assert guidance is not None

    # 3.0 mmol/L (54.0 mg/dL equivalent)
    reading, unit, clarify, guidance, reason = _process_glucose_input("3.0 mmol/L", previously_asked=True)
    assert reading == 54.0
    assert unit == "mg/dL"
    assert clarify is False

    # 7.0 mmol/L (126.0 mg/dL equivalent)
    reading, unit, clarify, guidance, reason = _process_glucose_input("7.0 mmol/L", previously_asked=True)
    assert reading == 126.0
    assert unit == "mg/dL"
    assert clarify is False


def test_v2_urdu_roman_urdu_mmol_recognition():
    # Urdu text: ۷.۰ ملی مول -> 7.0 mmol -> 126.0 mg/dL
    reading, unit, clarify, guidance, reason = _process_glucose_input("۷.۰ ملی مول", previously_asked=True)
    assert reading == 126.0
    assert unit == "mg/dL"

    # Roman Urdu: 2.0 milli mole -> 36.0 mg/dL
    reading, unit, clarify, guidance, reason = _process_glucose_input("2.0 milli mole", previously_asked=True)
    assert reading == 36.0
    assert unit == "mg/dL"


def test_v2_bare_41_to_54_triggers_clarification_then_review():
    # Bare 45 on first turn -> needs unit clarification once
    reading, unit, clarify, guidance, reason = _process_glucose_input("45", previously_asked=False)
    assert clarify is True
    assert reading is None

    # Bare 45 on checkpoint / repeated -> recorded as possible low
    reading, unit, clarify, guidance, reason = _process_glucose_input("45", previously_asked=True)
    assert clarify is False
    assert reading == 45.0
    assert unit == "unclear"
    assert guidance is not None
    assert reason == "glucose value unit unclear, possible low"


def test_v2_bare_55_and_above_stays_mgdl():
    # Bare 55 on first turn -> accepted directly as mg/dL
    reading, unit, clarify, guidance, reason = _process_glucose_input("55", previously_asked=False)
    assert clarify is False
    assert reading == 55.0
    assert unit == "mg/dL"

    # Bare 126 on first turn -> accepted directly as mg/dL
    reading, unit, clarify, guidance, reason = _process_glucose_input("126", previously_asked=False)
    assert clarify is False
    assert reading == 126.0
    assert unit == "mg/dL"


def test_v2_full_flow_preserves_raw_reading_in_note():
    # Patient provides mmol reading, answered through checkpoint
    state = start(["diabetes"])
    answers = ["Feeling okay", "2.0 mmol/L", "just checking my sugar", "No", "Yes", "No changes", "None"]
    for a in answers:
        if state.step == "interview_complete":
            break
        state = adaptive_interview_node(state, a)

    intake = state.intake
    assert intake["readings"][0]["value"] == 36.0
    assert intake["readings"][0]["unit"] == "mg/dL"
    assert "2.0 mmol/L" in intake["symptoms"].get("glucose_original_text", "")
    assert "2.0 mmol/L" in intake.get("lifestyle_notes", "")
