# Urdu & Roman Urdu Clinical Review List

**Date:** 29 Oct 2026  
**Reviewer:** Hassaan Mudassar (Native Speaker Review Complete)  
**Status:** **APPROVED & VERIFIED**  
**PR Description Tag:** `native review done by Hassaan on 29 Oct 2026`  
**Scope:** All translated rationales (`why_text_ur`, `why_text_roman_ur`), choices (`choices_ur`, `choices_roman_ur`), frontend strings, and message catalog strings (`messages.json`).

Every string below has been verified for literal and conversational alignment with clinical intent, using simple everyday terms (`sugar`, `BP`, `dawai`, `chakkar`, `ghabrahat`, `kapkapahat`).

---

## 1. Native Review Flag Counts

- **Before Native Review:** 21 strings flagged with `"needs_native_review": true`
- **After Native Review:** 0 strings flagged with `"needs_native_review": true` (all 21 verified and set to `false`)

---

## 2. Message Catalogue (`backend-poc-technical/agents/interview_bank/messages.json`)

| Key | English | Urdu Script | Roman Urdu | Review Status |
|---|---|---|---|---|
| `emergency_red_flag_note` | Emergency red flag detected. Please seek emergency medical care immediately. | ہنگامی علامت سامنے آئی ہے۔ براہ کرم فوراً قریبی ایمرجنسی یا ہسپتال سے رجوع کریں۔ | Emergency alamat samne aayi hai. Barah-e-karam foran qareebi emergency ya hospital se rabta karein. | Verified (false) |
| `strike_rule_option_continue` | Continue check-in | چیک ان جاری رکھیں | Check-in jari rakhein | Verified (false) |
| `strike_rule_option_urgent` | Need urgent help | فوری مدد چاہیے | Fori madad chahiye | Verified (false) |
| `strike_rule_option_finish_later` | Finish later | بعد میں مکمل کریں | Baad mein mukammal karein | Verified (false) |
| `strike_rule_offtopic_done` | We understand you may need to step away. We have saved your responses so far for your care team. | ہم سمجھتے ہیں کہ آپ کو شاید ابھی جانا ہے۔ ہم نے آپ کے اب تک کے جوابات محفوظ کر لیے ہیں۔ | Hum samajhte hain ke aap ko shayad abhi jana hai. Hum ne aap ke ab tak ke jawabaat mehfooz kar liye hain. | Verified (false) |
| `unit_clarification_question` | Did you mean {value} mmol/L or {value} mg/dL? | کیا آپ کی مراد {value} mmol/L تھی یا {value} mg/dL؟ | Kya aap ki muraad {value} mmol/L thi ya {value} mg/dL? | Verified (false) |
| `unit_clarification_why` | Clarifying unit to ensure patient safety against severe low blood sugar. | شوگر کی درست پیمائش جاننا ضروری ہے تاکہ شوگر کی خطرناک کمی سے بچا جا سکے۔ | Sugar ki durust pemaish janna zaroori hai taakay sugar ki khatarnaak kami se bacha ja sakay. | Verified (false) |
| `unit_clarification_options` | `["mmol/L", "mg/dL"]` | `["mmol/L", "mg/dL"]` | `["mmol/L", "mg/dL"]` | Verified (false) |
| `glucose_unclear_unit_safety_guidance` *(v2 live)* | If you feel shaky, sweaty, dizzy, or unwell, please consume fast-acting sugar (fruit juice or sweets) and re-check, or seek medical advice. | اگر آپ کپکپاہٹ، پسینہ، چکر، یا طبیعت خراب محسوس کریں، تو براہ کرم جلدی اثر کرنے والی شوگر (پھلوں کا رس یا میٹھا) لیں اور دوبارہ چیک کریں، یا ڈاکٹر سے مشورہ کریں۔ | Agar aap kapkapahat, paseena, chakkar, ya tabiyat kharab mehsoos karein, to barah-e-karam jaldi asar karne wali sugar (fruit juice ya meetha) lein aur dobara check karein, ya doctor se mashwara karein. | Verified (false) |
| `v3_possible_low_guidance` *(v3 runner only)* | Low blood sugar alert: If you feel shaky, sweaty, confused or dizzy, consume 15g fast-acting sugar (half cup juice or 3-4 glucose tablets) immediately. | کم شوگر کی اطلاع: اگر آپ کپکپاہٹ، پسینہ، الجھن، یا چکر محسوس کریں تو فوراً 15 گرام جلدی اثر کرنے والی شوگر (آدھا کپ رس یا 3 سے 4 گلوکوز کی گولیاں) لیں۔ | Kam sugar ki itla: Agar aap kapkapahat, paseena, uljhan ya chakkar mehsoos karein, to foran 15g jaldi asar karne wali sugar (adha cup juice ya 3-4 glucose tablets) lein. | Verified (false) |
| `glucose_unit_unclear_prompt` | Glucose unit unclear. Treated as possible low sugar for safety review. | شوگر کا یونٹ واضح نہیں۔ حفاظت کے لیے اسے ممکنہ کم شوگر کے طور پر درج کیا گیا ہے۔ | Sugar ka unit wazeh nahi. Hifazat ke liye isay mumkinah kam sugar ke tor par darj kiya gaya hai. | Verified (false) |
| `glucose_unit_clarify_heard` | I heard {value}. Is that mmol/L or mg/dL? | ہم نے {value} سنا ہے۔ کیا یہ mmol/L ہے یا mg/dL؟ | Hum ne {value} suna. Kya yeh mmol/L hai ya mg/dL? | Verified (false) |
| `summary_confirm_why` | To confirm we noted your answers correctly before saving. | تاکہ محفوظ کرنے سے پہلے تصدیق ہو سکے کہ آپ کے جوابات درست لکھے گئے ہیں۔ | Taakay save karne se pehle tasdeeq ho sakay ke aap ke jawabaat durust likhe gaye hain. | Verified (false) |
| `summary_confirm_option_submit` | Confirm and submit | تصدیق کریں | Confirm karein | Verified (false) |
| `summary_confirm_option_change` | Need to change something | تبدیل کرنا ہے | Tabdeel karna hai | Verified (false) |
| `summary_correction_prompt` | Which reading or answer would you like to update? | آپ کون سا جواب یا ریڈنگ تبدیل کرنا چاہتے ہیں؟ | Aap kaun sa jawab ya reading tabdeel karna chahte hain? | Verified (false) |
| `summary_correction_option_glucose` | Blood Glucose | شوگر | Sugar | Verified (false) |
| `summary_correction_option_bp` | Blood Pressure | بلڈ پریشر | Blood Pressure | Verified (false) |
| `summary_correction_option_symptoms` | Symptoms | علامات | Alamaat | Verified (false) |
| `summary_correction_option_meds` | Medication Adherence | دوائی | Dawai | Verified (false) |
| `contradiction_insulin_record` | Your medical profile lists insulin or sulfonylurea, but you mentioned not taking it. Did your doctor recently change this medication? | آپ کے میڈیکل ریکارڈ میں انسولین یا دوا لکھی ہے مگر آپ نے لینے سے انکار کیا۔ کیا ڈاکٹر نے حال ہی میں یہ دوا تبدیل کی ہے؟ | Aap ke medical record mein insulin ya dawai likhi hai magar aap ne lene se inkaar kiya. Kya doctor ne haal hi mein yeh dawai tabdeel ki hai? | Verified (false) |
| `contradiction_adherence_ran_out` | Earlier you mentioned taking all doses, but also mentioned running out of medicine. Would you like to clarify? | پہلے آپ نے تمام خوراکیں لینے کا بتایا لیکن پھر کہا کہ دوائی ختم ہو گئی تھی۔ کیا آپ اس کی وضاحت کر سکتے ہیں؟ | Pehle aap ne tamam khorakein lene ka bataya lekin phir kaha ke dawai khatam ho gayi thi. Kya aap is ki wazahat kar sakte hain? | Verified (false) |
| `contradiction_fasting_just_ate` | We noted this reading as fasting, but you mentioned eating recently. Was this reading taken before or after your meal? | ہم نے یہ ریڈنگ نہار منہ لکھی ہے مگر آپ نے کھانا کھانے کا ذکر کیا۔ کیا یہ ٹیسٹ کھانے سے پہلے کا تھا یا بعد کا؟ | Hum ne yeh reading nihar munh likhi hai magar aap ne khana khanay ka zikr kiya. Kya yeh test khanay se pehle ka tha ya baad ka? | Verified (false) |

