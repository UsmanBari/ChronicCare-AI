# External Validation of ChronicCare-AI ML Models

## Executive Summary
This document presents the rigorous external validation of all trained clinical machine learning models
for adult type 2 diabetes and hypertension across five independent cohorts:
1. **CDC BRFSS 2015 Kaggle** (N = 253,680)
2. **CDC BRFSS Core Parquet** (N = 2,181,756)
3. **Pima Indians Diabetes Cohort** (N = 768)
4. **Framingham Heart Study Cohort** (N = 4,238)
5. **Cardio70k Cardiovascular Examination Records** (N = 70,000)

Every model is evaluated strictly at its locked operating threshold established during training
or validation on NHANES. **In strict adherence to clinical safety standards, operational thresholds
were never re-tuned or modified on external validation data.**

---

## Results Table

| Model | Dataset | Mode | N | Prevalence | AUROC (95% CI) | Sens | Spec | Cal-in-Large | Brier | Missing Features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_temporal_lr | brfss2015_kaggle | as-saved | 253,680 | 13.9% | 0.737 [0.730, 0.741] | 0.859 | 0.466 | +0.367 | 0.260 | - |
| baseline_temporal_lr | brfss_core | as-saved | 1,982,127 | 13.5% | 0.751 [0.743, 0.755] | 0.864 | 0.489 | +0.354 | 0.252 | - |
| baseline_temporal_lr | pima | as-saved | 757 | 35.1% | 0.736 [0.704, 0.769] | 0.278 | 0.888 | -0.067 | 0.203 | - |
| diabetes_basic_nhanes | brfss2015_kaggle | as-saved | 253,680 | 13.9% | 0.761 [0.754, 0.765] | 0.904 | 0.428 | -0.086 | 0.120 | - |
| diabetes_basic_nhanes | brfss_core | as-saved | 1,931,900 | 13.5% | 0.769 [0.764, 0.775] | 0.905 | 0.454 | -0.084 | 0.116 | - |
| diabetes_basic_nhanes | pima | overlap refit, not Usman's saved model | 757 | 35.1% | 0.735 [0.702, 0.770] | 0.391 | 0.849 | -0.329 | 0.330 | ever_smoked_100, told_high_bp |
| diabetes_full_nhanes | brfss2015_kaggle | overlap refit, not Usman's saved model | 253,680 | 13.9% | 0.761 [0.755, 0.766] | 0.903 | 0.430 | -0.086 | 0.120 | sbp, dbp, waist_cm |
| diabetes_full_nhanes | brfss_core | overlap refit, not Usman's saved model | 1,931,900 | 13.5% | 0.770 [0.765, 0.775] | 0.905 | 0.454 | -0.084 | 0.116 | sbp, dbp, waist_cm |
| diabetes_full_nhanes | pima | overlap refit, not Usman's saved model | 757 | 35.1% | 0.735 [0.702, 0.770] | 0.391 | 0.845 | -0.329 | 0.330 | ever_smoked_100, told_high_bp, sbp, dbp, waist_cm |
| diabetes_ref_age_sex_bmi | brfss2015_kaggle | as-saved | 253,680 | 13.9% | 0.742 [0.735, 0.747] | 0.891 | 0.413 | -0.087 | 0.121 | - |
| diabetes_ref_age_sex_bmi | brfss_core | as-saved | 1,982,127 | 13.5% | 0.753 [0.744, 0.756] | 0.895 | 0.438 | -0.084 | 0.117 | - |
| diabetes_ref_age_sex_bmi | pima | as-saved | 757 | 35.1% | 0.735 [0.702, 0.770] | 0.391 | 0.849 | -0.329 | 0.330 | - |
| htn_basic_nhanes | framingham | as-saved | 4,219 | 31.0% | 0.701 [0.686, 0.718] | 0.890 | 0.395 | +0.004 | 0.194 | - |
| htn_basic_nhanes | brfss_core | as-saved | 1,931,900 | 40.7% | 0.743 [0.738, 0.747] | 0.937 | 0.343 | +0.002 | 0.201 | - |
| htn_basic_nhanes | cardio70k | overlap refit, not Usman's saved model | 68,737 | 81.6% | 0.667 [0.664, 0.677] | 0.785 | 0.439 | -0.402 | 0.304 | ever_smoked_100, told_diabetes |
| htn_full_nhanes | framingham | overlap refit, not Usman's saved model | 4,219 | 31.0% | 0.720 [0.704, 0.736] | 0.800 | 0.544 | +0.060 | 0.194 | hba1c, waist_cm |
| htn_full_nhanes | brfss_core | overlap refit, not Usman's saved model | 1,931,900 | 40.7% | 0.753 [0.750, 0.758] | 0.909 | 0.416 | +0.060 | 0.201 | hba1c, waist_cm |
| htn_full_nhanes | cardio70k | overlap refit, not Usman's saved model | 68,737 | 81.6% | 0.667 [0.664, 0.677] | 0.785 | 0.439 | -0.402 | 0.304 | ever_smoked_100, told_diabetes, hba1c, waist_cm |
| htn_ref_age_sex_bmi | framingham | as-saved | 4,219 | 31.0% | 0.700 [0.684, 0.717] | 0.879 | 0.405 | +0.001 | 0.194 | - |
| htn_ref_age_sex_bmi | brfss_core | as-saved | 1,979,349 | 40.7% | 0.751 [0.751, 0.759] | 0.938 | 0.349 | +0.005 | 0.198 | - |
| htn_ref_age_sex_bmi | cardio70k | as-saved | 68,737 | 81.6% | 0.663 [0.660, 0.672] | 0.860 | 0.329 | -0.465 | 0.361 | - |

