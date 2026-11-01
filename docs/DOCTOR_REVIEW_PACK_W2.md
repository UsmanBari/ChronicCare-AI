# ChronicCare AI — Doctor Review Pack (Week 2)

**Document Purpose**: Clinical review and sign-off pack for supervising medical officers (Dr. Talha Yasin, Dr. Anam).
**Date**: November 2026
**Motto**: *"The model proposes, the rules decide. The rules protect, the clinician directs."*

Every item below describes an active clinical safety decision, triage behavior, or decision-support threshold in ChronicCare AI. For each item, the current implementation in the codebase is documented alongside the proposed option, clinical rationale, exact repository citations, and a blank decision line for doctor sign-off.

---

## Decision 1: Urdu-Script Red-Flag Danger Phrases (14 of 20 Missed)

- **What the app does today**: Stage 1 input triage runs an exact keyword/regex substring match (`backend-poc-technical/agents/input_triage.py`). In independent evaluation by Hassaan on 20 Urdu-script danger phrases (`docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md:19-24`), 14 out of 20 severe red flags were missed (False Negative Rate = 70.0%), classifying severe emergencies (e.g. severe hypoglycemia "شوگر 35 پر گر گئی اور غش کھا کر گر گیا", stroke symptoms) as `routine` / `normal_clinical`.
- **Proposed option**: Expand Urdu-script keyword and morphological pattern coverage in `input_triage.py` using Hassaan's proposed token patterns and fuzzy/stemmed variations once clinically reviewed, ensuring any severe symptom string immediately triggers `emergency`.
- **Why**: A 70% false-negative rate on native Urdu-script inputs is an unacceptable safety risk for an acute emergency triage screener.
- **File citation**: `docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md:19-28`, `backend-poc-technical/agents/input_triage.py`
- **Doctor decision**: 
  - [ ] Approve proposed pattern expansions
  - [ ] Require LLM/hybrid clinical entity extraction fallback
  - [ ] Other instructions: __________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 2: Blood Glucose Meter "LO" and "HI" Text Readings

- **What the app does today**: When a patient enters glucometer screen text such as "LO" or "HI" instead of a number, `answer_validation.py:155` treats the input as non-numeric and sets `valid=False, is_unclear=True, needs_review=True`. In triage without other flags, the overall check-in finishes at `routine` level (`triage_protocol.py:98`).
- **Proposed option**:
  - Map "LO" (< 20 mg/dL / < 1.1 mmol/L) immediately to `emergency` (or minimum `urgent` with severe low protocol and immediate carbohydrate guidance).
  - Map "HI" (> 600 mg/dL / > 33.3 mmol/L) immediately to `urgent` or `emergency` for hyperglycemic crisis / DKA screening.
- **Why**: Handheld glucometers display "LO" when blood glucose is below detectable limits (~20 mg/dL) and "HI" when above ~600 mg/dL. Both indicate life-threatening metabolic crises that must never finish as `routine`.
- **File citation**: `backend-poc-technical/agents/answer_validation.py:150-160`, `backend-poc-technical/agents/triage_protocol.py:98`
- **Doctor decision**:
  - "LO" mapping: [ ] `emergency`  [ ] `urgent`
  - "HI" mapping: [ ] `emergency`  [ ] `urgent`
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 3: 15 g Fast-Acting Sugar Guidance in v3 Interview

- **What the app does today**: In `backend-poc-technical/agents/interview_bank/messages.json:2` and `messages.json:58-60`, the system displays:
  > *"Low blood sugar alert: If you feel shaky, sweaty, confused or dizzy, consume 15g fast-acting sugar (half cup juice or 3-4 glucose tablets) immediately."*
  (Urdu: *"لو شوگر کی اطلاع: اگر آپ کپکپاہٹ، پسینہ، الجھن یا چکر محسوس کریں تو فوراً 15 گرام جلدی اثر کرنے والی شوگر (آدھا کپ جوس یا 3 سے 4 گلوکوز کی گولیاں) لیں"*)
- **Proposed option**:
  - Option A: Keep verbatim (standard ADA "Rule of 15" hypoglycemia treatment).
  - Option B: Rephrase to neutral non-prescriptive first-aid referral: *"Take quick sugar such as fruit juice or glucose, and seek immediate medical attention if symptoms persist."*
  - Option C: Remove specific gram dosage and advise immediate clinical contact.
- **Why**: Project governance rule G-06 forbids automated prescription or dosage advice without explicit physician authorization.
- **File citation**: `backend-poc-technical/agents/interview_bank/messages.json:2, 58-60`
- **Doctor decision**: 
  - [ ] Keep Option A (15g rule)  [ ] Option B (neutral sugar guidance)  [ ] Option C (remove dosage)
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 4: Blood Pressure Guideline Edition (ACC/AHA 2017 vs 2025)

