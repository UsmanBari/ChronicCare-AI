# In-App Notification Centre & FCM Web Push Architecture (PR I4-H)

> **Traceability & Authority**
> - **Proposal Section 13.2 ("Notification Service")**: "Daily reminder and urgent alerts via Firebase Cloud Messaging."
> - **Proposal Section 15 ("Escalation Timeout")**: "Re-notify after 2 h, admin flag after 24 h."
> - **Proposal Section 35 ("Committed for Real Implementation")**: Lists Notification Service & FCM as committed deliverables for FYP-1.
> - **Proposal Section 37 ("Safety Invariants & Verification")**: Lock screen privacy: push notifications must NEVER display PHI (no BP or blood sugar readings).
> - **Local Acceptance**: `LA-29` in `scripts/local_acceptance.py`.

---

## 1. Safety Invariants & Privacy Protections

### Critical Privacy Rule: Zero PHI on Lock Screen
Push notifications and mobile lock screens are visible to third parties, caregivers, and bystanders without unlocking the device. Under HIPAA and Pakistan PMDC data privacy guidelines, clinical metrics must never be displayed in lock-screen alerts.

1. **Title & Body Scrubber (`validate_no_health_values`)**:
   - Every generated notification string is checked before insertion into the database or dispatch to FCM.
   - Any string matching blood pressure patterns (e.g. `140/90`, `120 / 80`) or blood glucose values/units (e.g. `250 mg/dL`, `8.5 mmol/L`, `HbA1c`, `blood sugar`) triggers an immediate `ValueError("PHI Guard Violation: ...")`.
2. **Generic, Safe Copy**:
   - Provider alerts use: `"Urgent check-in from <Patient Name> requires clinical review"`.
   - Patient daily reminders use: `"Please log your evening health check-in today"`.
   - Escalation alerts use: `"Case requires clinical acknowledgment (2h elapsed)"`.
3. **Frontend Defensive Fallback**:
   - In `app/components/NotificationBell.tsx`, an additional sanitization filter replaces any unexpected numbers with `"Clinical review required"`.
4. **Service Worker Fallback**:
   - In `public/firebase-messaging-sw.js`, push event data is intercepted and sanitized before calling `self.registration.showNotification()`.

---

## 2. Notification Triggers & Event Types

| Event Type | Target Role | Recipient | Trigger Event | Frequency / Idempotency Key |
|:---|:---:|:---:|:---|:---|
| `urgent_checkin` | Provider | Assigned Doctor | Check-in finishes with Red (Emergency) or Amber (Urgent) triage | Exactly 1 per `checkin_id` |
| `escalation_renotify` | Provider | Assigned Doctor | Urgent appointment remains unacknowledged for $\ge 2$ hours | Exactly 1 per appointment (transition to `re_notified`) |
| `escalation_admin_flag` | Admin | System Admin | Urgent appointment remains unacknowledged for $\ge 24$ hours | Exactly 1 per appointment (transition to `admin_flagged`) |
| `daily_reminder` | Patient | Active Patient | Hour $\ge$ 18:00 local, no check-in completed today | At most 1 per calendar day (`patient_id + YYYY-MM-DD`) |

---

## 3. Database Schema (Schema Version 18)

### Table `notifications`
```sql
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(191) PRIMARY KEY,
    user_id VARCHAR(191) NOT NULL,
    role VARCHAR(32) NOT NULL,
    type VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    reference_id VARCHAR(191),
    is_read BOOLEAN NOT NULL DEFAULT 0,
    created_at VARCHAR(64) NOT NULL,
    read_at VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read);
```

### Table `fcm_tokens`
```sql
CREATE TABLE IF NOT EXISTS fcm_tokens (
    token VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(191) NOT NULL,
    device_info VARCHAR(255),
    created_at VARCHAR(64) NOT NULL,
    updated_at VARCHAR(64) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fcm_tokens_user ON fcm_tokens(user_id);
```

