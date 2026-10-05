# ChronicCare AI — Technical Proof of Concept (Reconciliation & Verification)

> **Algorithmic Validation of Multi-Source Clinical Data Reconciliation and Consistency Verification**

---

## Overview

This directory contains the original **backend technical proof of concept (PoC)** for ChronicCare AI. It implements and validates the system's foundational computational mechanisms:

1. **Deterministic Data Reconciliation**: Cross-matching patient self-reported observations against electronic health record (EHR) telemetry to detect, categorize, and flag discrepancies (e.g. self-reported glucose elevation vs. clinical lab records).
2. **Clinical Consistency Verification Protocol**: A deterministic verification pipeline that evaluates clinical safety constraints, missing data flags, and threshold conflicts without relying on probabilistic or non-deterministic LLM outputs.
3. **Dual Data-Source Adapters**:
   - **HL7® FHIR® Adapter**: Client integration for querying synthetic FHIR R4 server endpoints (HAPI FHIR public testbed).
   - **Local SQLite Adapter**: Isolated offline data store matching the exact schema and interface contract of the FHIR layer.
4. **Source-Blind Verification**: Validation tests confirming that verification and reconciliation logic executes identically regardless of whether the underlying data source is FHIR or the local offline store.

---

## Technical Scope

- **Deterministic Python Core**: Pure algorithmic logic implementing reconciliation matrices, threshold checks, confidence scoring, and structured discrepancy reporting.
- **No LLM/ML Dependencies**: Built deliberately without probabilistic language models or machine learning dependencies to prove the feasibility and safety of the foundational reconciliation algorithms.
- **Pre-Validated Foundation**: This technical PoC was executed, verified, and benchmarked prior to developing the multi-portal frontend user interface prototype located in the repository root.

---

## FastAPI Backend Service

> **Note**: The FastAPI backend application (`main.py`) exposing `/api/reconcile`, `/api/verify`, and `/api/health` was introduced as part of the backend API scaffolding sprint. The core algorithmic reconciliation and verification agents (`reconciliation_agent.py` and `verification_agent.py`) remain completely unchanged from the validated technical proof-of-concept.

---

## Directory Structure

```text
backend-poc-technical/
├── main.py                          # FastAPI backend application exposing REST API endpoints
├── test_main.py                     # API test suite for FastAPI endpoints
├── init_local_db.py                 # SQLite database initialization script
├── test_fhir.py                     # FHIR server connectivity validation script
├── agents/
│   ├── reconciliation_agent.py      # Core data reconciliation and conflict detection logic (unchanged)
│   └── verification_agent.py        # Clinical consistency and safety threshold verification (unchanged)
├── data_sources/
│   ├── data_source.py               # Abstract DataSource interface definition
│   ├── fhir_adapter.py              # FHIR R4 resource adapter (Patient, Observation, Condition)
│   ├── fhir_client.py               # HTTP client communicating with FHIR servers
│   ├── local_adapter.py             # SQLite data source adapter
│   ├── local_store.py               # SQLite schema definition and CRUD operations
│   └── models.py                    # Unified Pydantic / dataclass clinical entities
├── scenarios/
│   ├── fixtures.py                  # Seeded test fixtures for clinical discrepancy scenarios
│   ├── run_all_scenarios.py         # Test orchestrator executing all verification benchmarks
│   ├── test_reconciliation.py       # Unit tests for multi-source reconciliation
│   ├── test_source_blind.py         # Verification that FHIR and Local Store yield identical logic
│   └── test_verification.py         # Clinical threshold and safety constraint tests
├── output/
│   ├── fhir_connectivity.json       # Telemetry log from live FHIR testbed handshake
│   ├── scenario_evidence.json       # JSON execution log of all scenario outcomes
│   └── scenario_evidence_readable.md# Formatted clinical report of reconciliation runs
├── POC_RESULTS.md                   # Detailed validation summary and benchmark results
├── requirements.txt                 # Python dependencies (fastapi, uvicorn, requests, pydantic, pytest)
└── README.md                        # Technical PoC documentation
```

---

## API Endpoints & Usage

### 1. Patient Profile, Consent & EHR Connection

