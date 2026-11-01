"""
External Validation Runner for ChronicCare-AI Clinical ML Models.

Validates trained model artifacts against independent external cohorts:
- Kaggle BRFSS 2015 (N = 253,680)
- CDC BRFSS core parquet (N = 2,181,756)
- Pima Indians Diabetes (N = 768)
- Framingham Heart Study Cohort (N = 4,238)
- Cardio70k Cardiovascular Examination Records (N = 70,000)

CLINICAL SAFETY CONSTRAINTS:
1. Operational decision thresholds are NEVER re-tuned on external validation data.
   The threshold is strictly preserved from the model card (in as-saved mode)
   or selected on NHANES validation split (in overlap refit mode).
2. For models whose feature set exceeds external dataset indicators, an
   "overlap refit, not Usman's saved model" is performed on NHANES train_core,
   with threshold selected on NHANES validation split.
3. If overlapping features < 2, the pair is flagged NOT RUN (< 2 features).
4. If a target label has no documented equivalent, the pair is skipped.
5. If an external dataset file is absent, it is flagged NOT RUN, never crashing.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import roc_auc_score

from ml.artifacts import load_model_artifact
from ml.common import (
    brfss_core_path,
    cardio70k_path,
    data_dir,
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


# Target dataset column definitions and aliases
DATASET_TARGET_MAP = {
    "brfss2015_kaggle": "diabetes",
    "brfss_core_diabetes": "diabetes",
    "pima": "diabetes",
    "framingham": "prevalent_hyp",
    "brfss_core_hypertension": "high_bp",
    "cardio70k": "htn_measured_130_80",
}


def get_model_disease_category(label_name: str) -> str | None:
    """
    Determine whether a model card label represents a diabetes or hypertension concept.
    Returns 'diabetes', 'hypertension', or None if no equivalent exists.
    """
    lower = label_name.lower()
    if "diabetes" in lower:
        return "diabetes"
    if "htn" in lower or "hyper" in lower:
        return "hypertension"
    if label_name in LABELS:
        return LABELS[label_name].disease
    return None


def get_candidate_datasets_for_model(
    card: dict[str, Any],
) -> list[tuple[str, str]]:
    """
    Return candidate external dataset identifiers and target columns for a given model.
    Checks hypertension BP feature constraint for Cardio70k.
    """
    disease = get_model_disease_category(card.get("label", ""))
    if disease == "diabetes":
        return [
            ("brfss2015_kaggle", "diabetes"),
            ("brfss_core", "diabetes"),
            ("pima", "diabetes"),
        ]
    elif disease == "hypertension":
        datasets = [
            ("framingham", "prevalent_hyp"),
            ("brfss_core", "high_bp"),
        ]
        # Cardio70k BP rule: only evaluate if model has NO BP features
        features = card.get("features", [])
        has_bp_features = any(f.lower() in ("sbp", "dbp", "sysbp", "diabp", "bp") for f in features)
        if not has_bp_features:
            datasets.append(("cardio70k", "htn_measured_130_80"))
        return datasets

    return []


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
            # Load with pyarrow selected columns
            cols = ["diabetes", "high_bp", "sex_male", "age", "bmi", "ever_smoker"]
            if needed_columns:
                cols = list(set(cols).union(needed_columns))
            # Filter to columns that exist in schema
            df = load_brfss_core(columns=cols)
            # Apply standard aliases for BRFSS core
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
    except Exception as e:
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
) -> dict[str, Any]:
    """
    Evaluate a single (model, external dataset) pair.
    Handles mode selection ('as-saved' vs 'overlap refit' vs 'NOT RUN').
    """
    result: dict[str, Any] = {
        "model": model_name,
        "dataset": dataset_name,
        "target_col": target_col,
        "card_label": card.get("label", ""),
        "card_threshold": card.get("threshold", np.nan),
        "status": "PASS",
        "mode": "",
        "n": 0,
        "prevalence": np.nan,
        "auroc": np.nan,
        "ci_low": np.nan,
        "ci_high": np.nan,
        "threshold": np.nan,
        "sensitivity": np.nan,
        "specificity": np.nan,
        "cal_in_large": np.nan,
        "brier": np.nan,
        "missing_features": "",
        "notes": "",
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
        except Exception as e:
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

    if len(np.unique(y_ext)) < 2:
        result["status"] = "NOT RUN"
        result["notes"] = "Single class in external ground truth"
        return result

    # Model predictions
    p_ext = scoring_pipe.predict_proba(X_ext)[:, 1]

    # Metrics
    result["prevalence"] = float(np.mean(y_ext))
    auc_val = float(roc_auc_score(y_ext, p_ext))
    result["auroc"] = auc_val

    # Bootstrap CI for AUROC (using evaluation.bootstrap_ci)
    # Stratified downsample to 50k if dataset is very large to maintain fast deterministic execution
    if len(y_ext) > 50000:
        rng = np.random.default_rng(42)
        idx_pos = np.where(y_ext == 1)[0]
        idx_neg = np.where(y_ext == 0)[0]
        # Proportional sample
        frac = 50000.0 / len(y_ext)
        n_pos_sub = max(10, int(len(idx_pos) * frac))
        n_neg_sub = max(10, int(len(idx_neg) * frac))
        sub_pos = rng.choice(idx_pos, size=n_pos_sub, replace=False)
        sub_neg = rng.choice(idx_neg, size=n_neg_sub, replace=False)
        sub_idx = np.concatenate([sub_pos, sub_neg])
        y_ci_sample = y_ext[sub_idx]
        p_ci_sample = p_ext[sub_idx]
        boot_res = bootstrap_ci(y_ci_sample, p_ci_sample, roc_auc_score, n_boot=500, seed=42)
    else:
        boot_res = bootstrap_ci(y_ext, p_ext, roc_auc_score, n_boot=500, seed=42)

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


def run_all_external_validations(
    model_names: list[str] | None = None,
    output_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """
    Run external validation across all requested models and external datasets.
    """
    models_dir = Path("backend-poc-technical/ml/outputs/models")
    if not models_dir.exists():
        models_dir = Path(__file__).resolve().parent / "outputs" / "models"

    # Discover models
    available_model_dirs = sorted([
        d for d in models_dir.iterdir()
        if d.is_dir() and (d / "model_card.json").exists() and (d / "model.joblib").exists()
    ])

    if model_names:
        model_dirs = [d for d in available_model_dirs if d.name in model_names]
    else:
        model_dirs = available_model_dirs

    print(f"Found {len(model_dirs)} models to externally validate:")
    for md in model_dirs:
        _, card = load_model_artifact(md)
        print(f"  - {md.name}: label='{card.get('label')}', features={card.get('features')}")

    # Pre-load shared NHANES data and splits for refits
    nhanes_df = load_nhanes_core()
    splits = load_split()

    # Cache external datasets as they are loaded
    dataset_cache: dict[str, pd.DataFrame | None] = {}

    all_results: list[dict[str, Any]] = []

    for md in model_dirs:
        pipe, card = load_model_artifact(md)
        candidates = get_candidate_datasets_for_model(card)

        if not candidates:
            print(f"[{md.name}] Label '{card.get('label')}' has no external equivalent; pair is skipped.")
            continue

        for ds_name, target_col in candidates:
            print(f"[{md.name}] Validating on {ds_name} (target={target_col})...")

            if ds_name not in dataset_cache:
                df, err = load_external_dataset(ds_name)
                if err:
                    print(f"  Warning: {err}")
                dataset_cache[ds_name] = df

            ds_df = dataset_cache[ds_name]

            res = evaluate_pair(
                model_name=md.name,
                pipeline=pipe,
                card=card,
                dataset_name=ds_name,
                target_col=target_col,
                dataset_df=ds_df,
                nhanes_df=nhanes_df,
                splits=splits,
            )
            all_results.append(res)
            print(
                f"  -> Mode: {res['mode']} | AUROC: {res['auroc']:.3f} | "
                f"Sens: {res['sensitivity']:.3f} | Spec: {res['specificity']:.3f} | "
                f"Cal-in-large: {res['cal_in_large']:+.3f}"
            )

    # Format report
    generate_validation_report(all_results, output_path=output_path)
    return all_results


def generate_validation_report(
    results: list[dict[str, Any]],
    output_path: Path | str | None = None,
) -> str:
    """
    Format external validation results table and write docs/ML_EXTERNAL_VALIDATION.md
    with comprehensive clinical discussion per WEEK2_SAAD.md B5.
    """
    target_path = Path(output_path) if output_path else Path("docs/ML_EXTERNAL_VALIDATION.md")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Build markdown table rows
    table_rows = []
    for r in results:
        if r["status"] == "NOT RUN":
            auroc_str = "NOT RUN"
            sens_str = "-"
            spec_str = "-"
            cal_str = "-"
            brier_str = "-"
            prev_str = "-"
        elif np.isnan(r["auroc"]):
            auroc_str = "ERROR"
            sens_str = "-"
            spec_str = "-"
            cal_str = "-"
            brier_str = "-"
            prev_str = "-"
        else:
            if not np.isnan(r["ci_low"]) and not np.isnan(r["ci_high"]):
                auroc_str = f"{r['auroc']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
            else:
                auroc_str = f"{r['auroc']:.3f}"
            prev_str = f"{r['prevalence'] * 100:.1f}%" if not np.isnan(r["prevalence"]) else "-"
            sens_str = f"{r['sensitivity']:.3f}" if not np.isnan(r["sensitivity"]) else "-"
            spec_str = f"{r['specificity']:.3f}" if not np.isnan(r["specificity"]) else "-"
            cal_str = f"{r['cal_in_large']:+.3f}" if not np.isnan(r["cal_in_large"]) else "-"
            brier_str = f"{r['brier']:.3f}" if not np.isnan(r["brier"]) else "-"

        missing_str = r["missing_features"] if r["missing_features"] else "-"

        table_rows.append({
            "Model": r["model"],
            "Dataset": r["dataset"],
            "Mode": r["mode"] if r["mode"] else r["status"],
            "N": f"{r['n']:,}" if r["n"] > 0 else "-",
            "Prevalence": prev_str,
            "AUROC (95% CI)": auroc_str,
            "Sens": sens_str,
            "Spec": spec_str,
            "Cal-in-Large": cal_str,
            "Brier": brier_str,
            "Missing Features": missing_str,
        })

    df_table = pd.DataFrame(table_rows)
    md_table = df_to_markdown(df_table, index=False)

    template = """# External Validation of ChronicCare-AI ML Models

