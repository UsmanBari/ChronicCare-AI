# Clinical Rules Register

> **Reviewed by Dr Shaiza Jabbar and Capt Dr Talha Yasin, 13 Oct 2026.** Every number and rule in this document describes exactly what the code does; it reflects the deterministic decision logic in code.
> *Notice:* Nothing in this system is claimed to be clinically validated beyond clinician review. ChronicCare AI is decision support for a clinician. It never diagnoses, never gives treatment or dose advice, never changes a medication, and never ends a conversation about a possible emergency with reassurance.

## 1. Levels

| Level | Meaning | Text shown to the patient | Who is told |
|---|---|---|---|
| emergency | Warning signs are present | Call your local emergency number now. Your care team is being alerted. | Provider alerted immediately; saved by the same request that decides it |
| urgent | Needs a clinician the same day | Please contact your clinician today. If you feel worse, call your local emergency number. | Top of the provider queue after emergencies |
| review | A clinician should look at it | A clinician will review this. Please measure again later today and at the same time tomorrow. | Normal provider review queue |
| routine | Nothing to flag | (none) | Nobody |

A single number never decides an emergency. A numeric trigger starts the confirmation questions in section 3; only the answers decide the level. The only things that give emergency guidance at once are the danger phrases in section 5, because a patient reporting such a symptom is reporting a warning sign (the usual practice in nurse triage).

## 2. What starts a protocol (highest priority first)

| Priority | Protocol | Starts when | Constants | Source |
|---|---|---|---|---|
| 1 | bp_severe | systolic >= 180 or diastolic >= 120 | `DANGEROUS_BP_SYSTOLIC_MMHG`, `DANGEROUS_BP_DIASTOLIC_MMHG` | 2025 AHA/ACC Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults (replaces 2017; thresholds unchanged: Stage 2 from 140/90, crisis at 180/120); Project Proposal Section 27 |
| 2 | glucose_high | glucose >= 250 mg/dL | `GLUCOSE_HIGH_MG_DL` | Project Proposal Section 15 |
| 3 | glucose_low | glucose < 70 mg/dL | `GLUCOSE_LOW_MG_DL` | ADA Standards of Care (current edition) |
| 4 | bp_low | systolic < 90 or diastolic < 60 | `BP_LOW_SYSTOLIC_MMHG`, `BP_LOW_DIASTOLIC_MMHG` | Project team, illustrative (no guideline cited) |
| 5 | bp_change | systolic at least 20 mmHg above the patient's own median, and the reading is not already in the crisis range | `BP_CHANGE_NOTABLE_MMHG` | Project team, illustrative (no guideline cited); supervisor feedback |

Only the highest-priority protocol is run for a check-in. Readings that are ordinary start nothing and the check-in continues as before.

**The patient's own baseline.** The median systolic (and diastolic) of the patient's own readings from earlier completed, non-emergency check-ins and entered baseline readings in the last 14 days, using at most the latest 7. If there are fewer than 3 systolic readings there is no baseline and the change rule never fires. Constants: `BASELINE_WINDOW_DAYS`, `BASELINE_MAX_READINGS`, `BASELINE_MIN_READINGS`.

## 3. The questions and how each protocol decides

Each question is asked once. If an answer cannot be understood it is asked one more time; if it is still unclear it is recorded as **unknown**, and unknown answers to the warning-sign questions raise the level (they are never read as 'no'). A danger phrase in any answer ends the protocol as an emergency. When an emergency is already settled the remaining questions are skipped.

### bp_severe (crisis-range blood pressure)

Questions, in order:

1. `recheck`: "Please sit down, rest quietly for 5 minutes, then measure your blood pressure again. What is the new reading? If you cannot measure again, type: cannot"
2. `symptoms`: "Right now, do you have any of these: chest pain or pressure, trouble breathing, back pain, numbness or weakness, a change in your vision, trouble speaking, a severe headache, or confusion? Answer yes or no."
3. `substances`: "In the last few hours, did you take cold or flu medicine, painkillers such as ibuprofen, steroids, or stimulants such as energy drinks, strong coffee or tea, or nicotine, or did you miss your blood pressure medicine? Answer yes or no, and tell me which."
4. `circumstances`: "Just before the first reading, were you in pain, very upset or anxious, or physically active? Answer yes or no."

| Condition | Result |
|---|---|
| Warning symptoms = yes | emergency (stops the questions at once) |
| Otherwise start at review. Symptoms unknown | raise to urgent |
| The re-measure is missing, 'cannot', or unclear | raise to urgent |
| The re-measure is still in the crisis range (systolic >= 180 or diastolic >= 120) | raise to urgent |
| The re-measure is below the crisis range but systolic >= 140 or diastolic >= 90 | stay at review, reason 'improved after rest but still high' |
| The re-measure is lower | stay at review, reason 'first reading in the crisis range, normal after rest' |
| Pain, stress or activity before the first reading = yes | added to the reasons, no change of level |
| Medicines, caffeine, nicotine or a missed dose named | recorded as contributing factors for the clinician, no change of level |

### bp_change (rise from the patient's own baseline)

Questions, in order:

