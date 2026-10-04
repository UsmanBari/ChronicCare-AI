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

All check-in sessions live on the server; patient identity and connection mode are derived server-side.

```bash
# Start a new check-in session (auto-abandons any prior in-progress session)
curl -X POST http://localhost:8000/api/checkins/start \
  -H "Authorization: Bearer <PATIENT_TOKEN>"

# Advance interview state with patient response (max 1000 characters)
curl -X POST http://localhost:8000/api/checkins/<CHECKIN_ID>/answer \
  -H "Authorization: Bearer <PATIENT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"answer": "142 mg/dL fasting"}'

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
