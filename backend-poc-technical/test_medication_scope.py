from data_sources.models import NormalizedMedication
from data_sources.medication_scope import select_chronic_care_medications


def make_medication(
    name,
    status="active",
    timestamp="2026-10-13T10:00:00",
    record_id="med-1",
):
    return NormalizedMedication(
        patient_id="patient-1",
        medication_name=name,
        status=status,
        dosage="500 mg",
        timestamp=timestamp,
        source="local",
        source_record_id=record_id,
    )


def test_inactive_medication_is_dropped():
    medications = [
        make_medication("Metformin", status="stopped")
    ]

    result = select_chronic_care_medications(medications)

    assert result == []


def test_non_chronic_medication_is_dropped():
    medications = [
        make_medication("Paracetamol")
    ]

    result = select_chronic_care_medications(medications)

    assert result == []


def test_duplicate_medication_names_are_removed():
    medications = [
        make_medication(
            "Metformin",
            timestamp="2026-10-12T10:00:00",
            record_id="old",
        ),
        make_medication(
            "metformin",
            timestamp="2026-10-13T10:00:00",
            record_id="new",
        ),
    ]

    result = select_chronic_care_medications(medications)

    assert len(result) == 1
    assert result[0].source_record_id == "new"


def test_medications_are_sorted_newest_first():
    medications = [
        make_medication(
            "Metformin",
            timestamp="2026-10-11T10:00:00",
            record_id="old",
        ),
        make_medication(
            "Amlodipine",
            timestamp="2026-10-13T10:00:00",
            record_id="new",
        ),
        make_medication(
            "Losartan",
            timestamp="2026-10-12T10:00:00",
            record_id="middle",
        ),
    ]

    result = select_chronic_care_medications(medications)

    assert [med.source_record_id for med in result] == [
        "new",
        "middle",
        "old",
    ]


def test_medication_list_is_capped_at_eight():
    medication_names = [
        "Metformin",
        "Glimepiride",
        "Gliclazide",
        "Sitagliptin",
        "Amlodipine",
        "Losartan",
        "Ramipril",
        "Atenolol",
        "Valsartan",
        "Telmisartan",
    ]

    medications = [
        make_medication(
            name,
            timestamp=f"2026-10-{index + 1:02d}T10:00:00",
            record_id=f"med-{index}",
        )
        for index, name in enumerate(medication_names)
    ]

    result = select_chronic_care_medications(medications)

    assert len(result) == 8


def test_empty_input_returns_empty_list():
    result = select_chronic_care_medications([])

    assert result == []