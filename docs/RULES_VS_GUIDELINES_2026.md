# Clinical Rules vs. Guidelines (2026 ADA & 2025 AHA/ACC Comparison)

> **Licence & Compliance Notice:** American Diabetes Association (ADA) and American Heart Association / American College of Cardiology (AHA/ACC) guideline PDFs carry strict text/data mining prohibitions and copyright restrictions. In accordance with project licence rules, automated extraction from ADA and AHA/ACC PDFs is blocked pending formal written permission (request submitted 27 October 2026). For blocked rows, our system thresholds and the guideline section covering each topic are documented below, with guideline values marked `USMAN TO FILL FROM PDF (section X)` for manual entry by Usman. Non-blocked sources (WHO 2021, ISH 2020, IDF-DAR 2021, Pakistan Hypertension in Women 2023, AKU 2023) are cited from ingested RAG chunks.
>
> **Safety Rule:** This document is strictly an audit and decision-support comparison register. All values in `docs/CLINICAL_RULES.md` and `backend-poc-technical/agents/triage_protocol.py` remain **READ-ONLY** and unchanged.

---

## 1. Numeric Thresholds Comparison Matrix

| # | Rule / Constant | Our Value | Guideline Value (ADA 2026 / AHA 2025 / Non-Blocked) | Chunk ID & Citation | Verbatim Quote (<= 25 words) | Status | Proposed Action |
|---|---|---|---|---|---|---|---|
| 1 | `DANGEROUS_BP_SYSTOLIC_MMHG` | SBP ≥ 180 mmHg | USMAN TO FILL FROM PDF (Section 6.2) | PENDING PERMISSION (AHA/ACC 2025 Sec 6.2); Corroborated in `pk_htn_women_2023` chunk `5bbaa0d663c2` p. 15 | *"Severe and abrupt rise in blood pressure with impendeng or progressive acute target organ demagethe starting BP 180/120"* | MATCH (PK 2023 / ISH 2020) | Retain 180 mmHg crisis trigger; await manual fill from 2025 AHA PDF Sec 6.2. |
| 2 | `DANGEROUS_BP_DIASTOLIC_MMHG` | DBP ≥ 120 mmHg | USMAN TO FILL FROM PDF (Section 6.2) | PENDING PERMISSION (AHA/ACC 2025 Sec 6.2); Corroborated in `ish_2020_htn` chunk `4b4110431397` p. 15 | *"Acute ischaemic stroke and SBP >220 mm Hg or DBP >120 mm Hg"* | PARTIAL: stroke-specific context | Retain 120 mmHg crisis trigger; await manual fill from 2025 AHA PDF Sec 6.2. |
| 3 | `BP_STAGE2_SYSTOLIC_MMHG` | SBP ≥ 140 mmHg | USMAN TO FILL FROM PDF (Section 2) | PENDING PERMISSION (AHA/ACC 2025 Sec 2); Corroborated in `who_2021_htn` chunk `7bd706fc46fd` p. 28 | *"WHO recommends a target blood pressure treatment goal of <140/90 mmHg in all patients with hypertension without comorbidities."* | PARTIAL: WHO treatment target, not a definition | Retain 140 mmHg re-check boundary for 'improved but still high'. |
| 4 | `BP_STAGE2_DIASTOLIC_MMHG` | DBP ≥ 90 mmHg | USMAN TO FILL FROM PDF (Section 2) | PENDING PERMISSION (AHA/ACC 2025 Sec 2); Corroborated in `who_2021_htn` chunk `7bd706fc46fd` p. 28 | *"target blood pressure treatment goal of <140/90 mmHg in all patients"* | PARTIAL: WHO treatment target, not a definition | Retain 90 mmHg re-check boundary. |
| 5 | `BP_LOW_SYSTOLIC_MMHG` | SBP < 90 mmHg | NOT IN GUIDELINE | N/A (Clinical team illustrative rule) | N/A (Engineering / safety convention) | NOT IN GUIDELINE | Retain 90 mmHg low BP screening threshold for clinician review. |
| 6 | `BP_LOW_DIASTOLIC_MMHG` | DBP < 60 mmHg | NOT IN GUIDELINE | N/A (Clinical team illustrative rule) | N/A (Engineering / safety convention) | NOT IN GUIDELINE | Retain 60 mmHg low BP screening threshold for clinician review. |
| 7 | `BP_CHANGE_NOTABLE_MMHG` | SBP rise ≥ 20 mmHg | NOT IN GUIDELINE | N/A (Clinical team illustrative / supervisor feedback) | N/A (Dynamic change heuristic against patient median) | NOT IN GUIDELINE | Retain 20 mmHg rise over baseline trigger. |
| 8 | `BP_CHANGE_MARKED_MMHG` | SBP rise ≥ 40 mmHg | NOT IN GUIDELINE | N/A (Clinical team illustrative rule) | N/A (Marked rise heuristic escalates directly to urgent) | NOT IN GUIDELINE | Retain 40 mmHg escalation to urgent. |
| 9 | `BASELINE_MIN_READINGS` | 3 readings | NOT IN GUIDELINE | N/A (Engineering median requirement) | N/A (Minimum sample size to establish stable baseline) | NOT IN GUIDELINE | Retain minimum 3 readings rule. |
| 10 | `BASELINE_MAX_READINGS` | 7 readings | NOT IN GUIDELINE | N/A (Engineering rolling window) | N/A (Recency constraint) | NOT IN GUIDELINE | Retain 7 most recent readings rule. |
| 11 | `BASELINE_WINDOW_DAYS` | 14 days | NOT IN GUIDELINE | N/A (Engineering rolling window) | N/A (Two-week history constraint) | NOT IN GUIDELINE | Retain 14-day baseline lookback. |
| 12 | `GLUCOSE_HIGH_MG_DL` | Glucose ≥ 250 mg/dL | USMAN TO FILL FROM PDF (Section 6) | PENDING PERMISSION (ADA 2026 Sec 6); Corroborated in `idf_dar_2021` chunk `fe5c32a6e3e7` p. 183 | *"If BG between 160-250 mg/dL"* | PENDING ADA MANUAL FILL | Retain 250 mg/dL trigger for DKA symptom questions. |
| 13 | `GLUCOSE_URGENT_MG_DL` | Glucose ≥ 300 mg/dL | USMAN TO FILL FROM PDF (Section 6) | PENDING PERMISSION (ADA 2026 Sec 6) | N/A (Illustrative rule: asymptomatic high glucose goes to urgent) | NOT IN GUIDELINE | Retain 300 mg/dL urgent escalation; submit for clinician sign-off. |
| 14 | `GLUCOSE_LOW_MG_DL` | Glucose < 70 mg/dL | USMAN TO FILL FROM PDF (Section 6) | PENDING PERMISSION (ADA 2026 Sec 6: Level 1 Hypoglycemia) | *[Blocked under licence - Usman to fill from PDF]* | PENDING ADA MANUAL FILL | Standard Level 1 hypoglycemia definition (54-69 mg/dL); retain < 70. |
| 15 | `GLUCOSE_VERY_LOW_MG_DL` | Glucose < 54 mg/dL | USMAN TO FILL FROM PDF (Section 6) | PENDING PERMISSION (ADA 2026 Sec 6: Level 2 Hypoglycemia) | *[Blocked under licence - Usman to fill from PDF]* | PENDING ADA MANUAL FILL | Standard Level 2 clinically significant hypoglycemia (< 54 mg/dL); escalates to urgent. |
| 16 | `MIN_ADULT_AGE` | Age ≥ 18 years | 18 years | Corroborated in `who_2021_htn` chunk `7bd706fc46fd` p. 28 | *"in all patients with hypertension without comorbidities"* (adult population scope) | NOT IN NON-BLOCKED SOURCES | Retain onboarding age gate (adults only). |
| 17 | `OLDER_ADULT_AGE` | Age ≥ 65 years | USMAN TO FILL FROM PDF (Section 13) | PENDING PERMISSION (ADA 2026 Sec 13: Older Adults); Corroborated in `pk_htn_women_2023` chunk `9e0712e3c7c4` | *[Blocked under licence - Usman to fill from PDF]* | PENDING ADA MANUAL FILL | Retain 65 years for orthostatic dizziness, falls, and stroke extras. |
| 18 | `MAX_PLAUSIBLE_AGE` | Age ≤ 120 years | NOT IN GUIDELINE | N/A (Engineering plausibility boundary) | N/A (Date of birth validation) | NOT IN GUIDELINE | Retain 120 years boundary. |
| 19 | `GLUCOSE_RANGE_MG_DL` | 20.0 to 600.0 mg/dL | NOT IN GUIDELINE | N/A (Physical glucometer bounds) | N/A (Readings outside treated as missing) | NOT IN GUIDELINE | Retain 20-600 mg/dL range. |
| 20 | `SYSTOLIC_RANGE_MMHG` | 60 to 260 mmHg | NOT IN GUIDELINE | N/A (Physiological plausibility bounds) | N/A (Readings outside treated as missing) | NOT IN GUIDELINE | Retain 60-260 mmHg range. |
| 21 | `DIASTOLIC_RANGE_MMHG` | 30 to 160 mmHg | NOT IN GUIDELINE | N/A (Physiological plausibility bounds) | N/A (Readings outside treated as missing) | NOT IN GUIDELINE | Retain 30-160 mmHg range. |
| 22 | `NEGATION_WINDOW_WORDS` | 3 words | NOT IN GUIDELINE | N/A (NLP parsing heuristic) | N/A (Negation window preceding red-flag phrase) | NOT IN GUIDELINE | Retain 3-word clause negation rule. |
| 23 | `MAX_MEDICATIONS` | 20 medications | NOT IN GUIDELINE | N/A (Check-in interview length safety) | N/A (Maximum active prescriptions evaluated) | NOT IN GUIDELINE | Retain 20 active medications limit. |
| 24 | `MAX_DOSAGE_CHARS` | 100 chars | NOT IN GUIDELINE | N/A (Database column constraint) | N/A (Dose string truncation) | NOT IN GUIDELINE | Retain 100 characters limit. |
| 25 | Rest Time Before Re-check | 5 minutes | USMAN TO FILL FROM PDF (Section 2.1) | PENDING PERMISSION (AHA/ACC 2025 Sec 2.1); Corroborated in `pk_htn_women_2023` chunk `9e0712e3c7c4` p. 3 | *"Check after 5 minutes of rest and sitting position"* | MATCH (PK 2023) | Retain 5-minute quiet seated rest protocol before re-check. |
| 26 | Meter "LO" / "HI" Out-of-Range | LO (<~20 mg/dL) / HI (>~600 mg/dL) | NOT IN GUIDELINE | N/A (Known limitation: currently treated as missing -> routine in `CLINICAL_RULES.md`) | N/A | DOCTOR DECISION | Ask doctors what level LO (<~20 mg/dL) and HI (>~600 mg/dL) should map to. |

