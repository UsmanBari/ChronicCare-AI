# Interview Engine v3 Flow Rules

**Status:** Normative Specification  
**Engine:** v3 (`interview_planner.py`, `interview_v3_runner.py`)  
**Scope:** Adult decision-support for Type 2 Diabetes, Hypertension, and Dual Diagnosis.

---

## 1. Principles and Clinical Invariants

1. **Safety Never Compromised**: "The model proposes, the rules decide." No clinical step may ever lower a triage level, give diagnoses, or modify medication doses.
2. **Deterministic & De-duplicated**: Patients must never be asked the same clinical question or slot twice in the same check-in session.
3. **Respect Patient Burden**: For patients living with multiple comorbidities (Type 2 Diabetes and Hypertension), the check-in feels like one unified conversation, not two disjointed surveys concatenated together.

---

## 2. Core Flow Rules (R1 – R10)

### Rule R1: Safety-Class Items First
Safety priority class items (e.g., severe hypoglycemia red flags, acute chest pain or neurological red flags, acute sick-day dehydration or DKA symptoms) are always evaluated and scheduled before any routine data collection. If a severe safety trigger or danger cue fires, the interview escalates immediately without collecting subsequent routine items.

### Rule R2: Readings Second (Both Before Any Symptom)
Following safety clearance, the interview transitions directly to self-reported biometric measurements.
- For single-condition patients, the corresponding reading is collected (`glucose_reading` for diabetes, `bp_reading` for hypertension).
- For **dual-diagnosis** patients, **BOTH** readings (`glucose_reading` and `bp_reading`) must be scheduled and collected **before any symptom or contextual question** is asked.
- **Reading Order**:
  - If recent history or baseline records show that one condition was abnormal more recently (e.g., rising BP in recent check-ins or recurrent lows/highs), that reading is prioritized first.
  - Otherwise, the standard default order applies: **Glucose reading first**, followed immediately by **Blood pressure reading**.

### Rule R3: Condition Symptoms Asked Separately (`also_fills` Strict Rule)
`also_fills` is allowed ONLY when two question bank items ask the exact same clinical question in the exact same words.
- `diabetes_hyperglycemia_symptoms` asks specifically about thirst, urination, tiredness, and blurry vision.
- `hypertension_associated_symptoms` asks specifically about severe headache, shortness of breath, ankle swelling, and dizziness on standing.
Because both question sets can identify independent life-threatening or acuity-raising complications, they must NEVER be linked via `also_fills`. Dual-diagnosis patients must be evaluated for **both** condition symptom sets. De-duplication applies strictly to prevent re-asking the exact same slot twice, never by skipping different clinical questions.

### Rule R4: Medication Adherence in Dual-Diagnosis Check-ins
Currently, diabetes adherence asks about "diabetes medications" and hypertension adherence asks about "blood pressure medications". Because these address distinct prescribed regimens, an answer to one cannot automatically satisfy the other.
- Until a unified adherence question receives formal clinical approval, dual-diagnosis patients are asked BOTH adherence questions (`adherence_diabetes` and `adherence_hypertension`).

### PROPOSED — needs Usman + doctor approval
Unified multi-condition medication adherence question for dual-diagnosis patients:
- **English:** "Have you taken all your prescribed diabetes and blood pressure medications today as instructed by your doctor?"
- **Urdu:** "کیا آپ نے آج ڈاکٹر کی ہدایت کے مطابق اپنی شوگر اور بلڈ پریشر کی تمام دوائیں وقت پر لی ہیں؟"
- **Roman Urdu:** "Kya aap ne aaj doctor ki hidayat ke mutabiq apni sugar aur blood pressure ki tamam medicines le li hain?"

*Status:* PROPOSED. Until this unified phrasing receives clinician review and approval from Usman and the clinical supervisor, dual-diagnosis check-ins must ask each condition's adherence question separately (`adherence_diabetes` and `adherence_hypertension`).

### Rule R5: Lifestyle & Wellbeing Asked Once, Last
General lifestyle habits (dietary salt/carbohydrates, physical activity) and optional wellbeing screens (mood, stress, distress) are asked **once at the end of the clinical interview**, after all readings, acute symptoms, and adherence questions are concluded.

