# ChronicCare AI: Machine Learning Architecture & Decision Plan (ML_PLAN.md)

> **Document Status:** Decisions by Usman, 28 Oct 2026. Drafted by agent.  
> **Context:** ChronicCare AI Decision Support Prototype  
> **Core Principle:** The model proposes, the rules decide.

---

## Executive Summary & System Guardrails

ChronicCare AI operates under a strict principle:  
**"The model proposes, the rules decide."**

The machine learning models developed within this pipeline provide **condition risk stratification** and **screening decision support**. They do not diagnose conditions, do not prescribe medications or alter dosages, and cannot lower any clinical triage level established by deterministic clinical safety rules.

---

## Baseline Counts and Prevalence (from `scripts/ml/count_label_populations.py`)

The following statistics were computed directly by running `scripts/ml/count_label_populations.py` on the NHANES core dataset across temporal splits:
- `train_core`: 1999–2012 (7 survey cycles, 41,243 adults)
- `validation`: 2013–2016 (2 survey cycles, 12,105 adults)
- `test`: 2017–2023 (2 survey cycles, 14,009 adults)

```text
=== POPULATION COUNTS AND PREVALENCE ACROSS TEMPORAL SPLITS ===
| Target / Evaluation Group | Population | train_core (Pos / Total) | validation (Pos / Total) | test (Pos / Total) |
| --- | --- | --- | --- | --- |
| diabetes_undiagnosed (Option 2A) | Adults WITHOUT diagnosed diabetes (told_diabetes == 0) | 1,197 / 32,647 (3.7%) | 380 / 9,371 (4.1%) | 394 / 9,261 (4.3%) |
| diabetes_told_or_measured (Option 2B) | All adults | 5,629 / 41,189 (13.7%) | 2,023 / 12,081 (16.7%) | 2,447 / 13,935 (17.6%) |
| diabetes_told (Option 2C) | All adults | 4,250 / 40,580 (10.5%) | 1,571 / 11,790 (13.3%) | 1,951 / 13,554 (14.4%) |
| hypertension_measured_130_80 (Option 2D) | Adults NOT told high BP and NOT on BP meds | 7,139 / 25,380 (28.1%) | 1,861 / 7,299 (25.5%) | 2,244 / 7,268 (30.9%) |
| hypertension_stage1_or_clinical (Option 2E) | All adults | 20,125 / 41,184 (48.9%) | 6,106 / 12,104 (50.4%) | 7,341 / 13,999 (52.4%) |
| hypertension_told_or_meds (Option 2F) | All adults | 12,929 / 40,958 (31.6%) | 4,241 / 12,094 (35.1%) | 5,086 / 13,985 (36.4%) |
| hypertension_measured_130_80 (Option 2G) | All adults | 14,492 / 37,223 (38.9%) | 4,184 / 11,287 (37.1%) | 4,841 / 11,490 (42.1%) |
| Diabetes Card Eval Population | Non-diabetics with told_high_bp == 1 (Card audience) | 615 / 8,634 (7.1%) | 189 / 2,754 (6.9%) | 193 / 2,775 (7.0%) |
| Hypertension Card Eval Population | Diabetics not told high BP & not on meds (Card audience) | 533 / 1,223 (43.6%) | 172 / 453 (38.0%) | 197 / 488 (40.4%) |
```

---

## Decision D1: Who Sees Which Risk Card

### Clinical Context
ChronicCare AI patients are adults onboarded because they **already have diagnosed type 2 diabetes, essential hypertension, or both**. Displaying a diabetes incidence risk card to a patient who already carries an established diagnosis of type 2 diabetes confuses patients and provides no clinical utility.

### Options
1. **Option 1 (Condition-Reciprocal Risk Display):**
   - **Hypertension-only patient:** Evaluated and presented with the **Diabetes Risk Card** (screening for undetected diabetes).
   - **Diabetes-only patient:** Evaluated and presented with the **Hypertension Risk Card** (screening for undetected hypertension).
   - **Dual-diagnosed patient (Both T2D & HTN):** **No risk card displayed**. Their daily check-in interface focuses purely on symptom monitoring, red-flag screening, medication adherence, and trend reconciliation. Predicting disease incidence for both conditions is not in this project's scope.
