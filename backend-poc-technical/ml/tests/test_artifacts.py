"""
Unit tests for model artifact persistence and model card validation
(backend-poc-technical/ml/artifacts.py).
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
    # hba1c leaks diabetes_measured
    card["label"] = "diabetes_measured"
    card["features"] = ["age", "bmi", "hba1c"]
    with pytest.raises(LeakageError, match="Target leakage detected"):
        validate_model_card(card)


def test_validate_model_card_invalid_threshold(valid_card):
    card = valid_card.copy()
    card["threshold"] = 1.5  # Outside [0, 1]
    with pytest.raises(ValueError, match="threshold"):
        validate_model_card(card)

    card["threshold"] = -0.05
    with pytest.raises(ValueError, match="threshold"):
        validate_model_card(card)


def test_validate_model_card_sklearn_version_warning(valid_card):
    card = valid_card.copy()
    card["sklearn_version"] = "0.22.0"  # Deliberate mismatch

    with pytest.warns(UserWarning, match="scikit-learn 0.22.0"):
        validate_model_card(card)
