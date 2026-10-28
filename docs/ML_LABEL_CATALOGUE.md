# DRAFT FOR USMAN: ChronicCare AI ML Label Catalogue

> **Notice:** This catalogue documents candidate clinical label definitions for Diabetes and Hypertension across NHANES temporal splits (`nhanes_temporal_v1`). Each entry outlines exact column formulas, real dataset prevalence rates per temporal split, strict forbidden feature lists to prevent data leakage, and analytical trade-offs. Usman (ML Lead) will choose the primary labels in `ML_PLAN.md`.

---

## 1. Summary of Label Definitions and Prevalence Across Temporal Splits

| Label Name | Disease | BRFSS Equivalent | `train_core` (1999–2012) | `validation` (2013–2016) | `test` (2017–2023) |
|---|---|---|---|---|---|
| **`diabetes_told`** | Diabetes | `diabetes` | 4,250 / 40,580 (10.5%) | 1,571 / 11,790 (13.3%) | 1,951 / 13,554 (14.4%) |
| **`diabetes_measured`** | Diabetes | *None (Lab only)* | 4,082 / 37,057 (11.0%) | 1,510 / 11,134 (13.6%) | 1,696 / 11,268 (15.1%) |
| **`diabetes_told_or_measured`** | Diabetes | *None (Lab only)* | 5,629 / 41,189 (13.7%) | 2,023 / 12,081 (16.7%) | 2,447 / 13,935 (17.6%) |
| **`diabetes_undiagnosed`** | Diabetes | *None (Lab only)* | 1,197 / 32,647 (3.7%) | 380 / 9,371 (4.1%) | 394 / 9,261 (4.3%) |
| **`diabetes_prediabetes`** | Diabetes | `prediabetes` | 10,115 / 37,366 (27.1%) | 3,626 / 11,177 (32.4%) | 4,038 / 11,528 (35.0%) |
| **`hypertension_told`** | Hypertension | `high_bp` | 12,929 / 40,958 (31.6%) | 4,241 / 12,094 (35.1%) | 5,086 / 13,985 (36.4%) |
| **`hypertension_on_meds`** | Hypertension | `bp_meds` | 9,626 / 10,892 (88.4%) | 3,150 / 3,657 (86.1%) | 4,086 / 4,893 (83.5%) |
| **`hypertension_told_or_meds`** | Hypertension | `high_bp` | 12,929 / 40,958 (31.6%) | 4,241 / 12,094 (35.1%) | 5,086 / 13,985 (36.4%) |
| **`hypertension_measured_130_80`** | Hypertension | *None (Lab only)* | 14,492 / 37,223 (38.9%) | 4,184 / 11,287 (37.1%) | 4,841 / 11,490 (42.1%) |
| **`hypertension_measured_140_90`** | Hypertension | *None (Lab only)* | 7,297 / 37,223 (19.6%) | 2,003 / 11,287 (17.7%) | 2,367 / 11,490 (20.6%) |
| **`hypertension_stage1_or_clinical`** | Hypertension | *None (Lab only)* | 20,125 / 41,184 (48.9%) | 6,106 / 12,104 (50.4%) | 7,341 / 13,999 (52.4%) |

---

## 2. Diabetes Label Catalog Details

### D1. `diabetes_told` (Self-Reported Diagnosis)
- **Formula (`nhanes_core`):** `told_diabetes == 1` (positive), `told_diabetes == 0` (negative), else `NaN`.
- **BRFSS Equivalent:** `diabetes` (`DIABETE3` / `DIABETE4`).
- **Forbidden Features:** `told_diabetes`, `takes_insulin`, `takes_diabetes_pills`, `diagnosis_year_diabetes`.
- **Trade-off Notes:**
  1. Easiest to train on and directly harmonizable with large state-level survey data like BRFSS.
  2. Inherits diagnosis access bias: fails to identify people with active hyperglycemia who lack healthcare access.
  3. Underestimates true disease burden by ~25% because undiagnosed individuals are labeled as negative controls.

