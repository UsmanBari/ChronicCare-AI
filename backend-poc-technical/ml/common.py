"""
Common utilities and configuration for ChronicCare AI ML pipeline.
Shared across all Week 2 ML tasks.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

ADULT_MIN_AGE: int = 18
SEED: int = 42


def data_dir() -> Path:
    """Return Path to dataset directory defined by CHRONICCARE_DATA_DIR env var."""
    d = os.environ.get("CHRONICCARE_DATA_DIR")
    if not d:
        raise RuntimeError(
            "CHRONICCARE_DATA_DIR environment variable is not set. "
            "Please point it to your external Chronicare-data folder."
        )
    p = Path(d)
    if not p.exists():
        raise FileNotFoundError(f"CHRONICCARE_DATA_DIR path does not exist: {p}")
    return p


def nhanes_core_path() -> Path:
    """Return Path to nhanes_core.csv."""
    return data_dir() / "nhanes" / "nhanes_core.csv"


def brfss_core_path() -> Path:
    """Return Path to brfss_core.parquet."""
    return data_dir() / "brfss" / "brfss_core.parquet"


def load_nhanes_core(columns: Sequence[str] | None = None) -> pd.DataFrame:
    """
    Load nhanes_core.csv optionally selecting specific columns.
    """
    path = nhanes_core_path()
    if columns is not None:
        return pd.read_csv(path, usecols=list(columns), low_memory=False)
    return pd.read_csv(path, low_memory=False)


def load_brfss_core(columns: Sequence[str] | None = None) -> pd.DataFrame:
    """
    Load brfss_core.parquet with pyarrow selecting specific columns to conserve RAM.
    """
    path = brfss_core_path()
    if columns is not None:
        return pd.read_parquet(path, columns=list(columns), engine="pyarrow")
    return pd.read_parquet(path, engine="pyarrow")


# =====================================================================
# Pure Helper Functions for Quality Checks & Aggregations
# =====================================================================

def compute_missing_pct_table(
    df: pd.DataFrame,
    group_col: str,
    feature_cols: Sequence[str],
) -> pd.DataFrame:
    """
    Compute percentage of missing (NaN) values per column across groups (e.g. cycle or year).
    Returns a wide DataFrame with groups as rows and feature columns as percentage (0.0 to 100.0).
    """
    def pct_missing(series: pd.Series) -> float:
        return float(series.isna().mean() * 100.0)

    agg_dict = {col: pct_missing for col in feature_cols if col in df.columns}
    grouped = df.groupby(group_col, observed=True).agg(agg_dict)
    return grouped.round(1)


def count_implausible_nhanes(df: pd.DataFrame) -> dict[str, int]:
    """
    Count occurrences of clinical plausibility boundary violations without dropping rows:
    - sbp < 60 or > 260
    - dbp < 30 or > 160
    - dbp == 0
    - sbp <= dbp (where neither is null)
    - bmi < 12 or > 80
    - waist_cm < 40 or > 200
    - hba1c < 3 or > 20
    - fasting_glucose < 20 or > 600
    """
    counts: dict[str, int] = {}
    
    if "sbp" in df.columns:
        s = df["sbp"].dropna()
        counts["sbp_out_of_range"] = int(((s < 60) | (s > 260)).sum())
    else:
        counts["sbp_out_of_range"] = 0

    if "dbp" in df.columns:
        d = df["dbp"].dropna()
        counts["dbp_out_of_range"] = int(((d < 30) | (d > 160)).sum())
        counts["dbp_zero"] = int((d == 0).sum())
    else:
        counts["dbp_out_of_range"] = 0
        counts["dbp_zero"] = 0

    if "sbp" in df.columns and "dbp" in df.columns:
        valid_bp = df[df["sbp"].notna() & df["dbp"].notna()]
        counts["sbp_le_dbp"] = int((valid_bp["sbp"] <= valid_bp["dbp"]).sum())
    else:
        counts["sbp_le_dbp"] = 0

    if "bmi" in df.columns:
        b = df["bmi"].dropna()
        counts["bmi_out_of_range"] = int(((b < 12) | (b > 80)).sum())
    else:
        counts["bmi_out_of_range"] = 0

    if "waist_cm" in df.columns:
        w = df["waist_cm"].dropna()
        counts["waist_out_of_range"] = int(((w < 40) | (w > 200)).sum())
    else:
        counts["waist_out_of_range"] = 0

    if "hba1c" in df.columns:
        h = df["hba1c"].dropna()
        counts["hba1c_out_of_range"] = int(((h < 3) | (h > 20)).sum())
    else:
        counts["hba1c_out_of_range"] = 0

    if "fasting_glucose" in df.columns:
        g = df["fasting_glucose"].dropna()
        counts["glucose_out_of_range"] = int(((g < 20) | (g > 600)).sum())
    else:
        counts["glucose_out_of_range"] = 0

    return counts


def get_top_coded_age(df: pd.DataFrame, group_col: str) -> dict[str, float]:
    """Find the maximum age observed in each survey cycle/year to inspect top-coding."""
    if "age" not in df.columns or group_col not in df.columns:
        return {}
    return df.groupby(group_col, observed=True)["age"].max().to_dict()


def compute_pooled_exam_weights(weights: pd.Series, n_cycles: int) -> pd.Series:
    """
    Per CDC NHANES analytical guidelines, when pooling N 2-year survey cycles,
    divide the 2-year examination weights by N.
    """
    if n_cycles <= 0:
        raise ValueError(f"n_cycles must be > 0, got {n_cycles}")
    return weights / float(n_cycles)


def compute_weighted_prevalence(y: pd.Series, weights: pd.Series) -> float:
    """
    Compute weighted prevalence sum(y_i * w_i) / sum(w_i) over non-null y.
    Returns 0.0 if total weight is 0.
    """
    valid = y.notna() & weights.notna() & (weights > 0)
    if not valid.any():
        return 0.0
    w = weights[valid]
    y_val = y[valid]
    total_w = w.sum()
    if total_w == 0:
        return 0.0
    return float((y_val * w).sum() / total_w)
def df_to_markdown(df: pd.DataFrame, index: bool = True) -> str:
    """Convert DataFrame to markdown table string without third-party dependencies."""
    if index:
        df_copy = df.reset_index()
    else:
        df_copy = df.copy()

    headers = [str(c) for c in df_copy.columns]
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"

    rows = []
    for _, row in df_copy.iterrows():
        vals = [str(row[c]) for c in df_copy.columns]
        rows.append("| " + " | ".join(vals) + " |")

    return "\n".join([header_row, sep_row] + rows)