2. **Option 2 (Universal Risk Display):**
   - Every patient sees both risk scores regardless of prior diagnoses.
3. **Option 3 (Disease Progression / Complication Risk Model):**
   - Predict microvascular or macrovascular complications instead of incidence. Cross-sectional NHANES/BRFSS datasets do not support this without longitudinal follow-up.

### Recommendation & Rationale
Option 1 (Condition-Reciprocal Display). Clinically coherent for an already-diagnosed onboarding population; eliminates redundant self-prediction and focuses attention on undetected comorbid conditions.

**USMAN DECISION:** Option 1 (reciprocal). Hypertension-only patients see diabetes risk, diabetes-only patients see hypertension risk, patients with both see no card. Disease progression models for dual-diagnosed patients are not in this project's scope.

---

## Decision D2: Disease Label Definition (Target Formulation)

### Clinical Context
Evaluating risk requires choosing between self-reported survey awareness, objective biochemical/clinical measurements, combined total burden, or targeted undiagnosed/screening formulations.

### Empirical Evidence & Arithmetic
- **Option 2A (`diabetes_undiagnosed`):** Positives = 1,197 / 32,647 (3.7%) in `train_core`, 380 / 9,371 (4.1%) in `validation`, 394 / 9,261 (4.3%) in `test`.
- **Option 2B (`diabetes_told_or_measured`):** Positives = 5,629 / 41,189 (13.7%) in `train_core`, 2,023 / 12,081 (16.7%) in `validation`, 2,447 / 13,935 (17.6%) in `test`.
- **Option 2C (`diabetes_told` - Self-Report Gap Arithmetic):**
  - In `train_core`: Total = 5,629, Told = 4,250. Gap = 5,629 - 4,250 = 1,379 (1,379 / 5,629 = 24.5% missed by self-report).
  - In `validation`: Total = 2,023, Told = 1,571. Gap = 2,023 - 1,571 = 452 (452 / 2,023 = 22.3% missed by self-report).
  - In `test`: Total = 2,447, Told = 1,951. Gap = 2,447 - 1,951 = 496 (496 / 2,447 = 20.3% missed by self-report).
  - Self-report consistently underestimates total diabetes burden by 20.3% to 24.5% across cycles because undiagnosed individuals with elevated lab values are classified as negative.
- **Option 2D (`hypertension_measured_130_80` undiagnosed):** Positives = 7,139 / 25,380 (28.1%) in `train_core`, 1,861 / 7,299 (25.5%) in `validation`, 2,244 / 7,268 (30.9%) in `test`.
- **Option 2E (`hypertension_stage1_or_clinical`):** Positives = 20,125 / 41,184 (48.9%) in `train_core`, 6,106 / 12,104 (50.4%) in `validation`, 7,341 / 13,999 (52.4%) in `test`.

### Blood Pressure Measurement Protocol Shift (Known Limitation)
As documented in `get_nhanes.py` lines 54–55 and 157–160:
- For `train_core` (1999–2012) and `validation` (2013–2016), blood pressure was measured using a manual auscultatory cuff (`BPX`).
- For `test` (2017–2018 and 2021–2023), NHANES transitioned to an automated oscillometric cuff (`BPXO`).
- This measurement protocol change across survey cycles is a known limitation of the hypertension label, contributing to the higher observed test prevalence (30.9% in test vs. 25.5% in validation).

### Recommendation & Rationale
Option 2A for Diabetes and Option 2D for Hypertension. The card answers "could you have the other condition without knowing it?", so the label is the undiagnosed version.

