# ChronicCare AI — Model Evaluation Report

## Config
- **Name:** `htn_basic_nhanes`
- **Target Label:** `hypertension_measured_130_80`
- **Population Filter:** `adults_without_htn_unmedicated`
- **Tier:** `basic`
- **Features (5):** `age, sex_male, bmi, ever_smoked_100, told_diabetes`
- **Candidate Models:** `lr, lr_balanced, rf, hgb`
- **Threshold Policy:** `{"type": "min_sensitivity", "value": 0.8}`
- **Seed:** `42`
- **Wall Time:** 13.26 seconds (0.2 minutes)

## Data
### Complete Case Cohort Statistics Across Temporal Splits

| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |
|---|---|---|---|---|---|
| `train_core` (1999-2012) | 25,380 | 3,319 | 22,061 | 6,623 | 30.02% |
| `validation` (2013-2016) | 7,299 | 173 | 7,126 | 1,803 | 25.30% |
| `test` (2017-2023) | 7,268 | 231 | 7,037 | 2,158 | 30.67% |

## Validation
### Candidate Model Validation Tuning

| Model | Best Hyperparameters | Val AUROC | Val Calibration Slope |
| --- | --- | --- | --- |
| lr | {"C": 0.01} | 0.7540 | 1.066 |
| lr_balanced | {"C": 1.0} | 0.7539 | 0.982 |
| rf | {"n_estimators": 100, "max_depth": 10, "min_samples_leaf": 50} | 0.7541 | 1.084 |
| hgb | {"learning_rate": 0.1, "max_leaf_nodes": 31, "min_samples_leaf": 20} | 0.7572 | 1.072 |

### Decision D10 Selection Rationale
- **Chosen Architecture:** `lr`
- **Selection Rule:** Logistic regression (lr) selected under D10 parsimony rule (plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: -0.0001)): best tree did not beat LR by >= 0.02 validation AUROC (tree gap: +0.0032).
- **Validation Calibration Gate:** `PASS` (Slope: 1.066)
- **D7 Locked Threshold:** `0.2443` (Val Sens: 80.03%, Val Spec: 60.17%)
- **D8 Risk Stratification Bands:** Low < `0.2443`, Moderate `0.2443` - `0.5387`, High >= `0.5387`

## Test
### Held-Out Test Discrimination & Diagnostic Performance (2017-2023)

- **Test AUROC (95% Bootstrap CI):** **0.7148** [0.7022 - 0.7262]
- **Test AUPRC (95% Bootstrap CI):** **0.4620** [0.4478 - 0.4790]
- **Locked Threshold:** `0.2443`
- **Test Sensitivity:** **80.40%**
- **Test Specificity:** **52.65%**
- **Test PPV:** **42.89%**
- **Test NPV:** **85.86%**
- **Confusion Matrix:** TP=1735, FP=2310, TN=2569, FN=423

### D11 Acceptance Gate Audit

- Gate 1 (Test AUROC >= 0.75): **FAIL** (0.7148)
- Gate 2 (Test Sensitivity >= 0.75): **PASS** (80.40%)
- Gate 3 (Test Calibration Slope 0.8-1.2): **PASS** (0.869)
- Gate 4 (Subgroup Sens >= 0.60): **FAIL** (Worst: 38.41%)
- Gate 5 (FULL beats BASIC on Val AUROC): **N/A (BASIC)**
- **Overall FYP-1 Status:** **NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60)**

## Calibration
### Test Calibration Diagnostics

- **Brier Score:** 0.1910
- **Calibration-in-the-large (mean p - mean y):** +0.0107
- **Logistic Calibration Slope:** 0.869
- **Logistic Calibration Intercept:** -0.143

#### Reliability Table Across Decile Bins

