# ChronicCare AI — Machine Learning Experiments Summary & Governance Report

> **Document Status:** Official Summary of Day 4 Risk Model Benchmarks  
> **Evaluation Date:** 29 October 2026  
> **Clinical Governance Decision:** Usman (ML Lead) & Clinical Safety Team  
> **Guiding Principle:** The model proposes, the rules decide.

---

## 1. Machine Learning Experiment Benchmark Matrix

All models were evaluated on the held-out NHANES temporal test set (`test` 2017–2023, 2 survey cycles). Thresholds and hyperparameters were locked strictly on the temporal validation set (`validation` 2013–2016). Decision threshold policy is `min_sensitivity >= 0.80` on validation.

| Experiment Name | Clean n (train/val/test) | Test Prev | Chosen Model (D10) | Val AUROC | Test AUROC [95% CI] | Test Sens / Spec / PPV | Cal Slope (Val / Test) | Worst Subgroup Sens (>= 50 pos) | Card Pop AUROC / Sens | Gap vs Ref (Val / Test) | FYP-1 Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `diabetes_basic_nhanes` | 29,084 / 9,264 / 9,117 | 4.26% | lr ({'C': 10.0}) | 0.7542 | 0.7403 [0.7182–0.7616] | 85.05% / 51.40% / 7.22% | 0.850 / 0.820 | age_band=18-39: 58.82% (n=51) | 0.6561 / 93.68% | +0.0002 (val) / -0.0019 (test) | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `diabetes_full_nhanes` | 27,448 / 8,714 / 8,681 | 4.15% | lr ({'C': 0.1}) | 0.7617 | 0.7527 [0.7293–0.7748] | 85.28% / 52.23% / 7.17% | 0.857 / 0.848 | age_band=40-59: 76.00% (n=125) | 0.6640 / 93.18% | +0.0077 (val) / +0.0106 (test) | NOT SHIPPED (Decision 29 Oct: +0.0075 gain over basic does not justify waist/vital burden; flag off) |
| `htn_basic_nhanes` | 22,061 / 7,126 / 7,037 | 30.67% | lr ({'C': 0.01}) | 0.7540 | 0.7148 [0.7022–0.7262] | 80.40% / 52.65% / 42.89% | 1.066 / 0.869 | age_band=18-39: 38.41% (n=552) | 0.5442 / 89.53% | +0.0007 (val) / -0.0002 (test) | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `htn_full_nhanes` | 20,766 / 6,609 / 6,537 | 30.66% | lr ({'C': 0.01}) | 0.7546 | 0.7105 [0.6983–0.7230] | 80.49% / 52.08% / 42.62% | 1.088 / 0.858 | age_band=18-39: 39.14% (n=511) | 0.5317 / 90.75% | +0.0013 (val) / -0.0045 (test) | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `diabetes_ref_age_sex_bmi` | 32,081 / 9,278 / 9,133 | 4.25% | lr ({'C': 1.0}) | 0.7540 | 0.7421 [0.7203–0.7640] | 84.28% / 50.05% / 6.96% | 0.854 / 0.825 | age_band=18-39: 50.98% (n=51) | 0.6582 / 89.47% | Ref Baseline | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |
| `htn_ref_age_sex_bmi` | 25,033 / 7,246 / 7,206 | 30.81% | lr ({'C': 0.1}) | 0.7533 | 0.7150 [0.7030–0.7269] | 80.14% / 53.11% / 43.21% | 1.026 / 0.840 | age_band=18-39: 37.99% (n=558) | 0.5437 / 92.15% | Ref Baseline | NOT SHIPPED (gate_1_test_auroc_ge_0_75, gate_4_subgroup_sens_ge_0_60) |

---

## 2. Guideline-Rule Screening Baselines (No Training Required)

Evaluated on the exact same held-out test cohort records and card audience as the diabetes models:

| Guideline Screening Rule | Cohort Evaluated | Prevalence | Sensitivity | Specificity | PPV | Clinical Evidence Source |
| --- | --- | --- | --- | --- | --- | --- |
| Rule Baseline: Age >= 35 (General Test) | n=9,117 (pos=388) | 4.26% | 93.04% | 28.71% | 5.48% | as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman |
| Rule Baseline: Age 35-70 & BMI >= 25 (General Test) | n=9,117 (pos=388) | 4.26% | 63.66% | 58.01% | 6.31% | as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman |
| Rule Baseline: Age >= 35 (Card Audience: High BP) | n=2,720 (pos=190) | 6.99% | 96.32% | 8.46% | 7.32% | as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman |
| Rule Baseline: Age 35-70 & BMI >= 25 (Card Audience: High BP) | n=2,720 (pos=190) | 6.99% | 60.00% | 46.17% | 7.72% | as recommended by ADA Standards / USPSTF 2021 — citation to be confirmed by Usman |

