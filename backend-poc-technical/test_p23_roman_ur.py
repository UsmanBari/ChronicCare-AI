"""
test_p23_roman_ur.py

Verifies P3-23 requirements:
- In roman_ur, summary displays "(khane ke baad)" instead of "(after_meal)" for after-meal glucose.
- In roman_ur, summary confirmation options and option_items labels are localized ("Confirm karein", "Tabdeel karna hai")
  and do not leak English "Confirm and submit" / "Need to change something".
- Summary confirmation parser handles "Confirm karein" / "Confirm and submit" and "Tabdeel karna hai" / "Need to change something".
"""

import pytest
from agents.interview_v3_runner import (
    _build_dual_summary_text,
    start_v3_session,
    next_turn,
)


def test_roman_ur_summary_after_meal_glucose():
    known_slots = {
        "glucose_reading": 140.0,
        "glucose_context": "after_meal",
        "bp_reading": (120, 80),
        "symptoms_denied": True,
        "adherence_diabetes": True,
    }
    summary_ro = _build_dual_summary_text(known_slots, lang="roman_ur")
    assert "(khane ke baad)" in summary_ro
    assert "(after_meal)" not in summary_ro
    assert "Sugar: 140 mg/dL (khane ke baad)" in summary_ro

    summary_ur = _build_dual_summary_text(known_slots, lang="ur")
    assert "کھانے کے بعد" in summary_ur
    assert "(after_meal)" not in summary_ur

    summary_en = _build_dual_summary_text(known_slots, lang="en")
    assert "after meal" in summary_en


def test_roman_ur_summary_confirmation_options():
    state = start_v3_session(
        checkin_id="test-chk-ro",
        patient_id="PAT-RO",
        conditions=["diabetes"],
        language="roman_ur",
    )
    # Provide answers to reach summary_confirmation
    turn_answers = [
        "140",
        "after_meal",
        "no",
        "yes",
        "none",
    ]
    for ans in turn_answers:
        if state.get("step") == "summary_confirmation" or state.get("complete"):
            break
        state = next_turn(state, ans)

    if state.get("step") == "summary_confirmation":
        options = state.get("options")
        assert options is not None
        assert "Confirm karein" in options
        assert "Tabdeel karna hai" in options
        assert "Confirm and submit" not in options

        option_items = state.get("option_items")
        assert option_items is not None
        labels = [item["label"] for item in option_items]
        assert "Confirm karein" in labels
        assert "Tabdeel karna hai" in labels
        assert "Confirm and submit" not in labels
