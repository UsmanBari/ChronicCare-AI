# ChronicCare AI — Model Evaluation Report

## Config
- **Name:** `diabetes_basic_nhanes`
- **Target Label:** `diabetes_undiagnosed`
- **Population Filter:** `adults_without_diabetes`
- **Tier:** `basic`
- **Features (5):** `age, sex_male, bmi, ever_smoked_100, told_high_bp`
- **Candidate Models:** `lr, lr_balanced, rf, hgb`
- **Threshold Policy:** `{"type": "min_sensitivity", "value": 0.8}`
- **Seed:** `42`
- **Wall Time:** 14.55 seconds (0.2 minutes)

## Data
### Complete Case Cohort Statistics Across Temporal Splits

| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |
|---|---|---|---|---|---|
| `train_core` (1999-2012) | 32,647 | 3,563 | 29,084 | 1,135 | 3.90% |
| `validation` (2013-2016) | 9,371 | 107 | 9,264 | 372 | 4.02% |
| `test` (2017-2023) | 9,261 | 144 | 9,117 | 388 | 4.26% |

## Validation
### Candidate Model Validation Tuning

| Model | Best Hyperparameters | Val AUROC | Val Calibration Slope |
| --- | --- | --- | --- |
| lr | {"C": 10.0} | 0.7542 | 0.850 |
| lr_balanced | {"C": 0.1} | 0.7540 | 0.716 |
| rf | {"n_estimators": 100, "max_depth": 5, "min_samples_leaf": 50} | 0.7537 | 0.977 |
| hgb | {"learning_rate": 0.05, "max_leaf_nodes": 15, "min_samples_leaf": 20} | 0.7481 | 0.792 |

### Decision D10 Selection Rationale
- **Chosen Architecture:** `lr`
- **Selection Rule:** Logistic regression (lr) selected under D10 parsimony rule (plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: -0.0002)): best tree did not beat LR by >= 0.02 validation AUROC (tree gap: -0.0005).
- **Validation Calibration Gate:** `PASS` (Slope: 0.850)
- **D7 Locked Threshold:** `0.0287` (Val Sens: 80.11%, Val Spec: 59.10%)
- **D8 Risk Stratification Bands:** Low < `0.0287`, Moderate `0.0287` - `0.0863`, High >= `0.0863`

## Test
### Held-Out Test Discrimination & Diagnostic Performance (2017-2023)

- **Test AUROC (95% Bootstrap CI):** **0.7403** [0.7182 - 0.7616]
- **Test AUPRC (95% Bootstrap CI):** **0.0997** [0.0882 - 0.1177]
- **Locked Threshold:** `0.0287`
- **Test Sensitivity:** **85.05%**
- **Test Specificity:** **51.40%**
- **Test PPV:** **7.22%**
- **Test NPV:** **98.72%**
- **Confusion Matrix:** TP=330, FP=4242, TN=4487, FN=58

### D11 Acceptance Gate Audit

- Gate 1 (Test AUROC >= 0.75): **FAIL** (0.7403)
- Gate 2 (Test Sensitivity >= 0.75): **PASS** (85.05%)
- Gate 3 (Test Calibration Slope 0.8-1.2): **PASS** (0.820)
- Gate 4 (Subgroup Sens >= 0.60): **FAIL** (Worst: 58.82%)
- Gate 5 (FULL beats BASIC on Val AUROC): **N/A (BASIC)**
- **Overall FYP-1 Status:** **NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60)**

## Calibration
### Test Calibration Diagnostics

- **Brier Score:** 0.0401
- **Calibration-in-the-large (mean p - mean y):** +0.0016
- **Logistic Calibration Slope:** 0.820
- **Logistic Calibration Intercept:** -0.531

#### Reliability Table Across Decile Bins