1. `symptoms`: "Do you have a headache, dizziness, a pounding heartbeat, blurred vision or shortness of breath right now? Answer yes or no."
2. `substances`: "In the last few hours, did you take cold or flu medicine, painkillers such as ibuprofen, steroids, or stimulants such as energy drinks, strong coffee or tea, or nicotine? Answer yes or no, and tell me which."
3. `adherence`: "Did you take your blood pressure medicine as prescribed over the last two days? Answer yes or no."
4. `circumstances`: "Just before the reading, were you in pain, very upset or anxious, or physically active? Answer yes or no."
5. `orthostatic`: "Do you feel dizzy or faint when you stand up? Answer yes or no." *(asked only at age 65 and over)*

| Condition | Result |
|---|---|
| Start at review | reason: the size of the rise over the patient's usual |
| The rise is >= 40 mmHg | raise to urgent |
| Symptoms = yes, or unknown | raise to urgent |
| Dizziness on standing = yes (age 65 and over only) | raise to urgent |
| Blood pressure medicine not taken as prescribed | recorded as a contributing factor, no change of level |

### bp_low (low blood pressure)

Questions, in order:

1. `symptoms`: "Do you feel dizzy, faint, very weak or unusually tired right now? Answer yes or no."
2. `medicines`: "Did you recently start, stop or change a medicine, or have you been vomiting, had diarrhoea, or been drinking very little? Answer yes or no, and tell me which."
3. `falls`: "Have you fallen or nearly fallen today? Answer yes or no." *(asked only at age 65 and over)*

| Condition | Result |
|---|---|
| Start at review | reason: blood pressure is low |
| Symptoms (dizzy, faint, very weak, unusually tired) = yes, or unknown | raise to urgent |
| A fall or near-fall today = yes (age 65 and over only) | raise to urgent |

### glucose_high (high glucose)

Questions, in order:

1. `dka_symptoms`: "Do you have nausea or vomiting, stomach pain, fast or deep breathing, breath that smells fruity, or feel very drowsy? Answer yes or no."
2. `thirst`: "Are you very thirsty and passing urine much more than usual? Answer yes or no."
3. `context`: "Did you eat a large meal just before, miss your insulin or diabetes medicine, or have an illness or infection? Answer yes or no, and tell me which."

| Condition | Result |
|---|---|
| Warning symptoms (nausea or vomiting, stomach pain, fast or deep breathing, fruity breath, very drowsy) = yes | emergency (stops the questions at once) |
| Otherwise start at review. Warning symptoms unknown | raise to urgent |
| Glucose >= 300 mg/dL | raise to urgent |
| Marked thirst and passing much more urine = yes | added to the reasons, no change of level |
| Large meal, missed insulin or diabetes medicine, illness named | recorded as contributing factors, no change of level |

### glucose_low (low glucose)

Questions, in order:

1. `neuro`: "Are you confused, very drowsy, or having trouble speaking or staying awake? Answer yes or no."
   - If `neuro` is yes or reported, followed by targeted orientation clarification: `orientation`: "Is the patient oriented in time, place and person? Answer yes or no."
2. `can_swallow`: "Can you swallow and eat or drink safely right now? Answer yes or no."
3. `symptoms`: "Do you feel shaky, sweaty, hungry or have a pounding heartbeat? Answer yes or no."
4. `context`: "Did you take insulin or diabetes tablets, skip or delay a meal, or exercise a lot? Answer yes or no, and tell me which."

| Condition | Result |
|---|---|
| Neuro = yes, and Orientation = no or unclear | emergency (stops the questions at once) |
| Neuro = yes, and Orientation = yes (oriented) | review (does not escalate to emergency) |
| Cannot swallow and eat or drink safely (can_swallow is no) | emergency (stops the questions at once) |
| Otherwise start at review. Warning answers unknown | raise to urgent |
| Glucose < 54 mg/dL | raise to urgent |
| Shaky, sweaty, hungry or pounding heartbeat = yes | added to the reasons, no change of level |
| Insulin or tablets taken, skipped or delayed meal, exercise named | recorded as contributing factors, no change of level |

### Stroke Extras Rule (Reviewed by Dr Shaiza Jabbar and Capt Dr Talha Yasin, 13 Oct 2026)

Stroke extra symptoms: dizziness, blurred vision, headache (`STROKE_EXTRAS_KEYWORDS`).
Main stroke signs: one-sided weakness, facial droop (`STROKE_MAIN_KEYWORDS`).

| Condition | Result |
|---|---|
| Stroke extras combined with one-sided weakness or facial droop | emergency (stops questions at once; reasons list the extras) |
| Stroke extras alone in patient aged >= 65 with heart or brain history (earlier heart attack, stroke, TIA, ischaemic heart disease) OR with >= 2 of hypertension, diabetes, ischaemic heart disease | urgent (advice text: "Please go for an urgent CT scan today.") |
| Stroke extras alone in anyone else | review |

The system gives **no treatment advice** in any protocol. The only advice it shows is the level text in section 1 (call emergency services, contact your clinician today, a clinician will review and please measure again later).

## 4. Age, inclusion and exclusions

