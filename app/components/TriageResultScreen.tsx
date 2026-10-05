"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import {
  AlertTriangle,
  Info,
  AlertOctagon,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Home,
  ShieldAlert,
  Activity,
  Pill,
  FileText,
  Hospital,
} from "lucide-react";
import { describeTriageLevel, describeSide, describeMedicationItem } from "../lib/presentation";

export const TriageResultScreen = () => {
  const {
    returnToHomeAndClearRun,
    liveCheckinResult,
    liveEhrConnection,
    isLiveMode,
    t,
    isUrdu,
  } = useApp();

  const [isWhyOpen, setIsWhyOpen] = useState<boolean>(false);

  const triage = liveCheckinResult?.triage;
  const level = triage?.level || "routine";
  const levelDesc = describeTriageLevel(level, triage?.guidance);
  const reasons: string[] = Array.isArray(triage?.reasons) ? triage.reasons : [];

  const isUrgent = level.toLowerCase() === "urgent";

  // Check if there are also medication or reading conflicts to display below
  const obsComparisons = liveCheckinResult?.reconciliation?.observation_comparisons || [];
  const medComparisons = liveCheckinResult?.reconciliation?.medication_comparisons || [];
  const medVerifications = liveCheckinResult?.verification?.medication_verifications || [];

  const hasObsDiscrepancies = obsComparisons.some(
    (c: any) =>
      c.status === "conflict" ||
      c.status === "flagged" ||
      c.status === "source_a_only" ||
      c.status === "source_b_only" ||
      c.status === "insufficient_data"
  );

  const medicationItems: Array<{
    desc: ReturnType<typeof describeMedicationItem>;
    comparison: any;
    verification: any;
  }> = isLiveMode
    ? medComparisons.map((c: any) => {
        const v = medVerifications.find((ver: any) => ver.medication_name === c.medication_name);
        return {
          desc: describeMedicationItem(c, v),
          comparison: c,
          verification: v,
        };
      })
    : [];

  return (
    <div
      className="w-full max-w-xl mx-auto bg-white rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      {/* Header Banner - Urgent vs Review styled distinctly with color, icon, and text */}
      <div
        className={`p-7 text-white text-center relative overflow-hidden ${
          isUrgent
            ? "bg-gradient-to-br from-amber-700 via-amber-800 to-red-800 border-b-2 border-amber-600"
            : "bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800"
        }`}
      >
        <div
          className={`w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-3.5 shadow-md ${
            isUrgent
              ? "bg-amber-600/90 text-amber-100 border border-amber-400/40"
              : "bg-teal-500/20 text-teal-300 border border-teal-400/40"
          }`}
        >
          {isUrgent ? (
            <AlertTriangle className="w-8 h-8 text-amber-100 stroke-[2.5]" />
          ) : (
            <Info className="w-8 h-8 text-teal-300 stroke-[2.5]" />
          )}
        </div>

        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider mb-2 bg-black/20 text-white/90">
          <span>{levelDesc.label}</span>
        </div>

        <h1 className="font-heading text-2xl sm:text-[26px] font-bold tracking-tight text-white mb-1.5">
          {levelDesc.headline}
        </h1>
      </div>

      {/* Main Body */}
      <div className="p-6 sm:p-7 space-y-6">
        {/* Large Server Guidance Text */}
        <div
          className={`p-5 rounded-2xl border-2 text-center space-y-2 ${
            isUrgent
              ? "bg-amber-50/90 border-amber-400 text-amber-950 shadow-sm"
              : "bg-teal-50/70 border-teal-200 text-navy-900"
          }`}
        >
          <p className="text-base sm:text-lg font-bold leading-relaxed">
            {levelDesc.patientText}
          </p>
        </div>

        {/* Collapsible "Why am I seeing this?" */}
        {reasons.length > 0 && (
          <div className="rounded-2xl border border-slate-200 bg-slate-50/80 overflow-hidden transition-all">
            <button
              type="button"
              onClick={() => setIsWhyOpen(!isWhyOpen)}
              id="triage-why-toggle-btn"
              className="w-full p-4 text-left flex items-center justify-between gap-2 text-sm font-bold text-navy-800 hover:bg-slate-100/80 transition-colors"
            >
              <span>{t.triageWhyTitle}</span>
              {isWhyOpen ? (
                <ChevronUp className="w-4 h-4 text-slate-500" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-500" />
              )}
            </button>

            {isWhyOpen && (
              <div className="p-4 pt-1 border-t border-slate-200 space-y-2 text-xs sm:text-sm text-slate-700 animate-fadeIn">
                <ul className="space-y-1.5 list-disc list-inside">
                  {reasons.map((reason, idx) => (
                    <li key={idx} className="leading-relaxed">
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Discrepancies / Medication Conflicts below if present */}
        {hasObsDiscrepancies && obsComparisons.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-slate-200">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
              {isUrdu ? "طبی مشاہدات میں فرق:" : "Telemetry Discrepancies:"}
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {obsComparisons.map((c: any, idx: number) => (
                <div key={idx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <span className="font-bold text-navy-900 block">
                    {c.observation_type?.replace(/_/g, " ").toUpperCase() || "OBSERVATION"}
                  </span>
                  <div className="flex justify-between text-slate-600">
                    <span>Record: {c.value_a !== null ? `${c.value_a} ${c.unit_a || ""}` : "N/A"}</span>
                    <span className="font-semibold text-navy-900">Today: {c.value_b !== null ? `${c.value_b} ${c.unit_b || ""}` : "N/A"}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {medicationItems.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-slate-200">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
              {isUrdu ? "ادویات کا موازنہ:" : "Medication Discrepancies:"}
            </span>
            <div className="space-y-2 text-xs">
              {medicationItems.map((item, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <div className="flex items-center justify-between font-bold text-navy-900">
                    <span>{item.desc.title}</span>
                    <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                      {item.desc.severity}
                    </span>
                  </div>
                  <p className="text-slate-600">{item.desc.reason}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Not a diagnosis disclaimer */}
        <div className="p-3 text-center text-xs font-semibold text-slate-500 bg-slate-50 rounded-xl border border-slate-200">
          <span>
            {t.notADiagnosisDisclaimer}
          </span>
        </div>

        {/* Back to home button */}
        <button
          type="button"
          onClick={returnToHomeAndClearRun}
          id="triage-back-home-btn"
          className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <Home className="w-4 h-4" />
          <span>{isUrdu ? "ہوم پر واپس جائیں" : "Back to home"}</span>
        </button>
      </div>
    </div>
  );
};
