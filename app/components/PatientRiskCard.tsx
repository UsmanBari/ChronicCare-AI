"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { PatientRisk } from "../lib/api";
import { Activity, ShieldCheck, AlertTriangle, AlertOctagon, Info } from "lucide-react";

interface PatientRiskCardProps {
  risk?: PatientRisk | null;
  emergency?: boolean;
  isDemo?: boolean;
}

/**
 * PatientRiskCard renders an advisory qualitative risk band and top reasons
 * for patients after a check-in. It adheres strictly to medical safety invariants:
 * 1. Never displays probabilities, percentages, model names, or version strings.
 * 2. Displays only when status is "ok" or "not_enough_information".
 * 3. Never renders in emergency states or on computational errors.
 * 4. All clinical reason labels are wrapped in <bdi> for bidirectional text safety.
 */
export const PatientRiskCard: React.FC<PatientRiskCardProps> = ({
  risk: propRisk,
  emergency: propEmergency,
  isDemo = false,
}) => {
  const { liveCheckinResult, t, isUrdu } = useApp();

  const risk = propRisk !== undefined ? propRisk : liveCheckinResult?.risk;
  const isEmergency = propEmergency !== undefined ? propEmergency : liveCheckinResult?.emergency;

  // Invariant 1: Never render during emergencies
  if (isEmergency) {
    return null;
  }

  // Invariant 2: Never render when risk is missing or in an error/inapplicable state
  if (!risk || risk.status === "error" || risk.status === "not_applicable") {
    return null;
  }

  // State: not_enough_information
  if (risk.status === "not_enough_information") {
    return (
      <div
        data-testid="patient-risk-card"
        dir={isUrdu ? "rtl" : "ltr"}
        className={`p-4 sm:p-5 rounded-2xl bg-amber-50/70 border border-amber-200 text-left space-y-2.5 animate-fadeIn shadow-xs ${
          isUrdu ? "font-urdu text-right" : ""
        }`}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-amber-700 shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-amber-900">
              {t.patientRiskTitle}
            </span>
          </div>
          {isDemo && (
            <span className="px-2 py-0.5 rounded-full bg-amber-200/60 text-amber-900 text-[10px] font-bold uppercase tracking-wider border border-amber-300">
              {isUrdu ? "مثال" : "Example"}
            </span>
          )}
        </div>

        <p className="text-xs text-amber-900 font-medium leading-relaxed">
          {t.patientRiskMissingWaist}
        </p>

        <p className="text-[11px] text-amber-800/80 italic leading-relaxed pt-1 border-t border-amber-200/60">
          {risk.advisory || t.patientRiskAdvisory}
        </p>
      </div>
    );
  }

  // State: ok
  if (risk.status === "ok") {
    const rawBand = (risk.band || "low").toLowerCase();
    const bandConfig = {
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

    const config = bandConfig[rawBand as keyof typeof bandConfig] || bandConfig.low;
    const IconComponent = config.icon;

    // Up to 3 reasons
    const topReasons = (risk.reasons || []).slice(0, 3);

    return (
      <div
        data-testid="patient-risk-card"
        dir={isUrdu ? "rtl" : "ltr"}
        className={`p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4 text-left animate-fadeIn ${
          isUrdu ? "font-urdu text-right" : ""
        }`}
      >
        {/* Header & Advisory Notice */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/70 pb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4.5 h-4.5 text-teal-700 shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800">
              {t.patientRiskTitle}
            </span>
          </div>
          {isDemo && (
            <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold uppercase tracking-wider border border-slate-200">
              {isUrdu ? "مثال" : "Example"}
            </span>
          )}
        </div>

        {/* Qualitative Band Badge (Accessible: text + icon + dot, never color alone) */}
        <div className="flex items-center gap-3">
          <div
            data-testid="patient-risk-badge"
            className={`inline-flex items-center rounded-full border px-3.5 py-1.5 text-xs font-semibold tracking-wide shadow-2xs gap-2 ${config.badgeClasses}`}
          >
            <span className={`w-2 h-2 rounded-full shrink-0 ${config.dotClass}`} />
            <IconComponent className="w-4 h-4 shrink-0" />
            <span>{config.label}</span>
          </div>
        </div>

        {/* Contributing reasons list */}
        {topReasons.length > 0 && (
          <div className="space-y-2 pt-1">
            <span className="text-xs font-bold text-slate-700 block">
              {t.patientRiskTopReasons}
            </span>
            <ul
              data-testid="patient-risk-reasons"
              className="space-y-1.5 text-xs text-slate-600 pl-4 list-disc marker:text-teal-600"
            >
              {topReasons.map((r, idx) => {
                const labelText = isUrdu
                  ? (r.label?.ur || r.label?.en || r.feature)
                  : (r.label?.en || r.label?.ur || r.feature);
                return (
                  <li key={idx} data-testid="patient-risk-reason-item" className="leading-relaxed">
                    <bdi>{labelText}</bdi>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Mandatory Advisory Notice (never diagnoses or replaces clinical judgment) */}
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70 text-[11px] text-slate-500 leading-relaxed flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
          <p>{risk.advisory || t.patientRiskAdvisory}</p>
        </div>
      </div>
    );
  }

  return null;
};