### Rule R6: Probes Drill into Newest Finding Without Repetition
Probes drill down into the most recent clinically significant finding (up to a maximum of 2 probes per finding).
- A probe slot never repeats an already answered question or slot.
- If a probe slot serves both conditions (e.g., assessing chest tightness or orthostatic dizziness), it is asked once and de-duplicated.

### Rule R7: Strict Single Budget Accounting & Accurate Progress Hint
A shared question counts as **one single question** against the session budget.
- The base budget is 8 questions; if concerning symptoms or elevated readings occur, the planner expands the budget up to 12 questions (with a hard cap of 14).
- Every turn, `session_state["progress_hint"]` displays the true asked question count and current budget:
  `f"{decision.question_count}/{decision.max_budget}"`
- Clarification re-asks or unit disambiguations do not advance the primary clinical question counter.

### Rule R8: Summary Confirmation & Targeted Correction
Before completing the check-in, the interview presents a structured summary of all captured values across both conditions in the active session language (`en`, `ur`, `roman_ur`).
- The summary explicitly lists:
  - Glucose reading (with unit and context if provided)
  - Blood pressure reading (systolic/diastolic)
  - Reported symptoms (or "None reported")
  - Medication adherence status
- The patient is offered options: "Confirm and submit" or "Need to change something".
- If the patient selects "Need to change something", the interview allows them to select **one slot to correct**, re-asks that specific slot, and then re-renders the updated summary.
- A maximum of **2 correction rounds** is permitted; thereafter, the session is submitted with a clinician review note attached.

### Rule R9: Caregiver Session Tracking & Confidence Adjustment
- Once a check-in is identified as answered by a caregiver (e.g. `answered_by="caregiver"` via explicit selection or third-party reporting), this attribute persists on the session.
- Questions utilize the caregiver phrasing variant if defined in the bank (e.g., `caregiver.json`); otherwise, the standard template is used with a session note indicating caregiver reporting.
- Downstream clinical intake confidence is automatically lowered by one level (e.g., `"High"` becomes `"Medium"`, `"Medium"` becomes `"Low"`).
- The `answered_by` attribute is preserved in the stored check-in result, returned in the `/complete` endpoint response, and surfaced in the provider review detail.

### Rule R10: Single-Condition Flow Invariance
The question sequence and triage outcomes for single-condition patients (diabetes only or hypertension only) must remain unchanged from baseline, except where explicitly updated by verified safety fixes (such as glucose unit clarification). This invariance is continuously enforced by automated equivalence tests.

---

## 3. Worked Trace Examples

### Case 1: Diabetes Only (Routine Check-in)
- **Profile**: Type 2 Diabetes on Metformin.
1. `diabetes_glucose_reading`: Patient reports `128` (fasting).
2. `diabetes_glucose_context`: Patient confirms `fasting`.
3. `diabetes_hyperglycemia_symptoms`: Patient answers "No".
4. `diabetes_foot_problems`: Patient answers "No".
5. `diabetes_adherence`: Patient answers "Yes, taking regularly".
6. `diabetes_lifestyle`: Patient answers "Walking 20 minutes daily".
7. `core_summary_confirm`: Displays captured values (Glucose: 128 mg/dL fasting, no symptoms, adherent). Patient confirms.
- **Outcome**: Routine triage, 7 questions, budget 7/8.

---

### Case 2: Hypertension Only (Elevated BP)
- **Profile**: Hypertension on Amlodipine.
1. `hypertension_bp_reading`: Patient reports `152/94`.
2. `hypertension_bp_technique`: Patient confirms "Sat quietly for 5 minutes".
3. `hypertension_associated_symptoms`: Patient answers "Mild headache".
4. *Probe*: `probe_headache_severity`: Patient reports "Mild, no vision changes".
5. `hypertension_adherence`: Patient reports "Yes, took tablet this morning".
6. `hypertension_lifestyle`: Patient reports "Trying to reduce salt".
7. `core_summary_confirm`: Displays BP 152/94 mmHg, mild headache, adherent. Patient confirms.
- **Outcome**: Review triage (elevated systolic), budget 7/12.

---

