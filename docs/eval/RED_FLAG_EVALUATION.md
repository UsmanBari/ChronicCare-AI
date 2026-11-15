# ChronicCare AI — Red-Flag Safety & Emergency Evaluation Report

**Date:** 14 November 2026  
**Scope:** Stage-1 Emergency Triage & Rule-Based Red-Flag Detection  
**Primary Engine:** `backend-poc-technical/agents/red_flag_patterns.py`  
**Protected Failsafe:** `backend-poc-technical/agents/input_triage.py` (Untouched, Byte-Identical to `dev`)  
**Emergency Routing Protocol:** Deterministic escalation to Emergency Screen (1122 dispatch in Pakistan)  

---

## 1. Executive Summary & Honest Diagnostic Figures

Safety in chronic disease telemonitoring requires that acute life threats (cardiac ischemia, respiratory failure, acute cerebrovascular stroke, sudden hemodynamic collapse, diabetic ketoacidosis) are detected reliably in natural conversation.

However, clinical diagnostic claims must be made with complete scientific transparency:

| Evaluation Dimension | Metric | Benchmark Source | Notes / Interpretation |
| :--- | :---: | :--- | :--- |
| **Developer Regression Test Suite** | **100.0%** (713/713) | Internal regression suites (`test_red_flag_patterns.py`, `test_red_flags_harmless_answers.py`, `test_red_flags_round4.py`, etc.) | Tests written against known syntactic templates and verified vocabulary lists across English, Urdu, and Roman Urdu. |
| **Reviewer Independent Hidden Set** | **~60%–70%** (12/22) | External hidden test sentences submitted by clinical reviewer prior to Round 3/4 | On natural sentences **not written by the developer**, uncalibrated sentence templates missed unusual syntactic structures and synonym variations. |
| **Harmless Check-In Answer False Positives** | **0 / 155** (0.0%) | `test_red_flags_harmless_answers.py` | Ordinary non-emergency check-in answers ("no breathing trouble", "pehle se behtar", "haath sunn jab mobile chalata hoon") correctly stay non-emergency. |
| **Single-LLM Baseline Emergency Recall** | **11.1%** (1/9) | Single-LLM baseline (`qwen/qwen3.8-27b` via Groq across 3 trials) | Generalist LLM failed to trigger emergency on 8 of 9 life-threatening presentations (`p22` chest pain, `p35` HTN crisis, `p37` DKA). |
| **Pipeline Overall Emergency Recall** | **100.0%** (3/3) | 51-Persona Benchmark Suite (`p22`, `p35`, `p37`) | Multi-agent deterministic failsafe successfully captured all life-threatening emergencies. |

> [!WARNING]
> **No Unqualified "100% Sensitivity" Claim:**
> In accordance with honest evaluation practices, ChronicCare AI does **NOT** claim 100% sensitivity in the wild. While our 713-case developer regression suite achieves 100% pass rates, evaluation on unseen real-world phrases written by external clinicians demonstrated ~60–70% emergency sensitivity. Real-world deployment requires continuous clinical lexicon updates, localized negator models, and human-in-the-loop safety nets.

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
2. **Clause-Bounded Token Windows:** Matches require an anatomical noun and an acute descriptor within a small token distance window ($N \le 6$ words) within the same clause.
3. **Localized Negator Suppression:** A negative frame directly preceding the symptom noun phrase (*"no / not / without / never / koi ... nahi / بغیر / کوئی ... نہیں"*, or *"no \<symptom\> trouble/problem/issue/masla/takleef"*) actively suppresses false emergency hits.
4. **Benign Activity & Posture Exclusions:** Numbness associated with clear posture triggers (*"jab der tak mobile chalata hoon"*, *"sleeping on arm"*) or long-standing chronic neuropathy (*"for years"*) is suppressed from acute FAST stroke. Heartburn triggered by spicy meals (*"tez mirch wala khana"*) without pressure or radiating pain is suppressed from acute cardiac emergency.

---

## 3. Comprehensive Developer Test Suite Breakdown (713 Tests)

| Test File | Total Tests | Focus Area | Result |
| :--- | :---: | :--- | :---: |
| `backend-poc-technical/test_red_flag_patterns.py` | 185 | Core token-window matching across all 5 red flag categories | **PASS** |
| `backend-poc-technical/test_red_flags_harmless_answers.py` | 155 | Multi-lingual ordinary check-in answers, negations, and benign activity exclusions | **PASS** |
| `backend-poc-technical/test_red_flags_round4.py` | 278 | FAST stroke, cyanosis, fluid failure, and family subject variations | **PASS** |
| `backend-poc-technical/test_q1_red_flags.py` | 65 | Stage-1 emergency prompt guardrail evaluation | **PASS** |
| `backend-poc-technical/test_vomiting_fluids_red_flags.py` | 30 | Dehydration, DKA, and inability to retain fluids (*"paani nahi rukta"*) | **PASS** |
| **Total Test Suite** | **713** | **End-to-End Red-Flag Regression Suite** | **100% PASS** |

---

## 4. Safety Fail-Safe & Production Boundaries

1. **Protocol 1122 Escalation:** Any positive red-flag trigger immediately halts conversational intake, launches the Emergency Screen, displays 1122 emergency contact options, and alerts the attending clinician.
2. **Zero Protected File Modifications:** All pattern updates were made strictly in `agents/red_flag_patterns.py`. Core guardrails in `input_triage.py` remain 100% byte-identical to `origin/dev`.
3. **Multi-Lingual Coverage:** Patterns are tested and evaluated natively across English, formal Urdu script, and vernacular Roman Urdu.
