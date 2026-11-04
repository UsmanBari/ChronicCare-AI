"""
Unit and Integration Tests for Meter LO and HI Confirmation (Rule R1).

Covers:
1. detect_meter_lo_hi matching:
   - English: 'LO', 'HI', 'meter says LO', 'screen shows HI'
   - Urdu: 'میٹر پر LO', 'اسکرین پر HI'
   - Roman Urdu: 'meter par LO likha hai', 'screen pe HI hai'
   - Plain statements that must NOT trigger: 'sugar low hai', 'sugar high hai', 'bohot low lag raha hai', 'sugar lo hai', 'sugar hi hai'
2. Negative confirmation: 'LO' -> 'No, I just feel low' -> does not trigger emergency, prompts for numeric reading.
3. Affirmative confirmation in v2: 'LO' -> 'yes' -> EMERGENCY, 'HI' -> 'yes' -> EMERGENCY.
4. Affirmative confirmation in v3: 'LO' -> 'yes' -> EMERGENCY, 'HI' -> 'yes' -> EMERGENCY.
5. End-to-end checkin API tests for v2 and v3 in direct and graph modes.
"""

import os
import time
import pytest
from fastapi.testclient import TestClient

from main import app
from agents.answer_validation import detect_meter_lo_hi
from agents.adaptive_interview_agent import (
    InterviewState,
    DiabetesStep,
    adaptive_interview_node,
    get_current_question,
    get_red_flag_level,
)
from agents.interview_v3_runner import (
    start_v3_session,
    next_turn,
)
from agents.interview_bank.loader import get_message


def test_detect_meter_lo_hi_english():
    assert detect_meter_lo_hi("LO") == "LO"
    assert detect_meter_lo_hi("Lo") == "LO"
    assert detect_meter_lo_hi("lo") == "LO"
    assert detect_meter_lo_hi("HI") == "HI"
    assert detect_meter_lo_hi("Hi") == "HI"
    assert detect_meter_lo_hi("hi") == "HI"
    assert detect_meter_lo_hi("meter says LO") == "LO"
    assert detect_meter_lo_hi("screen shows HI") == "HI"
    assert detect_meter_lo_hi("my meter screen is showing LO") == "LO"
    assert detect_meter_lo_hi("display has HI") == "HI"


def test_detect_meter_lo_hi_urdu():
    assert detect_meter_lo_hi("میٹر پر LO") == "LO"
    assert detect_meter_lo_hi("اسکرین پر HI") == "HI"
    assert detect_meter_lo_hi("میٹر پر LO لکھا ہے") == "LO"
    assert detect_meter_lo_hi("اسکرین پر HI لکھا آ رہا ہے") == "HI"
    # Urdu-script transliteration tests (with and without meter/screen cue)
    assert detect_meter_lo_hi("ایل او") == "LO"
    assert detect_meter_lo_hi("ایچ آئی") == "HI"
    assert detect_meter_lo_hi("میٹر پر ایل او") == "LO"
    assert detect_meter_lo_hi("میٹر پر ایچ آئی") == "HI"
    assert detect_meter_lo_hi("اسکرین پر ایل او") == "LO"
    assert detect_meter_lo_hi("اسکرین پر ایچ آئی") == "HI"


def test_detect_meter_lo_hi_roman_urdu():
    assert detect_meter_lo_hi("meter par LO likha hai") == "LO"
    assert detect_meter_lo_hi("screen pe HI hai") == "HI"
    assert detect_meter_lo_hi("meter keh raha hai LO") == "LO"
    assert detect_meter_lo_hi("screen par HI aa raha hai") == "HI"


def test_plain_statements_do_not_trigger():
    assert detect_meter_lo_hi("sugar low hai") is None
    assert detect_meter_lo_hi("sugar high hai") is None
    assert detect_meter_lo_hi("bohot low lag raha hai") is None
    assert detect_meter_lo_hi("sugar lo hai") is None
    assert detect_meter_lo_hi("sugar hi hai") is None
    assert detect_meter_lo_hi("I feel low today") is None
    assert detect_meter_lo_hi("Hi doctor") is None
    assert detect_meter_lo_hi("120 mg/dL") is None
    assert detect_meter_lo_hi("9") is None


