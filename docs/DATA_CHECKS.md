# ChronicCare AI - Survey Data Quality & Checks Report

> **Notice:** This document contains AGGREGATES ONLY. It strictly contains zero patient identifiers, zero SEQN records, and zero raw clinical observations.
> Generated automatically by backend-poc-technical/ml/data_checks.py.

---

## Part 1: NHANES (1999-2023, 11 Cycles)

### D1. Sample Sizes and Deduplication
- **Total Participants:** 113,249
- **Adults (age >= 18):** 67,357
- **Duplicate SEQN Count:** 0 (must be 0)

| cycle | Total Participants | Adults (18+) | Adult % |
| --- | --- | --- | --- |
| 1999-2000 | 9965.0 | 5448.0 | 54.7 |
| 2001-2002 | 11039.0 | 5993.0 | 54.3 |
| 2003-2004 | 10122.0 | 5620.0 | 55.5 |
| 2005-2006 | 10348.0 | 5563.0 | 53.8 |
| 2007-2008 | 10149.0 | 6228.0 | 61.4 |
| 2009-2010 | 10537.0 | 6527.0 | 61.9 |
| 2011-2012 | 9756.0 | 5864.0 | 60.1 |
| 2013-2014 | 10175.0 | 6113.0 | 60.1 |
| 2015-2016 | 9971.0 | 5992.0 | 60.1 |
| 2017-2018 | 9254.0 | 5856.0 | 63.3 |
| 2021-2023 | 11933.0 | 8153.0 | 68.3 |
| Total Pooled | 113249.0 | 67357.0 | 59.5 |

### D2. Missing Value Percentage Across Cycles (Adults Only)
| cycle | age | sex_male | race_eth | income_poverty_ratio | bmi | waist_cm | height_cm | weight_kg | sbp | dbp | pulse | hba1c | fasting_glucose | total_chol | told_diabetes | takes_insulin | takes_diabetes_pills | told_high_bp | takes_bp_meds | family_hx_diabetes | ever_smoked_100 | exam_weight_2yr | borderline_diabetes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1999-2000 | 0.0 | 0.0 | 0.0 | 15.5 | 10.0 | 11.9 | 10.0 | 9.7 | 11.8 | 11.8 | 11.3 | 13.5 | 58.1 | 15.2 | 1.2 | 28.4 | 91.2 | 1.5 | 77.6 | 100.0 | 10.7 | 0.0 | 0.0 |
| 2001-2002 | 0.0 | 0.0 | 0.0 | 8.0 | 12.7 | 12.0 | 9.6 | 11.2 | 11.7 | 11.7 | 11.2 | 11.6 | 55.9 | 13.1 | 1.3 | 0.0 | 91.4 | 1.5 | 77.8 | 100.0 | 9.9 | 0.0 | 0.0 |
| 2003-2004 | 0.0 | 0.0 | 0.0 | 6.4 | 7.5 | 11.0 | 7.5 | 7.2 | 12.0 | 12.0 | 10.1 | 10.2 | 56.9 | 11.2 | 1.3 | 0.0 | 90.3 | 1.3 | 74.3 | 100.0 | 10.4 | 0.0 | 0.0 |
| 2005-2006 | 0.0 | 0.0 | 0.0 | 5.3 | 5.9 | 9.2 | 5.6 | 5.6 | 9.1 | 9.1 | 8.1 | 9.7 | 56.4 | 10.2 | 1.7 | 0.0 | 100.0 | 0.3 | 76.2 | 12.5 | 10.6 | 0.0 | 0.0 |
| 2007-2008 | 0.0 | 0.0 | 0.0 | 9.5 | 5.5 | 9.4 | 5.4 | 5.4 | 8.5 | 8.5 | 8.4 | 9.9 | 55.8 | 10.3 | 1.6 | 0.0 | 100.0 | 0.1 | 69.7 | 6.8 | 4.8 | 0.0 | 0.0 |
| 2009-2010 | 0.0 | 0.0 | 0.0 | 10.1 | 3.7 | 8.2 | 3.6 | 3.6 | 7.0 | 7.0 | 6.8 | 7.6 | 55.0 | 8.5 | 2.0 | 0.0 | 83.1 | 0.2 | 70.3 | 7.0 | 4.7 | 0.0 | 0.0 |
| 2011-2012 | 0.0 | 0.0 | 0.0 | 9.1 | 5.8 | 10.3 | 5.6 | 5.6 | 8.7 | 8.7 | 8.6 | 9.6 | 55.7 | 11.5 | 2.1 | 0.0 | 81.9 | 0.1 | 70.3 | 7.0 | 5.3 | 0.0 | 0.0 |
| 2013-2014 | 0.0 | 0.0 | 0.0 | 7.9 | 4.4 | 8.6 | 4.2 | 4.1 | 6.5 | 6.5 | 6.3 | 6.9 | 55.4 | 7.7 | 2.9 | 0.0 | 80.9 | 0.1 | 70.4 | 7.5 | 0.0 | 0.0 | 0.0 |
| 2015-2016 | 0.0 | 0.0 | 0.0 | 11.3 | 5.5 | 10.4 | 5.3 | 5.4 | 7.0 | 7.0 | 6.9 | 9.2 | 57.1 | 10.0 | 2.3 | 0.1 | 75.5 | 0.1 | 69.2 | 6.4 | 0.2 | 0.0 | 0.0 |
| 2017-2018 | 0.0 | 0.0 | 0.0 | 14.3 | 7.2 | 11.5 | 7.0 | 7.0 | 8.4 | 8.4 | 8.3 | 10.2 | 56.7 | 11.6 | 3.0 | 0.0 | 72.2 | 0.2 | 66.9 | 6.3 | 0.0 | 0.0 | 0.0 |
| 2021-2023 | 0.0 | 0.0 | 0.0 | 17.0 | 23.5 | 26.2 | 23.2 | 23.4 | 24.9 | 24.9 | 24.9 | 26.4 | 59.2 | 29.9 | 3.4 | 86.8 | 72.7 | 0.2 | 63.8 | 100.0 | 0.4 | 0.0 | 0.0 |

