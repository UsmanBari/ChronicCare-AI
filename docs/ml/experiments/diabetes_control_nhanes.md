# ChronicCare AI — Model Evaluation Report

## Config
- **Name:** `diabetes_control_nhanes`
- **Target Label:** `diabetes_poor_control_80`
- **Population Filter:** `adults_with_diagnosed_diabetes`
- **Tier:** `full`
- **Features (9):** `age, sex_male, bmi, waist_cm, ever_smoked_100, sbp, dbp, on_insulin, on_diabetes_pills`
- **Candidate Models:** `lr, lr_balanced, rf, hgb`
- **Threshold Policy:** `{"type": "min_sensitivity", "value": 0.8}`
- **Seed:** `42`
- **Wall Time:** 30.99 seconds (0.5 minutes)

## Data
### Complete Case Cohort Statistics Across Temporal Splits

| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |
|---|---|---|---|---|---|
| `train_core` (1999-2012) | 3,793 | 1,471 | 2,322 | 660 | 28.42% |
| `validation` (2013-2016) | 1,472 | 170 | 1,302 | 391 | 30.03% |
| `test` (2017-2023) | 1,626 | 157 | 1,469 | 413 | 28.11% |

## Validation
### Candidate Model Validation Tuning

| Model | Best Hyperparameters | Val AUROC | Val Calibration Slope |
| --- | --- | --- | --- |
| lr | {"C": 0.01} | 0.7235 | 1.568 |
| lr_balanced | {"C": 0.01} | 0.7231 | 1.486 |
| rf | {"n_estimators": 100, "max_depth": 3, "min_samples_leaf": 5} | 0.7236 | 2.038 |
| hgb | {"learning_rate": 0.01, "max_depth": 3, "min_samples_leaf": 10} | 0.7097 | 1.916 |

### Decision D10 Selection Rationale
- **Chosen Architecture:** `lr`
- **Selection Rule:** Logistic regression (lr) selected under D10 parsimony rule (plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: -0.0004)): best tree did not beat LR by >= 0.02 validation AUROC (tree gap: +0.0001).
- **Validation Calibration Gate:** `CALIBRATION GATE: STOP, Usman decides` (Slope: 1.568)
- **D7 Locked Threshold:** `0.2445` (Val Sens: 80.05%, Val Spec: 51.59%)
- **D8 Risk Stratification Bands:** Low < `0.2445`, Moderate `0.2445` - `0.3823`, High >= `0.3823`

## Test
### Held-Out Test Discrimination & Diagnostic Performance (2017-2023)

- **Test AUROC (95% Bootstrap CI):** **0.7167** [0.6859 - 0.7462]
- **Test AUPRC (95% Bootstrap CI):** **0.4761** [0.4353 - 0.5227]

#### Operating Point: Locked Threshold (Low / Moderate Risk Cut)
- **Threshold:** `0.2445`
- **Sensitivity:** **77.48%**
- **Specificity:** **53.50%**
- **PPV (Precision):** **39.46%**
- **NPV:** **85.87%**
- **F1-Score:** **0.5229**
- **Confusion Matrix:** TP=320, FP=491, TN=565, FN=93

#### Operating Point: High Risk Cutoff (Top 20% Validation Scores)
- **Threshold:** `0.3823`
- **Sensitivity:** **34.62%**
- **Specificity:** **87.31%**
- **PPV (Precision):** **51.62%**
- **NPV:** **77.35%**
- **F1-Score:** **0.4145**
- **Confusion Matrix:** TP=143, FP=134, TN=922, FN=270

### App Population (Post-Hoc, Not a Gate: Adults with Diagnosed Diabetes)

- **Cohort Size (n):** 1,469 (Positives: 413, Prevalence: 28.11%)
- **AUROC (95% Bootstrap CI):** **0.7167** [0.6859 - 0.7462]
- **At Locked Threshold (`0.2445`):** Sensitivity = **77.48%**, Specificity = **53.50%**, PPV = **39.46%**
- **At High Risk Cutoff (`0.3823`):** Sensitivity = **34.62%**, Specificity = **87.31%**, PPV = **51.62%**

