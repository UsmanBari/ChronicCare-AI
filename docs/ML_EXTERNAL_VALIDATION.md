# External Validation of ChronicCare-AI ML Models

## Executive Summary
This document presents external validation of trained machine learning models across independent external cohorts:
- **Framingham Heart Study Cohort** (N = 4,238)
- **Pima Indians Diabetes Cohort** (N = 768)
- **CDC BRFSS 2015 Kaggle** (N = 253,680)
- **CDC BRFSS Core Parquet** (N = 2,181,756)
- **Cardio70k Examination Records** (N = 70,000)

Per ML_PLAN D12, the primary model evaluated is `diabetes_full_nhanes` (the only model deployed in the application as provider-only, experimental).
Per ML_PLAN D13, hypertension models are retired and not used in the application; their evaluations appear in the Appendix.

Operating decision thresholds are strictly locked from training/validation on NHANES. Thresholds are never re-tuned on external cohorts.
For cohorts missing model features, an overlap refit is trained on NHANES `train_core` and thresholded on NHANES `validation`.

---

## 1. Undiagnosed Diabetes Target Equivalents

Evaluates diabetes models against external cohorts with biochemical or laboratory proxies for undiagnosed diabetes:
- **Framingham (`diabetes == 0` cohort):** Evaluates two proxies: (1) `glucose >= 200 mg/dL` (ADA random glucose cutoff; 0 positive cases as max glucose is 163.0 mg/dL in undiagnosed cohort); (2) `glucose >= 126 mg/dL` (fasting cutoff proxy; 22 positive cases, 0.54% prevalence).
- **Pima Indians:** Evaluates 2-hour post-load oral glucose tolerance testing (`Outcome` >= 200 mg/dL; caveat: adult females only, indigenous heritage, not restricted to undiagnosed individuals).
- **Cardio70k:** Skipped for diabetes because blood glucose is recorded only as a 3-level categorical index (`1 = normal`, `2 = above normal`, `3 = well above normal`), which does not constitute a clinical diabetes diagnostic equivalent.

| Model | Dataset | Target Definition | Mode | N | Prevalence | AUROC (95% CI) | CI Basis | Sens | Spec | Cal-in-Large | Brier | Missing Features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diabetes_full_nhanes | framingham | glucose >= 200 mg/dL (proxy random glucose, ADA cutoff) | overlap refit, not Usman's saved model | 4,112 | 0.0% | NOT RUN | - | - | - | - | - | waist_cm |
| diabetes_full_nhanes | framingham | glucose >= 126 mg/dL ("only valid if fasting") | overlap refit, not Usman's saved model | 4,112 | 0.5% | 0.596 [0.487, 0.715] | full n | 0.500 | 0.641 | +0.022 | 0.006 | waist_cm |
| diabetes_full_nhanes | pima | diabetes (measured 2h OGTT >= 200 mg/dL) | overlap refit, not Usman's saved model | 757 | 35.1% | 0.735 [0.706, 0.769] | full n | 0.391 | 0.845 | -0.329 | 0.330 | ever_smoked_100, told_high_bp, sbp, dbp, waist_cm |
| diabetes_basic_nhanes | framingham | glucose >= 200 mg/dL (proxy random glucose, ADA cutoff) | as-saved | 4,112 | 0.0% | NOT RUN | - | - | - | - | - | - |
| diabetes_basic_nhanes | framingham | glucose >= 126 mg/dL ("only valid if fasting") | as-saved | 4,112 | 0.5% | 0.585 [0.483, 0.695] | full n | 0.455 | 0.689 | +0.020 | 0.006 | - |
| diabetes_basic_nhanes | pima | diabetes (measured 2h OGTT >= 200 mg/dL) | overlap refit, not Usman's saved model | 757 | 35.1% | 0.735 [0.706, 0.769] | full n | 0.391 | 0.849 | -0.329 | 0.330 | ever_smoked_100, told_high_bp |
| diabetes_ref_age_sex_bmi | framingham | glucose >= 200 mg/dL (proxy random glucose, ADA cutoff) | as-saved | 4,112 | 0.0% | NOT RUN | - | - | - | - | - | - |
| diabetes_ref_age_sex_bmi | framingham | glucose >= 126 mg/dL ("only valid if fasting") | as-saved | 4,112 | 0.5% | 0.571 [0.483, 0.672] | full n | 0.364 | 0.698 | +0.019 | 0.006 | - |
| diabetes_ref_age_sex_bmi | pima | diabetes (measured 2h OGTT >= 200 mg/dL) | as-saved | 757 | 35.1% | 0.735 [0.706, 0.769] | full n | 0.391 | 0.849 | -0.329 | 0.330 | - |

