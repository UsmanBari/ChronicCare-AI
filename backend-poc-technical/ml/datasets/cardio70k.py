"""
Cardio70k (Cardiovascular Disease Dataset) Loader and Cleaning Pipeline.

Dataset description:
70,000 examination records containing objective vital signs, demographic indicators,
and cardiovascular disease target status. Semicolon-separated CSV.

Cleaning Rules (per docs/tasks/WEEK2_SAAD.md A1):
1. Age conversion: age_years = age_days / 365.25
2. Gender verification: verified by empirical height evidence:
   gender 2 has higher mean height (169.95 cm) vs gender 1 (161.36 cm).
   sex_male = 1 if gender == 2 else 0.
3. BP Cleaning Rules:
   (1) Negative values -> NaN
   (2) Inverted BP (ap_hi < ap_lo): swap only if both in range after swap
       (60 <= cand_sbp <= 260 and 30 <= cand_dbp <= 160 and cand_sbp > cand_dbp), else NaN
   (3) Extreme typo values (>= 1000, e.g. 1100, 14020, 16020) -> NaN (no divide-by-10 guessing)
   (4) Out of app plausibility ranges (sbp 60-260, dbp 30-160) -> NaN
   (5) SBP <= DBP after steps above -> NaN
4. BMI from height and weight: weight / (height/100)^2, plausibility [12, 80]
5. Standard column names:
   age, sex_male, bmi, sbp, dbp, current_smoker, chol_cat, gluc_cat, cvd, htn_measured_130_80
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ml.common import cardio70k_path


def clean_cardio_df(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Clean and standardize a Cardio70k DataFrame.
    Can operate on the full dataset or on synthetic test frames.
    """
    report: dict[str, Any] = {
        "dataset": "cardio70k",
        "total_rows": len(df),
    }

    # 1. Gender check & coding
    if "gender" in df.columns and "height" in df.columns and len(df) > 0:
        g1_height = df.loc[df["gender"] == 1, "height"].mean()
        g2_height = df.loc[df["gender"] == 2, "height"].mean()
        report["mean_height_gender_1"] = float(g1_height) if pd.notna(g1_height) else None
        report["mean_height_gender_2"] = float(g2_height) if pd.notna(g2_height) else None
        report["gender_evidence"] = (
            "gender 2 has greater mean height than gender 1 -> gender 2 is male (sex_male=1), "
            "gender 1 is female (sex_male=0)"
        )
        sex_male = (df["gender"] == 2).astype(int)
    elif "sex_male" in df.columns:
        sex_male = df["sex_male"].astype(int)
    else:
        sex_male = pd.Series(np.nan, index=df.index)

    # 2. Age in years
    if "age" in df.columns:
        # If max age > 150, assume age is in days
        if df["age"].max() > 150:
            age_years = df["age"] / 365.25
        else:
            age_years = df["age"].astype(float)
    else:
        age_years = pd.Series(np.nan, index=df.index)

    # 3. BMI calculation
    if "height" in df.columns and "weight" in df.columns:
        h_m = df["height"] / 100.0
        # Prevent zero division
        valid_h = h_m > 0
        raw_bmi = pd.Series(np.nan, index=df.index)
        raw_bmi[valid_h] = df.loc[valid_h, "weight"] / (h_m[valid_h] ** 2)

        bmi_out_mask = (raw_bmi < 12.0) | (raw_bmi > 80.0)
        report["bmi_out_of_range"] = int(bmi_out_mask.sum())
        clean_bmi = raw_bmi.copy()
        clean_bmi[bmi_out_mask] = np.nan
    elif "bmi" in df.columns:
        clean_bmi = df["bmi"].astype(float)
        bmi_out_mask = (clean_bmi < 12.0) | (clean_bmi > 80.0)
        report["bmi_out_of_range"] = int(bmi_out_mask.sum())
        clean_bmi[bmi_out_mask] = np.nan
    else:
        clean_bmi = pd.Series(np.nan, index=df.index)
        report["bmi_out_of_range"] = 0

    # 4. BP Cleaning Rules
    sbp_raw = df["ap_hi"].astype(float).copy() if "ap_hi" in df.columns else df["sbp"].astype(float).copy()
    dbp_raw = df["ap_lo"].astype(float).copy() if "ap_lo" in df.columns else df["dbp"].astype(float).copy()

    sbp = sbp_raw.copy()
    dbp = dbp_raw.copy()

    # (1) Negative values -> NaN
    neg_sbp = sbp < 0
    neg_dbp = dbp < 0
    report["rule1_negative_sbp"] = int(neg_sbp.sum())
    report["rule1_negative_dbp"] = int(neg_dbp.sum())
    report["rule1_negative_rows"] = int((neg_sbp | neg_dbp).sum())
    sbp[neg_sbp] = np.nan
    dbp[neg_dbp] = np.nan

    # (2) ap_hi < ap_lo: swap only if BOTH are in range after swap, else NaN
    # Inverted condition: both non-null and sbp < dbp
    # Audit note: 1,234 raw rows have ap_hi < ap_lo; 7 had negative values caught in Rule 1.
    # Exactly 1,227 non-negative inverted rows enter Rule 2 (100 swapped + 1,127 set to NaN).
    inv_mask = (sbp < dbp) & sbp.notna() & dbp.notna()
    cand_sbp = dbp
    cand_dbp = sbp
    swappable = (
        inv_mask
        & (cand_sbp >= 60.0)
        & (cand_sbp <= 260.0)
        & (cand_dbp >= 30.0)
        & (cand_dbp <= 160.0)
        & (cand_sbp > cand_dbp)
    )
    unswappable = inv_mask & (~swappable)

    report["rule2_swapped_inverted"] = int(swappable.sum())
    report["rule2_unswappable_inverted"] = int(unswappable.sum())

    # Execute swap
    temp_sbp = sbp[swappable].copy()
    sbp[swappable] = dbp[swappable]
    dbp[swappable] = temp_sbp

    # Set unswappable inverted to NaN
    sbp[unswappable] = np.nan
    dbp[unswappable] = np.nan

    # (3) Values >= 1000 (e.g. 1100, 14020, 16020) -> NaN (no divide by 10 guessing)
    typo_sbp = (sbp >= 1000.0) & sbp.notna()
    typo_dbp = (dbp >= 1000.0) & dbp.notna()
    report["rule3_typo_sbp_ge_1000"] = int(typo_sbp.sum())
    report["rule3_typo_dbp_ge_1000"] = int(typo_dbp.sum())
    report["rule3_typo_rows"] = int((typo_sbp | typo_dbp).sum())
    sbp[typo_sbp] = np.nan
    dbp[typo_dbp] = np.nan

    # (4) Out of app plausibility ranges (sbp 60-260, dbp 30-160) -> NaN
    out_sbp = ((sbp < 60.0) | (sbp > 260.0)) & sbp.notna()
    out_dbp = ((dbp < 30.0) | (dbp > 160.0)) & dbp.notna()
    report["rule4_out_of_range_sbp"] = int(out_sbp.sum())
    report["rule4_out_of_range_dbp"] = int(out_dbp.sum())
    report["rule4_out_of_range_rows"] = int((out_sbp | out_dbp).sum())
    sbp[out_sbp] = np.nan
    dbp[out_dbp] = np.nan

    # (5) SBP <= DBP after steps above -> NaN
    le_mask = (sbp <= dbp) & sbp.notna() & dbp.notna()
    report["rule5_sbp_le_dbp"] = int(le_mask.sum())
    sbp[le_mask] = np.nan
    dbp[le_mask] = np.nan

    valid_bp = sbp.notna() & dbp.notna()
    report["clean_bp_rows"] = int(valid_bp.sum())

    # Build clean standardized DataFrame
    out_df = pd.DataFrame(index=df.index)
    out_df["age"] = age_years.round(2)
    out_df["sex_male"] = sex_male
    out_df["bmi"] = clean_bmi.round(2)
    out_df["sbp"] = sbp
    out_df["dbp"] = dbp

    # Smoker
    if "smoke" in df.columns:
        out_df["current_smoker"] = df["smoke"].astype(int)
    elif "current_smoker" in df.columns:
        out_df["current_smoker"] = df["current_smoker"].astype(int)

    # Categories
    if "cholesterol" in df.columns:
        out_df["chol_cat"] = df["cholesterol"].astype(int)
    if "gluc" in df.columns:
        out_df["gluc_cat"] = df["gluc"].astype(int)
    if "cardio" in df.columns:
        out_df["cvd"] = df["cardio"].astype(int)

    # Hypertension label (130/80)
    out_df["htn_measured_130_80"] = np.where(
        valid_bp,
        ((sbp >= 130.0) | (dbp >= 80.0)).astype(int),
        np.nan,
    )

    report["valid_complete_rows"] = int(out_df[["age", "sex_male", "bmi", "sbp", "dbp"]].dropna().shape[0])
    return out_df, report


def load_cardio70k(path: str | Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Load and clean the Cardio70k dataset.
    """
    target_path = Path(path) if path is not None else cardio70k_path()
    if not target_path.exists():
        raise FileNotFoundError(f"Cardio70k dataset file not found: {target_path}")

    raw_df = pd.read_csv(target_path, sep=";")
    return clean_cardio_df(raw_df)

