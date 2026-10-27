# DRAFT FOR USMAN: ChronicCare AI ML Feature Map

> **Notice:** This document maps candidate clinical and behavioral features across the active application codebase, NHANES 1999–2023, and BRFSS 2015–2023. Final feature inclusion for model training is decided by Usman (ML Lead) and the clinical team in `ML_PLAN.md`.

---

## 1. Feature Map Cross-Reference

| Feature | App Field Today (Exact Name + file:line) | How App Gets It | NHANES Column (`nhanes_core`) | BRFSS Column (`brfss_core`) | Units + Conversion | Missing % NHANES / BRFSS | Suggested for Basic Model? | Suggested for Full Model? | Leakage Risk (Label it would leak) |
|---|---|---|---|---|---|---|---|---|---|
| **Age** | `date_of_birth` (`main.py:368`, `app_store.py:270`) | Profile (derived: `current_year - birth_year`) | `age` | `age` | Years (integer $\ge 18$) | 0.0% / 0.0% | **Yes** | **Yes** | None |
| **Sex** | `sex_at_birth` (`main.py:370`, `app_store.py:274`) | Profile (`male`, `female`, `prefer_not_to_say`) | `sex_male` | `sex_male` | Binary (1=Male, 0=Female) | 0.0% / 0.0% | **Yes** | **Yes** | None |
| **Height** | `height_cm` (`main.py:373`, `app_store.py:279`) | Profile (UI supports ft/in $\to$ cm) | `height_cm` | Not collected | Centimeters ($cm = in \times 2.54$) | 8.4% / — | **Yes** (via BMI) | **Yes** | None |
| **Weight** | `weight_kg` (`main.py:374`, `app_store.py:281`) | Profile or Check-in (`main.py:483`) | `weight_kg` | Not collected | Kilograms ($kg = lb \times 0.453592$) | 8.5% / — | **Yes** (via BMI) | **Yes** | None |
| **Body Mass Index (BMI)** | Derived: `weight_kg / (height_cm/100)^2` | Profile (computed from height + weight) | `bmi` | `bmi` | $kg/m^2$ | 8.8% / 9.0% | **Yes** | **Yes** | None |
| **Waist Circumference** | *Not collected* | N/A | `waist_cm` | Not collected | Centimeters | 12.1% / — | No | Yes (if collected) | None |
| **Smoking Status** | `smoking_status` (`main.py:377`, `app_store.py:287`) | Profile (`never`, `former`, `current`) | `ever_smoked_100` | `smoker_status`, `ever_smoker` | Categorical / Binary (1=Ever smoked 100+ cigarettes) | 4.9% / 4.8% | No | **Yes** | None |
| **Family History of Diabetes** | *Not collected* | N/A | `family_hx_diabetes` | Not collected | Binary (1=Yes, 0=No) | 42.2% / — | No | Yes (if collected) | None |
| **Physical Activity** | *Not collected* | N/A | Not harmonized in core | `phys_active` | Binary (1=Yes, 0=No) | — / 4.4% | No | Yes (if collected) | None |
| **Diabetes Diagnosis Year** | `diagnosis_year_diabetes` (`main.py:375`, `app_store.py:283`) | Profile (duration = `current_year - diagnosis_year`) | `told_diabetes` (age at diag in full) | Not harmonized in core | Years duration | 2.1% / — | **FORBIDDEN** | **FORBIDDEN** | **Severe Leakage:** Leaks `diabetes_told`, `diabetes_told_or_measured` |
| **Hypertension Diagnosis Year** | `diagnosis_year_hypertension` (`main.py:376`, `app_store.py:285`) | Profile (duration = `current_year - diagnosis_year`) | `told_high_bp` | Not harmonized in core | Years duration | 0.5% / — | **FORBIDDEN** | **FORBIDDEN** | **Severe Leakage:** Leaks `hypertension_told`, `hypertension_stage1_or_clinical` |
| **Comorbidities** | `comorbidities` (`main.py:378`, keys: `kidney_disease`, `heart_disease`, `stroke_or_tia`, `eye_problems`, `nerve_or_foot_problems`) | Profile checklist | Available in full / questionnaire | `kidney_disease`, `heart_disease`, `stroke` | Binary indicators per comorbidity | Variable / 0.4%–0.9% | No | **Yes** | None |
| **Insulin / Sulfonylurea** | `on_insulin_or_sulfonylurea` (`main.py:366`, `app_store.py:127`) | Profile | `takes_insulin`, `takes_diabetes_pills` | Not in core | Binary (1=Yes, 0=No) | 12.8% / — | **FORBIDDEN** | **FORBIDDEN** | **Severe Leakage:** Leaks `diabetes_told`, `diabetes_told_or_measured` |
| **BP Medications** | Active meds in `app_store.py:45` & EHR bundle | Isolated record / Reconciled EHR | `takes_bp_meds` | `bp_meds` | Binary (1=On antihypertensive meds) | 71.1% / 59.9% | **FORBIDDEN** | **FORBIDDEN** | **Severe Leakage:** Leaks `hypertension_told`, `hypertension_on_meds`, `hypertension_stage1_or_clinical` |
| **Random Blood Glucose** | `glucose` (`main.py:483`, `/api/checkin`) | Daily Check-in / Patient Record | `fasting_glucose` | Not collected | $mg/dL$ ($mg/dL = mmol/L \times 18.0182$) | 56.6% / — | **FORBIDDEN** | **FORBIDDEN** | **Severe Leakage:** Leaks `diabetes_measured`, `diabetes_undiagnosed`, `prediabetes` |
| **Blood Pressure (SBP / DBP)** | `blood_pressure_systolic`, `blood_pressure_diastolic` (`main.py:483`) | Daily Check-in / Patient Record | `sbp`, `dbp` | Not collected | $mmHg$ | 10.9% / — | **FORBIDDEN** | **FORBIDDEN** | **Severe Leakage:** Leaks `hypertension_measured_130_80`, `hypertension_measured_140_90`, `hypertension_stage1_or_clinical` |
| **HbA1c** | `hba1c` (`main.py:483`) | Patient Record (isolated/EHR) | `hba1c` | Not collected | Percentage (%) | 11.8% / — | **FORBIDDEN** | **FORBIDDEN** | **Severe Leakage:** Leaks `diabetes_measured`, `diabetes_undiagnosed`, `prediabetes` |
| **Total Cholesterol** | *Not collected in check-in* | N/A (EHR lab only) | `total_chol` | `high_chol` (self-report) | $mg/dL$ | 13.2% / 11.1% | No | Yes (if lab available) | None |
| **Income / Education** | *Not collected* | N/A | `income_poverty_ratio` | `income_group`, `education` | Ratio / Categorical brackets | 10.6% / 19.0% | **REJECTED** | **REJECTED** | Non-clinical (equity / algorithmic bias risk) |

