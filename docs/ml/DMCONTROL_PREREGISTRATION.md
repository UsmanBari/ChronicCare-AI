# Pre-Registration: Diabetes Glycaemic Control Model (`diabetes_control_nhanes`)

**Pre-registration Date:** 12 November 2026  
**Author:** Muhammad Saad (ChronicCare-AI Lead ML Engineer)  
**Status:** Pre-registered BEFORE model training and test-set evaluation (hermetic lock)  
**Task / Objective:** Proposal Section 13.1 (Agent 4 — Diabetes Risk Prediction Agent) and Week 4 Finish Sprint (PR F): Among adults with diagnosed diabetes, estimate the risk that diabetes is poorly controlled ($\text{HbA1c} \ge 8.0\%$). Compares Logistic Regression, Random Forest, and HistGradientBoosting under Decision D10 parsimony, with SHAP explainability and pre-registered validation gates.

---

## 1. Clinical Context & Target Definition

- **Target Label:** `diabetes_poor_control_80`
  - Binary indicator ($1 = \text{poor glycaemic control: } \text{HbA1c} \ge 8.0\% \text{ [64 mmol/mol]}$, $0 = \text{adequate glycaemic control: } \text{HbA1c} < 8.0\%$).
- **Clinical Evidence & Threshold Sources (cited by title only):**
  1. *American Diabetes Association (ADA) Standards of Care in Diabetes — Glycemic Goals and Hypoglycemia.*
  2. *National Committee for Quality Assurance (NCQA) Healthcare Effectiveness Data and Information Set (HEDIS) — Comprehensive Diabetes Care: Hemoglobin A1c (HbA1c) Poor Control (>8.0%).*
- **Target Population (App Applicability):** Adults aged $\ge 18$ with documented diagnosed diabetes (`conditions` contains `diabetes`). Patients without diabetes receive `None` from this agent (they are screened by `diabetes_full_nhanes` instead).

---

## 2. Feature Specification

The model is strictly restricted to **9 features** that the ChronicCare-AI mobile check-in application collects:

| Feature Name | App Source / Type | NHANES Source Column | Unit / Encoding | Clinical Relevance |
| :--- | :--- | :--- | :--- | :--- |
| `age` | Profile / Check-in | `age` (RIDAGEYR) | Years ($\ge 18$) | Demographic baseline for glycaemic control dynamics |
| `sex_male` | Profile | `sex_male` (RIAGENDR) | Binary ($1 = \text{Male}, 0 = \text{Female}$) | Sex-specific metabolic and adherence patterns |
| `bmi` | Profile / Vitals | `bmi` (BMXBMI) | $\text{kg/m}^2$ | Insulin resistance and metabolic demand marker |
| `waist_cm` | Profile (v13 schema) | `waist_cm` (BMXWAIST) | $\text{cm}$ | Central visceral adiposity indicator |
| `ever_smoked_100` | Profile / Screening | `ever_smoked_100` (SMQ020) | Binary ($1 = \text{Yes}, 0 = \text{No}$) | Vascular inflammation and insulin resistance accelerator |
| `sbp` | Vitals Check-in | `sbp` (BPXSY) | $\text{mmHg}$ | Systolic blood pressure (cardiovascular comorbidity marker) |
| `dbp` | Vitals Check-in | `dbp` (BPXDI) | $\text{mmHg}$ | Diastolic blood pressure |
| `on_insulin` | Active Meds List | `takes_insulin` (DIQ050) | Binary ($1 = \text{Yes}, 0 = \text{No}$) | Indicator of advanced beta-cell loss / therapeutic escalation |
| `on_diabetes_pills` | Active Meds List | `takes_diabetes_pills` (DIQ070) | Binary ($1 = \text{Yes}, 0 = \text{No}$) | Oral antihyperglycaemic pharmacotherapy indicator |

### Excluded Features and Explicit Rationale ("The app does not collect it")

1. **Years since diagnosis (`DID040`):** Excluded because the check-in app does not mandate exact historical diagnosis duration from patients.
2. **Income-to-poverty ratio (`INDFMPIR`):** Excluded because socioeconomic income data is not collected during clinical remote check-in.
3. **Dietary recall / Carbohydrate intake:** Excluded because full dietary macronutrient logs are not part of daily vitals check-in.
4. **Venous laboratory panels (Lipids, eGFR, Creatinine, Urine Albumin):** Excluded because the model operates as a remote non-lab check-in tool without requiring immediate blood draws.

