"""
Plotting utilities for ML model evaluation.
Generates ROC curves and calibration reliability diagrams.
Saves ONLY to git-ignored outputs directory (backend-poc-technical/ml/outputs/).

NOTE: This module is an OPTIONAL visualizer for local developers and is NOT
run or required in CI pipelines (matplotlib is not pinned as a CI test dependency).
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

from ml.evaluation import auroc, calibration


def _get_default_output_dir() -> Path:
    out = Path(__file__).resolve().parent / "outputs" / "plots"
    out.mkdir(parents=True, exist_ok=True)
    return out


def roc_plot(
    y_true: Sequence[int] | np.ndarray,
    y_prob: Sequence[float] | np.ndarray,
    out_path: Path | str | None = None,
    title: str = "Receiver Operating Characteristic (ROC)",
) -> Path:
    """
    Generate and save an ROC curve plot.
    Saved strictly to git-ignored outputs directory.
    """
    try:
        import matplotlib.pyplot as plt
        from sklearn.metrics import roc_curve
    except ImportError as e:
        raise ImportError("matplotlib is required to generate plots.") from e

    y_arr = np.asarray(y_true, dtype=int)
    p_arr = np.asarray(y_prob, dtype=float)

    fpr, tpr, _ = roc_curve(y_arr, p_arr)
    score = auroc(y_arr, p_arr)

    if out_path is None:
        out_file = _get_default_output_dir() / "roc_curve.png"
    else:
        out_file = Path(out_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6))
    label = f"Model (AUROC = {score:.4f})" if score is not None else "Model"
    ax.plot(fpr, tpr, color="#2563eb", lw=2, label=label)
    ax.plot([0, 1], [0, 1], color="#94a3b8", lw=1.5, linestyle="--", label="Chance")
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel("False Positive Rate (1 - Specificity)")
    ax.set_ylabel("True Positive Rate (Sensitivity)")
    ax.set_title(title)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_file, dpi=150)
    plt.close(fig)

    return out_file


def reliability_plot(
    y_true: Sequence[int] | np.ndarray,
    y_prob: Sequence[float] | np.ndarray,
    n_bins: int = 10,
    out_path: Path | str | None = None,
    title: str = "Calibration Reliability Diagram",
) -> Path:
    """
    Generate and save a calibration reliability plot.
    Saved strictly to git-ignored outputs directory.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib is required to generate plots.") from e

    cal_res = calibration(y_true, y_prob, n_bins=n_bins)
    table = cal_res["reliability_table"]

    mean_p = [r["mean_p"] for r in table]
    obs = [r["observed_rate"] for r in table]

    if out_path is None:
        out_file = _get_default_output_dir() / "reliability_diagram.png"
    else:
        out_file = Path(out_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(mean_p, obs, marker="o", color="#0284c7", lw=2, label="Reliability Curve")
    ax.plot([0, 1], [0, 1], color="#94a3b8", lw=1.5, linestyle="--", label="Perfect Calibration")

    brier = cal_res["brier"]
    slope = cal_res["slope"]
    sub_title = []
    if brier is not None:
        sub_title.append(f"Brier: {brier:.4f}")
    if slope is not None:
        sub_title.append(f"Slope: {slope:.3f}")
    if sub_title:
        ax.set_title(f"{title}\n({', '.join(sub_title)})")
    else:
        ax.set_title(title)

    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.0])
    ax.set_xlabel("Mean Predicted Probability")
    ax.set_ylabel("Observed Positive Fraction")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_file, dpi=150)
    plt.close(fig)

    return out_file
