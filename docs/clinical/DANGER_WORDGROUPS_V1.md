# Danger Word Groups v1: Clinical Safety Specification

**Document Version:** 1.0  
**Status:** Frozen for Blind Set Evaluation  
**Author:** Usman Bari (Lead Backend & Safety Architecture)  
**Date:** November 2026  
**Related Pull Request:** feat/i3-danger-wordgroups  

---

## 1. Clinical Rationale & System Architecture

In an asynchronous remote chronic care management setting (Type 2 Diabetes and Hypertension), patients frequently communicate acute or evolving symptoms in unstructured free text. A patient reporting severe symptoms during a routine check-in may describe life-threatening cardiovascular, cerebrovascular, or respiratory emergencies using diverse vernacular phrases, colloquialisms, and code-mixed expressions (English, Urdu script, and Roman Urdu).

Naive exact-string matching and rigid keyword lists fail to capture:
- Composable symptom descriptions (e.g., anatomical location separated from severity or descriptors: *"seenay par shadeed dabao mehsoos ho raha hai"*).
- Syntactic word order inversions in Urdu and Hindi (*"dard hai seene mein"* vs *"seene mein dard"*).
- Functional inability idioms that confirm profound neurological or respiratory deficits (*"uthaya nahi ja raha"* = motor paresis; *"bol nahi pa raha"* = dysarthria/aphasia; *"saans nahi aa rahi"* = dyspnea). Naive trailing negation detectors erroneously treat *"nahi"* in these phrases as symptom absence, missing acute emergencies.
- Cross-clause mentions of historical chronic conditions alongside acute emergencies (*"pichle saal sugar zyada thi, aaj seene mein shadeed dabao hai"*).

Danger Word Groups v1 provides a pure deterministic, regex-based clinical safety detector across five emergency groups. It operates without network access, language models, or database queries, delivering microsecond evaluation and provable safety properties.

---

## 2. The 5 Acute Danger Word Groups

The detector targets five acute medical emergencies where delayed clinical attention carries catastrophic risk:

| Group ID | Clinical Description | Target Emergency Syndromes | Anatomical & Symptom Cues |
|---|---|---|---|
| `cardiac_chest_pain` | Acute Coronary Syndrome | Myocardial Infarction, Unstable Angina, Aortic Dissection | Chest / sternum / ribs / heart / left arm + crushing / pressure / squeezing / tightness / severe pain / radiating (*seena, seenay, dil, chhati, dabao, bojh, phat raha, درد, دباؤ, سینہ*) |
| `stroke_fast_cue` | Acute Cerebrovascular Event | Ischemic Stroke, TIA, Intracranial Hemorrhage | Facial droop / crookedness / numbness (*terha, chehra, munh, ڈھلک*); Unilateral limb weakness / paralysis / numbness (*bazu, haath, taang, falij, kamzori, جان نہیں رہی*); Speech loss / slurring (*bol nahi pa raha, awaz ladkhada, بول نہیں پا رہا*) |
| `breathing_distress` | Acute Respiratory Distress | Pulmonary Embolism, Acute Pulmonary Edema, Severe Bronchospasm | Inability to breathe, gasping, suffocation, severe shortness of breath at rest (*saans nahi aa rahi, dum ghut, saans phool, دم گھٹ, سانس اکھڑ*) |
| `unresponsive_faint` | Syncope & Collapse | Cardiac Arrest, Ventricular Arrhythmia, Neurogenic Syncope | Sudden loss of consciousness, passed out, collapsed, unresponsive, blacked out (*behosh, gash, chakkar kha kar gir, بے ہوش, غش*) |
| `vomiting_blood` | Acute Upper/Lower GI Hemorrhage | Bleeding Peptic Ulcer, Esophageal Varices, Severe Lower GI Bleed | Hematemesis (vomiting blood, coffee ground emesis), melena (black tarry stool) (*khoon ki ulti, kala pakhana, خون کی الٹی, سیاہ پاخانہ*) |

---

## 3. Invariants & Safety Guarantees

Danger Word Groups v1 operates under strict, provably verified safety invariants:

1. **Raise-Only Invariant:**
   - A danger word-group match can **ONLY raise** a routine check-in triage level to `"review"`.
   - It **NEVER lowers** any triage level (e.g., cannot lower `"emergency"` or `"urgent"`).
   - It **NEVER sets** `"emergency"` or `"urgent"` by itself. Definitive emergency triage remains the exclusive domain of stage-1 red-flag screening (`run_stage1_red_flag_screen`) and validated clinical triage protocols.
2. **Conservative Decision Support on Chest Pain:**
   - In chronic hypertensive and diabetic cohorts, `"chest + pain/dard"` alone raises triage to `"review"` on purpose.
   - This conservative policy ensures that any patient reporting chest pain receives timely provider review without inappropriately alarming the patient with an unconfirmed false emergency designation.
3. **Feature Flag Gating (Default OFF):**
   - The detector is gated behind the environment variable `DANGER_WORDGROUPS_ENABLED="true"` (case-insensitive).
   - When the flag is unset or `"false"`, the check-in pipeline behaves identically to Release 1 baseline with zero side-effects.

---

## 4. Suppression Guards & Clause-Level Isolation

To prevent false alarms without compromising sensitivity, five general suppression guards are implemented:

### a. Clause-Level Isolation
- Sentences are segmented into clinical clauses at punctuation (`.,;:!?،؛؟`) and conjunction boundaries (`and`, `aur`, `lekin`, `magar`, `but`, `اور`, `لیکن`, `مگر`).
- Past-tense and resolved evaluations are conducted **strictly on the clause containing the candidate match**, never across `full_text`.
- Example: In *"last year I had a cold. Now my face is drooping"*, Clause 1 is past, but Clause 2 is active acute stroke. Clause 2 is evaluated independently and triggers `stroke_fast_cue`.

### b. Bidirectional & Trailing Negation
- **Preceding Negation:** Inspected up to 4 tokens prior to the match span (*"no"*, *"not"*, *"denies"*, *"bina"*, *"baghair"*, *"نہیں"*, *"نہ"*, *"بغیر"*).
- **Trailing Negation:** Evaluated after the symptom (*"seene mein dard nahi hai"* -> suppressed by `negation`).
- **Inability Idiom Exclusion:** Functional inability constructions (*"uthaya nahi ja raha"*, *"bol nahi pa raha"*, *"saans nahi aa rahi"*, *"jaan nahi rahi"*, *"نہیں جا رہا"*, *"نہیں پا رہا"*, *"نہیں آ رہی"*) represent loss of function and confirm danger. They are explicitly excluded from trailing negation and never suppress a symptom match.

### c. Explicitly Resolved State Guard
- A match is suppressed by `resolved` only if accompanied by an explicit recovery marker:
  - English: `"now fine"`, `"currently better"`, `"resolved"`.
  - Roman Urdu: `"ab theek"`, `"ab behtar"`, `"ab acha"` (within 3 words), `"theek ho gaya"`.
  - Urdu Script: `اب ٹھیک`, `اب بہتر`, `ٹھیک ہو گیا`.
- **Exclusion of "nahi":** `"nahi"` is strictly removed from resolved patterns to prevent confusion with active inability (*"ab saans nahi aa rahi"* is active danger, not resolved).
- **Exclusion of "abhi":** `"abhi"` (*ابھی*) means "right now" (acute onset) and is strictly excluded from resolved patterns.

### d. Ongoing Time vs. Historical Past
- Ongoing temporal phrases (*"since yesterday"*, *"kal se"*, *"subah se"*, *"do din se"*, *"کل سے"*, *"صبح سے"*) describe active complaints and immediately disqualify past-tense suppression.
- Historical past requires explicit past-only markers in the same clause:
  - English: `"history of"`, `"used to"`, `"previously"`, `"in the past"`, `"months ago"`, `"had [event] ago"`.
  - Roman Urdu: Explicit past verbs `tha / thi / the` combined with historical markers (*"pehle tha"*, *"pichle saal ... tha"*, *"kal tha"*).
  - Urdu Script: `پہلے تھا`, `کل تھا`, `پچھلے سال ... تھا`.

### e. Urdu Script Unicode Lookaround Boundaries
- Python's standard `\b` regex boundary is ASCII-centric and fails on Arabic/Urdu Unicode sequences (`\u0600-\u06FF`).
- Every Urdu word and token is bounded by lookarounds:
  - Preceding: `(?<![\u0600-\u06FF])`
  - Trailing: `(?![\u0600-\u06FF])`