- **What the app does today**: `docs/CLINICAL_RULES.md:21, 189-190, 207-208` cites the ACC/AHA 2017 Blood Pressure Guideline (`DANGEROUS_BP_SYSTOLIC_MMHG = 180`, `DANGEROUS_BP_DIASTOLIC_MMHG = 120`, `BP_STAGE2_SYSTOLIC_MMHG = 140`, `BP_STAGE2_DIASTOLIC_MMHG = 90`).
- **Proposed option**: Update all clinical documentation and references to align with the 2025 AHA/ACC/multisociety hypertension guideline updates while maintaining the crisis thresholds (180/120 mmHg) and stage 2 thresholds (140/90 mmHg).
- **Why**: Clinical citations must reflect current peer-reviewed guideline consensus while preserving proven safety-critical thresholds.
- **File citation**: `docs/CLINICAL_RULES.md:21, 189-208`, `backend-poc-technical/agents/triage_protocol.py`
- **Doctor decision**: 
  - [ ] Formally approve 2025 citation update
  - [ ] Retain 2017 historical citation
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 5: Non-Stop Vomiting and Inability to Keep Fluids Down (Dr. Anam Item)

- **What the app does today**: In `docs/CLINICAL_RULES.md:154`, `unable_to_keep_fluids` is currently classified as `urgent` based on Dr. Talha Yasin's feedback (`docs/CLINICIAN_RESPONSES.md:64`: *"nonstop vomiting is NOT emergency, it is an urgent review"*). Dr. Anam's response was *"Rest approved"* (`docs/CLINICIAN_RESPONSES.md:45, 76`), leaving ambiguity as to whether vomiting with dehydration in diabetic patients should escalate to `emergency` or remain `urgent`.
- **Proposed option**:
  - Keep as `urgent` (same-day clinic or urgent care referral) unless accompanied by high blood glucose (> 250 mg/dL) or altered mental status / drowsiness, which escalates to `emergency` (suspected DKA/HHS).
- **Why**: Isolated vomiting in an alert patient does not necessarily require emergency resuscitation, but diabetic ketoacidosis (vomiting + hyperglycemia) is immediately life-threatening.
- **File citation**: `docs/CLINICAL_RULES.md:154, 278, 288`, `docs/CLINICIAN_RESPONSES.md:45, 64, 76`
- **Doctor decision**: 
  - [ ] Confirm `urgent` for isolated vomiting; `emergency` if combined with high glucose / confusion
  - [ ] Escalate all nonstop vomiting to `emergency`
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 6: D15 Preventive Care HbA1c Screening Reminder

- **What the app does today**: `backend-poc-technical/agents/screening_reminder.py` is fully implemented but strictly **dormant by default** (`screening_interval_months = None`). No reminders are generated without clinician configuration.
- **Proposed option**:
  - Configure screening reminder interval: recommended **12 months** (365 days) for hypertensive adults without diagnosed diabetes (per ADA Standards of Care / USPSTF).
  - Approved patient wording:
    - English: *"Ask your doctor whether you need an HbA1c (sugar) test."*
    - Urdu: *"اپنے ڈاکٹر سے پوچھیں کہ کیا آپ کو HbA1c (شوگر) ٹیسٹ کی ضرورت ہے۔"*
    - Roman Urdu: *"Apne doctor se poochein ke kya aap ko HbA1c (sugar) test ki zaroorat hai."*
- **Why**: As demonstrated in decision curve analysis (`docs/ml/DECISION_CURVE.md`), testing every hypertensive adult for diabetes once per year achieves equal or superior net clinical benefit compared to an ML classifier, without false reassurance.
- **File citation**: `backend-poc-technical/agents/screening_reminder.py:34-122`, `docs/ml/DECISION_CURVE.md`, `docs/ML_PLAN.md:D15`
- **Doctor decision**: 
  - Approved interval: [ ] 12 months (365 days)  [ ] 6 months  [ ] 24 months  [ ] Keep dormant
  - Approved wording: [ ] Approved as proposed  [ ] Modified: _________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 7: D12 Provider-Only Experimental Diabetes Risk Panel

- **What the app does today**: The `risk` evaluation runs strictly behind `RISK_ENABLED` on provider review endpoints (`/api/provider/review/{id}`). It is never exposed to patients (`/api/me/*`, `/api/checkins/*`). `RISK_CAN_RAISE` is default `false` (`backend-poc-technical/agents/risk_rules.py`), meaning the model cannot alter any patient triage level.
- **Proposed option**:
  - Retain the panel as a provider-only experimental decision-support card.
  - Keep `RISK_CAN_RAISE = false` in production unless supervising physicians formally validate the model on a local South Asian clinical cohort.
  - Display band badge (Low / Moderate / High) with clinical caveats (`home_bp_not_exam_bp`, `not_validated_pakistan`) and top reasons, with raw percentages strictly hidden.
