# Clinical Rules Register

> **Medical Decision-Support Specification for ChronicCare AI**  
> **Version:** 1.0 (Stage 7D-1)  
> **Purpose:** Comprehensive clinician-readable specification of deterministic clinical rules, physiological thresholds, triage logic, guideline citations, intentional exclusions, and codebase constants.

---

## 1. Executive Summary & Design Principles

ChronicCare AI is a medical decision-support prototype assisting adults living with chronic hypertension and type 2 diabetes. The system is designed to behave like a careful, conservative clinician:
1. **Safety First (Fail-Safe)**: When uncertainty, contradiction, or physiological extremes arise, the system always escalates conservatively (Routine $\rightarrow$ Review $\rightarrow$ Urgent $\rightarrow$ Emergency) and never down-grades clinical risk.
2. **Confirmation-Based Triage**: A single extreme blood pressure reading without warning symptoms is not immediately treated as an unconfirmed emergency, nor is it dismissed. It triggers a structured, protocol-driven re-measurement after quiet rest, followed by systematic symptom and factor investigation.
3. **Deterministic Execution**: All routing, thresholding, triage classifications, and reconciliation comparisons are deterministic algorithms with zero reliance on generative language models for clinical calculations or safety gating.
4. **No Direct Prescribing or Titration**: The system does not calculate insulin boluses, titrate antihypertensive medications, or offer unsolicited diagnostic conclusions.

---

## 2. Enforced Clinical Rules

### 2.1 Patient Inclusion & Eligibility
- **Adults Only (`MIN_ADULT_AGE = 18`, `MAX_PLAUSIBLE_AGE = 120`)**:
  - *Rule*: Check-ins are restricted to adult patients aged 18 to 120 years.
  - *Logic*: Profile submission validates `date_of_birth` (ISO `YYYY-MM-DD`). Ages $< 18$ return HTTP 422 `adults_only`. Ages $> 120$ or future dates return HTTP 422 `invalid_date_of_birth`.
  - *Inclusion Confirmation*: Patient must explicitly confirm "I am 18 or older and not pregnant" (`inclusion_confirmed_at`). Check-in starts are blocked (HTTP 403 `profile_incomplete`) if either DOB or inclusion confirmation is missing when `REQUIRE_INCLUSION` is enabled.
  - *Guideline*: NICE NG136 (Hypertension in adults), ADA Standards of Care (2024, Chapter 15 - Management of Diabetes in Pregnancy).

### 2.2 Adaptive Interview Phase
- **Plausible Physiological Bounds**:
  - *Blood Pressure Systolic (`SYSTOLIC_RANGE_MMHG = (50, 300)`)*: Readings $< 50$ or $> 300\text{ mmHg}$ are rejected as non-physiological input.
  - *Blood Pressure Diastolic (`DIASTOLIC_RANGE_MMHG = (30, 200)`)*: Readings $< 30$ or $> 200\text{ mmHg}$ are rejected.
  - *Blood Glucose (`GLUCOSE_RANGE_MG_DL = (20.0, 1000.0)`)*: Readings $< 20$ or $> 1000\text{ mg/dL}$ are rejected.
- **Stage 1 Dangerous Reading Screening**:
  - *Dangerous Blood Pressure (`DANGEROUS_BP_SYSTOLIC_MMHG = 180`, `DANGEROUS_BP_DIASTOLIC_MMHG = 120`)*: During intake interview, systolic $\ge 180$ or diastolic $\ge 120\text{ mmHg}$ triggers the confirmation-based severe blood pressure triage protocol at the end of interview.
  - *Guideline*: 2017 ACC/AHA High Blood Pressure Clinical Practice Guideline (Hypertensive Crisis / Crisis Range).
- **Stage 1 Red-Flag Keyword Screening**:
  - Unprompted statements of acute medical distress ("chest pain", "shortness of breath", "loss of vision", "slurred speech", "weakness on one side") halt the intake and immediately trigger emergency persistence. Negation cues within `NEGATION_WINDOW_WORDS = 3` words prevent false escalations.

