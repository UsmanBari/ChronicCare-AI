# ChronicCare AI — Clinician Review & Decision Pack

> **CLINICAL DISCLAIMER & SAFETY NOTICE**
> **IMPORTANT**: Nothing in this repository or prototype has been clinically validated, approved by regulatory bodies (e.g., FDA, MHRA, CE), or trialed on real human patients. This document is an engineering decision-support pack prepared for clinical review by licensed medical practitioners.

## 1. Level-Raising Rules (Interview Engine v2.3)
The clinical intake interview protocol operates four categorical triage levels: `routine`, `review`, `urgent`, and `emergency`.

| Trigger Condition | Protocol Rule / Node | Target Level | Clinical Rationale |
|:---|:---|:---:|:---|
| Red-Flag Danger Screen Match | Stage 1 Emergency Screen (`run_stage1_red_flag_screen`) | `emergency` | Immediate safety danger hard-stop (e.g. crushing chest pain, inability to keep fluids down, stroke symptoms). |
| Severe Hypoglycemia (< 54 mg/dL or < 3.0 mmol/L) | `evaluate_triage_decision` | `urgent` | Critical neuroglycopenic risk requiring urgent carbohydrate rescue and clinical escalation. |
| Moderate Hypoglycemia (54 - 69 mg/dL or 3.0 - 3.8 mmol/L) | `evaluate_triage_decision` | `review` | Biochemical low sugar; requires adherence review and preventive guidance. |
| Severe Hyperglycemia / Crisis (>= 300 mg/dL or >= 16.7 mmol/L) | `evaluate_triage_decision` | `urgent` | Severe acute hyperglycemia requiring clinical investigation for dehydration or hyperosmolarity. |
| Moderate Hyperglycemia (>= 250 mg/dL or >= 13.9 mmol/L) | `evaluate_triage_decision` | `review` | Elevated reading triggering sick-day protocol check and provider notification. |
| Hypertensive Crisis (BP >= 180/120 mmHg) | `evaluate_triage_decision` | `emergency` | Immediate hypertensive emergency / urgency threshold. |
| Stage 2 Hypertension (BP >= 140/90 mmHg) | `evaluate_triage_decision` | `review` | Elevated blood pressure triggering OTC medication screening and clinician review. |
| Reported Medication Non-Adherence | `ADHERENCE` Step | `review` | Missed medication doses flag provider review queue for adherence barrier evaluation. |
| Possible Severe Low with Inability to Swallow Safely | `FAST_HYPO_SAFETY` Step | `urgent` | Hypoglycemic patient reporting inability to safely eat or drink. |

## 2. Glucose Unit Rules, Conversion Thresholds & Truth Table
Automated extraction parses both explicit units (`mg/dL`, `mmol/L`) and bare numbers based on physiological ranges:
- Values < 25 without explicit units are inferred as `mmol/L` (or clarified) and converted via multiplication by 18.0182.
- Values >= 25 are treated as `mg/dL`.
- Hypoglycemia thresholds: Level 2 severe low < 54 mg/dL (< 3.0 mmol/L); Level 1 low < 70 mg/dL (< 3.9 mmol/L).

