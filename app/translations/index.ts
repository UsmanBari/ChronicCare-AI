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
  close: string;
  resolve: string;
  scheduleAppointment: string;
  escalate: string;
  acknowledge: string;
  confirmed: string;
  pending: string;
  resolved: string;
  active: string;

  // Header & Navigation
  settings: string;
  connectedHospital: string;
  offlineMode: string;
  portalSwitchTitle: string;
  patientPortal: string;
  providerPortal: string;
  adminPortal: string;
  switchPortal: string;
  backToDashboard: string;

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

  // Provider Login
  providerLoginTitle: string;
  providerLoginSubtitle: string;
  providerIdLabel: string;
  providerIdPlaceholder: string;
  adminLoginTitle: string;
  adminLoginSubtitle: string;

  // Auth / Firebase Errors
  authInvalidApiKey: string;
  authUserNotFound: string;
  authWrongPassword: string;
  authInvalidCredentials: string;
  authRoleMismatch: string;
  authGeneralError: string;
  authSigningIn: string;
  authModeFirebase: string;
  authModeMock: string;
  authConfigError: string;
  authEmptyFields: string;

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

  // Screen 4: Home / Dashboard (Patient)
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
  patientAppointmentsBtn: string;

  // Presenter Controls (Demo tool)
  presenterControlsLabel: string;
  scenarioNormalBtn: string;
  scenarioConflictBtn: string;
  scenarioEmergencyBtn: string;
  resetDemoBtn: string;
  activeScenarioLabel: string;

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
  viewResultsBtn: string;

  // M2: Processing & Risk & Trends
  processingTitle: string;
  processingSubtitle: string;
  verifiedTitle: string;
  verifiedSubtitle: string;
  riskLowTitle: string;
  riskModerateTitle: string;
  riskHighTitle: string;
  riskSupportingText: string;
  riskDescription: string;
  seeWhyBtn: string;
  contributingFactorsTitle: string;
  shapDisclaimer: string;
  factor1: string;
  factor2: string;
  factor3: string;
  factor4: string;
  viewTrendsBtn: string;
  trendsTitle: string;
  trendsSubtitle: string;
  glucoseChartTitle: string;
  bloodPressureChartTitle: string;
  adherenceChartTitle: string;
  systolicLabel: string;
  diastolicLabel: string;
  targetRangeLabel: string;
  dayLabel: string;

  // M3: Conflict & Review & Emergency
  conflictDetectedTitle: string;
  conflictPatientReported: string;
  conflictEhrRecord: string;
  patientCheckInSource: string;
  fhirEhrSource: string;
  confidenceLowTag: string;
  unansweredQuestionTag: string;
  conflictSimulationCaption: string;
  routedToReviewTitle: string;
  routedToReviewDesc: string;
  emergencyDetectedTitle: string;
  emergencyGuidanceText: string;
  emergencyAlertedText: string;

  // M4: Provider Dashboard & Review Queue
  providerDashboardTitle: string;
  providerSubtitle: string;
  activeCasesLabel: string;
  urgentCasesLabel: string;
  notificationsTitle: string;
  patientListTitle: string;
  reviewQueueTitle: string;
  viewReviewQueueBtn: string;
  columnPatient: string;
  columnReason: string;
  columnConfidence: string;
  columnStatus: string;
  columnActions: string;
  alertDetailsTitle: string;
  reconciliationAlertBadge: string;
  caseResolvedToast: string;
  caseAcknowledgedToast: string;
  incompleteCheckInTitle: string;
  incompleteCheckInDesc: string;

  // M4: Appointment Scheduling
  scheduleTitle: string;
  scheduleSubtitle: string;
  selectSlotLabel: string;
  confirmBookingBtn: string;
  bookingSuccessTitle: string;
  bookingSuccessDesc: string;

  // M4: Patient Appointments View
  noAppointmentsTitle: string;
  noAppointmentsDesc: string;
  myAppointmentsTitle: string;
  appointmentWith: string;
  appointmentReason: string;
  appointmentStatus: string;

  // M4: Admin Portal
  adminDashboardTitle: string;
  adminSubtitle: string;
  statUsers: string;
  statProviders: string;
  statPatients: string;
  statActiveAlerts: string;
  userManagementTitle: string;
  auditLogTitle: string;

  // M4: Unified Settings
  unifiedSettingsTitle: string;
  unifiedSettingsSubtitle: string;
  languageSettingLabel: string;
  connectionModeSettingLabel: string;
  activeProfileLabel: string;

  // Stage 4 Live Additions
  authPasswordTooShort: string;
  authPasswordMismatch: string;
  authInvalidEmail: string;
  confirmPasswordLabel: string;
  confirmPasswordPlaceholder: string;
  serverWakingTitle: string;
  serverWakingDesc: string;
  consentTitle: string;
  consentSubtitle: string;
  consentBody: string;
  consentAcceptBtn: string;
  consentDeclineBtn: string;
  consentDeclinedNotice: string;
  insulinOrSulfonylureaLabel: string;
  insulinOrSulfonylureaHint: string;
  insulinYes: string;
  insulinNo: string;
  selectEhrSystemLabel: string;
  patientIdLabel: string;
  patientIdPlaceholder: string;
  connectEhrBtn: string;
  disconnectEhrBtn: string;
  disconnectConfirm: string;
  connectedBadgeTitle: string;
  isolatedBadgeTitle: string;
  lastVerified: string;
  patientIdMasked: string;
  dontHaveInfoBtn: string;
  checkinSummaryTitle: string;
  checkinSummarySubtitle: string;
  agreementsCountLabel: string;
  missingCountLabel: string;
  confidenceLabel: string;
  riskScoringOmittedNote: string;
  notEnoughHistory: string;
  serverTyping: string;
  overdueBadge: string;
  emergencyPriority: string;
  actionNoteLabel: string;
  actionNotePlaceholder: string;
  actionResolveBtn: string;
  actionEscalateBtn: string;
  actionAcknowledgeBtn: string;
  demoCrossPortalLabel: string;
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
    close: "Close",
    resolve: "Resolve Case",
    scheduleAppointment: "Schedule Appointment",
    escalate: "Escalate",
    acknowledge: "Acknowledge",
    confirmed: "Confirmed",
    pending: "Pending Review",
    resolved: "Resolved",
    active: "Active",

    settings: "Settings",
    connectedHospital: "City General Hospital (FHIR)",
    offlineMode: "Isolated Mode (Local Store)",
    portalSwitchTitle: "Select Portal",
    patientPortal: "Patient Portal",
    providerPortal: "Provider Portal",
    adminPortal: "Admin Portal",
    switchPortal: "Switch Portal",
    backToDashboard: "Back to Dashboard",

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
    loginHelpText: "Enter any non-empty credentials to proceed.",

    providerLoginTitle: "Provider Clinical Access",
    providerLoginSubtitle: "Sign in to access patient triage, review queue, and EHR alerts.",
    providerIdLabel: "Clinical ID / Provider Email",
    providerIdPlaceholder: "e.g. dr.sanamalik@citygeneral.org",
    adminLoginTitle: "System Administration Portal",
    adminLoginSubtitle: "Manage platform users, system parameters, and audit trails.",

    // Auth / Firebase Errors
    authInvalidApiKey: "Invalid Firebase API configuration. Please check your system settings.",
    authUserNotFound: "No registered account found with this email address.",
    authWrongPassword: "Incorrect password. Please verify and try again.",
    authInvalidCredentials: "Invalid credentials. Please check your email and password.",
    authRoleMismatch: "Access denied: this account does not have permission for this portal.",
    authGeneralError: "Authentication failed. Please check your network and try again.",
    authSigningIn: "Signing in...",
    authModeFirebase: "Auth: Firebase",
    authModeMock: "Auth: Demo (mock)",
    authConfigError: "Firebase authentication is not properly configured. Please check your configuration.",
    authEmptyFields: "Please enter both your email and password to proceed.",

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
    medicationPlaceholder: "e.g., Metformin 500mg (1+1), Lisinopril 10mg (1+0)",
    addMedication: "+ Add another medication",
    removeMedication: "Remove",
    ageLabel: "Patient Age (Years)",
    agePlaceholder: "e.g. 58",

    homeGreeting: "Good day, Ali Khan",
    homeSubtitle: "Your daily care overview and proactive symptom check-in.",
    reminderTitle: "Time for your daily check-in",
    reminderDesc: "Take 60 seconds to record your daily symptoms and ensure your care plan remains on track.",
    startCheckInBtn: "Start Daily Check-In",
    statusTitle: "Care Summary",
    activeConditions: "Active Conditions",
    trackedMeds: "Tracked Prescriptions",
    lastCheckIn: "Previous Check-In",
    lastCheckInValue: "Yesterday, 8:30 AM (Logged)",
    patientAppointmentsBtn: "My Appointments",

    presenterControlsLabel: "DEMO CONTROL — NOT PART OF PRODUCT",
    scenarioNormalBtn: "Scenario A: Normal",
    scenarioConflictBtn: "Scenario B: Conflict",
    scenarioEmergencyBtn: "Scenario C: Emergency",
    resetDemoBtn: "Reset Demo",
    activeScenarioLabel: "Active Demo Scenario",

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
    viewResultsBtn: "View My Results",

    processingTitle: "Analyzing your recent health information…",
    processingSubtitle: "Synthesizing symptoms, clinical parameters, and check-in responses",
    verifiedTitle: "Result verified",
    verifiedSubtitle: "Input parameters validated against baseline record",

    riskLowTitle: "Low Risk",
    riskModerateTitle: "Moderate Risk",
    riskHighTitle: "High Risk",
    riskSupportingText: "Your recent check-ins look stable",
    riskDescription: "All tracked clinical parameters and daily symptom responses are within target safety boundaries.",
    seeWhyBtn: "See Why",

    contributingFactorsTitle: "Contributing Factors",
    shapDisclaimer: "Example contributing factors — representative visualization of future SHAP-based explanation.",
    factor1: "Blood glucose readings remain within individual target range (avg 110 mg/dL)",
    factor2: "Consistent medication adherence with zero reported missed doses",
    factor3: "Blood pressure measurements remain stable and controlled (120/80 mmHg baseline)",
    factor4: "No acute symptom escalations detected in daily check-in",
    viewTrendsBtn: "View Trends",

    trendsTitle: "Health Trends & Trajectory",
    trendsSubtitle: "Consistent multi-day tracking across key clinical indicators",
    glucoseChartTitle: "Blood Glucose (mg/dL)",
    bloodPressureChartTitle: "Blood Pressure (mmHg)",
    adherenceChartTitle: "Medication Adherence (%)",
    systolicLabel: "Systolic",
    diastolicLabel: "Diastolic",
    targetRangeLabel: "Target Range",
    dayLabel: "Day",

    conflictDetectedTitle: "Conflict Detected",
    conflictPatientReported: "Your reported blood sugar: 180 mg/dL",
    conflictEhrRecord: "Your last clinic record (FHIR): 140 mg/dL",
    patientCheckInSource: "Patient Check-in",
    fhirEhrSource: "FHIR EHR",
    confidenceLowTag: "Confidence: Low",
    unansweredQuestionTag: "This check-in also included an unanswered question.",
    conflictSimulationCaption: "This is a simulated system state for demonstration purposes. The actual reconciliation and verification logic has been separately validated in our technical proof of concept.",

    routedToReviewTitle: "Low Confidence — Routed to Human Review",
    routedToReviewDesc: "Your check-in has been flagged for review by your care provider. You'll be notified once it's been reviewed.",

    emergencyDetectedTitle: "Emergency Pattern Detected",
    emergencyGuidanceText: "Based on your responses, please seek medical attention promptly.",
    emergencyAlertedText: "Your care provider has been alerted.",

    // M4: Provider Dashboard & Review Queue
    providerDashboardTitle: "Clinical Provider Dashboard",
    providerSubtitle: "Proactive triage, clinical reconciliation alerts, and review queue.",
    activeCasesLabel: "Active Cases",
    urgentCasesLabel: "Urgent Cases",
    notificationsTitle: "Clinical Notifications",
    patientListTitle: "Assigned Patient Cohort",
    reviewQueueTitle: "Clinical Review Queue",
    viewReviewQueueBtn: "Open Review Queue",
    columnPatient: "Patient",
    columnReason: "Triage Reason",
    columnConfidence: "Confidence",
    columnStatus: "Status",
    columnActions: "Action",
    alertDetailsTitle: "Reconciliation Alert & Triage",
    reconciliationAlertBadge: "Reconciliation Discrepancy",
    caseResolvedToast: "Case marked as resolved and closed.",
    caseAcknowledgedToast: "Case reviewed and acknowledged.",
    incompleteCheckInTitle: "Incomplete Check-In",
    incompleteCheckInDesc: "Insufficient data submitted for automated risk assessment. Scheduled for routine clinical check.",

    // M4: Appointment Scheduling
    scheduleTitle: "Schedule Patient Follow-up",
    scheduleSubtitle: "Select an available clinic consultation slot for Ali Khan.",
    selectSlotLabel: "Available Time Slots",
    confirmBookingBtn: "Confirm Appointment",
    bookingSuccessTitle: "Appointment Confirmed",
    bookingSuccessDesc: "Appointment booked. Ali Khan has been notified in their Patient Portal.",

    // M4: Patient Appointments View
    noAppointmentsTitle: "No Upcoming Appointments",
    noAppointmentsDesc: "You currently have no scheduled appointments. Your care provider will notify you if a follow-up is required.",
    myAppointmentsTitle: "Scheduled Clinical Appointments",
    appointmentWith: "Provider",
    appointmentReason: "Reason for Visit",
    appointmentStatus: "Status",

    // M4: Admin Portal
    adminDashboardTitle: "System Administration & Telemetry",
    adminSubtitle: "Platform health, user access directory, and immutable audit log.",
    statUsers: "Total Users",
    statProviders: "Providers",
    statPatients: "Patients",
    statActiveAlerts: "Active System Alerts",
    userManagementTitle: "User Directory & Roles",
    auditLogTitle: "System Audit & Compliance Log",

    // M4: Unified Settings
    unifiedSettingsTitle: "Application Settings",
    unifiedSettingsSubtitle: "Manage language preferences, clinical connection mode, and profile parameters.",
    languageSettingLabel: "Display Language",
    connectionModeSettingLabel: "Clinical Data Synchronizer",
    activeProfileLabel: "Active Profile",

    // Stage 4 Live Additions
    authPasswordTooShort: "Password must be at least 8 characters.",
    authPasswordMismatch: "Passwords do not match.",
    authInvalidEmail: "Please enter a valid email address.",
    confirmPasswordLabel: "Confirm Password",
    confirmPasswordPlaceholder: "Re-enter your password",
    serverWakingTitle: "The server is waking up, please wait",
    serverWakingDesc: "Initial requests may take a moment while the cloud service starts.",
    consentTitle: "Patient Privacy & Care Consent",
    consentSubtitle: "Please review and accept our clinical monitoring consent before proceeding.",
    consentBody: "ChronicCare AI assists in daily symptom monitoring, clinical parameter cross-validation, and provider alerts. Your health data is encrypted, stored under HIPAA-grade protections, and only shared with your designated clinical care team. You can revoke consent at any time from your settings.",
    consentAcceptBtn: "I Understand and Accept",
    consentDeclineBtn: "Decline and Sign Out",
    consentDeclinedNotice: "Consent is required to use ChronicCare AI daily monitoring.",
    insulinOrSulfonylureaLabel: "Are you currently taking Insulin or a Sulfonylurea (e.g., Glimepiride, Glibenclamide)?",
    insulinOrSulfonylureaHint: "Helps identify hypoglycemia risk during glycemic monitoring.",
    insulinYes: "Yes, taking Insulin or Sulfonylurea",
    insulinNo: "No, neither",
    selectEhrSystemLabel: "Select Healthcare Organization / EHR",
    patientIdLabel: "Patient Identifier (MRN / Patient ID)",
    patientIdPlaceholder: "e.g. 768be7ac-743f-4c24-aa0f-fed5a3a38b6a or PT-04821",
    connectEhrBtn: "Connect EHR",
    disconnectEhrBtn: "Disconnect",
    disconnectConfirm: "Are you sure you want to disconnect from this EHR?",
    connectedBadgeTitle: "Connected EHR",
    isolatedBadgeTitle: "Isolated Mode (Own Records)",
    lastVerified: "Last verified",
    patientIdMasked: "Patient ID",
    dontHaveInfoBtn: "I don't have this information",
    checkinSummaryTitle: "Check-in recorded and verified",
    checkinSummarySubtitle: "Your daily health parameters have been processed against your clinical profile.",
    agreementsCountLabel: "Verified In-Range Parameters",
    missingCountLabel: "Omitted / Incomplete Data Points",
    confidenceLabel: "Assessment Confidence",
    riskScoringOmittedNote: "Note: Automated risk scoring is not part of this release. Clinical review is prioritized based on source reconciliation and safety rules.",
    notEnoughHistory: "Not enough history yet (minimum 3 check-ins required to display trend trajectory).",
    serverTyping: "Processing response...",
    overdueBadge: "OVERDUE",
    emergencyPriority: "EMERGENCY",
    actionNoteLabel: "Clinical Review Note (Required)",
    actionNotePlaceholder: "Enter clinical observation, rationale, or instructions for care team...",
    actionResolveBtn: "Resolve & Close Alert",
    actionEscalateBtn: "Escalate to Care Team",
    actionAcknowledgeBtn: "Acknowledge Alert",
    demoCrossPortalLabel: "Demo Cross-Portal Feature",
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
    close: "بند کریں",
    resolve: "کیس حل کریں",
    scheduleAppointment: "اپوائنٹمنٹ طے کریں",
    escalate: "ایسکلیٹ کریں",
    acknowledge: "تصدیق کریں",
    confirmed: "تصدیق شدہ",
    pending: "زیر التواء جائزہ",
    resolved: "حل شدہ",
    active: "فعال",

    settings: "ترتیبات",
    connectedHospital: "سٹی جنرل ہسپتال (FHIR)",
    offlineMode: "آف لائن موڈ (مقامی اسٹور)",
    portalSwitchTitle: "پورٹل منتخب کریں",
    patientPortal: "مریض پورٹل",
    providerPortal: "ڈاکٹر / پرووائیڈر پورٹل",
    adminPortal: "ایڈمن پورٹل",
    switchPortal: "پورٹل تبدیل کریں",
    backToDashboard: "ڈیش بورڈ پر واپس",

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
    loginHelpText: "آگے بڑھنے کے لیے کوئی بھی معلومات درج کریں۔",

    providerLoginTitle: "ڈاکٹر / کلینیکل لاگ ان",
    providerLoginSubtitle: "مریضوں کی فہرست اور الرٹس تک رسائی کے لیے سائن ان کریں۔",
    providerIdLabel: "کلینیکل آئی ڈی یا ای میل",
    providerIdPlaceholder: "مثلاً dr.sanamalik@citygeneral.org",
    adminLoginTitle: "سسٹم ایڈمنسٹریشن پورٹل",
    adminLoginSubtitle: "سسٹم کے صارفین اور آڈٹ لاگ کا انتظام کریں۔",

    // Auth / Firebase Errors
    authInvalidApiKey: "فائر بیس API کی ترتیب درست نہیں ہے۔ براہ کرم سسٹم سیٹنگز چیک کریں۔",
    authUserNotFound: "اس ای میل سے کوئی رجسٹرڈ اکاؤنٹ موجود نہیں ہے۔",
    authWrongPassword: "پاس ورڈ غلط ہے۔ براہ کرم دوبارہ کوشش کریں۔",
    authInvalidCredentials: "ای میل یا پاس ورڈ غلط ہے۔ براہ کرم دوبارہ تصدیق کریں۔",
    authRoleMismatch: "رسائی مسترد: اس اکاؤنٹ کے پاس اس پورٹل کے لیے اجازت نہیں ہے۔",
    authGeneralError: "لاگ ان تصدیق ناکام ہو گئی۔ براہ کرم نیٹ ورک چیک کریں اور دوبارہ کوشش کریں۔",
    authSigningIn: "سائن ان ہو رہا ہے...",
    authModeFirebase: "تصدیق: فائر بیس",
    authModeMock: "تصدیق: ڈیمو (فرضی)",
    authConfigError: "فائر بیس کی ترتیب نامکمل ہے۔ لاگ ان سروس دستیاب نہیں ہے۔",
    authEmptyFields: "براہ کرم آگے بڑھنے کے لیے ای میل اور پاس ورڈ درج کریں۔",

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
    medicationPlaceholder: "مثلاً میٹفارمین 500mg (1+1)، لیسینوپرل 10mg (1+0)",
    addMedication: "+ دوسری دوا شامل کریں",
    removeMedication: "ختم کریں",
    ageLabel: "مریض کی عمر (سال)",
    agePlaceholder: "مثلاً 58",

    homeGreeting: "خوش آمدید، علی خان",
    homeSubtitle: "آپ کی روزانہ نگہداشت کا جائزہ اور علامات کا چیک ان۔",
    reminderTitle: "روزانہ چیک ان کا وقت ہو گیا ہے",
    reminderDesc: "اپنی علامات درج کرنے کے لیے 60 سیکنڈ نکالیں تاکہ آپ کی صحت کا معمول درست رہے۔",
    startCheckInBtn: "روزانہ چیک ان شروع کریں",
    statusTitle: "طبی خلاصہ",
    activeConditions: "فعال بیماریاں",
    trackedMeds: "زیر نگرانی ادویات",
    lastCheckIn: "پچھلا چیک ان",
    lastCheckInValue: "کل صبح 8:30 بجے (محفوظ شدہ)",
    patientAppointmentsBtn: "میری اپوائنٹمنٹس",

    presenterControlsLabel: "ڈیمو کنٹرول — پروڈکٹ کا حصہ نہیں ہے",
    scenarioNormalBtn: "منظرنامہ A: نارمل",
    scenarioConflictBtn: "منظرنامہ B: تضاد (Conflict)",
    scenarioEmergencyBtn: "منظرنامہ C: ایمرجنسی",
    resetDemoBtn: "ڈیمو ری سیٹ کریں",
    activeScenarioLabel: "فعال ڈیمو منظرنامہ",

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
    viewResultsBtn: "میرے نتائج دیکھیں",

    processingTitle: "آپ کی صحت کی حالیہ معلومات کا تجزیہ ہو رہا ہے…",
    processingSubtitle: "علامات، طبی تاریخ اور چیک ان ڈیٹا کا جائزہ لیا جا رہا ہے",
    verifiedTitle: "نتیجہ تصدیق شدہ",
    verifiedSubtitle: "بنیادی ریکارڈ کے مطابق تصدیق مکمل ہو گئی",

    riskLowTitle: "کم خطرہ (Low Risk)",
    riskModerateTitle: "معتدل خطرہ (Moderate Risk)",
    riskHighTitle: "زیادہ خطرہ (High Risk)",
    riskSupportingText: "آپ کا حالیہ چیک ان مستحکم نظر آتا ہے",
    riskDescription: "تمام زیر نگرانی علامات اور طبی اشارے ہدف کے مطابق محفوظ حد میں ہیں۔",
    seeWhyBtn: "وجوہات دیکھیں",

    contributingFactorsTitle: "معاون عوامل (Contributing Factors)",
    shapDisclaimer: "Example contributing factors — representative visualization of future SHAP-based explanation.",
    factor1: "بلڈ شوگر کی مقدار انفرادی ہدف کی حد میں ہے (اوسط 110 mg/dL)",
    factor2: "باقاعدگی سے ادویات کا استعمال اور کوئی خوراک نہیں چھوٹی",
    factor3: "بلڈ پریشر معمول کے مطابق اور کنٹرول میں ہے (120/80 mmHg)",
    factor4: "روزانہ چیک ان میں کسی شدید علامت کی نشاندہی نہیں ہوئی",
    viewTrendsBtn: "رجحانات دیکھیں",

    trendsTitle: "صحت کے رجحانات",
    trendsSubtitle: "اہم طبی اشاریوں کی کثیر روزہ نگرانی",
    glucoseChartTitle: "بلڈ شوگر (mg/dL)",
    bloodPressureChartTitle: "بلڈ پریشر (mmHg)",
    adherenceChartTitle: "ادویات کی پابندی (%)",
    systolicLabel: "سسٹولک",
    diastolicLabel: "ڈائسٹولک",
    targetRangeLabel: "ہدف کی حد",
    dayLabel: "دن",

    conflictDetectedTitle: "تضاد پایا گیا (Conflict Detected)",
    conflictPatientReported: "مریض کی طرف سے درج شدہ بلڈ شوگر: 180 mg/dL",
    conflictEhrRecord: "کلینک کا آخری ریکارڈ (FHIR): 140 mg/dL",
    patientCheckInSource: "مریض کا چیک ان",
    fhirEhrSource: "ہسپتال کا ریکارڈ (FHIR EHR)",
    confidenceLowTag: "اعتماد: کم (Confidence: Low)",
    unansweredQuestionTag: "اس چیک ان میں ایک غیر جواب شدہ سوال بھی شامل تھا۔",
    conflictSimulationCaption: "This is a simulated system state for demonstration purposes. The actual reconciliation and verification logic has been separately validated in our technical proof of concept.",

    routedToReviewTitle: "کم اعتماد — ڈاکٹر کے جائزے کے لیے بھیج دیا گیا",
    routedToReviewDesc: "آپ کے چیک ان کو دیکھ بھال فراہم کرنے والے ڈاکٹر کے جائزے کے لیے بھیج دیا گیا ہے۔ جائزہ مکمل ہونے پر آپ کو مطلع کیا جائے گا۔",

    emergencyDetectedTitle: "ایمرجنسی صورتحال کی نشاندہی (Emergency Pattern Detected)",
    emergencyGuidanceText: "آپ کے جوابات کے مطابق، براہ کرم فوری طور پر طبی امداد حاصل کریں۔",
    emergencyAlertedText: "آپ کے ڈاکٹر اور نگہداشت فراہم کنندہ کو الرٹ جاری کر دیا گیا ہے۔",

    // M4: Provider Dashboard & Review Queue
    providerDashboardTitle: "کلینیکل پرووائیڈر ڈیش بورڈ",
    providerSubtitle: "مریضوں کی نگرانی، طبی تضادات اور ریویو کیو۔",
    activeCasesLabel: "فعال کیسز",
    urgentCasesLabel: "ارجنٹ کیسز",
    notificationsTitle: "کلینیکل اطلاعات",
    patientListTitle: "نگرانی کے تحت مریض",
    reviewQueueTitle: "کلینیکل ریویو کیو",
    viewReviewQueueBtn: "ریویو کیو کھولیں",
    columnPatient: "مریض",
    columnReason: "وجہ",
    columnConfidence: "اعتماد",
    columnStatus: "حیثیت",
    columnActions: "کارروائی",
    alertDetailsTitle: "طبی تضاد کا الرٹ اور جائزہ",
    reconciliationAlertBadge: "طبی تضاد",
    caseResolvedToast: "کیس کامیابی سے حل کر دیا گیا۔",
    caseAcknowledgedToast: "کیس کا جائزہ مکمل اور تسلیم کر لیا گیا۔",
    incompleteCheckInTitle: "نامکمل چیک ان",
    incompleteCheckInDesc: "خودکار تجزیے کے لیے ڈیٹا ناکافی تھا۔ معمول کے جائزے کے لیے زیر التواء ہے۔",

    // M4: Appointment Scheduling
    scheduleTitle: "مریض کے لیے اپوائنٹمنٹ بک کریں",
    scheduleSubtitle: "علی خان کے فالو اپ کے لیے دستیاب وقت کا انتخاب کریں۔",
    selectSlotLabel: "دستیاب اوقات",
    confirmBookingBtn: "اپوائنٹمنٹ کی تصدیق کریں",
    bookingSuccessTitle: "اپوائنٹمنٹ کنفرم ہو گئی",
    bookingSuccessDesc: "اپوائنٹمنٹ بک ہو گئی ہے۔ علی خان کو ان کے مریض پورٹل میں اطلاع بھیج دی گئی ہے۔",

    // M4: Patient Appointments View
    noAppointmentsTitle: "کوئی طے شدہ اپوائنٹمنٹ نہیں ہے",
    noAppointmentsDesc: "آپ کی اس وقت کوئی اپوائنٹمنٹ طے نہیں ہے۔ فالو اپ کی ضرورت پر آپ کا ڈاکٹر مطلع کرے گا۔",
    myAppointmentsTitle: "میری طے شدہ اپوائنٹمنٹس",
    appointmentWith: "ڈاکٹر",
    appointmentReason: "ملاقات کا مقصد",
    appointmentStatus: "حیثیت",

    // M4: Admin Portal
    adminDashboardTitle: "سسٹم ایڈمنسٹریشن اور ٹیلی میٹری",
    adminSubtitle: "پلیٹ فارم کی حالت، صارفین کی ڈائریکٹری اور آڈٹ لاگ۔",
    statUsers: "کل صارفین",
    statProviders: "ڈاکٹرز",
    statPatients: "مریض",
    statActiveAlerts: "فعال الرٹس",
    userManagementTitle: "صارفین کی فہرست اور کردار",
    auditLogTitle: "سسٹم آڈٹ اور تعمیل کا لاگ",

    // M4: Unified Settings
    unifiedSettingsTitle: "ایپلیکیشن ترتیبات",
    unifiedSettingsSubtitle: "زبان، کلینیکل کنکشن موڈ اور پروفائل کی ترتیبات۔",
    languageSettingLabel: "زبان کا انتخاب",
    connectionModeSettingLabel: "کلینیکل ڈیٹا سنکرونائزر",
    activeProfileLabel: "فعال پروفائل",

    // Stage 4 Live Additions
    authPasswordTooShort: "پاس ورڈ کم از کم 8 حروف پر مشتمل ہونا چاہیے۔",
    authPasswordMismatch: "پاس ورڈ مماثلت نہیں رکھتے۔",
    authInvalidEmail: "براہ کرم درست ای میل ایڈریس درج کریں۔",
    confirmPasswordLabel: "پاس ورڈ کی تصدیق کریں",
    confirmPasswordPlaceholder: "اپنا پاس ورڈ دوبارہ درج کریں",
    serverWakingTitle: "سرور بیدار ہو رہا ہے، براہ کرم انتظار کریں",
    serverWakingDesc: "کلاؤڈ سروس کے آغاز کے دوران چند لمحے لگ سکتے ہیں۔",
    consentTitle: "مریض کی رازداری اور دیکھ بھال کا اقرار نامہ",
    consentSubtitle: "آگے بڑھنے سے پہلے براہ کرم نگہداشت کا اقرار نامہ پڑھیں اور منظور کریں۔",
    consentBody: "کرونک کیئر اے آئی روزانہ علامات کی نگرانی، طبی ڈیٹا کی تصدیق اور ڈاکٹروں کو الرٹ بھیجنے میں مدد کرتا ہے۔ آپ کا ڈیٹا مکمل محفوظ اور خفیہ رکھا جاتا ہے اور صرف آپ کی نگہداشت کی ٹیم کے ساتھ شیئر کیا جاتا ہے۔ آپ کسی بھی وقت ترتیبات سے یہ اجازت واپس لے سکتے ہیں۔",
    consentAcceptBtn: "میں نے پڑھ لیا ہے اور منظور ہے",
    consentDeclineBtn: "مسترد کریں اور لاگ آؤٹ کریں",
    consentDeclinedNotice: "کرونک کیئر اے آئی کے استعمال کے لیے اقرار نامہ لازمی ہے۔",
    insulinOrSulfonylureaLabel: "کیا آپ انسولین یا سلفونائل یوریا ادویات استعمال کر رہے ہیں؟",
    insulinOrSulfonylureaHint: "لو شوگر (ہائپوگلیسیمیا) کے خطرے کی نشاندہی میں مدد ملتی ہے۔",
    insulinYes: "جی ہاں، انسولین یا سلفونائل یوریا لے رہا ہوں",
    insulinNo: "نہیں، کوئی بھی نہیں",
    selectEhrSystemLabel: "ہسپتال یا EHR سسٹم منتخب کریں",
    patientIdLabel: "مریض کی شناختی آئی ڈی (MRN / Patient ID)",
    patientIdPlaceholder: "مثلاً 768be7ac-743f-4c24-aa0f-fed5a3a38b6a یا PT-04821",
    connectEhrBtn: "EHR منسلک کریں",
    disconnectEhrBtn: "منقطع کریں",
    disconnectConfirm: "کیا آپ واقعی اس EHR سے رابطہ ختم کرنا چاہتے ہیں؟",
    connectedBadgeTitle: "منسلک EHR",
    isolatedBadgeTitle: "آئسولیٹڈ موڈ (ذاتی ریکارڈ)",
    lastVerified: "آخری تصدیق",
    patientIdMasked: "مریض آئی ڈی",
    dontHaveInfoBtn: "میرے پاس یہ معلومات نہیں ہیں",
    checkinSummaryTitle: "چیک ان محفوظ اور تصدیق شدہ",
    checkinSummarySubtitle: "آپ کا روزانہ ڈیٹا آپ کے کلینیکل پروفائل کے مطابق پروسیس کر لیا گیا ہے۔",
    agreementsCountLabel: "تصدیق شدہ درست اشارے",
    missingCountLabel: "نامکمل یا چھوٹی ہوئی معلومات",
    confidenceLabel: "تجزیاتی اعتماد",
    riskScoringOmittedNote: "نوٹ: خودکار رسک اسکورنگ اس ورژن کا حصہ نہیں ہے۔ دیکھ بھال کی ترجیح ڈیٹا کے تضاد اور حفاظتی اصولوں پر مبنی ہے۔",
    notEnoughHistory: "ابھی کافی تاریخ موجود نہیں ہے (رجحانات دیکھنے کے لیے کم از کم 3 چیک ان ضروری ہیں)۔",
    serverTyping: "جواب کا تجزیہ ہو رہا ہے...",
    overdueBadge: "وقت گزر چکا ہے",
    emergencyPriority: "ایمرجنسی",
    actionNoteLabel: "کلینیکل نوٹ (لازمی)",
    actionNotePlaceholder: "طبی مشاہدہ، وجہ یا نگہداشت کے لیے ہدایات درج کریں...",
    actionResolveBtn: "حل کریں اور الرٹ بند کریں",
    actionEscalateBtn: "نگہداشت کی ٹیم کو ایسکلیٹ کریں",
    actionAcknowledgeBtn: "الرٹ تسلیم کریں",
    demoCrossPortalLabel: "ڈیمو فیچر",
  }
};
