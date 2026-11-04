# v3 Production Readiness Evaluation & Go/No-Go Decision Report

**Date:** Thursday 5 Nov 2026  
**Author:** Hassaan Mudassar (AI & Backend Lead)  
**Target Branch:** `feat/i3-v3-readiness`  
**Persona Count:** 64 standardized personas evaluated live across both engines.  
**Computed Decision:** **NO-GO**  

## 1. Executive Go/No-Go Readiness Checklist

Evaluated against the formal criteria in `docs/INTERVIEW_AUDIT.md` Section 6:

| Gate # | Readiness Criterion | v2 Baseline | v3 Engine Status | Verdict | Evidence Citation |
|:---:|---|:---:|:---:|:---:|---|
| **1** | **Protocol Equivalence (Acute Group m)** | Urgent | Urgent | **GO (PASS)** | 100% triage level parity across BP crisis (185/125), hypo (45 mg/dL), and hyper (320 mg/dL) |
| **2** | **Danger-Phrase Parity (0 Regressions)** | 47.0% Gold / 20.0% Hassaan | 100% Gold / 30.0% Hassaan | **GO (PASS)** | v3 >= v2 across all benchmark sets; 0 regressions on critical red flags |
| **3** | **Persona Invariance & Demotion Audit** | Standard baseline | 64 Personas simulated | **NO-GO (FAIL)** | 18 demotions measured (v3 < v2). Zero chest pain emergencies missed. |
| **4** | **Hermetic Equivalence (CS1-7)** | 7/7 Pass | 7/7 Pass | **GO (PASS)** | `test_engine_equivalence.py` passing 8/8 tests (100% parity) |
| **5** | **No English-Only Leakage** | English only | 100% trilingual (en, ur, roman_ur) | **GO (PASS)** | 79 strings checked; 0 leaks |
| **6** | **G-02 Unclear Adherence Handling** | Silent `adh=None`, no review | Clarifies once; unresolved -> review | **GO (PASS)** | `test_v3_adherence_unclear.py` 32/32 tests passing |
| **7** | **G-14 Caregiver Urdu Vernacular** | Discarded readings | `answered_by="caregiver"`, Medium conf, readings kept | **GO (PASS)** | `test_v3_caregiver_roman_ur.py` 36/36 tests passing |
| **8** | **Clinical Advice Sign-off (15g sugar G-06)** | Retained in v2 | Neutral emergency wording | **DONE: R2 (PR #106)** | Measured probe: 15g and dosage numbers strictly absent across all templates and message files in both engines |
| **9** | **Meter LO/HI Escalation (G-18)** | Routine in v2 | Confirms with patient -> Emergency | **DONE: R1 (PR #106)** | Measured probe: LO input triggers meter confirmation (conf_asked=True) -> 'yes' triggers Emergency (emergency=True) |
| **10** | **Zero-Reading Completion (G-21)** | Escalates to review | Routine if no symptoms | **DONE: R8 (PR #106)** | Measured probe: 0 readings + 0 symptoms checkin completed with level='routine' (routine achieved) |

> **Computed Recommendation:** **NO-GO (FAIL):** 18 of 64 personas experienced clinical triage demotions under v3 relative to v2 (v3 < v2). In medical decision-support prototypes, 'the model proposes, the rules decide' requires that a new engine never lowers a triage level below existing safety behavior. v3 cannot become the default interview engine until Usman reviews each demotion and confirms whether v2 over-triage should be preserved or adjusted in the safety protocol.

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

## 3. Persona Simulations & Demotion Audit (64 Personas)

Every persona in `tests/sim/personas.json` (64 total) was simulated live under both `INTERVIEW_ENGINE=v2` and `v3`.
Level hierarchy: **emergency (3) > urgent (2) > review (1) > routine (0)**. A demotion is strictly when **v3 < v2**.

- **Total Personas Simulated:** 64
- **Total Clinical Demotions (v3 < v2):** 18
- **P0 Hypertensive Chest Pain Missed:** 0

### Case-by-Case Breakdown of Measured Demotions:

| Persona ID | Persona Name | Expected | v2 Level | v3 Level | Clinical Explanation |
|---|---|:---:|:---:|:---:|---|
| `p01_stoic_minimiser` | Stoic Minimiser | routine | **review** | **routine** | Minimises symptoms with 'just a little' and 'slight' |
| `p02_anxious_overreporter` | Anxious Over-Reporter | review | **review** | **routine** | Reports multiple symptoms with anxiety |
| `p08_mixed_language` | Mixed English and Urdu | routine | **review** | **routine** | Bilingual code-switching check-in |
| `p09_voice_transcript_mishearings` | Voice Transcript with Fillers | routine | **review** | **routine** | Spoken-language fillers and verbal phrasing |
| `p14_fasting_ramadan_with_low` | Fasting Patient with Hypoglycemia | review | **emergency** | **routine** | Fasting low blood sugar episode requiring fast breaking |
| `p15_newly_diagnosed_confused_units` | Newly Diagnosed Confused About Units | routine | **emergency** | **routine** | Typed 7.2 and disambiguated unit to mmol/L |
| `p17_wrong_unit_clarification` | Glucose Number Ambiguity Prompt | routine | **emergency** | **routine** | Prompts unit clarification for 6.5 |
| `p23_negated_danger_phrase` | Negated Danger Phrase | routine | **review** | **routine** | Negation correctly prevents emergency trigger |
| `p24_dont_know_to_everything` | Don't Know to All Questions | routine | **emergency** | **review** | Handles 'I don't know' without crash or marking unknown as 'no' |
| `p25_romantic_remark_handled` | Romantic Remark | routine | **review** | **routine** | Polite boundary response and continues check-in |
| `p30_fear_prognosis_handled` | Fear of Mortality | review | **review** | **routine** | Caring message + flagged for clinician reassurance |
| `p36_severe_hypo_urgent` | Acute Severe Hypoglycemia | urgent | **emergency** | **urgent** | Glucose < 54 mg/dL triggers urgent clinical review |
| `p39_fasting_broke_fast_recorded` | Fasting Broke Fast for Low Sugar | review | **emergency** | **routine** | Broke fast safely due to hypoglycemia |
| `p43_htn_severe_headache` | Hypertension with Severe Headache | review | **review** | **routine** | Elevated BP with severe headache and NSAID usage |
| `p45_orthostatic_dizziness` | Orthostatic Postural Dizziness | review | **review** | **routine** | Postural hypotension / overmedication fall risk |
| `p47_young_adult_stress_sleep` | Young Adult Stress and Poor Sleep | routine | **review** | **routine** | Lifestyle factors influencing blood pressure |
| `p49_roman_urdu_hypo_insulin` | Roman Urdu Hypoglycemia on Insulin | review | **emergency** | **review** | Roman Urdu recurrent hypoglycemia report |
| `dual_both_high` | Dual Both High | review | **urgent** | **review** | expected level set by rules, needs doctor review |

### Complete Measured Persona Results Table:

| # | Persona ID | Archetype | Expected | v2 Level | v3 Level | Demotion? |
|:---:|---|---|:---:|:---:|:---:|:---:|
| 1 | `p01_stoic_minimiser` | stoic_minimiser | routine | review | routine | **DEMOTION** |
| 2 | `p02_anxious_overreporter` | anxious_overreporter | review | review | routine | **DEMOTION** |
| 3 | `p03_people_pleaser` | people_pleaser | routine | routine | routine | No |
| 4 | `p04_terse_yes_no` | terse_yes_no | routine | routine | routine | No |
| 5 | `p05_rambling_story` | rambler | routine | routine | routine | No |
| 6 | `p06_urdu_script_normal` | urdu_script | routine | routine | routine | No |
| 7 | `p07_roman_urdu_normal` | roman_urdu | routine | routine | review | No |
| 8 | `p08_mixed_language` | mixed_language | routine | review | routine | **DEMOTION** |
| 9 | `p09_voice_transcript_mishearings` | voice_transcript | routine | review | routine | **DEMOTION** |
| 10 | `p10_caregiver_son` | caregiver | routine | routine | routine | No |
| 11 | `p11_no_glucometer_barrier` | no_device | routine | routine | routine | No |
| 12 | `p12_no_bp_cuff_barrier` | no_device | routine | review | review | No |
| 13 | `p13_cannot_afford_meds` | cost_barrier | review | routine | routine | No |
| 14 | `p14_fasting_ramadan_with_low` | fasting_low | review | emergency | routine | **DEMOTION** |
| 15 | `p15_newly_diagnosed_confused_units` | confused_units | routine | emergency | routine | **DEMOTION** |
| 16 | `p16_elderly_slow_respondent` | elderly_slow | routine | review | review | No |
| 17 | `p17_wrong_unit_clarification` | wrong_unit | routine | emergency | routine | **DEMOTION** |
| 18 | `p18_contradiction_insulin_record` | contradiction_record | routine | routine | review | No |
| 19 | `p19_refuses_everything_declined` | refusal | routine | routine | review | No |
| 20 | `p20_changes_answer_midway` | changed_answer | routine | routine | review | No |
| 21 | `p21_low_mood_distress` | low_mood | review | routine | routine | No |
| 22 | `p22_hidden_danger_phrase_long_text` | hidden_danger | emergency | emergency | emergency | No |
| 23 | `p23_negated_danger_phrase` | negated_danger | routine | review | routine | **DEMOTION** |
| 24 | `p24_dont_know_to_everything` | dont_know | routine | emergency | review | **DEMOTION** |
| 25 | `p25_romantic_remark_handled` | romantic | routine | review | routine | **DEMOTION** |
| 26 | `p26_joke_chitchat_handled` | chitchat | routine | routine | routine | No |
| 27 | `p27_abusive_language_handled` | abuse | routine | routine | routine | No |
| 28 | `p28_gibberish_emojis_handled` | gibberish | routine | routine | routine | No |
| 29 | `p29_asks_dose_change_advice` | advice_request | review | urgent | urgent | No |
| 30 | `p30_fear_prognosis_handled` | fear_prognosis | review | review | routine | **DEMOTION** |
| 31 | `p31_reports_pregnant_exit` | pregnancy_exit | routine | routine | routine | No |
| 32 | `p32_minor_mention_handled` | minor_mention | routine | routine | routine | No |
| 33 | `p33_prompt_injection_attempt` | prompt_injection | routine | routine | routine | No |
| 34 | `p34_dual_normal_readings` | dual_normal | routine | routine | routine | No |
| 35 | `p35_hypertensive_crisis_emergency` | crisis_bp | emergency | emergency | emergency | No |
| 36 | `p36_severe_hypo_urgent` | severe_hypo | urgent | emergency | urgent | **DEMOTION** |
| 37 | `p37_dka_sick_day_emergency` | dka_sick_day | emergency | urgent | emergency | No |
| 38 | `p38_fasting_suhoor_safe` | fasting_safe | routine | routine | review | No |
| 39 | `p39_fasting_broke_fast_recorded` | fasting_broke | review | emergency | routine | **DEMOTION** |
| 40 | `p40_multi_barrier_cost_and_meter` | multi_barrier | review | review | review | No |
| 41 | `p41_side_effects_stopping_meds` | side_effects | review | routine | review | No |
| 42 | `p42_felt_well_stopped_meds` | felt_well_stopped | review | routine | review | No |
| 43 | `p43_htn_severe_headache` | htn_headache | review | review | routine | **DEMOTION** |
| 44 | `p44_diabetic_foot_ulcer` | foot_ulcer | review | routine | routine | No |
| 45 | `p45_orthostatic_dizziness` | orthostatic_dizzy | review | review | routine | **DEMOTION** |
| 46 | `p46_elderly_complex_meds` | elderly_complex | routine | routine | routine | No |
| 47 | `p47_young_adult_stress_sleep` | young_stress | routine | review | routine | **DEMOTION** |
| 48 | `p48_caregiver_low_confidence` | caregiver_uncertain | routine | routine | routine | No |
| 49 | `p49_roman_urdu_hypo_insulin` | roman_urdu_hypo | review | emergency | review | **DEMOTION** |
| 50 | `p50_urdu_script_htn_elevated` | urdu_script_htn | review | routine | review | No |
| 51 | `p51_dyspnea_exertion` | dyspnea_exertion | routine | routine | routine | No |
| 52 | `p52_swollen_ankles_salty_diet` | swollen_ankles | review | routine | routine | No |
| 53 | `dual_normal_ur` | dual_normal_ur | routine | routine | routine | No |
| 54 | `dual_normal_roman_ur` | dual_normal_roman_ur | routine | routine | review | No |
| 55 | `dual_both_high` | dual_both_high | review | urgent | review | **DEMOTION** |
| 56 | `dual_glucose_low_bp_normal` | dual_glucose_low_bp_normal | urgent | review | review | No |
| 57 | `dual_bp_crisis_first` | dual_bp_crisis_first | emergency | emergency | emergency | No |
| 58 | `dual_fasting` | dual_fasting | routine | routine | routine | No |
| 59 | `dual_sick_day` | dual_sick_day | review | routine | review | No |
| 60 | `dual_caregiver_roman_ur` | dual_caregiver_roman_ur | review | routine | review | No |
| 61 | `dual_changes_answer_at_summary` | dual_changes_answer_at_summary | routine | routine | routine | No |
| 62 | `dual_unclear_everything` | dual_unclear_everything | review | routine | review | No |
| 63 | `dual_record_contradiction` | dual_record_contradiction | review | routine | routine | No |
| 64 | `family_history_not_caregiver` | family_history_not_caregiver | routine | routine | review | No |

## 4. Doctor Items Measured Probes (PR #106 / CLINICIAN_RESPONSES.md Appendix D)

All 3 clinician-decided rules were evaluated with live in-process probes:

1. **Rule R2 (G-06: Neutral Low Sugar Guidance Without Grams):**
   - **Status:** `DONE: R2 (PR #106)`
   - **Result:** `PASS`
   - **Measured Evidence:** 15g and dosage numbers strictly absent across all templates and message files in both engines.

2. **Rule R1 (G-18: Meter LO/HI Escalation to Emergency):**
   - **Status:** `DONE: R1 (PR #106)`
   - **Result:** `PASS`
   - **Measured Evidence:** LO input triggers meter confirmation (conf_asked=True) -> 'yes' triggers Emergency (emergency=True).

3. **Rule R8 (G-21: Zero-Reading Routine Completion):**
   - **Status:** `DONE: R8 (PR #106)`
   - **Result:** `PASS`
   - **Measured Evidence:** 0 readings + 0 symptoms checkin completed with level='routine' (routine achieved).

## 5. Trilingual English Leak Scan

- **Urdu Bank/Messages Scanned:** 79 items
- **Roman Urdu Bank/Messages Scanned:** 79 items
- **Missing/Leaked English Strings:** 0
- **Verdict:** **PASS** (Zero English leaks in vernacular modes)

## 6. Native Speaker Verification Checks

*Note: Real authentic vernacular check-in transcripts and native speaker audio recordings are documented by Hassaan in the PR #113 description, not generated by automated scripts.*
