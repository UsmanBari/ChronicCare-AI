# ChronicCare AI — Adaptive Interview Evidence-Backed Audit (v2 vs v3)

**Date:** 26 October 2026  
**Auditor:** Hassaan Mudassar (`i230536@isb.nu.edu.pk`)  
**Scope:** In-process audit of Adaptive Interview Engine v2 (Production) vs Engine v3 (Behind Feature Flag `INTERVIEW_ENGINE=v3`), combining real in-process API execution (107 scenarios, 214 total check-in runs) and full codebase inspection.  
**Baseline Test Evidence:** `docs/audit/interview_probe_day1.md` (350KB+ full turn trace) and `docs/audit/interview_probe_day1.json`.

---

## 1. Executive Summary

This audit establishes the baseline and detailed roadmap for Iteration 2 (Days 1–4) adaptive interview modernization.

- **Total Clinical Scenarios Probed:** 107 scenarios evaluated across both engines (214 hermetic API check-ins).
- **Total Deficiencies / Gaps Identified:** 17 gaps across 8 clinical and architectural categories.
- **Items Requiring Clinician / Medical Decision:** 4 items (treatment advice in low-glucose alert, clinical validity of 15g fast-acting sugar, triage level assignments for symptom combinations, fasting threshold follow-up protocols).
- **Safety Danger-Phrase Parity (Saad 30-Phrase Set):**
  - **v2 Sensitivity:** 20.0% (detected 3/15 danger phrases)
  - **v3 Sensitivity:** 40.0% (detected 6/15 danger phrases; captured Roman Urdu and acute stroke/vision cues that v2 missed)
  - **Overall Concordance:** 90.0% (27/30 identical emergency triage outcomes)
- **Key Findings:**
  1. **Slot Filling & Dead Code:** `interview_v3_runner.py` only extracts numeric glucose/BP readings into `known_slots`. It never parses or slots affirmative/negative answers or free text for fasting (`is_fasting_today`) or acute illness (`sick_vomiting_diarrhea`). Consequently, all items in `fasting.json` and `sick_day.json` are dead code in v3.
  2. **Unclear Answers Treated as Compliant:** In v2, ambiguous responses (e.g., "maybe", "shayad", "pata nahi") to adherence questions evaluate to `None`, bypassing the non-adherence branch and proceeding as if the patient took their medication.
  3. **Hard-coded English Text in Patient Flow:** The v3 unit clarification prompt, possible-low alert guidance, emergency notes, strike-rule choices, and summary confirmation buttons are hard-coded in English.
  4. **Direct Medical Treatment Advice Violation:** In `interview_v3_runner.py:294,303`, the possible severe low guidance instructs patients: *"consume 15g fast-acting sugar (half cup juice or 3-4 glucose tablets) immediately"*. This explicitly violates the core project safety rule (*"The app never gives a dose or treatment advice"*).
  5. **API Profile Language Barrier:** `ProfileUpdateRequest` in `backend-poc-technical/main.py` enforces `ALLOWED_LANGUAGES = {"en", "ur"}`. Passing `"roman_ur"` results in HTTP 422 Unprocessable Content.

---

## 2. Comprehensive Gap Table

