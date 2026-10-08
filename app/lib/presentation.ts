/**
 * Pure presentation logic for clinical labels, side descriptions, and user-safe error mappings.
 * Free of React dependencies to ensure pure unit testability.
 */

export interface DeltaInfo {
  delta?: number | string | null;
  unit?: string | null;
}

export interface MedicationComparison {
  medication_name?: string | null;
  status_a?: string | null;
  status_b?: string | null;
  dosage_a?: string | null;
  dosage_b?: string | null;
  source_a?: string | null;
  source_b?: string | null;
  comparison_status?: string | null;
}

export interface MedicationVerification {
  medication_name?: string | null;
  reconciliation_status?: string | null;
  trust_level_a?: string | null;
  trust_level_b?: string | null;
  severity?: string | null;
  requires_human_review?: boolean | null;
  review_reason?: string | null;
}

export interface MedicationItemDescription {
  title: string;
  recordText: string;
  todayText: string;
  reason: string;
  severity: string;
  isConfirmed: boolean;
}

/**
 * Calculates exact chronological age from DOB in YYYY-MM-DD format.
 */
export function calculateAgeFromDob(dobString?: string | null, asOfDateStr?: string): number | null {
  if (!dobString || !/^\d{4}-\d{2}-\d{2}$/.test(dobString.trim())) return null;
  const parts = dobString.trim().split("-").map(Number);
  const birthDate = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  if (isNaN(birthDate.getTime())) return null;

  let today: Date;
  if (asOfDateStr && /^\d{4}-\d{2}-\d{2}$/.test(asOfDateStr.trim())) {
    const refParts = asOfDateStr.trim().split("-").map(Number);
    today = new Date(Date.UTC(refParts[0], refParts[1] - 1, refParts[2]));
  } else {
    today = new Date();
  }

  let age = today.getUTCFullYear() - birthDate.getUTCFullYear();
  const m = today.getUTCMonth() - birthDate.getUTCMonth();
  if (m < 0 || (m === 0 && today.getUTCDate() < birthDate.getUTCDate())) {
    age--;
  }
  if (age < 0 || age > 120) return null;
  return age;
}

/**
 * Describes a medication comparison & verification item in honest, plain language.
 * Follows clinical rules: matching medicines are confirmed calmly, not flagged.
 */
export function describeMedicationItem(
  comparison?: MedicationComparison | null,
  verification?: MedicationVerification | null,
  isUrdu?: boolean
): MedicationItemDescription {
  const medName =
    comparison?.medication_name || verification?.medication_name || (isUrdu ? "دوا" : "Medication");
  const title = medName;

  const statusA = (comparison?.status_a || "active").toLowerCase();
  const dosageA = comparison?.dosage_a ? comparison.dosage_a.trim() : null;

  const statusB = comparison?.status_b ? comparison.status_b.toLowerCase() : null;
  const dosageB = comparison?.dosage_b ? comparison.dosage_b.trim() : null;

  const compStatus = (
    comparison?.comparison_status ||
    verification?.reconciliation_status ||
    ""
  ).toLowerCase();

  const isConfirmed = compStatus === "agree" || compStatus === "agreement";

  // 1. Record Text (Side A)
  let recordDetails = "";
  if (dosageA) {
    recordDetails = `${dosageA} (${statusA})`;
  } else {
    recordDetails = `(${statusA})`;
  }
  const recordText = isUrdu
    ? `ریکارڈ: ${medName}، ${recordDetails}`
    : `Record: ${medName}, ${recordDetails}`;

  // 2. Today's Text (Side B)
  let todayText = isUrdu ? "آج نہیں بتایا گیا" : "Not reported today";
  if (compStatus === "missing_in_b" || (!statusB && !dosageB)) {
    todayText = isUrdu ? "آج نہیں بتایا گیا" : "Not reported today";
  } else if (statusB === "stopped") {
    todayText = isUrdu ? "آج: بند کر دی ہے" : "Today: stopped";
  } else if (statusB === "active") {
    if (dosageB && dosageA && dosageB.toLowerCase() !== dosageA.toLowerCase()) {
      todayText = isUrdu
        ? `آج: جاری، نئی مقدار: ${dosageB}`
        : `Today: active, new dose: ${dosageB}`;
    } else if (dosageB) {
      todayText = isUrdu ? `آج: جاری، ${dosageB}` : `Today: active, ${dosageB}`;
    } else if (dosageA) {
      todayText = isUrdu ? `آج: جاری، ${dosageA}` : `Today: active, ${dosageA}`;
    } else {
      todayText = isUrdu ? "آج: جاری" : "Today: active";
    }
  } else if (dosageB) {
    todayText = isUrdu ? `آج: ${dosageB}` : `Today: ${dosageB}`;
  }

  // 3. Reason
  let reason = isUrdu ? "طبی معالج کے جائزے کی ضرورت ہے۔" : "Requires clinician review.";
  if (isConfirmed) {
    reason = isUrdu ? "ریکارڈ کے مطابق ہے۔" : "Matches the record.";
  } else if (compStatus === "conflict") {
    if (statusA === "active" && statusB === "stopped") {
      reason = isUrdu
        ? "ریکارڈ کے مطابق آپ یہ دوا لیتے ہیں؛ آپ نے بتایا کہ آپ نے بند کر دی ہے۔"
        : "The record says you take this medication; you said you stopped it.";
    } else if (dosageA && dosageB && dosageA.toLowerCase() !== dosageB.toLowerCase()) {
      reason = isUrdu
        ? "آپ نے ریکارڈ سے مختلف مقدار بتائی ہے۔"
        : "You reported a different dose from the record.";
    } else {
      reason = isUrdu
        ? "ریکارڈ کے مطابق آپ یہ دوا لیتے ہیں؛ آپ نے بتایا کہ آپ نے بند کر دی ہے۔"
        : "The record says you take this medication; you said you stopped it.";
    }
  } else if (compStatus === "missing_in_b") {
    reason = isUrdu ? "آج نہیں بتایا گیا۔" : "Not reported today.";
  } else if (verification?.review_reason && verification.review_reason.trim()) {
    reason = verification.review_reason.trim();
  }

  // 4. Severity
  const severity = (
    verification?.severity ||
    (compStatus === "conflict" ? "high" : "low")
  ).toLowerCase();

  return {
    title,
    recordText,
    todayText,
    reason,
    severity,
    isConfirmed,
  };
}

