"""
Unit Tests for Age Calculation, DOB Boundaries, and Negation-Aware Pregnancy Detection.
"""

from datetime import date
import pytest

from data_sources.validation import (
    calculate_age,
    validate_date_of_birth,
    detect_pregnancy_statement,
)


def test_age_exact_18_today():
    ref_date = date(2026, 10, 7)
    # Born exactly 18 years ago today
    dob = "2008-10-07"
    age = calculate_age(dob, as_of_date=ref_date)
    assert age == 18
    clean_dob, age_val = validate_date_of_birth(dob, as_of_date=ref_date)
    assert clean_dob == "2008-10-07"
    assert age_val == 18


def test_age_18_minus_one_day_refused():
    ref_date = date(2026, 10, 7)
    # Born tomorrow 18 years ago -> still 17 today
    dob = "2008-10-08"
    assert calculate_age(dob, as_of_date=ref_date) == 17
    with pytest.raises(ValueError, match="adults_only"):
        validate_date_of_birth(dob, as_of_date=ref_date)


def test_age_leap_day_feb_29():
    # Born on Feb 29, 2004 (leap year)
    dob = "2004-02-29"
    # In non-leap year 2022 on Feb 28 -> age is 17 (1 day before 18th anniversary)
    assert calculate_age(dob, as_of_date=date(2022, 2, 28)) == 17
    # In non-leap year 2022 on March 1 -> age is 18
    assert calculate_age(dob, as_of_date=date(2022, 3, 1)) == 18
    # In leap year 2024 on Feb 29 -> age is 20
    assert calculate_age(dob, as_of_date=date(2024, 2, 29)) == 20


def test_age_future_date_refused():
    ref_date = date(2026, 10, 7)
    with pytest.raises(ValueError, match="invalid_date_of_birth"):
        calculate_age("2026-10-08", as_of_date=ref_date)
    with pytest.raises(ValueError, match="invalid_date_of_birth"):
        validate_date_of_birth("2027-01-01", as_of_date=ref_date)


def test_age_older_than_120_refused():
    ref_date = date(2026, 10, 7)
    # 121 years old
    dob = "1905-10-06"
    with pytest.raises(ValueError, match="invalid_date_of_birth"):
        calculate_age(dob, as_of_date=ref_date)
    with pytest.raises(ValueError, match="invalid_date_of_birth"):
        validate_date_of_birth(dob, as_of_date=ref_date)

    # Exactly 120 years old today is allowed
    dob_120 = "1906-10-07"
    assert calculate_age(dob_120, as_of_date=ref_date) == 120
    clean_dob, age_120 = validate_date_of_birth(dob_120, as_of_date=ref_date)
    assert clean_dob == "1906-10-07"
    assert age_120 == 120


def test_age_malformed_and_boundary_dates():
    ref_date = date(2026, 10, 7)
    for bad_date in ["not-a-date", "2000-02-30", "1990/01/01", "", "2000-13-01", "2000-00-00"]:
        with pytest.raises(ValueError, match="invalid_date_of_birth"):
            calculate_age(bad_date, as_of_date=ref_date)
        with pytest.raises(ValueError, match="invalid_date_of_birth"):
            validate_date_of_birth(bad_date, as_of_date=ref_date)

    # Year-end and month-end boundaries
    assert calculate_age("2000-12-31", as_of_date=date(2026, 12, 30)) == 25
    assert calculate_age("2000-12-31", as_of_date=date(2026, 12, 31)) == 26
    assert calculate_age("2000-01-01", as_of_date=date(2026, 1, 1)) == 26


def test_pregnancy_affirmation_detection():
    # Affirmatory phrases
    assert detect_pregnancy_statement("I am pregnant") is True
    assert detect_pregnancy_statement("Found out I am pregnant today") is True
    assert detect_pregnancy_statement("My pregnancy test came back positive") is True
    assert detect_pregnancy_statement("I'm expecting a baby next month") is True
    assert detect_pregnancy_statement("میں حاملہ ہوں") is True


def test_pregnancy_negation_awareness():
    # Negated phrases must NOT trigger
    assert detect_pregnancy_statement("I am not pregnant") is False
    assert detect_pregnancy_statement("Not pregnant") is False
    assert detect_pregnancy_statement("Never been pregnant") is False
    assert detect_pregnancy_statement("I am definitely not expecting a baby") is False
    assert detect_pregnancy_statement("No pregnancy") is False
    assert detect_pregnancy_statement("Without pregnancy issues") is False
    # Irrelevant phrases
    assert detect_pregnancy_statement("My blood pressure was 140/90") is False
    assert detect_pregnancy_statement("Took my metformin this morning") is False
