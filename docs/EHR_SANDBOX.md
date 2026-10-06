# EHR Sandbox and Connected Mode Documentation

## 1. Overview & Connected Mode Architecture

In **Stage 7E**, ChronicCare AI implements a robust, clinically safe, and verifiable **Connected Mode** for Electronic Health Record (EHR) integration via HL7® FHIR® R4.

Connected Mode operates in two operational configurations:
1. **In-Process Simulated Hospital (`demo-hospital`)**: A fast, deterministic in-memory simulator (`sim://demo`) providing predictable clinical archetypes with relative timestamps.
2. **Public FHIR Sandbox (`public-sandbox`)**: A live connection to public FHIR R4 sandbox endpoints (primary: SMART Health IT `https://r4.smarthealthit.org`) using verified synthetic adult patient records.

```mermaid
flowchart TD
    subgraph Client [ChronicCare AI Frontend]
        ConnScreen[EHR Connection Screen]
        TestBtn[Test Connection Button]
    end

    subgraph Backend [FastAPI Backend]
        Router["/api/ehr/test & /api/ehr/connect"]
        ClientCore[Robust FHIR Client]
        Cache[(In-Memory 30s TTL Cache)]
        Adapter[FHIR Normalisation Adapter]
        MedScope[Medication Scope Filter]
    end

    subgraph EHR_Targets [EHR Record Providers]
        Sim[In-Process Simulated Hospital (demo-hospital)]
        Public[SMART Health IT FHIR R4 Sandbox (public-sandbox)]
    end

    ConnScreen -->|EHR System Selection| Router
    TestBtn -->|Metadata Latency Check| Router
    Router --> ClientCore
    ClientCore <--> Cache
    ClientCore -->|sim://*| Sim
    ClientCore -->|https://*| Public
    ClientCore --> Adapter
    Adapter --> MedScope
    MedScope -->|Scoped Bundle| Router
```

---

## 2. Public Sandbox Probe Results & Selection

A live probe script (`scripts/probe_fhir.py`) evaluated multiple candidate public FHIR R4 sandbox servers on key operational dimensions: uptime, latency, search capabilities, and synthetic adult data availability.

### Sandbox Evaluation Matrix

| Sandbox Server | Base URL | Version / Software | Probe Result | Latency | Evaluation & Decision |
|---|---|---|---|---|---|
| **SMART Health IT R4** | `https://r4.smarthealthit.org` | FHIR 4.0.0 (Smile CDR) | **Pass (HTTP 200)** | ~720ms | **Selected as Primary Public Sandbox.** Open access, reliable search, verified adult cohort with complete BP panels and active medication requests. |
| **HAPI FHIR Public R4** | `https://hapi.fhir.org/baseR4` | FHIR 4.0.1 (HAPI / JPA) | Variable (Rate-limited) | >2500ms | **Excluded as primary.** Frequent test timeouts, community data overwrites, and intermittent 502/503 errors. |
| **Logica Health Open** | `https://api.logicahealth.org/open` | FHIR 4.0.1 | Requires Auth Token | N/A | **Excluded as default unauthenticated sandbox.** Requires OAuth2 bearer credentials. |

### Verified Adult Patient Cohort (SMART Health IT)

The probe script verified the following adult synthetic patients meeting the clinical criteria (Adult >= 18, >= 3 BP observation panels, >= 1 active medication request):

1. **`d48ac962-78c6-46cf-ba33-a24771bfa0e4`**
   - **DOB**: 1939-01-27 (Adult, age 87)
   - **Observations**: 4 BP panels (LOINC `55284-4` / `85354-9`)
   - **Medications**: Active prescription for Hydrochlorothiazide
2. **`b85d7e00-3690-4e2a-87a0-f3d2dfc908b3`**
   - **DOB**: 1973-01-28 (Adult, age 53)
   - **Observations**: 4 BP panels
   - **Medications**: Active prescription for Lisinopril
3. **`4551370c-c3eb-4164-a2ff-b528f73a4e0f`**
   - **DOB**: 1997-03-03 (Adult, age 29)
   - **Observations**: 3 BP panels
   - **Medications**: Active prescription for Metformin

---

## 3. In-Process Simulated Hospital (`demo-hospital`)

To enable fast, hermetic, and offline testing without network dependence or sandbox flakiness, ChronicCare AI includes an in-process deterministic FHIR server (`data_sources/fhir_sim.py`).

### Key Features
- **Relative Timestamps**: Generates timestamps relative to invocation time (`T - 2h`, `T - 24h`, `T - 7d`), ensuring observation comparisons and 14-day history lookbacks never decay or expire.
- **SSRF Immunity**: The `sim://` URL scheme is intercepted inside `data_sources/fhir_client.py` and routed directly to in-memory handlers with zero socket allocation.
- **Deterministic Clinical Archetypes**:

| Patient ID | Display Name & Age | Clinical Conditions | Baseline Vitals & Medications | Test Purpose |
|---|---|---|---|---|
| `sim-ayesha` | Ayesha K. (age 52) | Type 2 Diabetes & Hypertension | BP 128/82, Glucose 145 mg/dL, Metformin 1000mg, Lisinopril 10mg | Primary reconciliation happy path and conflict testing. |
| `sim-bilal` | Bilal A. (age 67) | Hypertension | Low baseline BP (110-116/70-74 mmHg), Amlodipine 5mg | Personal baseline evaluation & BP spike triage protocol triggering (>= 20 mmHg rise). |
| `sim-sana` | Sana M. (age 45) | Type 2 Diabetes | Glucose 150-175 mg/dL, Insulin glargine, Metformin | Insulin safety scoping. |
| `sim-imran` | Imran Q. (age 71) | Type 2 Diabetes & Hypertension | Rising BP (148-156/92-98) and Glucose (180-210) | Urgent review queue ordering. |
| `sim-newpatient` | Nadia R. (age 38) | Hypertension | No recent observations | Cold start & empty record warning testing. |
| `sim-child` | Omar K. (age 12) | Type 1 Diabetes (Pediatric) | Vitals & insulin | Adult-only safety boundary enforcement (HTTP 422 `ehr_patient_not_adult`). |

---

## 4. Medication Scope Filter

Large hospital EHR records often contain dozens of unrelated prescriptions (e.g. eye drops, topical creams, historical antibiotics) that would overwhelm patients during a daily check-in.

The **Medication Scope Filter** (`data_sources/medication_scope.py`):
1. **Filters for Active Status**: Keeps only `status == "active"`.
2. **Filters for Disease Relevance**: Matches against curated Type 2 Diabetes and Hypertension active ingredient keywords.
3. **Deduplicates**: Groups multiple prescriptions for the same medication class (e.g., titrated doses of Metformin) and retains only the most recently authored prescription.
4. **Enforces Clinical Limit**: Caps the total medication review list to **8 items**.

---

## 5. Normalisation and Unit Conversion Audit

The FHIR Adapter (`data_sources/fhir_adapter.py`) normalises diverse FHIR R4 representations into unified internal schemas (`NormalizedObservation` and `NormalizedMedication`):

### Supported LOINC Codes
- **Blood Glucose**: `2339-0`, `15074-8`, `15075-5`, `41653-7`
- **HbA1c**: `4548-4`, `17855-8`, `17856-6`, `59261-8`
- **Blood Pressure Panels**: `55284-4` (BP systolic and diastolic), `85354-9` (BP panel with components `8480-6` Systolic and `8462-4` Diastolic)
- **Body Weight**: `29463-7`, `3141-9`

### Unit Conversion Rules
- **Glucose**: `mmol/L` values are converted to `mg/dL` by multiplying by `18.0182`.
- **HbA1c**: `mmol/mol` (IFCC) values are converted to `%` (DCCT) via `(0.09148 * mmol_mol) + 2.152`.
- **Weight**: Pounds (`[lb_av]`, `lbs`) are converted to `kg` by multiplying by `0.45359237`.
- **Blood Pressure**: Expressed in `mmHg` (raw string format preserved if unconverted).

---

## 6. Testing & Running Connected Mode

### 1. Run Hermetic Unit and Integration Tests
All tests are 100% hermetic (no real network or live database required):
```bash
# Backend pytest suite (includes simulated hospital and client tests)
cd backend-poc-technical
pytest test_ehr_connected.py test_fhir_client.py test_fhir_sim.py

# Frontend vitest suite
npm test
```

### 2. Run the FHIR Probe Script (Diagnostic Tool)
To probe public sandbox servers or your own local FHIR instance:
```bash
python scripts/probe_fhir.py --server https://r4.smarthealthit.org
```

---

## 7. Honest Limitations and Safety Boundaries

1. **Synthetic Data Only**: All records in the simulated hospital and public sandboxes are synthetic. Real patient identifiers (PHI/PII) must never be transmitted to public sandboxes.
2. **Read-Only Scope**: Connected Mode retrieves patient observations and medications for clinical decision support and check-in reconciliation. It does not write back or modify EHR records.
3. **Adult-Only Scope**: In this release, ChronicCare AI strictly supports adult patients (age 18 and older). Connecting a patient record under 18 is explicitly refused with HTTP 422 (`ehr_patient_not_adult`).
4. **Public Sandbox Volatility**: Public sandboxes may experience downtime, network latency, or periodic data resets. For dependable demos and local testing, always use the **In-Process Simulator (`demo-hospital`)**.
