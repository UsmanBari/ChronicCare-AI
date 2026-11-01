# ChronicCare AI — Machine Learning Model Cards
**Document Version:** 1.0.0  
**Date:** 30 October 2026  
**Clinical Scope:** Adult Type 2 Diabetes and Hypertension Decision Support  
**Audience:** Internal Engineering, Clinical Reviewers, and Auditors  
**Governing Decisions:** D10, D12, D13, D14, D15 (`docs/ML_PLAN.md`, `docs/ml/EXPERIMENTS_SUMMARY.md` Section 6)  
**Safety Invariant:** *The model proposes, the rules decide.* Advisory only; never diagnoses; never prescribes; never lowers a triage level.

---

## Part 1: Primary Production Advisory Model (`diabetes_full_nhanes`)

### 1.1 Model Overview
- **Model Name:** `diabetes_full_nhanes`
- **Model Version:** `1.0.0`
- **Release Status:** **SHIP CANDIDATE (Provider-Only Experimental Advisory under D12)**
- **Model Type:** Regularized Logistic Regression (`scikit-learn LogisticRegression(C=0.1, penalty='l2')`)
- **Selection Decision:** Plain `lr` selected under D10 parsimony rule (lr_balanced did not beat plain lr by $\ge 0.01$ validation AUROC [gap: +0.0005]; best tree did not beat LR by $\ge 0.02$ validation AUROC [gap: +0.0010]).
- **Model Owner:** Usman (ML Lead)
- **Scikit-Learn Version:** 1.9.1
- **Training Source Split:** NHANES Temporal Split `nhanes_temporal_v1` (1999–2023)

### 1.2 Intended Use & Target Audience
- **Primary Audience:** **PROVIDER ONLY**. Displayed exclusively on the clinical provider review dashboard (`/api/provider/review/{checkin_id}`) behind the `RISK_ENABLED` environment feature flag.
- **Intended Clinical Role:** Experimental advisory ranking to assist clinical providers in identifying patients with hypertension who may benefit from glycemic screening (HbA1c / fasting glucose evaluation).
- **Mandatory Display Banner:**
  > *"Experimental: trained on US NHANES data, not validated for Pakistani patients"*
- **Target Population (Applicability Filter):** Adults aged $\ge 18$ with documented hypertension who **do not have diagnosed diabetes** (`conditions` contains `hypertension` and does NOT contain `diabetes`). Patients with diabetes only, dual diagnoses, or neither receive `None` from the risk agent.

### 1.3 Out-of-Scope & Misuse Caveats
- **Never Diagnostic:** Does not diagnose type 2 diabetes or prediabetes.
- **Never Patient-Facing in FYP-1:** Patients **never** see a numerical risk score, probability percentage, or risk badge.
- **Excluded Populations:**
  - Individuals with existing clinician-diagnosed or self-reported diabetes.
  - Individuals under 18 years of age.
  - Pregnant individuals (pregnancy alters glycemic dynamics and renal thresholds).
  - Use outside a licensed clinician's review.
- **Triage Level Floor:** Under D14 and the architectural safety invariant, risk assessment can **never lower a triage level**. It can only raise `routine -> review` when both `RISK_ENABLED=true` and `RISK_CAN_RAISE=true`.

### 1.4 Data, Cohort & Temporal Split
- **Dataset:** US National Health and Nutrition Examination Survey (NHANES) 1999–2023.
- **Target Label:** `diabetes_undiagnosed` ($\text{HbA1c} \ge 6.5\%$ [48 mmol/mol] or fasting plasma glucose $\ge 126\text{ mg/dL}$ [7.0 mmol/L] among adults without self-reported diagnosed diabetes).
- **Splits:**
  - **Train Core (1999–2014):** Initial 32,647 rows $\to$ dropped 5,199 missing $\to$ **27,448 clean** rows (1,043 positives, prevalence 3.80%).
  - **Validation (2015–2016):** Initial 9,371 rows $\to$ dropped 657 missing $\to$ **8,714 clean** rows (336 positives, prevalence 3.86%).
  - **Test (2017–2023):** Initial 9,261 rows $\to$ dropped 580 missing $\to$ **8,681 clean** rows (360 positives, prevalence 4.15%).

