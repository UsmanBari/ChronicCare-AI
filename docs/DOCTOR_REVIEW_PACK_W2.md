# ChronicCare AI — Doctor Review Pack (Week 2)

**Document Purpose**: Clinical review and sign-off pack for supervising medical officers:
- Dr Shaiza Jabbar (Medical Officer, Hearts International Hospital; to confirm permission to be named)
- Captain Dr Talha Yasin (Army doctor, CMH Rawalpindi; to confirm exact title)
- Dr Anam Zafar (agreed to be named, signed 14/10/26)

**Date**: November 2026  
**Motto**: *"The model proposes, the rules decide. The rules protect, the clinician directs."*

Every item below describes an active clinical safety decision, triage behavior, or decision-support threshold in ChronicCare AI. For each item, the current implementation in the codebase is documented alongside the proposed option, clinical rationale, exact repository citations, and a blank decision line for doctor sign-off.

---

## Decision 1: Urdu-Script Red-Flag Danger Phrases (14 of 20 Missed)

- **What the app does today**: Stage 1 input triage runs an exact keyword and regex substring match (`backend-poc-technical/agents/input_triage.py`). In an independent evaluation on 20 Urdu-script danger phrases (`docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md:19-24`), 14 of 20 severe red flags were missed (False Negative Rate = 70.0%), classifying severe emergency presentations as `routine` (`normal_clinical`). Examples of real missed test phrases include:
  - ID 2: "چھاتی پر شدید دباؤ ہے اور درد بائیں بازو میں جا رہا ہے" (severe chest pressure radiating to left arm)
  - ID 14: "شوگر 35 آ گئی ہے اور ہاتھ کانپ رہے ہیں، شدید پسینہ آ رہا ہے" (glucose 35 with tremors and diaphoresis)