---

## 2. Different Target (Told Diabetes): Ranking Only

> **Important Clinical Methodological Distinction:**
> Calibration, sensitivity, and specificity are not meaningful for our models in this table. Our models predict **undiagnosed diabetes** in adults without prior diabetes diagnosis (`label: diabetes_undiagnosed`, `population: adults_without_diabetes`). BRFSS records **ever told diabetes** (self-reported doctor diagnosis in the general population).
> Self-reported diagnosed diabetes is substantially easier to discriminate from age, BMI, and hypertension history than undiagnosed metabolic dysregulation, producing higher apparent AUROCs that do not reflect performance on undiagnosed screening. Only discriminative ranking (AUROC) is reported.

| Model | Dataset | Target Definition | Mode | N | Prevalence | AUROC (95% CI) | CI Basis | Missing Features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diabetes_full_nhanes | brfss2015_kaggle | diabetes (ever told diabetes) | overlap refit, not Usman's saved model | 253,680 | 13.9% | 0.760 [0.755, 0.766] | 50k stratified sample | sbp, dbp, waist_cm |
| diabetes_full_nhanes | brfss_core | diabetes (ever told diabetes) | overlap refit, not Usman's saved model | 1,931,900 | 13.5% | 0.770 [0.765, 0.775] | 50k stratified sample | sbp, dbp, waist_cm |
| diabetes_basic_nhanes | brfss2015_kaggle | diabetes (ever told diabetes) | as-saved | 253,680 | 13.9% | 0.760 [0.754, 0.765] | 50k stratified sample | - |
| diabetes_basic_nhanes | brfss_core | diabetes (ever told diabetes) | as-saved | 1,931,900 | 13.5% | 0.770 [0.764, 0.775] | 50k stratified sample | - |
| diabetes_ref_age_sex_bmi | brfss2015_kaggle | diabetes (ever told diabetes) | as-saved | 253,680 | 13.9% | 0.741 [0.735, 0.746] | 50k stratified sample | - |
| diabetes_ref_age_sex_bmi | brfss_core | diabetes (ever told diabetes) | as-saved | 1,982,127 | 13.5% | 0.750 [0.743, 0.756] | 50k stratified sample | - |

---

## Appendix: Retired Models (Not Used in the App)

> **Retirement Notice:**
> Per ML_PLAN D13, hypertension models (`htn_full_nhanes`, `htn_basic_nhanes`, `htn_ref_age_sex_bmi`) are retired and not used in the ChronicCare-AI application. Their target was undiagnosed hypertension (measured SBP >= 130 or DBP >= 80 mmHg among adults not told and not on antihypertensive medication).
> Evaluated below against:
> 1. Framingham undiagnosed HTN analogue (`prevalent_hyp == 0 & bp_meds == 0`, label measured SBP >= 130 or DBP >= 80 mmHg).
> 2. Cardio70k (measured SBP >= 130 or DBP >= 80 mmHg in clinical examinees; evaluated only for models without BP features).
> 3. BRFSS Core (different target: self-reported told high blood pressure).

