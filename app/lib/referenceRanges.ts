/**
 * Physiological Target Ranges Helper (G3 / Doctor Decisions D5 & D6).
 * One single source of truth for UI range indicators and status tags.
 *
 * Rules & Thresholds strictly from CLINICAL_RULES.md and agents/reference_ranges.py:
 * - Systolic BP: 90 to < 140 mmHg (2025 AHA/ACC Guideline)
 * - Diastolic BP: 60 to < 90 mmHg (2025 AHA/ACC Guideline)
 * - Fasting Glucose: 90 to 125 mg/dL (5.0 to 6.9 mmol/L) (Doctor Decision D6, Nov 2026)
 * - Post-Meal Glucose: 125 to 200 mg/dL (6.9 to 11.1 mmol/L) (Doctor Decision D6; 90–124 accepted as in-target)
 * - Random / General Glucose: 90 to 200 mg/dL (5.0 to 11.1 mmol/L)
 *
 * Non-diagnostic wording disclaimer: "Target range used by this app"
 */

export interface ReadingStatus {
  status: "in_target" | "above_target" | "below_target" | "normal" | "above" | "below" | "unspecified";
  label: string;
  colorClass: string;
  badgeClass: string;
}

export function getTargetRangeText(
  obsType: string,
  language: "en" | "ur" | "roman_ur" = "en",
  glucoseUnit: "mg/dL" | "mmol/L" = "mg/dL"
): string {
  const norm = (obsType || "").toLowerCase();
  const isUr = language === "ur";
  const isRoman = language === "roman_ur";

  if (norm.includes("systolic") || norm === "sbp") {
    if (isUr) return "ہدف: 90–139 ملی میٹر ایچ جی";
    return "Target: 90–139 mmHg";
  }

  if (norm.includes("diastolic") || norm === "dbp") {
    if (isUr) return "ہدف: 60–89 ملی میٹر ایچ جی";
    return "Target: 60–89 mmHg";
  }

  if (norm.includes("blood_pressure") || norm === "bp") {
    if (isUr) return "ہدف: 90–139 / 60–89 ملی میٹر ایچ جی";
    return "Target: 90–139 / 60–89 mmHg";
  }

  if (norm.includes("glucose") || norm.includes("sugar")) {
    if (glucoseUnit === "mmol/L") {
      if (isUr) return "ہدف: 5.0–6.9 نہار منہ / 6.9–11.1 کھانے کے بعد mmol/L";
      if (isRoman) return "Target: 5.0–6.9 nihar munh / 6.9–11.1 khaney ke baad mmol/L";
      return "Target: 5.0–6.9 fasting / 6.9–11.1 post-meal mmol/L";
    }
    if (isUr) return "ہدف: 90–125 نہار منہ / 125–200 کھانے کے بعد mg/dL";
    if (isRoman) return "Target: 90–125 nihar munh / 125–200 khaney ke baad mg/dL";
    return "Target: 90–125 fasting / 125–200 after meals mg/dL";
  }

  return "";
}

export const getNormalRangeText = getTargetRangeText;

export function getReadingStatus(
  obsType: string,
  value: number | string | null | undefined,
  language: "en" | "ur" | "roman_ur" = "en",
  glucoseUnit: "mg/dL" | "mmol/L" = "mg/dL",
  context?: string
): ReadingStatus {
  const isUr = language === "ur";
  const isRoman = language === "roman_ur";

  const labels = {
    in_target: isUr ? "ہدف کے مطابق" : isRoman ? "Target ke mutabiq" : "In target",
    above_target: isUr ? "ہدف سے زیادہ" : isRoman ? "Target se zyada" : "Above target",
    below_target: isUr ? "ہدف سے کم" : isRoman ? "Target se kam" : "Below target",
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
        status: "below_target",
        label: labels.below_target,
        colorClass: "text-blue-700",
        badgeClass: "bg-blue-50 text-blue-800 border-blue-200",
      };
    }
    if (num >= 140) {
      return {
        status: "above_target",
        label: labels.above_target,
        colorClass: "text-amber-800",
        badgeClass: "bg-amber-50 text-amber-900 border-amber-200",
      };
    }
    return {
      status: "in_target",
      label: labels.in_target,
      colorClass: "text-teal-700",
      badgeClass: "bg-teal-50 text-teal-800 border-teal-200",
    };
  }

  // 2. Diastolic BP: [60, 90)
  if (norm.includes("diastolic") || norm === "dbp") {
    if (num < 60) {
      return {
        status: "below_target",
        label: labels.below_target,
        colorClass: "text-blue-700",
        badgeClass: "bg-blue-50 text-blue-800 border-blue-200",
      };
    }
    if (num >= 90) {
      return {
        status: "above_target",
        label: labels.above_target,
        colorClass: "text-amber-800",
        badgeClass: "bg-amber-50 text-amber-900 border-amber-200",
      };
    }
    return {
      status: "in_target",
      label: labels.in_target,
      colorClass: "text-teal-700",
      badgeClass: "bg-teal-50 text-teal-800 border-teal-200",
    };
  }

  // 3. Glucose (Doctor Decision D6):
  // Fasting: 90–125 mg/dL (5.0–6.9 mmol/L). Below 90 is below target in any context.
  // After meals: 125–200 mg/dL (6.9–11.1 mmol/L). 90–124 post-meal is In target.
  // Random/unspecified: 90–200 mg/dL (5.0–11.1 mmol/L).
  if (norm.includes("glucose") || norm.includes("sugar")) {
    const isMmol = glucoseUnit === "mmol/L" || num < 30; // auto-detect mmol if < 30
    const ctx = (context || "").trim().toLowerCase();
    const isFasting = ctx === "fasting" || ctx === "before_meal" || ctx === "before_breakfast";

    const lowThresh = isMmol ? 5.0 : 90.0;
    const highThresh = isMmol ? (isFasting ? 6.9 : 11.1) : (isFasting ? 125.0 : 200.0);

    if (num < lowThresh) {
      return {
        status: "below_target",
        label: labels.below_target,
        colorClass: "text-blue-700",
        badgeClass: "bg-blue-50 text-blue-800 border-blue-200",
      };
    }
    if (num > highThresh) {
      return {
        status: "above_target",
        label: labels.above_target,
        colorClass: "text-amber-800",
        badgeClass: "bg-amber-50 text-amber-900 border-amber-200",
      };
    }
    return {
      status: "in_target",
      label: labels.in_target,
      colorClass: "text-teal-700",
      badgeClass: "bg-teal-50 text-teal-800 border-teal-200",
    };
  }

  return { status: "unspecified", label: "", colorClass: "", badgeClass: "" };
}
