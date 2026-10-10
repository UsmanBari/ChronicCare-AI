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

## Hypertension

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `hypertension_bp_reading` | English | Have you measured your blood pressure today? If so, what was the reading (for example 130/85)? | OK | Clear and gives a useful example. Do not require the patient to know “mmHg”; accept the numbers shown on the monitor. |
| `hypertension_bp_reading` | Roman Urdu | Kya aap ne aaj apna blood pressure check kiya hai? Agar haan, toh kya reading thi (maslan 130/85)? | Unclear | “Reading” is common but vague. Say “blood pressure ke numbers kya thay” for older patients; “misal ke taur par” is more natural than “maslan.” |
| `hypertension_bp_reading` | Urdu | کیا آپ نے آج اپنا بلڈ پریشر چیک کیا ہے؟ اگر ہاں، تو کیا ریڈنگ تھی (مثلاً 130/85)؟ | Unclear | The meaning is clear, but “ریڈنگ” is English-derived and may be unclear. Consider “بلڈ پریشر کے نمبر کیا تھے؟” |
| `hypertension_bp_technique` | English | Before measuring, did you rest quietly for 5 minutes with your back supported and arm resting on a table? | Unclear | The instruction is accurate but long. Split it into short steps or say “sit quietly for 5 minutes, with your back supported and arm on a table.” |
| `hypertension_bp_technique` | Roman Urdu | Kya BP check karne se pehle aap ne 5 minute pursukoon baith kar aaram kiya tha aur kamar aur baazu ko sahara diya tha? | Unclear | “BP” and “pursukoon” may be less clear. Use “blood pressure check karne se pehle 5 minute chup-chaap baithay thay? Kamar aur baazu ko sahara diya tha?” |
| `hypertension_bp_technique` | Urdu | کیا بلڈ پریشر چیک کرنے سے پہلے آپ نے 5 منٹ پرسکون بیٹھ کر آرام کیا تھا اور کمر اور بازو کو سہارا دیا تھا؟ | OK | Correct and understandable, though it is long. Consider splitting the rest and posture questions for easier answering. |
| `hypertension_associated_symptoms` | English | Do you have a severe headache, shortness of breath, ankle swelling, or dizziness when standing up? | OK | The symptoms are clear and appropriately direct. “Severe” is important but not unnecessarily frightening. |
| `hypertension_associated_symptoms` | Roman Urdu | Kya aap ko shadeed sar dard, saans phoolna, takhno par sojan, ya kharay hone par chakkar aana mehsoos ho raha hai? | Unclear | “Shadeed” is formal. Use “bahut tez sar dard”; “takhno par sojan” and the standing-up phrase are otherwise understandable. |
| `hypertension_associated_symptoms` | Urdu | کیا آپ کو شدید سر درد، سانس پھولنا، ٹخنوں پر سوجن، یا کھڑے ہونے پر چکر آنا محسوس ہو رہا ہے؟ | Unclear | “شدید” is correct but formal. “بہت تیز سر درد” may be easier; the symptom list itself is medically understandable. |
| `hypertension_otc_meds_bp` | English | Have you taken any pain medicines (like ibuprofen), cold/cough syrups, or herbal supplements recently? | Unclear | “Over-the-counter” is not shown in the patient text, which helps. “Herbal supplements” may still be unfamiliar; say “herbal medicines or supplements.” |
| `hypertension_otc_meds_bp` | Roman Urdu | Kya aap ne haal hi mein dard ki dawaiyan (jaise ibuprofen), nazla zukam ka syrup, ya desi jari bootiyan li hain? | Unclear | “Desi jari bootiyan” can sound like ordinary herbs rather than medicines. Use “jari bootiyon ki dawa ya supplement” and explain ibuprofen if needed. |
| `hypertension_otc_meds_bp` | Urdu | کیا آپ نے حال ہی میں درد کش دوائیں (جیسے بروفین)، نزلہ زکام کا شربت، یا دیسی جڑی بوٹیاں لی ہیں؟ | Unclear | “دیسی جڑی بوٹیاں” is too broad and may not capture supplements. Use “جڑی بوٹیوں کی دوا یا سپلیمنٹ” and consider writing “آئیبوپروفین” rather than a brand-like term if that is intended. |
| `hypertension_adherence` | English | Have you taken your prescribed blood pressure medications today? | OK | Clear and neutral. “Prescribed” is acceptable, though “the blood pressure medicines your doctor gave you” is more conversational. |
| `hypertension_adherence` | Roman Urdu | Kya aap ne aaj apne blood pressure ki dawaiyan le li hain? | OK | Simple and understandable. It could specify “doctor ke bataye mutabiq” only if adherence to instructions is being checked. |
| `hypertension_adherence` | Urdu | کیا آپ نے آج اپنے بلڈ پریشر کی دوائیاں لے لی ہیں؟ | OK | Clear and natural. No scary or incorrect medical wording. |
| `hypertension_missed_doses_reason` | English | What made it hard to take your blood pressure medication as prescribed today? | Unclear | “As prescribed” is formal. Use “What made it hard to take your blood pressure medicine the way your doctor told you today?” |
| `hypertension_missed_doses_reason` | Roman Urdu | Aaj BP ki dawa lene mein kya rukawat pesh aayi? | Unclear | “BP” and “rukawat pesh aayi” are formal. Use “Aaj blood pressure ki dawa lena mushkil kyun hua?” |
| `hypertension_missed_doses_reason` | Urdu | آج بلڈ پریشر کی دوا لینے میں کیا رکاوٹ پیش آئی؟ | Unclear | “رکاوٹ پیش آئی” is formal. “آج بلڈ پریشر کی دوا لینا مشکل کیوں ہوا؟” is simpler and less blaming. |
| `hypertension_lifestyle` | English | How has your sleep and stress level been, and have you had any salty food or alcohol recently? | Unclear | “Stress level” and “salty food” are understandable but formal. “How have you been sleeping and feeling lately? Have you eaten salty foods or had any alcohol?” is more conversational and non-judgmental. |
| `hypertension_lifestyle` | Roman Urdu | Aap ki neend aur zehni dabao kaisa raha, aur kya aap ne namkeen khanay ya alcohol ka istemal kiya? | Unclear | “Zehni dabao” and “alcohol ka istemal” are formal. Use “neend aur fikr/tension kaisi rahi? Kya namkeen khana ya alcohol wali koi cheez li?” |
| `hypertension_lifestyle` | Urdu | آپ کی نیند اور ذہنی دباؤ کیسا رہا، اور کیا آپ نے نمکین کھانے یا شراب کا استعمال کیا؟ | Unclear | “شراب” is clear but may feel judgmental in some settings. A neutral phrase such as “کیا آپ نے الکحل والی کوئی چیز پی؟” may be easier, while “ذہنی دباؤ” can be replaced with “فکر یا ٹینشن.” |

