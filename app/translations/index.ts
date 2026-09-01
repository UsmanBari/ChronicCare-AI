export type Language = 'en' | 'ur';

export interface Translations {
  // Common / Navigation
  appName: string;
  demoWatermark: string;
  disclaimerScope: string;
  continue: string;
  back: string;
  submit: string;
  saving: string;
  loading: string;
  yes: string;
  no: string;
  preferNotToAnswer: string;
  skip: string;

  // Header
  settings: string;
  connectedHospital: string;
  offlineMode: string;

  // Screen 1: Login / Sign-up
  loginTitle: string;
  loginSubtitle: string;
  createAccountTitle: string;
  createAccountSubtitle: string;
  emailOrPhoneLabel: string;
  emailOrPhonePlaceholder: string;
  passwordLabel: string;
  passwordPlaceholder: string;
  signInBtn: string;
  signUpBtn: string;
  toggleToSignUp: string;
  toggleToSignIn: string;
  loginHelpText: string;

  // Screen 2: Connection Choice
  connectionTitle: string;
  connectionSubtitle: string;
  fhirCardTitle: string;
  fhirCardDesc: string;
  fhirConnectingText: string;
  fhirConnectedText: string;
  offlineCardTitle: string;
  offlineCardDesc: string;
  offlineConnectedText: string;

  // Screen 3: Initial Health Profile
  profileTitle: string;
  profileSubtitle: string;
  conditionsLabel: string;
  type2Diabetes: string;
  hypertension: string;
  bothConditions: string;
  medicationsLabel: string;
  medicationsHint: string;
  medicationPlaceholder: string;
  addMedication: string;
  removeMedication: string;
  ageLabel: string;
  agePlaceholder: string;

  // Screen 4: Home / Dashboard
  homeGreeting: string;
  homeSubtitle: string;
  reminderTitle: string;
  reminderDesc: string;
  startCheckInBtn: string;
  statusTitle: string;
  activeConditions: string;
  trackedMeds: string;
  lastCheckIn: string;
  lastCheckInValue: string;

  // Screen 5: Check-in Entry
  checkInEntryTitle: string;
  checkInEntrySubtitle: string;
  howAreYouFeelingLabel: string;
  howAreYouFeelingPlaceholder: string;
  voiceInputTitle: string;
  listeningAnimationText: string;
  voiceHelperText: string;

  // Screen 6: Adaptive Interview
  adaptiveInterviewTitle: string;
  adaptiveInterviewSubtitle: string;
  questionCount: string;
  q1Text: string;
  q2Text: string;
  q3Text: string;
  submitCheckInBtn: string;

  // Screen 7: Confirmation
  confirmationTitle: string;
  confirmationSubtitle: string;
  confirmationMessage: string;
  submittedAt: string;
  finishBtn: string;
}

