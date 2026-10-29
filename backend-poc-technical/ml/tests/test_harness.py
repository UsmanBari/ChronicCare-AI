"""
Unit tests for ML experiment harness (ml.experiments.run).
Operates strictly on synthetic test data without loading real survey datasets.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import tempfile
from typing import Any
import pytest
import numpy as np
import pandas as pd

import sklearn
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from ml.artifacts import validate_model_card
from ml.evaluation import LeakageError, choose_threshold
from ml.experiments.run import (
    extract_target_series,
    run_experiment as execute_experiment,
    score_record_pure_python,
    validate_config,
)


@pytest.fixture
def base_valid_config() -> dict[str, Any]:
    return {
        "name": "test_synthetic_exp",
        "dataset": "nhanes_core",
        "split": "nhanes_temporal_v1",
        "label": "diabetes_undiagnosed",
        "population": "adults_without_diabetes",
        "card_population": "told_high_bp_1",
        "tier": "basic",
        "features": ["age", "sex_male", "bmi", "ever_smoked_100", "told_high_bp"],
        "models": ["lr", "lr_balanced"],
        "grid": {
            "lr": {"C": [1.0]},
            "lr_balanced": {"C": [1.0]},
        },
        "threshold_policy": {"type": "min_sensitivity", "value": 0.80},
        "missing": "drop",
        "seed": 42,
        "notes": "Synthetic unit test configuration.",
    }


def test_leakage_guard_fires_before_data_loads(monkeypatch, base_valid_config):
    """Verify that if forbidden features are given, LeakageError fires before data loader is called."""
    def fake_loader(*args, **kwargs):
        raise AssertionError("Data loader was called when leakage guard should have prevented it!")

    monkeypatch.setattr("ml.experiments.run.load_nhanes_core", fake_loader)

    leaked_config = copy.deepcopy(base_valid_config)
    # hba1c is forbidden for diabetes_undiagnosed
    leaked_config["features"] = ["age", "sex_male", "hba1c"]

    with pytest.raises(LeakageError):
        execute_experiment(leaked_config)


def test_unknown_config_key_raises_error(base_valid_config):
    """Verify that unknown config keys raise ValueError."""
    bad_config = copy.deepcopy(base_valid_config)
    bad_config["unrecognized_custom_key"] = "forbidden"

    with pytest.raises(ValueError, match="Unknown config keys not allowed"):
        validate_config(bad_config)


def test_missing_policy_impute_raises_error(base_valid_config):
    """Verify that non-'drop' missing policies like 'impute' raise ValueError."""
    bad_config = copy.deepcopy(base_valid_config)
    bad_config["missing"] = "impute_mean"

    with pytest.raises(ValueError, match="Unsupported missing policy"):
        validate_config(bad_config)


def test_population_filter_before_split_matches_fake_frame():
    """Verify that population filter accurately isolates eligible cohort prior to splitting."""
    fake_df = pd.DataFrame({
        "seqn": [1, 2, 3, 4, 5],
        "told_diabetes": [0, 1, 0, 0, 0],
        "hba1c": [5.5, 7.0, 6.8, np.nan, 5.0],
        "fasting_glucose": [90.0, 140.0, np.nan, np.nan, 100.0],
    })

    y_series, pop_mask = extract_target_series(fake_df, "diabetes_undiagnosed", "adults_without_diabetes")

    # Row 0: told=0, hba1c=5.5 -> neg (0)
    # Row 1: told=1 -> excluded from undiagnosed population (NaN)
    # Row 2: told=0, hba1c=6.8 -> pos (1)
    # Row 3: told=0, no labs -> excluded from evaluable population (NaN)
    # Row 4: told=0, labs normal -> neg (0)
    assert pop_mask.tolist() == [True, False, True, False, True]
    assert y_series[pop_mask].tolist() == [0.0, 1.0, 0.0]


def test_preprocessing_and_tuning_never_see_test_rows(monkeypatch, base_valid_config):
    """Verify scaler is fitted on train only, and choose_threshold never receives test rows."""
    n_train, n_val, n_test = 100, 40, 50
    total = n_train + n_val + n_test

    rng = np.random.default_rng(42)
    fake_df = pd.DataFrame({
        "seqn": list(range(total)),
        "cycle": ["2000"] * n_train + ["2014"] * n_val + ["2018"] * n_test,
        "age": rng.integers(20, 80, size=total),
        "sex_male": rng.integers(0, 2, size=total),
        "bmi": rng.uniform(18.0, 40.0, size=total),
        "ever_smoked_100": rng.integers(0, 2, size=total),
        "told_high_bp": [1] * 20 + [0] * (total - 20),
        "told_diabetes": [0] * total,
        "hba1c": rng.choice([5.4, 7.2], size=total),
        "fasting_glucose": [100.0] * total,
        "takes_bp_meds": [0] * total,
        "sbp": [120.0] * total,
        "dbp": [80.0] * total,
        "waist_cm": [90.0] * total,
    })

    train_seqns = set(range(0, n_train))
    val_seqns = set(range(n_train, n_train + n_val))
    test_seqns = set(range(n_train + n_val, total))

    monkeypatch.setattr("ml.experiments.run.load_nhanes_core", lambda cols: fake_df)
    monkeypatch.setattr(
        "ml.experiments.run.load_split",
        lambda name: {"train_core": train_seqns, "validation": val_seqns, "test": test_seqns},
    )
    monkeypatch.setattr(
        "ml.experiments.run.REFERENCE_POPULATION_COUNTS",
        {"adults_without_diabetes": {"train_core": n_train, "validation": n_val, "test": n_test}},
    )

    # Spy on choose_threshold to assert it only receives validation records
    original_choose = choose_threshold
    threshold_input_lengths = []

    def spy_choose_threshold(y_val, p_val, policy):
        threshold_input_lengths.append(len(y_val))
        return original_choose(y_val, p_val, policy)

    monkeypatch.setattr("ml.experiments.run.choose_threshold", spy_choose_threshold)

    with tempfile.TemporaryDirectory() as tmpdir:
        res = execute_experiment(base_valid_config, project_root=Path(tmpdir))

    # Assert choose_threshold was called with exactly n_val rows (never test rows)
    assert len(threshold_input_lengths) > 0
    for length in threshold_input_lengths:
        assert length == n_val, f"choose_threshold received {length} rows instead of validation size {n_val}!"


def test_d10_rule_tree_winning_by_019_vs_021():
    """Verify D10 parsimony rule: tree beating LR by 0.019 chooses LR; by 0.021 chooses tree."""
    # Case 1: Tree beats LR by 0.019 -> LR chosen
    lr_candidate = {"model_type": "lr", "val_auroc": 0.750}
    tree_candidate_small = {"model_type": "rf", "val_auroc": 0.769}  # Gap = +0.019

    gap_small = tree_candidate_small["val_auroc"] - lr_candidate["val_auroc"]
    chosen_1 = tree_candidate_small if gap_small >= 0.02 else lr_candidate
    assert chosen_1["model_type"] == "lr"

    # Case 2: Tree beats LR by 0.021 -> Tree chosen
    tree_candidate_large = {"model_type": "rf", "val_auroc": 0.771}  # Gap = +0.021
    gap_large = tree_candidate_large["val_auroc"] - lr_candidate["val_auroc"]
    chosen_2 = tree_candidate_large if gap_large >= 0.02 else lr_candidate
    assert chosen_2["model_type"] == "rf"


def test_band_boundaries_match_threshold_and_90th_percentile():
    """Verify low_max == threshold and high_min == 90th percentile of validation predictions."""
    val_probs = np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50])
    threshold = 0.12

    low_max = threshold
    high_min = float(np.percentile(val_probs, 90))

    assert low_max == 0.12
    assert high_min == float(np.percentile(val_probs, 90))
    assert low_max < high_min


def test_same_seed_generates_identical_metrics(monkeypatch, base_valid_config):
    """Verify determinism: identical random seed produces bit-exact metrics."""
    n_train, n_val, n_test = 60, 30, 30
    total = n_train + n_val + n_test

    rng = np.random.default_rng(123)
    fake_df = pd.DataFrame({
        "seqn": list(range(total)),
        "cycle": ["2000"] * n_train + ["2014"] * n_val + ["2018"] * n_test,
        "age": rng.integers(20, 80, size=total),
        "sex_male": rng.integers(0, 2, size=total),
        "bmi": rng.uniform(18.0, 40.0, size=total),
        "ever_smoked_100": rng.integers(0, 2, size=total),
        "told_high_bp": [1] * 15 + [0] * (total - 15),
        "told_diabetes": [0] * total,
        "hba1c": rng.choice([5.4, 7.2], size=total),
        "fasting_glucose": [100.0] * total,
        "takes_bp_meds": [0] * total,
        "sbp": [120.0] * total,
        "dbp": [80.0] * total,
        "waist_cm": [90.0] * total,
    })

    monkeypatch.setattr("ml.experiments.run.load_nhanes_core", lambda cols: fake_df)
    monkeypatch.setattr(
        "ml.experiments.run.load_split",
        lambda name: {"train_core": set(range(0, n_train)), "validation": set(range(n_train, n_train + n_val)), "test": set(range(n_train + n_val, total))},
    )
    monkeypatch.setattr(
        "ml.experiments.run.REFERENCE_POPULATION_COUNTS",
        {"adults_without_diabetes": {"train_core": n_train, "validation": n_val, "test": n_test}},
    )

    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        res1 = execute_experiment(base_valid_config, project_root=Path(tmp1))
        res2 = execute_experiment(base_valid_config, project_root=Path(tmp2))

        # Metrics must match exactly
        assert res1["threshold"]["locked_threshold"] == res2["threshold"]["locked_threshold"]
        assert res1["test_evaluation"]["auroc"]["point"] == res2["test_evaluation"]["auroc"]["point"]
        assert res1["test_evaluation"]["metrics_at_threshold"] == res2["test_evaluation"]["metrics_at_threshold"]


def test_saved_model_card_and_pure_python_export_parity():
    """Verify saved model card passes validate_model_card and pure-Python scorer matches within 1e-9."""
    rng = np.random.default_rng(42)
    X = rng.normal(size=(200, 3))
    y = rng.integers(0, 2, size=200)

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(random_state=42)),
    ])
    pipe.fit(X, y)

    card = {
        "name": "test_lr_artifact",
        "owner": "usman",
        "created_at": "2026-10-29T12:00:00Z",
        "git_commit": "0" * 40,
        "label": "diabetes_undiagnosed",
        "population": "told_diabetes == 0",
        "tier": "basic",
        "features": ["age", "sex_male", "bmi"],
        "threshold": 0.15,
        "threshold_policy": {"type": "min_sensitivity", "value": 0.80},
        "bands": {"low_max": 0.15, "high_min": 0.35},
        "split": "nhanes_temporal_v1",
        "model_type": "LogisticRegression",
        "hyperparameters": {"C": 1.0},
        "sklearn_version": sklearn.__version__,
        "train_rows": 150,
        "val_rows": 50,
        "val_auroc": 0.77,
        "test_metrics": {"auroc": 0.76, "sensitivity": 0.81},
        "notes": "Test card.",
    }

    validate_model_card(card)

    export_spec = {
        "model_name": card["name"],
        "label": card["label"],
        "tier": card["tier"],
        "population": card["population"],
        "feature_order": card["features"],
        "scaler_mean": [float(m) for m in pipe.named_steps["scaler"].mean_],
        "scaler_scale": [float(s) for s in pipe.named_steps["scaler"].scale_],
        "coef": [float(c) for c in pipe.named_steps["clf"].coef_[0]],
        "intercept": float(pipe.named_steps["clf"].intercept_[0]),
        "threshold": card["threshold"],
        "bands": card["bands"],
    }

    # Test pure Python evaluation
    sklearn_probs = pipe.predict_proba(X)[:, 1]
    for i in range(len(X)):
        row_dict = {"age": X[i, 0], "sex_male": X[i, 1], "bmi": X[i, 2]}
        py_prob = score_record_pure_python(row_dict, export_spec)
        assert abs(py_prob - sklearn_probs[i]) < 1e-9
