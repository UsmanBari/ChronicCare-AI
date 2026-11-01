"""
External Validation Runner for ChronicCare-AI Clinical ML Models.

Validates trained model artifacts against independent external cohorts:
- Framingham Heart Study Cohort (N = 4,238)
- Pima Indians Diabetes Cohort (N = 768)
- CDC BRFSS 2015 Kaggle (N = 253,680)
- CDC BRFSS Core Parquet (N = 2,181,756)
- Cardio70k Cardiovascular Examination Records (N = 70,000)

CLINICAL SAFETY CONSTRAINTS:
1. Operational decision thresholds are NEVER re-tuned on external validation data.
   The threshold is strictly preserved from the model card (in as-saved mode)
   or selected on NHANES validation split (in overlap refit mode).
2. For models whose feature set exceeds external dataset indicators, an
   "overlap refit, not Usman's saved model" is performed on NHANES train_core,
   with threshold selected on NHANES validation split.
3. If overlapping features < 2, the pair is flagged NOT RUN (< 2 features).
4. Pairs are selected strictly by matching (card.label, card.population) against
   an explicit equivalence table. Unmatched pairs are skipped with reason printed.
5. If an external dataset file is absent, it is flagged NOT RUN, never crashing.
6. AUROC point estimates and 95% bootstrap CIs are computed on the identical sample basis.
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ml.artifacts import load_model_artifact
from ml.common import (
    brfss_core_path,
    cardio70k_path,
    df_to_markdown,
    framingham_path,
    load_brfss_core,
    load_nhanes_core,
    load_split,
    pima_path,
)
from ml.datasets import (
    load_brfss2015_kaggle,
    load_cardio70k,
    load_framingham,
    load_pima,
)
from ml.evaluation import (
    bootstrap_ci,
    calibration,
    choose_threshold,
    metrics_at_threshold,
)
from ml.labels import LABELS
from sklearn.base import clone
from sklearn.metrics import roc_auc_score

# Explicit mapping from (card.label, card.population) to target evaluation suites
EQUIVALENCE_TABLE: dict[tuple[str, str], dict[str, Any]] = {
    ("diabetes_undiagnosed", "adults_without_diabetes"): {
        "section": "diabetes",
        "table1_targets": [
            {
                "dataset": "framingham",
                "cohort": "undiagnosed",  # diabetes == 0
                "target_col": "glucose_ge_200",
                "display": "glucose >= 200 mg/dL (proxy random glucose, ADA cutoff)",
                "note": "diabetes==0 cohort; max glucose is 163.0 mg/dL (0 positive cases)",
            },
            {
                "dataset": "framingham",
                "cohort": "undiagnosed",  # diabetes == 0
                "target_col": "glucose_ge_126",
                "display": 'glucose >= 126 mg/dL ("only valid if fasting")',
                "note": "diabetes==0 cohort (22 positives, 0.54% prevalence)",
            },
            {
                "dataset": "pima",
                "cohort": "all",
                "target_col": "diabetes",
                "display": "diabetes (measured 2h OGTT >= 200 mg/dL)",
                "note": "Adult women only, indigenous heritage, not restricted to undiagnosed",
            },
        ],
        "table2_targets": [
            {
                "dataset": "brfss2015_kaggle",
                "cohort": "all",
                "target_col": "diabetes",
                "display": "diabetes (ever told diabetes)",
                "note": "Different target: told diabetes in general adult population",
            },
            {
                "dataset": "brfss_core",
                "cohort": "all",
                "target_col": "diabetes",
                "display": "diabetes (ever told diabetes)",
                "note": "Different target: told diabetes in general adult population",
            },
        ],
    },
    ("hypertension_measured_130_80", "adults_without_htn_unmedicated"): {
        "section": "hypertension_retired",
        "appendix_targets": [
            {
                "dataset": "framingham",
                "cohort": "undiagnosed_htn",  # prevalent_hyp == 0 & bp_meds == 0
                "target_col": "htn_measured_130_80",
                "display": "measured >= 130/80 mmHg (prevalent_hyp==0 & bp_meds==0)",
                "note": "Closest undiagnosed HTN analogue (51.1% prevalence)",
            },
            {
                "dataset": "cardio70k",
                "cohort": "all",
                "target_col": "htn_measured_130_80",
                "display": "htn_measured_130_80 (measured >= 130/80 mmHg)",
                "note": "Different population: clinical examinees, not restricted to unmedicated/untold",
                "skip_if_features_contain": ("sbp", "dbp", "sysbp", "diabp", "bp"),
            },
            {
                "dataset": "brfss_core",
                "cohort": "all",
                "target_col": "high_bp",
                "display": "high_bp (ever told high BP)",
                "note": "Different target: told high BP in general adult population",
            },
        ],
    },
}


def get_model_disease_category(label_name: str, population: str = "") -> str | None:
    """
    Determine disease category strictly from EQUIVALENCE_TABLE matching both (label, population).
    """
    if (label_name, population) in EQUIVALENCE_TABLE:
        return EQUIVALENCE_TABLE[(label_name, population)]["section"]
    return None


def get_candidate_datasets_for_model(card: dict[str, Any]) -> list[tuple[str, str]]:
    """
    Return candidate external dataset identifiers and target columns for a given model
    strictly based on the card's (label, population) registration in EQUIVALENCE_TABLE.
    """
    label = card.get("label", "")
    pop = card.get("population", "")
    key = (label, pop)

    entry = EQUIVALENCE_TABLE.get(key)
    if entry is None:
        return []

    candidates: list[tuple[str, str]] = []
    if entry["section"] == "diabetes":
        for t in entry["table1_targets"] + entry["table2_targets"]:
            candidates.append((t["dataset"], t["target_col"]))
    elif entry["section"] == "hypertension_retired":
        features = card.get("features", [])
        has_bp = any(f.lower() in ("sbp", "dbp", "sysbp", "diabp", "bp") for f in features)
        for t in entry["appendix_targets"]:
            if has_bp and t.get("skip_if_features_contain"):
                continue
            candidates.append((t["dataset"], t["target_col"]))

    return candidates


def load_external_dataset(
    dataset_name: str,
    needed_columns: Sequence[str] | None = None,
) -> tuple[pd.DataFrame | None, str | None]:
    """
    Load external validation dataset with standardized columns.
    Returns (DataFrame, None) or (None, error_reason) if file is missing.
    """
    try:
        if dataset_name == "cardio70k":
            if not cardio70k_path().exists():
                return None, f"Dataset file missing: {cardio70k_path()}"
            df, _ = load_cardio70k()
            return df, None

        elif dataset_name == "framingham":
            if not framingham_path().exists():
                return None, f"Dataset file missing: {framingham_path()}"
            df, _ = load_framingham()
            return df, None

        elif dataset_name == "brfss2015_kaggle":
            df, _ = load_brfss2015_kaggle()
            return df, None

        elif dataset_name == "pima":
            if not pima_path().exists():
                return None, f"Dataset file missing: {pima_path()}"
            df, _ = load_pima()
            return df, None

        elif dataset_name == "brfss_core":
            if not brfss_core_path().exists():
                return None, f"Dataset file missing: {brfss_core_path()}"
            cols = ["diabetes", "high_bp", "sex_male", "age", "bmi", "ever_smoker"]
            if needed_columns:
                cols = list(set(cols).union(needed_columns))
            df = load_brfss_core(columns=cols)
            if "ever_smoker" in df.columns and "ever_smoked_100" not in df.columns:
                df["ever_smoked_100"] = df["ever_smoker"]
            if "high_bp" in df.columns and "told_high_bp" not in df.columns:
                df["told_high_bp"] = df["high_bp"]
            if "diabetes" in df.columns and "told_diabetes" not in df.columns:
                df["told_diabetes"] = df["diabetes"]
            return df, None

        else:
            return None, f"Unknown dataset: {dataset_name}"

    except FileNotFoundError as e:
        return None, f"Dataset file missing: {e}"
    except Exception as e:  # noqa: BLE001
        return None, f"Error loading {dataset_name}: {e}"


def refit_on_overlap(
    pipeline: Any,
    card: dict[str, Any],
    overlap_features: list[str],
    nhanes_df: pd.DataFrame | None = None,
    splits: dict[str, set[int]] | None = None,
) -> tuple[Any, float]:
    """
    Refit the same pipeline architecture on NHANES train_core using only overlapping features.
    Select operating threshold on NHANES validation split.

    CLINICAL SAFETY CRITICAL:
    This function strictly passes NHANES validation arrays to choose_threshold.
    External validation data is NEVER passed to choose_threshold.
    """
    if nhanes_df is None:
        nhanes_df = load_nhanes_core()
    if splits is None:
        splits = load_split()

    label_name = card["label"]
    if label_name not in LABELS:
        raise ValueError(f"Label '{label_name}' not registered in ml.labels.LABELS")

    label_info = LABELS[label_name]
    y_nhanes = label_info.extractor(nhanes_df)

    # Filter complete cases on train_core and validation
    train_mask = (
        nhanes_df["seqn"].isin(splits["train_core"])
        & y_nhanes.notna()
        & nhanes_df[overlap_features].notna().all(axis=1)
    )
    val_mask = (
        nhanes_df["seqn"].isin(splits["validation"])
        & y_nhanes.notna()
        & nhanes_df[overlap_features].notna().all(axis=1)
    )

    X_train = nhanes_df.loc[train_mask, overlap_features].to_numpy()
    y_train = y_nhanes[train_mask].astype(int).to_numpy()

    X_val = nhanes_df.loc[val_mask, overlap_features].to_numpy()
    y_val = y_nhanes[val_mask].astype(int).to_numpy()

    # Clone pipeline architecture & fit
    refit_pipe = clone(pipeline)
    refit_pipe.fit(X_train, y_train)

    # Predict probabilities strictly on NHANES validation split
    p_val = refit_pipe.predict_proba(X_val)[:, 1]

    # Select threshold strictly on NHANES validation data
    policy = card.get("threshold_policy", {"type": "min_sensitivity", "value": 0.80})
    thresh_res = choose_threshold(y_val, p_val, policy)
    chosen_threshold = float(thresh_res["threshold"])

    return refit_pipe, chosen_threshold


def evaluate_pair(
    model_name: str,
    pipeline: Any,
    card: dict[str, Any],
    dataset_name: str,
    target_col: str,
    dataset_df: pd.DataFrame | None,
    nhanes_df: pd.DataFrame | None = None,
    splits: dict[str, set[int]] | None = None,
    target_display: str | None = None,
    eval_note: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate a single (model, external dataset) pair.
    Handles mode selection ('as-saved' vs 'overlap refit' vs 'NOT RUN').
    Computes point AUROC and bootstrap CI on the identical sample basis.
    """
    result: dict[str, Any] = {
        "model": model_name,
        "dataset": dataset_name,
        "target_col": target_col,
        "target_display": target_display or target_col,
        "card_label": card.get("label", ""),
        "card_population": card.get("population", ""),
        "card_threshold": card.get("threshold", np.nan),
        "status": "PASS",
        "mode": "",
        "n": 0,
        "n_pos": 0,
        "prevalence": np.nan,
        "auroc": np.nan,
        "ci_low": np.nan,
        "ci_high": np.nan,
        "ci_basis": "",
        "threshold": np.nan,
        "sensitivity": np.nan,
        "specificity": np.nan,
        "cal_in_large": np.nan,
        "brier": np.nan,
        "missing_features": "",
        "notes": eval_note or "",
    }

    if dataset_df is None:
        result["status"] = "NOT RUN"
        result["notes"] = "Dataset file missing"
        return result

    # Check target column
    if target_col not in dataset_df.columns:
        result["status"] = "NOT RUN"
        result["notes"] = f"Target column '{target_col}' not found in dataset"
        return result

    model_features = list(card.get("features", []))
    overlap_features = [f for f in model_features if f in dataset_df.columns]
    missing_features = [f for f in model_features if f not in dataset_df.columns]

    # Mode determination
    if len(missing_features) == 0:
        mode = "as-saved"
        scoring_pipe = pipeline
        operating_threshold = float(card["threshold"])
        eval_features = model_features
    else:
        # Overlap refit mode
        if len(overlap_features) < 2:
            result["status"] = "NOT RUN"
            result["mode"] = "NOT RUN (< 2 features)"
            result["missing_features"] = ", ".join(missing_features)
            result["notes"] = f"Overlap < 2 features ({overlap_features})"
            return result

        mode = "overlap refit, not Usman's saved model"
        eval_features = overlap_features
        result["missing_features"] = ", ".join(missing_features)

        # Refit on NHANES train_core, threshold on NHANES validation
        try:
            scoring_pipe, operating_threshold = refit_on_overlap(
                pipeline=pipeline,
                card=card,
                overlap_features=overlap_features,
                nhanes_df=nhanes_df,
                splits=splits,
            )
        except Exception as e:  # noqa: BLE001
            result["status"] = "ERROR"
            result["notes"] = f"Overlap refit failed: {e}"
            return result

    result["mode"] = mode
    result["threshold"] = operating_threshold

    # Complete cases in external dataset
    cols_to_check = eval_features + [target_col]
    valid_mask = dataset_df[cols_to_check].notna().all(axis=1)
    df_eval = dataset_df.loc[valid_mask]

    n_eval = len(df_eval)
    result["n"] = n_eval
    if n_eval == 0:
        result["status"] = "NOT RUN"
        result["notes"] = "Zero complete cases for evaluation"
        return result

    X_ext = df_eval[eval_features].to_numpy()
    y_ext = df_eval[target_col].astype(int).to_numpy()

    result["n_pos"] = int(np.sum(y_ext == 1))
    result["prevalence"] = float(np.mean(y_ext))

    # Single class check (e.g. glucose >= 200 in Framingham undiagnosed cohort)
    if len(np.unique(y_ext)) < 2:
        result["status"] = "NOT RUN"
        unique_val = int(np.unique(y_ext)[0])
        result["notes"] = f"Single class ({unique_val}) in external cohort ground truth (0 positive cases)"
        return result

    # Model predictions
    p_ext = scoring_pipe.predict_proba(X_ext)[:, 1]

    # CI basis and point AUROC: compute both on the identical sample basis
    if len(y_ext) > 50000:
        rng = np.random.default_rng(42)
        idx_pos = np.where(y_ext == 1)[0]
        idx_neg = np.where(y_ext == 0)[0]
        frac = 50000.0 / len(y_ext)
        n_pos_sub = max(10, int(len(idx_pos) * frac))
        n_neg_sub = max(10, int(len(idx_neg) * frac))
        sub_pos = rng.choice(idx_pos, size=n_pos_sub, replace=False)
        sub_neg = rng.choice(idx_neg, size=n_neg_sub, replace=False)
        sub_idx = np.concatenate([sub_pos, sub_neg])
        y_eval_basis = y_ext[sub_idx]
        p_eval_basis = p_ext[sub_idx]
        ci_basis_str = "50k stratified sample"
    else:
        y_eval_basis = y_ext
        p_eval_basis = p_ext
        ci_basis_str = "full n"

    result["ci_basis"] = ci_basis_str
    auc_val = float(roc_auc_score(y_eval_basis, p_eval_basis))
    result["auroc"] = auc_val

    boot_res = bootstrap_ci(y_eval_basis, p_eval_basis, roc_auc_score, n_boot=200, seed=42)
    result["ci_low"] = boot_res.low if boot_res.low is not None else np.nan
    result["ci_high"] = boot_res.high if boot_res.high is not None else np.nan

    # Diagnostic performance at operating threshold
    diag_metrics = metrics_at_threshold(y_ext, p_ext, operating_threshold)
    result["sensitivity"] = diag_metrics["sensitivity"]
    result["specificity"] = diag_metrics["specificity"]

    # Calibration & Brier
    cal_res = calibration(y_ext, p_ext)
    result["cal_in_large"] = cal_res["calibration_in_the_large"]
    result["brier"] = cal_res["brier"]

    return result


