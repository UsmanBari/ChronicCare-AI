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

## Directory Structure

```text
backend-poc-technical/
├── agents/
│   ├── reconciliation_agent.py      # Core data reconciliation and conflict detection logic
│   └── verification_agent.py        # Clinical consistency and safety threshold verification
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
├── requirements.txt                 # Python dependencies (requests, pydantic, sqlite3)
└── init_local_db.py                 # SQLite database initialization script
```

---

## Running the PoC Verification Tests

### Prerequisites
- Python 3.10+
- `pip`

### Execution
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize local test database
python init_local_db.py

# 3. Execute all technical scenarios and verification suites
python scenarios/run_all_scenarios.py
```
