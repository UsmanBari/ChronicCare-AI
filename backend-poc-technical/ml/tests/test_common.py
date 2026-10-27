"""
Unit tests for backend-poc-technical/ml/common.py using synthetic DataFrames only.
"""
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from ml import common


def test_missing_env_var_error(monkeypatch):
    """Assert clear RuntimeError when CHRONICCARE_DATA_DIR is missing or empty."""
    monkeypatch.delenv("CHRONICCARE_DATA_DIR", raising=False)
    with pytest.raises(RuntimeError, match="CHRONICCARE_DATA_DIR environment variable is not set"):
        common.data_dir()


def test_nonexistent_env_dir_error(monkeypatch, tmp_path):
    """Assert FileNotFoundError when CHRONICCARE_DATA_DIR points to a nonexistent path."""
    non_existent = tmp_path / "does_not_exist_12345"
    monkeypatch.setenv("CHRONICCARE_DATA_DIR", str(non_existent))
    with pytest.raises(FileNotFoundError, match="does not exist"):
        common.data_dir()


def test_valid_data_dir(monkeypatch, tmp_path):
    """Assert Path object returned when CHRONICCARE_DATA_DIR points to an existing directory."""
    monkeypatch.setenv("CHRONICCARE_DATA_DIR", str(tmp_path))
    p = common.data_dir()
    assert p == tmp_path
    assert common.nhanes_core_path() == tmp_path / "nhanes" / "nhanes_core.csv"
    assert common.brfss_core_path() == tmp_path / "brfss" / "brfss_core.parquet"


def test_pooled_weight_division():
    """Assert 2-year survey weights are divided by the number of pooled cycles."""
    w = pd.Series([1100.0, 2200.0, 3300.0])
    pooled = common.compute_pooled_exam_weights(w, n_cycles=11)
    expected = pd.Series([100.0, 200.0, 300.0])
    pd.testing.assert_series_equal(pooled, expected)

    with pytest.raises(ValueError, match="n_cycles must be > 0"):
        common.compute_pooled_exam_weights(w, n_cycles=0)


def test_weighted_prevalence_calculation():
    """Assert weighted prevalence on known hand-made synthetic arrays."""
    y = pd.Series([1, 0, 1, 0])
    weights = pd.Series([10.0, 10.0, 30.0, 50.0])  # total weight = 100, pos weight = 40 -> 0.40
    prev = common.compute_weighted_prevalence(y, weights)
    assert pytest.approx(prev, 1e-6) == 0.40

    # Test all zeros or all nulls
    assert common.compute_weighted_prevalence(pd.Series([np.nan, np.nan]), weights[:2]) == 0.0
    assert common.compute_weighted_prevalence(y, pd.Series([0.0, 0.0, 0.0, 0.0])) == 0.0


def test_implausible_boundary_checks():
    """
    Assert implausible boundary criteria at exact edges:
    - sbp: 59 out, 60 in, 260 in, 261 out
    - dbp: 29 out, 30 in, 160 in, 161 out, 0 counted
    - sbp <= dbp (including sbp == dbp)
    - bmi: 11.9 out, 12 in, 80 in, 80.1 out
    - waist: 39.9 out, 40 in, 200 in, 200.1 out
    - hba1c: 2.9 out, 3 in, 20 in, 20.1 out
    - glucose: 19 out, 20 in, 600 in, 601 out
    """
    df = pd.DataFrame({
        "sbp": [59.0, 60.0, 260.0, 261.0, 120.0],
        "dbp": [29.0, 30.0, 160.0, 161.0, 120.0],  # row 4 has sbp == dbp == 120
        "bmi": [11.9, 12.0, 80.0, 80.1, 25.0],
        "waist_cm": [39.9, 40.0, 200.0, 200.1, 85.0],
        "hba1c": [2.9, 3.0, 20.0, 20.1, 5.5],
        "fasting_glucose": [19.0, 20.0, 600.0, 601.0, 95.0]
    })

    counts = common.count_implausible_nhanes(df)
    assert counts["sbp_out_of_range"] == 2      # 59 and 261
    assert counts["dbp_out_of_range"] == 2      # 29 and 161
    assert counts["sbp_le_dbp"] == 1            # row 4: 120 <= 120
    assert counts["bmi_out_of_range"] == 2      # 11.9 and 80.1
    assert counts["waist_out_of_range"] == 2    # 39.9 and 200.1
    assert counts["hba1c_out_of_range"] == 2    # 2.9 and 20.1
    assert counts["glucose_out_of_range"] == 2  # 19 and 601

    # Check dbp == 0 explicitly
    df_zero = pd.DataFrame({"dbp": [0.0, 80.0]})
    assert common.count_implausible_nhanes(df_zero)["dbp_zero"] == 1


def test_df_to_markdown_formatting():
    """Assert dataframe markdown conversion is properly structured with headers and rows."""
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    md = common.df_to_markdown(df, index=False)
    lines = md.strip().split("\n")
    assert len(lines) == 4  # Header, separator, 2 rows
    assert "| A | B |" in lines[0]
    assert "| --- | --- |" in lines[1]
    assert "| 1 | x |" in lines[2]
    assert "| 2 | y |" in lines[3]