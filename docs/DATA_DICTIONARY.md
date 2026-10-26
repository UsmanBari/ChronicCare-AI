# ChronicCare AI Data Dictionary

This document describes the database fields used by ChronicCare AI. It is based on the database schema and migrations defined in `backend-poc-technical/data_sources/app_store.py`.

## Users

Table: `users`

Stores application user account and access information.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `user_id` | TEXT | Unique identifier for the user. Primary key. | `usr_001` | Yes |
| `email` | TEXT | User's unique email address used to identify the account. Cannot be null. | `patient@example.com` | Yes |
| `role` | TEXT | Application role assigned to the user. Allowed values are `patient`, `provider`, or `admin`. | `patient` | Yes |
| `display_name` | TEXT | Optional name displayed for the user in the application. | `Example Patient` | Yes |
| `status` | TEXT | Current account status. Allowed values are `active` or `disabled`; default is `active`. | `active` | Yes |
| `created_at` | TEXT | Timestamp recording when the user account was created. | `2026-10-11T09:30:00Z` | Yes |
| `last_login_at` | TEXT | Timestamp of the user's most recent login, if available. | `2026-10-11T10:15:00Z` | Yes |

### Constraints

- `user_id` is the primary key.
- `email` must be unique and cannot be null.
- `role` must be one of `patient`, `provider`, or `admin`.
- `status` must be either `active` or `disabled`.

---

## Patient Profiles

Table: `patient_profiles`

Stores patient-specific clinical, consent, demographic, and preference information. The `user_id` field links the profile to the corresponding record in the `users` table.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `user_id` | TEXT | Unique user identifier and foreign key referencing `users.user_id`. It is also the primary key of the patient profile. | `usr_001` | Yes |
| `conditions_json` | TEXT | JSON-encoded list of the patient's tracked health conditions. Defaults to an empty list. | `["diabetes","hypertension"]` | Yes |
| `on_insulin_or_sulfonylurea` | INTEGER | Boolean-like value indicating whether the patient uses insulin or a sulfonylurea. `0` represents false and `1` represents true. | `1` | Yes |
| `language` | TEXT | Patient's selected language for the application. Defaults to `en`. | `en` | Yes |
| `consent_granted_at` | TEXT | Timestamp recording when the patient granted consent, if consent has been granted. | `2026-10-01T12:00:00Z` | Yes |
| `consent_revoked_at` | TEXT | Timestamp recording when the patient revoked consent, if applicable. | `2026-10-10T14:30:00Z` | Yes |
| `updated_at` | TEXT | Timestamp recording when the patient profile was most recently updated. | `2026-10-11T09:45:00Z` | Yes |
| `conditions_basis_json` | TEXT | JSON-encoded information describing the basis or supporting information for recorded conditions. | `{"diabetes":"patient_reported"}` | Yes |
| `provider_notification_consent_at` | TEXT | Timestamp recording when consent for provider notifications was granted. | `2026-10-01T12:05:00Z` | Yes |
| `provider_notification_revoked_at` | TEXT | Timestamp recording when consent for provider notifications was revoked. | `2026-10-10T14:35:00Z` | Yes |
| `smoking_status` | TEXT | Patient smoking status recorded in the profile. | `never` | Yes |
| `comorbidities_json` | TEXT | JSON-encoded comorbidities recorded for the patient. | `["ckd"]` | Yes |
| `date_of_birth` | TEXT | Patient's date of birth. | `1985-06-15` | Yes |
| `inclusion_confirmed_at` | TEXT | Timestamp recording when the patient's inclusion or eligibility was confirmed. | `2026-10-01T12:10:00Z` | Yes |
| `sex_at_birth` | TEXT | Patient's recorded sex at birth. API validation permits `female`, `male`, or `prefer_not_to_say`. | `female` | Yes |
| `pregnancy_status` | TEXT | Patient's recorded pregnancy status. API validation permits `no`, `yes`, `not_sure`, or `not_applicable`. | `not_applicable` | Yes |
| `voice_enabled` | INTEGER | Boolean-like setting indicating whether the voice feature is enabled. Defaults to `0`. | `0` | Yes |
| `height_cm` | REAL | Patient's height in centimetres. The API currently validates values from 50 to 250 cm. | `170.5` | Yes |
| `weight_kg` | REAL | Patient's weight in kilograms. The API currently validates values from 20 to 400 kg. | `72.0` | Yes |
| `diagnosis_year_diabetes` | INTEGER | Year in which the patient was diagnosed with diabetes, when provided. | `2020` | Yes |
| `diagnosis_year_hypertension` | INTEGER | Year in which the patient was diagnosed with hypertension, when provided. | `2022` | Yes |