### Monotonic Truth Table (Live API Output)
| Series | Glucose Input | Converted mg/dL | Final Level | Rank | Monotonic / Valid? | API Reasons |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `bare_number` | `35` | 35.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `35 mg/dL` | 35.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mmol` | `2.0 mmol/L` | 36.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `45` | 45.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `45 mg/dL` | 45.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mmol` | `2.8 mmol/L` | 50.4 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `53` | 53.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `53 mg/dL` | 53.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `54` | 54.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `54 mg/dL` | 54.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `explicit_mmol` | `3.0 mmol/L` | 54.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `bare_number` | `55` | 55.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `55 mg/dL` | 55.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `explicit_mmol` | `3.8 mmol/L` | 68.4 | `review` | 1 | OK | Glucose is low. |
| `bare_number` | `69` | 69.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `69 mg/dL` | 69.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `bare_number` | `70` | 70.0 | `routine` | 0 | OK | (none) |
| `explicit_mgdl` | `70 mg/dL` | 70.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| `bare_number` | `126` | 126.0 | `routine` | 0 | OK | (none) |
| `explicit_mgdl` | `126 mg/dL` | 126.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| `explicit_mmol` | `7.0 mmol/L` | 126.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| Series | Glucose Input | Converted mg/dL | Final Level | Rank | Monotonic / Valid? | API Reasons |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `bare_number` | `35` | 35.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `35 mg/dL` | 35.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mmol` | `2.0 mmol/L` | 36.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `45` | 45.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `45 mg/dL` | 45.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mmol` | `2.8 mmol/L` | 50.4 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `53` | 53.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `53 mg/dL` | 53.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `54` | 54.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `54 mg/dL` | 54.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `explicit_mmol` | `3.0 mmol/L` | 54.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `bare_number` | `55` | 55.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `55 mg/dL` | 55.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `explicit_mmol` | `3.8 mmol/L` | 68.4 | `review` | 1 | OK | Glucose is low. |
| `bare_number` | `69` | 69.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `69 mg/dL` | 69.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `bare_number` | `70` | 70.0 | `routine` | 0 | OK | (none) |
| `explicit_mgdl` | `70 mg/dL` | 70.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| `bare_number` | `126` | 126.0 | `routine` | 0 | OK | (none) |
| `explicit_mgdl` | `126 mg/dL` | 126.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| `explicit_mmol` | `7.0 mmol/L` | 126.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| Series | Glucose Input | Converted mg/dL | Final Level | Rank | Monotonic / Valid? | API Reasons |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `bare_number` | `35` | 35.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `35 mg/dL` | 35.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mmol` | `2.0 mmol/L` | 36.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `45` | 45.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `45 mg/dL` | 45.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mmol` | `2.8 mmol/L` | 50.4 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `53` | 53.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL. |
| `explicit_mgdl` | `53 mg/dL` | 53.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL. |
| `bare_number` | `54` | 54.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `54 mg/dL` | 54.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `explicit_mmol` | `3.0 mmol/L` | 54.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `bare_number` | `55` | 55.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `55 mg/dL` | 55.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `explicit_mmol` | `3.8 mmol/L` | 68.4 | `review` | 1 | OK | Glucose is low. |
| `bare_number` | `69` | 69.0 | `review` | 1 | OK | Glucose is low. |
| `explicit_mgdl` | `69 mg/dL` | 69.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low. |
| `bare_number` | `70` | 70.0 | `routine` | 0 | OK | (none) |
| `explicit_mgdl` | `70 mg/dL` | 70.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| `bare_number` | `126` | 126.0 | `routine` | 0 | OK | (none) |
| `explicit_mgdl` | `126 mg/dL` | 126.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| `explicit_mmol` | `7.0 mmol/L` | 126.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| Series | Glucose Input | Converted mg/dL | Final Level | Rank | Monotonic / Valid? | API Reasons |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `bare_number` | `35` | 35.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL.; Symptoms of low glucose. |
| `explicit_mgdl` | `35 mg/dL` | 35.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL.; Symptoms of low glucose. |
| `explicit_mmol` | `2.0 mmol/L` | 36.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL.; Symptoms of low glucose. |
| `bare_number` | `45` | 45.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL.; Symptoms of low glucose. |
| `explicit_mgdl` | `45 mg/dL` | 45.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL.; Symptoms of low glucose. |
| `explicit_mmol` | `2.8 mmol/L` | 50.4 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL.; Symptoms of low glucose. |
| `bare_number` | `53` | 53.0 | `urgent` | 2 | OK | Glucose is low.; Glucose is below 54 mg/dL.; Symptoms of low glucose. |
| `explicit_mgdl` | `53 mg/dL` | 53.0 | `urgent` | 2 | EQUIVALENT (OK) | Glucose is low.; Glucose is below 54 mg/dL.; Symptoms of low glucose. |
| `bare_number` | `54` | 54.0 | `review` | 1 | OK | Glucose is low.; Symptoms of low glucose. |
| `explicit_mgdl` | `54 mg/dL` | 54.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low.; Symptoms of low glucose. |
| `explicit_mmol` | `3.0 mmol/L` | 54.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low.; Symptoms of low glucose. |
| `bare_number` | `55` | 55.0 | `review` | 1 | OK | Glucose is low.; Symptoms of low glucose. |
| `explicit_mgdl` | `55 mg/dL` | 55.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low.; Symptoms of low glucose. |
| `explicit_mmol` | `3.8 mmol/L` | 68.4 | `review` | 1 | OK | Glucose is low.; Symptoms of low glucose. |
| `bare_number` | `69` | 69.0 | `review` | 1 | OK | Glucose is low.; Symptoms of low glucose. |
| `explicit_mgdl` | `69 mg/dL` | 69.0 | `review` | 1 | EQUIVALENT (OK) | Glucose is low.; Symptoms of low glucose. |
| `bare_number` | `70` | 70.0 | `routine` | 0 | OK | (none) |
| `explicit_mgdl` | `70 mg/dL` | 70.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| `bare_number` | `126` | 126.0 | `routine` | 0 | OK | (none) |
| `explicit_mgdl` | `126 mg/dL` | 126.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |
| `explicit_mmol` | `7.0 mmol/L` | 126.0 | `routine` | 0 | EQUIVALENT (OK) | (none) |