---

## 3. Cohort Eligibility & Split Protocol

- **Dataset Source:** US NHANES Core Dataset (`nhanes_core.csv` under `$env:CHRONICCARE_DATA_DIR/nhanes/nhanes_core.csv`).
- **Inclusion Criteria:**
  1. Age $\ge 18$ years.
  2. Diagnosed diabetes: `told_diabetes == 1` (NHANES DIQ010: "told by a doctor you have diabetes").
  3. Non-pregnant participants.
  4. Valid laboratory measurement of Hemoglobin A1c (`hba1c` / LBXGH is not null).
- **Missingness Rule:** Complete-case analysis across the 9 features. Rows with missing values in any of the 9 features are dropped without synthetic imputation.
- **Temporal Splitting Protocol (`nhanes_temporal_v1`):**
  - **Train Core (1999–2012, Cycles 1–7):** Model fitting and 5-fold cross-validation for hyperparameter tuning.
  - **Validation (2013–2016, Cycles 8–9):** Model architecture selection, calibration verification, and threshold locking.
  - **Held-Out Test (2017–2023, Cycles 10–11):** Evaluated strictly **ONCE** after locking architecture, hyperparameters, and thresholds.

---

## 4. Candidate Models & Hyperparameter Tuning

All continuous features (`age`, `bmi`, `waist_cm`, `sbp`, `dbp`) are scaled using `StandardScaler` fitted strictly on `train_core`. Binary features ($0/1$) remain unscaled.

1. **Logistic Regression (`lr`, L2 penalty):**
   - Grid over $C \in [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]$, solver `lbfgs`.
2. **Logistic Regression Balanced (`lr_balanced`):**
   - Same $C$ grid with `class_weight='balanced'`.
3. **Random Forest Classifier (`rf`):**
   - Grid over `n_estimators` $\in [100, 200]$, `max_depth` $\in [3, 5, 8]$, `min_samples_leaf` $\in [5, 10, 20]$, `random_state=42`.
4. **HistGradientBoosting Classifier (`hgb`):**
   - Grid over `learning_rate` $\in [0.01, 0.05, 0.1]$, `max_iter` $\in [100, 200]$, `max_depth` $\in [3, 5]$, `min_samples_leaf` $\in [10, 20]$, `random_state=42`.

---

## 5. Model Selection Decision Rule (Decision D10)

Following ChronicCare-AI's established parsimony and safety standard:
- **Logistic Regression is the primary candidate.**
- A non-linear tree model (`rf` or `hgb`) will be chosen **only if** it beats the best Logistic Regression model by $\ge 0.02$ in Validation AUROC:
  $$\Delta \text{AUROC}_{\text{val}} = \text{AUROC}_{\text{tree}} - \text{AUROC}_{\text{lr}} \ge 0.02$$
- If a tree model beats LR by $\ge 0.02$, export pauses as BLOCKED per project rules to consult before tree export.
- If Logistic Regression is chosen: it is exported to production JSON using the pure-Python sigmoid inference contract.

---

## 6. Operational Thresholds & Risk Stratification Bands (Decision D7 & D8)

Thresholds are established **strictly on the validation set**:
1. **Low / Moderate Operational Threshold ($t_{\text{locked}}$):**
   - Minimum Sensitivity Policy ($\ge 80\%$ validation sensitivity).
   - The highest threshold on the validation set achieving $\text{Sensitivity} \ge 80.0\%$.
2. **High Risk Threshold ($t_{\text{high}}$):**
   - Top 20% of validation risk scores (80th percentile of predicted probabilities on validation set).
3. **Risk Stratification Bands:**
   - **Low Risk:** Probability $< t_{\text{locked}}$
   - **Moderate Risk:** Probability between $t_{\text{locked}}$ and $t_{\text{high}}$
   - **High Risk:** Probability $\ge t_{\text{high}}$
