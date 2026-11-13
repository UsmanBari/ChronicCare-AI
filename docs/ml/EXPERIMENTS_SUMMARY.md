# ChronicCare AI — Machine Learning Experiments Summary & Governance Report

> **Decisions:** Usman (ML lead), 29 Oct 2026. Not yet reviewed by clinicians.  
> **Guiding Principle:** The model proposes, the rules decide.

---

## 1. Machine Learning Experiment Benchmark Matrix

All models were evaluated on the held-out NHANES temporal test set (`test` 2017–2023, 2 survey cycles). Thresholds and hyperparameters were locked strictly on the temporal validation set (`validation` 2013–2016). Decision threshold policy is `min_sensitivity >= 0.80` on validation.

| Experiment Name | Clean n (train/val/test) | Test Prev | Chosen Model (D10) | Val AUROC | Test AUROC [95% CI] | Test Sens / Spec / PPV | Cal Slope (Val / Test) | Worst Subgroup Sens (>= 50 pos) | Card Pop AUROC / Sens | Gap vs Ref (Val / Test) | FYP-1 Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `diabetes_basic_nhanes` | 29,084 / 9,264 / 9,117 | 4.26% | lr ({'C': 10.0}) | 0.7542 | 0.7403 [0.7182–0.7616] | 85.05% / 51.40% / 7.22% | 0.850 / 0.820 | age_band=18-39: 58.82% (n=51) | 0.6561 / 93.68% | +0.0002 (val) / -0.0019 (test) | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `diabetes_full_nhanes` | 27,448 / 8,714 / 8,681 | 4.15% | lr ({'C': 0.1}) | 0.7617 | 0.7527 [0.7293–0.7748] | 85.28% / 52.23% / 7.17% | 0.857 / 0.848 | age_band=40-59: 76.00% (n=125) | 0.6640 / 93.18% | +0.0077 (val) / +0.0106 (test) | SHIP CANDIDATE (all D11 gates passed) |
| `htn_basic_nhanes` | 22,061 / 7,126 / 7,037 | 30.67% | lr ({'C': 0.01}) | 0.7540 | 0.7148 [0.7022–0.7262] | 80.40% / 52.65% / 42.89% | 1.066 / 0.869 | age_band=18-39: 38.41% (n=552) | 0.5442 / 89.53% | +0.0007 (val) / -0.0002 (test) | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `htn_full_nhanes` | 20,766 / 6,609 / 6,537 | 30.66% | lr ({'C': 0.01}) | 0.7546 | 0.7105 [0.6983–0.7230] | 80.49% / 52.08% / 42.62% | 1.088 / 0.858 | age_band=18-39: 39.14% (n=511) | 0.5317 / 90.75% | +0.0013 (val) / -0.0045 (test) | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `diabetes_ref_age_sex_bmi` | 32,081 / 9,278 / 9,133 | 4.25% | lr ({'C': 1.0}) | 0.7540 | 0.7421 [0.7203–0.7640] | 84.28% / 50.05% / 6.96% | 0.854 / 0.825 | age_band=18-39: 50.98% (n=51) | 0.6582 / 89.47% | Ref Baseline | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `htn_ref_age_sex_bmi` | 25,033 / 7,246 / 7,206 | 30.81% | lr ({'C': 0.1}) | 0.7533 | 0.7150 [0.7030–0.7269] | 80.14% / 53.11% / 43.21% | 1.026 / 0.840 | age_band=18-39: 37.99% (n=558) | 0.5437 / 92.15% | Ref Baseline | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `chd10_framingham` | 2,499 / 833 / 834 | 14.99% | lr ({'C': 0.01}) | 0.7170 | 0.7241 [0.6732–0.7659] | 84.80% / 39.07% / 19.70% | 1.079 / 1.142 | age_band=<50: 60.53% (n=38) | 0.6488 / 100.00% | N/A (Framingham) | SHIP CANDIDATE (all G1-G5 gates passed) |
| `diabetes_control_nhanes` | 2,322 / 1,302 / 1,469 | 28.11% | lr ({'C': 0.01}) | 0.7235 | 0.7167 [0.6859–0.7462] | 77.48% / 53.50% / 39.46% | 1.568 / 1.439 | on_insulin=0.0: 53.77% (n=199) | 0.7167 / 77.48% | N/A (Diagnosed Diabetes) | NOT SHIPPED (Failed G2 Slope 1.439, Failed G4 Subgroup Sens 53.77%) |

