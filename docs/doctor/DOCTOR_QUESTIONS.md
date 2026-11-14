# ChronicCare AI — Clinical Protocol Review & Doctor Questions

> **Audience:** Consulting Clinician / Medical Reviewer  
> **Purpose:** Plain-language clinical validation questions for final triage policies, model thresholds, and edge-case handling.  
> **Privacy Invariant:** Zero patient PHI; all cases reference synthetic simulated benchmark personas. No clinician names are recorded in documentation.  
> **Date:** November 2026

---

## Instructions for Clinical Reviewer
For each clinical question below, please review the current application behavior and check your preferred response. If you recommend an alternate threshold or rule, please write it in the **"CHANGE IT TO"** line. The technical implementation impact for each choice is detailed under *What Changes in the App*.

---

### Question 1: Patient Reports Feeling Unwell Without Entering Numerical Readings

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 1: NO READINGS ENTERED + FEELING UNWELL -> ELEVATE TO YELLOW (REVIEW)?                   |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| In daily check-ins, a patient with Type-2 Diabetes or Hypertension sometimes completes their      |
| interview without measuring or providing blood glucose or blood pressure values (e.g. no glucometer|
| available), but explicitly tells the conversational agent:                                        |
| "I am feeling unwell today" / "Tabiyat kharab lag rahi hai" / "Feeling dizzy and weak".           |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| Unless explicit red-flag danger phrases (e.g., chest pain, confusion, severe breathlessness) are  |
| triggered, the system notes missing readings but leaves triage at Green (Routine) because no acute|
| physiological crisis was measured.                                                                |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| If a chronic patient has no readings AND explicitly reports feeling unwell, should the system     |
| automatically escalate their triage severity from Green (Routine) to Yellow (Review), prompting   |
| clinic staff to call the patient or schedule an interim review?                                   |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [X] YES  -- Elevate to Yellow (Review). Unmeasured symptoms in chronic illness warrant review.  |
|               Answer: YES. Approved by the doctor on record (Nov 2026).                           |
|                                                                                                   |
|   [ ] NO   -- Keep at Green (Routine) unless specific red-flag keywords or vitals trigger Yellow. |
|                                                                                                   |
|   [ ] CHANGE IT TO: _____________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If YES: In `backend-poc-technical/agents/triage_protocol.py` (Rule R8), any check-in where     |
|   `readings_present == False` AND `general_unwell == True` will deterministically assign          |
|   severity = "review" (Yellow chip) and advise prompt clinic contact.                             |
| - If NO: Rule R8 remains advisory, keeping triage at "routine" while prompting the patient to      |
|   measure vitals when possible.                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 2: High Cardiovascular Risk Alert Cooldown Period (30 Days)

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 2: HIGH-RISK STAGE-2 ELEVATION COOLDOWN -> WAIT 30 DAYS BEFORE RE-ELEVATING?             |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| Our machine learning risk engine calculates the 10-year Framingham Cardiovascular Disease (CVD)   |
| risk. When a patient's risk is elevated (score >= 20% / "High Risk"), Stage-2 Final Triage        |
| elevates their routine check-in from Green (Routine) to Yellow (Review) so the physician can      |
| conduct a comprehensive cardiovascular review.                                                     |
|                                                                                                   |
| THE DILEMMA:                                                                                      |
| Chronic patients submit check-ins several times a week. Without a cooldown window, a patient with |
| a high baseline Framingham score would be elevated to Yellow on every single daily check-in,      |
| causing severe alert fatigue for the clinic and unnecessary alarm for the patient.               |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| We enforce a 30-day cooldown (`RISK_RAISE_COOLDOWN_DAYS = 30`). Once elevated to Yellow based on |
| baseline risk, the patient remains at Green for subsequent normal check-ins for the next 30 days |
| unless acute vitals, worsening trends (5 consecutive rises), or symptoms occur.                   |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| Is a 30-day cooldown clinically sound for non-acute baseline risk elevation?                      |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] YES  -- Retain the 30-day cooldown window. Prevents alert fatigue while ensuring review.    |
|                                                                                                   |
|   [ ] NO   -- No cooldown. Elevate every single check-in to Yellow regardless of frequency.       |
|                                                                                                   |
|   [X] CHANGE IT TO: "just having heart risk doesn't need a review unless associated with any      |
|       symptoms" (the doctor on record, Nov 2026). Retain 30-day cooldown applied to this         |
|       symptom-linked raise only. Asymptomatic high risk remains Green (Routine).                  |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If YES: `RISK_RAISE_COOLDOWN_DAYS = 30` in `backend-poc-technical/agents/final_triage.py` is     |
|   confirmed.                                                                                      |
| - If NO: Cooldown logic is disabled; every high-risk check-in will elevate to Yellow.             |
| - If CHANGED: The integer constant in `agents/final_triage.py` is updated to the specified value. |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 3: Diabetes Control Model (Predicted HbA1c >= 8.0%) Elevating Green to Yellow

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 3: DIABETES CONTROL MODEL (HbA1c >= 8.0%) -> ELEVATE GREEN TO YELLOW (REVIEW)?           |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| A dedicated NHANES-trained XGBoost classifier predicts glycemic control status based on patient   |
| history, age, BMI, vitals history, and lifestyle factors. An output label of "poor_control"       |
| correlates to laboratory HbA1c >= 8.0%.                                                           |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| When the diabetes control classifier indicates poor glycemic control (predicted HbA1c >= 8.0%),   |
| should the deterministic triage engine elevate the patient's daily triage from Green (Routine) to |
| Yellow (Review), prompting the physician to order a confirmatory laboratory HbA1c panel and       |
| evaluate medication adherence?                                                                    |
|                                                                                                   |
| NOTE:                                                                                             |
| Red flags (hypoglycemia, crisis glucose > 300 mg/dL) already trigger Red (Urgent/Emergency).      |
| This question applies strictly to asymptomatic, stable patients whose model indicators suggest     |
| chronic poor control.                                                                             |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] YES  -- Elevate Green to Yellow (Review). Uncontrolled HbA1c warrants medical review.       |
|                                                                                                   |
|   [ ] NO   -- Do NOT elevate triage color. Keep at Green (Routine), but display the poor control  |
|               risk badge on the provider review portal for optional clinician inspection.         |
|                                                                                                   |
|   [X] CHANGE IT TO: "I am fine with this raising to Yellow for review, but only if the model     |
|       meets its pre-registered validation gates. Since it didn't, it must NOT be used to raise   |
|       triage in this release." (the doctor on record, Nov 2026). Model trained, not shipped.      |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If YES: In `backend-poc-technical/agents/final_triage.py`, `evaluate_stage2_risk()` will check  |
|   `diabetes_control_poor` alongside Framingham high risk to elevate severity from Routine to      |
|   Review.                                                                                         |
| - If NO: Diabetes control predictions will only be surfaced as an informational card in           |
|   `app/components/provider/ReconciliationAlertDetail.tsx` without affecting triage chips.          |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 4: Clinical Edge Cases & Practice Gaps (Category B Gaps Audit)

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 4: BORDERLINE PRESENTATIONS & UNIDENTIFIED APP GAPS                                      |
+---------------------------------------------------------------------------------------------------+
| BENCHMARK EVALUATION FINDINGS:                                                                    |
| We evaluated the multi-agent pipeline against 51 clinical persona test scenarios across Type-2   |
| Diabetes and Hypertension:                                                                        |
| - Overall Under-Triage Rate: 2.0% (1/51 cases).                                                   |
| - Missed Emergency / Urgent Recall: 0.0% (0/4 cases missed; 100% emergency recall).               |
| - Detailed Case Audit: The single under-triaged case (`p30_fear_prognosis_handled`) was caused     |
|   by a synthetic test harness dialog loop (Category A).                                           |
| - Real App Logic Gaps Identified: EXACTLY 0 CASES (Category B).                                   |
|                                                                                                   |
| CLINICAL INQUIRY:                                                                                 |
| Although our deterministic rules correctly captured all acute safety scenarios in our benchmark  |
| suite, what common, subtle clinical presentations in outpatient diabetes or hypertension care     |
| do you believe could slip through standard automated triage rules?                                |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN FEEDBACK:                                                                               |
|                                                                                                   |
|   [ ] NO IMMEDIATE GAPS -- Current triage rules (R1 to R8) and red-flag dictionaries provide       |
|       comprehensive coverage for outpatient tele-triage.                                          |
|                                                                                                   |
|   [ ] SUGGESTED CLINICAL EDGE CASE TO ADD TO SUITE:                                               |
|                                                                                                   |
|       - Clinical Scenario / Presentation:                                                         |
|         _________________________________________________________________________________________ |
|         _________________________________________________________________________________________ |
|                                                                                                   |
|       - Patient Symptoms / Reported Vitals:                                                       |
|         _________________________________________________________________________________________ |
|         _________________________________________________________________________________________ |
|                                                                                                   |
|       - Expected Triage Action:                                                                   |
|         [ ] Yellow (Review within 48h)                                                            |
|         [ ] Red (Urgent clinic visit within 12h)                                                  |
|         [ ] Emergency (Immediate 1122 dispatch)                                                   |
|                                                                                                   |
|       - Guideline Justification:                                                                  |
|         _________________________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| Any edge cases identified above will be formalized as synthetic test scenarios in                 |
| `backend-poc-technical/scenarios/` and encoded into `agents/triage_protocol.py` with full        |
| regression coverage.                                                                              |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 5: Subjective BP Increase Belief ("mere khyal me bp barh gaya")

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 5: SUBJECTIVE PERCEPTION OF ELEVATED BP -> ESCALATE TO YELLOW (REVIEW) OR GREEN (ROUTINE)?|
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| In Urdu and Roman Urdu check-ins, patients frequently report subjective beliefs about their blood |
| pressure without providing a numeric cuff measurement, such as:                                   |
| "mere khyal me bp barh gaya" / "mujhe lagta hai mera bp high hai" / "I think my blood pressure    |
| has gone up".                                                                                     |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| The check-in prompts the patient to measure their blood pressure with a cuff. If no measurement   |
| is entered and no acute symptoms (severe headache, chest pain, neurological deficit) are present,  |
| the check-in completes at Green (Routine) because subjective perception of blood pressure is known |
| to be poorly correlated with true hemodynamic values.                                             |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| Should a patient's unverified subjective belief that their blood pressure is elevated ("mere       |
| khyal me bp barh gaya") automatically escalate their triage to Yellow (Review), or should it      |
| remain at Green (Routine) while advising them to take a formal cuff measurement?                  |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] KEEP AT GREEN (ROUTINE) -- Advise cuff measurement; subjective blood pressure perception is |
|       clinically unreliable in asymptomatic patients.                                             |
|                                                                                                   |
|   [ ] ELEVATE TO YELLOW (REVIEW) -- Unverified belief of hypertension warrants clinical review to  |
|       assess medication adherence or prompt clinic follow-up.                                     |
|                                                                                                   |
|   [ ] CHANGE IT TO: _____________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If KEEP AT GREEN: Subjective phrases remain informational prompts advising cuff measurement.    |
| - If ELEVATE TO YELLOW: The phrase is mapped into the symptom dictionary to set triage = review.  |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 6: Severe Chest Pain in Urdu ("seene me shadeed dard")

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 6: SEVERE CHEST PAIN IN URDU -> TRIGGER EMERGENCY (1122 DISPATCH) OR URGENT CLINIC VISIT? |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| Red flag detection captures chest pain in English, Urdu script, and Roman Urdu. For the phrase:   |
| "seene me shadeed dard" / "سینے میں شدید درد" (severe chest pain).                                |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| All acute chest pain mentions immediately trigger Red / EMERGENCY (immediate advice to call 1122 |
| emergency services, interview halted).                                                            |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| Confirm whether "seene me shadeed dard" should unconditionally trigger an EMERGENCY exit (1122    |
| ambulance dispatch) as currently implemented, or whether any non-cardiac modifier allows triage to|
| Urgent (same-day emergency department / urgent care visit)?                                       |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] CONFIRM EMERGENCY (1122 DISPATCH) -- Severe chest pain must always trigger immediate 1122   |
|       emergency failsafe across all languages without exception.                                  |
|                                                                                                   |
|   [ ] DOWNGRADE TO URGENT -- Advise urgent same-day emergency clinic visit rather than 1122.      |
|                                                                                                   |
|   [ ] CHANGE IT TO: _____________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If CONFIRM EMERGENCY: The Stage-1 invariant in `RED_FLAG_PATTERNS` remains active at Emergency.  |
| - If DOWNGRADE TO URGENT: The pattern is moved to the urgent symptom group in `triage_protocol.py`|
+---------------------------------------------------------------------------------------------------+
```

---

### Question 7: Bare "Shortness of Breath" Mentions vs Severe / Inability Presentations

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 7: BARE "SHORTNESS OF BREATH" -> EMERGENCY (1122) VS URGENT / CLINIC REVIEW?             |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| Patients frequently report mild, exertional, or chronic dyspnea using the bare clinical term      |
| "shortness of breath" (e.g. "I have some shortness of breath when walking"). Acute respiratory    |
| emergencies ("cannot breathe", "gasping for air", "suffocating", "saans bilkul nahi aa rahi")     |
| represent immediate life threats requiring 1122 ambulance dispatch.                              |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| "shortness of breath" is currently retained in `MULTILINGUAL_DANGER_CATEGORIES["breathing"]` in    |
| `input_triage.py`, unconditionally triggering Red / EMERGENCY (immediate 1122 dispatch).          |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| Should bare "shortness of breath" (without qualifiers like "severe", "at rest", or "inability to  |
| breathe") continue to trigger immediate Emergency (1122), or should bare mentions be classified  |
| as Urgent / Review (Yellow) unless accompanied by acute inability or chest symptoms?            |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] KEEP AS EMERGENCY -- Any mention of "shortness of breath" must remain an emergency failsafe. |
|                                                                                                   |
|   [ ] DOWNGRADE BARE PHRASE TO URGENT/REVIEW -- Only acute inability ("cannot breathe", "gasping", |
|       "severe breathlessness at rest") triggers Emergency 1122; bare mild dyspnea routes to Yellow.|
|                                                                                                   |
|   [ ] CHANGE IT TO: _____________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If KEEP AS EMERGENCY: "shortness of breath" remains in `input_triage.py` breathing red flags.   |
| - If DOWNGRADE: Remove bare "shortness of breath" from `input_triage.py`, relying on               |
|   `red_flag_patterns.py` for severe/inability breathing distress, routing bare dyspnea to Yellow.    |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 8: Poetic and Emotional "dil mein dard" vs Physical Cardiac Pain

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 8: EMOTIONAL "DIL MEIN DARD" -> SUPPRESS FROM EMERGENCY (1122) UNLESS PHYSICAL CUES?    |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| In Urdu and Roman Urdu cultural expressions, patients frequently use "dil mein dard" or           |
| "دل میں درد" metaphorically to express emotional grief, missing a loved one, heartbreak, or       |
| sorrow (e.g. "dil mein dard hai uski yaad mein", "dil bohot dukhta hai jab wo yaad aata hai").    |
| True acute coronary syndrome presentations typically involve physical radiation (left arm, jaw),  |
| diaphoresis (sweating), crushing pressure, or dyspnea.                                            |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| The pattern matcher suppresses "dil" mentions from Red (Emergency) when accompanied by emotional  |
| tokens ("yaad", "udas", "gham", "ro raha", "sad", "miss", "heartbroken") unless explicit physical |
| cardiac markers (radiating to left arm/jaw, diaphoresis, severe crushing pressure) are affirmed.  |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| Confirm whether metaphorical/emotional "dil" expressions should be suppressed from immediate 1122 |
| emergency failsafe unless coupled with objective physical cardiac features?                       |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] CONFIRM SUPPRESSION -- Emotional "dil mein dard" without physical cardiac cues must not      |
|       trigger 1122 ambulance dispatch; route to standard interview or supportive follow-up.       |
|                                                                                                   |
|   [ ] TRIGGER EMERGENCY ON ANY "DIL DARD" -- Any mention of "dil mein dard" regardless of context  |
|       must immediately halt the check-in and dispatch 1122.                                       |
|                                                                                                   |
|   [ ] CHANGE IT TO: _____________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If CONFIRM: The emotional contextual exclusion filter in `agents/red_flag_patterns.py` is       |
|   formally ratified for Stage-1 red-flag screening.                                               |
| - If TRIGGER EMERGENCY: Emotional exclusion is removed, causing any "dil ... dard" phrase to     |
|   unconditionally escalate to Red (Emergency).                                                    |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 9: Chronic Neuropathy and Long-Standing Weakness vs Acute FAST Stroke

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 9: CHRONIC NEUROPATHY ("FEET NUMB FOR YEARS") -> SUPPRESS FROM ACUTE STROKE RED FLAG?   |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| Diabetic peripheral neuropathy commonly causes long-standing bilateral numbness or weakness in the|
| lower extremities (e.g. "my feet have been numb and weak for years", "pairon mein saalon se      |
| sunnpan hai"). In contrast, acute stroke (FAST protocol) presents with acute, sudden, unilateral  |
| focal neurological deficits (facial droop, arm weakness, slurred speech, acute hemiparesis).      |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| The pattern matcher suppresses chronic duration phrases ("for years", "saalon se", "purana",      |
| "chronic") and bilateral foot numbness from triggering Red (Emergency FAST stroke), routing them |
| to routine/review assessment unless acute unilateral or facial/speech deficits are reported.      |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| Confirm whether chronic long-standing bilateral numbness/weakness should remain suppressed from   |
| acute 1122 stroke dispatch?                                                                       |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] CONFIRM SUPPRESSION -- Chronic diabetic neuropathy ("feet numb for years") is not an acute  |
|       stroke and should not dispatch emergency 1122; assess in routine clinic review.             |
|                                                                                                   |
|   [ ] TRIGGER EMERGENCY ON ANY NUMBNESS/WEAKNESS -- Any mention of numbness or weakness must      |
|       trigger immediate 1122 emergency failsafe regardless of chronicity.                         |
|                                                                                                   |
|   [ ] CHANGE IT TO: _____________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If CONFIRM: Chronic duration filters in `agents/red_flag_patterns.py` are clinically ratified.  |
| - If TRIGGER EMERGENCY: Chronic duration suppression is removed from stroke screening.           |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 10: Exertional Dyspnea Relieved by Rest vs Acute Rest Dyspnea

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 10: EXERTIONAL DYSPNEA RELIEVED BY REST -> ROUTE TO REVIEW (YELLOW) VS EMERGENCY (RED)?  |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| Patients with stable chronic lung disease or deconditioning often report dyspnea strictly during   |
| physical exertion that resolves with rest (e.g. "I get breathless only when walking fast and feel |
| better after resting", "tez chalne se sans phoolti hai aaram karne se theek ho jati hai").        |
| Acute respiratory emergencies (acute pulmonary edema, severe bronchospasm, PE) present with acute |
| resting dyspnea, gasping, inability to speak, or suffocating sensations.                          |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| Exertion coupled with rest relief ("walking fast ... better after rest") is suppressed from Red   |
| (Emergency 1122 dispatch) and evaluated on the clinical review / outpatient follow-up path.        |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| Confirm whether exertional dyspnea that readily resolves with rest should be routed to clinical   |
| review (Yellow) rather than immediate 1122 emergency ambulance dispatch?                          |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] ROUTE TO REVIEW (YELLOW) -- Exertional dyspnea relieved by rest warrants outpatient review,  |
|       not emergency 1122 dispatch.                                                                |
|                                                                                                   |
|   [ ] TRIGGER EMERGENCY (1122) -- Any breathlessness on walking must trigger immediate 1122.      |
|                                                                                                   |
|   [ ] CHANGE IT TO: _____________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If ROUTE TO REVIEW: The exertion+rest suppression rule in `agents/red_flag_patterns.py` is      |
|   clinically ratified, preventing unnecessary ambulance dispatches for exertional shortness.      |
| - If TRIGGER EMERGENCY: Exertion+rest relief suppression is disabled.                             |
+---------------------------------------------------------------------------------------------------+
```

