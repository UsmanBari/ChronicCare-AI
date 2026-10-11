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