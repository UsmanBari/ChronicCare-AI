# ChronicCare AI — Model Evidence Completeness Report

**Date:** 14 November 2026  
**Scope:** Machine Learning Models Developed, Validated, and Governed for FYP-1  
**Standards:** TRIPOD-AI / DECIDE-AI Reporting Transparency Guidelines  
**Dataset Artifacts:** US NHANES 2017–2023 ($N=8,681$), Framingham Heart Study ($N=834$)  
**Privacy & Safety Invariant:** Pre-trained weights and pre-registered validation splits only; zero patient PHI.

---

## 1. Executive Summary & Production Status

ChronicCare AI evaluated three candidate machine learning risk models for deployment in clinical triage:

| Model ID | Clinical Objective | Test AUROC [95% CI] | Brier Score | Calibration Slope | Shipped in FYP-1? | Rationale |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `diabetes_full_nhanes` | 3-Year Undiagnosed Type 2 Diabetes Risk | **0.7527** [0.7293–0.7748] | **0.0389** | **0.848** | **YES** (Provider-facing) | Passed all 5 pre-registered clinical gates; excellent calibration and demographic equity. |
| `chd10_framingham` | 10-Year Coronary Heart Disease (Framingham) | **0.7241** [0.6732–0.7659] | **0.1172** | **1.142** | **YES** (Patient & Provider) | Passed all clinical gates; verified against clinical benchmarks. |
| `diabetes_control_nhanes` | Uncontrolled Diabetes ($\text{HbA1c} \ge 8.0\%$) | **0.7167** [0.6859–0.7462] | **0.1812** | **1.439** | **NO** (Responsibly Withheld) | **FAILED G2 (Calibration 1.439) & G4 (Non-insulin sensitivity 53.8%)**. Held back per Doctor Decision D3. |

> [!IMPORTANT]
> **Clarification on AUROC Figures:**
> Earlier experimental notes referenced an exploratory unvalidated baseline AUROC of 0.835 on an unregularized in-sample exploratory subset. The **true, audited, pre-registered test AUROC on the temporal held-out NHANES partition is 0.7527 [0.7293–0.7748]**. All thesis documentation, viva presentations, and benchmark tables report the audited 0.7527 figure.

---

## 2. Model 1: Undiagnosed Diabetes Risk (`diabetes_full_nhanes`)

### 2.1 Clinical Target & Data Partitioning
- **Target:** Undiagnosed type 2 diabetes defined by laboratory criteria ($\text{HbA1c} \ge 6.5\%$ [48 mmol/mol] or fasting plasma glucose $\ge 126\text{ mg/dL}$) in adults with no self-reported physician diagnosis.
- **Data Source:** US National Health and Nutrition Examination Survey (NHANES) 2017–March 2020 Pre-Pandemic and 2021–2023 Cycles.
- **Partitioning:** Temporal held-out evaluation partition ($N = 8,681$, positive cases = 360, prevalence = 4.15%).
- **Operating Threshold:** $p_t = 0.0276$ (locked on validation split using Youden index).

### 2.2 Diagnostic Performance Metrics
- **Test AUROC:** 0.7527 [95% CI: 0.7293 – 0.7748] (Validation AUROC: 0.7617)
- **Sensitivity / Recall:** 85.28% [95% CI: 81.61% – 88.86%] (307 / 360 true positives identified)
- **Specificity:** 52.23% (4,346 / 8,321 true negatives)
- **Positive Predictive Value (PPV):** 7.17% [95% CI: 6.37% – 7.92%] (consistent with low population prevalence of 4.15%)
- **Negative Predictive Value (NPV):** 98.80% (4,346 / 4,399)
- **Brier Score:** 0.0389 (vs naive prevalence baseline of 0.0398)
- **Calibration Slope:** 0.848 (intercept: -0.442)
- **Subgroup Sensitivity:** Age 40–59 sensitivity 76.0% (exceeds pre-registered $\ge 60\%$ equity gate).

### 2.3 Top Clinical Features (SHAP Explanations)
1. **Age ($\beta = +0.595$, OR = 1.81):** Universal demographic predictor aligned with ADA 2026 screening guidelines ($\ge 35$ years).
2. **Waist Circumference ($\beta = +0.507$, OR = 1.66):** Primary surrogate for visceral adiposity and portal free-fatty-acid flux.
3. **Body Mass Index ($\beta = +0.163$, OR = 1.18):** Global adiposity metric, synergistic with central waist measurement.
4. **Systolic Blood Pressure ($\beta = +0.157$, OR = 1.17):** Microvascular and hemodynamic marker of metabolic syndrome.
5. **Prior Hypertension History ($\beta = +0.098$, OR = 1.10):** Clinical surrogate for chronic vascular resistance.