### Constraints and notes

- `user_id` is the primary key and references `users.user_id`.
- `conditions_json` cannot be null and defaults to `[]`.
- `on_insulin_or_sulfonylurea` cannot be null and defaults to `0`.
- `language` cannot be null and defaults to `en`.
- `updated_at` cannot be null.
- Several profile fields were introduced through later schema migrations rather than in the original `CREATE TABLE` statement.
- `voice_enabled` is stored as an integer but is exposed by the API as a boolean.
- `height_cm` and `weight_kg` are stored as `REAL` values.
- `diagnosis_year_diabetes` and `diagnosis_year_hypertension` are optional integer values.
- The API model also exposes fields such as `smoking_status` and `comorbidities`. They are not listed above because the reviewed `patient_profiles` schema/migration output did not establish them as database columns.

## Personal Data Classification

The `users` and `patient_profiles` tables contain personal data. The `users` table contains account identifiers and account-related information such as email address, display name, role, status, and login timestamps. The `patient_profiles` table contains additional patient-specific information, including health conditions, medication-related information, consent records, date of birth, sex at birth, pregnancy status, height, weight, and diagnosis years. These fields should therefore be handled as sensitive application data and protected appropriately.

---

## Check-ins

Table: `checkins`

Stores the state and lifecycle of a patient's check-in session.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `checkin_id` | TEXT | Unique identifier for the check-in. Primary key. | `chk_001` | Yes |
| `user_id` | TEXT | Identifier of the user who owns the check-in. Foreign key referencing `users.user_id`. | `usr_001` | Yes |
| `mode` | TEXT | Operating mode of the check-in. Allowed values are `connected` or `isolated`. | `connected` | Yes |
| `record_patient_id` | TEXT | Identifier of the patient record associated with the check-in. | `patient_001` | Yes |
| `status` | TEXT | Current check-in status. Allowed values are `in_progress`, `complete`, `emergency`, or `abandoned`. | `in_progress` | Yes |
| `state_json` | TEXT | JSON-encoded state of the check-in. This state may contain the answers collected during the check-in and other interview state. | `{"answers":{"symptoms":"none"}}` | Yes |
| `version` | INTEGER | Version number used for the stored check-in state. Defaults to `0`. | `0` | No |
| `started_at` | TEXT | Timestamp recording when the check-in started. | `2026-10-11T09:00:00Z` | Yes |
| `completed_at` | TEXT | Timestamp recording when the check-in was completed, if applicable. | `2026-10-11T09:10:00Z` | Yes |
| `med_state_json` | TEXT | Optional JSON-encoded medication-related state maintained during the check-in. | `{"confirmed":true}` | Yes |
| `protocol_state_json` | TEXT | Optional JSON-encoded state used by the check-in protocol. | `{"step":"assessment"}` | Yes |
| `ehr_system_id` | TEXT | Optional identifier of the EHR system associated with the check-in. | `ehr_001` | Yes |

### Constraints and notes

- `checkin_id` is the primary key.
- `user_id` cannot be null and references `users.user_id`.
- `mode` must be either `connected` or `isolated`.
- `status` must be one of `in_progress`, `complete`, `emergency`, or `abandoned`.
- `state_json` cannot be null.
- `version` cannot be null and defaults to `0`.
- `started_at` cannot be null.
- `completed_at` is optional.
- `med_state_json`, `protocol_state_json`, and `ehr_system_id` were introduced through later schema migrations.

---

## Check-in Results

Table: `checkin_results`