**USMAN DECISION:**
- **Diabetes Label:** Option 2A (`diabetes_undiagnosed`, formula `(hba1c >= 6.5) | (fasting_glucose >= 126.0)` among adults with `told_diabetes == 0`).
- **Hypertension Label:** Option 2D (Measured BP $\ge 130/80$, formula `(sbp >= 130.0) | (dbp >= 80.0)` among adults NOT told they have high BP and NOT on BP medications, `told_high_bp == 0 & takes_bp_meds != 1`).
- **Reason:** The card answers "could you have the other condition without knowing it?", so the label is the undiagnosed version.

---

## Decision D3: Training Population Cohort & Evaluation Card Populations

### Clinical Context
Models must be trained on an appropriate non-diagnosed cohort, but must also be evaluated specifically on the exact subpopulation that will see the card in the application.

### Cohorts Defined
1. **Training Population (Option 1):**
   - **Diabetes Model:** Adults without diagnosed diabetes (`told_diabetes == 0`). Evaluated rows: 32,647 (`train_core`), 9,371 (`validation`), 9,261 (`test`).
   - **Hypertension Model:** Adults not told high BP and not on BP meds (`told_high_bp == 0 & takes_bp_meds != 1`). Evaluated rows: 25,380 (`train_core`), 7,299 (`validation`), 7,268 (`test`).
2. **Card Population (for Evaluation):**
   These are the patients who actually see the card in the app:
   - **Diabetes Card Population:** Rows in the diabetes population with `told_high_bp == 1` (hypertensive adults screened for diabetes).
     - `train_core`: 615 / 8,634 (7.1% prevalence)
     - `validation`: 189 / 2,754 (6.9% prevalence)
     - `test`: 193 / 2,775 (7.0% prevalence)
   - **Hypertension Card Population:** Rows in the hypertension population with `told_diabetes == 1` (diabetic adults screened for hypertension).
     - `train_core`: 533 / 1,223 (43.6% prevalence)
     - `validation`: 172 / 453 (38.0% prevalence)
     - `test`: 197 / 488 (40.4% prevalence)
3. **Condition-Specific Training Subpopulation (Option 3):**
   - Training solely on cross-diagnosed adults would restrict training records to 8,634 for diabetes and only 1,223 for hypertension in `train_core`, which drastically reduces training sample size.

**USMAN DECISION:** Option 1 for TRAINING (adults without the diagnosed condition). Card populations (hypertensive adults for diabetes model; diabetic adults for hypertension model) used for EVALUATION.

---

## Decision D4: Feature Sets (BASIC and FULL)

### Feature Availability in NHANES Core
Computed via `scripts/ml/count_label_populations.py`:

```text
=== FEATURE AVAILABILITY AND NON-MISSING % PER SPLIT ===
| Feature | In nhanes_core | train_core Non-Missing % | validation Non-Missing % | test Non-Missing % |
| --- | --- | --- | --- | --- |
| age | Yes | 100.0% (41,243/41,243) | 100.0% (12,105/12,105) | 100.0% (14,009/14,009) |
| sex_male | Yes | 100.0% (41,243/41,243) | 100.0% (12,105/12,105) | 100.0% (14,009/14,009) |
| bmi | Yes | 92.8% (38,263/41,243) | 95.1% (11,509/12,105) | 83.3% (11,669/14,009) |
| ever_smoked_100 | Yes | 92.1% (37,970/41,243) | 99.9% (12,092/12,105) | 99.8% (13,977/14,009) |
| told_high_bp | Yes | 99.3% (40,958/41,243) | 99.9% (12,094/12,105) | 99.8% (13,985/14,009) |
| told_diabetes | Yes | 98.4% (40,580/41,243) | 97.4% (11,790/12,105) | 96.8% (13,554/14,009) |
| sbp | Yes | 90.3% (37,223/41,243) | 93.2% (11,287/12,105) | 82.0% (11,490/14,009) |
| dbp | Yes | 90.3% (37,223/41,243) | 93.2% (11,287/12,105) | 82.0% (11,490/14,009) |
| hba1c | Yes | 89.8% (37,018/41,243) | 92.0% (11,131/12,105) | 80.4% (11,263/14,009) |
| fasting_glucose | Yes | 43.8% (18,054/41,243) | 43.8% (5,298/12,105) | 41.9% (5,866/14,009) |
| waist_cm | Yes | 89.8% (37,024/41,243) | 90.5% (10,955/12,105) | 80.0% (11,203/14,009) |
| family_hx_diabetes | Yes | 53.8% (22,198/41,243) | 93.0% (11,261/12,105) | 39.2% (5,487/14,009) |
| phys_active | No | 0.0% (Missing from data) | 0.0% (Missing from data) | 0.0% (Missing from data) |
```

