# Queue Task Report: H1 — Appointments Workflow & Provider Directory

- **Task ID**: `h1-appointments`
- **Branch**: `feat/i4-appointments`
- **PR Title**: `I4-D: appointment workflow (triage colour -> booking), synthetic provider directory, escalation timeout`
- **Author**: Hassaan (AI Assistant)
- **Date**: 2026-11-12
- **Status**: COMPLETED

---

## 1. Commitments Delivered (Proposal Sec 15, 35, 37)
1. **Colour to Appointment Action**:
   - **Green (`routine`)**: No appointment created; patient guided to maintain daily routine.
   - **Yellow (`review`)**: Offered routine appointment (`urgency="routine"`, default `telehealth`), slot selectable within a 3-day booking window.
   - **Red (`urgent` or `emergency`)**: Booked urgent appointment (`urgency="urgent"`, default `in_person`) scheduled for today, care team notified immediately.
2. **Specialty Routing & Provider Fallbacks**:
   - Diabetes -> `endocrinology` (`prov-demo-endo`, Dr. Ayesha Siddiqa).
   - Hypertension -> `cardiology_im` (`prov-demo-cardio`, Dr. Tariq Mahmood).
   - Dual conditions (Diabetes + Hypertension) -> `internal_medicine` (`prov-demo-im`, Dr. Sana Malik) per `docs/CLINICIAN_RESPONSES.md` item 4.
   - Other / Unspecified -> `general` (`prov-demo-gen-1`, Dr. Bilal Ahmed).
   - If specialist unavailable, falls back to `general`; if all unavailable, queues as unassigned (`provider_id=""`).
3. **Escalation Timeout Ladder**:
   - `< 2h`: `pending` (waiting for provider acknowledgment).
   - `≥ 2h`: `re_notify` (care team re-notified; amber alert banner).
   - `≥ 24h`: `admin_flag` (red pulse alert on admin dashboard; single immutable audit record `escalation_timeout_24h` written).
   - Provider acknowledgment sets `acknowledged_at` and clears escalation timeout.
4. **Synthetic Provider Directory**:
   - 5 synthetic providers seeded at migration v17 without third-party EHR dependencies.
   - Admin toggle switch to update provider availability in real time.
5. **Clinical Invariant Preserved**:
   - Triage levels are strictly read-only. The appointment service consumes the final triage level; it never modifies, overrides, or lowers it ("the model proposes, the rules decide").

---

## 2. Schema Migration v16 -> v17
- Updated `LATEST_SCHEMA_VERSION = 17` in `data_sources/app_store.py`.
- Added tables `provider_directory` and `appointments` for both SQLite and MySQL.
- Enforced MySQL hotfix width contract (`VARCHAR(191)` on all ID columns).
- Seeded initial fictional provider roster upon migration.
- Validated via `test_schema_v16_to_v17.py` and `test_mysql_preflight.py`.

---

## 3. Endpoints Implemented
- `GET /api/me/appointments` (Patient role)
- `POST /api/me/appointments/{id}/book` (Patient role)
- `POST /api/me/appointments/{id}/cancel` (Patient role)
- `GET /api/provider/appointments` (Provider role)
- `POST /api/provider/appointments/{id}/acknowledge` (Provider role)
- `POST /api/provider/appointments/{id}/attended` (Provider role)
- `GET /api/admin/providers` (Admin role)
- `PATCH /api/admin/providers/{id}` (Admin role)
- `GET /api/admin/escalations` (Admin role)

---

## 4. UI Integrations & Translations
- `PatientAppointmentsScreen.tsx`: Real appointments list, offered booking slot selector, booked status, cancel button, bilingual English & Urdu.
- `RiskResultScreen.tsx`: Yellow routine booking recommendation card; Red care team alerted urgent card with provider details.
- `AppointmentSchedulingScreen.tsx`: Provider live queue with urgency badge, specialty, slot, acknowledge & mark attended actions.
- `AdminDashboardScreen.tsx`: Synthetic provider directory availability toggle switches; active escalation timeout alerts.
- `app/translations/index.ts`: Full English and Urdu translations for all appointment, status, specialty, and escalation keys.

---

## 5. Verification & Acceptance
- **Acceptance Check**: `LA-25` implemented in `scripts/local_acceptance.py`. Result: `PASS` (`specialties_ok=True; colour_to_action_ok=True; escalation_ok=True; http_ok=True`).
- **Promise Tracker**: `docs/PROMISE_TRACKER.md` updated Section 4 rows to `**PASS**`.
- **Backend Tests**: 37/37 tests passed across `test_schema_v16_to_v17.py` and `test_appointments.py` under both `direct` and `graph` orchestrator modes.
- **Frontend Tests**: 329/329 vitest tests passed (41 test files, including 7/7 in `tests/appointments.test.tsx`).
- **Static Verification**:
  - `npx tsc --noEmit`: 0 errors.
  - `npm run lint`: 0 warnings, 0 errors.
  - `ruff check`: All checks passed.
  - `npm run build`: Production build succeeded.
  - `test_traceability_links.py`: Passed.
- **Protected Files**: All 8 clinical safety files verified 100% byte-identical against pre-flight SHA-256 hashes.
