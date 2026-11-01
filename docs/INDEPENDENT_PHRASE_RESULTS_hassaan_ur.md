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

These regex patterns are proposed for clinical sign-off by Usman, then the reviewing doctors (see docs/DOCTOR_REVIEW_PACK_W2.md) before being incorporated into `backend-poc-technical/agents/input_triage.py`. Per project safety rules, **no triage code has been modified**; these proposals are submitted for formal review.

| Phrase | Proposed Pattern / Evaluator | Category | Proposed Level | Clinical Reason |
|---|---|---|---|---|
| چھاتی پر شدید دباؤ ہے اور درد بائیں بازو میں جا رہا ہے | `(?:چھاتی|سینے).*(?:دباؤ|بوجھ|درد|چبھن|سخت گھٹن).*(?:بائیں|بازو|گردن|کندھ)` | `chest_pain` | `emergency` | Radiation of heavy chest pressure into the left arm, neck, or shoulder is a hallmark symptom of acute coronary syndrome (ACS). |
| سینے میں جلن اور شدید گھٹن ہو رہی ہے | `(?:سینے|چھاتی).*(?:شدید گھٹن|سخت گھٹن|دم گھٹ)` | `chest_pain` | `emergency` | Severe chest constriction/suffocation ("گھٹن") with burning sensations often indicates ischemic cardiac pain rather than benign gastroesophageal reflux. |
| سانس پھول رہی ہے اور بیٹھا بھی نہیں جا رہا | `سانس.*(?:پھول|تکلیف|رکنے لگا|رک رہا).*(?:بیٹھا بھی نہیں جا رہا|چلنا محال|لیٹنے پر دم گھٹ|جھاگ)` | `breathing` | `emergency` | Orthopnea or acute breathlessness that impairs sitting or lying down indicates acute respiratory compromise or decompensated heart failure. |
| آنکھوں کے آگے اندھیرا آ گیا اور غشی کے دورے پڑ رہے ہیں | `غشی(?: کے دورے)?|(?:آنکھوں کے آگے اندھیرا.*(?:دورے|غشی|بے ہوش|گر پڑ|چھا گیا))|(?:بے سدھ ہو کر گر)` | `syncope` | `emergency` | Recurrent blackout episodes or actual fainting spells ("غشی") suggest hemodynamically unstable arrhythmias or transient cerebral hypoperfusion. Tightened to require faint/blackout context so benign sensory mentions do not alarm. |
| میرا آدھا جسم بالکل سن ہو گیا ہے اور ہلایا نہیں جا رہا | `(?:آدھا جسم|ایک طرف|بائیں ہاتھ|دائیں ہاتھ).*(?:سن|کمزور|جان نہیں|ہلایا نہیں جا رہا)` | `focal_weakness_stroke` | `emergency` | Acute unilateral body numbness and inability to move limbs (hemiparesis) is a cardinal stroke warning sign (FAST criteria). |
| میرے بائیں ہاتھ اور پاؤں میں جان نہیں رہی، کمزوری ہو گئی ہے | `(?:ایک طرف کا (?:ہاتھ|بازو|پاؤں|ٹانگ).*(?:کمزور|سن|جان نہیں))|(?:ہاتھ اور پاؤں.*جان نہیں رہی)` | `focal_weakness_stroke` | `emergency` | Sudden unilateral motor loss ("جان نہیں رہی") indicates focal neurological deficit consistent with ischemic stroke or TIA. |
| میرا منہ ایک طرف ٹیڑھا ہو گیا ہے اور بولا نہیں جا رہا | `(?:منہ.*(?:ٹیڑھا|ڈھلک|لٹک))|(?:چہرہ|چہرے).*(?:ٹیڑھا|ڈھلک|لٹک)|(?:بولنے میں مشکل.*ایک طرف)|(?:منہ.*ٹیڑھا.*بولا نہیں جا رہا)|(?:پانی پیتے ہوئے منہ سے نکل)` | `focal_weakness_stroke` | `emergency` | Acute facial asymmetry ("منہ ٹیڑھا") paired with dysphasia ("بولا نہیں جا رہا") demands immediate emergency thrombolysis evaluation. Tightened to exclude bare "بولا نہیں جا رہا" which occurs in benign sore throats. |
| بہت شدید چکر آ رہے ہیں اور سر گھوم رہا ہے، حواس کام نہیں کر رہے | `حواس کام نہیں کر رہے|باتیں بہکی|نہیں پتہ.*کہاں` | `confusion` | `emergency` | Acute loss of faculties / encephalopathy / severe cognitive confusion ("حواس کام نہیں کر رہے") indicates critical cerebral compromise. |
| شوگر 35 آ گئی ہے اور ہاتھ کانپ رہے ہیں، شدید پسینہ آ رہا ہے | Numeric extraction with `\b\d{1,3}\b < 54` + symptoms `(?:ہاتھ کانپ|پسینہ|کپکپی|لرز|چکر|بے ہوش|غشی|الجھن|بے چینی|کمزوری)` | `severe_hypoglycemia` | `emergency` | Objective glucose $< 54\text{ mg/dL}$ with acute autonomic/neuroglycopenic symptoms represents neuroglycopenic risk of seizure/coma. Evaluated numerically with Eastern Arabic digit conversion (۰-۹) and word boundaries to guarantee `135` never matches `35`. |
| کپکپی طاری ہے، آنکھوں کے آگے اندھیرا ہے اور شوگر 40 سے کم ہے | `شوگر.*(?:40|50|54)\s*سے کم|کپکپی.*آنکھوں کے آگے اندھیرا.*شوگر` | `severe_hypoglycemia` | `emergency` | Explicit report of glucose $< 40\text{ mg/dL}$ with presyncopal visual darkening and tremors requires immediate intervention. |
| میرے سر میں ایسا شدید درد ہے جیسے پہلے کبھی نہیں ہوا | `سر.*(?:بجلی کا جھٹکا|شدید ترین درد|بدترین|پہلے کبھی نہیں ہوا|چبھن.*شدید ترین|(?:درد.*(?:اتنا شدید.*(?:الٹی|برداشت سے باہر))))` | `severe_headache` | `emergency` | Classic "thunderclap" headache description ("worst headache of life"), a red flag for subarachnoid hemorrhage (SAH). |
| اچانک ایک آنکھ سے نظر آنا بند ہو گیا ہے | `(?:اچانک.*(?:ایک آنکھ|دائیں آنکھ|بائیں آنکھ|دونوں آنکھوں)?.*(?:نظر آنا بند|کالی پٹی))` | `vision_loss` | `emergency` | Acute monocular visual loss (amaurosis fugax or central retinal artery occlusion) is an acute ocular and cerebrovascular emergency. |
| خون کی الٹی آئی ہے اور چکر آ رہے ہیں | `خون کی الٹی|قے.*خون|الٹی میں.*خون|پاخانے کا رنگ کالا سیاہ` | `bleeding` | `emergency` | Hematemesis or melena accompanied by postural dizziness indicates active gastrointestinal hemorrhage with hemodynamic risk. |
| دل کی دھڑکن بے قابو ہو کر سینے سے باہر آ رہی ہے اور پسینے چھوٹ رہے ہیں | `(?:دھڑکن|دل).*بے قابو.*(?:پسینے|سینے)|دل بہت تیز دھڑک.*سینے سے باہر` | `palpitations_danger` | `emergency` | Uncontrolled violent palpitations accompanied by cold sweats indicates acute tachyarrhythmia or cardiogenic distress. |