### D3. Clinical Plausibility Boundary Checks (Adults Only, Counted Not Dropped)
| Clinical Measure | Boundary Criterion | Count Out of Bounds |
|---|---|---|
| Systolic BP (sbp) | < 60 or > 260 mmHg | 2 |
| Diastolic BP (dbp) | < 30 or > 160 mmHg | 582 |
| Diastolic Zero | dbp == 0 mmHg | 0 |
| Systolic <= Diastolic | sbp <= dbp | 0 |
| Body Mass Index (bmi) | < 12 or > 80 kg/m2 | 9 |
| Waist Circumference | < 40 or > 200 cm | 0 |
| Glycated Hemoglobin (hba1c) | < 3 or > 20 % | 2 |
| Fasting Glucose | < 20 or > 600 mg/dL | 1 |

#### Age Top-Coding by Cycle
- **Top-coded at 85:** 1999-2000, 2001-2002, 2003-2004, 2005-2006 (cycles prior to 2007-2008)
- **Top-coded at 80:** 2007-2008, 2009-2010, 2011-2012, 2013-2014, 2015-2016, 2017-2018, 2021-2023 (cycles from 2007-2008 onward)

### D4. Descriptive Candidate Label Prevalence by Cycle (Adults Only)
| Cycle | Told Diabetes | Borderline Diabetes | Measured Diabetes (A1c>=6.5 or FPG>=126) | Undiagnosed Diabetes | Told High BP | Takes BP Meds | BP >= 130/80 (Stage 1+) | BP >= 140/90 (Stage 2) | Uncontrolled (Told HBP & BP>=140/90) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1999-2000 | 482 / 5,384 (9.0%) | 57 / 5,448 (1.0%) | 451 / 4,712 (9.6%) | 118 / 4,657 (2.5%) | 1,511 / 5,366 (28.2%) | 1,065 / 1,220 (87.3%) | 2,112 / 4,805 (44.0%) | 1,145 / 4,805 (23.8%) | 652 / 1,308 (49.8%) |
| 2001-2002 | 516 / 5,914 (8.7%) | 77 / 5,993 (1.3%) | 487 / 5,299 (9.2%) | 146 / 5,224 (2.8%) | 1,665 / 5,905 (28.2%) | 1,182 / 1,333 (88.7%) | 2,183 / 5,290 (41.3%) | 1,107 / 5,290 (20.9%) | 631 / 1,436 (43.9%) |
| 2003-2004 | 547 / 5,548 (9.9%) | 69 / 5,620 (1.2%) | 479 / 5,051 (9.5%) | 128 / 4,988 (2.6%) | 1,781 / 5,548 (32.1%) | 1,290 / 1,447 (89.1%) | 1,968 / 4,943 (39.8%) | 1,043 / 4,943 (21.1%) | 635 / 1,543 (41.2%) |
| 2005-2006 | 511 / 5,469 (9.3%) | 88 / 5,563 (1.6%) | 460 / 5,032 (9.1%) | 122 / 4,946 (2.5%) | 1,609 / 5,547 (29.0%) | 1,157 / 1,324 (87.4%) | 1,787 / 5,057 (35.3%) | 884 / 5,057 (17.5%) | 544 / 1,457 (37.3%) |
| 2007-2008 | 761 / 6,126 (12.4%) | 96 / 6,228 (1.5%) | 757 / 5,619 (13.5%) | 249 / 5,525 (4.5%) | 2,133 / 6,222 (34.3%) | 1,670 / 1,890 (88.4%) | 2,195 / 5,700 (38.5%) | 1,132 / 5,700 (19.9%) | 698 / 1,962 (35.6%) |
| 2009-2010 | 727 / 6,399 (11.4%) | 124 / 6,527 (1.9%) | 742 / 6,038 (12.3%) | 227 / 5,916 (3.8%) | 2,210 / 6,514 (33.9%) | 1,742 / 1,936 (90.0%) | 2,209 / 6,072 (36.4%) | 1,050 / 6,072 (17.3%) | 687 / 2,059 (33.4%) |
| 2011-2012 | 706 / 5,740 (12.3%) | 119 / 5,864 (2.0%) | 706 / 5,306 (13.3%) | 207 / 5,192 (4.0%) | 2,020 / 5,856 (34.5%) | 1,520 / 1,742 (87.3%) | 2,038 / 5,356 (38.1%) | 936 / 5,356 (17.5%) | 616 / 1,852 (33.3%) |
| 2013-2014 | 726 / 5,934 (12.2%) | 176 / 6,113 (2.9%) | 693 / 5,692 (12.2%) | 170 / 5,525 (3.1%) | 2,160 / 6,108 (35.4%) | 1,584 / 1,809 (87.6%) | 2,000 / 5,716 (35.0%) | 939 / 5,716 (16.4%) | 638 / 2,022 (31.6%) |
| 2015-2016 | 845 / 5,856 (14.4%) | 132 / 5,992 (2.2%) | 817 / 5,442 (15.0%) | 210 / 5,318 (3.9%) | 2,081 / 5,986 (34.8%) | 1,566 / 1,848 (84.7%) | 2,184 / 5,571 (39.2%) | 1,064 / 5,571 (19.1%) | 714 / 1,956 (36.5%) |
| 2017-2018 | 878 / 5,678 (15.5%) | 174 / 5,856 (3.0%) | 860 / 5,264 (16.3%) | 215 / 5,099 (4.2%) | 2,130 / 5,846 (36.4%) | 1,649 / 1,941 (85.0%) | 2,376 / 5,367 (44.3%) | 1,262 / 5,367 (23.5%) | 798 / 1,967 (40.6%) |
| 2021-2023 | 1,073 / 7,876 (13.6%) | 272 / 8,153 (3.3%) | 836 / 6,004 (13.9%) | 179 / 5,788 (3.1%) | 2,956 / 8,139 (36.3%) | 2,437 / 2,952 (82.6%) | 2,465 / 6,123 (40.3%) | 1,105 / 6,123 (18.0%) | 714 / 2,241 (31.9%) |
| **Total Pooled** | 7,772 / 65,924 (11.8%) | 1,384 / 67,357 (2.1%) | 7,288 / 59,459 (12.3%) | 1,971 / 58,178 (3.4%) | 22,256 / 67,037 (33.2%) | 16,862 / 19,442 (86.7%) | 23,517 / 60,000 (39.2%) | 11,667 / 60,000 (19.4%) | 7,327 / 19,803 (37.0%) |