## 3. Vomiting & Fluids Inability Red-Flag Phrases (`unable_to_keep_fluids`)
Authoritative phrases configured in `adaptive_interview_agent.py` to trigger immediate emergency safety stop:
| Language | Configured Verbatim Phrase | Category |
|:---|:---|:---:|
| English (en) | "can't keep anything down" | `unable_to_keep_fluids` |
| English (en) | "cant keep anything down" | `unable_to_keep_fluids` |
| English (en) | "cannot keep anything down" | `unable_to_keep_fluids` |
| English (en) | "can not keep anything down" | `unable_to_keep_fluids` |
| English (en) | "unable to keep anything down" | `unable_to_keep_fluids` |
| English (en) | "not able to keep anything down" | `unable_to_keep_fluids` |
| English (en) | "can't keep fluids down" | `unable_to_keep_fluids` |
| English (en) | "cant keep fluids down" | `unable_to_keep_fluids` |
| English (en) | "cannot keep fluids down" | `unable_to_keep_fluids` |
| English (en) | "can not keep fluids down" | `unable_to_keep_fluids` |
| English (en) | "unable to keep fluids down" | `unable_to_keep_fluids` |
| English (en) | "not able to keep fluids down" | `unable_to_keep_fluids` |
| English (en) | "can't keep water down" | `unable_to_keep_fluids` |
| English (en) | "cant keep water down" | `unable_to_keep_fluids` |
| English (en) | "cannot keep water down" | `unable_to_keep_fluids` |
| English (en) | "can not keep water down" | `unable_to_keep_fluids` |
| English (en) | "won't stay down" | `unable_to_keep_fluids` |
| English (en) | "wont stay down" | `unable_to_keep_fluids` |
| English (en) | "throwing up everything" | `unable_to_keep_fluids` |
| English (en) | "keep nothing down" | `unable_to_keep_fluids` |
| English (en) | "vomiting all day" | `unable_to_keep_fluids` |
| English (en) | "vomiting nonstop" | `unable_to_keep_fluids` |
| English (en) | "vomiting non-stop" | `unable_to_keep_fluids` |
| English (en) | "vomiting with high sugar" | `unable_to_keep_fluids` |
| Roman Urdu (ur-Latn) | "musalsal ultiyan" | `unable_to_keep_fluids` |
| Roman Urdu (ur-Latn) | "ulti ruk nahi rahi" | `unable_to_keep_fluids` |
| Roman Urdu (ur-Latn) | "paani bhi nahi rukta" | `unable_to_keep_fluids` |
| Urdu Script (ur) | "مسلسل الٹیاں" | `unable_to_keep_fluids` |
| Urdu Script (ur) | "الٹی رک نہیں رہی" | `unable_to_keep_fluids` |
| Urdu Script (ur) | "پانی بھی نہیں رک رہا" | `unable_to_keep_fluids` |

**Negation Handling**: Negations (e.g., *"I am not vomiting"*, *"no vomiting, I can keep fluids down"*, *"without vomiting"*) are verified by a 3-word negation window and clause boundary parser. They do NOT trigger the red-flag screen.

