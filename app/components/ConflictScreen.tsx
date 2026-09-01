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
} from "lucide-react";

export const ConflictScreen = () => {
  const { setScreen, checkIn, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn space-y-0">
      {/* Header */}
      <div className="bg-amber-800 p-6 text-white text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-amber-700/80 border border-amber-500/40 flex items-center justify-center mx-auto mb-3 shadow-md">
          <AlertTriangle className="w-8 h-8 text-amber-200" />
        </div>
        <h1 className="font-heading text-2xl font-bold text-white mb-1">
          {t.conflictDetectedTitle}
        </h1>
        <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-amber-900/40 text-amber-100 text-xs font-semibold">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>{t.confidenceLowTag}</span>
        </div>
      </div>

      <div className="p-6 space-y-5">
        {/* Conflict Data Comparison Box */}
        <div className="space-y-3">
          {/* Item 1: Patient Reported */}
          <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200/80 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-200/70 text-amber-900 inline-flex items-center gap-1">
                <FileText className="w-3 h-3" />
                {t.patientCheckInSource}
              </span>
            </div>
            <p className="text-sm font-bold text-navy-800 pt-1">
              {t.conflictPatientReported}
            </p>
          </div>

          {/* Item 2: Hospital EHR Record */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                <Hospital className="w-3 h-3" />
                {t.fhirEhrSource}
              </span>
            </div>
            <p className="text-sm font-semibold text-navy-800 pt-1">
              {t.conflictEhrRecord}
            </p>
          </div>
        </div>

        {/* Realism Detail: Low Confidence from M1 interview unanswered question */}
        {checkIn.lowConfidence && (
          <div className="p-3 rounded-xl bg-slate-100 border border-slate-300/80 flex items-start gap-2.5 text-xs text-slate-700 animate-fadeIn">
            <HelpCircle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
            <span className="font-medium">
              {t.unansweredQuestionTag}
            </span>
          </div>
        )}

        {/* Exact Protective Defensive Caption */}
        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5 text-[11px] text-slate-500 leading-relaxed">
          <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <span>{t.conflictSimulationCaption}</span>
        </div>

        {/* Continue to Routed to Review */}
        <button
          type="button"
          onClick={() => setScreen("conflict_review")}
          id="conflict-continue-btn"
          className="w-full py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <span>{t.continue}</span>
          <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>
      </div>
    </div>
  );
};