4. **Clinical Display & Audience Contract:**
   - `"audience": "provider_and_patient_band"`
   - **Providers:** View full numerical probability, risk band, odds ratios, and SHAP feature attributions.
   - **Patients:** View their categorical band ONLY (`Low`, `Moderate`, `High`) with an educational disclaimer, avoiding numerical panic:
     - English: *"This is an estimate from a research model, not a diagnosis."*
     - Urdu: *"یہ ایک تحقیقی ماڈل سے لگایا گیا تخمینہ ہے، کوئی تشخیص نہیں۔"*
     - Roman Urdu: *"Yeh ek tehqeeqi model se lagaya gaya takhmeena hai, koi tashkhees nahi."*
   - **Safety Invariant:** The model may only raise triage (`routine -> review`), never lower a triage level, and never alter medication doses.

---

## 7. Pre-Registered Test Set Acceptance Gates (G1–G5)

Before `diabetes_control_nhanes` can be shipped, it must pass all five gates evaluated on the held-out test cohort (2017–2023):

| Gate ID | Criterion | Target Threshold | Clinical & Safety Rationale |
| :--- | :--- | :--- | :--- |
| **Gate 1** | Discrimination | $\text{Test AUROC} \ge 0.65$ | Adequate discrimination for predicting poor control using non-lab check-in inputs. |
| **Gate 2** | Calibration Slope | $\text{Slope} \in [0.80, 1.20]$ | Reliable risk estimation without systematic over- or under-confidence. |
| **Gate 3** | Operational Sensitivity | $\text{Test Sensitivity at } t_{\text{locked}} \ge 70.0\%$ | High sensitivity to ensure patients with elevated HbA1c are identified for review. |
| **Gate 4** | Subgroup Equity | $\text{Worst Subgroup Sensitivity} \ge 60.0\%$ | Evaluated across sex (`male`, `female`) and age brackets ($<50$, $50–64$, $65+$) for groups with $\ge 30$ positives. |
| **Gate 5** | Information Value | $\text{Brier} < \text{Brier}_{\text{prev}}$ | Model forecasts must carry greater predictive value than naive prevalence baseline ($p(1-p)$). |

*If any gate fails, the model is marked **"NOT SHIPPED (Gate X)"** and cannot be deployed to production.*

---

## 8. App Population Post-Hoc Reporting

Because the training population consists of adults with diagnosed diabetes, the App Population is identical to the target cohort.
To provide additional transparency for clinicians, the post-hoc evaluation will also report:
- Overall App Population metrics ($n$, positives, prevalence, AUROC with 95% bootstrap CI, sensitivity, specificity, PPV at the locked threshold and high-risk threshold).
- Breakdown by insulin status:
  - Patients taking insulin (`on_insulin == 1`)
  - Patients not taking insulin (`on_insulin == 0`)

---

## 9. Explainability & Sanity Verification

1. **Odds Ratios & Direction Sanity:** Compute standardized odds ratios per 1 SD. Inspect direction consistency:
   - `on_insulin`: Expected positive ($\beta > 0$, higher risk of poor control due to advanced disease).
   - `bmi` / `waist_cm`: Expected positive ($\beta > 0$, adiposity-driven insulin resistance).
   - `age`: Frequently negative in NHANES ($\beta < 0$, younger adults often have higher HbA1c than older adults with stable routines). Report empirical directions without forcing.
2. **SHAP Attributions:** Compute linear SHAP values for global ranking and evaluate 3 synthetic patient cases (Low, Moderate, High risk profiles).

---

## 10. Correction (12 Nov 2026, before any test-set number)

As defined in the authoritative splitting code (`backend-poc-technical/ml/splits.py`, `nhanes_temporal_v1`), the exact cycle partition across time is:
- **`TRAIN_CORE_CYCLES` (7 cycles):** `1999-2000`, `2001-2002`, `2003-2004`, `2005-2006`, `2007-2008`, `2009-2010`, `2011-2012` (1999–2012).
- **`VALIDATION_CYCLES` (2 cycles):** `2013-2014`, `2015-2016` (2013–2016).
- **`TEST_CYCLES` (2 cycles):** `2017-2018`, `2021-2023` (2017–2023). Note that the COVID-interrupted `2019-2020` cycle is NOT used in NHANES data processing or splits.

Nothing else in this pre-registration changed: all features, candidate models, Decision D10 parsimony rules, validation threshold policies, D8 risk bands, and G1–G5 acceptance gates remain exactly as locked.