---

## 3. Model 2: 10-Year Cardiovascular Risk (`chd10_framingham`)

### 3.1 Clinical Target & Implementation
- **Target:** 10-year probability of hard coronary heart disease events (myocardial infarction, coronary death).
- **Dataset:** Framingham Heart Study held-out test split ($N = 834$, positive events = 125, prevalence = 14.99%).
- **Clinical Thresholds Evaluated:**
  - $p_t = 0.10$ (10% Moderate Risk cut): Sensitivity 84.80%, Specificity 39.07%, PPV 19.70%, NPV 93.58%.
  - $p_t = 0.20$ (20% High Risk cut): Sensitivity 58.40%, Specificity 78.00%, PPV 31.88%, NPV 91.40%.
- **Test AUROC:** 0.7241 [95% CI: 0.6732 – 0.7659].
- **Calibration Slope:** 1.142 (intercept: +0.164).
- **Brier Score:** 0.1172 (vs naive prevalence baseline of 0.1274).

### 3.2 Clinical Governance & Doctor Decision D2
- **Rule in Triage:** Per Doctor Decision D2 (Nov 2026), an elevated Framingham score ($\ge 20\%$) escalates a routine check-in to Review (Yellow) **only when accompanied by reported clinical symptoms** in the current check-in. Asymptomatic high baseline risk remains Routine (Green) with the risk score displayed in the provider summary, preventing alert fatigue. A 30-day cooldown window is enforced.

---

## 4. Model 3: Responsibly Withheld Glycemic Control Model (`diabetes_control_nhanes`)

### 4.1 Objective & Experimental Design
- **Target:** Probabilistic prediction of poor glycemic control ($\text{HbA1c} \ge 8.0\%$ [64 mmol/mol]) from non-invasive self-reported check-in dialogue among diagnosed diabetic patients ($N = 1,469$, prevalence = 28.11%).
- **Pre-Registration:** All hypotheses, feature pipelines, and quantitative acceptance criteria were pre-registered in `docs/ml/DMCONTROL_PREREGISTRATION.md`.

### 4.2 Gate Audit Results

| Gate | Requirement | Actual Result | Audit Status |
| :--- | :--- | :--- | :---: |
| **G1: Discrimination** | Test AUROC $\ge 0.65$ | **0.7167** [0.6859–0.7462] | **PASS** |
| **G2: Calibration** | Calibration Slope $\in [0.80, 1.20]$ | **1.439** (Severe probability compression) | **FAIL** |
| **G3: Sensitivity** | Sensitivity @ $p_t = 0.2445 \ge 70.0\%$ | **77.48%** (Specificity 53.50%) | **PASS** |
| **G4: Demographic Equity** | Worst Subgroup Sensitivity $\ge 60.0\%$ | **53.77%** (Non-insulin group: `on_insulin=0`) | **FAIL** |
| **G5: Brier Improvement** | Brier Score < Naive Baseline | **0.1812** vs 0.2021 | **PASS** |

### 4.3 Why Withholding is a Demonstration of Rigorous Engineering
1. **Calibration Breakdown:** A slope of 1.439 compresses predicted probabilities toward the mean, misinforming clinical decision-making.
2. **Subgroup Vulnerability:** The model achieved acceptable sensitivity in insulin-treated patients by using insulin prescription as an implicit shortcut, but missed nearly half (**46.2% false negative rate**) of poorly controlled patients on oral medications or lifestyle management.
3. **Adherence to Clinical Governance:** ChronicCare AI safety rules mandate an immediate stop when calibration or equity gates fail. Production artifact generation was aborted, and deployment was blocked.
4. **Doctor Decision D3 Confirmation:** The doctor on record approved holding this model back from production in FYP-1 until future iterations satisfy all pre-registered validation gates.

---

## 5. Summary Table for Viva & Examiners

| Dimension | Undiagnosed Diabetes Model | 10-Year CHD Risk Model | Glycemic Control Model |
| :--- | :--- | :--- | :--- |
| **Status in Repo** | **SHIPPED** (`models/diabetes_full_nhanes.json`) | **SHIPPED** (`models/chd10_framingham.json`) | **RESPONSIBLY NOT SHIPPED** |
| **Audited Test AUROC** | **0.7527** [0.7293–0.7748] | **0.7241** [0.6732–0.7659] | **0.7167** (Failed G2 & G4) |
| **Calibration** | Well-calibrated (Slope: 0.848) | Well-calibrated (Slope: 1.142) | Miscalibrated (Slope: 1.439) |
| **Clinical Role** | Provider-facing risk stratifier | Patient risk band & provider card | Research benchmark only |
| **Clinical Decision** | Approved for clinical display | Approved with D2 symptom-link | Approved to withhold (D3) |