### D2. `diabetes_measured` (Biochemically Confirmed)
- **Formula (`nhanes_core`):** `(hba1c >= 6.5) | (fasting_glucose >= 126.0)`. Requires at least one lab measurement.
- **BRFSS Equivalent:** *None* (BRFSS does not collect biological samples).
- **Forbidden Features:** `hba1c`, `fasting_glucose`, `glucose`.
- **Trade-off Notes:**
  1. Represents the objective biological gold standard according to ADA diagnostic criteria.
  2. Cannot be evaluated on BRFSS, limiting external validation to laboratory cohorts.
  3. Fasting glucose is available for only ~43% of adult participants, meaning HbA1c carries most of the sample weight.

### D3. `diabetes_told_or_measured` (Total Diabetes Burden)
- **Formula (`nhanes_core`):** `(told_diabetes == 1) | (hba1c >= 6.5) | (fasting_glucose >= 126.0)`.
- **BRFSS Equivalent:** *None*.
- **Forbidden Features:** `told_diabetes`, `takes_insulin`, `takes_diabetes_pills`, `diagnosis_year_diabetes`, `hba1c`, `fasting_glucose`, `glucose`.
- **Trade-off Notes:**
  1. Provides the most complete epidemiological estimate of total diabetes prevalence in the population.
  2. Resolves false negatives in self-report by catching undiagnosed individuals.
  3. Requires strict leakage exclusion across both clinical history and lab features during training.

### D4. `diabetes_undiagnosed` (Screening Target)
- **Formula (`nhanes_core`):** Evaluated strictly among adults who report never having been told they have diabetes (`told_diabetes == 0`): positive if `(hba1c >= 6.5) | (fasting_glucose >= 126.0)`, negative if neither elevated. Known diabetics (`told_diabetes == 1`) are excluded (`NaN`).
- **BRFSS Equivalent:** *None*.
- **Forbidden Features:** `told_diabetes`, `hba1c`, `fasting_glucose`, `glucose`, `takes_insulin`, `takes_diabetes_pills`.
- **Trade-off Notes:**
  1. Represents the highest-value clinical screening application: finding patients who need immediate clinical referral.
  2. Lower positive prevalence (~3.7%–4.3%) demands careful precision-recall thresholding and cost-sensitive loss weighting.
  3. Prevents model shortcutting: the model cannot rely on patient awareness signals to predict risk.

### D5. `diabetes_prediabetes` (Early Prevention Target)
- **Formula (`nhanes_core`):** `((hba1c >= 5.7 & hba1c <= 6.4) | (fasting_glucose >= 100.0 & fasting_glucose <= 125.0)) & (told_diabetes == 0) & (measured_diabetes == 0)`.
- **BRFSS Equivalent:** `prediabetes` (`PREDIAB1` / `PREDIAB2`).
- **Forbidden Features:** `hba1c`, `fasting_glucose`, `glucose`, `told_diabetes`, `borderline_diabetes`.
- **Trade-off Notes:**
  1. Enables early lifestyle intervention before irreversible pancreatic beta-cell loss occurs.
  2. Very high prevalence (~27%–35%), providing large positive sample sizes for deep feature representation.
  3. Broad biochemical boundary means non-diabetic controls and prediabetic cases have high baseline overlap on standard features.

---

## 3. Hypertension Label Catalog Details

### H1. `hypertension_told` (Self-Reported Diagnosis)
- **Formula (`nhanes_core`):** `told_high_bp == 1` (positive), `told_high_bp == 0` (negative), else `NaN`.
- **BRFSS Equivalent:** `high_bp` (`_RFHYPE5` / `_RFHYPE6`).
- **Forbidden Features:** `told_high_bp`, `takes_bp_meds`, `diagnosis_year_hypertension`.
- **Trade-off Notes:**
  1. Standard question across all US national surveillance surveys with minimal missingness (<0.5%).
  2. Misses asymptomatic stage 1 and stage 2 hypertensive individuals who have not seen a physician.
  3. Susceptible to patient recall inaccuracy and misunderstanding of white-coat episodes.