---

## 2. Guideline-Rule Screening Baselines (No Training Required)

Evaluated on the exact same held-out test cohort records and card audience as the diabetes models:

| Guideline Screening Rule | Cohort Evaluated | Prevalence | Sensitivity | Specificity | PPV | Clinical Evidence Source |
| --- | --- | --- | --- | --- | --- | --- |
| Rule Baseline: Age >= 35 (General Test) | n=9,117 (pos=388) | 4.26% | 93.04% | 28.71% | 5.48% | ADA Standards of Care 2026, Section 2 |
| Rule Baseline: Age 35-70 & BMI >= 25 (General Test) | n=9,117 (pos=388) | 4.26% | 63.66% | 58.01% | 6.31% | USPSTF 2021 |
| Rule Baseline: Age >= 35 (Card Audience: High BP) | n=2,720 (pos=190) | 6.99% | 96.32% | 8.46% | 7.32% | ADA Standards of Care 2026, Section 2 |
| Rule Baseline: Age 35-70 & BMI >= 25 (Card Audience: High BP) | n=2,720 (pos=190) | 6.99% | 60.00% | 46.17% | 7.72% | USPSTF 2021 |
| Rule Baseline: BMI >= 25 & High BP, any age (Card Audience: High BP) | n=2,720 (pos=190) | 6.99% | 91.58% | 20.12% | 7.93% | ADA Standards of Care 2026, Section 2, Table 2.5 (item 1, risk factor: hypertension) |
| Rule Baseline: BMI >= 23 & High BP, any age (Card Audience: High BP) | n=2,720 (pos=190) | 6.99% | 96.32% | 10.08% | 7.45% | ADA 2026 Table 2.5 / USPSTF 2021 (BMI >= 23 for Asian American adults) |

---

## 3. Matched Operating-Point Comparison (Fair Model vs Rule Evaluation)

Evaluating the model and guideline rules at matched operating points on the held-out test set (ROC curve evaluated with `drop_intermediate=False`):

| Model | Population | Rule | Rule Sens / Spec | Model Spec @ Rule Sens | Model Sens @ Rule Spec | Comparison |
| --- | --- | --- | --- | --- | --- | --- |
| `diabetes_basic_nhanes` | General Test | Age >= 35 | 93.04% / 28.71% | 39.02% | 96.91% | Model (+10.3 pp spec / +3.9 pp sens) |
| `diabetes_basic_nhanes` | General Test | Age 35-70 & BMI >= 25 | 63.66% / 58.01% | 70.09% | 75.52% | Model (+12.1 pp spec / +11.9 pp sens) |
| `diabetes_basic_nhanes` | Card Audience: High BP | Age >= 35 | 96.32% / 8.46% | 9.68% | 97.89% | Model (+1.2 pp spec / +1.6 pp sens) |
| `diabetes_basic_nhanes` | Card Audience: High BP | Age 35-70 & BMI >= 25 | 60.00% / 46.17% | 65.18% | 77.89% | Model (+19.0 pp spec / +17.9 pp sens) |
| `diabetes_basic_nhanes` | Card Audience: High BP | BMI >= 25 & High BP, any age | 91.58% / 20.12% | 18.26% | 87.89% | Rule (+1.9 pp spec / +3.7 pp sens) |
| `diabetes_basic_nhanes` | Card Audience: High BP | BMI >= 23 & High BP, any age | 96.32% / 10.08% | 9.68% | 95.79% | Rule (+0.4 pp spec / +0.5 pp sens) |
| `diabetes_full_nhanes` | General Test | Age >= 35 | 93.06% / 28.77% | 41.34% | 96.67% | Model (+12.6 pp spec / +3.6 pp sens) |
| `diabetes_full_nhanes` | General Test | Age 35-70 & BMI >= 25 | 65.00% / 57.83% | 69.96% | 79.44% | Model (+12.1 pp spec / +14.4 pp sens) |
| `diabetes_full_nhanes` | Card Audience: High BP | Age >= 35 | 97.16% / 8.61% | 10.65% | 98.30% | Model (+2.0 pp spec / +1.1 pp sens) |
| `diabetes_full_nhanes` | Card Audience: High BP | Age 35-70 & BMI >= 25 | 63.07% / 45.48% | 63.75% | 77.27% | Model (+18.3 pp spec / +14.2 pp sens) |
| `diabetes_full_nhanes` | Card Audience: High BP | BMI >= 25 & High BP, any age | 92.05% / 19.98% | 18.64% | 90.91% | Rule (+1.3 pp spec / +1.1 pp sens) |
| `diabetes_full_nhanes` | Card Audience: High BP | BMI >= 23 & High BP, any age | 96.02% / 9.78% | 11.61% | 98.30% | Model (+1.8 pp spec / +2.3 pp sens) |

