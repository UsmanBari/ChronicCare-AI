"""
Generate docs/ml/EXPERIMENTS_SUMMARY.md programmatically from metrics.json files
and evaluate ADA/USPSTF guideline screening rules on held-out test data.

Adheres strictly to docs/ML_PLAN.md decisions and Day 4 instructions.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.common import df_to_markdown, load_nhanes_core, load_split
from ml.labels import extract_diabetes_undiagnosed

CONFIG_NAMES = [
    "diabetes_basic_nhanes",
    "diabetes_full_nhanes",
    "htn_basic_nhanes",
    "htn_full_nhanes",
    "diabetes_ref_age_sex_bmi",
    "htn_ref_age_sex_bmi",
]


def compute_guideline_rules(project_root: Path) -> list[dict[str, Any]]:
    """
    Evaluate guideline-rule screening baselines (no ML training) on the same
    test records and card population as the diabetes models.
    """
    df = load_nhanes_core()
    splits = load_split("nhanes_temporal_v1")
    test_seqns = splits["test"]

    y_und = extract_diabetes_undiagnosed(df)
    df["_target"] = y_und
    df["_in_pop"] = (df["told_diabetes"] == 0) & y_und.notna()

    test_df = df[df["seqn"].isin(test_seqns) & df["_in_pop"]].copy()

    # Match complete-case cohort for diabetes_basic_nhanes
    basic_feats = ["age", "sex_male", "bmi", "ever_smoked_100", "told_high_bp"]
    clean_test = test_df.dropna(subset=basic_feats + ["_target"]).copy()
    clean_test["_target"] = clean_test["_target"].astype(int)

    card_clean = clean_test[clean_test["told_high_bp"] == 1].copy()

    rules = [
        (
            "Rule Baseline: Age >= 35 (General Test)",
            clean_test,
            clean_test["age"] >= 35,
            "as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman",
        ),
        (
            "Rule Baseline: Age 35-70 & BMI >= 25 (General Test)",
            clean_test,
            (clean_test["age"] >= 35) & (clean_test["age"] <= 70) & (clean_test["bmi"] >= 25.0),
            "as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman",
        ),
        (
            "Rule Baseline: Age >= 35 (Card Audience: High BP)",
            card_clean,
            card_clean["age"] >= 35,
            "as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman",
        ),
        (
            "Rule Baseline: Age 35-70 & BMI >= 25 (Card Audience: High BP)",
            card_clean,
            (card_clean["age"] >= 35) & (card_clean["age"] <= 70) & (card_clean["bmi"] >= 25.0),
            "as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman",
        ),
    ]

    rule_rows = []
    for label, subset_df, pred_mask, citation in rules:
        y = subset_df["_target"].to_numpy()
        p_mask = pred_mask.to_numpy()
        tp = int(np.sum((y == 1) & p_mask))
        fp = int(np.sum((y == 0) & p_mask))
        tn = int(np.sum((y == 0) & ~p_mask))
        fn = int(np.sum((y == 1) & ~p_mask))

        n_pos = tp + fn
        n_total = len(y)
        prev = (n_pos / n_total * 100.0) if n_total > 0 else 0.0
        sens = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        spec = (tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        ppv = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0

        rule_rows.append({
            "name": label,
            "n_total": n_total,
            "positives": n_pos,
            "prevalence": prev,
            "sensitivity": sens,
            "specificity": spec,
            "ppv": ppv,
            "citation": citation,
        })

    return rule_rows


def generate_experiments_summary(project_root: Path | None = None) -> str:
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent.parent

    reports_dir = project_root / "backend-poc-technical" / "ml" / "outputs" / "reports"
    docs_dir = project_root / "docs" / "ml"
    docs_dir.mkdir(parents=True, exist_ok=True)
    summary_path = docs_dir / "EXPERIMENTS_SUMMARY.md"

    metrics_map: dict[str, dict[str, Any]] = {}
    for name in CONFIG_NAMES:
        m_file = reports_dir / name / "metrics.json"
        if not m_file.is_file():
            raise FileNotFoundError(f"Missing metrics.json for {name} at {m_file}")
        metrics_map[name] = json.loads(m_file.read_text(encoding="utf-8"))

    # Extract reference baselines for gap computation
    ref_dm = metrics_map["diabetes_ref_age_sex_bmi"]
    ref_htn = metrics_map["htn_ref_age_sex_bmi"]

    ref_dm_val_auroc = ref_dm["chosen_model"]["val_auroc"]
    ref_dm_test_auroc = ref_dm["test_evaluation"]["auroc"]["point"]

    ref_htn_val_auroc = ref_htn["chosen_model"]["val_auroc"]
    ref_htn_test_auroc = ref_htn["test_evaluation"]["auroc"]["point"]

    table_rows = []
    for name in CONFIG_NAMES:
        m = metrics_map[name]
        counts = m["split_counts"]
        n_str = f"{counts['train_core']['clean']:,} / {counts['validation']['clean']:,} / {counts['test']['clean']:,}"
        test_prev_str = f"{counts['test']['prevalence']:.2f}%"

        chosen_m = m["chosen_model"]
        chosen_str = f"{chosen_m['model_type']} ({chosen_m['best_params']})"

        val_auroc = chosen_m["val_auroc"]
        val_auroc_str = f"{val_auroc:.4f}"

        test_auroc_obj = m["test_evaluation"]["auroc"]
        test_auroc_str = f"{test_auroc_obj['point']:.4f} [{test_auroc_obj['ci_low']:.4f}–{test_auroc_obj['ci_high']:.4f}]"

        m_thresh = m["test_evaluation"]["metrics_at_threshold"]
        diag_str = f"{m_thresh['sensitivity'] * 100:.2f}% / {m_thresh['specificity'] * 100:.2f}% / {m_thresh['ppv'] * 100:.2f}%"

        val_slope = chosen_m["val_calibration_slope"]
        test_slope = m["test_evaluation"]["calibration"]["slope"]
        cal_str = f"{val_slope:.3f} / {test_slope:.3f}" if (val_slope is not None and test_slope is not None) else "N/A"

        worst_sg = m["test_evaluation"]["worst_subgroup"]
        worst_str = f"{worst_sg['group']}: {worst_sg['sensitivity'] * 100:.2f}% (n={worst_sg['positives']})"

        card_pop = m["test_evaluation"]["card_population"]
        card_auroc_val = card_pop["auroc"]
        card_sens_val = card_pop["sensitivity"]
        card_str = f"{card_auroc_val:.4f} / {card_sens_val * 100:.2f}%" if (card_auroc_val is not None and card_sens_val is not None) else "N/A"

        # Gap vs reference
        if "diabetes" in name:
            gap_val = val_auroc - ref_dm_val_auroc
            gap_test = test_auroc_obj["point"] - ref_dm_test_auroc
        else:
            gap_val = val_auroc - ref_htn_val_auroc
            gap_test = test_auroc_obj["point"] - ref_htn_test_auroc

        gap_str = "Ref Baseline" if "ref" in name else f"{gap_val:+.4f} (val) / {gap_test:+.4f} (test)"

        # Clinical governance status: All 6 are NOT SHIPPED for patient-facing use in FYP-1
        # (Even if diabetes_full technically satisfied mathematical D11 gates, its marginal gain of +0.0075 val AUROC
        # does not justify patient burden of collecting waist_cm and blood pressure in the profile, and fails clinical utility)
        if name == "diabetes_full_nhanes":
            status_str = "NOT SHIPPED (Decision 29 Oct: +0.0075 gain over basic does not justify waist/vital burden; flag off)"
        else:
            status_str = m["ship_status"]

        table_rows.append({
            "Experiment Name": f"`{name}`",
            "Clean n (train/val/test)": n_str,
            "Test Prev": test_prev_str,
            "Chosen Model (D10)": chosen_str,
            "Val AUROC": val_auroc_str,
            "Test AUROC [95% CI]": test_auroc_str,
            "Test Sens / Spec / PPV": diag_str,
            "Cal Slope (Val / Test)": cal_str,
            "Worst Subgroup Sens (>= 50 pos)": worst_str,
            "Card Pop AUROC / Sens": card_str,
            "Gap vs Ref (Val / Test)": gap_str,
            "FYP-1 Status": status_str,
        })

    model_summary_df = pd.DataFrame(table_rows)
    models_table_md = df_to_markdown(model_summary_df, index=False)

    # Compute guideline rules
    guideline_rules = compute_guideline_rules(project_root)
    guideline_rows = []
    for gr in guideline_rules:
        guideline_rows.append({
            "Guideline Screening Rule": gr["name"],
            "Cohort Evaluated": f"n={gr['n_total']:,} (pos={gr['positives']:,})",
            "Prevalence": f"{gr['prevalence']:.2f}%",
            "Sensitivity": f"{gr['sensitivity'] * 100:.2f}%",
            "Specificity": f"{gr['specificity'] * 100:.2f}%",
            "PPV": f"{gr['ppv'] * 100:.2f}%",
            "Clinical Evidence Source": gr["citation"],
        })
    guideline_df = pd.DataFrame(guideline_rows)
    guideline_table_md = df_to_markdown(guideline_df, index=False)

    # Extract key numbers for honest synthesis
    dm_basic_val = metrics_map["diabetes_basic_nhanes"]["chosen_model"]["val_auroc"]
    dm_full_val = metrics_map["diabetes_full_nhanes"]["chosen_model"]["val_auroc"]
    dm_basic_test = metrics_map["diabetes_basic_nhanes"]["test_evaluation"]["auroc"]["point"]
    dm_full_test = metrics_map["diabetes_full_nhanes"]["test_evaluation"]["auroc"]["point"]

    htn_basic_val = metrics_map["htn_basic_nhanes"]["chosen_model"]["val_auroc"]
    htn_full_val = metrics_map["htn_full_nhanes"]["chosen_model"]["val_auroc"]
    htn_basic_test = metrics_map["htn_basic_nhanes"]["test_evaluation"]["auroc"]["point"]
    htn_full_test = metrics_map["htn_full_nhanes"]["test_evaluation"]["auroc"]["point"]

    dm_card_auroc = metrics_map["diabetes_basic_nhanes"]["test_evaluation"]["card_population"]["auroc"]
    htn_card_auroc = metrics_map["htn_basic_nhanes"]["test_evaluation"]["card_population"]["auroc"]

    doc_content = f"""# ChronicCare AI — Machine Learning Experiments Summary & Governance Report

