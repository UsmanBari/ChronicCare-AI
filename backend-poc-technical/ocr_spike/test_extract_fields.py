"""
Hermetic Unit Tests for OCR Spike Field Extractor.

Tests deterministic extraction of HbA1c, glucose, blood pressure, and medications
from plain strings without requiring external OCR engines or dependencies.
"""

from __future__ import annotations

import pytest
from data_sources.ocr.extract_fields import (
    extract_fields,
    levenshtein_distance,
    match_medication_name,
)


def test_hba1c_with_space_before_percent():
    text = "Lab Report: HbA1c: 7.8 % (Normal < 5.7 %)"
    res = extract_fields(text)
    hba1c_fields = [f for f in res["fields"] if f["kind"] == "hba1c"]
    assert len(hba1c_fields) == 1
    assert hba1c_fields[0]["value"] == 7.8
    assert hba1c_fields[0]["unit"] == "%"
    assert "HbA1c" in hba1c_fields[0]["evidence"]
    assert hba1c_fields[0]["confidence"] == "High"


def test_hba1c_without_space_before_percent():
    text = "Glycated haemoglobin 8.1% observed"
    res = extract_fields(text)
    hba1c_fields = [f for f in res["fields"] if f["kind"] == "hba1c"]
    assert len(hba1c_fields) == 1
    assert hba1c_fields[0]["value"] == 8.1
    assert hba1c_fields[0]["unit"] == "%"


def test_hba1c_implausible_dropped_with_warning():
    text = "Patient A1c: 2.1 % and other patient HbA1c: 24.5 %"
    res = extract_fields(text)
    hba1c_fields = [f for f in res["fields"] if f["kind"] == "hba1c"]
    assert len(hba1c_fields) == 0
    assert len(res["warnings"]) >= 2
    assert any("2.1" in w for w in res["warnings"])
    assert any("24.5" in w for w in res["warnings"])


def test_glucose_mmol_conversion_and_fields():
    text = "Blood Glucose (Fasting): 7.2 mmol/L"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 7.2
    assert gluc_fields[0]["unit"] == "mmol/L"
    assert gluc_fields[0]["mg_dl"] == round(7.2 * 18.0, 1)  # 129.6
    assert gluc_fields[0]["context"] == "fasting"
    assert gluc_fields[0]["confidence"] == "High"


def test_glucose_mg_dl_kept():
    text = "Fasting Blood Sugar: 126 mg/dL"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 126.0
    assert gluc_fields[0]["unit"] == "mg/dL"
    assert gluc_fields[0]["context"] == "fasting"


def test_glucose_random_context():
    text = "Random Glucose: 160 mg/dl"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 160.0
    assert gluc_fields[0]["context"] == "random"


def test_glucose_postprandial_context():
    text = "Post-prandial blood sugar: 185 mg/dL"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 185.0
    assert gluc_fields[0]["context"] == "post-prandial"


def test_glucose_unit_missing_gets_low_confidence_and_warning():
    text = "Patient Fasting Glucose: 140"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 140.0
    assert gluc_fields[0]["unit"] is None
    assert gluc_fields[0]["confidence"] == "Low"
    assert any("unit missing" in w for w in res["warnings"])


def test_bp_accepted_within_bounds():
    text = "Vitals: BP: 148/92 mmHg observed at rest"
    res = extract_fields(text)
    bp_fields = [f for f in res["fields"] if f["kind"] == "bp"]
    assert len(bp_fields) == 1
    assert bp_fields[0]["value"] == [148, 92]
    assert bp_fields[0]["unit"] == "mmHg"
    assert bp_fields[0]["confidence"] == "High"
    assert "148/92" in bp_fields[0]["evidence"]


def test_bp_reversed_rejected():
    text = "Vitals: Blood pressure measured 80/120 mmHg"
    res = extract_fields(text)
    bp_fields = [f for f in res["fields"] if f["kind"] == "bp"]
    assert len(bp_fields) == 0
    assert any("reversed" in w.lower() for w in res["warnings"])


def test_bp_out_of_range_rejected():
    text = "BP: 290/180 mmHg"
    res = extract_fields(text)
    bp_fields = [f for f in res["fields"] if f["kind"] == "bp"]
    assert len(bp_fields) == 0
    assert len(res["warnings"]) >= 1


def test_levenshtein_distance_calculation():
    assert levenshtein_distance("metformin", "metformin") == 0
    assert levenshtein_distance("metf0rmin", "metformin") == 1
    assert levenshtein_distance("amlodipine", "amlodipne") == 1
    assert levenshtein_distance("losartan", "lisinopril") > 2


def test_levenshtein_slip_matching_medication():
    # 'Metf0rmin' (9 letters, dist 1)
    match = match_medication_name("Tab. Metf0rmin 500mg BD")
    assert match is not None
    assert match[0] == "metformin"


