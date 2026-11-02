# ChronicCare AI — Interview Probe Audit Report (Day 1b: Step-Keyed Answers)

**Audit Execution:** Hermetic in-process TestClient evaluation
**Total Executions:** 36
- **Engine v2 Valid:** 18/18 (0 INVALID)
- **Engine v3 Valid:** 18/18 (0 INVALID)

## Summary Table

| Scenario | Engine | Group | Status | Questions Asked | Final Level | Emergency | Unmapped Answers | Notes |
|---|---|:---:|:---:|:---:|:---:|:---:|---|---|
| `norm_dm_en` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_dm_en` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `norm_dm_ur` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_dm_ur` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `norm_dm_roman_ur` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_dm_roman_ur` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `norm_htn_en` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_htn_en` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `norm_htn_ur` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_htn_ur` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `norm_htn_roman_ur` | **v2** | a | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_htn_roman_ur` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `norm_both_en` | **v2** | a | VALID | 9 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_both_en` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `norm_both_ur` | **v2** | a | VALID | 9 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_both_ur` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `norm_both_roman_ur` | **v2** | a | VALID | 9 | `review` | No | summary_confirmation | Valid normal completion |
| `norm_both_roman_ur` | **v3** | a | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_maybe` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_maybe` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_shayad` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_shayad` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_pata_nahi` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_pata_nahi` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_pata_nahi_ur` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_pata_nahi_ur` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_kal_tha` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_kal_tha` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_thumbs_up` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_thumbs_up` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_dots` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_dots` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_same_as_yesterday` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_same_as_yesterday` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |
| `unclear_ok` | **v2** | c | VALID | 5 | `review` | No | summary_confirmation | Valid normal completion |
| `unclear_ok` | **v3** | c | VALID | 9 | `review` | No | - | Valid normal completion |

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
| 5 | `foot_problems` | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | no | `kind_default` | yes, no | Catching sores, cuts, or numbness on feet early prevents serious complications. | - |
| 6 | `adherence_diabetes` | Have you taken your diabetes medications as prescribed today? | no | `kind_default` | yes, no | Knowing whether you took your medicine as prescribed helps your doctor interpret your sugar readings. | - |
| 7 | `missed_doses_reason_diabetes` | What made it difficult to take your diabetes medicine as prescribed today? | none | `kind_default` |  | Understanding why a dose was missed helps your team find practical solutions. | - |
| 8 | `lifestyle_diabetes` | Any changes in your meals, physical activity, or stress levels recently? | none | `kind_default` |  | Diet, activity, and stress directly influence your blood sugar. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Missed doses reported Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

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
| 1 | `greeting` | آج آپ کیسا محسوس کر رہے ہیں؟ کیا آپ کوئی علامت بتانا چاہتے ہیں؟ | ٹھیک ہوں | `step_map` |  | طبی سوالات شروع کرنے سے پہلے یہ جاننے کے لیے کہ عمومی طور پر آج آپ کی طبیعت کیسی ہے۔ | - |
| 2 | `glucose_reading` | کیا آپ نے آج شوگر چیک کی ہے؟ اگر ہاں، تو کیا ریڈنگ تھی؟ | 120 mg/dL | `step_map` |  | شوگر کی ریڈنگ سے آپ کے ڈاکٹر کو یہ جانچنے میں مدد ملتی ہے کہ شوگر قابو میں ہے یا نہیں۔ | - |
| 3 | `glucose_context` | کیا یہ ریڈنگ نہار منہ تھی، کھانے سے پہلے، کھانے کے بعد، یا رات سونے سے پہلے؟ | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | کھانے سے پہلے اور بعد میں شوگر کے اہداف مختلف ہوتے ہیں، وقت جاننے سے ریڈنگ کی صحیح سمجھ آتی ہے۔ | - |
| 4 | `hyperglycemia_symptoms` | کیا آپ کو حال ہی میں پیاس زیادہ لگنا، بار بار پیشاب آنا، غیر معمولی تھکاوٹ، یا دھندلا نظر آنا محسوس ہوا ہے؟ | نہیں | `kind_default` | yes, no | شوگر بڑھنے سے پیاس، بار بار پیشاب یا آنکھوں کے آگے دھندلا پن ہو سکتا ہے، اس سے ریڈنگ کو سمجھنے میں مدد ملتی ہے۔ | - |
| 5 | `foot_problems` | کیا آپ کے پاؤں پر کوئی نیا زخم، چھالا، درد، یا بے حسی (سن ہونا) ہے؟ | نہیں | `kind_default` | yes, no | پاؤں میں زخم، چھالے یا سن ہونے کی بروقت نشاندہی ذیابیطس کی پیچیدگیوں سے بچاتی ہے۔ | - |
| 6 | `adherence_diabetes` | کیا آپ نے آج اپنی شوگر کی دوائیاں ہدایت کے مطابق لی ہیں؟ | نہیں | `kind_default` | yes, no | یہ جاننا ضروری ہے کہ کیا آپ نے دوا باقاعدگی سے لی تاکہ ڈاکٹر شوگر کی ریڈنگ کا صحیح اندازہ لگا سکے۔ | - |
| 7 | `missed_doses_reason_diabetes` | آج شوگر کی دوا لینے میں کیا مشکل پیش آئی؟ | کچھ نہیں | `kind_default` |  | دوا چھوٹنے کی وجہ جاننے سے ڈاکٹر آپ کے روزمرہ کے معمول کے مطابق آسان حل تجویز کر سکتا ہے۔ | - |
| 8 | `lifestyle_diabetes` | کیا حالیہ دنوں میں آپ کے کھانے پینے، ورزش، یا ذہنی دباؤ میں کوئی تبدیلی آئی ہے؟ | کچھ نہیں | `kind_default` |  | خوراک، ورزش اور ذہنی تناؤ کا شوگر پر براہ راست اثر پڑتا ہے۔ | - |
| 9 | `summary_confirmation` | ہم نے آج یہ معلومات درج کی ہیں: - شوگر: 120 mg/dL - بلڈ پریشر: درج نہیں کیا گیا - علامات: کوئی نہیں - ادویات: خوراک چھوٹنے کی اطلاع کیا سب کچھ ٹھیک ہے؟ | yes | `step_map` | Confirm and submit, Need to change something | تاکہ محفوظ کرنے سے پہلے تصدیق ہو سکے کہ تمام معلومات درست لکھی گئی ہیں۔ | ✅ COMPLETE |

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
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | theek hoon | `step_map` |  | Tibbi sawalaat shuru karne se pehle yeh janne ke liye ke aam tor par aaj aap ki tabiyat kaisi hai. | - |
| 2 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 120 mg/dL | `step_map` |  | Sugar ki reading se aap ke doctor ko yeh dekhne mein madad milti hai ke sugar control mein hai ya nahi. | - |
| 3 | `glucose_context` | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Khanay se pehle aur baad mein sugar ke targets mukhtalif hotay hain, waqt janne se reading ka sahi andaza hota hai. | - |
| 4 | `hyperglycemia_symptoms` | Kya aap ko haal hi mein pyas ziada lagna, bar bar peshab aana, ghair mamooli thakawat, ya dhundla nazar aana mehsoos hua hai? | nahi | `kind_default` | yes, no | Sugar barhne se pyas, baar baar peshab ya aankhon ke aagay dhundla pan ho sakta hai, is se reading samajhne mein madad milti hai. | - |
| 5 | `foot_problems` | Kya aap ke paon par koi naya zakham, chaala, dard, ya sunn hona (numbness) hai? | nahi | `kind_default` | yes, no | Paon mein zakham, chhalay ya sunn honay ki barwaqt nishandahi sugar ki pecheedgiyon se bachati hai. | - |
| 6 | `adherence_diabetes` | Kya aap ne aaj apni sugar ki dawaiyan hidayat ke mutabiq li hain? | nahi | `kind_default` | yes, no | Yeh janna zaroori hai ke kya aap ne dawai waqt par li taakay doctor sugar ki reading ka sahi andaza laga sakay. | - |
| 7 | `missed_doses_reason_diabetes` | Aaj sugar ki dawa lene mein kya mushkil pesh aayi? | koi nahi | `kind_default` |  | Dawai chhootne ki wajah janne se doctor aap ke rozmarrah ke mamool ke mutabiq asaan hal nikaal sakta hai. | - |
| 8 | `lifestyle_diabetes` | Kya haalia dino mein aap ke khanay peenay, warzish, ya zehni dabao mein koi tabdeeli aayi hai? | koi nahi | `kind_default` |  | Khorak, warzish aur zehni dabao ka sugar par seedha asar parta hai. | - |
| 9 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 120 mg/dL - Blood Pressure: Darj nahi kiya gaya - Alamaat: Koi nahi - Dawai: Dose miss hone ki ittila Kya sab theek hai? | yes | `step_map` | Confirm and submit, Need to change something | Taakay save karne se pehle tasdeeq ho sakay ke tamam maloomat theek likhi gayi hain. | ✅ COMPLETE |

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
| 5 | `adherence_hypertension` | Have you taken your prescribed blood pressure medications today? | no | `kind_default` | yes, no | Taking blood pressure medicines consistently every day protects against strokes and heart issues. | - |
| 6 | `missed_doses_reason_hypertension` | What made it hard to take your blood pressure medication as prescribed today? | none | `kind_default` |  | Knowing what got in the way helps your clinician adjust your schedule or prescription. | - |
| 7 | `lifestyle_hypertension` | How has your sleep and stress level been, and have you had any salty food or alcohol recently? | none | `kind_default` |  | Salt intake, quality sleep, and daily stress affect your blood pressure. | - |
| 8 | `is_fasting_today` | Are you fasting today (for Ramadan or another fast)? | no | `kind_default` | yes, no | Fasting changes your meal timing and medication requirements. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: Not provided - Blood Pressure: 120/80 mmHg - Symptoms: None reported - Medication: Missed doses reported Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

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
| 1 | `greeting` | آج آپ کیسا محسوس کر رہے ہیں؟ کیا آپ کوئی علامت بتانا چاہتے ہیں؟ | ٹھیک ہوں | `step_map` |  | طبی سوالات شروع کرنے سے پہلے یہ جاننے کے لیے کہ عمومی طور پر آج آپ کی طبیعت کیسی ہے۔ | - |
| 2 | `bp_reading` | کیا آپ نے آج اپنا بلڈ پریشر چیک کیا ہے؟ اگر ہاں، تو کیا ریڈنگ تھی (مثلاً 130/85)؟ | 120/80 | `step_map` |  | بلڈ پریشر کی ریڈنگ سے ڈاکٹر کو دل اور شریانوں کی صحت کا بروقت اندازہ ہوتا ہے۔ | - |
| 3 | `bp_technique` | کیا بلڈ پریشر چیک کرنے سے پہلے آپ نے 5 منٹ پرسکون بیٹھ کر آرام کیا تھا اور کمر اور بازو کو سہارا دیا تھا؟ | نہیں | `kind_default` | yes, no | ٹیسٹ سے پہلے سکون سے بیٹھنے سے درست ریڈنگ آتی ہے، جلد بازی یا بات کرنے سے بی پی وقتی طور پر بڑھ سکتا ہے۔ | - |
| 4 | `associated_symptoms` | کیا آپ کو شدید سر درد، سانس پھولنا، ٹخنوں پر سوجن، یا کھڑے ہونے پر چکر آنا محسوس ہو رہا ہے؟ | نہیں | `kind_default` | yes, no | بلڈ پریشر کے ساتھ شدید سر درد یا سانس پھولنے کی علامات میں فوری طبی جانچ ضروری ہے۔ | - |
| 5 | `adherence_hypertension` | کیا آپ نے آج اپنے بلڈ پریشر کی دوائیاں لے لی ہیں؟ | نہیں | `kind_default` | yes, no | بلڈ پریشر کی باقاعدہ دوا دل اور شریانوں کو محفوظ رکھتی ہے۔ | - |
| 6 | `missed_doses_reason_hypertension` | آج بلڈ پریشر کی دوا لینے میں کیا رکاوٹ پیش آئی؟ | کچھ نہیں | `kind_default` |  | وجہ جان کر ڈاکٹر آپ کے لیے بی پی کی دوا کا معمول آسان بنا سکتا ہے۔ | - |
| 7 | `lifestyle_hypertension` | آپ کی نیند اور ذہنی دباؤ کیسا رہا، اور کیا آپ نے نمکین کھانے یا شراب کا استعمال کیا؟ | کچھ نہیں | `kind_default` |  | نمک کا استعمال، نیند اور روزمرہ کا تناؤ بلڈ پریشر پر گہرا اثر ڈالتے ہیں۔ | - |
| 8 | `is_fasting_today` | کیا آپ نے آج روزہ رکھا ہوا ہے؟ | نہیں | `kind_default` | yes, no | روزے میں کھانے پینے اور ادویات کے اوقات بدل جاتے ہیں، تاکہ ڈاکٹر کے لیے رہنمائی آسان ہو۔ | - |
| 9 | `summary_confirmation` | ہم نے آج یہ معلومات درج کی ہیں: - شوگر: درج نہیں کی گئی - بلڈ پریشر: 120/80 mmHg - علامات: کوئی نہیں - ادویات: خوراک چھوٹنے کی اطلاع کیا سب کچھ ٹھیک ہے؟ | yes | `step_map` | Confirm and submit, Need to change something | تاکہ محفوظ کرنے سے پہلے تصدیق ہو سکے کہ تمام معلومات درست لکھی گئی ہیں۔ | ✅ COMPLETE |

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
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | theek hoon | `step_map` |  | Tibbi sawalaat shuru karne se pehle yeh janne ke liye ke aam tor par aaj aap ki tabiyat kaisi hai. | - |
| 2 | `bp_reading` | Kya aap ne aaj apna blood pressure check kiya hai? Agar haan, toh kya reading thi (maslan 130/85)? | 120/80 | `step_map` |  | BP ki reading se doctor ko dil aur khoon ki naliyon ki sehat ka barwaqt andaza hota hai. | - |
| 3 | `bp_technique` | Kya BP check karne se pehle aap ne 5 minute pursukoon baith kar aaram kiya tha aur kamar aur baazu ko sahara diya tha? | nahi | `kind_default` | yes, no | Test se pehle sukoon se baithne se sahi reading aati hai, jaldbazi ya baat karne se BP barh sakta hai. | - |
| 4 | `associated_symptoms` | Kya aap ko shadeed sar dard, saans phoolna, takhno par sojan, ya kharay hone par chakkar aana mehsoos ho raha hai? | nahi | `kind_default` | yes, no | BP ke sath shadeed sar dard ya saans phoolne ki alamaat mein fori tibbi jaanch zaroori hai. | - |
| 5 | `adherence_hypertension` | Kya aap ne aaj apne blood pressure ki dawaiyan le li hain? | nahi | `kind_default` | yes, no | BP ki baqaida dawai dil aur shariyanon ko mehfooz rakhti hai. | - |
| 6 | `missed_doses_reason_hypertension` | Aaj BP ki dawa lene mein kya rukawat pesh aayi? | koi nahi | `kind_default` |  | Wajah jaan kar doctor aap ke liye BP ki dawai ka mamool asaan bana sakta hai. | - |
| 7 | `lifestyle_hypertension` | Aap ki neend aur zehni dabao kaisa raha, aur kya aap ne namkeen khanay ya alcohol ka istemal kiya? | koi nahi | `kind_default` |  | Namak ka istemal, neend aur rozmarrah ka dabao BP par asar daaltay hain. | - |
| 8 | `is_fasting_today` | Kya aap ne aaj roza rakha hua hai? | nahi | `kind_default` | yes, no | Rozay mein khanay peenay aur dawai ke auqaat badal jatay hain, taakay doctor ke liye rehnumai asaan ho. | - |
| 9 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: Darj nahi ki gayi - Blood Pressure: 120/80 mmHg - Alamaat: Koi nahi - Dawai: Dose miss hone ki ittila Kya sab theek hai? | yes | `step_map` | Confirm and submit, Need to change something | Taakay save karne se pehle tasdeeq ho sakay ke tamam maloomat theek likhi gayi hain. | ✅ COMPLETE |

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
| 6 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 7 | `foot_problems` | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | no | `kind_default` | yes, no | Catching sores, cuts, or numbness on feet early prevents serious complications. | - |
| 8 | `associated_symptoms` | Do you have a severe headache, shortness of breath, ankle swelling, or dizziness when standing up? | no | `kind_default` | yes, no | Symptoms like severe headaches or breathlessness help identify if high blood pressure needs prompt attention. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: 120/80 mmHg - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

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
| 1 | `greeting` | آج آپ کیسا محسوس کر رہے ہیں؟ کیا آپ کوئی علامت بتانا چاہتے ہیں؟ | ٹھیک ہوں | `step_map` |  | طبی سوالات شروع کرنے سے پہلے یہ جاننے کے لیے کہ عمومی طور پر آج آپ کی طبیعت کیسی ہے۔ | - |
| 2 | `glucose_reading` | کیا آپ نے آج شوگر چیک کی ہے؟ اگر ہاں، تو کیا ریڈنگ تھی؟ | 120 mg/dL | `step_map` |  | شوگر کی ریڈنگ سے آپ کے ڈاکٹر کو یہ جانچنے میں مدد ملتی ہے کہ شوگر قابو میں ہے یا نہیں۔ | - |
| 3 | `bp_reading` | کیا آپ نے آج اپنا بلڈ پریشر چیک کیا ہے؟ اگر ہاں، تو کیا ریڈنگ تھی (مثلاً 130/85)؟ | 120/80 | `step_map` |  | بلڈ پریشر کی ریڈنگ سے ڈاکٹر کو دل اور شریانوں کی صحت کا بروقت اندازہ ہوتا ہے۔ | - |
| 4 | `glucose_context` | کیا یہ ریڈنگ نہار منہ تھی، کھانے سے پہلے، کھانے کے بعد، یا رات سونے سے پہلے؟ | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | کھانے سے پہلے اور بعد میں شوگر کے اہداف مختلف ہوتے ہیں، وقت جاننے سے ریڈنگ کی صحیح سمجھ آتی ہے۔ | - |
| 5 | `bp_technique` | کیا بلڈ پریشر چیک کرنے سے پہلے آپ نے 5 منٹ پرسکون بیٹھ کر آرام کیا تھا اور کمر اور بازو کو سہارا دیا تھا؟ | نہیں | `kind_default` | yes, no | ٹیسٹ سے پہلے سکون سے بیٹھنے سے درست ریڈنگ آتی ہے، جلد بازی یا بات کرنے سے بی پی وقتی طور پر بڑھ سکتا ہے۔ | - |
| 6 | `hyperglycemia_symptoms` | کیا آپ کو حال ہی میں پیاس زیادہ لگنا، بار بار پیشاب آنا، غیر معمولی تھکاوٹ، یا دھندلا نظر آنا محسوس ہوا ہے؟ | نہیں | `kind_default` | yes, no | شوگر بڑھنے سے پیاس، بار بار پیشاب یا آنکھوں کے آگے دھندلا پن ہو سکتا ہے، اس سے ریڈنگ کو سمجھنے میں مدد ملتی ہے۔ | - |
| 7 | `foot_problems` | کیا آپ کے پاؤں پر کوئی نیا زخم، چھالا، درد، یا بے حسی (سن ہونا) ہے؟ | نہیں | `kind_default` | yes, no | پاؤں میں زخم، چھالے یا سن ہونے کی بروقت نشاندہی ذیابیطس کی پیچیدگیوں سے بچاتی ہے۔ | - |
| 8 | `associated_symptoms` | کیا آپ کو شدید سر درد، سانس پھولنا، ٹخنوں پر سوجن، یا کھڑے ہونے پر چکر آنا محسوس ہو رہا ہے؟ | نہیں | `kind_default` | yes, no | بلڈ پریشر کے ساتھ شدید سر درد یا سانس پھولنے کی علامات میں فوری طبی جانچ ضروری ہے۔ | - |
| 9 | `summary_confirmation` | ہم نے آج یہ معلومات درج کی ہیں: - شوگر: 120 mg/dL - بلڈ پریشر: 120/80 mmHg - علامات: کوئی نہیں - ادویات: درج نہیں کیا سب کچھ ٹھیک ہے؟ | yes | `step_map` | Confirm and submit, Need to change something | تاکہ محفوظ کرنے سے پہلے تصدیق ہو سکے کہ تمام معلومات درست لکھی گئی ہیں۔ | ✅ COMPLETE |

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
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | theek hoon | `step_map` |  | Tibbi sawalaat shuru karne se pehle yeh janne ke liye ke aam tor par aaj aap ki tabiyat kaisi hai. | - |
| 2 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 120 mg/dL | `step_map` |  | Sugar ki reading se aap ke doctor ko yeh dekhne mein madad milti hai ke sugar control mein hai ya nahi. | - |
| 3 | `bp_reading` | Kya aap ne aaj apna blood pressure check kiya hai? Agar haan, toh kya reading thi (maslan 130/85)? | 120/80 | `step_map` |  | BP ki reading se doctor ko dil aur khoon ki naliyon ki sehat ka barwaqt andaza hota hai. | - |
| 4 | `glucose_context` | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Khanay se pehle aur baad mein sugar ke targets mukhtalif hotay hain, waqt janne se reading ka sahi andaza hota hai. | - |
| 5 | `bp_technique` | Kya BP check karne se pehle aap ne 5 minute pursukoon baith kar aaram kiya tha aur kamar aur baazu ko sahara diya tha? | nahi | `kind_default` | yes, no | Test se pehle sukoon se baithne se sahi reading aati hai, jaldbazi ya baat karne se BP barh sakta hai. | - |
| 6 | `hyperglycemia_symptoms` | Kya aap ko haal hi mein pyas ziada lagna, bar bar peshab aana, ghair mamooli thakawat, ya dhundla nazar aana mehsoos hua hai? | nahi | `kind_default` | yes, no | Sugar barhne se pyas, baar baar peshab ya aankhon ke aagay dhundla pan ho sakta hai, is se reading samajhne mein madad milti hai. | - |
| 7 | `foot_problems` | Kya aap ke paon par koi naya zakham, chaala, dard, ya sunn hona (numbness) hai? | nahi | `kind_default` | yes, no | Paon mein zakham, chhalay ya sunn honay ki barwaqt nishandahi sugar ki pecheedgiyon se bachati hai. | - |
| 8 | `associated_symptoms` | Kya aap ko shadeed sar dard, saans phoolna, takhno par sojan, ya kharay hone par chakkar aana mehsoos ho raha hai? | nahi | `kind_default` | yes, no | BP ke sath shadeed sar dard ya saans phoolne ki alamaat mein fori tibbi jaanch zaroori hai. | - |
| 9 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 120 mg/dL - Blood Pressure: 120/80 mmHg - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm and submit, Need to change something | Taakay save karne se pehle tasdeeq ho sakay ke tamam maloomat theek likhi gayi hain. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient); None (conf: High, by: patient)

