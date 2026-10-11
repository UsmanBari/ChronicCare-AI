# Candidate Public Datasets

This document reviews public datasets that may be useful for ChronicCare AI development, testing, synthetic test-data design, and plausibility checking.

No dataset files are stored in this repository.

## 1. NHANES — National Health and Nutrition Examination Survey

**Source:** CDC / National Center for Health Statistics  
**Link:** https://wwwn.cdc.gov/Nchs/Nhanes/continuousnhanes/default.aspx?Cycle=2021-2023

**Licence / access:** Generally public domain for data and materials produced by U.S. federal agencies. Some NHANES materials may originate from other publications and should be cited appropriately.

**Size:** Large national survey released in cycles and split across multiple demographic, examination, laboratory, dietary, and questionnaire datasets rather than one single table.

**Potential ChronicCare AI use:**
- Check realistic distributions and ranges for health measurements.
- Study variables related to diabetes, hypertension, weight, age, laboratory measurements, and demographics.
- Help design realistic non-production test cases.
- Support research into plausible combinations of chronic-disease risk factors.

**Must NOT be used for:**
- Making patient-specific diagnoses.
- Treating population distributions as clinical safety thresholds.
- Assuming every NHANES participant represents the ChronicCare AI target population.
- Re-identification or attempts to combine data to identify participants.
- Replacing clinical guidelines or clinician-reviewed rules.

---

## 2. Synthea Synthetic Patient Data

**Source:** Synthea / MITRE  
**Link:** https://github.com/synthetichealth/synthea

**Licence:** Apache License 2.0.

**Size:** Configurable. Synthea generates a requested synthetic population size rather than providing one fixed-size dataset. Patient records can be generated in formats including FHIR.

**Potential ChronicCare AI use:**
- Generate synthetic patient records for development and testing.
- Test FHIR/EHR integration without using real patient records.
- Create repeatable test scenarios.
- Exercise medication, condition, observation, and patient-record workflows.
- Test larger synthetic patient populations.

**Must NOT be used for:**
- Assuming synthetic records reproduce the true prevalence of diseases or events.
- Deriving clinical safety thresholds without clinical evidence.
- Claiming model performance on Synthea is equivalent to performance on real patients.
- Treating synthetic outcomes as evidence of clinical effectiveness.

---

## 3. Diabetes 130-US Hospitals for Years 1999–2008

**Source:** UCI Machine Learning Repository  
**Link:** https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008

**Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).

**Size:** 101,766 instances and 47 features.

**Description:** Contains hospital encounter records for patients diagnosed with diabetes from 130 US hospitals and integrated delivery networks during 1999–2008.

**Potential ChronicCare AI use:**
- Explore diabetes-related variables and hospital-record structures.
- Create representative test scenarios based on the kinds of variables present in clinical data.
- Test data-processing pipelines with a relatively large diabetes-focused dataset.
- Study missing values and categorical clinical information.

**Must NOT be used for:**
- Assuming data from 1999–2008 represents current clinical practice.
- Using historical patterns as current treatment recommendations.
- Directly transferring hospital-population statistics to ChronicCare AI users.
- Making patient-specific treatment or diagnosis decisions.
- Treating demographic associations as causal relationships.

---

## 4. Early Stage Diabetes Risk Prediction

**Source:** UCI Machine Learning Repository  
**Link:** https://archive.ics.uci.edu/dataset/529/early+stage+diabetes+risk+prediction

**Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).

**Size:** 520 instances and 16 features.

**Description:** Contains signs and symptoms collected through questionnaires from patients at Sylhet Diabetes Hospital in Bangladesh.

**Potential ChronicCare AI use:**
- Inspect examples of symptom-oriented diabetes questionnaire data.
- Develop small test cases for questionnaire-processing logic.
- Test categorical data handling.
- Compare possible symptom/question representations with the application's test-data requirements.

**Must NOT be used for:**
- Automatically diagnosing diabetes from symptoms.
- Assuming the 520 participants represent all populations.
- Defining clinical escalation or safety rules.
- Treating associations in the dataset as causal.
- Replacing validated clinical screening or diagnostic procedures.

---

## 5. CDC Diabetes Health Indicators

**Source:** UCI Machine Learning Repository / CDC BRFSS-derived data  
**Link:** https://archive.ics.uci.edu/dataset/891/cdc+diabetes+health+indicators

**Licence / access:** UCI directs users to the linked original dataset for licensing and acknowledgement requirements.

**Size:** 253,680 instances and 21 features in the UCI version.