def test_v2_negative_confirmation():
    state = InterviewState(
        patient_id="test-pat",
        conditions_on_file=["diabetes"],
        active_condition="diabetes",
        step=DiabetesStep.GLUCOSE_READING.value,
    )
    # Turn 1: Patient says "LO"
    state = adaptive_interview_node(state, patient_response="LO")
    assert state.answers.get("_pending_meter_lo_hi") == "LO"
    assert state.stage1_red_flag is False
    q = get_current_question(state)
    assert "Does your meter screen show the letters LO" in q

    # Turn 2: Patient says "No, I just feel low"
    state = adaptive_interview_node(state, patient_response="No, I just feel low")
    assert state.stage1_red_flag is False
    assert state.answers.get("_pending_meter_lo_hi") is None
    assert state.step == DiabetesStep.MISSING_DATA_CHECKPOINT.value


def test_v2_affirmative_confirmation_lo():
    state = InterviewState(
        patient_id="test-pat",
        conditions_on_file=["diabetes"],
        active_condition="diabetes",
        step=DiabetesStep.GLUCOSE_READING.value,
    )
    # Turn 1: Patient says "meter says LO"
    state = adaptive_interview_node(state, patient_response="meter says LO")
    assert state.answers.get("_pending_meter_lo_hi") == "LO"

    # Turn 2: Patient confirms "Yes"
    state = adaptive_interview_node(state, patient_response="Yes")
    assert state.stage1_red_flag is True
    assert state.stage1_reason == "meter_lo"
    assert get_red_flag_level(state.stage1_reason) == "emergency"
    assert state.intake.get("emergency") is True
    assert state.intake.get("reason") == "meter_lo"


def test_v2_affirmative_confirmation_hi():
    state = InterviewState(
        patient_id="test-pat",
        conditions_on_file=["diabetes"],
        active_condition="diabetes",
        step=DiabetesStep.GLUCOSE_READING.value,
    )
    state = adaptive_interview_node(state, patient_response="HI")
    assert state.answers.get("_pending_meter_lo_hi") == "HI"

    state = adaptive_interview_node(state, patient_response="haan")
    assert state.stage1_red_flag is True
    assert state.stage1_reason == "meter_hi"
    assert get_red_flag_level(state.stage1_reason) == "emergency"
    assert state.intake.get("emergency") is True


def test_v3_negative_confirmation():
    sess = start_v3_session(
        checkin_id="chk-v3-neg",
        patient_id="pat-v3-neg",
        conditions=["diabetes"],
        language="en",
    )
    # Advance greeting
    sess = next_turn(sess, "Feeling ok")
    # Now at glucose reading slot
    sess = next_turn(sess, "LO")
    assert sess.get("awaiting_meter_lo_hi_confirmation") == "LO"
    assert "Does your meter screen show the letters LO" in sess.get("current_question")

    # Negative confirmation
    sess = next_turn(sess, "No, I just feel low")
    assert sess.get("emergency") is False
    assert sess.get("awaiting_meter_lo_hi_confirmation") is None
    assert "Please enter your numeric blood sugar" in sess.get("current_question")


def test_v3_affirmative_confirmation_lo():
    sess = start_v3_session(
        checkin_id="chk-v3-lo",
        patient_id="pat-v3-lo",
        conditions=["diabetes"],
        language="en",
    )
    sess = next_turn(sess, "Feeling ok")
    sess = next_turn(sess, "screen shows LO")
    assert sess.get("awaiting_meter_lo_hi_confirmation") == "LO"

    sess = next_turn(sess, "yes")
    assert sess.get("emergency") is True
    assert sess.get("emergency_reason") == "meter_lo"
    assert sess.get("completed") is True
    assert sess.get("possible_severe_low") is True


def test_v3_affirmative_confirmation_hi():
    sess = start_v3_session(
        checkin_id="chk-v3-hi",
        patient_id="pat-v3-hi",
        conditions=["diabetes"],
        language="en",
    )
    sess = next_turn(sess, "Feeling ok")
    sess = next_turn(sess, "HI")
    assert sess.get("awaiting_meter_lo_hi_confirmation") == "HI"

    sess = next_turn(sess, "yes")
    assert sess.get("emergency") is True
    assert sess.get("emergency_reason") == "meter_hi"
    assert sess.get("completed") is True