/**
 * Returns a truthful, clinical source description for side A (prior baseline) or side B (today's check-in).
 * Rule: The words 'clinic', 'hospital' and 'FHIR' may appear only when the origin really is an EHR.
 */
export function describeSide(
  side: "a" | "b" | string,
  source?: string | null,
  trustLevel?: "high" | "medium" | "low" | string | null,
  mode?: string | null,
  recordSourceLabel?: string | null,
  timestamp?: string | null,
  isUrdu?: boolean
): string {
  const normSide = (side || "").toLowerCase();
  const normSource = (source || "").toLowerCase();
  const normTrust = (trustLevel || "").toLowerCase();
  const normMode = (mode || "").toLowerCase();

  if (normSide === "b") {
    return isUrdu ? "آج کا آپ کا جواب" : "Today's check-in (reported by you)";
  }

  // Side A: prioritize server-provided recordSourceLabel if available
  if (recordSourceLabel && recordSourceLabel.trim()) {
    return recordSourceLabel.trim();
  }

  const dateFormatted = timestamp ? timestamp.slice(0, 10) : "";
  const dateSuffix = dateFormatted ? `, ${dateFormatted}` : "";

  if (normSource === "fhir" || normMode === "connected" || normMode === "fhir") {
    if (normMode === "simulated" || normSource === "simulated") {
      return isUrdu
        ? `ہسپتال کا مصنوعی ریکارڈ (مصنوعی ڈیٹا)${dateSuffix}`
        : `Simulated hospital record (synthetic data)${dateSuffix}`;
    }
    if (dateFormatted) {
      return isUrdu
        ? `ہسپتال کا ریکارڈ, ${dateFormatted}`
        : `Hospital record, ${dateFormatted}`;
    }
    return isUrdu ? "ہسپتال کا ریکارڈ" : "Hospital EHR (FHIR)";
  }

  if (normSource === "simulated" || normMode === "simulated") {
    return isUrdu
      ? `ہسپتال کا مصنوعی ریکارڈ (مصنوعی ڈیٹا)${dateSuffix}`
      : `Simulated hospital record (synthetic data)${dateSuffix}`;
  }

  if (normSource === "checkin" || normSource === "prior_checkin") {
    return isUrdu
      ? `آپ کا پچھلا چیک ان, ${dateFormatted}`
      : `Your check-in on ${dateFormatted || "previous check-in"}`;
  }

  if (dateFormatted) {
    return isUrdu
      ? `آپ کی بنیادی ریڈنگ جو آپ نے ${dateFormatted} کو درج کی`
      : `Your baseline reading you entered on ${dateFormatted}`;
  }

  if (normSource === "local") {
    if (normTrust === "low") {
      return isUrdu ? "آپ کا پہلے خود درج کردہ ریکارڈ" : "Your earlier self-reported record";
    }
    if (normTrust === "high") {
      return isUrdu ? "طبی معالج کا درج کردہ ریکارڈ" : "Clinician-entered record";
    }
    return isUrdu ? "محفوظ شدہ ریکارڈ (غیر تصدیق شدہ)" : "Saved record (unverified)";
  }

  if (normTrust === "low") {
    return isUrdu ? "آپ کا پہلے خود درج کردہ ریکارڈ" : "Your earlier self-reported record";
  }

  if (normTrust === "high") {
    return isUrdu ? "طبی معالج کا درج کردہ ریکارڈ" : "Clinician-entered record";
  }

  return isUrdu ? "محفوظ شدہ ریکارڈ (غیر تصدیق شدہ)" : "Saved record (unverified)";
}