> **Denominator Note on Antihypertensive Meds & Control:** In NHANES, the medication question (`takes_bp_meds` from BPQ050A) is only asked conditionally to participants who reported having been told they had high blood pressure (`told_high_bp == 1`). Therefore, 'Takes BP Meds' (7,750 / 8,822, 87.8% among told) and 'Uncontrolled' (2,607 / 8,822, 29.6% among told) evaluate strictly the told-high-BP denominator. Consequently, `hypertension_told_or_meds` equals `hypertension_told` across all NHANES cycles (12,929 / 40,958, 31.6%).

### D5. Weighted vs. Unweighted Prevalence (Pooled Over 11 Cycles)
Per CDC NHANES analytical guidance, when pooling N cycles of 2-year survey data, the 2-year examination weights (exam_weight_2yr) are divided by N (N = 11 cycles):

| Clinical Label | Unweighted Prevalence | Weighted Prevalence (exam_weight_2yr / 11) | Sample Denominator |
|---|---|---|---|
| Told Diabetes (DIQ010 == 1) | 11.79% | 9.03% | 65,924 adults |
| Measured Diabetes (HbA1c >= 6.5 or FPG >= 126) | 12.26% | 9.28% | 59,459 adults with lab |

### D6. NHANES Data Notes
1. **Fasting Glucose Subsample:** Fasting glucose is measured only in the morning exam subsample (29,218 of 67,357 adults, ~43.4%), whereas HbA1c is available for 59,412 adults (~88.2%).
2. **Age Top-Coding Shift:** Max age is top-coded at 85 years in cycles 1999-2006, and top-coded at 80 years from 2007-2008 onward to protect participant privacy.
3. **Blood Pressure Plausibility & DBP Anomaly Explanation:** Found 0 adults with `dbp == 0` mmHg because get_nhanes.py:129 (`vals = df[have].where(df[have] > 0)`) automatically filters out 0 values (which represent 'reading not taken' in CDC NHANES BPX/BPXO protocols) to NaN. Among non-null readings, 582 adults had DBP out of clinical plausibility bounds (< 30 or > 160 mmHg): exactly 582 adults had `dbp < 30 mmHg` and 0 adults had `dbp > 160 mmHg`. Additionally, 2 adults had `sbp <= dbp` (auscultatory artifact). These represent anomalies that should be flagged or cleaned prior to model fitting.
4. **Borderline Diabetes Coding:** In get_nhanes.py, borderline_diabetes is derived from DIQ010 == 3. When DIQ010 is missing or skipped, it is 0 rather than NaN in the raw derived column.

