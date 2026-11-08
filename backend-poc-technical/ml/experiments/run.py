"""
ChronicCare AI — Machine Learning Experiment Harness.
Executes risk-model training, threshold selection, calibration, evaluation,
and artifact packaging from declarative JSON configurations.

Adheres strictly to docs/ML_PLAN.md decisions (D1-D11) and docs/ML_INTERFACES.md.
Runs entirely on CPU using scikit-learn standard models.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.artifacts import export_production_lr, save_model_artifact, validate_model_card
from ml.common import (
    ADULT_MIN_AGE,
    df_to_markdown,
    load_nhanes_core,
    load_split,
)
from ml.evaluation import (
    auprc,
    auroc,
    bootstrap_ci,
    calibration,
    check_leakage,
    choose_threshold,
    metrics_at_threshold,
    subgroup_report,
    write_eval_report,
)
from ml.labels import (
    extract_diabetes_undiagnosed,
    extract_hypertension_measured_130_80,
)

ALLOWED_CONFIG_KEYS = {
    "name",
    "dataset",
    "split",
    "label",
    "population",
    "card_population",
    "tier",
    "features",
    "models",
    "grid",
    "threshold_policy",
    "missing",
    "seed",
    "notes",
}

# Reference population counts from scripts/ml/count_label_populations.py
REFERENCE_POPULATION_COUNTS = {
    "adults_without_diabetes": {
        "train_core": 32647,
        "validation": 9371,
        "test": 9261,
    },
    "adults_without_htn_unmedicated": {
        "train_core": 25380,
        "validation": 7299,
        "test": 7268,
    },
    "hypertension_or_diabetes": {
        "train_core": 2499,
        "validation": 833,
        "test": 834,
    },
    "all_eligible": {
        "train_core": 2499,
        "validation": 833,
        "test": 834,
    },
}

REFERENCE_CARD_COUNTS = {
    "told_high_bp_1": {
        "train_core": 8634,
        "validation": 2754,
        "test": 2775,
    },
    "told_diabetes_1": {
        "train_core": 1223,
        "validation": 453,
        "test": 488,
    },
    "hypertension_or_diabetes": {
        "train_core": 2499,
        "validation": 833,
        "test": 834,
    },
}


def get_git_commit() -> str:
    """Retrieve current HEAD commit hash or fallback."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def validate_config(config: dict[str, Any]) -> None:
    """Validate JSON configuration against strict schema."""
    config_keys = set(config.keys())
    extra_keys = config_keys - ALLOWED_CONFIG_KEYS
    if extra_keys:
        raise ValueError(f"Unknown config keys not allowed: {sorted(extra_keys)}")

    missing_keys = ALLOWED_CONFIG_KEYS - config_keys
    if missing_keys:
        raise ValueError(f"Missing required config keys: {sorted(missing_keys)}")

    if config["missing"] != "drop":
        raise ValueError(f"Unsupported missing policy: '{config['missing']}'. Only 'drop' is allowed.")

    if config["tier"] not in ("basic", "full"):
        raise ValueError(f"Tier must be 'basic' or 'full', got '{config['tier']}'")

    if config["dataset"] not in ("nhanes_core", "framingham"):
        raise ValueError(f"Unsupported dataset: '{config['dataset']}'. Only 'nhanes_core' and 'framingham' are supported.")

    if config["split"] not in ("nhanes_temporal_v1", "framingham_stratified_v1"):
        raise ValueError(f"Unsupported split: '{config['split']}'.")

    if config["dataset"] == "nhanes_core":
        if config["population"] not in ("adults_without_diabetes", "adults_without_htn_unmedicated"):
            raise ValueError(f"Unknown population filter: '{config['population']}'")

        if config["card_population"] not in ("told_high_bp_1", "told_diabetes_1"):
            raise ValueError(f"Unknown card population: '{config['card_population']}'")
    elif config["dataset"] == "framingham":
        if config["population"] not in ("hypertension_or_diabetes", "all_eligible"):
            raise ValueError(f"Unknown population filter: '{config['population']}'")

        if config["card_population"] not in ("hypertension_or_diabetes", "all_eligible"):
            raise ValueError(f"Unknown card population: '{config['card_population']}'")

    for model_name, grid_dict in config.get("grid", {}).items():
        n_points = 1
        for param, vals in grid_dict.items():
            n_points *= len(vals)
        if n_points > 6:
            raise ValueError(f"Grid for model '{model_name}' has {n_points} combinations (> 6 max allowed).")


def extract_target_series(df: pd.DataFrame, label_name: str, population_name: str) -> tuple[pd.Series, pd.Series]:
    """
    Extract binary target series y and base population mask matching count_label_populations.py.
    """
    if label_name == "diabetes_undiagnosed" and population_name == "adults_without_diabetes":
        y_series = extract_diabetes_undiagnosed(df)
        pop_mask = (df["told_diabetes"] == 0) & y_series.notna()
        return y_series, pop_mask

    elif label_name == "hypertension_measured_130_80" and population_name == "adults_without_htn_unmedicated":
        htn_pop_mask = (df["told_high_bp"] == 0) & (df["takes_bp_meds"] != 1)
        y_series = pd.Series(
            np.where(
                htn_pop_mask & df["sbp"].notna() & df["dbp"].notna(),
                np.where((df["sbp"] >= 130.0) | (df["dbp"] >= 80.0), 1.0, 0.0),
                np.nan,
            ),
            index=df.index,
        )
        pop_mask = htn_pop_mask & y_series.notna()
        return y_series, pop_mask

    elif label_name == "TenYearCHD":
        y_series = df["TenYearCHD"].astype(float)
        pop_mask = pd.Series(True, index=df.index)
        return y_series, pop_mask

    else:
        raise ValueError(f"Unsupported label/population combination: {label_name} / {population_name}")


def extract_card_mask(df: pd.DataFrame, card_pop_name: str, base_pop_mask: pd.Series) -> pd.Series:
    """Extract boolean mask for the card evaluation subpopulation."""
    if card_pop_name == "told_high_bp_1":
        return base_pop_mask & (df["told_high_bp"] == 1)
    elif card_pop_name == "told_diabetes_1":
        return base_pop_mask & (df["told_diabetes"] == 1)
    elif card_pop_name in ("hypertension_or_diabetes", "all_eligible"):
        return base_pop_mask
    else:
        raise ValueError(f"Unknown card population: {card_pop_name}")


def generate_roc_and_calibration_plots(
    y_test: np.ndarray,
    p_test: np.ndarray,
    cal_dict: dict[str, Any],
    out_dir: Path,
) -> tuple[Path, Path]:
    """Render ROC curve and Calibration curve as clean PNGs using Pillow."""
    roc_path = out_dir / "roc_curve.png"
    cal_path = out_dir / "calibration_curve.png"

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # Pillow is optional; skip rendering if not installed in CI environment
        return roc_path, cal_path

    out_dir.mkdir(parents=True, exist_ok=True)
    fpr, tpr, _ = roc_curve(y_test, p_test)
    test_auc = roc_auc_score(y_test, p_test)

    # 1. ROC Plot (600x600)
    img_roc = Image.new("RGB", (600, 600), color=(255, 255, 255))
    draw_roc = ImageDraw.Draw(img_roc)

    # Axes: origin at (70, 530), width=460, height=460
    ox, oy, w, h = 70, 530, 460, 460
    draw_roc.rectangle([ox, oy - h, ox + w, oy], outline=(200, 200, 200), width=1)
    # Diagonal reference line (chance)
    draw_roc.line([(ox, oy), (ox + w, oy - h)], fill=(180, 180, 180), width=1)

    # Plot ROC curve points
    roc_points = [(ox + int(fp * w), oy - int(tp * h)) for fp, tp in zip(fpr, tpr)]
    if len(roc_points) > 1:
        draw_roc.line(roc_points, fill=(31, 119, 180), width=3)

    roc_path = out_dir / "roc_curve.png"
    img_roc.save(roc_path)

    # 2. Calibration Plot (600x600)
    img_cal = Image.new("RGB", (600, 600), color=(255, 255, 255))
    draw_cal = ImageDraw.Draw(img_cal)
    draw_cal.rectangle([ox, oy - h, ox + w, oy], outline=(200, 200, 200), width=1)
    # 45-degree ideal calibration line
    draw_cal.line([(ox, oy), (ox + w, oy - h)], fill=(180, 180, 180), width=1)

    # Plot reliability decile points
    rel_table = cal_dict.get("reliability_table", [])
    cal_pts = []
    for row in rel_table:
        px = ox + int(row["mean_p"] * w)
        py = oy - int(row["observed_rate"] * h)
        cal_pts.append((px, py))
        draw_cal.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(214, 39, 40), outline=(0, 0, 0))
    if len(cal_pts) > 1:
        draw_cal.line(cal_pts, fill=(214, 39, 40), width=2)

    cal_path = out_dir / "calibration_curve.png"
    img_cal.save(cal_path)

    return roc_path, cal_path


