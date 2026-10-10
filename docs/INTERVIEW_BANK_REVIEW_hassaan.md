# Core Interview Bank Wording Review

Reviewed from `backend-poc-technical/agents/interview_bank/core.json`. Review focus: whether a 65-year-old patient can understand the wording, and whether any medical term is unclear or alarming. Suggestions only; the JSON source was not edited.

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `core_greeting` | English | How are you feeling today? Any symptoms you would like to report? | OK | Clear and non-scary. “Symptoms” is acceptable, though “problems or changes in your health” may be easier for some older patients. |
| `core_greeting` | Roman Urdu | Aaj aap kaisa mehsoos kar rahe hain? Kya koi alamat batana chahte hain? | Unclear | “Alamat” is formal and may sound medical. Use “koi takleef ya sehat ki koi baat” for more natural patient wording. |
| `core_greeting` | Urdu | آج آپ کیسا محسوس کر رہے ہیں؟ کیا آپ کوئی علامت بتانا چاہتے ہیں؟ | Unclear | “علامت” is correct but formal. Consider “کیا آپ کو کوئی تکلیف ہے جس کے بارے میں بتانا چاہتے ہیں؟” |
| `core_missing_data_checkpoint` | English | No problem. Can you tell me roughly how you have been feeling instead (for example more thirsty than usual, tired, or dizzy)? If you do have a reading, please share it. | Unclear | “Reading” is ambiguous without naming blood pressure or blood sugar. Say “blood pressure or blood sugar reading” when that is what is meant; “roughly” is otherwise reassuring. |
| `core_missing_data_checkpoint` | Roman Urdu | Koi baat nahi. Kya aap bata sakte hain ke aap kaisa mehsoos kar rahe hain (maslan pyas ziada lagna, thakawat, ya chakkar aana)? Agar reading hai toh zaroor batayein. | Unclear | “Reading” may not be clear to a 65-year-old patient. Use “blood pressure ya blood sugar ka number” if applicable. “Zyada” is the standard spelling. |
| `core_missing_data_checkpoint` | Urdu | کوئی بات نہیں۔ کیا آپ بتا سکتے ہیں کہ آپ کیسا محسوس کر رہے ہیں (مثلاً پیاس زیادہ لگنا، تھکاوٹ، یا چکر آنا)؟ اگر آپ کے پاس ریڈنگ ہے تو ضرور بتائیں۔ | Unclear | The symptom examples are understandable. Replace “ریڈنگ” with “بلڈ پریشر یا شوگر کا نمبر” when the measurement type is known. |
| `core_patient_free_text` | English | Is there anything else you would like your clinician to know about your health today? | Unclear | “Clinician” is professional jargon. “Doctor or care team” is more familiar and less formal. |
| `core_patient_free_text` | Roman Urdu | Kya koi aur baat hai jo aap aaj apni medical team ko batana chahte hain? | Unclear | “Medical team” is understandable but English-heavy. “Doctor ya ilaaj karne wali team” is more conversational. |
| `core_patient_free_text` | Urdu | کیا کوئی اور بات ہے جو آپ آج اپنی میڈیکل ٹیم کے علم میں لانا چاہتے ہیں؟ | Unclear | The meaning is correct, but “علم میں لانا” is formal. Consider “کیا آپ اپنی صحت کے بارے میں آج ڈاکٹر یا علاج کرنے والی ٹیم کو کوئی اور بات بتانا چاہتے ہیں؟” |
| `core_summary_confirm` | English | Here is what we have recorded today. Does everything look right to you? | OK | Clear, respectful, and suitable for confirmation. |
| `core_summary_confirm` | Roman Urdu | Hum ne aaj yeh maloomat darj ki hain. Kya sab theek hai? | OK | Simple and understandable. “Darj” is slightly formal but commonly understood. |
| `core_summary_confirm` | Urdu | ہم نے آج یہ معلومات درج کی ہیں۔ کیا سب کچھ ٹھیک ہے؟ | OK | Correct and calm. “درج” is formal but clear in this short confirmation. |