- Adults only: age below `MIN_ADULT_AGE` (18) is refused at onboarding; above `MAX_PLAUSIBLE_AGE` (120) is treated as an invalid date of birth.
- For adults the 2025 AHA/ACC categories and the crisis limits do not change with age (thresholds identical to 2017). Age band changes the questions only: from `OLDER_ADULT_AGE` (65) the bp_change and bp_low protocols add one question each (dizziness on standing, falls).
- The patient confirms at onboarding that they are 18 or older and not pregnant. Pregnancy has different blood-pressure limits and is **out of scope**.
- Not for children, pregnancy, anyone who cannot answer for themselves, or any emergency. The system does not consider kidney disease, heart failure or other conditions that change the targets.

## 5. The interview: danger phrases, readings and missing data

**Danger phrases (end the interview as an emergency or urgent at any answer based on `RED_FLAG_LEVELS`).** A phrase is ignored only if a negation (no, not, never, without, don't, didn't, haven't, isn't and similar) appears within `NEGATION_WINDOW_WORDS` words before it in the same clause, or if it represents a past historical event (`_PAST_EVENT_CUES`: "last year", "years ago", etc.) which is triaged for review instead of emergency. Anything unclear is flagged. Text is split into clauses at punctuation and at but, however, although, though, and, while.

| Category | Phrases | Level | Notes (Reviewed 13 Oct 2026) |
|---|---|---|---|
| chest_pain | chest pain; chest tightness; chest pressure; chest hurts; pain in my chest; crushing chest; crushing chest pain; crushing pain in my chest; pain going down my left arm; pain in my left arm and jaw; left jaw pain with pressure; pain in my left arm; left arm pain; left jaw pain; bayein bazu me dard; bayein bazu mein dard; bayein bazu aur jabray me dard; bayein jabray me dard; baayein baazu me dard; seene me dabao aur bayein bazu me dard; seene mein shadeed dabao aur bayein baazu me dard; سینے میں درد; بائیں بازو میں درد; بائیں جبڑے میں درد; بائیں بازو اور جبڑے میں درد | emergency | Negations ("no chest pain") not triggered; past events ("chest pain last year") go to review. |
| breathing | can't breathe; cant breathe; cannot breathe; struggling to breathe; severe shortness of breath; gasping for air; سانس لینے میں دشواری; سانس نہیں آ رہی | emergency | |
| confusion | slurred speech; can't speak clearly; cant speak clearly; don't know where i am; do not know where i am; samajh nahi aa raha main kahan hoon; main kahan hoon; disoriented; سمجھ نہیں آ رہا میں کہاں ہوں; کہاں ہوں | emergency | Word "confused" alone removed ("confused by my morning pills" not emergency); acute disorientation wording triggers emergency. |
| loss_of_consciousness | fainted; passed out; lost consciousness; blacked out; بے ہوش | emergency | |
| one_sided_weakness | one side weak; one-sided weakness; can't move one side; cant move one side; face drooping | emergency | |
| unable_to_keep_fluids | can't keep anything down; can't keep fluids down; can't keep water down; can't keep medicines down; dawa nahi ruk rahi; dawa ulti mein nikal jati hai; paani bhi nahi rukta; پانی بھی نہیں رک رہا; دوائی نہیں رک رہی | emergency | Elevated from urgent to emergency by clinician consensus (3 Nov 2026). Acute dehydration, AKI, and DKA risk. |
| non_stop_vomiting | vomiting nonstop; vomiting non-stop; vomiting all day; musalsal ultiyan; ulti ruk nahi rahi; مسلسل الٹیاں; الٹی رک نہیں رہی | urgent | Stays urgent by default; prompts one follow-up question regarding severe warning signs (blood/dark material, confusion, dizziness, >24h) which elevates to emergency if positive. |
| severe_headache | worst headache; severe headache; thunderclap headache | emergency | |
| vision_loss | sudden vision loss; lost my vision; went blind; can't see at all; cannot see at all | emergency | |

The Urdu phrases have been reviewed; Urdu negation is handled for danger screening.

**Readings.** A glucose must be one number from 20 to 600 mg/dL (`GLUCOSE_RANGE_MG_DL`); a blood pressure one pair with systolic 60 to 260 (`SYSTOLIC_RANGE_MMHG`), diastolic 30 to 160 (`DIASTOLIC_RANGE_MMHG`) and systolic greater than diastolic. Several plausible numbers, a negative number, a value in mmol/L or an out-of-range value count as **missing**; the patient is asked one clarifying question and the intake is tagged Low confidence. A meter that shows 'HI' is not understood (known limitation).

**Hand-off.** `check_dangerous_bp` reports a crisis-range pair; the interview keeps the reading and the protocol in section 3 decides.

### Update 3 Nov 2026: Vomiting and Unable to Keep Fluids / Medicines (Rule R4)

- **Consensus decision (all 3 doctors):** 'Unable to keep fluids down' or 'unable to keep medicines down' in adult chronic disease patients is elevated from URGENT to **EMERGENCY** (`unable_to_keep_fluids` -> `level: emergency`). This covers phrases like:
  - 'can't keep fluids down', 'can't keep anything down', 'can't keep medicines down', 'cannot keep water down', 'dawa nahi ruk rahi', 'paani bhi nahi ruk raha', 'dawa ulti mein nikal jati hai', 'پانی بھی نہیں رک رہا', 'دوائی نہیں رک رہی'.
  - Clinical rationale: Acute dehydration, electrolyte derangements, acute kidney injury risk, inability to retain essential diabetes/hypertension medications, and rapid progression to diabetic ketoacidosis (DKA) or hyperosmolar state.