| Model | Dataset | Target Definition | Mode | N | Prevalence | AUROC (95% CI) | CI Basis | Sens | Spec | Cal-in-Large | Brier | Missing Features |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| htn_full_nhanes | framingham | measured >= 130/80 mmHg (prevalent_hyp==0 & bp_meds==0) | overlap refit, not Usman's saved model | 2,879 | 51.2% | 0.631 [0.608, 0.653] | full n | 0.556 | 0.652 | -0.168 | 0.268 | hba1c, waist_cm |
| htn_full_nhanes | cardio70k | htn_measured_130_80 (measured >= 130/80 mmHg) | overlap refit, not Usman's saved model | 68,737 | 81.6% | 0.671 [0.665, 0.676] | 50k stratified sample | 0.785 | 0.439 | -0.402 | 0.304 | ever_smoked_100, told_diabetes, hba1c, waist_cm |
| htn_full_nhanes | brfss_core | high_bp (ever told high BP) | overlap refit, not Usman's saved model | 1,934,561 | 40.8% | 0.753 [0.749, 0.758] | 50k stratified sample | 0.906 | 0.420 | +0.060 | 0.201 | told_diabetes, hba1c, waist_cm |
| htn_basic_nhanes | framingham | measured >= 130/80 mmHg (prevalent_hyp==0 & bp_meds==0) | as-saved | 2,879 | 51.2% | 0.629 [0.607, 0.651] | full n | 0.701 | 0.495 | -0.222 | 0.290 | - |
| htn_basic_nhanes | cardio70k | htn_measured_130_80 (measured >= 130/80 mmHg) | overlap refit, not Usman's saved model | 68,737 | 81.6% | 0.671 [0.665, 0.676] | 50k stratified sample | 0.785 | 0.439 | -0.402 | 0.304 | ever_smoked_100, told_diabetes |
| htn_basic_nhanes | brfss_core | high_bp (ever told high BP) | overlap refit, not Usman's saved model | 1,934,561 | 40.8% | 0.753 [0.749, 0.758] | 50k stratified sample | 0.906 | 0.420 | +0.060 | 0.201 | told_diabetes |
| htn_ref_age_sex_bmi | framingham | measured >= 130/80 mmHg (prevalent_hyp==0 & bp_meds==0) | as-saved | 2,879 | 51.2% | 0.627 [0.606, 0.650] | full n | 0.687 | 0.503 | -0.225 | 0.291 | - |
| htn_ref_age_sex_bmi | cardio70k | htn_measured_130_80 (measured >= 130/80 mmHg) | as-saved | 68,737 | 81.6% | 0.666 [0.660, 0.672] | 50k stratified sample | 0.860 | 0.329 | -0.465 | 0.361 | - |
| htn_ref_age_sex_bmi | brfss_core | high_bp (ever told high BP) | as-saved | 1,979,349 | 40.7% | 0.755 [0.751, 0.759] | 50k stratified sample | 0.938 | 0.349 | +0.005 | 0.198 | - |

---

## Clinical Discussion & Epidemiological Findings

### 1. Model Target vs External Label Distinctions
- **Undiagnosed Diabetes (`diabetes_undiagnosed`) vs Diagnosed Diabetes (`told_diabetes`):**
  ChronicCare-AI models were developed to detect undiagnosed elevated blood sugar among adults unaware of their diabetic status. When applied to BRFSS cohorts, the target is doctor-diagnosed diabetes. Because individuals with established clinical diagnoses frequently have long-standing disease, elevated BMI, older age, and prescribed comorbidities, discriminative ranking appears higher (AUROC 0.741–0.770). However, calibration and diagnostic sensitivity/specificity from these cohorts do not apply to our screening task.
- **Framingham Blood Glucose Distribution:**
  In the Framingham Heart Study baseline examination, after excluding subjects with known diabetes (`diabetes == 0`, N = 4,129; 3,745 with measured glucose), the maximum observed blood glucose is 163.0 mg/dL. Every subject in the original cohort with glucose >= 200 mg/dL had already been clinically diagnosed and coded as `diabetes == 1`. Consequently, applying the ADA random glucose threshold (`>= 200 mg/dL`) yields exactly 0 positive cases in the undiagnosed cohort, precluding AUROC computation. Applying the fasting threshold (`>= 126 mg/dL`) yields 22 positive cases (0.54% prevalence), producing an overlap refit AUROC of 0.596 [0.487, 0.715]. Because the confidence interval includes 0.5, with only 22 cases, this can't be told apart from chance.
