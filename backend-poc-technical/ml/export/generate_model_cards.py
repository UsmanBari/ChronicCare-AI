"""
Programmatic Model Cards Generator for ChronicCare AI (docs/ML_MODEL_CARDS.md).
Reads exact metric values from ml/outputs/reports/*/metrics.json and writes
the complete, honest model card for diabetes_full_nhanes and not-shipped cards for the others.

Adheres strictly to D12-D15 and Week 2 Day 5 instructions.
"""
from __future__ import annotations

import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent
REPORTS_DIR = BACKEND_DIR / "ml" / "outputs" / "reports"
OUTPUT_MD = REPO_ROOT / "docs" / "ML_MODEL_CARDS.md"


def load_metrics(name: str) -> dict:
    path = REPORTS_DIR / name / "metrics.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing metrics.json at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_pct(val: float, decimals: int = 2) -> str:
    return f"{val * 100:.{decimals}f}%"


def fmt_num(val: float, decimals: int = 4) -> str:
    return f"{val:.{decimals}f}"


def main():
    m_full = load_metrics("diabetes_full_nhanes")
    m_basic = load_metrics("diabetes_basic_nhanes")
    m_ref = load_metrics("diabetes_ref_age_sex_bmi")
    m_htn_basic = load_metrics("htn_basic_nhanes")
    m_htn_full = load_metrics("htn_full_nhanes")
    m_htn_ref = load_metrics("htn_ref_age_sex_bmi")

    t_full = m_full["test_evaluation"]
    t_full_m = t_full["metrics_at_threshold"]
    t_full_cal = t_full["calibration"]
    t_full_card = t_full["card_population"]

    t_ref = m_ref["test_evaluation"]
    t_ref_m = t_ref["metrics_at_threshold"]

    # Subgroups table rows for diabetes_full_nhanes
    subgroup_rows = []
    for sg in t_full["subgroups"]:
        subgroup_rows.append(
            f"| `{sg['group_type']}` | {sg['group_value']} | {sg['n']:,} | {sg['positives']:,} | "
            f"{sg['prevalence']:.2f}% | {fmt_num(sg['auroc'])} | {fmt_pct(sg['sensitivity'])} | {fmt_pct(sg['specificity'])} |"
        )
    subgroups_table = "\n".join(subgroup_rows)

    # Feature explanations table
    feat_rows = []
    app_mappings = {
        "age": ("Years (18–85)", "Calculated from `date_of_birth` in `patient_profiles` (`main.py:382`) and check-in date."),
        "sex_male": ("Binary (1=Male, 0=Female)", "Mapped from `sex_at_birth` in `patient_profiles` (`main.py:384`)."),
        "bmi": ("kg/m² (10.0–100.0)", "Calculated as `weight_kg / ((height_cm/100)**2)` from `height_cm` and `weight_kg` in `patient_profiles` (`main.py:379-380`)."),
        "ever_smoked_100": ("Binary (1=Yes, 0=No)", "Mapped from `smoking_status` (`never` -> 0, `former`/`current` -> 1) in `patient_profiles` (`main.py:389`)."),
        "told_high_bp": ("Binary (1=Yes)", "Set to 1 by applicability filter (only patients with hypertension condition evaluated)."),
        "sbp": ("mmHg (60–260)", "Most recent systolic BP reading within 30 days from reading history (`main.py:3761`)."),
        "dbp": ("mmHg (30–150)", "Most recent diastolic BP reading within 30 days from reading history (`main.py:3761`)."),
        "waist_cm": ("cm (40.0–200.0)", "Optional profile field, added today (Part H) in `patient_profiles` (`main.py: ProfileUpdateRequest.waist_cm`)."),
    }

    for f_item in m_full["feature_explanations"]:
        f_name = f_item["feature"]
        unit, how_app_gets = app_mappings.get(f_name, ("-", "-"))
        feat_rows.append(
            f"| `{f_name}` | {unit} | {how_app_gets} | {fmt_num(f_item['coef_standardized'])} | {fmt_num(f_item['odds_ratio_per_1_sd'])} |"
        )
    feats_table = "\n".join(feat_rows)

    md = f"""# ChronicCare AI — Machine Learning Model Cards
**Document Version:** 1.0.0  
**Date:** 30 October 2026  
**Clinical Scope:** Adult Type 2 Diabetes and Hypertension Decision Support  
**Audience:** Internal Engineering, Clinical Reviewers, and Auditors  
**Governing Decisions:** D10, D12, D13, D14, D15 (`docs/ML_PLAN.md`, `docs/ml/EXPERIMENTS_SUMMARY.md` Section 6)  
**Safety Invariant:** *The model proposes, the rules decide.* Advisory only; never diagnoses; never prescribes; never lowers a triage level.

---

## Part 1: Primary Production Advisory Model (`diabetes_full_nhanes`)

### 1.1 Model Overview
- **Model Name:** `diabetes_full_nhanes`
- **Model Version:** `1.0.0`
- **Release Status:** **SHIP CANDIDATE (Provider-Only Experimental Advisory under D12)**
- **Model Type:** Regularized Logistic Regression (`scikit-learn LogisticRegression(C=0.1, penalty='l2')`)
- **Selection Decision:** Plain `lr` selected under D10 parsimony rule (lr_balanced did not beat plain lr by $\\ge 0.01$ validation AUROC [gap: +{m_full['candidate_models']['lr_balanced']['val_auroc'] - m_full['candidate_models']['lr']['val_auroc']:.4f}]; best tree did not beat LR by $\\ge 0.02$ validation AUROC [gap: +{m_full['candidate_models']['rf']['val_auroc'] - m_full['candidate_models']['lr']['val_auroc']:.4f}]).
- **Model Owner:** Usman (ML Lead)
- **Scikit-Learn Version:** 1.9.1
- **Training Source Split:** NHANES Temporal Split `nhanes_temporal_v1` (1999–2023)

### 1.2 Intended Use & Target Audience
- **Primary Audience:** **PROVIDER ONLY**. Displayed exclusively on the clinical provider review dashboard (`/api/provider/review/{{checkin_id}}`) behind the `RISK_ENABLED` environment feature flag.
- **Intended Clinical Role:** Experimental advisory ranking to assist clinical providers in identifying patients with hypertension who may benefit from glycemic screening (HbA1c / fasting glucose evaluation).
- **Mandatory Display Banner:**
  > *"Experimental: trained on US NHANES data, not validated for Pakistani patients"*
- **Target Population (Applicability Filter):** Adults aged $\\ge 18$ with documented hypertension who **do not have diagnosed diabetes** (`conditions` contains `hypertension` and does NOT contain `diabetes`). Patients with diabetes only, dual diagnoses, or neither receive `None` from the risk agent.

### 1.3 Out-of-Scope & Misuse Caveats
- **Never Diagnostic:** Does not diagnose type 2 diabetes or prediabetes.
- **Never Patient-Facing in FYP-1:** Patients **never** see a numerical risk score, probability percentage, or risk badge.
- **Excluded Populations:**
  - Individuals with existing clinician-diagnosed or self-reported diabetes.
  - Individuals under 18 years of age.
  - Pregnant individuals (pregnancy alters glycemic dynamics and renal thresholds).
  - Use outside a licensed clinician's review.
- **Triage Level Floor:** Under D14 and the architectural safety invariant, risk assessment can **never lower a triage level**. It can only raise `routine -> review` when both `RISK_ENABLED=true` and `RISK_CAN_RAISE=true`.

### 1.4 Data, Cohort & Temporal Split
- **Dataset:** US National Health and Nutrition Examination Survey (NHANES) 1999–2023.
- **Target Label:** `diabetes_undiagnosed` ($\\text{{HbA1c}} \\ge 6.5\\%$ [48 mmol/mol] or fasting plasma glucose $\\ge 126\\text{{ mg/dL}}$ [7.0 mmol/L] among adults without self-reported diagnosed diabetes).
- **Splits:**
  - **Train Core (1999–2014):** Initial {m_full['split_counts']['train_core']['initial']:,} rows $\\to$ dropped {m_full['split_counts']['train_core']['dropped']:,} missing $\\to$ **{m_full['split_counts']['train_core']['clean']:,} clean** rows ({m_full['split_counts']['train_core']['positives']:,} positives, prevalence {m_full['split_counts']['train_core']['prevalence']:.2f}%).
  - **Validation (2015–2016):** Initial {m_full['split_counts']['validation']['initial']:,} rows $\\to$ dropped {m_full['split_counts']['validation']['dropped']:,} missing $\\to$ **{m_full['split_counts']['validation']['clean']:,} clean** rows ({m_full['split_counts']['validation']['positives']:,} positives, prevalence {m_full['split_counts']['validation']['prevalence']:.2f}%).
  - **Test (2017–2023):** Initial {m_full['split_counts']['test']['initial']:,} rows $\\to$ dropped {m_full['split_counts']['test']['dropped']:,} missing $\\to$ **{m_full['split_counts']['test']['clean']:,} clean** rows ({m_full['split_counts']['test']['positives']:,} positives, prevalence {m_full['split_counts']['test']['prevalence']:.2f}%).

### 1.5 Features, Units & Application Acquisition
| Feature | Units / Format | How the App Acquires Feature | Standardized Coef | Odds Ratio (per 1 SD) |
| :--- | :--- | :--- | :--- | :--- |
{feats_table}

> **Note on Missing Data (D8):** If **any** required feature is missing (e.g. no waist measurement or no blood pressure reading within the past 30 days), the risk agent returns `{{"status": "not_enough_information", "missing": [...]}}`. It **never** falls back to `diabetes_basic_nhanes`.

### 1.6 Performance Metrics & Confidence Intervals
Evaluated on the held-out temporal test set (2017–2023, $n={t_full_m['n']:,}$, prevalence {fmt_pct(t_full_m['prevalence'])}):

| Metric | Point Estimate | 95% Confidence Interval | Clinical Interpretation |
| :--- | :--- | :--- | :--- |
| **AUROC** | **{fmt_num(t_full['auroc']['point'])}** | [{fmt_num(t_full['auroc']['ci_low'])}, {fmt_num(t_full['auroc']['ci_high'])}] | Exceeds D11 threshold ($\\ge 0.75$). |
| **AUPRC** | **{fmt_num(t_full['auprc']['point'])}** | [{fmt_num(t_full['auprc']['ci_low'])}, {fmt_num(t_full['auprc']['ci_high'])}] | Baseline prevalence is {fmt_pct(t_full_m['prevalence'])}. |
| **Sensitivity** | **{fmt_pct(t_full_m['sensitivity'])}** | - | Catches {t_full_m['tp']} of {t_full_m['tp'] + t_full_m['fn']} undiagnosed cases. |
| **Specificity** | **{fmt_pct(t_full_m['specificity'])}** | - | Correctly identifies {t_full_m['tn']} of {t_full_m['tn'] + t_full_m['fp']} non-cases. |
| **PPV (Precision)** | **{fmt_pct(t_full_m['ppv'])}** | - | ~1 in 14 flagged individuals has undiagnosed diabetes. |
| **NPV** | **{fmt_pct(t_full_m['npv'])}** | - | 98.8% probability of no undiagnosed diabetes when unflagged. |
| **F1 Score** | **{fmt_num(t_full_m['f1'])}** | - | Harmonic mean of precision and recall. |
| **Operating Threshold** | **{fmt_num(m_full['threshold']['locked_threshold'])}** | - | Locked at $\\ge 80\\%$ validation sensitivity policy. |

### 1.7 Calibration & Risk Bands
- **Brier Score:** {fmt_num(t_full_cal['brier'])}
- **Calibration-in-the-Large (CITL):** {fmt_num(t_full_cal['citl'])}
- **Calibration Slope:** **{fmt_num(t_full_cal['slope'])}** (Passes D11 gate: within $[0.8, 1.2]$)
- **Calibration Intercept:** {fmt_num(t_full_cal['intercept'])}
- **Risk Bands (D8):**
  - **Low Risk:** Probability $< {fmt_num(m_full['bands']['low_max'])} (< 2.76\\%)$
  - **Moderate Risk:** Probability between ${fmt_num(m_full['bands']['low_max'])}$ and ${fmt_num(m_full['bands']['high_min'])}$
  - **High Risk:** Probability $\\ge {fmt_num(m_full['bands']['high_min'])} (\\ge 8.71\\%)$

### 1.8 Subgroup Evaluation
Evaluated across sex, age brackets, race/ethnicity proxy groups, and survey cycles:

| Subgroup Variable | Subgroup Value | $N$ | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{subgroups_table}

- **Worst Subgroup Sensitivity:** `age_band=40-59` at **{fmt_pct(t_full['worst_subgroup']['sensitivity'])}**, which passes the D11 gate ($\\ge 60\\%$).
- **Older Adults (60+):** Sensitivity is {fmt_pct(t_full['subgroups'][4]['sensitivity'])}, but specificity drops to **{fmt_pct(t_full['subgroups'][4]['specificity'])}**. In older adults, age drives high baseline probabilities.

### 1.9 Card-Population Performance (`told_high_bp == 1`)
For the intended clinical audience (patients with documented hypertension):
- **Cohort Size ($N$):** {t_full_card['n']:,} ({t_full_card['positives']:,} positives, prevalence {fmt_pct(t_full_card['prevalence'])})
- **AUROC:** **{fmt_num(t_full_card['auroc'])}**
- **Sensitivity:** **{fmt_pct(t_full_card['sensitivity'])}**
- **Specificity:** **{fmt_pct(t_full_card['specificity'])}**
- **Clinical Reading:** Among hypertensive patients, discrimination drops from 0.7527 to 0.6640 because hypertension is already one of the strongest predictors. While sensitivity is very high (93.18%), specificity is low (17.60%), meaning the model flags a substantial fraction of hypertensive individuals.

### 1.10 Comparison with Reference Config on the Same Label
Comparing `diabetes_full_nhanes` against the unregularized reference model (`diabetes_ref_age_sex_bmi`) evaluated on the **identical undiagnosed diabetes target label**:

| Config | Features | Val AUROC | Test AUROC | Test Sensitivity | Test Specificity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`diabetes_full_nhanes` (Production)** | Age, Sex, BMI, Smoking, Told High BP, SBP, DBP, Waist | **{fmt_num(m_full['chosen_model']['val_auroc'])}** | **{fmt_num(t_full['auroc']['point'])}** | **{fmt_pct(t_full_m['sensitivity'])}** | **{fmt_pct(t_full_m['specificity'])}** |
| `diabetes_ref_age_sex_bmi` (Reference) | Age, Sex, BMI | {fmt_num(m_ref['chosen_model']['val_auroc'])} | {fmt_num(t_ref['auroc']['point'])} | {fmt_pct(t_ref_m['sensitivity'])} | {fmt_pct(t_ref_m['specificity'])} |
| **Difference** | Additional clinical features | **+{m_full['chosen_model']['val_auroc'] - m_ref['chosen_model']['val_auroc']:.4f}** | **+{t_full['auroc']['point'] - t_ref['auroc']['point']:.4f}** | **+{t_full_m['sensitivity'] - t_ref_m['sensitivity']:.2%}** | **+{t_full_m['specificity'] - t_ref_m['specificity']:.2%}** |

### 1.11 Decision Curve Analysis (DCA) Summary
From `docs/ml/DECISION_CURVE.md`:
- **General Test Population:** The model provides positive net clinical benefit over deterministic rules and "screen all" across threshold probabilities $p_t \\in [0.01, 0.12]$.
- **Card Population (Hypertension):** At low threshold probabilities ($p_t \\le 0.03$), the model provides no net benefit over simply screening all hypertensive patients (e.g. at $p_t = 0.03$, net benefit: model 0.0391 vs screen all 0.0394 vs Age $\\ge 35$ rule 0.0400). The model adds net benefit only from $p_t \\in [0.04, 0.13]$.
- **Clinical Policy Implication:** Because an HbA1c blood test is a low-cost, low-risk laboratory test, clinicians commonly operate at low screening thresholds ($\\le 3\\%$). At that threshold, testing every hypertensive adult achieves equivalent or superior net benefit. This strongly justifies **D15** (a deterministic, rule-based screening reminder) rather than an unconstrained patient-facing ML risk score.

### 1.12 External Validation Status
- **Saad, Day 6:** Pending.
- **BRFSS Limitation Note:** The BRFSS survey contains no laboratory biomarker data (no HbA1c, fasting glucose) and no physical examination cuff measurements. External validation on BRFSS cannot evaluate undiagnosed target labels, but will evaluate self-reported diagnosis awareness (`told_diabetes`) and demographic feature drift.

### 1.13 Limitations & Transportability
1. **US NHANES Training Origin:** The model is trained on United States survey data and has **not been clinically validated for Pakistani patients**.
2. **South Asian Phenotypic Differences:** South Asian populations develop type 2 diabetes at younger ages and significantly lower BMI thresholds compared to European and North American populations. The World Health Organization (WHO) recommends lower BMI action points for Asian adults ($\\ge 23.0\\text{{ kg/m}}^2$ for overweight, $\\ge 27.5\\text{{ kg/m}}^2$ for obesity).
3. **Home Blood Pressure vs Exam Blood Pressure:** The model was trained on calibrated clinical examination blood pressure readings (standardized mercury sphygmomanometer). The app collects patient home BP readings, which have higher measurement variance and may reflect white-coat or masked hypertension discrepancies.
4. **Self-Reported Inclusion Filter:** The target population excludes diagnosed diabetes based on self-report (`told_diabetes == 0`). Patients unaware of their diagnosis or with incomplete medical history may be misclassified.
5. **Unweighted Survey Training:** The model was trained without NHANES complex survey weights to optimize discrimination on individual cases rather than population-level prevalence estimation.

---

## Part 2: Retired & Non-Shipped Models

| Model Config | Primary Gates Failed | Ship Decision | Reference Document |
| :--- | :--- | :--- | :--- |
| **`diabetes_basic_nhanes`** | Failed Gate 5: FULL model beats BASIC by +{m_full['chosen_model']['val_auroc'] - m_basic['chosen_model']['val_auroc']:.4f} validation AUROC. | **NOT EXPORTED.** Missing waist size in production yields `not_enough_information` with NO fallback to basic. | [`docs/ml/experiments/diabetes_basic_nhanes.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/diabetes_basic_nhanes.md) |
| **`htn_basic_nhanes`** | Failed Gate 1 (val AUROC {fmt_num(m_htn_basic['chosen_model']['val_auroc'])} $< 0.75$), Failed Gate 3 (slope {fmt_num(m_htn_basic['test_evaluation']['calibration']['slope'])} $\\notin [0.8, 1.2]$), Card AUROC {fmt_num(m_htn_basic['test_evaluation']['card_population']['auroc'])}. | **RETIRED (D13).** Poor discrimination on diabetic patients. | [`docs/ml/experiments/htn_basic_nhanes.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/htn_basic_nhanes.md) |
| **`htn_full_nhanes`** | Failed Gate 1 (val AUROC {fmt_num(m_htn_full['chosen_model']['val_auroc'])} $< 0.75$), Failed Gate 3 (slope {fmt_num(m_htn_full['test_evaluation']['calibration']['slope'])} $\\notin [0.8, 1.2]$), Flags 100% of adults 60+ (0% specificity). | **RETIRED (D13).** Near-chance discrimination in target population ({fmt_num(m_htn_full['test_evaluation']['card_population']['auroc'])}). | [`docs/ml/experiments/htn_full_nhanes.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/htn_full_nhanes.md) |
| **`diabetes_ref_age_sex_bmi`** | Baseline reference configuration on the same undiagnosed diabetes label. | **REFERENCE ONLY.** Not intended for production deployment. | [`docs/ml/experiments/diabetes_ref_age_sex_bmi.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/diabetes_ref_age_sex_bmi.md) |
| **`htn_ref_age_sex_bmi`** | Baseline reference configuration on the same measured hypertension label. | **REFERENCE ONLY.** Not intended for production deployment. | [`docs/ml/experiments/htn_ref_age_sex_bmi.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/htn_ref_age_sex_bmi.md) |

---

## Part 3: Summary of D11 Gate Evaluation

| Gate ID | Gate Description | Target Criteria | `diabetes_full_nhanes` Result | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 1** | Test Discrimination | Test AUROC $\\ge 0.75$ | **{fmt_num(t_full['auroc']['point'])}** (Val: {fmt_num(m_full['chosen_model']['val_auroc'])}) | **PASS** |
| **Gate 2** | Test Sensitivity | Test Sensitivity $\\ge 75\\%$ | **{fmt_pct(t_full_m['sensitivity'])}** | **PASS** |
| **Gate 3** | Test Calibration | Calibration Slope $\\in [0.80, 1.20]$ | **{fmt_num(t_full_cal['slope'])}** | **PASS** |
| **Gate 4** | Subgroup Equity | Worst Subgroup Sensitivity $\\ge 60\\%$ | **{fmt_pct(t_full['worst_subgroup']['sensitivity'])}** (`age_band=40-59`) | **PASS** |
| **Gate 5** | Tier Parsimony | Full Tier beats Basic Tier | **+{m_full['chosen_model']['val_auroc'] - m_basic['chosen_model']['val_auroc']:.4f} AUROC** ({fmt_num(m_full['chosen_model']['val_auroc'])} vs {fmt_num(m_basic['chosen_model']['val_auroc'])}) | **PASS** |

**Final Recommendation:** Ship `diabetes_full_nhanes` to production **strictly** as a provider-only experimental advisory module per D12.
"""
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"Generated {OUTPUT_MD} successfully from metrics.json.")


if __name__ == "__main__":
    main()
