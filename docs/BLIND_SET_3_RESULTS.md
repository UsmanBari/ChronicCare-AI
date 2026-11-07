# Blind Danger Phrase Set #3 Evaluation Results — Muhammad Saad

**Date:** 7 November 2026 (Iteration 3 Day 7)  
**Author:** Muhammad Saad  
**Branch:** `test/i3-blind3-release-check`  
**Evaluation Script:** `scripts/eval_all_phrase_sets.py`  
**Dataset:** `tests/sim/blind_set_3_saad.json` (50 items: 25 danger, 25 tricky safe; balanced across English, Roman Urdu, and Urdu script)

---

## 1. Provenance & Blind Discipline Verification

Per protocol (Day 7 Rule A1 & A2), Blind Set #3 was designed and held outside the repository, copied into `tests/sim/blind_set_3_saad.json`, and committed to git **BEFORE** the evaluation harness was executed. Zero changes were made to any detector, pattern, or prototype after seeing the results.

### Git Log Proof (Committed Prior to Execution)
```text
commit 0fa5e5ed84e5171472092034a08bc697b95eb060
Author: Muhammad Saad <muhammad.saadd06@gmail.com>
Date:   Sat Nov 7 18:29:43 2026 +0500

    test(sim): add blind danger phrase set 3 (saad)

 tests/sim/blind_set_3_saad.json | 352 ++++++++++++++++++++++++++++++++++++++++
 1 file changed, 352 insertions(+)
```

---

## 2. Benchmark Results Across All Evaluated Engines

The evaluation harness was executed exactly **ONCE** in held-out counts-only mode with verbose failure capture:
```powershell
python scripts/eval_all_phrase_sets.py --heldout-counts-only --verbose-misses
```

### Table 1: Blind Set #3 Performance Matrix (50 Phrases: 25 Danger, 25 Tricky Safe)

| Engine | Sensitivity (Danger Caught / Total) | False Alarm Rate (False Alarms / Safe) | Specificity | Key Architecture |
|---|:---:|:---:|:---:|---|
| **v2 (Legacy Live Engine)** | 4 / 25 (**16.0%**) | 0 / 25 (**0.0%**) | **100.0%** | Exact substring match on `RED_FLAG_PATTERNS` |
| **v3 (Triage Slot Classifier)** | 7 / 25 (**28.0%**) | 0 / 25 (**0.0%**) | **100.0%** | Multilingual slot filling & regex dictionary |
| **WG_V1 (Danger Word Groups v1)** | 20 / 25 (**80.0%**) | 4 / 25 (**16.0%**) | **84.0%** | Usman's composable symptom word groups (PR #103) |
| **V2_PLUS_WG (Hybrid v2 + Word Groups)** | 20 / 25 (**80.0%**) | 4 / 25 (**16.0%**) | **84.0%** | Parallel union of v2 and Word Groups |
| **V3_PLUS_WG (Hybrid v3 + Word Groups)** | 20 / 25 (**80.0%**) | 4 / 25 (**16.0%**) | **84.0%** | Parallel union of v3 and Word Groups |
| **PROTOTYPE (Experimental Composable)** | 16 / 25 (**64.0%**) | 8 / 25 (**32.0%**) | **68.0%** | Prototype heuristic screen with negation window |

---

## 3. Detailed Missed Danger Phrases (False Negatives)

