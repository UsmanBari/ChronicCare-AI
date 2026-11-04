"""
Tests for G-14: Roman Urdu & Urdu Caregiver Detection in Interview Engine v3.

Verifies:
1. All 9 target caregiver phrases in Roman Urdu, Urdu script, and English set
   answered_by="caregiver" and lower interview confidence to Medium.
2. 5 look-alike distractor phrases (third-party advice/speech to patient)
   must NOT trigger caregiver classification.
"""

import pytest
from agents.answer_understanding import detect_caregiver_phrase
from agents.interview_v3_runner import start_v3_session, next_turn, finish_v3_session


CAREGIVER_POSITIVE_PHRASES = [
    "ammi ki taraf se",
    "abbu ke liye",
    "main apni walida ke liye jawab de raha hoon",
    "میں اپنی امی کی طرف سے",
    "walid sahab ki taraf se",
    "apni ammi ke liye check in kar raha hoon",
    "mere abbu ki checking hai",
    "walida ke liye check in",
    "میں اپنے والد کے لیے جواب دے رہا ہوں",
]

LOOKALIKE_NEGATIVE_PHRASES = [
    "ammi ne kaha tha dawai lo",
    "abbu ne bola doctor ke paas jao",
    "walida ne kaha sugar check karo",
    "walid ne dawai mangwai thi",
    "ammi kehti hain meetha kam khao",
]


@pytest.mark.parametrize("phrase", CAREGIVER_POSITIVE_PHRASES)
def test_caregiver_detector_accepts_all_positive_phrases(phrase: str):
    assert detect_caregiver_phrase(phrase) is True, f"Failed to detect caregiver phrase: {phrase}"


@pytest.mark.parametrize("distractor", LOOKALIKE_NEGATIVE_PHRASES)
def test_caregiver_detector_rejects_lookalike_distractors(distractor: str):
    assert detect_caregiver_phrase(distractor) is False, f"Lookalike erroneously triggered caregiver: {distractor}"


@pytest.mark.parametrize("phrase", CAREGIVER_POSITIVE_PHRASES)
def test_v3_runner_sets_caregiver_and_lowers_confidence(phrase: str):
    """When a patient submits a caregiver statement, runner records answered_by='caregiver' and confidence=Medium."""
    state = start_v3_session(
        checkin_id="chk-cg-test-1",
        patient_id="pat-cg-1",
        conditions=["diabetes"],
        language="roman_ur",
    )
    # Patient provides caregiver phrase as their check-in turn
    next_state = next_turn(state, phrase)

    assert next_state.get("answered_by") == "caregiver"
    assert next_state.get("known_slots", {}).get("answered_by") == "caregiver"

    # Finish session and verify confidence calculation
    summary = finish_v3_session(next_state)
    assert summary.get("answered_by") == "caregiver"
    for intake in summary.get("intakes", []):
        assert intake.get("answered_by") == "caregiver"
        # Standard routine checkin confidence lowered from High to Medium
        assert intake.get("confidence") == "Medium"


@pytest.mark.parametrize("distractor", LOOKALIKE_NEGATIVE_PHRASES)
def test_v3_runner_preserves_patient_for_distractors(distractor: str):
    """Look-alike phrases mentioning parents giving advice do not alter answered_by to caregiver."""
    state = start_v3_session(
        checkin_id="chk-cg-distractor-1",
        patient_id="pat-cg-2",
        conditions=["diabetes"],
        language="roman_ur",
    )
    next_state = next_turn(state, distractor)

    assert next_state.get("answered_by") != "caregiver"
    assert next_state.get("known_slots", {}).get("answered_by") != "caregiver"

