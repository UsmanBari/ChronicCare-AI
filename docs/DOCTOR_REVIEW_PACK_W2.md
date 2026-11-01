# ChronicCare AI — Doctor Review Pack (Week 2)

**Document Purpose**: Clinical review and sign-off pack for reviewing medical officers:
- Dr Shaiza Jabbar (Medical Officer, Hearts International Hospital; to confirm permission to be named)
- Captain Dr Talha Yasin (Army doctor, CMH Rawalpindi; to confirm exact title)
- Dr Anam Zafar (agreed to be named, signed 14/10/26)

**Date**: November 2026  
**Motto**: *"The model proposes, the rules decide."*

Every item below describes an active clinical safety decision, triage behavior, or decision-support threshold in ChronicCare AI. For each item, the current implementation in the codebase is documented alongside the proposed option, clinical rationale, exact repository citations, and a blank decision line for doctor sign-off.

---

## Decision 1: Urdu-Script Red-Flag Danger Phrases

- **What the app does today**: Stage 1 input triage runs an exact keyword and regex substring match (`backend-poc-technical/agents/input_triage.py:classify_input`).
  - In an initial evaluation on 20 Urdu-script danger phrases (`docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md:19-24`), 14 of 20 severe red flags were missed (False Negative Rate = 70.0%), classifying severe emergency presentations as `normal_clinical` (meaning not flagged as danger).
  - In an independent blind evaluation on 20 danger phrases and 20 tricky safe look-alike phrases authored by Saad (`tests/sim/blind_urdu_saad.json`, Table 6E in `docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md:171-184`), the current v3 engine detected only 3 of 20 danger phrases (15.0% sensitivity, 17 false negatives) and achieved 90.0% safe specificity (18/20, with 2 false alarms on safe phrases recounting resolved past events). Proposed regex patterns (Round 0 un-tuned) detected 7 of 20 danger phrases (35.0% sensitivity, 13 false negatives) with the same 90.0% safe specificity (2 false alarms).
- **Proposed option**:
  - Option A: Approve proposed keyword and regex pattern expansions as an interim improvement step.
  - Option B: Require broader symptom word-groups or an LLM/hybrid clinical entity extraction fallback to capture colloquial and caregiver formulations.
  - Option C: Other doctor instruction.
- **Why**: A high false-negative rate on native Urdu-script inputs is a critical clinical safety risk that requires clinician guidance on the acceptable architectural approach.
- **File citation**: `docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md:19-28, 171-184`, `backend-poc-technical/agents/input_triage.py`, `tests/sim/blind_urdu_saad.json`
- **Doctor decision**: 
  - [ ] Approve proposed pattern expansions as a partial step
  - [ ] Require broader symptom word-groups or LLM/hybrid clinical entity extraction
  - [ ] Other instructions: __________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 2: Blood Glucose Meter "LO" and "HI" Text Readings

- **What the app does today**: When a patient enters glucometer screen text such as "LO" or "HI" instead of a number, `answer_validation.py:validate_glucose_input` (lines 150–156) parses no numeric float token and returns `valid=False, is_unclear=True, needs_review=True`. Because no numeric value exists in `readings_map`, `triage_protocol.py:evaluate_triggers` (lines 189–200) receives no glucose reading and fires no protocol trigger (`protocol_state` evaluates to `None`). Consequently, the check-in enters the `protocol_state is None` else-branch in `backend-poc-technical/main.py:3662-3675` (`final_triage_level = "review" if final_requires_review else "routine"`). In actual end-to-end execution, verification flags a gap/reconciliation review (`verif_requires_review = True`), so the check-in completes with `triage_level: "review"` and `triage: null` (no acute protocol triage is triggered, and no immediate emergency/urgent escalation occurs).
- **Proposed option**:
  - Map "LO" immediately to `emergency` (or `urgent` if clinician prefers).
  - Map "HI" immediately to `urgent` or `emergency` for hyperglycemic crisis evaluation.
- **Why**: Handheld glucometers display "LO" when blood glucose is below detectable limits and "HI" when above detectable limits. These detection boundaries vary by meter model (to confirm). Both indicate severe metabolic abnormalities that should not rely on generic reconciliation review.
- **File citation**: `backend-poc-technical/agents/answer_validation.py:150-156`, `backend-poc-technical/agents/triage_protocol.py:189-200`, `backend-poc-technical/main.py:3662-3675`
- **Doctor decision**:
  - "LO" mapping: [ ] `emergency`  [ ] `urgent`
  - "HI" mapping: [ ] `emergency`  [ ] `urgent`
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 3: 15 g Fast-Acting Sugar Guidance in v3 Interview

