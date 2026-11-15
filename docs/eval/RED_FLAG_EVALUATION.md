# ChronicCare AI — Red-Flag Safety & Emergency Evaluation Report

**Date:** 15 November 2026 (Updated for Post-Freeze Round 5 Robustness)  
**Scope:** Stage-1 Emergency Triage & Rule-Based Red-Flag Detection  
**Primary Engine:** `backend-poc-technical/agents/red_flag_patterns.py`  
**Yellow Safety Net:** `backend-poc-technical/agents/danger_wordgroups.py` (`acute_unclassified`)  
**Protected Failsafe:** `backend-poc-technical/agents/input_triage.py` (Untouched, Byte-Identical to `origin/dev`)  
**Emergency Routing Protocol:** Deterministic escalation to Emergency Screen (1122 dispatch in Pakistan)  

---

## 1. Executive Summary & Honest Diagnostic Figures

Safety in chronic disease telemonitoring requires that acute life threats (cardiac ischemia, respiratory failure, acute cerebrovascular stroke, sudden hemodynamic collapse, diabetic ketoacidosis) are detected reliably in natural conversation.

However, clinical diagnostic claims must be made with complete scientific transparency:

| Evaluation Dimension | Metric | Benchmark Source | Notes / Interpretation |
| :--- | :---: | :--- | :--- |
| **Developer Regression Test Suite** | **100.0%** (845/845) | Internal regression suites (`test_red_flag_patterns.py`, `test_red_flags_harmless_answers.py`, `test_red_flags_round4.py`, `test_red_flag_r5.py`, etc.) | Unit tests written against known syntactic templates and verified vocabulary lists across English, Urdu script, and Roman Urdu. |
| **Frozen Systematic Held-Out Corpus (R5)** | **76.9%** (538/700) Red Recall<br>**84.4%** (591/700) Safety Net | `tests/fixtures/red_flag_heldout_r5.json` (N=1400: 700 positive, 700 negative, frozen seed=42) | Systematic generator-synthesized corpus. Baseline recall was 74.3% with 19.7% false reds. R5 increased recall to 76.9%, dropped false reds by 46% to 10.6% (74/700), and caught 53 acute near-misses in Yellow Safety Net (84.4% combined safety catch). |
| **Reviewer Independent Hidden Sets** | Round 3: **54.5%** (12/22)<br>Round 4: **50.0%** (5/10) | External hidden test sentences submitted by clinical reviewer prior to Round 3/4/5 | On natural sentences **not written by the developer**, uncalibrated sentence templates missed unusual syntactic structures and synonym variations. |
| **Harmless Check-In Answer False Positives** | **0 / 155** (0.0%) | `test_red_flags_harmless_answers.py` | Ordinary non-emergency check-in answers ("no breathing trouble", "pehle se behtar", "haath sunn jab mobile chalata hoon") correctly stay non-emergency. |
| **Simulated Personas Non-Emergency Utterances** | **0 / 52** (0.0% Red) | `tests/sim/personas.json` (all non-emergency persona utterances) | Zero false-red emergency escalations on ordinary, non-emergency conversation flows. |
| **Single-LLM Baseline Emergency Recall** | **11.1%** (1/9) | Single-LLM baseline (`qwen/qwen3.8-27b` via Groq across 3 trials) | Generalist LLM failed to trigger emergency on 8 of 9 life-threatening presentations (`p22` chest pain, `p35` HTN crisis, `p37` DKA). |
| **Pipeline Overall Emergency Recall** | **100.0%** (3/3) | 51-Persona Benchmark Suite (`p22`, `p35`, `p37`) | Multi-agent deterministic failsafe successfully captured all life-threatening emergencies. Pipeline under-triage 3.9% (2/51), over-triage 7.8% (4/51). |

> [!WARNING]
> **No Unqualified "100% Sensitivity" Claim:**
> In accordance with honest evaluation practices, ChronicCare AI does **NOT** claim 100% sensitivity in the wild. While our 845-case developer regression suite achieves 100% pass rates, evaluation on unseen real-world phrases written by external clinicians demonstrated 50%–70% emergency sensitivity. Real-world deployment requires continuous clinical lexicon updates, localized negator models, and human-in-the-loop safety nets.

---

## 2. Evolution of the Red-Flag Detection Architecture

### 2.1 Round 1 & 2 Limitations: Rigid Sentence Patterns
In early iterations, emergency matching relied heavily on rigid whole-sentence regular expressions. This approach exhibited two critical failure modes:
1. **False Negatives (Over-Specificity):** If a patient expressed an emergency with slightly altered word order, dialectal particles, or unexpected intervening words (e.g., *"mujhe kal se seene mein shadeed dabao mehsoos ho raha hai"* vs *"seene mein dabao"*), the rigid pattern failed to trigger.
2. **False Positives (Over-Generalization on Root Words):** Matching bare symptom roots without negation scope parsing caused ordinary answers to trigger 1122 emergency screens:
   - *"no breathing trouble"* $\rightarrow$ triggered RED `breathing_difficulty`
   - *"haath thoda sunn ho jata hai jab der tak mobile chalata hoon"* $\rightarrow$ triggered RED `stroke_fast`
   - *"seene mein jalan hoti hai tez mirch wala khana kha kar"* $\rightarrow$ triggered RED `chest_pain`