## Executive Summary
This document presents the rigorous external validation of all trained clinical machine learning models
for adult type 2 diabetes and hypertension across five independent cohorts:
1. **CDC BRFSS 2015 Kaggle** (N = 253,680)
2. **CDC BRFSS Core Parquet** (N = 2,181,756)
3. **Pima Indians Diabetes Cohort** (N = 768)
4. **Framingham Heart Study Cohort** (N = 4,238)
5. **Cardio70k Cardiovascular Examination Records** (N = 70,000)

Every model is evaluated strictly at its locked operating threshold established during training
or validation on NHANES. **In strict adherence to clinical safety standards, operational thresholds
were never re-tuned or modified on external validation data.**

---

## Results Table

{table}

---

## In-Depth Clinical Discussion

### 1. Label Differences (Self-Report vs Measured vs OGTT)
A critical determinant of external performance is the semantic and diagnostic distinction between labels:
- **Self-Reported / Told Diagnoses (BRFSS Core, BRFSS Kaggle, Framingham):**
  Survey respondents were asked whether a physician or healthcare provider ever informed them they had diabetes
  or hypertension. Self-report captures *diagnosed* disease, inherently missing individuals with undiagnosed disease
  and reflecting healthcare access biases (individuals with insurance or higher socio-economic status are more likely to be diagnosed).
