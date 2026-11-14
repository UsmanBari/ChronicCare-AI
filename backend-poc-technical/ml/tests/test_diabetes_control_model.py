"""
Hermetic unit tests for the diabetes glycaemic control model (diabetes_control_nhanes),
target label extraction logic, safety non-shipment assertions, and feature contracts.
Strictly runs without any dataset files or $env:CHRONICCARE_DATA_DIR.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.labels import LABELS, extract_diabetes_poor_control_80


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_MODEL_PATH = REPO_ROOT / "models" / "diabetes_control_nhanes.json"
CONFIG_PATH = REPO_ROOT / "ml" / "experiments" / "configs" / "diabetes_control_nhanes.json"

EXPECTED_FEATURE_ORDER = [
    "age",
    "sex_male",
    "bmi",
    "waist_cm",
    "ever_smoked_100",
    "sbp",
    "dbp",
    "on_insulin",
    "on_diabetes_pills",
]


def test_extract_diabetes_poor_control_80_threshold_and_eligibility():
    """
    Test extraction of diabetes_poor_control_80 label on synthetic micro-dataframe:
    - Diagnosed (told_diabetes == 1) with HbA1c < 8.0 -> 0.0
    - Diagnosed (told_diabetes == 1) with HbA1c == 8.0 -> 1.0 (boundary)
    - Diagnosed (told_diabetes == 1) with HbA1c > 8.0 -> 1.0
    - Undiagnosed (told_diabetes == 0) -> NaN (excluded from cohort)
    - Diagnosed with missing HbA1c -> NaN
    """
    df = pd.DataFrame({
        "told_diabetes": [1, 1, 1, 0, 1],
        "hba1c": [7.9, 8.0, 8.1, 9.5, np.nan],
    })

    y = extract_diabetes_poor_control_80(df)

    assert y.iloc[0] == 0.0, f"Expected 0.0 for HbA1c 7.9, got {y.iloc[0]}"
    assert y.iloc[1] == 1.0, f"Expected 1.0 for HbA1c 8.0, got {y.iloc[1]}"
    assert y.iloc[2] == 1.0, f"Expected 1.0 for HbA1c 8.1, got {y.iloc[2]}"
    assert np.isnan(y.iloc[3]), f"Expected NaN for undiagnosed patient, got {y.iloc[3]}"
    assert np.isnan(y.iloc[4]), f"Expected NaN for missing HbA1c, got {y.iloc[4]}"


def test_label_registry_definition():
    """Verify diabetes_poor_control_80 metadata and forbidden leakage features."""
    assert "diabetes_poor_control_80" in LABELS
    info = LABELS["diabetes_poor_control_80"]
    assert info.disease == "diabetes"
    assert "hba1c" in info.forbidden_features
    assert "fasting_glucose" in info.forbidden_features
    assert "glucose" in info.forbidden_features


def test_experiment_config_feature_contract():
    """Verify declarative experiment config adheres to pre-registered 9 features."""
    assert CONFIG_PATH.is_file(), f"Config file missing: {CONFIG_PATH}"
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert config["name"] == "diabetes_control_nhanes"
    assert config["dataset"] == "nhanes_core"
    assert config["split"] == "nhanes_temporal_v1"
    assert config["label"] == "diabetes_poor_control_80"
    assert config["population"] == "adults_with_diagnosed_diabetes"
    assert config["features"] == EXPECTED_FEATURE_ORDER
    assert config["threshold_policy"] == {"type": "min_sensitivity", "value": 0.80}


def test_safety_non_shipment_guard():
    """
    Assert that models/diabetes_control_nhanes.json is NOT present in production.
    The model failed pre-registered Gate 2 (calibration slope 1.439 outside [0.80, 1.20])
    and Gate 4 (subgroup sensitivity on on_insulin=0 of 53.77% < 60.0%).
    Under ChronicCare-AI safety rules, uncalibrated risk models must NEVER be exported
    to production JSON to prevent distorted clinical decision-support.
    """
    assert not PRODUCTION_MODEL_PATH.exists(), (
        f"Safety violation: {PRODUCTION_MODEL_PATH} must NOT exist because diabetes_control_nhanes "
        f"failed pre-registered gates G2 and G4 and is NOT SHIPPED."
    )