/**
 * Returns UI description and badges for an EHR system based on its kind.
 */
export function describeEhrSystem(system?: { kind?: string; display_name?: string; description?: string } | null): {
  badge: string;
  badgeColor: string;
  description: string;
  isSimulated: boolean;
} {
  const kind = (system?.kind || "public_sandbox").toLowerCase();
  if (kind === "simulated") {
    return {
      badge: "In-Process Simulator",
      badgeColor: "bg-purple-100 text-purple-800 border-purple-200",
      description: system?.description || "Simulated hospital with deterministic clinical test profiles (synthetic data).",
      isSimulated: true,
    };
  }
  if (kind === "public_sandbox") {
    return {
      badge: "Public FHIR Sandbox",
      badgeColor: "bg-blue-100 text-blue-800 border-blue-200",
      description: system?.description || "Public FHIR R4 sandbox server (synthetic test data only).",
      isSimulated: false,
    };
  }
  return {
    badge: "Connected EHR",
    badgeColor: "bg-teal-100 text-teal-800 border-teal-200",
    description: system?.description || "Clinical HL7 FHIR EHR system.",
    isSimulated: false,
  };
}

/**
 * Maps standard EHR error codes to truthful, user-facing explanations.
 */
export function mapEhrError(code?: string | null): string {
  const norm = (code || "").toLowerCase().trim();
  switch (norm) {
    case "ehr_unreachable":
      return "The EHR server is unreachable or timed out. Please check your connection or test the server.";
    case "ehr_patient_not_found":
      return "Patient record was not found in this EHR system. Please verify the Patient ID.";
    case "ehr_forbidden":
      return "Access was forbidden by the EHR server.";
    case "ehr_bad_response":
      return "The EHR server returned an invalid or unreadable response.";
    case "ehr_patient_not_adult":
      return "This record belongs to a patient under 18. ChronicCare AI is designed for adults (18 and over).";
    case "ehr_empty_record":
      return "Connected, but this record has no recent observations or active medications.";
    case "ehr_birthdate_missing":
      return "Connected, but birth date is missing in the EHR record.";
    default:
      return "An error occurred while communicating with the EHR server.";
  }
}

/**
 * Describes the clinical review rationale in honest, understandable language.
 */
export function describeReviewReason(
  status?: string | null,
  reviewReason?: string | null,
  deltaInfo?: DeltaInfo | null
): string {
  const normStatus = (status || "").toLowerCase();

  if (normStatus === "agree" || normStatus === "agreement" || normStatus === "review_required") {
    return "Matches an earlier self-reported value only; no trusted source confirms it.";
  }

  if (normStatus === "conflict" || normStatus === "flagged") {
    if (deltaInfo && deltaInfo.delta !== undefined && deltaInfo.delta !== null && deltaInfo.delta !== "") {
      const unitStr = deltaInfo.unit ? ` ${deltaInfo.unit}` : "";
      return `Differs from the earlier value by ${deltaInfo.delta}${unitStr}.`;
    }
    return "Differs from the earlier value.";
  }

  if (normStatus === "missing_in_a" || normStatus === "source_b_only") {
    return "No earlier record to compare with.";
  }

  if (normStatus === "missing_in_b" || normStatus === "source_a_only") {
    return "Not reported today.";
  }

  if (normStatus === "insufficient_data") {
    return "Could not be compared (missing or incompatible value).";
  }

  if (reviewReason && reviewReason.trim()) {
    return reviewReason.trim();
  }

  return "Requires clinician review.";
}