Stores the result, review status, escalation information, and generated clinical processing output for a completed or processed check-in.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `checkin_id` | TEXT | Identifier of the associated check-in. Primary key and foreign key referencing `checkins.checkin_id`. | `chk_001` | Yes |
| `emergency` | INTEGER | Boolean-like value indicating whether the check-in was classified as an emergency. | `0` | Yes |
| `intakes_json` | TEXT | JSON-encoded intake information collected or generated during the check-in. | `{"symptoms":[]}` | Yes |
| `reconciliation_json` | TEXT | Optional JSON-encoded result of data reconciliation. | `{"status":"matched"}` | Yes |
| `verification_json` | TEXT | Optional JSON-encoded verification information associated with the check-in. | `{"verified":true}` | Yes |
| `requires_review` | INTEGER | Boolean-like value indicating whether the check-in requires review. | `1` | Yes |
| `max_severity` | TEXT | Highest severity assigned to the result. Permitted values are `none`, `low`, `moderate`, or `high`, or null. | `moderate` | Yes |
| `review_status` | TEXT | Current review workflow status. Allowed values are `open`, `acknowledged`, `resolved`, or `escalated`. | `open` | Yes |
| `trigger_category` | TEXT | Optional category describing what triggered a safety or review action. | `symptom` | Yes |
| `trigger_text` | TEXT | Optional text associated with the trigger that caused review or escalation. | `Patient reported concerning symptoms` | Yes |
| `escalated_at` | TEXT | Timestamp recording when the result was escalated, if applicable. | `2026-10-11T09:12:00Z` | Yes |
| `created_at` | TEXT | Timestamp recording when the check-in result was created. | `2026-10-11T09:10:00Z` | Yes |
| `triage_level` | TEXT | Optional triage level assigned during check-in processing. | `high` | Yes |
| `triage_json` | TEXT | Optional JSON-encoded detailed triage result/state. | `{"level":"high"}` | Yes |

### Constraints and notes

- `checkin_id` is the primary key and references `checkins.checkin_id`.
- `emergency`, `intakes_json`, `requires_review`, `review_status`, and `created_at` cannot be null.
- `max_severity`, when present, must be `none`, `low`, `moderate`, or `high`.
- `review_status` must be `open`, `acknowledged`, `resolved`, or `escalated`.
- `trigger_category`, `trigger_text`, `escalated_at`, `triage_level`, and `triage_json` are optional fields.
- `trigger_category`, `trigger_text`, `escalated_at`, `triage_level`, and `triage_json` are also handled through later schema migrations.

---

## Check-in Answers

There is no separate `answers` database table in the reviewed application-store schema.

Check-in answers are submitted through the check-in answer workflow and persisted as part of the check-in state. The application accesses an `answers` object from the check-in state, while `apply_checkin_answer_atomic` is used when saving check-in answers. Therefore, answer content should be treated as personal data because it can contain patient-provided health and symptom information.

The exact structure of individual answers is application-state dependent rather than represented by dedicated relational database columns.

---

## Schema Version

Table: `schema_version`

Stores the database schema migration versions that have been applied.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `version` | INTEGER | Database schema version number. Primary key. | `12` | No |
| `applied_at` | TEXT | Timestamp recording when the schema version was applied. | `2026-10-11T09:00:00Z` | No |

### Constraints and notes

- `version` is the primary key.
- `applied_at` cannot be null.
- This is application/database metadata rather than patient information.

---

## Audit Log

Table: `audit_log`

Stores application audit events and their outcomes.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `id` | INTEGER | Auto-incrementing identifier for the audit event. Primary key. | `101` | No |
| `ts` | TEXT | Timestamp when the audited event occurred. | `2026-10-11T09:15:00Z` | Yes |
| `actor_user_id` | TEXT | Optional identifier of the user responsible for the action. | `usr_001` | Yes |
| `action` | TEXT | Name or description of the audited action. | `profile_update` | Yes |
| `target` | TEXT | Optional target or resource affected by the action. | `patient_profile` | Yes |
| `outcome` | TEXT | Outcome of the action: `ok`, `denied`, or `error`. | `ok` | Yes |
| `detail_json` | TEXT | JSON-encoded details associated with the audit event. | `{"reason":"profile updated"}` | Yes |

### Constraints and notes

- `id` is an auto-incrementing primary key.
- `ts`, `action`, `outcome`, and `detail_json` cannot be null.
- `outcome` must be `ok`, `denied`, or `error`.
- Audit records can become personal data when they identify a user or contain user-related details.

---

## EHR Systems

Table: `ehr_systems`

