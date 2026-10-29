# ChronicCare AI — Model Evaluation Report

## Config
- **Name:** `diabetes_ref_age_sex_bmi`
- **Target Label:** `diabetes_undiagnosed`
- **Population Filter:** `adults_without_diabetes`
- **Tier:** `basic`
- **Features (3):** `age, sex_male, bmi`
- **Candidate Models:** `lr, lr_balanced, rf, hgb`
- **Threshold Policy:** `{"type": "min_sensitivity", "value": 0.8}`
- **Seed:** `42`
- **Wall Time:** 14.75 seconds (0.2 minutes)

## Data
### Complete Case Cohort Statistics Across Temporal Splits

| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |
|---|---|---|---|---|---|
| `train_core` (1999-2012) | 32,647 | 566 | 32,081 | 1,158 | 3.61% |
| `validation` (2013-2016) | 9,371 | 93 | 9,278 | 373 | 4.02% |
| `test` (2017-2023) | 9,261 | 128 | 9,133 | 388 | 4.25% |

## Validation
### Candidate Model Validation Tuning

| Model | Best Hyperparameters | Val AUROC | Val Calibration Slope |
| --- | --- | --- | --- |
| lr | {"C": 1.0} | 0.7540 | 0.854 |
| lr_balanced | {"C": 0.01} | 0.7534 | 0.725 |
| rf | {"n_estimators": 100, "max_depth": 5, "min_samples_leaf": 10} | 0.7546 | 0.959 |
| hgb | {"learning_rate": 0.05, "max_leaf_nodes": 15, "min_samples_leaf": 20} | 0.7496 | 0.856 |

### Decision D10 Selection Rationale
- **Chosen Architecture:** `lr`
- **Selection Rule:** Logistic regression (lr) selected under D10 parsimony rule (plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: -0.0007)): best tree did not beat LR by >= 0.02 validation AUROC (tree gap: +0.0006).
- **Validation Calibration Gate:** `PASS` (Slope: 0.854)
- **D7 Locked Threshold:** `0.0285` (Val Sens: 80.16%, Val Spec: 58.18%)
- **D8 Risk Stratification Bands:** Low < `0.0285`, Moderate `0.0285` - `0.0853`, High >= `0.0853`

## Test
### Held-Out Test Discrimination & Diagnostic Performance (2017-2023)

- **Test AUROC (95% Bootstrap CI):** **0.7421** [0.7203 - 0.7640]
- **Test AUPRC (95% Bootstrap CI):** **0.0991** [0.0880 - 0.1152]
- **Locked Threshold:** `0.0285`
- **Test Sensitivity:** **84.28%**
- **Test Specificity:** **50.05%**
- **Test PPV:** **6.96%**
- **Test NPV:** **98.63%**
- **Confusion Matrix:** TP=327, FP=4368, TN=4377, FN=61

### D11 Acceptance Gate Audit

- Gate 1 (Test AUROC >= 0.75): **FAIL** (0.7421)
- Gate 2 (Test Sensitivity >= 0.75): **PASS** (84.28%)
- Gate 3 (Test Calibration Slope 0.8-1.2): **PASS** (0.825)
- Gate 4 (Subgroup Sens >= 0.60): **FAIL** (Worst: 50.98%)
- Gate 5 (FULL beats BASIC on Val AUROC): **N/A (BASIC)**
- **Overall FYP-1 Status:** **NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60)**

## Calibration
### Test Calibration Diagnostics

- **Brier Score:** 0.0401
- **Calibration-in-the-large (mean p - mean y):** +0.0024
- **Logistic Calibration Slope:** 0.825
- **Logistic Calibration Intercept:** -0.531

#### Reliability Table Across Decile Bins