/**
 * Converts any name or email prefix to title-cased words (e.g. "ali khan" -> "Ali Khan").
 */
export function titleCaseName(name?: string | null): string {
  if (!name) return "";
  const trimmed = name.trim();
  if (!trimmed) return "";

  // If email address, take prefix before @
  const raw = trimmed.includes("@") ? trimmed.split("@")[0].replace(/[._-]/g, " ") : trimmed;

  return raw
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/**
 * Maps raw API status codes and detail strings to user-safe English message keys.
 */
export function mapApiError(status?: number | null, detail?: string | null): string {
  const normDetail = (detail || "").toLowerCase();

  if (status === 401) {
    return "Your session has expired. Please sign in again.";
  }

  if (status === 400) {
    if (normDetail.includes("maximum_medications_exceeded")) {
      return "You have reached the maximum limit of 30 medications.";
    }
    if (normDetail.includes("maximum_allergies_exceeded")) {
      return "You have reached the maximum limit of 30 allergies.";
    }
    if (normDetail.includes("maximum_observations_exceeded")) {
      return "You have reached the maximum limit of 20 baseline readings.";
    }
    if (normDetail.includes("plausible range")) {
      return detail && detail.trim() ? detail.trim() : "The reading value is outside the plausible clinical range.";
    }
  }

  if (status === 403) {
    if (normDetail.includes("provider_notification_consent_required")) {
      return "Provider notification consent is required before starting a check-in.";
    }
    if (normDetail.includes("consent_required") || normDetail.includes("active consent")) {
      return "Active consent is required before proceeding.";
    }
    return "Access denied. You do not have permission for this action.";
  }

  if (status === 409) {
    if (normDetail.includes("record_managed_by_ehr")) {
      return "Your record is managed by your hospital EHR.";
    }
    if (normDetail.includes("duplicate_medication")) {
      return "A medication with this name already exists in your record.";
    }
    if (normDetail.includes("stale_step")) {
      return "The check-in question was updated. Please answer the current question.";
    }
    if (normDetail.includes("concurrent_update")) {
      return "A conflict occurred while saving your answer. Please try again.";
    }
    return "A conflict occurred with existing data or state.";
  }

  if (status === 422) {
    if (normDetail.includes("ehr_patient_not_adult") || normDetail.includes("under 18")) {
      return "This record belongs to a patient under 18. ChronicCare AI is for adults (18 and over) in this release.";
    }
    return "Invalid information provided. Please verify your input.";
  }

  if (status === 502) {
    if (normDetail.includes("ehr_patient_not_found")) {
      return "Patient record was not found in this EHR system.";
    }
    if (normDetail.includes("ehr_unreachable")) {
      return "The EHR server is unreachable or timed out. Please try again in a moment.";
    }
    return "The clinical service is temporarily unavailable. Please try again in a moment.";
  }

  if (status === 503 || status === 504) {
    if (normDetail.includes("authentication not configured") || normDetail.includes("firebase") || normDetail.includes("auth")) {
      return "Authentication not configured on the backend. Please contact the administrator to verify Firebase setup.";
    }
    return "The clinical service is currently waking up or busy. Please try again in a moment.";
  }

  if (!status || status === 0 || normDetail.includes("network") || normDetail.includes("failed to fetch")) {
    return "Network request failed. Please check your connection and try again.";
  }

  return detail && detail.trim() ? detail.trim() : "An unexpected error occurred. Please try again.";
}

export type BlockedActionTarget =
  | "consent"
  | "inclusion"
  | "profile"
  | "connection"
  | "retry"
  | "none";

export interface BlockedActionDescription {
  message: string;
  actionText: string | null;
  target: BlockedActionTarget;
}

/**
 * Maps blocked action responses (403, 409, 500, network errors) to clear, friendly explanations
 * and actionable UI navigation targets in English and Urdu.
 */
export function describeBlockedAction(
  status?: number | null,
  detail?: string | null,
  missing?: string[] | null,
  isUrdu: boolean = false
): BlockedActionDescription {
  const normDetail = (detail || "").toLowerCase();

  // 1. Consent blocked actions
  if (
    normDetail.includes("consent_required") ||
    normDetail.includes("active consent is required") ||
    normDetail.includes("provider_notification_consent_required") ||
    normDetail.includes("provider notification consent")
  ) {
    if (normDetail.includes("provider_notification") || normDetail.includes("provider notification")) {
      return {
        message: isUrdu
          ? "چیک ان شروع کرنے کے لیے معالج کی اطلاع کا اجازت نامہ درکار ہے۔"
          : "Provider notification consent is required before starting a check-in.",
        actionText: isUrdu ? "اجازت نامہ کی ترتیبات کھولیں" : "Open Consent Settings",
        target: "consent",
      };
    }
    return {
      message: isUrdu
        ? "چیک ان شروع کرنے کے لیے اجازت نامہ فعال ہونا ضروری ہے۔"
        : "Active consent is required before starting a check-in.",
      actionText: isUrdu ? "اجازت نامہ کی ترتیبات کھولیں" : "Open Consent Settings",
      target: "consent",
    };
  }

  // 2. Profile incomplete blocked actions (403 or explicit code)
  if (normDetail.includes("profile_incomplete") || (status === 403 && missing && missing.length > 0)) {
    const missingList = missing || [];
    if (
      missingList.includes("date_of_birth") ||
      missingList.includes("inclusion_confirmed") ||
      missingList.length === 0
    ) {
      return {
        message: isUrdu
          ? "چیک ان شروع کرنے سے پہلے تاریخ پیدائش اور بالغ ہونے کی تصدیق درکار ہے۔"
          : "Clinical inclusion and eligibility details are required before starting a check-in.",
        actionText: isUrdu ? "شمولیت کی تفصیلات درج کریں" : "Complete Eligibility Details",
        target: "inclusion",
      };
    }
    if (missingList.includes("conditions")) {
      return {
        message: isUrdu
          ? "چیک ان شروع کرنے سے پہلے اپنے طبی حالات کا اندراج مکمل کریں۔"
          : "Please complete your conditions profile before starting a check-in.",
        actionText: isUrdu ? "طبی پروفائل مکمل کریں" : "Complete Health Profile",
        target: "profile",
      };
    }
    return {
      message: isUrdu
        ? "چیک ان شروع کرنے سے پہلے اپنے پروفائل کی تفصیلات مکمل کریں۔"
        : "Please complete your clinical profile before starting a check-in.",
      actionText: isUrdu ? "پروفائل مکمل کریں" : "Complete Profile",
      target: "inclusion",
    };
  }

  // 3. Incomplete profile via 409 conflict
  if (status === 409 && (normDetail.includes("complete your profile") || normDetail.includes("profile first"))) {
    return {
      message: isUrdu
        ? "چیک ان شروع کرنے سے پہلے اپنے طبی حالات کا اندراج کریں۔"
        : "Please complete your conditions profile before starting a check-in.",
      actionText: isUrdu ? "طبی پروفائل کھولیں" : "Open Health Profile",
      target: "profile",
    };
  }

  // 4. Role mismatch / wrong portal (403)
  if (
    status === 403 &&
    (normDetail.includes("role") ||
      normDetail.includes("forbidden") ||
      normDetail.includes("patient only") ||
      normDetail.includes("provider only") ||
      normDetail.includes("admin only") ||
      normDetail.includes("rejected") ||
      normDetail.includes("cannot access"))
  ) {
    return {
      message: isUrdu
        ? "یہ اکاؤنٹ اس پورٹل کو استعمال کرنے کی اجازت نہیں رکھتا۔"
        : "This account cannot use this portal. Please sign in with the appropriate account.",
      actionText: null,
      target: "none",
    };
  }

  // 5. Generic 403 Forbidden
  if (status === 403) {
    return {
      message: isUrdu
        ? "اس کارروائی کی فی الوقت اجازت نہیں ہے۔"
        : "You do not have permission to perform this action.",
      actionText: null,
      target: "none",
    };
  }

  // 6. Server errors (500, 502, 503, 504) or Network Failures (0)
  if (
    !status ||
    status === 0 ||
    status >= 500 ||
    normDetail.includes("network") ||
    normDetail.includes("failed to fetch")
  ) {
    return {
      message: isUrdu
        ? "سرور اس وقت درخواست مکمل نہیں کر سکا۔ براہ کرم دوبارہ کوشش کریں۔"
        : "The server could not complete your request. Please try again.",
      actionText: isUrdu ? "دوبارہ کوشش کریں" : "Retry",
      target: "retry",
    };
  }

  // 7. General neutral fallback
  return {
    message: isUrdu
      ? "کارروائی مکمل نہیں ہو سکی۔ براہ کرم دوبارہ کوشش کریں۔"
      : "The action could not be completed. Please try again.",
    actionText: isUrdu ? "دوبارہ کوشش کریں" : "Retry",
    target: "retry",
  };
}