### 3.1 `v2` Missed Positives (21 / 25 Missed — 84.0% Miss Rate)
1. `"There is an unbearable heavy elephant sitting on my chest and radiating to my left jaw"`
2. `"My mother suddenly cannot speak properly and her right arm went completely limp"`
3. `"Throwing up dark red blood and severe stomach cramps since one hour"`
4. `"I have complete loss of vision in my right eye that started 10 minutes ago"`
5. `"Black sticky tarry stool and feeling faint whenever I sit up"`
6. `"Ammi ka chehra achanak aik taraf dhalak gaya hai aur bazu sunn ho gaya hai"`
7. `"Seenay mein intahai shadeed dabao aur jalan hai jo ultay bazu ki taraf ja rahi hai"`
8. `"Saans bilkul nahi aa rahi dam ghut raha hai foran madad chahiye"`
9. `"Abba achanak chakkar kha kar gir pare aur behosh ho gaye hain"`
10. `"Khoon ki ulti aayi hai shadeed aur pait mein sakht maror uth rahe hain"`
11. `"Zuban ladkhada rahi hai aur bol nahi pa rahe theek se achanak"`
12. `"Seene par shadeed bojh mehsoos ho raha hai aur paseenay chhoot rahe hain"`
13. `"Achanak se aik aankh se dikhna bilkul band ho gaya hai"`
14. `"Sans ruk ruk kar aa rahi hai aur gale mein phanda lag raha hai"`
15. `"سینے میں شدید درد اور دباؤ ہے جو بائیں کندھے اور جبڑے میں جا رہا ہے"`
16. `"سانس لینا انتہائی مشکل ہو گیا ہے اور دم گھٹ رہا ہے"`
17. `"والد صاحب کا اچانک چہرہ ٹیڑھا ہو گیا اور دایاں بازو کام نہیں کر رہا"`
18. `"خون کی قے آئی ہے بہت زیادہ مقدار میں اور چکر آ رہے ہیں"`
19. `"سینے پر ہاتھی جیسا بوجھ ہے اور ٹھنڈے پسینے آ رہے ہیں"`
20. `"زبان لڑکھڑا گئی ہے اور ایک طرف کا جسم بالکل سن ہو گیا ہے"`
21. `"کالا تارکول جیسا پاخانہ آ رہا ہے اور شدید کمزوری سے کھڑے نہیں ہو پا رہے"`

### 3.2 `v3` Missed Positives (18 / 25 Missed — 72.0% Miss Rate)
1. `"There is an unbearable heavy elephant sitting on my chest and radiating to my left jaw"`
2. `"My mother suddenly cannot speak properly and her right arm went completely limp"`
3. `"Throwing up dark red blood and severe stomach cramps since one hour"`
4. `"I have complete loss of vision in my right eye that started 10 minutes ago"`
5. `"Black sticky tarry stool and feeling faint whenever I sit up"`
6. `"Ammi ka chehra achanak aik taraf dhalak gaya hai aur bazu sunn ho gaya hai"`
7. `"Seenay mein intahai shadeed dabao aur jalan hai jo ultay bazu ki taraf ja rahi hai"`
8. `"Saans bilkul nahi aa rahi dam ghut raha hai foran madad chahiye"`
9. `"Abba achanak chakkar kha kar gir pare aur behosh ho gaye hain"`
10. `"Khoon ki ulti aayi hai shadeed aur pait mein sakht maror uth rahe hain"`
11. `"Seene par shadeed bojh mehsoos ho raha hai aur paseenay chhoot rahe hain"`
12. `"Achanak se aik aankh se dikhna bilkul band ho gaya hai"`
13. `"Sans ruk ruk kar aa rahi hai aur gale mein phanda lag raha hai"`
14. `"والد صاحب کا اچانک چہرہ ٹیڑھا ہو گیا اور دایاں بازو کام نہیں کر رہا"`
15. `"خون کی قے آئی ہے بہت زیادہ مقدار میں اور چکر آ رہے ہیں"`
16. `"سینے پر ہاتھی جیسا بوجھ ہے اور ٹھنڈے پسینے آ رہے ہیں"`
17. `"زبان لڑکھڑا گئی ہے اور ایک طرف کا جسم بالکل سن ہو گیا ہے"`
18. `"کالا تارکول جیسا پاخانہ آ رہا ہے اور شدید کمزوری سے کھڑے نہیں ہو پا رہے"`

### 3.3 `WG_V1` Missed Positives (5 / 25 Missed — 20.0% Miss Rate)
1. `"I have complete loss of vision in my right eye that started 10 minutes ago"` (Awaiting acute monocular vision loss word group)
2. `"Black sticky tarry stool and feeling faint whenever I sit up"` (Awaiting melena / lower GI bleed word group)
3. `"Saans bilkul nahi aa rahi dam ghut raha hai foran madad chahiye"` (Roman Urdu breathing idiom missing explicit respiratory anchor)
4. `"Achanak se aik aankh se dikhna bilkul band ho gaya hai"` (Vernacular Roman Urdu vision loss)
5. `"خون کی قے آئی ہے بہت زیادہ مقدار میں اور چکر آ رہے ہیں"` (Urdu script hematemesis variant "خون کی قے" vs "خون کی الٹی")

