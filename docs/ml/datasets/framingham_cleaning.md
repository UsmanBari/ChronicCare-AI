# Framingham Heart Study Dataset Cleaning Report

## Overview
- **Dataset:** Framingham Cohort (`framingham.csv`)
- **Total Raw Records:** 4,238
- **File Format:** Comma-delimited CSV
- **Target Concept:** Prevalent Hypertension (`prevalent_hyp` / `prevalentHyp`) and Prevalent Diabetes (`diabetes`)

## Standard Column Renaming
- `male` $\to$ `sex_male`
- `age` $\to$ `age`
- `BMI` $\to$ `bmi`
- `sysBP` $\to$ `sbp`
- `diaBP` $\to$ `dbp`
- `currentSmoker` $\to$ `current_smoker` (aliased to `ever_smoked_100`)
- `diabetes` $\to$ `diabetes` (aliased to `told_diabetes`)
- `prevalentHyp` $\to$ `prevalent_hyp` (aliased to `high_bp`, `told_high_bp`)
- `glucose` $\to$ `glucose`
- `totChol` $\to$ `total_chol`
- `BPMeds` $\to$ `bp_meds`

## Missing Value (NA) Audit Counts

| Column | Description | NA Count | % Missing |
|---|---|---|---|
| `age` | Participant age in years | 0 | 0.00% |
| `sex_male` | Binary sex (1=Male, 0=Female) | 0 | 0.00% |
| `bmi` | Body Mass Index ($\text{kg/m}^2$) | 19 | 0.45% |
| `sbp` | Systolic blood pressure (mmHg) | 0 | 0.00% |
| `dbp` | Diastolic blood pressure (mmHg) | 0 | 0.00% |
| `current_smoker` | Current smoker status | 0 | 0.00% |
| `diabetes` | Prevalent diabetes status | 0 | 0.00% |
| `prevalent_hyp` | Prevalent hypertension status | 0 | 0.00% |
| `glucose` | Casual serum glucose (mg/dL) | 388 | 9.16% |
| `total_chol` | Total cholesterol (mg/dL) | 50 | 1.18% |
| `bp_meds` | Use of anti-hypertensive medication | 53 | 1.25% |

## Summary
- **Total Rows:** 4,238
- **Complete Feature Rows across all 11 standardized columns:** 3,775 (89.07%)
- **Prevalent Hypertension Rate:** 31.05% (1,316 / 4,238)
- **Prevalent Diabetes Rate:** 2.57% (109 / 4,238)

