# EHR Test Patients (SMART Health IT Sandbox & Simulated Hospital)

This document catalogs the selected test patients from the public SMART Health IT R4 sandbox (`https://r4.smarthealthit.org`) and the in-process simulated hospital for Connected Mode testing in ChronicCare AI.

---

## 1. Selected Sandbox Test Patients (Part B1)

We selected 12 real sandbox patient records discovered via `scripts/find_ehr_test_patients.py`, meeting all inclusion criteria (adults $\ge 18$, non-deceased, confirmed chronic conditions):

1. **`12edb5a0-ec71-45b7-aff6-0fef1c382881` (Age 75, Male, Dual T2D + HTN)**
   *Why it's in:* Tests high-complexity older adult on triple in-scope therapy (Amlodipine + Humulin Insulin + Hydrochlorothiazide) with concurrent labs and vitals.
2. **`9bf59715-246f-4ce2-85a6-58c1757f8d21` (Age 78, Female, Dual T2D + HTN)**
   *Why it's in:* Tests geriatric patient ($75+$) with dual conditions, complete labs/vitals, and active oral antidiabetic + thiazide regimen (Metformin ER + Hydrochlorothiazide).
3. **`948e608d-e408-4788-8cf2-8157c49c2940` (Age 55, Male, Dual T2D + HTN)**
   *Why it's in:* Tests multi-drug regimen (Humulin 70/30 Insulin + Hydrochlorothiazide + Metformin ER) covering injectable insulin, diuretic, and biguanide.
4. **`bd6f9f37-7295-4cd6-b212-134afcef1253` (Age 70, Male, Dual T2D + HTN)**
   *Why it's in:* Tests dual diagnosis on 3 concurrent chronic medications (Humulin Insulin + Metformin ER + Hydrochlorothiazide) with complete synchronized laboratory panel.
5. **`fa064acf-b7f1-4279-83d3-7a94686da7ba` (Age 106, Male, Dual HTN + T2D)**
   *Why it's in:* Tests centenarian ($100+$) geriatric edge case with dual conditions, blood pressure vitals, and chronic medications (Metformin ER + Hydrochlorothiazide).
6. **`0e61c3ad-d11e-4080-a6aa-cac89cae4e37` (Age 73, Male, Dual T2D + HTN)**
   *Why it's in:* Tests insulin therapy combined with a thiazide diuretic (Hydrochlorothiazide) and biguanide (Metformin ER).
7. **`ab4e7a7d-8b0d-41e1-9ce9-3877d7615aed` (Age 69, Female, Dual T2D + HTN)**
   *Why it's in:* Tests dual diagnosis on injectable insulin (Humulin 70/30) and antihypertensive diuretic (Hydrochlorothiazide).
8. **`4d58465c-4703-4c36-ab8f-2f935dc4bee7` (Age 64, Female, Dual T2D + HTN)**
   *Why it's in:* Tests female adult with dual conditions on full triple chronic therapy (Humulin Insulin + Metformin ER + Hydrochlorothiazide).
9. **`7099b4c5-6f47-4293-9690-f2afb23b9dd6` (Age 80, Male, T2D Only)**
   *Why it's in:* Tests isolated Type 2 Diabetes in an octogenarian on combined oral and injectable glycemic control (Humulin Insulin + Metformin ER).
10. **`132f48ba-1d72-4e0c-a220-91786d7501aa` (Age 56, Female, T2D Only)**
    *Why it's in:* Tests Type 2 Diabetes isolated condition on combined injectable insulin (Humulin) and oral Metformin with full glycemic history.
11. **`71304c2e-64b0-4b57-91f6-2c1ff771d72c` (Age 67, Female, T2D Only)**
    *Why it's in:* Tests Type 2 Diabetes on a single first-line oral antidiabetic (Metformin ER 500 mg).
12. **`d4f1aab1-73e6-4d51-98eb-e1556406b2a3` (Age 63, Male, HTN Only)**
    *Why it's in:* Tests essential hypertension isolated condition on Hydrochlorothiazide diuretic therapy with recorded blood pressure.

