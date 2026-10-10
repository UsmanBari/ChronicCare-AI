# Simulated Patient Evaluation Report (Interview Engine v3)

> **STATUS: PROPOSED, NOT REVIEWED BY A CLINICIAN.**
> Generated automatically from hermetic test execution across 52 simulated patient personas.

---

## 1. Executive Summary

| Metric | Measured Value | Standard / Target |
|---|---|---|
| **Total Simulated Personas Tested** | `52` | $\ge 50$ personas |
| **Average Questions Per Check-in** | `7.29` | $\le 10$ normal, $\le 14$ hard cap |
| **Average Slots Captured Per Session** | `7.25` | Comprehensive profile capture |
| **Clarifications & Odd Input Reroutes** | `5` | Handled via fixed response bank |
| **Early Safety / Eligibility Exits** | `5` (4 emergencies, 1 pregnancy) | Immediate safety bypass |
| **LLM Fallback Rate (Stage 9A)** | `100.0% (Templates Default)` | 100% operational with LLM off |

---

## 2. Archetype Breakdown

| Archetype | Persona Count | Avg Questions | Avg Slots Captured |
|---|---|---|---|
| `abuse` | 1 | 7.0 | 7.0 |
| `advice_request` | 1 | 7.0 | 7.0 |
| `anxious_overreporter` | 1 | 13.0 | 13.0 |
| `caregiver` | 1 | 8.0 | 8.0 |
| `caregiver_uncertain` | 1 | 8.0 | 8.0 |
| `changed_answer` | 1 | 8.0 | 8.0 |
| `chitchat` | 1 | 6.0 | 6.0 |
| `confused_units` | 1 | 8.0 | 8.0 |
| `contradiction_record` | 1 | 8.0 | 8.0 |
| `cost_barrier` | 1 | 8.0 | 8.0 |
| `crisis_bp` | 1 | 0.0 | 0.0 |
| `dka_sick_day` | 1 | 0.0 | 0.0 |
| `dont_know` | 1 | 7.0 | 7.0 |
| `dual_normal` | 1 | 10.0 | 9.0 |
| `dyspnea_exertion` | 1 | 8.0 | 8.0 |
| `elderly_complex` | 1 | 0.0 | 0.0 |
| `elderly_slow` | 1 | 8.0 | 8.0 |
| `fasting_broke` | 1 | 8.0 | 8.0 |
| `fasting_low` | 1 | 8.0 | 8.0 |
| `fasting_safe` | 1 | 8.0 | 8.0 |
| `fear_prognosis` | 1 | 7.0 | 7.0 |
| `felt_well_stopped` | 1 | 8.0 | 8.0 |
| `foot_ulcer` | 1 | 7.0 | 7.0 |
| `gibberish` | 1 | 6.0 | 6.0 |
| `hidden_danger` | 1 | 0.0 | 0.0 |
| `htn_headache` | 1 | 8.0 | 8.0 |
| `low_mood` | 1 | 8.0 | 8.0 |
| `minor_mention` | 1 | 7.0 | 7.0 |
| `mixed_language` | 1 | 14.0 | 13.0 |
| `multi_barrier` | 1 | 12.0 | 12.0 |
| `negated_danger` | 1 | 8.0 | 8.0 |
| `no_device` | 2 | 8.0 | 8.0 |
| `orthostatic_dizzy` | 1 | 8.0 | 8.0 |
| `people_pleaser` | 1 | 7.0 | 7.0 |
| `pregnancy_exit` | 1 | 0.0 | 0.0 |
| `prompt_injection` | 1 | 8.0 | 8.0 |
| `rambler` | 1 | 7.0 | 7.0 |
| `refusal` | 1 | 8.0 | 8.0 |
| `roman_urdu` | 1 | 8.0 | 8.0 |
| `roman_urdu_hypo` | 1 | 8.0 | 8.0 |
| `romantic` | 1 | 7.0 | 7.0 |
| `severe_hypo` | 1 | 8.0 | 8.0 |
| `side_effects` | 1 | 8.0 | 8.0 |
| `stoic_minimiser` | 1 | 8.0 | 8.0 |
| `swollen_ankles` | 1 | 8.0 | 8.0 |
| `terse_yes_no` | 1 | 8.0 | 8.0 |
| `urdu_script` | 1 | 7.0 | 7.0 |
| `urdu_script_htn` | 1 | 8.0 | 8.0 |
| `voice_transcript` | 1 | 8.0 | 8.0 |
| `wrong_unit` | 1 | 8.0 | 8.0 |
| `young_stress` | 1 | 8.0 | 8.0 |

---

## 3. Hard Safety Invariants Verified
1. **Danger-Phrase Recall:** `100.0%` recall across 139 positive and negated emergency phrases.
2. **Unknown Retention:** Zero unknown values converted to `False` or dropped.
3. **No Redundant Questioning:** Zero filled slots re-asked without a correction reason.
4. **Strict Budget Cap:** Zero sessions exceeded the 14 questions hard cap.
5. **Deterministic Monotonicity:** Odd inputs never lowered a clinical triage level.