## Insulin or Sulfonylurea

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `insulin_hypo_events_past_week` | English | In the past 7 days, have you had any low blood sugar episodes (like sudden shakiness, cold sweat, hunger, or feeling faint)? | Unclear | “Episodes” is formal. Ask “In the past 7 days, have you had low blood sugar, such as shaking, a cold sweat, sudden hunger, or feeling like you might faint?” |
| `insulin_hypo_events_past_week` | Roman Urdu | Pichle 7 dino mein, kya aap ki sugar kam (low) hui thi (jaise kapkapahat, thanday paseenay, shadeed bhook, ya ghashi)? | Unclear | “Ghashi” can sound like complete fainting and may alarm patients. Use “behoshi jaisa mehsoos hona” or explain “aisa lagna ke aap gir sakte hain”; “shadeed bhook” is also formal. |
| `insulin_hypo_events_past_week` | Urdu | گزشتہ 7 دنوں میں، کیا آپ کی شوگر کم (لو) ہوئی تھی (جیسے کپکپاہٹ، ٹھنڈے پسینے، شدید بھوک، یا غشی)؟ | Unclear | “غشی” may imply actual loss of consciousness and can sound scary. Consider “بے ہوشی جیسا محسوس ہونا” and replace “شدید بھوک” with “اچانک بہت بھوک لگنا.” |
| `insulin_hypo_symptoms_acute` | English | Are you currently feeling any shakiness, sweating, dizziness, or confusion that gets better when you eat something sweet? | Unclear | The symptom list is clear, but the conditional is long. Split it: “Are you shaking, sweating, dizzy, or confused now? Does it improve after you eat or drink something sugary?” |
| `insulin_hypo_symptoms_acute` | Roman Urdu | Kya aap is waqt kapkapahat, paseena, chakkar, ya uljhan mehsoos kar rahe hain jo meetha khanay se theek hoti ho? | Unclear | The meaning is understandable but the sentence is long. Use “Kya abhi kapkapahat, paseena, chakkar ya uljhan hai? Kya meetha khane ya peene se behtari hoti hai?” |
| `insulin_hypo_symptoms_acute` | Urdu | کیا آپ اس وقت کپکپاہٹ، پسینہ، چکر، یا الجھن محسوس کر رہے ہیں جو میٹھا کھانے سے بہتر ہوتی ہو؟ | Unclear | Correct but long and slightly awkward. Use “کیا ابھی آپ کو کپکپاہٹ، پسینہ، چکر یا الجھن ہو رہی ہے؟ کیا میٹھا کھانے یا پینے سے یہ بہتر ہوتی ہے؟” |

