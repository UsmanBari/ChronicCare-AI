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
  logoutBtn: string;

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
  showPassword: string;
  hidePassword: string;
  showConfirmPassword: string;
  hideConfirmPassword: string;

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
  authEmailAlreadyInUse: string;
  authWeakPassword: string;
  authTooManyRequests: string;
  authNetworkError: string;
  sessionExpired: string;
  forgotPasswordBtn: string;
  resetPasswordSent: string;
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
  profileMedsNextStepHint: string;
  demoPatientNotice: string;
  recordMedsPurpose: string;
  hospitalRecordMedsTitle: string;
  somethingDifferent: string;
  ageLabel: string;
  agePlaceholder: string;

  // Screen 4: Home / Dashboard (Patient)
  homeGreeting: string;
  homeSubtitle: string;
  reminderTitle: string;
  reminderDesc: string;
  reminderDescHypertension: string;
  reminderDescBoth: string;
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
  checkInEntrySubtitleHypertension: string;
  checkInEntrySubtitleBoth: string;
  howAreYouFeelingLabel: string;
  howAreYouFeelingPlaceholder: string;
  howAreYouFeelingPlaceholderHypertension: string;
  howAreYouFeelingPlaceholderBoth: string;
  sampleVoiceNoteDiabetes: string;
  sampleVoiceNoteHypertension: string;
  sampleVoiceNoteBoth: string;
  voiceInputTitle: string;
  listeningAnimationText: string;
  voiceHelperText: string;

  // Baseline Observations & Landing Telemetry
  obsPlaceholderSystolic: string;
  obsPlaceholderDiastolic: string;
  obsPlaceholderGlucose: string;
  obsPlaceholderGlucoseMmol: string;
  obsGlucoseRangeErrorMmol: string;
  obsGlucoseRangeErrorMgdl: string;
  obsOptionGlucoseMgdl: string;
  obsOptionGlucoseMmol: string;
  landingHtnDemoPatient: string;
  landingHtnDemoCondition: string;
  landingHtnDemoReading: string;
  landingHtnDemoValue: string;
  landingHtnBaselineValue: string;
  landingHtnMonitoringNote: string;

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
  trendRising: string;
  trendFalling: string;
  trendStable: string;
  trendNotEnoughHistory: string;
  trendNotEnoughExplain: string;
  trendsErrorTitle: string;
  trendsErrorRetry: string;
  trendsReadingsInDays: string;
  providerTrendsTitle: string;
  providerLongitudinalWindow: string;
  trendLongitudinalTrajectory: string;
  clinicalObservationWindow8Day: string;
  noTrendsAvailable: string;
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
  langRomanUrdu: string;
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
  dontKnowBtn: string;
  skipQuestionBtn: string;
  someoneElseAnsweringBtn: string;
  whyAmIAskedThisBtn: string;
  questionProgressText: string;
  sendBtnLabel: string;
  micSpeakLabel: string;
  micDisabledLabel: string;
  interviewRetryBtn: string;
  interviewEmergencyCall: string;
  interviewNetworkError: string;
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
  researchPrototypeNotice: string;
  consentBulletRoleAccess: string;
  consentBulletWithdrawConsent: string;
  consentBulletNotForEmergencies: string;
  routedToReviewHeadline: string;
  routedToReviewExplanation: string;
  confidenceLowChip: string;
  medicationsNoneRecorded: string;
  noCheckinsYet: string;
  notConnectedYet: string;
  isolatedModeLabel: string;
  needsClinicianReviewTitle: string;
  readingDiffersTitle: string;
  firstCheckinNoRecordTitle: string;
  firstCheckinNoRecordDesc: string;
  earlierCheckinLabel: string;
  savedReadingLabel: string;
  clinicianReviewAnswers: string;
  connectionBadgeIsolated: string;
  connectionBadgeIsolatedShort: string;
  connectionBadgeConnected: string;
  connectionBadgeConnectedGeneric: string;
  demoSimulationBadge: string;
  notOnFile: string;
  notReportedToday: string;
  demoVoiceSampleBadge: string;
  recordingVoice: string;
  transcribingVoice: string;
  stopRecording: string;
  cancelRecording: string;
  hospitalRecordMedsManagedLine: string;
  simulatedExampleBadge: string;
  directHotlineDispatch: string;
  researchPrototypeDisclaimer: string;
  notFoundTitle: string;
  notFoundDesc: string;
  returnHomeBtn: string;

  // Physical Measurements Units & Labels
  heightToggleLabel: string;
  weightToggleLabel: string;
  heightUnitCm: string;
  heightUnitFtIn: string;
  weightUnitLb: string;
  weightUnitKg: string;
  heightLabelCm: string;
  heightLabelFtIn: string;
  feetLabel: string;
  inchesLabel: string;
  weightLabelLb: string;
  weightLabelKg: string;
  heightErrorCm: string;
  heightErrorFtIn: string;
  heightFeetError: string;
  heightInchesError: string;
  weightErrorKg: string;
  weightErrorLb: string;
  bodyMeasurementsOptional: string;
  waistLabelIn: string;
  waistLabelCm: string;
  waistToggleLabel: string;
  waistUnitIn: string;
  waistUnitCm: string;
  waistUnitInAria: string;
  waistUnitCmAria: string;
  waistHelperText: string;
  waistErrorCm: string;
  waistErrorIn: string;
  doctorOnRecordLabel: string;
  ehrAllergiesTitle: string;
  noEhrAllergiesRecorded: string;
  providerRiskTitle: string;
  providerRiskNotice: string;
  riskBandLow: string;
  riskBandMedium: string;
  riskBandHigh: string;
  riskReasonsTitle: string;
  riskCaveatsTitle: string;
  riskCaveatHomeBp: string;
  riskCaveatNotValidatedPakistan: string;
  riskMissingDataTitle: string;
  riskMissingDataDescription: string;
  riskMissingBp: string;
  riskMissingWaist: string;
  riskMissingSmoking: string;
  riskMissingHeightWeight: string;

  // Record History, Export & Import (Day 6)
  recordHistoryTitle: string;
  recordHistoryBtn: string;
  viewFullHistory: string;
  noHistoryRecorded: string;
  historyField: string;
  historyOldValue: string;
  historyNewValue: string;
  historyChangedAt: string;
  originSelfReported: string;
  originOcr: string;
  originClinician: string;
  originImport: string;
  originEhr: string;
  exportRecordBtn: string;
  exportJson: string;
  exportFhir: string;
  exporting: string;
  importRecordBtn: string;
  importTitle: string;
  importSubtitle: string;
  importPreviewTitle: string;
  importToAdd: string;
  importDuplicates: string;
  importInvalid: string;
  confirmImport: string;
  cancelImport: string;
  importSuccess: string;
  importFailed: string;
  importBaselineNote: string;
  recentRecordChangesTitle: string;
  recentRecordChangesSubtitle: string;
  importBadgeAdd: string;
  importBadgeSkip: string;

  // OCR v1 (Day 7)
  uploadDocumentBtn: string;
  ocrConfirmTitle: string;
  ocrConfirmSubtitle: string;
  ocrNoticeUrdu: string;
  ocrConfirmSaveBtn: string;
  ocrFixBtn: string;
  ocrRemoveBtn: string;
  ocrConfirmedBadge: string;
  ocrEvidenceLabel: string;
  ocrBadge: string;
  ocrObservationsTitle: string;
  ocrMedicationsTitle: string;
  ocrAllergiesTitle: string;
  ocrEmptyExtracted: string;
  ocrUploading: string;
  ocrUploadFailed: string;
  ocrSaveSuccess: string;
  ocrConfirmItem: string;
  ocrCancelBtn: string;
  failedToLoadHistory: string;
  failedToExportRecord: string;
  failedToPreviewImport: string;
  failedToCommitImport: string;
  reasonDuplicate: string;
  reasonOutOfRange: string;
  reasonInvalidType: string;
  reasonInvalidUnit: string;
  reasonInvalidDate: string;
  reasonInvalidMedName: string;
  reasonInvalidMedDosage: string;
  reasonInvalidMedStatus: string;
  reasonInvalidAllergy: string;
  reasonAllergyTooLong: string;
  ocrInvalidItemBanner: string;
  ocrFixOrRemoveHint: string;

  // Patient Explanation (I3 Day 2)
  whyThisResultBtn: string;
  hideWhyThisResultBtn: string;
  explanationSourcesTitle: string;
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
    logoutBtn: "Log Out",

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
    showPassword: "Show password",
    hidePassword: "Hide password",
    showConfirmPassword: "Show confirm password",
    hideConfirmPassword: "Hide confirm password",

    providerLoginTitle: "Provider Clinical Access",
    providerLoginSubtitle: "Sign in to access patient triage, review queue, and EHR alerts.",
    providerIdLabel: "Clinical ID / Provider Email",
    providerIdPlaceholder: "e.g. dr.sanamalik@citygeneral.org",
    adminLoginTitle: "System Administration Portal",
    adminLoginSubtitle: "Manage platform users, system parameters, and audit trails.",

    // Auth / Firebase Errors
    authInvalidApiKey: "Invalid Firebase API configuration. Please check your system settings.",
    authUserNotFound: "Incorrect email or password. Please check your details and try again.",
    authWrongPassword: "Incorrect email or password. Please check your details and try again.",
    authInvalidCredentials: "Incorrect email or password. Please check your details and try again.",
    authEmailAlreadyInUse: "An account with this email already exists. Please sign in instead.",
    authWeakPassword: "Password is too weak. Please use at least 8 characters.",
    authTooManyRequests: "Too many failed attempts. Please wait a moment before trying again.",
    authNetworkError: "Network error. Please check your connection and try again.",
    sessionExpired: "Your session expired. Please sign in again.",
    forgotPasswordBtn: "Forgot password?",
    resetPasswordSent: "If an account exists for this email, password reset instructions have been sent.",
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
    fhirCardDesc: "Link your record with City General Hospital using the HL7® FHIR® standard interface.",
    fhirConnectingText: "Establishing FHIR connection...",
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
    profileMedsNextStepHint: "If you do not link a hospital record, you can add your medicines in the next steps.",
    demoPatientNotice: "Demo patient",
    recordMedsPurpose: "Your medicines. We use this to check what you tell us in each check-in.",
    hospitalRecordMedsTitle: "Your medicines",
    somethingDifferent: "If this looks wrong, tell your clinician.",
    ageLabel: "Patient Age (Years)",
    agePlaceholder: "e.g. 58",

    homeGreeting: "Good day, Ali Khan",
    homeSubtitle: "Your daily care overview and proactive symptom check-in.",
    reminderTitle: "Time for your daily check-in",
    reminderDesc: "Take 60 seconds to record your daily symptoms and ensure your care plan remains on track.",
    reminderDescHypertension: "Take 60 seconds to log your blood pressure and daily symptoms to keep your hypertension care plan on track.",
    reminderDescBoth: "Take 60 seconds to log your blood pressure, blood sugar, and symptoms to keep your care plan on track.",
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
    checkInEntrySubtitleHypertension: "Describe your blood pressure readings, symptoms, or speak into your microphone.",
    checkInEntrySubtitleBoth: "Describe your blood pressure, blood sugar readings, and symptoms or speak into your microphone.",
    howAreYouFeelingLabel: "How are you feeling today?",
    howAreYouFeelingPlaceholder: "Describe any symptoms, energy levels, fatigue, or changes you noticed today...",
    howAreYouFeelingPlaceholderHypertension: "Describe your blood pressure, headaches, dizziness, fatigue, or any symptoms you noticed today...",
    howAreYouFeelingPlaceholderBoth: "Describe your blood pressure, blood sugar, fatigue, thirst, or changes you noticed today...",
    sampleVoiceNoteDiabetes: "I've been feeling a bit tired and thirsty lately",
    sampleVoiceNoteHypertension: "My blood pressure was 135/85 this morning and I felt a bit dizzy earlier",
    sampleVoiceNoteBoth: "Checked my blood pressure and sugar this morning, feeling slightly fatigued",
    voiceInputTitle: "Tap microphone for Voice Input",
    listeningAnimationText: "Listening... (capturing audio)",
    voiceHelperText: "Speak clearly. Audio will be transcribed directly into your check-in notes.",

    obsPlaceholderSystolic: "e.g. 130",
    obsPlaceholderDiastolic: "e.g. 85",
    obsPlaceholderGlucose: "e.g. 140",
    obsPlaceholderGlucoseMmol: "e.g. 7.0",
    obsGlucoseRangeErrorMmol: "Glucose reading must be between 1.1 and 33.3 mmol/L.",
    obsGlucoseRangeErrorMgdl: "Glucose reading must be between 20 and 600 mg/dL.",
    obsOptionGlucoseMgdl: "Blood Glucose (mg/dL)",
    obsOptionGlucoseMmol: "Blood Glucose (mmol/L)",
    landingHtnDemoPatient: "Bilal Ahmed (62y M)",
    landingHtnDemoCondition: "HTN",
    landingHtnDemoReading: "Blood Pressure",
    landingHtnDemoValue: "150/95 mmHg",
    landingHtnBaselineValue: "128/82 mmHg",
    landingHtnMonitoringNote: "Continuous protocol tracking for Type 2 Diabetes & Hypertension monitoring.",

    adaptiveInterviewTitle: "Adaptive Symptom Interview",
    adaptiveInterviewSubtitle: "Personalized follow-up questions tailored to your check-in report.",
    questionCount: "Step-by-Step Clinical Follow-up",
    q1Text: "Have you noticed increased thirst recently?",
    q2Text: "Have you been urinating more frequently than usual?",
    q3Text: "Have you missed any medication doses this week?",
    submitCheckInBtn: "Submit Check-In",

    confirmationTitle: "Check-in submitted!",
    confirmationSubtitle: "Your daily health check-in has been successfully recorded.",
    confirmationMessage: "Thank you for completing your daily check-in. Your responses have been recorded in your active profile.",
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
    trendRising: "Rising",
    trendFalling: "Falling",
    trendStable: "Stable",
    trendNotEnoughHistory: "Not enough history",
    trendNotEnoughExplain: "Not enough readings yet. Trends appear after 3 check-ins.",
    trendsErrorTitle: "Unable to load trends right now.",
    trendsErrorRetry: "Try Again",
    trendsReadingsInDays: "{n} readings in {days} days",
    providerTrendsTitle: "Trends (30 days)",
    providerLongitudinalWindow: "Longitudinal window: {days} days",
    trendLongitudinalTrajectory: "Longitudinal Trajectory (30-Day Window)",
    clinicalObservationWindow8Day: "8-Day Clinical Observation Window",
    noTrendsAvailable: "No trend data available.",
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
    langRomanUrdu: "Roman Urdu",
    connectionModeSettingLabel: "Clinical Data Synchronizer",
    activeProfileLabel: "Active Profile",

    // Stage 4 Live Additions
    authPasswordTooShort: "Password must be at least 8 characters.",
    authPasswordMismatch: "Passwords do not match.",
    authInvalidEmail: "Please enter a valid email address.",
    confirmPasswordLabel: "Confirm Password",
    confirmPasswordPlaceholder: "Re-enter your password",
    serverWakingTitle: "Waking up the server, this can take up to a minute on the free test plan",
    serverWakingDesc: "Initial requests may take a moment while the cloud service starts.",
    consentTitle: "Patient Privacy & Care Consent",
    consentSubtitle: "Please review and accept our clinical monitoring consent before proceeding.",
    consentBody: "ChronicCare AI is a university research prototype. It records your daily symptoms and readings, compares what you report with your health record, and flags differences for a clinician to review. It does not diagnose, give treatment advice, or replace your doctor, and it is not for emergencies: if you feel seriously unwell, contact your local emergency services. The answers you enter and the results are stored in this prototype's database. In this prototype, any clinician account registered with the system can view check-ins that need review. Please enter test information only unless you are part of an approved evaluation. You can withdraw consent at any time in your settings; withdrawing stops new check-ins but does not delete reviews that were already sent.",
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
    dontKnowBtn: "I don't know",
    skipQuestionBtn: "Skip",
    someoneElseAnsweringBtn: "Someone else is answering",
    whyAmIAskedThisBtn: "Why am I asked this?",
    questionProgressText: "Progress",
    sendBtnLabel: "Send",
    micSpeakLabel: "Speak your answer",
    micDisabledLabel: "Voice disabled - enable in Settings",
    interviewRetryBtn: "Retry",
    interviewEmergencyCall: "In an emergency, call your local emergency number.",
    interviewNetworkError: "We could not send your answer. If this is an emergency, call your local emergency number now.",
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
    researchPrototypeNotice: "Research prototype. Please enter test information only.",
    consentBulletRoleAccess: "Role-based access: patients, clinicians and administrators see different screens and data.",
    consentBulletWithdrawConsent: "You can withdraw consent at any time in your settings.",
    consentBulletNotForEmergencies: "This prototype is not for emergencies.",
    routedToReviewHeadline: "Sent for clinician review",
    routedToReviewExplanation: "A clinician will see this in their review queue. This version of the app does not send notifications.",
    confidenceLowChip: "Confidence: Low (a reading was missing)",
    medicationsNoneRecorded: "Medications: none recorded yet",
    noCheckinsYet: "No check-ins yet",
    notConnectedYet: "Not connected yet",
    isolatedModeLabel: "Isolated Mode (Local Store)",
    needsClinicianReviewTitle: "Needs clinician review",
    readingDiffersTitle: "Your reading differs from the record",
    firstCheckinNoRecordTitle: "This is your first check-in",
    firstCheckinNoRecordDesc: "There is nothing on file to compare with yet, so a clinician will review it.",
    earlierCheckinLabel: "Your earlier check-in",
    savedReadingLabel: "Your saved reading",
    clinicianReviewAnswers: "A clinician will review today's answers.",
    connectionBadgeIsolated: "Not connected to a hospital record. Using the record you entered",
    connectionBadgeIsolatedShort: "Local record (not connected)",
    connectionBadgeConnected: "Connected to {system} (test environment)",
    connectionBadgeConnectedGeneric: "Connected to hospital EHR (test environment)",
    demoSimulationBadge: "Demo",
    notOnFile: "Not on file",
    notReportedToday: "Not reported today",
    demoVoiceSampleBadge: "Demo voice sample",
    recordingVoice: "Recording... Speak clearly",
    transcribingVoice: "Transcribing your voice...",
    stopRecording: "Stop recording",
    cancelRecording: "Cancel",
    hospitalRecordMedsManagedLine: "Managed by your hospital record. Your clinician sees the full list.",
    simulatedExampleBadge: "Simulated example",
    directHotlineDispatch: "Direct Hotline Dispatch:",
    researchPrototypeDisclaimer: "Research prototype, not a medical device.",
    notFoundTitle: "Page Not Found",
    notFoundDesc: "The requested page does not exist or has been moved.",
    returnHomeBtn: "Return to Home",

    // Physical Measurements Units & Labels
    heightToggleLabel: "Height unit",
    weightToggleLabel: "Weight unit",
    heightUnitCm: "cm",
    heightUnitFtIn: "ft + in",
    weightUnitLb: "lb",
    weightUnitKg: "kg",
    heightLabelCm: "Height (cm)",
    heightLabelFtIn: "Height (ft + in)",
    feetLabel: "Feet",
    inchesLabel: "Inches",
    weightLabelLb: "Weight (lb)",
    weightLabelKg: "Weight (kg)",
    heightErrorCm: "Height must be between 50 and 250 cm.",
    heightErrorFtIn: "Height must be between 1 ft 8 in and 8 ft 2 in.",
    heightFeetError: "Feet must be a whole number between 1 and 8.",
    heightInchesError: "Inches must be between 0 and 11.99.",
    weightErrorKg: "Weight must be between 20 and 400 kg.",
    weightErrorLb: "Weight must be between 44 and 882 lb.",
    bodyMeasurementsOptional: "Body Measurements (Optional)",
    waistLabelIn: "Waist (in)",
    waistLabelCm: "Waist (cm)",
    waistToggleLabel: "Waist measurement unit",
    waistUnitIn: "in",
    waistUnitCm: "cm",
    waistUnitInAria: "Waist unit: in",
    waistUnitCmAria: "Waist unit: cm",
    waistHelperText: "Measure around your waist at the top of your hip bones, after breathing out.",
    waistErrorCm: "Waist circumference must be between 40 and 200 cm (needs doctor review).",
    waistErrorIn: "Waist circumference must be between 15.7 and 78.7 inches (needs doctor review).",
    doctorOnRecordLabel: "Doctor on record: {name} (from your hospital record)",
    ehrAllergiesTitle: "Allergies in your hospital record",
    noEhrAllergiesRecorded: "None recorded",
    providerRiskTitle: "Diabetes risk (experimental)",
    providerRiskNotice: "Internal research feature — not for clinical diagnosis without physician evaluation.",
    riskBandLow: "Low",
    riskBandMedium: "Moderate",
    riskBandHigh: "High",
    riskReasonsTitle: "Top Contributing Factors",
    riskCaveatsTitle: "Clinical Caveats",
    riskCaveatHomeBp: "Home blood pressure readings are self-reported and have not been validated against clinic measurements.",
    riskCaveatNotValidatedPakistan: "This model was developed on US NHANES data and has not been validated on a Pakistani population.",
    riskMissingDataTitle: "Not Enough Information",
    riskMissingDataDescription: "Risk assessment requires complete baseline measurements:",
    riskMissingBp: "Blood pressure reading in the last 30 days",
    riskMissingWaist: "Waist circumference in patient profile",
    riskMissingSmoking: "Smoking status in patient profile",
    riskMissingHeightWeight: "Height and weight in patient profile",

    // Record History, Export & Import (Day 6)
    recordHistoryTitle: "Record History",
    recordHistoryBtn: "History",
    viewFullHistory: "View full record history",
    noHistoryRecorded: "No changes recorded yet.",
    historyField: "Field",
    historyOldValue: "Before",
    historyNewValue: "After",
    historyChangedAt: "Date & Time",
    originSelfReported: "You",
    originOcr: "OCR Scan",
    originClinician: "Clinician",
    originImport: "Imported",
    originEhr: "Hospital EHR",
    exportRecordBtn: "Download my record",
    exportJson: "Download JSON",
    exportFhir: "Download FHIR",
    exporting: "Downloading...",
    importRecordBtn: "Import a record file",
    importTitle: "Import Health Record",
    importSubtitle: "Upload a previously exported ChronicCare JSON or standard FHIR Bundle file.",
    importPreviewTitle: "Import Preview",
    importToAdd: "Items to add",
    importDuplicates: "Duplicates (will skip)",
    importInvalid: "Invalid (cannot import)",
    confirmImport: "Confirm import",
    cancelImport: "Cancel",
    importSuccess: "Record imported successfully",
    importFailed: "Import failed",
    importBaselineNote: "Readings older than 14 days will be imported to your history, but will not be used in the 14-day check-in baseline.",
    recentRecordChangesTitle: "Recent record changes",
    recentRecordChangesSubtitle: "Recent updates made to patient's clinical baseline record",
    importBadgeAdd: "Add",
    importBadgeSkip: "Skip",

    // OCR v1 (Day 7)
    uploadDocumentBtn: "Upload Lab Report / Prescription",
    ocrConfirmTitle: "Confirm Extracted Values",
    ocrConfirmSubtitle: "Review each detected value below. Only confirmed items will be saved to your health record.",
    ocrNoticeUrdu: "We can only read English reports for now. Please add these values yourself.",
    ocrConfirmSaveBtn: "Confirm & Save to Record",
    ocrFixBtn: "Fix",
    ocrRemoveBtn: "Remove",
    ocrConfirmedBadge: "Confirmed",
    ocrEvidenceLabel: "Detected in document:",
    ocrBadge: "OCR",
    ocrObservationsTitle: "Observations & Lab Tests",
    ocrMedicationsTitle: "Medications",
    ocrAllergiesTitle: "Allergies",
    ocrEmptyExtracted: "No readable clinical values were detected in this image.",
    ocrUploading: "Analyzing document...",
    ocrUploadFailed: "Could not process document. Please ensure it is a clear JPEG or PNG under 5MB.",
    ocrSaveSuccess: "Confirmed values saved to your health record.",
    ocrConfirmItem: "Confirm",
    ocrCancelBtn: "Cancel",
    failedToLoadHistory: "Failed to load record history",
    failedToExportRecord: "Failed to export record",
    failedToPreviewImport: "Failed to preview import file",
    failedToCommitImport: "Failed to import record",
    reasonDuplicate: "Duplicate entry",
    reasonOutOfRange: "Value out of clinical range",
    reasonInvalidType: "Unsupported observation type",
    reasonInvalidUnit: "Invalid unit",
    reasonInvalidDate: "Invalid date or time",
    reasonInvalidMedName: "Invalid medication name",
    reasonInvalidMedDosage: "Invalid dosage",
    reasonInvalidMedStatus: "Invalid medication status",
    reasonInvalidAllergy: "Invalid allergy substance",
    reasonAllergyTooLong: "Reaction text too long",
    ocrInvalidItemBanner: "Please fix or remove the highlighted invalid item before saving.",
    ocrFixOrRemoveHint: "Value is invalid. Click Fix to correct or Remove to discard.",

    // Patient Explanation (I3 Day 2)
    whyThisResultBtn: "Why this result?",
    hideWhyThisResultBtn: "Hide explanation",
    explanationSourcesTitle: "Clinical Sources",
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
    logoutBtn: "لاگ آؤٹ",

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
    showPassword: "پاس ورڈ دکھائیں",
    hidePassword: "پاس ورڈ چھپائیں",
    showConfirmPassword: "پاس ورڈ کی تصدیق دکھائیں",
    hideConfirmPassword: "پاس ورڈ کی تصدیق چھپائیں",

    providerLoginTitle: "ڈاکٹر / کلینیکل لاگ ان",
    providerLoginSubtitle: "مریضوں کی فہرست اور الرٹس تک رسائی کے لیے سائن ان کریں۔",
    providerIdLabel: "کلینیکل آئی ڈی یا ای میل",
    providerIdPlaceholder: "مثلاً dr.sanamalik@citygeneral.org",
    adminLoginTitle: "سسٹم ایڈمنسٹریشن پورٹل",
    adminLoginSubtitle: "سسٹم کے صارفین اور آڈٹ لاگ کا انتظام کریں۔",

    // Auth / Firebase Errors
    authInvalidApiKey: "فائر بیس API کی ترتیب درست نہیں ہے۔ براہ کرم سسٹم سیٹنگز چیک کریں۔",
    authUserNotFound: "ای میل یا پاس ورڈ درست نہیں ہے۔ براہ کرم اپنی تفصیلات چیک کریں اور دوبارہ کوشش کریں۔",
    authWrongPassword: "ای میل یا پاس ورڈ درست نہیں ہے۔ براہ کرم اپنی تفصیلات چیک کریں اور دوبارہ کوشش کریں۔",
    authInvalidCredentials: "ای میل یا پاس ورڈ درست نہیں ہے۔ براہ کرم اپنی تفصیلات چیک کریں اور دوبارہ کوشش کریں۔",
    authEmailAlreadyInUse: "اس ای میل پر پہلے ہی اکاؤنٹ موجود ہے۔ براہ کرم لاگ ان کریں۔",
    authWeakPassword: "پاس ورڈ بہت کمزور ہے۔ براہ کرم کم از کم 8 حروف استعمال کریں۔",
    authTooManyRequests: "بہت زیادہ کوششیں کی گئیں۔ براہ کرم کچھ دیر بعد دوبارہ کوشش کریں۔",
    authNetworkError: "نیٹ ورک کی خرابی۔ براہ کرم اپنا انٹرنیٹ کنکشن چیک کریں اور دوبارہ کوشش کریں۔",
    sessionExpired: "آپ کا سیشن ختم ہو چکا ہے۔ براہ کرم دوبارہ سائن ان کریں۔",
    forgotPasswordBtn: "پاس ورڈ بھول گئے؟",
    resetPasswordSent: "اگر اس ای میل پر اکاؤنٹ موجود ہے تو پاس ورڈ تبدیل کرنے کی ہدایات بھیج دی گئی ہیں۔",
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
    profileMedsNextStepHint: "اگر آپ اسپتال کا ریکارڈ منسلک نہیں کرتے تو اگلے مراحل میں اپنی ادویات شامل کر سکتے ہیں۔",
    demoPatientNotice: "ڈیمو مریض",
    recordMedsPurpose: "آپ کی ادویات۔ ہم اسے ہر چیک ان میں آپ کی بتائی ہوئی باتوں کی تصدیق کے لیے استعمال کرتے ہیں۔",
    hospitalRecordMedsTitle: "آپ کی ادویات",
    somethingDifferent: "اگر یہ غلط معلوم ہو تو اپنے معالج کو بتائیں۔",
    ageLabel: "مریض کی عمر (سال)",
    agePlaceholder: "مثلاً 58",

    homeGreeting: "خوش آمدید، علی خان",
    homeSubtitle: "آپ کی روزانہ نگہداشت کا جائزہ اور علامات کا چیک ان۔",
    reminderTitle: "روزانہ چیک ان کا وقت ہو گیا ہے",
    reminderDesc: "اپنی علامات درج کرنے کے لیے 60 سیکنڈ نکالیں تاکہ آپ کی صحت کا معمول درست رہے۔",
    reminderDescHypertension: "بلڈ پریشر اور روزانہ کی علامات درج کرنے کے لیے 60 سیکنڈ نکالیں تاکہ آپ کی نگہداشت کا معمول درست رہے۔",
    reminderDescBoth: "بلڈ پریشر، شوگر اور علامات درج کرنے کے لیے 60 سیکنڈ نکالیں تاکہ آپ کی نگہداشت کا معمول درست رہے۔",
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
    checkInEntrySubtitleHypertension: "اپنا بلڈ پریشر، علامات اور روزمرہ کیفیت بیان کریں یا مائیکروفون میں بولیں۔",
    checkInEntrySubtitleBoth: "اپنا بلڈ پریشر، بلڈ شوگر اور علامات بیان کریں یا مائیکروفون میں بولیں۔",
    howAreYouFeelingLabel: "آج آپ کیسا محسوس کر رہے ہیں؟",
    howAreYouFeelingPlaceholder: "اپنی علامات، تھکاوٹ، پیاس یا کسی تبدیلی کے بارے میں بتائیں...",
    howAreYouFeelingPlaceholderHypertension: "اپنا بلڈ پریشر، سر درد، چکر، تھکاوٹ یا کوئی بھی علامات درج کریں...",
    howAreYouFeelingPlaceholderBoth: "اپنا بلڈ پریشر، شوگر، تھکاوٹ، پیاس یا کسی تبدیلی کے بارے میں بتائیں...",
    sampleVoiceNoteDiabetes: "مجھے کچھ عرصے سے تھکاوٹ اور زیادہ پیاس محسوس ہو رہی ہے",
    sampleVoiceNoteHypertension: "آج صبح میرا بلڈ پریشر 135/85 تھا اور مجھے تھوڑا چکر آ رہا تھا",
    sampleVoiceNoteBoth: "صبح بلڈ پریشر اور شوگر چیک کی، تھوڑی تھکاوٹ محسوس ہو رہی ہے",
    voiceInputTitle: "آواز سے درج کرنے کے لیے مائیکروفون دبائیں",
    listeningAnimationText: "سن رہا ہے... (آڈیو ریکارڈنگ جاری)",
    voiceHelperText: "صاف آواز میں بولیں۔ آپ کی آواز تحریر میں تبدیل ہو جائے گی۔",

    obsPlaceholderSystolic: "مثلاً 130",
    obsPlaceholderDiastolic: "مثلاً 85",
    obsPlaceholderGlucose: "مثلاً 140",
    obsPlaceholderGlucoseMmol: "مثلاً 7.0",
    obsGlucoseRangeErrorMmol: "بلڈ گلوکوز کی ریڈنگ 1.1 اور 33.3 mmol/L کے درمیان ہونی چاہیے۔",
    obsGlucoseRangeErrorMgdl: "بلڈ شوگر کی پیمائش 20 اور 600 mg/dL کے درمیان ہونی چاہیے۔",
    obsOptionGlucoseMgdl: "بلڈ شوگر (mg/dL)",
    obsOptionGlucoseMmol: "بلڈ شوگر (mmol/L)",
    landingHtnDemoPatient: "بلال احمد (62 سال، مرد)",
    landingHtnDemoCondition: "ہائی بلڈ پریشر",
    landingHtnDemoReading: "بلڈ پریشر",
    landingHtnDemoValue: "150/95 mmHg",
    landingHtnBaselineValue: "128/82 mmHg",
    landingHtnMonitoringNote: "ذیابیطس اور ہائی بلڈ پریشر کی علامات اور پروٹوکول کی مسلسل نگرانی۔",

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
    trendRising: "اوپر کی طرف",
    trendFalling: "نیچے کی طرف",
    trendStable: "مستحکم",
    trendNotEnoughHistory: "ناکافی ریکارڈ",
    trendNotEnoughExplain: "ابھی ناکافی ریڈنگز ہیں۔ رجحانات 3 چیک ان کے بعد ظاہر ہوتے ہیں۔",
    trendsErrorTitle: "اس وقت رجحانات لوڈ نہیں ہو سکے",
    trendsErrorRetry: "دوبارہ کوشش کریں",
    trendsReadingsInDays: "{days} دن میں {n} ریڈنگ",
    providerTrendsTitle: "رجحانات (30 دن)",
    providerLongitudinalWindow: "طویل مدتی دورانیہ: {days} دن",
    trendLongitudinalTrajectory: "طویل مدتی رجحان (30 دن کا دورانیہ)",
    clinicalObservationWindow8Day: "8 دن کا کلینیکل مشاہداتی دورانیہ",
    noTrendsAvailable: "کوئی رجحان کا ڈیٹا دستیاب نہیں ہے۔",
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
    langRomanUrdu: "رومن اردو",
    connectionModeSettingLabel: "کلینیکل ڈیٹا سنکرونائزر",
    activeProfileLabel: "فعال پروفائل",

    // Stage 4 Live Additions
    authPasswordTooShort: "پاس ورڈ کم از کم 8 حروف پر مشتمل ہونا چاہیے۔",
    authPasswordMismatch: "پاس ورڈ مماثلت نہیں رکھتے۔",
    authInvalidEmail: "براہ کرم درست ای میل ایڈریس درج کریں۔",
    confirmPasswordLabel: "پاس ورڈ کی تصدیق کریں",
    confirmPasswordPlaceholder: "اپنا پاس ورڈ دوبارہ درج کریں",
    serverWakingTitle: "سرور بیدار ہو رہا ہے، مفت ٹیسٹ پلان پر اس میں ایک منٹ تک لگ سکتا ہے",
    serverWakingDesc: "کلاؤڈ سروس کے آغاز کے دوران چند لمحے لگ سکتے ہیں۔",
    consentTitle: "مریض کی رازداری اور دیکھ بھال کا اقرار نامہ",
    consentSubtitle: "آگے بڑھنے سے پہلے براہ کرم نگہداشت کا اقرار نامہ پڑھیں اور منظور کریں۔",
    // UNREVIEWED
    consentBody: "کرونک کیئر اے آئی یونیورسٹی کا ایک تحقیقی پروٹوٹائپ ہے۔ یہ آپ کی روزانہ کی علامات اور ریڈنگز کو ریکارڈ کرتا ہے، آپ کی فراہم کردہ معلومات کا آپ کے ہیلتھ ریکارڈ سے موازنہ کرتا ہے، اور فرق کی نشاندہی کرتا ہے تاکہ کوئی معالج جائزہ لے سکے۔ یہ کوئی تشخیص نہیں کرتا، علاج کا مشورہ نہیں دیتا، یا آپ کے ڈاکٹر کا متبادل نہیں ہے، اور یہ ہنگامی حالات کے لیے نہیں ہے: اگر آپ کی طبیعت شدید خراب ہو تو اپنی مقامی ایمرجنسی سروسز سے رابطہ کریں۔ آپ کے درج کردہ جوابات اور نتائج اس پروٹوٹائپ کے ڈیٹا بیس میں محفوظ کیے جاتے ہیں۔ اس پروٹوٹائپ میں، سسٹم کے ساتھ رجسٹرڈ کوئی بھی معالج اکاؤنٹ ان چیک انز کو دیکھ سکتا ہے جن کے جائزے کی ضرورت ہے۔ براہ کرم صرف ٹیسٹ معلومات درج کریں الا یہ کہ آپ کسی منظور شدہ تشخیص کا حصہ ہوں۔ آپ اپنی ترتیبات سے کسی بھی وقت اجازت واپس لے سکتے ہیں؛ اجازت واپس لینے سے نئے چیک ان رک جائیں گے لیکن پہلے سے بھیجے گئے جائزے حذف نہیں ہوں گے۔",
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
    dontKnowBtn: "معلوم نہیں",
    skipQuestionBtn: "چھوڑ دیں",
    someoneElseAnsweringBtn: "کوئی اور جواب دے رہا ہے",
    whyAmIAskedThisBtn: "یہ کیوں پوچھا جا رہا ہے؟",
    questionProgressText: "پیش رفت",
    sendBtnLabel: "بھیجیں",
    micSpeakLabel: "بول کر جواب دیں",
    micDisabledLabel: "سیٹنگز میں آواز کا فیچر آن کریں",
    interviewRetryBtn: "دوبارہ کوشش کریں",
    interviewEmergencyCall: "ہنگامی صورتحال میں اپنے مقامی ایمرجنسی نمبر پر رابطہ کریں۔",
    interviewNetworkError: "ہم آپ کا جواب نہیں بھیج سکے۔ اگر یہ ہنگامی صورتحال ہے تو فوراً اپنے مقامی ایمرجنسی نمبر پر کال کریں۔",
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
    // UNREVIEWED Urdu strings
    researchPrototypeNotice: "تحقیقی پروٹوٹائپ۔ براہ کرم صرف ٹیسٹ معلومات درج کریں۔",
    consentBulletRoleAccess: "کردار کی بنیاد پر رسائی: مریض، معالجین اور منتظمین مختلف اسکرینز اور ڈیٹا دیکھتے ہیں۔",
    consentBulletWithdrawConsent: "آپ اپنی ترتیبات میں کسی بھی وقت رضامندی واپس لے سکتے ہیں۔",
    consentBulletNotForEmergencies: "یہ پروٹوٹائپ ہنگامی حالات کے لیے نہیں ہے۔",
    routedToReviewHeadline: "طبی معالج کے جائزے کے لیے بھیج دیا گیا",
    routedToReviewExplanation: "طبی معالج اسے اپنی جائزہ قطار میں دیکھیں گے۔ ایپ کا یہ ورژن اطلاعات نہیں بھیجتا ہے۔",
    confidenceLowChip: "اعتماد: کم (کوئی ریڈنگ موجود نہیں تھی)",
    medicationsNoneRecorded: "ادویات: ابھی تک کوئی درج نہیں ہیں",
    noCheckinsYet: "ابھی تک کوئی چیک ان نہیں ہوا",
    notConnectedYet: "ابھی منسلک نہیں ہے",
    isolatedModeLabel: "آئسولیٹڈ موڈ (مقامی اسٹور)",
    needsClinicianReviewTitle: "طبی معالج کے جائزے کی ضرورت ہے",
    readingDiffersTitle: "آپ کی ریڈنگ ریکارڈ سے مختلف ہے",
    firstCheckinNoRecordTitle: "یہ آپ کا پہلا چیک ان ہے",
    firstCheckinNoRecordDesc: "ابھی موازنہ کرنے کے لیے کوئی پچھلا ریکارڈ موجود نہیں ہے، اس لیے طبی معالج اس کا جائزہ لیں گے۔",
    earlierCheckinLabel: "آپ کا پچھلا چیک ان",
    savedReadingLabel: "آپ کی محفوظ کردہ ریڈنگ",
    clinicianReviewAnswers: "طبی معالج آج کے جوابات کا جائزہ لیں گے۔",
    connectionBadgeIsolated: "ہسپتال کے ریکارڈ سے منسلک نہیں ہے۔ آپ کے درج کردہ ریکارڈ کا استعمال ہو رہا ہے",
    connectionBadgeIsolatedShort: "مقامی ریکارڈ (منسلک نہیں)",
    connectionBadgeConnected: "{system} سے منسلک (ٹیسٹ ماحول)",
    connectionBadgeConnectedGeneric: "ہسپتال کے ریکارڈ سے منسلک (ٹیسٹ ماحول)",
    demoSimulationBadge: "ڈیمو",
    notOnFile: "ریکارڈ میں موجود نہیں",
    notReportedToday: "آج درج نہیں کیا گیا",
    demoVoiceSampleBadge: "ڈیمو وائس نمونہ",
    recordingVoice: "ریکارڈنگ جاری ہے... واضح بولیں",
    transcribingVoice: "آواز کو تحریر میں تبدیل کیا جا رہا ہے...",
    stopRecording: "ریکارڈنگ روکیں",
    cancelRecording: "منسوخ کریں",
    hospitalRecordMedsManagedLine: "آپ کے اسپتال کے ریکارڈ سے منظم ہے۔ آپ کا معالج مکمل فہرست دیکھ سکتا ہے۔",
    simulatedExampleBadge: "فرضی مثال",
    directHotlineDispatch: "براہ راست ہاٹ لائن رابطہ:",
    researchPrototypeDisclaimer: "تحقیقی پروٹوٹائپ، یہ کوئی طبی آلہ نہیں ہے۔",
    notFoundTitle: "صفحہ نہیں ملا",
    notFoundDesc: "درخواست کردہ صفحہ موجود نہیں ہے یا تبدیل ہو چکا ہے۔",
    returnHomeBtn: "مرکزی صفحہ پر واپس جائیں",

    // Physical Measurements Units & Labels
    heightToggleLabel: "قد کی اکائی",
    weightToggleLabel: "وزن کی اکائی",
    heightUnitCm: "سینٹی میٹر",
    heightUnitFtIn: "فٹ + انچ",
    weightUnitLb: "پاؤنڈ",
    weightUnitKg: "کلوگرام",
    heightLabelCm: "قد (سینٹی میٹر)",
    heightLabelFtIn: "قد (فٹ اور انچ)",
    feetLabel: "فٹ",
    inchesLabel: "انچ",
    weightLabelLb: "وزن (پاؤنڈ)",
    weightLabelKg: "وزن (کلوگرام)",
    heightErrorCm: "قد ۵۰ سے ۲۵۰ سینٹی میٹر کے درمیان ہونا چاہیے۔",
    heightErrorFtIn: "قد ۱ فٹ ۸ انچ سے ۸ فٹ ۲ انچ کے درمیان ہونا چاہیے۔",
    heightFeetError: "فٹ ۱ سے ۸ کے درمیان مکمل عدد ہونا چاہیے۔",
    heightInchesError: "انچ ۰ سے ۱۱.۹۹ کے درمیان ہونے چاہئیں۔",
    weightErrorKg: "وزن ۲۰ سے ۴۰۰ کلوگرام کے درمیان ہونا چاہیے۔",
    weightErrorLb: "وزن ۴۴ سے ۸۸۲ پاؤنڈ کے درمیان ہونا چاہیے۔",
    bodyMeasurementsOptional: "جسمانی پیمائش (اختیاری)",
    waistLabelIn: "کمر کی پیمائش (انچ)",
    waistLabelCm: "کمر کی پیمائش (سینٹی میٹر)",
    waistToggleLabel: "کمر کی پیمائش کی اکائی",
    waistUnitIn: "انچ",
    waistUnitCm: "سینٹی میٹر",
    waistUnitInAria: "کمر کی اکائی: انچ",
    waistUnitCmAria: "کمر کی اکائی: سینٹی میٹر",
    waistHelperText: "سانس باہر نکالنے کے بعد کولہے کی ہڈی کے اوپری حصے پر کمر کی پیمائش کریں۔",
    waistErrorCm: "کمر کی پیمائش ۴۰ سے ۲۰۰ سینٹی میٹر کے درمیان ہونی چاہیے (ڈاکٹر کے جائزے کی ضرورت ہے)۔",
    waistErrorIn: "کمر کی پیمائش ۱۵.۷ سے ۷۸.۷ انچ کے درمیان ہونی چاہیے (ڈاکٹر کے جائزے کی ضرورت ہے)۔",
    doctorOnRecordLabel: "ریکارڈ پر ڈاکٹر: {name} (آپ کے ہسپتال کے ریکارڈ سے)",
    ehrAllergiesTitle: "آپ کے ہسپتال کے ریکارڈ میں الرجیاں",
    noEhrAllergiesRecorded: "کوئی درج نہیں",
    providerRiskTitle: "ذیابیطس کا خطرہ (تجرباتی)",
    providerRiskNotice: "اندرونی تحقیقی فیچر — معالج کے جائزے کے بغیر تشخیصی فیصلے کے لیے نہیں۔",
    riskBandLow: "کم",
    riskBandMedium: "درمیانہ",
    riskBandHigh: "زیادہ",
    riskReasonsTitle: "بنیادی وجوہات",
    riskCaveatsTitle: "طبی تنبیہات",
    riskCaveatHomeBp: "گھر پر لیے گئے بلڈ پریشر کے نتائج مریض کے خود درج کردہ ہیں اور کلینک کے امتحانی بلڈ پریشر سے تصدیق شدہ نہیں ہیں۔",
    riskCaveatNotValidatedPakistan: "یہ ماڈل امریکی این ایچ اے این ای ایس (NHANES) ڈیٹا پر بنایا گیا ہے اور اس کی پاکستانی آبادی پر توثیق نہیں کی گئی ہے۔",
    riskMissingDataTitle: "معلومات ناکافی ہیں",
    riskMissingDataDescription: "خطرے کے جائزے کے لیے درج ذیل مکمل پیمائشیں درکار ہیں:",
    riskMissingBp: "پچھلے ۳۰ دنوں کے اندر بلڈ پریشر کی ریڈنگ",
    riskMissingWaist: "مریض کے پروفائل میں کمر کی پیمائش",
    riskMissingSmoking: "مریض کے پروفائل میں تمباکو نوشی کی تفصیل",
    riskMissingHeightWeight: "مریض کے پروفائل میں قد اور وزن",

    // Record History, Export & Import (Day 6)
    recordHistoryTitle: "ریکارڈ کی تاریخ",
    recordHistoryBtn: "تاریخ",
    viewFullHistory: "پورے ریکارڈ کی تاریخ دیکھیں",
    noHistoryRecorded: "ابھی تک کوئی تبدیلی درج نہیں کی گئی۔",
    historyField: "شعبہ",
    historyOldValue: "پہلے",
    historyNewValue: "بعد میں",
    historyChangedAt: "تاریخ اور وقت",
    originSelfReported: "آپ خود",
    originOcr: "او سی آر اسکین",
    originClinician: "طبی ماہر",
    originImport: "درآمد شدہ",
    originEhr: "ہسپتال ریکارڈ",
    exportRecordBtn: "اپنا ریکارڈ ڈاؤن لوڈ کریں",
    exportJson: "جے سن (JSON) ڈاؤن لوڈ کریں",
    exportFhir: "فائر (FHIR) ڈاؤن لوڈ کریں",
    exporting: "ڈاؤن لوڈ ہو رہا ہے...",
    importRecordBtn: "ریکارڈ فائل درآمد کریں",
    importTitle: "صحت کا ریکارڈ درآمد کریں",
    importSubtitle: "پہلے سے برآمد شدہ کرونک کیئر JSON یا معیاری FHIR بنڈل فائل اپ لوڈ کریں۔",
    importPreviewTitle: "درآمد کا پیش نظارہ",
    importToAdd: "شامل ہونے والی چیزیں",
    importDuplicates: "پہلے سے موجود (چھوڑ دی جائیں گی)",
    importInvalid: "ناقابل قبول (درآمد نہیں ہو سکتیں)",
    confirmImport: "درآمد کی تصدیق کریں",
    cancelImport: "منسوخ کریں",
    importSuccess: "ریکارڈ کامیابی سے درآمد ہو گیا",
    importFailed: "درآمد ناکام ہو گئی",
    importBaselineNote: "۱۴ دن سے پرانی ریڈنگز آپ کی تاریخ میں شامل ہوں گی، لیکن روزانہ کے چیک ان موازنے میں استعمال نہیں ہوں گی۔",
    recentRecordChangesTitle: "ریکارڈ میں حالیہ تبدیلیاں",
    recentRecordChangesSubtitle: "مریض کے کلینیکل ریکارڈ میں کی گئی تازہ ترین تبدیلیاں",
    importBadgeAdd: "شامل کریں",
    importBadgeSkip: "چھوڑیں",

    // OCR v1 (Day 7)
    uploadDocumentBtn: "لیب رپورٹ یا نسخہ اپ لوڈ کریں",
    ocrConfirmTitle: "نکالی گئی اقدار کی تصدیق کریں",
    ocrConfirmSubtitle: "نیچے دی گئی ہر قدر کا جائزہ لیں۔ صرف تصدیق شدہ اندراجات ہی آپ کے ہیلتھ ریکارڈ میں شامل کیے جائیں گے۔",
    ocrNoticeUrdu: "ہم فی الحال صرف انگریزی رپورٹس پڑھ سکتے ہیں۔ براہ کرم یہ اقدار خود شامل کریں۔",
    ocrConfirmSaveBtn: "تصدیق کریں اور محفوظ کریں",
    ocrFixBtn: "تبدیل کریں",
    ocrRemoveBtn: "حذف کریں",
    ocrConfirmedBadge: "تصدیق شدہ",
    ocrEvidenceLabel: "دستاویز میں پایا گیا:",
    ocrBadge: "او سی آر",
    ocrObservationsTitle: "مشاہدات اور لیب ٹیسٹ",
    ocrMedicationsTitle: "ادویات",
    ocrAllergiesTitle: "الرجیز",
    ocrEmptyExtracted: "اس تصویر میں کوئی پڑھنے کے قابل طبی اقدار نہیں ملیں۔",
    ocrUploading: "دستاویز کا تجزیہ جاری ہے...",
    ocrUploadFailed: "دستاویز پر کارروائی نہیں ہو سکی۔ براہ کرم یقینی بنائیں کہ تصویر 5MB سے کم اور JPEG یا PNG فارمیٹ میں ہو۔",
    ocrSaveSuccess: "تصدیق شدہ اقدار آپ کے ہیلتھ ریکارڈ میں محفوظ کر دی گئی ہیں۔",
    ocrConfirmItem: "تصدیق کریں",
    ocrCancelBtn: "منسوخ کریں",
    failedToLoadHistory: "ریکارڈ کی تاریخ لوڈ کرنے میں ناکامی",
    failedToExportRecord: "ریکارڈ ایکسپورٹ کرنے میں ناکامی",
    failedToPreviewImport: "فائل کا پیش نظارہ حاصل کرنے میں ناکامی",
    failedToCommitImport: "ریکارڈ امپورٹ کرنے میں ناکامی",
    reasonDuplicate: "پہلے سے موجود اندراج",
    reasonOutOfRange: "طبی حد سے باہر قیمت",
    reasonInvalidType: "غیر معاون معائنہ کی قسم",
    reasonInvalidUnit: "غلط اکائی",
    reasonInvalidDate: "تاریخ یا وقت درست نہیں ہے",
    reasonInvalidMedName: "دوا کا نام درست نہیں ہے",
    reasonInvalidMedDosage: "خوراک درست نہیں ہے",
    reasonInvalidMedStatus: "دوا کی حالت درست نہیں ہے",
    reasonInvalidAllergy: "الرجی کا مادہ درست نہیں ہے",
    reasonAllergyTooLong: "ردعمل کی تفصیل بہت طویل ہے",
    ocrInvalidItemBanner: "براہ کرم محفوظ کرنے سے پہلے نمایاں کیے گئے غلط اندراج کو درست کریں یا ہٹا دیں۔",
    ocrFixOrRemoveHint: "یہ اندراج درست نہیں ہے۔ درست کرنے کے لیے 'درست کریں' یا خارج کرنے کے لیے 'ہٹائیں' کا بٹن دبائیں۔",

    // Patient Explanation (I3 Day 2)
    whyThisResultBtn: "یہ نتیجہ کیوں؟",
    hideWhyThisResultBtn: "وضاحت چھپائیں",
    explanationSourcesTitle: "طبی ذرائع",
  }
};