### 1.5 Features, Units & Application Acquisition
| Feature | Units / Format | How the App Acquires Feature | Standardized Coef | Odds Ratio (per 1 SD) |
| :--- | :--- | :--- | :--- | :--- |
| `age` | Years (18–85) | Calculated from `date_of_birth` in `patient_profiles` (`main.py:382`) and check-in date. | 0.5947 | 1.8124 |
| `waist_cm` | cm (40.0–200.0) | Optional profile field, added today (Part H) in `patient_profiles` (`main.py: ProfileUpdateRequest.waist_cm`). | 0.5073 | 1.6608 |
| `bmi` | kg/m² (10.0–100.0) | Calculated as `weight_kg / ((height_cm/100)**2)` from `height_cm` and `weight_kg` in `patient_profiles` (`main.py:379-380`). | 0.1627 | 1.1767 |
| `sbp` | mmHg (60–260) | Most recent systolic BP reading within 30 days from reading history (`main.py:3761`). | 0.1573 | 1.1704 |
| `told_high_bp` | Binary (1=Yes) | Set to 1 by applicability filter (only patients with hypertension condition evaluated). | 0.0978 | 1.1028 |
| `ever_smoked_100` | Binary (1=Yes, 0=No) | Mapped from `smoking_status` (`never` -> 0, `former`/`current` -> 1) in `patient_profiles` (`main.py:389`). | 0.0969 | 1.1017 |
| `sex_male` | Binary (1=Male, 0=Female) | Mapped from `sex_at_birth` in `patient_profiles` (`main.py:384`). | 0.0860 | 1.0898 |
| `dbp` | mmHg (30–150) | Most recent diastolic BP reading within 30 days from reading history (`main.py:3761`). | 0.0086 | 1.0086 |

> **Note on Missing Data (D8):** If **any** required feature is missing (e.g. no waist measurement or no blood pressure reading within the past 30 days), the risk agent returns `{"status": "not_enough_information", "missing": [...]}`. It **never** falls back to `diabetes_basic_nhanes`.

### 1.6 Performance Metrics & Confidence Intervals
Evaluated on the held-out temporal test set (2017–2023, $n=8,681$, prevalence 4.15%):

| Metric | Point Estimate | 95% Confidence Interval | Clinical Interpretation |
| :--- | :--- | :--- | :--- |
| **AUROC** | **0.7527** | [0.7293, 0.7748] | Exceeds D11 threshold ($\ge 0.75$). |
| **AUPRC** | **0.1008** | [0.0891, 0.1165] | Baseline prevalence is 4.15%. |
| **Sensitivity** | **85.28%** | - | Catches 307 of 360 undiagnosed cases. |
| **Specificity** | **52.23%** | - | Correctly identifies 4346 of 8321 non-cases. |
| **PPV (Precision)** | **7.17%** | - | ~1 in 14 flagged individuals has undiagnosed diabetes. |
| **NPV** | **98.80%** | - | 98.8% probability of no undiagnosed diabetes when unflagged. |
| **F1 Score** | **0.1323** | - | Harmonic mean of precision and recall. |
| **Operating Threshold** | **0.0276** | - | Locked at $\ge 80\%$ validation sensitivity policy. |

### 1.7 Calibration & Risk Bands
- **Brier Score:** 0.0389
- **Calibration-in-the-Large (CITL):** 0.0011
- **Calibration Slope:** **0.8482** (Passes D11 gate: within $[0.8, 1.2]$)
- **Calibration Intercept:** -0.4418
- **Risk Bands (D8):**
  - **Low Risk:** Probability $< 0.0276 (< 2.76\%)$
  - **Moderate Risk:** Probability between $0.0276$ and $0.0871$
  - **High Risk:** Probability $\ge 0.0871 (\ge 8.71\%)$

### 1.8 Subgroup Evaluation
Evaluated across sex, age brackets, race/ethnicity proxy groups, and survey cycles:

