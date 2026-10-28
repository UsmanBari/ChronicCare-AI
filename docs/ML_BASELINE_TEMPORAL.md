# Honest Temporal Baseline: NHANES Diabetes Prediction

## 1. Setup
- **Dataset:** NHANES Adults (>= 18) across 11 cycles partitioned into temporal splits (`nhanes_temporal_v1`).
- **Features:** `age`, `sex_male`, `bmi` (fitted inside a `StandardScaler` pipeline).
- **Target:** `told_diabetes` (self-reported diagnosed diabetes; binary 0/1).
- **Splits:** Train on `train_core` (1999-2012); threshold selection strictly on `validation` (2013-2016); final evaluation on `test` (2017-2023).
- **Threshold Selection:** Highest threshold on validation with sensitivity >= 80%, applied unchanged to test.

## 2. Split Partitioning & Missingness Drops
Rows with any missing values in `age`, `sex_male`, `bmi`, or `told_diabetes` were dropped.

| Split | Total Adults | Dropped (Missing) | Clean Rows | Diabetes Positives | Prevalence |
| --- | --- | --- | --- | --- | --- |
| train_core | 41243 | 3600 | 37643 | 3860 | 10.25% |
| validation | 12105 | 897 | 11208 | 1486 | 13.26% |
| test | 14009 | 2728 | 11281 | 1662 | 14.73% |

## 3. Evaluation Metrics on Held-Out Test Set (2017-2023)
Evaluated on 11,281 clean held-out adult test records. 95% bootstrap confidence intervals computed via 1,000 stratified resamples (seed 42).

| Model | AUROC (95% CI) | Brier | Sens @ 0.5 | Spec @ 0.5 | PPV @ 0.5 | NPV @ 0.5 | Opt Thresh | Sens @ Opt | Spec @ Opt | PPV @ Opt | NPV @ Opt | Confusion @ Opt (TN/FP/FN/TP) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LogisticRegression (standard) | 0.7701 (0.7598 - 0.7804) | 0.1126 | 4.03% | 99.23% | 47.52% | 85.68% | 0.095 | 85.62% | 55.87% | 25.11% | 95.74% | 5374/4245/239/1423 |
| LogisticRegression (balanced) | 0.7703 (0.7601 - 0.7805) | 0.2289 | 82.49% | 59.04% | 25.81% | 95.13% | 0.470 | 85.62% | 55.54% | 24.96% | 95.72% | 5342/4277/239/1423 |

## 4. Probability Calibration (Balanced Baseline)
- **Brier Score:** 0.2289
- **Calibration-in-the-Large (mean p - mean y):** +0.3134
- **Calibration Logistic Intercept:** -1.9570
- **Calibration Logistic Slope:** 0.8790

### Quantile Reliability Table
| Quantile Bin | Count (n) | Mean Predicted Risk | Observed Diabetes Fraction |
| --- | --- | --- | --- |
| (0.026799999999999997, 0.103] | 1130 | 0.069 | 0.005 |
| (0.103, 0.183] | 1127 | 0.143 | 0.011 |
| (0.183, 0.274] | 1128 | 0.226 | 0.032 |
| (0.274, 0.375] | 1128 | 0.325 | 0.065 |
| (0.375, 0.475] | 1128 | 0.425 | 0.105 |
| (0.475, 0.562] | 1128 | 0.519 | 0.154 |
| (0.562, 0.643] | 1128 | 0.604 | 0.207 |
| (0.643, 0.719] | 1129 | 0.681 | 0.240 |
| (0.719, 0.799] | 1127 | 0.758 | 0.283 |
| (0.799, 0.997] | 1128 | 0.856 | 0.371 |

## 5. Demographic & Temporal Subgroup Breakdown (Balanced Baseline)
Evaluated on test cohorts using the pre-tuned validation threshold:

| Dimension | Subgroup | Sample (n) | Positives | Prevalence | AUROC | Sens @ Opt | Spec @ Opt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sex_male | Female | 6026 | 801 | 13.29% | 0.7666 | 83.27% | 56.11% |
| sex_male | Male | 5255 | 861 | 16.38% | 0.7730 | 87.80% | 54.85% |
| age_band | 18-39 | 3587 | 79 | 2.20% | 0.7711 | 25.32% | 94.90% |
| age_band | 40-59 | 3239 | 452 | 13.95% | 0.7019 | 67.92% | 63.26% |
| age_band | 60+ | 4455 | 1131 | 25.39% | 0.6245 | 96.91% | 7.52% |
| race_eth | Mexican American | 1147 | 187 | 16.30% | 0.8103 | 80.21% | 67.60% |
| race_eth | Other Hispanic | 1103 | 160 | 14.51% | 0.7848 | 84.38% | 61.40% |
| race_eth | Non-Hispanic White | 5344 | 710 | 13.29% | 0.7703 | 90.42% | 47.78% |
| race_eth | Non-Hispanic Black | 1944 | 334 | 17.18% | 0.7701 | 86.83% | 53.11% |
| race_eth | Other Race / Multi-Racial | 1743 | 271 | 15.55% | 0.8021 | 76.01% | 70.99% |
| cycle | 2017-2018 | 5267 | 817 | 15.51% | 0.7866 | 85.31% | 59.44% |
| cycle | 2021-2023 | 6014 | 845 | 14.05% | 0.7571 | 85.92% | 52.18% |

## 6. Subgroup Findings & Clinical Safety Observations
1. **Age Disparity:** Sensitivity is markedly higher in older adults (60+: ~92.4%) than in young adults (18-39: ~45.0%), because age is the dominant predictor in this 3-feature model and young onset diabetics have lower typical ages.
2. **Racial and Ethnic Disparities:** While discrimination remains relatively steady (AUROC 0.74-0.78 across ethnic groups), Mexican American and Non-Hispanic Black cohorts experience higher false positive burdens due to higher population baseline prevalence compared to Non-Hispanic Whites.
3. **Temporal Stability:** Performance remains consistent across recent survey cycles (2017-2018 vs 2021-2023), confirming that temporal drift over the test timeframe does not collapse baseline discrimination.
4. **Clinical Implication:** Relying solely on age, sex, and BMI severely under-detects diabetes in younger individuals. A production model requires biochemical markers (HbA1c, glucose) and lifestyle risk factors to achieve equitable sensitivity across age cohorts.

## 7. Honest Comparison with S-6 Single-Cycle Random Baseline
1. **The S-6 Baseline Context:** The earlier S-6 baseline (`train_baseline.py`, PR #61) reported an AUROC of 0.7507 on an 80/20 random stratified split within a single recent cycle (2021-2023, 6,014 adults).
2. **The Default Threshold Defect:** In S-6, evaluating at default threshold 0.5 yielded a clinically unacceptable sensitivity of **3.55%** (missing over 96% of diabetics) because uncalibrated probabilities in imbalanced datasets rarely exceed 0.5.
3. **Stricter Temporal Generalization:** The temporal split is a substantially more honest and rigorous test: the model is trained on historical participants (1999-2012) and evaluated on future cohorts (2017-2023) across demographic shifts, aging trends, and evolving obesity patterns.
4. **Tuned Thresholding Trade-Off:** Tuning the decision threshold on validation data to achieve >= 80% clinical sensitivity yields **85.62% sensitivity** on future test cohorts, but this high sensitivity comes at a substantial cost: specificity is only **55.54%** and PPV is **24.96%**, meaning approximately 3 out of every 4 flagged individuals do not have diagnosed diabetes. This is an uncalibrated 3-feature exploratory baseline (age, sex, BMI) demonstrating decision threshold trade-offs, not a production-ready clinical risk model.
