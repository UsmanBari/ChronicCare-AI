"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import {
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  FileText,
  Hospital,
  HelpCircle,
  Info,
  Scale,
  Activity,
  CheckCircle2,
} from "lucide-react";
import { describeSide, describeMedicationItem } from "../lib/presentation";
import { Pill } from "lucide-react";

export const ConflictScreen = () => {
  const { setScreen, checkIn, liveCheckinResult, liveEhrConnection, isLiveMode, t, isUrdu } = useApp();

  // In live mode, extract comparisons and verifications
  const obsComparisons = liveCheckinResult?.reconciliation?.observation_comparisons || [];
  const medComparisons = liveCheckinResult?.reconciliation?.medication_comparisons || [];
  const medVerifications = liveCheckinResult?.verification?.medication_verifications || [];

  const medicationItems = isLiveMode
    ? medComparisons.map((c: any) => {
        const v = medVerifications.find((ver: any) => ver.medication_name === c.medication_name);
        return {
          desc: describeMedicationItem(c, v),
          comparison: c,
          verification: v,
        };
      })
    : [];

  let sideALabel = isLiveMode
    ? describeSide("a", "local", "low", liveEhrConnection?.mode)
    : "Source A: Patient Check-in";
  let sideBLabel = isLiveMode
    ? describeSide("b", "local", "low", liveEhrConnection?.mode)
    : "Source B: Hospital EHR";
  let sideAValue = "180 mg/dL";
  let sideBValue = "140 mg/dL";
  let sideADesc = t.conflictPatientReported;
  let sideBDesc = t.conflictEhrRecord;
  let severity = liveCheckinResult?.max_severity || "medium";
  let isAllPlainConflicts = true;

  if (isLiveMode && liveCheckinResult?.reconciliation) {
    if (obsComparisons.length > 0) {
      isAllPlainConflicts = obsComparisons.every((c: any) => c.status === "conflict");
    }

    const conflictObs =
      obsComparisons.find(
        (c: any) =>
          c.status === "conflict" ||
          c.status === "flagged" ||
          c.status === "source_a_only" ||
          c.status === "source_b_only" ||
          c.status === "insufficient_data"
      ) || obsComparisons[0];

    if (conflictObs) {
      sideALabel = describeSide("a", conflictObs.source_a, null, liveEhrConnection?.mode);
      sideBLabel = describeSide("b", conflictObs.source_b, null, liveEhrConnection?.mode);
      sideAValue =
        conflictObs.value_a !== null && conflictObs.value_a !== undefined
          ? `${conflictObs.value_a} ${conflictObs.unit_a || ""}`.trim()
          : "Not on file";
      sideBValue =
        conflictObs.value_b !== null && conflictObs.value_b !== undefined
          ? `${conflictObs.value_b} ${conflictObs.unit_b || ""}`.trim()
          : "Not reported today";
      sideADesc = `${conflictObs.observation_type || "Observation"}: ${sideAValue}`;
      sideBDesc = `${conflictObs.observation_type || "Observation"}: ${sideBValue}`;
    }
  }

  const screenTitle = isLiveMode
    ? isAllPlainConflicts
      ? t.readingDiffersTitle
      : t.needsClinicianReviewTitle
    : t.conflictDetectedTitle;

  return (
    <div
      className="w-full max-w-xl mx-auto surface-raised rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      {/* Clinical Alert Header */}
      <div className="bg-amber-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-amber-700/90 border border-amber-500/40 flex items-center justify-center mx-auto mb-3 shadow-md">
          <AlertTriangle className="w-8 h-8 text-amber-200" />
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1.5">
          {screenTitle}
        </h1>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-900/50 text-amber-100 text-xs font-semibold border border-amber-600/40">
          <ShieldAlert className="w-4 h-4 text-amber-300" />
          <span>{severity ? `Severity: ${severity.toUpperCase()}` : t.confidenceLowTag}</span>
        </div>
      </div>

      <div className="p-6 sm:p-7 space-y-6">
        {/* Context Narrative */}
        <div className="text-center space-y-1">
          <p className="text-sm font-semibold text-navy-800">
            {isLiveMode
              ? isUrdu
                ? "آپ کے آج کے چیک ان اور پہلے سے موجود ریکارڈ کے درمیان فرق پایا گیا ہے۔"
                : "A difference was noted between today's check-in and your saved health record."
              : isUrdu
              ? "مریض کی درج کردہ معلومات اور اسپتال کے ریکارڈ کے درمیان تضاد پایا گیا ہے۔"
              : "A discrepancy has been detected between patient-reported telemetry and hospital records."}
          </p>
          <p className="text-xs text-slate-500">
            {isUrdu
              ? "طبی معالج کے جائزے کے لیے کیس بھیج دیا گیا ہے۔"
              : "Flagged for clinician review to ensure longitudinal safety."}
          </p>
        </div>

        {/* Structured Source Comparison Grid: Left = Side A (Earlier Record), Right = Side B (Today's Check-in) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Side A: Earlier Record */}
          <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border-2 border-slate-200 space-y-2 text-left">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-slate-200 text-slate-800 inline-flex items-center gap-1">
                <FileText className="w-3.5 h-3.5" />
                {sideALabel}
              </span>
            </div>
            <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
              {sideAValue}
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {sideADesc}
            </p>
          </div>

          {/* Side B: Today's Check-in */}
          <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/80 border-2 border-amber-300 space-y-2 text-left">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                <Activity className="w-3.5 h-3.5" />
                {sideBLabel}
              </span>
            </div>
            <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
              {sideBValue}
            </div>
            <p className="text-xs text-amber-950 leading-relaxed">
              {sideBDesc}
            </p>
          </div>
        </div>

        {/* Medication Comparison Items */}
        {isLiveMode && medicationItems.length > 0 && (
          <div className="space-y-3 pt-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
              {isUrdu ? "ادویات کا موازنہ:" : "Medication Reconciliation:"}
            </span>
            <div className="space-y-3">
              {medicationItems.map((item, idx) => {
                const isHigh = item.desc.severity === "high";
                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-2xl border-2 transition-all ${
                      isHigh
                        ? "bg-red-50/90 border-emergencyRed-500 shadow-xs ring-1 ring-emergencyRed-400"
                        : "bg-amber-50/80 border-amber-300"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <Pill className={`w-4 h-4 ${isHigh ? "text-emergencyRed-700" : "text-amber-800"}`} />
                        <span className="font-bold text-sm text-navy-900">{item.desc.title}</span>
                      </div>
                      <span
                        className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full inline-flex items-center gap-1 ${
                          isHigh
                            ? "bg-emergencyRed-100 text-emergencyRed-900 border border-emergencyRed-300 font-extrabold"
                            : "bg-amber-100 text-amber-900 border border-amber-300"
                        }`}
                      >
                        {isHigh ? (
                          <AlertTriangle className="w-3.5 h-3.5 text-emergencyRed-700" />
                        ) : (
                          <ShieldAlert className="w-3.5 h-3.5 text-amber-700" />
                        )}
                        <span>{item.desc.severity.toUpperCase()} SEVERITY</span>
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs py-1">
                      <div className="p-2.5 rounded-xl bg-white/90 border border-slate-200">
                        <span className="text-slate-500 font-semibold block">{item.desc.recordText}</span>
                      </div>
                      <div className="p-2.5 rounded-xl bg-white/90 border border-slate-200">
                        <span className="text-navy-900 font-bold block">{item.desc.todayText}</span>
                      </div>
                    </div>

                    <div className="pt-2 flex items-center justify-between text-xs">
                      <p className={`font-semibold ${isHigh ? "text-emergencyRed-950 font-bold" : "text-amber-950"}`}>
                        {item.desc.reason}
                      </p>
                      <span className="text-[11px] font-bold text-slate-500 shrink-0 ml-2">
                        Needs clinician review
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Low Confidence Tag */}
        {checkIn.lowConfidence && (
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-300/80 flex items-start gap-2.5 text-xs text-slate-700 animate-fadeIn">
            <HelpCircle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
            <span className="font-medium leading-relaxed">
              {t.unansweredQuestionTag}
            </span>
          </div>
        )}

        {/* Mandatory Caption in Mock Mode only */}
        {!isLiveMode && (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-start gap-3 text-xs text-slate-600 leading-relaxed">
            <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <span>{t.conflictSimulationCaption}</span>
          </div>
        )}

        {/* Continue to Routed to Review */}
        <button
          type="button"
          onClick={() => setScreen("conflict_review")}
          id="conflict-continue-btn"
          className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <span>{t.continue}</span>
          <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>
      </div>
    </div>
  );
};
