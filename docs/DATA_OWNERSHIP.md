# Data Ownership & EHR Integration Architecture

This document formalizes the data ownership, synchronization boundaries, mode derivation, and conflict resolution model for ChronicCare AI.

---

## 1. Core Architectural Principles

### 1.1 Registered EHR Connection Model
- ChronicCare AI maintains an internal registry of trusted Electronic Health Record (EHR) systems (`ehr_systems` table).
- A patient account may link to at most **one** external patient record in **one** registered EHR system.
- An external patient identifier within a given EHR system may be actively linked to at most **one** user account (enforced via database uniqueness and code invariants, returning `409 Conflict` on collision).
- **Zero Client-Supplied URLs (SSRF Prevention):** The FHIR base URL is resolved strictly on the backend from the registry database. Clients can never supply FHIR endpoints or base URLs.
- **Privacy & Least Privilege:** No patient names, dates of birth, or clinical records are persisted during the link step. Only the external identifier is stored, and audit logs mask external IDs to their last 4 characters (`...XXXX`).

### 1.2 Mode Derivation
- Operational mode is **strictly derived** by backend business logic, never client-supplied:
  - **`connected` mode:** The patient account has a verified, active EHR connection record.
  - **`isolated` mode:** No active EHR connection exists (or the connection was revoked/failed).
- Patients can freely disconnect at any time via `DELETE /api/ehr/connection`, instantly transitioning their account to `isolated` mode.

### 1.3 System of Record & Synchronization Boundaries
- **Connected Mode:**
  - The external EHR system is the **authoritative System of Record (SoR)**.
  - ChronicCare AI queries the EHR FHIR R4 endpoint fresh during each clinical check-in.
  - ChronicCare AI **never mirrors** the EHR database into local persistent tables and **never writes back** data to the EHR in this phase (write-back is future work).
  - When clinicians modify medications or add observations in the EHR, these changes are retrieved during the patient's next check-in and surfaced via the deterministic Reconciliation and Verification agents as reconciliation conflicts.
- **Isolated Mode:**
  - The Local Store (SQLite/MySQL database) acts as the local system of record.
  - All observations, measurements, and medication entries recorded directly by the patient are explicitly tagged with provenance `source = 'local'` and `status = 'self_reported'`.

### 1.4 Prototype Limitations & Future Security Roadmaps
- **Observation Comparison Window:** Algorithmic reconciliation compares clinical observations only within a 48-hour window of each other. Older baseline readings are preserved as historical records for long-term multi-day trend analysis, but will not be matched against today's check-in observations.
- **Allergies Invariant:** Patient allergies can be recorded, edited, and retrieved via the patient record API; however, allergies are not yet evaluated by the algorithmic reconciliation engine in this phase.
- **Prototype Limitation:** In this technical prototype, entering an EHR external patient ID verifies that the record exists on the FHIR server, but does not cryptographically prove that the authenticated user *is* that specific patient.
- **Production Roadmap:** A clinical production deployment requires **SMART on FHIR OAuth 2.0 Patient Launch** (or Provider EHR Launch) with PKCE and OpenID Connect identity assertion tokens. The current prototype is validated strictly against synthetic patients (e.g., SMART Health IT Sandbox).

---

## 2. Data Ownership Matrix

| Data Item | Authoritative Owner | Storage Location | Authorized Mutators | Conflict Resolution Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **User Identity & Role** | Identity Provider & System Admin | Firebase Auth / `users` table | User (credentials), System Admin (role) | Admin assignment overrides default demo mapping. |
| **Patient Profile & Consent** | Patient | `patient_profiles` table | Patient (explicit self-service) | Last explicit update wins; revoking consent halts future automated check-ins without purging historical escalations. |
| **EHR System Registry** | System Administrator | `ehr_systems` table | System Administrator | Registry configuration is static and authoritative. |
| **EHR Active Linkage** | Patient | `ehr_connections` table | Patient (connect / revoke) | At most one active link per user. Duplicate links across users rejected with `409 Conflict`. |
| **Clinical Record (Connected Mode)** | External EHR / Clinician | External EHR (retrieved on-demand via FHIR R4) | Licensed Clinical Providers via EHR | Surfaced as reconciliation delta (`discrepancy` or `missing_in_checkin`) and flagged for provider verification. EHR values treated as authoritative clinical history. |
| **Clinical Record (Isolated Mode)** | Patient | Local Store database (`normalized_observations`, `normalized_medications`) | Patient (manual entry) | Self-reported entries are tagged `source='local'` and tracked chronologically. |
| **Reconciliation & Verification Results** | Deterministic Reconciliation & Verification Engines | Ephemeral / Check-in Session State | Algorithmic Rules (No LLM in verification loop) | High-severity discrepancies trigger clinician review escalations. |
| **Audit Logs** | System (Compliance Auditor) | Append-Only `audit_log` table | System Backend Only (Immutable) | Append-only invariant; no update or delete operations allowed. |

---

## 3. Consent Lifecycle & Audit Governance

- **Explicit Grant:** Connecting an EHR requires prior active consent (`consent_granted_at` is non-null and `consent_revoked_at` is null). Attempting to connect without consent returns `403 Forbidden`.
- **Revocation Safety (SRS FR-2):** Revoking consent immediately halts new automated check-ins and EHR verifications. However, per clinical safety requirements (SRS FR-2), previously generated clinician escalations and immutable audit records are preserved for clinical continuity and medico-legal auditing.
- **Privacy Assurance:** Audit logs record event metadata (actor, action, timestamp, outcome) without logging PHI, access tokens, credentials, or unmasked patient IDs.