### Feature Inclusion and Exclusion Rules
Per decision rule: "Drop any feature that is missing from the data or > 40% missing in train_core":
- **`phys_active`:** Dropped (missing from `nhanes_core`).
- **`family_hx_diabetes`:** Dropped (46.2% missing in `train_core`, exceeding the 40% threshold).
- **`fasting_glucose`:** Dropped (56.2% missing in `train_core`). For the hypertension model, `hba1c` is used instead (only 10.2% missing in `train_core`).
- **Demographics & Equity:** Race/ethnicity, `income_poverty_ratio`, and education are **NOT** model features. They are reserved solely for post-hoc fairness and subgroup evaluation.

### Model Feature Sets
1. **BASIC Model (Profile fields only):**
   - Enables scoring for patients who have not yet logged daily check-in readings.
   - **Diabetes Model:** `age`, `sex_male`, `bmi`, `ever_smoked_100`, `told_high_bp`.
   - **Hypertension Model:** `age`, `sex_male`, `bmi`, `ever_smoked_100`, `told_diabetes`.
2. **FULL Model (Profile + Vitals/Labs + Physical Measures):**
   - **Diabetes Model:** BASIC + `sbp` + `dbp` + `waist_cm`.
   - **Hypertension Model:** BASIC + `hba1c` + `waist_cm`.

### App Data Collection Requirements ("App must collect")
To execute the FULL model in future releases, the ChronicCare AI profile or check-in must collect:
- **`waist_cm` (Waist Circumference in cm):** Not currently collected in the application profile.
*(Note: Age, sex, BMI, smoking status, condition flags, blood pressure, and HbA1c are already part of the existing app profile and check-in schema).*

**USMAN DECISION:** Option 1 (two tiers: BASIC profile-only, FULL with vital/lab + waist_cm). Features missing from data or > 40% missing in train_core dropped. Race/ethnicity, income, and education reserved for subgroup evaluation only.

---

## Decision D5: Handling Missing Inputs at Inference and Training

### Inference Policy
- **No silent imputation during live inference.**
- If FULL model features are missing, fall back to the BASIC model.
- If mandatory BASIC features (`age`, `sex`, or `bmi`) are missing, return `null` risk card with status `"not_enough_information"`.

### Training Policy (Complete Cases Only)
- Models are trained on complete cases without imputed values.

#### Complete Case Counts by Split:
1. **Diabetes Model (Evaluated Pop: `told_diabetes == 0` & lab valid):**
   - `train_core` (Total evaluable: 32,647):
     - BASIC complete: 29,084 (1,135 pos, 3.90%) | Dropped missing BASIC: 3,563 (10.9%)
     - FULL complete: 27,448 (1,043 pos, 3.80%) | Dropped missing FULL: 5,199 (15.9%)
   - `validation` (Total evaluable: 9,371):
     - BASIC complete: 9,264 (372 pos, 4.02%) | Dropped missing BASIC: 107 (1.1%)
     - FULL complete: 8,714 (336 pos, 3.86%) | Dropped missing FULL: 657 (7.0%)
   - `test` (Total evaluable: 9,261):
     - BASIC complete: 9,117 (388 pos, 4.26%) | Dropped missing BASIC: 144 (1.6%)
     - FULL complete: 8,681 (360 pos, 4.15%) | Dropped missing FULL: 580 (6.3%)

