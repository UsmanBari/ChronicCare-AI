# ChronicCare AI — Model Evaluation Report

## Config
- **Name:** `diabetes_full_nhanes`
- **Target Label:** `diabetes_undiagnosed`
- **Population Filter:** `adults_without_diabetes`
- **Tier:** `full`
- **Features (8):** `age, sex_male, bmi, ever_smoked_100, told_high_bp, sbp, dbp, waist_cm`
- **Candidate Models:** `lr, lr_balanced, rf, hgb`
- **Threshold Policy:** `{"type": "min_sensitivity", "value": 0.8}`
- **Seed:** `42`
- **Wall Time:** 16.98 seconds (0.3 minutes)

## Data
### Complete Case Cohort Statistics Across Temporal Splits

| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |
|---|---|---|---|---|---|
| `train_core` (1999-2012) | 32,647 | 5,199 | 27,448 | 1,043 | 3.80% |
| `validation` (2013-2016) | 9,371 | 657 | 8,714 | 336 | 3.86% |
| `test` (2017-2023) | 9,261 | 580 | 8,681 | 360 | 4.15% |

## Validation
### Candidate Model Validation Tuning

| Model | Best Hyperparameters | Val AUROC | Val Calibration Slope |
| --- | --- | --- | --- |
| lr | {"C": 0.1} | 0.7617 | 0.857 |
| lr_balanced | {"C": 0.01} | 0.7622 | 0.756 |
| rf | {"n_estimators": 100, "max_depth": 5, "min_samples_leaf": 10} | 0.7627 | 1.047 |
| hgb | {"learning_rate": 0.05, "max_leaf_nodes": 15, "min_samples_leaf": 20} | 0.7549 | 0.789 |

### Decision D10 Selection Rationale
- **Chosen Architecture:** `lr`
- **Selection Rule:** Logistic regression (lr) selected under D10 parsimony rule (plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: +0.0005)): best tree did not beat LR by >= 0.02 validation AUROC (tree gap: +0.0010).
- **Validation Calibration Gate:** `PASS` (Slope: 0.857)
- **D7 Locked Threshold:** `0.0276` (Val Sens: 80.06%, Val Spec: 60.07%)
- **D8 Risk Stratification Bands:** Low < `0.0276`, Moderate `0.0276` - `0.0871`, High >= `0.0871`

## Test
### Held-Out Test Discrimination & Diagnostic Performance (2017-2023)

- **Test AUROC (95% Bootstrap CI):** **0.7527** [0.7293 - 0.7748]
- **Test AUPRC (95% Bootstrap CI):** **0.1008** [0.0891 - 0.1165]
- **Locked Threshold:** `0.0276`
- **Test Sensitivity:** **85.28%**
- **Test Specificity:** **52.23%**
- **Test PPV:** **7.17%**
- **Test NPV:** **98.80%**
- **Confusion Matrix:** TP=307, FP=3975, TN=4346, FN=53

### D11 Acceptance Gate Audit

- Gate 1 (Test AUROC >= 0.75): **PASS** (0.7527)
- Gate 2 (Test Sensitivity >= 0.75): **PASS** (85.28%)
- Gate 3 (Test Calibration Slope 0.8-1.2): **PASS** (0.848)
- Gate 4 (Subgroup Sens >= 0.60): **PASS** (Worst: 76.00%)
- Gate 5 (FULL beats BASIC on Val AUROC): **PASS (FULL 0.7617 vs BASIC 0.7542, diff: +0.0075)**
- **Overall FYP-1 Status:** **SHIP CANDIDATE**

## Calibration
### Test Calibration Diagnostics

- **Brier Score:** 0.0389
- **Calibration-in-the-large (mean p - mean y):** +0.0011
- **Logistic Calibration Slope:** 0.848
- **Logistic Calibration Intercept:** -0.442

#### Reliability Table Across Decile Bins