| bin | n | mean_p | observed_rate |
| --- | --- | --- | --- |
| (0.00074, 0.00628] | 912 | 0.004410192223411953 | 0.0021929824561403508 |
| (0.00628, 0.0105] | 912 | 0.008330405517177633 | 0.006578947368421052 |
| (0.0105, 0.0153] | 911 | 0.012786480524861858 | 0.005488474204171241 |
| (0.0153, 0.0213] | 912 | 0.018162651739666615 | 0.025219298245614034 |
| (0.0213, 0.0289] | 912 | 0.02494116371044312 | 0.02412280701754386 |
| (0.0289, 0.038] | 911 | 0.03315162875885752 | 0.05378704720087816 |
| (0.038, 0.0498] | 912 | 0.04352299319667044 | 0.043859649122807015 |
| (0.0498, 0.0667] | 911 | 0.05758462668377144 | 0.06476399560922064 |
| (0.0667, 0.0998] | 912 | 0.0811709659674963 | 0.08771929824561403 |
| (0.0998, 0.763] | 912 | 0.15757961872615056 | 0.1118421052631579 |

## Subgroups
### Subgroup Breakdown on Held-Out Test Set

| Dimension | Group | Total (n) | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 4,966 | 207 | 4.2% | 0.7510 | 80.2% | 57.5% |
| sex_male | Male | 4,151 | 181 | 4.4% | 0.7292 | 90.6% | 44.1% |
| age_band | 18-39 | 3,254 | 51 | 1.6% | 0.8150 | 58.8% | 87.9% |
| age_band | 40-59 | 2,668 | 133 | 5.0% | 0.6825 | 77.4% | 51.9% |
| age_band | 60+ | 3,195 | 204 | 6.4% | 0.6647 | 96.6% | 11.9% |
| race_eth | Mexican American | 928 | 52 | 5.6% | 0.7651 | 76.9% | 62.4% |
| race_eth | Other Hispanic | 908 | 46 | 5.1% | 0.7572 | 87.0% | 57.8% |
| race_eth | Non-Hispanic White | 4,433 | 137 | 3.1% | 0.7844 | 91.2% | 44.9% |
| race_eth | Non-Hispanic Black | 1,478 | 93 | 6.3% | 0.7007 | 84.9% | 46.6% |
| race_eth | Other Race / Multi-Racial | 1,370 | 60 | 4.4% | 0.7627 | 76.7% | 66.3% |
| cycle | 2017-2018 | 4,223 | 210 | 5.0% | 0.7229 | 81.4% | 53.7% |
| cycle | 2021-2023 | 4,894 | 178 | 3.6% | 0.7682 | 89.3% | 49.4% |

### Feature Importance & Explanations

| feature | coef_standardized | odds_ratio_per_1_sd |
| --- | --- | --- |
| age | 0.7231069754770973 | 2.0608262105528707 |
| bmi | 0.5815299439804462 | 1.7887730608780776 |
| sex_male | 0.21464326846805165 | 1.2394196780135647 |
| told_high_bp | 0.1375856372543667 | 1.14749997051132 |
| ever_smoked_100 | 0.10847156092529597 | 1.1145732106568131 |

> **SHAP Method Notice:** SHAP NOT USED: pip install shap requires adding 5 unpinned dependencies (shap, slicer, tqdm, numba, and llvmlite with a 41.9 MB LLVM binary) not in ml/requirements.txt. As specified in A3, CPU-friendly standardized odds ratios per 1 SD are used for logistic regression and scikit-learn validation permutation importance (n_repeats=10) is used for tree models.

## Limitations
- **Temporal Shift:** Evaluated strictly on temporal hold-out cohorts (2017-2023) following historical fitting (1999-2012).
- **External Validation:** BRFSS validation cannot evaluate undiagnosed labels because BRFSS lacks biological specimen assays and cuff measurements.
- **Complete Cases:** Complete case analysis drops missing survey records without synthetic imputation.

- **US Survey Population:** Trained and evaluated on US NHANES survey participants; not directly representative of South Asian or Pakistani diaspora physiology.
- **Survey Weights Omitted in Training:** Standard maximum-likelihood estimation was used without complex survey pseudo-weights to reflect empirical prediction performance.
- **NHANES Age Top-Coding:** Participants aged 80+ (or 85+ in early cycles) have capped ages, which introduces minor attenuation at extreme elderly ages.
- **Self-Report Target Inclusion:** Self-reported diabetes diagnoses may omit undiagnosed individuals or contain recall noise compared to pure biochemical definitions.
