"""
test_p24_no_duplicate_questions.py

Verifies P3-24 requirements:
- After the patient already gave a reading, do not ask "Do you have a glucometer?" / "BP cuff?"
  (ask only when the reading is missing).
- After "Feeling fine today" do not ask "How are you feeling today?" again.
"""

import pytest
from agents.interview_v3_runner import (
    start_v3_session,
    next_turn,
)


def test_after_reading_do_not_ask_device():
    # Dual patient with glucose provided
    st = start_v3_session(
        checkin_id="test-chk-dev-1",
        patient_id="PAT-DEV-1",
        conditions=["diabetes", "hypertension"],
        opening_note="Fasting sugar was 110 mg/dL",
    )
    # Check that glucometer question is NOT asked
    curr_q = (st.get("current_question") or "").lower()
    assert "glucometer" not in curr_q, f"Asked glucometer despite glucose reading: {curr_q}"

    # Feed answers through interview turns
    for _ in range(6):
        if st.get("step") == "summary_confirmation" or st.get("complete"):
            break
        q_text = (st.get("current_question") or "").lower()
        assert "glucometer" not in q_text, f"Asked glucometer during interview: {q_text}"
        st = next_turn(st, "no")


def test_after_bp_reading_do_not_ask_cuff():
    # Hypertension patient with BP provided
    st = start_v3_session(
        checkin_id="test-chk-cuff-1",
        patient_id="PAT-CUFF-1",
        conditions=["hypertension"],
        opening_note="BP 124/80 today",
    )
    curr_q = (st.get("current_question") or "").lower()
    assert "cuff" not in curr_q, f"Asked cuff despite BP reading: {curr_q}"

    for _ in range(6):
        if st.get("step") == "summary_confirmation" or st.get("complete"):
            break
        q_text = (st.get("current_question") or "").lower()
        assert "cuff" not in q_text, f"Asked cuff during interview: {q_text}"
        st = next_turn(st, "no")


def test_after_feeling_fine_do_not_ask_greeting():
    # 1. Feeling fine in opening note
    st1 = start_v3_session(
        checkin_id="test-chk-feel-1",
        patient_id="PAT-FEEL-1",
        conditions=["diabetes"],
        opening_note="Feeling fine today",
    )
    q1 = (st1.get("current_question") or "").lower()
    assert "how are you feeling" not in q1, f"Asked greeting after 'Feeling fine today' in note: {q1}"
    assert "kaisa mehsoos" not in q1

    # 2. Feeling fine in first turn
    st2 = start_v3_session(
        checkin_id="test-chk-feel-2",
        patient_id="PAT-FEEL-2",
        conditions=["diabetes"],
    )
    # If the first question was greeting, answer it with 'Feeling fine today'
    st2_next = next_turn(st2, "Feeling fine today")
    q2 = (st2_next.get("current_question") or "").lower()
    assert "how are you feeling" not in q2, f"Repeated greeting after 'Feeling fine today': {q2}"

    # 3. Roman Urdu 'theek hoon'
    st3 = start_v3_session(
        checkin_id="test-chk-feel-3",
        patient_id="PAT-FEEL-3",
        conditions=["hypertension"],
        opening_note="aaj theek hoon",
        language="roman_ur",
    )
    q3 = (st3.get("current_question") or "").lower()
    assert "kaisa mehsoos" not in q3, f"Asked greeting in Roman Urdu after 'theek hoon': {q3}"