---

## 4. FCM Web Push Integration

- **Environment Flag**: `FCM_ENABLED` (boolean, defaults to `false`).
- **Credentials Path**: `GOOGLE_APPLICATION_CREDENTIALS` (path to Firebase Service Account JSON).
- **Graceful Degradation**:
  - If `FCM_ENABLED=false`: `send_fcm_push()` logs debug and immediately returns `{"sent": 0, "status": "skipped", "reason": "FCM_DISABLED"}` without attempting any network call.
  - If `FCM_ENABLED=true` but `GOOGLE_APPLICATION_CREDENTIALS` is missing: logs a warning once and returns `{"sent": 0, "status": "skipped", "reason": "CREDENTIALS_MISSING"}`.
- **Client Opt-In**:
  - In `app/components/NotificationBell.tsx`, browser notification permission (`Notification.requestPermission()`) is requested **only** when the user explicitly clicks the "Enable browser alerts" button. It is never requested automatically upon page load.

---

## 5. Daily Reminder Timing & Lifespan Task

- **Environment Flag**: `REMINDERS_ENABLED` (boolean, defaults to `false`).
- **Reminder Hour**: `DEFAULT_REMINDER_HOUR` (integer, defaults to `18` [6:00 PM local Pakistan time]).
- **Timezone & Local Offset**:
  - `REMINDER_UTC_OFFSET_HOURS` (integer, defaults to `5` for Pakistan Standard Time, UTC+5; Pakistan observes no daylight saving).
  - Reminder evaluation (`is_patient_reminder_due`) compares local hour (`now_dt.astimezone(timezone(timedelta(hours=5))).hour >= 18`).
  - 18:00 PKT corresponds to 13:00 UTC (1:00 PM UTC). At 17:59 PKT (12:59 UTC) the reminder does not fire; at 18:00 PKT (13:00 UTC) the reminder fires.
  - "Today" (calendar date and midnight boundary for check-ins) is computed relative to Pakistan midnight (00:00:00 PKT = 19:00:00 UTC of previous day).
- **FastAPI Lifespan Integration**:
  - When `REMINDERS_ENABLED=true`, a background `asyncio` task runs on a 15-minute interval (`services.reminder_service.reminder_worker_loop`).
  - On application shutdown, the task is cancelled cleanly without leaking tasks or connections.
- **On-Demand Dispatch**:
  - When the patient navigates to the app and queries `GET /api/me/notifications`, due reminders are evaluated dynamically using local Pakistan time so users without push permissions still see in-app reminder badges immediately upon opening the app. Tests freeze or monkeypatch `get_now_utc` to ensure deterministic execution independent of the CI runner's wall-clock time.

---

## 6. Emergency Screen Clarification (N4 Compliance)

In `app/components/EmergencyScreen.tsx`:
- `"Your care provider has been alerted"` is rendered **only** when `escalationRecorded === true`.
- If `escalationRecorded` is `false` or missing, the screen truthfully renders: `"Your check-in has been sent to your care team's review list"`.
- Both strings are localized in English and Urdu (`app/translations/index.ts`).

---

## 7. Verification & Test Evidence

- **Unit Tests**:
  - `backend-poc-technical/test_schema_v17_to_v18.py`: 6 tests (schema migration, MySQL compatibility, CRUD operations).
  - `backend-poc-technical/test_notifications.py`: 12 tests (PHI lock screen guard, idempotency, role isolation, escalation milestones, daily reminder rules, dormant FCM).
  - `tests/notifications.test.tsx`: 8 tests (NotificationBell dropdown, unread count badge, mark-read, mark-all-read, PHI sanitization, EmergencyScreen conditional sentence).
- **Local Acceptance**:
  - `LA-29` passes with full evidence: `urgent_ok=True; reminder_ok=True; guard_ok=True; fcm_dormant=True; idempotent_ok=True`.