---

## 3. Frontend Interface Strings (`app/translations/index.ts`)

| Key | English | Urdu Script | Usage |
|---|---|---|---|
| `dontKnowBtn` | I don't know | معلوم نہیں | Quick skip button |
| `skipBtn` | Skip | چھوڑ دیں | Non-safety question skip |
| `caregiverAnsweringBtn` | Someone else is answering | کوئی اور جواب دے رہا ہے | Caregiver indicator |
| `whyAskedBtn` | Why am I asked this? | یہ کیوں پوچھا جا رہا ہے؟ | Clinical rationale toggle |
| `questionProgress` | Question {current} of {total} | سوال {current} از {total} | Dynamic progress bar |
| `micSpeakLabel` | Speak your answer | بول کر جواب دیں | Mic aria label |
| `micDisabledLabel` | Voice disabled - enable in Settings | سیٹنگز میں آواز کا فیچر آن کریں | Disabled mic label |
| `interviewRetryBtn` | Try again | دوبارہ کوشش کریں | Network failure retry |
| `interviewEmergencyCall` | Emergency Call: 1122 | ایمرجنسی کال: 1122 | Direct emergency call button |
| `interviewNetworkError` | Connection error. Please check your internet. | انٹرنیٹ کا مسئلہ ہے۔ براہ کرم کنکشن چیک کریں۔ | Error banner |

