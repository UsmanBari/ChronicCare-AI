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

## Milestone 4: The Verification Agent

### Purpose & Architecture
Milestone 4 implements the deterministic, rule-based **Verification Agent** (`agents/verification_agent.py`).
Sitting directly on top of M3's Reconciliation Agent output (`ReconciliationResult`), the Verification Agent evaluates trust metadata and risk severity to decide whether a comparison can proceed automatically (`requires_human_review = False`) or requires human review (`requires_human_review = True`), assigning an auditable `review_reason` string.

> **Scope Clarification & Non-Clinical Boundary:**
> - The Verification Agent is **strictly rule-based** (zero LLM, ML, RAG, or agent frameworks).
> - It does **NOT** perform conflict resolution (never picks a winning value between sources).
> - It does **NOT** make clinical triage or care decisions (e.g. green/yellow/red routing, appointment scheduling).
> - It does **NOT** alter M2 normalized schemas or M3 reconciliation output — Verification only adds a judgment layer on top.

---

### Trust Level Assignment & Origin Handling
The Verification Agent assigns trust levels (`"high"`, `"medium"`, `"low"`) to data sources:
```python
TRUST_LEVELS = {
    "fhir_clinician_entered": "high",
    "local_clinician_entered": "high",
    "local_ocr_or_upload": "medium",
    "local_self_reported": "low",
}
```
- **Simplified POC Assignment Rule**: `source == "fhir"` -> `"high"` trust; `source == "local"` -> `"medium"` trust by default.
- **Fixture-Level Origin Tagging**: Optional origin tags (e.g. `"self_reported"` -> `"low"`) are mapped via fixture-level lookup dictionaries (`FIXTURE_ORIGINS`) without altering M2's `NormalizedObservation` or `NormalizedMedication` schema definitions.
- **Missing Side Nullability**: If `source` is `None` (missing record on one side), the corresponding `trust_level` for that side is strictly `None`.

---

### Severity & Review Decision Table
*(Illustrative POC rules only — explicitly NOT clinical guidance)*

1. `reconciliation_status == "agree"`:
   - Both trust levels present & at least one is NOT `"low"` -> severity `"none"`, `requires_human_review = False` (auto-resolved).
   - Both trust levels present & BOTH are `"low"` -> severity `"low"`, `requires_human_review = True` (reason: "agreement only between low-trust sources").

2. `reconciliation_status == "conflict"`:
   - **Observations**:
     - `delta` within 1x–2x M3 threshold -> severity `"moderate"`, `requires_human_review = True`.
     - `delta` exceeding 2x threshold -> severity `"high"`, `requires_human_review = True`.
   - **Medications**:
     - Status conflict involving `"active"` vs `"stopped"` -> severity `"high"`, `requires_human_review = True`.
     - Other status/dosage mismatch -> severity `"moderate"`, `requires_human_review = True`.

3. `reconciliation_status in ("missing_in_a", "missing_in_b")`:
   - Present side is `"high"` trust -> severity `"low"`, `requires_human_review = False` (auto-resolved path for high-trust single-source data).
   - Present side is `"medium"` or `"low"` trust -> severity `"moderate"`, `requires_human_review = True`.

4. `reconciliation_status == "insufficient_data"`:
   - Severity `"moderate"` unconditionally, `requires_human_review = True`.

---

### What M1–M5 Together Prove / Do Not Prove

- **What It Proves**: M1–M5 demonstrate that a deterministic, trust-aware Reconciliation → Verification pipeline can ingest multi-source EHR/local patient data, identify data conflicts, preserve full record provenance end-to-end, prioritize risk severity, distinguish auto-resolvable missing-data from review-required missing-data based on present-side trust, explicitly track trust metadata, and produce defense-ready structured evidence traces.
- **What It Does NOT Prove**: M1–M5 do **NOT** prove clinical validity or medical safety, do **NOT** constitute a certified medical device, and relied on synthetic/hand-authored test fixtures rather than a live matched real-patient clinical dataset.

---

## Milestone 5: Scenarios, Evidence, and Defense Writeup

### Status: **ALL 5 MILESTONES COMPLETE (M1–M5)**

Milestone 5 exercises the end-to-end pipeline against the committed defense scenario set, captures full structured evidence traces, and establishes the formal FYP proposal defense document (`POC_RESULTS.md`).

---

### Artifacts & Deliverables
- **Scenario Execution Runner**: `scenarios/run_all_scenarios.py`
- **Structured JSON Evidence Trace**: `output/scenario_evidence.json`
- **Presentation-Ready Readable Evidence**: `output/scenario_evidence_readable.md`
- **Defense Writeup & Results**: `POC_RESULTS.md`

---

### Defense Scenario Set
1. **Scenario 1 — Clean/Connected (All High-Trust)**: Both sources agree within thresholds; local records explicitly tagged `local_clinician_entered` (high trust). Outcome: 100% eligible for automatic resolution (0 review required).
2. **Scenario 2 — Conflicting Observation**: Glucose (115 vs 175 mg/dL) & HbA1c (6.4 vs 8.1%) disagree beyond 2x threshold. Outcome: severity `"high"`, review required with delta-driven reason.
3. **Scenario 3 — Missing Medication Record (2 Subcases)**:
   - **3A**: Present side high-trust (`fhir`) $\rightarrow$ severity `"low"`, `requires_human_review = False` (auto-resolved).
   - **3B**: Present side low-trust (`local_self_reported`) $\rightarrow$ severity `"moderate"`, `requires_human_review = True`.
   - *Demonstrates that present-side trust level dictates auto-resolution vs. human review.*
4. **Scenario 4 — Trust Metadata in Conflict Cases (2 Subcases)**:
   - **4A**: Both sides high-trust (`trust_a = "high"`, `trust_b = "high"`).
   - **4B**: Side B low-trust (`trust_a = "high"`, `trust_b = "low"`).
   - *Demonstrates trust metadata is explicitly tracked per comparison without altering delta-driven observation severity.*
5. **Adversarial Stress-Test Scenario C1 (Separate)**: Mismatched dosage strings (`"1 tablet twice daily"` vs `"2 tablets once daily"`). Outcome: severity `"moderate"`, review required. Narrow claim: string mismatch detection, not semantic dosage parsing.

---

### Reproducibility Guarantee
Executing `python scenarios/run_all_scenarios.py` twice against the fixed repository fixtures produces **100% identical, deterministic scenario outcomes and evidence traces**.

---

### How to Run All Scenarios & Verifications

```bash
# Execute full pipeline (Regression check + 4 Defense Scenarios + Adversarial C1 + Evidence Generation)
python scenarios/run_all_scenarios.py
```

#### Individual Verification Commands
```bash
python verify_m4.py
python verify_m3.py
python verify_m2.py
python verify_m1.py
```

---

### System Requirements & Setup
- **Python Version**: Python 3.9+
- **Dependencies**: `requests`, `python-dotenv`

```bash
pip install -r requirements.txt
python scenarios/run_all_scenarios.py
```