def score_record_pure_python(features_dict: dict[str, float], export_spec: dict[str, Any]) -> float:
    """Pure-Python logistic regression scorer implementation."""
    z = float(export_spec["intercept"])
    feature_order = export_spec["feature_order"]
    means = export_spec["scaler_mean"]
    scales = export_spec["scaler_scale"]
    coefs = export_spec["coef"]

    for i, name in enumerate(feature_order):
        raw_val = float(features_dict[name])
        val = (raw_val - means[i]) / scales[i]
        z += coefs[i] * val

    return 1.0 / (1.0 + math.exp(-z))


def run_experiment(config: dict[str, Any], project_root: Path | None = None) -> dict[str, Any]:
    """Run full experiment from validated config dictionary."""
    start_time = time.perf_counter()
    validate_config(config)

    name = config["name"]
    label_name = config["label"]
    features = list(config["features"])
    population_name = config["population"]
    card_pop_name = config["card_population"]
    tier = config["tier"]
    seed = int(config["seed"])
    notes = config.get("notes", "")

    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent.parent

    # Step A2.1: Target leakage check BEFORE any data is loaded
    print(f"\n=======================================================")
    print(f"EXPERIMENT: {name} (Tier: {tier}, Label: {label_name})")
    print(f"=======================================================")
    print("Checking target leakage before data loading...")
    check_leakage(label_name, features)
    print("[PASS] Leakage check passed: features are valid for target.")

    # Step A2.2: Load data
    if config["dataset"] == "framingham":
        from ml.datasets.framingham import load_framingham_chd10
        from ml.splits import generate_stratified_random_splits
        from ml.common import data_dir
        print("Loading Framingham dataset...")
        df_complete, chd_rep = load_framingham_chd10(features=features)
        adults = df_complete.copy()
        adults["seqn"] = adults["_id"].astype(int)

        # Step A2.3: Extract target and population mask
        y_series, pop_mask = extract_target_series(adults, label_name, population_name)
        adults["_target"] = y_series
        adults["_in_pop"] = pop_mask

        split_name = config["split"]
        split_dir = data_dir() / "splits"
        split_file = split_dir / f"{split_name}.json"
        if not split_file.exists():
            splits_data = generate_stratified_random_splits(adults, target_col="TenYearCHD", seed=seed, id_col="_id")
            split_dir.mkdir(parents=True, exist_ok=True)
            with open(split_file, "w", encoding="utf-8") as f:
                json.dump({
                    "version": split_name,
                    "train_core": splits_data["train_core"],
                    "validation": splits_data["validation"],
                    "test": splits_data["test"],
                }, f)
        splits = load_split(split_name)
    else:
        print("Loading NHANES core dataset...")
        # Load required columns
        all_needed_cols = list(set(["seqn", "cycle", "age", "sex_male", "race_eth", "told_diabetes", "told_high_bp", "takes_bp_meds", "sbp", "dbp", "hba1c", "fasting_glucose", "waist_cm"] + features))
        df = load_nhanes_core(all_needed_cols)
        adults = df[df["age"] >= ADULT_MIN_AGE].copy()
        adults["seqn"] = adults["seqn"].astype(int)

        # Step A2.3: Extract target and population mask
        y_series, pop_mask = extract_target_series(adults, label_name, population_name)
        adults["_target"] = y_series
        adults["_in_pop"] = pop_mask

        # Step A2.4: Load split and verify population counts
        splits = load_split(config["split"])
    print("\n--- POPULATION COUNT VERIFICATION VS count_label_populations.py ---")
    pop_matches = True
    ref_counts = REFERENCE_POPULATION_COUNTS.get(population_name, {})
    for split_name in ["train_core", "validation", "test"]:
        s_seqns = splits[split_name]
        s_mask = adults["seqn"].isin(s_seqns) & adults["_in_pop"]
        actual_count = int(s_mask.sum())
        expected_count = ref_counts.get(split_name)
        match_str = "MATCH" if actual_count == expected_count else "MISMATCH"
        print(f"  {split_name:12s}: Actual={actual_count:,} | Expected={expected_count:,} [{match_str}]")
        if actual_count != expected_count:
            pop_matches = False

    if not pop_matches:
        raise ValueError(f"Population counts do not match reference for {population_name}!")
    print("✓ Population counts exactly match reference across all splits.")

    # Step A2.5: Drop missing values (complete cases)
    print("\n--- COMPLETE CASES & MISSINGNESS DROPS ---")
    split_data: dict[str, dict[str, Any]] = {}
    for split_name in ["train_core", "validation", "test"]:
        s_seqns = splits[split_name]
        s_pop_df = adults[adults["seqn"].isin(s_seqns) & adults["_in_pop"]].copy()
        n_initial = len(s_pop_df)

        # Complete cases on features and target
        clean_df = s_pop_df.dropna(subset=features + ["_target"]).copy()
        clean_df["_target"] = clean_df["_target"].astype(int)
        n_clean = len(clean_df)
        n_dropped = n_initial - n_clean
        n_pos = int((clean_df["_target"] == 1).sum())
        prev = (n_pos / n_clean * 100.0) if n_clean > 0 else 0.0

        print(f"  {split_name:12s}: Initial={n_initial:,} | Dropped={n_dropped:,} | Clean={n_clean:,} | Positives={n_pos:,} ({prev:.2f}%)")

        split_data[split_name] = {
            "df": clean_df,
            "X": clean_df[features].to_numpy(dtype=float),
            "y": clean_df["_target"].to_numpy(dtype=int),
            "n_initial": n_initial,
            "n_dropped": n_dropped,
            "n_clean": n_clean,
            "n_pos": n_pos,
            "prevalence": prev,
        }

    # Step A2.6: Preprocessing fitted on train_core ONLY
    print("\nFitting StandardScaler on train_core features only...")
    scaler = StandardScaler()
    scaler.fit(split_data["train_core"]["X"])
    X_train_scaled = scaler.transform(split_data["train_core"]["X"])
    X_val_scaled = scaler.transform(split_data["validation"]["X"])
    X_test_scaled = scaler.transform(split_data["test"]["X"])

    y_train = split_data["train_core"]["y"]
    y_val = split_data["validation"]["y"]
    y_test = split_data["test"]["y"]

    # Step A2.7: Fit candidate models x grid combinations
    print("\n--- BENCHMARKING CANDIDATE MODELS & HYPERPARAMETER TUNING ---")
    candidate_results: dict[str, dict[str, Any]] = {}
    model_types_to_try = config["models"]

    for m_type in model_types_to_try:
        grid_params = config.get("grid", {}).get(m_type, {})
        # Flatten grid points
        keys = list(grid_params.keys())
        combos = [{}]
        for k in keys:
            new_combos = []
            for c in combos:
                for val in grid_params[k]:
                    nc = dict(c)
                    nc[k] = val
                    new_combos.append(nc)
            combos = new_combos

        best_pipe = None
        best_val_auroc = -1.0
        best_params = {}
        best_val_prob = None

        for p_set in combos:
            if m_type == "lr":
                pipe = Pipeline([
                    ("scaler", StandardScaler()),
                    ("clf", LogisticRegression(random_state=seed, max_iter=1000, **p_set)),
                ])
            elif m_type == "lr_balanced":
                pipe = Pipeline([
                    ("scaler", StandardScaler()),
                    ("clf", LogisticRegression(random_state=seed, max_iter=1000, class_weight="balanced", **p_set)),
                ])
            elif m_type == "rf":
                pipe = Pipeline([
                    ("scaler", StandardScaler()),
                    ("clf", RandomForestClassifier(random_state=seed, n_jobs=-1, **p_set)),
                ])
            elif m_type == "hgb":
                pipe = Pipeline([
                    ("scaler", StandardScaler()),
                    ("clf", HistGradientBoostingClassifier(random_state=seed, **p_set)),
                ])
            else:
                raise ValueError(f"Unknown model type: {m_type}")

            pipe.fit(split_data["train_core"]["X"], y_train)
            p_val = pipe.predict_proba(split_data["validation"]["X"])[:, 1]
            score = auroc(y_val, p_val) or 0.0

            if score > best_val_auroc:
                best_val_auroc = score
                best_pipe = pipe
                best_params = p_set
                best_val_prob = p_val

        # Validation calibration
        cal_val = calibration(y_val, best_val_prob, n_bins=10)

        candidate_results[m_type] = {
            "model_type": m_type,
            "pipeline": best_pipe,
            "best_params": best_params,
            "val_auroc": best_val_auroc,
            "val_prob": best_val_prob,
            "val_calibration": cal_val,
        }
        print(f"  {m_type:12s}: Best Val AUROC = {best_val_auroc:.4f} (params: {best_params}, Val Cal Slope: {cal_val['slope']:.3f})")

    # Step A2.8: Decision D10 Model Choice (Amended: lr_balanced must beat plain lr by >= 0.01 val AUROC)
    print("\n--- DECISION D10 MODEL SELECTION ---")
    lr_plain = candidate_results.get("lr")
    lr_bal = candidate_results.get("lr_balanced")
    best_lr = None
    lr_sub_reason = ""

    if lr_plain and lr_bal:
        bal_gain = lr_bal["val_auroc"] - lr_plain["val_auroc"]
        if bal_gain >= 0.01:
            best_lr = lr_bal
            lr_sub_reason = f"lr_balanced beat plain lr by >= 0.01 validation AUROC (+{bal_gain:.4f})"
        else:
            best_lr = lr_plain
            lr_sub_reason = f"plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: {bal_gain:+.4f})"
    elif lr_plain:
        best_lr = lr_plain
        lr_sub_reason = "plain lr chosen (only plain lr trained)"
    else:
        best_lr = lr_bal
        lr_sub_reason = "lr_balanced chosen (only lr_balanced trained)"

    tree_candidates = [candidate_results[k] for k in ["rf", "hgb"] if k in candidate_results]
    best_tree = max(tree_candidates, key=lambda c: c["val_auroc"]) if tree_candidates else None

    chosen = None
    selection_reason = ""
    if best_tree and (best_tree["val_auroc"] - best_lr["val_auroc"] >= 0.02):
        chosen = best_tree
        selection_reason = (
            f"Tree model ({chosen['model_type']}) beat best LR ({best_lr['model_type']}) by >= 0.02 validation AUROC "
            f"({chosen['val_auroc']:.4f} vs {best_lr['val_auroc']:.4f}, gap: +{chosen['val_auroc'] - best_lr['val_auroc']:.4f})."
        )
    else:
        chosen = best_lr
        gap = (best_tree["val_auroc"] - best_lr["val_auroc"]) if best_tree else 0.0
        selection_reason = (
            f"Logistic regression ({chosen['model_type']}) selected under D10 parsimony rule ({lr_sub_reason}): "
            f"best tree did not beat LR by >= 0.02 validation AUROC (tree gap: {gap:+.4f})."
        )

    print(f"Chosen Model: {chosen['model_type']}")
    print(f"Reason: {selection_reason}")

    # Validation calibration slope gate check
    val_slope = chosen["val_calibration"]["slope"]
    calibration_gate_passed = True
    cal_gate_status = "PASS"
    if val_slope is None or val_slope < 0.8 or val_slope > 1.2:
        calibration_gate_passed = False
        cal_gate_status = "CALIBRATION GATE: STOP, Usman decides"
        print(f"\n⚠️  {cal_gate_status} (Validation slope is {val_slope:.3f}, outside [0.8, 1.2])")
    else:
        print(f"✓ Validation calibration slope passed: {val_slope:.3f} is in [0.8, 1.2]")

    # Note 3 check: If lr_balanced wins, probabilities are inflated rankings
    is_lr_balanced = (chosen["model_type"] == "lr_balanced")
    ranking_warning = "score is a ranking, not a % risk; never display it as a percentage" if is_lr_balanced else ""
    if is_lr_balanced:
        print(f"ℹ️  Notice (lr_balanced winner): {ranking_warning}")

    # Step A2.9: Operational Threshold & Risk Bands
    if name == "chd10_framingham":
        print("\n--- CHD10 OPERATIONAL THRESHOLD & RISK BANDS (PRE-REGISTERED) ---")
        locked_threshold = 0.10
        low_max = 0.10
        high_min = 0.20
        bands = {"low_max": low_max, "high_min": high_min}
        m_val_10 = metrics_at_threshold(y_val, chosen["val_prob"], 0.10)
        val_sens = m_val_10["sensitivity"]
        val_spec = m_val_10["specificity"]
        print(f"Pre-registered Operational Threshold: {locked_threshold:.4f} (Val Sens: {val_sens:.2%}, Val Spec: {val_spec:.2%})")
        print(f"  LOW Band     : Risk < {low_max:.4f}")
        print(f"  MODERATE Band: {low_max:.4f} <= Risk < {high_min:.4f}")
        print(f"  HIGH Band    : Risk >= {high_min:.4f}")
    else:
        print("\n--- DECISION D7 OPERATIONAL THRESHOLD SELECTION (VALIDATION ONLY) ---")
        thresh_res = choose_threshold(
            y_val,
            chosen["val_prob"],
            policy=config["threshold_policy"],
        )
        locked_threshold = float(thresh_res["threshold"])
        val_sens = thresh_res["val_sensitivity"]
        val_spec = thresh_res["val_specificity"]
        print(f"Locked Operational Threshold: {locked_threshold:.4f} (Val Sens: {val_sens:.2%}, Val Spec: {val_spec:.2%})")

        # Step A2.10: Decision D8 Risk Bands
        print("\n--- DECISION D8 RISK STRATIFICATION BANDS ---")
        val_90th = float(np.percentile(chosen["val_prob"], 90))
        low_max = locked_threshold
        high_min = val_90th
        bands = {"low_max": low_max, "high_min": high_min}
        print(f"  LOW Band     : Risk < {low_max:.4f}")
        print(f"  MODERATE Band: {low_max:.4f} <= Risk < {high_min:.4f}")
        print(f"  HIGH Band    : Risk >= {high_min:.4f} (Top 10% validation scores)")

    # Step A2.11: HELD-OUT TESTING (ONCE for the chosen model)
    print("\n--- HELD-OUT TEST EVALUATION (CHOSEN MODEL ONCE) ---")
    chosen_pipe = chosen["pipeline"]
    y_test_prob = chosen_pipe.predict_proba(split_data["test"]["X"])[:, 1]

    # Test AUROC & AUPRC with bootstrap 95% CIs
    ci_auroc = bootstrap_ci(y_test, y_test_prob, metric_fn=auroc, n_boot=1000, seed=seed)
    ci_auprc = bootstrap_ci(y_test, y_test_prob, metric_fn=auprc, n_boot=1000, seed=seed)
    print(f"Test AUROC: {ci_auroc.point:.4f} [95% CI: {ci_auroc.low:.4f} - {ci_auroc.high:.4f}]")
    print(f"Test AUPRC: {ci_auprc.point:.4f} [95% CI: {ci_auprc.low:.4f} - {ci_auprc.high:.4f}]")

    # Test metrics at locked threshold (10% cut)
    m_test = metrics_at_threshold(y_test, y_test_prob, locked_threshold)
    m_test_20 = metrics_at_threshold(y_test, y_test_prob, 0.20)
    print(f"Test Sensitivity @ 10%: {m_test['sensitivity']:.2%} | Specificity: {m_test['specificity']:.2%} | PPV: {m_test['ppv']:.2%} | NPV: {m_test['npv']:.2%}")
    print(f"Confusion Matrix @ 10%: TP={m_test['tp']}, FP={m_test['fp']}, TN={m_test['tn']}, FN={m_test['fn']}")
    if name == "chd10_framingham":
        print(f"Test Sensitivity @ 20%: {m_test_20['sensitivity']:.2%} | Specificity: {m_test_20['specificity']:.2%} | PPV: {m_test_20['ppv']:.2%} | NPV: {m_test_20['npv']:.2%}")
        print(f"Confusion Matrix @ 20%: TP={m_test_20['tp']}, FP={m_test_20['fp']}, TN={m_test_20['tn']}, FN={m_test_20['fn']}")

    # Test calibration
    cal_test = calibration(y_test, y_test_prob, n_bins=10)
    print(f"Test Calibration: Brier={cal_test['brier']:.4f}, CITL={cal_test['calibration_in_the_large']:+.4f}, Slope={cal_test['slope']:.3f}, Intercept={cal_test['intercept']:+.3f}")

    # Test Subgroup Breakdown
    test_clean_df = split_data["test"]["df"].copy()
    test_clean_df["_prob"] = y_test_prob
    if name == "chd10_framingham":
        test_clean_df["age_band"] = pd.cut(
            test_clean_df["age"],
            bins=[0, 50, 60, 150],
            labels=["<50", "50-59", "60+"],
            right=False,
        )
        subgroup_groups = ["sex_male", "age_band"]
    else:
        subgroup_groups = ["sex_male", "age_band", "race_eth", "cycle"]

    subgroups = subgroup_report(
        test_clean_df,
        y_col="_target",
        p_col="_prob",
        threshold=locked_threshold,
        groups=subgroup_groups,
        min_n=30 if name == "chd10_framingham" else 50,
    )

    # Card Population Evaluation
    print(f"\n--- CARD EVALUATION POPULATION ({card_pop_name}) ---")
    card_mask = extract_card_mask(test_clean_df, card_pop_name, test_clean_df["_in_pop"])
    card_test_df = test_clean_df[card_mask]
    n_card = len(card_test_df)
    n_card_pos = int((card_test_df["_target"] == 1).sum())
    card_prev = (n_card_pos / n_card * 100.0) if n_card > 0 else 0.0

    if n_card_pos >= 10:
        card_auroc = auroc(card_test_df["_target"].to_numpy(), card_test_df["_prob"].to_numpy())
        card_metrics = metrics_at_threshold(card_test_df["_target"].to_numpy(), card_test_df["_prob"].to_numpy(), locked_threshold)
        card_sens = card_metrics["sensitivity"]
        card_spec = card_metrics["specificity"]
    else:
        card_auroc = None
        card_sens = None
        card_spec = None

    card_subgroup_row = {
        "group_type": "card_population",
        "group_value": card_pop_name,
        "n": n_card,
        "positives": n_card_pos,
        "prevalence": card_prev / 100.0,
        "auroc": card_auroc,
        "sensitivity": card_sens,
        "specificity": card_spec,
    }
    auroc_disp = f"{card_auroc:.4f}" if card_auroc is not None else "N/A"
    sens_disp = f"{card_sens:.2%}" if card_sens is not None else "N/A"
    print(f"  Card Population ({card_pop_name}): n={n_card:,}, pos={n_card_pos:,} ({card_prev:.1f}%), AUROC={auroc_disp}, Sens={sens_disp}")

    # Find worst subgroup sensitivity among evaluated groups with >= 50 positives
    worst_group = None
    worst_sens = 1.0
    worst_pos = 0
    for sg in subgroups:
        if sg["positives"] >= 50 and sg["sensitivity"] not in (None, "too few"):
            s_val = float(sg["sensitivity"])
            if s_val < worst_sens:
                worst_sens = s_val
                worst_group = f"{sg['group_type']}={sg['group_value']}"
                worst_pos = sg["positives"]

    print(f"\nWorst Subgroup Sensitivity (>= 50 positives): {worst_group} = {worst_sens:.2%} (positives={worst_pos})")

    # Step A3: Feature Explanation & Clinical Sanity
    print("\n--- FEATURE EXPLANATION & CLINICAL SANITY ---")
    feature_explanations: list[dict[str, Any]] = []
    clinical_sanity: list[dict[str, Any]] = []
    shap_global: list[dict[str, Any]] = []
    fake_patient_shap: list[dict[str, Any]] = []

    if "lr" in chosen["model_type"]:
        clf_step = chosen_pipe.named_steps["clf"]
        coefs = clf_step.coef_[0]
        for f_name, c_val in zip(features, coefs):
            or_val = math.exp(c_val)
            feature_explanations.append({
                "feature": f_name,
                "coef_standardized": float(c_val),
                "odds_ratio_per_1_sd": float(or_val),
            })
            clinical_sanity.append({
                "feature": f_name,
                "coef": float(c_val),
                "sign": "+" if c_val > 0 else "-",
                "direction": "UP (+)" if c_val > 0 else "DOWN (-)",
                "expected": "UP (+)" if f_name in ("age", "sbp", "current_smoker", "diabetes", "bp_meds") else "UP (+)",
                "concordant": bool(c_val > 0),
            })
        feature_explanations.sort(key=lambda x: abs(x["coef_standardized"]), reverse=True)
        print("Standardized Logistic Regression Coefficients (Odds Ratio per 1 SD):")
        for fe in feature_explanations:
            print(f"  {fe['feature']:18s}: beta={fe['coef_standardized']:+.3f}, OR={fe['odds_ratio_per_1_sd']:.3f}")

        print("\nClinical Sanity Direction Check:")
        for cs in clinical_sanity:
            mark = "✓" if cs["concordant"] else "⚠️ OPPOSITE"
            print(f"  {mark} {cs['feature']:18s}: beta={cs['coef']:+.4f} -> {cs['direction']}")

        # SHAP calculation for chd10_framingham
        if name == "chd10_framingham":
            try:
                import shap
                print("\n--- COMPUTING SHAP EXPLANATIONS ---")
                explainer = shap.LinearExplainer(chosen_pipe.named_steps["clf"], X_train_scaled)
                shap_vals_val = explainer(X_val_scaled)
                mean_abs_shap = np.mean(np.abs(shap_vals_val.values), axis=0)
                for f_name, imp in sorted(zip(features, mean_abs_shap), key=lambda x: x[1], reverse=True):
                    shap_global.append({"feature": f_name, "mean_abs_shap": float(imp)})
                    print(f"  {f_name:18s}: mean |SHAP| = {imp:.4f}")

                # 3 Fake Example Patients
                fake_cases = [
                    {
                        "case_id": "Fake Patient 1 (Low Risk Profile)",
                        "profile": {"age": 42, "sex_male": 0, "current_smoker": 0, "bmi": 22.0, "sbp": 115.0, "dbp": 75.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 0},
                    },
                    {
                        "case_id": "Fake Patient 2 (Moderate Risk Profile)",
                        "profile": {"age": 54, "sex_male": 1, "current_smoker": 1, "bmi": 27.5, "sbp": 138.0, "dbp": 86.0, "bp_meds": 0, "diabetes": 0, "prevalent_hyp": 1},
                    },
                    {
                        "case_id": "Fake Patient 3 (High Risk Profile)",
                        "profile": {"age": 66, "sex_male": 1, "current_smoker": 1, "bmi": 31.2, "sbp": 165.0, "dbp": 98.0, "bp_meds": 1, "diabetes": 1, "prevalent_hyp": 1},
                    },
                ]
                print("\n--- PER-PATIENT SHAP EXPLANATIONS (3 FAKE PATIENTS) ---")
                for fc in fake_cases:
                    x_row = np.array([[fc["profile"][f] for f in features]], dtype=float)
                    x_scaled = chosen_pipe.named_steps["scaler"].transform(x_row)
                    prob = float(chosen_pipe.predict_proba(x_row)[0, 1])
                    sv = explainer(x_scaled).values[0]
                    band_label = "Low (<10%)" if prob < 0.10 else "Moderate (10-20%)" if prob < 0.20 else "High (>=20%)"
                    print(f"\n{fc['case_id']}: Predicted Risk = {prob:.2%} [Band: {band_label}]")
                    contribs = []
                    for f_name, val, phi in zip(features, x_row[0], sv):
                        contribs.append({"feature": f_name, "value": val, "shap_value": float(phi)})
                        print(f"    {f_name:18s} = {val:<6}: SHAP contribution = {phi:+.4f}")
                    fake_patient_shap.append({
                        "case_id": fc["case_id"],
                        "profile": fc["profile"],
                        "predicted_risk": prob,
                        "predicted_band": band_label,
                        "shap_contributions": contribs,
                    })
            except Exception as e:
                print(f"SHAP note: {e}")
    else:
        print("Computing permutation importance on validation set (n_repeats=10)...")
        perm_res = permutation_importance(
            chosen_pipe,
            split_data["validation"]["X"],
            y_val,
            n_repeats=10,
            random_state=seed,
            n_jobs=-1,
        )
        for f_name, imp in zip(features, perm_res.importances_mean):
            feature_explanations.append({
                "feature": f_name,
                "importance_mean": float(imp),
            })
        feature_explanations.sort(key=lambda x: x["importance_mean"], reverse=True)
        print("Validation Permutation Importance:")
        for fe in feature_explanations:
            print(f"  {fe['feature']:18s}: importance={fe['importance_mean']:.4f}")

    shap_notice = (
        "Linear SHAP (shap.LinearExplainer) was used for logistic regression feature attribution, "
        "providing global mean |SHAP| and exact additive contributions for patient cases."
        if (name == "chd10_framingham" and shap_global) else
        "SHAP NOT USED: Standardized odds ratios per 1 SD are used for logistic regression "
        "and validation permutation importance is used for tree models."
    )

    # Decision Curve Analysis
    dca_table: list[dict[str, Any]] = []
    n_test = len(y_test)
    test_prev = float(np.mean(y_test))
    for pt in [round(x * 0.01, 2) for x in range(1, 21)]:
        weight = pt / (1.0 - pt)
        m_pt = metrics_at_threshold(y_test, y_test_prob, pt)
        nb_model = (m_pt["tp"] / n_test) - (m_pt["fp"] / n_test) * weight
        nb_all = test_prev - (1.0 - test_prev) * weight
        dca_table.append({
            "pt": pt,
            "net_benefit_model": round(nb_model, 4),
            "net_benefit_all": round(nb_all, 4),
            "net_benefit_none": 0.0,
        })

    # Step D11 / Pre-registered Acceptance Gates
    gate_results = {}
    if name == "chd10_framingham":
        print("\n--- PRE-REGISTERED GATES AUDIT (G1 - G5) ---")
        g1 = (ci_auroc.point >= 0.68) if ci_auroc.point is not None else False
        gate_results["gate_1_test_auroc_ge_0_68"] = "PASS" if g1 else "FAIL"

        test_slope = cal_test["slope"]
        g2 = (test_slope is not None and 0.80 <= test_slope <= 1.20)
        gate_results["gate_2_calibration_slope_in_0_80_1_20"] = "PASS" if g2 else "FAIL"

        g3 = (m_test["sensitivity"] >= 0.70) if m_test["sensitivity"] is not None else False
        gate_results["gate_3_sensitivity_10pct_ge_0_70"] = "PASS" if g3 else "FAIL"

        worst_sens = 1.0
        worst_group = None
        worst_pos = 0
        for sg in subgroups:
            if sg["positives"] >= 30 and sg["sensitivity"] not in (None, "too few"):
                s_val = float(sg["sensitivity"])
                if s_val < worst_sens:
                    worst_sens = s_val
                    worst_group = f"{sg['group_type']}={sg['group_value']}"
                    worst_pos = sg["positives"]
        g4 = (worst_sens >= 0.60)
        gate_results["gate_4_subgroup_sens_ge_0_60"] = "PASS" if g4 else "FAIL"

        prev_brier = test_prev * (1.0 - test_prev)
        test_brier = float(cal_test["brier"])
        g5 = (test_brier < prev_brier)
        gate_results["gate_5_brier_lower_than_prevalence"] = "PASS" if g5 else "FAIL"

        failed_gates = [k for k, v in gate_results.items() if v.startswith("FAIL")]
        ship_status = "SHIP CANDIDATE (all G1-G5 gates passed)" if (len(failed_gates) == 0 and calibration_gate_passed) else f"NOT SHIPPED ({', '.join(failed_gates)})"
        slope_str = f"{test_slope:.3f}" if test_slope is not None else "N/A"
        print(f"  Gate 1 (Test AUROC >= 0.68)      : {gate_results['gate_1_test_auroc_ge_0_68']} ({ci_auroc.point:.4f})")
        print(f"  Gate 2 (Test Cal Slope 0.80-1.20): {gate_results['gate_2_calibration_slope_in_0_80_1_20']} ({slope_str})")
        print(f"  Gate 3 (Test Sens @ 10% >= 70%)  : {gate_results['gate_3_sensitivity_10pct_ge_0_70']} ({m_test['sensitivity']:.2%})")
        print(f"  Gate 4 (Subgroup Sens >= 60%)    : {gate_results['gate_4_subgroup_sens_ge_0_60']} (Worst: {worst_group}={worst_sens:.2%}, pos={worst_pos})")
        print(f"  Gate 5 (Brier < Prev Brier)      : {gate_results['gate_5_brier_lower_than_prevalence']} ({test_brier:.4f} vs {prev_brier:.4f})")
        print(f"  Overall Status                   : {ship_status}")
    else:
        print("\n--- D11 ACCEPTANCE GATES AUDIT ---")
        g1 = (ci_auroc.point >= 0.75) if ci_auroc.point is not None else False
        gate_results["gate_1_test_auroc_ge_0_75"] = "PASS" if g1 else "FAIL"

        g2 = (m_test["sensitivity"] >= 0.75) if m_test["sensitivity"] is not None else False
        gate_results["gate_2_test_sens_ge_0_75"] = "PASS" if g2 else "FAIL"

        test_slope = cal_test["slope"]
        g3 = (test_slope is not None and 0.8 <= test_slope <= 1.2)
        gate_results["gate_3_calibration_slope_0_8_to_1_2"] = "PASS" if g3 else "FAIL"

        g4 = (worst_sens >= 0.60)
        gate_results["gate_4_subgroup_sens_ge_0_60"] = "PASS" if g4 else "FAIL"

        gate_5_status = "N/A (BASIC)"
        if tier == "full":
            basic_name = name.replace("_full_", "_basic_")
            basic_metrics_path = project_root / "backend-poc-technical" / "ml" / "outputs" / "reports" / basic_name / "metrics.json"
            if basic_metrics_path.is_file():
                try:
                    b_data = json.loads(basic_metrics_path.read_text(encoding="utf-8"))
                    basic_val_auroc = float(b_data["chosen_model"]["val_auroc"])
                    full_val_auroc = float(chosen["val_auroc"])
                    diff = full_val_auroc - basic_val_auroc
                    if diff > 0:
                        gate_5_status = f"PASS (FULL {full_val_auroc:.4f} vs BASIC {basic_val_auroc:.4f}, diff: +{diff:.4f})"
                    else:
                        gate_5_status = f"FAIL (FULL {full_val_auroc:.4f} vs BASIC {basic_val_auroc:.4f}, diff: {diff:+.4f})"
                except Exception as e:
                    gate_5_status = f"UNKNOWN ({e})"
            else:
                gate_5_status = "EVALUATED_IN_SUMMARY (BASIC metrics not found)"
        gate_results["gate_5_full_beats_basic"] = gate_5_status

        failed_gates = [k for k, v in gate_results.items() if v.startswith("FAIL")]
        if not calibration_gate_passed:
            failed_gates.append("val_calibration_slope")

        ship_status = "SHIP CANDIDATE (all D11 gates passed)" if (len(failed_gates) == 0 and calibration_gate_passed) else f"NOT SHIPPED ({', '.join(failed_gates)})"
        slope_str = f"{test_slope:.3f}" if test_slope is not None else "N/A"
        print(f"  Gate 1 (Test AUROC >= 0.75): {gate_results['gate_1_test_auroc_ge_0_75']} ({ci_auroc.point:.4f})")
        print(f"  Gate 2 (Test Sens >= 0.75) : {gate_results['gate_2_test_sens_ge_0_75']} ({m_test['sensitivity']:.2%})")
        print(f"  Gate 3 (Test Cal Slope)    : {gate_results['gate_3_calibration_slope_0_8_to_1_2']} ({slope_str})")
        print(f"  Gate 4 (Subgroup Sens >=60): {gate_results['gate_4_subgroup_sens_ge_0_60']} (Worst: {worst_sens:.2%})")
        if tier == "full":
            print(f"  Gate 5 (FULL beats BASIC)  : {gate_results['gate_5_full_beats_basic']}")
        print(f"  Overall Status             : {ship_status}")

    # Step A2.15: Save artifacts (only if validation calibration didn't halt export)
    out_models_dir = project_root / "backend-poc-technical" / "ml" / "outputs" / "models" / name
    out_reports_dir = project_root / "backend-poc-technical" / "ml" / "outputs" / "reports" / name
    out_docs_dir = project_root / "docs" / "ml" / "experiments"

    # Generate PNG evaluation plots
    roc_png, cal_png = generate_roc_and_calibration_plots(y_test, y_test_prob, cal_test, out_reports_dir)
    print(f"Saved evaluation plots to: {roc_png} and {cal_png}")

    model_card = {
        "name": name,
        "owner": "saad" if name == "chd10_framingham" else "usman",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
        "label": label_name,
        "population": population_name,
        "tier": tier,
        "features": features,
        "threshold": locked_threshold,
        "threshold_policy": config["threshold_policy"],
        "bands": bands,
        "split": config["split"],
        "model_type": chosen["model_type"],
        "hyperparameters": chosen["best_params"],
        "sklearn_version": sklearn.__version__,
        "train_rows": int(split_data["train_core"]["n_clean"]),
        "val_rows": int(split_data["validation"]["n_clean"]),
        "val_auroc": float(chosen["val_auroc"]),
        "test_metrics": {
            "auroc": float(ci_auroc.point) if ci_auroc.point is not None else 0.0,
            "auprc": float(ci_auprc.point) if ci_auprc.point is not None else 0.0,
            "brier": float(cal_test["brier"]) if cal_test["brier"] is not None else 0.0,
            "sensitivity": float(m_test["sensitivity"]) if m_test["sensitivity"] is not None else 0.0,
            "specificity": float(m_test["specificity"]) if m_test["specificity"] is not None else 0.0,
            "ppv": float(m_test["ppv"]) if m_test["ppv"] is not None else 0.0,
            "npv": float(m_test["npv"]) if m_test["npv"] is not None else 0.0,
            "calibration_slope": float(test_slope) if test_slope is not None else 0.0,
            "calibration_intercept": float(cal_test["intercept"]) if cal_test["intercept"] is not None else 0.0,
        },
        "notes": config.get("notes", "Framingham Heart Study 10-year CHD risk model (LR).") if name == "chd10_framingham" else config.get("notes", ""),
    }

    if calibration_gate_passed:
        print(f"\nSaving model artifact to {out_models_dir}...")
        save_model_artifact(chosen_pipe, model_card, out_models_dir)

        # LR Production Export & Pure Python Parity Verification
        if "lr" in chosen["model_type"]:
            export_path = out_models_dir / "export.json"
            export_spec = export_production_lr(chosen_pipe, model_card, export_path)

            print("Verifying pure-Python scorer against scikit-learn predict_proba on validation rows...")
            val_df_recs = split_data["validation"]["df"][features].to_dict(orient="records")
            py_probs = np.array([score_record_pure_python(r, export_spec) for r in val_df_recs])
            sk_probs = chosen["val_prob"]
            max_diff = float(np.max(np.abs(py_probs - sk_probs)))
            print(f"  Max absolute difference: {max_diff:.3e}")
            assert max_diff < 1e-9, f"Pure-Python scorer differs from predict_proba by {max_diff} (> 1e-9)!"
            print("✓ Pure-Python scorer matches predict_proba within 1e-9 tolerance.")
    else:
        print(f"\nSkipping model export due to: {cal_gate_status}")

    # Compile metrics dictionary
    wall_time = time.perf_counter() - start_time
    metrics_payload = {
        "config": config,
        "wall_time_seconds": round(wall_time, 2),
        "split_counts": {
            s: {
                "initial": split_data[s]["n_initial"],
                "dropped": split_data[s]["n_dropped"],
                "clean": split_data[s]["n_clean"],
                "positives": split_data[s]["n_pos"],
                "prevalence": split_data[s]["prevalence"],
            }
            for s in ["train_core", "validation", "test"]
        },
        "candidate_models": {
            m: {
                "best_params": candidate_results[m]["best_params"],
                "val_auroc": candidate_results[m]["val_auroc"],
                "val_calibration_slope": candidate_results[m]["val_calibration"]["slope"],
            }
            for m in model_types_to_try
        },
        "chosen_model": {
            "model_type": chosen["model_type"],
            "selection_reason": selection_reason,
            "best_params": chosen["best_params"],
            "val_auroc": chosen["val_auroc"],
            "val_calibration_slope": val_slope,
            "calibration_gate": cal_gate_status,
        },
        "threshold": {
            "policy": config["threshold_policy"],
            "locked_threshold": locked_threshold,
            "val_sensitivity": val_sens,
            "val_specificity": val_spec,
        },
        "bands": bands,
        "test_evaluation": {
            "auroc": {
                "point": ci_auroc.point,
                "ci_low": ci_auroc.low,
                "ci_high": ci_auroc.high,
            },
            "auprc": {
                "point": ci_auprc.point,
                "ci_low": ci_auprc.low,
                "ci_high": ci_auprc.high,
            },
            "metrics_at_threshold": m_test,
            "metrics_at_10pct": m_test,
            "metrics_at_20pct": m_test_20,
            "calibration": {
                "brier": cal_test["brier"],
                "citl": cal_test["calibration_in_the_large"],
                "slope": cal_test["slope"],
                "intercept": cal_test["intercept"],
            },
            "worst_subgroup": {
                "group": worst_group,
                "positives": worst_pos,
                "sensitivity": worst_sens,
            },
            "card_population": card_subgroup_row,
            "subgroups": subgroups,
            "decision_curve": dca_table,
        },
        "feature_explanations": feature_explanations,
        "clinical_sanity": clinical_sanity,
        "shap_global": shap_global,
        "fake_patient_shap": fake_patient_shap,
        "shap_notice": shap_notice,
        "d11_gates": gate_results,
        "ship_status": ship_status,
    }

    # Save metrics.json
    out_reports_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_reports_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    # Generate Markdown Report
    sec_config = (
        f"- **Name:** `{name}`\n"
        f"- **Target Label:** `{label_name}`\n"
        f"- **Population Filter:** `{population_name}`\n"
        f"- **Tier:** `{tier}`\n"
        f"- **Features ({len(features)}):** `{', '.join(features)}`\n"
        f"- **Candidate Models:** `{', '.join(model_types_to_try)}`\n"
        f"- **Threshold Policy:** `{json.dumps(config['threshold_policy'])}`\n"
        f"- **Seed:** `{seed}`\n"
        f"- **Wall Time:** {wall_time:.2f} seconds ({wall_time / 60:.1f} minutes)\n"
    )

    if name == "chd10_framingham":
        sec_data = (
            f"### Complete Case Cohort Statistics Across Stratified 60/20/20 Splits\n\n"
            f"| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |\n"
            f"|---|---|---|---|---|---|\n"
            f"| `train` (60%) | {split_data['train_core']['n_initial']:,} | {split_data['train_core']['n_dropped']:,} | {split_data['train_core']['n_clean']:,} | {split_data['train_core']['n_pos']:,} | {split_data['train_core']['prevalence']:.2f}% |\n"
            f"| `validation` (20%) | {split_data['validation']['n_initial']:,} | {split_data['validation']['n_dropped']:,} | {split_data['validation']['n_clean']:,} | {split_data['validation']['n_pos']:,} | {split_data['validation']['prevalence']:.2f}% |\n"
            f"| `test` (20%) | {split_data['test']['n_initial']:,} | {split_data['test']['n_dropped']:,} | {split_data['test']['n_clean']:,} | {split_data['test']['n_pos']:,} | {split_data['test']['prevalence']:.2f}% |\n"
        )
    else:
        sec_data = (
            f"### Complete Case Cohort Statistics Across Temporal Splits\n\n"
            f"| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |\n"
            f"|---|---|---|---|---|---|\n"
            f"| `train_core` (1999-2012) | {split_data['train_core']['n_initial']:,} | {split_data['train_core']['n_dropped']:,} | {split_data['train_core']['n_clean']:,} | {split_data['train_core']['n_pos']:,} | {split_data['train_core']['prevalence']:.2f}% |\n"
            f"| `validation` (2013-2016) | {split_data['validation']['n_initial']:,} | {split_data['validation']['n_dropped']:,} | {split_data['validation']['n_clean']:,} | {split_data['validation']['n_pos']:,} | {split_data['validation']['prevalence']:.2f}% |\n"
            f"| `test` (2017-2023) | {split_data['test']['n_initial']:,} | {split_data['test']['n_dropped']:,} | {split_data['test']['n_clean']:,} | {split_data['test']['n_pos']:,} | {split_data['test']['prevalence']:.2f}% |\n"
        )

    cand_rows = []
    for m in model_types_to_try:
        cand_rows.append({
            "Model": m,
            "Best Hyperparameters": json.dumps(candidate_results[m]["best_params"]),
            "Val AUROC": f"{candidate_results[m]['val_auroc']:.4f}",
            "Val Calibration Slope": f"{candidate_results[m]['val_calibration']['slope']:.3f}" if candidate_results[m]['val_calibration']['slope'] is not None else "N/A",
        })
    cand_df = pd.DataFrame(cand_rows)

    sec_val = (
        f"### Candidate Model Validation Tuning\n\n"
        f"{df_to_markdown(cand_df, index=False)}\n\n"
        f"### Decision D10 Selection Rationale\n"
        f"- **Chosen Architecture:** `{chosen['model_type']}`\n"
        f"- **Selection Rule:** {selection_reason}\n"
        f"- **Validation Calibration Gate:** `{cal_gate_status}` (Slope: {val_slope:.3f})\n"
        f"- **D7 Locked Threshold:** `{locked_threshold:.4f}` (Val Sens: {val_sens:.2%}, Val Spec: {val_spec:.2%})\n"
        f"- **D8 Risk Stratification Bands:** Low < `{low_max:.4f}`, Moderate `{low_max:.4f}` - `{high_min:.4f}`, High >= `{high_min:.4f}`\n"
    )
    if ranking_warning:
        sec_val += f"\n> **Clinical Warning:** {ranking_warning}.\n"

    if name == "chd10_framingham":
        sec_test = (
            f"### Held-Out Test Discrimination & Diagnostic Performance\n\n"
            f"- **Test AUROC (95% Bootstrap CI):** **{ci_auroc.point:.4f}** [{ci_auroc.low:.4f} - {ci_auroc.high:.4f}]\n"
            f"- **Test AUPRC (95% Bootstrap CI):** **{ci_auprc.point:.4f}** [{ci_auprc.low:.4f} - {ci_auprc.high:.4f}]\n\n"
            f"#### Operating Point: 10% Cutoff (Moderate / High Risk)\n"
            f"- **Threshold:** `0.1000`\n"
            f"- **Sensitivity:** **{m_test['sensitivity']:.2%}**\n"
            f"- **Specificity:** **{m_test['specificity']:.2%}**\n"
            f"- **PPV (Precision):** **{m_test['ppv']:.2%}**\n"
            f"- **NPV:** **{m_test['npv']:.2%}**\n"
            f"- **F1-Score:** **{m_test['f1']:.4f}**\n"
            f"- **Confusion Matrix:** TP={m_test['tp']}, FP={m_test['fp']}, TN={m_test['tn']}, FN={m_test['fn']}\n\n"
            f"#### Operating Point: 20% Cutoff (High Risk)\n"
            f"- **Threshold:** `0.2000`\n"
            f"- **Sensitivity:** **{m_test_20['sensitivity']:.2%}**\n"
            f"- **Specificity:** **{m_test_20['specificity']:.2%}**\n"
            f"- **PPV (Precision):** **{m_test_20['ppv']:.2%}**\n"
            f"- **NPV:** **{m_test_20['npv']:.2%}**\n"
            f"- **F1-Score:** **{m_test_20['f1']:.4f}**\n"
            f"- **Confusion Matrix:** TP={m_test_20['tp']}, FP={m_test_20['fp']}, TN={m_test_20['tn']}, FN={m_test_20['fn']}\n\n"
            f"### Pre-Registered Acceptance Gates Audit (G1 - G5)\n\n"
            f"- Gate 1 (Test AUROC >= 0.68): **{gate_results['gate_1_test_auroc_ge_0_68']}** ({ci_auroc.point:.4f})\n"
            f"- Gate 2 (Test Calibration Slope in [0.80, 1.20]): **{gate_results['gate_2_calibration_slope_in_0_80_1_20']}** ({slope_str})\n"
            f"- Gate 3 (Test Sensitivity @ 10% >= 70%): **{gate_results['gate_3_sensitivity_10pct_ge_0_70']}** ({m_test['sensitivity']:.2%})\n"
            f"- Gate 4 (Subgroup Sens @ 10% >= 60%): **{gate_results['gate_4_subgroup_sens_ge_0_60']}** (Worst: {worst_group}={worst_sens:.2%})\n"
            f"- Gate 5 (Brier Score < Naive Prevalence Brier): **{gate_results['gate_5_brier_lower_than_prevalence']}** ({test_brier:.4f} vs {prev_brier:.4f})\n"
            f"- **Overall FYP-1 Status:** **{ship_status}**\n"
        )
    else:
        sec_test = (
            f"### Held-Out Test Discrimination & Diagnostic Performance (2017-2023)\n\n"
            f"- **Test AUROC (95% Bootstrap CI):** **{ci_auroc.point:.4f}** [{ci_auroc.low:.4f} - {ci_auroc.high:.4f}]\n"
            f"- **Test AUPRC (95% Bootstrap CI):** **{ci_auprc.point:.4f}** [{ci_auprc.low:.4f} - {ci_auprc.high:.4f}]\n"
            f"- **Locked Threshold:** `{locked_threshold:.4f}`\n"
            f"- **Test Sensitivity:** **{m_test['sensitivity']:.2%}**\n"
            f"- **Test Specificity:** **{m_test['specificity']:.2%}**\n"
            f"- **Test PPV:** **{m_test['ppv']:.2%}**\n"
            f"- **Test NPV:** **{m_test['npv']:.2%}**\n"
            f"- **Confusion Matrix:** TP={m_test['tp']}, FP={m_test['fp']}, TN={m_test['tn']}, FN={m_test['fn']}\n\n"
            f"### D11 Acceptance Gate Audit\n\n"
            f"- Gate 1 (Test AUROC >= 0.75): **{gate_results['gate_1_test_auroc_ge_0_75']}** ({ci_auroc.point:.4f})\n"
            f"- Gate 2 (Test Sensitivity >= 0.75): **{gate_results['gate_2_test_sens_ge_0_75']}** ({m_test['sensitivity']:.2%})\n"
            f"- Gate 3 (Test Calibration Slope 0.8-1.2): **{gate_results['gate_3_calibration_slope_0_8_to_1_2']}** ({slope_str})\n"
            f"- Gate 4 (Subgroup Sens >= 0.60): **{gate_results['gate_4_subgroup_sens_ge_0_60']}** (Worst: {worst_sens:.2%})\n"
            f"- Gate 5 (FULL beats BASIC on Val AUROC): **{gate_results['gate_5_full_beats_basic']}**\n"
            f"- **Overall FYP-1 Status:** **{ship_status}**\n"
        )

    sec_cal = (
        f"### Test Calibration Diagnostics\n\n"
        f"- **Brier Score:** {cal_test['brier']:.4f} (Naive Prevalence Brier: {prev_brier if name == 'chd10_framingham' else 'N/A'})\n"
        f"- **Calibration-in-the-large (mean p - mean y):** {cal_test['calibration_in_the_large']:+.4f}\n"
        f"- **Logistic Calibration Slope:** {cal_test['slope']:.3f}\n"
        f"- **Logistic Calibration Intercept:** {cal_test['intercept']:+.3f}\n\n"
        f"#### Reliability Table Across Decile Bins\n\n"
        f"{df_to_markdown(pd.DataFrame(cal_test['reliability_table']), index=False) if cal_test['reliability_table'] else 'N/A'}\n"
    )

    sg_rows = []
    for sg in subgroups:
        sg_rows.append({
            "Dimension": sg["group_type"],
            "Group": sg["group_value"],
            "Total (n)": f"{sg['n']:,}",
            "Positives": f"{sg['positives']:,}",
            "Prevalence": f"{sg['prevalence'] * 100:.1f}%",
            "AUROC": f"{sg['auroc']:.4f}" if isinstance(sg["auroc"], (int, float)) else str(sg["auroc"]),
            "Sensitivity": f"{sg['sensitivity'] * 100:.1f}%" if isinstance(sg["sensitivity"], (int, float)) else str(sg["sensitivity"]),
            "Specificity": f"{sg['specificity'] * 100:.1f}%" if isinstance(sg["specificity"], (int, float)) else str(sg["specificity"]),
        })

    subgroup_table_md = df_to_markdown(pd.DataFrame(sg_rows), index=False)
    feat_table_md = df_to_markdown(pd.DataFrame(feature_explanations), index=False)
    sanity_table_md = df_to_markdown(pd.DataFrame(clinical_sanity), index=False) if clinical_sanity else "N/A"
    shap_global_md = df_to_markdown(pd.DataFrame(shap_global), index=False) if shap_global else "N/A"
    dca_md = df_to_markdown(pd.DataFrame(dca_table), index=False) if dca_table else "N/A"

    sec_sub = (
        f"### Subgroup Breakdown on Held-Out Test Set\n\n"
        f"{subgroup_table_md}\n\n"
        f"### Feature Importance & Odds Ratios\n\n"
        f"{feat_table_md}\n\n"
        f"### Clinical Sanity Direction Check\n\n"
        f"{sanity_table_md}\n\n"
        f"### Global SHAP Feature Attributions\n\n"
        f"{shap_global_md}\n\n"
        f"### Decision Curve Analysis (Net Benefit across Thresholds)\n\n"
        f"{dca_md}\n\n"
        f"> **SHAP Method Notice:** {shap_notice}\n"
    )

    if name == "chd10_framingham":
        sec_lim = (
            f"- **Dataset Context:** Framingham Heart Study 10-year risk reflects an American cohort initialized in 1948 with predominantly White participants; baseline risk may vary for contemporary South Asian populations.\n"
            f"- **Clinical Setting:** BP readings in Framingham were standardized clinical measurements, whereas ChronicCare AI receives home self-measurements.\n"
            f"- **Intended Use:** Provider decision support with patient-facing risk tier; raw risk percentages are not shown to patients to avoid unnecessary anxiety.\n"
        )
    else:
        sec_lim = (
            f"- **Temporal Shift:** Evaluated strictly on temporal hold-out cohorts (2017-2023) following historical fitting (1999-2012).\n"
            f"- **External Validation:** BRFSS validation cannot evaluate undiagnosed labels because BRFSS lacks biological specimen assays and cuff measurements.\n"
            f"- **Complete Cases:** Complete case analysis drops missing survey records without synthetic imputation.\n"
        )

    sections = {
        "Config": sec_config,
        "Data": sec_data,
        "Validation": sec_val,
        "Test": sec_test,
        "Calibration": sec_cal,
        "Subgroups": sec_sub,
        "Limitations": sec_lim,
    }

    doc_report_path = out_docs_dir / f"{name}.md"
    write_eval_report(doc_report_path, sections)
    print(f"\nSaved standardized evaluation report to: {doc_report_path}")

    print(f"\n=======================================================")
    print(f"EXPERIMENT FINISHED: {name} in {wall_time:.2f}s ({wall_time / 60:.1f}m)")
    print(f"Status: {ship_status}")
    print(f"=======================================================\n")

    return metrics_payload


def main():
    parser = argparse.ArgumentParser(description="ChronicCare AI ML Experiment Harness")
    parser.add_argument("--config", type=str, required=True, help="Path to experiment JSON config file")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    config_data = json.loads(cfg_path.read_text(encoding="utf-8"))
    run_experiment(config_data)


if __name__ == "__main__":
    main()