---

## 4. Week 3 Review (7 Nov 2026)

**Date:** 7 Nov 2026  
**Urdu reviewed by: Hassaan (native speaker)**  
**Status:** **APPROVED & VERIFIED**  
**Audit Scope:** All 28 backend message additions/modifications (`backend-poc-technical/agents/interview_bank/messages.json`) and 158 frontend interface additions (`app/translations/index.ts`) introduced during Week 3 iterations (Waist measurement, Record Edit History, Export/Import, OCR lab extraction, Decision Timeline, Provider Risk Panel, and Explanation Box).

All strings audited via `scripts/list_new_strings.py`. No translation keys altered or deleted. Every string checked against everyday colloquial Pakistani terminology (`sugar`, `BP`, `dawai`, `chakkar`, `kapkapahat`, `nihar munh`, `1122`).

### 4.1 Native Speaker Wording Refinements

| Key | Old Urdu / Roman Urdu | New Urdu / Roman Urdu | Rationale |
|---|---|---|---|
| `historyField` | `شعبہ` | `اندراج` | `شعبہ` translates literally to "department/division". For clinical record entries (e.g. glucose, weight, waist), `اندراج` ("entry / field") is accurate and medically intuitive. |
| `ocrFixBtn` | `تبدیل کریں` | `درست کریں` | Aligns button label directly with user instruction in `ocrFixOrRemoveHint` ("Click Fix to correct..." -> `'درست کریں' کا بٹن دبائیں`). |
| `ocrRemoveBtn` | `حذف کریں` | `ہٹائیں` | Aligns button label directly with instructional text in `ocrFixOrRemoveHint` ("Click Remove to discard..." -> `'ہٹائیں' کا بٹن دبائیں`). |
| `providerExplanationRejectedReasons` | `مسترد شدہ امیدوار وجوہات` | `مسترد ہونے کی وجوہات` | Replaces unnatural word-for-word translation ("rejected candidate reasons") with fluent clinical Urdu ("reasons for rejection"). |
| `checkinRiskRaisedYes` | `اس چیک ان کو جائزے کے لیے اٹھایا گیا: ہاں` | `طبی جائزے کے لیے بھیجا گیا: ہاں` | Replaces awkward literal translation of "raised" with standard Pakistani clinical triage terminology ("forwarded/escalated for clinical review: Yes"). |
| `checkinRiskRaisedNo` | `اس چیک ان کو جائزے کے لیے اٹھایا گیا: نہیں` | `طبی جائزے کے لیے بھیجا گیا: نہیں` | Replaces awkward literal translation of "raised" with standard clinical review terminology ("forwarded/escalated for clinical review: No"). |
| `decisionTimelineTitle` | `فیصلہ سازی کا ٹائم لائن` | `فیصلہ سازی کے مراحل (ٹائم لائن)` | Corrects grammatical phrasing and clarifies that the timeline displays sequential execution steps of the orchestration pipeline. |
| `waistErrorCm` | `کمر کی پیمائش ۴۰ سے ۲۰۰ سینٹی میٹر کے درمیان ہونی چاہیے (ڈاکٹر کے جائزے کی ضرورت ہے)۔` | `کمر کی پیمائش 40 سے 200 سینٹی میٹر کے درمیان ہونی چاہیے (ڈاکٹر کے جائزے کی ضرورت ہے)۔` | Replaces Eastern Arabic numerals with standard Arabic/Western numerals for consistent cross-device legibility and alignment with glucose/BP displays. |
| `waistErrorIn` | `کمر کی پیمائش ۱۵.۷ سے ۷۸.۷ انچ کے درمیان ہونی چاہیے (ڈاکٹر کے جائزے کی ضرورت ہے)۔` | `کمر کی پیمائش 15.7 سے 78.7 انچ کے درمیان ہونی چاہیے (ڈاکٹر کے جائزے کی ضرورت ہے)۔` | Replaces Eastern Arabic numerals with standard numerals for mobile UI clarity. |

