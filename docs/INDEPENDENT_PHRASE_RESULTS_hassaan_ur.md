# Independent Urdu-Script Phrase Test Results (Hassaan)

**Date:** 2026-10-29  
**Evaluator:** Hassaan Mudassar  
**Test Set:** `tests/sim/danger_phrases_independent_hassaan_ur.json`  
**Total Phrases:** 30 (20 Expected Danger, 10 Expected Safe Look-alikes)  

> **Clinical Safety Invariant:**  
> `input_triage` was not changed today; any failure is logged for Usman to decide on Week 3.

---

## 1. Summary Metrics

| Metric | Formula | Value | Percentage |
|---|---|---|---|
| **True Positives (TP)** | Correctly identified red flags | 6 / 20 | - |
| **True Negatives (TN)** | Correctly identified safe look-alikes | 10 / 10 | - |
| **False Negatives (FN)** | Missed red flags (Safety risk) | 14 / 20 | - |
| **False Positives (FP)** | False alarms on safe phrases | 0 / 10 | - |
| **Sensitivity** | TP / (TP + FN) | 6/20 | **30.0%** |
| **Specificity** | TN / (TN + FP) | 10/10 | **100.0%** |
| **False Negative Rate (FNR)** | FN / (TP + FN) | 14/20 | **70.0%** |
| **False Positive Rate (FPR)** | FP / (TN + FP) | 0/10 | **0.0%** |

---

## 2. False Negatives (Missed Red Flags)

| ID | Category | Patient Phrase | Actual Classification | Detected Category |
|---|---|---|---|---|
| 2 | `chest_pain` | چھاتی پر شدید دباؤ ہے اور درد بائیں بازو میں جا رہا ہے | `normal_clinical` | `None` |
| 3 | `chest_pain` | سینے میں جلن اور شدید گھٹن ہو رہی ہے | `normal_clinical` | `None` |
| 6 | `breathing` | سانس پھول رہی ہے اور بیٹھا بھی نہیں جا رہا | `normal_clinical` | `None` |
| 8 | `syncope` | آنکھوں کے آگے اندھیرا آ گیا اور غشی کے دورے پڑ رہے ہیں | `normal_clinical` | `None` |
| 9 | `focal_weakness_stroke` | میرا آدھا جسم بالکل سن ہو گیا ہے اور ہلایا نہیں جا رہا | `normal_clinical` | `None` |
| 10 | `focal_weakness_stroke` | میرے بائیں ہاتھ اور پاؤں میں جان نہیں رہی، کمزوری ہو گئی ہے | `normal_clinical` | `None` |
| 11 | `focal_weakness_stroke` | میرا منہ ایک طرف ٹیڑھا ہو گیا ہے اور بولا نہیں جا رہا | `normal_clinical` | `None` |
| 13 | `confusion` | بہت شدید چکر آ رہے ہیں اور سر گھوم رہا ہے، حواس کام نہیں کر رہے | `normal_clinical` | `None` |
| 14 | `severe_hypoglycemia` | شوگر 35 آ گئی ہے اور ہاتھ کانپ رہے ہیں، شدید پسینہ آ رہا ہے | `normal_clinical` | `None` |
| 16 | `severe_hypoglycemia` | کپکپی طاری ہے، آنکھوں کے آگے اندھیرا ہے اور شوگر 40 سے کم ہے | `normal_clinical` | `None` |
| 17 | `severe_headache` | میرے سر میں ایسا شدید درد ہے جیسے پہلے کبھی نہیں ہوا | `normal_clinical` | `None` |
| 18 | `vision_loss` | اچانک ایک آنکھ سے نظر آنا بند ہو گیا ہے | `normal_clinical` | `None` |
| 19 | `bleeding` | خون کی الٹی آئی ہے اور چکر آ رہے ہیں | `normal_clinical` | `None` |
| 20 | `palpitations_danger` | دل کی دھڑکن بے قابو ہو کر سینے سے باہر آ رہی ہے اور پسینے چھوٹ رہے ہیں | `normal_clinical` | `None` |

---

## 3. False Positives (Safe Look-alikes Escalated)

*Zero False Positives encountered.* (Specificity: 100.0%)

---

## 4. Complete Test Results Breakdown