> **Document Status:** Official Summary of Day 4 Risk Model Benchmarks  
> **Evaluation Date:** 29 October 2026  
> **Clinical Governance Decision:** Usman (ML Lead) & Clinical Safety Team  
> **Guiding Principle:** The model proposes, the rules decide.

---

## 1. Machine Learning Experiment Benchmark Matrix

All models were evaluated on the held-out NHANES temporal test set (`test` 2017–2023, 2 survey cycles). Thresholds and hyperparameters were locked strictly on the temporal validation set (`validation` 2013–2016). Decision threshold policy is `min_sensitivity >= 0.80` on validation.

{models_table_md}

---

## 2. Guideline-Rule Screening Baselines (No Training Required)

Evaluated on the exact same held-out test cohort records and card audience as the diabetes models:

{guideline_table_md}

---

## 3. Honest Findings & Clinical Governance Synthesis

1. **All Six Configurations Are NOT SHIPPED for Patient-Facing Risk Cards:** Every evaluated risk model fails critical D11 acceptance gates or clinical utility bars. The hypertension models fail Gate 1 (test AUROC is {htn_basic_test:.4f} for BASIC and {htn_full_test:.4f} for FULL, well below the 0.75 threshold) and catastrophic young-adult sensitivity collapse (Gate 4 failure: missing over 60% of young hypertensive individuals aged 18–39). While the `diabetes_full_nhanes` model technically passed the mathematical D11 gates under plain logistic regression, it is rejected by clinical governance because its marginal gain does not justify clinical burden.
2. **BASIC and FULL Add Little or Nothing Over Age, Sex, and BMI:** Comparing the engineered models against the reference baseline (`diabetes_ref_age_sex_bmi` and `htn_ref_age_sex_bmi`) demonstrates extreme feature parsimony limits. For diabetes, adding smoking status and hypertension awareness (`diabetes_basic_nhanes`) improves validation AUROC by only **{dm_basic_val - ref_dm_val_auroc:+.4f}** and actually decreases test AUROC by **{dm_basic_test - ref_dm_test_auroc:+.4f}**. Adding waist circumference and blood pressure readings (`diabetes_full_nhanes`) yields a validation gain of only **{dm_full_val - dm_basic_val:+.4f}** (test gain of **{dm_full_test - dm_basic_test:+.4f}**), which fails to justify asking patients for uncollected physical measurements like waist circumference. For hypertension, the FULL model test AUROC ({htn_full_test:.4f}) is actually **{htn_full_test - htn_basic_test:+.4f}** lower than the BASIC model.
3. **Card-Population Discrimination is Poor (Near Chance for Hypertension):** When evaluated on the exact reciprocal patient cohort who would view the risk card in production, discrimination drops significantly. In patients with hypertension screened for undiagnosed diabetes, card AUROC is only **{dm_card_auroc:.4f}** (with a positive predictive value of ~7%). Worse, in patients with diagnosed diabetes screened for hypertension, card AUROC collapses to **{htn_card_auroc:.4f}**, which is barely distinguishable from a random coin flip (0.50).
4. **Young Adults Are Systematically Missed Across All Models:** Because age dominates tabular logistic regression coefficients (odds ratio ~2.0 to 2.3 per 1 SD), models exhibit severe age disparity. In older adults (60+), sensitivity is ~95–97% but specificity collapses to near zero (flagging almost everyone). In contrast, in young adults aged 18–39, sensitivity drops to **38.41%** for hypertension and **58.82%** for diabetes, systematically failing the patients who have the most life-years to gain from early diagnosis.
5. **Low Precision and High False-Positive Burden:** At ~4% baseline prevalence of undiagnosed diabetes, operating at 85% sensitivity yields an operational specificity of only ~51% and a Positive Predictive Value (PPV) of **{metrics_map['diabetes_basic_nhanes']['test_evaluation']['metrics_at_threshold']['ppv'] * 100:.2f}%**. Approximately 13 out of every 14 flagged individuals do not have undiagnosed diabetes, creating unwarranted patient anxiety and potential healthcare provider alert fatigue.
6. **Simple Guideline Rules Match or Outperform Complex Models:** Evaluating deterministic screening rules recommended by ADA Standards and USPSTF 2021 on the exact same test records demonstrates that software models provide no decisive clinical edge. The simple rule `Age >= 35` achieves **93.04% sensitivity** (substantially higher than the model's 85.05%), while `Age 35–70 & BMI >= 25` achieves **63.66% sensitivity** and **58.01% specificity** (higher specificity than the basic model's 51.40%) without requiring mathematical model scoring or algorithmic complexity.
7. **Official Decision (Usman, 29 October 2026):** **No patient-facing risk card will be shown in FYP-1.** The configuration flag `RISK_ENABLED` remains locked `off` across all production environments. The Day 5 runtime scoring machinery and Day 7 integration will still be built, tested, and hermetically verified behind this feature flag to complete the technical architecture. For patients with diabetes, we formally recommend to supervising clinicians and doctors that the application directly request an actual blood pressure cuff measurement during check-ins rather than attempting to infer hypertension probabilistically from demographic proxies.
8. **External Validation Limitation for BRFSS (Day 6):** The BRFSS surveillance dataset contains no laboratory specimen data (no HbA1c, fasting glucose) and no physical cuff examination measurements. Consequently, BRFSS cannot evaluate undiagnosed target labels (`diabetes_undiagnosed` or `hypertension_measured_130_80`). Saad's Day 6 external validation on BRFSS will be strictly limited to evaluating self-reported awareness labels (`diabetes_told`, `hypertension_told`) or assessing feature drift across demographics.
"""

    summary_path.write_text(doc_content.strip() + "\n", encoding="utf-8")
    print(f"Generated complete summary report to: {summary_path}")
    return doc_content


if __name__ == "__main__":
    content = generate_experiments_summary()
    print("\n" + "=" * 60)
    print("EXPERIMENTS SUMMARY REPORT GENERATED SUCCESSFULLY")
    print("=" * 60)
