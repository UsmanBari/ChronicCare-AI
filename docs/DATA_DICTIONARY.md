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