| Subgroup Variable | Subgroup Value | $N$ | Positives | Prevalence | AUROC | Sensitivity | Specificity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `sex_male` | Female | 4,689 | 189 | 0.04% | 0.7655 | 81.48% | 57.58% |
| `sex_male` | Male | 3,992 | 171 | 0.04% | 0.7377 | 89.47% | 45.93% |
| `age_band` | 18-39 | 3,107 | 47 | 0.02% | 0.8232 | 63.83% | 86.34% |
| `age_band` | 40-59 | 2,556 | 125 | 0.05% | 0.7021 | 76.00% | 52.57% |
| `age_band` | 60+ | 3,018 | 188 | 0.06% | 0.6752 | 96.81% | 15.05% |
| `race_eth` | Mexican American | 888 | 49 | 0.06% | 0.7642 | 79.59% | 62.10% |
| `race_eth` | Other Hispanic | 856 | 42 | 0.05% | 0.7691 | 83.33% | 59.95% |
| `race_eth` | Non-Hispanic White | 4,258 | 125 | 0.03% | 0.7953 | 93.60% | 45.08% |
| `race_eth` | Non-Hispanic Black | 1,388 | 88 | 0.06% | 0.7267 | 82.95% | 48.69% |
| `race_eth` | Other Race / Multi-Racial | 1,291 | 56 | 0.04% | 0.7864 | 76.79% | 68.10% |
| `cycle` | 2017-2018 | 4,010 | 197 | 0.05% | 0.7359 | 81.73% | 53.97% |
| `cycle` | 2021-2023 | 4,671 | 163 | 0.03% | 0.7780 | 89.57% | 50.75% |

- **Worst Subgroup Sensitivity:** `age_band=40-59` at **76.00%**, which passes the D11 gate ($\ge 60\%$).
- **Older Adults (60+):** Sensitivity is 96.81%, but specificity drops to **15.05%**. In older adults, age drives high baseline probabilities.

### 1.9 Card-Population Performance (`told_high_bp == 1`)
For the intended clinical audience (patients with documented hypertension):
- **Cohort Size ($N$):** 2,579 (176 positives, prevalence 6.82%)
- **AUROC:** **0.6640**
- **Sensitivity:** **93.18%**
- **Specificity:** **17.60%**
- **Clinical Reading:** Among hypertensive patients, discrimination drops from 0.7527 to 0.6640 because hypertension is already one of the strongest predictors. While sensitivity is very high (93.18%), specificity is low (17.60%), meaning the model flags a substantial fraction of hypertensive individuals.

### 1.10 Comparison with Reference Config on the Same Label
Comparing `diabetes_full_nhanes` against the unregularized reference model (`diabetes_ref_age_sex_bmi`) evaluated on the **identical undiagnosed diabetes target label**:

| Config | Features | Val AUROC | Test AUROC | Test Sensitivity | Test Specificity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`diabetes_full_nhanes` (Production)** | Age, Sex, BMI, Smoking, Told High BP, SBP, DBP, Waist | **0.7617** | **0.7527** | **85.28%** | **52.23%** |
| `diabetes_ref_age_sex_bmi` (Reference) | Age, Sex, BMI | 0.7540 | 0.7421 | 84.28% | 50.05% |
| **Difference** | Additional clinical features | **+0.0077** | **+0.0106** | **+1.00%** | **+2.18%** |

### 1.11 Decision Curve Analysis (DCA) Summary
From `docs/ml/DECISION_CURVE.md`:
- **General Test Population:** The model provides positive net clinical benefit over deterministic rules and "screen all" across threshold probabilities $p_t \in [0.01, 0.12]$.
- **Card Population (Hypertension):** At low threshold probabilities ($p_t \le 0.03$), the model provides no net benefit over simply screening all hypertensive patients (e.g. at $p_t = 0.03$, net benefit: model 0.0391 vs screen all 0.0394 vs Age $\ge 35$ rule 0.0400). The model adds net benefit only from $p_t \in [0.04, 0.13]$.
- **Clinical Policy Implication:** Because an HbA1c blood test is a low-cost, low-risk laboratory test, clinicians commonly operate at low screening thresholds ($\le 3\%$). At that threshold, testing every hypertensive adult achieves equivalent or superior net benefit. This strongly justifies **D15** (a deterministic, rule-based screening reminder) rather than an unconstrained patient-facing ML risk score.

### 1.12 External Validation Status
- **Saad, Day 6:** Pending.
- **BRFSS Limitation Note:** The BRFSS survey contains no laboratory biomarker data (no HbA1c, fasting glucose) and no physical examination cuff measurements. External validation on BRFSS cannot evaluate undiagnosed target labels, but will evaluate self-reported diagnosis awareness (`told_diabetes`) and demographic feature drift.