def test_levenshtein_slip_matching_amlodipine():
    match = match_medication_name("Amlodipne 5mg OD")
    assert match is not None
    assert match[0] == "amlodipine"


def test_non_chronic_drug_rejected():
    text = "Rx: 1. Tab. Amoxicillin 500 mg TDS\n2. Syp. Paracetamol 10 ml"
    res = extract_fields(text)
    med_fields = [f for f in res["fields"] if f["kind"] == "medication"]
    assert len(med_fields) == 0
    assert len(res["unmatched_lines"]) >= 1


def test_dose_and_frequency_parsing_standard():
    text = "1. Tab. Metformin 500 mg BD"
    res = extract_fields(text)
    med_fields = [f for f in res["fields"] if f["kind"] == "medication"]
    assert len(med_fields) == 1
    assert med_fields[0]["name"] == "metformin"
    assert med_fields[0]["dose"] == "500 mg"
    assert med_fields[0]["frequency"] == "BD"
    assert med_fields[0]["confidence"] == "High"


def test_dose_and_frequency_parsing_fractional_units():
    text = "Insulin glargine 10 units at night"
    res = extract_fields(text)
    med_fields = [f for f in res["fields"] if f["kind"] == "medication"]
    assert len(med_fields) == 1
    assert med_fields[0]["name"] == "insulin glargine"
    assert med_fields[0]["dose"] == "10 units"
    assert med_fields[0]["frequency"] == "at night"


def test_frequency_parsing_1_plus_0_plus_1():
    text = "Tab. Gliclazide 80mg 1+0+1"
    res = extract_fields(text)
    med_fields = [f for f in res["fields"] if f["kind"] == "medication"]
    assert len(med_fields) == 1
    assert med_fields[0]["name"] == "gliclazide"
    assert med_fields[0]["dose"] == "80mg"
    assert "1+0+1" in med_fields[0]["frequency"]


def test_frequency_parsing_once_daily():
    text = "Losartan 50 mg — once daily"
    res = extract_fields(text)
    med_fields = [f for f in res["fields"] if f["kind"] == "medication"]
    assert len(med_fields) == 1
    assert med_fields[0]["name"] == "losartan"
    assert med_fields[0]["dose"] == "50 mg"
    assert med_fields[0]["frequency"].lower() == "once daily"


def test_urdu_frequency_parsing():
    text = "Tab. Metformin 500 mg روزانہ دو بار"
    res = extract_fields(text)
    med_fields = [f for f in res["fields"] if f["kind"] == "medication"]
    assert len(med_fields) == 1
    assert med_fields[0]["name"] == "metformin"
    assert med_fields[0]["frequency"] == "روزانہ دو بار"


def test_unmatched_prescription_line_captured():
    text = "1. Tab. UnknownCure 250 mg OD\n2. Tab. Metformin 500 mg BD"
    res = extract_fields(text)
    assert len(res["fields"]) == 1
    assert res["fields"][0]["name"] == "metformin"
    assert any("UnknownCure" in line for line in res["unmatched_lines"])


def test_empty_string_returns_clean_structure():
    res = extract_fields("")
    assert res["fields"] == []
    assert res["warnings"] == []
    assert res["unmatched_lines"] == []


def test_evidence_string_always_present():
    text = """
    SAMPLE LAB
    HbA1c: 7.0 %
    Glucose: 130 mg/dL
    BP: 125/80 mmHg
    Rx: Tab. Metformin 500 mg BD
    """
    res = extract_fields(text)
    assert len(res["fields"]) == 4
    for field in res["fields"]:
        assert "evidence" in field
        assert len(field["evidence"].strip()) > 0



def test_ocr_slip_hba1c_letters():
    text = "HbAlc: 7.8% and HbA1.c: 8.5%"
    res = extract_fields(text)
    hba1c_fields = [f for f in res["fields"] if f["kind"] == "hba1c"]
    assert len(hba1c_fields) == 2
    assert {f["value"] for f in hba1c_fields} == {7.8, 8.5}


def test_cross_line_observation_table():
    text = "TEST\nGlycated haemoglobin\n8.1%\nBlood Pressure\n140/90 mmHg"
    res = extract_fields(text)
    kinds = {f["kind"] for f in res["fields"]}
    assert "hba1c" in kinds
    assert "bp" in kinds


def test_cholesterol_not_extracted_as_glucose():
    text = "Total Cholesterol: 195 mg/dL\nFasting Blood Glucose: 110 mg/dL"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 110.0


def test_medication_with_internal_whitespace():
    text = "Tab. Glime pinide 2mg 1+0+0\nTab. Empag liflozin 10mg OD"
    res = extract_fields(text)
    med_names = {f["name"] for f in res["fields"] if f["kind"] == "medication"}
    assert "glimepiride" in med_names
    assert "empagliflozin" in med_names


