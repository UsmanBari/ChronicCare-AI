/**
 * Physiological Reference Ranges Helper (F2 / Doctor Decision D5).
 * One single source of truth for UI range indicators and status tags.
 *
 * Rules & Thresholds strictly from CLINICAL_RULES.md and agents/reference_ranges.py:
 * - Systolic BP: 90 to < 140 mmHg (2025 AHA/ACC Guideline)
 * - Diastolic BP: 60 to < 90 mmHg (2025 AHA/ACC Guideline)
 * - Fasting Glucose: 70 to 130 mg/dL (3.9 to 7.2 mmol/L) (ADA Standards of Care)
 * - Post-Meal / General Glucose: 70 to 180 mg/dL (3.9 to 10.0 mmol/L) (ADA Standards of Care)
 *
 * Non-diagnostic wording disclaimer: "Normal range used by this app"
 */

export interface ReadingStatus {
  status: "normal" | "above" | "below" | "unspecified";
  label: string;
  colorClass: string;
  badgeClass: string;
}

export function getNormalRangeText(
  obsType: string,
  language: "en" | "ur" | "roman_ur" = "en",
  glucoseUnit: "mg/dL" | "mmol/L" = "mg/dL"
): string {
  const norm = (obsType || "").toLowerCase();
  const isUr = language === "ur";
  const isRoman = language === "roman_ur";

  if (norm.includes("systolic") || norm === "sbp") {
    if (isUr) return "نارمل: 90–139 ملی میٹر ایچ جی";
    return "Normal: 90–139 mmHg";
  }

  if (norm.includes("diastolic") || norm === "dbp") {
    if (isUr) return "نارمل: 60–89 ملی میٹر ایچ جی";
    return "Normal: 60–89 mmHg";
  }

  if (norm.includes("blood_pressure") || norm === "bp") {
    if (isUr) return "نارمل: 90–139 / 60–89 ملی میٹر ایچ جی";
    return "Normal: 90–139 / 60–89 mmHg";
  }

  if (norm.includes("glucose") || norm.includes("sugar")) {
    if (glucoseUnit === "mmol/L") {
      if (isUr) return "نارمل: 3.9–7.2 نہار منہ / 3.9–10.0 کھانے کے بعد mmol/L";
      if (isRoman) return "Normal: 3.9–7.2 nihar munh / 3.9–10.0 khaney ke baad mmol/L";
      return "Normal: 3.9–7.2 fasting / 3.9–10.0 post-meal mmol/L";
    }
    if (isUr) return "نارمل: 70–130 نہار منہ / 70–180 کھانے کے بعد mg/dL";
    if (isRoman) return "Normal: 70–130 nihar munh / 70–180 khaney ke baad mg/dL";
    return "Normal: 70–130 fasting / 70–180 post-meal mg/dL";
  }

  return "";
}

export function getReadingStatus(
  obsType: string,
  value: number | string | null | undefined,
  language: "en" | "ur" | "roman_ur" = "en",
  glucoseUnit: "mg/dL" | "mmol/L" = "mg/dL"
): ReadingStatus {
  const isUr = language === "ur";
  const isRoman = language === "roman_ur";

  const labels = {
    normal: isUr ? "نارمل" : "Normal",
    above: isUr ? "نارمل سے زیادہ" : isRoman ? "Normal se zyada" : "Above normal",
    below: isUr ? "نارمل سے کم" : isRoman ? "Normal se kam" : "Below normal",
  };

  if (value === null || value === undefined || value === "") {
    return { status: "unspecified", label: "", colorClass: "", badgeClass: "" };
  }

  const num = typeof value === "number" ? value : parseFloat(String(value));
  if (isNaN(num)) {
    return { status: "unspecified", label: "", colorClass: "", badgeClass: "" };
  }

  const norm = (obsType || "").toLowerCase();

  // 1. Systolic BP: [90, 140)
  if (norm.includes("systolic") || norm === "sbp") {
    if (num < 90) {
      return {
        status: "below",
        label: labels.below,
        colorClass: "text-blue-700",
        badgeClass: "bg-blue-50 text-blue-800 border-blue-200",
      };
    }
    if (num >= 140) {
      return {
        status: "above",
        label: labels.above,
        colorClass: "text-amber-800",
        badgeClass: "bg-amber-50 text-amber-900 border-amber-200",
      };
    }
    return {
      status: "normal",
      label: labels.normal,
      colorClass: "text-teal-700",
      badgeClass: "bg-teal-50 text-teal-800 border-teal-200",
    };
  }

  // 2. Diastolic BP: [60, 90)
  if (norm.includes("diastolic") || norm === "dbp") {
    if (num < 60) {
      return {
        status: "below",
        label: labels.below,
        colorClass: "text-blue-700",
        badgeClass: "bg-blue-50 text-blue-800 border-blue-200",
      };
    }
    if (num >= 90) {
      return {
        status: "above",
        label: labels.above,
        colorClass: "text-amber-800",
        badgeClass: "bg-amber-50 text-amber-900 border-amber-200",
      };
    }
    return {
      status: "normal",
      label: labels.normal,
      colorClass: "text-teal-700",
      badgeClass: "bg-teal-50 text-teal-800 border-teal-200",
    };
  }

  // 3. Glucose: [70, 180] mg/dL or [3.9, 10.0] mmol/L
  if (norm.includes("glucose") || norm.includes("sugar")) {
    const isMmol = glucoseUnit === "mmol/L" || num < 30; // auto-detect mmol if < 30
    const lowThresh = isMmol ? 3.9 : 70.0;
    const highThresh = isMmol ? 10.0 : 180.0;

    if (num < lowThresh) {
      return {
        status: "below",
        label: labels.below,
        colorClass: "text-blue-700",
        badgeClass: "bg-blue-50 text-blue-800 border-blue-200",
      };
    }
    if (num > highThresh) {
      return {
        status: "above",
        label: labels.above,
        colorClass: "text-amber-800",
        badgeClass: "bg-amber-50 text-amber-900 border-amber-200",
      };
    }
    return {
      status: "normal",
      label: labels.normal,
      colorClass: "text-teal-700",
      badgeClass: "bg-teal-50 text-teal-800 border-teal-200",
    };
  }

  return { status: "unspecified", label: "", colorClass: "", badgeClass: "" };
}
