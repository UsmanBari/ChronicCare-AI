"""
Tests for G-02: Unclear Medication Adherence Handling in Interview Engine v3.

Verifies:
1. Phrases like "maybe", "shayad", "pata nahi", "kal tha", "kabhi kabhi", "not sure",
   "یاد نہیں", "yad nahi" trigger a clarification question.
2. Clear affirmative ("haan", "yes") after clarification records adherent (True).
3. Clear negative ("no", "nahi") after clarification records missed dose (False)
   and triggers missed dose reason inquiry.
4. Unclear response after clarification records "unclear", flags clinician review
   (needs_review=True), and NEVER silently records adherent.
5. In-process probe on v2 showing v2's contrasting behavior for open questions.
"""

import pytest
from agents.answer_understanding import is_unclear_adherence_answer, parse_yes_no
from agents.interview_bank.loader import get_message
from agents.interview_v3_runner import start_v3_session, next_turn, finish_v3_session


UNCLEAR_PHRASES = [
    "maybe",
    "shayad",
    "pata nahi",
    "kal tha",
    "kabhi kabhi",
    "not sure",
    "یاد نہیں",
    "yad nahi",
]


@pytest.mark.parametrize("phrase", UNCLEAR_PHRASES)
def test_adherence_unclear_detector_identifies_all_target_phrases(phrase: str):
    assert is_unclear_adherence_answer(phrase) is True, f"Expected {phrase} to be identified as unclear"


@pytest.mark.parametrize("clear_yes", ["yes", "haan", "haan ji", "ji haan", "of course", "yes taken"])
def test_adherence_unclear_detector_rejects_clear_yes(clear_yes: str):
    assert is_unclear_adherence_answer(clear_yes) is False


@pytest.mark.parametrize("clear_no", ["no", "nahi", "nahin", "ji nahi", "bilkul nahi", "never"])
def test_adherence_unclear_detector_rejects_clear_no(clear_no: str):
    assert is_unclear_adherence_answer(clear_no) is False


@pytest.mark.parametrize("phrase", UNCLEAR_PHRASES)
def test_v3_flow_unclear_phrase_triggers_clarification(phrase: str):
    """An unclear adherence answer must prompt a clarification question, not advance or mark adherent."""
    state = start_v3_session(
        checkin_id="chk-adh-clarify-1",
        patient_id="pat-test-1",
        conditions=["diabetes"],
        language="en",
    )
    # Fast-forward past reading and context to adherence
    state["step"] = "adherence_diabetes"
    state["current_question"] = "Have you taken your diabetes medications as prescribed today?"

    next_state = next_turn(state, phrase)

    # Must ask clarification question from messages.json
    expected_q = get_message("adherence_clarification_question", "en")
    assert next_state.get("awaiting_adherence_clarification") == "adherence_diabetes"
    assert next_state.get("current_question") == expected_q
    # Adherence slot must NOT be set to True
    assert next_state.get("known_slots", {}).get("adherence_diabetes") is None


def test_v3_flow_clear_yes_after_clarification_records_adherent():
    """An unclear adherence answer followed by clear 'haan' or 'yes' records True."""
    state = start_v3_session(
        checkin_id="chk-adh-yes-2",
        patient_id="pat-test-2",
        conditions=["diabetes"],
        language="roman_ur",
    )
    state["step"] = "adherence_diabetes"

    # Turn 1: unclear answer "shayad"
    state = next_turn(state, "shayad")
    assert state.get("awaiting_adherence_clarification") == "adherence_diabetes"

    # Turn 2: clear affirmative "haan"
    state = next_turn(state, "haan")
    assert state.get("awaiting_adherence_clarification") is None
    assert state.get("known_slots", {}).get("adherence_diabetes") is True


def test_v3_flow_clear_no_after_clarification_records_false_and_asks_missed_dose_reason():
    """An unclear answer followed by 'no' records False and triggers missed doses inquiry."""
    state = start_v3_session(
        checkin_id="chk-adh-no-3",
        patient_id="pat-test-3",
        conditions=["diabetes"],
        language="en",
    )
    state["known_slots"] = {
        "greeting": True,
        "glucose_reading": 120,
        "glucose_context": "fasting",
        "foot_problems": False,
        "hyperglycemia_symptoms": False,
    }
    state["asked_slots"] = ["greeting", "glucose_reading", "glucose_context", "foot_problems", "hyperglycemia_symptoms"]
    state["step"] = "adherence_diabetes"

    # Turn 1: unclear answer "kal tha"
    state = next_turn(state, "kal tha")
    assert state.get("awaiting_adherence_clarification") == "adherence_diabetes"

    # Turn 2: clear negative "no"
    state = next_turn(state, "no")
    assert state.get("awaiting_adherence_clarification") is None
    assert state.get("known_slots", {}).get("adherence_diabetes") is False
    # Next question must be missed doses reason
    assert state.get("step") == "missed_doses_reason_diabetes" or "missed" in (state.get("current_question") or "").lower()


def test_v3_flow_still_unclear_after_clarification_sets_unclear_and_requires_review():
    """An unclear answer followed by another unclear answer records 'unclear' and escalates to review."""
    state = start_v3_session(
        checkin_id="chk-adh-unclear-4",
        patient_id="pat-test-4",
        conditions=["hypertension"],
        language="ur",
    )
    state["step"] = "adherence_hypertension"

    # Turn 1: unclear answer
    state = next_turn(state, "یاد نہیں")
    assert state.get("awaiting_adherence_clarification") == "adherence_hypertension"

    # Turn 2: still unclear
    state = next_turn(state, "پتہ نہیں")
    assert state.get("awaiting_adherence_clarification") is None
    assert state.get("known_slots", {}).get("adherence_hypertension") == "unclear"
    assert state.get("needs_clinician_flag") is True

    # Complete session and verify review level
    summary = finish_v3_session(state)
    assert summary.get("needs_review") is True
    for intake in summary.get("intakes", []):
        assert intake.get("requires_review") is True
        assert intake.get("level") == "review"


def test_v2_comparison_probe_unclear_adherence_gap():
    """
    Demonstrates v2 baseline behavior on unclear adherence answers for the Day 4 report.
    v2 uses _looks_affirmative() in adaptive_interview_agent.py which evaluates:
    - 'maybe', 'kal tha', 'kabhi kabhi', 'یاد نہیں' -> None (unhandled token / no Urdu regex:
      in v2 adh is None jumps to lifestyle without review, silently missing the ambiguity)
    - 'not sure' -> False (erroneously treated as missed dose due to bare English 'not' token match)
    """
    from agents.adaptive_interview_agent import _looks_affirmative

    # In v2, unhandled/hedged tokens and Urdu script return None
    assert _looks_affirmative("maybe") is None
    assert _looks_affirmative("kal tha") is None
    assert _looks_affirmative("kabhi kabhi") is None
    assert _looks_affirmative("یاد نہیں") is None

    # In v2, 'not sure' matches negative cue 'not' -> False (not recognized as uncertainty)
    assert _looks_affirmative("not sure") is False