| bin | n | mean_p | observed_rate |
| --- | --- | --- | --- |
| (0.0006900000000000001, 0.0063] | 914 | 0.004402593188008138 | 0.002188183807439825 |
| (0.0063, 0.0107] | 913 | 0.008452050495092931 | 0.0065717415115005475 |
| (0.0107, 0.0157] | 913 | 0.013071446227862413 | 0.0065717415115005475 |
| (0.0157, 0.022] | 913 | 0.018654222614667645 | 0.0208105147864184 |
| (0.022, 0.0296] | 914 | 0.025803304660710902 | 0.0350109409190372 |
| (0.0296, 0.0389] | 913 | 0.03408992682220909 | 0.040525739320920046 |
| (0.0389, 0.0513] | 913 | 0.044862372012300714 | 0.04928806133625411 |
| (0.0513, 0.068] | 913 | 0.05902428429488193 | 0.06352683461117196 |
| (0.068, 0.0995] | 916 | 0.08184494648941686 | 0.08296943231441048 |
| (0.0995, 0.829] | 911 | 0.15834658101592064 | 0.11745334796926454 |

## Subgroups
### Subgroup Breakdown on Held-Out Test Set

| Dimension | Group | Total (n) | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 4,974 | 207 | 4.2% | 0.7509 | 79.2% | 56.0% |
| sex_male | Male | 4,159 | 181 | 4.4% | 0.7342 | 90.1% | 42.9% |
| age_band | 18-39 | 3,262 | 51 | 1.6% | 0.8172 | 51.0% | 87.9% |
| age_band | 40-59 | 2,673 | 133 | 5.0% | 0.6876 | 76.7% | 50.1% |
| age_band | 60+ | 3,198 | 204 | 6.4% | 0.6667 | 97.5% | 9.4% |
| race_eth | Mexican American | 930 | 52 | 5.6% | 0.7722 | 78.8% | 58.5% |
| race_eth | Other Hispanic | 911 | 46 | 5.0% | 0.7560 | 84.8% | 55.6% |
| race_eth | Non-Hispanic White | 4,440 | 137 | 3.1% | 0.7820 | 92.0% | 43.4% |
| race_eth | Non-Hispanic Black | 1,479 | 93 | 6.3% | 0.7093 | 80.6% | 47.3% |
| race_eth | Other Race / Multi-Racial | 1,373 | 60 | 4.4% | 0.7692 | 76.7% | 65.5% |
| cycle | 2017-2018 | 4,228 | 210 | 5.0% | 0.7293 | 80.5% | 53.2% |
| cycle | 2021-2023 | 4,905 | 178 | 3.6% | 0.7660 | 88.8% | 47.3% |

### Feature Importance & Explanations

| feature | coef_standardized | odds_ratio_per_1_sd |
| --- | --- | --- |
| age | 0.854655242650186 | 2.3505638666983706 |
| bmi | 0.6152087959611124 | 1.8500428407071525 |
| sex_male | 0.2332135071440745 | 1.2626510355667124 |

> **SHAP Method Notice:** SHAP NOT USED: pip install shap requires adding 5 unpinned dependencies (shap, slicer, tqdm, numba, and llvmlite with a 41.9 MB LLVM binary) not in ml/requirements.txt. As specified in A3, CPU-friendly standardized odds ratios per 1 SD are used for logistic regression and scikit-learn validation permutation importance (n_repeats=10) is used for tree models.

## Limitations
- **Temporal Shift:** Evaluated strictly on temporal hold-out cohorts (2017-2023) following historical fitting (1999-2012).
- **External Validation:** BRFSS validation cannot evaluate undiagnosed labels because BRFSS lacks biological specimen assays and cuff measurements.
- **Complete Cases:** Complete case analysis drops missing survey records without synthetic imputation.

- **US Survey Population:** Trained and evaluated on US NHANES survey participants; not directly representative of South Asian or Pakistani diaspora physiology.
- **Survey Weights Omitted in Training:** Standard maximum-likelihood estimation was used without complex survey pseudo-weights to reflect empirical prediction performance.
- **NHANES Age Top-Coding:** Participants aged 80+ (or 85+ in early cycles) have capped ages, which introduces minor attenuation at extreme elderly ages.
- **Self-Report Target Inclusion:** Self-reported diabetes diagnoses may omit undiagnosed individuals or contain recall noise compared to pure biochemical definitions.
