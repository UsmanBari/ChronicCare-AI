import pytest

from main import calculate_age, validate_date_of_birth


def test_leap_day_date_of_birth():
    dob = "2004-02-29"
    as_of_date = "2026-03-01"

    cleaned_dob, age = validate_date_of_birth(
        dob,
        as_of_date=as_of_date,
    )

    assert cleaned_dob == "2004-02-29"
    assert age == 22


def test_birthday_today():
    dob = "2000-10-13"
    as_of_date = "2026-10-13"

    age = calculate_age(dob, as_of_date=as_of_date)

    assert age == 26


def test_birthday_tomorrow():
    dob = "2000-10-14"
    as_of_date = "2026-10-13"

    age = calculate_age(dob, as_of_date=as_of_date)

    assert age == 25


def test_future_date_of_birth_is_rejected():
    dob = "2027-01-01"
    as_of_date = "2026-10-13"

    with pytest.raises(ValueError, match="invalid_date_of_birth"):
        validate_date_of_birth(
            dob,
            as_of_date=as_of_date,
        )


def test_exactly_eighteen_is_accepted():
    dob = "2008-10-13"
    as_of_date = "2026-10-13"

    cleaned_dob, age = validate_date_of_birth(
        dob,
        as_of_date=as_of_date,
    )

    assert cleaned_dob == "2008-10-13"
    assert age == 18


def test_one_day_before_eighteen_is_rejected():
    dob = "2008-10-14"
    as_of_date = "2026-10-13"

    with pytest.raises(ValueError, match="adults_only"):
        validate_date_of_birth(
            dob,
            as_of_date=as_of_date,
        )