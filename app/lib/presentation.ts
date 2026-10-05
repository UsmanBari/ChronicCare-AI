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
}

/**
 * Describes a medication comparison & verification item in honest, plain language.
 * Follows clinical rules: never uses the word "hospital" unless source is "fhir".
 */
export function describeMedicationItem(
  comparison?: MedicationComparison | null,
  verification?: MedicationVerification | null
): MedicationItemDescription {
  const medName =
    comparison?.medication_name || verification?.medication_name || "Medication";
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

  // 1. Record Text (Side A)
  let recordDetails = "";
  if (dosageA) {
    recordDetails = `${dosageA} (${statusA})`;
  } else {
    recordDetails = `(${statusA})`;
  }
  const recordText = `Record: ${medName}, ${recordDetails}`;

  // 2. Today's Text (Side B)
  let todayText = "Not reported today";
  if (compStatus === "missing_in_b" || (!statusB && !dosageB)) {
    todayText = "Not reported today";
  } else if (statusB === "stopped") {
    todayText = "Today: stopped";
  } else if (statusB === "active") {
    if (dosageB && dosageA && dosageB.toLowerCase() !== dosageA.toLowerCase()) {
      todayText = `Today: active, new dose: ${dosageB}`;
    } else if (dosageB) {
      todayText = `Today: active, ${dosageB}`;
    } else if (dosageA) {
      todayText = `Today: active, ${dosageA}`;
    } else {
      todayText = "Today: active";
    }
  } else if (dosageB) {
    todayText = `Today: ${dosageB}`;
  }

  // 3. Reason
  let reason = "Requires clinician review.";
  if (compStatus === "conflict") {
    if (statusA === "active" && statusB === "stopped") {
      reason = "The record says you take this medication; you said you stopped it.";
    } else if (dosageA && dosageB && dosageA.toLowerCase() !== dosageB.toLowerCase()) {
      reason = "You reported a different dose from the record.";
    } else {
      reason = "The record says you take this medication; you said you stopped it.";
    }
  } else if (compStatus === "missing_in_b") {
    reason = "Not reported today.";
  } else if (compStatus === "agree" || compStatus === "agreement") {
    reason = "Matches the record.";
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
  };
}

/**
 * Returns a truthful, clinical source description for side A (prior baseline) or side B (today's check-in).
 * Rule: The word "hospital" appears ONLY when source is explicitly "fhir".
 */
export function describeSide(
  side: "a" | "b" | string,
  source?: string | null,
  trustLevel?: "high" | "medium" | "low" | string | null,
  mode?: string | null
): string {
  const normSide = (side || "").toLowerCase();
  const normSource = (source || "").toLowerCase();
  const normTrust = (trustLevel || "").toLowerCase();

  if (normSide === "b") {
    return "Today's check-in (reported by you)";
  }

  // Side A (earlier record)
  if (normSource === "fhir") {
    return "Hospital EHR (FHIR)";
  }

  if (normSource === "local") {
    if (normTrust === "low") {
      return "Your earlier self-reported record";
    }
    if (normTrust === "high") {
      return "Clinician-entered record";
    }
    return "Saved record (unverified)";
  }

  if (normTrust === "low") {
    return "Your earlier self-reported record";
  }

  if (normTrust === "high") {
    return "Clinician-entered record";
  }

  return "Saved record (unverified)";
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
 * Returns descriptive clinical presentation metadata for a triage level.
 * Never computes or alters the level; strictly presents server-provided data.
 */
export interface TriageLevelDescription {
  label: string;
  tone: "danger" | "warning" | "info" | "neutral";
  icon: string;
  headline: string;
  patientText: string;
}

export function describeTriageLevel(
  level?: string | null,
  serverGuidance?: string | null
): TriageLevelDescription {
  const norm = (level || "").toLowerCase().trim();

  if (norm === "emergency") {
    return {
      label: "Emergency",
      tone: "danger",
      icon: "AlertOctagon",
      headline: "Emergency",
      patientText: serverGuidance && serverGuidance.trim()
        ? serverGuidance.trim()
        : "Call your local emergency number now.",
    };
  }

  if (norm === "urgent") {
    return {
      label: "Needs a clinician today",
      tone: "warning",
      icon: "AlertTriangle",
      headline: "Needs a clinician today",
      patientText: serverGuidance && serverGuidance.trim()
        ? serverGuidance.trim()
        : "Please contact your clinician today. If you feel worse, call your local emergency number.",
    };
  }

  if (norm === "review") {
    return {
      label: "A clinician will review this",
      tone: "info",
      icon: "Info",
      headline: "A clinician will review this",
      patientText: serverGuidance && serverGuidance.trim()
        ? serverGuidance.trim()
        : "A clinician will review this. Please measure again later today and at the same time tomorrow.",
    };
  }

  return {
    label: "Routine",
    tone: "neutral",
    icon: "CheckCircle2",
    headline: "Routine check-in",
    patientText: serverGuidance && serverGuidance.trim()
      ? serverGuidance.trim()
      : "",
  };
}

/**
 * Returns plain-word descriptions for protocol names.
 */
export function describeProtocol(protocol?: string | null): string {
  const norm = (protocol || "").toLowerCase().trim();
  if (norm === "bp_severe") {
    return "Blood pressure in the crisis range";
  }
  if (norm === "bp_change") {
    return "Blood pressure above the patient's usual";
  }
  if (norm === "bp_low") {
    return "Low blood pressure";
  }
  if (norm === "glucose_high") {
    return "High glucose";
  }
  if (norm === "glucose_low") {
    return "Low glucose";
  }
  return protocol ? protocol.replace(/_/g, " ") : "Protocol";
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
    if (normDetail.includes("profile_incomplete")) {
      return "Please complete your date of birth and inclusion confirmation.";
    }
    if (normDetail.includes("provider_notification_consent_required")) {
      return "Provider notification consent is required before starting a check-in.";
    }
    if (normDetail.includes("consent_required") || normDetail.includes("active consent")) {
      return "Active consent is required before proceeding.";
    }
    return "Access denied. You do not have permission for this action.";
  }

  if (status === 409) {
    if (normDetail.includes("triage_incomplete")) {
      return "Please finish answering all safety questions.";
    }
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
    if (normDetail.includes("adults_only")) {
      return "ChronicCare AI is for adults (18 and over) in this release.";
    }
    if (normDetail.includes("invalid_date_of_birth")) {
      return "Please enter a valid date of birth (age 18 to 120).";
    }
    return "Invalid information provided. Please verify your input.";
  }

  if (status === 502) {
    return "The clinical service is temporarily unavailable. Please try again in a moment.";
  }

  if (status === 503 || status === 504) {
    return "The clinical service is currently waking up or busy. Please try again in a moment.";
  }

  if (!status || status === 0 || normDetail.includes("network") || normDetail.includes("failed to fetch")) {
    return "Network request failed. Please check your connection and try again.";
  }

  return detail && detail.trim() ? detail.trim() : "An unexpected error occurred. Please try again.";
}