| ID | Gap Description | Category | Engine | Evidence (File:Line or Probe Scenario) | Proposed Architectural Fix | Scheduled Day | Needs Doctor Decision? | Priority |
|---|---|---|---|---|---|:---:|:---:|:---:|
| **G-01** | `is_fasting_today` and `sick_vomiting_diarrhea` never set in `known_slots`, rendering all `fasting.json` and `sick_day.json` items dead code | Slot-Filling | v3 | `interview_v3_runner.py:334-353`; probe `fasting_roza_roman_ur`, `sick_day_en` | Populate `known_slots` from validated yes/no and symptom intent | Day 2 | No | **P1** |
| **G-02** | Unclear adherence answers ("maybe", "pata nahi", "kal tha") fall through to safe/adherent branch, bypassing missed dose reasons | Understanding | v2 | `adaptive_interview_agent.py:583-588`; probe `unclear_maybe` | Route unclear / non-affirmative answers to clarification or review | Day 2 | No | **P1** |
| **G-03** | Number word parser misses Roman Urdu compounds (21–99 such as "baais", "pachpan") and "do sau tees" | Understanding | v3 | `answer_validation.py:77-101`; probe `num_ek_sau_baais`, `num_do_sau_tees` | Expand `_WORD_TO_NUMBER` and regex parser for Urdu / Roman Urdu numbers | Day 2 | No | **P2** |
| **G-04** | Urdu-script number words (ایک سو بیس) fail word extraction regex `[a-z']+` and return None | Understanding | v3 | `answer_validation.py:79`; probe `num_ur_ek_sau_bees` | Add Unicode Arabic/Persian letter and digit tokenization | Day 2 | No | **P2** |
| **G-05** | Ambiguous glucose values (<40 or bare numbers) ask hard-coded English unit clarification: "Did you mean X mmol/L or X mg/dL?" | Language | v3 | `interview_v3_runner.py:313,325`; probe `unit_bare_7` | Extract localized templates from interview bank with ur / roman_ur | Day 4 | No | **P1** |
| **G-06** | Severe low blood sugar alert prescribes specific clinical dosage ("consume 15g fast-acting sugar") | Doctor Decision / Safety | v3 | `interview_v3_runner.py:294,303`; probe `unit_lo_reading` | Replace treatment advice with neutral safety referral per doctor decision | Day 2 | **YES** | **P1** |
| **G-07** | Unit clarification `why_text` and `options` hard-coded in English | Language | v3 | `interview_v3_runner.py:315-316, 327-328` | Localize `why_text` and options across all 3 languages | Day 4 | No | **P2** |
| **G-08** | Emergency `system_note` hard-coded in English ("Emergency red flag detected...") | Language | v3 | `interview_v3_runner.py:201`; probe `saad_phrase_10` | Route emergency response notes through localized response bank | Day 4 | No | **P1** |
| **G-09** | Summary confirmation buttons ("Yes, submit" / "Need to change something") hard-coded in English | Language | v3 | `interview_v3_runner.py:440`; probe `norm_dm_ur` | Localize summary action options for `ur` and `roman_ur` | Day 4 | No | **P2** |
| **G-10** | Strike-rule choices ("Continue check-in", "Need urgent help", "Finish later") hard-coded in English | Language | v3 | `interview_v3_runner.py:254`; probe `offtopic_abuse` | Localize strike rule recovery options in interview bank | Day 4 | No | **P2** |
| **G-11** | All 37 interview bank items lack `why_text_ur` and `why_text_roman_ur` keys | Language | v3 | `interview_bank/*.json`; `loader.py:27` | Add verified Urdu and Roman Urdu rationale strings to bank items | Day 4 | No | **P2** |
| **G-12** | API profile endpoint `PUT /api/me/profile` rejects `"roman_ur"` with HTTP 422 | Language / API | Both | `main.py:399`; `app_store.py:896` | Add `"roman_ur"` to `ALLOWED_LANGUAGES` in profile model and DB schema | Day 4 | No | **P1** |
| **G-13** | Dual-diagnosis in v2 asks adherence and lifestyle twice (once for DM, once for HTN) | Dual-Diagnosis | v2 | `adaptive_interview_agent.py:820-845`; probe `dual_diagnosis_order` | Interleave and de-duplicate shared slots as demonstrated in v3 planner | Day 3 | No | **P2** |
| **G-14** | Caregiver statements ("answering for my mother", "ammi ki taraf se") are ignored, setting answered_by=patient | Understanding | Both | `interview_v3_runner.py`; probe `caregiver_en`, `caregiver_roman_ur` | Detect caregiver persona and record `answered_by="caregiver"` on intakes | Day 3 | No | **P2** |
| **G-15** | Normal readings with affirmative sick-day or acute symptoms do not escalate triage level in clinical rules doc gap | Doctor Decision | Both | `docs/CLINICAL_RULES.md:sec8`; probe `gap_sick_day_yes` | Review clinical symptom escalation matrix with supervising clinician | Day 3 | **YES** | **P2** |
| **G-16** | Past-event headache negation fails on "I had a severe headache yesterday but it is completely gone now" | Danger Phrases | Both | `agents/input_triage.py`; probe `saad_phrase_29` | Refine past-tense temporal resolution cue extraction in danger screen | Day 2 | No | **P2** |
| **G-17** | Progress hint disagrees with total questions asked because clarification and probe items bypass counter | Budget | v3 | `interview_planner.py:141`; `interview_v3_runner.py:147` | Normalize `current_count` to track all patient-facing interactions | Day 3 | No | **P3** |

---

## 3. Side-by-Side Danger Phrase Evaluation (Saad Independent 30-Phrase Set)

