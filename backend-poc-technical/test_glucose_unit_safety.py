"""
Unit Tests for Glucose Unit Safety Rule (Stage 9A-2 Task C).

Tests glucose safety across all critical boundaries:
- <= 40 without unit: asks unit once
- <= 40 with no unit response / repeated value: treats as POSSIBLE SEVERE LOW (Review level, low-sugar guidance, provider note, symptom questions continue)
- Values: 2, 7, 12, 35, 40, 41, 126 with and without units
- Eastern Arabic/Urdu digits
- 'I don't know' responses
"""

import pytest
from agents.answer_validation import validate_glucose_input


def test_glucose_boundaries_with_and_without_units():
    # 1. Glucose 2 without unit -> triggers unit clarification
    res_2 = validate_glucose_input("2")
    assert res_2.needs_unit_clarification is True
    assert res_2.value == 2.0

    # Glucose 2 mmol/L -> Valid in mmol/L (36.0 mg/dL)
    res_2_mmol = validate_glucose_input("2 mmol/L")
    assert res_2_mmol.valid is True
    assert res_2_mmol.unit == "mmol/L"
    assert res_2_mmol.value == 2.0

    # 2. Glucose 7 without unit -> triggers unit clarification
    res_7 = validate_glucose_input("7")
    assert res_7.needs_unit_clarification is True
    assert res_7.value == 7.0

    # Glucose 7 mmol/L -> Valid (126 mg/dL equivalent)
    res_7_mmol = validate_glucose_input("7 mmol/L")
    assert res_7_mmol.valid is True
    assert res_7_mmol.unit == "mmol/L"

    # 3. Glucose 12 without unit -> triggers unit clarification
    res_12 = validate_glucose_input("12")
    assert res_12.needs_unit_clarification is True
    assert res_12.value == 12.0

    # 4. Glucose 35 without unit -> triggers unit clarification
    res_35 = validate_glucose_input("35")
    assert res_35.needs_unit_clarification is True
    assert res_35.value == 35.0

    # 5. Glucose 40 without unit -> triggers unit clarification
    res_40 = validate_glucose_input("40")
    assert res_40.needs_unit_clarification is True
    assert res_40.value == 40.0

    # 6. Glucose 41 without unit -> defaults to mg/dL (above 40)
    res_41 = validate_glucose_input("41")
    assert res_41.valid is True
    assert res_41.unit == "mg/dL"
    assert res_41.value == 41.0
    assert res_41.needs_unit_clarification is False

    # 7. Glucose 126 without unit -> defaults to mg/dL
    res_126 = validate_glucose_input("126")
    assert res_126.valid is True
    assert res_126.unit == "mg/dL"
    assert res_126.value == 126.0


def test_glucose_unanswered_unit_possible_severe_low():
    # If asked once and patient gives the number again (or fails to clarify unit),
    # treat as POSSIBLE SEVERE LOW (<= 40 mg/dL)
    for val_str in ("2", "7", "12", "35", "40"):
        res = validate_glucose_input(val_str, previously_asked_unit=True)
        assert res.valid is False
        assert res.is_possible_severe_low is True
        assert res.needs_review is True
        assert res.confidence == "Low"
        assert res.review_reason == "glucose value unit unclear, possible low"
        assert "fast-acting sugar" in res.safety_guidance.lower()


def test_glucose_urdu_eastern_digits():
    # Urdu digit ۷ (7) without unit -> triggers unit clarification
    res_urdu_7 = validate_glucose_input("۷")
    assert res_urdu_7.needs_unit_clarification is True
    assert res_urdu_7.value == 7.0

    # Urdu digits ۴۰ (40) -> triggers unit clarification
    res_urdu_40 = validate_glucose_input("۴۰")
    assert res_urdu_40.needs_unit_clarification is True
    assert res_urdu_40.value == 40.0

    # Urdu digits ۱۲۶ (126) -> defaults to mg/dL
    res_urdu_126 = validate_glucose_input("۱۲۶")
    assert res_urdu_126.valid is True
    assert res_urdu_126.unit == "mg/dL"
    assert res_urdu_126.value == 126.0


def test_glucose_unknown_or_dont_know():
    # Patient says "I don't know" or "pata nahi"
    res_dont_know = validate_glucose_input("I don't know my sugar")
    assert res_dont_know.valid is False
    assert res_dont_know.is_unclear is True
    assert res_dont_know.needs_review is True

    res_ur_dont_know = validate_glucose_input("mujhe nahi pata")
    assert res_ur_dont_know.valid is False
    assert res_ur_dont_know.is_unclear is True
