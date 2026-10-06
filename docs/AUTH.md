# Server-Side Authentication & Authorization Architecture

## Overview
ChronicCare AI enforces server-side identity verification using Firebase ID tokens and server-managed role definitions. The frontend cannot grant privileges; all permissions and authorization checks originate strictly from the backend database (`users` table).

---

## Token Verification Flow (Text Sequence)

```text
[ Client (Browser) ]                 [ Backend (FastAPI) ]              [ Google Public Keys ]
         |                                     |                                   |
         | --- 1. POST /api/auth/session ----> |                                   |
         |    (Bearer <Firebase_ID_Token>)     |                                   |
         |                                     | --- 2. Check cached x509 certs -> |
         |                                     |    (Fetch if kid missing/expired) |
         |                                     | <--- Return public certs ---------|
         |                                     |
         |                                     | --- 3. Verify RS256 signature,
         |                                     |        aud=FIREBASE_PROJECT_ID,
         |                                     |        iss=https://securetoken.google.com/<ID>,
         |                                     |        sub non-empty, exp/iat valid.
         |                                     |
         |                                     | --- 4. Query `users` database table:
         |                                     |        - If user missing: register with role
         |                                     |          from DEMO_ROLE_MAP or default 'patient'
         |                                     |        - If user exists: update last_login_at
         |                                     |
         |                                     | --- 5. Write append-only audit row:
         |                                     |        (action: user_registered | login)
         |                                     |
         | <--- 6. Return session JSON --------|
         |     {user_id, email, role, status}  |
```

---

## Roles & Access Control

Roles are stored in the `users` table and enforced via the backend `require_role(...)` dependency:

| Role | Description | Capabilities |
| :--- | :--- | :--- |
| **`patient`** | Default self-registered role | Accesses own check-in sessions, clinical reconciliation, profile `/api/me`. |
| **`provider`** | Clinical care provider | Accesses clinical verification reviews, patient records, reconciliation tools. |
| **`admin`** | Administrative operator | Can change user roles (`/api/admin/users/{id}/role`) and view audit logs (`/api/admin/audit`). Cannot alter their own role. |

---

## Route Authorization Matrix

| Endpoint | Method | Required Role | Public / Auth |
| :--- | :--- | :--- | :--- |
| `/api/health` | GET | None | **Public** |
| `/api/ehr/systems` | GET | None | **Public** |
| `/api/auth/session` | POST | Any valid token | Authenticated |
| `/api/me` | GET | Any active user | Authenticated |
| `/api/profile` | GET / PUT | `patient` | Authenticated |
| `/api/consent` | GET / POST | `patient` | Authenticated |
| `/api/ehr/connect` | POST | `patient` | Authenticated |
| `/api/ehr/connection` | GET | Any active user | Authenticated |
| `/api/ehr/connection` | DELETE | `patient` | Authenticated |
| `/api/checkin/start` | POST | `patient` | Authenticated |
| `/api/checkin/{session_id}/step` | POST | `patient` | Authenticated |
| `/api/checkin/{session_id}/complete` | POST | `patient` | Authenticated |
| `/api/checkin/history` | GET | `patient` | Authenticated |
| `/api/checkin/{checkin_id}` | GET | `patient` | Authenticated |
| `/api/reviews/queue` | GET | `provider` | Authenticated |
| `/api/reviews/{checkin_id}` | GET | `provider` | Authenticated |
| `/api/reviews/{checkin_id}/action` | POST | `provider` | Authenticated |
| `/api/reconcile` | POST | `provider` or `admin` | Authenticated |
| `/api/verify` | POST | `provider` or `admin` | Authenticated |
| `/api/llm/health` | GET | `admin` | Authenticated |
| `/api/admin/users/{user_id}/role` | POST | `admin` | Authenticated |
| `/api/admin/audit` | GET | `admin` | Authenticated |

---

## Configuration Variables

| Variable Name | Required | Description |
| :--- | :--- | :--- |
| `FIREBASE_PROJECT_ID` | **Yes** | Firebase project identifier for JWT audience (`aud`) and issuer (`iss`) validation. If unset, backend protected endpoints fail closed with HTTP 503. |
| `DEMO_ROLE_MAP` | No | Comma-delimited mapping (`email:role,email:role`) used to seed initial provider or admin accounts during first sign-in. Ignored if malformed. |
| `LOCAL_DB_PATH` | No | SQLite database file path (defaults to `local_store.db`). |
| `DB_BACKEND` | No | `sqlite` (default) or `mysql`. |

---

## Audit Logging & Privacy Guarantees

All authentication events, role escalations, and permission denials are appended to `audit_log`:
- **Immutable**: The data layer exposes `append_audit(...)` and read helpers only. No update or delete operations exist.
- **Privacy & Redaction**: Audit detail JSON records events without storing bearer tokens, password hashes, or Protected Health Information (PHI).

---

## Known Limitations

1. **Email Verification**: Token claims include `email_verified`, but email verification is not strictly enforced at the gate.
2. **Multi-Factor Authentication (MFA)**: MFA enforcement is delegated to Firebase client policy and is not evaluated independently by backend claims.
3. **Rate Limiting**: Rate limiting for authentication and token validation requests is currently managed at the reverse proxy / gateway level.
4. **Provider / Admin Creation**: Providers and admins are created exclusively through predefined configuration (`DEMO_ROLE_MAP`) or explicit elevation by an existing administrator.
