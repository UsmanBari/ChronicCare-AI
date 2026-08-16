# ChronicCare AI - Proof of Concept (POC)

## Project Overview & Scope
ChronicCare AI is a clinical decision-support system POC testing a trust-aware **Reconciliation → Verification** pipeline across two distinct data-source modes:
1. **Connected Mode**: External FHIR/EHR server (SMART Health IT Open R4 endpoint).
2. **Isolated Mode**: Local Store (SQLite database for offline/air-gapped synthetic patient records).

---

## Milestone 1: Environment & Data-Source Foundation
Establishes project scaffolding, verifies SMART Health IT R4 server reachability (`/metadata`), retrieves raw synthetic FHIR JSON, and initializes a local SQLite database for isolated synthetic patient records.

---

## Milestone 2: Data Source Abstraction Layer
Implements a source-agnostic **Data Source Abstraction Layer** (`data_sources/data_source.py`) exposing `get_patient_bundle(patient_id, mode)` which returns normalized patient, observation, and medication dataclass instances (`NormalizedPatient`, `NormalizedObservation`, `NormalizedMedication`). Proves structural and type equivalence across sources.

---

## Milestone 3: The Reconciliation Agent

### Purpose & Architecture
Milestone 3 implements the deterministic, rule-based **Reconciliation Agent** (`agents/reconciliation_agent.py`).
The Reconciliation Agent takes two normalized bundles (Connected Mode + Isolated Mode) asserted by the caller to represent the **SAME** real-world patient, and compares observations and medications to characterize agreement, conflict, missing data, or insufficient data.

> **Scope Clarification & Non-Clinical Boundary:**
> - The Reconciliation Agent is **strictly rule-based** (zero LLM, ML, or agent frameworks).
> - It characterizes agreement/disagreement only; it does **NOT** resolve conflicts, pick winners, assign trust/confidence scores, or flag items for human review (human review flagging belongs strictly to M4).
> - Matching windows and conflict thresholds are illustrative POC values, not clinical guidelines.

```text
                  Normalized Bundle A          Normalized Bundle B
                    (Connected Mode)            (Isolated Mode)
                           │                           │
                           └─────────────┬─────────────┘
                                         │
                                         ▼
                             reconcile_bundles()
                                         │
                       ┌─────────────────┼─────────────────┐
                       ▼                 ▼                 ▼
                   Step 1:            Step 2:           Step 3:
                   Matching        Classification     Result Building
                 (48h Window)     (Agree/Conflict)    (Full Provenance)
                                         │
                                         ▼
                                ReconciliationResult
```

---

### Patient Identity Contract Validation
Before performing any comparisons, `reconcile_bundles()` verifies that `bundle_a["patient"].patient_id == bundle_b["patient"].patient_id`. If the IDs differ, `reconcile_bundles()` immediately raises a `ValueError`.

> **Synthetic Test Fixtures Rationale (`scenarios/fixtures.py`):**
> Because the live FHIR sandbox patient (`768be7ac-...`) and local SQLite patients (`LOCAL-PATIENT-001`) represent different synthetic individuals, cross-source reconciliation testing uses hand-authored synthetic paired bundles sharing a common `patient_id`.

---

### Reconciliation Logic & Matching Rules

#### 1. Observation Matching & Classification Rules
- **Match Window**: `OBSERVATION_MATCH_WINDOW_HOURS = 48` (48 hours).
- **Matching Algorithm**: Deterministic, 1-to-1, nearest-neighbor matching by timestamp for identical `observation_type`. Each source record participates in at most one comparison.
- **Classification Statuses**:
  - `"agree"`: Matched pair where `abs(value_a - value_b) <= threshold`.
  - `"conflict"`: Matched pair where `abs(value_a - value_b) > threshold`.
  - `"missing_in_a"`: Record present in Bundle B, absent in Bundle A.
  - `"missing_in_b"`: Record present in Bundle A, absent in Bundle B.
  - `"insufficient_data"`: Matched pair within 48h window, but required value is `None` or non-numeric.

#### Illustrative Conflict Thresholds (`OBSERVATION_CONFLICT_THRESHOLDS`)
*(Note: Illustrative POC threshold values only — NOT clinical guidance)*
- `glucose`: 15.0 mg/dL
- `hba1c`: 0.5 %
- `blood_pressure_systolic`: 10.0 mmHg
- `blood_pressure_diastolic`: 10.0 mmHg
- `weight`: 2.0 kg

#### 2. Medication Matching & Classification Rules
- **Matching**: Matched by normalized medication name (`medication_name.strip().lower()`).
- **Classification Statuses**:
  - `"agree"`: Status and dosage match identically after whitespace/case normalization.
  - `"conflict"`: Medication names match, but status or dosage differ.
  - `"missing_in_a"`: Medication present in Bundle B, absent in Bundle A.
  - `"missing_in_b"`: Medication present in Bundle A, absent in Bundle B.

---

### Provenance Preservation
Every `ObservationComparison` and `MedicationComparison` retains full provenance fields:
- `source_a`, `source_record_id_a`, `timestamp_a`
- `source_b`, `source_record_id_b`, `timestamp_b`

---

### How to Run Verification & Tests

#### 1. Run Reconciliation Acceptance Test
Executes `reconcile_bundles()` against all fixture pairs (Clean Agree, Conflict, Missing Data, Insufficient Data, Negative Control) and asserts identity contract validation:
```bash
python scenarios/test_reconciliation.py
```

#### 2. Run Milestone 3 Verification Suite
```bash
python verify_m3.py
```

#### 3. Run Milestone 2 Verification Suite (Regression Check)
```bash
python verify_m2.py
```

#### 4. Run Milestone 1 Verification Suite (Regression Check)
```bash
python verify_m1.py
```

---

### System Requirements & Setup
- **Python Version**: Python 3.9+
- **Dependencies**: `requests`, `python-dotenv`

```bash
pip install -r requirements.txt
python scenarios/test_reconciliation.py
python verify_m3.py
```
