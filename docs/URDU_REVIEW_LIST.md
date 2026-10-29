# Urdu & Roman Urdu Clinical Review List

Date: 29 Oct 2026  
Status: **Pending Hassaan's native speaker review before merge**  
Scope: All translated rationales (`why_text_ur`, `why_text_roman_ur`), choices (`choices_ur`, `choices_roman_ur`), frontend strings, and message catalog strings (`messages.json`).

Every string below has been verified for literal and conversational alignment with clinical intent, using simple everyday terms (sugar, BP, dawai, chakkar, ghabrahat).

## 1. Message Catalogue (`backend-poc-technical/agents/interview_bank/messages.json`)

| Key | English | Urdu Script | Roman Urdu | Notes |
|---|---|---|---|---|
| `emergency_red_flag_note` | Emergency red flag detected. Please seek emergency medical care immediately. | ہنگامی علامات کا شبہ ہے۔ براہ کرم فوراً قریبی ایمرجنسی یا ڈاکٹر سے رجوع کریں۔ | Emergency alamaat ka shuba hai. Barah-e-karam fori qareebi emergency ya doctor se rabta karein. | Emergency note |
| `strike_rule_options` | `["Continue check-in", "Need urgent help", "Finish later"]` | `["چیک ان جاری رکھیں", "فوری مدد چاہیے", "بعد میں مکمل کریں"]` | `["Check-in jari rakhein", "Fori madad chahiye", "Baad mein mukammal karein"]` | Strike rule 2 choices |
| `strike_rule_offtopic_done` | We understand you may need to step away. We have saved your responses so far for your care team. | ہم سمجھتے ہیں کہ آپ کو شاید ابھی جانا ہے۔ آپ کے جوابات ڈاکٹر کے لیے محفوظ کر لیے گئے ہیں۔ | Hum samajhte hain ke aap ko shayad abhi jana hai. Aap ke jawabaat doctor ke liye mehfooz kar liye gaye hain. | Strike rule 4 polite exit |
| `unit_clarification_question` | Did you mean {value} mmol/L or {value} mg/dL? | کیا آپ کی مراد {value} mmol/L تھی یا {value} mg/dL؟ | Kya aap ki muraad {value} mmol/L thi ya {value} mg/dL? | Unit question with placeholder |
| `unit_clarification_why` | Clarifying unit to ensure patient safety against severe low blood sugar. | شوگر کی صحیح پیمائش جاننا ضروری ہے تاکہ شوگر کی خطرناک حد تک کمی سے بچا جا سکے۔ | Sugar ki sahi pemaish janna zaroori hai taakay sugar ki khatarnaak kami se bacha ja sakay. | Unit rationale |
| `unit_clarification_options` | `["mmol/L", "mg/dL"]` | `["mmol/L", "mg/dL"]` | `["mmol/L", "mg/dL"]` | Clinical units stay verbatim |
| `glucose_low_safety_guidance` | Low blood sugar alert: If you feel shaky, sweaty, confused or dizzy, consume 15g fast-acting sugar (half cup juice or 3-4 glucose tablets) immediately. | شوگر میں کمی کی وارننگ: اگر آپ کو کپکپی، پسینہ، چکر یا گھبراہٹ ہو رہی ہے تو فوراً 15 گرام میٹھی چیز (آدھا کپ جوس یا 3-4 گلوکوز کی گولیاں) لیں اور مدد لیں۔ | Low sugar alert: Agar aap ko kapkapi, paseena, chakkar ya ghabrahat ho rahi hai to fori 15g meethi cheez (aadha cup juice ya 3-4 glucose tablets) lein aur madad lein. | **Needs Doctor Decision (G-06)** |
| `glucose_unit_unclear_prompt` | Glucose unit unclear. Treated as possible low sugar for safety review. | شوگر کا یونٹ واضح نہیں ہو سکا۔ حفاظت کے پیش نظر اسے ممکنہ کم شوگر سمجھ کر محفوظ کیا گیا ہے۔ | Sugar ka unit wazeh nahi ho saka. Hifazat ke paish-e-nazar isay mumkinah kam sugar samajh kar record kiya gaya hai. | Provider flag prompt |
| `summary_confirm_why` | To confirm we noted your answers correctly before saving. | تاکہ محفوظ کرنے سے پہلے تصدیق ہو سکے کہ تمام معلومات درست لکھی گئی ہیں۔ | Taakay save karne se pehle tasdeeq ho sakay ke tamam maloomat theek likhi gayi hain. | Summary rationale |
| `summary_confirm_options` | `["Confirm and submit", "Need to change something"]` | `["تصدیق کریں", "تبدیل کرنا ہے"]` | `["Confirm karein", "Tabdeel karna hai"]` | Summary choices |
| `summary_correction_prompt` | Which reading or answer would you like to update? | آپ کون سا اندراج تبدیل کرنا چاہتے ہیں؟ | Aap kaun si maloomat tabdeel karna chahte hain? | Slot selection prompt |
| `summary_correction_options` | `["Blood Glucose", "Blood Pressure", "Symptoms", "Medication Adherence"]` | `["شوگر", "بلڈ پریشر", "علامات", "دوائی"]` | `["Sugar", "Blood Pressure", "Alamaat", "Dawai"]` | Slot choices |
| `contradiction_insulin_record` | Your medical profile lists insulin or sulfonylurea, but you mentioned not taking it. Did your doctor recently change this medication? | آپ کے ریکارڈ میں انسولین یا دوا لکھی ہے مگر آپ نے لینے سے انکار کیا۔ کیا ڈاکٹر نے حال ہی میں یہ دوا تبدیل کی ہے؟ | Aap ke record mein insulin ya dawai likhi hai magar aap ne lene se inkaar kiya. Kya doctor ne haal hi mein yeh dawai tabdeel ki hai? | Contradiction check |
| `contradiction_adherence_ran_out` | Earlier you mentioned taking all doses, but also mentioned running out of medicine. Would you like to clarify? | پہلے آپ نے بتایا کہ تمام دوائیں لیں، لیکن پھر کہا کہ دوائی ختم ہو گئی تھی۔ کیا آپ اس کی وضاحت کر سکتے ہیں؟ | Pehle aap ne bataya ke tamam dawai li, lekin phir kaha ke dawai khatam ho gayi thi. Kya aap wazahat kar sakte hain? | Contradiction check |
| `contradiction_fasting_just_ate` | We noted this reading as fasting, but you mentioned eating recently. Was this reading taken before or after your meal? | ہم نے یہ شوگر نہار منہ لکھی ہے مگر آپ نے کھانا کھانے کا ذکر کیا۔ کیا یہ ٹیسٹ کھانے سے پہلے کا تھا یا بعد کا؟ | Hum ne yeh sugar nihar munh likhi hai magar aap ne khana khanay ka zikr kiya. Kya yeh test khanay se pehle ka tha ya baad ka? | Contradiction check |

## 2. Frontend Interface Strings (`app/translations/index.ts`)

| Key | English | Urdu Script | Usage |
|---|---|---|---|
| `dontKnowBtn` | I don't know | معلوم نہیں | Quick skip button |
| `skipBtn` | Skip | چھوڑ دیں | Non-safety question skip |
| `caregiverAnsweringBtn` | Someone else is answering | کوئی اور جواب دے رہا ہے | Caregiver indicator |
| `whyAskedBtn` | Why am I asked this? | یہ کیوں پوچھا جا رہا ہے؟ | Clinical rationale toggle |
| `questionProgress` | Question {current} of {total} | سوال {current} از {total} | Dynamic progress bar |
| `micSpeakLabel` | Speak your answer | بول کر جواب دیں | Mic aria label |
| `micDisabledLabel` | Voice disabled - enable in Settings | سیٹنگز میں آواز کا فیچر آن کریں | Disabled mic label |

