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

---

## 2. Guideline-Rule Screening Baselines (No Training Required)

Evaluated on the exact same held-out test cohort records and card audience as the diabetes models:

| Guideline Screening Rule | Cohort Evaluated | Prevalence | Sensitivity | Specificity | PPV | Clinical Evidence Source |
| --- | --- | --- | --- | --- | --- | --- |
| Rule Baseline: Age >= 35 (General Test) | n=9,117 (pos=388) | 4.26% | 93.04% | 28.71% | 5.48% | as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman |
| Rule Baseline: Age 35-70 & BMI >= 25 (General Test) | n=9,117 (pos=388) | 4.26% | 63.66% | 58.01% | 6.31% | as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman |
| Rule Baseline: Age >= 35 (Card Audience: High BP) | n=2,720 (pos=190) | 6.99% | 96.32% | 8.46% | 7.32% | as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman |
| Rule Baseline: Age 35-70 & BMI >= 25 (Card Audience: High BP) | n=2,720 (pos=190) | 6.99% | 60.00% | 46.17% | 7.72% | as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman |

---

## 3. Matched Operating-Point Comparison (Fair Model vs Rule Evaluation)

Evaluating the model and guideline rules at matched operating points on the held-out test set (ROC curve evaluated with `drop_intermediate=False`):

| Model | Population | Rule | Rule Sens / Spec | Model Spec @ Rule Sens | Model Sens @ Rule Spec | Comparison |
| --- | --- | --- | --- | --- | --- | --- |
| `diabetes_basic_nhanes` | General Test | Age >= 35 | 93.04% / 28.71% | 39.02% | 96.91% | Model (+10.3% spec / +3.9% sens) |
| `diabetes_basic_nhanes` | General Test | Age 35-70 & BMI >= 25 | 63.66% / 58.01% | 70.09% | 75.52% | Model (+12.1% spec / +11.9% sens) |
| `diabetes_basic_nhanes` | Card Audience: High BP | Age >= 35 | 96.32% / 8.46% | 9.68% | 97.89% | Model (+1.2% spec / +1.6% sens) |
| `diabetes_basic_nhanes` | Card Audience: High BP | Age 35-70 & BMI >= 25 | 60.00% / 46.17% | 65.18% | 77.89% | Model (+19.0% spec / +17.9% sens) |
| `diabetes_full_nhanes` | General Test | Age >= 35 | 93.06% / 28.77% | 41.34% | 96.67% | Model (+12.6% spec / +3.6% sens) |
| `diabetes_full_nhanes` | General Test | Age 35-70 & BMI >= 25 | 65.00% / 57.83% | 69.96% | 79.44% | Model (+12.1% spec / +14.4% sens) |
| `diabetes_full_nhanes` | Card Audience: High BP | Age >= 35 | 97.16% / 8.61% | 10.65% | 98.30% | Model (+2.0% spec / +1.1% sens) |
| `diabetes_full_nhanes` | Card Audience: High BP | Age 35-70 & BMI >= 25 | 63.07% / 45.48% | 63.75% | 77.27% | Model (+18.3% spec / +14.2% sens) |

At matched trade-offs, both the basic and full models achieve higher specificity at the guideline rule's sensitivity and higher sensitivity at the rule's specificity, though in the card population for Age >= 35 both the model and the rule provide negligible specificity (< 11%).

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
6. **Comparison with Guideline Rules:** When matched at the same sensitivity or specificity (Table 3), the trained logistic regression models show modest discrimination gains over deterministic age and BMI cut-offs on the general test set, while on the card audience for `Age >= 35`, both the model and the rule exhibit specificity under 11%.

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
5. **Decision D15 (Proposed Patient-Facing Feature):** A rule-based screening reminder (needs doctor approval; NOT built today). If a patient with hypertension has no HbA1c in their record within the interval clinicians set, display: *"Ask your doctor whether you need an HbA1c (sugar) test."* Deterministic, record-based, explainable: "the rules decide".
6. **External Validation Limitation for BRFSS (Day 6):** The BRFSS surveillance dataset contains no laboratory specimen data (no HbA1c, fasting glucose) and no physical cuff examination measurements. Consequently, BRFSS cannot evaluate undiagnosed target labels (`diabetes_undiagnosed` or `hypertension_measured_130_80`). Day 6 external validation on BRFSS will be limited to evaluating self-reported awareness labels (`diabetes_told`, `hypertension_told`) or assessing feature drift across demographics.
