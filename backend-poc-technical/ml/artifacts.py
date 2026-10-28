"""
Model artifact serialization, loading, and schema validation.
Defines the contract for saving and loading trained clinical risk models
between Usman's experiment harness and downstream evaluation/inference tooling.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import warnings

import joblib
import sklearn

from ml.evaluation import check_leakage
from ml.labels import LABELS

REQUIRED_MODEL_CARD_KEYS = {
    "name",
    "owner",
    "created_at",
    "git_commit",
    "label",
    "features",
    "threshold",
    "threshold_policy",
    "split",
    "model_type",
    "hyperparameters",
    "sklearn_version",
    "train_rows",
    "val_rows",
    "val_auroc",
    "notes",
}


def validate_model_card(card: dict[str, Any]) -> None:
    """
    Validate a model card dictionary against the strict schema contract.

    Raises
    ------
    ValueError:
        If required keys are missing, extra unexpected keys exist,
        the label is unknown, or the threshold is outside [0.0, 1.0].
    LeakageError:
        If the feature list contains forbidden features for the target label.
    UserWarning:
        If sklearn_version does not match the currently installed scikit-learn version.
    """
    card_keys = set(card.keys())

    missing = REQUIRED_MODEL_CARD_KEYS - card_keys
    if missing:
        raise ValueError(f"Model card missing required key(s): {sorted(missing)}")

    extra = card_keys - REQUIRED_MODEL_CARD_KEYS
    if extra:
        raise ValueError(f"Model card contains unrecognized extra key(s): {sorted(extra)}")

    # 1. Label existence
    label = card["label"]
    if label not in LABELS:
        raise ValueError(f"Unknown label '{label}' in model card. Registered labels: {sorted(LABELS.keys())}")

    # 2. Features and Target Leakage
    features = card["features"]
    if not isinstance(features, list) or len(features) == 0:
        raise ValueError("Model card 'features' must be a non-empty ordered list of feature column names.")

    check_leakage(label, features)

    # 3. Threshold bounds [0.0, 1.0]
    thresh = card["threshold"]
    if not isinstance(thresh, (int, float)) or thresh < 0.0 or thresh > 1.0:
        raise ValueError(f"Model card 'threshold' must be a float in range [0.0, 1.0], got {thresh}")

    # 4. Scikit-learn version mismatch check
    installed_ver = sklearn.__version__
    card_ver = str(card.get("sklearn_version", ""))
    if card_ver != installed_ver:
        warnings.warn(
            f"Model artifact was saved with scikit-learn {card_ver}, but the currently "
            f"installed version is {installed_ver}. Loading pickled models across "
            f"different scikit-learn versions may cause compatibility warnings or prediction discrepancies.",
            UserWarning,
            stacklevel=2,
        )


def save_model_artifact(
    pipeline: Any,
    card: dict[str, Any],
    out_dir: Path | str,
) -> Path:
    """
    Save a fitted scikit-learn Pipeline and its corresponding model card.

    Parameters
    ----------
    pipeline : Any
        Fitted sklearn Pipeline or estimator.
    card : dict
        Model card metadata satisfying validate_model_card.
    out_dir : Path | str
        Output directory path (e.g. backend-poc-technical/ml/outputs/models/<model_name>).

    Returns
    -------
    Path:
        The directory where artifacts were saved.
    """
    validate_model_card(card)

    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    model_path = target_dir / "model.joblib"
    joblib.dump(pipeline, model_path)

    card_path = target_dir / "model_card.json"
    card_path.write_text(json.dumps(card, indent=2, sort_keys=True), encoding="utf-8")

    return target_dir


def load_model_artifact(dir_path: Path | str) -> tuple[Any, dict[str, Any]]:
    """
    Load a saved model pipeline and its model card metadata.

    Parameters
    ----------
    dir_path : Path | str
        Directory containing model.joblib and model_card.json.

    Returns
    -------
    tuple[Any, dict[str, Any]]:
        (fitted_pipeline, validated_model_card)
    """
    p = Path(dir_path)
    if not p.is_dir():
        raise FileNotFoundError(f"Model artifact directory not found: {p}")

    card_file = p / "model_card.json"
    if not card_file.is_file():
        raise FileNotFoundError(f"model_card.json not found in {p}")

    model_file = p / "model.joblib"
    if not model_file.is_file():
        raise FileNotFoundError(f"model.joblib not found in {p}")

    card_data = json.loads(card_file.read_text(encoding="utf-8"))
    validate_model_card(card_data)

    pipeline = joblib.load(model_file)
    return pipeline, card_data