### Pre-Registered Acceptance Gates Audit (G1 - G5)

- Gate 1 (Test AUROC >= 0.65): **PASS** (0.7167)
- Gate 2 (Test Calibration Slope in [0.80, 1.20]): **FAIL** (1.439)
- Gate 3 (Test Sensitivity @ locked threshold >= 70%): **PASS** (77.48%)
- Gate 4 (Subgroup Sens >= 60%): **FAIL** (Worst: on_insulin=0.0=53.77%)
- Gate 5 (Brier Score < Naive Prevalence Brier): **PASS** (0.1812 vs 0.2021)
- **Overall FYP-1 Status:** **NOT SHIPPED (gate_2_calibration_slope_in_0_80_1_20, gate_4_subgroup_sens_ge_0_60)**

## Calibration
### Test Calibration Diagnostics

- **Brier Score:** 0.1812 (Naive Prevalence Brier: 0.20210189155411057)
- **Calibration-in-the-large (mean p - mean y):** +0.0028
- **Logistic Calibration Slope:** 1.439
- **Logistic Calibration Intercept:** +0.363

#### Reliability Table Across Decile Bins

| bin | n | mean_p | observed_rate |
| --- | --- | --- | --- |
| (0.0979, 0.166] | 147 | 0.1454036281962062 | 0.08163265306122448 |
| (0.166, 0.192] | 147 | 0.17998697769373323 | 0.1292517006802721 |
| (0.192, 0.211] | 147 | 0.20103885569733118 | 0.1564625850340136 |
| (0.211, 0.235] | 147 | 0.22339798229112232 | 0.16326530612244897 |
| (0.235, 0.257] | 147 | 0.2454843504652967 | 0.19727891156462585 |
| (0.257, 0.283] | 146 | 0.2688010195355695 | 0.2465753424657534 |
| (0.283, 0.324] | 147 | 0.3012684497842584 | 0.35374149659863946 |
| (0.324, 0.375] | 147 | 0.3487061065239228 | 0.4489795918367347 |
| (0.375, 0.447] | 147 | 0.408837354887014 | 0.5102040816326531 |
| (0.447, 0.739] | 147 | 0.5162871367571168 | 0.5238095238095238 |

## Subgroups
### Subgroup Breakdown on Held-Out Test Set

| Dimension | Group | Total (n) | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 693 | 193 | 27.8% | 0.7436 | 76.7% | 60.8% |
| sex_male | Male | 776 | 220 | 28.4% | 0.6925 | 78.2% | 46.9% |
| age_band | <50 | 197 | 71 | 36.0% | 0.6812 | 100.0% | 16.7% |
| age_band | 50-64 | 550 | 180 | 32.7% | 0.6930 | 82.8% | 39.5% |
| age_band | 65+ | 722 | 162 | 22.4% | 0.7112 | 61.7% | 71.1% |
| on_insulin | 0.0 | 1,043 | 199 | 19.1% | 0.6445 | 53.8% | 66.5% |
| on_insulin | 1.0 | 426 | 214 | 50.2% | 0.5610 | 99.5% | 1.9% |

### Feature Importance & Odds Ratios

| feature | coef_standardized | odds_ratio_per_1_sd |
| --- | --- | --- |
| on_insulin | 0.42910027092511316 | 1.5358750302867101 |
| age | -0.34383093607788157 | 0.7090487924866804 |
| on_diabetes_pills | 0.1514830927646735 | 1.1635586290838122 |
| bmi | -0.09385346657759937 | 0.9104161588625634 |
| sex_male | 0.061984971039363096 | 1.0639463545999934 |
| waist_cm | -0.05883814053650856 | 0.9428593675183966 |
| sbp | 0.05145257493040427 | 1.052799256030182 |
| dbp | 0.042088598313936174 | 1.0429868815364989 |
| ever_smoked_100 | -0.014733220250851685 | 0.9853747825782255 |

### Clinical Sanity Direction Check