## Fasting

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `fasting_is_fasting` | English | Are you fasting today (for Ramadan or another fast)? | OK | Clear and respectful. Mentioning Ramadan and other fasts makes the question inclusive. |
| `fasting_is_fasting` | Roman Urdu | Kya aap ne aaj roza rakha hua hai? | Unclear | Natural for Ramadan, but it assumes “roza” rather than any kind of fasting. Use “Kya aap aaj roza ya koi aur fast rakh rahe hain?” if non-Ramadan fasting matters. |
| `fasting_is_fasting` | Urdu | کیا آپ نے آج روزہ رکھا ہوا ہے؟ | Unclear | Natural Urdu for Ramadan, but it does not reflect the English “another fast.” Consider “کیا آپ آج روزہ یا کوئی اور فاسٹنگ کر رہے ہیں؟” if other fasting is supported. |
| `fasting_predawn_meal` | English | Did you eat a pre-dawn meal (Sehri/Suhoor) before starting your fast today? | OK | Clear, and the parenthetical terms help patients using either spelling. |
| `fasting_predawn_meal` | Roman Urdu | Kya aap ne aaj roza shuru karne se pehle Sehri ki thi? | OK | Natural and easy to understand for a patient observing Ramadan. |
| `fasting_predawn_meal` | Urdu | کیا آپ نے آج روزہ شروع کرنے سے پہلے سحری کی تھی؟ | OK | Natural and clear for Ramadan. If other fasts are supported, add a version for a pre-dawn meal without assuming Sehri. |
| `fasting_symptoms` | English | Have you felt severe dizziness, confusion, extreme thirst, or heavy sweating during your fast today? | OK | The symptoms are clear and the question is appropriately direct. “Severe” and “extreme” communicate importance without naming a frightening diagnosis. |
| `fasting_symptoms` | Roman Urdu | Kya roze ke dauran aap ko shadeed chakkar, uljhan, shadeed pyas, ya bohat ziada paseena mehsoos hua? | Unclear | “Shadeed” is formal and repeated. Use “bahut zyada chakkar, uljhan, bahut zyada pyas, ya bohat paseena” for more natural patient language. |
| `fasting_symptoms` | Urdu | کیا روزے کے دوران آپ کو شدید چکر، الجھن، شدید پیاس، یا بہت زیادہ پسینہ محسوس ہوا؟ | Unclear | The meaning is correct, but “شدید” is formal. “بہت زیادہ چکر” and “بہت زیادہ پیاس” may be easier for some older patients. |
| `fasting_broke_fast` | English | Did you need to break your fast early today for any reason, such as feeling unwell or low blood sugar? | Unclear | “Break your fast” may sound like criticism. Use “Did you need to stop fasting early today because you felt unwell or had low blood sugar?” |
| `fasting_broke_fast` | Roman Urdu | Kya aap ko tabiyat kharab hone ya sugar low hone ki wajah se waqt se pehle roza torna para? | Unclear | “Roza torna” can sound blameful or religiously sensitive. Use “Kya tabiyat kharab hone ya sugar low hone ki wajah se aap ko waqt se pehle roza kholna para?” |
| `fasting_broke_fast` | Urdu | کیا آپ کو طبیعت خراب ہونے یا شوگر کم ہونے کی وجہ سے وقت سے پہلے روزہ توڑنا پڑا؟ | Unclear | “روزہ توڑنا” is understood but can feel judgmental. “کیا طبیعت خراب ہونے یا شوگر کم ہونے کی وجہ سے آپ کو وقت سے پہلے روزہ کھولنا پڑا؟” is gentler. |

## Access Barriers

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `barrier_has_glucometer` | English | Do you currently have a working blood sugar meter and strips at home? | OK | Clear and practical. “Test strips” could be used instead of “strips” if patients may not know which strips are meant. |
| `barrier_has_glucometer` | Roman Urdu | Kya aap ke paas ghar par theek chalne wali sugar check karne ki machine (glucometer) aur strips mojood hain? | OK | Understandable. “Sugar check karne wali machine” is more familiar than the technical name, and the parenthetical helps. |
| `barrier_has_glucometer` | Urdu | کیا آپ کے پاس گھر پر کام کرنے والی شوگر چیک کرنے کی مشین (گلوکو میٹر) اور سٹرپس موجود ہیں؟ | OK | Clear and patient-friendly. “شوگر چیک کرنے والی مشین” is accessible; “ٹیسٹ سٹرپس” may be slightly clearer than “سٹرپس.” |
| `barrier_has_bp_cuff` | English | Do you have a working blood pressure monitor (cuff) available at home? | OK | Clear. “Blood pressure machine” may be more familiar than “monitor,” while “cuff” is useful if the device has a separate arm band. |
| `barrier_has_bp_cuff` | Roman Urdu | Kya aap ke paas ghar par BP check karne wala aala mojood hai? | Unclear | “Aala” is formal and “BP” may be unclear. Use “ghar par blood pressure naapne wali machine mojood hai?” |
| `barrier_has_bp_cuff` | Urdu | کیا آپ کے پاس گھر پر بلڈ پریشر چیک کرنے والا آلہ موجود ہے؟ | Unclear | “آلہ” is formal. “کیا آپ کے گھر میں بلڈ پریشر چیک کرنے والی مشین ہے؟” is more natural for a 65-year-old patient. |
| `barrier_affordability_meds` | English | Has the cost of medicines or test strips made it hard to get what you need recently? | OK | Clear, respectful, and non-judgmental. “Get what you need” could be replaced with “buy your medicines or strips” for greater precision. |
| `barrier_affordability_meds` | Roman Urdu | Kya dawaiyon ya strips ki qeemat ki wajah se aap ke liye inhein khareedna mushkil hua hai? | Unclear | “Inhein” is slightly unclear because it refers to both medicines and strips. Say “dawaiyan ya test strips khareedna mushkil hua hai?” |
| `barrier_affordability_meds` | Urdu | کیا ادویات یا سٹرپس کی قیمت کی وجہ سے آپ کے لیے انہیں خریدنا مشکل ہوا ہے؟ | Unclear | “انہیں” could refer to either medicines or strips. Use “کیا ادویات یا ٹیسٹ سٹرپس کی قیمت کی وجہ سے انہیں خریدنا مشکل ہوا ہے؟” |
| `barrier_ran_out_meds` | English | Have you run out of any of your prescribed medicines recently? | OK | Simple and direct. It does not blame the patient or use frightening language. |
| `barrier_ran_out_meds` | Roman Urdu | Kya haal hi mein aap ki koi tajweez shuda dawa khatam ho gayi thi? | Unclear | “Tajweez shuda” is formal and “khatam ho gayi” could sound like the medicine expired. Use “Kya haal hi mein aap ki koi doctor wali dawa khatam ho gayi thi?” |
| `barrier_ran_out_meds` | Urdu | کیا حال ہی میں آپ کی کوئی تجویز کردہ دوا ختم ہو گئی تھی؟ | Unclear | “تجویز کردہ” is formal and “ختم ہو گئی” may be mistaken for expiry. Consider “کیا حال ہی میں آپ کی کوئی ڈاکٹر کی لکھی ہوئی دوا ختم ہو گئی تھی؟” |
| `barrier_side_effects` | English | Did any side effects or unpleasant symptoms make you stop taking your medication? | Unclear | “Make you stop” may sound blaming. Use “Did you stop taking your medicine because of any side effect or unpleasant symptom?” |
| `barrier_side_effects` | Roman Urdu | Kya kisi side effect ya takleef ki wajah se aap ne dawa lena band ki? | OK | Natural and understandable. “Side effect” is familiar; adding “dawai ka” before it can make the phrase more explicit. |
| `barrier_side_effects` | Urdu | کیا کسی مضر اثر (سائیڈ ایفیکٹ) یا تکلیف کی وجہ سے آپ نے دوا لینا بند کی؟ | Unclear | “مضر اثر” is formal and can sound alarming, although the parenthetical helps. Use “کیا دوا کے کسی سائیڈ ایفیکٹ یا تکلیف کی وجہ سے آپ نے دوا لینا بند کی؟” |

