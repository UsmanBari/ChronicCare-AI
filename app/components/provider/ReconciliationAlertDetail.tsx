"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import {
  AlertTriangle,
  FileText,
  Hospital,
  ShieldAlert,
  Calendar,
  CheckCircle2,
  ArrowLeft,
  Info,
  ShieldCheck,
  AlertOctagon,
} from "lucide-react";

export const ReconciliationAlertDetail = () => {
  const {
    setProviderScreen,
    resolveCase,
    resolvedCases,
    demoScenario,
    t,
    isUrdu,
  } = useApp();

  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const isResolved = resolvedCases.includes("Ali Khan");

  const handleResolve = () => {
    resolveCase("Ali Khan");
    setToastMessage(t.caseResolvedToast);
    setTimeout(() => {
      setToastMessage(null);
    }, 2500);
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-5 animate-fadeIn py-2">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-3.5 rounded-xl bg-mutedGreen-100 border border-mutedGreen-800 text-mutedGreen-800 text-xs font-bold shadow-lg flex items-center justify-between animate-slideUp">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-mutedGreen-800 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setProviderScreen("review_queue")}
            id="reconciliation-back-btn"
            className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 transition-colors"
          >
            <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
          </button>
          <div>
            <h1 className="font-heading text-2xl font-bold text-navy-800">
              {t.alertDetailsTitle}
            </h1>
            <span className="text-xs text-slate-500">Patient: Ali Khan (PT-04821) • T2D</span>
          </div>
        </div>

        {isResolved ? (
          <span className="px-3 py-1 rounded-full bg-mutedGreen-100 text-mutedGreen-800 text-xs font-bold inline-flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
          </span>
        ) : (
          <span className="px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-bold inline-flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5" /> Action Required
          </span>
        )}
      </div>

      {/* Discrepancy Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-700" />
            <span className="font-heading font-bold text-base text-navy-800">
              Blood Glucose Measurement Conflict
            </span>
          </div>
          <span className="text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-0.5 rounded bg-amber-100 text-amber-800">
            Confidence: Low
          </span>
        </div>

        {/* Source Comparison Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Patient Reported */}
          <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-200 text-amber-900 inline-flex items-center gap-1">
                <FileText className="w-3 h-3" />
                Patient Check-in
              </span>
              <span className="text-[10px] text-slate-500">Today, 8:42 AM</span>
            </div>
            <div className="text-xl font-bold text-navy-800 pt-1">
              180 mg/dL
            </div>
            <p className="text-[11px] text-slate-600">
              Patient-reported blood sugar elevation via daily check-in survey.
            </p>
          </div>

          {/* Clinic FHIR EHR Record */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                <Hospital className="w-3 h-3" />
                FHIR EHR
              </span>
              <span className="text-[10px] text-slate-500">Last Clinic Visit</span>
            </div>
            <div className="text-xl font-bold text-navy-800 pt-1">
              140 mg/dL
            </div>
            <p className="text-[11px] text-slate-600">
              Verified clinical lab telemetry from City General Hospital EHR.
            </p>
          </div>
        </div>

        {/* Mandatory Defensive Caption (Exact Wording) */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5 text-xs text-slate-600 leading-relaxed">
          <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <span>
            This is a simulated system state for demonstration purposes. The actual reconciliation and verification logic has been separately validated in our technical proof of concept.
          </span>
        </div>

        {/* Three Action Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          {/* 1. Resolve */}
          <button
            type="button"
            onClick={handleResolve}
            disabled={isResolved}
            id="reconciliation-resolve-btn"
            className={`py-3 px-4 rounded-xl font-semibold text-xs transition-all flex items-center justify-center gap-2 ${
              isResolved
                ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                : "bg-mutedGreen-800 hover:bg-mutedGreen-700 active:scale-[0.98] text-white shadow-md"
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{isResolved ? "Case Resolved ✓" : t.resolve}</span>
          </button>

          {/* 2. Schedule Appointment */}
          <button
            type="button"
            onClick={() => setProviderScreen("schedule_appointment")}
            id="reconciliation-schedule-btn"
            className="py-3 px-4 bg-teal-700 hover:bg-teal-600 active:scale-[0.98] text-white font-semibold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <Calendar className="w-4 h-4" />
            <span>{t.scheduleAppointment}</span>
          </button>

          {/* 3. Escalate */}
          <button
            type="button"
            onClick={() => setProviderScreen("schedule_appointment")}
            id="reconciliation-escalate-btn"
            className="py-3 px-4 bg-amber-800 hover:bg-amber-700 active:scale-[0.98] text-white font-semibold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <AlertOctagon className="w-4 h-4" />
            <span>{t.escalate}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
