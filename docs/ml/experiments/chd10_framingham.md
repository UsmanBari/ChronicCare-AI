# ChronicCare AI — Model Evaluation Report

## Config
- **Name:** `chd10_framingham`
- **Target Label:** `TenYearCHD`
- **Population Filter:** `hypertension_or_diabetes`
- **Tier:** `full`
- **Features (9):** `age, sex_male, current_smoker, bmi, sbp, dbp, bp_meds, diabetes, prevalent_hyp`
- **Candidate Models:** `lr, lr_balanced, rf, hgb`
- **Threshold Policy:** `{"type": "fixed", "value": 0.1}`
- **Seed:** `42`
- **Wall Time:** 8.24 seconds (0.1 minutes)

## Data
### Complete Case Cohort Statistics Across Stratified 60/20/20 Splits

| Split | Initial In Population | Dropped (Missing Features) | Clean Evaluated Rows | Positives | Prevalence |
|---|---|---|---|---|---|
| `train` (60%) | 2,499 | 0 | 2,499 | 374 | 14.97% |
| `validation` (20%) | 833 | 0 | 833 | 124 | 14.89% |
| `test` (20%) | 834 | 0 | 834 | 125 | 14.99% |

## Validation
### Candidate Model Validation Tuning

| Model | Best Hyperparameters | Val AUROC | Val Calibration Slope |
| --- | --- | --- | --- |
| lr | {"C": 0.01} | 0.7170 | 1.079 |
| lr_balanced | {"C": 0.001} | 0.7163 | 1.748 |
| rf | {"n_estimators": 100, "max_depth": 5, "min_samples_leaf": 5} | 0.7169 | 1.090 |
| hgb | {"learning_rate": 0.05, "max_depth": 3, "min_samples_leaf": 10} | 0.7011 | 0.797 |

### Decision D10 Selection Rationale
- **Chosen Architecture:** `lr`
- **Selection Rule:** Logistic regression (lr) selected under D10 parsimony rule (plain lr chosen: lr_balanced did not beat plain lr by >= 0.01 validation AUROC (gap: -0.0007)): best tree did not beat LR by >= 0.02 validation AUROC (tree gap: -0.0001).
- **Validation Calibration Gate:** `PASS` (Slope: 1.079)
- **D7 Locked Threshold:** `0.1000` (Val Sens: 86.29%, Val Spec: 38.93%)
- **D8 Risk Stratification Bands:** Low < `0.1000`, Moderate `0.1000` - `0.2000`, High >= `0.2000`

## Test
### Held-Out Test Discrimination & Diagnostic Performance

- **Test AUROC (95% Bootstrap CI):** **0.7241** [0.6732 - 0.7659]
- **Test AUPRC (95% Bootstrap CI):** **0.3083** [0.2561 - 0.3726]

#### Operating Point: 10% Cutoff (Moderate / High Risk)
- **Threshold:** `0.1000`
- **Sensitivity:** **84.80%**
- **Specificity:** **39.07%**
- **PPV (Precision):** **19.70%**
- **NPV:** **93.58%**
- **F1-Score:** **0.3198**
- **Confusion Matrix:** TP=106, FP=432, TN=277, FN=19

#### Operating Point: 20% Cutoff (High Risk)
- **Threshold:** `0.2000`
- **Sensitivity:** **58.40%**
- **Specificity:** **78.00%**
- **PPV (Precision):** **31.88%**
- **NPV:** **91.40%**
- **F1-Score:** **0.4124**
- **Confusion Matrix:** TP=73, FP=156, TN=553, FN=52

### Pre-Registered Acceptance Gates Audit (G1 - G5)

- Gate 1 (Test AUROC >= 0.68): **PASS** (0.7241)
- Gate 2 (Test Calibration Slope in [0.80, 1.20]): **PASS** (1.142)
- Gate 3 (Test Sensitivity @ 10% >= 70%): **PASS** (84.80%)
- Gate 4 (Subgroup Sens @ 10% >= 60%): **PASS** (Worst: age_band=<50=60.53%)
- Gate 5 (Brier Score < Naive Prevalence Brier): **PASS** (0.1172 vs 0.1274)
- **Overall FYP-1 Status:** **SHIP CANDIDATE (all G1-G5 gates passed)**

## Calibration
### Test Calibration Diagnostics

- **Brier Score:** 0.1172 (Naive Prevalence Brier: 0.12741605276929538)
- **Calibration-in-the-large (mean p - mean y):** +0.0061
- **Logistic Calibration Slope:** 1.142
- **Logistic Calibration Intercept:** +0.164

#### Reliability Table Across Decile Bins

| bin | n | mean_p | observed_rate |
| --- | --- | --- | --- |
| (0.033, 0.0569] | 84 | 0.047172781243811024 | 0.011904761904761904 |
| (0.0569, 0.0726] | 83 | 0.06462030841421354 | 0.08433734939759036 |
| (0.0726, 0.0902] | 83 | 0.08091629519615375 | 0.08433734939759036 |
| (0.0902, 0.111] | 84 | 0.0998113472627358 | 0.05952380952380952 |
| (0.111, 0.132] | 83 | 0.12150449393947764 | 0.08433734939759036 |
| (0.132, 0.159] | 83 | 0.14582032633242822 | 0.10843373493975904 |
| (0.159, 0.192] | 84 | 0.1740806342552342 | 0.16666666666666666 |
| (0.192, 0.226] | 83 | 0.20727296190109326 | 0.30120481927710846 |
| (0.226, 0.292] | 83 | 0.2574410961200277 | 0.26506024096385544 |
| (0.292, 0.588] | 84 | 0.36011403042844636 | 0.3333333333333333 |