- **Other non-stop vomiting (Rule R4 Part 2):** Non-stop vomiting without stated fluid/medication inability remains **URGENT** by default (`non_stop_vomiting` -> `level: urgent`), but prompts ONE follow-up question:
  - English: *"Are you vomiting blood or dark material, feeling confused or very dizzy, or have you been unable to keep fluids down for more than 24 hours?"*
  - Urdu: *"کیا آپ کو الٹی میں خون یا گہرے رنگ کا مواد آ رہا ہے، چکر یا الجھن ہے، یا 24 گھنٹے سے پانی بھی نہیں رک رہا؟"*
  - Roman Urdu: *"Kya aap ko ulti mein khoon ya gehre rang ka mawad aa raha hai, chakkar ya uljhan hai, ya 24 ghante se paani bhi nahi ruk raha?"*
  - An affirmative answer elevates triage to **EMERGENCY**. A negative answer maintains **URGENT**.
- **Age consideration (Dr Shaiza suggestion):** Dr Shaiza suggested considering age (more aggressive elevation in older adults). **Status: Suggested, not adopted** (no specific age cut-off provided; all adult patients elevated per consensus on severe warning signs).

### Update 3 Nov 2026: HbA1c 365-Day Preventive Screening Interval (Rule R5)

- **Approved by consensus (all 3 doctors):** Annual (365-day) screening reminder interval for stable hypertensive patients meeting treatment goals without diagnosed diabetes (`SCREENING_REMINDER_INTERVAL_DAYS = 365`).
- Suggests consulting a clinician for an HbA1c test if none has been performed within the past 365 days or if no records are available.
- Controlled via `SCREENING_REMINDER_INTERVAL_DAYS` environment variable; dormant when unconfigured.

### Update 3 Nov 2026: Provider-Only Experimental Risk Panel (Rule R6)