### H2. `hypertension_on_meds` (Pharmacologically Treated)
- **Formula (`nhanes_core`):** `takes_bp_meds == 1` (positive), `takes_bp_meds == 0` (negative).
- **BRFSS Equivalent:** `bp_meds` (`BPMEDS`).
- **Forbidden Features:** `takes_bp_meds`, `told_high_bp`, `medications`, `diagnosis_year_hypertension`.
- **Trade-off Notes:**
  1. Unambiguous confirmation of diagnosed, actively treated chronic hypertension.
  2. Question is conditional in NHANES/BRFSS: asked primarily of individuals who previously reported high BP.
  3. Excludes untreated patients and lifestyle-managed hypertensive patients.

### H3. `hypertension_told_or_meds` (Clinical History)
- **Formula (`nhanes_core`):** `(told_high_bp == 1) | (takes_bp_meds == 1)`.
- **BRFSS Equivalent:** `high_bp`.
- **Forbidden Features:** `told_high_bp`, `takes_bp_meds`, `diagnosis_year_hypertension`, `medications`.
- **Trade-off Notes:**
  1. Effectively identical to `told_high_bp` in survey skip patterns (virtually all on meds were told).
  2. Robust indicator for patients with an established clinical record of hypertension.
  3. Cannot capture currently uncontrolled or unmonitored blood pressure surges.

### H4. `hypertension_measured_130_80` (AHA/ACC Stage 1+)
- **Formula (`nhanes_core`):** `(sbp >= 130.0) | (dbp >= 80.0)`. Requires non-null examination blood pressure.
- **BRFSS Equivalent:** *None*.
- **Forbidden Features:** `sbp`, `dbp`, `blood_pressure_systolic`, `blood_pressure_diastolic`.
- **Trade-off Notes:**
  1. Aligned with 2017 AHA/ACC guidelines, catching early cardiovascular disease elevation.
  2. High prevalence (38%–42% of US adult population), capturing wide clinical risk.
  3. Single-exam measurement protocol in NHANES may include acute white-coat or stress reactions.

### H5. `hypertension_measured_140_90` (Classic Stage 2 / JNC7)
- **Formula (`nhanes_core`):** `(sbp >= 140.0) | (dbp >= 90.0)`. Requires non-null examination blood pressure.
- **BRFSS Equivalent:** *None*.
- **Forbidden Features:** `sbp`, `dbp`, `blood_pressure_systolic`, `blood_pressure_diastolic`.
- **Trade-off Notes:**
  1. Highly specific for moderate-to-severe cardiovascular risk requiring immediate pharmacotherapy.
  2. More conservative cutoff (~20% prevalence), reducing false-positive treatment burden.
  3. Ignores stage 1 pre-hypertensive elevation that guidelines recommend managing early.

### H6. `hypertension_stage1_or_clinical` (Comprehensive Hypertension)
- **Formula (`nhanes_core`):** `(told_high_bp == 1) | (takes_bp_meds == 1) | (sbp >= 130.0) | (dbp >= 80.0)`.
- **BRFSS Equivalent:** *None*.
- **Forbidden Features:** `told_high_bp`, `takes_bp_meds`, `sbp`, `dbp`, `blood_pressure_systolic`, `blood_pressure_diastolic`, `medications`, `diagnosis_year_hypertension`.
- **Trade-off Notes:**
  1. Captures total clinical hypertension burden: past diagnoses, treated patients, and undiagnosed elevated cuffs.
  2. Affects ~50% of the entire adult population, creating a balanced 50/50 binary classification target.
  3. Requires extensive feature exclusions (all BP readings, history, and medication records).
