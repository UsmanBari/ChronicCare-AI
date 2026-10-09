# Clinical Interview Protocol v2.3 Design Document

> **Proposed, not reviewed by a clinician.**
> Every question, threshold, and clinical justification in this document is proposed decision support. It is **not clinical guidance**. This document defines the adaptive question state machine for Type 2 Diabetes and Hypertension check-ins in ChronicCare AI. A qualified clinician must review and approve this document before anyone relies on it for real patients.

---

## 1. Existing Question Sets (v1.0 Baseline from Code)

The following baseline questions are currently active in `agents/adaptive_interview_agent.py`:

### 1.1 Type 2 Diabetes (Single Condition)
1. **Greeting (`greeting`)**: *"How are you feeling today? Any symptoms you'd like to report?"*
2. **Glucose Reading (`glucose_reading`)**: *"Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)?"*
3. **Missing Data Checkpoint (`missing_data_checkpoint`)** *(asked only if reading is missing/unusable)*: *"No problem. Can you tell me roughly how you've been feeling instead (for example more thirsty than usual, tired, or dizzy)? If you do have a reading, please give it in mg/dL."*
4. **Hyperglycemia Symptoms (`hyperglycemia_symptoms`)**: *"Have you noticed increased thirst, frequent urination, or blurred vision?"*
5. **Hypoglycemia Symptoms (`hypoglycemia_symptoms`)** *(asked only if on insulin or sulfonylurea)*: *"Any shakiness, sweating, or confusion that improved after eating?"*
6. **Medication Adherence (`adherence`)**: *"Have you taken your diabetes medication as prescribed today?"*
7. **Lifestyle Notes (`lifestyle`)**: *"Any changes in your diet, exercise, or stress levels recently?"*

### 1.2 Hypertension (Single Condition)
1. **Greeting (`greeting`)**: *"How are you feeling today? Any symptoms you'd like to report?"*
2. **Blood Pressure Reading (`bp_reading`)**: *"Have you measured your blood pressure today? If so, what was the reading (for example 130/85)?"*
3. **Missing Data Checkpoint (`missing_data_checkpoint`)** *(asked only if reading is missing/unusable)*: *"That's okay. Can you describe how you've been feeling instead (for example headaches, dizziness, or palpitations)? If you do have a reading, please give it like 130/85."*
4. **Associated Symptoms (`associated_symptoms`)**: *"Any dizziness, blurred vision, shortness of breath, or palpitations along with that?"*
5. **Medication Adherence (`adherence`)**: *"Did you take your blood pressure medication today?"*
6. **Lifestyle Notes (`lifestyle`)**: *"How has your sodium intake, sleep, or stress been recently?"*

### 1.3 Dual Diagnosis (Diabetes + Hypertension)
When both conditions are on file, the greeting is asked once. The diabetes branch runs through its questions, and then pivots directly to the hypertension blood pressure reading and condition-specific questions. Total questions in v1.0: 10 to 12.

---

## 2. Proposed Additions (v2.3 Extensions)

To provide richer clinical context without causing patient survey fatigue, the following questions are added adaptively. The hard safety rule is maintained: **New questions can only add INFORMATION for the clinician or RAISE the review/triage level. No new question may ever lower a level set by existing rules.**