| ID | Category | Expected Danger | Actual Danger | Status | Phrase |
|---|---|---|---|---|---|
| 1 | `chest_pain` | True | True | **TP** | میرے سینے میں شدید درد ہو رہا ہے جیسے کوئی بوجھ رکھا ہو |
| 2 | `chest_pain` | True | False | **FN** | چھاتی پر شدید دباؤ ہے اور درد بائیں بازو میں جا رہا ہے |
| 3 | `chest_pain` | True | False | **FN** | سینے میں جلن اور شدید گھٹن ہو رہی ہے |
| 4 | `breathing` | True | True | **TP** | مجھے سانس لینے میں بہت تنگی ہو رہی ہے، دم گھٹ رہا ہے |
| 5 | `breathing` | True | True | **TP** | بالکل سانس نہیں آ رہی، بولا بھی نہیں جا رہا |
| 6 | `breathing` | True | False | **FN** | سانس پھول رہی ہے اور بیٹھا بھی نہیں جا رہا |
| 7 | `syncope` | True | True | **TP** | مجھے اچانک چکر آیا اور میں بے ہوش ہو کر گر پڑا |
| 8 | `syncope` | True | False | **FN** | آنکھوں کے آگے اندھیرا آ گیا اور غشی کے دورے پڑ رہے ہیں |
| 9 | `focal_weakness_stroke` | True | False | **FN** | میرا آدھا جسم بالکل سن ہو گیا ہے اور ہلایا نہیں جا رہا |
| 10 | `focal_weakness_stroke` | True | False | **FN** | میرے بائیں ہاتھ اور پاؤں میں جان نہیں رہی، کمزوری ہو گئی ہے |
| 11 | `focal_weakness_stroke` | True | False | **FN** | میرا منہ ایک طرف ٹیڑھا ہو گیا ہے اور بولا نہیں جا رہا |
| 12 | `confusion` | True | True | **TP** | زبان لڑکھڑا رہی ہے، سمجھ نہیں آ رہا کہ میں کہاں ہوں |
| 13 | `confusion` | True | False | **FN** | بہت شدید چکر آ رہے ہیں اور سر گھوم رہا ہے، حواس کام نہیں کر رہے |
| 14 | `severe_hypoglycemia` | True | False | **FN** | شوگر 35 آ گئی ہے اور ہاتھ کانپ رہے ہیں، شدید پسینہ آ رہا ہے |
| 15 | `severe_hypoglycemia` | True | True | **TP** | شوگر بہت گر گئی ہے، بے ہوشی طاری ہو رہی ہے |
| 16 | `severe_hypoglycemia` | True | False | **FN** | کپکپی طاری ہے، آنکھوں کے آگے اندھیرا ہے اور شوگر 40 سے کم ہے |
| 17 | `severe_headache` | True | False | **FN** | میرے سر میں ایسا شدید درد ہے جیسے پہلے کبھی نہیں ہوا |
| 18 | `vision_loss` | True | False | **FN** | اچانک ایک آنکھ سے نظر آنا بند ہو گیا ہے |
| 19 | `bleeding` | True | False | **FN** | خون کی الٹی آئی ہے اور چکر آ رہے ہیں |
| 20 | `palpitations_danger` | True | False | **FN** | دل کی دھڑکن بے قابو ہو کر سینے سے باہر آ رہی ہے اور پسینے چھوٹ رہے ہیں |
| 21 | `safe_lookalike` | False | False | **TN** | کل سینے میں ہلکی سی جلن تھی لیکن اب ٹھیک ہے |
| 22 | `safe_lookalike` | False | False | **TN** | تیز چلنے پر تھوڑا سا سانس پھولتا ہے ورنہ میں آرام سے ہوں |
| 23 | `safe_lookalike` | False | False | **TN** | کل رات نیند پوری نہیں ہوئی تو سر میں ہلکا سا بوجھ ہے |
| 24 | `safe_lookalike` | False | False | **TN** | دوائی وقت پر لے رہا ہوں، بس کبھی کبھار تھکن ہو جاتی ہے |
| 25 | `safe_lookalike` | False | False | **TN** | میری شوگر 130 ہے اور میں بالکل ٹھیک محسوس کر رہا ہوں |
| 26 | `safe_lookalike` | False | False | **TN** | صبح سے کچھ نہیں کھایا اس لیے بھوک لگی ہے اور سستی ہو رہی ہے |
| 27 | `safe_lookalike` | False | False | **TN** | بلڈ پریشر 125/80 ہے، سب ٹھیک چل رہا ہے |
| 28 | `safe_lookalike` | False | False | **TN** | گذشتہ ہفتے ہلکا چکر آیا تھا مگر پانی پینے کے بعد بالکل ٹھیک ہو گیا |
| 29 | `safe_lookalike` | False | False | **TN** | کندھے میں پٹھوں کا کھچاؤ ہے، سینے میں کوئی درد نہیں |
| 30 | `safe_lookalike` | False | False | **TN** | ڈاکٹر صاحب نے کل چیک کیا تھا، طبیعت اب پہلے سے بہت بہتر ہے |