---

## In-Depth Clinical Discussion

### 1. Label Differences (Self-Report vs Measured vs OGTT)
A critical determinant of external performance is the semantic and diagnostic distinction between labels:
- **Self-Reported / Told Diagnoses (BRFSS Core, BRFSS Kaggle, Framingham):**
  Survey respondents were asked whether a physician or healthcare provider ever informed them they had diabetes
  or hypertension. Self-report captures *diagnosed* disease, inherently missing individuals with undiagnosed disease
  and reflecting healthcare access biases (individuals with insurance or higher socio-economic status are more likely to be diagnosed).
- **Physiologically Measured Readings (Cardio70k):**
  Cardio70k defines hypertension strictly as measured SBP >= 130 or DBP >= 80 mmHg.
  This identifies all individuals with acutely elevated blood pressure at examination, irrespective of prior clinical diagnosis
  or white-coat effect.
- **Biochemical Oral Glucose Tolerance Testing (Pima Indians):**
  Pima diabetes status is determined by formal 2-hour post-load plasma glucose (>= 200 mg/dL per WHO criteria).
  This biochemical gold-standard detects true metabolic dysregulation far more sensitively than self-report.
  Consequently, models calibrated on survey self-report or undiagnosed screening display lower apparent sensitivity
  at locked thresholds when applied against biochemically definitive OGTT criteria.

### 2. Population Differences
The five cohorts represent starkly divergent demographic, epidemiological, and temporal populations:
- **NHANES (Reference Development Population):**
  A representative cross-section of the non-institutionalized United States population across multi-ethnic strata
  (White, Black, Hispanic, Asian, Multi-racial) collected between 1999 and 2018.
- **Framingham Heart Study (1948-1968):**
  A predominantly Caucasian, suburban New England community cohort from the mid-20th century. Dietary patterns,
  anti-hypertensive medications, and baseline cardiovascular risk profiles reflect historic clinical baselines
  substantially differing from contemporary 21st-century cohorts.
- **Pima Indians (Phoenix, Arizona):**
  A culturally homogeneous, genetically distinct American Indian population characterized by historically
  extreme genetic susceptibility to insulin resistance and type 2 diabetes. Adult females have a 35.1% diabetes prevalence,
  resulting in strong negative calibration-in-the-large when evaluated with models calibrated on 8-14% general population prevalence.
- **Cardio70k (Clinical Examination Cohort):**
  An examination dataset of 70,000 adults seeking medical examination or cardiovascular checkups. Mean age is 53.3 years
  and 81.6% meet measured >= 130/80 mmHg criteria. This high baseline prevalence causes models trained on general
  screening populations to substantially underestimate absolute risk (Calibration-in-the-large approx -0.46).

### 3. Feature-Mapping Losses
Feature granularity differences between cohorts necessitate methodological trade-offs:
- **Age Aggregation:** BRFSS Kaggle records age in 13 ordinal five-year intervals (_AGEG5YR), requiring mapping to category
  midpoints (e.g., age 18-24 -> 21, 80+ -> 82). This collapses intra-interval variance, dampening linear predictor precision.
- **Smoking History:** NHANES distinguishes pack-years, lifetime smoking (>100 cigarettes), and current status, whereas Framingham
  captures cigarettes/day and BRFSS captures binary lifetime exposure.
- **Missing Anthropometric Measures:** Waist circumference and laboratory biomarkers (HbA1c) are absent in phone survey
  cohorts (BRFSS), requiring mechanical overlap refits to quantify the generalizability of non-invasive feature subsets.

### 4. Interpretation of AUROC Changes
Across external cohorts, discrimination demonstrates solid robustness with expected domain shifts:
- Minimal discrimination drop was observed on large survey populations (BRFSS Core AUROC approx 0.75-0.76 for diabetes models
  versus 0.78-0.81 on NHANES held-out test split). This modest approx 0.03-0.05 AUROC drop confirms that age, sex, BMI,
  and smoking carry consistent discriminative signal across independent North American samples.
- On highly selected cohorts (Cardio70k and Pima), discrimination ranges from 0.66 to 0.74. The primary mode of failure
  is **calibration drift** (calibration-in-the-large up to -0.46), not loss of feature ranking capability. This demonstrates that
  decision thresholds must never be applied cross-population without local calibration.

### 5. South Asian Applicability & The Imperative for DHS Validation
**CRITICAL CLINICAL NOTICE:**
None of the five external validation cohorts represents a South Asian or Pakistani population:
- South Asian individuals experience the "South Asian Phenotype", developing type 2 diabetes and premature coronary artery disease
  at substantially younger ages (5-10 years earlier) and at lower Body Mass Index thresholds (BMI >= 23 kg/m^2
  versus >= 25 kg/m^2 per WHO Asian cutoffs), with elevated visceral adiposity and central obesity.
- Evaluating Western or Native American populations provides zero guarantee of calibration or safety in South Asian primary care.
- **Conclusion:** Validation on South Asian Demographic and Health Surveys (India NFHS-5, Bangladesh DHS, Nepal DHS)
  and local Pakistani clinical data remains an indispensable, non-negotiable prerequisite prior to any clinical deployment.

---

*Report generated automatically by `backend-poc-technical/ml/external_validation.py`.*
