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
| LogisticRegression (standard) | 0.7701 (0.7598 - 0.7804) | 0.1126 | 4.03% | 99.23% | 47.52% | 85.68% | 0.094 | 85.62% | 55.81% | 25.08% | 95.74% | 5368/4251/239/1423 |
| LogisticRegression (balanced) | 0.7703 (0.7601 - 0.7805) | 0.2289 | 82.49% | 59.04% | 25.81% | 95.13% | 0.470 | 85.62% | 55.54% | 24.96% | 95.72% | 5342/4277/239/1423 |

## 4. Honest Comparison with S-6 Single-Cycle Random Baseline
1. **The S-6 Baseline Context:** The earlier S-6 baseline (`train_baseline.py`, PR #61) reported an AUROC of 0.7507 on an 80/20 random stratified split within a single recent cycle (2021-2023, 6,014 adults).
2. **The Default Threshold Defect:** In S-6, evaluating at default threshold 0.5 yielded a clinically unacceptable sensitivity of **3.55%** (missing over 96% of diabetics) because uncalibrated probabilities in imbalanced datasets rarely exceed 0.5.
3. **Stricter Temporal Generalization:** The temporal split is a substantially more honest and rigorous test: the model is trained on historical participants (1999-2012) and evaluated on future cohorts (2017-2023) across demographic shifts, aging trends, and evolving obesity patterns.
4. **Tuned Thresholding Trade-Off:** Tuning the decision threshold on validation data to achieve >= 80% clinical sensitivity yields **85.62% sensitivity** on future test cohorts, but this high sensitivity comes at a substantial cost: specificity is only **55.54%** and PPV is **24.96%**, meaning approximately 3 out of every 4 flagged individuals do not have diagnosed diabetes. This is an uncalibrated 3-feature exploratory baseline (age, sex, BMI) demonstrating decision threshold trade-offs, not a production-ready clinical risk model.