export const translations: Record<Language, Translations> = {
  en: {
    appName: "ChronicCare AI",
    demoWatermark: "DEMO — DATA NOT REAL",
    disclaimerScope: "This prototype represents the interface and interaction layer; the underlying computational functionality will be implemented in subsequent milestones.",
    continue: "Continue",
    back: "Back",
    submit: "Submit",
    saving: "Saving...",
    loading: "Loading...",
    yes: "Yes",
    no: "No",
    preferNotToAnswer: "Prefer not to answer",
    skip: "Skip",

    settings: "Settings",
    connectedHospital: "City General Hospital (FHIR)",
    offlineMode: "Isolated Mode (Local Store)",

    loginTitle: "Welcome to ChronicCare AI",
    loginSubtitle: "Sign in to manage your chronic condition check-ins and care journey.",
    createAccountTitle: "Create Your Account",
    createAccountSubtitle: "Get started with daily personalized chronic care monitoring.",
    emailOrPhoneLabel: "Email address or Mobile phone",
    emailOrPhonePlaceholder: "e.g. patient@example.com or +1 (555) 019-2834",
    passwordLabel: "Password",
    passwordPlaceholder: "Enter your password",
    signInBtn: "Sign In",
    signUpBtn: "Create Account",
    toggleToSignUp: "Don't have an account? Sign up here",
    toggleToSignIn: "Already have an account? Sign in",
    loginHelpText: "Enter any non-empty credentials to proceed to connection selection.",

    connectionTitle: "Select Connection Mode",
    connectionSubtitle: "Choose how ChronicCare AI should access and synchronize your clinical profile.",
    fhirCardTitle: "Connect to your hospital's EHR",
    fhirCardDesc: "Securely link your record with City General Hospital using the HL7® FHIR® standard interface.",
    fhirConnectingText: "Establishing secure FHIR handshake...",
    fhirConnectedText: "Connected to City General Hospital via FHIR ✓",
    offlineCardTitle: "Set up offline profile",
    offlineCardDesc: "Maintain an isolated, private local profile on this device without connecting to an EHR.",
    offlineConnectedText: "Isolated Mode — using Local Store ✓",

    profileTitle: "Initial Health Profile",
    profileSubtitle: "Please provide your baseline health parameters to customize your daily monitoring.",
    conditionsLabel: "Existing Conditions",
    type2Diabetes: "Type 2 Diabetes",
    hypertension: "Hypertension",
    bothConditions: "Both (Type 2 Diabetes & Hypertension)",
    medicationsLabel: "Current Medications",
    medicationsHint: "Add each daily medication or prescription you are currently taking.",
    medicationPlaceholder: "e.g., Metformin 500mg, Lisinopril 10mg",
    addMedication: "+ Add another medication",
    removeMedication: "Remove",
    ageLabel: "Patient Age (Years)",
    agePlaceholder: "e.g. 58",

    homeGreeting: "Good day, Patient",
    homeSubtitle: "Your daily care overview and proactive symptom check-in.",
    reminderTitle: "Time for your daily check-in",
    reminderDesc: "Take 60 seconds to record your daily symptoms and ensure your care plan remains on track.",
    startCheckInBtn: "Start Daily Check-In",
    statusTitle: "Care Summary",
    activeConditions: "Active Conditions",
    trackedMeds: "Tracked Prescriptions",
    lastCheckIn: "Previous Check-In",
    lastCheckInValue: "Yesterday, 8:30 AM (Logged)",

    checkInEntryTitle: "Daily Symptom Check-In",
    checkInEntrySubtitle: "Describe how you are feeling in your own words or speak into your microphone.",
    howAreYouFeelingLabel: "How are you feeling today?",
    howAreYouFeelingPlaceholder: "Describe any symptoms, energy levels, fatigue, or changes you noticed today...",
    voiceInputTitle: "Tap microphone for Voice Input",
    listeningAnimationText: "Listening... (capturing audio)",
    voiceHelperText: "Speak clearly. Audio will be transcribed directly into your check-in notes.",

    adaptiveInterviewTitle: "Adaptive Symptom Interview",
    adaptiveInterviewSubtitle: "Personalized follow-up questions tailored to your check-in report.",
    questionCount: "Step-by-Step Clinical Follow-up",
    q1Text: "Have you noticed increased thirst recently?",
    q2Text: "Have you been urinating more frequently than usual?",
    q3Text: "Have you missed any medication doses this week?",
    submitCheckInBtn: "Submit Check-In",

    confirmationTitle: "Check-in submitted!",
    confirmationSubtitle: "Your daily health check-in has been successfully recorded.",
    confirmationMessage: "Thank you for completing your daily check-in. Your responses have been securely stored in your active profile.",
    submittedAt: "Submitted on",
    finishBtn: "Return to Home",
  },
  ur: {
    appName: "کرونک کیئر اے آئی (ChronicCare AI)",
    demoWatermark: "ڈیمو — ڈیٹا حقیقی نہیں ہے",
    disclaimerScope: "This prototype represents the interface and interaction layer; the underlying computational functionality will be implemented in subsequent milestones.",
    continue: "آگے بڑھیں",
    back: "پیچھے",
    submit: "جمع کروائیں",
    saving: "محفوظ ہو رہا ہے...",
    loading: "لوڈ ہو رہا ہے...",
    yes: "جی ہاں",
    no: "نہیں",
    preferNotToAnswer: "جواب نہ دینے کو ترجیح",
    skip: "چھوڑ دیں",

    settings: "ترتیبات",
    connectedHospital: "سٹی جنرل ہسپتال (FHIR)",
    offlineMode: "آف لائن موڈ (مقامی اسٹور)",

    loginTitle: "کرونک کیئر اے آئی میں خوش آمدید",
    loginSubtitle: "اپنی دائمی بیماریوں کی دیکھ بھال اور روزانہ چیک ان کے لیے سائن ان کریں۔",
    createAccountTitle: "نیا اکاؤنٹ بنائیں",
    createAccountSubtitle: "روزانہ ذاتی نگہداشت کے نظام کے ساتھ شروعات کریں۔",
    emailOrPhoneLabel: "ای میل ایڈریس یا موبائل نمبر",
    emailOrPhonePlaceholder: "مثلاً patient@example.com یا 0300-1234567",
    passwordLabel: "پاس ورڈ",
    passwordPlaceholder: "اپنا پاس ورڈ درج کریں",
    signInBtn: "سائن ان کریں",
    signUpBtn: "اکاؤنٹ بنائیں",
    toggleToSignUp: "کیا اکاؤنٹ موجود نہیں ہے؟ یہاں سائن اپ کریں",
    toggleToSignIn: "کیا پہلے سے اکاؤنٹ موجود ہے؟ سائن ان کریں",
    loginHelpText: "آگے بڑھنے کے لیے کوئی بھی معلوماتی ان پٹ درج کریں۔",

    connectionTitle: "کنکشن کا طریقہ منتخب کریں",
    connectionSubtitle: "منتخب کریں کہ کرونک کیئر اے آئی آپ کی طبی معلومات کیسے حاصل کرے۔",
    fhirCardTitle: "اپنے ہسپتال کے EHR سے منسلک ہوں",
    fhirCardDesc: "سٹی جنرل ہسپتال کے ساتھ HL7® FHIR® معیاری انٹرفیس کے ذریعے محفوظ رابطہ قائم کریں۔",
    fhirConnectingText: "ہسپتال کے ریکارڈ سے رابطہ ہو رہا ہے...",
    fhirConnectedText: "سٹی جنرل ہسپتال سے FHIR کے ذریعے رابطہ قائم ہو گیا ✓",
    offlineCardTitle: "آف لائن پروفائل بنائیں",
    offlineCardDesc: "ہسپتال سے منسلک ہوئے بغیر اس ڈیوائس پر نجی مقامی پروفائل برقرار رکھیں۔",
    offlineConnectedText: "آئسولیٹڈ موڈ — لوکل اسٹور استعمال ہو رہا ہے ✓",

    profileTitle: "ابتدائی صحت کی پروفائل",
    profileSubtitle: "اپنی روزانہ کی نگرانی کو حسب ضرورت بنانے کے لیے بنیادی معلومات فراہم کریں۔",
    conditionsLabel: "موجودہ بیماریاں",
    type2Diabetes: "ذیابیطس ٹائپ 2 (شوگر)",
    hypertension: "بلڈ پریشر (ہائپرٹینشن)",
    bothConditions: "دونوں (ذیابیطس اور ہائپرٹینشن)",
    medicationsLabel: "موجودہ ادویات",
    medicationsHint: "روزانہ لی جانے والی ہر دوائی یا نسخہ درج کریں۔",
    medicationPlaceholder: "مثلاً میٹفارمین 500mg، لیسینوپرل 10mg",
    addMedication: "+ دوسری دوا شامل کریں",
    removeMedication: "ختم کریں",
    ageLabel: "مریض کی عمر (سال)",
    agePlaceholder: "مثلاً 58",

    homeGreeting: "خوش آمدید",
    homeSubtitle: "آپ کی روزانہ نگہداشت کا جائزہ اور علامات کا چیک ان۔",
    reminderTitle: "روزانہ چیک ان کا وقت ہو گیا ہے",
    reminderDesc: "اپنی علامات درج کرنے کے لیے 60 سیکنڈ نکالیں تاکہ آپ کی صحت کا معمول درست رہے۔",
    startCheckInBtn: "روزانہ چیک ان شروع کریں",
    statusTitle: "طبی خلاصہ",
    activeConditions: "فعال بیماریاں",
    trackedMeds: "زیر نگرانی ادویات",
    lastCheckIn: "پچھلا چیک ان",
    lastCheckInValue: "کل صبح 8:30 بجے (محفوظ شدہ)",

    checkInEntryTitle: "روزانہ علامات کا چیک ان",
    checkInEntrySubtitle: "بیان کریں کہ آپ کیسا محسوس کر رہے ہیں یا مائیکروفون میں بولیں۔",
    howAreYouFeelingLabel: "آج آپ کیسا محسوس کر رہے ہیں؟",
    howAreYouFeelingPlaceholder: "اپنی علامات، تھکاوٹ، پیاس یا کسی تبدیلی کے بارے میں بتائیں...",
    voiceInputTitle: "آواز سے درج کرنے کے لیے مائیکروفون دبائیں",
    listeningAnimationText: "سن رہا ہے... (آڈیو ریکارڈنگ جاری)",
    voiceHelperText: "صاف آواز میں بولیں۔ آپ کی آواز تحریر میں تبدیل ہو جائے گی۔",

    adaptiveInterviewTitle: "علامات کا فالو اپ انٹرویو",
    adaptiveInterviewSubtitle: "آپ کی علامات کے مطابق طبی سوالات۔",
    questionCount: "طبی فالو اپ سوالات",
    q1Text: "کیا آپ نے حال ہی میں پیاس کی زیادتی محسوس کی ہے؟",
    q2Text: "کیا آپ کو معمول سے زیادہ پیشاب آ رہا ہے؟",
    q3Text: "کیا اس ہفتے آپ کی دوا کی کوئی خوراک چھوٹ گئی ہے؟",
    submitCheckInBtn: "چیک ان جمع کروائیں",

    confirmationTitle: "چیک ان جمع کر دیا گیا!",
    confirmationSubtitle: "آپ کا روزانہ چیک ان کامیابی سے محفوظ ہو گیا ہے۔",
    confirmationMessage: "روزانہ چیک ان مکمل کرنے کا شکریہ۔ آپ کے جوابات آپ کی فعال پروفائل میں محفوظ ہو گئے ہیں۔",
    submittedAt: "جمع کرانے کا وقت",
    finishBtn: "ہوم اسکرین پر واپس جائیں",
  }
};