## Sick Day

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `sick_vomiting_diarrhea` | English | Are you currently experiencing vomiting, diarrhoea, or inability to keep fluids down? | Unclear | “Inability to keep fluids down” is medically accurate but formal. Say “Are you vomiting, having diarrhoea, or unable to keep water or other drinks down?” |
| `sick_vomiting_diarrhea` | Roman Urdu | Kya aap ko is waqt ultiyan (vomiting), dast (diarrhea), ya paani na peene ki takleef ho rahi hai? | Unclear | “Paani na peene” means not drinking water, not vomiting fluids back up. Use “paani ya koi mashroob andar na thehrne” or explain “peene ke baad ulti ho jana.” |
| `sick_vomiting_diarrhea` | Urdu | کیا آپ کو اس وقت الٹیاں، دست، یا پانی نہ پینے کی تکلیف ہو رہی ہے؟ | Wrong | The final phrase changes the meaning to difficulty not drinking water. Use “کیا آپ کو اس وقت الٹیاں، دست، یا پانی یا کوئی مشروب پینے کے بعد اندر نہ ٹھہرنے کی تکلیف ہے؟” |
| `sick_fever` | English | Do you currently have a high fever or chills? | OK | Short, clear, and not frightening. “Chills” is a familiar symptom word. |
| `sick_fever` | Roman Urdu | Kya aap ko is waqt taiz bukhaar ya thand lag rahi hai? | OK | Natural and understandable. “Taiz bukhaar” clearly means high fever. |
| `sick_fever` | Urdu | کیا آپ کو اس وقت تیز بخار یا کپکپی ہے؟ | OK | Correct and clear. No scary or incorrect medical wording. |
| `sick_fluid_intake` | English | Are you able to drink water and fluids normally today? | Unclear | “Fluids” is formal. Ask “Can you drink water and other drinks normally today?” |
| `sick_fluid_intake` | Roman Urdu | Kya aap aaj mamool ke mutabiq paani aur liquid cheezein pee pa rahe hain? | Unclear | “Liquid cheezein” is awkward English-heavy wording. Use “paani aur doosray mashroobaat mamool ke mutabiq pee pa rahe hain?” |
| `sick_fluid_intake` | Urdu | کیا آپ آج معمول کے مطابق پانی اور مائع چیزیں پی پا رہے ہیں؟ | Unclear | “مائع چیزیں” is formal. Use “کیا آپ آج معمول کے مطابق پانی اور دوسرے مشروبات پی پا رہے ہیں؟” |

