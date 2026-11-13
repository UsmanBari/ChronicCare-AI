# Appointment Workflow & Escalation Architecture (PR I4-D)

## 1. Executive Summary & Proposal Scope
This document specifies the appointment workflow, synthetic provider directory, and red-flag escalation timeout tracking committed in **Proposal Section 15 ("Appointment Workflow")**, **Section 35 ("Committed for Real Implementation")**, and **Section 37 ("Clinical Traceability")**.

Previously, appointment screens were frontend mock placeholders. PR I4-D establishes the complete backend service, persistence tables (`provider_directory` and `appointments` at schema version 17), REST endpoints, and responsive frontend portal integrations across Patient, Provider, and Admin views.

---

## 2. Clinical Invariant: Triage is Read-Only
In strict adherence to the project motto:
> *"The model proposes, the rules decide."*

The appointment workflow is purely downstream of clinical triage:
- The appointment service **reads** the final triage level (`routine`, `review`, `urgent`, `emergency`).
- It **never** alters, lowers, or bypasses any triage level.
- Clinical rules remain untouched and 100% deterministic.

---

## 3. Triage Colour to Action Mapping
As committed in Section 15 and Section 37:

| Triage Level | Triage Colour | Appointment Action | Urgency | Default Mode | Booking Window / Timing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **routine** | **Green** | **No appointment created** | — | — | Patient advised to continue daily monitoring |
| **review** | **Yellow** | **Offered routine appointment** | `routine` | `telehealth` | Slot selectable within 3 days |
| **urgent** | **Red** | **Booked urgent appointment** | `urgent` | `in_person` | Scheduled for today (immediate care team notification) |
| **emergency** | **Red** | **Booked urgent appointment** | `urgent` | `in_person` | Scheduled for today alongside emergency 1122 guidance |

---

## 4. Specialty Routing & Fallbacks
Specialty determination follows clinical consensus recorded in `docs/CLINICIAN_RESPONSES.md` (item 4):

| Patient Enrolled Condition | Target Specialty | Fictional Provider | Fallback Rule |
| :--- | :--- | :--- | :--- |
| **Diabetes only** | `endocrinology` | Dr. Ayesha Siddiqa (`prov-demo-endo`) | General practice (`general`) if unavailable |
| **Hypertension only** | `cardiology_im` | Dr. Tariq Mahmood (`prov-demo-cardio`) | General practice (`general`) if unavailable |
| **Diabetes + Hypertension** | `internal_medicine` | Dr. Sana Malik (`prov-demo-im`) | General practice (`general`) if unavailable |
| **Other / Unspecified** | `general` | Dr. Bilal Ahmed (`prov-demo-gen-1`) | Unassigned queue if all unavailable |

If all matching specialist and general providers are toggled unavailable by admin, the appointment is created with `provider_id=""` (unassigned) and placed into the central clinic queue.

---

## 5. Escalation Timeout Tracking
For urgent (Red) appointments, Section 15 mandates an escalation ladder to prevent unacknowledged critical cases:

| Elapsed Time from Creation | Escalation State | System Action | Audit Log Record |
| :--- | :--- | :--- | :--- |
| **< 2 hours** | `pending` | Waiting for provider review | Appointment created |
| **≥ 2 hours** | `re_notify` | Re-notify care team; amber alert badge | Re-notification logged |
| **≥ 24 hours** | `admin_flag` | Red pulse flag on admin dashboard | `escalation_timeout_24h` written once to immutable audit table |
| **Provider Acknowledges** | `none` (or `acknowledged`) | Escalation alert cleared; `acknowledged_at` recorded | Provider acknowledgment logged |

### 5.1 Environment Overrides for Evaluation Demonstrations
In standard operation, timeouts default to the clinical specifications (2 hours for `re_notify` and 24 hours for `admin_flag`). For testing and live evaluation demonstrations (e.g. 10-minute viva demos), timeout durations can be overridden via environment variables without altering clinical business logic:
- `ESCALATION_TIMEOUT_MINUTES`: Sets the admin flag timeout in minutes (code default: `1440` = 24 hours).
- `ESCALATION_RENOTIFY_MINUTES`: Sets the re-notification timeout in minutes (code default: `120` = 2 hours; if omitted but `ESCALATION_TIMEOUT_MINUTES` is set, scales proportionally to `admin_minutes / 12`).

---

## 6. Synthetic Provider Directory
To support testing and demonstration without third-party EHR dependencies, 5 synthetic fictional clinical providers are seeded in `provider_directory`:

1. `prov-demo-endo`: **Dr. Ayesha Siddiqa** — Endocrinology (`endocrinology`)
2. `prov-demo-cardio`: **Dr. Tariq Mahmood** — Cardiology (`cardiology_im`)
3. `prov-demo-im`: **Dr. Sana Malik** — Internal Medicine (`internal_medicine`)
4. `prov-demo-gen-1`: **Dr. Bilal Ahmed** — General Practice (`general`)
5. `prov-demo-gen-2`: **Dr. Zainab Qureshi** — General Practice (`general`)

Admins can toggle each provider's `available` status via `PATCH /api/admin/providers/{id}`.

---

## 7. REST API Endpoints

### Patient Endpoints
- `GET /api/me/appointments` — Lists the authenticated patient's appointments (latest first).
- `POST /api/me/appointments/{id}/book` — Books a slot for an offered appointment (must be within 3 days).
- `POST /api/me/appointments/{id}/cancel` — Cancels an appointment.

### Provider Endpoints
- `GET /api/provider/appointments` — Lists appointments assigned to the provider or unassigned queue.
- `POST /api/provider/appointments/{id}/acknowledge` — Clears escalation timer by setting `acknowledged_at`.
- `POST /api/provider/appointments/{id}/attended` — Marks consultation completed (`status="attended"`).

### Admin Endpoints
- `GET /api/admin/providers` — Lists all synthetic providers with availability status.
- `PATCH /api/admin/providers/{id}` — Updates provider availability (`available: boolean`).
- `GET /api/admin/escalations` — Lists active unacknowledged urgent appointments exceeding 2h or 24h.
