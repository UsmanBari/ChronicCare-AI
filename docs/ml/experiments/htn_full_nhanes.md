# ChronicCare AI — Model Evaluation Report

## Config
- **Name:** `htn_full_nhanes`
- **Target Label:** `hypertension_measured_130_80`
- **Population Filter:** `adults_without_htn_unmedicated`
- **Tier:** `full`
- **Features (7):** `age, sex_male, bmi, ever_smoked_100, told_diabetes, hba1c, waist_cm`
- **Candidate Models:** `lr, lr_balanced, rf, hgb`
- **Threshold Policy:** `{"type": "min_sensitivity", "value": 0.8}`
- **Seed:** `42`
- **Wall Time:** 13.27 seconds (0.2 minutes)

## Data
### Complete Case Cohort Statistics Across Temporal Splits

| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |
|---|---|---|---|---|---|
| `train_core` (1999-2012) | 25,380 | 4,614 | 20,766 | 6,186 | 29.79% |
| `validation` (2013-2016) | 7,299 | 690 | 6,609 | 1,642 | 24.84% |
| `test` (2017-2023) | 7,268 | 731 | 6,537 | 2,004 | 30.66% |

## Validation
### Candidate Model Validation Tuning

| Model | Best Hyperparameters | Val AUROC | Val Calibration Slope |
| --- | --- | --- | --- |
| lr | {"C": 0.01} | 0.7546 | 1.088 |
| lr_balanced | {"C": 0.01} | 0.7547 | 1.030 |
| rf | {"n_estimators": 100, "max_depth": 10, "min_samples_leaf": 50} | 0.7555 | 1.225 |
| hgb | {"learning_rate": 0.05, "max_leaf_nodes": 15, "min_samples_leaf": 20} | 0.7539 | 1.093 |

### Decision D10 Selection Rationale
- **Chosen Architecture:** `lr`
- **Selection Rule:** Logistic regression (lr) selected under D10 parsimony rule (plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: +0.0000)): best tree did not beat LR by >= 0.02 validation AUROC (tree gap: +0.0009).
- **Validation Calibration Gate:** `PASS` (Slope: 1.088)
- **D7 Locked Threshold:** `0.2442` (Val Sens: 80.02%, Val Spec: 59.86%)
- **D8 Risk Stratification Bands:** Low < `0.2442`, Moderate `0.2442` - `0.5336`, High >= `0.5336`

## Test
### Held-Out Test Discrimination & Diagnostic Performance (2017-2023)

- **Test AUROC (95% Bootstrap CI):** **0.7105** [0.6983 - 0.7230]
- **Test AUPRC (95% Bootstrap CI):** **0.4571** [0.4421 - 0.4746]
- **Locked Threshold:** `0.2442`
- **Test Sensitivity:** **80.49%**
- **Test Specificity:** **52.08%**
- **Test PPV:** **42.62%**
- **Test NPV:** **85.79%**
- **Confusion Matrix:** TP=1613, FP=2172, TN=2361, FN=391

### D11 Acceptance Gate Audit

- Gate 1 (Test AUROC >= 0.75): **FAIL** (0.7105)
- Gate 2 (Test Sensitivity >= 0.75): **PASS** (80.49%)
- Gate 3 (Test Calibration Slope 0.8-1.2): **PASS** (0.858)
- Gate 4 (Subgroup Sens >= 0.60): **FAIL** (Worst: 39.14%)
- Gate 5 (FULL beats BASIC on Val AUROC): **PASS (FULL 0.7546 vs BASIC 0.7540, diff: +0.0006)**
- **Overall FYP-1 Status:** **NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60)**

## Calibration
### Test Calibration Diagnostics

- **Brier Score:** 0.1919
- **Calibration-in-the-large (mean p - mean y):** +0.0115
- **Logistic Calibration Slope:** 0.858
- **Logistic Calibration Intercept:** -0.154

#### Reliability Table Across Decile Bins

