# ChronicCare AI POC — Milestone 5 Scenario Evidence Report

**Execution Status**: ALL SCENARIOS VERIFIED SUCCESSFULLY

This document contains the complete, human-readable evidence trace captured by running the end-to-end M1–M4 pipeline (`reconcile_bundles()` -> `verify_reconciliation()`) against the committed defense scenario set.

## Executive Summary Results Table

| Scenario ID | Scenario Name | Status | Expected Outcome | Actual Summary | Result |
| :--- | :--- | :---: | :--- | :--- | :---: |
| `scenario_1` | Scenario 1 — Clean/Connected, All High-Trust | `{'auto_resolved': 4, 'requires_review': 0, 'severity_none': 4, 'severity_low': 0, 'severity_moderate': 0, 'severity_high': 0}` | all severity 'none', zero requires_human_review (100% eligible for automatic resolution under deterministic rules) | `review=0, auto=4` | **PASS** |
| `scenario_2` | Scenario 2 — Conflicting Observation | `{'auto_resolved': 0, 'requires_review': 2, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 0, 'severity_high': 2}` | severity 'high' (delta > 2x threshold), requires_human_review = True with delta-driven review_reason | `review=2, auto=0` | **PASS** |
| `scenario_3a` | Scenario 3A — Missing Medication Record (High-Trust Present Side) | `{'auto_resolved': 1, 'requires_review': 0, 'severity_none': 0, 'severity_low': 1, 'severity_moderate': 0, 'severity_high': 0}` | severity 'low', requires_human_review = False (auto-resolved due to high-trust present side) | `review=0, auto=1` | **PASS** |
| `scenario_3b` | Scenario 3B — Missing Medication Record (Low-Trust Present Side) | `{'auto_resolved': 0, 'requires_review': 1, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 1, 'severity_high': 0}` | severity 'moderate', requires_human_review = True (review required due to non-high trust present side) | `review=1, auto=0` | **PASS** |
| `scenario_4a` | Scenario 4A — Trust Metadata in Conflict Cases (Both Sides High-Trust) | `{'auto_resolved': 0, 'requires_review': 1, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 0, 'severity_high': 1}` | trust_level_a='high', trust_level_b='high', severity='high', requires_human_review=True | `review=1, auto=0` | **PASS** |
| `scenario_4b` | Scenario 4B — Trust Metadata in Conflict Cases (One Side Low-Trust) | `{'auto_resolved': 0, 'requires_review': 1, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 0, 'severity_high': 1}` | trust_level_a='high', trust_level_b='low', severity='high', requires_human_review=True (trust metadata carried into result) | `review=1, auto=0` | **PASS** |

### Adversarial / Stress-Test Scenario (Kept Separate)

| Scenario ID | Scenario Name | Status | Expected Outcome | Actual Summary | Result |
| :--- | :--- | :---: | :--- | :--- | :---: |
| `scenario_c1` | Adversarial / Stress-Test Scenario C1 — Medication Dosage Mismatch (Separate from 4 Official Scenarios) | `{'auto_resolved': 0, 'requires_review': 1, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 1, 'severity_high': 0}` | severity 'moderate', requires_human_review = True (dosage string mismatch detected; narrow claim: string mismatch detection, not semantic dosage parsing) | `review=1, auto=0` | **PASS** |

---

## Detailed Scenario Traces

### Scenario 1 — Clean/Connected, All High-Trust

- **Scenario ID**: `scenario_1`
- **Patient ID**: `M5-PATIENT-SCENARIO-1`
- **Description**: Both prior FHIR record and new FHIR check-in agree within M3 thresholds for Connected Patient A (M5-PATIENT-SCENARIO-1).
- **Origin Tags Used**: `{}`
- **Expected Outcome**: all severity 'none', zero requires_human_review (100% eligible for automatic resolution under deterministic rules)
- **Verification Summary**: `{'auto_resolved': 4, 'requires_review': 0, 'severity_none': 4, 'severity_low': 0, 'severity_moderate': 0, 'severity_high': 0}`
- **Scenario Verdict**: **PASS**

#### Observation Traces
| Observation | Recon Status | Side A (Val/Src/ID/Trust) | Side B (Val/Src/ID/Trust) | Delta | Severity | Review Required | Review Reason |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| `glucose` | `agree` | `120.0 mg/dL (fhir:M5-S1-FHIR-OBS-01, high)` | `122.0 mg/dL (fhir:M5-S1-FHIR-OBS-01-CHECKIN, high)` | `2.0` | `none` | **NO (Auto)** | Agreement between trusted sources (auto-resolved) |
| `hba1c` | `agree` | `6.8 % (fhir:M5-S1-FHIR-OBS-02, high)` | `6.9 % (fhir:M5-S1-FHIR-OBS-02-CHECKIN, high)` | `0.1` | `none` | **NO (Auto)** | Agreement between trusted sources (auto-resolved) |
| `blood_pressure_systolic` | `agree` | `124.0 mmHg (fhir:M5-S1-FHIR-OBS-03, high)` | `126.0 mmHg (fhir:M5-S1-FHIR-OBS-03-CHECKIN, high)` | `2.0` | `none` | **NO (Auto)** | Agreement between trusted sources (auto-resolved) |

