/**
 * Condition normalization and helper flags for condition-aware UI presentation.
 * Supports variations: "Type 2 Diabetes", "diabetes", "Hypertension", "hypertension", etc.
 */

export interface ConditionFlags {
  hasDiabetes: boolean;
  hasHypertension: boolean;
  isHypertensionOnly: boolean;
  isDiabetesOnly: boolean;
  hasBoth: boolean;
}

export function getConditionFlags(
  input?: string[] | { conditions?: string[] | null } | null
): ConditionFlags {
  const list: string[] = Array.isArray(input)
    ? input
    : input && Array.isArray(input.conditions)
    ? input.conditions
    : [];

  const normalized = list
    .filter((c): c is string => typeof c === "string")
    .map((c) => c.trim().toLowerCase());

  const hasDiabetes = normalized.some(
    (c) =>
      c === "diabetes" ||
      c === "type 2 diabetes" ||
      c === "type-2 diabetes" ||
      c === "t2d" ||
      c.includes("diabet")
  );

  const hasHypertension = normalized.some(
    (c) =>
      c === "hypertension" ||
      c === "high blood pressure" ||
      c === "htn" ||
      c.includes("hypertens")
  );

  return {
    hasDiabetes,
    hasHypertension,
    isHypertensionOnly: hasHypertension && !hasDiabetes,
    isDiabetesOnly: hasDiabetes && !hasHypertension,
    hasBoth: hasDiabetes && hasHypertension,
  };
}