| bin | n | mean_p | observed_rate |
| --- | --- | --- | --- |
| (0.0479, 0.11] | 654 | 0.08496277955166455 | 0.047400611620795105 |
| (0.11, 0.148] | 654 | 0.12860623642572097 | 0.12691131498470948 |
| (0.148, 0.187] | 653 | 0.16695435356176141 | 0.14854517611026033 |
| (0.187, 0.233] | 654 | 0.2098102066966148 | 0.21406727828746178 |
| (0.233, 0.286] | 654 | 0.2596543668261836 | 0.2874617737003058 |
| (0.286, 0.347] | 653 | 0.31515568907693436 | 0.3568147013782542 |
| (0.347, 0.414] | 654 | 0.37957311383544284 | 0.43730886850152906 |
| (0.414, 0.486] | 653 | 0.45002998213311535 | 0.4609494640122512 |
| (0.486, 0.578] | 654 | 0.531088656879936 | 0.5076452599388379 |
| (0.578, 0.871] | 654 | 0.6550504814105254 | 0.4785932721712538 |

## Subgroups
### Subgroup Breakdown on Held-Out Test Set

| Dimension | Group | Total (n) | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 3,519 | 917 | 26.1% | 0.7356 | 75.2% | 61.3% |
| sex_male | Male | 3,018 | 1,087 | 36.0% | 0.6642 | 84.9% | 39.7% |
| age_band | 18-39 | 2,843 | 511 | 18.0% | 0.7288 | 39.1% | 87.5% |
| age_band | 40-59 | 1,935 | 689 | 35.6% | 0.6389 | 88.4% | 25.7% |
| age_band | 60+ | 1,759 | 804 | 45.7% | 0.5442 | 100.0% | 0.0% |
| race_eth | Mexican American | 789 | 217 | 27.5% | 0.7311 | 79.3% | 58.0% |
| race_eth | Other Hispanic | 677 | 170 | 25.1% | 0.7271 | 80.6% | 57.0% |
| race_eth | Non-Hispanic White | 3,131 | 973 | 31.1% | 0.6904 | 84.1% | 44.9% |
| race_eth | Non-Hispanic Black | 889 | 324 | 36.4% | 0.7484 | 77.5% | 60.2% |
| race_eth | Other Race / Multi-Racial | 1,051 | 320 | 30.4% | 0.7189 | 73.4% | 59.0% |
| cycle | 2017-2018 | 3,044 | 955 | 31.4% | 0.7398 | 80.2% | 57.2% |
| cycle | 2021-2023 | 3,493 | 1,049 | 30.0% | 0.6860 | 80.7% | 47.7% |

### Feature Importance & Explanations

| feature | coef_standardized | odds_ratio_per_1_sd |
| --- | --- | --- |
| age | 0.7612119541579994 | 2.1408692842730157 |
| sex_male | 0.3132460164871242 | 1.3678580052581424 |
| bmi | 0.25080749949508885 | 1.285062685303977 |
| hba1c | 0.0708788380291994 | 1.0734511565311045 |
| told_diabetes | -0.0665992928843063 | 0.9355700157989106 |
| ever_smoked_100 | -0.03686426987377434 | 0.963806944109689 |
| waist_cm | 0.01623935190826794 | 1.0163719268549838 |

> **SHAP Method Notice:** SHAP NOT USED: pip install shap requires adding 5 unpinned dependencies (shap, slicer, tqdm, numba, and llvmlite with a 41.9 MB LLVM binary) not in ml/requirements.txt. As specified in A3, CPU-friendly standardized odds ratios per 1 SD are used for logistic regression and scikit-learn validation permutation importance (n_repeats=10) is used for tree models.

## Limitations
- **Temporal Shift:** Evaluated strictly on temporal hold-out cohorts (2017-2023) following historical fitting (1999-2012).
- **External Validation:** BRFSS validation cannot evaluate undiagnosed labels because BRFSS lacks biological specimen assays and cuff measurements.
- **Complete Cases:** Complete case analysis drops missing survey records without synthetic imputation.

- **US Survey Population:** Trained and evaluated on US NHANES survey participants; not directly representative of South Asian or Pakistani diaspora physiology.
- **Survey Weights Omitted in Training:** Standard maximum-likelihood estimation was used without complex survey pseudo-weights to reflect empirical prediction performance.
- **NHANES Age Top-Coding:** Participants aged 80+ (or 85+ in early cycles) have capped ages, which introduces minor attenuation at extreme elderly ages.
- **Self-Report Target Inclusion:** Self-reported diabetes diagnoses may omit undiagnosed individuals or contain recall noise compared to pure biochemical definitions.