---

### Question 11: Base Screen Remote-Past and Exertion Over-Triggering

```
+---------------------------------------------------------------------------------------------------+
| QUESTION 11: BASE SCREEN OVER-TRIGGERS ON CLEARLY PAST OR EXERTIONAL EVENTS;                       |
| MAY WE ADD REMOTE-PAST / EXERTION GUARDS TO INPUT_TRIAGE.PY?                                      |
+---------------------------------------------------------------------------------------------------+
| CLINICAL CONTEXT:                                                                                 |
| In the protected base input screener (`agents/input_triage.py`), keyword matching triggers Red    |
| (Emergency failsafe) on utterances describing historical past events or chronic exertional events  |
| that do not represent active, acute medical emergencies.                                           |
|                                                                                                   |
| EXAMPLES OBSERVED:                                                                                |
| 1. "I fainted once at a wedding in 2019" (past remote event, years ago)                           |
| 2. "I had chest pain last month, doctor said muscular, fine now" (resolved past event)             |
| 3. "shortness of breath when climbing stairs, same as always" (stable exertional symptom)         |
|                                                                                                   |
| CURRENT APP BEHAVIOR:                                                                             |
| Because `input_triage.py` does not inspect remote years ("2019") or past months ("last month") or  |
| chronic exertional baselines ("climbing stairs, same as always"), all three trigger immediate Red.|
| (Note: `agents/red_flag_patterns.py` correctly handles these, but `input_triage.py` runs first).    |
|                                                                                                   |
| CLINICAL PROPOSAL:                                                                                |
| May we update `input_triage.py` with remote-past and exertional baseline guards to avoid false     |
| ambulance dispatches on historical or stable exertional descriptions?                             |
+---------------------------------------------------------------------------------------------------+
| CLINICIAN DECISION:                                                                               |
|                                                                                                   |
|   [ ] PERMIT GUARDS -- Add remote-past ("2019", "last month") and exertional baseline ("climbing  |
|       stairs, same as always") guards to `input_triage.py`.                                        |
|                                                                                                   |
|   [ ] KEEP CURRENT BEHAVIOR -- Preserve protected strict keyword matching in `input_triage.py`.    |
|                                                                                                   |
|   [ ] CHANGE IT TO: _____________________________________________________________________________ |
+---------------------------------------------------------------------------------------------------+
| WHAT CHANGES IN THE APP:                                                                          |
| - If PERMIT GUARDS: Add targeted remote-past and exertion filters in `input_triage.py`.           |
| - If KEEP CURRENT: Keep `input_triage.py` byte-identical to dev as protected baseline failsafe.   |
+---------------------------------------------------------------------------------------------------+
```