At matched trade-offs, both the basic and full models achieve higher specificity at the guideline rule's sensitivity and higher sensitivity at the rule's specificity on the general test set. In the card population, for Age >= 35 both the model and the rule provide negligible specificity (< 11%), while Rule c (BMI >= 25 & High BP) achieves 20.12% specificity at 91.58% sensitivity, matching or outperforming the models.

Detailed Decision Curve Analysis (DCA) assessing net benefit across decision threshold probabilities $p_t \in [0.01, 0.20]$ is documented in [docs/ml/DECISION_CURVE.md](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/DECISION_CURVE.md).

---

## 4. Honest Findings & Technical Synthesis

1. **Model Gate Evaluation:** `diabetes_full_nhanes` is the only model that satisfies all five D11 acceptance gates (`SHIP CANDIDATE (all D11 gates passed)`), with test AUROC of 0.7527, test sensitivity of 85.28%, test calibration slope of 0.848, worst subgroup sensitivity of 76.00%, and validation AUROC exceeding basic (+0.0075). The remaining five configurations are NOT SHIPPED due to failing Gate 1 (test AUROC < 0.75) and/or Gate 4 (subgroup sensitivity < 60.0% in adults aged 18–39).
2. **Parity Gaps Over Age, Sex, and BMI:**
   - `diabetes_full_nhanes` vs `diabetes_basic_nhanes` (engineered basic tier): validation AUROC gap **+0.0075**, test AUROC gap **+0.0124**.
   - `diabetes_full_nhanes` vs `diabetes_ref_age_sex_bmi` (reference baseline): validation AUROC gap **+0.0077**, test AUROC gap **+0.0106**.
   - `diabetes_basic_nhanes` vs `diabetes_ref_age_sex_bmi`: validation AUROC gap **+0.0002**, test AUROC gap **-0.0019**.
   - `htn_basic_nhanes` vs `htn_ref_age_sex_bmi`: validation AUROC gap **+0.0007**, test AUROC gap **-0.0002**.
   - `htn_full_nhanes` vs `htn_basic_nhanes`: validation AUROC gap **+0.0006**, test AUROC gap **-0.0043**.
   For hypertension, adding physical measurements in FULL yields a test AUROC that is 0.0043 lower than BASIC.
3. **Card-Population Discrimination:** When evaluated on the specific patient group who would view the risk card in the profile (the reciprocal diagnosis population), discrimination is modest for diabetes and near chance for hypertension:
   - For patients with high BP screened for undiagnosed diabetes: card AUROC is **0.6561** (basic) and **0.6640** (full).
   - For patients with diabetes screened for hypertension: card AUROC is **0.5442** (basic) and **0.5317** (full), which is close to an uninformative classifier (0.50).