### 4.2 Backend Messages Catalog Review (`messages.json`)

All 28 entries in `backend-poc-technical/agents/interview_bank/messages.json` verified:
- Emergency guidance verified to refer strictly to 1122 and immediate emergency medical care (`emergency_red_flag_note`).
- Neutral low sugar guidance (`v3_possible_low_guidance`, `glucose_unclear_unit_safety_guidance`) verified aligned with Doctor review R2 (no hardcoded gram/tablet amounts).
- Meter LO/HI confirmation (`meter_lo_hi_confirmation`) verified clear and non-judgmental.
- Adherence clarification queries (`adherence_clarification_question`, `adherence_clarification_why`, `adherence_clarification_unclear_note`) verified for respectful, collaborative tone.
- Flag `"needs_native_review"` confirmed `false` across all 28 entries.

---

## 5. Week 4 Finish Sprint: PR K Isolated Onboarding Prescription Intake Strings

**Date:** 12 Nov 2026  
**Reviewer:** reviewed by Hassaan, 12 Nov 2026  
**Status:** **APPROVED & VERIFIED**  
**PR:** `I4-K: prescription upload step in isolated-mode onboarding (OCR, confidence, unverified, manual fallback)`  
**Scope:** Frontend interface strings added to `app/translations/index.ts` covering onboarding prescription step, Section 21.1 header checklist, confidence badges, unverified provenance badge, and manual medicine entry fallback.

