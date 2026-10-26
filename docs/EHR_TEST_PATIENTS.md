# EHR Test Patients (SMART Health IT Sandbox & Simulated Hospital)

This document catalogs the selected test patients from the public SMART Health IT R4 sandbox (`https://r4.smarthealthit.org`) and the in-process simulated hospital for Connected Mode testing in ChronicCare AI.

---

## 1. Selected Sandbox Test Patients (Part B1)

We selected 10 real sandbox patient records discovered via `scripts/find_ehr_test_patients.py`, meeting all inclusion criteria (adults $\ge 18$, non-deceased, confirmed chronic conditions):

1. **`9bf59715-246f-4ce2-85a6-58c1757f8d21` (Age 78, Female, Dual T2D + HTN)**
   *Why it's in:* Tests geriatric patient ($75+$) with dual conditions, complete labs/vitals, and active chronic medications.
2. **`948e608d-e408-4788-8cf2-8157c49c2940` (Age 55, Male, Dual T2D + HTN)**
   *Why it's in:* Tests multi-drug regimen (Humulin 70/30 Insulin + Metformin ER + Lisinopril) covering both insulin and antihypertensives.
3. **`bd6f9f37-7295-4cd6-b212-134afcef1253` (Age 70, Male, Dual T2D + HTN)**
   *Why it's in:* Tests dual diagnosis on 3 concurrent chronic medications (Humulin Insulin + Metformin ER + Lisinopril) with complete lab history.
4. **`0e61c3ad-d11e-4080-a6aa-cac89cae4e37` (Age 73, Male, Dual T2D + HTN)**
   *Why it's in:* Tests insulin therapy combined with a thiazide diuretic (Hydrochlorothiazide) and biguanide (Metformin ER).
5. **`132f48ba-1d72-4e0c-a220-91786d7501aa` (Age 56, Female, T2D Only)**
   *Why it's in:* Tests Type 2 Diabetes isolated condition on combined injectable insulin (Humulin) and oral Metformin with full glycemic history.
6. **`71304c2e-64b0-4b57-91f6-2c1ff771d72c` (Age 67, Female, T2D Only)**
   *Why it's in:* Tests Type 2 Diabetes on a single first-line oral antidiabetic (Metformin ER 500 mg).
7. **`54d0aacd-9b70-4a62-91ac-af86c9408ae8` (Age 72, Male, HTN Only)**
   *Why it's in:* Tests essential hypertension alone in an older adult on Hydrochlorothiazide diuretic therapy with recorded blood pressure.
8. **`b3873037-a455-4558-a066-9faaed01b673` (Age 59, Male, HTN Only)**
   *Why it's in:* Tests uncomplicated essential hypertension on monotherapy with routine blood pressure monitoring.
9. **`9462ff5c-47c8-4e46-a180-1cac0a2003c4` (Age 28, Male, HTN Only)**
   *Why it's in:* Tests young adult onset hypertension (age 28) on active antihypertensive therapy.
10. **`76d2fa2d-66a6-4823-8dab-52cd70822844` (Age 52, Female, Dual T2D + HTN + Allergies)**
    *Why it's in:* Tests extensive EHR allergy record (10 allergies including Latex, Shellfish, Peanuts) alongside chronic disease management.
11. **`ecaea95c-46de-4ac9-a58d-4847d1a3e574` (Age 109, Female, Dual Conditions, No Practitioner)**
    *Why it's in:* Tests the "no practitioner on record" fallback path (generalPractitioner is empty and encounter participant is null).
12. **`d48ac962-78c6-46cf-ba33-a24771bfa0e4` (Age 64, Male, Dual Conditions, Legacy Sandbox)**
    *Why it's in:* Retains backward-compatible continuity with the original POC sandbox patient registry.

---

## 2. Patient Specification Table (Part B2)