4. **Age-Band Performance Disparity:**
   Because age carries the largest standardized coefficient in tabular logistic regression, models exhibit notable variation across age bands:
   - In `htn_basic_nhanes`:
     - Age 18–39: sensitivity 38.41%, specificity 87.54% (n=3,104, positives=552).
     - Age 40–59: sensitivity 88.84%, specificity 25.42% (n=2,062, positives=744).
     - Age 60+: sensitivity 100.0%, specificity 0.0% (n=1,871, positives=862). Every adult aged 60+ in the test set is flagged.
   - In `diabetes_basic_nhanes`:
     - Age 18–39: sensitivity 58.82%, specificity 87.92% (n=3,254, positives=51).
     - Age 40–59: sensitivity 77.44%, specificity 51.91% (n=2,668, positives=133).
     - Age 60+: sensitivity 96.57%, specificity 11.87% (n=3,195, positives=204).
   - In `diabetes_full_nhanes`:
     - Age 18–39: sensitivity 63.83%, specificity 86.34% (n=3,107, positives=47).
     - Age 40–59: sensitivity 76.00%, specificity 52.57% (n=2,556, positives=125).
     - Age 60+: sensitivity 96.81%, specificity 15.05% (n=3,018, positives=188).
5. **Precision and False-Positive Rates:** At ~4.15% baseline prevalence of undiagnosed diabetes, operating at 85.28% sensitivity produces an operational specificity of 52.23% and a Positive Predictive Value (PPV) of **7.17%**. Approximately 13 out of every 14 flagged individuals do not have undiagnosed diabetes.
6. **Comparison with Guideline Rules & Clinical Low Thresholds:** When matched at the same sensitivity or specificity (Table 3), the trained logistic regression models show modest discrimination gains over deterministic age and BMI cut-offs on the general test set, while on the card audience for `Age >= 35`, both the model and the rule exhibit specificity under 11%. HbA1c is a low-cost test, so clinicians are likely to use a low threshold (≤3%); in that range, testing every patient with high BP is as good as the model. This supports D15 (a rule-based reminder) over a patient-facing ML card.

---

## 5. Transportability & Population Limits

- **US NHANES Training Origin:** The models are developed and evaluated on US NHANES data (1999–2023).
- **South Asian Population Differences:** South Asian adults develop type 2 diabetes at younger ages and lower BMI thresholds compared to European-derived populations. The World Health Organization (WHO) identifies lower BMI action points for Asian populations (overweight: $\ge 23.0\text{ kg/m}^2$; obese: $\ge 27.5\text{ kg/m}^2$).
- **Lack of Pakistani Validation:** The model is **not validated for Pakistani patients**.
- **Proxy Group in NHANES:** NHANES race code 5 (`Other Race / Multi-Racial`) is the closest available group in the dataset. In `diabetes_full_nhanes`, this subgroup contains $n=1,291$ individuals with 56 positive cases (prevalence 4.34%), yielding an AUROC of 0.7864, sensitivity of 76.79%, and specificity of 68.10%. This subgroup serves only as a weak proxy and does not establish clinical validity in South Asian cohorts.

---

## 6. Decisions, 29 Oct (Usman, ML Lead)

> **Decisions:** Usman (ML lead), 29 Oct 2026. Not yet reviewed by clinicians.  
> **Guiding Principle:** The model proposes, the rules decide.