---

### Scenario: `unclear_maybe` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | maybe | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_maybe` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling okay | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `foot_problems` | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | no | `kind_default` | yes, no | Catching sores, cuts, or numbness on feet early prevents serious complications. | - |
| 6 | `adherence_diabetes` | Have you taken your diabetes medications as prescribed today? | maybe | `step_map` | yes, no | Knowing whether you took your medicine as prescribed helps your doctor interpret your sugar readings. | - |
| 7 | `lifestyle_diabetes` | Any changes in your meals, physical activity, or stress levels recently? | none | `kind_default` |  | Diet, activity, and stress directly influence your blood sugar. | - |
| 8 | `is_fasting_today` | Are you fasting today (for Ramadan or another fast)? | no | `kind_default` | yes, no | Fasting changes your meal timing and medication requirements. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `unclear_shayad` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | nahi | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | shayad | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | koi nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_shayad` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | feeling okay | `step_map` |  | Tibbi sawalaat shuru karne se pehle yeh janne ke liye ke aam tor par aaj aap ki tabiyat kaisi hai. | - |
| 2 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 120 mg/dL | `step_map` |  | Sugar ki reading se aap ke doctor ko yeh dekhne mein madad milti hai ke sugar control mein hai ya nahi. | - |
| 3 | `glucose_context` | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Khanay se pehle aur baad mein sugar ke targets mukhtalif hotay hain, waqt janne se reading ka sahi andaza hota hai. | - |
| 4 | `hyperglycemia_symptoms` | Kya aap ko haal hi mein pyas ziada lagna, bar bar peshab aana, ghair mamooli thakawat, ya dhundla nazar aana mehsoos hua hai? | nahi | `kind_default` | yes, no | Sugar barhne se pyas, baar baar peshab ya aankhon ke aagay dhundla pan ho sakta hai, is se reading samajhne mein madad milti hai. | - |
| 5 | `foot_problems` | Kya aap ke paon par koi naya zakham, chaala, dard, ya sunn hona (numbness) hai? | nahi | `kind_default` | yes, no | Paon mein zakham, chhalay ya sunn honay ki barwaqt nishandahi sugar ki pecheedgiyon se bachati hai. | - |
| 6 | `adherence_diabetes` | Kya aap ne aaj apni sugar ki dawaiyan hidayat ke mutabiq li hain? | shayad | `step_map` | yes, no | Yeh janna zaroori hai ke kya aap ne dawai waqt par li taakay doctor sugar ki reading ka sahi andaza laga sakay. | - |
| 7 | `lifestyle_diabetes` | Kya haalia dino mein aap ke khanay peenay, warzish, ya zehni dabao mein koi tabdeeli aayi hai? | koi nahi | `kind_default` |  | Khorak, warzish aur zehni dabao ka sugar par seedha asar parta hai. | - |
| 8 | `is_fasting_today` | Kya aap ne aaj roza rakha hua hai? | nahi | `kind_default` | yes, no | Rozay mein khanay peenay aur dawai ke auqaat badal jatay hain, taakay doctor ke liye rehnumai asaan ho. | - |
| 9 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 120 mg/dL - Blood Pressure: Darj nahi kiya gaya - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm and submit, Need to change something | Taakay save karne se pehle tasdeeq ho sakay ke tamam maloomat theek likhi gayi hain. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `unclear_pata_nahi` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | pata nahi | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_pata_nahi` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling okay | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `foot_problems` | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | no | `kind_default` | yes, no | Catching sores, cuts, or numbness on feet early prevents serious complications. | - |
| 6 | `adherence_diabetes` | Have you taken your diabetes medications as prescribed today? | pata nahi | `step_map` | yes, no | Knowing whether you took your medicine as prescribed helps your doctor interpret your sugar readings. | - |
| 7 | `lifestyle_diabetes` | Any changes in your meals, physical activity, or stress levels recently? | none | `kind_default` |  | Diet, activity, and stress directly influence your blood sugar. | - |
| 8 | `is_fasting_today` | Are you fasting today (for Ramadan or another fast)? | no | `kind_default` | yes, no | Fasting changes your meal timing and medication requirements. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `unclear_pata_nahi_ur` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | نہیں | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | پتہ نہیں | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | کچھ نہیں | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_pata_nahi_ur` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | آج آپ کیسا محسوس کر رہے ہیں؟ کیا آپ کوئی علامت بتانا چاہتے ہیں؟ | feeling okay | `step_map` |  | طبی سوالات شروع کرنے سے پہلے یہ جاننے کے لیے کہ عمومی طور پر آج آپ کی طبیعت کیسی ہے۔ | - |
| 2 | `glucose_reading` | کیا آپ نے آج شوگر چیک کی ہے؟ اگر ہاں، تو کیا ریڈنگ تھی؟ | 120 mg/dL | `step_map` |  | شوگر کی ریڈنگ سے آپ کے ڈاکٹر کو یہ جانچنے میں مدد ملتی ہے کہ شوگر قابو میں ہے یا نہیں۔ | - |
| 3 | `glucose_context` | کیا یہ ریڈنگ نہار منہ تھی، کھانے سے پہلے، کھانے کے بعد، یا رات سونے سے پہلے؟ | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | کھانے سے پہلے اور بعد میں شوگر کے اہداف مختلف ہوتے ہیں، وقت جاننے سے ریڈنگ کی صحیح سمجھ آتی ہے۔ | - |
| 4 | `hyperglycemia_symptoms` | کیا آپ کو حال ہی میں پیاس زیادہ لگنا، بار بار پیشاب آنا، غیر معمولی تھکاوٹ، یا دھندلا نظر آنا محسوس ہوا ہے؟ | نہیں | `kind_default` | yes, no | شوگر بڑھنے سے پیاس، بار بار پیشاب یا آنکھوں کے آگے دھندلا پن ہو سکتا ہے، اس سے ریڈنگ کو سمجھنے میں مدد ملتی ہے۔ | - |
| 5 | `foot_problems` | کیا آپ کے پاؤں پر کوئی نیا زخم، چھالا، درد، یا بے حسی (سن ہونا) ہے؟ | نہیں | `kind_default` | yes, no | پاؤں میں زخم، چھالے یا سن ہونے کی بروقت نشاندہی ذیابیطس کی پیچیدگیوں سے بچاتی ہے۔ | - |
| 6 | `adherence_diabetes` | کیا آپ نے آج اپنی شوگر کی دوائیاں ہدایت کے مطابق لی ہیں؟ | پتہ نہیں | `step_map` | yes, no | یہ جاننا ضروری ہے کہ کیا آپ نے دوا باقاعدگی سے لی تاکہ ڈاکٹر شوگر کی ریڈنگ کا صحیح اندازہ لگا سکے۔ | - |
| 7 | `lifestyle_diabetes` | کیا حالیہ دنوں میں آپ کے کھانے پینے، ورزش، یا ذہنی دباؤ میں کوئی تبدیلی آئی ہے؟ | کچھ نہیں | `kind_default` |  | خوراک، ورزش اور ذہنی تناؤ کا شوگر پر براہ راست اثر پڑتا ہے۔ | - |
| 8 | `is_fasting_today` | کیا آپ نے آج روزہ رکھا ہوا ہے؟ | نہیں | `kind_default` | yes, no | روزے میں کھانے پینے اور ادویات کے اوقات بدل جاتے ہیں، تاکہ ڈاکٹر کے لیے رہنمائی آسان ہو۔ | - |
| 9 | `summary_confirmation` | ہم نے آج یہ معلومات درج کی ہیں: - شوگر: 120 mg/dL - بلڈ پریشر: درج نہیں کیا گیا - علامات: کوئی نہیں - ادویات: درج نہیں کیا سب کچھ ٹھیک ہے؟ | yes | `step_map` | Confirm and submit, Need to change something | تاکہ محفوظ کرنے سے پہلے تصدیق ہو سکے کہ تمام معلومات درست لکھی گئی ہیں۔ | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `unclear_kal_tha` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | nahi | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | kal tha | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | koi nahi | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_kal_tha` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | feeling okay | `step_map` |  | Tibbi sawalaat shuru karne se pehle yeh janne ke liye ke aam tor par aaj aap ki tabiyat kaisi hai. | - |
| 2 | `glucose_reading` | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | 120 mg/dL | `step_map` |  | Sugar ki reading se aap ke doctor ko yeh dekhne mein madad milti hai ke sugar control mein hai ya nahi. | - |
| 3 | `glucose_context` | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Khanay se pehle aur baad mein sugar ke targets mukhtalif hotay hain, waqt janne se reading ka sahi andaza hota hai. | - |
| 4 | `hyperglycemia_symptoms` | Kya aap ko haal hi mein pyas ziada lagna, bar bar peshab aana, ghair mamooli thakawat, ya dhundla nazar aana mehsoos hua hai? | nahi | `kind_default` | yes, no | Sugar barhne se pyas, baar baar peshab ya aankhon ke aagay dhundla pan ho sakta hai, is se reading samajhne mein madad milti hai. | - |
| 5 | `foot_problems` | Kya aap ke paon par koi naya zakham, chaala, dard, ya sunn hona (numbness) hai? | nahi | `kind_default` | yes, no | Paon mein zakham, chhalay ya sunn honay ki barwaqt nishandahi sugar ki pecheedgiyon se bachati hai. | - |
| 6 | `adherence_diabetes` | Kya aap ne aaj apni sugar ki dawaiyan hidayat ke mutabiq li hain? | kal tha | `step_map` | yes, no | Yeh janna zaroori hai ke kya aap ne dawai waqt par li taakay doctor sugar ki reading ka sahi andaza laga sakay. | - |
| 7 | `lifestyle_diabetes` | Kya haalia dino mein aap ke khanay peenay, warzish, ya zehni dabao mein koi tabdeeli aayi hai? | koi nahi | `kind_default` |  | Khorak, warzish aur zehni dabao ka sugar par seedha asar parta hai. | - |
| 8 | `is_fasting_today` | Kya aap ne aaj roza rakha hua hai? | nahi | `kind_default` | yes, no | Rozay mein khanay peenay aur dawai ke auqaat badal jatay hain, taakay doctor ke liye rehnumai asaan ho. | - |
| 9 | `summary_confirmation` | Hum ne aaj yeh record kiya hai: - Sugar: 120 mg/dL - Blood Pressure: Darj nahi kiya gaya - Alamaat: Koi nahi - Dawai: Record nahi hui Kya sab theek hai? | yes | `step_map` | Confirm and submit, Need to change something | Taakay save karne se pehle tasdeeq ho sakay ke tamam maloomat theek likhi gayi hain. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `unclear_thumbs_up` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | maybe | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_thumbs_up` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling okay | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `foot_problems` | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | no | `kind_default` | yes, no | Catching sores, cuts, or numbness on feet early prevents serious complications. | - |
| 6 | `adherence_diabetes` | Have you taken your diabetes medications as prescribed today? | maybe | `step_map` | yes, no | Knowing whether you took your medicine as prescribed helps your doctor interpret your sugar readings. | - |
| 7 | `lifestyle_diabetes` | Any changes in your meals, physical activity, or stress levels recently? | none | `kind_default` |  | Diet, activity, and stress directly influence your blood sugar. | - |
| 8 | `is_fasting_today` | Are you fasting today (for Ramadan or another fast)? | no | `kind_default` | yes, no | Fasting changes your meal timing and medication requirements. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `unclear_dots` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | maybe | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_dots` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling okay | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `foot_problems` | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | no | `kind_default` | yes, no | Catching sores, cuts, or numbness on feet early prevents serious complications. | - |
| 6 | `adherence_diabetes` | Have you taken your diabetes medications as prescribed today? | maybe | `step_map` | yes, no | Knowing whether you took your medicine as prescribed helps your doctor interpret your sugar readings. | - |
| 7 | `lifestyle_diabetes` | Any changes in your meals, physical activity, or stress levels recently? | none | `kind_default` |  | Diet, activity, and stress directly influence your blood sugar. | - |
| 8 | `is_fasting_today` | Are you fasting today (for Ramadan or another fast)? | no | `kind_default` | yes, no | Fasting changes your meal timing and medication requirements. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `unclear_same_as_yesterday` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | maybe | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_same_as_yesterday` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling okay | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `foot_problems` | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | no | `kind_default` | yes, no | Catching sores, cuts, or numbness on feet early prevents serious complications. | - |
| 6 | `adherence_diabetes` | Have you taken your diabetes medications as prescribed today? | maybe | `step_map` | yes, no | Knowing whether you took your medicine as prescribed helps your doctor interpret your sugar readings. | - |
| 7 | `lifestyle_diabetes` | Any changes in your meals, physical activity, or stress levels recently? | none | `kind_default` |  | Diet, activity, and stress directly influence your blood sugar. | - |
| 8 | `is_fasting_today` | Are you fasting today (for Ramadan or another fast)? | no | `kind_default` | yes, no | Fasting changes your meal timing and medication requirements. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---

### Scenario: `unclear_ok` (Engine: V2) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** ['summary_confirmation']
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you'd like to report? | feeling okay | `step_map` |  |  | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (and was it fasting or after a meal)? | 120 mg/dL | `step_map` |  |  | - |
| 3 | `hyperglycemia_symptoms` | Have you noticed increased thirst, frequent urination, or blurred vision? | no | `kind_default` |  |  | - |
| 4 | `adherence` | Have you taken your diabetes medication as prescribed today? | maybe | `step_map` |  |  | - |
| 5 | `lifestyle` | Any changes in your diet, exercise, or stress levels recently? | none | `kind_default` |  |  | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: Medium, by: patient)

---

### Scenario: `unclear_ok` (Engine: V3) — Status: VALID

- **Group:** c
- **Valid Delivery:** `True` (must_deliver: ['adherence'])
- **Final Level:** `review`
- **Emergency:** False
- **Unmapped Answers:** None
- **Notes:** Valid normal completion

| Turn | Step ID | Question Text Served | Answer Sent | Answer Source | Options | Why Text | Flags / Note |
|:---:|---|---|---|:---:|---|---|---|
| 1 | `greeting` | How are you feeling today? Any symptoms you would like to report? | feeling okay | `step_map` |  | To check how you are feeling generally today before looking at your numbers. | - |
| 2 | `glucose_reading` | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | 120 mg/dL | `step_map` |  | Your blood sugar reading helps your clinician track how your diabetes treatment is working. | - |
| 3 | `glucose_context` | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | fasting | `kind_default` | fasting, before_meal, after_meal, bedtime, random | Blood sugar targets are different before breakfast compared to after a meal. | - |
| 4 | `hyperglycemia_symptoms` | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | no | `kind_default` | yes, no | High blood sugar can cause thirst, frequent urination, and blurry vision. | - |
| 5 | `foot_problems` | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | no | `kind_default` | yes, no | Catching sores, cuts, or numbness on feet early prevents serious complications. | - |
| 6 | `adherence_diabetes` | Have you taken your diabetes medications as prescribed today? | maybe | `step_map` | yes, no | Knowing whether you took your medicine as prescribed helps your doctor interpret your sugar readings. | - |
| 7 | `lifestyle_diabetes` | Any changes in your meals, physical activity, or stress levels recently? | none | `kind_default` |  | Diet, activity, and stress directly influence your blood sugar. | - |
| 8 | `is_fasting_today` | Are you fasting today (for Ramadan or another fast)? | no | `kind_default` | yes, no | Fasting changes your meal timing and medication requirements. | - |
| 9 | `summary_confirmation` | Here is what we recorded today: - Blood Glucose: 120 mg/dL - Blood Pressure: Not provided - Symptoms: None reported - Medication: Not recorded Does everything look right to you? | yes | `step_map` | Confirm and submit, Need to change something | To confirm we noted your answers correctly before saving. | ✅ COMPLETE |

**Completion Result Details:**
- Requires Review: `True` | Max Severity: `moderate`
- Reasons: None
- Factors: None
- Intakes: None (conf: High, by: patient)

---