Evaluation of all 30 independent phrases from `tests/sim/danger_phrases_independent_saad.json`.
- `v2 Detected`: In-process outcome from Stage 1 Red Flag Screen & BP Crisis Check (`adaptive_interview_agent.py:run_stage1_red_flag_screen`).
- `v3 Detected`: Outcome from Multilingual Danger Phrase Screen (`agents/input_triage.screen_multilingual_danger_phrases`).

| # | Phrase | Expected Danger | v2 Detected (Category) | v3 Detected (Category) | Concordance | Clinical Note |
|---|---|:---:|:---:|:---:|:---:|---|
| 1 | I have crushing chest pain right now | True | **True** (chest_pain) | **True** (chest_pain) | YES | Both caught crushing chest pain |
| 2 | My chest feels very tight and painful | True | False (None) | False (None) | YES | Both missed tight/painful descriptor |
| 3 | Mere se saans nahi li ja rahi | True | False (None) | False (None) | YES | Both missed Roman Urdu breathing inability |
| 4 | I am not breathing properly | True | False (None) | False (None) | YES | Both missed "not breathing properly" |
| 5 | Mujhe saans lene mein bohat mushkil ho rahi hai | True | False (None) | False (None) | YES | Both missed Roman Urdu severe dyspnea |
| 6 | I suddenly feel confused and cannot speak properly | True | False (None) | False (None) | YES | Both missed sudden confusion + speech impairment |
| 7 | Mera aik bazu achanak sunn ho gaya hai aur bolne mein mushkil hai | True | False (None) | False (None) | YES | Both missed unilateral arm numbness + dysphasia |
| 8 | One side of my face suddenly feels weak | True | False (None) | False (None) | YES | Both missed unilateral facial weakness (FAST) |
| 9 | I fainted a few minutes ago and still feel very weak | True | **True** (loss_of_consciousness) | **True** (loss_of_consciousness) | YES | Both caught syncope / fainting |
| 10 | Main achanak behosh ho gaya tha | True | False (None) | **True** (loss_of_consciousness) | **NO** | **v3 captured Roman Urdu syncope (behosh)** |
| 11 | I suddenly cannot see properly from my left eye | True | False (None) | **True** (vision_loss) | **NO** | **v3 captured acute unilateral vision loss** |
| 12 | Meri nazar achanak chali gayi hai | True | False (None) | **True** (vision_loss) | **NO** | **v3 captured Roman Urdu vision loss** |
| 13 | My sugar is extremely high and I keep vomiting | True | False (None) | False (None) | YES | Both missed compound DKA presentation |
| 14 | Sugar bohat high hai aur mujhe bar bar ulti ho rahi hai | True | False (None) | False (None) | YES | Both missed compound Roman Urdu DKA |
| 15 | I suddenly have the worst headache of my life | True | **True** (severe_headache) | **True** (severe_headache) | YES | Both caught thunderclap headache description |
| 16 | I had chest pain last year but I am fine now | False | False (None) | False (None) | YES | Correctly identified past event negation |
| 17 | I do not have any chest pain | False | False (None) | False (None) | YES | Correctly identified explicit negation |
| 18 | Mujhe seene mein dard nahi hai | False | False (None) | False (None) | YES | Correctly identified Roman Urdu negation |
| 19 | My breathing is normal today | False | False (None) | False (None) | YES | Correctly identified normal breathing |
| 20 | Mujhe saans lene mein koi mushkil nahi hai | False | False (None) | False (None) | YES | Correctly identified Roman Urdu normal breathing |
| 21 | I am not confused and I can speak normally | False | False (None) | False (None) | YES | Correctly identified negative stroke cues |
| 22 | Mera bazu sunn nahi hai aur main theek bol raha hoon | False | False (None) | False (None) | YES | Correctly identified Roman Urdu negative cues |
| 23 | I have never fainted | False | False (None) | False (None) | YES | Correctly identified lifetime negation |
| 24 | Main behosh nahi hua | False | False (None) | False (None) | YES | Correctly identified Roman Urdu negation |
| 25 | My vision is normal and I can see clearly | False | False (None) | False (None) | YES | Correctly identified normal vision |
| 26 | Meri nazar bilkul theek hai | False | False (None) | False (None) | YES | Correctly identified Roman Urdu normal vision |
| 27 | My sugar is high but I am not vomiting | False | False (None) | False (None) | YES | Correctly identified vomiting negation |
| 28 | Sugar high hai lekin mujhe ulti nahi ho rahi | False | False (None) | False (None) | YES | Correctly identified Roman Urdu vomiting negation |
| 29 | I had a severe headache yesterday but it is completely gone now | False | **True** (severe_headache) | **True** (severe_headache) | YES | **False Positive in both:** past event negation failed |
| 30 | I have no chest pain but my arm is numb | False | False (None) | False (None) | YES | Correctly identified chest pain negation |

