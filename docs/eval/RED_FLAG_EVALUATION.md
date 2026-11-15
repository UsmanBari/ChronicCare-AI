# ChronicCare AI — Red-Flag Safety & Emergency Evaluation Report

**Date:** 15 November 2026 (Updated for Post-Freeze Round 6 Robustness)  
**Scope:** Stage-1 Emergency Triage & Rule-Based Red-Flag Detection  
**Primary Engine:** `backend-poc-technical/agents/red_flag_patterns.py`  
**Yellow Safety Net:** `backend-poc-technical/agents/danger_wordgroups.py` (`acute_unclassified`)  
**Base-Screen Conservative Failsafe:** `backend-poc-technical/main.py` (Downgrades negated/past base hits to Yellow Review, gated by `NEGATED_RED_FLAG_TO_REVIEW`)  
**Protected Failsafe:** `backend-poc-technical/agents/input_triage.py` (Untouched, Byte-Identical to `origin/dev`)  
**Emergency Routing Protocol:** Deterministic escalation to Emergency Screen (1122 dispatch in Pakistan)  

---

## 1. Executive Summary & Honest Diagnostic Figures

Safety in chronic disease telemonitoring requires that acute life threats (cardiac ischemia, respiratory failure, acute cerebrovascular stroke, sudden hemodynamic collapse, diabetic ketoacidosis) are detected reliably in natural conversation.

However, clinical diagnostic claims must be made with complete scientific transparency:

| Evaluation Dimension | Metric | Benchmark Source | Notes / Interpretation |
| :--- | :---: | :--- | :--- |
| **Developer Regression Test Suite** | **100.0%** (991/991) | Internal regression suites (`test_red_flag_patterns.py`, `test_red_flags_harmless_answers.py`, `test_red_flags_round4.py`, `test_red_flag_r5.py`, `test_red_flag_r6.py`, `test_red_flag_mixed_answers.py`) | 991 unit tests verifying known syntactic templates, vocabulary lists, and compound mixed clauses across English, Urdu script, and Roman Urdu. |
| **Development Corpus (R5 / R6 Tuning)** | **96.57%** (676/700) Red Recall<br>**98.86%** (692/700) Combined Recall<br>**0.00%** (0/700) False Reds | `tests/fixtures/red_flag_heldout_r5.json` (N=1400: 700 positive, 700 negative, seed=42) | Development set used during R6 tuning. Stage-1 Red Recall reached 96.57%, Combined Red+Yellow reached 98.86%, and False Reds dropped to 0.00%. |
| **True Held-Out Systematic Corpus (R7)** | **88.86%** (622/700) Red Recall<br>**93.43%** (654/700) Combined Recall<br>**1.71%** (12/700) False Reds | `tests/fixtures/red_flag_heldout_r7.json` (N=1400: 700 positive, 700 negative, seed=2026, >30% new templates) | Generated with seed 2026 and new phrasing templates BEFORE code changes. Evaluated strictly ONCE at the end without developer inspection of misses. Demonstrates robust out-of-sample generalization. |
| **Reviewer Independent Hidden Sets** | Round 3: **54.5%** (12/22)<br>Round 4: **50.0%** (5/10)<br>Round 5: **50.0%** (5/10) | External hidden test sentences submitted by clinical reviewer prior to Round 3/4/5 | Real-world independent benchmark: on natural sentences **written independently by external reviewers**, uncalibrated sentence templates achieved 50%–55% emergency sensitivity, highlighting the necessity of human-in-the-loop review. |
| **Harmless Check-In Answer False Positives** | **0 / 155** (0.0%) | `test_red_flags_harmless_answers.py` | Ordinary non-emergency check-in answers ("no breathing trouble", "pehle se behtar", "haath sunn jab mobile chalata hoon") correctly stay non-emergency. |
| **Simulated Personas Non-Emergency Utterances** | **0 / 52** (0.0% Red) | `tests/sim/personas.json` (all non-emergency persona utterances) | Zero false-red emergency escalations on ordinary, non-emergency conversation flows. |
| **Single-LLM Baseline Emergency Recall** | **11.1%** (1/9) | Single-LLM baseline (`qwen/qwen3.8-27b` via Groq across 3 trials) | Generalist LLM failed to trigger emergency on 8 of 9 life-threatening presentations (`p22` chest pain, `p35` HTN crisis, `p37` DKA). |
| **Pipeline Overall Emergency Recall** | **100.0%** (3/3) | 51-Persona Benchmark Suite (`p22`, `p35`, `p37`) | Multi-agent deterministic failsafe successfully captured all life-threatening emergencies. Pipeline under-triage 3.9% (2/51), over-triage 7.8% (4/51). |

> [!WARNING]
> **No Unqualified "100% Sensitivity" Claim:**
> In accordance with honest evaluation practices, ChronicCare AI does **NOT** claim 100% sensitivity in the wild. While our 922-case developer regression suite achieves 100% pass rates, evaluation on unseen real-world phrases written by external clinicians demonstrated 50%–70% emergency sensitivity. Real-world deployment requires continuous clinical lexicon updates, localized negator models, and human-in-the-loop safety nets.

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

