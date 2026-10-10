# Simulated Patient Persona Clinical Risk Expectations

> **CLINICAL GOVERNANCE & EVALUATION PACK**
> This document lists all simulated personas that model acute or progressive clinical risks (hypoglycemia, DKA, hypertensive crisis, headache, foot ulcer, dizziness, ankle swelling, dyspnea, confusion). It compares the current engineering expectations against the active engine's evaluated triage levels.

## 1. Summary of Clinical Risk Personas
A total of **12** personas directly evaluate acute physiological risk or symptoms requiring clinical scrutiny.

| Persona ID | Archetype | Clinical Risk / Manifestation | Current File `expected_level` | Engine Assigned Level | Clinician Expected Level | Clinical Status / Gap Notes |
|:---|:---|:---|:---:|:---:|:---:|:---|
| `p14_fasting_ramadan_with_low` | `fasting_low` | Fasting Hypoglycemia (58 mg/dL, Fast Broken) | `review` | `review` | | Engine assigns review. |
| `p15_newly_diagnosed_confused_units` | `confused_units` | Confusion (Units / Medication Regimen) | `routine` | `urgent` | | Colloquial confusion vs stroke/hypo ambiguity. |
| `p22_hidden_danger_phrase_long_text` | `hidden_danger` | Crushing Chest Pain in Long Text | `emergency` | `emergency` | | Correctly escalated to emergency on Turn 1. |
| `p35_hypertensive_crisis_emergency` | `crisis_bp` | Hypertensive Crisis (BP 210/120) | `emergency` | `emergency` | | Correctly escalated to emergency on Turn 1. |
| `p36_severe_hypo_urgent` | `severe_hypo` | Acute Severe Hypoglycemia (48 mg/dL + Shaking) | `urgent` | `emergency` | | Engine escalates to emergency; file expected urgent. |
| `p37_dka_sick_day_emergency` | `dka_sick_day` | DKA (High Glucose + Vomiting) | `emergency` | `emergency` | | Correctly escalated to emergency on Turn 1. |
| `p43_htn_severe_headache` | `htn_headache` | Hypertension with Severe Headache | `review` | `routine` | | GAP: Normal vitals leave reading at routine; clinician review expected. |
| `p44_diabetic_foot_ulcer` | `foot_ulcer` | Diabetic Foot Ulcer / Bleeding Toe Wound | `review` | `routine` | | GAP: Normal vitals leave reading at routine; clinician review expected. |
| `p45_orthostatic_dizziness` | `orthostatic_dizzy` | Orthostatic Postural Dizziness / Fall Risk | `review` | `routine` | | GAP: Normal vitals leave reading at routine; clinician review expected. |
| `p49_roman_urdu_hypo_insulin` | `roman_urdu_hypo` | Hypoglycemia on Insulin (Roman Urdu) | `review` | `review` | | Engine assigns review. |
| `p51_dyspnea_exertion` | `dyspnea_exertion` | Dyspnea on Exertion | `routine` | `routine` | | Normal vitals leave reading at routine. |
| `p52_swollen_ankles_salty_diet` | `swollen_ankles` | Bilateral Ankle Edema / High Sodium | `review` | `routine` | | GAP: Normal vitals leave reading at routine; clinician review expected. |

## 2. Key Observations for the Reviewing Clinician
1. **The 'Normal Vitals' Narrative Gap**: Personas reporting acute symptomatic pathology (diabetic foot ulcer `p44`, severe hypertensive headache `p43`, orthostatic dizziness `p45`, swollen ankles `p52`) currently finish as `routine` when blood pressure and glucose readings are physiologically normal. The clinician must establish whether affirmative symptom reports must override normal vitals to assign `review` or `urgent`.
2. **Severe Hypoglycemia Target**: Persona `p36_severe_hypo_urgent` tests a reading of 48 mg/dL with acute tremor and diaphoresis. The file expected level was `urgent`, but the engine escalated to `emergency`. The clinician should confirm whether glucose < 54 mg/dL with acute neuroglycopenic symptoms should be categorized as `emergency` (911 ambulance) or `urgent` (immediate clinic contact).
3. **Elderly Conversational Confusion (`p46`)**: Persona `p46_elderly_complex_meds` states *'Feeling a bit confused by all my morning pills'*. This triggers the bare `confusion` emergency red flag. Clinician guidance is requested on the three options presented in `CLINICIAN_REVIEW_PACK.md`.

## 3. Clinical Governance Sign-Off

| Clinician Name | License # / Hospital | Signature | Date | Overall Decision |
|:---|:---|:---|:---|:---|
| | | | | |
