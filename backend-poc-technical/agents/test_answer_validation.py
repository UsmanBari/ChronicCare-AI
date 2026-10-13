import pytest
from agents.answer_validation import (
    validate_bp_input,
    validate_glucose_input,
)


def test_bp_urdu_digits():
    """Shows that Eastern Arabic / Urdu digits (۱۲۰/۸۰) are correctly translated and parsed for BP."""
    result = validate_bp_input("۱۲۰/۸۰")
    assert result.valid is True
    assert result.value == [120, 80]
    assert result.unit == "mmHg"


def test_bp_mixed_digits():
    """Shows that mixed English and Urdu/Arabic-Indic digits (12۰/80) are successfully normalized and validated."""
    result = validate_bp_input("12۰/80")
    assert result.valid is True
    assert result.value == [120, 80]
    assert result.unit == "mmHg"


def test_glucose_roman_urdu_compound_words():
    """Shows that compound Roman Urdu number words ('ek sau bees') parse correctly into 120 mg/dL."""
    result = validate_glucose_input("ek sau bees")
    assert result.valid is True
    assert result.value == 120.0
    assert result.unit == "mg/dL"


def test_glucose_do_sau_without_unit():
    """Shows that 'do sau' (200) without a unit defaults to mg/dL since it is well above 40."""
    result = validate_glucose_input("do sau")
    assert result.valid is True
    assert result.value == 200.0
    assert result.unit == "mg/dL"


@pytest.mark.xfail(
    reason="Known gap: a spoken number word followed by a unit ('do sau mg/dl') is not parsed yet. Planned for Iteration 2.",
    strict=False,
)
def test_glucose_do_sau_with_unit():
    """Shows that 'do sau mg/dl' correctly parses the number word and respects the explicit unit."""
    result = validate_glucose_input("do sau mg/dl")
    assert result.valid is True
    assert result.value == 200.0
    assert result.unit == "mg/dL"


@pytest.mark.xfail(
    reason="Minimiser detection ('bas thora sa') is documented in module docstring but not yet implemented in validation functions."
)
def test_minimiser_phrase_bp():
    """Shows that minimiser phrases combined with BP inputs currently fail validation because text stripping only isolates digits."""
    result = validate_bp_input("bas thora sa 120/80")
    assert result.is_minimiser is True
    assert result.valid is True
    assert result.value == [120, 80]


def test_glucose_decimal_comma():
    """Shows that European decimal comma notation ('6,5 mmol/l') is normalized to a dot and parsed correctly."""
    result = validate_glucose_input("6,5 mmol/l")
    assert result.valid is True
    assert result.value == 6.5
    assert result.unit == "mmol/L"


def test_glucose_seven_no_unit():
    """Shows that a glucose value of 7 with no unit falls in the 2.0-40.0 ambiguous range, triggering clarification."""
    result = validate_glucose_input("7")
    assert result.valid is False
    assert result.is_ambiguous is True
    assert result.needs_unit_clarification is True
    assert result.value == 7.0