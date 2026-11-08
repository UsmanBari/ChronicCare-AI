"""
Unit and Integration Tests for Rule R4: Vomiting and Fluids/Medicines Inability Red-Flag Elevation.

Covers:
1. 'can't keep fluids down' -> EMERGENCY
2. 'can't keep my medicines down' -> EMERGENCY
3. 'paani bhi nahi ruk raha' -> EMERGENCY
4. 'dawa ulti mein nikal jati hai' -> EMERGENCY
5. Non-stop vomiting ('vomiting nonstop') + follow-up YES -> EMERGENCY
6. Non-stop vomiting ('vomiting nonstop') + follow-up NO -> URGENT
7. Both v2 and v3 engine verification
"""

import pytest
from agents.adaptive_interview_agent import (
    InterviewState,
    DiabetesStep,
    HypertensionStep,
    adaptive_interview_node,
    run_stage1_red_flag_screen as screen_rf,
    get_red_flag_level,
    get_current_question,
)
from agents.interview_v3_runner import (
    start_v3_session,
    next_turn,
)


def test_unable_to_keep_fluids_direct_emergencies():
    cases = [
        "can't keep fluids down",
        "can't keep my medicines down",
        "cannot keep medicines down",
        "paani bhi nahi ruk raha",
        "dawa ulti mein nikal jati hai",
        "throwing up everything",
        "پانی بھی نہیں رک رہا",
        "دوائی نہیں رک رہی",
    ]
    for text in cases:
        flagged, reason = screen_rf(text)
        assert flagged is True, f"Failed to flag: {text}"
        assert reason == "unable_to_keep_fluids", f"Wrong category for {text}: {reason}"
        assert get_red_flag_level(reason) == "emergency", f"Expected emergency for {text}"


def test_v2_unable_to_keep_fluids_immediate_emergency():
    state = InterviewState(
        patient_id="pat-v2-fluids",
        conditions_on_file=["diabetes"],
        active_condition="diabetes",
        step=DiabetesStep.GREETING.value,
    )
    next_st = adaptive_interview_node(state, patient_response="I can't keep fluids down")
    assert next_st.stage1_red_flag is True
    assert next_st.stage1_reason == "unable_to_keep_fluids"
    assert next_st.intake.get("emergency") is True
    assert next_st.intake.get("reason") == "unable_to_keep_fluids"


def test_v2_unable_to_keep_medicines_immediate_emergency():
    state = InterviewState(
        patient_id="pat-v2-meds",
        conditions_on_file=["hypertension"],
        active_condition="hypertension",
        step=HypertensionStep.GREETING.value,
    )
    next_st = adaptive_interview_node(state, patient_response="dawa ulti mein nikal jati hai")
    assert next_st.stage1_red_flag is True
    assert next_st.stage1_reason == "unable_to_keep_fluids"
    assert next_st.intake.get("emergency") is True


def test_v2_nonstop_vomiting_followup_yes_elevates_to_emergency():
    state = InterviewState(
        patient_id="pat-v2-vomit-yes",
        conditions_on_file=["diabetes"],
        active_condition="diabetes",
        step=DiabetesStep.GREETING.value,
    )
    # Turn 1: Patient reports nonstop vomiting
    next_st = adaptive_interview_node(state, patient_response="I have been vomiting nonstop")
    assert next_st.stage1_red_flag is False
    assert next_st.answers.get("_pending_vomiting_followup") is True
    q = get_current_question(next_st)
    assert "Are you vomiting blood or dark material" in q

    # Turn 2: Patient answers YES
    final_st = adaptive_interview_node(next_st, patient_response="Yes, I feel very dizzy")
    assert final_st.stage1_red_flag is True
    assert final_st.stage1_reason == "unable_to_keep_fluids"
    assert final_st.intake.get("emergency") is True


def test_v2_nonstop_vomiting_followup_no_stays_urgent():
    state = InterviewState(
        patient_id="pat-v2-vomit-no",
        conditions_on_file=["diabetes"],
        active_condition="diabetes",
        step=DiabetesStep.GREETING.value,
    )
    # Turn 1: Patient reports nonstop vomiting
    next_st = adaptive_interview_node(state, patient_response="musalsal ultiyan ho rahi hain")
    assert next_st.stage1_red_flag is False
    assert next_st.answers.get("_pending_vomiting_followup") is True

    # Turn 2: Patient answers NO
    final_st = adaptive_interview_node(next_st, patient_response="No, nothing like that")
    assert final_st.stage1_red_flag is True
    assert final_st.stage1_reason == "non_stop_vomiting"
    assert final_st.intake.get("emergency") is False
    assert final_st.intake.get("level") == "urgent"


def test_v3_unable_to_keep_fluids_immediate_emergency():
    sess = start_v3_session(
        checkin_id="chk-v3-fluids",
        patient_id="pat-v3-fluids",
        conditions=["diabetes"],
        language="en",
    )
    sess = next_turn(sess, "can't keep my medicines down")
    assert sess.get("emergency") is True
    assert sess.get("emergency_reason") == "unable_to_keep_fluids"
    assert sess.get("completed") is True


def test_v3_nonstop_vomiting_followup_yes_elevates_to_emergency():
    sess = start_v3_session(
        checkin_id="chk-v3-v-yes",
        patient_id="pat-v3-v-yes",
        conditions=["diabetes"],
        language="en",
    )
    # Turn 1: nonstop vomiting triggers follow-up
    sess = next_turn(sess, "vomiting all day")
    assert sess.get("awaiting_vomiting_followup") is True
    assert "Are you vomiting blood or dark material" in sess.get("current_question")

    # Turn 2: Yes
    sess = next_turn(sess, "yes")
    assert sess.get("emergency") is True
    assert sess.get("emergency_reason") == "unable_to_keep_fluids"
    assert sess.get("completed") is True


def test_v3_nonstop_vomiting_followup_no_stays_urgent():
    sess = start_v3_session(
        checkin_id="chk-v3-v-no",
        patient_id="pat-v3-v-no",
        conditions=["diabetes"],
        language="en",
    )
    sess = next_turn(sess, "vomiting non-stop")
    assert sess.get("awaiting_vomiting_followup") is True

    # Turn 2: No
    sess = next_turn(sess, "no")
    assert sess.get("emergency") is False
    assert sess.get("urgent") is True
    assert sess.get("needs_clinician_flag") is True
    assert sess.get("completed") is True
