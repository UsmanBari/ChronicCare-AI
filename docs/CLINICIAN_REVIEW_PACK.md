# ChronicCare AI — Clinician Review & Decision Pack

> **CLINICAL DISCLAIMER & SAFETY NOTICE**
> **IMPORTANT**: Nothing in this repository or prototype has been clinically validated, approved by regulatory bodies (e.g., FDA, MHRA, CE), or trialed on real human patients. This document is an engineering decision-support pack prepared for clinical review by licensed medical practitioners.

## 1. Glucose Triage Thresholds & Unit Conversion
Automated extraction parses both explicit units (`mg/dL`, `mmol/L`) and bare numbers based on physiological ranges:
- Conversion formula: `mmol/L * 18.0 = mg/dL`.
- Values < 25 without explicit units are inferred as `mmol/L` (or clarified) and converted via multiplication by 18.0.
- Values >= 25 are treated as `mg/dL`.
- Thresholds: Very low glucose < 54 mg/dL (< 3.0 mmol/L); Low glucose < 70 mg/dL (< 3.9 mmol/L); High glucose >= 250 mg/dL (>= 13.9 mmol/L); Urgent high glucose >= 300 mg/dL (>= 16.7 mmol/L).

| Clinical Glucose Band | Code Constant | Triage Level | Clinical Action / Rationale |
|:---|:---|:---:|:---|
| Severe Hypoglycemia (< 54 mg/dL) | `GLUCOSE_VERY_LOW_MG_DL = 54` | `urgent` | Very low glucose without acute neuro symptoms triggers urgent clinician contact today. If neuro symptoms (confusion/drowsiness) or unable to swallow, escalates to `emergency`. |
| Low Glucose (54 - 69 mg/dL) | `GLUCOSE_LOW_MG_DL = 70` | `review` | Biochemical low glucose; requires provider review and fasting/medication inquiry. |
| Severe Hyperglycemia (>= 300 mg/dL) | `GLUCOSE_URGENT_MG_DL = 300` | `urgent` | Severe hyperglycemia without acute DKA symptoms flags urgent clinician contact. If DKA symptoms (vomiting, fruity breath, hyperventilation) present, escalates to `emergency`. |
| Elevated Glucose (>= 250 mg/dL) | `GLUCOSE_HIGH_MG_DL = 250` | `review` | Elevated glucose triggering provider review queue and hydration inquiry. |

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

## 2. Blood Pressure Triage Thresholds
| Clinical BP Band | Code Constant | Triage Level | Clinical Action / Rationale |
|:---|:---|:---:|:---|
| Hypertensive Crisis (>= 180/120 mmHg) | `DANGEROUS_BP_SYSTOLIC_MMHG = 180`, `DANGEROUS_BP_DIASTOLIC_MMHG = 120` | `emergency` / `urgent` | With warning symptoms: immediate `emergency`. Asymptomatic after rest: `urgent` (requires same-day contact). |
| Stage 2 Hypertension (>= 140/90 mmHg) | `BP_STAGE2_SYSTOLIC_MMHG = 140`, `BP_STAGE2_DIASTOLIC_MMHG = 90` | `review` | Elevated blood pressure triggering OTC medication screening and clinician review. |
| Low Blood Pressure (< 90/60 mmHg) | `BP_LOW_SYSTOLIC_MMHG = 90`, `BP_LOW_DIASTOLIC_MMHG = 60` | `urgent` / `review` | Hypotension with dizziness or falls flags `urgent`; asymptomatic flags `review`. |
| BP Shift Above Baseline (>= 40 mmHg marked, >= 20 mmHg notable) | `BP_CHANGE_MARKED_MMHG = 40`, `BP_CHANGE_NOTABLE_MMHG = 20` | `urgent` / `review` | Notable departure from 14-day median baseline. |

## 3. Red Flag Symptoms & Escalations (Live API Results)
The clinical triage engine categorizes red flags deterministically based on live API evaluations:

- **Immediate Emergency (`emergency`)**:
  - Chest pain, tightness, heaviness (`chest_pain`): immediate lockout -> `emergency`
  - Shortness of breath, gasping (`breathing`): immediate lockout -> `emergency`
  - Loss of consciousness, blacking out (`loss_of_consciousness`): immediate lockout -> `emergency`
  - Sudden one-sided weakness, facial drooping (`one_sided_weakness`): immediate lockout -> `emergency`
  - Inability to keep fluids down (`unable_to_keep_fluids`): triggers Stage 1 red flag screen -> immediate lockout -> `emergency`
  - Severe hypoglycemia (< 54 mg/dL) WITH neuro symptoms (`neuro = True`): protocol evaluation -> `emergency`
  - Severe hypoglycemia (< 54 mg/dL) and UNABLE to swallow safely (`can_swallow = False`): protocol evaluation -> `emergency`
  - Hypertensive crisis (>= 180/120 mmHg) WITH warning symptoms: protocol evaluation -> `emergency`
  - Severe hyperglycemia (>= 250 mg/dL) WITH DKA symptoms: protocol evaluation -> `emergency`

