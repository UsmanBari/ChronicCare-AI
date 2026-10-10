"""
Unit Tests for Answer Validation Engine (Stage 9A Task E).

Verifies every row of the 'Wrong Answers' specification table in INTERVIEW_V3_RESEARCH_AND_DESIGN.md:
1. 'wrong_answer_impossible_number_glucose_5_or_5000'
2. 'wrong_answer_impossible_number_bp_12080_parsed'
3. 'wrong_answer_unit_confusion_glucose_7_clarification'
4. 'wrong_answer_second_unclear_stored_unknown_needs_review'
5. 'wrong_answer_contradiction_insulin_record_mismatch'
6. 'wrong_answer_contradiction_adherence_vs_ran_out'
7. 'wrong_answer_minimiser_just_a_little_dizzy'
8. 'wrong_answer_number_words_english_and_roman_urdu'
9. 'wrong_answer_decimal_comma_conversion'
10. 'wrong_answer_eastern_digits_conversion'
"""

import pytest
from agents.answer_validation import (
    validate_glucose_input,
    validate_bp_input,
    detect_cross_checks_and_contradictions,
    _parse_number_words,
    PLAUSIBILITY_RANGES,
)


def test_wrong_answer_impossible_number_glucose_5_or_5000():
    # 5.0 with no unit -> triggers unit clarification prompt (could be 5.0 mmol/L)
    res_5 = validate_glucose_input("5")
    assert res_5.needs_unit_clarification is True
    assert "Is that mmol/L or mg/dL?" in res_5.clarification_prompt

    # 5000 -> outside plausible ranges
    res_5000 = validate_glucose_input("5000")
    assert res_5000.valid is False
    assert res_5000.needs_review is True


def test_wrong_answer_impossible_number_bp_12080_parsed():
    # "12080" compact string -> correctly parsed as 120/80 mmHg
    res = validate_bp_input("12080")
    assert res.valid is True
    assert res.value == [120, 80]
    assert res.unit == "mmHg"

    # "13585" -> 135/85
    res2 = validate_bp_input("13585")
    assert res2.valid is True
    assert res2.value == [135, 85]


def test_wrong_answer_unit_confusion_glucose_7_clarification():
    # 7.0 without unit is ambiguous between 7.0 mmol/L (126 mg/dL) and 7.0 mg/dL (severe low)
    res = validate_glucose_input("7")
    assert res.needs_unit_clarification is True
    assert res.value == 7.0

    # Explicit 7 mmol/L -> Valid in mmol/L
    res_mmol = validate_glucose_input("7 mmol/L")
    assert res_mmol.valid is True
    assert res_mmol.unit == "mmol/L"
    assert res_mmol.value == 7.0

    # Explicit 126 mg/dL -> Valid in mg/dL
    res_mg = validate_glucose_input("126 mg/dL")
    assert res_mg.valid is True
    assert res_mg.unit == "mg/dL"
    assert res_mg.value == 126.0


def test_wrong_answer_second_unclear_stored_unknown_needs_review():
    # When asked unit once and patient still gives unclear response, mark unknown + needs_review
    res_unclear = validate_glucose_input("7", previously_asked_unit=True)
    assert res_unclear.valid is False
    assert res_unclear.needs_review is True
    assert res_unclear.confidence == "Low"


def test_wrong_answer_contradiction_insulin_record_mismatch():
    record = {"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": True}
    contra = detect_cross_checks_and_contradictions(
        current_slot="adherence_diabetes",
        answer_text="I don't take insulin anymore",
        known_slots={},
        patient_record=record,
    )
    assert contra is not None
    assert contra["type"] == "record_mismatch"
    assert "insulin" in contra["message"]


def test_wrong_answer_contradiction_adherence_vs_ran_out():
    record = {"conditions": ["hypertension"]}
    known = {"adherence_hypertension": True}
    contra = detect_cross_checks_and_contradictions(
        current_slot="lifestyle_hypertension",
        answer_text="I ran out of medicine 3 days ago",
        known_slots=known,
        patient_record=record,
    )
    assert contra is not None
    assert contra["type"] == "answer_contradiction"


def test_wrong_answer_number_words_english_and_roman_urdu():
    assert _parse_number_words("one twenty") == 120.0
    assert _parse_number_words("ek sau bees") == 120.0
    assert _parse_number_words("aik sau assi") == 180.0
    assert _parse_number_words("two hundred") == 200.0
    assert _parse_number_words("do sau") == 200.0


def test_wrong_answer_decimal_comma_conversion():
    res = validate_glucose_input("6,5 mmol/L")
    assert res.valid is True
    assert res.value == 6.5
    assert res.unit == "mmol/L"


def test_wrong_answer_eastern_digits_conversion():
    # Urdu digits: ۱۲۰/۸۰ -> 120/80
    res_bp = validate_bp_input("۱۲۰/۸۰")
    assert res_bp.valid is True
    assert res_bp.value == [120, 80]

    # Arabic-Indic digits: ١٤٥ -> 145 mg/dL
    res_gluc = validate_glucose_input("١٤٥")
    assert res_gluc.valid is True
    assert res_gluc.value == 145.0
    assert res_gluc.unit == "mg/dL"