---

## Summary of Clinical Rules Governed by this Review

| Rule Ref | Clinical Focus | Current Default | Proposed Review Modification |
|:---|:---|:---|:---|
| **R8** | Missing vitals with subjective malaise | Routine (Green) with warning | Approved by the doctor on record: escalate to Review (Yellow) (Nov 2026) |
| **Stage 2** | CVD High-Risk Alert Cooldown | 30 days suppression window | Approved by the doctor on record: high risk requires symptoms to escalate; 30d cooldown retained (Nov 2026) |
| **Stage 2** | Uncontrolled Diabetes (HbA1c >= 8%) | Informational model score | Approved by the doctor on record if future model passes gates; not shipped in FYP-1 (Nov 2026) |
| **Audit** | Edge-case benchmark suite | 51 synthetic personas (0 Category B gaps) | Expandable based on clinician feedback |
| **Lang-1** | Subjective BP increase ("mere khyal me bp barh gaya") | Routine (Green) | Option to escalate to Review (Yellow) |
| **Lang-2** | Urdu severe chest pain ("seene me shadeed dard") | Emergency (1122) | Confirmation of emergency failsafe |
| **Lang-3** | Bare "shortness of breath" | Emergency (1122) | Option to downgrade bare dyspnea to Review |
| **Lang-4** | Emotional "dil mein dard" | Suppressed from Red unless physical cardiac cues present | Question for the doctor on record (Nov 2026) |
| **Lang-5** | Chronic neuropathy ("feet numb for years") | Suppressed from acute FAST stroke | Question for the doctor on record (Nov 2026) |
| **Lang-6** | Exertional dyspnea relieved by rest | Suppressed from Red, routed to Review | Question for the doctor on record (Nov 2026) |
| **Lang-7** | Base screen over-triggering on past/exertion | Emergency (1122) in `input_triage.py` | Question for the doctor on record: allow remote-past/exertion guards (Nov 2026) |