#### Medication Traces
| Medication | Recon Status | Side A (Status/Dosage/Src/ID/Trust) | Side B (Status/Dosage/Src/ID/Trust) | Severity | Review Required | Review Reason |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `Metformin 500mg` | `agree` | `active | '1 tablet twice daily' (fhir:M5-S1-FHIR-MED-01, high)` | `active | '1 tablet twice daily' (fhir:M5-S1-FHIR-MED-01-CHECKIN, high)` | `none` | **NO (Auto)** | Medication agreement between trusted sources (auto-resolved) |

---

### Scenario 2 — Conflicting Observation

- **Scenario ID**: `scenario_2`
- **Patient ID**: `M5-PATIENT-SCENARIO-2`
- **Description**: Glucose and HbA1c readings disagree beyond M3 thresholds within 48h window between prior Local state and new Local check-in for Isolated Patient B (M5-PATIENT-SCENARIO-2).
- **Origin Tags Used**: `{}`
- **Expected Outcome**: severity 'high' (delta > 2x threshold), requires_human_review = True with delta-driven review_reason
- **Verification Summary**: `{'auto_resolved': 0, 'requires_review': 2, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 0, 'severity_high': 2}`
- **Scenario Verdict**: **PASS**

#### Observation Traces
| Observation | Recon Status | Side A (Val/Src/ID/Trust) | Side B (Val/Src/ID/Trust) | Delta | Severity | Review Required | Review Reason |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| `glucose` | `conflict` | `115.0 mg/dL (local:M5-S2-LOC-OBS-01, medium)` | `175.0 mg/dL (local:M5-S2-LOC-OBS-01-CHECKIN, medium)` | `60.0` | `high` | **YES** | Observation conflict exceeding 2x threshold (delta 60.0 > 2x threshold 30.0) |
| `hba1c` | `conflict` | `6.4 % (local:M5-S2-LOC-OBS-02, medium)` | `8.1 % (local:M5-S2-LOC-OBS-02-CHECKIN, medium)` | `1.7` | `high` | **YES** | Observation conflict exceeding 2x threshold (delta 1.7 > 2x threshold 1.0) |

---

### Scenario 3A — Missing Medication Record (High-Trust Present Side)

- **Scenario ID**: `scenario_3a`
- **Patient ID**: `M5-PATIENT-SCENARIO-3A`
- **Description**: Active Lisinopril present in FHIR prior state only (high trust), missing in new check-in for Connected Patient A. Auto-resolved.
- **Origin Tags Used**: `{}`
- **Expected Outcome**: severity 'low', requires_human_review = False (auto-resolved due to high-trust present side)
- **Verification Summary**: `{'auto_resolved': 1, 'requires_review': 0, 'severity_none': 0, 'severity_low': 1, 'severity_moderate': 0, 'severity_high': 0}`
- **Scenario Verdict**: **PASS**

#### Medication Traces
| Medication | Recon Status | Side A (Status/Dosage/Src/ID/Trust) | Side B (Status/Dosage/Src/ID/Trust) | Severity | Review Required | Review Reason |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `Lisinopril 10mg` | `missing_in_b` | `active | '1 tablet daily' (fhir:M5-S3A-FHIR-MED-01, high)` | `None` | `low` | **NO (Auto)** | Medication missing in one source (missing_in_b); present side is high-trust (auto-resolved) |

---

### Scenario 3B — Missing Medication Record (Low-Trust Present Side)

- **Scenario ID**: `scenario_3b`
- **Patient ID**: `M5-PATIENT-SCENARIO-3B`
- **Description**: Active Lisinopril present in new Local check-in only, explicitly tagged 'local_self_reported' (low trust) for Isolated Patient B. Requires human review.
- **Origin Tags Used**: `{'M5-S3B-LOC-MED-01': 'local_self_reported'}`
- **Expected Outcome**: severity 'moderate', requires_human_review = True (review required due to non-high trust present side)
- **Verification Summary**: `{'auto_resolved': 0, 'requires_review': 1, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 1, 'severity_high': 0}`
- **Scenario Verdict**: **PASS**

