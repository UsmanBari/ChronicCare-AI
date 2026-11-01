# Cardio70k Dataset Cleaning Report

## Overview
- **Dataset:** Cardio70k (`cardio_train.csv`)
- **Total Raw Records:** 70,000
- **File Format:** Semicolon-delimited CSV (`sep=';'`)
- **Target Concept:** Cardiovascular Disease (`cardio` / `cvd`) and measured hypertension (`htn_measured_130_80`)

## Demographic & Anthropometric Verification
### Gender Coding Verification
- **Empirical Evidence:**
  - Group `gender == 1`: Mean height = 161.36 cm (N = 45,530)
  - Group `gender == 2`: Mean height = 169.95 cm (N = 24,470)
  - Mean difference: +8.59 cm in group 2
- **Conclusion:** Group 2 represents male (`sex_male = 1`), and group 1 represents female (`sex_male = 0`).

### Age
- Converted from days to years: `age_years = age_days / 365.25`

### Body Mass Index (BMI)
- Derived as $\text{weight} / (\text{height}/100)^2$
- Plausibility range applied: $[12.0, 80.0]$
- Rows with BMI out of range set to NaN: 41 rows

## Blood Pressure Cleaning Rules & Audit Counts

| Rule | Description | Condition | Count Affected | Action Taken |
|---|---|---|---|---|
| Rule 1 | Negative BP values | `ap_hi < 0` or `ap_lo < 0` | 8 rows (7 SBP, 1 DBP) | Set to NaN |
| Rule 2 | Inverted BP readings | `ap_hi < ap_lo` | 1,234 rows total | 100 swapped (both in plausible range post-swap); 1,127 unswappable set to NaN |
| Rule 3 | Extreme typo values | BP $\ge 1000$ (e.g. 1100, 14020, 16020) | 24 rows (24 SBP, 0 DBP) | Set to NaN (no divide-by-10 guessing) |
| Rule 4 | Out-of-app plausibility bounds | SBP $\notin [60, 260]$ or DBP $\notin [30, 160]$ | 65 rows (21 SBP, 55 DBP) | Set to NaN |
| Rule 5 | Inconsistent residual relationship | SBP $\le$ DBP after rules 1–4 | 2 rows | Set to NaN |

## Final Clean Record Counts
- **Total Valid BP Records:** 68,775 rows (98.25%)
- **Complete Feature Rows (age, sex, bmi, sbp, dbp):** 68,737 rows (98.20%)
- **Measured Hypertension Prevalence (SBP $\ge$ 130 or DBP $\ge$ 80):** 46.52% (31,993 / 68,775)