**Description:** Contains health statistics, lifestyle survey information, demographics, and diabetes-status information derived from CDC survey data.

**Potential ChronicCare AI use:**
- Examine large-scale diabetes-related health and lifestyle variables.
- Check realistic combinations of demographic and health indicators.
- Develop non-production test scenarios.
- Explore how chronic-disease indicators are represented in survey data.
- Test data-processing workflows against a relatively large tabular dataset.

**Must NOT be used for:**
- Diagnosing an individual patient.
- Assuming survey associations are causal.
- Defining medication or treatment recommendations.
- Treating population-level patterns as individual clinical thresholds.
- Assuming survey variables are equivalent to EHR measurements.

---

## Dataset Usage Principles

These datasets are candidates for development, testing, research, and plausibility checking only. Their inclusion in this review does not mean they have been clinically approved for ChronicCare AI.

Clinical thresholds, emergency rules, medication guidance, and patient-specific recommendations must not be derived solely from these datasets. Such behaviour should instead be based on appropriate clinical sources and clinical review.

No raw dataset should be committed to this repository as part of this review. Before any future dataset is incorporated into the project, its licence, provenance, population, limitations, privacy implications, and intended use should be reviewed.

---

# Proposed Plausibility Ranges

> **Status: PROPOSED, NOT CLINICALLY REVIEWED**
>
> The ranges below are proposed for development, validation, and synthetic test-data checking. They are not diagnostic thresholds, treatment targets, or emergency decision rules. They must be reviewed by the clinical team before being used for clinical validation or patient-facing decisions.

| Measurement | Proposed Minimum | Proposed Maximum | Unit | Source / Basis |
|---|---:|---:|---|---|
| Glucose | 20 | 600 | mg/dL | NHANES glucose laboratory documentation provides measured glucose in mg/dL and identifies values below 50 or above 500 mg/dL as critical-call values in one laboratory protocol. The wider 20–600 interval is therefore proposed only as an engineering plausibility envelope, not a clinical threshold. |
| Glucose | 1.1 | 33.3 | mmol/L | Converted from the proposed 20–600 mg/dL engineering range using approximately 18 mg/dL per mmol/L. |
| Systolic blood pressure | 50 | 250 | mmHg | NHLBI documents normal and hypertension categories and identifies readings above 180/120 mmHg as dangerously high. The wider range is proposed as an engineering plausibility envelope so abnormal but potentially real measurements are not automatically rejected. |
| Diastolic blood pressure | 30 | 150 | mmHg | NHLBI blood-pressure guidance provides clinical BP categories and identifies readings above 180/120 mmHg as dangerously high. This wider interval is proposed for input plausibility checking rather than diagnosis. |
| Weight | 20 | 400 | kg | Current ChronicCare AI profile validation accepts weight from 20 to 400 kg. Retained here as a proposed implementation-aligned plausibility range pending clinical/data review. |
| Height | 50 | 250 | cm | Current ChronicCare AI profile validation accepts height from 50 to 250 cm. Retained here as a proposed implementation-aligned plausibility range pending clinical/data review. |
| Age | 18 | 120 | years | Proposed adult-system test-data range. The lower bound reflects an adult-focused use case; the upper bound is a conservative engineering limit and requires clinical/product review. |

## Interpretation

These limits should be treated as data-quality guardrails only. A value being inside a proposed range does not mean that it is healthy or clinically safe, and a value outside a range should not automatically be interpreted as a diagnosis or emergency.

For example, NHLBI identifies blood pressure above 180/120 mmHg as dangerously high, while NHANES laboratory documentation includes critical-call handling for extreme glucose results. Those clinical contexts are different from simple input plausibility validation.

The proposed limits should therefore remain separate from ChronicCare AI's clinical triage, escalation, diagnosis, and treatment logic.

## Sources

1. CDC/NCHS, National Health and Nutrition Examination Survey (NHANES), laboratory documentation and glucose laboratory procedures:
   https://wwwn.cdc.gov/nchs/nhanes/

2. National Heart, Lung, and Blood Institute (NHLBI), High Blood Pressure — Diagnosis:
   https://www.nhlbi.nih.gov/health/high-blood-pressure/diagnosis

3. ChronicCare AI backend profile validation in `backend-poc-technical/main.py` for the currently implemented height and weight validation limits.

## Review Requirement

**These ranges are proposed, not clinically reviewed.**

Before they are used as production validation rules, they should be checked against the intended ChronicCare AI population, current clinical guidance, observed dataset distributions, measurement-device constraints, and clinician review.