- **What the app does today**: In `backend-poc-technical/agents/interview_bank/messages.json:58-60`, the system defines:
  - English: `"Low blood sugar alert: If you feel shaky, sweaty, confused or dizzy, consume 15g fast-acting sugar (half cup juice or 3-4 glucose tablets) immediately."`
  - Urdu: `"کم شوگر کی اطلاع: اگر آپ کپکپاہٹ، پسینہ، الجھن، یا چکر محسوس کریں تو فوراً 15 گرام جلدی اثر کرنے والی شوگر (آدھا کپ رس یا 3 سے 4 گلوکوز کی گولیاں) لیں۔"`
  - Roman Urdu: `"Kam sugar ki itla: Agar aap kapkapahat, paseena, uljhan ya chakkar mehsoos karein, to foran 15g jaldi asar karne wali sugar (adha cup juice ya 3-4 glucose tablets) lein."`
- **Proposed option**:
  - Option A: Keep verbatim (standard hypoglycemia "Rule of 15" guidance).
  - Option B: Rephrase to neutral non-prescriptive first-aid referral: *"Take quick sugar such as fruit juice or glucose, and seek immediate medical attention if symptoms persist."*
  - Option C: Remove specific gram dosage and advise immediate clinical contact.
- **Why**: The app gives no dosing advice without doctor approval (project rule).
- **File citation**: `backend-poc-technical/agents/interview_bank/messages.json:58-60`
- **Doctor decision**: 
  - [ ] Keep Option A (15g rule)  [ ] Option B (neutral sugar guidance)  [ ] Option C (remove dosage)
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 4: Blood Pressure Guideline Edition (ACC/AHA 2017 vs 2025)

- **What the app does today**: `docs/CLINICAL_RULES.md:21, 189-190, 207-208` cites the ACC/AHA 2017 Blood Pressure Guideline. The codebase implements:
  - Stage 2 Hypertension: `BP_STAGE2_SYSTOLIC_MMHG = 140` and `BP_STAGE2_DIASTOLIC_MMHG = 90` (`backend-poc-technical/agents/triage_protocol.py:72-73`).
  - Hypertensive Crisis / Dangerous BP: `DANGEROUS_BP_SYSTOLIC_MMHG = 180` and `DANGEROUS_BP_DIASTOLIC_MMHG = 120` (`backend-poc-technical/agents/adaptive_interview_agent.py:85-86`).
- **Proposed option**: Update documentation and references to cite the 2025 AHA/ACC hypertension guideline. Doctor to confirm whether the 2025 guideline changes any of these thresholds.
- **Why**: Clinical documentation should reflect current peer-reviewed guideline consensus while preserving proven deterministic crisis limits.
- **File citation**: `docs/CLINICAL_RULES.md:21, 189-208`, `backend-poc-technical/agents/triage_protocol.py:72-73`, `backend-poc-technical/agents/adaptive_interview_agent.py:85-86`
- **Doctor decision**: 
  - [ ] Formally approve 2025 citation update
  - [ ] Retain 2017 historical citation
  - Threshold adjustments (if any): __________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 5: Non-Stop Vomiting and Inability to Keep Fluids Down (Reviewer Split)

- **What the app does today**: In `docs/CLINICAL_RULES.md:154, 192`, `unable_to_keep_fluids` is currently classified as `urgent`. In clinician feedback (`docs/CLINICIAN_RESPONSES.md`):
  - Capt Dr Talha Yasin stated: *"nonstop vomiting is NOT emergency, it is an urgent review. No need to label it emergency."* (`docs/CLINICIAN_RESPONSES.md:64`)
  - Dr Shaiza Jabbar's response in table row 4 was: *"Rest approved"* (`docs/CLINICIAN_RESPONSES.md:45`), and verbally agreed with Dr Talha (`docs/CLINICIAN_RESPONSES.md:89`: *"Confirm in writing if possible"*).
  - Dr Anam Zafar marked vomiting as **emergency** (`docs/CLINICIAN_RESPONSES.md:107`: *"Item 4 (vomiting): she marked **emergency**. Dr Shaiza and Capt Dr Talha said **urgent** (implemented). Open split, 2 urgent versus 1 emergency. Code is not changed. Plan: one joint written decision in Iteration 2."*)
- **Proposed options for doctor**:
  - Option (a): Keep as `urgent` (same-day clinical review) for all nonstop vomiting.
  - Option (b): Escalate all nonstop vomiting to `emergency`.
  - Option (c): Keep as `urgent` for isolated vomiting, but escalate to `emergency` when combined with other danger signs (doctor to specify accompanying danger signs).