| Patient ID | Age | Sex | Conditions | In-Scope Medications | Latest Reading Dates (BP / Gluc / HbA1c) | Practitioner | What it tests |
|---|---|---|---|---|---|---|---|
| `9bf59715-246f-4ce2-85a6-58c1757f8d21` | 78 | F | T2D, HTN | Metformin, Lisinopril | 2021-01-11 / 2021-01-11 / 2021-01-11 | Yes (Dr. Mariam Gleason) | Older adult (75+), dual conditions, full labs |
| `948e608d-e408-4788-8cf2-8157c49c2940` | 55 | M | T2D, HTN | Humulin Insulin, Metformin ER, Lisinopril | 2021-03-02 / 2021-03-02 / 2021-03-02 | Yes (Dr. Jonah Schroeder) | Multi-drug regimen (insulin + ACEi + biguanide) |
| `bd6f9f37-7295-4cd6-b212-134afcef1253` | 70 | M | T2D, HTN | Humulin Insulin, Metformin ER, Lisinopril | 2021-03-13 / 2021-03-13 / 2021-03-13 | Yes (Dr. Jonah Schroeder) | Dual conditions on 3 in-scope chronic meds |
| `0e61c3ad-d11e-4080-a6aa-cac89cae4e37` | 73 | M | T2D, HTN | Humulin Insulin, Hydrochlorothiazide, Metformin ER | 2020-09-17 / 2020-09-17 / 2020-09-17 | Yes (Dr. Maricarmen Partida) | Insulin therapy combined with diuretic |
| `132f48ba-1d72-4e0c-a220-91786d7501aa` | 56 | F | T2D | Humulin Insulin, Metformin ER | 2021-03-12 / 2021-03-12 / 2021-03-12 | Yes (Dr. Noe Dibbert) | T2D only on insulin + oral antidiabetic |
| `71304c2e-64b0-4b57-91f6-2c1ff771d72c` | 67 | F | T2D | Metformin ER | 2020-11-05 / 2020-11-05 / 2020-11-05 | Yes (Dr. Quentin Beahan) | T2D only on single oral monotherapy |
| `54d0aacd-9b70-4a62-91ac-af86c9408ae8` | 72 | M | HTN | Hydrochlorothiazide | 2020-07-28 / 2020-07-28 / None | Yes (Dr. Cedrick Runte) | HTN only in older adult, diuretic therapy |
| `b3873037-a455-4558-a066-9faaed01b673` | 59 | M | HTN | Hydrochlorothiazide | 2020-09-11 / None / None | Yes (Dr. Dagny Schoen) | HTN only on monotherapy with BP vitals |
| `9462ff5c-47c8-4e46-a180-1cac0a2003c4` | 28 | M | HTN | Hydrochlorothiazide | 2020-04-01 / None / None | Yes (Dr. Lloyd Effertz) | Young adult hypertension (<35) |
| `76d2fa2d-66a6-4823-8dab-52cd70822844` | 52 | F | T2D, HTN | Hydrochlorothiazide | 2020-02-06 / 2020-02-06 / 2020-02-06 | Yes (Dr. Jonah Schroeder) | EHR allergies (10 entries: latex, shellfish, peanut) |
| `ecaea95c-46de-4ac9-a58d-4847d1a3e574` | 109 | F | T2D, HTN | None in-scope | 2020-08-11 / 2020-08-11 / 2020-08-11 | No (None) | "No practitioner on record" fallback path |
| `d48ac962-78c6-46cf-ba33-a24771bfa0e4` | 64 | M | T2D, HTN | Metformin | 2020-06-15 / 2020-06-15 / 2020-06-15 | Yes (Dr. SMART) | Baseline POC sandbox backward compatibility |

---

## 3. Gaps and Mitigation (Part B3)

While the public SMART Health IT sandbox contains valid FHIR R4 resources, several structural gaps exist for realistic clinical check-in testing:

1. **Temporal Gap (Stale Timestamps):**
   - All sandbox observations, encounters, and medication requests date between **2018 and 2021**.
   - Because our reconciliation and baseline window checks require observations within the last 48 hours to 14 days, connecting to a live sandbox patient will never produce an immediate 48-hour observation match with a check-in conducted today.
2. **Fixed Medication Statuses:**
   - Active medications in the public sandbox are static. We cannot test dynamic discontinuation or dosage changes across visits in the external server without write access (which public SMART forbids).
3. **Sparse Allergy Documentation in Chronic Subgroups:**
   - Most diabetes/hypertension sandbox patients do not have documented allergies; only a subset of general cohort patients have populated `AllergyIntolerance` entries.
4. **Practitioner Reference Inconsistency:**
   - Sandbox patients rarely populate `Patient.generalPractitioner`; practitioner references must usually be resolved by inspecting the participant array of historical `Encounter` resources.

### Mitigation via Synthea and FhirSim (Part F)
To close these gaps:
- The in-process simulator (`fhir_sim.py`) implements relative dynamic timestamps ($T - \text{hours/days}$ from `now`), guaranteeing recent readings within the 48-hour comparison window for every check-in.
- Part F converts synthetic Synthea bundles into lightweight fixtures (`backend-poc-technical/data_sources/fhir_sim_fixtures/sim-syn-*.json`), re-based relative to execution time, providing freshly dated vitals (glucose, HbA1c, BP), active medications, populated practitioners, and allergies.
