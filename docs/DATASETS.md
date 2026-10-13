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
>
> Clinical sources listed below provide context for clinically meaningful values and thresholds. Unless explicitly stated, they do not define or validate the exact outer engineering bounds used by ChronicCare AI.

| Measurement | Proposed Minimum | Proposed Maximum | Unit | Source / Basis |
|---|---:|---:|---|---|
| Glucose | 20 | 600 | mg/dL | Project-defined engineering plausibility envelope used by the current interview validation. ADA Standards of Care provides clinical glucose thresholds and treatment targets, but the 20–600 mg/dL interval is not presented as an ADA-defined physiologic range. It remains an illustrative input-validation bound pending clinical review. |
| Glucose | 1.1 | 33.3 | mmol/L | Converted from the project-defined 20–600 mg/dL engineering envelope using approximately 18 mg/dL per mmol/L. This is an input-validation bound, not a diagnostic or treatment range. |
| Systolic blood pressure | 60 | 260 | mmHg | Project-defined engineering plausibility envelope used by the current interview validation. AHA/ACC guidance provides clinical blood-pressure categories and severe-hypertension thresholds, but does not define 60–260 mmHg as a physiologic plausibility range. |
| Diastolic blood pressure | 30 | 160 | mmHg | Project-defined engineering plausibility envelope used by the current interview validation. It is intentionally separate from clinical hypertension and emergency thresholds and requires clinical review. |
| Weight | 20 | 400 | kg | Project-defined profile-validation range. A separate observation-validation path currently accepts 20–300 kg. This implementation difference is documented here and should be reconciled before a single project-wide weight plausibility rule is claimed. |
| Height | 50 | 250 | cm | Project-defined profile-validation range retained as an engineering input guardrail pending clinical and product review. |
| Age | 18 | 120 | years | Project scope and engineering bounds. The lower bound reflects the adults-only ChronicCare AI scope. The upper bound is an illustrative maximum plausible age used by the implementation and requires clinical/product review. |

## Interpretation

These limits are data-quality and input-validation guardrails only. A value being inside a proposed range does not mean that it is healthy, clinically safe, or appropriate for a particular patient. Likewise, a value outside one of these engineering ranges should not automatically be interpreted as a diagnosis or emergency.

Clinical thresholds must remain distinct from plausibility bounds. For example, AHA/ACC blood-pressure guidance defines clinically meaningful blood-pressure categories and severe-hypertension thresholds. Those thresholds have a different purpose from the broad 60–260 mmHg systolic and 30–160 mmHg diastolic envelopes used to decide whether an entered value is structurally plausible enough for further processing.

Similarly, ADA Standards of Care provides clinically meaningful glucose thresholds and treatment targets. These should not be interpreted as evidence that ChronicCare AI's broader 20–600 mg/dL engineering envelope is itself a clinically validated range.

NHANES data and laboratory documentation may help the project understand realistic observations, units, distributions, and extreme laboratory values. Dataset distributions and laboratory handling rules must not be treated as substitutes for clinical guidelines.

The proposed plausibility limits must therefore remain separate from ChronicCare AI's clinical triage, escalation, diagnosis, and treatment logic.

## Implementation Alignment

The current implementation contains the following relevant validation bounds:

- `backend-poc-technical/agents/answer_validation.py`
  - Glucose: 20–600 mg/dL
  - Glucose: 1.1–33.3 mmol/L
  - Systolic BP: 60–260 mmHg
  - Diastolic BP: 30–160 mmHg
  - Pulse: 30–220 bpm
  - Weight: 20–400 kg
  - Height: 50–250 cm
  - Temperature: 34–43 °C

- `backend-poc-technical/agents/adaptive_interview_agent.py`
  - Glucose: 20–600 mg/dL
  - Systolic BP: 60–260 mmHg
  - Diastolic BP: 30–160 mmHg
  - These constants are explicitly described in the implementation as illustrative plausibility bounds rather than clinical guidance.

- `backend-poc-technical/main.py`
  - Glucose observation: 20–600 mg/dL
  - Systolic BP observation: 60–260 mmHg
  - Diastolic BP observation: 30–160 mmHg
  - Weight observation: 20–300 kg
  - HbA1c observation: 3–20%

The difference between the 20–400 kg profile/answer-validation weight range and the 20–300 kg observation-validation range is an implementation inconsistency. This document records that difference rather than claiming that either maximum is a clinically established threshold.

Pulse, height, weight, temperature, age, and HbA1c outer plausibility limits remain project-defined engineering limits unless a future clinical review approves a specific evidence-backed rule.

## Sources

1. American Diabetes Association Professional Practice Committee. *Standards of Care in Diabetes—2026*, Section 6: Glycemic Goals, Hypoglycemia, and Hyperglycemic Crises.
   - Used as clinical context for glucose thresholds, goals, hypoglycemia, and hyperglycemia.
   - It is not represented here as the source of the project's exact 20–600 mg/dL engineering plausibility envelope.

2. American Heart Association / American College of Cardiology. *2025 High Blood Pressure Guideline*.
   - Used as clinical context for blood-pressure classification and severe hypertension.
   - It is not represented here as defining the project's exact 60–260 / 30–160 mmHg engineering plausibility envelopes.

3. CDC/NCHS, National Health and Nutrition Examination Survey (NHANES), laboratory documentation:
   https://wwwn.cdc.gov/nchs/nhanes/
   - Used as supporting context for measured health and laboratory data.
   - NHANES observations and laboratory procedures are not treated as clinical validation of the project's outer plausibility bounds.

4. National Heart, Lung, and Blood Institute (NHLBI), High Blood Pressure:
   https://www.nhlbi.nih.gov/health/high-blood-pressure
   - Used as additional patient-facing clinical context for blood-pressure categories and high blood pressure.
   - Clinical categories are kept separate from the project's broad input-plausibility envelopes.

5. ChronicCare AI implementation:
   - `backend-poc-technical/agents/answer_validation.py`
   - `backend-poc-technical/agents/adaptive_interview_agent.py`
   - `backend-poc-technical/main.py`
   - These files are the source of the currently implemented engineering validation bounds. Where implementation paths disagree, the discrepancy is documented rather than presented as a clinically validated rule.

## Review Requirement

**These ranges are proposed, not clinically reviewed.**

Before these ranges are relied upon as production validation rules, they should be reviewed against:

- the intended ChronicCare AI patient population;
- current clinical guidelines;
- observed dataset distributions;
- measurement-device constraints and valid device ranges;
- unit-conversion behaviour;
- handling of extreme but genuine measurements;
- the consequences of rejecting a genuine reading as implausible; and
- clinician and product-owner review.

Any future change from an engineering plausibility bound to a clinically approved validation rule should record the exact guideline, version/year, relevant section or table, rationale for the selected bound, and date of clinical review.