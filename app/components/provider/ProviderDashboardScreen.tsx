"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import {
  Activity,
  AlertTriangle,
  AlertOctagon,
  Bell,
  Users,
  ChevronRight,
  ClipboardList,
  CheckCircle2,
  Clock,
  Search,
  ShieldCheck,
} from "lucide-react";

export const ProviderDashboardScreen = () => {
  const {
    setProviderScreen,
    setSelectedPatient,
    demoScenario,
    resolvedCases,
    acknowledgedPatients,
    t,
    isUrdu,
  } = useApp();

  const [showNotifications, setShowNotifications] = useState(true);

  // Compute live counters based on demoScenario
  const isAliResolved = resolvedCases.includes("Ali Khan");
  const isSaraResolved = resolvedCases.includes("Sara Ahmed");

  let activeCasesCount = 2; // Baseline: Ahmed + Sara Ahmed
  let activeCasesSubtext = "";
  let urgentCasesCount = 0;

  if (demoScenario === "conflict") {
    if (!isAliResolved) {
      activeCasesCount = 3;
      activeCasesSubtext = " — New: Ali Khan";
    }
  } else if (demoScenario === "emergency") {
    if (!isAliResolved) {
      activeCasesCount = 3;
      activeCasesSubtext = " — New: Ali Khan";
      urgentCasesCount = 1;
    }
  }

  // Pending queue items count
  const pendingQueueCount =
    (isSaraResolved ? 0 : 1) +
    (demoScenario !== "normal" && !isAliResolved ? 1 : 0);

  return (
    <div className="w-full max-w-6xl mx-auto space-y-7 animate-fadeIn py-2" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header with Live Counters */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden border border-teal-500/30">
        <div className="absolute -top-12 -right-12 w-56 h-56 bg-teal-400/15 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-teal-300 block mb-1.5">
              Dr. Sana Malik — City General Clinic
            </span>
            <h1 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-bold text-white tracking-tight">
              {t.providerDashboardTitle}
            </h1>
            <p className="text-sm text-slate-200 mt-1.5 max-w-lg leading-relaxed">
              {t.providerSubtitle}
            </p>
          </div>

          {/* Live Counters with Visible Transition Flash */}
          <div className="flex items-center gap-3.5">
            {/* Active Cases Counter */}
            <div
              key={`active-${activeCasesCount}`}
              className={`border rounded-2xl p-4 px-5 text-center min-w-[130px] transition-all duration-500 animate-fadeIn ${
                activeCasesCount > 2
                  ? "bg-teal-950/80 border-teal-400 ring-2 ring-teal-400/30 shadow-lg shadow-teal-500/20"
                  : "bg-navy-700/80 border-slate-600/60"
              }`}
            >
              <span className="text-xs uppercase font-bold text-slate-300 block">
                {t.activeCasesLabel}
              </span>
              <div className="text-2xl sm:text-3xl font-bold text-white font-sans mt-0.5 flex items-center justify-center gap-1.5">
                <span>{activeCasesCount}</span>
                {activeCasesCount > 2 && (
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-400 animate-ping shrink-0" />
                )}
              </div>
              <span className="text-xs font-medium text-teal-300 block">
                {activeCasesSubtext || "Tracked"}
              </span>
            </div>

            {/* Urgent Cases Counter */}
            <div
              key={`urgent-${urgentCasesCount}`}
              className={`rounded-2xl p-4 px-5 text-center min-w-[130px] transition-all duration-500 animate-fadeIn border ${
                urgentCasesCount > 0
                  ? "bg-emergencyRed-800/90 border-emergencyRed-700 text-white ring-2 ring-emergencyRed-800/40 shadow-lg shadow-red-700/30"
                  : "bg-navy-700/80 border-slate-600/60 text-slate-300"
              }`}
            >
              <span className="text-xs uppercase font-bold block">
                {t.urgentCasesLabel}
              </span>
              <div className="text-2xl sm:text-3xl font-bold font-sans mt-0.5 flex items-center justify-center gap-1">
                {urgentCasesCount > 0 ? (
                  <span className="text-red-100 flex items-center gap-1.5 text-base">
                    <AlertOctagon className="w-5 h-5 text-red-200 animate-pulse" />
                    <span>1 Urgent</span>
                  </span>
                ) : (
                  <span className="text-slate-200">0</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Review Queue CTA Banner */}
      <div className="bg-gradient-to-r from-teal-900 via-navy-800 to-navy-900 rounded-3xl p-6 text-white border border-teal-500/30 shadow-md flex flex-col sm:flex-row items-center justify-between gap-5">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-teal-700 text-white flex items-center justify-center shrink-0 shadow-sm">
            <ClipboardList className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="font-heading text-lg sm:text-xl font-bold text-white">
                {t.reviewQueueTitle}
              </h2>
              {pendingQueueCount > 0 && (
                <span className="px-2.5 py-0.5 rounded-full bg-amber-500 text-navy-900 text-xs font-bold">
                  {pendingQueueCount} Pending
                </span>
              )}
            </div>
            <p className="text-sm text-slate-200 mt-1 max-w-xl">
              {isUrdu
                ? "طبی تضادات، نامکمل چیک ان اور الرٹس کا تفصیلی جائزہ لیں۔"
                : "Evaluate flagged reconciliation discrepancies, incomplete surveys, and escalations."}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setProviderScreen("review_queue")}
          id="open-review-queue-btn"
          className="w-full sm:w-auto min-h-[48px] px-6 py-3 bg-teal-600 hover:bg-teal-500 text-white text-sm font-bold rounded-xl shadow-md transition-all shrink-0 flex items-center justify-center gap-2"
        >
          <span>{t.viewReviewQueueBtn}</span>
          <ChevronRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>
      </div>

      {/* Multi-Column Responsive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-7">
        {/* Patient Cohort List (2 Cols) */}
        <div className="lg:col-span-2 glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
            <h3 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
              <Users className="w-5 h-5 text-teal-700" />
              <span>{t.patientListTitle}</span>
            </h3>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              3 Assigned Patients
            </span>
          </div>

          <div className="space-y-3">
            {/* Patient 1: Ali Khan (Dynamic) */}
            <div
              onClick={() => {
                setSelectedPatient("Ali Khan");
                if (demoScenario === "conflict" && !isAliResolved) {
                  setProviderScreen("reconciliation_alert");
                } else {
                  setProviderScreen("patient_detail");
                }
              }}
              id="patient-row-ali-khan"
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 hover:border-teal-600 bg-white/90 hover:bg-teal-50/40 transition-all cursor-pointer flex items-center justify-between shadow-xs"
            >
              <div className="flex items-center gap-3.5">
                <div className="shrink-0">
                  {demoScenario === "emergency" && !isAliResolved ? (
                    <div className="w-9 h-9 rounded-xl bg-emergencyRed-100 border border-emergencyRed-700/40 text-emergencyRed-800 flex items-center justify-center animate-pulse">
                      <AlertOctagon className="w-5 h-5" />
                    </div>
                  ) : demoScenario === "conflict" && !isAliResolved ? (
                    <div className="w-9 h-9 rounded-xl bg-amber-100 border border-amber-300 text-amber-800 flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                  ) : (
                    <div className="w-9 h-9 rounded-xl bg-mutedGreen-100 border border-mutedGreen-800/30 text-mutedGreen-800 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-base text-navy-800">Ali Khan</span>
                    <span className="text-xs text-slate-500 font-medium">58y • Type 2 Diabetes</span>
                  </div>
                  <div className="text-sm mt-0.5">
                    {demoScenario === "emergency" && !isAliResolved ? (
                      <span className="text-emergencyRed-800 font-semibold flex items-center gap-1">
                        <AlertOctagon className="w-3.5 h-3.5 shrink-0" />
                        <span>Critical: High-Risk Pattern Alerted</span>
                      </span>
                    ) : demoScenario === "conflict" && !isAliResolved ? (
                      <span className="text-amber-800 font-semibold flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        <span>Discrepancy: Glucose 180 vs 140 mg/dL</span>
                      </span>
                    ) : (
                      <span className="text-mutedGreen-800 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                        <span>Stable Check-in Logged</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <ChevronRight className={`w-5 h-5 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
            </div>

            {/* Patient 2: Sara Ahmed (Static baseline) */}
            <div
              onClick={() => {
                setSelectedPatient("Sara Ahmed");
                setProviderScreen("patient_detail");
              }}
              id="patient-row-sara-ahmed"
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 hover:border-teal-600 bg-white/90 hover:bg-teal-50/40 transition-all cursor-pointer flex items-center justify-between shadow-xs"
            >
              <div className="flex items-center gap-3.5">
                <div className="shrink-0">
                  {isSaraResolved ? (
                    <div className="w-9 h-9 rounded-xl bg-mutedGreen-100 border border-mutedGreen-800/30 text-mutedGreen-800 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5" />
                    </div>
                  ) : (
                    <div className="w-9 h-9 rounded-xl bg-amber-100 border border-amber-300 text-amber-800 flex items-center justify-center">
                      <AlertTriangle className="w-5 h-5" />
                    </div>
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-base text-navy-800">Sara Ahmed</span>
                    <span className="text-xs text-slate-500 font-medium">62y • Hypertension</span>
                  </div>
                  <div className="text-sm mt-0.5">
                    {isSaraResolved ? (
                      <span className="text-mutedGreen-800 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                        <span>Follow-up complete</span>
                      </span>
                    ) : (
                      <span className="text-amber-800 font-semibold flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                        <span>Incomplete Check-in (Missing Meds)</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <ChevronRight className={`w-5 h-5 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
            </div>

            {/* Patient 3: Ahmed (Static baseline) */}
            <div
              onClick={() => {
                setSelectedPatient("Ahmed");
                setProviderScreen("patient_detail");
              }}
              id="patient-row-ahmed"
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 hover:border-teal-600 bg-white/90 hover:bg-teal-50/40 transition-all cursor-pointer flex items-center justify-between shadow-xs"
            >
              <div className="flex items-center gap-3.5">
                <div className="w-9 h-9 rounded-xl bg-mutedGreen-100 border border-mutedGreen-800/30 text-mutedGreen-800 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-base text-navy-800">Ahmed</span>
                    <span className="text-xs text-slate-500 font-medium">45y • T2D & HTN</span>
                  </div>
                  <div className="text-sm mt-0.5 text-mutedGreen-800 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                    <span>Stable — Adherence 100%</span>
                  </div>
                </div>
              </div>
              <ChevronRight className={`w-5 h-5 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
            </div>
          </div>
        </div>

        {/* Provider Notifications Bell Dropdown / List (1 Col) */}
        <div className="glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
            <h3 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
              <Bell className="w-5 h-5 text-teal-700" />
              <span>{t.notificationsTitle}</span>
            </h3>
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              Live Feed
            </span>
          </div>

          <div className="space-y-3 text-sm">
            {demoScenario === "emergency" && !isAliResolved && (
              <div className="p-4 rounded-2xl bg-emergencyRed-50 border border-emergencyRed-800/30 text-emergencyRed-800 space-y-1 animate-fadeIn">
                <div className="flex items-center gap-2 font-bold text-sm">
                  <AlertOctagon className="w-4 h-4 shrink-0 text-emergencyRed-800 animate-pulse" />
                  <span>Urgent Case Escalation</span>
                </div>
                <p className="text-xs leading-relaxed">
                  New urgent case — Ali Khan, high-risk pattern detected.
                </p>
              </div>
            )}

            {demoScenario === "conflict" && !isAliResolved && (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-amber-900 space-y-1 animate-fadeIn">
                <div className="flex items-center gap-2 font-bold text-sm">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-800" />
                  <span>Reconciliation Conflict</span>
                </div>
                <p className="text-xs leading-relaxed">
                  Review required — Ali Khan, conflicting glucose readings.
                </p>
              </div>
            )}

            {!isSaraResolved && (
              <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-300 text-amber-900 space-y-1">
                <div className="flex items-center gap-2 font-bold text-sm">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-800" />
                  <span>Incomplete Check-In</span>
                </div>
                <p className="text-xs leading-relaxed">
                  Review required — Sara Ahmed, incomplete check-in survey.
                </p>
              </div>
            )}

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 text-slate-700 space-y-1">
              <div className="flex items-center gap-2 font-semibold text-sm text-navy-800">
                <ShieldCheck className="w-4 h-4 text-teal-700 shrink-0" />
                <span>FHIR Sync Active</span>
              </div>
              <p className="text-xs text-slate-500">
                City General EHR nightly reconciliation completed (140 records).
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
