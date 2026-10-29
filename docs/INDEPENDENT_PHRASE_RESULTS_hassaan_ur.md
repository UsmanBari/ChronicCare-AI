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

## 3. False Positives (Safe Look-alikes Escalated)

*Zero False Positives encountered.*

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
