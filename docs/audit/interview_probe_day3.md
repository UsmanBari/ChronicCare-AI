# ChronicCare AI — Interview Probe Audit Report (Day 1b: Step-Keyed Answers)

**Audit Execution:** Hermetic in-process TestClient evaluation
**Total Executions:** 34
- **Engine v2 Valid:** 15/17 (2 INVALID)
- **Engine v3 Valid:** 15/17 (2 INVALID)

## Summary Table

| Scenario | Engine | Group | Status | Questions Asked | Final Level | Emergency | Unmapped Answers | Notes |
|---|---|:---:|:---:|:---:|:---:|:---:|---|---|
| `norm_dm_en` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_dm_en` | **v3** | a | VALID | 5 | `review` | No | - | Valid normal completion |
| `norm_dm_ur` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_dm_ur` | **v3** | a | VALID | 5 | `review` | No | - | Valid normal completion |
| `norm_dm_roman_ur` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_dm_roman_ur` | **v3** | a | VALID | 5 | `review` | No | - | Valid normal completion |
| `norm_htn_en` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_htn_en` | **v3** | a | VALID | 5 | `review` | No | - | Valid normal completion |
| `norm_htn_ur` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_htn_ur` | **v3** | a | VALID | 5 | `review` | No | - | Valid normal completion |
| `norm_htn_roman_ur` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_htn_roman_ur` | **v3** | a | VALID | 5 | `review` | No | - | Valid normal completion |
| `norm_both_en` | **v2** | a | VALID | 9 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_both_en` | **v3** | a | VALID | 6 | `review` | No | - | Valid normal completion |
| `norm_both_ur` | **v2** | a | VALID | 9 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_both_ur` | **v3** | a | VALID | 6 | `review` | No | - | Valid normal completion |
| `norm_both_roman_ur` | **v2** | a | VALID | 9 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_both_roman_ur` | **v3** | a | VALID | 6 | `review` | No | - | Valid normal completion |
| `dual_diagnosis_order` | **v2** | b | VALID | 9 | `review` | No | summary_confirmation | Valid normal completion |
| `dual_diagnosis_order` | **v3** | b | VALID | 6 | `review` | No | - | Valid normal completion |
| `fasting_roza_roman_ur` | **v2** | g | **INVALID** | 6 | `review` | No | glucose_context, is_fasting_today, summary_confirmation | INVALID: must_deliver ['is_fasting_today'] not delivered via step_map |
| `fasting_roza_roman_ur` | **v3** | g | **INVALID** | 5 | `review` | No | glucose_context, is_fasting_today | INVALID: must_deliver ['is_fasting_today'] not delivered via step_map |
| `fasting_yes_en` | **v2** | g | **INVALID** | 6 | `review` | No | glucose_context, is_fasting_today, summary_confirmation | INVALID: must_deliver ['is_fasting_today'] not delivered via step_map |
| `fasting_yes_en` | **v3** | g | **INVALID** | 5 | `review` | No | glucose_context, is_fasting_today | INVALID: must_deliver ['is_fasting_today'] not delivered via step_map |
| `sick_day_roman_ur` | **v2** | g | VALID | 9 | `review` | No | sick_day_flags, sick_vomiting_diarrhea, summary_confirmation | Valid normal completion |
| `sick_day_roman_ur` | **v3** | g | VALID | 11 | `review` | No | sick_day_flags, sick_vomiting_diarrhea | Valid normal completion |
| `sick_day_en` | **v2** | g | VALID | 9 | `review` | No | sick_day_flags, sick_vomiting_diarrhea, summary_confirmation | Valid normal completion |
| `sick_day_en` | **v3** | g | VALID | 11 | `review` | No | sick_day_flags, sick_vomiting_diarrhea | Valid normal completion |
| `caregiver_en` | **v2** | h | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `caregiver_en` | **v3** | h | VALID | 4 | `routine` | No | glucose_reading, summary_confirmation | Valid normal completion |
| `caregiver_roman_ur` | **v2** | h | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `caregiver_roman_ur` | **v3** | h | VALID | 5 | `review` | No | - | Valid normal completion |
| `caregiver_trap_non_caregiver` | **v2** | h | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `caregiver_trap_non_caregiver` | **v3** | h | VALID | 5 | `review` | No | - | Valid normal completion |

---

## Detailed Scenario Audits

### Scenario: `norm_dm_en` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling fine | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | no | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `norm_dm_en` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling fine | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `norm_dm_ur` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | ٹھیک ہوں | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | نہیں | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | نہیں | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | کچھ نہیں | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `norm_dm_ur` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | آج آپ کیسا محسوس کر رہے ہیں؟ کیا آپ کوئی علامت بتانا چاہتے ہیں؟ | ٹھیک ہوں | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | کیا آپ نے آج شوگر چیک کی ہے؟ اگر ہاں، تو کیا ریڈنگ تھی؟ | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | کیا یہ ریڈنگ نہار منہ تھی، کھانے سے پہلے، کھانے کے بعد، یا رات سونے سے پہلے؟ | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | کیا آپ کو حال ہی میں پیاس زیادہ لگنا، بار بار پیشاب آنا، غیر معمولی تھکاوٹ، یا دھندلا نظر آنا محسوس ہوا ہے؟ | نہیں | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `summary_confirmation` | ہم نے آج یہ معلومات درج کی ہیں: - شوگر: 120 mg/dL - بلڈ پریشر: درج نہیں کیا گیا - علامات: کوئی نہیں - ادویات: درج نہیں کیا سب کچھ ٹھیک ہے؟ | yes | `step_map` | تصدیق کریں, تبدیل کرنا ہے | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `norm_dm_roman_ur` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | theek hoon | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | nahi | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | nahi | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | koi nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `norm_dm_roman_ur` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | theek hoon | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Kya aap ko haal hi mein pyas ziada lagna, bar bar peshab aana, ghair mamooli thakawat, ya dhundla nazar aana mehsoos hua hai? | nahi | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 120 mg/dL - Blood Pressure: Darj nahi kiya gaya - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm karein, Tabdeel karna hai | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `norm_htn_en` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling fine | `step_map` |  |  | - |
| 2 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  |  | - |
| 3 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, dizziness when standing, or palpitations? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Did you take your blood pressure medication today? | no | `kind_default` |  |  | - |
| 5 | `lifestyle` | How has your sodium intake, sleep, or stress been recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `norm_htn_en` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling fine | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  | Your blood pressure numbers tell your care team whether your treatment is keeping you protected. | - |
| 3 | `bp_technique` | Before measuring, did you rest quietly for 5 minutes with your back supported and arm resting on a table? | no | `kind_default` | yes, no | Resting quietly before measuring gives a much more accurate blood pressure reading. | - |
| 4 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, or dizziness when standing up? | no | `kind_default` | yes, no | Symptoms like severe headaches or breathlessness help identify if high blood pressure needs prompt attention. | - |
| 5 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: Not provided - Blood Pressure: 120/80 mmHg - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `norm_htn_ur` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | ٹھیک ہوں | `step_map` |  |  | - |
| 2 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  |  | - |
| 3 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, dizziness when standing, or palpitations? | نہیں | `kind_default` |  |  | - |
| 4 | `adherence` | Did you take your blood pressure medication today? | نہیں | `kind_default` |  |  | - |
| 5 | `lifestyle` | How has your sodium intake, sleep, or stress been recently? | کچھ نہیں | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `norm_htn_ur` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | آج آپ کیسا محسوس کر رہے ہیں؟ کیا آپ کوئی علامت بتانا چاہتے ہیں؟ | ٹھیک ہوں | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `bp_reading` | کیا آپ نے آج اپنا بلڈ پریشر چیک کیا ہے؟ اگر ہاں، تو کیا ریڈنگ تھی (مثلاً 130/85)؟ | 120/80 | `step_map` |  | Your blood pressure numbers tell your care team whether your treatment is keeping you protected. | - |
| 3 | `bp_technique` | کیا بلڈ پریشر چیک کرنے سے پہلے آپ نے 5 منٹ پرسکون بیٹھ کر آرام کیا تھا اور کمر اور بازو کو سہارا دیا تھا؟ | نہیں | `kind_default` | yes, no | Resting quietly before measuring gives a much more accurate blood pressure reading. | - |
| 4 | `associated_symptoms` | کیا آپ کو شدید سر درد، سانس پھولنا، ٹخنوں پر سوجن، یا کھڑے ہونے پر چکر آنا محسوس ہو رہا ہے؟ | نہیں | `kind_default` | yes, no | Symptoms like severe headaches or breathlessness help identify if high blood pressure needs prompt attention. | - |
| 5 | `summary_confirmation` | ہم نے آج یہ معلومات درج کی ہیں: - شوگر: درج نہیں کی گئی - بلڈ پریشر: 120/80 mmHg - علامات: کوئی نہیں - ادویات: درج نہیں کیا سب کچھ ٹھیک ہے؟ | yes | `step_map` | تصدیق کریں, تبدیل کرنا ہے | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `norm_htn_roman_ur` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | theek hoon | `step_map` |  |  | - |
| 2 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  |  | - |
| 3 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, dizziness when standing, or palpitations? | nahi | `kind_default` |  |  | - |
| 4 | `adherence` | Did you take your blood pressure medication today? | nahi | `kind_default` |  |  | - |
| 5 | `lifestyle` | How has your sodium intake, sleep, or stress been recently? | koi nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `norm_htn_roman_ur` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | theek hoon | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `bp_reading` | Kya aap ne aaj apna blood pressure check kiya hai? Agar haan, toh kya reading thi (maslan 130/85)? | 120/80 | `step_map` |  | Your blood pressure numbers tell your care team whether your treatment is keeping you protected. | - |
| 3 | `bp_technique` | Kya BP check karne se pehle aap ne 5 minute pursukoon baith kar aaram kiya tha aur kamar aur baazu ko sahara diya tha? | nahi | `kind_default` | yes, no | Resting quietly before measuring gives a much more accurate blood pressure reading. | - |
| 4 | `associated_symptoms` | Kya aap ko shadeed sar dard, saans phoolna, takhno par sojan, ya kharay hone par chakkar aana mehsoos ho raha hai? | nahi | `kind_default` | yes, no | Symptoms like severe headaches or breathlessness help identify if high blood pressure needs prompt attention. | - |
| 5 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: Darj nahi ki gayi - Blood Pressure: 120/80 mmHg - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm karein, Tabdeel karna hai | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `norm_both_en` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading', 'bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling fine | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | no | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | - |
| 6 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  |  | - |
| 7 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, dizziness when standing, or palpitations? | no | `kind_default` |  |  | - |
| 8 | `adherence` | Did you take your blood pressure medication today? | no | `kind_default` |  |  | - |
| 9 | `lifestyle` | How has your sodium intake, sleep, or stress been recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient); None (conf: Medium, by: patient)

---

### Scenario: `norm_both_en` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading', 'bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling fine | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  | Your blood pressure numbers tell your care team whether your treatment is keeping you protected. | - |
| 4 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 5 | `bp_technique` | Before measuring, did you rest quietly for 5 minutes with your back supported and arm resting on a table? | no | `kind_default` | yes, no | Resting quietly before measuring gives a much more accurate blood pressure reading. | - |
| 6 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: 120/80 mmHg - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient); None (conf: High, by: patient)

---

### Scenario: `norm_both_ur` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading', 'bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | ٹھیک ہوں | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | نہیں | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | نہیں | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | کچھ نہیں | `kind_default` |  |  | - |
| 6 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  |  | - |
| 7 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, dizziness when standing, or palpitations? | نہیں | `kind_default` |  |  | - |
| 8 | `adherence` | Did you take your blood pressure medication today? | نہیں | `kind_default` |  |  | - |
| 9 | `lifestyle` | How has your sodium intake, sleep, or stress been recently? | کچھ نہیں | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient); None (conf: Medium, by: patient)

---

### Scenario: `norm_both_ur` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading', 'bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | آج آپ کیسا محسوس کر رہے ہیں؟ کیا آپ کوئی علامت بتانا چاہتے ہیں؟ | ٹھیک ہوں | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | کیا آپ نے آج شوگر چیک کی ہے؟ اگر ہاں، تو کیا ریڈنگ تھی؟ | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `bp_reading` | کیا آپ نے آج اپنا بلڈ پریشر چیک کیا ہے؟ اگر ہاں، تو کیا ریڈنگ تھی (مثلاً 130/85)؟ | 120/80 | `step_map` |  | Your blood pressure numbers tell your care team whether your treatment is keeping you protected. | - |
| 4 | `glucose_context` | کیا یہ ریڈنگ نہار منہ تھی، کھانے سے پہلے، کھانے کے بعد، یا رات سونے سے پہلے؟ | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 5 | `bp_technique` | کیا بلڈ پریشر چیک کرنے سے پہلے آپ نے 5 منٹ پرسکون بیٹھ کر آرام کیا تھا اور کمر اور بازو کو سہارا دیا تھا؟ | نہیں | `kind_default` | yes, no | Resting quietly before measuring gives a much more accurate blood pressure reading. | - |
| 6 | `summary_confirmation` | ہم نے آج یہ معلومات درج کی ہیں: - شوگر: 120 mg/dL - بلڈ پریشر: 120/80 mmHg - علامات: کوئی نہیں - ادویات: درج نہیں کیا سب کچھ ٹھیک ہے؟ | yes | `step_map` | تصدیق کریں, تبدیل کرنا ہے | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient); None (conf: High, by: patient)

---

### Scenario: `norm_both_roman_ur` (Engine: V2) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading', 'bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | theek hoon | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | nahi | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | nahi | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | koi nahi | `kind_default` |  |  | - |
| 6 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  |  | - |
| 7 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, dizziness when standing, or palpitations? | nahi | `kind_default` |  |  | - |
| 8 | `adherence` | Did you take your blood pressure medication today? | nahi | `kind_default` |  |  | - |
| 9 | `lifestyle` | How has your sodium intake, sleep, or stress been recently? | koi nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient); None (conf: Medium, by: patient)

---

### Scenario: `norm_both_roman_ur` (Engine: V3) — Status: VALID

- **Group:** a
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading', 'bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | theek hoon | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `bp_reading` | Kya aap ne aaj apna blood pressure check kiya hai? Agar haan, toh kya reading thi (maslan 130/85)? | 120/80 | `step_map` |  | Your blood pressure numbers tell your care team whether your treatment is keeping you protected. | - |
| 4 | `glucose_context` | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 5 | `bp_technique` | Kya BP check karne se pehle aap ne 5 minute pursukoon baith kar aaram kiya tha aur kamar aur baazu ko sahara diya tha? | nahi | `kind_default` | yes, no | Resting quietly before measuring gives a much more accurate blood pressure reading. | - |
| 6 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 120 mg/dL - Blood Pressure: 120/80 mmHg - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm karein, Tabdeel karna hai | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient); None (conf: High, by: patient)

---

### Scenario: `dual_diagnosis_order` (Engine: V2) — Status: VALID

- **Group:** b
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading', 'bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | no | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | - |
| 6 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  |  | - |
| 7 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, dizziness when standing, or palpitations? | no | `kind_default` |  |  | - |
| 8 | `adherence` | Did you take your blood pressure medication today? | no | `kind_default` |  |  | - |
| 9 | `lifestyle` | How has your sodium intake, sleep, or stress been recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient); None (conf: Medium, by: patient)

---

### Scenario: `dual_diagnosis_order` (Engine: V3) — Status: VALID

- **Group:** b
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading', 'bp_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling okay | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `bp_reading` | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | 120/80 | `step_map` |  | Your blood pressure numbers tell your care team whether your treatment is keeping you protected. | - |
| 4 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 5 | `bp_technique` | Before measuring, did you rest quietly for 5 minutes with your back supported and arm resting on a table? | no | `kind_default` | yes, no | Resting quietly before measuring gives a much more accurate blood pressure reading. | - |
| 6 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: 120/80 mmHg - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient); None (conf: High, by: patient)

---

### Scenario: `fasting_roza_roman_ur` (Engine: V2) — Status: INVALID

- **Group:** g
- **Valid Delivery:** `False` (must_deliver: ['is_fasting_today'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['glucose_context', 'is_fasting_today', 'summary_confirmation']
- **Notes:** INVALID: must_deliver ['is_fasting_today'] not delivered via step_map

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | theek hoon | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 110 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | nahi | `kind_default` |  |  | - |
| 4 | `hypoglycemia_symptoms` | Any shakiness, sweating, or confusion that improved after eating? | nahi | `kind_default` |  |  | - |
| 5 | `adherence` | Have you taken your diabetes medication as prescribed today? | nahi | `kind_default` |  |  | - |
| 6 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | koi nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `fasting_roza_roman_ur` (Engine: V3) — Status: INVALID

- **Group:** g
- **Valid Delivery:** `False` (must_deliver: ['is_fasting_today'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['glucose_context', 'is_fasting_today']
- **Notes:** INVALID: must_deliver ['is_fasting_today'] not delivered via step_map

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `hypo_events_past_week` | Pichle 7 dino mein, kya aap ki sugar kam (low) hui thi (jaise kapkapahat, thanday paseenay, shadeed bhook, ya ghashi)? | nahi | `kind_default` | yes, no | People on insulin or sulfonylureas have a higher risk of low blood sugar, which needs safe prevention. | - |
| 2 | `hypo_symptoms_acute` | Kya aap is waqt kapkapahat, paseena, chakkar, ya uljhan mehsoos kar rahe hain jo meetha khanay se theek hoti ho? | nahi | `kind_default` | yes, no | To check if you are currently feeling symptoms of a low blood sugar. | - |
| 3 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | theek hoon | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 4 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 110 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 5 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 110 mg/dL - Blood Pressure: Darj nahi kiya gaya - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm karein, Tabdeel karna hai | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `fasting_yes_en` (Engine: V2) — Status: INVALID

- **Group:** g
- **Valid Delivery:** `False` (must_deliver: ['is_fasting_today'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['glucose_context', 'is_fasting_today', 'summary_confirmation']
- **Notes:** INVALID: must_deliver ['is_fasting_today'] not delivered via step_map

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling fine | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 110 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `hypoglycemia_symptoms` | Any shakiness, sweating, or confusion that improved after eating? | no | `kind_default` |  |  | - |
| 5 | `adherence` | Have you taken your diabetes medication as prescribed today? | no | `kind_default` |  |  | - |
| 6 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `fasting_yes_en` (Engine: V3) — Status: INVALID

- **Group:** g
- **Valid Delivery:** `False` (must_deliver: ['is_fasting_today'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['glucose_context', 'is_fasting_today']
- **Notes:** INVALID: must_deliver ['is_fasting_today'] not delivered via step_map

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `hypo_events_past_week` | In the past 7 days, have you had any low blood sugar episodes (like sudden shakiness, cold sweat, hunger, or feeling faint)? | no | `kind_default` | yes, no | People on insulin or sulfonylureas have a higher risk of low blood sugar, which needs safe prevention. | - |
| 2 | `hypo_symptoms_acute` | Are you currently feeling any shakiness, sweating, dizziness, or confusion that gets better when you eat something sweet? | no | `kind_default` | yes, no | To check if you are currently feeling symptoms of a low blood sugar. | - |
| 3 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling fine | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 4 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 110 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 5 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 110 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `sick_day_roman_ur` (Engine: V2) — Status: VALID

- **Group:** g
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['sick_day_flags', 'sick_vomiting_diarrhea', 'summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | bemaar hoon | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 260 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | nahi | `kind_default` |  |  | - |
| 4 | `hypoglycemia_symptoms` | Any shakiness, sweating, or confusion that improved after eating? | nahi | `kind_default` |  |  | - |
| 5 | `adherence` | Have you taken your diabetes medication as prescribed today? | nahi | `kind_default` |  |  | - |
| 6 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | koi nahi | `kind_default` |  |  | - |
| 7 | `triage:glucose_high:0:0` | Do you have nausea or vomiting, stomach pain, fast or deep breathing, breath that smells fruity, or feel very drowsy? Answer yes or no. | nahi | `kind_default` |  |  | - |
| 8 | `triage:glucose_high:1:0` | Are you very thirsty and passing urine much more than usual? Answer yes or no. | no | `protocol_default` |  |  | - |
| 9 | `triage:glucose_high:2:0` | Did you eat a large meal just before, miss your insulin or diabetes medicine, or have an illness or infection? Answer yes or no, and tell me which. | nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: Glucose is high.
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `sick_day_roman_ur` (Engine: V3) — Status: VALID

- **Group:** g
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['sick_day_flags', 'sick_vomiting_diarrhea']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `hypo_events_past_week` | Pichle 7 dino mein, kya aap ki sugar kam (low) hui thi (jaise kapkapahat, thanday paseenay, shadeed bhook, ya ghashi)? | nahi | `kind_default` | yes, no | People on insulin or sulfonylureas have a higher risk of low blood sugar, which needs safe prevention. | - |
| 2 | `hypo_symptoms_acute` | Kya aap is waqt kapkapahat, paseena, chakkar, ya uljhan mehsoos kar rahe hain jo meetha khanay se theek hoti ho? | nahi | `kind_default` | yes, no | To check if you are currently feeling symptoms of a low blood sugar. | - |
| 3 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | bemaar hoon | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 4 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 260 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 5 | `glucose_context` | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 6 | `hyperglycemia_symptoms` | Kya aap ko haal hi mein pyas ziada lagna, bar bar peshab aana, ghair mamooli thakawat, ya dhundla nazar aana mehsoos hua hai? | nahi | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 7 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 260 mg/dL - Blood Pressure: Darj nahi kiya gaya - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm karein, Tabdeel karna hai | To confirm we noted your answers correctly before saving. | - |
| 8 | `triage:glucose_high:0:0` | Do you have nausea or vomiting, stomach pain, fast or deep breathing, breath that smells fruity, or feel very drowsy? Answer yes or no. | Confirm karein | `kind_default` | Confirm karein, Tabdeel karna hai | To confirm we noted your answers correctly before saving. | - |
| 9 | `triage:glucose_high:0:1` | Sorry, I didn't catch that. Do you have nausea or vomiting, stomach pain, fast or deep breathing, breath that smells fruity, or feel very drowsy? Answer yes or no. | nahi | `kind_default` |  |  | - |
| 10 | `triage:glucose_high:1:0` | Are you very thirsty and passing urine much more than usual? Answer yes or no. | no | `protocol_default` |  |  | - |
| 11 | `triage:glucose_high:2:0` | Did you eat a large meal just before, miss your insulin or diabetes medicine, or have an illness or infection? Answer yes or no, and tell me which. | nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: Glucose is high.
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `sick_day_en` (Engine: V2) — Status: VALID

- **Group:** g
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['sick_day_flags', 'sick_vomiting_diarrhea', 'summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling unwell | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 260 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `hypoglycemia_symptoms` | Any shakiness, sweating, or confusion that improved after eating? | no | `kind_default` |  |  | - |
| 5 | `adherence` | Have you taken your diabetes medication as prescribed today? | no | `kind_default` |  |  | - |
| 6 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | - |
| 7 | `triage:glucose_high:0:0` | Do you have nausea or vomiting, stomach pain, fast or deep breathing, breath that smells fruity, or feel very drowsy? Answer yes or no. | no | `kind_default` |  |  | - |
| 8 | `triage:glucose_high:1:0` | Are you very thirsty and passing urine much more than usual? Answer yes or no. | no | `protocol_default` |  |  | - |
| 9 | `triage:glucose_high:2:0` | Did you eat a large meal just before, miss your insulin or diabetes medicine, or have an illness or infection? Answer yes or no, and tell me which. | no | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: Glucose is high.
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `sick_day_en` (Engine: V3) — Status: VALID

- **Group:** g
- **Valid Delivery:** `True` (must_deliver: ['glucose_reading'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['sick_day_flags', 'sick_vomiting_diarrhea']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `hypo_events_past_week` | In the past 7 days, have you had any low blood sugar episodes (like sudden shakiness, cold sweat, hunger, or feeling faint)? | no | `kind_default` | yes, no | People on insulin or sulfonylureas have a higher risk of low blood sugar, which needs safe prevention. | - |
| 2 | `hypo_symptoms_acute` | Are you currently feeling any shakiness, sweating, dizziness, or confusion that gets better when you eat something sweet? | no | `kind_default` | yes, no | To check if you are currently feeling symptoms of a low blood sugar. | - |
| 3 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling unwell | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 4 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 260 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 5 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 6 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 7 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 260 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | - |
| 8 | `triage:glucose_high:0:0` | Do you have nausea or vomiting, stomach pain, fast or deep breathing, breath that smells fruity, or feel very drowsy? Answer yes or no. | Confirm and submit | `kind_default` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | - |
| 9 | `triage:glucose_high:0:1` | Sorry, I didn't catch that. Do you have nausea or vomiting, stomach pain, fast or deep breathing, breath that smells fruity, or feel very drowsy? Answer yes or no. | no | `kind_default` |  |  | - |
| 10 | `triage:glucose_high:1:0` | Are you very thirsty and passing urine much more than usual? Answer yes or no. | no | `protocol_default` |  |  | - |
| 11 | `triage:glucose_high:2:0` | Did you eat a large meal just before, miss your insulin or diabetes medicine, or have an illness or infection? Answer yes or no, and tell me which. | no | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: Glucose is high.
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `caregiver_en` (Engine: V2) — Status: VALID

- **Group:** h
- **Valid Delivery:** `True` (must_deliver: ['greeting'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | I am answering for my mother who has diabetes | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | no | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `caregiver_en` (Engine: V3) — Status: VALID

- **Group:** h
- **Valid Delivery:** `True` (must_deliver: ['greeting'])
- **Final Level:** `routine`
- **Emergency:** False
- **Unmapped Answers:** ['glucose_reading', 'summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | I am answering for my mother who has diabetes | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | Note: Thank you for helping with this check-in. We have noted that a family member or caregiver is assisting today. |
| 2 | `greeting` | How are you feeling today? Any symptoms you would like to report? | I am answering for my mother who has diabetes | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | Note: Thank you for helping with this check-in. We have noted that a family member or caregiver is assisting today. |
| 3 | `greeting` | How are you feeling today? Any symptoms you would like to report? | I am answering for my mother who has diabetes | `step_map` | Continue check-in, Need urgent help, Finish later | To check how you are feeling generally today before looking at your numbers. | Note: Thank you for helping with this check-in. We have noted that a family member or caregiver is assisting today. |
| 4 | `greeting` | How are you feeling today? Any symptoms you would like to report? | I am answering for my mother who has diabetes | `step_map` | Continue check-in, Need urgent help, Finish later | To check how you are feeling generally today before looking at your numbers. | ✅ COMPLETE; Note: We understand you may need to step away. We have saved your responses so far for your care team. |

**Completion Result Details:**
- Requires Review: `False` | Max Severity: `none`
- Reasons: None
- Factors: None
- Intakes: None (conf: Low, by: caregiver)

---

### Scenario: `caregiver_roman_ur` (Engine: V2) — Status: VALID

- **Group:** h
- **Valid Delivery:** `True` (must_deliver: ['greeting'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | Main apni ammi ki taraf se baat kar raha hoon | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | nahi | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | nahi | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | koi nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `caregiver_roman_ur` (Engine: V3) — Status: VALID

- **Group:** h
- **Valid Delivery:** `True` (must_deliver: ['greeting'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | Main apni ammi ki taraf se baat kar raha hoon | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Kya aap ko haal hi mein pyas ziada lagna, bar bar peshab aana, ghair mamooli thakawat, ya dhundla nazar aana mehsoos hua hai? | nahi | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 120 mg/dL - Blood Pressure: Darj nahi kiya gaya - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm karein, Tabdeel karna hai | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `caregiver_trap_non_caregiver` (Engine: V2) — Status: VALID

- **Group:** h
- **Valid Delivery:** `True` (must_deliver: ['greeting'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | My mother has diabetes but I am taking my own reading today | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | no | `kind_default` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `caregiver_trap_non_caregiver` (Engine: V3) — Status: VALID

- **Group:** h
- **Valid Delivery:** `True` (must_deliver: ['greeting'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | My mother has diabetes but I am taking my own reading today | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---


## Dual-Diagnosis Step Order Comparison (Day 2 vs Day 3)

Under Day 3 Rule R2, both readings (`glucose_reading` and `bp_reading`) are scheduled *before* any symptom questions.

Under Day 3 Rule R3, shared questions (e.g. medication adherence) are asked only once and de-duplicated.

### Scenario: `norm_both_en` (Engine: V3)

- **Day 2 Step Sequence (6 steps):** `greeting -> glucose_reading -> glucose_context -> bp_reading -> bp_technique -> summary_confirmation`
- **Day 3 Step Sequence (6 steps):** `greeting -> glucose_reading -> bp_reading -> glucose_context -> bp_technique -> summary_confirmation`
- **Key Ordering Transformation:** In Day 3, glucose and BP readings both complete upfront (`greeting` -> `glucose_reading` -> `glucose_context` -> `bp_reading`), before any symptom inquiries (`hyperglycemia_symptoms`). Adherence is consolidated to 1 question.

### Scenario: `norm_both_ur` (Engine: V3)

- **Day 2 Step Sequence (6 steps):** `greeting -> glucose_reading -> glucose_context -> bp_reading -> bp_technique -> summary_confirmation`
- **Day 3 Step Sequence (6 steps):** `greeting -> glucose_reading -> bp_reading -> glucose_context -> bp_technique -> summary_confirmation`
- **Key Ordering Transformation:** In Day 3, glucose and BP readings both complete upfront (`greeting` -> `glucose_reading` -> `glucose_context` -> `bp_reading`), before any symptom inquiries (`hyperglycemia_symptoms`). Adherence is consolidated to 1 question.

### Scenario: `norm_both_roman_ur` (Engine: V3)

- **Day 2 Step Sequence (6 steps):** `greeting -> glucose_reading -> glucose_context -> bp_reading -> bp_technique -> summary_confirmation`
- **Day 3 Step Sequence (6 steps):** `greeting -> glucose_reading -> bp_reading -> glucose_context -> bp_technique -> summary_confirmation`
- **Key Ordering Transformation:** In Day 3, glucose and BP readings both complete upfront (`greeting` -> `glucose_reading` -> `glucose_context` -> `bp_reading`), before any symptom inquiries (`hyperglycemia_symptoms`). Adherence is consolidated to 1 question.

