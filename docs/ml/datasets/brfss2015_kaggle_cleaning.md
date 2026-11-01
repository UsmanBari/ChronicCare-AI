# BRFSS 2015 Kaggle Indicators Cleaning Report

## Overview
- **Dataset:** BRFSS 2015 Kaggle (`diabetes_binary_health_indicators_BRFSS2015.csv`)
- **Total Records:** 253,680
- **File Format:** Comma-delimited CSV
- **Target Concept:** Binary Diabetes Status (`Diabetes_binary` $\to$ `diabetes`)

## Demographic Mappings & Audits
### Sex Coding
- `Sex == 0.0`: Female (N = 141,974, 55.97%)
- `Sex == 1.0`: Male (N = 111,706, 44.03%)
- Mapped directly to standard `sex_male`.

### Age Categorization to Midpoint
Per CDC BRFSS documentation, `_AGEG5YR` (mapped in Kaggle as `Age` 1 to 13) is converted to continuous age midpoint `age_mid` and aliased to `age`:

| Age Group Code | Source Age Range | Documented Midpoint (`age_mid`) | Record Count |
|---|---|---|---|
| 1 | 18–24 | 21.0 | 5,700 |
| 2 | 25–29 | 27.0 | 7,598 |
| 3 | 30–34 | 32.0 | 11,123 |
| 4 | 35–39 | 37.0 | 13,823 |
| 5 | 40–44 | 42.0 | 16,157 |
| 6 | 45–49 | 47.0 | 19,819 |
| 7 | 50–54 | 52.0 | 26,314 |
| 8 | 55–59 | 57.0 | 30,832 |
| 9 | 60–64 | 62.0 | 33,244 |
| 10 | 65–69 | 67.0 | 32,194 |
| 11 | 70–74 | 72.0 | 23,533 |
| 12 | 75–79 | 77.0 | 15,980 |
| 13 | 80+ | 82.0 | 17,363 |

## Feature Standardizations & Missingness
- Every indicator in the 21 Kaggle indicators is complete (0 missing values across all 253,680 records).
- `HighBP` $\to$ `high_bp` (aliased to `told_high_bp`)
- `Smoker` $\to$ `ever_smoker` (aliased to `ever_smoked_100`)
- `Diabetes_binary` $\to$ `diabetes` (aliased to `told_diabetes`)
- `BMI` $\to$ `bmi`

## Summary
- **Total Valid Complete Records:** 253,680 (100.0%)
- **Diabetes Prevalence:** 13.93% (35,346 / 253,680)
- **High Blood Pressure Prevalence:** 42.90% (108,829 / 253,680)