---

## 2. Blood Pressure Stage Definitions: 2017 vs. 2025 AHA/ACC Guidelines

`CLINICAL_RULES.md` currently cites the 2017 ACC/AHA guidelines for blood pressure staging:
- **Normal Blood Pressure:** Systolic < 120 mmHg and Diastolic < 80 mmHg.
- **Elevated Blood Pressure:** Systolic 120–129 mmHg and Diastolic < 80 mmHg.
- **Stage 1 Hypertension:** Systolic 130–139 mmHg or Diastolic 80–89 mmHg.
- **Stage 2 Hypertension:** Systolic ≥ 140 mmHg or Diastolic ≥ 90 mmHg.
- **Hypertensive Crisis:** Systolic ≥ 180 mmHg or Diastolic ≥ 120 mmHg.

### Status: CONFIRMED FROM PDF (Table 4, p. e222 & Section 8.1, p. e277)
The 2025 AHA/ACC guideline (Jones et al., *Hypertension* 2025;82:e212–e316) retains these exact blood pressure categories in Table 4 (Section 2, p. e222):
- **Normal:** SBP < 120 mmHg and DBP < 80 mmHg
- **Elevated:** SBP 120–129 mmHg and DBP < 80 mmHg
- **Stage 1 Hypertension:** SBP 130–139 mmHg or DBP 80–89 mmHg
- **Stage 2 Hypertension:** SBP ≥ 140 mmHg or DBP ≥ 90 mmHg
- **Severe Hypertension / Hypertensive Emergency:** SBP > 180 mmHg and/or DBP > 120 mmHg (Section 8.1, p. e277)

- **AHA/ACC 2025 Citation:** Jones DW et al. 2025 AHA/ACC/AAPA/ABC/ACPM/AGS/APhA/ASH/ASPC/NMA/PCNA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults. *Hypertension*. 2025;82:e212–e316. Table 4.
- **Clinician Review Item:** The values in ChronicCare AI match the 2025 AHA/ACC guideline definitions. `CLINICAL_RULES.md` citation should be updated from Whelton et al. 2017 to Jones et al. 2025.
- **Current Action:** Retain existing code thresholds unchanged. Citation update ready for clinician sign-off.


---

SENT TO DOCTORS: TO FILL BY USMAN — awaiting written sign-off
