import pytest
from agents.interview_v3_runner import start_v3_session, next_turn


def test_fasting_symptoms_free_text_symptoms():
    """Verify that free-text symptoms at fasting_symptoms are recognized as yes and recorded as findings."""
    session = start_v3_session(
        checkin_id="test_fast_1",
        patient_id="pat_fast_1",
        conditions=["diabetes"],
        on_insulin_or_sulfonylurea=True,
        language="en",
    )
    # Fasting patient
    session["known_slots"]["is_fasting_today"] = True
    session["step"] = "fasting_symptoms"

    res = next_turn(session, "Had shakiness and sweating around 2pm")
    assert session["known_slots"].get("fasting_symptoms") is True
    # Verify findings recorded
    finding_kinds = {f["kind"] for f in session.get("findings", [])}
    assert "low_sugar_episode" in finding_kinds or len(session.get("findings", [])) > 0


def test_fasting_symptoms_broke_fast():
    """Verify that 'roza tod diya / broke my fast' is understood as yes with fasting_broke_fast=True."""
    session = start_v3_session(
        checkin_id="test_fast_2",
        patient_id="pat_fast_2",
        conditions=["diabetes"],
        on_insulin_or_sulfonylurea=True,
        language="roman_ur",
    )
    session["known_slots"]["is_fasting_today"] = True
    session["step"] = "fasting_symptoms"

    res = next_turn(session, "Roza tod kar meetha paani piya")
    assert session["known_slots"].get("fasting_symptoms") is True
    assert session["known_slots"].get("fasting_broke_fast") is True
    assert session.get("fasting_broke_fast") is True


def test_global_loop_guard_max_two_attempts():
    """Verify that the same step is asked at most 2 times (original + 1 clarify), then marked unclear and moves on."""
    session = start_v3_session(
        checkin_id="test_loop_1",
        patient_id="pat_loop_1",
        conditions=["diabetes"],
        on_insulin_or_sulfonylurea=True,
        language="en",
    )
    # Set step to a safety item
    session["step"] = "hypo_symptoms_acute"
    session["turn_count"] = 1

    # Turn 1: Original ask answered with unknown/unclear
    res1 = next_turn(session, "not sure maybe")
    assert res1.get("needs_clinician_flag") or res1.get("safety_clarify_slot") == "hypo_symptoms_acute"
    assert session["step_attempt_counts"]["hypo_symptoms_acute"] == 1

    # Turn 2: Clarification answered with unknown/unclear again
    res2 = next_turn(session, "still have no idea")
    assert session["step_attempt_counts"]["hypo_symptoms_acute"] == 2
    assert session["known_slots"]["hypo_symptoms_acute"] in ("unknown", "unclear")
    assert session.get("needs_clinician_flag") is True
    # Crucially, step must have moved on and NOT be hypo_symptoms_acute again
    assert session["step"] != "hypo_symptoms_acute"