- **Approved by consensus (all 3 doctors):** Provider-only experimental risk panel (PR #90) with mandatory "Experimental / decision-support only" labelling.
- Available exclusively in the authenticated clinician review queue; never exposed to patients.
- Strictly decision-support only; cannot lower triage levels and never provides automatic medical diagnoses.

### Update 3 Nov 2026: Bare Glucose 2-40 Unit Re-Ask (Rule R7)

- **Consensus decision (2 doctors requested, approved):** On a bare glucose reading between 2.0 and 40.0 with no unit, the interview asks ONCE for the unit before treating the reading as possible severe hypoglycemia:
  - English: *"Is that number in mg/dL (most meters) or mmol/L?"*
  - Urdu: *"کیا یہ نمبر mg/dL میں ہے (زیادہ تر میٹر) یا mmol/L میں؟"*
  - Roman Urdu: *"Kya yeh number mg/dL mein hai (zyada tar meter) ya mmol/L mein?"*
- If the patient provides the unit (e.g. mmol/L), the engine converts to mg/dL (multiplied by 18.0) and evaluates against clinical thresholds.
- If STILL unclear after the re-ask (e.g. "don't know", no unit, or repeated bare number), the engine routes to the safe path: flagged for clinician review, attaches low-sugar guidance, never lowers triage level.

### Update 3 Nov 2026: Check-in With No Readings (Rule R8)

- **Consensus decision (3 doctors approved: Dr Shaiza Jabbar, Dr Anam Zafar, Doctor C (asked not to be named)):**
  - If a patient completes a check-in with **no blood glucose and no blood pressure reading**:
    - **ROUTINE** (`level: "routine"`, `requires_review: False`): when no symptoms were reported (all symptom questions answered negative, and no clinical symptoms extracted in free text).
    - **REVIEW** (`level: "review"`, `requires_review: True`): when any symptom is reported (affirmative answer to any symptom question, or symptom finding extracted in free text).
  - Both engines (v2 and v3) implement this rule identically across direct and graph modes.
  - *Note:* In v2 this lowers previous behavior (which held missing data in review or flagged review unconditionally) for symptom-free check-ins; this reflects the unanimous clinical decision of all three reviewing physicians.

#### Symptoms Gap Table (Reported by Doctors but not currently in Question Bank)

The doctors identified symptoms that should mandate clinician review, which are not currently explicitly probed as standalone questions in today's Question Bank:

| Symptom Identified by Doctors | Doctor Source | Today's Question Bank Status | Interim Safety Handling |
|---|---|---|---|
| Severe headache for days or repeated episodes / migraine episodes | Dr Shaiza Jabbar, Doctor C (asked not to be named) | Not asked as duration/episodes; only severe acute headache in `associated_symptoms` | Free text parsed via `extract_findings_from_answer` flags `headache` -> routes to `review` |
| Numbness in both feet or both hands | Dr Shaiza Jabbar, Doctor C (asked not to be named) | Feet sores/cuts asked in v2/v3; bilateral hand numbness not asked | Hand/limb numbness caught if acute (stroke extras); otherwise free text note routes to `review` |
| Slow wound healing | Doctor C (asked not to be named) | Not asked in current question bank | Captured via patient free-text note; requires future question bank expansion |
| Blurred vision (standalone / persistent outside acute context) | Dr Shaiza Jabbar, Doctor C (asked not to be named) | Included only inside acute composite symptom list (`hyperglycemia_symptoms`) | Captured if patient affirms composite question or reports in free text |

### Doctor review 3 Nov 2026: pending or not adopted

- **D1 word groups**: approved by Doctor C (asked not to be named) (raise to review + 1122 line). Dr Shaiza did not answer it; Dr Anam's page 1 was not received. Stays off in production until Release 2 decision.
- **D8 waist**: keep top of the hip bone and 40-200 cm (Dr Anam, Dr Shaiza). Doctor C (asked not to be named) prefers the WHO midpoint for medical use. Not changed (the risk model was trained on the hip-bone landmark).
- **D9 trend arrows**: keep 10 / 5 / 20 and 5 readings (Dr Anam, Dr Shaiza). Doctor C (asked not to be named) suggested 10 mg/dL for sugar. Not changed.
- **Dr Shaiza (vomiting age threshold)**: age-dependent threshold on vomiting (younger <50 = urgent; older = emergency). Location: `backend-poc-technical/agents/triage_protocol.py` lines 270-285 (`_decide_vomiting` / age checks), where age is currently read as `>=65` for extra questions but does not split triage level. Pending explicit cut-off consensus.
- **Dr Shaiza (high glucose >=250)**: high glucose >=250 without symptoms -> advise diet control and re-chart for 5 days. Location: `backend-poc-technical/agents/triage_protocol.py` lines 180-210 (`_decide_glucose_high`), where glucose 250 without symptoms is currently `review`. Not adopted (conflicts with clinical protocol rules).
- **Dr Shaiza (BP >=180/120 symptoms)**: BP >=180/120 message should list symptoms (headache, blurred vision, numbness) because patients say their BP is always high. Location: `backend-poc-technical/agents/triage_protocol.py` lines 120-140 (`_decide_bp_severe`), where asymptomatic 180/120 currently re-measures. Pending clinical consensus on re-measure vs immediate symptom inquiry.
- **Doctor C (asked not to be named) (waist WHO midpoint)**: waist measurement at WHO midpoint (between lowest rib and top of hip bone). Location: `backend-poc-technical/main.py` profile validation and `backend-poc-technical/agents/interview_bank/messages.json` waist landmark instructions. Not adopted (risk model NHANES training aligned with top of iliac crest).
- **Doctor C (asked not to be named) (sugar trend absolute delta)**: fasting blood glucose trend threshold of 10 mg/dL rather than 10%. Location: `backend-poc-technical/agents/trend_agent.py` and `backend-poc-technical/main.py` trend calculations. Not adopted (consensus of Dr Anam and Dr Shaiza kept 10%).
- **Doctor C (asked not to be named) (bilateral / recurrent symptoms)**: bilateral symptoms (feet/hands numbness) and recurrent headache mandate review. Location: `backend-poc-technical/agents/adaptive_interview_agent.py` symptom checks (recorded in R8 gap table; pending Question Bank addition in Release 2).

## 6. Medication confirmation

After the interview (and the protocol, if one was needed) the patient is asked about each **active** medication in the record, at most `MAX_MEDICATIONS` (20). The answer is read as: stopped (stop words such as stopped, quit, discontinued, no longer, anymore), still taking at the same dose, still taking at a different dose (only when a unit or dose word such as mg, tablet, half, twice, once, daily is given; a bare number is not a dose; the text is cut at `MAX_DOSAGE_CHARS` = 100), or unclear. Missed or skipped doses are not a stop. An unclear answer is asked once more, then recorded as unknown and left out of the comparison. A medication that the record lists as active but the patient says is stopped is high severity for the clinician. Every answer goes through the danger-phrase check first.

## 7. Known limitations

- No clinician has reviewed any value in this document.
- The language understanding is keyword and pattern based, English only for the interview.
- A glucose meter reading of 'HI' or 'LO' is not understood.
- Targets do not depend on the patient's individual target set by a clinician.
- Kidney disease, heart failure, pregnancy and other conditions are not considered.
- The negation window is a heuristic and can be fooled by unusual wording.
- The patient's own baseline needs at least three earlier readings in two weeks, so it does not exist for a new patient.

## 8. Every constant in the clinical code

| Constant | Value | File | Source | Meaning |
|---|---|---|---|---|
| `SUPPORTED_CONDITIONS` | `diabetes, hypertension` | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `INTERVIEW_COMPLETE` | `interview_complete` | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `SELF_REPORTED_ORIGIN` | `self_reported` | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `GLUCOSE_RANGE_MG_DL` | `20.0, 600.0` | adaptive_interview_agent.py | Project team, illustrative (no guideline cited) | A glucose outside this range is treated as a missing reading. |
| `SYSTOLIC_RANGE_MMHG` | `60, 260` | adaptive_interview_agent.py | Project team, illustrative (no guideline cited) | A systolic outside this range is treated as a missing reading. |
| `DIASTOLIC_RANGE_MMHG` | `30, 160` | adaptive_interview_agent.py | Project team, illustrative (no guideline cited) | A diastolic outside this range is treated as a missing reading. |
| `NEGATION_WINDOW_WORDS` | `3` | adaptive_interview_agent.py | Project team, illustrative (no guideline cited) | A negation within this many words before a danger phrase cancels it. |
| `DANGEROUS_BP_SYSTOLIC_MMHG` | `180` | adaptive_interview_agent.py | 2025 AHA/ACC Guideline (hypertensive crisis, replaces 2017, thresholds unchanged); Project Proposal Section 27 | Crisis-range limit; starts the confirmation protocol, never an emergency by itself. |
| `DANGEROUS_BP_DIASTOLIC_MMHG` | `120` | adaptive_interview_agent.py | 2025 AHA/ACC Guideline (hypertensive crisis, replaces 2017, thresholds unchanged); Project Proposal Section 27 | Same as above, diastolic limit. |
| `RED_FLAG_PATTERNS` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `RED_FLAG_LEVELS` | `unable_to_keep_fluids=urgent; dka_vomiting_high_glucose=urgent` | adaptive_interview_agent.py | Clinician review decision (13 Oct 2026) | Maps red-flag categories to urgent or emergency. |
| `_NEGATION_CUES` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_PAST_EVENT_CUES` | (see the sections above) | adaptive_interview_agent.py | Clinician review decision (13 Oct 2026) | Historical phrases ("last year", etc.) that route to review instead of emergency. |
| `_CLAUSE_BREAK` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_TIME_OF_DAY` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_NO_CUES` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_STRONG_YES` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_WEAK_YES` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_NO_PROBLEM` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_NEGATIVE_NUMBER` | (see the sections above) | adaptive_interview_agent.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `STROKE_EXTRAS_KEYWORDS` | `dizziness, blurred vision, headache` | triage_protocol.py | Clinician review decision (13 Oct 2026) | Neurological symptoms evaluated under stroke extras rule. |
| `STROKE_MAIN_KEYWORDS` | `weakness, droop` | triage_protocol.py | Clinician review decision (13 Oct 2026) | High-severity stroke signs triggering emergency. |
| `MIN_ADULT_AGE` | `18` | triage_protocol.py | Scope decision (adults only) | Younger patients are refused: paediatric blood pressure is judged against age, sex and height percentiles. |
| `OLDER_ADULT_AGE` | `65` | triage_protocol.py | Project team, illustrative (no guideline cited) | From this age two extra questions are asked (standing dizziness, falls). |
| `MAX_PLAUSIBLE_AGE` | `120` | triage_protocol.py | Project team, illustrative (no guideline cited) | Upper limit for a plausible age. |
| `BP_STAGE2_SYSTOLIC_MMHG` | `140` | triage_protocol.py | 2025 AHA/ACC Guideline (stage 2 hypertension, replaces 2017, thresholds unchanged: 140/90) | After a re-measure, at or above this the first reading is judged 'improved but still high'. |
| `BP_STAGE2_DIASTOLIC_MMHG` | `90` | triage_protocol.py | 2025 AHA/ACC Guideline (stage 2 hypertension, replaces 2017, thresholds unchanged: 140/90) | Same as above, diastolic limit. |
| `BP_LOW_SYSTOLIC_MMHG` | `90` | triage_protocol.py | Project team, illustrative (no guideline cited) | Common clinical convention for low blood pressure; starts the low-pressure questions. |
| `BP_LOW_DIASTOLIC_MMHG` | `60` | triage_protocol.py | Project team, illustrative (no guideline cited) | Same as above, diastolic limit. |
| `BP_CHANGE_NOTABLE_MMHG` | `20` | triage_protocol.py | Project team, illustrative (no guideline cited); supervisor feedback, October 2026 | Rise over the patient's own median that starts the change questions. |
| `BP_CHANGE_MARKED_MMHG` | `40` | triage_protocol.py | Project team, illustrative (no guideline cited) | A rise this large is urgent even without symptoms. |
| `BASELINE_MIN_READINGS` | `3` | triage_protocol.py | Project team, illustrative (no guideline cited) | A baseline is never built from fewer readings than this. |
| `BASELINE_MAX_READINGS` | `7` | triage_protocol.py | Project team, illustrative (no guideline cited) | Only the most recent readings are used. |
| `BASELINE_WINDOW_DAYS` | `14` | triage_protocol.py | Project team, illustrative (no guideline cited) | Only readings from this many days back are used. |
| `GLUCOSE_HIGH_MG_DL` | `250` | triage_protocol.py | Project Proposal Section 15 (glucose at or above 250 mg/dL with warning symptoms is Red) | Starts the high-glucose questions. |
| `GLUCOSE_URGENT_MG_DL` | `300` | triage_protocol.py | Project team, illustrative (no guideline cited) | At or above this a high glucose is urgent even without warning symptoms. |
| `GLUCOSE_LOW_MG_DL` | `70` | triage_protocol.py | ADA Standards of Care (current edition) (level 1 hypoglycaemia) | Starts the low-glucose questions. |
| `GLUCOSE_VERY_LOW_MG_DL` | `54` | triage_protocol.py | ADA Standards of Care (current edition) (level 2 hypoglycaemia) | Below this a low glucose is urgent. |
| `SYSTOLIC` | `blood_pressure_systolic` | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `DIASTOLIC` | `blood_pressure_diastolic` | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `GLUCOSE` | `glucose` | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `LEVEL_RANK` | `routine=0; review=1; urgent=2; emergency=3` | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `GUIDANCE` | `emergency=Call your local emergency number now. Your care team is being alerted.; urgent=Please contact your clinician today. If you feel worse, call your local emergency number.; review=A clinician will review this. Please measure again later today and at the same time tomorrow.; routine=` | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `_SYMPTOMS_CRISIS` | `chest pain or pressure, trouble breathing, back pain, numbness or weakness, a change in your vision, trouble speaking, a severe headache, or confusion` | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_BP_SEVERE_QUESTIONS` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_BP_CHANGE_QUESTIONS` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_BP_LOW_QUESTIONS` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_GLUCOSE_HIGH_QUESTIONS` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_GLUCOSE_LOW_QUESTIONS` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_OLDER_EXTRA` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_QUESTION_SETS` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_FACTOR_PATTERNS` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_CANNOT` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_CONTRADICTION` | (see the sections above) | triage_protocol.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `MAX_MEDICATIONS` | `20` | medication_confirmation.py | Project team, illustrative (no guideline cited) | Maximum number of medications asked about per check-in. |
| `MAX_DOSAGE_CHARS` | `100` | medication_confirmation.py | Project team, illustrative (no guideline cited) | Maximum length of a stored dose text. |
| `SELF_REPORTED_ORIGIN` | `self_reported` | medication_confirmation.py | Implementation detail (matching rule, no clinical threshold) | Implementation detail. |
| `_STOP_WORDS` | (see the sections above) | medication_confirmation.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_MISSED` | (see the sections above) | medication_confirmation.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_HARD_NO` | (see the sections above) | medication_confirmation.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_DOSE_HINT` | (see the sections above) | medication_confirmation.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_LEADING_YES` | (see the sections above) | medication_confirmation.py | Implementation detail (matching rule, no clinical threshold) | Matching rule or label; no clinical threshold of its own. |
| `_EASTERN_DIGITS_TABLE` | Unicode translation table for Eastern Arabic (٠-٩) and Urdu (۰-۹) digits | adaptive_interview_agent.py | Implementation detail (numeral normalisation) | Implementation detail for multilingual numeral parsing. |
| `_MMOL_RE` | Regular expression matching mmol/L in English, Roman-Urdu, and Urdu forms | adaptive_interview_agent.py | Implementation detail (unit detection) | Recognises explicit mmol/L units for 18.0 conversion to mg/dL. |

## 7. Medication scope in Connected Mode

In Connected Mode, an EHR patient record may contain dozens of active medication requests (e.g. historical, topical, acute, or unrelated prescriptions). Asking about every single active medication would impose an unacceptable burden on the check-in interview.

`data_sources/medication_scope.py` defines `select_chronic_care_medications(medications, limit=8)` to filter connected records prior to the medication confirmation check.

### Inclusion Rules:
1. Only **ACTIVE** medications are considered (completed, stopped, or cancelled medications are excluded).
2. The normalised medication name must match at least one recognised diabetes or hypertension medication keyword:
   - **Diabetes medications (`DIABETES_MEDICATIONS`):** `metformin`, `glimepiride`, `gliclazide`, `glibenclamide`, `glipizide`, `insulin`, `sitagliptin`, `vildagliptin`, `linagliptin`, `empagliflozin`, `dapagliflozin`, `canagliflozin`, `pioglitazone`, `liraglutide`, `semaglutide`, `dulaglutide`, `acarbose`.
   - **Hypertension medications (`HYPERTENSION_MEDICATIONS`):** `amlodipine`, `nifedipine`, `lisinopril`, `enalapril`, `ramipril`, `perindopril`, `losartan`, `valsartan`, `telmisartan`, `candesartan`, `irbesartan`, `atenolol`, `bisoprolol`, `metoprolol`, `carvedilol`, `propranolol`, `hydrochlorothiazide`, `chlorthalidone`, `indapamide`, `furosemide`, `spironolactone`, `hydralazine`, `methyldopa`, `doxazosin`.
3. Medications are deduplicated by normalised name and sorted with most recently authored first.
4. The total number of medications selected is capped at `DEFAULT_MEDICATION_LIMIT` = `8`.

*Note:* In Isolated Mode, the scope filter is not applied because patients explicitly choose and enter their own medications.

## 8. New rules in v2.3 needing clinician sign-off

> **Empirically verified against live `/api/checkins/{id}/complete` endpoint (Stage 9A-5).**
> A rule exists only if the completed check-in final triage level differs from the all-normal baseline (`routine`, reasons `[]`, factors `[]`).
> Narrative answers to Stage 8b questions (`glucose_context`, `hypo_events_past_week`, `sick_day_flags`, `foot_problems`, `bp_technique`, `associated_symptoms`, `otc_meds_bp`, `missed_doses_reason`, `patient_free_text`) are stored in the intake payload as clinical context for the clinician, but do not alter the completed triage level when blood pressure and glucose readings are in normal range.

| Question Step | Answer Class | Baseline Level | Final Level | Level Differs? | API Reasons | API Factors | Rule Triggered? | Code Location |
|---|---|---|---|---|---|---|---|---|
| `all Stage 8b steps` | `yes` | `routine` | `routine` | NO | `[]` | `[]` | NO (Intake context only) | `adaptive_interview_agent.py` |
| `all Stage 8b steps` | `no` | `routine` | `routine` | NO | `[]` | `[]` | NO (Intake context only) | `adaptive_interview_agent.py` |
| `all Stage 8b steps` | `unknown` | `routine` | `routine` | NO | `[]` | `[]` | NO (Intake context only) | `adaptive_interview_agent.py` |
| `all Stage 8b steps` | `skip` | `routine` | `routine` | NO | `[]` | `[]` | NO (Intake context only) | `adaptive_interview_agent.py` |
| `all Stage 8b steps` | `danger_phrase` | `routine` | `emergency` | YES | `['chest_pain']` (v2) / `['chest_pain', 'red_flag_emergency']` (v3) | `[]` | YES (Stage 1 Red-Flag) | `adaptive_interview_agent.py:194` / `input_triage.py:440` |

### KNOWN GAP FOR CLINICIAN:
Answering "yes" to `hypo_events_past_week`, `sick_day_flags`, `associated_symptoms`, and `foot_problems` leaves the triage level at `routine` when blood pressure and glucose readings are in the normal physiological range. While the patient's narrative answers and affirmative flags are stored in the intake payload (`symptoms` and `lifestyle_notes`) for subsequent clinician review, the automated protocol does not escalate the check-in level beyond `routine`. Consequently, an acute patient who reports a clinically significant symptom (for example, stating *"I have been vomiting and cannot keep fluids down"*) with a normal glucose reading (e.g. 120 mg/dL) will complete the interview classified as `routine` unless an exact verbatim phrase in the Stage 1 emergency red-flag screen catches the text. Clinician sign-off is required to determine whether affirmative responses to these four steps must mandate escalation to `review` or `urgent`.

## 10. Proposed additional danger screen patterns (from interview engine v3 input triage)

> **Proposed, not reviewed by a clinician.**
> In Interview Engine v3, the safety screen authoritatively runs `run_stage1_red_flag_screen` FIRST. The following additional multilingual patterns are added defensively to catch edge-case phrasing across English, Urdu, and Roman Urdu.

| Category | Additional Patterns (English / Roman Urdu / Urdu) | Level Action | Status |
|---|---|---|---|
| Direct Inability Emergencies | `can't breathe`, `cannot breathe`, `can't move`, `can't see`, `cannot see`, `can't keep`, `saans nahi aa rahi`, `bol nahi pa raha`, `ulti ruk nahi rahi`, `paani bhi nahi rukta`, `سانس نہیں آ رہی`, `بول نہیں پا رہا`, `الٹی رک نہیں رہی`, `پانی بھی نہیں رک رہا` | `emergency` | Proposed, not reviewed by a clinician |
| DKA / Severe Vomiting with High Glucose | `vomiting continuously`, `musalsal ultiyan`, `مسلسل الٹیاں`, `مسلسل قے اور الٹی` | `emergency` | Proposed, not reviewed by a clinician |
| Multilingual Chest Pain | `crushing chest pain`, `heavy chest`, `chest pressure`, `pain in my chest` | `emergency` | Proposed, not reviewed by a clinician |
| Urgent Safety / Self-Harm | Explicit self-harm or hopelessness phrases (e.g. `want to end my life`, `zindagi khatam karni hai`) | `emergency` + crisis support guidance + urgent clinician alert | Proposed, not reviewed by a clinician |

## 11. Proposed glucose unit safety rule (from interview engine v3 answer validation)

> **Proposed, not reviewed by a clinician.**
> Clinical Rationale: Under ADA Standards of Care (2026 Section 6), blood glucose values $\le 40$ mg/dL represent severe, life-threatening hypoglycemia requiring urgent intervention. If a patient enters a number $\le 40$ without a unit (e.g. "7" meaning 7.0 mmol/L $\approx$ 126 mg/dL vs 7 mg/dL), assuming either unit without verification creates risk.

- **Disambiguation Question:** If a patient enters a value between $2.0$ and $40.0$ with no unit, the engine asks ONE unit clarification question ("Did you mean X mmol/L or X mg/dL?").
- **Unanswered Unit Safety Fallback:** If the unit question is unanswered, repeated, or unclear, the engine:
  1. Sets the check-in triage level to AT LEAST `review` (so a clinician reviews it today).
  2. Provides immediate low-sugar safety guidance ("If you feel shaky, sweaty, dizzy, or unwell, please consume fast-acting sugar...").
  3. Records a note for the provider: "glucose value unit unclear, possible low".
  4. Continues interview questions (symptom exploration continues to check for neuroglycopenia or autonomic symptoms).
- **Values $> 40$:** Numbers $> 40$ without an explicit unit default to mg/dL (physiologic upper limit for mmol/L is $\approx 33.3$ mmol/L).

## Doctor decisions (Nov 2026)
- D1: Feeling unwell with no reading entered is approved to escalate routine to review (NO_READING_SYMPTOM_RAISE=true).
- D2: High cardiovascular risk escalates routine to review only when accompanied by at least one reported symptom in the check-in; asymptomatic high risk remains routine with risk band documented.
- D3: High diabetes-control risk estimate approved to escalate routine to review once a future model satisfies all pre-registered validation gates.




