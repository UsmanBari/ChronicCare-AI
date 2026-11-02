# ChronicCare AI — Model Evaluation Report

## Config
- **Name:** `htn_ref_age_sex_bmi`
- **Target Label:** `hypertension_measured_130_80`
- **Population Filter:** `adults_without_htn_unmedicated`
- **Tier:** `basic`
- **Features (3):** `age, sex_male, bmi`
- **Candidate Models:** `lr, lr_balanced, rf, hgb`
- **Threshold Policy:** `{"type": "min_sensitivity", "value": 0.8}`
- **Seed:** `42`
- **Wall Time:** 13.58 seconds (0.2 minutes)

## Data
### Complete Case Cohort Statistics Across Temporal Splits

| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |
|---|---|---|---|---|---|
| `train_core` (1999-2012) | 25,380 | 347 | 25,033 | 7,000 | 27.96% |
| `validation` (2013-2016) | 7,299 | 53 | 7,246 | 1,849 | 25.52% |
| `test` (2017-2023) | 7,268 | 62 | 7,206 | 2,220 | 30.81% |

## Validation
### Candidate Model Validation Tuning

| Model | Best Hyperparameters | Val AUROC | Val Calibration Slope |
| --- | --- | --- | --- |
| lr | {"C": 0.1} | 0.7533 | 1.026 |
| lr_balanced | {"C": 0.01} | 0.7531 | 0.988 |
| rf | {"n_estimators": 100, "max_depth": 10, "min_samples_leaf": 50} | 0.7551 | 1.043 |
| hgb | {"learning_rate": 0.05, "max_leaf_nodes": 31, "min_samples_leaf": 20} | 0.7554 | 1.067 |

### Decision D10 Selection Rationale
- **Chosen Architecture:** `lr`
- **Selection Rule:** Logistic regression (lr) selected under D10 parsimony rule (plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: -0.0002)): best tree did not beat LR by >= 0.02 validation AUROC (tree gap: +0.0021).
- **Validation Calibration Gate:** `PASS` (Slope: 1.026)
- **D7 Locked Threshold:** `0.2437` (Val Sens: 80.04%, Val Spec: 60.09%)
- **D8 Risk Stratification Bands:** Low < `0.2437`, Moderate `0.2437` - `0.5476`, High >= `0.5476`

## Test
### Held-Out Test Discrimination & Diagnostic Performance (2017-2023)

- **Test AUROC (95% Bootstrap CI):** **0.7150** [0.7030 - 0.7269]
- **Test AUPRC (95% Bootstrap CI):** **0.4629** [0.4486 - 0.4806]
- **Locked Threshold:** `0.2437`
- **Test Sensitivity:** **80.14%**
- **Test Specificity:** **53.11%**
- **Test PPV:** **43.21%**
- **Test NPV:** **85.72%**
- **Confusion Matrix:** TP=1779, FP=2338, TN=2648, FN=441

### D11 Acceptance Gate Audit

- Gate 1 (Test AUROC >= 0.75): **FAIL** (0.7150)
- Gate 2 (Test Sensitivity >= 0.75): **PASS** (80.14%)
- Gate 3 (Test Calibration Slope 0.8-1.2): **PASS** (0.840)
- Gate 4 (Subgroup Sens >= 0.60): **FAIL** (Worst: 37.99%)
- Gate 5 (FULL beats BASIC on Val AUROC): **N/A (BASIC)**
- **Overall FYP-1 Status:** **NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60)**

## Calibration
### Test Calibration Diagnostics

- **Brier Score:** 0.1918
- **Calibration-in-the-large (mean p - mean y):** +0.0112
- **Logistic Calibration Slope:** 0.840
- **Logistic Calibration Intercept:** -0.163

#### Reliability Table Across Decile Bins

