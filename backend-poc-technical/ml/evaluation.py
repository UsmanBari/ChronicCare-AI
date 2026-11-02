"""
Evaluation toolkit for ChronicCare AI risk models.
Provides pure, reproducible evaluation functions for threshold selection,
performance metrics, bootstrap confidence intervals, calibration, subgroup
analysis, target leakage checks, and standardized report generation.

All random operations take an explicit seed for strict determinism.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable, Sequence
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
    roc_curve,
)

from ml.common import df_to_markdown
from ml.labels import LABELS

NHANES_CORE_COLUMNS = {
    "seqn",
    "cycle",
    "age",
    "sex_male",
    "race_eth",
    "income_poverty_ratio",
    "bmi",
    "waist_cm",
    "height_cm",
    "weight_kg",
    "sbp",
    "dbp",
    "pulse",
    "hba1c",
    "fasting_glucose",
    "total_chol",
    "told_diabetes",
    "takes_insulin",
    "takes_diabetes_pills",
    "told_high_bp",
    "takes_bp_meds",
    "family_hx_diabetes",
    "ever_smoked_100",
    "exam_weight_2yr",
    "borderline_diabetes",
}


class LeakageError(ValueError):
    """Raised when forbidden features are provided for a target label."""
    pass


class BootstrapCI(tuple):
    """
    3-tuple (point, low, high) with metadata attributes:
    point, low, high, skipped_count.
    Unpacks cleanly as (point, low, high).
    """
    def __new__(cls, point: float | None, low: float | None, high: float | None, skipped: int = 0):
        return super().__new__(cls, (point, low, high))

    def __init__(self, point: float | None, low: float | None, high: float | None, skipped: int = 0):
        self.point = point
        self.low = low
        self.high = high
        self.skipped_count = skipped
        self.skipped = skipped


def choose_threshold(
    y_val: Sequence[int] | np.ndarray,
    p_val: Sequence[float] | np.ndarray,
    policy: dict[str, Any],
) -> dict[str, Any]:
    """
    Select an operational decision threshold from model predictions.

    CRITICAL CLINICAL SAFETY RULE:
    THIS FUNCTION ONLY EVER RECEIVES VALIDATION ARRAYS.
    IT MUST NEVER BE CALLED ON TEST SET DATA. EVALUATION THRESHOLDS
    MUST BE CHOSEN STRICTLY ON VALIDATION DATA PRIOR TO HELD-OUT TESTING.

    Parameters
    ----------
    y_val : Sequence[int] | np.ndarray
        True binary labels (0 or 1) strictly from the VALIDATION split.
    p_val : Sequence[float] | np.ndarray
        Predicted probabilities strictly from the VALIDATION split.
    policy : dict
        Policy specifying threshold selection logic:
        - {"type": "min_sensitivity", "value": float}
          The HIGHEST threshold achieving sensitivity >= value.
          Ties broken by higher specificity.
          If no threshold reaches the target, returns the threshold with
          the highest sensitivity and sets 'met': False.
        - {"type": "fixed", "value": float}
          Uses the fixed threshold specified in value.
        - {"type": "youden"}
          Maximises Youden's J statistic (sensitivity + specificity - 1).

    Returns
    -------
    dict:
        {
            "threshold": float,
            "policy": dict,
            "met": bool,
            "val_sensitivity": float,
            "val_specificity": float,
        }
    """
    y = np.asarray(y_val, dtype=int)
    p = np.asarray(p_val, dtype=float)

    if len(y) != len(p):
        raise ValueError(f"Mismatched lengths: y_val ({len(y)}) vs p_val ({len(p)})")
    if len(y) == 0:
        raise ValueError("Empty arrays passed to choose_threshold")

    p_type = policy.get("type")
    if not p_type:
        raise ValueError("policy must specify a 'type' key")

    # 1. Fixed Policy
    if p_type == "fixed":
        thresh = float(policy["value"])
        m = metrics_at_threshold(y, p, thresh)
        return {
            "threshold": thresh,
            "policy": policy,
            "met": True,
            "val_sensitivity": m["sensitivity"],
            "val_specificity": m["specificity"],
        }

    unique_classes = np.unique(y)
    if len(unique_classes) < 2:
        thresh = 0.5
        m = metrics_at_threshold(y, p, thresh)
        return {
            "threshold": thresh,
            "policy": policy,
            "met": False,
            "val_sensitivity": m["sensitivity"],
            "val_specificity": m["specificity"],
        }

    fpr, tpr, thresholds = roc_curve(y, p)
    # Filter out non-finite thresholds (e.g. inf at start of sklearn roc_curve)
    valid_mask = np.isfinite(thresholds)
    candidate_thresholds = thresholds[valid_mask]

    # Include bounds [0.0, 1.0] and unique predictions to ensure fine grid
    all_candidates = np.unique(np.concatenate([candidate_thresholds, p, [0.0, 1.0]]))
    all_candidates = all_candidates[(all_candidates >= 0.0) & (all_candidates <= 1.0)]
    all_candidates = np.sort(all_candidates)

    eval_rows = []
    for t in all_candidates:
        m = metrics_at_threshold(y, p, t)
        eval_rows.append({
            "threshold": float(t),
            "sensitivity": m["sensitivity"] if m["sensitivity"] is not None else 0.0,
            "specificity": m["specificity"] if m["specificity"] is not None else 0.0,
            "youden": (m["sensitivity"] or 0.0) + (m["specificity"] or 0.0) - 1.0,
        })

    # 2. Youden Policy
    if p_type == "youden":
        # Maximise Youden J; tie breaker: higher sensitivity, then higher threshold
        best = max(eval_rows, key=lambda r: (r["youden"], r["sensitivity"], r["threshold"]))
        return {
            "threshold": best["threshold"],
            "policy": policy,
            "met": True,
            "val_sensitivity": best["sensitivity"],
            "val_specificity": best["specificity"],
        }

    # 3. Minimum Sensitivity Policy
    if p_type == "min_sensitivity":
        target_sens = float(policy.get("value", 0.80))
        qualifying = [r for r in eval_rows if r["sensitivity"] >= target_sens]

        if qualifying:
            # The HIGHEST threshold whose sensitivity >= target; ties -> higher specificity
            best = max(qualifying, key=lambda r: (r["threshold"], r["specificity"]))
            return {
                "threshold": best["threshold"],
                "policy": policy,
                "met": True,
                "val_sensitivity": best["sensitivity"],
                "val_specificity": best["specificity"],
            }
        else:
            # If no threshold reaches it, return highest sensitivity; ties -> higher threshold
            best = max(eval_rows, key=lambda r: (r["sensitivity"], r["threshold"], r["specificity"]))
            return {
                "threshold": best["threshold"],
                "policy": policy,
                "met": False,
                "val_sensitivity": best["sensitivity"],
                "val_specificity": best["specificity"],
            }

    raise ValueError(f"Unsupported policy type: {p_type}")


def metrics_at_threshold(
    y: Sequence[int] | np.ndarray,
    p: Sequence[float] | np.ndarray,
    t: float,
) -> dict[str, Any]:
    """
    Compute confusion matrix counts and diagnostic metrics at decision threshold t.
    Zero denominators return None rather than crashing or returning fake 0.
    """
    y_arr = np.asarray(y, dtype=int)
    p_arr = np.asarray(p, dtype=float)

    n = len(y_arr)
    if n == 0:
        return {
            "n": 0,
            "prevalence": None,
            "tp": 0,
            "fp": 0,
            "tn": 0,
            "fn": 0,
            "sensitivity": None,
            "specificity": None,
            "ppv": None,
            "npv": None,
            "f1": None,
            "threshold": float(t),
        }

    y_pred = (p_arr >= t).astype(int)

    tp = int(np.sum((y_arr == 1) & (y_pred == 1)))
    fp = int(np.sum((y_arr == 0) & (y_pred == 1)))
    tn = int(np.sum((y_arr == 0) & (y_pred == 0)))
    fn = int(np.sum((y_arr == 1) & (y_pred == 0)))

    n_pos = tp + fn
    n_neg = tn + fp
    n_pred_pos = tp + fp
    n_pred_neg = tn + fn

    prevalence = float(n_pos / n)
    sensitivity = float(tp / n_pos) if n_pos > 0 else None
    specificity = float(tn / n_neg) if n_neg > 0 else None
    ppv = float(tp / n_pred_pos) if n_pred_pos > 0 else None
    npv = float(tn / n_pred_neg) if n_pred_neg > 0 else None

    if ppv is not None and sensitivity is not None and (ppv + sensitivity) > 0:
        f1 = float(2 * ppv * sensitivity / (ppv + sensitivity))
    else:
        f1 = None

    return {
        "n": n,
        "prevalence": prevalence,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "ppv": ppv,
        "npv": npv,
        "f1": f1,
        "threshold": float(t),
    }


def bootstrap_ci(
    y: Sequence[int] | np.ndarray,
    p: Sequence[float] | np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float | None],
    n_boot: int = 1000,
    seed: int = 42,
    stratified: bool = True,
    alpha: float = 0.05,
) -> BootstrapCI:
    """
    Compute bootstrap confidence intervals for an arbitrary evaluation metric.
    Resamples within each label class when stratified=True.
    A resample with only one class is skipped and counted.
    """
    y_arr = np.asarray(y, dtype=int)
    p_arr = np.asarray(p, dtype=float)

    point = metric_fn(y_arr, p_arr)

    rng = np.random.default_rng(seed)
    n = len(y_arr)

    pos_idx = np.where(y_arr == 1)[0]
    neg_idx = np.where(y_arr == 0)[0]

    n_pos = len(pos_idx)
    n_neg = len(neg_idx)

    boot_vals = []
    skipped = 0

    for _ in range(n_boot):
        if stratified:
            if n_pos == 0 or n_neg == 0:
                skipped += 1
                continue
            b_pos = rng.choice(pos_idx, size=n_pos, replace=True)
            b_neg = rng.choice(neg_idx, size=n_neg, replace=True)
            boot_idx = np.concatenate([b_pos, b_neg])
        else:
            boot_idx = rng.choice(n, size=n, replace=True)
            b_y = y_arr[boot_idx]
            if len(np.unique(b_y)) < 2:
                skipped += 1
                continue

        b_y = y_arr[boot_idx]
        b_p = p_arr[boot_idx]

        val = metric_fn(b_y, b_p)
        if val is not None and not math.isnan(val):
            boot_vals.append(float(val))
        else:
            skipped += 1

    if not boot_vals:
        return BootstrapCI(point, None, None, skipped=skipped)

    low = float(np.percentile(boot_vals, (alpha / 2.0) * 100.0))
    high = float(np.percentile(boot_vals, (1.0 - alpha / 2.0) * 100.0))

    return BootstrapCI(point, low, high, skipped=skipped)


def auroc(y: Sequence[int] | np.ndarray, p: Sequence[float] | np.ndarray) -> float | None:
    """Compute AUROC, returning None if only one class is present."""
    y_arr = np.asarray(y, dtype=int)
    p_arr = np.asarray(p, dtype=float)
    if len(np.unique(y_arr)) < 2:
        return None
    return float(roc_auc_score(y_arr, p_arr))


def auprc(y: Sequence[int] | np.ndarray, p: Sequence[float] | np.ndarray) -> float | None:
    """Compute AUPRC (Average Precision), returning None if only one class is present."""
    y_arr = np.asarray(y, dtype=int)
    p_arr = np.asarray(p, dtype=float)
    if len(np.unique(y_arr)) < 2:
        return None
    return float(average_precision_score(y_arr, p_arr))


def calibration(
    y: Sequence[int] | np.ndarray,
    p: Sequence[float] | np.ndarray,
    n_bins: int = 10,
) -> dict[str, Any]:
    """
    Evaluate probability calibration on model predictions.
    Computes:
    - Brier score
    - Calibration-in-the-large (mean(p) - mean(y))
    - Calibration intercept and slope via logistic regression of y on logit(p)
      (with probabilities clipped to [1e-6, 1 - 1e-6])
    - Reliability table across quantile bins
    """
    y_arr = np.asarray(y, dtype=int)
    p_arr = np.asarray(p, dtype=float)

    if len(y_arr) == 0:
        return {
            "brier": None,
            "calibration_in_the_large": None,
            "intercept": None,
            "slope": None,
            "reliability_table": [],
        }

    brier = float(brier_score_loss(y_arr, p_arr))
    cal_large = float(np.mean(p_arr) - np.mean(y_arr))

    # Slope & intercept via logistic regression
    p_clipped = np.clip(p_arr, 1e-6, 1.0 - 1e-6)
    logit_p = np.log(p_clipped / (1.0 - p_clipped)).reshape(-1, 1)

    if len(np.unique(y_arr)) >= 2:
        # C=1e9 gives unpenalized logistic regression across all sklearn versions
        lr = LogisticRegression(C=1e9, solver="lbfgs")
        lr.fit(logit_p, y_arr)
        slope = float(lr.coef_[0][0])
        intercept = float(lr.intercept_[0])
    else:
        slope = None
        intercept = None

    # Quantile reliability table
    reliability_table: list[dict[str, Any]] = []
    try:
        bins, bin_edges = pd.qcut(p_arr, q=n_bins, retbins=True, duplicates="drop")
        df_cal = pd.DataFrame({"y": y_arr, "p": p_arr, "bin": bins})
        for b_name, grp in df_cal.groupby("bin", observed=True):
            reliability_table.append({
                "bin": str(b_name),
                "n": int(len(grp)),
                "mean_p": float(grp["p"].mean()),
                "observed_rate": float(grp["y"].mean()),
            })
    except Exception:
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        for i in range(n_bins):
            low, high = bin_edges[i], bin_edges[i + 1]
            if i == n_bins - 1:
                mask = (p_arr >= low) & (p_arr <= high)
            else:
                mask = (p_arr >= low) & (p_arr < high)
            if np.any(mask):
                reliability_table.append({
                    "bin": f"[{low:.2f}, {high:.2f}]",
                    "n": int(np.sum(mask)),
                    "mean_p": float(np.mean(p_arr[mask])),
                    "observed_rate": float(np.mean(y_arr[mask])),
                })

    return {
        "brier": brier,
        "calibration_in_the_large": cal_large,
        "intercept": intercept,
        "slope": slope,
        "reliability_table": reliability_table,
    }


def subgroup_report(
    df: pd.DataFrame,
    y_col: str,
    p_col: str,
    threshold: float,
    groups: Sequence[str] | None = None,
    min_n: int = 50,
) -> list[dict[str, Any]]:
    """
    Compute subgroup performance breakdowns to audit algorithmic equity and clinical safety.
    Groups with n < min_n or fewer than 10 positive cases return 'too few'.
    """
    if groups is None:
        groups = ["sex_male", "age_band", "race_eth", "cycle"]

    work_df = df.copy()
    if "age_band" in groups and "age_band" not in work_df.columns and "age" in work_df.columns:
        work_df["age_band"] = pd.cut(
            work_df["age"],
            bins=[18, 40, 60, 150],
            labels=["18-39", "40-59", "60+"],
            right=False,
        )

    race_labels = {
        1: "Mexican American",
        2: "Other Hispanic",
        3: "Non-Hispanic White",
        4: "Non-Hispanic Black",
        5: "Other Race / Multi-Racial",
    }

    report_rows: list[dict[str, Any]] = []

    for g_col in groups:
        if g_col not in work_df.columns:
            continue

        for g_val, sub in work_df.groupby(g_col, observed=True):
            clean_sub = sub.dropna(subset=[y_col, p_col])
            n = len(clean_sub)
            y_sub = clean_sub[y_col].to_numpy(dtype=int)
            p_sub = clean_sub[p_col].to_numpy(dtype=float)
            positives = int(np.sum(y_sub == 1))
            prev = float(positives / n) if n > 0 else 0.0

            display_val = str(g_val)
            if g_col == "sex_male":
                display_val = "Male" if int(g_val) == 1 else "Female"
            elif g_col == "race_eth":
                display_val = race_labels.get(int(g_val), f"Code {g_val}")

            row: dict[str, Any] = {
                "group_type": g_col,
                "group_value": display_val,
                "n": n,
                "positives": positives,
                "prevalence": prev,
            }

            if n < min_n or positives < 10:
                row["auroc"] = "too few"
                row["sensitivity"] = "too few"
                row["specificity"] = "too few"
            else:
                row["auroc"] = auroc(y_sub, p_sub)
                m = metrics_at_threshold(y_sub, p_sub, threshold)
                row["sensitivity"] = m["sensitivity"]
                row["specificity"] = m["specificity"]

            report_rows.append(row)

    return report_rows


def check_leakage(label_name: str, features: Sequence[str]) -> None:
    """
    Validate candidate feature list against strict target leakage rules.
    Must be called BEFORE fitting or loading data.
    """
    if label_name not in LABELS:
        raise KeyError(f"Unknown label '{label_name}' not registered in labels.LABELS")

    unknown = [f for f in features if f not in NHANES_CORE_COLUMNS]
    if unknown:
        raise ValueError(f"Feature(s) {unknown} are not recognized columns in nhanes_core")

    forbidden = set(LABELS[label_name].forbidden_features)
    leaked = [f for f in features if f in forbidden]
    if leaked:
        raise LeakageError(
            f"Target leakage detected: features {leaked} are strictly forbidden "
            f"for target label '{label_name}' (defined in ml.labels)."
        )


def write_eval_report(path: Path | str, sections: dict[str, Any]) -> None:
    """
    Write a comprehensive, standardized markdown evaluation report.
    Mandatory sections: 'Config', 'Data', 'Validation', 'Test',
    'Calibration', 'Subgroups', 'Limitations'.
    Any omitted section is written as 'NOT RUN'.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    required_sections = [
        "Config",
        "Data",
        "Validation",
        "Test",
        "Calibration",
        "Subgroups",
        "Limitations",
    ]

    mandatory_limitations = (
        "- **US Survey Population:** Trained and evaluated on US NHANES survey participants; "
        "not directly representative of South Asian or Pakistani diaspora physiology.\n"
        "- **Survey Weights Omitted in Training:** Standard maximum-likelihood estimation was used "
        "without complex survey pseudo-weights to reflect empirical prediction performance.\n"
        "- **NHANES Age Top-Coding:** Participants aged 80+ (or 85+ in early cycles) have capped ages, "
        "which introduces minor attenuation at extreme elderly ages.\n"
        "- **Self-Report Target Inclusion:** Self-reported diabetes diagnoses may omit undiagnosed individuals "
        "or contain recall noise compared to pure biochemical definitions."
    )

    lines = ["# ChronicCare AI — Model Evaluation Report", ""]

    for sec in required_sections:
        lines.append(f"## {sec}")
        content = sections.get(sec)
        if content is None or str(content).strip() == "":
            lines.append("NOT RUN")
        else:
            lines.append(str(content).strip())

        if sec == "Limitations":
            if content and mandatory_limitations not in str(content):
                lines.append("")
                lines.append(mandatory_limitations)
            elif not content:
                lines.append("")
                lines.append(mandatory_limitations)

        lines.append("")

    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
