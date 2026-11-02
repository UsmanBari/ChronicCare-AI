"""
Unit tests for ML label registry and extractors.
Uses hand-made synthetic records to test positive, negative, and NaN behavior.
"""
import numpy as np
import pandas as pd
import pytest
from ml.labels import LABELS


def test_every_label_has_forbidden_features():
    for name, info in LABELS.items():
        assert len(info.forbidden_features) > 0, f"{name} must define forbidden_features"
        assert info.name == name
        assert info.disease in ("diabetes", "hypertension")


def test_diabetes_labels_hand_made_rows():
    df = pd.DataFrame([
        # Row 0: Fully diagnosed diabetic (told=1, hba1c=7.5, glucose=150)
        {"told_diabetes": 1, "hba1c": 7.5, "fasting_glucose": 150.0, "takes_insulin": 1},
        # Row 1: Undiagnosed diabetic (told=0, hba1c=6.8, glucose=110)
        {"told_diabetes": 0, "hba1c": 6.8, "fasting_glucose": 110.0, "takes_insulin": 0},
        # Row 2: Prediabetic (told=0, hba1c=5.9, glucose=105)
        {"told_diabetes": 0, "hba1c": 5.9, "fasting_glucose": 105.0, "takes_insulin": 0},
        # Row 3: Healthy control (told=0, hba1c=5.1, glucose=85)
        {"told_diabetes": 0, "hba1c": 5.1, "fasting_glucose": 85.0, "takes_insulin": 0},
        # Row 4: Completely missing lab & exam
        {"told_diabetes": np.nan, "hba1c": np.nan, "fasting_glucose": np.nan, "takes_insulin": np.nan},
    ])

    # 1. diabetes_told
    told = LABELS["diabetes_told"].extractor(df)
    assert told.iloc[0] == 1.0
    assert told.iloc[1] == 0.0
    assert told.iloc[2] == 0.0
    assert told.iloc[3] == 0.0
    assert np.isnan(told.iloc[4]), "Missing input must yield NaN, never 0"

    # 2. diabetes_measured
    meas = LABELS["diabetes_measured"].extractor(df)
    assert meas.iloc[0] == 1.0
    assert meas.iloc[1] == 1.0
    assert meas.iloc[2] == 0.0
    assert meas.iloc[3] == 0.0
    assert np.isnan(meas.iloc[4]), "Missing lab must yield NaN, never 0"

    # 3. diabetes_told_or_measured
    told_or_meas = LABELS["diabetes_told_or_measured"].extractor(df)
    assert told_or_meas.iloc[0] == 1.0
    assert told_or_meas.iloc[1] == 1.0
    assert told_or_meas.iloc[2] == 0.0
    assert told_or_meas.iloc[3] == 0.0
    assert np.isnan(told_or_meas.iloc[4])

    # 4. diabetes_undiagnosed
    und = LABELS["diabetes_undiagnosed"].extractor(df)
    assert np.isnan(und.iloc[0]), "Already told diabetic is excluded (NaN) from undiagnosed screening"
    assert und.iloc[1] == 1.0, "Told=0 and measured=1 is undiagnosed positive"
    assert und.iloc[2] == 0.0
    assert und.iloc[3] == 0.0
    assert np.isnan(und.iloc[4])

    # 5. diabetes_prediabetes
    prediab = LABELS["diabetes_prediabetes"].extractor(df)
    assert prediab.iloc[0] == 0.0, "Diagnosed diabetic is not prediabetic"
    assert prediab.iloc[1] == 0.0, "Measured diabetic is not prediabetic"
    assert prediab.iloc[2] == 1.0, "HbA1c 5.9 is prediabetic"
    assert prediab.iloc[3] == 0.0, "HbA1c 5.1 is normal"
    assert np.isnan(prediab.iloc[4])


def test_hypertension_labels_hand_made_rows():
    df = pd.DataFrame([
        # Row 0: Diagnosed and on meds, controlled (told=1, meds=1, sbp=120, dbp=75)
        {"told_high_bp": 1, "takes_bp_meds": 1, "sbp": 120.0, "dbp": 75.0},
        # Row 1: Undiagnosed stage 1 (told=0, meds=0, sbp=132.0, dbp=78.0)
        {"told_high_bp": 0, "takes_bp_meds": 0, "sbp": 132.0, "dbp": 78.0},
        # Row 2: Undiagnosed stage 2 (told=0, meds=0, sbp=145.0, dbp=92.0)
        {"told_high_bp": 0, "takes_bp_meds": 0, "sbp": 145.0, "dbp": 92.0},
        # Row 3: Normotensive healthy (told=0, meds=0, sbp=115.0, dbp=72.0)
        {"told_high_bp": 0, "takes_bp_meds": 0, "sbp": 115.0, "dbp": 72.0},
        # Row 4: Completely missing BP
        {"told_high_bp": np.nan, "takes_bp_meds": np.nan, "sbp": np.nan, "dbp": np.nan},
    ])

    # 1. hypertension_told
    h_told = LABELS["hypertension_told"].extractor(df)
    assert h_told.iloc[0] == 1.0
    assert h_told.iloc[1] == 0.0
    assert np.isnan(h_told.iloc[4])

    # 2. hypertension_on_meds
    h_meds = LABELS["hypertension_on_meds"].extractor(df)
    assert h_meds.iloc[0] == 1.0
    assert h_meds.iloc[1] == 0.0
    assert np.isnan(h_meds.iloc[4])

    # 3. hypertension_measured_130_80
    h_130 = LABELS["hypertension_measured_130_80"].extractor(df)
    assert h_130.iloc[0] == 0.0
    assert h_130.iloc[1] == 1.0  # sbp 132 >= 130
    assert h_130.iloc[2] == 1.0
    assert h_130.iloc[3] == 0.0
    assert np.isnan(h_130.iloc[4])

    # 4. hypertension_measured_140_90
    h_140 = LABELS["hypertension_measured_140_90"].extractor(df)
    assert h_140.iloc[0] == 0.0
    assert h_140.iloc[1] == 0.0  # sbp 132 < 140
    assert h_140.iloc[2] == 1.0  # sbp 145 >= 140
    assert h_140.iloc[3] == 0.0
    assert np.isnan(h_140.iloc[4])

    # 5. hypertension_stage1_or_clinical
    h_all = LABELS["hypertension_stage1_or_clinical"].extractor(df)
    assert h_all.iloc[0] == 1.0  # told & meds
    assert h_all.iloc[1] == 1.0  # sbp >= 130
    assert h_all.iloc[2] == 1.0  # sbp >= 140
    assert h_all.iloc[3] == 0.0  # normotensive
    assert np.isnan(h_all.iloc[4])