1. **D10 Amendment (Model Parsimony):** Between plain `lr` and `lr_balanced`, select plain `lr` unless `lr_balanced` exceeds plain `lr` by $\ge 0.01$ validation AUROC (due to balanced class weighting inflating predicted probabilities and distorting calibration). Tree models remain unchanged (+0.02 rule over the chosen LR).
2. **Decision D12 (Diabetes Risk Deployment):** `diabetes_full_nhanes` is statistically a `SHIP CANDIDATE (all D11 gates passed)`, but its card-population AUROC is 0.6640. In FYP-1, it is displayed **ONLY on the provider review page** labeled: *"Experimental: trained on US NHANES data, not validated for Pakistani patients"*, behind the `RISK_ENABLED` feature flag (off by default in production, can be toggled on for demo). It is **NEVER shown to patients in FYP-1**. It requires `waist_cm`; without `waist_cm`, the provider sees "not enough information" (no fallback to basic, which failed its gates).
3. **Decision D13 (Hypertension Risk Deployment):** Retired for FYP-1. Card-population AUROC is ~0.54 (near chance), and in older adults (60+), the model flags 100.0% of individuals (specificity 0.0%), providing no discriminatory value. Artifacts and code are retained for documentation and academic reporting only.
4. **Decision D14 (Clinical Recommendation for Diabetics):** For patients with diabetes, recommend to supervising clinicians and doctors asking for an actual blood pressure cuff measurement during check-ins rather than attempting to infer high blood pressure probabilistically from demographic proxies. Requires clinical approval before implementation.
5. **Decision D15 (Proposed Patient-Facing Feature):** A rule-based screening reminder (needs doctor approval; NOT built today). If a patient with hypertension has no HbA1c in their record within the interval clinicians set, display: *"Ask your doctor whether you need an HbA1c (sugar) test."* Deterministic, record-based, explainable: "the rules decide". HbA1c is a low-cost test, so clinicians are likely to use a low threshold (≤3%); in that range, testing every patient with high BP is as good as the model. This supports D15 (a rule-based reminder) over a patient-facing ML card.
6. **External Validation Limitation for BRFSS (Day 6):** The BRFSS surveillance dataset contains no laboratory specimen data (no HbA1c, fasting glucose) and no physical cuff examination measurements. Consequently, BRFSS cannot evaluate undiagnosed target labels (`diabetes_undiagnosed` or `hypertension_measured_130_80`). Day 6 external validation on BRFSS will be limited to evaluating self-reported awareness labels (`diabetes_told`, `hypertension_told`) or assessing feature drift across demographics.

---

## 7. 10-Year Coronary Heart Disease (CHD) Risk Model (`chd10_framingham`)

> **Added:** Week 4 "Finish Sprint" (Saad, ML Engineer, 8 Nov 2026).  
> **Alignment:** Proposal Section 13.1 Agent 5 and Section 23 (hypertension-side risk model on Framingham Heart Study with tree comparison and SHAP).

### 7.1 Pre-Registration and Experimental Design
To avoid selective reporting, all experimental hyperparameters, evaluation rules, and acceptance gates were formally pre-registered in `docs/ml/CHD10_PREREGISTRATION.md` (committed and pushed alone prior to accessing held-out test data).
- **Target Label:** `TenYearCHD` (1 = event within 10 years).
- **Features (9 non-lab features):** `age`, `sex_male`, `current_smoker`, `bmi`, `sbp`, `dbp`, `bp_meds`, `diabetes`, `prevalent_hyp`. Excluded features requiring clinic blood draws: `totChol`, `glucose`, `heartRate`, `cigsPerDay`, `education`.
- **Target Population:** Adults aged 30–74 with hypertension or diabetes.
- **Split:** Deterministic stratified random split (60% Train, 20% Validation, 20% Test, `random_state=42`) on complete cases ($N=4,166$).

### 7.2 Candidate Architecture Tuning & Decision D10 Selection
Hyperparameters were tuned via 5-fold cross-validation on train ($N=2,499$):
- Plain Logistic Regression (`lr`, $C=0.01$): Val AUROC = **0.7170**, Val Calibration Slope = 1.079
- Balanced Logistic Regression (`lr_balanced`, $C=0.001$): Val AUROC = 0.7163, Val Calibration Slope = 1.748
- Random Forest (`rf`, `n_estimators=100, max_depth=5, min_samples_leaf=5`): Val AUROC = 0.7169, Val Calibration Slope = 1.090
- HistGradientBoosting (`hgb`, `learning_rate=0.05, max_depth=3, min_samples_leaf=10`): Val AUROC = 0.7011, Val Calibration Slope = 0.797