---

## Part 2: BRFSS (2015, 2017, 2019, 2021, 2023 - 5 Odd-Year Surveys)

### D7. Survey Rows and Missing Percentages Across Survey Years
- **Total Rows:** 2,181,756

| year | Total Adults |
| --- | --- |
| 2015 | 441456 |
| 2017 | 450016 |
| 2019 | 418268 |
| 2021 | 438693 |
| 2023 | 433323 |

#### Missing % per Column per Survey Year:
| year | diabetes | prediabetes | high_bp | borderline_bp | bp_meds | high_chol | sex_male | age_group | age | bmi | smoker_status | ever_smoker | phys_active | heavy_drinker | gen_health | phys_hlth_days | ment_hlth_days | heart_disease | stroke | kidney_disease | education | income_group | race | has_insurance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2015.0 | 0.2 | 0.2 | 0.3 | 0.3 | 59.7 | 14.2 | 0.0 | 1.2 | 0.0 | 8.2 | 4.1 | 4.1 | 8.6 | 5.8 | 0.3 | 2.2 | 1.7 | 0.9 | 0.3 | 0.4 | 0.4 | 18.0 | 0.0 | 0.4 |
| 2017.0 | 0.2 | 0.2 | 0.3 | 0.3 | 59.8 | 7.1 | 0.1 | 1.4 | 0.0 | 8.1 | 4.2 | 4.2 | 7.6 | 6.7 | 0.3 | 2.1 | 1.6 | 0.9 | 0.3 | 0.4 | 0.4 | 16.7 | 0.0 | 0.4 |
| 2019.0 | 0.2 | 0.2 | 0.4 | 0.4 | 59.5 | 6.9 | 0.0 | 1.6 | 0.0 | 8.7 | 4.5 | 4.5 | 5.3 | 6.6 | 0.3 | 2.5 | 2.1 | 1.0 | 0.3 | 0.4 | 0.4 | 19.1 | 0.0 | 0.5 |
| 2021.0 | 0.2 | 0.2 | 0.4 | 0.4 | 60.9 | 14.6 | 0.0 | 2.2 | 0.0 | 10.7 | 5.7 | 5.7 | 0.2 | 8.0 | 0.3 | 2.2 | 1.8 | 1.0 | 0.3 | 0.4 | 0.6 | 21.5 | 0.0 | 4.0 |
| 2023.0 | 0.2 | 0.2 | 0.4 | 0.4 | 59.4 | 12.7 | 0.0 | 1.8 | 0.0 | 9.4 | 5.3 | 5.3 | 0.3 | 7.6 | 0.3 | 2.5 | 1.9 | 1.0 | 0.3 | 0.4 | 0.5 | 20.0 | 0.0 | 4.3 |