## Wellbeing

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `wellbeing_little_interest` | English | Over the past 2 weeks, have you felt little interest or pleasure in doing things? (Optional - you can skip) | OK | Clear and appropriately optional. “Little interest or pleasure” is standard screening wording, though “not enjoying things you usually enjoy” may be more conversational. |
| `wellbeing_little_interest` | Roman Urdu | Pichle 2 hafto mein, kya aap ne kaam kaaj mein dilchaspi ya khushi ki kami mehsoos ki hai? (Optional - aap skip kar sakte hain) | Unclear | “Kaam kaaj” may sound like work or household tasks only. Use “kya aap ko un kaamon mein dilchaspi ya khushi kam mehsoos hui jo aap aam tor par pasand karte hain?” and translate the optional note fully. |
| `wellbeing_little_interest` | Urdu | گزشتہ 2 ہفتوں میں، کیا آپ نے کام کاج میں دلچسپی یا خوشی کی کمی محسوس کی ہے؟ (اختیاری سوال - آپ چھوڑ سکتے ہیں) | Unclear | “کام کاج” narrows the meaning to chores/work. Consider “کیا آپ کو ان کاموں میں دلچسپی یا خوشی کم محسوس ہوئی جو آپ عام طور پر پسند کرتے ہیں؟” The optional note is clear. |
| `wellbeing_depressed_mood` | English | Over the past 2 weeks, have you been feeling down, depressed, or hopeless? (Optional - you can skip) | Unclear | “Depressed” and “hopeless” may feel heavy but are clinically meaningful. Add “sad or without hope” if a simpler patient explanation is needed, while keeping the optional note. |
| `wellbeing_depressed_mood` | Roman Urdu | Pichle 2 hafto mein, kya aap udasi, mayoosi ya dil bardashtagi mehsoos kar rahe hain? (Optional) | Unclear | “Dil bardashtagi” does not naturally mean hopelessness and may be misunderstood. Use “udasi, mayoosi, ya aisa lagna ke umeed nahi rahi” and translate “optional” as “yeh sawal chhor sakte hain.” |
| `wellbeing_depressed_mood` | Urdu | گزشتہ 2 ہفتوں میں، کیا آپ اداسی، مایوسی یا دل برداشتگی محسوس کر رہے ہیں؟ (اختیاری سوال) | Unclear | “دل برداشتگی” can mean hurt or resentment rather than hopelessness. Use “اداسی، مایوسی، یا ایسا محسوس ہونا کہ کوئی امید نہیں رہی” and add “آپ یہ سوال چھوڑ سکتے ہیں” for clarity. |
| `wellbeing_overwhelmed` | English | Have you felt overwhelmed by the daily demands of managing your condition? (Optional - you can skip) | Unclear | “Overwhelmed” and “daily demands” are formal. Use “Have the daily tasks of looking after your condition felt like too much?” and keep the skip option explicit. |
| `wellbeing_overwhelmed` | Roman Urdu | Kya aap apni bimari ki rozana dekh bhaal aur dawaiyon se bojh mehsoos kar rahe hain? (Optional) | Unclear | “Bojh mehsoos karna” is understandable but the sentence can sound like the medicines themselves are a burden. Use “Kya rozana bimari ki dekh bhaal aur dawai lena aap ko bahut zyada mushkil lagta hai?” and translate the optional note. |
| `wellbeing_overwhelmed` | Urdu | کیا آپ اپنی بیماری کی روزانہ دیکھ بھال اور دوائیوں سے بیزاری یا بوجھ محسوس کر رہے ہیں؟ (اختیاری سوال) | Unclear | “بیزاری” suggests dislike or aversion and is stronger than “overwhelmed.” Use “کیا بیماری کی روزانہ دیکھ بھال اور دوائی لینا آپ کو بہت زیادہ مشکل یا بوجھ لگتا ہے؟” and add “آپ یہ سوال چھوڑ سکتے ہیں.” |

## Caregiver

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `caregiver_answered_by` | English | Who is answering the questions today? | OK | Short, clear, and neutral. The answer choices should use familiar labels such as “patient,” “family member,” or “caregiver.” |
| `caregiver_answered_by` | Roman Urdu | Aaj in sawalaat ke jawabaat kaun de raha hai? | OK | Natural and easy to understand. A gender-neutral “kaun jawab de raha hai?” is also acceptable in conversation. |
| `caregiver_answered_by` | Urdu | آج ان سوالات کے جوابات کون دے رہا ہے؟ | OK | Clear and neutral. No medical or frightening wording. |
| `caregiver_relationship` | English | What is your relationship to the patient (for example son, daughter, spouse)? | Unclear | “Spouse” is formal. Use “husband or wife” or “partner” if that matches the intended choices; include other family or non-family caregivers. |
| `caregiver_relationship` | Roman Urdu | Mareez ke sath aap ka kya rishta hai (maslan beta, beti, shareek-e-hayat)? | Unclear | “Mareez” can sound clinical and “shareek-e-hayat” is formal. Use “jis shakhs ke liye aap jawab de rahe hain, un se aap ka kya rishta hai? (beta, beti, shohar, biwi, ya koi aur)” |
| `caregiver_relationship` | Urdu | مریض کے ساتھ آپ کا کیا رشتہ ہے (مثلاً بیٹا، بیٹی، شریک حیات)؟ | Unclear | “مریض” is clinical and “شریک حیات” is formal. Consider “جس شخص کے لیے آپ جواب دے رہے ہیں، ان سے آپ کا کیا رشتہ ہے؟ (بیٹا، بیٹی، شوہر، بیوی، یا کوئی اور)” |

## Probes

