"""
Unit tests for external validation pipeline and clinical safety invariants.
"""
from pathlib import Path

import ml.external_validation as ev
import numpy as np
import pandas as pd
import pytest
import sklearn
from ml.artifacts import save_model_artifact
from ml.external_validation import (
    evaluate_pair,
    get_candidate_datasets_for_model,
    get_model_disease_category,
)
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@pytest.fixture
def synthetic_model_dir(tmp_path: Path):
    """Create a minimal valid synthetic model artifact for testing."""
    model_dir = tmp_path / "synthetic_diabetes_model"
    model_dir.mkdir()

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(random_state=42)),
    ])
    # Fit on minimal synthetic data
    X_dummy = np.array([[20, 0, 22], [40, 1, 28], [60, 0, 32], [70, 1, 35]])
    y_dummy = np.array([0, 0, 1, 1])
    pipe.fit(X_dummy, y_dummy)

    card = {
        "name": "synthetic_diabetes_model",
        "label": "diabetes_told",
        "tier": "basic",
        "model_type": "LogisticRegression",
        "features": ["age", "sex_male", "bmi"],
        "hyperparameters": {"C": 1.0},
        "threshold": 0.42,
        "threshold_policy": {"type": "min_sensitivity", "value": 0.80},
        "bands": {"low_max": 0.20, "high_min": 0.60},
        "population": "Synthetic Adult Test Population",
        "test_metrics": {"auroc": 0.85},
        "train_rows": 100,
        "val_rows": 50,
        "val_auroc": 0.82,
        "split": "synthetic_v1",
        "owner": "saad",
        "notes": "Synthetic model for testing",
        "created_at": "2026-11-01T00:00:00Z",
        "git_commit": "abcdef1234567890",
        "sklearn_version": sklearn.__version__,
    }

    save_model_artifact(pipeline=pipe, card=card, out_dir=model_dir)
    return model_dir, pipe, card


def test_label_with_no_equivalent_is_skipped():
    """Verify that a model with a label lacking an external equivalent is skipped."""
    card = {"label": "unrelated_biomarker_xyz", "features": ["age", "bmi"]}
    disease = get_model_disease_category(card["label"])
    assert disease is None

    candidates = get_candidate_datasets_for_model(card)
    assert candidates == []


def test_as_saved_mode_when_all_features_present(synthetic_model_dir):
    """Verify that as-saved mode is selected when all model features are in the dataset."""
    _, pipe, card = synthetic_model_dir

    df_ext = pd.DataFrame({
        "age": [30, 45, 60, 75],
        "sex_male": [0, 1, 0, 1],
        "bmi": [22.0, 26.5, 30.0, 34.0],
        "diabetes": [0, 0, 1, 1],
    })

    res = evaluate_pair(
        model_name="synthetic_diabetes_model",
        pipeline=pipe,
        card=card,
        dataset_name="test_ext_dataset",
        target_col="diabetes",
        dataset_df=df_ext,
    )

    assert res["status"] == "PASS"
    assert res["mode"] == "as-saved"
    assert res["missing_features"] == ""
    assert res["threshold"] == 0.42  # Card's threshold preserved
    assert res["n"] == 4
    assert res["auroc"] == 1.0


