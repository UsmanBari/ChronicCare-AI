"""
Unit tests for model artifact persistence, model card validation,
and production pure-Python scoring export (backend-poc-technical/ml/artifacts.py).
Strictly uses synthetic dummy estimators and temporary directories.
"""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.artifacts import (
    REQUIRED_MODEL_CARD_KEYS,
    export_production_lr,
    load_model_artifact,
    save_model_artifact,
    validate_model_card,
)
from ml.evaluation import LeakageError


@pytest.fixture
def valid_card() -> dict:
    return {
        "name": "synthetic_test_model",
        "owner": "saad",
        "created_at": "2026-10-28T12:00:00Z",
        "git_commit": "abcdef1234567890",
        "label": "diabetes_told",
        "features": ["age", "sex_male", "bmi"],
        "threshold": 0.45,
        "threshold_policy": {"type": "min_sensitivity", "value": 0.80},
        "split": "nhanes_temporal_v1",
        "model_type": "LogisticRegression",
        "hyperparameters": {"C": 1.0, "random_state": 42},
        "sklearn_version": "1.9.1",
        "train_rows": 100,
        "val_rows": 50,
        "val_auroc": 0.785,
        "notes": "Synthetic model for testing.",
        "population": "adults_without_diabetes",
        "tier": "basic",
        "test_metrics": {"auroc": 0.78, "brier": 0.12},
        "bands": {"low_max": 0.45, "high_min": 0.75},
    }


def test_artifact_round_trip(tmp_path, valid_card):
    # Fit dummy pipeline on synthetic data
    X = np.array([[25.0, 1.0, 22.0], [55.0, 0.0, 31.0], [70.0, 1.0, 35.0], [30.0, 0.0, 24.0], [60.0, 1.0, 28.0]])
    y = np.array([0, 1, 1, 0, 1])

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(random_state=42)),
    ])
    pipe.fit(X, y)

    # Save artifact
    out_dir = tmp_path / "model_artifact"
    saved_dir = save_model_artifact(pipe, valid_card, out_dir)
    assert saved_dir.is_dir()
    assert (saved_dir / "model.joblib").exists()
    assert (saved_dir / "model_card.json").exists()

    # Load artifact
    loaded_pipe, loaded_card = load_model_artifact(saved_dir)

    # Assert predictions on 5 test rows are identical
    orig_preds = pipe.predict_proba(X)
    loaded_preds = loaded_pipe.predict_proba(X)
    np.testing.assert_allclose(orig_preds, loaded_preds, rtol=1e-6)

    # Assert model card metadata is preserved
    assert loaded_card["name"] == valid_card["name"]
    assert loaded_card["threshold"] == valid_card["threshold"]
    assert loaded_card["population"] == valid_card["population"]
    assert loaded_card["tier"] == valid_card["tier"]


def test_validate_model_card_missing_key(valid_card):
    card = valid_card.copy()
    del card["features"]
    with pytest.raises(ValueError, match="missing required key"):
        validate_model_card(card)


def test_validate_model_card_extra_key(valid_card):
    card = valid_card.copy()
    card["unauthorized_secret_flag"] = "dangerous"
    with pytest.raises(ValueError, match="unrecognized extra key"):
        validate_model_card(card)


def test_validate_model_card_unknown_label(valid_card):
    card = valid_card.copy()
    card["label"] = "not_a_real_registered_label"
    with pytest.raises(ValueError, match="Unknown label"):
        validate_model_card(card)


def test_validate_model_card_leakage(valid_card):
    card = valid_card.copy()
    card["label"] = "diabetes_measured"
    card["features"] = ["age", "bmi", "hba1c"]
    with pytest.raises(LeakageError, match="Target leakage detected"):
        validate_model_card(card)


def test_validate_model_card_invalid_threshold(valid_card):
    card = valid_card.copy()
    card["threshold"] = 1.5
    with pytest.raises(ValueError, match="threshold"):
        validate_model_card(card)

    card["threshold"] = -0.05
    with pytest.raises(ValueError, match="threshold"):
        validate_model_card(card)


def test_validate_model_card_new_keys(valid_card):
    # Invalid tier
    c1 = valid_card.copy()
    c1["tier"] = "ultra_mega"
    with pytest.raises(ValueError, match="tier"):
        validate_model_card(c1)

    # Invalid bands
    c2 = valid_card.copy()
    c2["bands"] = {"invalid_band": 0.5}
    with pytest.raises(ValueError, match="bands"):
        validate_model_card(c2)

    # Invalid population
    c3 = valid_card.copy()
    c3["population"] = ""
    with pytest.raises(ValueError, match="population"):
        validate_model_card(c3)

    # Invalid test_metrics
    c4 = valid_card.copy()
    c4["test_metrics"] = "not_a_dict"
    with pytest.raises(ValueError, match="test_metrics"):
        validate_model_card(c4)


def test_validate_model_card_sklearn_version_warning(valid_card):
    card = valid_card.copy()
    card["sklearn_version"] = "0.22.0"

    with pytest.warns(UserWarning, match="scikit-learn 0.22.0"):
        validate_model_card(card)


def test_pure_python_scorer_matches_pipeline_within_1e9(tmp_path, valid_card):
    """
    USMAN DECISION / PRODUCTION EXPORT TEST:
    Backend NEVER loads model.joblib. Pure-Python scorer must reproduce
    pipeline's predict_proba to within 1e-9 on 1,000 synthetic validation rows.
    """
    rng = np.random.default_rng(42)
    # 1000 validation rows with 3 features: age (18-80), sex_male (0/1), bmi (15-50)
    age = rng.uniform(18.0, 80.0, size=1000)
    sex = rng.choice([0.0, 1.0], size=1000)
    bmi = rng.uniform(15.0, 50.0, size=1000)
    X_val = np.column_stack([age, sex, bmi])

    # Fit dummy logistic regression pipeline
    y_train = rng.choice([0, 1], size=200)
    X_train = rng.normal(size=(200, 3))
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(random_state=42)),
    ])
    pipe.fit(X_train, y_train)

    # Export production payload
    export_file = tmp_path / "export.json"
    export_payload = export_production_lr(pipe, valid_card, export_file)

    # Pure Python scorer implementation (as used by production runtime)
    def score_pure_python(X_raw: np.ndarray, export_dict: dict) -> np.ndarray:
        means = np.array(export_dict["scaler_mean"])
        scales = np.array(export_dict["scaler_scale"])
        coefs = np.array(export_dict["coef"])
        intercept = export_dict["intercept"]

        # Standardize: (x - mean) / scale
        X_scaled = (X_raw - means) / scales
        # Logit: intercept + dot(X_scaled, coef)
        logits = intercept + np.dot(X_scaled, coefs)
        # Probability: 1 / (1 + exp(-logits))
        return 1.0 / (1.0 + np.exp(-logits))

    # Evaluate both
    sklearn_probs = pipe.predict_proba(X_val)[:, 1]
    pure_python_probs = score_pure_python(X_val, export_payload)

    # Assert exact match to within 1e-9
    diff = np.abs(sklearn_probs - pure_python_probs)
    max_diff = np.max(diff)
    assert max_diff < 1e-9, f"Max difference {max_diff} exceeded 1e-9 threshold!"
