# Clinical Sources Review

This document lists the clinical and supporting sources currently referenced in the ChronicCare AI interview bank. Verification against the original sources has not yet been performed.

| # | Source ID | Title | Link | Claim / Use in Interview Bank | Current Status |
|---|---|---|---|---|---|
| 1 | `ada_2026_soc_sec6` | ADA Standards of Care in Diabetes 2026 - Section 6: Glycemic Goals and Hypoglycemia | https://doi.org/10.2337/dc26-S006 | Hypoglycemia levels (Level 1 <70 mg/dL, Level 2 <54 mg/dL), CGM metrics, and hypoglycemia frequency screening. | VERIFIED |
| 2 | `ada_2026_soc_sec5` | ADA Standards of Care in Diabetes 2026 - Section 5: Facilitating Positive Health Behaviors | https://doi.org/10.2337/dc26-S005 | Psychosocial screening, diabetes distress, and adherence barriers. | VERIFIED |
| 3 | `ada_2026_soc_sec12` | ADA Standards of Care in Diabetes 2026 - Section 12: Retinopathy, Neuropathy, and Foot Care | https://doi.org/10.2337/dc26-S012 | Comprehensive foot evaluation, peripheral neuropathy, and early ulcer identification. | VERIFIED |
| 4 | `aha_acc_2025_hypertension` | 2025 AHA/ACC Clinical Practice Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults | Not provided in SOURCES.json | Standardized home BP measurement protocol (5-minute rest, arm support, validated cuff), crisis thresholds, and medication-induced hypertension. | Title exists, claim not checked |
| 5 | `idf_dar_2021_ramadan` | IDF-DAR Diabetes and Ramadan: Practical Guidelines 2021 | Not provided in SOURCES.json | Risk stratification during fasting, pre-dawn meal timing, hypoglycemia symptoms while fasting, and criteria for breaking the fast. | Title exists, claim not checked |
| 6 | `nice_ng28_t2d` | NICE Guideline NG28: Type 2 Diabetes in Adults: Management | Not provided in SOURCES.json | Sick-day rules during acute intercurrent illness, fluid maintenance, and ketone monitoring alert triggers. | Title exists, claim not checked |
| 7 | `nice_ng136_hypertension` | NICE Guideline NG136: Hypertension in Adults: Diagnosis and Management | Not provided in SOURCES.json | Postural hypotension screening, target-organ damage red flags, and associated symptom evaluation. | Title exists, claim not checked |
| 8 | `nice_cg138_patient_experience` | NICE Clinical Guideline CG138: Patient Experience in Adult NHS Services | Not provided in SOURCES.json | Person-centered communication, open-ended free-text elicitation, and shared decision making. | Title exists, claim not checked |
| 9 | `phq2_kroenke_2003` | Patient Health Questionnaire-2 (PHQ-2) - Kroenke et al., 2003 (Public Domain) | Not provided in SOURCES.json | Two-item screener for depressed mood and anhedonia over the past 2 weeks. | Title exists, claim not checked |
| 10 | `diabetes_distress_dds2` | Diabetes Distress Screening Items (Adapted DDS-2 Framework) | Not provided in SOURCES.json | Feeling overwhelmed by the demands of living with diabetes. | Clinician review needed |
| 11 | `clinical_team_illustrative` | ChronicCare AI Decision Support Prototype - Clinical Team Illustrative Rule | Not provided in SOURCES.json | Illustrative threshold or question written for prototype decision support; requires formal clinician review and approval. | Clinician review needed |


## Source Verification

### Source 1 — ada_2026_soc_sec6

**Status:** VERIFIED

**Original source:** American Diabetes Association Professional Practice Committee for Diabetes. "6. Glycemic Goals, Hypoglycemia, and Hyperglycemic Crises: Standards of Care in Diabetes—2026." Diabetes Care. 2026;49(Suppl. 1):S132–S149.

**DOI:** https://doi.org/10.2337/dc26-S006

**Verification:** The original publication supports the interview-bank claims. It defines Level 1 hypoglycemia as glucose below 70 mg/dL but at least 54 mg/dL and Level 2 hypoglycemia as glucose below 54 mg/dL. It also includes CGM metrics such as time in range, time above range, and time below range, and recommends reviewing hypoglycemia history in at-risk individuals.

**Relevant sections:** "Glycemic Assessment" and "Hypoglycemia Assessment, Prevention, and Treatment."

### Source 2 — ada_2026_soc_sec5

**Status:** VERIFIED

**Original source:** American Diabetes Association Professional Practice Committee for Diabetes. "5. Facilitating Positive Health Behaviors and Well-being to Improve Health Outcomes: Standards of Care in Diabetes—2026." Diabetes Care. 2026;49(Suppl. 1):S89–S131.

**DOI:** https://doi.org/10.2337/dc26-S005

**Verification:** The original publication supports the interview-bank claims. It recommends routine psychosocial screening, including screening for diabetes distress, and discusses barriers that can affect diabetes treatment and self-management. It also recommends screening for diabetes distress at least annually and repeating screening when treatment goals are not met, during transitions, or when diabetes complications are present.

**Relevant sections:** "Psychosocial Care," "Screening," and "Diabetes Distress."

### Source 3 — ada_2026_soc_sec12

**Status:** VERIFIED

**Original source:** American Diabetes Association Professional Practice Committee for Diabetes. "12. Retinopathy, Neuropathy, and Foot Care: Standards of Care in Diabetes—2026." Diabetes Care. 2026;49(Suppl. 1):S261–S276.

**DOI:** https://doi.org/10.2337/dc26-S012

**Verification:** The original publication supports the interview-bank claims. It recommends assessment for diabetic peripheral neuropathy and annual 10-g monofilament testing to identify feet at risk for ulceration and amputation. It also recommends a comprehensive foot evaluation at least annually to identify risk factors for ulcers and amputations. The foot examination includes skin inspection, assessment of foot deformities, neurological assessment, and vascular assessment. The guidance also emphasizes early recognition and surveillance of at-risk feet and foot problems.

**Relevant sections:** "Neuropathy — Screening" and "Foot Care."

## Notes

- This is an initial inventory of the entries found in `backend-poc-technical/agents/interview_bank/SOURCES.json`.
- The claims have not yet been independently verified against the original publications.
- `SOURCES.json` does not provide source URLs, so links are marked as not provided rather than being inferred or invented.
- Entries marked as requiring clinician review have been retained with the same status used in the source file.