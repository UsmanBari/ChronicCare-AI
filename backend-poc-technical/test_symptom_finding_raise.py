"""
Tests for Stage-2 Clinical Symptom Finding Raise (Rule R-S2-5)
Doctor Decision D7 (approved by the doctor on record, Nov 2026).
"""
import os
import pytest
from agents.final_triage import (
    decide_stage2,
    check_has_symptom_finding_triggers,
    get_stage2_patient_reason_text,
)


def test_flag_off_preserves_routine():
    """When SYMPTOM_FINDING_RAISE is disabled, symptoms do not raise Routine to Review."""
    state = {
        "answers": {"foot_problems": "I have an open sore on my left foot"},
    }
    flags = {"SYMPTOM_FINDING_RAISE": False}
    result = decide_stage2(rules_level="routine", state=state, flags=flags)
    assert result["final_level"] == "routine"
    assert result["raised"] is False
    assert "R-S2-5" not in result["triggered_rules"]


def test_flag_on_foot_ulcer_raises():
    """Positive foot ulcer/blister/wound raises routine to review."""
    state = {
        "answers": {"foot_problems": "I noticed an open blister and cut on my right heel"},
    }
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="routine", state=state, flags=flags)
    assert result["final_level"] == "review"
    assert result["raised"] is True
    assert "R-S2-5" in result["triggered_rules"]
    assert result["patient_reason_key"] == "symptom_reported_needs_review"


def test_flag_on_dose_change_raises():
    """Request to change/adjust/stop medication raises routine to review."""
    state = {
        "answers": {"medication": "Can I decrease my metformin dose because of an upset stomach?"},
    }
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="routine", state=state, flags=flags)
    assert result["final_level"] == "review"
    assert result["raised"] is True
    assert "R-S2-5" in result["triggered_rules"]


def test_flag_on_orthostatic_dizziness_raises():
    """Dizziness on standing up / getting out of bed raises routine to review."""
    state = {
        "answers": {"dizziness": "I feel dizzy every morning when getting out of bed and standing up"},
    }
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="routine", state=state, flags=flags)
    assert result["final_level"] == "review"
    assert result["raised"] is True
    assert "R-S2-5" in result["triggered_rules"]


def test_flag_on_low_mood_distress_raises():
    """Low mood, depression, or feeling overwhelmed raises routine to review."""
    state = {
        "answers": {"wellbeing": "Feeling down, low mood and exhausted dealing with diabetes"},
    }
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="routine", state=state, flags=flags)
    assert result["final_level"] == "review"
    assert result["raised"] is True
    assert "R-S2-5" in result["triggered_rules"]


def test_flag_on_recent_hypos_raises():
    """Hypo events past week raises routine to review."""
    state = {
        "answers": {"hypo_events_past_week": 2},
    }
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="routine", state=state, flags=flags)
    assert result["final_level"] == "review"
    assert result["raised"] is True
    assert "R-S2-5" in result["triggered_rules"]


def test_flag_on_sick_days_raises():
    """Sick day flags raise routine to review."""
    state = {
        "answers": {"sick_day_flags": True},
    }
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="routine", state=state, flags=flags)
    assert result["final_level"] == "review"
    assert result["raised"] is True
    assert "R-S2-5" in result["triggered_rules"]


def test_negative_answers_remain_routine():
    """Negative answers do not trigger symptom raise."""
    state = {
        "answers": {
            "foot_problems": "No cuts, feet are fine",
            "dizziness": "no dizziness",
            "sick_day_flags": "no",
        },
    }
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="routine", state=state, flags=flags)
    assert result["final_level"] == "routine"
    assert result["raised"] is False


def test_doctor_decision_d7_default_flag_is_true(monkeypatch):
    """Under Doctor Decision D7, default flag value is True when omitted."""
    monkeypatch.delenv("SYMPTOM_FINDING_RAISE", raising=False)
    state = {
        "answers": {"foot_problems": "Open sore on toe"},
    }
    # Pass flags=None so it uses environment default
    result = decide_stage2(rules_level="routine", state=state, flags=None)
    assert result["final_level"] == "review"
    assert result["raised"] is True
    assert "R-S2-5" in result["triggered_rules"]


def test_emergency_never_lowered():
    """Emergency is never lowered by Stage-2 (R-S2-0)."""
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="emergency", state=None, flags=flags)
    assert result["final_level"] == "emergency"
    assert result["raised"] is False
    assert result["triggered_rules"] == ["R-S2-0"]


def test_urgent_never_lowered():
    """Urgent is never lowered by Stage-2 (R-S2-0)."""
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="urgent", state=None, flags=flags)
    assert result["final_level"] == "urgent"
    assert result["raised"] is False
    assert result["triggered_rules"] == ["R-S2-0"]


def test_review_never_lowered():
    """Review is never lowered by Stage-2 (R-S2-0)."""
    flags = {"SYMPTOM_FINDING_RAISE": True}
    result = decide_stage2(rules_level="review", state=None, flags=flags)
    assert result["final_level"] == "review"
    assert result["raised"] is False
    assert result["triggered_rules"] == ["R-S2-0"]


def test_patient_reason_translations():
    """Reason text is available in EN, UR, and Roman Urdu."""
    key = "symptom_reported_needs_review"
    en = get_stage2_patient_reason_text(key, "en")
    ur = get_stage2_patient_reason_text(key, "ur")
    roman_ur = get_stage2_patient_reason_text(key, "roman_ur")

    assert "review" in en.lower()
    assert "جائزہ" in ur
    assert "review" in roman_ur.lower()
