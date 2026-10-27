# ML Feature Map: ChronicCare-AI App vs. NHANES and BRFSS

This document establishes the bidirectional feature mapping between the ChronicCare-AI application data model, the NHANES epidemiological reference dataset (`nhanes_core.parquet`), and the BRFSS surveillance dataset (`brfss_core.parquet`).

---

## 1. Feature Map Cross-Reference

| Feature | App Field Today (Exact Name + file:line) | How App Gets It | NHANES Column (`nhanes_core`) | BRFSS Column (`brfss_core`) | Units + Conversion | Missing % NHANES / BRFSS | Diabetes Model: Allowed? (Basic / Full) | Hypertension Model: Allowed? (Basic / Full) | Forbidden for Labels (from `labels.py`) |
|---|---|---|---|---|---|---|---|---|---|
| **Age** | `date_of_birth` (`main.py:372`, `app_store.py:314`) | Profile (derived: `current_year - birth_year`) | `age` | `age` | Years (integer >= 18) | 0.0% / 0.0% | **Yes** (Basic & Full) | **Yes** (Basic & Full) | *None* |
| **Sex** | `sex_at_birth` (`main.py:374`, `app_store.py:373`) | Profile (`male`, `female`, `prefer_not_to_say`) | `sex_male` | `sex_male` | Binary (1=Male, 0=Female) | 0.0% / 0.0% | **Yes** (Basic & Full) | **Yes** (Basic & Full) | *None* |
| **Height** | `height_cm` (`main.py:377`, `app_store.py:386`) | Profile (UI supports ft/in -> cm) | `height_cm` | Not collected | Centimeters ($cm = in \times 2.54$) | 8.4% / - | **Yes** (via BMI in Basic; Full) | **Yes** (via BMI in Basic; Full) | *None* |
| **Weight** | `weight_kg` (`main.py:378`, `app_store.py:388`) or check-in (`main.py:681`) | Profile or Check-in (`weight`) | `weight_kg` | Not collected | Kilograms ($kg = lb \times 0.453592$) | 8.5% / - | **Yes** (via BMI in Basic; Full) | **Yes** (via BMI in Basic; Full) | *None* |
| **Body Mass Index (BMI)** | Derived: `weight_kg / (height_cm/100)^2` | Profile (computed from height + weight) | `bmi` | `bmi` | $kg/m^2$ | 8.8% / 9.0% | **Yes** (Basic & Full) | **Yes** (Basic & Full) | *None* |
| **Waist Circumference** | *Not collected* | N/A (Proposed) | `waist_cm` | Not collected | Centimeters | 12.1% / - | No / **Yes** (Full, if collected) | No / **Yes** (Full, if collected) | *None* |
| **Smoking Status** | `smoking_status` (`main.py:381`, `app_store.py:394`) | Profile (`never`, `former`, `current`) | `ever_smoked_100` | `smoker_status`, `ever_smoker` | Categorical / Binary (1=Ever smoked 100+ cigarettes) | 4.9% / 4.8% | No / **Yes** (Full) | No / **Yes** (Full) | *None* |
| **Family History of Diabetes** | *Not collected* | N/A (Proposed) | `family_hx_diabetes` | Not collected | Binary (1=Yes, 0=No) | 42.2% / - | No / **Yes** (Full, if collected) | No / **Yes** (Full, if collected) | *None* |
| **Physical Activity** | *Not collected* | N/A (Proposed) | Not harmonized in core | `phys_active` | Binary (1=Yes, 0=No) | - / 4.4% | No / **Yes** (Full, if collected) | No / **Yes** (Full, if collected) | *None* |
| **Diabetes Diagnosis Year** | `diagnosis_year_diabetes` (`main.py:379`, `app_store.py:390`) | Profile (duration = `current_year - diagnosis_year`) | `told_diabetes` (age at diag in full) | Not harmonized in core | Years duration | 2.1% / - | **FORBIDDEN** (Target leakage) | No / **Yes** (Full - CVD/HTN risk factor) | `diabetes_told`, `diabetes_told_or_measured` |
| **Hypertension Diagnosis Year** | `diagnosis_year_hypertension` (`main.py:380`, `app_store.py:392`) | Profile (duration = `current_year - diagnosis_year`) | `told_high_bp` | Not harmonized in core | Years duration | 0.5% / - | No / **Yes** (Full - metabolic risk factor) | **FORBIDDEN** (Target leakage) | `hypertension_told`, `hypertension_on_meds`, `hypertension_told_or_meds`, `hypertension_stage1_or_clinical` |
| **Comorbidities** | `comorbidities` (`main.py:382`, keys in `main.py:359-365`, `app_store.py:396`) | Profile checklist (`kidney_disease`, `heart_disease`, `stroke_or_tia`, `eye_problems`, `nerve_or_foot_problems`) | Available in questionnaire | `kidney_disease`, `heart_disease`, `stroke` | Binary indicators per comorbidity | Variable / 0.4%-0.9% | No / **Yes** (Full) | No / **Yes** (Full) | *None* |
| **Insulin / Sulfonylurea** | `on_insulin_or_sulfonylurea` (`main.py:370`, `app_store.py:151`) | Profile | `takes_insulin`, `takes_diabetes_pills` | Not in core | Binary (1=Yes, 0=No) | 12.8% / - | **FORBIDDEN** (Target leakage) | No / **Yes** (Full - metabolic severity indicator) | `diabetes_told`, `diabetes_told_or_measured`, `diabetes_undiagnosed` |
| **BP Medications** | Active meds in `app_store.py:45` & EHR bundle | Isolated record / Reconciled EHR | `takes_bp_meds` | `bp_meds` | Binary (1=On antihypertensive meds) | 71.1% / 59.9% | No / **Yes** (Full - ADA/Framingham diabetes risk feature) | **FORBIDDEN** (Target leakage) | `hypertension_told`, `hypertension_on_meds`, `hypertension_told_or_meds`, `hypertension_stage1_or_clinical` |
| **Random Blood Glucose** | `glucose` (`main.py:681`, `main.py:1545`) | Daily Check-in / Patient Record | `fasting_glucose` | Not collected | $mg/dL$ ($mg/dL = mmol/L \times 18.0182$) | 56.6% / - | **FORBIDDEN** (Target leakage) | No / **Yes** (Full - vascular risk factor) | `diabetes_measured`, `diabetes_told_or_measured`, `diabetes_undiagnosed`, `diabetes_prediabetes` |
| **Blood Pressure (SBP / DBP)** | `blood_pressure_systolic`, `blood_pressure_diastolic` (`main.py:681`, `main.py:1549-1558`) | Daily Check-in / Patient Record | `sbp`, `dbp` | Not collected | $mmHg$ | 10.9% / - | No / **Yes** (Full - core metabolic risk factor) | **FORBIDDEN** (Target leakage) | `hypertension_measured_130_80`, `hypertension_measured_140_90`, `hypertension_stage1_or_clinical` |
| **HbA1c** | `hba1c` (`main.py:681`, `main.py:1541`) | Patient Record (lab/EHR) | `hba1c` | Not collected | Percentage (%) | 11.8% / - | **FORBIDDEN** (Target leakage) | No / **Yes** (Full - glycemic cardiovascular predictor) | `diabetes_measured`, `diabetes_told_or_measured`, `diabetes_undiagnosed`, `diabetes_prediabetes` |
| **Total Cholesterol** | *Not collected in check-in* | N/A (EHR lab only) | `total_chol` | `high_chol` (self-report) | $mg/dL$ | 13.2% / 11.1% | No / **Yes** (Full, if lab available) | No / **Yes** (Full, if lab available) | *None* |
| **Income / Education** | *Not collected* | N/A | `income_poverty_ratio` | `income_group`, `education` | Ratio / Categorical brackets | 10.6% / 19.0% | **REJECTED** (Algorithmic bias risk) | **REJECTED** (Algorithmic bias risk) | *N/A (Algorithmic Equity Policy)* |

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
- **Proposed Urdu:** "کیا آپ کے والدین یا بہن بھائیوں میں سے کسی کو ذیابیطس (شوگر) کی بیماری ہے؟"

