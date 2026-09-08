"use client";

import React from "react";
import { RiskLevel } from "../context/AppContext";
import { useApp } from "../context/AppContext";
import { ShieldCheck, AlertTriangle, AlertOctagon } from "lucide-react";

interface RiskBadgeProps {
  riskLevel: RiskLevel;
  size?: "sm" | "md" | "lg";
}

/**
 * Purely presentational component that accepts a `riskLevel` prop ('low' | 'moderate' | 'high').
 * It renders only the passed value without any calculation or inference.
 */
export const RiskBadge: React.FC<RiskBadgeProps> = ({ riskLevel, size = "md" }) => {
  const { t } = useApp();

  const configs = {
    low: {
      label: t.riskLowTitle,
      icon: ShieldCheck,
      badgeClasses: "bg-mutedGreen-100 text-mutedGreen-800 border-mutedGreen-800/30",
      dotClass: "bg-mutedGreen-800",
    },
    moderate: {
      label: t.riskModerateTitle,
      icon: AlertTriangle,
      badgeClasses: "bg-amber-100 text-amber-800 border-amber-800/30",
      dotClass: "bg-amber-800",
    },
    high: {
      label: t.riskHighTitle,
      icon: AlertOctagon,
      badgeClasses: "bg-emergencyRed-100 text-emergencyRed-800 border-emergencyRed-800/40",
      dotClass: "bg-emergencyRed-800",
    },
  };

  const config = configs[riskLevel] || configs.low;
  const IconComponent = config.icon;

  const sizeClasses = {
    sm: "px-2.5 py-1 text-xs gap-1.5",
    md: "px-4 py-2 text-sm gap-2",
    lg: "px-5 py-3 text-base gap-2.5",
  };

  const iconSizes = {
    sm: "w-3.5 h-3.5",
    md: "w-4 h-4",
    lg: "w-5 h-5",
  };

  return (
    <div
      className={`inline-flex items-center rounded-full border font-semibold tracking-wide shadow-sm ${config.badgeClasses} ${sizeClasses[size]}`}
    >
      <span className={`rounded-full shrink-0 ${config.dotClass} ${size === "lg" ? "w-2.5 h-2.5" : "w-2 h-2"}`} />
      <IconComponent className={`${iconSizes[size]} shrink-0`} />
      <span>{config.label}</span>
    </div>
  );
};