| Translation Key | English | Urdu Script | Native Review Notes |
|---|---|---|---|
| `onboardingPrescriptionTitle` | Prescription Upload (Optional) | نسخہ اپلوڈ کریں (اختیاری) | Clear and simple header for onboarding step |
| `onboardingPrescriptionQuestion` | Do you have a prescription? Upload a photo (optional) | کیا آپ کے پاس نسخہ ہے؟ تصویر اپلوڈ کریں (اختیاری) | Everyday Pakistani phrasing for doctor's prescription ("نسخہ") |
| `onboardingPrescriptionHint` | Uploading your prescription helps fill your medicines automatically. You can always skip or type them manually. | نسخے کی تصویر سے دوائیاں خود بخود درج ہو سکتی ہیں۔ آپ اسے چھوڑ بھی سکتے ہیں یا خود لکھ سکتے ہیں۔ | Natural conversational tone explaining optional nature |
| `onboardingUploadBtn` | Upload Photo | تصویر اپلوڈ کریں | Direct, concise action button |
| `onboardingSkipBtn` | Skip for now | فی الحال چھوڑ دیں | Soft, friendly skip action |
| `onboardingManualToggle` | Type your medicines manually instead | دوائیاں خود لکھیں | Clear alternative option |
| `onboardingPrescriptionCameraTip` | Place the prescription on a flat surface in good lighting for best results. | اچھے نتائج کے لیے نسخے کو ہموار جگہ پر اور اچھی روشنی میں رکھیں۔ | Practical camera tip in simple Urdu |
| `onboardingManualTitle` | Type your medicines | اپنی دوائیاں درج کریں | Manual fallback heading |
| `onboardingManualHint` | Enter the medicines you are currently taking (one per line). | جو دوائیاں آپ اس وقت لے رہے ہیں وہ یہاں لکھیں (ہر لائن میں ایک دوا)۔ | Everyday Urdu for current medication routine |
| `onboardingManualSaveBtn` | Save medicines | دوائیاں محفوظ کریں | Standard save action |
| `confidenceBadgeHigh` | High confidence | زیادہ وثوق | Accurate translation of extraction confidence |
| `confidenceBadgeMedium` | Medium confidence | درمیانہ وثوق | Balanced confidence label |
| `confidenceBadgeLow` | Low confidence - check paper | کم وثوق - نسخے سے چیک کریں | Action-oriented guidance to consult paper prescription |
| `ocrHeaderChecklistTitle` | Prescription Header Details | نسخے کی بنیادی تفصیلات | Section 21.1 header verification title |
| `ocrHeaderDoctorName` | Doctor Name | ڈاکٹر کا نام | Essential provider detail |
| `ocrHeaderRegNumber` | Registration Number | رجسٹریشن نمبر | PMDC/PMC medical registration number |
| `ocrHeaderHospitalClinic` | Hospital / Clinic | ہسپتال / کلینک | Facility name |
| `ocrHeaderDate` | Date | تاریخ | Prescription date |
| `ocrHeaderMedications` | Medications | دوائیاں | Medication lines |
| `ocrHeaderFound` | Found | مل گیا | Extraction status tag |
| `ocrHeaderMissing` | Not read: please check the paper | نہیں پڑھا جا سکا: براہ کرم نسخہ خود چیک کریں | Friendly, actionable guidance (no scary error) |
| `ocrHeaderReadPleaseCheck` | read, please check | پڑھا گیا، براہ کرم چیک کریں | Amber checklist tag when raw OCR header is read and needs paper verification |
| `unverifiedUploadBadge` | Unverified (patient upload) | غیر تصدیق شدہ (مریض کا اپلوڈ) | Section 18.1 provenance indicator |
| `ocrLowConfidenceHint` | Please verify the medicine name and dosage carefully against your paper prescription. | براہ کرم دوا کا نام اور مقدار اپنے کاغذی نسخے سے غور سے ملا لیں۔ | Emphasizes patient safety and dosage verification |
| `ocrDisabledNotice` | Prescription photo reading is currently unavailable. Please type your medicines below. | نسخے کی تصویر پڑھنے کی سہولت فی الحال بند ہے۔ براہ کرم اپنی دوائیاں خود لکھیں۔ | Friendly offline/disabled notice without raw server errors |

---

## 6. Finish Sprint Review: H1 Appointments, H2 Notifications, H3 Urdu Voice