| Item id | Language | Wording | OK / Unclear / Wrong | Suggested fix |
|---|---|---|---|---|
| `probe_dizziness_postural` | English | Does the dizziness happen mainly when you stand up from sitting or lying down? | OK | Clear. “Stand up from sitting or lying down” is understandable for older patients. |
| `probe_dizziness_postural` | Roman Urdu | Kya chakkar khaas tor par baithne ya leitne se kharay hone par aate hain? | OK | Natural and clear. “Leitne” may also be spelled “letne,” but the meaning is understandable. |
| `probe_dizziness_postural` | Urdu | کیا چکر خاص طور پر بیٹھنے یا لیٹنے سے کھڑے ہونے پر آتے ہیں؟ | OK | Clear and medically appropriate without alarming language. |
| `probe_dizziness_falls` | English | Has the dizziness caused you to stumble, fall, or lose your balance? | OK | Direct and easy to answer. “Stumble” may be less familiar than “nearly fall,” but the list clarifies it. |
| `probe_dizziness_falls` | Roman Urdu | Kya chakkaro ki wajah se aap larkharaye, giray, ya balance kho baithay? | Unclear | “Balance” is common but English-heavy. Use “larhkharaaye, giray, ya apna tawazun kho diya?” |
| `probe_dizziness_falls` | Urdu | کیا چکروں کی وجہ سے آپ لڑکھڑائے، گرے، یا توازن کھو بیٹھے؟ | OK | Correct and understandable. “توازن کھو بیٹھے” is slightly formal but clear. |
| `probe_headache_onset` | English | Did this headache come on suddenly, or has it built up gradually? | OK | Clear contrast between sudden and gradual onset. |
| `probe_headache_onset` | Roman Urdu | Kya yeh sar dard achanak shuru hua, ya aahista aahista barha hai? | OK | Natural and easy to understand. |
| `probe_headache_onset` | Urdu | کیا یہ سر درد اچانک شروع ہوا، یا آہستہ آہستہ بڑھا ہے؟ | OK | Clear and accurate. |
| `probe_headache_severity` | English | On a scale from 1 to 10 (where 10 is the most severe pain), how would you rate this headache? | Unclear | The scale is standard but may need a simple explanation: “1 means very little pain and 10 means the worst pain.” |
| `probe_headache_severity` | Roman Urdu | 1 se 10 ke scale par (jahan 10 shadeed tareen dard hai), aap is sar dard ko kya number dein ge? | Unclear | “Shadeed tareen” is formal. Explain the endpoints as “1 bahut halka dard, 10 sab se zyada dard.” |
| `probe_headache_severity` | Urdu | 1 سے 10 کے پیمانے پر (جہاں 10 شدید ترین درد ہے)، آپ اس سر درد کو کیا نمبر دیں گے؟ | Unclear | “پیمانہ” and “شدید ترین” are formal. Explain “1 ہلکا درد اور 10 سب سے زیادہ درد” for older patients. |
| `probe_breathlessness_pattern` | English | Does the breathlessness happen while resting quietly, or only when you exert yourself? | Unclear | “Exert yourself” is formal. Use “when you are walking or doing something” for clearer patient language. |
| `probe_breathlessness_pattern` | Roman Urdu | Kya saans aaram se baithay hue bhi phoolta hai, ya sirf chalnay phirnay par? | OK | Natural and clear. |
| `probe_breathlessness_pattern` | Urdu | کیا سانس آرام سے بیٹھے ہوئے بھی پھولتا ہے، یا صرف چلنے پھرنے پر؟ | OK | Clear and suitable for an older patient. |
| `probe_breathlessness_orthopnea` | English | Does your breathing feel noticeably worse when you lie completely flat in bed? | Unclear | “Noticeably worse” and “completely flat” are slightly formal. Say “Does it become harder to breathe when you lie flat in bed?” |
| `probe_breathlessness_orthopnea` | Roman Urdu | Kya bistar par bilkul seedha leitne se saans ziada kharab mehsoos hota hai? | Unclear | “Saans zyada kharab” can sound vague. Use “kya bistar par seedha letne se saans lena mushkil ho jata hai?” |
| `probe_breathlessness_orthopnea` | Urdu | کیا بستر پر بالکل سیدھا لیٹنے سے سانس زیادہ خراب محسوس ہوتا ہے؟ | Unclear | “سانس زیادہ خراب” is understandable but awkward. Use “کیا بستر پر سیدھا لیٹنے سے سانس لینا مشکل ہو جاتا ہے؟” |
| `probe_chest_discomfort_exertion` | English | Does the discomfort happen with physical exertion, or when resting quietly? | Unclear | “Physical exertion” is medical/formal. Use “when walking or doing physical work, or while resting?” |
| `probe_chest_discomfort_exertion` | Roman Urdu | Kya yeh takleef jismani mushaqat ke waqt hoti hai ya aaram se baithay hue bhi? | Unclear | “Jismani mushaqat” is formal. Use “chalne ya mehnat karne ke waqt” for natural speech. |
| `probe_chest_discomfort_exertion` | Urdu | کیا یہ تکلیف جسمانی مشقت کے وقت ہوتی ہے یا آرام سے بیٹھے ہوئے بھی؟ | Unclear | “جسمانی مشقت” is correct but formal. “چلنے یا کام کرنے کے وقت” may be easier. |
| `probe_vision_type` | English | Is your vision generally blurry, or are you seeing spots, floaters, or dark patches? | Unclear | “Floaters” is technical. Explain it as “small moving spots or lines” if that option is shown to patients. |
| `probe_vision_type` | Roman Urdu | Kya aam tor par dhundla nazar aa raha hai, ya kaalay dhabay (spots) dikhayi de rahe hain? | Unclear | The source lists floaters but the wording only says dark spots. Add “chaltay hue nuqtay ya dhabay” if floaters are intended. |
| `probe_vision_type` | Urdu | کیا عام طور پر دھندلا نظر آ رہا ہے، یا کالے دھبے اور پردے دکھائی دے رہے ہیں؟ | Unclear | “پردے” may sound like a curtain and could be confusing. Say “کالے دھبے، تیرتے ہوئے نقطے، یا نظر کے آگے سایہ” if clinically intended. |
| `probe_thirst_intensity` | English | Are you feeling much thirstier than usual, or needing to get up multiple times at night to pass urine? | OK | Clear, though “pass urine” could be “urinate” in formal English; the current version is patient-friendly. |
| `probe_thirst_intensity` | Roman Urdu | Kya aap ko mamool se bohat ziada pyas lag rahi hai ya raat ko bar bar peshab ke liye uthna par raha hai? | OK | Natural and understandable. |
| `probe_thirst_intensity` | Urdu | کیا آپ کو معمول سے بہت زیادہ پیاس لگ رہی ہے یا رات کو بار بار پیشاب کے لیے اٹھنا پڑ رہا ہے؟ | OK | Clear and respectful. |
| `probe_foot_open_wound` | English | Is there an open wound, break in the skin, or bleeding on your foot? | Unclear | “Break in the skin” is formal. Say “an open cut, wound, or bleeding on your foot?” |
| `probe_foot_open_wound` | Roman Urdu | Kya paon par koi khula zakham, skin ka phatna, ya khoon ka bahao hai? | Unclear | “Skin ka phatna” is English-heavy and “khoon ka bahao” is formal. Use “khula zakhm, jild par cut, ya khoon nikal raha hai?” |
| `probe_foot_open_wound` | Urdu | کیا پاؤں پر کوئی کھلا زخم، جلد کا پھٹنا، یا خون کا بہاؤ ہے؟ | Unclear | “جلد کا پھٹنا” and “خون کا بہاؤ” are formal. Use “کوئی کھلا زخم، جلد پر کٹ، یا خون نکل رہا ہے؟” |
| `probe_foot_redness_warmth` | English | Is the area red, hot to touch, or swollen? | OK | Short and clear. |
| `probe_foot_redness_warmth` | Roman Urdu | Kya woh jagah surkh, chhoonay par garam, ya sooji hui hai? | OK | Understandable. “Surkh” could be replaced with “laal” for more conversational speech. |
| `probe_foot_redness_warmth` | Urdu | کیا وہ جگہ سرخ، چھونے پر گرم، یا سوجی ہوئی ہے؟ | OK | Clear and natural. |
| `probe_hypo_recovery` | English | Did your symptoms improve within 15 minutes after eating or drinking fast-acting sugar (like juice or sweets)? | Unclear | “Fast-acting sugar” is technical. Say “something sugary that works quickly, such as juice or sweets.” |
| `probe_hypo_recovery` | Roman Urdu | Kya meetha khanay ya juice peenay ke 15 minute ke andar alamaat theek ho gayi theen? | OK | Clear and easy to understand. “Alamat” is slightly formal but the examples are concrete. |
| `probe_hypo_recovery` | Urdu | کیا میٹھا کھانے یا جوس پینے کے 15 منٹ کے اندر علامات بہتر ہو گئی تھیں؟ | OK | Clear and appropriately specific. |
| `probe_missed_dose_reason` | English | What made it hard to take your medicine (for example: ran out, side effects, cost, or forgot)? | Unclear | The list is useful, but “ran out” needs an object. Say “your medicine ran out, side effects, cost, or forgetting?” |
| `probe_missed_dose_reason` | Roman Urdu | Dawa lene mein kya mushkil pesh aayi (maslan: dawa khatam ho gayi, side effects, qeemat, ya bhool gaye)? | Unclear | “Mushkil pesh aayi” is formal. Use “dawa lena mushkil kyun hua? Dawa khatam ho gayi, side effect, qeemat, ya bhool ki wajah se?” |
| `probe_missed_dose_reason` | Urdu | دوا لینے میں کیا مشکل پیش آئی (مثلاً: دوا ختم ہو گئی، سائیڈ ایفیکٹس، لاگت، یا بھول گئے)؟ | Unclear | “مشکل پیش آئی” and “لاگت” are formal. Use “دوا لینا مشکل کیوں ہوا؟ دوا ختم ہو گئی، سائیڈ ایفیکٹ، قیمت، یا بھولنے کی وجہ سے؟” |
| `probe_swelling_location` | English | Is the swelling in both ankles/feet, in one leg only, or in your hands/face? | OK | Clear location choices. “Ankles/feet” could be shown as separate choices if precision matters. |
| `probe_swelling_location` | Roman Urdu | Kya sojan dono takhno/paon par hai, sirf aik taang par, ya haatho aur chehray par? | OK | Understandable. Use “dono takhnon ya paon par” for more natural grammar. |
| `probe_swelling_location` | Urdu | کیا سوجن دونوں ٹخنوں اور پاؤں پر ہے، صرف ایک ٹانگ پر، یا ہاتھوں اور چہرے پر؟ | OK | Clear and accurate. |
| `probe_tiredness_duration` | English | Has this tiredness lasted just today, for a few days, or for several weeks? | OK | Simple and easy to answer. |
| `probe_tiredness_duration` | Roman Urdu | Kya yeh thakawat sirf aaj se hai, chand dino se, ya kai hafto se? | OK | Natural and clear. |
| `probe_tiredness_duration` | Urdu | کیا یہ تھکاوٹ صرف آج سے ہے، چند دنوں سے، یا کئی ہفتوں سے؟ | OK | Clear and patient-friendly. |
| `probe_vomiting_fluid_retention` | English | Are you able to keep sips of water or fluids down without vomiting? | Unclear | “Keep ... down” is idiomatic. Use “Can you drink small sips of water without vomiting?” |
| `probe_vomiting_fluid_retention` | Roman Urdu | Kya aap paani ya liquid cheezein baghair ulti ke pee pa rahe hain? | Unclear | “Liquid cheezein” is awkward and “small sips” is omitted. Use “kya aap paani ke chhotay ghont pee kar ulti se bach pa rahe hain?” |
| `probe_vomiting_fluid_retention` | Urdu | کیا آپ پانی یا مائع چیزیں بغیر الٹی کے پی پا رہے ہیں؟ | Unclear | “مائع چیزیں” is formal and the small-sips meaning is omitted. Use “کیا آپ پانی کے چھوٹے گھونٹ پی کر بغیر الٹی کے رکھ پا رہے ہیں؟” |
| `probe_pain_location_severity` | English | On a scale from 1 to 10, how severe is this pain? | Unclear | Add the endpoint explanation: “1 is very mild and 10 is the worst pain.” |
| `probe_pain_location_severity` | Roman Urdu | 1 se 10 ke scale par, yeh dard kitna shadeed hai? | Unclear | “Shadeed” is formal. Say “1 se 10 tak, dard kitna zyada hai?” and explain what 1 and 10 mean. |
| `probe_pain_location_severity` | Urdu | 1 سے 10 کے پیمانے پر، یہ درد کتنا شدید ہے؟ | Unclear | “پیمانہ” and “شدید” are formal. Say “1 سے 10 تک، درد کتنا زیادہ ہے؟” and explain the endpoints. |
| `probe_sleep_cause` | English | Is difficulty sleeping mainly due to pain, shortness of breath, anxiety, or needing to pass urine? | Unclear | “Anxiety” and “pass urine” are formal. Use “worry or fear” and “needing to get up to urinate.” |
| `probe_sleep_cause` | Roman Urdu | Kya neend mein dushwari ki wajah dard, saans ki tangi, be chaini ya bar bar peshab aana hai? | Unclear | “Dushwari” and “be chaini” are formal. Use “neend na aane ki wajah dard, saans ki tangi, fikr, ya bar bar peshab aana hai?” |
| `probe_sleep_cause` | Urdu | کیا نیند میں دشواری کی وجہ درد، سانس کی تنگی، بے چینی یا بار بار پیشاب آنا ہے؟ | Unclear | “دشواری” and “بے چینی” are formal but correct. “فکر” may be more familiar than “بے چینی” for anxiety in this context. |
| `probe_low_mood_frequency` | English | Have you been feeling down or discouraged nearly every day over the past two weeks? | OK | Clear and gentle. “Discouraged” is less alarming than a diagnostic label. |
| `probe_low_mood_frequency` | Roman Urdu | Kya aap pichle do hafto ke dauran taqreeban rozana udasi ya mayoosi mehsoos kar rahe hain? | OK | Understandable. “Taqreeban” is slightly formal; “lagbhag” is also familiar. |
| `probe_low_mood_frequency` | Urdu | کیا آپ گزشتہ دو ہفتوں کے دوران تقریباً روزانہ اداسی یا مایوسی محسوس کر رہے ہیں؟ | OK | Correct and respectful. |
| `probe_other_symptom_onset` | English | When did you first notice this symptom (today, yesterday, or longer ago)? | OK | Clear and easy to answer. |
| `probe_other_symptom_onset` | Roman Urdu | Aap ne yeh alamat sab se pehle kab mehsoos ki (aaj, kal, ya is se pehle)? | Unclear | “Alamat” is formal. Use “yeh takleef ya sehat ki yeh baat” for a more familiar patient phrase. |
| `probe_other_symptom_onset` | Urdu | آپ نے یہ علامت سب سے پہلے کب محسوس کی (آج، کل، یا اس سے پہلے)؟ | Unclear | “علامت” is correct but formal. “یہ تکلیف” may be easier for a 65-year-old patient. |