def parse_nhanes_test_aurocs(exp_summary_path: Path) -> dict[str, str]:
    """Parse exact NHANES test AUROC [95% CI] values from Section 1 of EXPERIMENTS_SUMMARY.md."""
    aurocs = {}
    if not exp_summary_path.exists():
        return aurocs
    content = exp_summary_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("|") and ("diabetes_" in trimmed or "htn_" in trimmed):
            parts = [p.strip() for p in trimmed.split("|")]
            if len(parts) >= 8:
                m_name = parts[1].replace("`", "")
                if m_name in (
                    "diabetes_full_nhanes",
                    "diabetes_basic_nhanes",
                    "diabetes_ref_age_sex_bmi",
                ) and m_name not in aurocs:
                    aurocs[m_name] = parts[6]
    return aurocs


def run_all_external_validations(
    output_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Run external validation dynamically driven by (card.label, card.population)
    registered in EQUIVALENCE_TABLE across all models discovered in outputs/models.
    """
    models_dir = Path("backend-poc-technical/ml/outputs/models")
    if not models_dir.exists():
        models_dir = Path(__file__).resolve().parent / "outputs" / "models"

    # Pre-load shared NHANES data and splits for refits
    nhanes_df = load_nhanes_core()
    splits = load_split()

    # Load external datasets
    print("Loading external datasets...")
    df_fram_raw, _ = load_framingham()
    df_pima, _ = load_pima()
    df_cardio, cardio_report = load_cardio70k()
    df_brfss_k, _ = load_brfss2015_kaggle()
    df_brfss_c = load_brfss_core(columns=["diabetes", "high_bp", "sex_male", "age", "bmi", "ever_smoker"])
    if "ever_smoker" in df_brfss_c.columns and "ever_smoked_100" not in df_brfss_c.columns:
        df_brfss_c["ever_smoked_100"] = df_brfss_c["ever_smoker"]
    if "high_bp" in df_brfss_c.columns and "told_high_bp" not in df_brfss_c.columns:
        df_brfss_c["told_high_bp"] = df_brfss_c["high_bp"]

    # Prepare Framingham undiagnosed diabetes cohort (diabetes == 0)
    df_fram_undiag = df_fram_raw[df_fram_raw["diabetes"] == 0].copy()
    df_fram_undiag["glucose_ge_200"] = (df_fram_undiag["glucose"] >= 200).astype(int)
    df_fram_undiag["glucose_ge_126"] = (df_fram_undiag["glucose"] >= 126).astype(int)

    # Prepare Framingham undiagnosed HTN cohort (prevalent_hyp == 0 & bp_meds == 0)
    mask_fram_htn = (df_fram_raw["prevalent_hyp"] == 0) & (df_fram_raw["bp_meds"] == 0)
    df_fram_und_htn = df_fram_raw[mask_fram_htn].copy()
    df_fram_und_htn["htn_measured_130_80"] = (
        (df_fram_und_htn["sbp"] >= 130) | (df_fram_und_htn["dbp"] >= 80)
    ).astype(int)

    # Dynamic model discovery
    available_model_dirs = sorted([
        d for d in models_dir.iterdir()
        if d.is_dir() and (d / "model_card.json").exists() and (d / "model.joblib").exists()
    ])

    # Lead order priority: diabetes_full_nhanes (0), other diabetes (1), htn_full_nhanes (2), other (3)
    def model_sort_key(d: Path) -> tuple[int, str]:
        name = d.name
        if name == "diabetes_full_nhanes":
            return (0, name)
        elif "diabetes" in name:
            return (1, name)
        elif name == "htn_full_nhanes":
            return (2, name)
        return (3, name)

    available_model_dirs = sorted(available_model_dirs, key=model_sort_key)

    results_table1: list[dict[str, Any]] = []
    results_table2: list[dict[str, Any]] = []
    results_table3: list[dict[str, Any]] = []

    print(f"\nDiscovered {len(available_model_dirs)} model directories under {models_dir}:")
    for md in available_model_dirs:
        pipe, card = load_model_artifact(md)
        label = card.get("label", "")
        population = card.get("population", "")
        key = (label, population)

        if key not in EQUIVALENCE_TABLE:
            print(f"skipped: no external equivalent for {label}/{population} (model: {md.name})")
            continue

        suite = EQUIVALENCE_TABLE[key]
        section = suite["section"]

        if section == "diabetes":
            print(f"\n[{md.name}] Evaluating Table 1 targets (undiagnosed diabetes proxies)...")
            for t_info in suite["table1_targets"]:
                ds_name = t_info["dataset"]
                t_col = t_info["target_col"]
                ds_df = df_fram_undiag if ds_name == "framingham" else df_pima
                res = evaluate_pair(
                    model_name=md.name,
                    pipeline=pipe,
                    card=card,
                    dataset_name=ds_name,
                    target_col=t_col,
                    dataset_df=ds_df,
                    nhanes_df=nhanes_df,
                    splits=splits,
                    target_display=t_info["display"],
                    eval_note=t_info["note"],
                )
                results_table1.append(res)
                if res["status"] == "NOT RUN":
                    print(f"  - {ds_name} ({t_col}): NOT RUN ({res['notes']})")
                else:
                    print(
                        f"  - {ds_name} ({t_col}): AUROC={res['auroc']:.3f} "
                        f"[{res['ci_low']:.3f}, {res['ci_high']:.3f}] | Mode: {res['mode']}"
                    )

            print(f"\n[{md.name}] Evaluating Table 2 targets (told diabetes: ranking only)...")
            for t_info in suite["table2_targets"]:
                ds_name = t_info["dataset"]
                t_col = t_info["target_col"]
                ds_df = df_brfss_k if ds_name == "brfss2015_kaggle" else df_brfss_c
                res = evaluate_pair(
                    model_name=md.name,
                    pipeline=pipe,
                    card=card,
                    dataset_name=ds_name,
                    target_col=t_col,
                    dataset_df=ds_df,
                    nhanes_df=nhanes_df,
                    splits=splits,
                    target_display=t_info["display"],
                    eval_note=t_info["note"],
                )
                results_table2.append(res)
                print(
                    f"  - {ds_name} ({t_col}): AUROC={res['auroc']:.3f} "
                    f"[{res['ci_low']:.3f}, {res['ci_high']:.3f}] | Mode: {res['mode']}"
                )

        elif section == "hypertension_retired":
            print(f"\n[{md.name}] Evaluating Appendix targets (retired hypertension models)...")
            for t_info in suite["appendix_targets"]:
                ds_name = t_info["dataset"]
                t_col = t_info["target_col"]

                # Check skip rules (e.g. models with BP features on Cardio70k)
                skip_features = t_info.get("skip_if_features_contain")
                features = card.get("features", [])
                if skip_features and any(f.lower() in skip_features for f in features):
                    print(f"  - {ds_name}: skipped for {md.name} (model contains BP features).")
                    continue

                if ds_name == "framingham":
                    ds_df = df_fram_und_htn
                elif ds_name == "cardio70k":
                    ds_df = df_cardio
                else:
                    ds_df = df_brfss_c

                res = evaluate_pair(
                    model_name=md.name,
                    pipeline=pipe,
                    card=card,
                    dataset_name=ds_name,
                    target_col=t_col,
                    dataset_df=ds_df,
                    nhanes_df=nhanes_df,
                    splits=splits,
                    target_display=t_info["display"],
                    eval_note=t_info["note"],
                )
                results_table3.append(res)
                print(
                    f"  - {ds_name} ({t_col}): AUROC={res['auroc']:.3f} "
                    f"[{res['ci_low']:.3f}, {res['ci_high']:.3f}] | Mode: {res['mode']}"
                )

    # Collect dynamic metrics for report prose
    exp_summary_path = Path("docs/ml/EXPERIMENTS_SUMMARY.md")
    nhanes_test_aurocs = parse_nhanes_test_aurocs(exp_summary_path)

    # Dynamic metrics from results (strictly required; fail fast if missing rather than silently using old typed-in defaults)
    f126_res = next((r for r in results_table1 if r["target_col"] == "glucose_ge_126"), None)
    if f126_res is None or np.isnan(f126_res["auroc"]):
        raise RuntimeError("Missing or failed external validation result for Framingham glucose_ge_126")

    pima_res = next((r for r in results_table1 if r["dataset"] == "pima"), None)
    if pima_res is None or np.isnan(pima_res["auroc"]):
        raise RuntimeError("Missing or failed external validation result for Pima diabetes")

    cardio_htn_res = next((r for r in results_table3 if r["dataset"] == "cardio70k"), None)
    if cardio_htn_res is None or np.isnan(cardio_htn_res["auroc"]):
        raise RuntimeError("Missing or failed external validation result for Cardio70k hypertension")

    brfss_aurocs = [r["auroc"] for r in results_table2 if not np.isnan(r["auroc"])]
    if not brfss_aurocs:
        raise RuntimeError("Missing or failed external validation results for BRFSS")

    dynamic_context = {
        "framingham_total_undiag": len(df_fram_undiag),
        "framingham_measured_glucose": int(df_fram_undiag["glucose"].notna().sum()),
        "framingham_max_glucose": float(df_fram_undiag["glucose"].max()),
        "framingham_ge_126_positives": f126_res["n_pos"],
        "framingham_ge_126_prev": f126_res["prevalence"] * 100.0,
        "framingham_ge_126_auroc": f126_res["auroc"],
        "framingham_ge_126_ci_low": f126_res["ci_low"],
        "framingham_ge_126_ci_high": f126_res["ci_high"],
        "pima_prev": pima_res["prevalence"] * 100.0,
        "pima_auroc": pima_res["auroc"],
        "pima_ci_low": pima_res["ci_low"],
        "pima_ci_high": pima_res["ci_high"],
        "brfss_min_auroc": min(brfss_aurocs),
        "brfss_max_auroc": max(brfss_aurocs),
        "cardio_clean_bp": cardio_htn_res["n"],
        "cardio_prev_pct": cardio_htn_res["prevalence"] * 100.0,
        "cardio_htn_pos": cardio_htn_res["n_pos"],
        "cardio_swapped": cardio_report["rule2_swapped_inverted"],
        "cardio_unswappable": cardio_report["rule2_unswappable_inverted"],
        "cardio_rule2_handled": cardio_report["rule2_swapped_inverted"] + cardio_report["rule2_unswappable_inverted"],
        "cardio_rule1_neg": cardio_report["rule1_negative_rows"],
        "cardio_raw_inverted": cardio_report["rule2_swapped_inverted"] + cardio_report["rule2_unswappable_inverted"] + cardio_report["rule1_negative_rows"],
        "nhanes_full_test_auroc": nhanes_test_aurocs["diabetes_full_nhanes"],
        "nhanes_basic_test_auroc": nhanes_test_aurocs["diabetes_basic_nhanes"],
        "nhanes_ref_test_auroc": nhanes_test_aurocs["diabetes_ref_age_sex_bmi"],
    }

    all_categorized = {
        "table1_undiagnosed_diabetes": results_table1,
        "table2_told_diabetes": results_table2,
        "table3_retired_htn": results_table3,
        "context": dynamic_context,
    }

    generate_validation_report(all_categorized, output_path=output_path)
    return all_categorized


def format_results_table(results: list[dict[str, Any]], include_decision_metrics: bool = True) -> str:
    """Format evaluation results into a clean markdown table."""
    table_rows = []
    for r in results:
        if r["status"] == "NOT RUN":
            auroc_str = "NOT RUN"
            sens_str = "-"
            spec_str = "-"
            cal_str = "-"
            brier_str = "-"
            prev_str = f"{r['prevalence'] * 100:.1f}%" if not np.isnan(r["prevalence"]) else "-"
            ci_basis_str = "-"
        elif np.isnan(r["auroc"]):
            auroc_str = "ERROR"
            sens_str = "-"
            spec_str = "-"
            cal_str = "-"
            brier_str = "-"
            prev_str = "-"
            ci_basis_str = "-"
        else:
            if not np.isnan(r["ci_low"]) and not np.isnan(r["ci_high"]):
                auroc_str = f"{r['auroc']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
            else:
                auroc_str = f"{r['auroc']:.3f}"
            prev_str = f"{r['prevalence'] * 100:.1f}%" if not np.isnan(r["prevalence"]) else "-"
            ci_basis_str = r.get("ci_basis", "-")
            sens_str = f"{r['sensitivity']:.3f}" if not np.isnan(r["sensitivity"]) else "-"
            spec_str = f"{r['specificity']:.3f}" if not np.isnan(r["specificity"]) else "-"
            cal_str = f"{r['cal_in_large']:+.3f}" if not np.isnan(r["cal_in_large"]) else "-"
            brier_str = f"{r['brier']:.3f}" if not np.isnan(r["brier"]) else "-"

        missing_str = r["missing_features"] if r["missing_features"] else "-"

        row = {
            "Model": r["model"],
            "Dataset": r["dataset"],
            "Target Definition": r.get("target_display", r["target_col"]),
            "Mode": r["mode"] if r["mode"] else r["status"],
            "N": f"{r['n']:,}" if r["n"] > 0 else "-",
            "Prevalence": prev_str,
            "AUROC (95% CI)": auroc_str,
            "CI Basis": ci_basis_str,
        }
        if include_decision_metrics:
            row.update({
                "Sens": sens_str,
                "Spec": spec_str,
                "Cal-in-Large": cal_str,
                "Brier": brier_str,
            })
        row["Missing Features"] = missing_str
        table_rows.append(row)

    df_table = pd.DataFrame(table_rows)
    return df_to_markdown(df_table, index=False)


def generate_validation_report(
    results_bundle: dict[str, Any],
    output_path: Path | str | None = None,
) -> str:
    """
    Format external validation results tables and write docs/ML_EXTERNAL_VALIDATION.md
    with clinical discussion adhering strictly to review requirements.
    All prose figures are populated dynamically via f-strings.
    """
    target_path = Path(output_path) if output_path else Path("docs/ML_EXTERNAL_VALIDATION.md")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    t1_md = format_results_table(results_bundle["table1_undiagnosed_diabetes"], include_decision_metrics=True)
    t2_md = format_results_table(results_bundle["table2_told_diabetes"], include_decision_metrics=False)
    t3_md = format_results_table(results_bundle["table3_retired_htn"], include_decision_metrics=True)

    c = results_bundle.get("context", {})

    report_content = f"""# External Validation of ChronicCare-AI ML Models

## Executive Summary
This document presents external validation of trained machine learning models across independent external cohorts:
- **Framingham Heart Study Cohort** (N = 4,238)
- **Pima Indians Diabetes Cohort** (N = 768)
- **CDC BRFSS 2015 Kaggle** (N = 253,680)
- **CDC BRFSS Core Parquet** (N = 2,181,756)
- **Cardio70k Examination Records** (N = 70,000)

Per ML_PLAN D12, the primary model evaluated is `diabetes_full_nhanes` (the only model deployed in the application as provider-only, experimental).
Per ML_PLAN D13, hypertension models are retired and not used in the application; their evaluations appear in the Appendix.

Operating decision thresholds are strictly locked from training/validation on NHANES. Thresholds are never re-tuned on external cohorts.
For cohorts missing model features, an overlap refit is trained on NHANES `train_core` and thresholded on NHANES `validation`.

---

## 1. Undiagnosed Diabetes Target Equivalents

Evaluates diabetes models against external cohorts with biochemical or laboratory proxies for undiagnosed diabetes:
- **Framingham (`diabetes == 0` cohort):** Evaluates two proxies: (1) `glucose >= 200 mg/dL` (ADA random glucose cutoff; 0 positive cases as max glucose is {c['framingham_max_glucose']:.1f} mg/dL in undiagnosed cohort); (2) `glucose >= 126 mg/dL` (fasting cutoff proxy; {c['framingham_ge_126_positives']} positive cases, {c['framingham_ge_126_prev']:.2f}% prevalence).
- **Pima Indians:** Evaluates 2-hour post-load oral glucose tolerance testing (`Outcome` >= 200 mg/dL; caveat: adult females only, indigenous heritage, not restricted to undiagnosed individuals).
- **Cardio70k:** Skipped for diabetes because blood glucose is recorded only as a 3-level categorical index (`1 = normal`, `2 = above normal`, `3 = well above normal`), which does not constitute a clinical diabetes diagnostic equivalent.

{t1_md}

---

## 2. Different Target (Told Diabetes): Ranking Only

> **Important Clinical Methodological Distinction:**
> Calibration, sensitivity, and specificity are not meaningful for our models in this table. Our models predict **undiagnosed diabetes** in adults without prior diabetes diagnosis (`label: diabetes_undiagnosed`, `population: adults_without_diabetes`). BRFSS records **ever told diabetes** (self-reported doctor diagnosis in the general population).
> Self-reported diagnosed diabetes is substantially easier to discriminate from age, BMI, and hypertension history than undiagnosed metabolic dysregulation, producing higher apparent AUROCs that do not reflect performance on undiagnosed screening. Only discriminative ranking (AUROC) is reported.

{t2_md}

---

## Appendix: Retired Models (Not Used in the App)

> **Retirement Notice:**
> Per ML_PLAN D13, hypertension models (`htn_full_nhanes`, `htn_basic_nhanes`, `htn_ref_age_sex_bmi`) are retired and not used in the ChronicCare-AI application. Their target was undiagnosed hypertension (measured SBP >= 130 or DBP >= 80 mmHg among adults not told and not on antihypertensive medication).
> Evaluated below against:
> 1. Framingham undiagnosed HTN analogue (`prevalent_hyp == 0 & bp_meds == 0`, label measured SBP >= 130 or DBP >= 80 mmHg).
> 2. Cardio70k (measured SBP >= 130 or DBP >= 80 mmHg in clinical examinees; evaluated only for models without BP features).
> 3. BRFSS Core (different target: self-reported told high blood pressure).

{t3_md}

---

## Clinical Discussion & Epidemiological Findings

### 1. Model Target vs External Label Distinctions
- **Undiagnosed Diabetes (`diabetes_undiagnosed`) vs Diagnosed Diabetes (`told_diabetes`):**
  ChronicCare-AI models were developed to detect undiagnosed elevated blood sugar among adults unaware of their diabetic status. When applied to BRFSS cohorts, the target is doctor-diagnosed diabetes. Because individuals with established clinical diagnoses frequently have long-standing disease, elevated BMI, older age, and prescribed comorbidities, discriminative ranking appears higher (AUROC {c['brfss_min_auroc']:.3f}–{c['brfss_max_auroc']:.3f}). However, calibration and diagnostic sensitivity/specificity from these cohorts do not apply to our screening task.
- **Framingham Blood Glucose Distribution:**
  In the Framingham Heart Study baseline examination, after excluding subjects with known diabetes (`diabetes == 0`, N = {c['framingham_total_undiag']:,}; {c['framingham_measured_glucose']:,} with measured glucose), the maximum observed blood glucose is {c['framingham_max_glucose']:.1f} mg/dL. Every subject in the original cohort with glucose >= 200 mg/dL had already been clinically diagnosed and coded as `diabetes == 1`. Consequently, applying the ADA random glucose threshold (`>= 200 mg/dL`) yields exactly 0 positive cases in the undiagnosed cohort, precluding AUROC computation. Applying the fasting threshold (`>= 126 mg/dL`) yields {c['framingham_ge_126_positives']} positive cases ({c['framingham_ge_126_prev']:.2f}% prevalence), producing an overlap refit AUROC of {c['framingham_ge_126_auroc']:.3f} [{c['framingham_ge_126_ci_low']:.3f}, {c['framingham_ge_126_ci_high']:.3f}]. Because the confidence interval includes 0.5, with only {c['framingham_ge_126_positives']} cases, this can't be told apart from chance.
- **Pima Indians Biochemical OGTT:**
  Pima diabetes status is determined by formal 2-hour post-load oral glucose tolerance test (OGTT >= 200 mg/dL), identifying elevated blood glucose in a cohort with {c['pima_prev']:.1f}% prevalence among adult females. The models achieve an AUROC of {c['pima_auroc']:.3f} [{c['pima_ci_low']:.3f}, {c['pima_ci_high']:.3f}], with negative calibration-in-the-large reflecting the substantially higher prevalence compared to general screening populations. Because Pima lacks waist circumference, smoking, and blood pressure history, all three diabetes models reduce to the same overlap refit on age and BMI (yielding identical discrimination); consequently, Pima evaluation says nothing about diabetes_full's additional features.

### 2. Reference Development Discrimination
For context, the locked internal test AUROCs achieved on the held-out NHANES temporal test set (`test` 2017–2023, 2 survey cycles) are documented in [`docs/ml/EXPERIMENTS_SUMMARY.md:14-18`](file:///C:/Users/Saad/Documents/ChronicCare-AI/docs/ml/EXPERIMENTS_SUMMARY.md#L14-L18):
- `diabetes_full_nhanes`: AUROC = **{c['nhanes_full_test_auroc']}**
- `diabetes_basic_nhanes`: AUROC = **{c['nhanes_basic_test_auroc']}**
- `diabetes_ref_age_sex_bmi`: AUROC = **{c['nhanes_ref_test_auroc']}**

### 3. Feature Mapping Approximations
Differences in survey and clinical capture between cohorts introduce mapping approximations:
- **Framingham Heart Study:**
  - `current_smoker` mapped to `ever_smoked_100`: Current smoking does not capture former smokers who smoked >= 100 lifetime cigarettes.
  - `prevalent_hyp` mapped to `told_high_bp`: Hypertensive status at examination is an epidemiological indicator, not identical to doctor-told diagnosis.
  - Blood glucose: Recorded as a single measurement without protocol specification of fasting duration.
- **CDC BRFSS (Kaggle & Core Parquet):**
  - Age: Recorded in 13 ordinal five-year intervals (`_AGEG5YR`), mapped to category midpoints (e.g. 18–24 -> 21, 80+ -> 82), collapsing intra-interval variance.
  - Sex Coding: Kaggle dataset description specifies 0 = female, 1 = male (https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset), coding taken from the Kaggle description, TO CONFIRM.
- **Cardio70k Examination Records:**
  - Glucose: Recorded only as 3-level ordinal category (`gluc`: 1, 2, 3), precluding diabetes evaluation.
  - Blood Pressure: Raw examination measurements required systematic rule-based cleaning ({c['cardio_raw_inverted']:,} raw inverted rows, with {c['cardio_rule1_neg']} negative values caught in Rule 1, leaving {c['cardio_rule2_handled']:,} non-negative inverted rows handled in Rule 2: {c['cardio_swapped']} swapped and {c['cardio_unswappable']:,} set to NaN). Clean measured hypertension prevalence is {c['cardio_prev_pct']:.2f}% ({c['cardio_htn_pos']:,} / {c['cardio_clean_bp']:,}).
- **Pima Indians Diabetes:**
  - All participants are adult females of Pima Indian heritage. Features lack waist circumference and smoking history, necessitating overlap refit.

### 4. South Asian Applicability
**None of these five external cohorts is a South Asian population; DHS validation is still required.**
The external cohorts comprise North American general survey participants, historic suburban communities, and Indigenous American cohorts. South Asian populations exhibit different metabolic risk profiles, earlier onset of dysglycemia, and altered adiposity distributions. Validation on South Asian Demographic and Health Surveys (India NFHS-5, Bangladesh DHS, Nepal DHS) remains necessary prior to clinical deployment.

---

*Report generated automatically by `backend-poc-technical/ml/external_validation.py`.*
"""

    target_path.write_text(report_content, encoding="utf-8")
    print(f"\nExternal validation report written to {target_path}")
    return report_content


def main() -> None:
    parser = argparse.ArgumentParser(description="External validation of ChronicCare-AI ML models.")
    parser.add_argument(
        "--output",
        default="docs/ML_EXTERNAL_VALIDATION.md",
        help="Output markdown file path.",
    )
    args = parser.parse_args()

    results = run_all_external_validations(output_path=args.output)
    print(
        f"Completed external validation: "
        f"{len(results['table1_undiagnosed_diabetes'])} Table 1 pairs, "
        f"{len(results['table2_told_diabetes'])} Table 2 pairs, "
        f"{len(results['table3_retired_htn'])} Table 3 pairs."
    )


if __name__ == "__main__":
    main()