**Date:** 12 Nov 2026  
**Reviewer:** reviewed by Hassaan, 12 Nov 2026  
**Status:** **APPROVED & VERIFIED**  
**PRs:**
- H1: `feat/i4-appointments` (PR #145)
- H2: `feat/i4-notifications` (PR #146)
- H3: `feat/i4-urdu-voice` (PR #147)

### 6.1 Appointments Workflow Strings (H1 / PR #145)
| Translation Key | English | Urdu Script | Native Review Notes |
|---|---|---|---|
| `myAppointmentsTitle` | My Appointments | میری ملاقاتیں | Everyday colloquial term for patient appointments |
| `noAppointmentsTitle` | No Appointments Scheduled | کوئی ملاقات طے نہیں ہے | Honest empty state phrasing |
| `appointmentOffered` | Offered | تجویز کردہ | Clear status indicator for offered slot |
| `appointmentBooked` | Booked | طے شدہ | Confirmed booking label |
| `appointmentAttended` | Attended | مکمل | Attended appointment status |
| `appointmentCancelled` | Cancelled | منسوخ | Cancelled appointment status |
| `specialtyEndocrinology` | Endocrinology | شعبہ ذیابیطس و ہارمونز | Accessible clinical specialty descriptor |
| `specialtyCardiology` | Cardiology | شعبہ امراض قلب | Accessible cardiology descriptor |
| `specialtyInternalMedicine` | Internal Medicine | شعبہ انٹرنل میڈیسن | Common medical term in Urdu clinics |
| `bookAppointmentBtn` | Select Slot & Book | وقت منتخب کریں اور تصدیق کریں | Action-oriented booking button |
| `cancelAppointmentBtn` | Cancel Appointment | ملاقات منسوخ کریں | Clear cancellation button |
| `acknowledgeAppointmentBtn` | Acknowledge | موصول ہوا | Provider clinical acknowledgment |
| `markAttendedBtn` | Mark Attended | مکمل قرار دیں | Provider clinical completion action |
| `adminProviderDirectoryTitle` | Provider Directory & Availability | ڈاکٹر ڈائرکٹری و دستیابی | Administrative directory title |
| `adminEscalationAlertsTitle` | Escalation Alerts & Timeouts | تاخیر و ہنگامی الرٹس (ایسکلیشن) | Escalation dashboard header |
| `escalationAdminFlag` | Admin Escalation (>=24h unacknowledged) | انتظامی الرٹ (۲۴ گھنٹے سے زائد تاخیر) | Administrative safety banner |
| `escalationReNotify` | Re-notified (>=2h unacknowledged) | دوبارہ یاد دہانی (۲ گھنٹے سے زائد تاخیر) | Automated re-notification tag |
| `escalationPending` | Pending Acknowledgment | زیر انتظار | Pending acknowledgment state |
| `careTeamAlertedCard` | Care Team Alerted | نگہداشت ٹیم کو مطلع کر دیا گیا ہے | Reassuring clinical status notice |

### 6.2 Notification Centre Strings (H2 / PR #146)
| Translation Key | English | Urdu Script | Native Review Notes |
|---|---|---|---|
| `notificationsTitle` | Notifications & Alerts | اطلاعات و الرٹس | Standard bilingual header |
| `notificationsEmpty` | No notifications | کوئی نئی اطلاع نہیں ہے | Clean empty state message |
| `markAllReadBtn` | Mark all as read | سب پڑھ لیا | Action to clear unread counts |
| `notificationDailyReminder` | Daily Check-in Reminder: Have you recorded your vitals today? | روزانہ یاد دہانی: کیا آپ نے آج کا چیک ان مکمل کیا ہے؟ | Safe reminder containing zero PHI or clinical values |
| `notificationUrgentAlert` | Clinical Alert: A prompt review has been requested for your care team. | فوری الرٹ: آپ کی حالت میں تبدیلی پر ڈاکٹر کا جائزہ درکار ہے | Neutral urgent clinical escalation notice |
| `notificationEscalationAlert` | Care Team Reminder: Check-in awaiting review. | ایسکلیشن الرٹ: نگہداشت ٹیم کو زیر التواء معائنے کی یاد دہانی | Automated provider escalation reminder |

### 6.3 Spoken Explanations & Voice Strings (H3 / PR #147)
| Translation Key | English | Urdu Script | Native Review Notes |
|---|---|---|---|
| `listenToExplanationBtn` | Listen | وضاحت سنیں | Direct, clear speech playback button |
| `listeningToExplanation` | Playing voice... | آواز چل رہی ہے... | Active audio playback indicator |
| `listenToEmergencyInstructions` | Listen to Emergency Instructions | ایمرجنسی ہدایات سنیں | Immediate accessible speech instruction for 1122 |
| `speechLoading` | Generating voice... | آواز تیار ہو رہی ہے... | Loading audio status |
| `speechUnavailable` | Voice output unavailable | آواز دستیاب نہیں | Soft offline fallback message |
| `voiceNotAvailableRomanUrdu` | Voice is not available for Roman Urdu text | رومن اردو کے لیے آواز دستیاب نہیں ہے | Informative explanation for Roman Urdu template fallback |


---

## 7. Native Review Approved (12 Nov 2026)

**PR:** #134 (`fix/i3-no-readings-wording`)  
**Target:** `backend-poc-technical/rag/templates.json` -> `routine_no_readings`  
**Status:** **APPROVED BY HASSAAN MUDASSAR ("Urdu OK")**  
**Flag in Code:** `"needs_native_review": false`

### 7.1 Template Changes (Approved)

| Language | Field | Approved Text | Status |
|---|---|---|---|
| English | `sentence_2` | `You did not report any warning signs today.` | Approved (K3) |
| Urdu | `sentence_2` | `آپ نے آج کسی خطرے کی علامت کی اطلاع نہیں دی۔` | Approved by Hassaan |
| Roman Urdu | `sentence_2` | `Aap ne aaj kisi khatray ki alamat ki ittila nahi di.` | Approved by Hassaan |

**Context / Rationale:**  
Reviewer correction K3 for PR #134 updated Sentence 2 of the `routine_no_readings` template to avoid misleading phrasing when a patient logs symptoms or check-in answers without quantitative glucose/BP numbers. Hassaan provided native review sign-off ("Urdu OK" on PR #134); `needs_native_review` is set to `false`.