| bin | n | mean_p | observed_rate |
| --- | --- | --- | --- |
| (0.0484, 0.108] | 704 | 0.08358332441888966 | 0.03835227272727273 |
| (0.108, 0.146] | 704 | 0.12729950476395346 | 0.11931818181818182 |
| (0.146, 0.185] | 703 | 0.16565041971377 | 0.155049786628734 |
| (0.185, 0.231] | 704 | 0.20834894610268037 | 0.21732954545454544 |
| (0.231, 0.285] | 704 | 0.25715605060201896 | 0.28125 |
| (0.285, 0.346] | 703 | 0.31335285355438525 | 0.3541963015647226 |
| (0.346, 0.411] | 704 | 0.3778500342714994 | 0.4375 |
| (0.411, 0.486] | 703 | 0.4489425478361528 | 0.47083926031294454 |
| (0.486, 0.582] | 704 | 0.5329539905982404 | 0.5113636363636364 |
| (0.582, 0.883] | 704 | 0.6585459994052032 | 0.4815340909090909 |

## Subgroups
### Subgroup Breakdown on Held-Out Test Set

| Dimension | Group | Total (n) | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 3,812 | 999 | 26.2% | 0.7428 | 75.3% | 62.2% |
| sex_male | Male | 3,225 | 1,159 | 35.9% | 0.6657 | 84.8% | 39.6% |
| age_band | 18-39 | 3,104 | 552 | 17.8% | 0.7345 | 38.4% | 87.5% |
| age_band | 40-59 | 2,062 | 744 | 36.1% | 0.6363 | 88.8% | 25.4% |
| age_band | 60+ | 1,871 | 862 | 46.1% | 0.5458 | 100.0% | 0.0% |
| race_eth | Mexican American | 835 | 229 | 27.4% | 0.7434 | 80.3% | 58.9% |
| race_eth | Other Hispanic | 721 | 183 | 25.4% | 0.7288 | 78.7% | 56.3% |
| race_eth | Non-Hispanic White | 3,324 | 1,037 | 31.2% | 0.6925 | 84.5% | 45.3% |
| race_eth | Non-Hispanic Black | 1,000 | 364 | 36.4% | 0.7513 | 76.9% | 60.8% |
| race_eth | Other Race / Multi-Racial | 1,157 | 345 | 29.8% | 0.7251 | 72.8% | 60.0% |
| cycle | 2017-2018 | 3,274 | 1,034 | 31.6% | 0.7464 | 80.4% | 58.1% |
| cycle | 2021-2023 | 3,763 | 1,124 | 29.9% | 0.6883 | 80.4% | 48.0% |

### Feature Importance & Explanations

| feature | coef_standardized | odds_ratio_per_1_sd |
| --- | --- | --- |
| age | 0.7821057393019804 | 2.1860707172549563 |
| sex_male | 0.32065804451194424 | 1.3780342739326454 |
| bmi | 0.2804888732497564 | 1.3237768132464764 |
| told_diabetes | -0.036109017092221626 | 0.9645351369353223 |
| ever_smoked_100 | -0.032722260560178004 | 0.9678073205276071 |

> **SHAP Method Notice:** SHAP NOT USED: pip install shap requires adding 5 unpinned dependencies (shap, slicer, tqdm, numba, and llvmlite with a 41.9 MB LLVM binary) not in ml/requirements.txt. As specified in A3, CPU-friendly standardized odds ratios per 1 SD are used for logistic regression and scikit-learn validation permutation importance (n_repeats=10) is used for tree models.

## Limitations
- **Temporal Shift:** Evaluated strictly on temporal hold-out cohorts (2017-2023) following historical fitting (1999-2012).
- **External Validation:** BRFSS validation cannot evaluate undiagnosed labels because BRFSS lacks biological specimen assays and cuff measurements.
- **Complete Cases:** Complete case analysis drops missing survey records without synthetic imputation.

- **US Survey Population:** Trained and evaluated on US NHANES survey participants; not directly representative of South Asian or Pakistani diaspora physiology.
- **Survey Weights Omitted in Training:** Standard maximum-likelihood estimation was used without complex survey pseudo-weights to reflect empirical prediction performance.
- **NHANES Age Top-Coding:** Participants aged 80+ (or 85+ in early cycles) have capped ages, which introduces minor attenuation at extreme elderly ages.
- **Self-Report Target Inclusion:** Self-reported diabetes diagnoses may omit undiagnosed individuals or contain recall noise compared to pure biochemical definitions.