```bash
# Register or authenticate session
curl -X POST http://localhost:8000/api/auth/session \
  -H "Authorization: Bearer <FIREBASE_ID_TOKEN>"

# Grant patient consent (required before check-ins or EHR connection)
curl -X POST http://localhost:8000/api/me/consent \
  -H "Authorization: Bearer <PATIENT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"granted": true}'

# Update patient clinical profile
curl -X PUT http://localhost:8000/api/me/profile \
  -H "Authorization: Bearer <PATIENT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"conditions": ["diabetes", "hypertension"], "on_insulin_or_sulfonylurea": false, "language": "en"}'

# Connect external EHR system (transitions from Isolated to Connected mode)
curl -X POST http://localhost:8000/api/ehr/connect \
  -H "Authorization: Bearer <PATIENT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"ehr_system_id": "smart-sandbox", "external_patient_id": "smart-1088792"}'
```

### 2. Authenticated Patient Check-In Pipeline

All check-in sessions live on the server; patient identity, consent, and connection mode are derived server-side.

#### Request & Response Enhancements (Stage 7A Hardening)
- **State & Optimistic Locking**:
  - `POST /api/checkins/start` returns `step` (current interview step string, e.g. `"greeting"`) and `version` (integer starting at 0).
  - **Start Idempotency**: If a patient repeats or double-clicks start within 15 minutes and has given 0 answers, the server re-uses the existing in-progress check-in rather than abandoning it.
  - `POST /api/checkins/<CHECKIN_ID>/answer` accepts an optional `step: str`.
  - **409 Conflict Semantics**:
    - `{"detail": "stale_step", "step": <current_step>, "question": <current_question>}`: returned if client submits an answer with a `step` that does not match the server's current state step.
    - `{"detail": "concurrent_update"}`: returned if concurrent requests attempt to mutate the same check-in version (optimistic lock rejection).
  - **Atomic Emergency Persistence**:
    - When an emergency trigger (red-flag keyword or Stage 1 dangerous BP reading) is detected during `/answer`, the session status is immediately set to `emergency`, the `checkin_results` row is created, and an immutable `emergency_escalated` audit row is written within the same database transaction.
    - Response contains `complete: true`, `emergency: true`, `emergency_reason: "<category>"`, and `escalation_recorded: true`.
    - `POST /api/checkins/<CHECKIN_ID>/complete` is completely idempotent if called after an emergency.

#### Stage 1 Dangerous Blood Pressure Screening Rule
Under Proposal Section 27 and the AHA hypertensive-crisis benchmark, blood pressure readings at or above crisis range immediately halt the interview:
- `DANGEROUS_BP_SYSTOLIC_MMHG = 180` (systolic >= 180 mmHg)
- `DANGEROUS_BP_DIASTOLIC_MMHG = 120` (diastolic >= 120 mmHg)
- Trigger category: `bp_crisis_range` with `trigger_reading: {"systolic": ..., "diastolic": ..., "unit": "mmHg"}` exposed directly in the provider review queue.

```bash
# Start a new check-in session (idempotent for un-answered sessions <= 15m)
curl -X POST http://localhost:8000/api/checkins/start \
  -H "Authorization: Bearer <PATIENT_TOKEN>"

# Advance interview state with patient response and optional step (max 1000 characters)
curl -X POST http://localhost:8000/api/checkins/<CHECKIN_ID>/answer \
  -H "Authorization: Bearer <PATIENT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"answer": "142 mg/dL fasting", "step": "glucose_reading"}'

# Complete check-in, execute deterministic reconciliation & verification
curl -X POST http://localhost:8000/api/checkins/<CHECKIN_ID>/complete \
  -H "Authorization: Bearer <PATIENT_TOKEN>"

# List authenticated patient's historical check-ins (limit 20, newest first)
curl -X GET http://localhost:8000/api/checkins \
  -H "Authorization: Bearer <PATIENT_TOKEN>"

# Get detailed result and conversation state for a specific check-in
curl -X GET http://localhost:8000/api/checkins/<CHECKIN_ID> \
  -H "Authorization: Bearer <PATIENT_TOKEN>"
```

### 3. Provider Clinical Review Queue & Actions