---

## 2. Why Socioeconomic Factors (Income & Education) Must NOT Be Used in Clinical Risk Models

1. **Algorithmic Bias and Care Inequity:** Socioeconomic variables like income and education level reflect systemic social inequities rather than biological pathophysiological risk. Conditioning medical risk prediction models on income risks institutionalizing bias—for instance, systematically assigning lower risk or lower care intensity to underserved individuals based on poverty metrics.
2. **Clinical Non-Actionability:** A clinician, diabetes educator, or software agent cannot prescribe an increase in income or education. Clinical interventions must target modifiable risk factors (diet, physical activity, blood pressure, glycemic control) and established biological drivers.
3. **Patient Stigma and Attrition:** Requiring income disclosure during chronic disease onboarding creates discomfort, raises privacy fears, and leads to high drop-off rates during enrollment without delivering clinical diagnostic value.

---

## 3. Features the App Would Need to Start Collecting (Proposed)

*Note: Proposed only for Usman and physician review; do NOT add to app code at this stage.*

### 1. Family History of Diabetes (`family_hx_diabetes`)
- **Clinical Rationale:** First-degree family history is a well-established non-invasive risk factor for Type 2 Diabetes (ADA risk assessment score).
- **Proposed English:** "Did any of your biological parents or siblings have diabetes?"
- **Proposed Urdu:** "کیا آپ کے والدین یا بہن بھائیوں میں سے کسی کو ذیابیطس (شوگر) کی بیماری تھی؟"

### 2. Waist Circumference (`waist_circumference`)
- **Clinical Rationale:** Central visceral adiposity is a superior predictor of metabolic syndrome and insulin resistance compared to BMI alone.
- **Proposed English:** "What is your waist circumference (measured at your belly button) in inches or centimeters?"
- **Proposed Urdu:** "آپ کی کمر کی پیمائش (ناف کے برابر) کتنے انچ یا سینٹی میٹر ہے؟"

### 3. Leisure-Time Physical Activity (`physical_activity`)
- **Clinical Rationale:** Corresponds to the standard BRFSS question assessing physical exercise outside of regular employment.
- **Proposed English:** "During the past 30 days, did you participate in any physical activities or exercises such as running, brisk walking, or gym workouts?"
- **Proposed Urdu:** "کیا آپ نے پچھلے 30 دنوں میں کسی قسم کی جسمانی ورزش یا سرگرمی (جیسے تیز چلنا، دوڑنا، یا جم کی ورزش) میں حصہ لیا؟"

### 4. Total Cholesterol Lab Value (`total_cholesterol`)
- **Clinical Rationale:** Required for formal ASCVD cardiovascular risk calculations alongside systolic BP and smoking status.
- **Proposed English:** "What was your total cholesterol level from your most recent laboratory blood test (mg/dL)?"
- **Proposed Urdu:** "آپ کے حالیہ خون کے ٹیسٹ میں ٹوٹل کولیسٹرول کی سطح کتنی تھی (mg/dL)؟"