**Decision D10 Rule Applied:** Plain `lr` selected. `lr_balanced` did not beat plain `lr` by $\ge 0.01$ AUROC (gap: -0.0007), and neither tree model beat LR by $\ge 0.02$ validation AUROC (best tree gap: -0.0001). Calibration slope passed ($1.079 \in [0.8, 1.2]$).

### 7.3 Pre-Registered Acceptance Gates (G1–G5) on Held-Out Test Data ($N=834$)
| Gate | Criterion Description | Target Threshold | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 1** | Test Discrimination | Test AUROC $\ge 0.68$ | **0.7241** [95% CI: 0.6732–0.7659] | **PASS** |
| **Gate 2** | Calibration Slope | Calibration Slope $\in [0.80, 1.20]$ | **1.142** (Intercept: +0.164) | **PASS** |
| **Gate 3** | Sensitivity @ 10% Cutoff | Sensitivity $\ge 70.0\%$ | **84.80%** (Specificity: 39.07%, PPV: 19.70%) | **PASS** |
| **Gate 4** | Subgroup Equity | Worst Subgroup Sens @ 10% $\ge 60\%$ ($\ge 30$ pos) | **60.53%** (`age_band=<50`, 38 pos) | **PASS** |
| **Gate 5** | Information Value | Brier < Naive Prevalence Brier | **0.1172** vs 0.1274 | **PASS** |

**Overall Status:** **SHIP CANDIDATE** (all G1–G5 gates satisfied).

### 7.4 Explainability & Clinical Sanity
- **Odds Ratios & Direction Sanity:** All 9 standardized coefficients are positive ($\beta > 0$): `age` (+0.425), `sex_male` (+0.282), `sbp` (+0.199), `current_smoker` (+0.156), `prevalent_hyp` (+0.092), `bmi` (+0.074), `diabetes` (+0.051), `bp_meds` (+0.046), `dbp` (+0.045). All match clinical literature.
- **Global SHAP Hierarchy:** Mean absolute SHAP values confirm `age` (0.3658) and `sex_male` (0.2753) are the primary determinants, followed by `sbp` (0.1668) and `current_smoker` (0.1562).
- **Communication & Safety:** Audience set to `provider_and_patient_band`. Patients never see raw probabilities; they see their categorical risk band (`Low`, `Moderate`, `High`) with an explicit disclaimer that this is a research estimate, not a diagnosis.

### 7.5 App Population Performance (Post-Hoc, Not a Gate: `prevalent_hyp == 1 OR diabetes == 1`)
In production, the application displays the 10-year CHD risk estimate card only to patients with diagnosed hypertension or diabetes. In accordance with Decision D13, post-hoc subpopulation evaluation on the held-out test set ($N=834$) demonstrates:
- **Evaluated Subpopulation:** $n = 271$, positives = 69, prevalence = 25.46%
- **AUROC (95% Bootstrap CI):** **0.6488** [0.5795–0.7135]
- **At 10% Cutoff (Mod/High):** Sensitivity = **100.00%**, Specificity = **6.44%**, PPV = **26.74%**
- **At 20% Cutoff (High):** Sensitivity = **81.16%**, Specificity = **46.04%**, PPV = **33.94%**

### 7.6 Age Stratification & Senior Specificity Analysis
- **Age <50** ($n=429$, 38 positives):
  - 10% Cutoff: Sensitivity = 60.53%, Specificity = 63.68%, PPV = 13.94%
  - 20% Cutoff: Sensitivity = 36.84%, Specificity = 96.68%, PPV = 51.85%
- **Age 50–59** ($n=261$, 53 positives):
  - 10% Cutoff: Sensitivity = 92.45%, Specificity = 13.46%, PPV = 21.40%
  - 20% Cutoff: Sensitivity = 58.49%, Specificity = 69.23%, PPV = 32.63%