## Diabetes

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `diabetes_glucose_reading` | English | Have you measured your blood sugar today? If so, what was the reading in mg/dL (or mmol/L)? | Unclear | The question is clear, but the units may be unfamiliar. Add a short explanation or let the patient choose the unit shown on their meter. |
| `diabetes_glucose_reading` | Roman Urdu | Kya aap ne aaj sugar check ki hai? Agar haan, toh kya reading thi? | Unclear | “Sugar” and “reading” are commonly understood but vague. Say “blood sugar ka number” and ask for the unit if needed. |
| `diabetes_glucose_reading` | Urdu | کیا آپ نے آج شوگر چیک کی ہے؟ اگر ہاں، تو کیا ریڈنگ تھی؟ | Unclear | “شوگر” is familiar, but “ریڈنگ” may be unclear. Consider “بلڈ شوگر کا نمبر کیا تھا؟” and ask for the unit separately. |
| `diabetes_glucose_context` | English | Was this reading fasting (before breakfast), before a meal, after a meal, or at bedtime? | Unclear | “Fasting” is explained, which helps. “At bedtime” is clear; consider saying “before breakfast, without eating” for patients unfamiliar with fasting. |
| `diabetes_glucose_context` | Roman Urdu | Kya yeh reading nahar munh thi, khanay se pehle, khanay ke baad, ya raat sone se pehle? | Unclear | “Nahar munh” is formal and may be unfamiliar. Use “subah nashta karne se pehle, bina kuch khaye” if that is the intended meaning. |
| `diabetes_glucose_context` | Urdu | کیا یہ ریڈنگ نہار منہ تھی، کھانے سے پہلے، کھانے کے بعد، یا رات سونے سے پہلے؟ | Unclear | “نہار منہ” is correct but formal. Consider “صبح ناشتہ کرنے سے پہلے، بغیر کچھ کھائے” for older patients. |
| `diabetes_hyperglycemia_symptoms` | English | Have you noticed increased thirst, passing urine much more often, unusual tiredness, or blurry vision recently? | OK | The symptoms are understandable and not scary. “Passing urine” is clear, though “urinating” may be more concise. |
| `diabetes_hyperglycemia_symptoms` | Roman Urdu | Kya aap ko haal hi mein pyas ziada lagna, bar bar peshab aana, ghair mamooli thakawat, ya dhundla nazar aana mehsoos hua hai? | Unclear | “Ghair mamooli” is formal. Use “bahut zyada thakawat” and “dhundla dikhai dena” for more natural speech. |
| `diabetes_hyperglycemia_symptoms` | Urdu | کیا آپ کو حال ہی میں پیاس زیادہ لگنا، بار بار پیشاب آنا، غیر معمولی تھکاوٹ، یا دھندلا نظر آنا محسوس ہوا ہے؟ | Unclear | “غیر معمولی” is formal but correct. “بہت زیادہ تھکاوٹ” and “دھندلا دکھائی دینا” may be easier to understand. |
| `diabetes_foot_problems` | English | Do you have any new cuts, sores, blisters, pain, or numbness in your feet? | OK | Clear symptom list and appropriate urgency without frightening language. |
| `diabetes_foot_problems` | Roman Urdu | Kya aap ke paon par koi naya zakham, chaala, dard, ya sunn hona (numbness) hai? | Unclear | “Zakham” can sound serious and “numbness” is unnecessary English. Use “koi naya cut, zakhm, chaala, dard, ya paon ka sunn hona” with a simple explanation. |
| `diabetes_foot_problems` | Urdu | کیا آپ کے پاؤں پر کوئی نیا زخم، چھالا، درد، یا بے حسی (سن ہونا) ہے؟ | OK | Correct and understandable. The parenthetical explanation makes “بے حسی” clearer; “سن ہونا” alone may be more natural. |
| `diabetes_adherence` | English | Have you taken your diabetes medications as prescribed today? | Unclear | “As prescribed” is formal. Ask “Have you taken your diabetes medicines today the way your doctor told you?” |
| `diabetes_adherence` | Roman Urdu | Kya aap ne aaj apni sugar ki dawaiyan hidayat ke mutabiq li hain? | Unclear | “Hidayat ke mutabiq” is formal. Use “doctor ke bataye hue tareeqe ke mutabiq” for clarity. |
| `diabetes_adherence` | Urdu | کیا آپ نے آج اپنی شوگر کی دوائیاں ہدایت کے مطابق لی ہیں؟ | Unclear | “ہدایت کے مطابق” is correct but formal. Consider “کیا آپ نے آج شوگر کی دوائیاں ڈاکٹر کے بتائے ہوئے طریقے سے لی ہیں؟” |
| `diabetes_missed_doses_reason` | English | What made it difficult to take your diabetes medicine as prescribed today? | Unclear | “As prescribed” may sound blaming or formal. Use “What made it difficult to take your diabetes medicine the way your doctor told you today?” |
| `diabetes_missed_doses_reason` | Roman Urdu | Aaj sugar ki dawa lene mein kya mushkil pesh aayi? | OK | Natural, non-blaming, and easy to understand. |
| `diabetes_missed_doses_reason` | Urdu | آج شوگر کی دوا لینے میں کیا مشکل پیش آئی؟ | OK | Natural and non-judgmental. It invites practical reasons without making the patient feel blamed. |
| `diabetes_lifestyle` | English | Any changes in your meals, physical activity, or stress levels recently? | Unclear | “Physical activity” and “stress levels” are somewhat formal. Use “changes in what you eat, how much you move or exercise, or your tension recently?” |
| `diabetes_lifestyle` | Roman Urdu | Kya haalia dino mein aap ke khanay peenay, warzish, ya zehni dabao mein koi tabdeeli aayi hai? | Unclear | “Zehni dabao” is correct but formal. “Fikr ya tension” may be more familiar, while “haal hi ke dino mein” is more natural. |
| `diabetes_lifestyle` | Urdu | کیا حالیہ دنوں میں آپ کے کھانے پینے، ورزش، یا ذہنی دباؤ میں کوئی تبدیلی آئی ہے؟ | Unclear | The wording is correct, but “ذہنی دباؤ” may be formal. “فکر یا ٹینشن” may be easier for some older patients. |
