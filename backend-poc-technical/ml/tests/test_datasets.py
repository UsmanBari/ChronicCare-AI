"""
Unit tests for external dataset loaders on synthetic test frames.
Validates cleaning rules, threshold boundaries, and audit counts.
"""
import numpy as np
import pandas as pd
import pytest

from ml.datasets.brfss2015_kaggle import clean_brfss2015_kaggle_df
from ml.datasets.cardio70k import clean_cardio_df
from ml.datasets.framingham import clean_framingham_df
from ml.datasets.pima import clean_pima_df


# =====================================================================
# 1. Cardio70k Cleaning Tests
# =====================================================================

def test_cardio_gender_coding_empirical():
    """Verify gender coding: gender 2 with greater mean height is mapped to male (1)."""
    df_synthetic = pd.DataFrame({
        "age": [18262, 20000],  # ~50, 54.75 years
        "gender": [1, 2],
        "height": [160.0, 175.0],
        "weight": [65.0, 80.0],
        "ap_hi": [120, 130],
        "ap_lo": [80, 85],
    })
    cleaned, report = clean_cardio_df(df_synthetic)
    assert cleaned.loc[0, "sex_male"] == 0
    assert cleaned.loc[1, "sex_male"] == 1
    assert "greater mean height" in report["gender_evidence"]


def test_cardio_rule1_negative_bp():
    """Rule 1: Negative BP values are converted to NaN."""
    df_synthetic = pd.DataFrame({
        "gender": [1, 2],
        "height": [160, 175],
        "weight": [65, 80],
        "ap_hi": [-120, 130],
        "ap_lo": [80, -70],
    })
    cleaned, report = clean_cardio_df(df_synthetic)
    assert np.isnan(cleaned.loc[0, "sbp"])
    assert np.isnan(cleaned.loc[1, "dbp"])
    assert report["rule1_negative_rows"] == 2


def test_cardio_rule2_inverted_bp_swap():
    """Rule 2: Inverted readings are swapped if both in range post-swap, else set to NaN."""
    df_synthetic = pd.DataFrame({
        "gender": [1, 2],
        "height": [160, 175],
        "weight": [65, 80],
        # Row 0: ap_hi=80, ap_lo=120 -> after swap SBP=120, DBP=80 (valid, swappable)
        # Row 1: ap_hi=20, ap_lo=100 -> after swap SBP=100, DBP=20 (DBP 20 < 30, unswappable)
        "ap_hi": [80, 20],
        "ap_lo": [120, 100],
    })
    cleaned, report = clean_cardio_df(df_synthetic)
    # Row 0 swapped
    assert cleaned.loc[0, "sbp"] == 120.0
    assert cleaned.loc[0, "dbp"] == 80.0
    assert report["rule2_swapped_inverted"] == 1

    # Row 1 unswappable -> NaN
    assert np.isnan(cleaned.loc[1, "sbp"])
    assert np.isnan(cleaned.loc[1, "dbp"])
    assert report["rule2_unswappable_inverted"] == 1


def test_cardio_rule3_extreme_typo_values_16020():
    """Rule 3: Values >= 1000 (e.g. 1100, 14020, 16020) -> NaN with no guessing."""
    df_synthetic = pd.DataFrame({
        "gender": [1, 2, 1],
        "height": [160, 175, 165],
        "weight": [65, 80, 70],
        "ap_hi": [16020, 1100, 14020],
        "ap_lo": [80, 80, 90],
    })
    cleaned, report = clean_cardio_df(df_synthetic)
    assert np.isnan(cleaned.loc[0, "sbp"])
    assert np.isnan(cleaned.loc[1, "sbp"])
    assert np.isnan(cleaned.loc[2, "sbp"])
    assert report["rule3_typo_rows"] == 3


def test_cardio_rule4_and_rule5():
    """Rule 4: Out-of-range bounds, Rule 5: SBP <= DBP after cleaning -> NaN."""
    df_synthetic = pd.DataFrame({
        "gender": [1, 2],
        "height": [160, 175],
        "weight": [65, 80],
        # Row 0: SBP 280 (> 260) -> Rule 4 out of range
        # Row 1: SBP 100, DBP 100 -> Rule 5 SBP <= DBP
        "ap_hi": [280, 100],
        "ap_lo": [80, 100],
    })
    cleaned, report = clean_cardio_df(df_synthetic)
    assert np.isnan(cleaned.loc[0, "sbp"])
    assert report["rule4_out_of_range_rows"] == 1
    assert np.isnan(cleaned.loc[1, "sbp"])
    assert np.isnan(cleaned.loc[1, "dbp"])
    assert report["rule5_sbp_le_dbp"] == 1