### 3.4 `PROTOTYPE` Missed Positives (9 / 25 Missed — 36.0% Miss Rate)
1. `"My mother suddenly cannot speak properly and her right arm went completely limp"`
2. `"Throwing up dark red blood and severe stomach cramps since one hour"`
3. `"I have complete loss of vision in my right eye that started 10 minutes ago"`
4. `"Black sticky tarry stool and feeling faint whenever I sit up"`
5. `"Saans bilkul nahi aa rahi dam ghut raha hai foran madad chahiye"`
6. `"Achanak se aik aankh se dikhna bilkul band ho gaya hai"`
7. `"والد صاحب کا اچانک چہرہ ٹیڑھا ہو گیا اور دایاں بازو کام نہیں کر رہا"`
8. `"خون کی قے آئی ہے بہت زیادہ مقدار میں اور چکر آ رہے ہیں"`
9. `"کالا تارکول جیسا پاخانہ آ رہا ہے اور شدید کمزوری سے کھڑے نہیں ہو پا رہے"`

---

## 4. Detailed False Alarms (False Positives)

### 4.1 `v2` and `v3` False Alarms
- **Zero false alarms (0 / 25, 0.0%)** — Both engines maintain 100% specificity by virtue of strictly rigid keyword matching.

### 4.2 `WG_V1`, `V2_PLUS_WG`, `V3_PLUS_WG` False Alarms (4 / 25 — 16.0%)
1. `"Chronic numbness in my toes on both feet for the past three years due to sugar"` — Triggered stroke/neurological weakness group on "numbness".
2. `"Dono paon ke talwe purani sugar ki wajah se pichle do saal se sunn rehte hain"` — Triggered neurological word group on "sunn".
3. `"کل بھاری سامان اٹھانے سے سینے کے پٹھوں میں ہلکا درد ہے چھونے سے"` — Triggered chest pain group on "سینے" + "درد".
4. `"دونوں پاؤں کی انگلیاں شوگر کی وجہ سے کافی عرصے سے سن رہتی ہیں"` — Triggered neurological group on "سن".

*Clinical Insight:* 3 out of the 4 false alarms are chronic bilateral diabetic peripheral neuropathy ("sunn" / "numbness in toes/feet for years"), which should be clinically distinguished from acute unilateral stroke/FAST deficits.

### 4.3 `PROTOTYPE` False Alarms (8 / 25 — 32.0%)
1. `"My father had a severe heart attack five years ago but he is healthy now"` (Past history leakage)
2. `"Wazan uthane se seenay ke pathon mein halka sa khichao aur dard hai dabane par"` (Musculoskeletal wall pain)
3. `"Tez mirch masalay khane ki wajah se seenay mein jalan ho rahi thi jo eno peene se theek ho gayi"` (Benign reflux)
4. `"Seenay mein koi dard ya dabao bilkul nahi hai alhamdulillah"` (Failed negation parsing)
5. `"Khoon ki ulti ya behoshi jaisi koi baat nahi hai bas halki si khansi hai"` (Compound negation leakage)
6. `"کل بھاری سامان اٹھانے سے سینے کے پٹھوں میں ہلکا درد ہے چھونے سے"` (Musculoskeletal wall pain)
7. `"کھانے کے بعد سینے میں تیزابیت اور جلن ہو رہی ہے"` (Heartburn/acid reflux)
8. `"سینے میں کوئی درد یا سانس کا مسئلہ نہیں ہے الحمدللہ"` (Failed Urdu negation parsing)

---

## 5. Conclusions & Clinical Recommendations

1. **Massive Sensitivity Leap with Word Groups:** Usman's `WG_V1` detector dramatically lifted emergency sensitivity on realistic conversational expressions from **16.0% (v2) and 28.0% (v3) up to 80.0%**.
2. **Clinical Trade-Off:** The 16.0% false alarm rate in `WG_V1` is concentrated in chronic diabetic neuropathy ("sunn" in feet/toes) and musculoskeletal wall soreness. Adding an exclusion for bilateral foot/toe neuropathy ("paon", "toes", "bilateral") will safely recover specificity without compromising unilateral stroke detection.
3. **Safety Protocol Adherence:** All numbers in this document are strictly measured from the single run of `scripts/eval_all_phrase_sets.py`. No code or regex was altered after evaluating this blind set.

