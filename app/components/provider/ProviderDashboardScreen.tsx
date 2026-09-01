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
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn py-2">
      {/* Header with Live Counters */}
      <div className="bg-navy-800 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-teal-500/10 rounded-full blur-2xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-teal-400 block mb-1">
              Dr. Sana Malik — City General Clinic
            </span>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-white">
              {t.providerDashboardTitle}
            </h1>
            <p className="text-xs text-slate-300 mt-1 max-w-md">
              {t.providerSubtitle}
            </p>
          </div>

          {/* Live Counters with Visible Transition Flash */}
          <div className="flex items-center gap-3">
            {/* Active Cases Counter */}
            <div
              key={`active-${activeCasesCount}`}
              className={`border rounded-xl p-3 px-4 text-center min-w-[120px] transition-all duration-500 animate-fadeIn ${
                activeCasesCount > 2
                  ? "bg-teal-950/80 border-teal-400 ring-2 ring-teal-400/30 shadow-lg shadow-teal-500/20"
                  : "bg-navy-700/80 border-slate-600/60"
              }`}
            >
              <span className="text-[10px] uppercase font-bold text-slate-300 block">
                {t.activeCasesLabel}
              </span>
              <div className="text-xl sm:text-2xl font-bold text-white font-sans mt-0.5 flex items-center justify-center gap-1">
                <span>{activeCasesCount}</span>
                {activeCasesCount > 2 && (
                  <span className="w-2 h-2 rounded-full bg-teal-400 animate-ping shrink-0" />
                )}
              </div>
              <span className="text-xs font-normal text-teal-300 block text-[10px]">
                {activeCasesSubtext || "Tracked"}
              </span>
            </div>

            {/* Urgent Cases Counter */}
            <div
              key={`urgent-${urgentCasesCount}`}
              className={`rounded-xl p-3 px-4 text-center min-w-[120px] transition-all duration-500 animate-fadeIn border ${
                urgentCasesCount > 0
                  ? "bg-red-950/90 border-red-500 text-white ring-2 ring-red-500/40 shadow-lg shadow-red-600/30"
                  : "bg-navy-700/80 border-slate-600/60 text-slate-300"
              }`}
            >
              <span className="text-[10px] uppercase font-bold block">
                {t.urgentCasesLabel}
              </span>
              <div className="text-xl sm:text-2xl font-bold font-sans mt-0.5 flex items-center justify-center gap-1">
                {urgentCasesCount > 0 ? (
                  <span className="text-red-300 flex items-center gap-1">
                    <AlertOctagon className="w-4 h-4 text-red-400 animate-pulse" />
                    <span>🔴 1 New Urgent Case</span>
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
      <div className="bg-gradient-to-r from-teal-900 via-navy-800 to-navy-900 rounded-2xl p-5 text-white border border-teal-500/30 shadow-md flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-xl bg-teal-700 text-white flex items-center justify-center shrink-0 shadow-sm">
            <ClipboardList className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-lg font-bold text-white">
                {t.reviewQueueTitle}
              </h2>
              {pendingQueueCount > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-amber-500 text-navy-900 text-[10px] font-extrabold">
                  {pendingQueueCount} Pending
                </span>
              )}
            </div>
            <p className="text-xs text-slate-300">
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
          className="w-full sm:w-auto px-5 py-2.5 bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold rounded-xl shadow-md transition-all shrink-0 flex items-center justify-center gap-2"
        >
          <span>{t.viewReviewQueueBtn}</span>
          <ChevronRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Patient Cohort List (2 Cols) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
              <Users className="w-4 h-4 text-teal-700" />
              <span>{t.patientListTitle}</span>
            </h3>
            <span className="text-xs text-slate-500">3 Assigned Patients</span>
          </div>

          <div className="space-y-2.5">
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
              className="p-3.5 rounded-xl border border-slate-200 hover:border-teal-600 hover:bg-slate-50/70 transition-all cursor-pointer flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="shrink-0">
                  {demoScenario === "emergency" && !isAliResolved ? (
                    <div className="w-7 h-7 rounded-lg bg-red-100 border border-red-300 text-red-700 flex items-center justify-center animate-pulse">
                      <AlertOctagon className="w-4 h-4" />
                    </div>
                  ) : demoScenario === "conflict" && !isAliResolved ? (
                    <div className="w-7 h-7 rounded-lg bg-amber-100 border border-amber-300 text-amber-800 flex items-center justify-center">
                      <AlertTriangle className="w-4 h-4" />
                    </div>
                  ) : (
                    <div className="w-7 h-7 rounded-lg bg-mutedGreen-100 border border-mutedGreen-800/30 text-mutedGreen-800 flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-navy-800">Ali Khan</span>
                    <span className="text-[10px] text-slate-500 font-medium">58y • T2D</span>
                  </div>
                  <span className="text-xs text-slate-500 block">
                    {demoScenario === "emergency" && !isAliResolved ? (
                      <span className="text-red-700 font-semibold">🔴 Critical: High-Risk Pattern Alerted</span>
                    ) : demoScenario === "conflict" && !isAliResolved ? (
                      <span className="text-amber-800 font-semibold">🟡 Discrepancy: Glucose 180 vs 140 mg/dL</span>
                    ) : (
                      <span className="text-mutedGreen-800 font-semibold">🟢 Stable Check-in Logged</span>
                    )}
                  </span>
                </div>
              </div>
              <ChevronRight className={`w-4 h-4 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
            </div>

            {/* Patient 2: Sara Ahmed (Static baseline) */}
            <div
              onClick={() => {
                setSelectedPatient("Sara Ahmed");
                setProviderScreen("patient_detail");
              }}
              id="patient-row-sara-ahmed"
              className="p-3.5 rounded-xl border border-slate-200 hover:border-teal-600 hover:bg-slate-50/70 transition-all cursor-pointer flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="shrink-0">
                  {isSaraResolved ? (
                    <div className="w-7 h-7 rounded-lg bg-mutedGreen-100 border border-mutedGreen-800/30 text-mutedGreen-800 flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                  ) : (
                    <div className="w-7 h-7 rounded-lg bg-amber-100 border border-amber-300 text-amber-800 flex items-center justify-center">
                      <AlertTriangle className="w-4 h-4" />
                    </div>
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-navy-800">Sara Ahmed</span>
                    <span className="text-[10px] text-slate-500 font-medium">62y • Hypertension</span>
                  </div>
                  <span className="text-xs text-slate-500 block">
                    {isSaraResolved ? (
                      <span className="text-mutedGreen-800 font-semibold">🟢 Follow-up complete</span>
                    ) : (
                      <span className="text-amber-800 font-semibold">🟡 Incomplete Check-in (Missing Meds)</span>
                    )}
                  </span>
                </div>
              </div>
              <ChevronRight className={`w-4 h-4 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
            </div>

            {/* Patient 3: Ahmed (Static baseline) */}
            <div
              onClick={() => {
                setSelectedPatient("Ahmed");
                setProviderScreen("patient_detail");
              }}
              id="patient-row-ahmed"
              className="p-3.5 rounded-xl border border-slate-200 hover:border-teal-600 hover:bg-slate-50/70 transition-all cursor-pointer flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-mutedGreen-100 border border-mutedGreen-800/30 text-mutedGreen-800 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-navy-800">Ahmed</span>
                    <span className="text-[10px] text-slate-500 font-medium">45y • T2D & HTN</span>
                  </div>
                  <span className="text-xs text-mutedGreen-800 font-semibold block">
                    🟢 Stable — Adherence 100%
                  </span>
                </div>
              </div>
              <ChevronRight className={`w-4 h-4 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
            </div>
          </div>
        </div>

        {/* Provider Notifications Bell Dropdown / List (1 Col) */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-3.5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h3 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
              <Bell className="w-4 h-4 text-teal-700" />
              <span>{t.notificationsTitle}</span>
            </h3>
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
              Live Feed
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            {demoScenario === "emergency" && !isAliResolved && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-900 space-y-1 animate-fadeIn">
                <div className="flex items-center gap-1.5 font-bold">
                  <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
                  <span>🔴 Urgent Case Escalation</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  New urgent case — Ali Khan, high-risk pattern detected.
                </p>
              </div>
            )}

            {demoScenario === "conflict" && !isAliResolved && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 space-y-1 animate-fadeIn">
                <div className="flex items-center gap-1.5 font-bold">
                  <span className="w-2 h-2 rounded-full bg-amber-600" />
                  <span>🟡 Reconciliation Conflict</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  Review required — Ali Khan, conflicting glucose readings.
                </p>
              </div>
            )}

            {!isSaraResolved && (
              <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200 text-amber-900 space-y-1">
                <div className="flex items-center gap-1.5 font-bold">
                  <span className="w-2 h-2 rounded-full bg-amber-600" />
                  <span>🟡 Incomplete Check-In</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  Review required — Sara Ahmed, incomplete check-in survey.
                </p>
              </div>
            )}

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-slate-600 space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-slate-700">
                <CheckCircle2 className="w-3.5 h-3.5 text-mutedGreen-800" />
                <span>FHIR Sync Active</span>
              </div>
              <p className="text-[11px]">
                City General EHR nightly reconciliation completed (140 records).
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
