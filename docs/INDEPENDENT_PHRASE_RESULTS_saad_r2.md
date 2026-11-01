# Independent Danger-Phrase Evaluation (Round 2) — Muhammad Saad

**Date:** 1 November 2026  
**Evaluator Script:** `scripts/eval_phrase_set.py`  
**Detector Under Test:** `agents.input_triage.screen_multilingual_danger_phrases` (on `dev`)  

---

## 1. Overview & Context

This document reports the performance of the multilingual clinical danger-phrase detector against two independent test sets authored by Muhammad Saad:
1. **S-1 Baseline Set** (`tests/sim/danger_phrases_independent_saad.json`): 30 phrases (15 danger, 15 safe/negated; English & Roman Urdu), originally authored on 13 October 2026.
2. **Round 2 Independent Set** (`tests/sim/danger_phrases_independent_saad_r2.json`): 30 new blind phrases (15 danger, 15 safe/negated; balanced across English, Roman Urdu, and Urdu script), hand-authored without inspecting the detector's pattern lists.

> **SAFETY PROTOCOL NOTICE:**  
> The detector (`agents/input_triage.py`) is a protected safety file and was **not modified**. All missed danger phrases are documented here for Usman to triage in a dedicated safety issue.

---

## 2. Evaluation Results

### Table 1: Performance Summary Across Test Sets

| Metric | S-1 (13 Oct Baseline) | S-1 (Re-evaluated on `dev`) | Round 2 (New Blind Set) |
|---|:---:|:---:|:---:|
| **Total Phrases** | 30 | 30 | 30 |
| **Danger Phrases (Actual Positives)** | 15 | 15 | 15 |
| **Safe / Negated Phrases (Actual Negatives)** | 15 | 15 | 15 |
| **True Positives (TP)** | 7 | 6 | 2 |
| **False Negatives (FN — Missed Danger)** | 8 | 9 | 13 |
| **False Positives (FP — False Alarm)** | 2 | 1 | 0 |
| **True Negatives (TN — Correct Rejection)**| 13 | 14 | 15 |
| **Sensitivity (Recall)** | **46.67%** | **40.00%** | **13.33%** |
| **Specificity** | **86.67%** | **93.33%** | **100.00%** |

*Note: S-1 re-evaluation yielded 1 additional FN compared to initial 13 Oct baseline because strict boundary matching was refined.*

---

## 3. Analysis of Failing Items

### 3.1. Round 2 Missed Danger Phrases (13 False Negatives)

The detector failed to flag 13 out of 15 genuine danger phrases in Round 2 due to reliance on rigid keyword substring patterns:

1. **Chest Pain:**
   - `"Severe crushing pressure in the middle of my chest"` (English)  
     *Reason:* Missing phrase pattern for `"crushing pressure"`.
   - `"Seene mein achanak shadeed chubhan aur dard ho raha hai"` (Roman Urdu)  
     *Reason:* Roman Urdu variant `"chubhan aur dard"` not captured.
   - `"Achanak ultay bazu me shadeed dard aur khichao agya"` (Roman Urdu)  
     *Reason:* Radiation to left arm (`"ultay bazu me shadeed dard"`) uncaptured without explicit `"seene"` mention.
   - `"سینے میں بہت شدید گھٹن اور درد ہو رہا ہے"` (Urdu Script)  
     *Reason:* Exact compound `"گھٹن اور درد"` lacks matching pattern.

2. **Shortness of Breath / Breathing:**
   - `"I cannot catch my breath even while sitting still"` (English)  
     *Reason:* Idiomatic expression `"cannot catch my breath"` uncaptured.
   - `"Sans bilkul ruk raha hai ghutan mehsoos ho rahi hai"` (Roman Urdu)  
     *Reason:* Phrasing `"sans bilkul ruk raha hai"` not in exact keyword table.
   - `"سانس لینا ناممکن لگ رہا ہے دم گھٹ رہا ہے"` (Urdu Script)  
     *Reason:* Metaphorical expression `"دم گھٹ رہا ہے"` uncaptured.

3. **Stroke & Neurological Impairment:**
   - `"Sudden numbness in right side of face and arm"` (English)  
     *Reason:* Pattern looks for `"face drooping"` or `"slurred speech"`, missing `"numbness in right side of face"`.
   - `"Mera chehra achanak aik taraf terha ho gaya hai"` (Roman Urdu)  
     *Reason:* Variant spelling `"terha ho gaya"` missing from regex.
   - `"اچانک بائیں بازو اور آدھے چہرے پر سن پن آ گیا ہے"` (Urdu Script)  
     *Reason:* Urdu vocabulary `"سن پن"` (numbness) uncaptured.

4. **Fainting / Syncope:**
   - `"Achanak behosh ho kar gir paray thay"` (Roman Urdu)  
     *Reason:* Grammatical past tense `"gir paray thay"` not matched.
   - `"چکر آ کر بیہوش ہو گئی تھیں چند منٹ کے لیے"` (Urdu Script)  
     *Reason:* Feminine honorific past inflection `"بیہوش ہو گئی تھیں"` missing from root lemma.

5. **Acute Vision Loss:**
   - `"My vision suddenly went completely black in left eye"` (English)  
     *Reason:* Exact phrasing `"went completely black"` not captured.
   - `"اچانک دائیں آنکھ سے بالکل اندھیرا چھا گیا ہے"` (Urdu Script)  
     *Reason:* Idiomatic phrase `"اندھیرا چھا گیا ہے"` uncaptured.

### 3.2. S-1 Missed Danger Phrases (9 False Negatives)

1. `"My chest feels very tight and painful"` (`chest_pain`)
2. `"Mere se saans nahi li ja rahi"` (`breathing`)
3. `"I am not breathing properly"` (`breathing`)
4. `"Mujhe saans lene mein bohat mushkil ho rahi hai"` (`breathing`)
5. `"I suddenly feel confused and cannot speak properly"` (`confusion_and_stroke`)
6. `"Mera aik bazu achanak sunn ho gaya hai aur bolne mein mushkil hai"` (`confusion_and_stroke`)
7. `"One side of my face suddenly feels weak"` (`confusion_and_stroke`)
8. `"My sugar is extremely high and I keep vomiting"` (`dka_vomiting_high_glucose`)
9. `"Sugar bohat high hai aur mujhe bar bar ulti ho rahi hai"` (`dka_vomiting_high_glucose`)

### 3.3. S-1 False Positives (1 Item)

1. `"I had a severe headache yesterday but it is completely gone now"`  
   - Expected: `False` (resolved historical symptom).  
   - Detected: `True` (`severe_headache`).  
   - *Reason:* Detector lacks past-tense temporal negation extraction for headache mentions.

---

## 4. Key Findings & Recommendations

1. **High Specificity (100% on R2):** The current detector demonstrates excellent specificity (0 false alarms on Round 2 safe and negated inputs), successfully rejecting negative and non-emergency statements.
2. **Substantial Danger Recall Gap (13.33% on R2):** Keyword-matching detectors fail on natural conversational variations, inflections (especially Urdu verb conjugations), and compound symptom descriptions.
3. **Action Item for Usman:** Open GitHub safety issue titled: `safety(triage): danger-phrase detector low sensitivity on natural multi-lingual syntax (S-1: 40%, R2: 13.3%)` attaching the full failure logs from this report.
