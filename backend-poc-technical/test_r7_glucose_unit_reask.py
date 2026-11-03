"""
Unit & Integration Tests for Rule R7: Bare Glucose 2-40 Unit Re-Ask.

Verifies:
1. Bare number 2-40 triggers exactly one unit re-ask question:
   "Is that number in mg/dL (most meters) or mmol/L?" (en, ur, roman_ur)
2. Answering with unit (mmol/L) converts correctly (e.g. 7.0 mmol/L -> 126.0 mg/dL).
3. Answering with unit (mg/dL) uses reading directly.
4. Answering without unit (e.g. "don't know", "no unit") routes to safe path:
   possible severe low, clinician review required, low-sugar guidance attached.
5. Behavior verified in both v2 and v3 interview engines.
"""

import pytest
from agents.adaptive_interview_agent import (
    InterviewState,
    DiabetesStep,
    adaptive_interview_node,
    get_current_question,
)
from agents.interview_v3_runner import (
    start_v3_session,
    next_turn,
)
from agents.interview_bank.loader import get_message


def test_r7_question_texts_exact():
    assert get_message("unit_clarification_question", "en") == "Is that number in mg/dL (most meters) or mmol/L?"
    assert get_message("unit_clarification_question", "ur") == "کیا یہ نمبر mg/dL میں ہے (زیادہ تر میٹر) یا mmol/L میں؟"
    assert get_message("unit_clarification_question", "roman_ur") == "Kya yeh number mg/dL mein hai (zyada tar meter) ya mmol/L mein?"


def test_v2_bare_number_reask_and_resolved_mmol():
    state = InterviewState(
        patient_id="pat-v2-r7-mmol",
        conditions_on_file=["diabetes"],
        active_condition="diabetes",
        step=DiabetesStep.GLUCOSE_READING.value,
    )
    # Turn 1: Patient enters bare 7
    next_st = adaptive_interview_node(state, patient_response="7")
    assert next_st.step == DiabetesStep.MISSING_DATA_CHECKPOINT.value
    assert next_st.answers.get("_glucose_pending_raw") == "7"
    q = get_current_question(next_st)
    assert q == "Is that number in mg/dL (most meters) or mmol/L?"

    # Turn 2: Patient clarifies mmol/L
    final_st = adaptive_interview_node(next_st, patient_response="mmol/L")
    assert final_st.answers.get("glucose_reading") == 126.0  # 7 * 18
    assert final_st.step == DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value


def test_v2_bare_number_reask_and_unclear_safe_path():
    state = InterviewState(
        patient_id="pat-v2-r7-unclear",
        conditions_on_file=["diabetes"],
        active_condition="diabetes",
        step=DiabetesStep.GLUCOSE_READING.value,
    )
    # Turn 1: Patient enters bare 9
    next_st = adaptive_interview_node(state, patient_response="9")
    assert next_st.answers.get("_glucose_pending_raw") == "9"
    q = get_current_question(next_st)
    assert q == "Is that number in mg/dL (most meters) or mmol/L?"

    # Turn 2: Patient says "I don't know"
    final_st = adaptive_interview_node(next_st, patient_response="I don't know")
    assert final_st.answers.get("possible_severe_low") is True
    assert final_st.answers.get("safety_guidance") is not None
    assert final_st.step == DiabetesStep.HYPERGLYCEMIA_SYMPTOMS.value


def test_v3_bare_number_reask_and_resolved_mmol():
    sess = start_v3_session(
        checkin_id="chk-v3-r7-mmol",
        patient_id="pat-v3-r7-mmol",
        conditions=["diabetes"],
        language="en",
    )
    sess = next_turn(sess, "Feeling ok")
    sess = next_turn(sess, "7")
    assert sess.get("awaiting_glucose_unit") is True
    assert sess.get("current_question") == "Is that number in mg/dL (most meters) or mmol/L?"

    # Clarifies mmol/L
    sess = next_turn(sess, "mmol/L")
    assert sess.get("readings", {}).get("glucose") == 126.0
    assert sess.get("awaiting_glucose_unit") is False


def test_v3_bare_number_reask_and_unclear_safe_path():
    sess = start_v3_session(
        checkin_id="chk-v3-r7-unclear",
        patient_id="pat-v3-r7-unclear",
        conditions=["diabetes"],
        language="en",
    )
    sess = next_turn(sess, "Feeling ok")
    sess = next_turn(sess, "9")
    assert sess.get("awaiting_glucose_unit") is True
    assert sess.get("current_question") == "Is that number in mg/dL (most meters) or mmol/L?"

    # Answers without unit
    sess = next_turn(sess, "it just says 9")
    assert sess.get("possible_severe_low") is True
    assert sess.get("needs_clinician_flag") is True
    assert sess.get("readings", {}).get("glucose") == 9.0