## Subgroups
### Subgroup Breakdown on Held-Out Test Set

| Dimension | Group | Total (n) | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 458 | 61 | 13.3% | 0.7422 | 72.1% | 58.2% |
| sex_male | Male | 376 | 64 | 17.0% | 0.7036 | 96.9% | 14.7% |
| age_band | <50 | 429 | 38 | 8.9% | 0.7140 | 60.5% | 63.7% |
| age_band | 50-59 | 261 | 53 | 20.3% | 0.6616 | 92.5% | 13.5% |
| age_band | 60+ | 144 | 34 | 23.6% | 0.5955 | 100.0% | 0.0% |

### Feature Importance & Odds Ratios

| feature | coef_standardized | odds_ratio_per_1_sd |
| --- | --- | --- |
| age | 0.4246799860746401 | 1.529101007742481 |
| sex_male | 0.281551566249279 | 1.3251843293451353 |
| sbp | 0.19902025571333018 | 1.2202066818063027 |
| current_smoker | 0.15633602382674222 | 1.1692190225380787 |
| prevalent_hyp | 0.092383748184591 | 1.0967856308280721 |
| bmi | 0.07404248156136309 | 1.076852550902265 |
| diabetes | 0.051344587635712265 | 1.0526855732249294 |
| bp_meds | 0.046120019430228004 | 1.0472000877728256 |
| dbp | 0.04455105945906684 | 1.0455583609918928 |

### Clinical Sanity Direction Check

| feature | coef | sign | direction | expected | concordant |
| --- | --- | --- | --- | --- | --- |
| age | 0.4246799860746401 | + | UP (+) | UP (+) | True |
| sex_male | 0.281551566249279 | + | UP (+) | UP (+) | True |
| current_smoker | 0.15633602382674222 | + | UP (+) | UP (+) | True |
| bmi | 0.07404248156136309 | + | UP (+) | UP (+) | True |
| sbp | 0.19902025571333018 | + | UP (+) | UP (+) | True |
| dbp | 0.04455105945906684 | + | UP (+) | UP (+) | True |
| bp_meds | 0.046120019430228004 | + | UP (+) | UP (+) | True |
| diabetes | 0.051344587635712265 | + | UP (+) | UP (+) | True |
| prevalent_hyp | 0.092383748184591 | + | UP (+) | UP (+) | True |

### Global SHAP Feature Attributions

| feature | mean_abs_shap |
| --- | --- |
| age | 0.3658192239766682 |
| sex_male | 0.27532015951178207 |
| sbp | 0.1668005666564158 |
| current_smoker | 0.15617622911147225 |
| prevalent_hyp | 0.08691909328087864 |
| bmi | 0.055537773290250156 |
| dbp | 0.03566034179408911 |
| bp_meds | 0.016942516318602708 |
| diabetes | 0.00974736358764482 |

### Decision Curve Analysis (Net Benefit across Thresholds)

| pt | net_benefit_model | net_benefit_all | net_benefit_none |
| --- | --- | --- | --- |
| 0.01 | 0.1413 | 0.1413 | 0.0 |
| 0.02 | 0.1325 | 0.1325 | 0.0 |
| 0.03 | 0.1236 | 0.1236 | 0.0 |
| 0.04 | 0.1153 | 0.1145 | 0.0 |
| 0.05 | 0.1068 | 0.1051 | 0.0 |
| 0.06 | 0.1005 | 0.0956 | 0.0 |
| 0.07 | 0.0909 | 0.0859 | 0.0 |
| 0.08 | 0.0832 | 0.076 | 0.0 |
| 0.09 | 0.0754 | 0.0658 | 0.0 |
| 0.1 | 0.0695 | 0.0554 | 0.0 |
| 0.11 | 0.0668 | 0.0448 | 0.0 |
| 0.12 | 0.0663 | 0.034 | 0.0 |
| 0.13 | 0.0594 | 0.0229 | 0.0 |
| 0.14 | 0.0557 | 0.0115 | 0.0 |
| 0.15 | 0.0542 | -0.0001 | 0.0 |
| 0.16 | 0.05 | -0.012 | 0.0 |
| 0.17 | 0.0472 | -0.0242 | 0.0 |
| 0.18 | 0.049 | -0.0367 | 0.0 |
| 0.19 | 0.0452 | -0.0495 | 0.0 |
| 0.2 | 0.0408 | -0.0626 | 0.0 |

> **SHAP Method Notice:** Linear SHAP (shap.LinearExplainer) was used for logistic regression feature attribution, providing global mean |SHAP| and exact additive contributions for patient cases.

## Limitations
- **Dataset Context:** Framingham Heart Study 10-year risk reflects an American cohort initialized in 1948 with predominantly White participants; baseline risk may vary for contemporary South Asian populations.
- **Clinical Setting:** BP readings in Framingham were standardized clinical measurements, whereas ChronicCare AI receives home self-measurements.
- **Intended Use:** Provider decision support with patient-facing risk tier; raw risk percentages are not shown to patients to avoid unnecessary anxiety.

- **US Survey Population:** Trained and evaluated on US NHANES survey participants; not directly representative of South Asian or Pakistani diaspora physiology.
- **Survey Weights Omitted in Training:** Standard maximum-likelihood estimation was used without complex survey pseudo-weights to reflect empirical prediction performance.
- **NHANES Age Top-Coding:** Participants aged 80+ (or 85+ in early cycles) have capped ages, which introduces minor attenuation at extreme elderly ages.
- **Self-Report Target Inclusion:** Self-reported diabetes diagnoses may omit undiagnosed individuals or contain recall noise compared to pure biochemical definitions.