| feature | coef | sign | direction | expected | concordant |
| --- | --- | --- | --- | --- | --- |
| age | -0.34383093607788157 | - | DOWN (-) | EMPIRICAL | True |
| sex_male | 0.061984971039363096 | + | UP (+) | UP (+) | True |
| bmi | -0.09385346657759937 | - | DOWN (-) | UP (+) | False |
| waist_cm | -0.05883814053650856 | - | DOWN (-) | UP (+) | False |
| ever_smoked_100 | -0.014733220250851685 | - | DOWN (-) | UP (+) | False |
| sbp | 0.05145257493040427 | + | UP (+) | UP (+) | True |
| dbp | 0.042088598313936174 | + | UP (+) | UP (+) | True |
| on_insulin | 0.42910027092511316 | + | UP (+) | UP (+) | True |
| on_diabetes_pills | 0.1514830927646735 | + | UP (+) | UP (+) | True |

### Global SHAP Feature Attributions

| feature | mean_abs_shap |
| --- | --- |
| on_insulin | 0.37915648315358036 |
| age | 0.2728676542904203 |
| on_diabetes_pills | 0.13247554408490275 |
| bmi | 0.07681124955460708 |
| sex_male | 0.06205648879712702 |
| waist_cm | 0.04999633678379265 |
| sbp | 0.036368533299351136 |
| dbp | 0.02922405087723594 |
| ever_smoked_100 | 0.014708682348157587 |

### Decision Curve Analysis (Net Benefit across Thresholds)

| pt | net_benefit_model | net_benefit_all | net_benefit_none |
| --- | --- | --- | --- |
| 0.01 | 0.2739 | 0.2739 | 0.0 |
| 0.02 | 0.2665 | 0.2665 | 0.0 |
| 0.03 | 0.2589 | 0.2589 | 0.0 |
| 0.04 | 0.2512 | 0.2512 | 0.0 |
| 0.05 | 0.2433 | 0.2433 | 0.0 |
| 0.06 | 0.2353 | 0.2353 | 0.0 |
| 0.07 | 0.227 | 0.227 | 0.0 |
| 0.08 | 0.2186 | 0.2186 | 0.0 |
| 0.09 | 0.21 | 0.21 | 0.0 |
| 0.1 | 0.2013 | 0.2013 | 0.0 |
| 0.11 | 0.1928 | 0.1923 | 0.0 |
| 0.12 | 0.1826 | 0.1831 | 0.0 |
| 0.13 | 0.1749 | 0.1737 | 0.0 |
| 0.14 | 0.165 | 0.1641 | 0.0 |
| 0.15 | 0.1584 | 0.1543 | 0.0 |
| 0.16 | 0.1525 | 0.1442 | 0.0 |
| 0.17 | 0.1443 | 0.1339 | 0.0 |
| 0.18 | 0.1373 | 0.1233 | 0.0 |
| 0.19 | 0.1329 | 0.1125 | 0.0 |
| 0.2 | 0.1283 | 0.1014 | 0.0 |

> **SHAP Method Notice:** Linear SHAP (shap.LinearExplainer) was used for logistic regression feature attribution, providing global mean |SHAP| and exact additive contributions for patient cases.

## Limitations
- **Cross-Sectional Glycemic Control:** Predicts current poor glycemic control (HbA1c >= 8.0%), not future longitudinal trajectory or diabetes incidence.
- **US Population Source:** Trained on US NHANES data (1999-2023); not calibrated or clinically validated on Pakistani patients or South Asian cohorts.
- **Remote Non-Lab Check-In Setting:** Relies on self-reported demographics, profile waist circumference, and home BP measurements; venous lab panels (lipids, eGFR) and diagnosis duration are not collected.
- **Insulin Association:** Insulin therapy strongly associates with poor glycemic control in observational survey data because patients with severe, progressive beta-cell failure are selectively prescribed insulin.
- **Intended Use:** Clinical decision support for providers with patient-facing risk tier (Low / Moderate / High); raw probability percentages are never exposed directly to patients.