Stores configuration information for EHR/FHIR systems available to the application.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `ehr_system_id` | TEXT | Unique identifier for the EHR system. Primary key. | `demo-hospital` | No |
| `display_name` | TEXT | Human-readable name of the EHR system. | `Demo hospital` | No |
| `fhir_base_url` | TEXT | Base URL used to access the system's FHIR service. | `sim://demo` | No |
| `enabled` | INTEGER | Boolean-like value indicating whether the EHR system is enabled. Defaults to `1`. | `1` | No |
| `kind` | TEXT | Type of EHR integration. Added through a later migration and defaults to `public_sandbox`. | `simulated` | No |
| `description` | TEXT | Optional description of the EHR system. | `In-process FHIR server with synthetic data` | No |

### Constraints and notes

- `ehr_system_id` is the primary key.
- `display_name` and `fhir_base_url` cannot be null.
- `enabled` cannot be null and defaults to `1`.
- `kind` and `description` were introduced through later schema migrations.

---

## EHR Connections

Table: `ehr_connections`

Stores the relationship between an application user and an external EHR system.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `connection_id` | TEXT | Unique identifier for the EHR connection. Primary key. | `conn_001` | Yes |
| `user_id` | TEXT | Application user associated with the EHR connection. | `usr_001` | Yes |
| `ehr_system_id` | TEXT | Identifier of the connected EHR system. | `demo-hospital` | Yes |
| `external_patient_id` | TEXT | Patient identifier used by the external EHR system. | `patient_001` | Yes |
| `status` | TEXT | Current connection status. Allowed values are `active`, `failed`, or `revoked`. | `active` | Yes |
| `linked_at` | TEXT | Timestamp when the EHR connection was established. | `2026-10-01T10:00:00Z` | Yes |
| `last_verified_at` | TEXT | Timestamp when the connection was last successfully verified. | `2026-10-11T09:00:00Z` | Yes |
| `last_error_code` | TEXT | Optional error code from the most recent connection failure. | `FHIR_TIMEOUT` | Yes |
| `revoked_at` | TEXT | Timestamp when the EHR connection was revoked, if applicable. | `2026-10-12T10:00:00Z` | Yes |

### Constraints and notes

- `connection_id` is the primary key.
- `user_id` references `users.user_id`.
- `ehr_system_id` references `ehr_systems.ehr_system_id`.
- `status` must be `active`, `failed`, or `revoked`.
- `user_id`, `ehr_system_id`, `external_patient_id`, `status`, and `linked_at` cannot be null.

---

## Review Actions

Table: `review_actions`

Stores actions performed by providers when reviewing check-in results.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `id` | INTEGER | Auto-incrementing identifier for the review action. Primary key. | `25` | No |
| `checkin_id` | TEXT | Identifier of the check-in being reviewed. | `chk_001` | Yes |
| `provider_user_id` | TEXT | Identifier of the provider who performed the review action. | `usr_provider_001` | Yes |
| `action` | TEXT | Review action performed. Allowed values are `acknowledge`, `resolve`, or `escalate`. | `acknowledge` | Yes |
| `note` | TEXT | Optional note entered by the provider. | `Reviewed patient check-in` | Yes |
| `ts` | TEXT | Timestamp when the review action occurred. | `2026-10-11T09:30:00Z` | Yes |

### Constraints and notes

- `id` is an auto-incrementing primary key.
- `checkin_id` references `checkins.checkin_id`.
- `provider_user_id` references `users.user_id`.
- `action` must be `acknowledge`, `resolve`, or `escalate`.
- Provider notes may contain patient-related information and should therefore be handled as personal data.

---

## Allergies

Table: `allergies`

Stores allergy information associated with application users.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `allergy_id` | TEXT | Unique identifier for the allergy record. Primary key. | `allergy_001` | Yes |
| `user_id` | TEXT | Identifier of the user to whom the allergy belongs. | `usr_001` | Yes |
| `substance` | TEXT | Substance associated with the recorded allergy. | `penicillin` | Yes |
| `reaction` | TEXT | Optional description of the patient's reaction. | `rash` | Yes |
| `confirmed` | INTEGER | Boolean-like value indicating whether the allergy has been confirmed. | `1` | Yes |
| `created_at` | TEXT | Timestamp recording when the allergy record was created. | `2026-10-11T09:00:00Z` | Yes |

### Constraints and notes

- `allergy_id` is the primary key.
- `user_id` references `users.user_id`.
- `user_id`, `substance`, `confirmed`, and `created_at` cannot be null.
- Allergy information is health information associated with a user.

---

