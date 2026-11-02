"""
Unit tests for data_checks.py ensuring correct label calculations
and zero row-level data leakage into reports.
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pytest

from ml import common, data_checks


def test_label_counting_and_undiagnosed_logic():
    """
    Test label counting criteria on synthetic rows:
    - measured_diabetes: hba1c >= 6.5 or fasting_glucose >= 126
    - undiagnosed: measured == 1 and told_diabetes == 0
    """
    df = pd.DataFrame({
        "cycle": ["2017-2018"] * 5,
        "age": [45, 50, 60, 35, 70],
        "told_diabetes": [1.0, 0.0, 0.0, 0.0, np.nan],
        "hba1c": [6.0, 7.0, 5.5, np.nan, 8.0],
        "fasting_glucose": [110.0, 100.0, 130.0, 95.0, np.nan],
        "borderline_diabetes": [0.0, 0.0, 1.0, 0.0, 0.0],
        "told_high_bp": [1.0, 1.0, 0.0, 0.0, 0.0],
        "takes_bp_meds": [1.0, 0.0, 0.0, 0.0, 0.0],
        "sbp": [145.0, 125.0, 135.0, 115.0, 120.0],
        "dbp": [95.0, 85.0, 75.0, 70.0, 80.0],
        "exam_weight_2yr": [1000.0] * 5,
        "seqn": [99901, 99902, 99903, 99904, 99905]
    })

    # Row 0: told=1, a1c=6.0, fpg=110 -> measured=0, undiag=0, told_hbp=1, sbp=145/95 -> uncontrolled=1
    # Row 1: told=0, a1c=7.0 (>=6.5) -> measured=1, undiag=1, told_hbp=1, sbp=125/85 -> uncontrolled=0
    # Row 2: told=0, fpg=130 (>=126) -> measured=1, undiag=1, told_hbp=0 -> uncontrolled=0
    # Row 3: told=0, fpg=95 -> measured=0, undiag=0
    # Row 4: told=NaN, a1c=8.0 -> measured=1, undiag=NaN (told is unknown)

    md, metrics = data_checks.generate_nhanes_report(df)

    # Undiagnosed count should be exactly 2 (Rows 1 and 2)
    assert "2 / 4 (50.0%)" in md
    # Measured diabetes should be 3 (Rows 1, 2, 4) out of 4 (Row 3 is 0, Row 0 is 0; total measured valid = 5)
    assert "3 / 5 (60.0%)" in md
    # Uncontrolled BP should be 1 (Row 0) out of 2 told_hbp with valid BP (Row 0 and 1)
    assert "1 / 2 (50.0%)" in md


def test_no_row_level_data_in_generated_markdown(tmp_path):
    """
    CRITICAL PRIVACY TEST:
    Assert that the generated markdown report strictly contains zero individual SEQN IDs,
    zero row numbers, and zero unaggregated patient records.
    """
    fake_seqns = [1119991, 1119992, 1119993, 1119994]
    fake_nhanes = pd.DataFrame({
        "seqn": fake_seqns,
        "cycle": ["2021-2023"] * 4,
        "age": [25, 45, 65, 80],
        "sex_male": [1, 0, 1, 0],
        "race_eth": [1, 2, 3, 4],
        "income_poverty_ratio": [2.5, 3.1, 1.2, 4.0],
        "bmi": [24.5, 29.2, 33.1, 21.0],
        "waist_cm": [80.0, 92.0, 105.0, 75.0],
        "height_cm": [175.0, 160.0, 180.0, 155.0],
        "weight_kg": [75.0, 75.0, 107.0, 50.0],
        "sbp": [120.0, 130.0, 140.0, 110.0],
        "dbp": [80.0, 85.0, 90.0, 70.0],
        "pulse": [72, 75, 80, 68],
        "hba1c": [5.4, 6.2, 7.1, 5.0],
        "fasting_glucose": [90.0, 105.0, 140.0, 85.0],
        "total_chol": [180.0, 210.0, 240.0, 160.0],
        "told_diabetes": [0, 0, 1, 0],
        "takes_insulin": [0, 0, 1, 0],
        "takes_diabetes_pills": [0, 0, 1, 0],
        "told_high_bp": [0, 1, 1, 0],
        "takes_bp_meds": [0, 1, 1, 0],
        "family_hx_diabetes": [0, 1, 1, 0],
        "ever_smoked_100": [0, 0, 1, 0],
        "exam_weight_2yr": [5000.0, 5000.0, 5000.0, 5000.0],
        "borderline_diabetes": [0, 0, 0, 0]
    })

    md, _ = data_checks.generate_nhanes_report(fake_nhanes)

    # Check that NONE of the fake seqn values appear anywhere in the markdown output
    for seqn in fake_seqns:
        assert str(seqn) not in md, f"LEAKAGE ERROR: SEQN {seqn} found in generated markdown report!"

    # Ensure no column names followed by individual values appear as raw record lines
    assert not re.search(r"SEQN\s*:\s*\d+", md, re.IGNORECASE)
    assert not re.search(r"Patient\s*ID\s*:\s*\d+", md, re.IGNORECASE)