- **Pima Indians Biochemical OGTT:**
  Pima diabetes status is determined by formal 2-hour post-load oral glucose tolerance test (OGTT >= 200 mg/dL), identifying elevated blood glucose in a cohort with 35.1% prevalence among adult females. The models achieve an AUROC of 0.735 [0.706, 0.769], with negative calibration-in-the-large reflecting the substantially higher prevalence compared to general screening populations. Because Pima lacks waist circumference, smoking, and blood pressure history, all three diabetes models reduce to the same overlap refit on age and BMI (yielding identical discrimination); consequently, Pima evaluation says nothing about diabetes_full's additional features.

### 2. Reference Development Discrimination
For context, the locked internal test AUROCs achieved on the held-out NHANES temporal test set (`test` 2017–2023, 2 survey cycles) are documented in [`docs/ml/EXPERIMENTS_SUMMARY.md:14-18`](file:///C:/Users/Saad/Documents/ChronicCare-AI/docs/ml/EXPERIMENTS_SUMMARY.md#L14-L18):
- `diabetes_full_nhanes`: AUROC = **0.7527 [0.7293–0.7748]**
- `diabetes_basic_nhanes`: AUROC = **0.7403 [0.7182–0.7616]**
- `diabetes_ref_age_sex_bmi`: AUROC = **0.7421 [0.7203–0.7640]**

### 3. Feature Mapping Approximations
Differences in survey and clinical capture between cohorts introduce mapping approximations:
- **Framingham Heart Study:**
  - `current_smoker` mapped to `ever_smoked_100`: Current smoking does not capture former smokers who smoked >= 100 lifetime cigarettes.
  - `prevalent_hyp` mapped to `told_high_bp`: Hypertensive status at examination is an epidemiological indicator, not identical to doctor-told diagnosis.
  - Blood glucose: Recorded as a single measurement without protocol specification of fasting duration.
- **CDC BRFSS (Kaggle & Core Parquet):**
  - Age: Recorded in 13 ordinal five-year intervals (`_AGEG5YR`), mapped to category midpoints (e.g. 18–24 -> 21, 80+ -> 82), collapsing intra-interval variance.
  - Sex Coding: Kaggle dataset description specifies 0 = female, 1 = male (https://www.kaggle.com/datasets/alexteboul/diabetes-health-indicators-dataset), coding taken from the Kaggle description, TO CONFIRM.
- **Cardio70k Examination Records:**
  - Glucose: Recorded only as 3-level ordinal category (`gluc`: 1, 2, 3), precluding diabetes evaluation.
  - Blood Pressure: Raw examination measurements required systematic rule-based cleaning (1,234 raw inverted rows, with 7 negative values caught in Rule 1, leaving 1,227 non-negative inverted rows handled in Rule 2: 100 swapped and 1,127 set to NaN). Clean measured hypertension prevalence is 81.56% (56,061 / 68,737).
- **Pima Indians Diabetes:**
  - All participants are adult females of Pima Indian heritage. Features lack waist circumference and smoking history, necessitating overlap refit.

### 4. South Asian Applicability
**None of these five external cohorts is a South Asian population; DHS validation is still required.**
The external cohorts comprise North American general survey participants, historic suburban communities, and Indigenous American cohorts. South Asian populations exhibit different metabolic risk profiles, earlier onset of dysglycemia, and altered adiposity distributions. Validation on South Asian Demographic and Health Surveys (India NFHS-5, Bangladesh DHS, Nepal DHS) remains necessary prior to clinical deployment.

---

*Report generated automatically by `backend-poc-technical/ml/external_validation.py`.*