### 2.2 Round 3, 4, and Freeze Improvements: Word Lists & Token Distance Windows
Starting in B3 and finalized in Freeze Parts G1 and G1b, the engine was refactored:
1. **Vocabulary Lists Over Whole Sentences:** Separate semantic lists were created for body/person subjects (including family elders: *nana/nani/dada/dadi/ammi/abba*), anatomical sites, cardiac descriptors, and functional failure verbs (*kaam nahi kar raha/rahi*, *nahi khol rahi*, *hont neelay*, *paani nahi tikta*).
2. **Clause-Bounded Token Windows:** Matches require an anatomical noun and an acute descriptor within a small token distance window ($N \le 8$ words) within the same clause.
3. **Localized Negator Suppression:** A negative frame directly preceding the symptom noun phrase (*"no / not / without / never / koi ... nahi / بغیر / کوئی ... نہیں"*, or *"no \<symptom\> trouble/problem/issue/masla/takleef"*) actively suppresses false emergency hits.
4. **Benign Activity & Posture Exclusions:** Numbness associated with clear posture triggers (*"jab der tak mobile chalata hoon"*, *"sleeping on arm"*) or long-standing chronic neuropathy (*"for years"*) is suppressed from acute FAST stroke. Heartburn triggered by spicy meals (*"tez mirch wala khana"*) without pressure or radiating pain is suppressed from acute cardiac emergency.

### 2.3 Round 5 Post-Freeze Robustness: Architectural Mechanisms Over Ad-Hoc Regexes
Part R5 introduced four general architectural mechanisms to address reviewer-observed drops on novel phrasing:
1. **R5.1 Roman-Urdu & English Spelling Normaliser (`normalize_spelling`):**
   - Collapses repeated vowels in non-English tokens (`saans` $\rightarrow$ `sans`, `seena` $\rightarrow$ `sina`, `dabaav` $\rightarrow$ `dabao`, `panee` $\rightarrow$ `pani`) while protecting legitimate English double-vowel terms (`drooping`, `crooked`, `blood`, `bleed`, `sleep`, `keep`, `feel`).
   - Unifies vowel endings (`-ay`/`-ai` $\rightarrow$ `-e`), consonant variations (`zh` $\rightarrow$ `z`, `qay`/`qae` $\rightarrow$ `kay`), and drops silent `h` after non-aspirated consonants.
   - Maps high-variance Roman Urdu function words and verbs to canonical tokens (`nahi/nai/nahin/nhi` $\rightarrow$ `nahi`; `raha/rha/rahay/rahe/rahi/rahin/rahy` $\rightarrow$ `raha`; `hai/he/hy/hain` $\rightarrow$ `hai`; `mein/me/main/mai` $\rightarrow$ `mein`).
   - Crucially, all vocabulary lists are normalized at module import time (`_normalize_vocab_list`), guaranteeing that pattern definitions never drift from patient input.