- **Urgent Escalations (`urgent`)**:
  - Severe hypoglycemia (< 54 mg/dL) WITHOUT neuro symptoms (`neuro = False`, `can_swallow = True`): protocol evaluation -> `urgent` (same-day clinician contact)
  - Severe hyperglycemia (>= 300 mg/dL) WITHOUT DKA symptoms: protocol evaluation -> `urgent`
  - Hypertensive crisis (>= 180/120 mmHg) without acute end-organ symptoms: protocol evaluation -> `urgent`

## 4. Vomiting & Fluids Inability Red-Flag Phrases (`unable_to_keep_fluids`)
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

## 5. Neurological 'Confused' Pattern — Clinician Options
Exact pattern line in code: `backend-poc-technical/agents/adaptive_interview_agent.py:166:`
```python
    "confusion": ["confused", "slurred speech", "can't speak clearly", "cant speak clearly"],
```
Current behaviour: any message containing the word confused gives emergency.

In clinical practice, patients frequently use 'confused' colloquially (*"Feeling a bit confused by all my morning pills"*) rather than reporting acute stroke, delirium, or severe neuroglycopenia. The clinician must decide which approach to adopt:

1. **Option 1 (Keep As-Is / High Sensitivity)**: Maintain the existing conservative screen. Any mention of confusion in a diabetic/hypertensive elderly population defaults to acute stroke/hypoglycemia emergency. Advantage: Zero risk of missing acute confusion. Disadvantage: High false-alarm rate for conversational confusion.
2. **Option 2 (First-Person Syntactic Constraint)**: Require first-person neurological statements (e.g. `"I am confused"`, `"feeling disoriented"`, `"mind is foggy"`) combined with a second symptom (e.g. dizziness, slurred speech, weakness), excluding medication/regimen-specific confusion.
3. **Option 3 (Single Clarification Gate)**: When `"confused"` matches, ask one targeted clarification turn: *"Do you mean you feel mentally confused/disoriented, or are you confused about how to take your medications?"* before escalating to emergency.

## 6. Known Gaps & Limitations
### A. The Four Narrative-Yes Questions (Engine Limitation)
In the current interview flow, four clinical symptom questions record affirmative narrative findings in the patient profile, but under the Stage 8b clinical rules, they do NOT escalate the triage level if physiological vitals (glucose and BP) remain in normal range:

| Question Step | Concept / Condition | Narrative Capture | Current Escalation with Normal Vitals | Clinical Risk / Question for Clinician |
|:---|:---|:---|:---:|:---|
| `hypo_events_past_week` | Recurrent Hypoglycemia | Stored in findings | `routine` | Patient reports shaking/sweating episodes in past week. Should this escalate to `review`? |
| `sick_day_flags` | Intercurrent Illness | Stored in findings | `routine` | Patient reports mild illness without DKA red flags. Should this escalate to `review`? |
| `associated_symptoms` | Hypertension Headache / Vision | Stored in findings | `routine` | Patient reports non-crisis headache or vision blur. Should this escalate to `review`? |
| `foot_problems` | Diabetic Foot Ulcer / Wound | Stored in findings | `routine` | Patient reports open sore or blister on foot. Should this escalate to `review` or `urgent`? |

### B. Input-Triage Known Misses & Design Limits
1. **Conversational Affirmations (`ok`, `haan`, `acha theek`)**: These utterances are non-answers if presented in response to open-ended clinical questions, but serve as valid affirmative confirmations to yes/no prompts (e.g. *"Did you take your medicine?"*). They are intentionally NOT globally filtered as non-answers without dialogue context.
2. **Historical vs Active Symptoms (`chest pain last year but fine now`)**: Automated regex matching intentionally flags any mention of cardiac symptoms as safety-critical. Over-triaging historical symptoms into clinician review is an intentional safety design choice.
3. **Medication Advice Requests (`Can I stop taking metformin since my sugar is normal?`)**: Automated odd-input handler strictly refuses to provide medication advice, flags `needs_clinician_flag = True`, and routes the check-in to provider queue.

## 7. Clinical Sign-Off & Governance Record

| Item | Clinician Name | Date | Decision | Comment |
|:---|:---|:---|:---|:---|
| 1. Glucose Triage Thresholds & Conversion Factor (18.0) | | | | |
| 2. Blood Pressure Triage Thresholds | | | | |
| 3. Red Flag Symptoms & Escalation Levels | | | | |
| 4. Vomiting / Fluids Inability Phrases | | | | |
| 5. 'Confused' Pattern Handling Option (1, 2, or 3) | | | | |
| 6. Narrative-Yes 4-Question Gap (hypo, sick-day, symptoms, foot) | | | | |
| 7. Input Triage Handling (ok/haan, historical chest pain, dose requests) | | | | |
