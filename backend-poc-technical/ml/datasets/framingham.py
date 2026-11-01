"""
Framingham Heart Study Cohort Dataset Loader and Cleaner.

Dataset description:
4,238 participant records from the Framingham Heart Study containing
longitudinal cardiovascular and metabolic indicators.

Standard column mapping:
- age: participant age in years
- sex_male: 1 if male, 0 if female (from 'male')
- bmi: Body Mass Index (from 'BMI')
- sbp: systolic blood pressure (from 'sysBP')
- dbp: diastolic blood pressure (from 'diaBP')
- current_smoker: smoking status (from 'currentSmoker')
- diabetes: diabetes status (from 'diabetes')
- prevalent_hyp: prevalent hypertension (from 'prevalentHyp')
- glucose: blood glucose mg/dL (from 'glucose')
- total_chol: total serum cholesterol mg/dL (from 'totChol')
- bp_meds: currently taking BP medication (from 'BPMeds')
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ml.common import framingham_path


COLUMN_MAPPING = {
    "age": "age",
    "male": "sex_male",
    "BMI": "bmi",
    "sysBP": "sbp",
    "diaBP": "dbp",
    "currentSmoker": "current_smoker",
    "diabetes": "diabetes",
    "prevalentHyp": "prevalent_hyp",
    "glucose": "glucose",
    "totChol": "total_chol",
    "BPMeds": "bp_meds",
}


def clean_framingham_df(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Clean and standardize a Framingham DataFrame.
    Maps columns to standard names and reports NA counts per column.
    """
    report: dict[str, Any] = {
        "dataset": "framingham",
        "total_rows": int(len(df)),
    }

    out_df = pd.DataFrame(index=df.index)

    # Map existing columns
    for src_col, dest_col in COLUMN_MAPPING.items():
        if src_col in df.columns:
            out_df[dest_col] = df[src_col]
        elif dest_col in df.columns:
            out_df[dest_col] = df[dest_col]

    # Include aliases for model compatibility:
    # 'told_diabetes' alias to 'diabetes'
    if "diabetes" in out_df.columns:
        out_df["told_diabetes"] = out_df["diabetes"]
    # 'ever_smoked_100' alias to 'current_smoker'
    if "current_smoker" in out_df.columns:
        out_df["ever_smoked_100"] = out_df["current_smoker"]
    # 'high_bp' alias to 'prevalent_hyp'
    if "prevalent_hyp" in out_df.columns:
        out_df["high_bp"] = out_df["prevalent_hyp"]
        out_df["told_high_bp"] = out_df["prevalent_hyp"]

    # Compute NA count per column for standard columns
    na_counts: dict[str, int] = {}
    for dest_col in COLUMN_MAPPING.values():
        if dest_col in out_df.columns:
            na_counts[dest_col] = int(out_df[dest_col].isna().sum())
        else:
            na_counts[dest_col] = int(len(df))

    report["na_counts"] = na_counts
    report["valid_complete_rows"] = int(out_df.dropna(subset=[c for c in COLUMN_MAPPING.values() if c in out_df.columns]).shape[0])

    return out_df, report


def load_framingham(path: str | Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Load and clean the Framingham dataset from CSV.
    """
    target_path = Path(path) if path is not None else framingham_path()
    if not target_path.exists():
        raise FileNotFoundError(f"Framingham dataset file not found: {target_path}")

    raw_df = pd.read_csv(target_path)
    return clean_framingham_df(raw_df)