- **Why**: Resolves the open clinician split (2 urgent vs 1 emergency) with a single definitive consensus policy.
- **File citation**: `docs/CLINICAL_RULES.md:154, 192, 278, 288`, `docs/CLINICIAN_RESPONSES.md:45, 64, 89, 107`
- **Doctor decision**: 
  - [ ] Option (a) Keep urgent  [ ] Option (b) Emergency for all nonstop vomiting  [ ] Option (c) Urgent unless combined with other danger signs
  - If Option (c), specify signs: _____________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 6: D15 Preventive Care HbA1c Screening Reminder

- **What the app does today**: `backend-poc-technical/agents/screening_reminder.py` is fully implemented but strictly **dormant by default** (`interval_days = None` at line 68: `if interval_days is None or interval_days <= 0: return None`). The function signature is:
  ```python
  def hba1c_reminder(
      conditions: Optional[List[Any]],
      record_observations: Optional[List[Dict[str, Any]]],
      today: Optional[Any] = None,
      interval_days: Optional[int] = None,
  ) -> Optional[Dict[str, Any]]:
  ```
  The implemented reminder wording strings (`backend-poc-technical/agents/screening_reminder.py:115-122`) are:
  - English: *"Ask your doctor whether you need an HbA1c (sugar) test."*
  - Urdu: *"اپنے ڈاکٹر سے پوچھیں کہ کیا آپ کو HbA1c (شوگر) ٹیسٹ کی ضرورت ہے۔"*
  - Roman Urdu: *"Apne doctor se poochein ke kya aap ko HbA1c (sugar) test ki zaroorat hai."*
- **Proposed option**:
  - Doctor to decide whether and how often to remind; the app has no default.
  - Intervals for consideration in hypertensive adults without diagnosed diabetes:
    - 12 months (365 days)
    - 24 months (730 days)
    - 36 months (1095 days)
    - Keep dormant (`None`)
- **Why**: Requiring explicit clinician selection of `interval_days` ensures preventive reminders conform to the practice's clinical protocol.
- **File citation**: `backend-poc-technical/agents/screening_reminder.py:34-40, 68, 115-122`, `docs/ML_PLAN.md:D15`
- **Doctor decision**: 
  - Approved interval: [ ] 12 months (365 days)  [ ] 24 months (730 days)  [ ] 36 months (1095 days)  [ ] Keep dormant
  - Approved wording: [ ] Approved as implemented  [ ] Modified: ______________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 7: D12 Provider-Only Experimental Diabetes Risk Panel

- **What the app does today**: Risk evaluation runs strictly behind `RISK_ENABLED` on provider review detail endpoints (`/api/provider/review/{id}`). Patient-facing endpoints (`/api/me/*`, `/api/checkins/*`) never return risk (`docs/RISK_PANEL.md:36-38`). `RISK_CAN_RAISE` defaults to `false` (`backend-poc-technical/agents/risk_rules.py:47`, `backend-poc-technical/.env.example:42`), preventing the model from altering any triage level. The provider UI renders qualitative band badges (Low, Moderate, High), top clinical contributing factors, and clinical caveats (`home_bp_not_exam_bp`, `not_validated_pakistan`), with raw percentage probabilities strictly hidden (`docs/RISK_PANEL.md:53`).
- **Proposed option**:
  - Retain the panel as a provider-only experimental decision-support view.
  - Keep `RISK_CAN_RAISE = false` in production unless reviewing physicians formally validate the model on a local South Asian clinical cohort.
- **Why**: The model was trained on US NHANES survey data; external validation on Pakistani cohorts is pending. Provider-only advisory visibility avoids patient alarm while alerting clinicians to background cardiometabolic risk.
- **File citation**: `docs/RISK_PANEL.md:1-64`, `backend-poc-technical/agents/risk_rules.py:40-65`, `backend-poc-technical/.env.example:42`, `docs/ML_PLAN.md:D12`
- **Doctor decision**: 
  - [ ] Approve provider-only experimental panel
  - [ ] Keep `RISK_CAN_RAISE = false` (advisory only)
  - [ ] Doctor comments: _____________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 8: Waist Circumference Landmark and Valid Physiological Range

- **What the app does today**: The profile waist field accepts values between **40.0 cm and 200.0 cm** (`WAIST_MIN_CM = 40.0`, `WAIST_MAX_CM = 200.0` at `backend-poc-technical/main.py:369-370`, checked at lines 472–473). Values outside this range raise a `ValueError` requiring doctor review.
  - Implemented helper text in `app/translations/index.ts:1269`:
    - Urdu: `"سانس باہر نکالنے کے بعد کولہے کی ہڈی کے اوپری حصے پر کمر کی پیمائش کریں۔"`
    - English (`app/translations/index.ts:843`): `"Measure around your waist at the top of your hip bones, after breathing out."`