| # | Question Key | Exact Patient-Facing Wording | Clinical Rationale & Guideline Citation | Usage & Level Impact | Answer Type | Handling of Skip / "I don't know" | Flow & Length Impact |
|---|---|---|---|---|---|---|---|
| 1 | `glucose_context` | *"Was this blood sugar reading fasting (before breakfast), before a meal, after a meal, or at bedtime?"* | The clinical interpretation of glucose differs fundamentally between fasting (< 100-130 mg/dL target) and postprandial (< 180 mg/dL target). *Source: ADA Standards of Care 2026 (title exists, claim not checked; clinician review needed)* | **INFORMATION ONLY** for clinician review. Recorded in intake details. | Choice / Keyword: `fasting`, `before_meal`, `after_meal`, `bedtime`, `random` | Recorded as `unspecified`; does not block flow. | Adds 1 question to diabetes flow when a reading was provided. |
| 2 | `hypo_events_past_week` | *"In the past 7 days, have you had any low blood sugar episodes, like sudden shakiness, cold sweat, or feeling faint?"* | Recurring hypoglycemia is a key risk factor for severe hypoglycemia, falls, and cardiovascular events. *Source: ADA Standards of Care 2026 (title exists, claim not checked; clinician review needed)* | **RAISES LEVEL**: If patient reports recurrent or severe lows, raises attention to **review** or **urgent** if accompanied by disorientation. | Yes / No / Count | Recorded as `unknown`; does not penalize. | Asked only if on insulin/sulfonylurea or if glucose is low (< 70 mg/dL). |
| 3 | `sick_day_flags` | *"Are you currently experiencing vomiting, diarrhoea, high fever, or unable to drink fluids?"* | In acute illness, patients with diabetes face heightened risk of diabetic ketoacidosis (DKA) or hyperosmolar hyperglycemic state (HHS). *Source: NICE NG28; ADA Standards of Care 2026 (clinician review needed)* | **RAISES LEVEL**: Vomiting with high reading triggers triage emergency or urgent escalation. | Yes / No / Free text | Evaluated for red-flag cues; "no" continues. | Asked when glucose >= 250 mg/dL or during missing data checkpoint. |
| 4 | `diabetes_symptoms_check` | *"Have you noticed significant increased thirst, passing urine much more often, unusual tiredness, or blurry vision in the last few days?"* | Classic osmotic symptoms of persistent hyperglycemia indicate worsening glycemic control. *Source: ADA Standards of Care 2026; clinician review needed* | **INFORMATION / RAISES TO REVIEW** if multiple classic symptoms present. | Yes / No / Details | Recorded as `unknown`; continues. | Replaces or refines generic hyperglycemia prompt. |
| 5 | `foot_problems` | *"Do you have any new cuts, sores, blisters, pain, or numbness in your feet?"* | Diabetic foot ulcers and peripheral neuropathy can progress rapidly to severe infections or limb-threatening complications. *Source: ADA Standards of Care 2026 (Microvascular Complications and Foot Care; clinician review needed)* | **INFORMATION / RAISES TO REVIEW**: Noted as high-priority item on provider card if open wound or numbness reported. | Yes / No / Free text | Recorded as `no_reported_foot_issues`; continues. | Adds 1 question to diabetes flow. |
| 6 | `bp_technique` | *"Before taking your blood pressure, did you rest quietly for 5 minutes with your back and arm supported?"* | Blood pressure measurement technique significantly affects readings (talking, full bladder, lack of rest adds 5-15 mmHg). *Source: 2025 AHA/ACC Hypertension Guideline; ESC/ESH (clinician review needed)* | **INFORMATION ONLY**: Informs clinician whether the home reading strictly adhered to standard measurement protocol. | Yes / No / Skipped | Recorded as `unconfirmed_technique`; continues. | Asked immediately after BP reading entry (adds 1 question). |
| 7 | `bp_symptoms_extended` | *"Do you have a severe headache, shortness of breath, ankle swelling, or dizziness when standing up?"* | Differentiates asymptomatic hypertension from hypertensive urgency/emergency and postural hypotension. *Source: 2025 AHA/ACC Guideline; NICE NG136 (clinician review needed)* | **RAISES LEVEL**: Shortness of breath or severe headache with high BP escalates to **urgent/emergency**. Orthostatic dizziness in older adults alerts for overmedication/fall risk. | Yes / No / Symptoms | Screened for danger phrases; "no" continues. | Consolidates hypertension symptom checks into 1 targeted question. |
| 8 | `otc_meds_bp` | *"Have you taken any anti-inflammatory painkillers (like ibuprofen), cold/decongestant medicines, or herbal supplements recently?"* | NSAIDs and sympathomimetic decongestants frequently induce acute elevations in blood pressure and interfere with antihypertensive regimens. *Source: 2025 AHA/ACC Guidelines (clinician review needed)* | **INFORMATION ONLY**: Flags reversible drug-induced hypertension on provider card. | Yes / No / Free text | Recorded as `none_reported`; continues. | Asked when BP is elevated (systolic >= 140 or diastolic >= 90). |
| 9 | `lifestyle_sleep_stress` | *"How has your sleep and stress level been over the past few days, and did you have any alcohol or extra salt?"* | Poor sleep (sleep apnea, insomnia) and acute psychosocial stress acutely elevate sympathetic tone and blood pressure. *Source: 2025 AHA/ACC Guidelines; clinician review needed* | **INFORMATION ONLY**: Contextualizes labile or stress-induced elevations. | Short text / Skip | Skipped easily; default null. | Combines lifestyle notes into 1 concise question. |
| 10 | `patient_free_text_note` | *"Is there anything else you would like your clinician to know about your health today?"* | Patient-centered communication: allows patients to express concerns not covered by structured prompts. *Source: NICE CG138 (Patient Experience in Adult NHS Services; clinician review needed)* | **INFORMATION / SCREENED FOR RED FLAGS**: Free text is screened by Stage 1 red-flag parser and passed verbatim to provider triage note. | Free text (up to 500 chars) | Optional / Blank continues immediately. | Final question of the interview. |

---

## 3. Interview Length & Skip Optimization

To prevent excessive questions, the adaptive tree uses strict branch skipping:
- **Maximum Questions in Any Single Interview**: <= 10 questions for single condition; <= 14 questions for dual diagnosis.
- **Fast-Path Optimization**:
  - `glucose_context` is skipped if no glucose reading was entered.
  - `hypo_events_past_week` is skipped if patient is not on insulin/sulfonylurea and reading is normal.
  - `otc_meds_bp` is skipped if blood pressure reading is normal (< 130/80 mmHg).
  - Every non-reading question accepts `"skip"`, `"no"`, or `"I don't know"`, moving forward immediately.