### D8. Diabetes and Hypertension Prevalence (Unweighted vs Survey Weighted)
| Year | Total Rows | Diabetes Unweighted | Diabetes Weighted | High BP Unweighted | High BP Weighted |
| --- | --- | --- | --- | --- | --- |
| 2015 | 441,456 | 13.0% | 10.5% | 40.5% | 32.0% |
| 2017 | 450,016 | 13.5% | 10.9% | 40.4% | 32.5% |
| 2019 | 418,268 | 13.8% | 11.1% | 40.7% | 32.6% |
| 2021 | 438,693 | 13.2% | 11.4% | 39.4% | 32.8% |
| 2023 | 433,323 | 13.8% | 12.1% | 40.8% | 34.5% |
| **Pooled Total** | 2,181,756 | 13.4% | 11.2% | 40.4% | 32.9% |

### D9. BMI Extremes and Age Group Distribution
- **BMI < 12 or > 80 kg/m2:** 788 records out of 1,985,322 valid BMI records (0.04%)

#### Age Group Distribution (_AGEG5YR):
| index | 2015 | 2017 | 2019 | 2021 | 2023 | Total Pooled | Pooled % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 18-24 | 24192 | 26233 | 25098 | 26025 | 26280 | 127828 | 6.0 |
| 25-29 | 19746 | 22388 | 20817 | 21623 | 21247 | 105821 | 4.9 |
| 30-34 | 22917 | 24799 | 23058 | 25724 | 24803 | 121301 | 5.7 |
| 35-39 | 24545 | 26297 | 24724 | 28559 | 27153 | 131278 | 6.1 |
| 40-44 | 25942 | 25300 | 24258 | 29435 | 28463 | 133398 | 6.2 |
| 45-49 | 30276 | 30134 | 26075 | 28391 | 27070 | 141946 | 6.6 |
| 50-54 | 39881 | 37149 | 31768 | 34086 | 31291 | 174175 | 8.1 |
| 55-59 | 46209 | 45124 | 38902 | 38009 | 34219 | 202463 | 9.4 |
| 60-64 | 49794 | 49974 | 44456 | 44298 | 41974 | 230496 | 10.7 |
| 65-69 | 49264 | 50020 | 45206 | 45762 | 46099 | 236351 | 11.0 |
| 70-74 | 38362 | 41399 | 41535 | 42920 | 43533 | 207749 | 9.7 |
| 75-79 | 28232 | 29269 | 29767 | 29747 | 34543 | 151558 | 7.1 |
| 80+ | 36760 | 35829 | 35916 | 34507 | 38869 | 181881 | 8.5 |

### D10. BRFSS Data Notes
1. **Odd Years Survey Design:** Odd years (2015, 2017, 2019, 2021, 2023) are chosen because high blood pressure questions (BPHIGH4 / BPHIGH6 and BPMEDS) are optional modules in even years but standard in odd survey years.
2. **Self-Report Nature:** BRFSS is an anonymous telephone survey. Diabetes prevalence (~11.2%) and high blood pressure prevalence (~32.9%) are entirely based on self-reported clinical diagnoses, differing from NHANES laboratory-confirmed measures.
3. **Variable Mapping Fixes Verified:** Both kidney_disease (mapped from CHCKIDNY in 2015/2017 and CHCKDNY1/2 in 2019+) and has_insurance (mapped from _HLTHPL1 in 2023 and _HLTHPLN/1 in earlier years) show zero missing candidate exceptions.

## Temporal Splits (nhanes_temporal_v1)

| Split | Cycles | Adults | Told Diabetes | Measured Diabetes | BP >= 130/80 |
| --- | --- | --- | --- | --- | --- |
| train_core | 1999-2012 (7) | 41243 | 4250 / 40580 (10.5%) | 4082 / 37057 (11.0%) | 14492 / 37223 (38.9%) |
| validation | 2013-2016 (2) | 12105 | 1571 / 11790 (13.3%) | 1510 / 11134 (13.6%) | 4184 / 11287 (37.1%) |
| test | 2017-2023 (2) | 14009 | 1951 / 13554 (14.4%) | 1696 / 11268 (15.1%) | 4841 / 11490 (42.1%) |