- **Age 60+** ($n=144$, 34 positives):
  - 10% Cutoff: Sensitivity = 100.00%, Specificity = 0.00%, PPV = 23.61%
  - 20% Cutoff: Sensitivity = 82.35%, Specificity = 28.18%, PPV = 26.17%

> **Clinical Finding on Senior Patients (60+):** For patients 60 and over the model almost always says Moderate or High; age drives it. Specificity at the 10% cut is 0.0% for 60+ (every participant aged 60+ is categorized as Moderate or High) and 13.5% for 50–59. When moving to the 20% High Risk cutoff, specificity recovers to 28.18% for 60+ and 69.23% for 50–59.



---

## 8. Diabetes Glycaemic Control Model (`diabetes_control_nhanes`)

### 8.1 Clinical Objective & Population
- **Objective:** Predict poor glycaemic control ($\text{HbA1c} \ge 8.0\%$ [64 mmol/mol]) among adults with self-reported diagnosed diabetes (`told_diabetes == 1`, DIQ010) using non-invasive check-in inputs.
- **Dataset:** NHANES Core (`nhanes_temporal_v1` split).
- **Counts:**
  - `train_core` (1999–2012, 7 cycles): 2,322 complete cases (660 positives, 28.42% prevalence)
  - `validation` (2013–2016, 2 cycles): 1,302 complete cases (391 positives, 30.03% prevalence)
  - `test` (2017–2023, 2 cycles): 1,469 complete cases (413 positives, 28.11% prevalence)
- **Features (9 App-Available Variables):** `age`, `sex_male`, `bmi`, `waist_cm`, `ever_smoked_100`, `sbp`, `dbp`, `on_insulin`, `on_diabetes_pills`.

### 8.2 Candidate Selection (Decision D10 Parsimony Rule)
- `lr` (C=0.01): Val AUROC = **0.7235** (val cal slope = 1.568).
- `lr_balanced` (C=0.01): Val AUROC = 0.7231 (gap vs lr: -0.0004 $< 0.01$).
- `rf`: Val AUROC = 0.7236 (tree gap vs lr: +0.0001 $< 0.02$).
- `hgb`: Val AUROC = 0.7097.
- **Outcome:** Plain `lr` selected under Decision D10 parsimony rule.

### 8.3 Operational Threshold & Risk Bands
- **Locked Threshold:** `0.2445` (Validation Sensitivity: 80.05%, Specificity: 51.59%).
- **Risk Bands (Validation Distribution):**
  - Low Risk: $p < 0.2445$
  - Moderate Risk: $0.2445 \le p < 0.3823$
  - High Risk: $p \ge 0.3823$ (top 20% validation cut)

### 8.4 Pre-Registered Test Gates (G1–G5) Audit
| Gate | Criterion | Target | Actual Test Result | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **G1** | Discrimination | Test AUROC $\ge 0.65$ | **0.7167** [0.6859, 0.7462] | **PASS** |
| **G2** | Calibration | Calibration Slope $\in [0.80, 1.20]$ | **1.439** (oversteep / probability compression) | **FAIL** |
| **G3** | Sensitivity | Test Sensitivity @ 0.2445 $\ge 70.0\%$ | **77.48%** (Spec: 53.50%, PPV: 39.46%) | **PASS** |
| **G4** | Equity | Worst Subgroup Sens $\ge 60.0\%$ ($\ge 30$ pos) | **53.77%** (`on_insulin=0.0`, 199 pos) | **FAIL** |
| **G5** | Information Value | Brier < Prevalence Brier | **0.1812** vs 0.2021 | **PASS** |

### 8.5 Safe Stop & Non-Shipment Decision
- **Final Status:** **NOT SHIPPED (BLOCKED)** — Safe stop triggered by failure of pre-registered Gate 2 and Gate 4.
- **Action:** Production export file `models/diabetes_control_nhanes.json` was deliberately NOT generated. Under ChronicCare-AI safety rules, uncalibrated risk models that exhibit severe subgroup disparities must not be deployed to patient check-in workflows.