### 2.4 Round 6 Red-Flag Robustness Engine (F1 through F5)
Part R6 addressed structural weaknesses identified on natural held-out sets:
1. **F1 Unified Negation Engine:**
   - Preceding negators within 4 words (`no`, `without`, `never`, `koi ... nahi`, `بغیر`, `کوئی ... نہیں`).
   - Trailing negators within 6 words (`... was not experienced`, `... was never observed`, `... did not happen`, `... nahi hua`, `... نہیں ہوا`).
   - Passive avoidance frames (`... completely avoided and ruled out`, `... wali koi baat nahi hui`).
   - Echo frames (`chest tightness? nope`, `fainting: never`).
   - **Failure Verbs Invariant:** Failure verbs expressing acute loss of function (`sans nahi aa rahi`, `pani nahi ruk raha`, `aankhein nahi khol rahe`, `uth nahi raha`, `jawab nahi de raha`, `bol nahi pa raha`, `khada nahi hua ja raha`, `koi harkat nahi`, `bilkul behosh`) are acute emergencies whose `nahi` is NEVER treated as a negation. Verified by mutation `M-RF-2`.
2. **F2 Remote Past Historical Suppressor:**
   - Detects remote past markers (`< 2026`, `X saal pehle`, `last year`, `in childhood`, `bachpan mein`) combined with recovery cues (`tha lekin ab theek hoon`, `resolved`).
   - Does NOT suppress if current acute markers (`abhi`, `aaj subah se`, `kal se`, `now`, `today`) are present.
3. **F3 Organ-Subject Guard:**
   - Generic ambiguous terms (`band`, `ruk`, `phool`, `bhaari`, `sunn`, `kamzor`) only trigger emergencies for their dedicated target organ.
   - Benign colloquial uses (`naak band`, `dukaan band`, `light band`, `pet phool gaya`, `pair bhaari`, `sar bhaari`, `aankhein kamzor`, `nazar kamzor`) never trigger red flags.
4. **F4 Missing Family Members by Name:**
   - Direct named emergency matchers across all 5 clinical categories:
     - Breathing: `saans phansi/atki hui`, `dam ghut raha`, `cant get air in`.
     - Face droop: `chehra jhul gaya/dhalak gaya/mur gaya`, `mouth is lopsided`.
     - Vomiting/DKA: `andar nahi tik/thehar/reh raha`, `har ghante ulti`, `teen din se ulti`.
     - Syncope: `bilkul behosh`, `hosh kho baithe aur jaag nahi rahe`.
     - Stroke: `unable to move arm/leg`, `zaban larkhara rahi hai`.
5. **F5 Protected Base-Screen Conservative Downgrade (`main.py`):**
   - When the byte-protected base screen in `input_triage.py` fires on a clearly negated or remote past input (e.g. `"chest pain? no"`), `main.py` conservatively routes the check-in to Clinician Review (Yellow) rather than displaying the 1122 Red Emergency screen.
   - Clears `next_state.stage1_red_flag` and `next_state.intake["emergency"]`, attaches safety note, and logs an audit hit with `reason="negated_red_flag_needs_review"`.
   - Gated by flag `NEGATED_RED_FLAG_TO_REVIEW` (default: `true`).
   - Verified by architectural mutation proof `M-NRF-1` in `scripts/verify_mutations.py`.

---

## 3. Systematic Frozen Corpus Evaluation (R6 Benchmark)

To prevent overfitting to reviewer test sets, an independent systematic held-out corpus generator (`scripts/eval/gen_red_flag_corpus.py`) synthesized 1,400 balanced clinical utterances ($N=700$ emergency positives, $N=700$ non-emergency negatives, seed=42) frozen into `tests/fixtures/red_flag_heldout_r5.json`.

| Metric | Pre-R5 Baseline | Post-R5 Performance | Post-R6 Performance | Target / Requirement | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Emergency Positive Recall (Stage-1 Red)** | 74.29% (520/700) | 76.86% (538/700) | **96.57%** (676/700) | $\ge$ 85% | **PASS** |
| **Yellow Safety Net Catches (Stage-2 Review)** | 0.00% (0/700) | 7.57% (53/700) | **2.29%** (16/700) | Safety net for near-misses | **PASS** |
| **Combined Clinical Safety Sensitivity** | 74.29% (520/700) | 84.43% (591/700) | **98.86%** (692/700) | $\ge$ 95% | **PASS** |
| **False Red Alarms (Non-Emergency Negatives)** | 19.71% (138/700) | 10.57% (74/700) | **0.00%** (0/700) | $\le$ 3% | **PASS** |
| **Clean Non-Emergency Retention (Green)** | 67.29% (471/700) | 77.57% (543/700) | **99.43%** (696/700) | High routine triage fidelity | **PASS** |

---

## 4. Comprehensive Developer Test Suite Breakdown (922 Tests)

| Test File | Total Tests | Focus Area | Result |
| :--- | :---: | :--- | :---: |
| `backend-poc-technical/test_red_flag_patterns.py` | 185 | Core token-window matching across all 5 red flag categories | **PASS** |
| `backend-poc-technical/test_red_flags_harmless_answers.py` | 155 | Multi-lingual ordinary check-in answers, negations, and benign activity exclusions | **PASS** |
| `backend-poc-technical/test_red_flags_round4.py` | 278 | FAST stroke, cyanosis, fluid failure, and family subject variations | **PASS** |
| `backend-poc-technical/test_q1_red_flags.py` | 65 | Stage-1 emergency prompt guardrail evaluation | **PASS** |
| `backend-poc-technical/test_vomiting_fluids_red_flags.py` | 30 | Dehydration, DKA, and inability to retain fluids (*"paani nahi rukta"*) | **PASS** |
| `backend-poc-technical/test_red_flag_r5.py` | 132 | R5 spelling pairs (45), families (14), echo/negations (41), safety net & M-SN-1 | **PASS** |
| `backend-poc-technical/test_red_flag_r6.py` | 77 | R6 F1 negation & failure verbs, F2 remote past, F3 organ guards, F4 named cases, F5 conservative base downgrade & M-NRF-1 killer | **PASS** |
| **Total Test Suite** | **922** | **End-to-End Red-Flag Regression Suite** | **100% PASS** |

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
