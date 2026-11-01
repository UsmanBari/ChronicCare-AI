"""
Pima Indians Diabetes Dataset Loader and Cleaner.

Dataset description:
768 records of Pima Indian heritage females aged 21 and older from Phoenix, Arizona.
Features include oral glucose tolerance test (OGTT) 2-hour plasma glucose,
diastolic blood pressure, triceps skin fold thickness, 2-hour serum insulin,
BMI, diabetes pedigree function, age, and binary diabetes onset outcome.

Cleaning Rule:
Physiological zero values in Glucose, BloodPressure, SkinThickness, Insulin,
and BMI represent missing data entries (e.g. insulin or skinfold not measured,
or unrecorded vital signs). These zeros are converted to NaN with audit counts.
All subjects are female (sex_male = 0).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.common import pima_path


RAW_COLUMNS = [
    "pregnancies",
    "glucose",
    "bp",
    "skin_thickness",
    "insulin",
    "bmi",
    "diabetes_pedigree_function",
    "age",
    "diabetes",
]

ZERO_AS_NAN_COLUMNS = ["glucose", "bp", "skin_thickness", "insulin", "bmi"]


def clean_pima_df(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Clean and standardize a Pima Indians Diabetes DataFrame.
    Converts physiological zeros in specified columns to NaN.
    """
    report: dict[str, Any] = {
        "dataset": "pima",
        "total_rows": int(len(df)),
    }

    out_df = df.copy()

    # If raw column names are integers 0..8, assign standard names
    if list(out_df.columns) == list(range(len(RAW_COLUMNS))) or out_df.columns[0] == 0:
        out_df.columns = RAW_COLUMNS[: len(out_df.columns)]
    else:
        # Standardize known variations in column names
        rename_map = {
            "Pregnancies": "pregnancies",
            "Glucose": "glucose",
            "BloodPressure": "bp",
            "SkinThickness": "skin_thickness",
            "Insulin": "insulin",
            "BMI": "bmi",
            "DiabetesPedigreeFunction": "diabetes_pedigree_function",
            "Age": "age",
            "Outcome": "diabetes",
        }
        out_df = out_df.rename(columns=rename_map)

    # Convert physiological zeros to NaN
    zeros_converted: dict[str, int] = {}
    for col in ZERO_AS_NAN_COLUMNS:
        if col in out_df.columns:
            zero_mask = out_df[col] == 0
            count = int(zero_mask.sum())
            zeros_converted[col] = count
            out_df.loc[zero_mask, col] = np.nan
        else:
            zeros_converted[col] = 0

    report["zeros_converted_to_nan"] = zeros_converted

    # All subjects in Pima dataset are adult females
    out_df["sex_male"] = 0

    # Model aliases
    if "diabetes" in out_df.columns:
        out_df["told_diabetes"] = out_df["diabetes"]
        out_df["outcome"] = out_df["diabetes"]

    # NA counts
    na_counts = {c: int(out_df[c].isna().sum()) for c in out_df.columns}
    report["na_counts"] = na_counts
    report["valid_complete_rows"] = int(out_df[["age", "bmi", "sex_male", "diabetes"]].dropna().shape[0])

    return out_df, report


def load_pima(path: str | Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Load and clean Pima Indians Diabetes dataset from CSV.
    """
    target_path = Path(path) if path is not None else pima_path()
    if not target_path.exists():
        raise FileNotFoundError(f"Pima dataset file not found: {target_path}")

    # File has no header
    raw_df = pd.read_csv(target_path, header=None)
    return clean_pima_df(raw_df)