```bash
# Query provider review queue (ordered: emergency desc -> severity desc -> created_at asc)
curl -X GET "http://localhost:8000/api/provider/review-queue?status=open" \
  -H "Authorization: Bearer <PROVIDER_TOKEN>"

# View complete clinical intake, reconciliation comparisons, and verification details
curl -X GET http://localhost:8000/api/provider/review/<CHECKIN_ID> \
  -H "Authorization: Bearer <PROVIDER_TOKEN>"

# Record clinical action (acknowledge | resolve | escalate) with optional note (max 500 chars)
curl -X POST http://localhost:8000/api/provider/review/<CHECKIN_ID>/action \
  -H "Authorization: Bearer <PROVIDER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"action": "resolve", "note": "Contacted patient; confirmed insulin dosage adjustment."}'
```

### Prototype Limitations & Future Work
- **Observation Comparison Window:** Reconciliation matches observations only if they occur within 48 hours of each other. Older baseline readings are stored for longitudinal history/trends, but will not pair with today's observations. Medications have no temporal cutoff.
- **Allergies Invariant:** Allergies are persisted and retrieved in isolated mode, but are not yet evaluated by the algorithmic reconciliation engine.
- **Care-Team Assignment**: In this prototype, any authenticated provider can view and act on all patient review queue items. Production deployments require fine-grained patient panel assignment and care-team routing.
- **Secondary Notifications**: Critical alerts (emergencies and overdue high-severity reviews) are flagged in the queue dynamically (items older than 2 hours marked `overdue=true`). Out-of-band notifications (e.g. SMS, pager integration) represent future roadmap work.
- **No Risk Scoring**: As per clinical decision-support safety requirements, the system produces no probabilistic risk scores or unsolicited clinical recommendations; responses contain only deterministic computational reconciliations.

---

## Running the PoC Verification Tests

### Prerequisites
- Python 3.10+
- `pip`

### Execution
```bash
# 1. Install dependencies
pip install -r backend-poc-technical/requirements.txt

# 2. Initialize local test database
python backend-poc-technical/init_local_db.py

# 3. Execute hermetic test suite
pytest backend-poc-technical/ -v -k "not run_source_blind_test"
```

---

## MySQL (Aiven)

The backend supports dual database backends: SQLite (default for local development and hermetic CI testing) and Aiven MySQL for cloud persistence across the Local Store and Application Store.

### Environment Variables
- `DB_BACKEND`: Set to `mysql` to use MySQL. If unset or set to `sqlite`, SQLite is used.
- `MYSQL_URL`: Connection string in the format `mysql://<user>:<password>@<host>:<port>/<dbname>?ssl-mode=REQUIRED`.
- `MYSQL_SSL_CA`: (Optional) Absolute or relative path to the CA bundle. Defaults to `certs/aiven-ca.pem`.

### Safety Rules & Guardrails
- **Database Safety Guardrail (`_dev` suffix)**: Destructive schema resets (`--reset` via `init_local_db.py`) and live integration test suites strictly refuse execution unless the target database name ends with `_dev` (e.g., `chroniccare_dev`). This prevents accidental mutation or truncation of staging or production databases.
- **Connection Checks**: The connection script `scripts/check_mysql_connection.py` prints only the server version and connected database name, never exposing credentials or hostnames.

### Running Live Opt-in MySQL Tests
Live database tests are gated and opt-in:
```bash
# Verify connection
python backend-poc-technical/scripts/check_mysql_connection.py

# Initialize and seed MySQL database
python backend-poc-technical/init_local_db.py --backend mysql --reset

# Run opt-in MySQL test suite (requires RUN_MYSQL_TESTS=1 and a _dev database)
RUN_MYSQL_TESTS=1 pytest backend-poc-technical/test_mysql_store.py backend-poc-technical/test_mysql_app_store.py -v
```

> **Note on PR #2 (`feat/mysql-local-store`)**:
> PR #2 introduced the original MySQL Local Store integration. This work has now been fully reconciled across both the Local Store and the complete App Store (`app_store.py`) with unified migrations, TLS support, and safety guardrails. PR #2 can now be closed as superseded.