### 2.3 Clinical Triage Protocol Phase
When an intake interview completes without an acute red flag, the system evaluates all submitted vital signs and triggers specialized triage protocols in priority order:

1. **Severe Blood Pressure Protocol (`bp_severe`)**:
   - *Trigger*: First systolic $\ge 180$ or diastolic $\ge 120\text{ mmHg}$ (`BP_STAGE2_SYSTOLIC_MMHG`, `BP_STAGE2_DIASTOLIC_MMHG`).
   - *Protocol Steps*:
     1. Re-measurement instruction: "Please sit and rest quietly for 5 minutes, then take your blood pressure again. What is your reading now?"
     2. Acute symptom inquiry: Checks for hypertensive encephalopathy / end-organ damage symptoms (chest pain, shortness of breath, severe headache, vision changes, weakness/numbness). Any warning symptom $\rightarrow$ **Emergency** (immediate call 911/999).
     3. Substance & medication factors: Checks for recent sympathomimetics, decongestants, cold medicine, caffeine, or NSAIDs.
     4. Acute circumstances: Checks for acute stress, severe pain, or missed doses.
   - *Outcomes*:
     - Warning symptoms present $\rightarrow$ **Emergency**
     - Persistent severe reading ($\ge 180/120$) without symptoms $\rightarrow$ **Urgent** (same-day clinician assessment)
     - Improved reading ($< 180/120$) without symptoms $\rightarrow$ **Review** (routine clinician review with annotated context)
   - *Guideline*: ACC/AHA 2017 Guideline for Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults; NICE NG136 Section 1.4.

2. **High Blood Glucose Protocol (`glucose_high`)**:
   - *Trigger*: Glucose $\ge 250\text{ mg/dL}$ (`GLUCOSE_HIGH_MG_DL = 250.0`).
   - *Protocol Steps*:
     1. Diabetic Ketoacidosis (DKA) / Hyperosmolar Hyperglycemic State (HHS) symptoms: Nausea, vomiting, abdominal pain, shortness of breath, fruity breath, confusion. Any positive $\rightarrow$ **Emergency**.
     2. Acute infection / illness inquiry: Fever, cough, dysuria.
     3. Medication & nutritional factors: Missed insulin/medication, high-carbohydrate intake.
   - *Outcomes*:
     - Warning symptoms present $\rightarrow$ **Emergency**
     - Glucose $\ge 300\text{ mg/dL}$ (`GLUCOSE_URGENT_MG_DL = 300.0`) without symptoms $\rightarrow$ **Urgent**
     - Glucose between $250\text{ and }299\text{ mg/dL}$ without symptoms $\rightarrow$ **Review**
   - *Guideline*: ADA Standards of Care in Diabetes (2024, Chapter 6 - Glycemic Targets and Hypo/Hyperglycemia Management).

3. **Low Blood Glucose Protocol (`glucose_low`)**:
   - *Trigger*: Glucose $< 70\text{ mg/dL}$ (`GLUCOSE_LOW_MG_DL = 70.0`).
   - *Protocol Steps*:
     1. Severe neuroglycopenic symptoms: Confusion, unsteadiness, loss of coordination. Any positive $\rightarrow$ **Emergency**.
     2. Swallowing safety: Patient or caregiver confirms if patient can safely swallow liquids or fast-acting carbohydrate. If unable $\rightarrow$ **Emergency**.
     3. Rule of 15 guidance: Guidance to consume 15-20g fast-acting carbohydrate and recheck in 15 minutes.
   - *Outcomes*:
     - Severe confusion or unable to swallow $\rightarrow$ **Emergency**
     - Severe hypoglycemia ($< 54\text{ mg/dL}$, `GLUCOSE_VERY_LOW_MG_DL = 54.0`) $\rightarrow$ **Urgent**
     - Mild-moderate hypoglycemia ($54-69\text{ mg/dL}$) self-treatable $\rightarrow$ **Review**
   - *Guideline*: ADA Standards of Care in Diabetes (2024, Chapter 6 - Hypoglycemia Level 1/2/3 definitions).