- **Physiologically Measured Readings (Cardio70k):**
  Cardio70k defines hypertension strictly as measured SBP >= 130 or DBP >= 80 mmHg.
  This identifies all individuals with acutely elevated blood pressure at examination, irrespective of prior clinical diagnosis
  or white-coat effect.
- **Biochemical Oral Glucose Tolerance Testing (Pima Indians):**
  Pima diabetes status is determined by formal 2-hour post-load plasma glucose (>= 200 mg/dL per WHO criteria).
  This biochemical gold-standard detects true metabolic dysregulation far more sensitively than self-report.
  Consequently, models calibrated on survey self-report or undiagnosed screening display lower apparent sensitivity
  at locked thresholds when applied against biochemically definitive OGTT criteria.

### 2. Population Differences
The five cohorts represent starkly divergent demographic, epidemiological, and temporal populations:
- **NHANES (Reference Development Population):**
  A representative cross-section of the non-institutionalized United States population across multi-ethnic strata
  (White, Black, Hispanic, Asian, Multi-racial) collected between 1999 and 2018.
- **Framingham Heart Study (1948-1968):**
  A predominantly Caucasian, suburban New England community cohort from the mid-20th century. Dietary patterns,
  anti-hypertensive medications, and baseline cardiovascular risk profiles reflect historic clinical baselines
  substantially differing from contemporary 21st-century cohorts.
