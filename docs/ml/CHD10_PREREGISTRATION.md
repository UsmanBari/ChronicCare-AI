# Pre-Registration: 10-Year Coronary Heart Disease (CHD) Risk Model (`chd10_framingham`)

**Pre-registration Date:** 8 November 2026  
**Author:** Muhammad Saad (ChronicCare-AI Lead ML Engineer)  
**Status:** Pre-registered BEFORE test set evaluation (hermetic lock)  
**Task / Objective:** Proposal Section 13.1 (Agent 5) and Section 23 & 27: A hypertension- and diabetes-side risk model trained on the Framingham Heart Study cohort, comparing Logistic Regression, Random Forest, and HistGradientBoosting with SHAP explanations and pre-registered validation gates.

---

## 1. Target Definition

- **Target Variable:** `TenYearCHD`
  - Binary indicator ($1 = \text{developed CHD within 10 years of examination}$, $0 = \text{no CHD event within 10 years}$).
  - In Framingham Heart Study data, this corresponds to coronary death, myocardial infarction, angina pectoris, or coronary insufficiency.

---

## 2. Feature Specification

The model is strictly restricted to **non-lab features** that the ChronicCare-AI mobile check-in application collects:

| Feature Name | App Source / Type | Unit / Encoding | Clinical Relevance |
| :--- | :--- | :--- | :--- |
| `age` | Patient Profile / Check-in | Years (integer/float) | Primary non-modifiable cardiovascular risk driver |
| `sex_male` | Patient Profile | Binary ($1 = \text{Male}$, $0 = \text{Female}$) | Established baseline cardiovascular risk disparity |
| `current_smoker` | Daily Check-in / Screening | Binary ($1 = \text{Current smoker}$, $0 = \text{Non-smoker}$) | Endothelial dysfunction and vascular disease accelerator |
| `bmi` | Profile / Self-report / Vitals | $\text{kg/m}^2$ | Metabolic syndrome and adiposity indicator |
| `sbp` | Vitals Check-in | $\text{mmHg}$ | Systolic blood pressure (arterial wall tension) |
| `dbp` | Vitals Check-in | $\text{mmHg}$ | Diastolic blood pressure |
| `bp_meds` | Medication Reconciliation | Binary ($1 = \text{On BP medication}$, $0 = \text{Not on BP medication}$) | Marker for established hypertension needing pharmacotherapy |
| `diabetes` | Profile / Screening | Binary ($1 = \text{Diagnosed diabetes}$, $0 = \text{No diabetes}$) | CHD risk equivalent in cardiovascular guidelines |
| `prevalent_hyp` | Clinical History / Vitals | Binary ($1 = \text{Prevalent hypertension}$, $0 = \text{No prevalent hypertension}$) | Chronic vascular strain indicator |

### Excluded Features and Rationale

The following Framingham features are excluded from training because **the app does not collect them**:
- `totChol`: Serum total cholesterol requires a venous blood lab test; app is designed for non-invasive remote monitoring.
- `glucose`: Casual/fasting serum lab glucose requires blood draw/glucometer not universally integrated at check-in.
- `heartRate`: Not universally measured across all remote BP cuffs or manual entries.
- `cigsPerDay`: App collects smoking status as binary; quantity is not reliably tracked on daily check-ins.
- `education`: Socioeconomic variable not collected by clinical check-in interface.

---

## 3. Cohort Eligibility and Missingness Handling

- **Cohort Source:** Framingham Heart Study examination data (`framingham.csv` under `$env:CHRONICCARE_DATA_DIR/framingham/framingham.csv`).
- **Applicability Range:** Ages **30–74** inclusive.
  - Runtime contract: If a patient's age is $< 30$ or $> 74$, the app runtime returns `"not_enough_information: outside model age range"` and does not evaluate the model.
  - In Framingham data, raw age spans 32 to 70 years; 0 cases fall outside 30–74.