4. **Low Blood Pressure Protocol (`bp_low`)**:
   - *Trigger*: Systolic $< 90$ or Diastolic $< 60\text{ mmHg}$ (`BP_LOW_SYSTOLIC_MMHG = 90.0`, `BP_LOW_DIASTOLIC_MMHG = 60.0`).
   - *Protocol Steps*:
     1. Symptom check: Lightheadedness, dizziness, fainting, clammy skin.
     2. Hydration and fluid intake check.
     3. Recent antihypertensive medication timing.
     4. Older Adult Extension ($\ge 65$ years, `OLDER_ADULT_AGE = 65`): Evaluates recent falls or near-syncope.
   - *Outcomes*:
     - Dizziness, fainting, or fall in older adult $\rightarrow$ **Urgent**
     - Asymptomatic low BP $\rightarrow$ **Review**
   - *Guideline*: WHO Guidelines on Hypertension Management; NICE CG161 (Falls in older people).

5. **Blood Pressure Change from Baseline Protocol (`bp_change`)**:
   - *Baseline Calculation*: Requires at least 3 (`BASELINE_MIN_READINGS = 3`) completed, non-emergency readings within the last 14 days (`BASELINE_WINDOW_DAYS = 14`), using up to the latest 7 readings (`BASELINE_MAX_READINGS = 7`). Calculated as the statistical median.
   - *Trigger*: Systolic rise $\ge 20\text{ mmHg}$ (`BP_CHANGE_NOTABLE_MMHG = 20.0`) from the personal baseline (when not severe).
   - *Protocol Steps*:
     1. Headaches or visual disturbance inquiry.
     2. Adherence check (missed doses).
     3. Stress, sleep, or dietary sodium factors.
     4. Orthostatic dizziness on standing for older adults ($\ge 65$).
   - *Outcomes*:
     - Marked rise $\ge 30\text{ mmHg}$ (`BP_CHANGE_MARKED_MMHG = 30.0`) $\rightarrow$ **Urgent**
     - Rise $\ge 20\text{ mmHg}$ with symptoms or orthostatic dizziness $\rightarrow$ **Urgent**
     - Rise $\ge 20\text{ mmHg}$ without symptoms $\rightarrow$ **Review**
   - *Guideline*: NICE NG136 (Blood pressure variability and monitoring); BHS Guidelines.

---

## 3. Intentional Exclusions (Prototype Boundaries)

The following clinical domains are intentionally excluded from this prototype version:
1. **Insulin Titration / Bolus Calculation**: The system explicitly avoids computing insulin-to-carbohydrate ratios or correction factors. Titration requires clinician oversight and certified medical device classification (SaMD / FDA Class II/III).
2. **Paediatric Patients ($< 18$ years)**: Paediatric diabetes and hypertension follow distinct physiological curves, developmental milestones, and specialist regimens.
3. **Pregnancy & Gestational Conditions**: Preeclampsia, eclampsia, and gestational diabetes require specialized obstetric triage algorithms.
4. **End-Stage Renal Disease (ESRD) & Dialysis**: Hemodialysis shifts fluid balance and vital sign dynamics outside standard ambulatory baseline models.
5. **Direct Diagnostic Classification**: The prototype does not assign new diagnostic ICD-10 codes or assert clinical diagnosis.

---

## 4. Codebase Constants Reference Table

The table below catalogs every constant defined in `agents/triage_protocol.py` and `agents/adaptive_interview_agent.py`:

| Constant Name | Value | Unit | Meaning & Clinical Function | Guideline / Authority Reference |
|---|---|---|---|---|
| `MIN_ADULT_AGE` | 18 | years | Minimum eligible patient age for standard adult protocols | NICE NG136, ADA Standards of Care |
| `OLDER_ADULT_AGE` | 65 | years | Threshold for older adult fall/orthostatic risk extensions | NICE CG161, WHO Ageing Clinical Care |
| `MAX_PLAUSIBLE_AGE` | 120 | years | Upper bound for physiological human lifespan validation | Demographics & Health Data Quality Standards |
| `BP_STAGE2_SYSTOLIC_MMHG` | 180.0 | mmHg | Systolic threshold for hypertensive crisis range | ACC/AHA 2017 High Blood Pressure Guideline |
| `BP_STAGE2_DIASTOLIC_MMHG` | 120.0 | mmHg | Diastolic threshold for hypertensive crisis range | ACC/AHA 2017 High Blood Pressure Guideline |
| `BP_LOW_SYSTOLIC_MMHG` | 90.0 | mmHg | Systolic threshold defining symptomatic hypotension | WHO Guidelines, British Hypertension Society |
| `BP_LOW_DIASTOLIC_MMHG` | 60.0 | mmHg | Diastolic threshold defining symptomatic hypotension | WHO Guidelines, British Hypertension Society |
| `BP_CHANGE_NOTABLE_MMHG` | 20.0 | mmHg | Systolic increase above baseline initiating change protocol | NICE NG136 Monitoring Blood Pressure |
| `BP_CHANGE_MARKED_MMHG` | 30.0 | mmHg | Marked systolic increase indicating urgent review | NICE NG136, AHA Scientific Statement |
| `BASELINE_MIN_READINGS` | 3 | count | Minimum completed readings required to compute valid baseline | Statistical median stability standard |
| `BASELINE_MAX_READINGS` | 7 | count | Maximum recent readings window utilized for baseline calculation | Moving-window standard in ambulatory vitals |
| `BASELINE_WINDOW_DAYS` | 14 | days | Lookback temporal cutoff for personal baseline observations | NICE NG136 (14-day ambulatory monitoring) |
| `GLUCOSE_HIGH_MG_DL` | 250.0 | mg/dL | Hyperglycemia threshold for DKA/HHS warning protocol | ADA Standards of Care (Chapter 6, Table 6.1) |
| `GLUCOSE_URGENT_MG_DL` | 300.0 | mg/dL | Severe asymptomatic hyperglycemia requiring urgent clinical review | ADA Standards of Care (Glycemic Management) |
| `GLUCOSE_LOW_MG_DL` | 70.0 | mg/dL | Level 1 Hypoglycemia threshold initiating Rule of 15 protocol | ADA Standards of Care (Chapter 6: Hypoglycemia) |
| `GLUCOSE_VERY_LOW_MG_DL` | 54.0 | mg/dL | Level 2 Clinically Significant Hypoglycemia threshold | ADA Standards of Care / International Hypoglycemia Group |
| `SYSTOLIC` | "blood_pressure_systolic" | string | Observation type identifier for systolic blood pressure | LOINC 8480-6 / FHIR Observation standard |
| `DIASTOLIC` | "blood_pressure_diastolic" | string | Observation type identifier for diastolic blood pressure | LOINC 8462-4 / FHIR Observation standard |
| `GLUCOSE` | "glucose" | string | Observation type identifier for capillary blood glucose | LOINC 2339-0 / FHIR Observation standard |
| `LEVEL_RANK` | `{"routine": 0, "review": 1, "urgent": 2, "emergency": 3}` | dict | Severity hierarchy for conservative triage escalation | ChronicCare AI Decision-Support Matrix |
| `GUIDANCE` | `{"routine": ..., "review": ..., "urgent": ..., "emergency": ...}` | dict | Deterministic patient guidance templates by triage level | NHS Pathways / Clinical Triage Templates |
| `_SYMPTOMS_CRISIS` | Regex pattern | regex | Regex detecting acute organ damage / hypertensive crisis symptoms | ACC/AHA Crisis Symptom Lexicon |
| `_BP_SEVERE_QUESTIONS` | Question tuple | tuple | Step definitions and prompts for `bp_severe` protocol | Clinical Triage Protocol Definition |
| `_BP_CHANGE_QUESTIONS` | Question tuple | tuple | Step definitions and prompts for `bp_change` protocol | Clinical Triage Protocol Definition |
| `_BP_LOW_QUESTIONS` | Question tuple | tuple | Step definitions and prompts for `bp_low` protocol | Clinical Triage Protocol Definition |
| `_GLUCOSE_HIGH_QUESTIONS` | Question tuple | tuple | Step definitions and prompts for `glucose_high` protocol | Clinical Triage Protocol Definition |
| `_GLUCOSE_LOW_QUESTIONS` | Question tuple | tuple | Step definitions and prompts for `glucose_low` protocol | Clinical Triage Protocol Definition |
| `_OLDER_EXTRA` | Question definition | dict | Orthostatic dizziness / fall risk probe for older adults | NICE CG161 Falls Prevention Guideline |
| `_QUESTION_SETS` | Dictionary of question sets | dict | Registry mapping protocol identifiers to question sequences | ChronicCare AI Protocol Engine |
| `_FACTOR_PATTERNS` | Factor regex mappings | list | Clinical keyword patterns mapping to contextual review factors | Clinical Pharmacology & Adherence Lexicon |
| `_CANNOT` | Regex pattern | regex | Detection pattern for patient inability to perform action (e.g. swallow) | Patient Safety & Airway Reflex Screen |
| `_CONTRADICTION` | Regex pattern | regex | Detection pattern for conflicting affirmative/negative phrases | Conservative Linguistic Safety Screen |
| `SUPPORTED_CONDITIONS` | `("diabetes", "hypertension")` | tuple | Primary chronic disease tracks supported by the prototype | ChronicCare AI Initial Scope Specification |
| `INTERVIEW_COMPLETE` | "complete" | string | State step identifier indicating interview completion | Adaptive Interview Pipeline Architecture |
| `SELF_REPORTED_ORIGIN` | "self_reported" | string | Data origin tag indicating patient self-reported observation | Provenance & Trust Scoring Architecture |
| `GLUCOSE_RANGE_MG_DL` | `(20.0, 1000.0)` | mg/dL | Biologically plausible capillary blood glucose bounds | Clinical Pathology Reference Limits |
| `SYSTOLIC_RANGE_MMHG` | `(50.0, 300.0)` | mmHg | Biologically plausible systolic blood pressure bounds | Clinical Hemodynamic Reference Limits |
| `DIASTOLIC_RANGE_MMHG` | `(30.0, 200.0)` | mmHg | Biologically plausible diastolic blood pressure bounds | Clinical Hemodynamic Reference Limits |
| `NEGATION_WINDOW_WORDS` | 3 | count | Linguistic window for detecting red-flag negation modifiers | Clinical NLP Safety Standard |
| `DANGEROUS_BP_SYSTOLIC_MMHG` | 180.0 | mmHg | Intake screen systolic threshold triggering triage protocol | ACC/AHA 2017 Hypertensive Crisis Standard |
| `DANGEROUS_BP_DIASTOLIC_MMHG` | 120.0 | mmHg | Intake screen diastolic threshold triggering triage protocol | ACC/AHA 2017 Hypertensive Crisis Standard |
| `_NEGATION_CUES` | Regex pattern | regex | Cues negating acute red-flag symptoms | Clinical NLP Negation Dictionary |
| `_CLAUSE_BREAK` | Regex pattern | regex | Sentence and clause boundary punctuation markers | Linguistic Boundary Parser |
| `_TIME_OF_DAY` | Regex pattern | regex | Contextual markers for fasting vs post-prandial intake | Diabetes Telemetry Context Parser |
| `_NO_CUES` | Regex pattern | regex | Deterministic negative response indicators | Conservative Affirmation/Negation Parser |
| `_STRONG_YES` | Regex pattern | regex | Unambiguous affirmative response indicators | Conservative Affirmation/Negation Parser |
| `_WEAK_YES` | Regex pattern | regex | Contextual affirmative response indicators | Conservative Affirmation/Negation Parser |
| `_NO_PROBLEM` | Regex pattern | regex | Phrases indicating absence of symptoms or complaints | Clinical Symptom Screening Parser |
| `_NEGATIVE_NUMBER` | Regex pattern | regex | Regex rejecting negative numeric intake values | Data Sanitization & Plausibility Guard |

---

## 5. Review & Revision History

- **2026-10-05 (Stage 7D-1)**: Initial registration of complete clinical triage rules, inclusion criteria, baseline algorithms, and codebase constants.