## 4. Neurological 'Confused' Pattern — Clinician Options
Currently, `RED_FLAG_PATTERNS["confusion"]` includes `"confused"`, `"slurred speech"`, `"can't speak clearly"`.
In clinical practice, patients frequently use 'confused' colloquially (*"I am confused about my insulin dose"*) rather than reporting acute encephalopathy, stroke, or severe neuroglycopenia.

We submit three architectural options for clinician sign-off:
1. **Option 1: Strict / High Sensitivity (Current Behavior)**: Keep bare `"confused"` as an immediate emergency red-flag stop. **Advantage**: Zero risk of missing acute stroke or severe hypoglycemic confusion. **Disadvantage**: High false-positive rate for conversational confusion.
2. **Option 2: Neurological Co-occurrence Requirement**: Require co-occurrence of confusion with neurological or speech keywords (e.g. `"confused and dizzy"`, `"confused and slurred"`, `"confused and disoriented"`, `"suddenly confused"`).
3. **Option 3: Conversational Exclusion Filter**: Exclude non-neurological contexts (e.g., *"confused about [medication/dose/instructions]"*, *"confused by doctor"*) while retaining bare 'confused' in symptom descriptions.

## 5. Four Narrative-Yes Questions That Do Not Raise Triage Level (KNOWN GAP)
In Interview Engine v2.3, the following four Stage 8b questions ask narrative questions where an affirmative answer reports clinically relevant symptoms, but **does not raise the automated check-in level beyond `routine`** when blood glucose and blood pressure numbers are within normal physiological bounds:

1. `hypo_events_past_week`: Patient asked if they had low blood sugar episodes in the past week. Narrative affirmative reports are captured in the intake record, but do not promote normal glucose check-ins to `review`.
2. `sick_day_flags`: Patient asked if they have experienced nausea, fever, vomiting, or illness. Narrative reports are recorded, but do not promote the check-in level unless matched verbatim by Stage 1 emergency red flags.
3. `associated_symptoms`: Patient asked if they have headaches, dizziness, or visual changes with blood pressure. Answering 'yes, mild headache' records the text, but leaves triage at `routine` if BP is normal.
4. `foot_problems`: Patient asked about foot ulcers, numbness, cuts, or sores. Reporting a cut or sore records the note in the clinical intake, but does not promote the level to `review` or `urgent`.

> **Doctor Action Required**: Clinicians must specify whether affirmative responses to these four questions should automatically promote check-ins from `routine` to `review` (or `urgent`).

## 6. Input Triage Known Misses & Intentional Over-Triage
Evaluation of input triage over `tests/sim/odd_input_gold.json` demonstrates:
- **Romantic Miss Fixed**: *"You are so cute and hot"* was formerly missed; now authoritatively classified as `odd_input` (`romantic`).
- **Dose Advice Request Fixed**: *"Can I stop taking metformin since my sugar is normal?"* was formerly missed; now authoritatively classified as `odd_input` (`medical_advice_dose_request`).
- **Non-Answer Phrases ('ok', 'haan', 'acha theek')**: In isolated benchmark files without dialogue context, these appear labeled as `non_answer`. However, in live clinical dialogues, they represent affirmative confirmations to yes/no questions (e.g., adherence confirmation). They are intentionally not flagged as odd inputs globally to avoid corrupting valid clinical dialogues.
- **Intentional Safety Over-Triage**: *"chest pain last year but fine now"* is classified as `danger_phrase` (`emergency`). Automated negation engines deliberately avoid temporal discounting of chest pain to ensure that historical cardiac complaints are never dangerously under-triaged.

## 7. Clinician Sign-Off & Governance Record
To be completed by reviewing clinical practitioners:

| Review Item | Reviewer Name | Professional Title / GMC / Reg | Date | Clinical Decision (Approve / Reject / Modify) | Signature / Notes |
|:---|:---|:---|:---:|:---:|:---|
| Glucose Unit Inference & Thresholds | | | | | |
| Vomiting / Inability to Keep Fluids Red Flags | | | | | |
| 'Confused' Pattern Option (1, 2, or 3) | | | | | |
| Narrative-Yes 4-Question Promotion Rule | | | | | |
| Input Triage Safety Over-Triage Policy | | | | | |
