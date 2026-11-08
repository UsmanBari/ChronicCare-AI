"""
Hermetic unit tests for the 10-year CHD Framingham risk model,
pure-Python inference scorer, golden dataset verification, risk bands,
and stratified random splits.
Strictly runs without any dataset files or $env:CHRONICCARE_DATA_DIR.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.splits import generate_stratified_random_splits, generate_nhanes_temporal_splits


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_MODEL_PATH = REPO_ROOT / "models" / "chd10_framingham.json"
GOLDEN_PATH = REPO_ROOT / "models" / "chd10_framingham.golden.json"

EXPECTED_FEATURE_ORDER = [
    "age",
    "sex_male",
    "current_smoker",
    "bmi",
    "sbp",
    "dbp",
    "bp_meds",
    "diabetes",
    "prevalent_hyp",
]


def score_pure_python(inputs: dict[str, float], model_spec: dict) -> float:
    """Pure-Python sigmoid calculation without scikit-learn."""
    feats = model_spec["feature_order"]
    mean = model_spec["scaler_mean"]
    scale = model_spec["scaler_scale"]
    coef = model_spec["coef"]
    intercept = model_spec["intercept"]

    z = 0.0
    for i, f in enumerate(feats):
        val = float(inputs[f])
        val_scaled = (val - mean[i]) / scale[i]
        z += coef[i] * val_scaled
    z += intercept

    prob = 1.0 / (1.0 + math.exp(-z))
    return prob


def assign_risk_band(prob: float, bands: dict[str, float]) -> str:
    low_max = bands["low_max"]
    high_min = bands["high_min"]
    if prob < low_max:
        return "low"
    elif prob < high_min:
        return "moderate"
    else:
        return "high"


def test_production_model_structure():
    assert PRODUCTION_MODEL_PATH.is_file(), f"Model file missing: {PRODUCTION_MODEL_PATH}"
    spec = json.loads(PRODUCTION_MODEL_PATH.read_text(encoding="utf-8"))

    # Feature order contract
    assert spec["feature_order"] == EXPECTED_FEATURE_ORDER
    assert len(spec["coef"]) == len(EXPECTED_FEATURE_ORDER)
    assert len(spec["scaler_mean"]) == len(EXPECTED_FEATURE_ORDER)
    assert len(spec["scaler_scale"]) == len(EXPECTED_FEATURE_ORDER)

    # Doctor addendum: audience and patient note
    assert spec["audience"] == "provider_and_patient_band"
    assert "patient_note" in spec
    assert "en" in spec["patient_note"]
    assert "ur" in spec["patient_note"]
    assert "roman_ur" in spec["patient_note"]
    assert spec["patient_note"]["needs_native_review"] is True

    # Provider disclaimer preserved
    assert spec["label_text"]["en"] == "Experimental: trained on US Framingham data, not validated for Pakistani patients"
    assert spec["label_text"]["needs_native_review"] is True

    # Bands
    assert spec["bands"]["low_max"] == 0.10
    assert spec["bands"]["high_min"] == 0.20
    assert spec["threshold"] == 0.10


def test_golden_dataset_matches_pure_python():
    assert GOLDEN_PATH.is_file(), f"Golden file missing: {GOLDEN_PATH}"
    spec = json.loads(PRODUCTION_MODEL_PATH.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert len(golden) == 10, f"Expected 10 golden inputs, found {len(golden)}"

    for i, row in enumerate(golden):
        inputs = row["inputs"]
        expected_prob = row["expected_prob"]
        expected_band = row["expected_band"]

        # 1. Pure python scorer
        computed_prob = score_pure_python(inputs, spec)
        diff = abs(computed_prob - expected_prob)
        assert diff < 1e-9, f"Row {i} probability mismatch: computed={computed_prob}, expected={expected_prob}, diff={diff}"

        # 2. Band matches expected
        computed_band = assign_risk_band(computed_prob, spec["bands"])
        assert computed_band == expected_band, f"Row {i} band mismatch: computed={computed_band}, expected={expected_band}"


def test_risk_band_exact_boundaries():
    bands = {"low_max": 0.10, "high_min": 0.20}

    assert assign_risk_band(0.0000, bands) == "low"
    assert assign_risk_band(0.0999999, bands) == "low"
    assert assign_risk_band(0.1000000, bands) == "moderate"
    assert assign_risk_band(0.1500, bands) == "moderate"
    assert assign_risk_band(0.1999999, bands) == "moderate"
    assert assign_risk_band(0.2000000, bands) == "high"
    assert assign_risk_band(0.8500, bands) == "high"


def test_generate_stratified_random_splits_determinism_and_disjointness():
    # Synthetic DataFrame with 500 rows and 15% prevalence
    np.random.seed(123)
    n = 500
    y = (np.random.rand(n) < 0.15).astype(int)
    df = pd.DataFrame({
        "sample_id": np.arange(n),
        "TenYearCHD": y,
        "feature_1": np.random.randn(n),
    })

    splits_1 = generate_stratified_random_splits(df, target_col="TenYearCHD", seed=42)
    splits_2 = generate_stratified_random_splits(df, target_col="TenYearCHD", seed=42)

    # 1. Strict Determinism
    for s in ["train_core", "validation", "test"]:
        assert splits_1[s] == splits_2[s], f"Split {s} is not deterministic"

    # 2. Disjointness
    s_train = set(splits_1["train_core"])
    s_val = set(splits_1["validation"])
    s_test = set(splits_1["test"])

    assert s_train.isdisjoint(s_val)
    assert s_train.isdisjoint(s_test)
    assert s_val.isdisjoint(s_test)

    # 3. Exhaustive coverage
    assert (s_train | s_val | s_test) == set(df.index)

    # 4. Proportions ~ 60/20/20
    assert len(s_train) == int(0.60 * n)
    assert len(s_val) == int(0.20 * n)
    assert len(s_test) == n - len(s_train) - len(s_val)

    # 5. Different seed yields different split
    splits_diff = generate_stratified_random_splits(df, target_col="TenYearCHD", seed=999)
    assert splits_1["train_core"] != splits_diff["train_core"]


def test_nhanes_temporal_splits_unchanged():
    # Verify existing NHANES temporal split logic remains completely intact
    df_nhanes = pd.DataFrame([
        {"seqn": 101, "cycle": "1999-2000", "age": 40},
        {"seqn": 102, "cycle": "2013-2014", "age": 45},
        {"seqn": 103, "cycle": "2017-2018", "age": 50},
        {"seqn": 104, "cycle": "2017-2018", "age": 15},  # Under 18
    ])
    splits = generate_nhanes_temporal_splits(df_nhanes)
    assert 101 in splits["train_core"]
    assert 102 in splits["validation"]
    assert 103 in splits["test"]
    assert 104 not in (set(splits["train_core"]) | set(splits["validation"]) | set(splits["test"]))