---

## 2. Patient Specification Table (Part B2)

| Patient ID | Age | Sex | Conditions | In-Scope Medications | Latest Reading Dates (BP / Gluc / HbA1c) | Practitioner | What it tests |
|---|---|---|---|---|---|---|---|
| `12edb5a0-ec71-45b7-aff6-0fef1c382881` | 75 | M | T2D, HTN | Amlodipine, Humulin Insulin, Hydrochlorothiazide | 2021-03-11 / 2021-03-11 / 2021-03-11 | Yes (Cedrick Runte) | Triple in-scope therapy (CCB + insulin + diuretic) |
| `9bf59715-246f-4ce2-85a6-58c1757f8d21` | 78 | F | T2D, HTN | Metformin ER, Hydrochlorothiazide | 2021-01-11 / 2021-01-11 / 2021-01-11 | Yes (Mariam Gleason) | Older adult (75+), dual conditions, full labs |
| `948e608d-e408-4788-8cf2-8157c49c2940` | 55 | M | T2D, HTN | Humulin Insulin, Hydrochlorothiazide, Metformin ER | 2021-03-02 / 2021-03-02 / 2021-03-02 | Yes (Jonah Schroeder) | Multi-drug regimen (insulin + biguanide + diuretic) |
| `bd6f9f37-7295-4cd6-b212-134afcef1253` | 70 | M | T2D, HTN | Humulin Insulin, Metformin ER, Hydrochlorothiazide | 2021-03-13 / 2021-03-13 / 2021-03-13 | Yes (Jonah Schroeder) | Dual conditions on 3 in-scope chronic meds |
| `fa064acf-b7f1-4279-83d3-7a94686da7ba` | 106 | M | HTN, T2D | Metformin ER, Hydrochlorothiazide | 2021-03-27 / 2021-03-27 / 2021-03-27 | Yes (Peggie Bradtke) | Centenarian (100+) edge case with dual conditions |
| `0e61c3ad-d11e-4080-a6aa-cac89cae4e37` | 73 | M | T2D, HTN | Humulin Insulin, Hydrochlorothiazide, Metformin ER | 2020-09-17 / 2020-09-17 / 2020-09-17 | Yes (Maricarmen Partida) | Insulin therapy combined with diuretic |
| `ab4e7a7d-8b0d-41e1-9ce9-3877d7615aed` | 69 | F | T2D, HTN | Humulin Insulin, Hydrochlorothiazide | 2021-03-11 / 2021-03-11 / 2021-03-11 | Yes (Rashad Maggio) | Dual diagnosis on insulin + antihypertensive |
| `4d58465c-4703-4c36-ab8f-2f935dc4bee7` | 64 | F | T2D, HTN | Humulin Insulin, Metformin ER, Hydrochlorothiazide | 2021-02-18 / 2021-02-18 / 2021-02-18 | Yes (America Turner) | Dual conditions on full triple therapy |
| `7099b4c5-6f47-4293-9690-f2afb23b9dd6` | 80 | M | T2D | Humulin Insulin, Metformin ER | 2021-01-31 / 2021-01-31 / 2021-01-31 | Yes (Gregg Johns) | Octogenarian T2D on oral + injectable control |
| `132f48ba-1d72-4e0c-a220-91786d7501aa` | 56 | F | T2D | Humulin Insulin, Metformin ER | 2021-03-12 / 2021-03-12 / 2021-03-12 | Yes (Noe Dibbert) | T2D only on insulin + oral antidiabetic |
| `71304c2e-64b0-4b57-91f6-2c1ff771d72c` | 67 | F | T2D | Metformin ER | 2020-11-05 / 2020-11-05 / 2020-11-05 | Yes (Quentin Beahan) | T2D only on single oral monotherapy |
| `d4f1aab1-73e6-4d51-98eb-e1556406b2a3` | 63 | M | HTN | Hydrochlorothiazide | 2021-01-24 / 2021-02-07 / None | Yes (Georgann Beer) | HTN only on monotherapy with BP vitals |

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