# Local Clinical Data Store

The following tables are defined separately in `data_sources/local_store.py`.

## Patients

Table: `patients`

Stores basic patient identity information used by the local clinical data store.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `id` | TEXT | Unique patient identifier. Primary key. | `patient_001` | Yes |
| `name` | TEXT | Patient name. | `Example Patient` | Yes |
| `date_of_birth` | TEXT | Patient's date of birth. | `1985-06-15` | Yes |

### Constraints and notes

- `id` is the primary key.
- `name` and `date_of_birth` cannot be null.

---

## Observations

Table: `observations`

Stores clinical observations associated with patients.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `id` | TEXT | Unique identifier for the observation. Primary key. | `obs_001` | Yes |
| `patient_id` | TEXT | Identifier of the patient associated with the observation. | `patient_001` | Yes |
| `type` | TEXT | Type of clinical observation. | `blood_pressure` | Yes |
| `value` | REAL | Numeric value of the observation. | `120` | Yes |
| `unit` | TEXT | Unit in which the observation value is expressed. | `mmHg` | Yes |
| `timestamp` | TEXT | Timestamp associated with the observation. | `2026-10-11T08:30:00Z` | Yes |
| `source` | TEXT | Source from which the observation was obtained. | `local` | Yes |
| `origin` | TEXT | Optional origin/provenance information for the observation. | `ehr` | Yes |

### Constraints and notes

- `id` is the primary key.
- `patient_id` references `patients.id`.
- `patient_id`, `type`, `value`, `unit`, `timestamp`, and `source` cannot be null.
- `origin` is optional and is also ensured by a schema migration.

---

## Medications

Table: `medications`

Stores medication information associated with patients.

| Column | Type | Meaning | Example | Personal Data? |
|---|---|---|---|---|
| `id` | TEXT | Unique identifier for the medication record. Primary key. | `med_001` | Yes |
| `patient_id` | TEXT | Identifier of the patient associated with the medication. | `patient_001` | Yes |
| `medication_name` | TEXT | Name of the recorded medication. | `metformin` | Yes |
| `status` | TEXT | Current recorded medication status. | `active` | Yes |
| `dosage` | TEXT | Recorded dosage information. | `500 mg` | Yes |
| `timestamp` | TEXT | Timestamp associated with the medication record. | `2026-10-11T08:30:00Z` | Yes |
| `source` | TEXT | Source from which the medication information was obtained. | `local` | Yes |
| `origin` | TEXT | Optional origin/provenance information for the medication record. | `ehr` | Yes |

### Constraints and notes

- `id` is the primary key.
- `patient_id` references `patients.id`.
- `patient_id`, `medication_name`, `status`, `dosage`, `timestamp`, and `source` cannot be null.
- `origin` is optional and is also ensured by a schema migration.

---

## API Record Additions (Iteration 2 Day 1)

### `doctor_on_record`
Additive optional object in `PatientRecordResponse` (connected mode):
- `name` (TEXT): Display name of practitioner on record (from FHIR `generalPractitioner` or latest `Encounter.participant`).
- `identifier` (TEXT, optional): Clinical identifier of the practitioner, if available in the EHR record.
- `source` (TEXT): Provenance indicator, either `"ehr_general_practitioner"` or `"ehr_encounter"`.
- `as_of` (TEXT, optional): Timestamp associated with the practitioner reference.

### `allergies` (Connected Mode)
In connected mode, FHIR `AllergyIntolerance` entries are normalized into the allergies list with `origin: "ehr"` and high trust, read-only to preserve record authority. Any entries marked `entered-in-error` are excluded at adapter normalisation.

---

## Personal Data Summary

Personal data is stored across several parts of the ChronicCare AI data model. Account identity and access information is stored in `users`; demographic, condition, consent, and other patient-specific information is stored in `patient_profiles`; check-in responses and clinical processing information are stored in `checkins` and `checkin_results`; provider review activity is stored in `review_actions`; allergy information is stored in `allergies`; and external patient identifiers and EHR linkage information are stored in `ehr_connections`. The separate local clinical data store contains patient identity information in `patients`, clinical measurements in `observations`, and medication information in `medications`. `audit_log` may also contain personal data when an event identifies a user or contains user-related details. By contrast, `schema_version` contains database migration metadata and `ehr_systems` primarily contains system configuration rather than patient information.