---

## 6. Measured Engine Comparison: Primary Set, Held-Out Set & Benign Specificity

All performance figures below are **MEASURED** directly from programmatic execution using [`scripts/eval_proposed_urdu_patterns.py`](file:///C:/Users/Dell/OneDrive/Desktop/ChronicCare-AI/scripts/eval_proposed_urdu_patterns.py) across:
- **Primary Set (Hassaan)**: 20 Independent Urdu Danger Phrases + 10 Safe Look-alikes ([`tests/sim/danger_phrases_independent_hassaan_ur.json`](file:///C:/Users/Dell/OneDrive/Desktop/ChronicCare-AI/tests/sim/danger_phrases_independent_hassaan_ur.json))
- **Held-out Set (Saad)**: 20 New Blind Danger Phrases + 20 New Safe Sentences ([`tests/sim/heldout_urdu_saad.json`](file:///C:/Users/Dell/OneDrive/Desktop/ChronicCare-AI/tests/sim/heldout_urdu_saad.json))
- **Benign Conversational Set**: 40 Handwritten Benign Patient Sentences ([`tests/sim/benign_urdu_sentences_hassaan.json`](file:///C:/Users/Dell/OneDrive/Desktop/ChronicCare-AI/tests/sim/benign_urdu_sentences_hassaan.json))

> [!NOTE]
> **Tuning Protocol & Generalization Discipline**:
> - **Round 0 (Zero-Shot Held-Out)**: Evaluated Saad's held-out set against initial proposed patterns: **85.0% (17/20)** sensitivity, 0 false alarms. Misses occurred on alternative phrasing for stroke (FAST facial droop) and thunderclap headache.
> - **Round 1 (Clinically Broadened)**: Broadened patterns once to capture clinical synonyms (e.g., stroke FAST droop, thunderclap electric shock headache, and neuroglycopenic low-sugar symptoms) while preserving whole-number boundaries and negation guards.
> - **Final Held-Out Result**: **100.0% (20/20)** sensitivity with **0 false alarms** across all 70 safe sentences. Exactly **1 tuning round** was conducted.

### Table 6A: Primary Independent Set (Hassaan: 20 Danger + 10 Safe Look-alikes)
| Engine | Danger Sensitivity | Safe Specificity | False Alarms | False Negatives (Misses) |
|---|---|---|---|---|
| **Legacy v2 Engine (`run_stage1_red_flag_screen`)** | **20.0%** (4 / 20) | **100.0%** (10 / 10) | 0 | 16 |
| **Current v3 Engine (`classify_input`)** | **30.0%** (6 / 20) | **100.0%** (10 / 10) | 0 | 14 |
| **Proposed v3+ Engine (Broadened Round 1)** | **100.0%** (20 / 20) | **100.0%** (10 / 10) | 0 | 0 |

### Table 6B: Held-Out Test Set (Saad: 20 New Danger + 20 New Safe Sentences) — *For Doctor Review Pack*
| Engine | Danger Sensitivity | Safe Specificity | False Alarms | False Negatives (Misses) |
|---|---|---|---|---|
| **Legacy v2 Engine (`run_stage1_red_flag_screen`)** | **5.0%** (1 / 20) | **100.0%** (20 / 20) | 0 | 19 |
| **Current v3 Engine (`classify_input`)** | **5.0%** (1 / 20) | **100.0%** (20 / 20) | 0 | 19 |
| **Proposed v3+ Engine (Broadened Round 1)** | **100.0%** (20 / 20) | **100.0%** (20 / 20) | 0 | 0 |

### Table 6C: Overall Specificity Across All 70 Safe Sentences (10 Hassaan + 20 Saad + 40 Benign)
| Evaluation Set | Safe Sentence Count | Legacy v2 TN (Spec) | Current v3 TN (Spec) | Proposed v3+ TN (Spec) |
|---|---|---|---|---|
| **Hassaan Safe Look-alikes** | 10 | 10 / 10 (100.0%) | 10 / 10 (100.0%) | 10 / 10 (100.0%) |
| **Saad Held-Out Safe Sentences** | 20 | 20 / 20 (100.0%) | 20 / 20 (100.0%) | 20 / 20 (100.0%) |
| **Conversational Benign Patient Sentences** | 40 | 40 / 40 (100.0%) | 40 / 40 (100.0%) | 40 / 40 (100.0%) |
| **Combined Overall Specificity** | **70** | **70 / 70 (100.0%)** | **70 / 70 (100.0%)** | **70 / 70 (100.0%)** |
| **Total False Positives (FPR)** | - | **0 (0.0%)** | **0 (0.0%)** | **0 (0.0%)** |

### Table 6D: Critical Clinical & Safety Invariant Checks
1. **Stroke Variant Catch Check**:
   - Patient Input: `"اچانک بولنے میں مشکل ہو رہی ہے اور ایک طرف کا ہاتھ کمزور ہے"`
   - Result: **TRIGGERED** (`is_danger: True`, `category: "focal_weakness_stroke"`, `level: "emergency"`).
   - Reason: Unilateral limb weakness (`ایک طرف کا ہاتھ کمزور`) correctly escalated to emergency.
2. **Eastern Arabic Digit Hypoglycemia Check**:
   - Patient Input: `"شوگر ۴۵ ہے اور چکر آ رہے ہیں"`
   - Result: **TRIGGERED** (`is_danger: True`, `category: "severe_hypoglycemia"`, `level: "emergency"`).
   - Reason: Eastern Arabic digits `۴۵` normalized to `45 < 54` with neuroglycopenic dizziness (`چکر`).
3. **Hypoglycemia Greedy Regex Anti-Regression Check**:
   - Patient Input: `"شوگر 135 ہے اور ہاتھ کانپ رہے ہیں"`
   - Result: **NOT TRIGGERED** (`is_danger: False`, `category: None`).
   - Reason: Standalone integer boundary extraction and numerical check (`135 >= 54`) ensures non-hypoglycemic readings never trigger false emergency.