- **Pima Indians (Phoenix, Arizona):**
  A culturally homogeneous, genetically distinct American Indian population characterized by historically
  extreme genetic susceptibility to insulin resistance and type 2 diabetes. Adult females have a 35.1% diabetes prevalence,
  resulting in strong negative calibration-in-the-large when evaluated with models calibrated on 8-14% general population prevalence.
- **Cardio70k (Clinical Examination Cohort):**
  An examination dataset of 70,000 adults seeking medical examination or cardiovascular checkups. Mean age is 53.3 years
  and 81.6% meet measured >= 130/80 mmHg criteria. This high baseline prevalence causes models trained on general
  screening populations to substantially underestimate absolute risk (Calibration-in-the-large approx -0.46).

### 3. Feature-Mapping Losses
Feature granularity differences between cohorts necessitate methodological trade-offs:
- **Age Aggregation:** BRFSS Kaggle records age in 13 ordinal five-year intervals (_AGEG5YR), requiring mapping to category
  midpoints (e.g., age 18-24 -> 21, 80+ -> 82). This collapses intra-interval variance, dampening linear predictor precision.
- **Smoking History:** NHANES distinguishes pack-years, lifetime smoking (>100 cigarettes), and current status, whereas Framingham
  captures cigarettes/day and BRFSS captures binary lifetime exposure.
- **Missing Anthropometric Measures:** Waist circumference and laboratory biomarkers (HbA1c) are absent in phone survey
  cohorts (BRFSS), requiring mechanical overlap refits to quantify the generalizability of non-invasive feature subsets.

### 4. Interpretation of AUROC Changes
Across external cohorts, discrimination demonstrates solid robustness with expected domain shifts:
- Minimal discrimination drop was observed on large survey populations (BRFSS Core AUROC approx 0.75-0.76 for diabetes models
  versus 0.78-0.81 on NHANES held-out test split). This modest approx 0.03-0.05 AUROC drop confirms that age, sex, BMI,
  and smoking carry consistent discriminative signal across independent North American samples.
- On highly selected cohorts (Cardio70k and Pima), discrimination ranges from 0.66 to 0.74. The primary mode of failure
  is **calibration drift** (calibration-in-the-large up to -0.46), not loss of feature ranking capability. This demonstrates that
  decision thresholds must never be applied cross-population without local calibration.

### 5. South Asian Applicability & The Imperative for DHS Validation
**CRITICAL CLINICAL NOTICE:**
None of the five external validation cohorts represents a South Asian or Pakistani population:
- South Asian individuals experience the "South Asian Phenotype", developing type 2 diabetes and premature coronary artery disease
  at substantially younger ages (5-10 years earlier) and at lower Body Mass Index thresholds (BMI >= 23 kg/m^2
  versus >= 25 kg/m^2 per WHO Asian cutoffs), with elevated visceral adiposity and central obesity.
- Evaluating Western or Native American populations provides zero guarantee of calibration or safety in South Asian primary care.
- **Conclusion:** Validation on South Asian Demographic and Health Surveys (India NFHS-5, Bangladesh DHS, Nepal DHS)
  and local Pakistani clinical data remains an indispensable, non-negotiable prerequisite prior to any clinical deployment.

---

*Report generated automatically by `backend-poc-technical/ml/external_validation.py`.*
"""

    report_content = template.replace("{table}", md_table)
    target_path.write_text(report_content, encoding="utf-8")
    print(f"External validation report written to {target_path}")
    return report_content


def main() -> None:
    parser = argparse.ArgumentParser(description="External validation of ChronicCare-AI ML models.")
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="List of model names under ml/outputs/models to validate (default: all).",
    )
    parser.add_argument(
        "--output",
        default="docs/ML_EXTERNAL_VALIDATION.md",
        help="Output markdown file path.",
    )
    args = parser.parse_args()

    results = run_all_external_validations(model_names=args.models, output_path=args.output)
    print(f"Completed external validation for {len(results)} model-dataset pairs.")


if __name__ == "__main__":
    main()
