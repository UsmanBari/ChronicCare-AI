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

export const ConflictScreen = () => {
  const { setScreen, checkIn, liveCheckinResult, isLiveMode, t, isUrdu } = useApp();

  // In live mode, extract first conflicting comparison from reconciliation result if available
  let sourceAName = "Source A: Patient Check-in";
  let sourceBName = "Source B: Hospital EHR";
  let sourceAValue = "180 mg/dL";
  let sourceBValue = "140 mg/dL";
  let sourceADesc = t.conflictPatientReported;
  let sourceBDesc = t.conflictEhrRecord;
  let severity = liveCheckinResult?.max_severity || "medium";

  if (isLiveMode && liveCheckinResult?.reconciliation) {
    const obsComparisons = liveCheckinResult.reconciliation.observation_comparisons || [];
    const medComparisons = liveCheckinResult.reconciliation.medication_comparisons || [];

    const conflictObs = obsComparisons.find(
      (c: any) => c.status === "conflict" || c.status === "flagged" || c.status === "source_a_only" || c.status === "source_b_only"
    ) || obsComparisons[0];

    if (conflictObs) {
      sourceAName = conflictObs.source_a || "Patient Check-in";
      sourceBName = conflictObs.source_b || "Hospital EHR";
      sourceAValue = conflictObs.value_a !== null && conflictObs.value_a !== undefined
        ? `${conflictObs.value_a} ${conflictObs.unit_a || ""}`.trim()
        : "Not reported";
      sourceBValue = conflictObs.value_b !== null && conflictObs.value_b !== undefined
        ? `${conflictObs.value_b} ${conflictObs.unit_b || ""}`.trim()
        : "Not on file";
      sourceADesc = `${conflictObs.observation_type || "Observation"}: ${sourceAValue}`;
      sourceBDesc = `${conflictObs.observation_type || "Observation"}: ${sourceBValue}`;
    } else if (medComparisons.length > 0) {
      const conflictMed = medComparisons[0];
      sourceAName = conflictMed.source_a || "Patient Check-in";
      sourceBName = conflictMed.source_b || "Hospital EHR";
      sourceAValue = conflictMed.dosage_a || conflictMed.status_a || "Reported";
      sourceBValue = conflictMed.dosage_b || conflictMed.status_b || "Recorded";
      sourceADesc = `${conflictMed.medication_name}: ${sourceAValue}`;
      sourceBDesc = `${conflictMed.medication_name}: ${sourceBValue}`;
    }
  }

  return (
    <div className="w-full max-w-xl mx-auto surface-raised rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Clinical Alert Header */}
      <div className="bg-amber-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-amber-700/90 border border-amber-500/40 flex items-center justify-center mx-auto mb-3 shadow-md">
          <AlertTriangle className="w-8 h-8 text-amber-200" />
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1.5">
          {t.conflictDetectedTitle}
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
            {isUrdu
              ? "مریض کی درج کردہ معلومات اور اسپتال کے ریکارڈ کے درمیان تضاد پایا گیا ہے۔"
              : "A discrepancy has been detected between patient-reported telemetry and hospital records."}
          </p>
          <p className="text-xs text-slate-500">
            {isUrdu ? "طبی معالج کے جائزے کے لیے کیس الگ کیا جا رہا ہے۔" : "Flagged for clinician-in-the-loop review to ensure safety."}
          </p>
        </div>

        {/* Structured Source Comparison Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Source 1: Patient Reported */}
          <div className="p-4 sm:p-5 rounded-2xl bg-amber-50/80 border-2 border-amber-300 space-y-2 text-left">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-amber-200 text-amber-900 inline-flex items-center gap-1">
                <FileText className="w-3.5 h-3.5" />
                {sourceAName}
              </span>
            </div>
            <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
              {sourceAValue}
            </div>
            <p className="text-xs text-amber-950 leading-relaxed">
              {sourceADesc}
            </p>
          </div>

          {/* Source 2: Hospital EHR */}
          <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border-2 border-slate-200 space-y-2 text-left">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                <Hospital className="w-3.5 h-3.5" />
                {sourceBName}
              </span>
            </div>
            <div className="text-2xl font-bold text-navy-800 pt-1 font-mono">
              {sourceBValue}
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              {sourceBDesc}
            </p>
          </div>
        </div>

        {/* Low Confidence Tag */}
        {checkIn.lowConfidence && (
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-300/80 flex items-start gap-2.5 text-xs text-slate-700 animate-fadeIn">
            <HelpCircle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
            <span className="font-medium leading-relaxed">
              {t.unansweredQuestionTag}
            </span>
          </div>
        )}

        {/* Mandatory Caption */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-start gap-3 text-xs text-slate-600 leading-relaxed">
          <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <span>{t.conflictSimulationCaption}</span>
        </div>

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