### 2. Waist Circumference (`waist_circumference`)
- **Clinical Rationale:** Central visceral adiposity is a superior predictor of metabolic syndrome and insulin resistance compared to BMI alone.
- **Proposed English:** "What is your waist circumference (measured at your belly button) in inches or centimeters?"
- **Proposed Urdu:** "آپ کی کمر کا ناپ (ناف کے مقام پر) انچ یا سینٹی میٹر میں کتنا ہے؟"

### 3. Leisure-Time Physical Activity (`physical_activity`)
- **Clinical Rationale:** Corresponds to the standard BRFSS question assessing physical exercise outside of regular employment.
- **Proposed English:** "During the past 30 days, did you participate in any physical activities or exercises such as running, brisk walking, or gym workouts?"
- **Proposed Urdu:** "کیا آپ نے پچھلے 30 دنوں میں کسی بھی قسم کی جسمانی ورزش یا سرگرمی (جیسے تیز چلنا، دوڑنا یا جم وغیرہ) میں حصہ لیا؟"

### 4. Total Cholesterol Lab Value (`total_cholesterol`)
- **Clinical Rationale:** Required for formal ASCVD cardiovascular risk calculations alongside systolic BP and smoking status.
- **Proposed English:** "What was your total cholesterol level from your most recent laboratory blood test (mg/dL)?"
- **Proposed Urdu:** "آپ کے حالیہ خون کے ٹیسٹ میں ٹوٹل کولیسٹرول کی سطح کتنی تھی (mg/dL)؟"