### 1.13 Limitations & Transportability
1. **US NHANES Training Origin:** The model is trained on United States survey data and has **not been clinically validated for Pakistani patients**.
2. **South Asian Phenotypic Differences:** South Asian populations develop type 2 diabetes at younger ages and significantly lower BMI thresholds compared to European and North American populations. The World Health Organization (WHO) recommends lower BMI action points for Asian adults ($\ge 23.0\text{ kg/m}^2$ for overweight, $\ge 27.5\text{ kg/m}^2$ for obesity).
3. **Home Blood Pressure vs Exam Blood Pressure:** The model was trained on calibrated clinical examination blood pressure readings (standardized mercury sphygmomanometer). The app collects patient home BP readings, which have higher measurement variance and may reflect white-coat or masked hypertension discrepancies.
4. **Self-Reported Inclusion Filter:** The target population excludes diagnosed diabetes based on self-report (`told_diabetes == 0`). Patients unaware of their diagnosis or with incomplete medical history may be misclassified.
5. **Unweighted Survey Training:** The model was trained without NHANES complex survey weights to optimize discrimination on individual cases rather than population-level prevalence estimation.

---

## Part 2: Retired & Non-Shipped Models

| Model Config | Primary Gates Failed | Ship Decision | Reference Document |
| :--- | :--- | :--- | :--- |
| **`diabetes_basic_nhanes`** | Failed Gate 5: FULL model beats BASIC by +0.0075 validation AUROC. | **NOT EXPORTED.** Missing waist size in production yields `not_enough_information` with NO fallback to basic. | [`docs/ml/experiments/diabetes_basic_nhanes.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/diabetes_basic_nhanes.md) |
| **`htn_basic_nhanes`** | Failed Gate 1 (val AUROC 0.7540 $< 0.75$), Failed Gate 3 (slope 0.8691 $\notin [0.8, 1.2]$), Card AUROC 0.5442. | **RETIRED (D13).** Poor discrimination on diabetic patients. | [`docs/ml/experiments/htn_basic_nhanes.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/htn_basic_nhanes.md) |
| **`htn_full_nhanes`** | Failed Gate 1 (val AUROC 0.7546 $< 0.75$), Failed Gate 3 (slope 0.8582 $\notin [0.8, 1.2]$), Flags 100% of adults 60+ (0% specificity). | **RETIRED (D13).** Near-chance discrimination in target population (0.5317). | [`docs/ml/experiments/htn_full_nhanes.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/htn_full_nhanes.md) |
| **`diabetes_ref_age_sex_bmi`** | Baseline reference configuration on the same undiagnosed diabetes label. | **REFERENCE ONLY.** Not intended for production deployment. | [`docs/ml/experiments/diabetes_ref_age_sex_bmi.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/diabetes_ref_age_sex_bmi.md) |
| **`htn_ref_age_sex_bmi`** | Baseline reference configuration on the same measured hypertension label. | **REFERENCE ONLY.** Not intended for production deployment. | [`docs/ml/experiments/htn_ref_age_sex_bmi.md`](file:///c:/Users/usmanbari/Desktop/Chronicare/docs/ml/experiments/htn_ref_age_sex_bmi.md) |

---

## Part 3: Summary of D11 Gate Evaluation

| Gate ID | Gate Description | Target Criteria | `diabetes_full_nhanes` Result | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 1** | Test Discrimination | Test AUROC $\ge 0.75$ | **0.7527** (Val: 0.7617) | **PASS** |
| **Gate 2** | Test Sensitivity | Test Sensitivity $\ge 75\%$ | **85.28%** | **PASS** |
| **Gate 3** | Test Calibration | Calibration Slope $\in [0.80, 1.20]$ | **0.8482** | **PASS** |
| **Gate 4** | Subgroup Equity | Worst Subgroup Sensitivity $\ge 60\%$ | **76.00%** (`age_band=40-59`) | **PASS** |
| **Gate 5** | Tier Parsimony | Full Tier beats Basic Tier | **+0.0075 AUROC** (0.7617 vs 0.7542) | **PASS** |

**Final Recommendation:** Ship `diabetes_full_nhanes` to production **strictly** as a provider-only experimental advisory module per D12.