- **Proposed option**: Expand Urdu-script keyword and morphological pattern coverage in `input_triage.py` using proposed token patterns and morphological variations once clinically reviewed, ensuring any severe symptom string immediately triggers `emergency`. The proposed patterns have not yet been tested on new wordings. A blind test set is pending (PR #89).
- **Why**: A 70% false-negative rate on native Urdu-script inputs is an unacceptable safety risk for an acute emergency triage screener.
- **File citation**: `docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md:19-28, 31-45`, `backend-poc-technical/agents/input_triage.py`
- **Doctor decision**: 
  - [ ] Approve proposed pattern expansions
  - [ ] Require LLM/hybrid clinical entity extraction fallback
  - [ ] Other instructions: __________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 2: Blood Glucose Meter "LO" and "HI" Text Readings

- **What the app does today**: When a patient enters glucometer screen text such as "LO" or "HI" instead of a number, `answer_validation.py:validate_glucose_input` (lines 154–155) parses no numeric float token and returns `valid=False, is_unclear=True, needs_review=True`. Because no numeric value exists, `triage_protocol.py:evaluate_triggers` (lines 189–200) receives no glucose reading and fires no protocol trigger. Consequently, the check-in enters the `protocol_state is None` else-branch in `backend-poc-technical/main.py:3662-3675` where `final_triage_level = "review" if final_requires_review else "routine"`. Thus, an unreadable glucose such as "LO" ends as "routine" UNLESS verification (`verif_requires_review`), a low-sugar intake (`intake_requires_review`), or the stroke-extras rule (`evaluate_stroke_extras`) raises it.
- **Proposed option**:
  - Map "LO" (< 20 mg/dL / < 1.1 mmol/L) immediately to `emergency` (or minimum `urgent` with severe low protocol and immediate carbohydrate guidance).
  - Map "HI" (> 600 mg/dL / > 33.3 mmol/L) immediately to `urgent` or `emergency` for hyperglycemic crisis / DKA screening.
- **Why**: Handheld glucometers display "LO" when blood glucose is below detectable limits (~20 mg/dL) and "HI" when above ~600 mg/dL. Both indicate life-threatening metabolic crises that must never finish as `routine`.
- **File citation**: `backend-poc-technical/agents/answer_validation.py:150-156`, `backend-poc-technical/agents/triage_protocol.py:189-200`, `backend-poc-technical/main.py:3662-3675`
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
  - Option A: Keep verbatim (standard hypoglycemia "Rule of 15" guidance).
  - Option B: Rephrase to neutral non-prescriptive first-aid referral: *"Take quick sugar such as fruit juice or glucose, and seek immediate medical attention if symptoms persist."*
  - Option C: Remove specific gram dosage and advise immediate clinical contact.
- **Why**: The app gives no dosing advice without doctor approval (project rule).
- **File citation**: `backend-poc-technical/agents/interview_bank/messages.json:2, 58-60`
- **Doctor decision**: 
  - [ ] Keep Option A (15g rule)  [ ] Option B (neutral sugar guidance)  [ ] Option C (remove dosage)
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 4: Blood Pressure Guideline Edition (ACC/AHA 2017 vs 2025)

- **What the app does today**: `docs/CLINICAL_RULES.md:21, 189-190, 207-208` cites the ACC/AHA 2017 Blood Pressure Guideline (`DANGEROUS_BP_SYSTOLIC_MMHG = 180`, `DANGEROUS_BP_DIASTOLIC_MMHG = 120`, `BP_STAGE2_SYSTOLIC_MMHG = 140`, `BP_STAGE2_DIASTOLIC_MMHG = 90`).
- **Proposed option**: Update documentation and references to cite the 2025 AHA/ACC hypertension guideline updates while maintaining the crisis thresholds (180/120 mmHg) and stage 2 thresholds (140/90 mmHg).
- **Why**: Clinical documentation should reflect current peer-reviewed guideline consensus while preserving proven deterministic crisis limits.
- **File citation**: `docs/CLINICAL_RULES.md:21, 189-208`, `backend-poc-technical/agents/triage_protocol.py:80-92`
- **Doctor decision**: 
  - [ ] Formally approve 2025 citation update
  - [ ] Retain 2017 historical citation
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 5: Non-Stop Vomiting and Inability to Keep Fluids Down (Reviewer Split)

- **What the app does today**: In `docs/CLINICAL_RULES.md:154, 192`, `unable_to_keep_fluids` is currently classified as `urgent`. In clinician feedback:
  - Capt Dr Talha Yasin stated: *"nonstop vomiting is NOT emergency, it is an urgent review. No need to label it emergency."* (`docs/CLINICIAN_RESPONSES.md:64`)
  - Dr Shaiza Jabbar's response in table row 4 was: *"Rest approved"* (`docs/CLINICIAN_RESPONSES.md:45`), which verbally aligned with Dr Talha (`docs/CLINICIAN_RESPONSES.md:89`).
  - Dr Anam Zafar marked vomiting as **emergency** (`docs/CLINICIAN_RESPONSES.md:107`: *"Item 4 (vomiting): she marked emergency. Dr Shaiza and Capt Dr Talha said urgent (implemented). Open split, 2 urgent versus 1 emergency. Code is not changed. Plan: one joint written decision in Iteration 2."*)
- **Proposed option**:
  - Keep as `urgent` (same-day clinical review) for isolated vomiting in an alert patient; escalate to `emergency` if accompanied by high glucose (> 250 mg/dL) or drowsiness/disorientation (suspected DKA/HHS).
- **Why**: Resolves the open clinician split (2 urgent vs 1 emergency) with a clear rule distinguishing isolated gastroenteritis from acute diabetic ketoacidosis.
- **File citation**: `docs/CLINICAL_RULES.md:154, 192, 278, 288`, `docs/CLINICIAN_RESPONSES.md:45, 64, 89, 107`
- **Doctor decision**: 
  - [ ] Confirm `urgent` for isolated vomiting; `emergency` if combined with high glucose / confusion
  - [ ] Escalate all nonstop vomiting to `emergency`
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 6: D15 Preventive Care HbA1c Screening Reminder

- **What the app does today**: `backend-poc-technical/agents/screening_reminder.py` is fully implemented but strictly **dormant by default** (`screening_interval_months = None`, `interval_days = None` at line 68). The function signature is:
  ```python
  def hba1c_reminder(
      conditions: Optional[List[Any]],
      record_observations: Optional[List[Dict[str, Any]]],
      today: Optional[Any] = None,
      interval_days: Optional[int] = None,
  ) -> Optional[Dict[str, Any]]:
  ```
- **Proposed option**:
  - Choose clinical interval for hypertensive adults without diagnosed diabetes:
    - 12 months (365 days)
    - 24 months (730 days)
    - 36 months (1095 days)
    - Keep dormant (None)
  - Approved patient wording:
    - English: *"Ask your doctor whether you need an HbA1c (sugar) test."*
    - Urdu: *"اپنے ڈاکٹر سے پوچھیں کہ کیا آپ کو HbA1c (شوگر) ٹیسٹ کی ضرورت ہے۔"*
    - Roman Urdu: *"Apne doctor se poochein ke kya aap ko HbA1c (sugar) test ki zaroorat hai."*
- **Why**: Hypertensive patients without known diabetes benefit from routine periodic glycaemic screening; requiring explicit clinician selection of `interval_days` ensures the reminder aligns with practice policy.
- **File citation**: `backend-poc-technical/agents/screening_reminder.py:34-46, 68, 115-122`, `docs/ML_PLAN.md:D15`
- **Doctor decision**: 
  - Approved interval: [ ] 12 months (365 days)  [ ] 24 months (730 days)  [ ] 36 months (1095 days)  [ ] Keep dormant
  - Approved wording: [ ] Approved as proposed  [ ] Modified: _________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 7: D12 Provider-Only Experimental Diabetes Risk Panel

- **What the app does today**: Risk evaluation runs strictly behind `RISK_ENABLED` on provider review detail endpoints (`/api/provider/review/{id}`). Patient-facing endpoints (`/api/me/*`, `/api/checkins/*`) never return risk. `RISK_CAN_RAISE` defaults to `false` (`backend-poc-technical/agents/risk_rules.py:47`), preventing the model from altering any triage level. The provider UI renders qualitative band badges (Low, Moderate, High), top clinical contributing factors, and clinical caveats (`home_bp_not_exam_bp`, `not_validated_pakistan`), with raw percentage probabilities strictly hidden (`docs/RISK_PANEL.md:53`).
- **Proposed option**:
  - Retain the panel as a provider-only experimental decision-support view.
  - Keep `RISK_CAN_RAISE = false` in production unless supervising physicians formally validate the model on a local South Asian clinical cohort.
- **Why**: The model was trained on US NHANES survey data; external validation on Pakistani cohorts is pending. Provider-only advisory visibility avoids patient alarm while alerting clinicians to background cardiometabolic risk.
- **File citation**: `docs/RISK_PANEL.md:1-64`, `backend-poc-technical/agents/risk_agent.py:300-380`, `backend-poc-technical/agents/risk_rules.py:40-65`, `docs/ML_PLAN.md:D12`
- **Doctor decision**: 
  - [ ] Approve provider-only experimental panel
  - [ ] Keep `RISK_CAN_RAISE = false` (advisory only)
  - [ ] Doctor comments: _____________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 8: Waist Circumference Landmark and Valid Physiological Range

- **What the app does today**: The profile waist field accepts values between **40.0 cm and 200.0 cm** (15.7 to 78.7 inches). Values outside this range are rejected with an error message requiring doctor review (`backend-poc-technical/main.py:108`, `app/components/HealthProfileScreen.tsx:880-895`).
  - Current helper text: *"Measure around your waist at the top of your hip bones, after breathing out."* (Urdu: *"اپنی کمر کا ناپ کولہے کی ہڈی کے اوپر سے لیں، سانس باہر نکالنے کے بعد۔"*).
- **Proposed option**:
  - Option (a): Top of the hip bone (iliac crest), which is how NHANES measured waist, what the model was trained on, and the current helper text.
  - Option (b): WHO midpoint protocol (midpoint between lowest palpable rib and top of iliac crest). Note: the model was trained on protocol (a).
- **Why**: Standardizing the measurement protocol ensures self-reported measurements align with the epidemiological training data.
- **File citation**: `app/components/HealthProfileScreen.tsx:840-895`, `app/translations/index.ts:841-844, 1268-1271`, `backend-poc-technical/main.py:108`
- **Doctor decision**: 
  - Protocol: [ ] Option (a) Iliac crest (model-aligned)  [ ] Option (b) WHO midpoint
  - Range 40–200 cm: [ ] Approved  [ ] Modified: ____________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 9: Longitudinal Trend Thresholds and Directional Minimum Observations

- **What the app does today**: `backend-poc-technical/agents/trend_agent.py:54-63` proposes:
  - Systolic BP Delta Threshold: **10.0 mmHg**
  - Diastolic BP Delta Threshold: **5.0 mmHg**
  - Glucose Delta Threshold: **20.0 mg/dL**
  - Current operational requirement: `BASELINE_MIN_READINGS = 3` (from `triage_protocol.py`).
  - Proposed operational constant: `PROPOSED_MIN_READINGS_FOR_DIRECTION = 5` readings required before displaying a trajectory direction arrow (`rising` or `falling`).
- **Proposed option**:
  - Adopt 10 mmHg systolic, 5 mmHg diastolic, and 20 mg/dL glucose delta thresholds.
  - Require at least 5 readings over the 30-day window before asserting `rising` or `falling` direction; otherwise report `stable` or `not_enough_history`.
- **Why**: Home readings have substantial daily fluctuations. Requiring 5 readings and dual-agreement between median half-delta and Theil-Sen slope prevents false trend alerts.
- **File citation**: `backend-poc-technical/agents/trend_agent.py:54-63, 160-163`, `docs/TREND_AGENT.md:61-70`
- **Doctor decision**: 
  - [ ] Approve 10/5/20 thresholds and 5-reading minimum requirement
  - [ ] Adjust thresholds: __________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Clinician Summary & Sign-Off

| Item | Topic | Current State | Proposed Action | Clinician Sign-Off |
| :--- | :--- | :--- | :--- | :--- |
| **D1** | Urdu Red-Flag Phrases | 14/20 missed (70% FNR) | Pattern expansion (held-out test pending) | __________________ |
| **D2** | Meter LO / HI Text | Unreadable ends as routine unless raised | LO -> `emergency`; HI -> `urgent` | __________________ |
| **D3** | 15 g Fast Sugar Guidance | 15g rule in prompt | Review against project non-prescriptive rule | __________________ |
| **D4** | Blood Pressure Guidelines | ACC/AHA 2017 citation | Update to 2025 guideline edition | __________________ |
| **D5** | Non-Stop Vomiting | `urgent` (Talha, Shaiza) / `emergency` (Anam) | `urgent` if alert; `emergency` if DKA suspect | __________________ |
| **D6** | D15 HbA1c Reminder | Dormant in codebase (`interval_days=None`) | Clinician selects interval (12/24/36 mo) | __________________ |
| **D7** | D12 Risk Panel | Provider-only behind flag | Advisory card, `RISK_CAN_RAISE=false` | __________________ |
| **D8** | Waist Range & Landmark | 40–200 cm; iliac crest helper text | Confirm Option (a) iliac crest (model-aligned) | __________________ |
| **D9** | Longitudinal Trends | 10 / 5 / 20 mmHg & mg/dL | 5-reading minimum for trajectory arrow | __________________ |

**Supervising Reviewers**:
1. Dr Shaiza Jabbar, Medical Officer, Hearts International Hospital (to confirm permission to be named)
2. Captain Dr Talha Yasin, Army doctor, CMH Rawalpindi (to confirm exact title)
3. Dr Anam Zafar (agreed to be named, signed 14/10/26)

**Doctor Signature**: ________________________________________________________  
**Date Signed**: _____________________________________________________________
