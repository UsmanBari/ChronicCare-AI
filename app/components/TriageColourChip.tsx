import React from "react";
import { useApp } from "../context/AppContext";

export interface TriageColourChipProps {
  level?: string | null;
  colour?: string | null;
  className?: string;
  size?: "sm" | "md";
}

export const TriageColourChip: React.FC<TriageColourChipProps> = ({
  level,
  colour,
  className = "",
  size = "md",
}) => {
  const { t } = useApp();

  const normLevel = (level || "").toLowerCase().trim();
  let normColour = (colour || "").toLowerCase().trim();

  if (!normColour) {
    if (normLevel === "emergency" || normLevel === "urgent") {
      normColour = "red";
    } else if (normLevel === "review") {
      normColour = "yellow";
    } else {
      normColour = "green";
    }
  }

  let labelText = t.triageChipGreenRoutine;
  let bgClasses = "bg-emerald-50 text-emerald-800 border-emerald-200";
  let dotClass = "bg-emerald-500";

  if (normColour === "red") {
    if (normLevel === "emergency") {
      labelText = t.triageChipRedEmergency;
      bgClasses = "bg-rose-100 text-rose-900 border-rose-300";
      dotClass = "bg-rose-600 animate-pulse";
    } else {
      labelText = t.triageChipRedUrgent;
      bgClasses = "bg-rose-50 text-rose-800 border-rose-200";
      dotClass = "bg-rose-500";
    }
  } else if (normColour === "yellow" || normLevel === "review") {
    labelText = t.triageChipYellowReview;
    bgClasses = "bg-amber-50 text-amber-900 border-amber-200";
    dotClass = "bg-amber-500";
  }

  const paddingClass = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-3 py-1 text-xs";

  return (
    <span
      data-testid="triage-colour-chip"
      data-colour={normColour}
      data-level={normLevel}
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold shadow-2xs transition-colors ${bgClasses} ${paddingClass} ${className}`}
      role="status"
      aria-label={`Triage status: ${labelText}`}
    >
      <span className={`w-2 h-2 rounded-full shrink-0 ${dotClass}`} aria-hidden="true" />
      <span>{labelText}</span>
    </span>
  );
};