2. **R5.2 Synonym / Metaphor Families:**
   - Seven foundational clinical families covering 8+ semantic variants each across English, Urdu script, and Roman Urdu:
     - `chest_pressure` (crushing, elephant on chest, iron bands, pahar, pathar, dabao)
     - `breathing_failure` (gasping, suffocating, drowning, hawa nahi ja rahi, sans ukhad gayi)
     - `face_droop` (drooping mouth, crooked face, one-sided pull, chehra teerha, munh latak gaya)
     - `speech_failure` (slurred speech, words jumbled, awaz ladkhada rahi, bol nahi pa rahe)
     - `limb_failure` (cannot lift arm, leg paralyzed, bazu be-jaan, hath kaam nahi kar raha)
     - `unresponsive` (won't wake up, cannot be roused, hosh nahi, ankh nahi khol rahe)
     - `intractable_vomiting` (can't keep sips down, nonstop vomiting, pani nahi theharta)
   - Proximity matching ($N \le 8$ words) combines family descriptors with expanded family elder subjects (*ammi/abba/baba/nana/nani/dada/dadi/beta/beti/shohar/biwi*).
3. **R5.3 Echo-Question and Short-Answer Negation:**
   - Patients frequently echo the triage prompt before answering (e.g., *"chest pain? no"*, *"saans ki takleef? nahi"*, *"سینے میں درد؟ نہیں"*, *"بازو بے جان؟ بالکل نہیں"*).
   - `is_echo_question_negation()` segments on `?`, `:`, `-`, `,`, or Urdu question marks (`؟` U+061F) and Arabic commas (`،` U+060C) to safely suppress false Red triggers.
   - `is_bare_negative_answer()` guarantees that pure negative utterances (`no`, `nope`, `nahi`, `نہیں`, `bilkul nahi`) can never trigger Stage-1 Red.
4. **R5.4 Yellow Safety Net (`acute_unclassified`):**
   - Implemented in `backend-poc-technical/agents/danger_wordgroups.py`.
   - Near-miss utterances containing an acute severity cue (*achanak, sudden, severe, bohat, nonstop*) plus a critical organ mention (*chest, breathing, face, limb, consciousness, vomiting*), when not explicitly negated, remote past, or benign, raise to Stage-2 Clinician Review (Yellow) via group `acute_unclassified`.
   - Gated by flag `DANGER_SAFETY_NET` (default: `true`, exposed on `/api/admin/config-status`).
   - Verified by architectural mutation proof `M-SN-1` in `scripts/verify_mutations.py`.

---

## 3. Systematic Frozen Corpus Evaluation (R5 Benchmark)

To prevent overfitting to reviewer test sets, an independent systematic held-out corpus generator (`scripts/eval/gen_red_flag_corpus.py`) synthesized 1,400 balanced clinical utterances ($N=700$ emergency positives, $N=700$ non-emergency negatives, seed=42) frozen into `tests/fixtures/red_flag_heldout_r5.json`.

| Metric | Pre-R5 Baseline | Post-R5 Performance | Impact / Delta |
| :--- | :---: | :---: | :--- |
| **Emergency Positive Recall (Stage-1 Red)** | 74.29% (520/700) | **76.86%** (538/700) | +2.57% absolute recall gain |
| **Yellow Safety Net Catches (Stage-2 Review)** | 0.00% (0/700) | **7.57%** (53/700) | +53 near-miss emergencies caught |
| **Combined Clinical Safety Sensitivity** | 74.29% (520/700) | **84.43%** (591/700) | **+10.14%** total safety improvement |
| **False Red Alarms (Non-Emergency Negatives)** | 19.71% (138/700) | **10.57%** (74/700) | **46.4% reduction** in false emergency screens |
| **Clean Non-Emergency Retention (Green)** | 67.29% (471/700) | **77.57%** (543/700) | +10.28% increase in correct green routine triage |

---

## 4. Comprehensive Developer Test Suite Breakdown (845 Tests)

| Test File | Total Tests | Focus Area | Result |
| :--- | :---: | :--- | :---: |
| `backend-poc-technical/test_red_flag_patterns.py` | 185 | Core token-window matching across all 5 red flag categories | **PASS** |
| `backend-poc-technical/test_red_flags_harmless_answers.py` | 155 | Multi-lingual ordinary check-in answers, negations, and benign activity exclusions | **PASS** |
| `backend-poc-technical/test_red_flags_round4.py` | 278 | FAST stroke, cyanosis, fluid failure, and family subject variations | **PASS** |
| `backend-poc-technical/test_q1_red_flags.py` | 65 | Stage-1 emergency prompt guardrail evaluation | **PASS** |
| `backend-poc-technical/test_vomiting_fluids_red_flags.py` | 30 | Dehydration, DKA, and inability to retain fluids (*"paani nahi rukta"*) | **PASS** |
| `backend-poc-technical/test_red_flag_r5.py` | 132 | R5 spelling pairs (45), families (14), echo/negations (41), safety net & M-SN-1 | **PASS** |
| **Total Test Suite** | **845** | **End-to-End Red-Flag Regression Suite** | **100% PASS** |

---

## 5. Primary FYP-1 Clinical Limitation & FYP-2 Prospective Mandate

> [!IMPORTANT]
> **Primary Evaluation Limitation of FYP-1:**
> All quantitative figures reported herein are derived from:
> 1. Synthetic and developer-crafted persona simulation benchmarks ($N=52$).
> 2. Structured adversarial test suites ($N=845$).
> 3. Algorithmic pseudo-natural held-out corpora ($N=1,400$).
> 
> While these suites rigorously exercise linguistic corner-cases, syntactic permutations, and known clinical failure modes, **they do not substitute for prospective clinical validation in an unselected patient cohort.**
> 
> **FYP-2 Mandate:**
> The primary scientific and clinical objective of FYP-2 is the execution of a multi-center prospective validation study conducted in tertiary outpatient diabetic and hypertensive clinics in Pakistan (e.g., Services Hospital Lahore and Jinnah Postgraduate Medical Centre Karachi). Prospective evaluation will measure true real-world sensitivity, patient acceptability of Roman Urdu transcriptions, and clinical adjudication agreement across practicing physicians.

---

## 6. Safety Fail-Safe & Production Boundaries

1. **Protocol 1122 Escalation:** Any positive red-flag trigger immediately halts conversational intake, launches the Emergency Screen, displays 1122 emergency contact options, and alerts the attending clinician.
2. **Zero Protected File Modifications:** All pattern updates were made strictly in `agents/red_flag_patterns.py` and `agents/danger_wordgroups.py`. Core guardrails in `input_triage.py` remain 100% byte-identical to `origin/dev`.
3. **Multi-Lingual Coverage:** Patterns are tested and evaluated natively across English, formal Urdu script, and vernacular Roman Urdu.