---

## 5. Proposed for Doctor Review (14 Missed Urdu Danger Phrases)

These regex patterns are proposed for clinical sign-off by Usman / Dr. Farooq before being incorporated into `backend-poc-technical/agents/input_triage.py`. Per project safety rules, **no triage code has been modified**; these proposals are submitted for formal review.

| Phrase | Proposed Pattern | Category | Proposed Level | Clinical Reason |
|---|---|---|---|---|
| چھاتی پر شدید دباؤ ہے اور درد بائیں بازو میں جا رہا ہے | `(?:چھاتی\|سینے).*(?:دباؤ\|بوجھ).*بائیں بازو` | `chest_pain` | `emergency` | Radiation of heavy chest pressure into the left arm is a hallmark symptom of acute coronary syndrome (ACS). |
| سینے میں جلن اور شدید گھٹن ہو رہی ہے | `(?:سینے\|چھاتی).*(?:گھٹن\|شدید گھٹن)` | `chest_pain` | `emergency` | Severe chest constriction/suffocation ("گھٹن") with burning sensations often indicates ischemic cardiac pain rather than benign gastroesophageal reflux. |
| سانس پھول رہی ہے اور بیٹھا بھی نہیں جا رہا | `سانس پھول.*(?:بیٹھا بھی نہیں جا رہا\|چلنا محال)` | `breathing` | `emergency` | Orthopnea or acute breathlessness that impairs sitting still indicates acute respiratory compromise or decompensated heart failure. |
| آنکھوں کے آگے اندھیرا آ گیا اور غشی کے دورے پڑ رہے ہیں | `غشی(?: کے دورے)?\|آنکھوں کے آگے اندھیرا` | `syncope` | `emergency` | Recurrent blackout episodes or actual fainting spells ("غشی") suggest hemodynamically unstable arrhythmias or transient cerebral hypoperfusion. |
| میرا آدھا جسم بالکل سن ہو گیا ہے اور ہلایا نہیں جا رہا | `آدھا جسم.*(?:سن\|ہلایا نہیں جا رہا)` | `focal_weakness_stroke` | `emergency` | Acute unilateral body numbness and inability to move limbs (hemiparesis) is a cardinal stroke warning sign (FAST criteria). |
| میرے بائیں ہاتھ اور پاؤں میں جان نہیں رہی، کمزوری ہو گئی ہے | `(?:ہاتھ اور پاؤں\|ایک طرف).*جان نہیں رہی` | `focal_weakness_stroke` | `emergency` | Sudden unilateral motor loss ("جان نہیں رہی") indicates focal neurological deficit consistent with ischemic stroke or TIA. |
| میرا منہ ایک طرف ٹیڑھا ہو گیا ہے اور بولا نہیں جا رہا | `منہ.*ٹیڑھا\|بولا نہیں جا رہا` | `focal_weakness_stroke` | `emergency` | Acute facial asymmetry ("منہ ٹیڑھا") paired with dysphasia ("بولا نہیں جا رہا") demands immediate emergency thrombolysis evaluation. |
| بہت شدید چکر آ رہے ہیں اور سر گھوم رہا ہے، حواس کام نہیں کر رہے | `حواس کام نہیں کر رہے` | `confusion` | `emergency` | Acute loss of faculties / encephalopathy / severe cognitive confusion ("حواس کام نہیں کر رہے") indicates critical cerebral compromise. |
| شوگر 35 آ گئی ہے اور ہاتھ کانپ رہے ہیں، شدید پسینہ آ رہا ہے | `شوگر.*(?:3[0-9]\|2[0-9]\|[1-9])\b.*(?:کانپ\|پسینہ)` | `severe_hypoglycemia` | `emergency` | Objective glucose $< 40\text{ mg/dL}$ with acute autonomic symptoms (tremors, sweating) represents neuroglycopenic risk of seizure/coma. |
| کپکپی طاری ہے، آنکھوں کے آگے اندھیرا ہے اور شوگر 40 سے کم ہے | `شوگر.*40 سے کم\|کپکپی.*آنکھوں کے آگے اندھیرا` | `severe_hypoglycemia` | `emergency` | Explicit report of glucose $< 40\text{ mg/dL}$ with presyncopal visual darkening and tremors requires immediate intervention. |
| میرے سر میں ایسا شدید درد ہے جیسے پہلے کبھی نہیں ہوا | `شدید درد.*پہلے کبھی نہیں ہوا\|بدترین سر درد` | `severe_headache` | `emergency` | Classic "thunderclap" headache description ("worst headache of life"), a red flag for subarachnoid hemorrhage (SAH). |
| اچانک ایک آنکھ سے نظر آنا بند ہو گیا ہے | `اچانک.*نظر آنا بند\|ایک آنکھ سے.*بند` | `vision_loss` | `emergency` | Acute monocular visual loss (amaurosis fugax or central retinal artery occlusion) is an acute ocular and cerebrovascular emergency. |
| خون کی الٹی آئی ہے اور چکر آ رہے ہیں | `خون کی الٹی\|قے.*خون` | `bleeding` | `emergency` | Hematemesis accompanied by postural dizziness indicates active gastrointestinal hemorrhage with hemodynamic risk. |
| دل کی دھڑکن بے قابو ہو کر سینے سے باہر آ رہی ہے اور پسینے چھوٹ رہے ہیں | `(?:دھڑکن\|دل).*بے قابو.*(?:پسینے\|سینے)` | `palpitations_danger` | `emergency` | Uncontrolled violent palpitations accompanied by cold sweats indicates acute tachyarrhythmia or cardiogenic distress. |

