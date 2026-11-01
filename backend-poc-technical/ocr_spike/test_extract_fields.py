"""
Hermetic Unit Tests for OCR Spike Field Extractor.

Tests deterministic extraction of HbA1c, glucose, blood pressure, and medications
from plain strings without requiring external OCR engines or dependencies.
"""

from __future__ import annotations

import pytest
from ocr_spike.extract_fields import (
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