- **Missingness Rule:** Complete-case analysis across the 9 non-lab features and target. Any row with a missing value (`NaN`) in any of the 9 features or `TenYearCHD` is dropped.
- **Cohort Flow / Counts:**
  - Raw records in file: **4,238**
  - Records with missing features:
    - Missing `bmi`: 19 rows
    - Missing `bp_meds`: 53 rows
    - (Other 7 features + target: 0 missing rows)
    - Total unique dropped rows: **72 rows**
  - Clean complete-case cohort: **4,166 rows**
  - Target distribution:
    - Positive (`TenYearCHD = 1`): **623** ($14.95\%$)
    - Negative (`TenYearCHD = 0`): **3,543** ($85.05\%$)

---

## 4. Dataset Partitioning Protocol

- **Split Method:** Stratified random split based on `TenYearCHD`, with fixed `random_state=42`.
  - **Train set:** $60\%$ ($2,499$ rows; $374$ positive, $2,125$ negative; prevalence $14.97\%$)
  - **Validation set:** $20\%$ ($833$ rows; $124$ positive, $709$ negative; prevalence $14.89\%$)
  - **Test set (held-out lock):** $20\%$ ($834$ rows; $125$ positive, $709$ negative; prevalence $14.99\%$)
- **Hermetic Boundary:**
  - 5-fold cross-validation is performed **strictly on the Train set** for hyperparameter tuning.
  - Validation set is used **strictly for candidate model selection**.
  - Held-out Test set is evaluated **exactly ONCE** after model selection and hyperparameter freeze. No re-tuning or candidate switching is permitted after viewing test set performance.

---

## 5. Candidate Models & Hyperparameter Spaces

All continuous features (`age`, `bmi`, `sbp`, `dbp`) are standardized via `StandardScaler` fitted on the training split only for linear models; binary features remain 0/1.

1. **Logistic Regression (Standard, L2 penalty):**
   - Grid over $C \in [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]$, solver `lbfgs`.
2. **Logistic Regression (Class-weighted balanced):**
   - Same $C$ grid with `class_weight='balanced'`.
3. **Random Forest Classifier (`RandomForestClassifier`):**
   - Grid over `n_estimators` $\in [100, 200]$, `max_depth` $\in [3, 5, 8, \text{None}]$, `min_samples_leaf` $\in [1, 5, 10]$, `random_state=42`.
4. **HistGradientBoosting Classifier (`HistGradientBoostingClassifier`):**
   - Grid over `learning_rate` $\in [0.01, 0.05, 0.1]$, `max_iter` $\in [100, 200]$, `max_depth` $\in [3, 5]$, `min_samples_leaf` $\in [10, 20]$, `random_state=42`.

---

## 6. Model Selection Rule

Following the project's interpretability and safety philosophy (Decisions D10 and D13):
- **Logistic Regression is the default and will be selected unless a non-linear tree model (`RandomForest` or `HistGradientBoosting`) exceeds the best Logistic Regression model by $\ge 0.02$ in Validation AUROC.**
- If a tree model beats Logistic Regression by $\ge 0.02$ validation AUROC: execution pauses after Part 1 to consult the team/user before export.
- If Logistic Regression is chosen: it is exported to production JSON using the hermetic sigmoid parameter contract.

---

## 7. Pre-Registered Risk Bands & Clinical Use

- **Risk Categories:**
  - **Low Risk:** Predicted 10-year probability $< 10\%$ ($< 0.10$)
  - **Moderate Risk:** Predicted 10-year probability $10\%$ to $< 20\%$ ($0.10 \le p < 0.20$)
  - **High Risk:** Predicted 10-year probability $\ge 20\%$ ($p \ge 0.20$)