2. **Hypertension Model (Evaluated Pop: `told_high_bp == 0 & takes_bp_meds != 1` & BP valid):**
   - `train_core` (Total evaluable: 25,380):
     - BASIC complete: 22,061 (6,623 pos, 30.02%) | Dropped missing BASIC: 3,319 (13.1%)
     - FULL complete: 20,766 (6,186 pos, 29.79%) | Dropped missing FULL: 4,614 (18.2%)
   - `validation` (Total evaluable: 7,299):
     - BASIC complete: 7,126 (1,803 pos, 25.30%) | Dropped missing BASIC: 173 (2.4%)
     - FULL complete: 6,609 (1,642 pos, 24.84%) | Dropped missing FULL: 690 (9.5%)
   - `test` (Total evaluable: 7,268):
     - BASIC complete: 7,037 (2,158 pos, 30.67%) | Dropped missing BASIC: 231 (3.2%)
     - FULL complete: 6,537 (2,004 pos, 30.66%) | Dropped missing FULL: 731 (10.1%)

**USMAN DECISION:** Option 1. No imputation at inference. Training uses complete cases only; dropped counts per split documented above.

---

## Decision D6: Candidate Model Families to Benchmark

### Benchmark Slate
Restrict to scikit-learn standard models to avoid external dependency overhead:
1. `LogisticRegression` (standard L2 penalty)
2. `LogisticRegression(class_weight="balanced")`
3. `RandomForestClassifier`
4. `HistGradientBoostingClassifier`

External dependencies like LightGBM and EBM/interpret are excluded.

**USMAN DECISION:** Modified slate using scikit-learn only (LogisticRegression, LogisticRegression balanced, RandomForest, HistGradientBoosting). No LightGBM or EBM.

---

## Decision D7: Decision Threshold Selection Policy

### Selection Rule
1. On the temporal validation set (`validation` 2013–2016), determine the highest decision threshold that achieves **sensitivity $\ge 0.80$**.
2. Lock this threshold.
3. Apply this exact threshold unchanged to the temporal test set (`test` 2017–2023) and in production. The threshold is never altered on test data.

**USMAN DECISION:** Option 1. Highest threshold on validation with sensitivity $\ge 0.80$, locked for test evaluation and production.

---

## Decision D8: Risk Stratification Bands (Low, Moderate, High)

### Band Definitions
Because negative predictive value (NPV) exceeds 95% across virtually all thresholds at 4% baseline prevalence, the bands are defined using the validated operating points:
- **LOW:** Predicted probability $< \tau_{\text{opt}}$ (below the locked D7 threshold).  
  *Patient-facing text:* "Below the screening threshold; keep your usual check-ups."
- **MODERATE:** $\tau_{\text{opt}} \le \text{Predicted probability} < P_{90}$ (from the locked threshold up to the 90th percentile of validation set probabilities).
- **HIGH:** Predicted probability $\ge P_{90}$ (top 10% of validation set probabilities).

**USMAN DECISION:** Modified three-tier bands: LOW (< locked D7 threshold), MODERATE (locked threshold to 90th percentile validation), HIGH (top 10% validation scores). Patient text updated as specified.

---

## Decision D9: Triage Interaction Guardrail

### Triage Rules
- Machine learning scores can never lower a triage level.
- If deterministic clinical rules classify a patient as `routine`, and the ML risk band is `HIGH`, the triage level may be raised from `routine` $\rightarrow$ `review` for doctor review.
- This elevation behavior is controlled by two existing configuration flags:
  - `RISK_ENABLED`: default `off`
  - `RISK_CAN_RAISE`: default `off`
- Both flags must be set to `on` for risk scores to elevate routine check-ins to review.

**USMAN DECISION:** Option 1. Can only raise routine to review (doctor review). Controlled by existing configuration flags `RISK_ENABLED=off` and `RISK_CAN_RAISE=off` by default.

---

## Decision D10: Production Model Export and Runtime Format

