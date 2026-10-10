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
