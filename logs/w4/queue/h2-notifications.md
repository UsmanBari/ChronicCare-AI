# Queue Task Report: H2 — In-App Notification Centre & FCM Web Push

- **Task ID**: `h2-notifications`
- **Branch**: `feat/i4-notifications` (STACKED ON `feat/i4-appointments`)
- **PR Title**: `I4-H: in-app notification centre + FCM web push (reminders, urgent alerts, escalation)`
- **Author**: Hassaan (AI Assistant)
- **Date**: 2026-11-12
- **Status**: COMPLETED

---

## 1. Commitments Delivered (Proposal Sec 13.2, 15, 35, 37)

1. **Zero-PHI Lock Screen Guard (Proposal Section 37)**:
   - Built strict `validate_no_health_values` guard ensuring notification titles and bodies NEVER contain blood pressure readings (e.g. `140/90`, `120 / 80`) or blood glucose values/units (e.g. `250 mg/dL`, `mmol/L`, `HbA1c`).
   - Implemented defensive client-side (`NotificationBell.tsx`) and service worker (`firebase-messaging-sw.js`) sanitization fallbacks to protect against lock screen privacy leaks.

2. **Four Trigger Classes**:
   - `urgent_checkin`: Urgent or emergency check-in creates alert for assigned provider (`"Urgent check-in from <Patient Name> requires clinical review"`). Exactly 1 notification per `checkin_id`.
   - `escalation_renotify`: 2h unacknowledged urgent case sends re-notification to provider.
   - `escalation_admin_flag`: 24h unacknowledged urgent case flags alert to system admin.
   - `daily_reminder`: Patients with no check-in logged after 18:00 local receive evening reminder (`"Please log your evening health check-in today"`). Suppressed if check-in already logged today; idempotent per calendar day.

3. **Database Schema v18**:
   - Added tables `notifications` and `fcm_tokens` with `VARCHAR(191)` ID contract across SQLite and MySQL.
   - Indexed on `(user_id, is_read)` and `user_id`.

4. **FCM Web Push & Service Worker**:
   - Protected behind `FCM_ENABLED=false` flag with graceful fallback when `GOOGLE_APPLICATION_CREDENTIALS` is absent.
   - Implemented `public/firebase-messaging-sw.js` service worker handling background push and navigation click events.
   - Explicit user opt-in only (no permission prompts on mount; requested strictly on button click).

5. **FastAPI Lifespan Reminder Runner**:
   - Integrated `reminder_worker_loop` running on 15-minute intervals when `REMINDERS_ENABLED=true`, cancelled cleanly on shutdown.
   - On-demand dispatch in `GET /api/me/notifications` ensures reminders are visible even without background workers or push permissions.

6. **Truthful Emergency Screen (N4 Compliance)**:
   - Conditioned `"Your care provider has been alerted"` strictly on `escalationRecorded === true`.
   - Truthfully renders `"Your check-in has been sent to your care team's review list"` when unescalated.
   - Fully localized in English and Urdu.

7. **Frontend In-App Notification Center**:
   - Built accessible `NotificationBell` component with unread badge counter, popup dropdown list, mark-read, and mark-all-read controls.
   - Mounted in desktop header and mobile drawer across Patient, Provider, and Admin portals.

8. **Local Acceptance (LA-29)**:
   - Implemented `run_la_29` in `scripts/local_acceptance.py` passing locally with full evidence:
     `urgent_ok=True; reminder_ok=True; guard_ok=True; fcm_dormant=True; idempotent_ok=True`.

---

## 2. Schema Migration v17 -> v18
- Updated `LATEST_SCHEMA_VERSION = 18` in `data_sources/app_store.py`.
- Added tables `notifications` and `fcm_tokens` for both SQLite and MySQL.
- Enforced MySQL hotfix width contract (`VARCHAR(191)` on all ID columns).
- Validated via `test_schema_v17_to_v18.py`, `test_mysql_preflight.py`, and `test_mysql_id_width_contract.py`.

---

## 3. Endpoints Implemented
- `GET /api/me/notifications` (Patient role)
- `POST /api/me/notifications/{id}/read` (Patient role)
- `POST /api/me/notifications/read-all` (Patient role)
- `POST /api/me/fcm-token` (Patient role)
- `DELETE /api/me/fcm-token` (Patient role)
- `GET /api/provider/notifications` (Provider role)
- `POST /api/provider/notifications/{id}/read` (Provider role)
- `GET /api/admin/notifications` (Admin role)
- `POST /api/admin/notifications/{id}/read` (Admin role)

---

## 4. Verification Evidence
- **Backend Pytest**: 71 passed in 5.35s (including `test_schema_v17_to_v18.py` [6 tests], `test_notifications.py` [12 tests], `test_appointments.py` [32 tests]).
- **Frontend Vitest**: 337 passed across 42 files (including `tests/notifications.test.tsx` [8 tests]).
- **TypeScript**: `npx tsc --noEmit` exited 0 (clean, zero errors).
- **ESLint**: `npm run lint` clean (0 warnings/errors).
- **Next.js Build**: `npm run build` clean static export.
- **Ruff**: `ruff check` clean on `backend-poc-technical` and `scripts`.
- **Protected Files Integrity**: All 8 protected clinical safety files remain 100% byte-for-byte identical (SHA-256 hashes matched).