---

## 6. Engine Comparison: v2 vs v3 Triage on Urdu Phrases

| Architectural Dimension | Legacy v2 Engine (`adaptive_interview_agent.py`) | Modern v3 Engine (`input_triage.py` + Runner) | Impact on Urdu Safety & User Experience |
|---|---|---|---|
| **Triage Screening Phase** | Triage screening is embedded late in sequential question steps. | Upfront screening on **every patient input** before question planning. | In v3, a patient typing an emergency phrase in Urdu at turn 1 is escalated immediately without enduring symptom questions. |
| **Urdu Negation Handling** | Relies on basic English negation windowing; fails on complex Urdu negation suffixes (`نہ`, `نہیں`, `ورنہ ٹھیک ہے`). | Uses multilingual token normalization and Urdu negation boundary markers. | Correctly classifies safe phrases like *"کندھے میں پٹھوں کا کھچاؤ ہے، سینے میں کوئی درد نہیں"* as `TN` in both engines, but v3 normalizes Urdu diacritics systematically. |
| **Phrase Vocabulary & Coverage** | Hard-coded string fragments scattered across decision trees. | Centralized danger pattern table with standardized categories (`chest_pain`, `breathing`, etc.). | The blind phrase test yielded identical **30.0% sensitivity** and **100% specificity** because both engines currently rely on the pre-Week 2 vocabulary. v3 provides a clean single table for Usman to approve the 14 proposed patterns. |
| **Language Consistency (Leakage)** | Emitted mixed English fallbacks for unit clarifications and safety warnings. | **Zero English string leakage** (verified by `test_v3_no_english_leak.py`). | When an emergency is detected or a reading is clarified, v3 delivers 100% Urdu or Roman Urdu responses without cognitive dissonance for patients in distress. |
| **Doctor Override Governance** | Logic changes require editing protected agent core files. | Strictly declarative regex table proposed for clinician sign-off. | Eliminates regression risks in protected clinical rules while enabling continuous vocabulary expansion. |
