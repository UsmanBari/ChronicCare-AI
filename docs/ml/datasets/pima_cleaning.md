# Pima Indians Diabetes Dataset Cleaning Report

## Overview
- **Dataset:** Pima Indians Diabetes (`pima-indians-diabetes.data.csv`)
- **Total Records:** 768
- **Format:** Headerless CSV (9 columns)
- **Cohort:** Pima Indian heritage females aged $\ge 21$ from Phoenix, Arizona
- **Target Concept:** Diabetes Onset within 5 years (`Outcome` $\to$ `diabetes`)

## Standardization & Zero-as-Missing Cleaning
In the raw dataset, physiological zeros in vital sign and laboratory columns represent missing measurements rather than true biological zeros (a living subject cannot have 0 blood pressure or 0 BMI).

| Feature | Biological Meaning | Zeros Converted to NaN | % Missing |
|---|---|---|---|
| `glucose` | 2-hour plasma oral glucose tolerance test (mg/dL) | 5 | 0.65% |
| `bp` | Diastolic blood pressure (mmHg) | 35 | 4.56% |
| `skin_thickness` | Triceps skin fold thickness (mm) | 227 | 29.56% |
| `insulin` | 2-hour serum insulin ($\mu\text{U/mL}$) | 374 | 48.70% |
| `bmi` | Body Mass Index ($\text{kg/m}^2$) | 11 | 1.43% |
| `pregnancies` | Number of times pregnant | 0 (0 is valid) | 0.00% |
| `diabetes_pedigree_function` | Genetic pedigree score | 0 (0 is valid) | 0.00% |
| `age` | Participant age in years | 0 (all $\ge 21$) | 0.00% |

## Demographic Standardization
- All subjects in the Pima dataset are adult females $\to$ `sex_male = 0` (constant).
- `Outcome` mapped to `diabetes` (and aliased to `outcome`, `told_diabetes`).

## Summary
- **Total Records:** 768
- **Records with complete age, sex, bmi, and diabetes:** 757 (98.57%)
- **Diabetes Prevalence (OGTT / clinical onset):** 34.90% (268 / 768)