---

## 3. Honest Findings & Clinical Governance Synthesis

1. **All Six Configurations Are NOT SHIPPED for Patient-Facing Risk Cards:** Every evaluated risk model fails critical D11 acceptance gates or clinical utility bars. The hypertension models fail Gate 1 (test AUROC is 0.7148 for BASIC and 0.7105 for FULL, well below the 0.75 threshold) and catastrophic young-adult sensitivity collapse (Gate 4 failure: missing over 60% of young hypertensive individuals aged 18–39). While the `diabetes_full_nhanes` model technically passed the mathematical D11 gates under plain logistic regression, it is rejected by clinical governance because its marginal gain does not justify clinical burden.
2. **BASIC and FULL Add Little or Nothing Over Age, Sex, and BMI:** Comparing the engineered models against the reference baseline (`diabetes_ref_age_sex_bmi` and `htn_ref_age_sex_bmi`) demonstrates extreme feature parsimony limits. For diabetes, adding smoking status and hypertension awareness (`diabetes_basic_nhanes`) improves validation AUROC by only **+0.0002** and actually decreases test AUROC by **-0.0019**. Adding waist circumference and blood pressure readings (`diabetes_full_nhanes`) yields a validation gain of only **+0.0075** (test gain of **+0.0124**), which fails to justify asking patients for uncollected physical measurements like waist circumference. For hypertension, the FULL model test AUROC (0.7105) is actually **-0.0043** lower than the BASIC model.
3. **Card-Population Discrimination is Poor (Near Chance for Hypertension):** When evaluated on the exact reciprocal patient cohort who would view the risk card in production, discrimination drops significantly. In patients with hypertension screened for undiagnosed diabetes, card AUROC is only **0.6561** (with a positive predictive value of ~7%). Worse, in patients with diagnosed diabetes screened for hypertension, card AUROC collapses to **0.5442**, which is barely distinguishable from a random coin flip (0.50).
4. **Young Adults Are Systematically Missed Across All Models:** Because age dominates tabular logistic regression coefficients (odds ratio ~2.0 to 2.3 per 1 SD), models exhibit severe age disparity. In older adults (60+), sensitivity is ~95–97% but specificity collapses to near zero (flagging almost everyone). In contrast, in young adults aged 18–39, sensitivity drops to **38.41%** for hypertension and **58.82%** for diabetes, systematically failing the patients who have the most life-years to gain from early diagnosis.
5. **Low Precision and High False-Positive Burden:** At ~4% baseline prevalence of undiagnosed diabetes, operating at 85% sensitivity yields an operational specificity of only ~51% and a Positive Predictive Value (PPV) of **7.22%**. Approximately 13 out of every 14 flagged individuals do not have undiagnosed diabetes, creating unwarranted patient anxiety and potential healthcare provider alert fatigue.
6. **Simple Guideline Rules Match or Outperform Complex Models:** Evaluating deterministic screening rules recommended by ADA Standards and USPSTF 2021 on the exact same test records demonstrates that software models provide no decisive clinical edge. The simple rule `Age >= 35` achieves **93.04% sensitivity** (substantially higher than the model's 85.05%), while `Age 35–70 & BMI >= 25` achieves **63.66% sensitivity** and **58.01% specificity** (higher specificity than the basic model's 51.40%) without requiring mathematical model scoring or algorithmic complexity.
7. **Official Decision (Usman, 29 October 2026):** **No patient-facing risk card will be shown in FYP-1.** The configuration flag `RISK_ENABLED` remains locked `off` across all production environments. The Day 5 runtime scoring machinery and Day 7 integration will still be built, tested, and hermetically verified behind this feature flag to complete the technical architecture. For patients with diabetes, we formally recommend to supervising clinicians and doctors that the application directly request an actual blood pressure cuff measurement during check-ins rather than attempting to infer hypertension probabilistically from demographic proxies.
8. **External Validation Limitation for BRFSS (Day 6):** The BRFSS surveillance dataset contains no laboratory specimen data (no HbA1c, fasting glucose) and no physical cuff examination measurements. Consequently, BRFSS cannot evaluate undiagnosed target labels (`diabetes_undiagnosed` or `hypertension_measured_130_80`). Saad's Day 6 external validation on BRFSS will be strictly limited to evaluating self-reported awareness labels (`diabetes_told`, `hypertension_told`) or assessing feature drift across demographics.