### Export Format
- If Logistic Regression meets performance criteria (or if a tree model fails to beat Logistic Regression validation AUROC by at least $+0.02$ with acceptable calibration), export Logistic Regression coefficients, intercept, and scaler parameters to a pure Python class or JSON format.
- Pure Python execution requires standard library only (`math.exp`), with zero additional runtime dependencies and minimal memory overhead.

**USMAN DECISION:** Option 1. Export Logistic Regression parameters to pure Python unless a tree model beats LR validation AUROC by $\ge 0.02$ with acceptable calibration.

---

## Decision D11: Minimum Acceptance Gates for FYP-1

### Evaluation Gates
A model must satisfy all five gates on the held-out temporal test set (`test` 2017–2023):
1. **Test AUROC:** $\ge 0.75$ (report bootstrap 95% CI; CI is descriptive and not a gate).
2. **Test Sensitivity:** $\ge 0.75$ at the locked validation threshold (validation threshold selected at 0.80; report exact test sensitivity).
3. **Calibration Slope:** Between $0.8$ and $1.2$ on test data (report calibration intercept and Brier skill score relative to the prevalence-only null model).
4. **Subgroup Sensitivity:** No evaluated demographic or clinical subgroup with $\ge 50$ positive cases (sex, age band, race/ethnicity, card population) has sensitivity $< 0.60$.
5. **Model Selection:** The FULL model is shipped only if it beats the BASIC model on validation AUROC; otherwise ship BASIC.

If a model fails any gate, it is not shipped, remains disabled behind `RISK_ENABLED=off`, and the documentation states which gate was missed.

**USMAN DECISION:** Modified 5 gates (test AUROC $\ge 0.75$, test sensitivity $\ge 0.75$, calibration slope 0.8–1.2, subgroup sensitivity $\ge 0.60$, FULL beats BASIC).

---

## Summary Table of Final Decisions

| Decision | Topic | Final Usman Decision |
|---|---|---|
| **D1** | Target User & Reciprocal Display | Option 1: Reciprocal display (HTN sees T2D risk; T2D sees HTN risk; dual sees none). Progression models not in scope. |
| **D2 (T2D)** | Diabetes Target Label | Option 2A: `diabetes_undiagnosed` (`(hba1c >= 6.5) \| (fasting_glucose >= 126.0)` on non-diabetics). |
| **D2 (HTN)** | Hypertension Target Label | Option 2D: Measured BP $\ge 130/80$ on adults not told high BP and not on BP meds. |
| **D3** | Training & Card Populations | Option 1 for training (non-diagnosed adults). Card populations used for evaluation. |
| **D4** | Feature Sets | Option 1: Two tiers (BASIC profile-only; FULL with vitals/labs + waist_cm). Dropped: `phys_active`, `family_hx_diabetes`, `fasting_glucose`. App must collect: `waist_cm`. |
| **D5** | Missing Input Handling | Option 1: No imputation at inference. Training on complete cases only. |
| **D6** | Model Slate to Benchmark | Modified slate: scikit-learn only (`LogisticRegression`, `LogisticRegression` balanced, `RandomForest`, `HistGradientBoosting`). |
| **D7** | Decision Threshold Policy | Option 1: Highest threshold on validation with sensitivity $\ge 0.80$, locked for test. |
| **D8** | Risk Bands | Modified three-tier bands: LOW (< locked threshold), MODERATE (locked threshold to 90th percentile), HIGH (top 10%). |
| **D9** | Triage Interaction | Option 1: Can only raise routine $\rightarrow$ review (doctor review). Controlled by existing `RISK_ENABLED=off` and `RISK_CAN_RAISE=off`. |
| **D10** | Production Export Format | Option 1: Pure Python export if tree does not beat LR by $\ge 0.02$ validation AUROC. |
| **D11** | FYP-1 Acceptance Criteria | Modified 5 gates: Test AUROC $\ge 0.75$, Test Sens $\ge 0.75$, Calibration slope 0.8–1.2, Subgroup Sens $\ge 0.60$, FULL beats BASIC. |

---