- **Why**: NHANES was trained on a US population; external validation on Pakistani cohorts is pending. Advisory provider visibility prevents patient alarm while assisting clinician vigilance.
- **File citation**: `docs/RISK_PANEL.md`, `backend-poc-technical/agents/risk_agent.py`, `backend-poc-technical/agents/risk_rules.py`, `docs/ML_PLAN.md:D12`
- **Doctor decision**: 
  - [ ] Approve provider-only experimental panel
  - [ ] Keep `RISK_CAN_RAISE = false` (advisory only)
  - [ ] Doctor comments: _____________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 8: Waist Circumference Helper Text and Valid Physiological Range

- **What the app does today**: The profile waist field accepts values between **40.0 cm and 200.0 cm** (15.7 to 78.7 inches). Values outside this range are rejected with an error message requiring doctor review (`backend-poc-technical/main.py:108`, `app/components/HealthProfileScreen.tsx:880-895`).
  - Helper text: *"Measure around your waist at the top of your hip bones, after breathing out."* (Urdu: *"اپنی کمر کا ناپ کولہے کی ہڈی کے اوپر سے لیں، سانس باہر نکالنے کے بعد۔"*).
- **Proposed option**: Maintain the 40–200 cm acceptable range and WHO/IDF standard landmark instructions ("midpoint between the lower margin of the least palpable rib and the top of the iliac crest").
- **Why**: Self-reported waist circumference has measurement variability; standard guidance ensures consistency for abdominal adiposity risk assessment.
- **File citation**: `app/components/HealthProfileScreen.tsx:840-895`, `app/translations/index.ts:841-844, 1268-1271`, `backend-poc-technical/main.py:108`
- **Doctor decision**: 
  - [ ] Approve 40–200 cm range and helper guidance
  - [ ] Modify range or wording: _____________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 9: Longitudinal Trend Thresholds and Directional Minimum Observations

- **What the app does today**: `backend-poc-technical/agents/trend_agent.py:54-63` proposes:
  - Systolic BP Delta Threshold: **10.0 mmHg**
  - Diastolic BP Delta Threshold: **5.0 mmHg**
  - Glucose Delta Threshold: **20.0 mg/dL**
  - Current operational requirement: `BASELINE_MIN_READINGS = 3` (from `triage_protocol.py`).
  - Proposed operational requirement: `PROPOSED_MIN_READINGS_FOR_DIRECTION = 5` readings required before displaying a trajectory direction arrow (`rising` or `falling`), to prevent noise from day-to-day variability.
- **Proposed option**:
  - Adopt 10 mmHg systolic, 5 mmHg diastolic, and 20 mg/dL glucose thresholds.
  - Require at least 5 readings over the 30-day window before asserting `rising` or `falling` direction; otherwise report `stable` or `not_enough_history`.
- **Why**: Single home readings have wide white-coat, postural, and dietary fluctuations. 3 readings are prone to outlier skew; 5 readings with Theil-Sen median slopes provide robust trend estimation.
- **File citation**: `backend-poc-technical/agents/trend_agent.py:54-63, 160-163`, `docs/TREND_AGENT.md:61-70`
- **Doctor decision**: 
  - [ ] Approve 10/5/20 thresholds and 5-reading minimum requirement
  - [ ] Adjust thresholds: __________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Clinician Summary & Sign-Off

| Item | Topic | Current State | Proposed Action | Clinician Sign-Off |
| :--- | :--- | :--- | :--- | :--- |
| **D1** | Urdu Red-Flag Phrases | 14/20 missed (70% FNR) | Pattern expansion & entity validation | __________________ |
| **D2** | Meter LO / HI Text | Classified as `routine` | LO -> `emergency`; HI -> `urgent` | __________________ |
| **D3** | 15 g Fast Sugar Guidance | Explicit 15g rule in prompt | Review against G-06 non-prescriptive rule | __________________ |
| **D4** | Blood Pressure Guidelines | ACC/AHA 2017 citation | Update to 2025 guideline edition | __________________ |
| **D5** | Non-Stop Vomiting | `urgent` (Talha) / open (Anam) | `urgent` if alert; `emergency` if DKA suspect | __________________ |
| **D6** | D15 HbA1c Reminder | Dormant in codebase | 12-month interval for hypertensive adults | __________________ |
| **D7** | D12 Risk Panel | Provider-only behind flag | Advisory card, `RISK_CAN_RAISE=false` | __________________ |
| **D8** | Waist Range & Helper Text | 40–200 cm range | Maintain 40–200 cm with breathing out tip | __________________ |
| **D9** | Longitudinal Trends | 10 / 5 / 20 mmHg & mg/dL | 5-reading minimum for trajectory arrow | __________________ |

**Supervising Physician**: ___________________________________________________  
**Registration / License ID**: _______________________________________________  
**Hospital / Practice**: Hearts International Hospital / Rawalpindi General Hospital  
**Date Signed**: _____________________________________________________________