- **Clinical Basis:** Established thresholds from the National Cholesterol Education Program Adult Treatment Panel III (NCEP ATP III) guidelines for 10-year coronary heart disease risk.
- **Audience & Clinical Display (Doctor Decisions, 8 Nov 2026):**
  - `"audience": "provider_and_patient_band"`
  - **Providers:** View full risk probability, risk band, and SHAP feature drivers.
  - **Patients:** View their risk band ONLY (Low / Moderate / High) accompanied by the educational disclaimer:
    - English: *"This is an estimate from a research model, not a diagnosis."*
    - Urdu: *"یہ ایک تحقیقی ماڈل سے لگایا گیا تخمینہ ہے، کوئی تشخیص نہیں۔"*
    - Roman Urdu: *"Yeh ek tehqeeqi model se lagaya gaya takhmeena hai, koi tashkhees nahi."*
  - **Safety Rule:** Risk band display never changes the triage level on its own (triage is rule-governed).

---

## 8. Pre-Registered Test Set Validation Gates

Before `chd10_framingham` can be exported or shipped, the selected model must satisfy all five pre-registered gates on the untouched test set ($N=834$):

| Gate | Criterion | Target Threshold | Clinical & Safety Rationale |
| :--- | :--- | :--- | :--- |
| **G1** | Discrimination (AUROC) | $\text{AUROC} \ge 0.68$ | Adequate discrimination for a purely non-invasive, non-lab remote monitoring screening tool. |
| **G2** | Calibration Slope | $\text{Slope} \in [0.80, 1.20]$ | Probabilities reflect actual event rates without severe over- or under-confidence. |
| **G3** | Sensitivity at $10\%$ Cut | $\text{Sensitivity} \ge 70.0\%$ | High sensitivity at the moderate risk cutoff is required to safely identify at-risk patients. |
| **G4** | Worst Subgroup Sensitivity | $\text{Sensitivity} \ge 60.0\%$ | Evaluated across sex (`male`, `female`) and age groups ($<50$, $50-59$, $60+$) for subgroups with $\ge 30$ positive cases. Protects against demographic disparities. |
| **G5** | Brier Score vs Prevalence | $\text{Brier} < \text{Brier}_{\text{prev}}$ | Model forecasts must carry greater informational value than naive prevalence baseline ($p \cdot (1-p) \approx 0.1274$). |

*If any gate fails, the model is marked **"NOT SHIPPED (gate X)"**; no post-hoc tuning or hyperparameter adjustments are permitted.*

---

## 9. Metrics Reporting Protocol

The evaluation script will compute and report:
1. **Discrimination:** AUROC and AUPRC with 95% bootstrap confidence intervals (1,000 resamples).
2. **Operating Point Performance:** Sensitivity, Specificity, Precision (PPV), Negative Predictive Value (NPV), and F1-score evaluated at:
   - Moderate risk cut ($p \ge 0.10$)
   - High risk cut ($p \ge 0.20$)
3. **Calibration Metrics:** Calibration slope, calibration intercept, Brier score, and Brier score for naive prevalence.
4. **Error Analysis:** $2 \times 2$ Confusion matrices at both $10\%$ and $20\%$ cutoffs.
5. **Explainability & Sanity Check:**
   - Global SHAP mean absolute values.
   - Local SHAP waterfall / force plots for 3 synthetic test cases.
   - Monotonic clinical sign audit: verifying positive risk associations for `age`, `sbp`, `current_smoker`, `diabetes`, and `bp_meds`.

---

## 10. References

1. National Cholesterol Education Program (NCEP) Expert Panel on Detection, Evaluation, and Treatment of High Blood Cholesterol in Adults (Adult Treatment Panel III). Third Report of the National Cholesterol Education Program (NCEP) Expert Panel on Detection, Evaluation, and Treatment of High Blood Cholesterol in Adults (Adult Treatment Panel III) final report. *Circulation*. 2002;106(25):3143-3421.
2. D'Agostino RB Sr, Vasan RS, Pencina MJ, et al. General cardiovascular risk profile for use in primary care: the Framingham Heart Study. *Circulation*. 2008;117(6):743-753.
3. Steyerberg EW, Vickers AJ, Cook NR, et al. Assessing the performance of prediction models: a framework for traditional and novel measures. *Epidemiology*. 2010;21(1):128-138.