---

## 4. Approved Emergency Phrases List & Validation Rules

Stage 1 Red-Flag screening runs on **every single answer**, including all new question answers and free text. The list of approved emergency categories and trigger phrases is strictly governed:

### 4.1 Approved Trigger Patterns
1. **`chest_pain`**:
   - Phrases: `"chest pain"`, `"chest tightness"`, `"chest pressure"`, `"chest hurts"`, `"pain in my chest"`, `"crushing chest"`, `"crushing chest pain"`, `"heavy chest"`, `"سینے میں درد"`
   - Negations (must NOT trigger): `"no chest pain"`, `"not having chest pain"`, `"never had chest pain"`, `"without any chest pain"`
   - False Positives (must NOT trigger): `"chest pain resolved 3 years ago"`, `"my brother had chest pain"`
2. **`breathing`**:
   - Phrases: `"can't breathe"`, `"cant breathe"`, `"cannot breathe"`, `"struggling to breathe"`, `"severe shortness of breath"`, `"gasping for air"`, `"suffocating"`, `"سانس لینے میں دشواری"`, `"سانس نہیں آ رہی"`
   - Negations (must NOT trigger): `"no trouble breathing"`, `"not short of breath"`, `"not struggling to breathe"`
   - False Positives (must NOT trigger): `"breathed deeply"`, `"no shortness of breath"`
3. **`confusion_and_stroke`**:
   - Phrases: `"slurred speech"`, `"can't speak clearly"`, `"cant speak clearly"`, `"face drooping"`, `"one side weak"`, `"one-sided weakness"`, `"can't move my arm"`, `"cant move one side"`
   - Negations (must NOT trigger): `"no slurred speech"`, `"speech is not slurred"`, `"no weakness"`
   - False Positives (must NOT trigger): `"confused about my appointment date"`
4. **`loss_of_consciousness`**:
   - Phrases: `"fainted"`, `"passed out"`, `"lost consciousness"`, `"blacked out"`, `"collapsed"`, `"بے ہوش"`
   - Negations (must NOT trigger): `"never fainted"`, `"did not pass out"`, `"not fainted"`
   - False Positives (must NOT trigger): `"almost bought black shoes"`, `"the room blacked out during a power cut"`
5. **`severe_headache_thunderclap`**:
   - Phrases: `"worst headache of my life"`, `"thunderclap headache"`, `"sudden severe headache"`, `"worst headache"`
   - Negations (must NOT trigger): `"no severe headache"`, `"headache is not severe"`, `"not the worst headache"`
   - False Positives (must NOT trigger): `"mild headache after reading"`
6. **`vision_loss`**:
   - Phrases: `"sudden vision loss"`, `"lost my vision"`, `"went blind"`, `"can't see at all"`, `"cannot see at all"`
   - Negations (must NOT trigger): `"vision is not lost"`, `"no vision loss"`, `"not blind"`
   - False Positives (must NOT trigger): `"need new reading glasses"`
7. **`dka_vomiting_high_glucose`**:
   - Phrases: `"vomiting nonstop"`, `"vomiting non-stop"`, `"can't keep anything down"`, `"cant keep anything down"`, `"can't keep fluids down"`, `"vomiting with high sugar"`
   - Negations (must NOT trigger): `"no vomiting"`, `"not vomiting"`, `"can keep fluids down"`
   - False Positives (must NOT trigger): `"felt a bit nauseous after breakfast yesterday"`

---

## 5. Reading Parsing & Number Validation Extensions

The parser `_try_parse_float` and `_try_parse_bp` must robustly handle:
1. **Units**:
   - If glucose is in `[3.0, 35.0]`, it is recognized as potential `mmol/L` and flagged with guidance rather than misinterpreting `7.8` as `7.8 mg/dL`.
2. **Arabic-Indic and Eastern Arabic/Urdu Numerals**:
   - Normalize `۰۱۲۳۴۵۶۷۸۹` and `٠١٢٣٤٥٦٧٨٩` to standard ASCII digits `0123456789` prior to regex matching.
3. **Varied Delimiters**:
   - BP formats accepted: `"140/90"`, `"140 / 90"`, `"140 over 90"`, `"140-90"`, `"140 90"`, `"140, 90"`.
4. **Boundary & Plausibility**:
   - Glucose: `[20.0, 600.0] mg/dL` (values > 1000 rejected as implausible).
   - Systolic: `[60, 260] mmHg` (values > 300 rejected as implausible).
   - Diastolic: `[30, 160] mmHg` (must be strictly `< systolic`).
   - Explicit negative values (`"-120"`, `"-5"`) are **never** stripped of the minus sign and are rejected as invalid numbers.
   - Comma decimals (`"7,5"`) converted to standard decimal points (`"7.5"`).
   - 0 or whitespace-only inputs return `None` (missing data checkpoint).
