# Independent Danger-Phrase Evaluation (Round 2) — Muhammad Saad

**Date:** 1 November 2026  
**Engines Evaluated:**
- **Live Engine (v2 Default):** `agents.adaptive_interview_agent.run_stage1_red_flag_screen`
- **Triage Engine (v3 Runner):** `agents.input_triage.classify_input` (backed by `screen_multilingual_danger_phrases`)

---

## 1. Overview & Authorship

This document reports the performance of the multilingual danger-phrase screening mechanisms against two independent test sets authored by Muhammad Saad:
1. **S-1 Baseline Set** (`tests/sim/danger_phrases_independent_saad.json`): 30 phrases (15 danger, 15 safe/negated; English & Roman Urdu), authored 13 October 2026.
2. **Round 2 Independent Set** (`tests/sim/danger_phrases_independent_saad_r2.json`): 30 new blind phrases (15 danger, 15 safe/negated; balanced across English, Roman Urdu, and Urdu script), hand-written directly from clinical emergency scenarios without viewing or referencing the internal pattern tables (`RED_FLAG_PATTERNS` or `screen_multilingual_danger_phrases`).

> **SAFETY PROTOCOL NOTICE:**  
> Neither engine was modified for this evaluation. All missed phrases are logged for clinical triage under GitHub issue:  
> **[Safety Issue #95: Danger-phrase detector low sensitivity on natural multi-lingual syntax](https://github.com/UsmanBari/ChronicCare-AI/issues/95)**

---

## 2. Evaluation Results Across Engines

### Table 1: Dual-Engine Performance Matrix

```
=== S-1 EVALUATION (30 phrases: 15 Danger, 15 Safe/Negated) ===
v2 (Live Engine):  TP=3, FN=12, FP=1, TN=14  |  Sensitivity: 20.0%  |  Specificity: 93.3%
v3 (Triage Engine): TP=6, FN=9,  FP=1, TN=14  |  Sensitivity: 40.0%  |  Specificity: 93.3%

=== R2 EVALUATION (30 phrases: 15 Danger, 15 Safe/Negated) ===
v2 (Live Engine):  TP=1, FN=14, FP=1, TN=14  |  Sensitivity:  6.7%  |  Specificity: 93.3%
v3 (Triage Engine): TP=2, FN=13, FP=0, TN=15  |  Sensitivity: 13.3%  |  Specificity: 100.0%
```

| Metric | S-1 (v2 Live) | S-1 (v3 Triage) | R2 (v2 Live) | R2 (v3 Triage) |
|---|:---:|:---:|:---:|:---:|
| **Total Phrases** | 30 | 30 | 30 | 30 |
| **Actual Danger (Positives)** | 15 | 15 | 15 | 15 |
| **Actual Safe (Negatives)** | 15 | 15 | 15 | 15 |
| **True Positives (TP)** | **3** | **6** | **1** | **2** |
| **False Negatives (FN — Missed Danger)** | **12** | **9** | **14** | **13** |
| **False Positives (FP — False Alarm)** | **1** | **1** | **1** | **0** |
| **True Negatives (TN — Correct Rejection)** | **14** | **14** | **14** | **15** |
| **Sensitivity (Recall)** | **20.0%** | **40.0%** | **6.7%** | **13.3%** |
| **Specificity** | **93.3%** | **93.3%** | **93.3%** | **100.0%** |

---

## 3. Detailed Missed Phrases (False Negatives)

### 3.1. Round 2 Missed Danger Expressions
Both engines missed the majority of conversational expressions where colloquial vocabulary, compound symptoms, or gendered/past-tense inflections differed from rigid dictionary patterns:

1. **Chest Pain:**
   - `"Severe crushing pressure in the middle of my chest"` (Missed by v2 & v3; lacks pattern for "crushing pressure")
   - `"Seene mein achanak shadeed chubhan aur dard ho raha hai"` (Missed by v2 & v3; lacks pattern for "chubhan")
   - `"Achanak ultay bazu me shadeed dard aur khichao agya"` (Missed by v2 & v3; arm radiation without "seene")
   - `"سینے میں بہت شدید گھٹن اور درد ہو رہا ہے"` (Missed by v2 & v3; lacks pattern for "گھٹن")

2. **Dyspnea / Breathing:**
   - `"I cannot catch my breath even while sitting still"` (Missed by v2 & v3; idiomatic phrase)
   - `"Sans bilkul ruk raha hai ghutan mehsoos ho rahi hai"` (Missed by v2 & v3; colloquial Roman Urdu)
   - `"سانس لینا ناممکن لگ رہا ہے دم گھٹ رہا ہے"` (Missed by v2 & v3; metaphorical expression "دم گھٹ رہا ہے")

3. **Stroke & Neurological:**
   - `"Sudden numbness in right side of face and arm"` (Missed by v2 & v3; pattern expects "face drooping")
   - `"Mera chehra achanak aik taraf terha ho gaya hai"` (Missed by v2 & v3; variant spelling "terha")
   - `"اچانک بائیں بازو اور آدھے چہرے پر سن پن آ گیا ہے"` (Missed by v2 & v3; vocabulary "سن پن")

4. **Syncope / Fainting:**
   - `"Achanak behosh ho kar gir paray thay"` (Missed by v2 & v3; past auxiliary "gir paray thay")
   - `"چکر آ کر بیہوش ہو گئی تھیں چند منٹ کے لیے"` (Missed by v2 & v3; feminine inflection "ہو گئی تھیں")

5. **Acute Vision Loss:**
   - `"My vision suddenly went completely black in left eye"` (Missed by v2 & v3; phrasing "went completely black")
   - `"اچانک دائیں آنکھ سے بالکل اندھیرا چھا گیا ہے"` (Missed by v2 & v3; idiomatic phrase "اندھیرا چھا گیا ہے")

---

## 4. Key Takeaways & Recommendations

1. **Specificity is High (93.3%–100%):** False alarms remain minimal across both engines.
2. **Critical Sensitivity Deficit:** Because both engines rely on exact substring matching, sensitivity drops from 20–40% on standard phrasing down to 6.7–13.3% on realistic conversational inputs.
3. **Assigned to Usman:** Logged in safety backlog for semantic embedding / fast keyword stemmer upgrade in Iteration 3.