#### Medication Traces
| Medication | Recon Status | Side A (Status/Dosage/Src/ID/Trust) | Side B (Status/Dosage/Src/ID/Trust) | Severity | Review Required | Review Reason |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `Lisinopril 10mg` | `missing_in_a` | `None` | `active | '1 tablet daily' (local:M5-S3B-LOC-MED-01, low)` | `moderate` | **YES** | Medication missing in one source (missing_in_a); present side is low-trust |

---

### Scenario 4A — Trust Metadata in Conflict Cases (Both Sides High-Trust)

- **Scenario ID**: `scenario_4a`
- **Patient ID**: `M5-PATIENT-SCENARIO-4A`
- **Description**: Glucose conflict (delta 55 > 2x threshold) between prior Local state and new Local check-in, both tagged clinician-entered (high trust).
- **Origin Tags Used**: `{'M5-S4A-LOC-OBS-01': 'local_clinician_entered', 'M5-S4A-LOC-OBS-02': 'local_clinician_entered'}`
- **Expected Outcome**: trust_level_a='high', trust_level_b='high', severity='high', requires_human_review=True
- **Verification Summary**: `{'auto_resolved': 0, 'requires_review': 1, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 0, 'severity_high': 1}`
- **Scenario Verdict**: **PASS**

#### Observation Traces
| Observation | Recon Status | Side A (Val/Src/ID/Trust) | Side B (Val/Src/ID/Trust) | Delta | Severity | Review Required | Review Reason |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| `glucose` | `conflict` | `110.0 mg/dL (local:M5-S4A-LOC-OBS-01, high)` | `165.0 mg/dL (local:M5-S4A-LOC-OBS-02, high)` | `55.0` | `high` | **YES** | Observation conflict exceeding 2x threshold (delta 55.0 > 2x threshold 30.0) |

---

### Scenario 4B — Trust Metadata in Conflict Cases (One Side Low-Trust)

- **Scenario ID**: `scenario_4b`
- **Patient ID**: `M5-PATIENT-SCENARIO-4B`
- **Description**: Identical glucose conflict (delta 55 > 2x threshold) between prior Local state (high trust) and new Local check-in tagged self-reported (low trust).
- **Origin Tags Used**: `{'M5-S4B-LOC-OBS-01': 'local_clinician_entered', 'M5-S4B-LOC-OBS-02': 'local_self_reported'}`
- **Expected Outcome**: trust_level_a='high', trust_level_b='low', severity='high', requires_human_review=True (trust metadata carried into result)
- **Verification Summary**: `{'auto_resolved': 0, 'requires_review': 1, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 0, 'severity_high': 1}`
- **Scenario Verdict**: **PASS**

#### Observation Traces
| Observation | Recon Status | Side A (Val/Src/ID/Trust) | Side B (Val/Src/ID/Trust) | Delta | Severity | Review Required | Review Reason |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| `glucose` | `conflict` | `110.0 mg/dL (local:M5-S4B-LOC-OBS-01, high)` | `165.0 mg/dL (local:M5-S4B-LOC-OBS-02, low)` | `55.0` | `high` | **YES** | Observation conflict exceeding 2x threshold (delta 55.0 > 2x threshold 30.0) |

---

### ADVERSARIAL SCENARIO (SEPARATE): Adversarial / Stress-Test Scenario C1 — Medication Dosage Mismatch (Separate from 4 Official Scenarios)

- **Scenario ID**: `scenario_c1`
- **Patient ID**: `M5-PATIENT-ADVERSARIAL-C1`
- **Description**: Same active medication name on prior Local state and new Local check-in with mismatched dosage strings ('1 tablet twice daily' vs '2 tablets once daily in evening').
- **Origin Tags Used**: `{'M5-C1-LOC-MED-01': 'local_clinician_entered', 'M5-C1-LOC-MED-02': 'local_clinician_entered'}`
- **Expected Outcome**: severity 'moderate', requires_human_review = True (dosage string mismatch detected; narrow claim: string mismatch detection, not semantic dosage parsing)
- **Verification Summary**: `{'auto_resolved': 0, 'requires_review': 1, 'severity_none': 0, 'severity_low': 0, 'severity_moderate': 1, 'severity_high': 0}`
- **Scenario Verdict**: **PASS**

#### Medication Traces
| Medication | Recon Status | Side A (Status/Dosage/Src/ID/Trust) | Side B (Status/Dosage/Src/ID/Trust) | Severity | Review Required | Review Reason |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `Metformin 500mg` | `conflict` | `active | '1 tablet twice daily' (local:M5-C1-LOC-MED-01, high)` | `active | '2 tablets once daily in evening' (local:M5-C1-LOC-MED-02, high)` | `moderate` | **YES** | Medication dosage or status mismatch (A: status=active, dosage='1 tablet twice daily' vs B: status=active, dosage='2 tablets once daily in evening') |

---