- This eliminates false substring activations (e.g., preventing `دل` [heart] from matching within `بدل` [changed], and `سن` [numb] from matching within `سنبھل` [walk carefully]).

### f. Mild Sensation & Benign Procedure Qualifiers
- Non-cardiac sensations like mild heartburn (*"mild burning"*, *"halki jalan"*) are guarded unless severe descriptors (*"crushing"*, *"pressure"*, *"bojh"*) co-occur.
- Dental numbness (*"dentist numbness in mouth"*, *"daant sunn"*) is guarded as benign procedural local anesthesia in the absence of limb weakness or dysarthria.

---

## 5. System Wiring, Audit Logging & PHI Protection

### Call Sites
1. **Medication Adherence Answer:** Screened in `main.py:answer_checkin_endpoint` when medication adherence response text is provided.
2. **v2 Adaptive Interview Answers:** Screened in `main.py:answer_checkin_endpoint`. **Skipped** if existing stage-1 red-flag screen already triggered (`not next_state.stage1_red_flag`).
3. **v3 Adaptive Interview Answers:** Screened in `interview_v3_runner.py:next_turn`.

### Data Schema & PHI Hygiene
- **`WordGroupResult`:** Contains strictly `is_danger: bool`, `group: str | None`, and `suppressed_by: str | None` (`None`, `"negation"`, `"past"`, `"resolved"`).
- **Stored State Hits:** Stored as `{"group": str, "step": str}` only. Patient text, matched phrases, and raw substrings are **strictly forbidden** from storage in state or check-in records.
- **Audit Logging:** Emits action `danger_wordgroup_hit` with outcome `"flagged"` and detail `{"group": wg_hit.group}`. Zero patient free text or PHI is recorded in audit logs.

---

## 6. Patient Advisory & Emergency Routing

When an acute danger word-group is detected in patient text during check-in, the system returns a localized emergency advisory directing the patient to emergency medical services (Rescue 1122 in Pakistan):

- **English (`en`):**
  > *"If this is an emergency, call 1122 now."*
- **Urdu (`ur`):**
  > *"اگر یہ ایمرجنسی ہے تو ابھی 1122 پر کال کریں۔"*
- **Roman Urdu (`roman_ur`):**
  > *"Agar yeh emergency hai to abhi 1122 par call karein."*

---

## 7. Development Benchmark Analysis & Baseline Comparison

### Gold Eval Set Comparison (36/83 vs 39/83)
During initial benchmarking prior to the development improvement pass:
- **v2 Stage-1 Baseline:** Caught 39/83 danger sentences in the Gold set using static hardcoded exact substring matches (*"chest pain"*, *"bayein bazu me dard"*).
- **Initial Danger Word Groups v1:** Caught 36/83 danger sentences in the Gold set.
- **Root Cause of Initial 3-Sentence Gap:** The initial v1 detector required compound severity or radiation qualifiers alongside anatomical terms, whereas 3 sentences in the Gold set contained simple non-compound expressions (*"chest hurts"*, *"pain in my chest"*). Furthermore, Roman Urdu spelling variants (*"seene me"* vs *"seenay"*) lacked composable body+pain fallback.
- **Resolution:** By introducing the composable Group 1 body + pain/severity rule (*"chest + pain/dard"* raises to review), Danger Word Groups v1 catches all 39 sentences and correctly detects additional composable variants missed by the baseline, achieving superior sensitivity while maintaining 0% false alarms across all dev sets.

---

## 8. Verification & Mutation Proofs

The safety invariants are guarded by 81 hermetic tests in `backend-poc-technical/test_danger_wordgroups.py` and 4 targeted mutation proofs in `scripts/verify_mutations.py`:
- `M-U-WG-1`: Removing `_raise_level(..., "review")` fails `test_c3_unit_routine_plus_hit_raises_to_review` -> **KILLED**
- `M-U-WG-2`: Setting `emergency` instead of `review` fails `test_c4_wordgroup_hit_never_yields_urgent_or_emergency` -> **KILLED**
- `M-U-WG-3`: Disabling trailing negation guard fails `test_c2_negation_and_resolved_guards` -> **KILLED**
- `M-U-WG-4`: Forcing flag check to always true fails `test_c5_flag_off_invariant_behavior_identical_to_baseline` -> **KILLED**