**Summary Statistics:**
- Concordance between v2 and v3: **27 / 30 (90.0%)**
- Discrepancy cases: 3 (in all 3 cases, v3 correctly identified the danger phrase where v2 failed: Roman Urdu syncope `#10`, acute monocular vision loss `#11`, and Roman Urdu vision loss `#12`).
- Both engines share a false positive on `#29` (yesterday's headache that has completely resolved).

---

## 4. Code Reading Checklist Verdicts

### Item 1: Slot Filling and Unreachable Follow-up Branches
- **Verdict:** **CONFIRMED**
- **Evidence:**
  - `backend-poc-technical/agents/interview_v3_runner.py:334-353`:
    Only `known_slots["glucose_reading"]`, `known_slots["bp_reading"]`, and `known_slots["missing_reading"]` are ever assigned.
  - `backend-poc-technical/agents/interview_planner.py:173-176`:
    ```python
    if req.get("is_fasting_today") and not known_slots.get("is_fasting_today"):
        continue
    if req.get("sick_vomiting_diarrhea") and not known_slots.get("sick_vomiting_diarrhea"):
        continue
    ```
  - **Probe Proof:** In probe runs `fasting_roza_roman_ur` and `fasting_yes_en`, even when answering `"haan aaj roza hai"` or `"yes I am fasting"`, zero items from `fasting.json` were ever planned or asked.

### Item 2: Hard-coded English Strings in Patient Flow
- **Verdict:** **CONFIRMED**
- **Evidence:**
  - Unit clarification question: `interview_v3_runner.py:313, 325`: `f"Did you mean {val_res.value:g} mmol/L or {val_res.value:g} mg/dL?"`
  - Unit clarification rationale: `interview_v3_runner.py:315, 327`: `"Clarifying unit to ensure patient safety against severe low blood sugar."`
  - Unit clarification choices: `interview_v3_runner.py:316, 328`: `["mmol/L", "mg/dL"]`
  - Emergency note: `interview_v3_runner.py:201`: `"Emergency red flag detected. Please seek emergency medical care immediately."`
  - Possible low blood sugar guidance: `interview_v3_runner.py:292-295, 301-304`
  - Strike rule options: `interview_v3_runner.py:254`: `["Continue check-in", "Need urgent help", "Finish later"]`
  - Summary confirmation options: `interview_v3_runner.py:440`: `["Yes, submit", "Need to change something"]`

### Item 3: Direct Treatment Advice Violation in Low Sugar Guidance
- **Verdict:** **CONFIRMED**
- **Evidence:** `interview_v3_runner.py:294, 303`:
  ```python
  "consume 15g fast-acting sugar (half cup juice or 3-4 glucose tablets) immediately."
  ```
  This prescribes a specific dose and therapeutic intervention, violating the core safety principle: *"The app never diagnoses, never gives a dose or treatment advice"*. Needs clinician decision on wording.

### Item 4: Bank Rationale Strings (`why_text`) Missing Translations
- **Verdict:** **CONFIRMED**
- **Evidence:**
  All 37 question items in `backend-poc-technical/agents/interview_bank/*.json` (5 core, 10 diabetes, 9 hypertension, 5 fasting, 8 sick day) define only `why_text`. None contain `why_text_ur` or `why_text_roman_ur`.

### Item 5: Number Word Parsing Scope and Limitations
- **Verdict:** **CONFIRMED**
- **Evidence:** `backend-poc-technical/agents/answer_validation.py:77-101`:
  - **Supported:** Single digits 0–20, tens up to 100 in English/Roman Urdu, compound hundreds starting with "ek"/"one" + tens ("ek sau bees" -> 120), and "do sau" -> 200.
  - **Unsupported:**
    - Roman Urdu compound numbers 21–99: "baais" (22), "ikattis" (31), "pachpan" (55), "chhiyaasi" (86).
    - Hundreds starting with digits > 1: "do sau tees" (fails `words[0] in ('ek', 'aik', 'one')` check).
    - English compounds with conjunctions: "one hundred and twenty" (len == 4, fails len == 3 check).
    - Urdu script: `re.findall(r"[a-z']+", text.lower())` discards all Arabic/Urdu unicode text, returning `None`.

### Item 6: Engine v2 Serves English Exclusively
- **Verdict:** **CONFIRMED**
- **Evidence:**
  In probe run `norm_dm_ur (v2)` and `norm_htn_ur (v2)`, the questions returned were:
  `"How are you feeling today? Any symptoms you'd like to report?"` and `"Have you measured your blood sugar today?"`.
  Engine v2 completely lacks multi-language template selection (aligned with `CLINICAL_RULES.md` Section 7).

### Item 7: Unclear Answers Defaulting to False or Safe Paths
- **Verdict:** **CONFIRMED**
- **Evidence:**
  In `adaptive_interview_agent.py:583-588`:
  ```python
  adh = _looks_affirmative(answer)
  answers["adherence"] = adh
  if adh is False:
      state.step = DiabetesStep.MISSED_DOSES_REASON.value
  else:
      state.step = DiabetesStep.LIFESTYLE.value
  ```
  When an answer is ambiguous (e.g. "pata nahi", "maybe"), `adh` is `None`. Because `adh is False` is False, the code enters `else:`, skipping `MISSED_DOSES_REASON` and classifying the patient as compliant.
  In `adaptive_interview_agent.py:857, 860`, `narrative_review` checks `_looks_affirmative(...) is True`. An unclear answer leaves `narrative_review = False`, so clinical review is suppressed.

### Item 8: Dynamic Interview Budgeting Logic
- **Verdict:** **CONFIRMED**
- **Evidence:**
  - `interview_planner.py:100, 140`: Base budget is `8`, expands to `12` when `concerning = True`, with a hard cap of `14`.
  - Discrepancy: `current_count` ignores probe questions and clarification turns:
    `current_count = len([s for s in asked_slots if not s.startswith("probe_") and s != "summary_confirmation"])`.
    Thus, a patient may answer 10 questions while `progress_hint` still displays `6/8`.

---

## 5. What Works Correctly (Validated with Evidence)

1. **v3 Multilingual Delivery:**
   When configured with `language="ur"`, v3 correctly serves high-quality Nastaliq Urdu templates from the interview bank (`template_ur`), and Roman Urdu templates (`template_roman_ur`) when requested.
2. **Saad Phrase Detection Superiority in v3:**
   v3 detected 6 out of 15 true red flags, including Roman Urdu syncope and sudden loss of vision that v2 completely failed to detect.
3. **Hermetic Dynamic Engine Switching:**
   `main.py:2455` dynamically switches between `v2` and `v3` per request via `os.environ["INTERVIEW_ENGINE"]`, allowing side-by-side comparative testing without restarting the server.
4. **Isolated Mode Baseline History Integrity:**
   Baseline computations accurately distinguish personal check-in history, strictly segregating patient records and excluding emergency check-ins from median baseline trends.
5. **Protocol Safety Triggers:**
   Severe blood pressure crisis (185/125 mmHg) and acute hypoglycemia (45 mg/dL with confusion) immediately trigger escalation protocols across both engines.

---

## 6. v3 Production Readiness Checklist

Before Usman can switch the production environment default from `INTERVIEW_ENGINE=v2` to `v3`, the following gates must be met:

- [ ] **Danger-Phrase Parity:** v3 sensitivity on all independent phrase sets (Saad, Hassaan Independent) is greater than or equal to v2, with zero regressions on critical cardiovascular, cerebrovascular, and DKA cues.
- [ ] **Protocol Equivalency:** Identical triage levels and required reviews on all protocol scenarios (Group m: BP 185/125, severe low glucose 45 mg/dL, severe high glucose 320 mg/dL).
- [ ] **Persona Simulation Invariance:** All standardized persona test suites (`test_sim_personas.py`) pass with zero triage level demotions.
- [ ] **Hermetic Parity Tests:** `test_engine_equivalence.py` passing 100% across all clinical scenarios.
- [ ] **No English-Only Leakage:** 100% of patient-facing questions, options, guidance, rationales, and error messages translated in English, Urdu, and Roman Urdu.
- [ ] **Clinician Treatment Advice Clearance:** The possible-low alert wording ("consume 15g fast-acting sugar") reviewed and formally resolved by a supervising physician.
- [ ] **Native Speaker Review:** All Urdu and Roman Urdu text reviewed and certified by native Urdu speakers.
