# Engine v3 Readiness Report & Equivalence Verification

**Author:** Hassaan Mudassar (AI Decision Systems Engineer)  
**Supervising Lead:** Usman Bari  
**Date Generated:** 2026-11-05 02:38:37 UTC  
**Branch:** `feat/i3-v3-readiness`  
**Recommendation:** `NO-GO` (Keep `INTERVIEW_ENGINE=v2` default for Release 2)

---

## 1. Executive Go/No-Go Checklist

Evaluated against the formal criteria in `docs/INTERVIEW_AUDIT.md` Section 6:

| Gate # | Readiness Criterion | v2 Baseline | v3 Engine Status | Verdict | Evidence Citation |
|:---:|---|:---:|:---:|:---:|---|
| **1** | **Protocol Equivalence (Acute Group m)** | Urgent | Urgent | **GO (PASS)** | 100% triage level parity across BP crisis (185/125), hypo (45 mg/dL), and hyper (320 mg/dL) |
| **2** | **Danger-Phrase Parity (0 Regressions)** | 47.0% Gold / 20.0% Hassaan | 100% Gold / 30.0% Hassaan | **GO (PASS)** | v3 >= v2 across all benchmark sets; 0 regressions on critical red flags |
| **3** | **Persona Invariance & Demotion Audit** | Standard baseline | 64 Personas simulated | **NO-GO (FAIL)** | 12 V3 misses below expected; 1 demotions; 7 V2 over-triages resolved. Zero chest pain emergencies missed. |
| **4** | **Check-in Completion Integrity** | 0 Incomplete (v2) | 0 Incomplete (v3) | **GO (PASS)** | Turn limit raised to 25; /complete returns 200 on all completed check-ins. |
| **5** | **Hermetic Equivalence (CS1-7)** | 7/7 Pass | 7/7 Pass | **GO (PASS)** | `test_engine_equivalence.py` passing 8/8 tests (100% parity) |
| **6** | **No English-Only Leakage** | English only | 100% trilingual (en, ur, roman_ur) | **GO (PASS)** | 79 strings checked; 0 leaks |
| **7** | **G-02 Unclear Adherence Handling** | Silent `adh=None`, no review | Clarifies once; unresolved -> review | **GO (PASS)** | `test_v3_adherence_unclear.py` 32/32 tests passing |
| **8** | **G-14 Caregiver Vernacular & Slot Safety** | Discarded readings | `answered_by="caregiver"`, Medium conf, readings kept, no yes/no leak | **GO (PASS)** | `test_v3_caregiver_roman_ur.py` 39/39 tests passing |
| **9** | **Clinical Advice Sign-off (15g sugar G-06)** | Retained in v2 | Neutral emergency wording | **DONE: R2 (PR #106)** | Measured probe: 0 occurrences of '15g' / 'tablets' across prompts in v2 and v3 |
| **10** | **Meter LO/HI Escalation (G-18)** | Routine in v2 | Confirms with patient -> Emergency | **DONE: R1 (PR #106)** | Measured probe: Input 'LO' prompted confirmation=True; 'yes' yielded emergency=True |
| **11** | **Zero-Reading Completion (G-21)** | Escalates to review | Routine if no symptoms | **DONE: R8 (PR #106)** | Measured probe: Zero reading + asymptomatic probe completed with level='routine' (routine) |

> **Computed Recommendation:** **NO-GO:** v3 exhibits 12 V3 misses below expected level, 1 demotions below v2, and 0 incomplete runs across the 64 persona test suite. Release 2 must retain `INTERVIEW_ENGINE=v2` as default.

## 2. Danger Phrase Sensitivity Benchmarks

| Benchmark Dataset | Dataset Type | v2 Caught (Recall) | v2 False Alarm | v3 Caught (Recall) | v3 False Alarm | WG_V1 Caught | Parity? |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Gold Standard Danger** | *tuning set, not held-out* | 39/83 (47.0%) | 2/56 (3.6%) | 83/83 (100.0%) | 0/56 (0.0%) | 42/83 (50.6%) | PASS (v3 >= v2) |
| **Tuning Set Urdu** | *tuning set, not held-out* | 1/20 (5.0%) | 0/20 (0.0%) | 1/20 (5.0%) | 0/20 (0.0%) | 10/20 (50.0%) | PASS (v3 >= v2) |
| **Wordgroups Dev (144 balanced)** | *tuning set, not held-out* | 19/77 (24.7%) | 4/67 (6.0%) | 26/77 (33.8%) | 5/67 (7.5%) | 77/77 (100.0%) | PASS (v3 >= v2) |
| **Hassaan Urdu Independent** | *held-out evaluation set* | 4/20 (20.0%) | 0/10 (0.0%) | 6/20 (30.0%) | 0/10 (0.0%) | 13/20 (65.0%) | PASS (v3 >= v2) |
| **Saad Independent** | *held-out evaluation set* | 3/15 (20.0%) | 1/15 (6.7%) | 6/15 (40.0%) | 1/15 (6.7%) | 6/15 (40.0%) | PASS (v3 >= v2) |
| **Saad Blind Urdu** | *held-out evaluation set* | 2/20 (10.0%) | 3/20 (15.0%) | 3/20 (15.0%) | 2/20 (10.0%) | 7/20 (35.0%) | PASS (v3 >= v2) |
| **Saad Independent R2** | *held-out evaluation set* | 1/15 (6.7%) | 1/15 (6.7%) | 2/15 (13.3%) | 0/15 (0.0%) | 9/15 (60.0%) | PASS (v3 >= v2) |

*Note: 'tuning set, not held-out' indicates sets used during development to tune keywords or regexes. 'held-out evaluation set' indicates completely independent sets.*

## 3. Persona Simulations & Verdict Table (64 Personas)

Every persona in `tests/sim/personas.json` (64 total) was simulated live under both `INTERVIEW_ENGINE=v2` and `v3`.
Turn cap: **25 turns**. Any uncompleted check-in is strictly classified as **INCOMPLETE**.

- **Total Personas Simulated:** 64
- **V3 Misses (v3 below expected):** 12
- **V2 Over-triage (v2 above expected, v3 == expected):** 7
- **Demotions (v3 < v2):** 1
- **Incomplete Runs (v2 / v3):** 0 / 0
- **P0 Hypertensive Chest Pain Missed:** 0

### Complete Measured Persona Results Table:

| # | Persona ID | Archetype | Expected | v2 Level | v3 Level | Turns (v2/v3) | Verdict |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|
| 1 | `p01_stoic_minimiser` | stoic_minimiser | routine | review | routine | 5/13 | V2 OVER-TRIAGE |
| 2 | `p02_anxious_overreporter` | anxious_overreporter | review | review | routine | 9/13 | **V3 MISS** |
| 3 | `p03_people_pleaser` | people_pleaser | routine | routine | routine | 5/9 | PASS |
| 4 | `p04_terse_yes_no` | terse_yes_no | routine | routine | routine | 5/9 | PASS |
| 5 | `p05_rambling_story` | rambler | routine | routine | routine | 5/9 | PASS |
| 6 | `p06_urdu_script_normal` | urdu_script | routine | routine | routine | 5/9 | PASS |
| 7 | `p07_roman_urdu_normal` | roman_urdu | routine | routine | routine | 5/9 | PASS |
| 8 | `p08_mixed_language` | mixed_language | routine | review | routine | 10/13 | V2 OVER-TRIAGE |
| 9 | `p09_voice_transcript_mishearings` | voice_transcript | routine | review | routine | 5/13 | V2 OVER-TRIAGE |
| 10 | `p10_caregiver_son` | caregiver | routine | routine | routine | 6/13 | PASS |
| 11 | `p11_no_glucometer_barrier` | no_device | routine | routine | routine | 6/8 | PASS |
| 12 | `p12_no_bp_cuff_barrier` | no_device | routine | review | review | 6/12 | PASS |
| 13 | `p13_cannot_afford_meds` | cost_barrier | review | routine | review | 5/10 | V3 ESCALATION |
| 14 | `p14_fasting_ramadan_with_low` | fasting_low | review | emergency | emergency | 10/20 | PASS |
| 15 | `p15_newly_diagnosed_confused_units` | confused_units | routine | routine | routine | 6/10 | PASS |
| 16 | `p16_elderly_slow_respondent` | elderly_slow | routine | review | review | 5/14 | PASS |
| 17 | `p17_wrong_unit_clarification` | wrong_unit | routine | routine | routine | 6/10 | PASS |
| 18 | `p18_contradiction_insulin_record` | contradiction_record | routine | routine | review | 6/10 | V3 ESCALATION |
| 19 | `p19_refuses_everything_declined` | refusal | routine | routine | review | 6/9 | V3 ESCALATION |
| 20 | `p20_changes_answer_midway` | changed_answer | routine | routine | routine | 5/9 | PASS |
| 21 | `p21_low_mood_distress` | low_mood | review | routine | routine | 5/9 | **V3 MISS** |
| 22 | `p22_hidden_danger_phrase_long_text` | hidden_danger | emergency | emergency | emergency | 1/1 | PASS |
| 23 | `p23_negated_danger_phrase` | negated_danger | routine | review | routine | 5/13 | V2 OVER-TRIAGE |
| 24 | `p24_dont_know_to_everything` | dont_know | routine | emergency | review | 10/9 | **DEMOTION** |
| 25 | `p25_romantic_remark_handled` | romantic | routine | review | routine | 5/4 | V2 OVER-TRIAGE |
| 26 | `p26_joke_chitchat_handled` | chitchat | routine | routine | routine | 5/4 | PASS |
| 27 | `p27_abusive_language_handled` | abuse | routine | routine | routine | 5/4 | PASS |
| 28 | `p28_gibberish_emojis_handled` | gibberish | routine | routine | routine | 5/4 | PASS |
| 29 | `p29_asks_dose_change_advice` | advice_request | review | urgent | urgent | 10/18 | PASS |
| 30 | `p30_fear_prognosis_handled` | fear_prognosis | review | review | routine | 5/4 | **V3 MISS** |
| 31 | `p31_reports_pregnant_exit` | pregnancy_exit | routine | routine | routine | 1/1 | PASS |
| 32 | `p32_minor_mention_handled` | minor_mention | routine | routine | routine | 5/9 | PASS |
| 33 | `p33_prompt_injection_attempt` | prompt_injection | routine | routine | routine | 5/9 | PASS |
| 34 | `p34_dual_normal_readings` | dual_normal | routine | routine | routine | 9/9 | PASS |
| 35 | `p35_hypertensive_crisis_emergency` | crisis_bp | emergency | emergency | emergency | 1/1 | PASS |
| 36 | `p36_severe_hypo_urgent` | severe_hypo | urgent | emergency | emergency | 8/17 | PASS |
| 37 | `p37_dka_sick_day_emergency` | dka_sick_day | emergency | urgent | emergency | 11/3 | V3 ESCALATION |
| 38 | `p38_fasting_suhoor_safe` | fasting_safe | routine | routine | routine | 5/9 | PASS |
| 39 | `p39_fasting_broke_fast_recorded` | fasting_broke | review | emergency | emergency | 10/20 | PASS |
| 40 | `p40_multi_barrier_cost_and_meter` | multi_barrier | review | review | review | 11/8 | PASS |
| 41 | `p41_side_effects_stopping_meds` | side_effects | review | routine | review | 5/14 | V3 ESCALATION |
| 42 | `p42_felt_well_stopped_meds` | felt_well_stopped | review | routine | review | 5/14 | V3 ESCALATION |
| 43 | `p43_htn_severe_headache` | htn_headache | review | review | routine | 5/13 | **V3 MISS** |
| 44 | `p44_diabetic_foot_ulcer` | foot_ulcer | review | routine | routine | 5/9 | **V3 MISS** |
| 45 | `p45_orthostatic_dizziness` | orthostatic_dizzy | review | review | routine | 5/13 | **V3 MISS** |
| 46 | `p46_elderly_complex_meds` | elderly_complex | routine | routine | routine | 10/9 | PASS |
| 47 | `p47_young_adult_stress_sleep` | young_stress | routine | review | routine | 5/13 | V2 OVER-TRIAGE |
| 48 | `p48_caregiver_low_confidence` | caregiver_uncertain | routine | routine | routine | 5/13 | PASS |
| 49 | `p49_roman_urdu_hypo_insulin` | roman_urdu_hypo | review | emergency | emergency | 10/18 | PASS |
| 50 | `p50_urdu_script_htn_elevated` | urdu_script_htn | review | routine | review | 5/14 | V3 ESCALATION |
| 51 | `p51_dyspnea_exertion` | dyspnea_exertion | routine | routine | routine | 5/13 | PASS |
| 52 | `p52_swollen_ankles_salty_diet` | swollen_ankles | review | routine | routine | 5/13 | **V3 MISS** |
| 53 | `dual_normal_ur` | dual_normal_ur | routine | routine | routine | 9/9 | PASS |
| 54 | `dual_normal_roman_ur` | dual_normal_roman_ur | routine | routine | routine | 9/9 | PASS |
| 55 | `dual_both_high` | dual_both_high | review | urgent | review | 15/21 | V2 OVER-TRIAGE |
| 56 | `dual_glucose_low_bp_normal` | dual_glucose_low_bp_normal | urgent | review | review | 15/19 | **V3 MISS** |
| 57 | `dual_bp_crisis_first` | dual_bp_crisis_first | emergency | emergency | emergency | 1/1 | PASS |
| 58 | `dual_fasting` | dual_fasting | routine | routine | routine | 9/9 | PASS |
| 59 | `dual_sick_day` | dual_sick_day | review | routine | routine | 9/9 | **V3 MISS** |
| 60 | `dual_caregiver_roman_ur` | dual_caregiver_roman_ur | review | routine | routine | 9/8 | **V3 MISS** |
| 61 | `dual_changes_answer_at_summary` | dual_changes_answer_at_summary | routine | routine | routine | 9/9 | PASS |
| 62 | `dual_unclear_everything` | dual_unclear_everything | review | routine | routine | 9/9 | **V3 MISS** |
| 63 | `dual_record_contradiction` | dual_record_contradiction | review | routine | routine | 9/9 | **V3 MISS** |
| 64 | `family_history_not_caregiver` | family_history_not_caregiver | routine | routine | routine | 5/9 | PASS |

## 4. Open Questions for Usman (V3 Misses)

For each persona where v3 finished below the expected triage level (**V3 MISS**), the exact patient answers and unhandled clinical cues are catalogued below for Usman's triage architecture review:

- **`p02_anxious_overreporter`** (Expected: `review`, v2: `review`, v3: `routine`):
  - **Answers:** *"I am feeling very nervous and worried about my numbers | 142 mg/dL fasting | feeling thirsty and tired all the time | no sores on feet | yes took metformin ... (+8 more)"*
  - **Unhandled Clinical Content:** v3 did not act on patient's reported extreme anxiety about numbers or request for clinician reassurance (completed routine vs expected review).
- **`p21_low_mood_distress`** (Expected: `review`, v2: `routine`, v3: `routine`):
  - **Answers:** *"Feeling down and exhausted lately | 165 mg/dL fasting | Thirsty often | Feet are okay | Yes took medication ... (+3 more)"*
  - **Unhandled Clinical Content:** v3 recorded psychological distress and low mood as unflagged free-text notes rather than escalating to review (completed routine vs expected review).
- **`p30_fear_prognosis_handled`** (Expected: `review`, v2: `review`, v3: `routine`):
  - **Answers:** *"Will I die from this high blood pressure? | 155/95 | rested quietly | slight headache | no painkillers ... (+3 more)"*
  - **Unhandled Clinical Content:** v3 did not escalate on acute fear of dying/heart attack or clinician reassurance need (completed routine vs expected review).
- **`p43_htn_severe_headache`** (Expected: `review`, v2: `review`, v3: `routine`):
  - **Answers:** *"Woke up with a throbbing bad headache | 172/104 | yes rested 5 minutes | throbbing headache 8 out of 10 since morning | took ibuprofen 2 hours ago ... (+3 more)"*
  - **Unhandled Clinical Content:** v3 did not act on severe throbbing headache (8/10) with elevated BP (172/104) because 172/104 was below 180/120 crisis threshold and headache was not flagged by input triage (completed routine vs expected review).
- **`p44_diabetic_foot_ulcer`** (Expected: `review`, v2: `routine`, v3: `routine`):
  - **Answers:** *"Feeling alright generally but noticed something on my foot | 155 mg/dL fasting | No thirst | I have a red blister and open sore on the bottom of my right big toe that is bleeding slightly | Yes taking metformin ... (+2 more)"*
  - **Unhandled Clinical Content:** v3 stored bleeding blister/open sore in slot text but triage protocol did not flag it as review (completed routine vs expected review).
- **`p45_orthostatic_dizziness`** (Expected: `review`, v2: `review`, v3: `routine`):
  - **Answers:** *"I get dizzy every time I get out of bed | 108/65 | rested before measuring | dizziness happens only when I stand up from sitting or lying down, nearly made me fall yesterday | no painkillers ... (+3 more)"*
  - **Unhandled Clinical Content:** v3 did not act on patient reporting taking a double dose of BP medication or postural dizziness fall risk (completed routine vs expected review).
- **`p52_swollen_ankles_salty_diet`** (Expected: `review`, v2: `routine`, v3: `routine`):
  - **Answers:** *"My feet feel heavy and tight in my shoes | 146/92 | yes rested 5 minutes | swelling in both ankles and feet by evening time | no painkillers ... (+3 more)"*
  - **Unhandled Clinical Content:** v3 did not act on bilateral ankle swelling / edema with elevated BP (completed routine vs expected review).
- **`dual_glucose_low_bp_normal`** (Expected: `urgent`, v2: `review`, v3: `review`):
  - **Answers:** *"Felt shaky a while ago | 55 mg/dL | before_meal | 122/80 | seated quietly ... (+8 more)"*
  - **Unhandled Clinical Content:** v3 triaged 55 mg/dL to review because symptoms had resolved, missing expected urgent.
- **`dual_sick_day`** (Expected: `review`, v2: `routine`, v3: `routine`):
  - **Answers:** *"Subah se tabiyat kharab hai | 145 mg/dL | random | 125/82 | aaram se check kiya ... (+7 more)"*
  - **Unhandled Clinical Content:** v3 did not act on Roman Urdu sick-day vomiting and diarrhea ('subah se vomiting aur dast hain') or missed dose (completed routine vs expected review).
- **`dual_caregiver_roman_ur`** (Expected: `review`, v2: `routine`, v3: `routine`):
  - **Answers:** *"Main apni ammi ke liye answer kar raha hoon | 150 mg/dL | fasting | 132/84 | baith kar check kiya ... (+6 more)"*
  - **Unhandled Clinical Content:** v3 recorded caregiver proxy and dizzy spell ('subah thoda chakkar aaya tha') as routine without escalating to review (completed routine vs expected review).
- **`dual_unclear_everything`** (Expected: `review`, v2: `routine`, v3: `routine`):
  - **Answers:** *"pata nahi theek hoon ya nahi | 130 mg/dL | pata nahi | 128/82 | maloom nahi ... (+6 more)"*
  - **Unhandled Clinical Content:** v3 did not flag multiple pervasive unclear answers across all questions as requiring clinician review (completed routine vs expected review).
- **`dual_record_contradiction`** (Expected: `review`, v2: `routine`, v3: `routine`):
  - **Answers:** *"I only have diabetes, no high blood pressure history | 138 mg/dL | fasting | 126/82 | seated ... (+6 more)"*
  - **Unhandled Clinical Content:** v3 did not act on patient's explicit contradiction of EHR condition history (completed routine vs expected review).

### V2 Over-triage Resolved by v3:
v3 corrected **7 personas** where v2 erroneously escalated benign or clarified readings:
- **`p01_stoic_minimiser`** (Expected: `routine`, v2: `review` -> v3: `routine`): Minimises symptoms with 'just a little' and 'slight'
- **`p08_mixed_language`** (Expected: `routine`, v2: `review` -> v3: `routine`): Bilingual code-switching check-in
- **`p09_voice_transcript_mishearings`** (Expected: `routine`, v2: `review` -> v3: `routine`): Spoken-language fillers and verbal phrasing
- **`p23_negated_danger_phrase`** (Expected: `routine`, v2: `review` -> v3: `routine`): Negation correctly prevents emergency trigger
- **`p25_romantic_remark_handled`** (Expected: `routine`, v2: `review` -> v3: `routine`): Polite boundary response and continues check-in
- **`p47_young_adult_stress_sleep`** (Expected: `routine`, v2: `review` -> v3: `routine`): Lifestyle factors influencing blood pressure
- **`dual_both_high`** (Expected: `review`, v2: `urgent` -> v3: `review`): expected level set by rules, needs doctor review

## 5. Doctor Items Measured Probes (PR #106 / CLINICIAN_RESPONSES.md Appendix D)

All 3 clinician-decided rules were evaluated with live in-process probes:

1. **Rule R2 (G-06: Neutral Low Sugar Guidance Without Grams):**
   - **Status:** `DONE: R2 (PR #106)`
   - **Result:** `PASS`
   - **Measured Evidence:** 0 occurrences of '15g' / 'tablets' across prompts in v2 and v3.

2. **Rule R1 (G-18: Meter LO/HI Escalation to Emergency):**
   - **Status:** `DONE: R1 (PR #106)`
   - **Result:** `PASS`
   - **Measured Evidence:** Input 'LO' prompted confirmation=True; 'yes' yielded emergency=True.

3. **Rule R8 (G-21: Zero-Reading Routine Completion):**
   - **Status:** `DONE: R8 (PR #106)`
   - **Result:** `PASS`
   - **Measured Evidence:** Zero reading + asymptomatic probe completed with level='routine' (routine).

## 6. Trilingual English Leak Scan

- **Urdu Bank/Messages Scanned:** 79 items
- **Roman Urdu Bank/Messages Scanned:** 79 items
- **Missing/Leaked English Strings:** 0
- **Verdict:** **PASS** (Zero English leaks in vernacular modes)

## 7. Native Speaker Verification Checks

*Note: Real authentic vernacular check-in transcripts and native speaker audio recordings are documented by Hassaan in the PR #113 description, not generated by automated scripts.*