def test_overlap_refit_mode_when_features_missing(synthetic_model_dir, monkeypatch):
    """
    Verify overlap refit mode when some features are missing but overlap >= 2.
    Asserts threshold is chosen from NHANES validation and never re-tuned on external data.
    """
    _, pipe, card = synthetic_model_dir
    card_with_extra_feature = dict(card)
    card_with_extra_feature["features"] = ["age", "sex_male", "bmi", "waist_cm"]

    df_ext = pd.DataFrame({
        "age": [30, 45, 60, 75],
        "sex_male": [0, 1, 0, 1],
        "bmi": [22.0, 26.5, 30.0, 34.0],
        # waist_cm is missing
        "diabetes": [0, 0, 1, 1],
    })

    # Spy on choose_threshold to verify what arrays are passed
    choose_calls = []
    real_choose = ev.choose_threshold

    def spy_choose(y_val, p_val, policy):
        choose_calls.append({"y_len": len(y_val), "p_len": len(p_val)})
        return real_choose(y_val, p_val, policy)

    monkeypatch.setattr(ev, "choose_threshold", spy_choose)

    # Create synthetic NHANES reference data so test never depends on real parquet
    rng = np.random.default_rng(42)
    n_train = 100
    n_val = 50
    n_total = n_train + n_val
    synth_nhanes = pd.DataFrame({
        "seqn": list(range(n_total)),
        "age": rng.uniform(20, 80, n_total),
        "sex_male": rng.choice([0, 1], n_total),
        "bmi": rng.uniform(18, 40, n_total),
        "waist_cm": rng.uniform(60, 120, n_total),
        "told_diabetes": np.concatenate([
            rng.choice([0, 1], n_train, p=[0.7, 0.3]),
            rng.choice([0, 1], n_val, p=[0.7, 0.3]),
        ]),
    })
    synth_splits = {
        "train_core": set(range(n_train)),
        "validation": set(range(n_train, n_total)),
        "test": set(),
    }

    res = evaluate_pair(
        model_name="synthetic_diabetes_model",
        pipeline=pipe,
        card=card_with_extra_feature,
        dataset_name="test_ext_dataset",
        target_col="diabetes",
        dataset_df=df_ext,
        nhanes_df=synth_nhanes,
        splits=synth_splits,
    )

    assert res["status"] == "PASS"
    assert res["mode"] == "overlap refit, not Usman's saved model"
    assert "waist_cm" in res["missing_features"]

    # CRITICAL CLINICAL SAFETY ASSERTION:
    # choose_threshold must be called during overlap refit on NHANES validation,
    # NEVER with the external dataset length (len=4).
    assert len(choose_calls) == 1
    assert choose_calls[0]["y_len"] != len(df_ext)
    assert choose_calls[0]["y_len"] == n_val  # Reference validation split size


def test_overlap_under_two_features_is_not_run(synthetic_model_dir):
    """Verify that when overlapping features < 2, pair is flagged NOT RUN (< 2 features)."""
    _, pipe, card = synthetic_model_dir
    card_extra = dict(card)
    card_extra["features"] = ["age", "special_lab_1", "special_lab_2"]

    # Dataset only contains 'age' (overlap = 1 < 2)
    df_ext = pd.DataFrame({
        "age": [30, 45, 60, 75],
        "diabetes": [0, 0, 1, 1],
    })

    res = evaluate_pair(
        model_name="synthetic_model",
        pipeline=pipe,
        card=card_extra,
        dataset_name="test_ext_dataset",
        target_col="diabetes",
        dataset_df=df_ext,
    )

    assert res["status"] == "NOT RUN"
    assert "NOT RUN (< 2 features)" in res["mode"]
    assert "special_lab_1" in res["missing_features"]


def test_missing_dataset_returns_not_run_without_crashing(synthetic_model_dir):
    """Verify that a missing dataset returns NOT RUN rather than crashing."""
    _, pipe, card = synthetic_model_dir

    res = evaluate_pair(
        model_name="synthetic_model",
        pipeline=pipe,
        card=card,
        dataset_name="nonexistent_dataset",
        target_col="diabetes",
        dataset_df=None,  # Dataset failed to load
    )

    assert res["status"] == "NOT RUN"
    assert "missing" in res["notes"].lower()


def test_cardio70k_skipped_for_models_with_bp_features():
    """Verify Cardio70k is excluded from candidates for models with BP features."""
    # Model 1: no BP feature -> Cardio70k included
    card_no_bp = {"label": "hypertension_measured_130_80", "features": ["age", "bmi"]}
    candidates_no_bp = [c[0] for c in get_candidate_datasets_for_model(card_no_bp)]
    assert "cardio70k" in candidates_no_bp

    # Model 2: has BP feature -> Cardio70k excluded
    card_with_bp = {"label": "hypertension_measured_130_80", "features": ["age", "bmi", "sbp", "dbp"]}
    candidates_with_bp = [c[0] for c in get_candidate_datasets_for_model(card_with_bp)]
    assert "cardio70k" not in candidates_with_bp