def test_medication_digit_ocr_slip():
    text = "Tab. Lisinopni1 10mg OD"
    res = extract_fields(text)
    med_names = {f["name"] for f in res["fields"] if f["kind"] == "medication"}
    assert "lisinopril" in med_names


def test_multiline_table_hba1c_extracted_without_percent_on_same_line():
    text = """
    Test Description
    Observed Value
    Unit
    Reference Range
    HbA1c (Glycated Haemoglobin)
    7.6
    %
    < 5.7 %
    """
    res = extract_fields(text)
    hba1c_fields = [f for f in res["fields"] if f["kind"] == "hba1c"]
    assert len(hba1c_fields) == 1
    assert hba1c_fields[0]["value"] == 7.6
    assert hba1c_fields[0]["unit"] == "%"


def test_reference_range_hyphen_never_extracted_as_glucose():
    text = "Fasting Blood Sugar\n148 mg/dL\nReference Interval: 70 - 100 mg/dL"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 148.0
    # 70 and 100 in the reference interval must NOT be extracted
    assert all(f["value"] not in (70.0, 100.0) for f in gluc_fields)


def test_reference_range_operator_never_extracted_as_glucose():
    text = "Random Blood Sugar: 215 mg/dL\nNormal: < 200 mg/dL"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 215.0
    # Threshold 200 must be excluded
    assert all(f["value"] != 200.0 for f in gluc_fields)


def test_reference_range_bp_never_extracted_as_patient_vitals():
    text = """
    Test Description Observed Value Unit Reference Range
    B.P 145/95 mmHg 120/80 mmHg
    """
    res = extract_fields(text)
    bp_fields = [f for f in res["fields"] if f["kind"] == "bp"]
    assert len(bp_fields) == 1
    assert bp_fields[0]["value"] == [145, 95]


def test_footnote_text_does_not_leak_glucose_keywords():
    text = """
    Random Blood Sugar 185 mg/dL
    Note: Hexokinase enzymatic methodology for Glucose determination.
    """
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 185.0


def test_random_blood_sugar_mmol_with_next_line_unit():
    text = """
    Random Blood Sugar (RBS)
    11.2
    mmol/L
    4.0 - 7.8 mmol/L
    """
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 11.2
    assert gluc_fields[0]["unit"] == "mmol/L"
    assert gluc_fields[0]["context"] == "random"
    assert gluc_fields[0]["mg_dl"] == round(11.2 * 18.0, 1)


def test_low_confidence_when_unit_missing_in_isolated_string():
    text = "Fasting Blood Sugar: 145"
    res = extract_fields(text)
    gluc_fields = [f for f in res["fields"] if f["kind"] == "glucose"]
    assert len(gluc_fields) == 1
    assert gluc_fields[0]["value"] == 145.0
    assert gluc_fields[0]["unit"] is None
    assert gluc_fields[0]["confidence"] == "Low"
    assert any("unit missing" in w for w in res["warnings"])


def test_scoring_counts_at_most_one_tp_per_sample_per_field(tmp_path):
    """Proves scoring logic counts at most 1 TP per sample per field; duplicate matches of expected value are counted as FP."""
    import json
    from ocr_spike.run_compare import evaluate_pk_labs_scoring

    single_gt = {
        "pk_lab_01.png": {
            "hba1c_pct": 8.4,
            "glucose": {"value": 148.0, "unit": "mg/dL", "context": "fasting"},
            "bp": [138, 88],
        }
    }
    gt_file = tmp_path / "ground_truth.json"
    gt_file.write_text(json.dumps(single_gt), encoding="utf-8")

    # Mock extractor returning duplicate matches for expected values
    def mock_duplicate_extractor(text: str):
        return {
            "fields": [
                {"kind": "hba1c", "value": 8.4, "unit": "%"},
                {"kind": "hba1c", "value": 8.4, "unit": "%"},          # duplicate hba1c
                {"kind": "glucose", "value": 148.0, "unit": "mg/dL"},
                {"kind": "glucose", "value": 148.0, "unit": "mg/dL"},  # duplicate expected value
                {"kind": "bp", "value": [138, 88], "unit": "mmHg"},
                {"kind": "bp", "value": [138, 88], "unit": "mmHg"},    # duplicate expected BP
            ],
            "warnings": [],
            "unmatched_lines": [],
        }

    res = evaluate_pk_labs_scoring(
        extractor_fn=mock_duplicate_extractor,
        gt_path=gt_file,
    )
    # GT is 1 for each field
    assert res["hba1c"]["gt"] == 1
    assert res["glucose"]["gt"] == 1
    assert res["bp"]["gt"] == 1

    # Exactly 1 TP per field (never inflated to 2)
    assert res["hba1c"]["tp"] == 1
    assert res["glucose"]["tp"] == 1
    assert res["bp"]["tp"] == 1

    # Duplicates counted as FP
    assert res["hba1c"]["fp"] == 1
    assert res["glucose"]["fp"] == 1
    assert res["bp"]["fp"] == 1