| bin | n | mean_p | observed_rate |
| --- | --- | --- | --- |
| (0.0441, 0.104] | 721 | 0.0791067385716848 | 0.04160887656033287 |
| (0.104, 0.142] | 721 | 0.1231067364172325 | 0.10957004160887657 |
| (0.142, 0.183] | 720 | 0.16255532229010988 | 0.15694444444444444 |
| (0.183, 0.231] | 721 | 0.2064861449172022 | 0.22330097087378642 |
| (0.231, 0.285] | 720 | 0.2569105238104684 | 0.2875 |
| (0.285, 0.349] | 721 | 0.31549300653212325 | 0.34951456310679613 |
| (0.349, 0.417] | 720 | 0.3816552381751855 | 0.4444444444444444 |
| (0.417, 0.495] | 721 | 0.4551117802669115 | 0.47156726768377255 |
| (0.495, 0.591] | 720 | 0.5412970199080681 | 0.5111111111111111 |
| (0.591, 0.885] | 721 | 0.6712358755623287 | 0.4854368932038835 |

## Subgroups
### Subgroup Breakdown on Held-Out Test Set

| Dimension | Group | Total (n) | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 3,903 | 1,031 | 26.4% | 0.7444 | 74.7% | 62.9% |
| sex_male | Male | 3,303 | 1,189 | 36.0% | 0.6650 | 84.9% | 39.8% |
| age_band | 18-39 | 3,143 | 558 | 17.8% | 0.7377 | 38.0% | 88.2% |
| age_band | 40-59 | 2,113 | 758 | 35.9% | 0.6335 | 87.5% | 27.2% |
| age_band | 60+ | 1,950 | 904 | 46.4% | 0.5449 | 100.0% | 0.0% |
| race_eth | Mexican American | 855 | 238 | 27.8% | 0.7417 | 80.7% | 58.3% |
| race_eth | Other Hispanic | 741 | 191 | 25.8% | 0.7310 | 78.0% | 57.5% |
| race_eth | Non-Hispanic White | 3,389 | 1,058 | 31.2% | 0.6923 | 84.3% | 45.6% |
| race_eth | Non-Hispanic Black | 1,026 | 377 | 36.7% | 0.7517 | 75.9% | 61.6% |
| race_eth | Other Race / Multi-Racial | 1,195 | 356 | 29.8% | 0.7257 | 73.0% | 60.5% |
| cycle | 2017-2018 | 3,351 | 1,069 | 31.9% | 0.7468 | 80.4% | 58.5% |
| cycle | 2021-2023 | 3,855 | 1,151 | 29.9% | 0.6881 | 79.8% | 48.6% |

### Feature Importance & Explanations

| feature | coef_standardized | odds_ratio_per_1_sd |
| --- | --- | --- |
| age | 0.8311412998540988 | 2.295937598774997 |
| sex_male | 0.3315046538692029 | 1.3930626293945163 |
| bmi | 0.29730930724361887 | 1.3462316342531562 |

> **SHAP Method Notice:** SHAP NOT USED: pip install shap requires adding 5 unpinned dependencies (shap, slicer, tqdm, numba, and llvmlite with a 41.9 MB LLVM binary) not in ml/requirements.txt. As specified in A3, CPU-friendly standardized odds ratios per 1 SD are used for logistic regression and scikit-learn validation permutation importance (n_repeats=10) is used for tree models.

## Limitations
- **Temporal Shift:** Evaluated strictly on temporal hold-out cohorts (2017-2023) following historical fitting (1999-2012).
- **External Validation:** BRFSS validation cannot evaluate undiagnosed labels because BRFSS lacks biological specimen assays and cuff measurements.
- **Complete Cases:** Complete case analysis drops missing survey records without synthetic imputation.

- **US Survey Population:** Trained and evaluated on US NHANES survey participants; not directly representative of South Asian or Pakistani diaspora physiology.
- **Survey Weights Omitted in Training:** Standard maximum-likelihood estimation was used without complex survey pseudo-weights to reflect empirical prediction performance.
- **NHANES Age Top-Coding:** Participants aged 80+ (or 85+ in early cycles) have capped ages, which introduces minor attenuation at extreme elderly ages.
- **Self-Report Target Inclusion:** Self-reported diabetes diagnoses may omit undiagnosed individuals or contain recall noise compared to pure biochemical definitions.