### Case 3: Dual Diagnosis Standard (DM + HTN)
- **Profile**: Type 2 Diabetes and Hypertension, baseline stable.
1. **Reading 1** (R2): `diabetes_glucose_reading` -> `135` mg/dL.
2. **Reading 2** (R2): `hypertension_bp_reading` -> `124/82` mmHg.
3. **Shared Symptoms** (R3): `shared_symptoms_headache_vision` -> "No dizziness or vision problems".
   *(Fills both diabetes hypo/hyper symptoms and hypertension associated symptoms)*.
4. **Specific Symptoms**: `diabetes_foot_problems` -> "No sores or numbness".
5. **Shared Adherence** (R4): `shared_medication_adherence` -> "Yes, took both metformin and amlodipine".
   *(Fills both `adherence_diabetes` and `adherence_hypertension`)*.
6. **Shared Lifestyle** (R5): `shared_lifestyle` -> "Eating home cooked meals, moderate salt".
7. **Summary Confirmation** (R8):
   - Glucose: 135 mg/dL
   - Blood Pressure: 124/82 mmHg
   - Symptoms: None
   - Adherence: All medications taken
   Patient selects "Confirm".
- **Outcome**: Routine triage, 7 questions, 0 duplicate slots.

---

### Case 4: Dual Diagnosis + Fasting (Ramadan / Fasting Day)
- **Profile**: Type 2 Diabetes and Hypertension, patient is fasting today.
1. **Reading 1** (R2): `diabetes_glucose_reading` -> `88` mg/dL.
2. **Reading 2** (R2): `hypertension_bp_reading` -> `118/76` mmHg.
3. **Fasting Status**: `fasting_is_fasting` -> "Yes, fasting today".
4. **Fasting Safety Question** (triggered by `is_fasting_today is True`): `fasting_hypo_symptoms` -> "Feeling fine, no severe shakiness".
5. **Shared Symptoms** (R3): `shared_symptoms_headache_vision` -> "None".
6. **Shared Adherence** (R4): `shared_medication_adherence` -> "Took morning medicines at Sehri".
7. **Summary Confirmation** (R8):
   - Glucose: 88 mg/dL (fasting)
   - BP: 118/76 mmHg
   - Fasting: Yes (safe fasting confirmed, no hypo)
   - Adherence: Taken at Sehri
- **Outcome**: Routine triage with fasting safety noted.

---

### Case 5: Dual Diagnosis + Caregiver
- **Profile**: Elderly patient with DM + HTN; adult son answering on their behalf.
1. **Caregiver Identification** (R9): Patient's son opens session: "I am answering for my mother" -> `answered_by="caregiver"`.
2. **Reading 1** (R2): `diabetes_glucose_reading` -> `160` mg/dL.
3. **Reading 2** (R2): `hypertension_bp_reading` -> `130/85` mmHg.
4. **Shared Symptoms** (R3): `shared_symptoms_headache_vision` -> "She felt a little dizzy this morning".
5. **Shared Adherence** (R4): `shared_medication_adherence` -> "Yes, I gave her all morning tablets".
6. **Summary Confirmation** (R8):
   - Reported by: Caregiver (son)
   - Glucose: 160 mg/dL, BP: 130/85 mmHg
   - Symptoms: Mild morning dizziness
   Caregiver confirms.
- **Outcome**: Review triage; confidence lowered from "High" to "Medium"; `answered_by="caregiver"` stored for doctor review.

---

### Case 6: Dual Diagnosis with Correction at Summary
- **Profile**: Type 2 Diabetes and Hypertension.
1. `diabetes_glucose_reading` -> `140` mg/dL.
2. `hypertension_bp_reading` -> `190/100` mmHg. *(Patient accidentally typed 190 instead of 120)*.
3. `shared_symptoms_headache_vision` -> "No symptoms".
4. `shared_medication_adherence` -> "Taken".
5. **Summary Confirmation 1** (R8):
   - Shows: Glucose 140 mg/dL, BP 190/100 mmHg.
   - Patient selects: "Need to change something".
6. **Correction Round 1**:
   - System prompts: "Which reading or answer would you like to update?"
   - Patient selects: `hypertension_bp_reading`.
   - System re-asks: "Please enter your blood pressure reading:"
   - Patient answers: `120/80`.
7. **Summary Confirmation 2** (R8):
   - Shows updated: Glucose 140 mg/dL, BP 120/80 mmHg.
   - Patient selects: "Confirm".
- **Outcome**: Successfully updated slot, routine triage, correction round count = 1.
