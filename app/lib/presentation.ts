/**
 * Pure presentation logic for clinical labels, side descriptions, and user-safe error mappings.
 * Free of React dependencies to ensure pure unit testability.
 */

export interface DeltaInfo {
  delta?: number | string | null;
  unit?: string | null;
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
 * Maps raw API status codes and detail strings to user-safe English message keys.
 */
export function mapApiError(status?: number | null, detail?: string | null): string {
  const normDetail = (detail || "").toLowerCase();

  if (status === 401) {
    return "Your session has expired. Please sign in again.";
  }

  if (status === 403) {
    return "Access denied. You do not have permission for this action.";
  }

  if (status === 409) {
    if (normDetail.includes("stale_step")) {
      return "The check-in question was updated. Please answer the current question.";
    }
    if (normDetail.includes("concurrent_update")) {
      return "A conflict occurred while saving your answer. Please try again.";
    }
    return "A conflict occurred with existing data or state.";
  }

  if (status === 422) {
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