def test_cardio_bmi_calculation_and_bounds():
    """Verify BMI derived correctly and bounds [12, 80] enforced."""
    df_synthetic = pd.DataFrame({
        "gender": [1, 2],
        "height": [160.0, 170.0],
        # Row 0: 64kg / 1.6m^2 = 25.0
        # Row 1: 300kg / 1.7m^2 = 103.8 (> 80)
        "weight": [64.0, 300.0],
        "ap_hi": [120, 120],
        "ap_lo": [80, 80],
    })
    cleaned, report = clean_cardio_df(df_synthetic)
    assert cleaned.loc[0, "bmi"] == 25.0
    assert np.isnan(cleaned.loc[1, "bmi"])
    assert report["bmi_out_of_range"] == 1


# =====================================================================
# 2. Framingham Tests
# =====================================================================

def test_framingham_standard_columns_and_na_counts():
    """Verify Framingham column mappings and NA counts computation."""
    df_synthetic = pd.DataFrame({
        "male": [1, 0],
        "age": [45, 55],
        "BMI": [26.5, np.nan],
        "sysBP": [135.0, 140.0],
        "diaBP": [85.0, 90.0],
        "currentSmoker": [1, 0],
        "diabetes": [0, 1],
        "prevalentHyp": [1, 1],
        "glucose": [85.0, np.nan],
        "totChol": [210.0, 240.0],
        "BPMeds": [0.0, 1.0],
    })
    cleaned, report = clean_framingham_df(df_synthetic)
    assert "sex_male" in cleaned.columns
    assert "sbp" in cleaned.columns
    assert "dbp" in cleaned.columns
    assert "prevalent_hyp" in cleaned.columns
    assert report["na_counts"]["bmi"] == 1
    assert report["na_counts"]["glucose"] == 1
    assert report["na_counts"]["sbp"] == 0
    assert report["total_rows"] == 2


# =====================================================================
# 3. BRFSS 2015 Kaggle Tests
# =====================================================================

def test_brfss2015_kaggle_age_midpoints_and_sex():
    """Verify BRFSS 2015 Kaggle age group to midpoint mapping and sex coding."""
    df_synthetic = pd.DataFrame({
        "Sex": [1.0, 0.0],
        "Age": [1.0, 13.0],  # 18-24 -> 21, 80+ -> 82
        "BMI": [24.0, 31.0],
        "HighBP": [0.0, 1.0],
        "Smoker": [1.0, 0.0],
        "Diabetes_binary": [0.0, 1.0],
    })
    cleaned, report = clean_brfss2015_kaggle_df(df_synthetic)
    assert cleaned.loc[0, "sex_male"] == 1.0
    assert cleaned.loc[1, "sex_male"] == 0.0
    assert cleaned.loc[0, "age_mid"] == 21.0
    assert cleaned.loc[1, "age_mid"] == 82.0
    assert cleaned.loc[0, "age"] == 21.0
    assert cleaned.loc[1, "age"] == 82.0
    assert cleaned.loc[0, "high_bp"] == 0.0
    assert cleaned.loc[1, "high_bp"] == 1.0
    assert cleaned.loc[0, "ever_smoker"] == 1.0


# =====================================================================
# 4. Pima Tests
# =====================================================================

def test_pima_zeros_converted_to_nan():
    """Verify physiological zeros in Pima are converted to NaN with audit counts."""
    df_synthetic = pd.DataFrame({
        0: [2, 0],          # pregnancies (0 is valid)
        1: [120, 0],        # glucose (0 is missing -> NaN)
        2: [70, 0],         # bp (0 is missing -> NaN)
        3: [25, 0],         # skin_thickness (0 is missing -> NaN)
        4: [80, 0],         # insulin (0 is missing -> NaN)
        5: [28.5, 0.0],     # bmi (0.0 is missing -> NaN)
        6: [0.5, 0.2],      # dpf (0 is valid)
        7: [32, 45],        # age
        8: [0, 1],          # outcome
    })
    cleaned, report = clean_pima_df(df_synthetic)
    # Row 0 has non-zero values
    assert cleaned.loc[0, "glucose"] == 120.0
    assert cleaned.loc[0, "bp"] == 70.0
    assert cleaned.loc[0, "skin_thickness"] == 25.0
    assert cleaned.loc[0, "insulin"] == 80.0
    assert cleaned.loc[0, "bmi"] == 28.5
    assert cleaned.loc[0, "pregnancies"] == 2.0
    assert cleaned.loc[0, "sex_male"] == 0

    # Row 1 has zeros converted to NaN
    assert np.isnan(cleaned.loc[1, "glucose"])
    assert np.isnan(cleaned.loc[1, "bp"])
    assert np.isnan(cleaned.loc[1, "skin_thickness"])
    assert np.isnan(cleaned.loc[1, "insulin"])
    assert np.isnan(cleaned.loc[1, "bmi"])
    assert cleaned.loc[1, "pregnancies"] == 0.0  # pregnancy zero is not converted
    assert cleaned.loc[1, "sex_male"] == 0

    assert report["zeros_converted_to_nan"]["glucose"] == 1
    assert report["zeros_converted_to_nan"]["bp"] == 1
    assert report["zeros_converted_to_nan"]["skin_thickness"] == 1
    assert report["zeros_converted_to_nan"]["insulin"] == 1
    assert report["zeros_converted_to_nan"]["bmi"] == 1
