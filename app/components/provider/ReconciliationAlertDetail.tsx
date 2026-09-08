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
  Scale,
  Sparkles,
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
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn py-2" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-4 rounded-2xl bg-mutedGreen-100 border border-mutedGreen-800 text-mutedGreen-900 text-sm font-bold shadow-lg flex items-center justify-between animate-slideUp">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-mutedGreen-800 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setProviderScreen("review_queue")}
            id="reconciliation-back-btn"
            className="w-11 h-11 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 flex items-center justify-center transition-colors shadow-xs"
          >
            <ArrowLeft className={`w-5 h-5 ${isUrdu ? "rotate-180" : ""}`} />
          </button>
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
              {t.alertDetailsTitle}
            </h1>
            <span className="text-xs font-semibold text-slate-500">
              Patient: Ali Khan (PT-04821) • 58y M • Type 2 Diabetes
            </span>
          </div>
        </div>

        {isResolved ? (
          <span className="px-3.5 py-1.5 rounded-full bg-mutedGreen-100 text-mutedGreen-800 text-xs font-bold inline-flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" /> Case Resolved
          </span>
        ) : (
          <span className="px-3.5 py-1.5 rounded-full bg-amber-100 text-amber-900 text-xs font-bold inline-flex items-center gap-1.5 border border-amber-300">
            <ShieldAlert className="w-4 h-4 text-amber-800" /> Action Required
          </span>
        )}
      </div>

      {/* Clinical Investigation Card */}
      <div className="surface-card rounded-3xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-4">
          <div className="flex items-center gap-2.5">
            <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
            <span className="font-heading font-bold text-lg text-navy-800">
              Blood Glucose Measurement Discrepancy
            </span>
          </div>
          <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-amber-100 text-amber-900 self-start sm:self-auto border border-amber-300/80">
            AI Confidence: Low (Review Required)
          </span>
        </div>

        {/* Source Comparison Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Source 1: Patient Reported */}
          <div className="p-5 rounded-2xl bg-amber-50/80 border-2 border-amber-300 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-amber-200 text-amber-900 inline-flex items-center gap-1">
                <FileText className="w-3.5 h-3.5" />
                Source A: Patient Telemetry
              </span>
              <span className="text-xs text-slate-500 font-medium">Today, 8:42 AM</span>
            </div>
            <div className="text-3xl font-bold text-navy-800 pt-1 font-sans">
              180 <span className="text-sm font-semibold text-slate-500">mg/dL</span>
            </div>
            <p className="text-xs text-amber-950 leading-relaxed">
              Self-reported blood sugar elevation via daily check-in survey.
            </p>
          </div>

          {/* Source 2: Clinic FHIR EHR Record */}
          <div className="p-5 rounded-2xl bg-slate-50 border-2 border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                <Hospital className="w-3.5 h-3.5" />
                Source B: Hospital FHIR EHR
              </span>
              <span className="text-xs text-slate-500 font-medium">Last Clinic Visit</span>
            </div>
            <div className="text-3xl font-bold text-navy-800 pt-1 font-sans">
              140 <span className="text-sm font-semibold text-slate-500">mg/dL</span>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Verified clinical lab telemetry from City General Hospital EHR system.
            </p>
          </div>
        </div>

        {/* AI Reconciliation Reasoning */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5">
          <div className="flex items-center gap-2 font-bold text-xs text-navy-800 uppercase tracking-wider">
            <Sparkles className="w-4 h-4 text-teal-700" />
            <span>Automated Reconciliation Analysis</span>
          </div>
          <p className="text-xs text-slate-700 leading-relaxed">
            System flagged a 40 mg/dL elevation delta between patient check-in telemetry and historical baseline. Cross-validation recommends clinical clinician confirmation before updating long-term glycemic baseline.
          </p>
        </div>

        {/* Mandatory Defensive Caption (Exact Wording Preserved) */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-start gap-3 text-xs text-slate-600 leading-relaxed">
          <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <span>
            This is a simulated system state for demonstration purposes. The actual reconciliation and verification logic has been separately validated in our technical proof of concept.
          </span>
        </div>

        {/* Three Action Buttons (48px Touch Targets) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          {/* 1. Resolve */}
          <button
            type="button"
            onClick={handleResolve}
            disabled={isResolved}
            id="reconciliation-resolve-btn"
            className={`min-h-[48px] py-3 px-4 rounded-xl font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-2 ${
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
            className="min-h-[48px] py-3 px-4 bg-teal-700 hover:bg-teal-600 active:scale-[0.98] text-white font-bold text-xs sm:text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <Calendar className="w-4 h-4" />
            <span>{t.scheduleAppointment}</span>
          </button>

          {/* 3. Escalate */}
          <button
            type="button"
            onClick={() => setProviderScreen("schedule_appointment")}
            id="reconciliation-escalate-btn"
            className="min-h-[48px] py-3 px-4 bg-amber-800 hover:bg-amber-700 active:scale-[0.98] text-white font-bold text-xs sm:text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <AlertOctagon className="w-4 h-4" />
            <span>{t.escalate}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