- **Proposed option**:
  - Option (a): Top of the hip bone (iliac crest), which is how NHANES measured waist, what the model was trained on, and the current helper text.
  - Option (b): WHO midpoint protocol (midpoint between lowest palpable rib and top of iliac crest). Note: the model was trained on protocol (a).
- **Why**: Standardizing the measurement protocol ensures self-reported measurements align with the epidemiological training data.
- **File citation**: `app/translations/index.ts:843, 1269`, `backend-poc-technical/main.py:369-370, 472-473`
- **Doctor decision**: 
  - Protocol: [ ] Option (a) Iliac crest (model-aligned)  [ ] Option (b) WHO midpoint
  - Range 40–200 cm: [ ] Approved  [ ] Modified: ____________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Decision 9: Longitudinal Trend Thresholds and Directional Minimum Observations

- **What the app does today**: `backend-poc-technical/agents/trend_agent.py:55-59` proposes:
  - Systolic BP Delta Threshold: **10.0 mmHg** (`TYPE_SYSTOLIC: 10.0`)
  - Diastolic BP Delta Threshold: **5.0 mmHg** (`TYPE_DIASTOLIC: 5.0`)
  - Glucose Delta Threshold: **20.0 mg/dL** (`TYPE_GLUCOSE: 20.0`)
  - Current operational requirement: `BASELINE_MIN_READINGS = 3` (`backend-poc-technical/agents/triage_protocol.py:76`). When fewer than 3 readings are available, the direction evaluates to `"not_enough_history"` (`backend-poc-technical/agents/trend_agent.py:321`).
  - Proposed operational constant: `PROPOSED_MIN_READINGS_FOR_DIRECTION = 5` (`backend-poc-technical/agents/trend_agent.py:63`) required before asserting a trajectory direction arrow (`rising` or `falling`).
- **Proposed option**:
  - Adopt 10 mmHg systolic, 5 mmHg diastolic, and 20 mg/dL glucose delta thresholds.
  - Require at least 5 readings over the 30-day window before asserting `rising` or `falling` direction; with fewer readings, report `"not_enough_history"`.
- **Why**: Home readings have substantial daily fluctuations. Requiring 5 readings and dual-agreement between median half-delta and Theil-Sen slope prevents false trend alerts.
- **File citation**: `backend-poc-technical/agents/trend_agent.py:55-63, 321`, `backend-poc-technical/agents/triage_protocol.py:76`, `docs/TREND_AGENT.md:110-120, 215-222`
- **Doctor decision**: 
  - [ ] Approve 10/5/20 thresholds and 5-reading minimum requirement
  - [ ] Adjust thresholds: __________________________________________________
  - **Doctor Signature / Date**: _____________________________________________

---

## Clinician Summary & Sign-Off

| Item | Topic | Current State | Proposed Action | Clinician Sign-Off |
| :--- | :--- | :--- | :--- | :--- |
| **D1** | Urdu Red-Flag Phrases | 14/20 missed (70% FNR); Blind: 3/20 detected (15%) | Pattern expansion / LLM hybrid (Table 6E) | __________________ |
| **D2** | Meter LO / HI Text | Unreadable text ends as review (`triage: null`) | Map LO -> `emergency`/`urgent`; HI -> `urgent`/`emergency` | __________________ |
| **D3** | 15 g Fast Sugar Guidance | 15g rule in prompt | Review against project non-prescriptive rule | __________________ |
| **D4** | Blood Pressure Guidelines | ACC/AHA 2017 citation (140/90, 180/120) | Confirm whether 2025 guideline changes thresholds | __________________ |
| **D5** | Non-Stop Vomiting | `urgent` (Talha, Shaiza) / `emergency` (Anam) | (a) urgent, (b) emergency, or (c) urgent unless danger signs | __________________ |
| **D6** | D15 HbA1c Reminder | Dormant in codebase (`interval_days=None`) | Doctor decides whether and how often (12/24/36 mo) | __________________ |
| **D7** | D12 Risk Panel | Provider-only behind flag, `RISK_CAN_RAISE=false` | Retain provider-only advisory view | __________________ |
| **D8** | Waist Range & Landmark | 40–200 cm; iliac crest helper text | Confirm Option (a) iliac crest vs (b) WHO midpoint | __________________ |
| **D9** | Longitudinal Trends | 10 / 5 / 20 mmHg & mg/dL; <3 gives `not_enough_history` | 5-reading minimum for trajectory arrow | __________________ |

**Reviewing Doctors**:
1. Dr Shaiza Jabbar, Medical Officer, Hearts International Hospital (to confirm permission to be named)
2. Captain Dr Talha Yasin, Army doctor, CMH Rawalpindi (to confirm exact title)
3. Dr Anam Zafar (agreed to be named, signed 14/10/26)

**Doctor Signature**: ________________________________________________________  
**Date Signed**: _____________________________________________________________
