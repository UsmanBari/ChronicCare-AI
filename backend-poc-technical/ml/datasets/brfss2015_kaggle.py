"""
BRFSS 2015 Kaggle Diabetes Health Indicators Dataset Loader and Cleaner.

Dataset description:
253,680 survey responses from CDC's BRFSS 2015 formatted by Kaggle
containing 21 health and demographic indicators.

Mappings and transformations:
- HighBP -> high_bp (and told_high_bp)
- HighChol -> high_chol
- CholCheck -> chol_check
- BMI -> bmi
- Smoker -> ever_smoker (and ever_smoked_100)
- Stroke -> stroke
- HeartDiseaseorAttack -> heart_disease_or_attack
- PhysActivity -> phys_active
- Fruits -> fruits
- Veggies -> veggies
- HvyAlcoholConsump -> hvy_alcohol_consump
- AnyHealthcare -> any_healthcare
- NoDocbcCost -> no_doc_bc_cost
- GenHlth -> gen_hlth
- MentHlth -> ment_hlth
- PhysHlth -> phys_hlth
- DiffWalk -> diff_walk
- Sex -> sex_male (0 = female, 1 = male)
- Age (13 groups) -> age_group and age_mid (midpoints: 1->21, 2->27, ..., 13->82)
- Education -> education
- Income -> income
- Diabetes_binary -> diabetes (and told_diabetes)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.common import brfss2015_kaggle_path


# Documented age group midpoint mapping per BRFSS codebook
AGE_GROUP_TO_MIDPOINT: dict[int, float] = {
    1: 21.0,   # Age 18 - 24
    2: 27.0,   # Age 25 - 29
    3: 32.0,   # Age 30 - 34
    4: 37.0,   # Age 35 - 39
    5: 42.0,   # Age 40 - 44
    6: 47.0,   # Age 45 - 49
    7: 52.0,   # Age 50 - 54
    8: 57.0,   # Age 55 - 59
    9: 62.0,   # Age 60 - 64
    10: 67.0,  # Age 65 - 69
    11: 72.0,  # Age 70 - 74
    12: 77.0,  # Age 75 - 79
    13: 82.0,  # Age 80 or older
}

KAGGLE_TO_STANDARD = {
    "Diabetes_binary": "diabetes",
    "HighBP": "high_bp",
    "HighChol": "high_chol",
    "CholCheck": "chol_check",
    "BMI": "bmi",
    "Smoker": "ever_smoker",
    "Stroke": "stroke",
    "HeartDiseaseorAttack": "heart_disease_or_attack",
    "PhysActivity": "phys_active",
    "Fruits": "fruits",
    "Veggies": "veggies",
    "HvyAlcoholConsump": "hvy_alcohol_consump",
    "AnyHealthcare": "any_healthcare",
    "NoDocbcCost": "no_doc_bc_cost",
    "GenHlth": "gen_hlth",
    "MentHlth": "ment_hlth",
    "PhysHlth": "phys_hlth",
    "DiffWalk": "diff_walk",
    "Sex": "sex_male",
    "Age": "age_group",
    "Education": "education",
    "Income": "income",
}


def clean_brfss2015_kaggle_df(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Clean and standardize a Kaggle BRFSS 2015 DataFrame.
    """
    report: dict[str, Any] = {
        "dataset": "brfss2015_kaggle",
        "total_rows": int(len(df)),
    }

    out_df = pd.DataFrame(index=df.index)

    # 1. Column renaming
    for src_col, dest_col in KAGGLE_TO_STANDARD.items():
        if src_col in df.columns:
            out_df[dest_col] = df[src_col]
        elif dest_col in df.columns:
            out_df[dest_col] = df[dest_col]

    # 2. Sex coding audit & verification
    if "sex_male" in out_df.columns:
        male_count = int((out_df["sex_male"] == 1).sum())
        female_count = int((out_df["sex_male"] == 0).sum())
        report["sex_distribution"] = {"male (1)": male_count, "female (0)": female_count}

    # 3. Age conversion: age_group -> age_mid and age
    if "age_group" in out_df.columns:
        # Map age_group to age_mid
        out_df["age_mid"] = out_df["age_group"].map(AGE_GROUP_TO_MIDPOINT)
        out_df["age"] = out_df["age_mid"]
        report["age_groups_mapped"] = int(out_df["age_mid"].notna().sum())
    elif "age" in df.columns:
        out_df["age"] = df["age"]
        out_df["age_mid"] = df["age"]

    # 4. Model feature aliases
    if "high_bp" in out_df.columns:
        out_df["told_high_bp"] = out_df["high_bp"]
    if "ever_smoker" in out_df.columns:
        out_df["ever_smoked_100"] = out_df["ever_smoker"]
    if "diabetes" in out_df.columns:
        out_df["told_diabetes"] = out_df["diabetes"]

    # 5. NA counts
    na_counts = {c: int(out_df[c].isna().sum()) for c in out_df.columns}
    report["na_counts"] = na_counts
    report["valid_complete_rows"] = int(out_df[["age", "sex_male", "bmi", "diabetes", "high_bp"]].dropna().shape[0]) if all(c in out_df.columns for c in ["age", "sex_male", "bmi", "diabetes", "high_bp"]) else 0

    return out_df, report


def load_brfss2015_kaggle(
    path: str | Path | None = None,
    filename: str = "diabetes_binary_health_indicators_BRFSS2015.csv",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Load and clean Kaggle BRFSS 2015 dataset from CSV.
    """
    target_path = Path(path) if path is not None else brfss2015_kaggle_path(filename)
    if not target_path.exists():
        raise FileNotFoundError(f"BRFSS 2015 Kaggle dataset file not found: {target_path}")

    raw_df = pd.read_csv(target_path)
    return clean_brfss2015_kaggle_df(raw_df)