| bin | n | mean_p | observed_rate |
| --- | --- | --- | --- |
| (1.0000000000000026e-05, 0.0053] | 869 | 0.003617780853469289 | 0.0011507479861910242 |
| (0.0053, 0.00898] | 868 | 0.007057861975080984 | 0.00576036866359447 |
| (0.00898, 0.0136] | 868 | 0.011313178509029081 | 0.008064516129032258 |
| (0.0136, 0.0196] | 868 | 0.016453678794139844 | 0.014976958525345621 |
| (0.0196, 0.027] | 868 | 0.023129700089977338 | 0.029953917050691243 |
| (0.027, 0.0358] | 868 | 0.03119676397979034 | 0.04032258064516129 |
| (0.0358, 0.0478] | 868 | 0.04157750439238628 | 0.05184331797235023 |
| (0.0478, 0.0664] | 868 | 0.056254336800601185 | 0.06105990783410138 |
| (0.0664, 0.0989] | 868 | 0.0805090820901037 | 0.08525345622119816 |
| (0.0989, 0.584] | 868 | 0.1551088981545702 | 0.11635944700460829 |

## Subgroups
### Subgroup Breakdown on Held-Out Test Set

| Dimension | Group | Total (n) | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 4,689 | 189 | 4.0% | 0.7655 | 81.5% | 57.6% |
| sex_male | Male | 3,992 | 171 | 4.3% | 0.7377 | 89.5% | 45.9% |
| age_band | 18-39 | 3,107 | 47 | 1.5% | 0.8232 | 63.8% | 86.3% |
| age_band | 40-59 | 2,556 | 125 | 4.9% | 0.7021 | 76.0% | 52.6% |
| age_band | 60+ | 3,018 | 188 | 6.2% | 0.6752 | 96.8% | 15.1% |
| race_eth | Mexican American | 888 | 49 | 5.5% | 0.7642 | 79.6% | 62.1% |
| race_eth | Other Hispanic | 856 | 42 | 4.9% | 0.7691 | 83.3% | 60.0% |
| race_eth | Non-Hispanic White | 4,258 | 125 | 2.9% | 0.7953 | 93.6% | 45.1% |
| race_eth | Non-Hispanic Black | 1,388 | 88 | 6.3% | 0.7267 | 83.0% | 48.7% |
| race_eth | Other Race / Multi-Racial | 1,291 | 56 | 4.3% | 0.7864 | 76.8% | 68.1% |
| cycle | 2017-2018 | 4,010 | 197 | 4.9% | 0.7359 | 81.7% | 54.0% |
| cycle | 2021-2023 | 4,671 | 163 | 3.5% | 0.7780 | 89.6% | 50.8% |

### Feature Importance & Explanations

| feature | coef_standardized | odds_ratio_per_1_sd |
| --- | --- | --- |
| age | 0.5946617619236584 | 1.8124178125591928 |
| waist_cm | 0.5073138033655146 | 1.6608238980477357 |
| bmi | 0.16273043189475622 | 1.1767194409002237 |
| sbp | 0.15733415611691628 | 1.1703866404203769 |
| told_high_bp | 0.09783171040643994 | 1.102777183567532 |
| ever_smoked_100 | 0.09686429841817035 | 1.101710859570231 |
| sex_male | 0.0859985865734003 | 1.0898047879449644 |
| dbp | 0.008575505947103983 | 1.0086123809300707 |

> **SHAP Method Notice:** SHAP NOT USED: pip install shap requires adding 5 unpinned dependencies (shap, slicer, tqdm, numba, and llvmlite with a 41.9 MB LLVM binary) not in ml/requirements.txt. As specified in A3, CPU-friendly standardized odds ratios per 1 SD are used for logistic regression and scikit-learn validation permutation importance (n_repeats=10) is used for tree models.

## Limitations
- **Temporal Shift:** Evaluated strictly on temporal hold-out cohorts (2017-2023) following historical fitting (1999-2012).
- **External Validation:** BRFSS validation cannot evaluate undiagnosed labels because BRFSS lacks biological specimen assays and cuff measurements.
- **Complete Cases:** Complete case analysis drops missing survey records without synthetic imputation.

- **US Survey Population:** Trained and evaluated on US NHANES survey participants; not directly representative of South Asian or Pakistani diaspora physiology.
- **Survey Weights Omitted in Training:** Standard maximum-likelihood estimation was used without complex survey pseudo-weights to reflect empirical prediction performance.
- **NHANES Age Top-Coding:** Participants aged 80+ (or 85+ in early cycles) have capped ages, which introduces minor attenuation at extreme elderly ages.
- **Self-Report Target Inclusion:** Self-reported diabetes diagnoses may omit undiagnosed individuals or contain recall noise compared to pure biochemical definitions.
