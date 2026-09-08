"use client";

import React from "react";
import { useApp } from "../../context/AppContext";
import {
  ClipboardList,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  ArrowLeft,
  ChevronRight,
  ShieldAlert,
  Clock,
  ShieldCheck,
} from "lucide-react";

export const ReviewQueueScreen = () => {
  const {
    setProviderScreen,
    setSelectedPatient,
    demoScenario,
    resolvedCases,
    t,
    isUrdu,
  } = useApp();

  const isAliResolved = resolvedCases.includes("Ali Khan");
  const isSaraResolved = resolvedCases.includes("Sara Ahmed");

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-fadeIn py-2" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setProviderScreen("dashboard")}
              id="review-queue-back-btn"
              className="w-11 h-11 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 flex items-center justify-center transition-colors shadow-xs"
            >
              <ArrowLeft className={`w-5 h-5 ${isUrdu ? "rotate-180" : ""}`} />
            </button>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
              {t.reviewQueueTitle}
            </h1>
          </div>
          <p className="text-sm text-slate-600 mt-1">
            {isUrdu
              ? "طبی تجزیے اور تضاد کے حل کے لیے کیسز کی فہرست۔"
              : "Review flagged cases requiring clinical clinician intervention or reconciliation."}
          </p>
        </div>

        <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-teal-50 text-teal-800 border border-teal-200 self-start sm:self-auto flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-teal-700" />
          <span>City General Triage Engine</span>
        </span>
      </div>

      {/* Queue Table (Soft Glass Elevation) */}
      <div className="glass-resting rounded-3xl shadow-sm overflow-hidden border border-slate-200/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-slate-50/90 border-b border-slate-200/80 text-slate-600 font-bold uppercase text-xs tracking-wider">
                <th className="py-3.5 px-5">{t.columnPatient}</th>
                <th className="py-3.5 px-5">{t.columnReason}</th>
                <th className="py-3.5 px-5">{t.columnConfidence}</th>
                <th className="py-3.5 px-5">{t.columnStatus}</th>
                <th className="py-3.5 px-5 text-right">{t.columnActions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {/* Row 1: Ali Khan (Present if Scenario is conflict) */}
              {demoScenario === "conflict" && (
                <tr
                  onClick={() => {
                    setSelectedPatient("Ali Khan");
                    setProviderScreen("reconciliation_alert");
                  }}
                  id="queue-row-ali-khan-conflict"
                  className="hover:bg-amber-50/60 bg-white/70 cursor-pointer transition-colors"
                >
                  <td className="py-4.5 px-5">
                    <div className="font-bold text-navy-800 text-sm">Ali Khan</div>
                    <div className="text-xs text-slate-500">ID: PT-04821 • 58y M</div>
                  </td>
                  <td className="py-4.5 px-5">
                    <div className="inline-flex items-center gap-1.5 font-semibold text-amber-800 text-sm">
                      <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
                      <span>Conflicting Glucose (180 vs 140 mg/dL)</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      Patient Check-in vs. FHIR EHR Record
                    </div>
                  </td>
                  <td className="py-4.5 px-5">
                    <span className="px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 font-bold text-xs">
                      Low
                    </span>
                  </td>
                  <td className="py-4.5 px-5">
                    {isAliResolved ? (
                      <span className="inline-flex items-center gap-1.5 text-mutedGreen-800 font-bold text-xs">
                        <CheckCircle2 className="w-4 h-4 text-mutedGreen-800" /> Resolved
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-amber-800 font-bold text-xs">
                        <Clock className="w-4 h-4 text-amber-800" /> Pending Review
                      </span>
                    )}
                  </td>
                  <td className="py-4.5 px-5 text-right">
                    <button
                      type="button"
                      className="min-h-[40px] px-4 py-2 rounded-xl bg-navy-800 hover:bg-navy-900 text-white font-semibold text-xs shadow-xs inline-flex items-center gap-1.5"
                    >
                      <span>Review Discrepancy</span>
                      <ChevronRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                    </button>
                  </td>
                </tr>
              )}

              {/* Row 1 Alternative: Ali Khan Emergency */}
              {demoScenario === "emergency" && (
                <tr
                  onClick={() => {
                    setSelectedPatient("Ali Khan");
                    setProviderScreen("reconciliation_alert");
                  }}
                  id="queue-row-ali-khan-emergency"
                  className="hover:bg-emergencyRed-50/60 bg-emergencyRed-50/30 cursor-pointer transition-colors"
                >
                  <td className="py-4.5 px-5">
                    <div className="font-bold text-navy-800 text-sm">Ali Khan</div>
                    <div className="text-xs text-slate-500">ID: PT-04821 • 58y M</div>
                  </td>
                  <td className="py-4.5 px-5">
                    <div className="inline-flex items-center gap-1.5 font-bold text-emergencyRed-800 text-sm">
                      <AlertOctagon className="w-4 h-4 text-emergencyRed-800 shrink-0 animate-pulse" />
                      <span>Acute Escalation & Critical Pattern</span>
                    </div>
                    <div className="text-xs text-emergencyRed-800/80 mt-0.5">
                      Emergency Alert Dispatched to Care Team
                    </div>
                  </td>
                  <td className="py-4.5 px-5">
                    <span className="px-2.5 py-1 rounded-full bg-emergencyRed-100 text-emergencyRed-800 font-bold text-xs">
                      High Urgency
                    </span>
                  </td>
                  <td className="py-4.5 px-5">
                    {isAliResolved ? (
                      <span className="inline-flex items-center gap-1.5 text-mutedGreen-800 font-bold text-xs">
                        <CheckCircle2 className="w-4 h-4 text-mutedGreen-800" /> Resolved
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-emergencyRed-800 font-bold text-xs animate-pulse">
                        <Clock className="w-4 h-4" /> Urgent Action Required
                      </span>
                    )}
                  </td>
                  <td className="py-4.5 px-5 text-right">
                    <button
                      type="button"
                      className="min-h-[40px] px-4 py-2 rounded-xl bg-emergencyRed-800 hover:bg-emergencyRed-700 text-white font-semibold text-xs shadow-xs inline-flex items-center gap-1.5"
                    >
                      <span>Emergency Triage</span>
                      <ChevronRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                    </button>
                  </td>
                </tr>
              )}

              {/* Row 2: Sara Ahmed (Always present static baseline) */}
              <tr
                onClick={() => {
                  setSelectedPatient("Sara Ahmed");
                  setProviderScreen("patient_detail");
                }}
                id="queue-row-sara-ahmed"
                className="hover:bg-slate-50 bg-white/70 cursor-pointer transition-colors"
              >
                <td className="py-4.5 px-5">
                  <div className="font-bold text-navy-800 text-sm">Sara Ahmed</div>
                  <div className="text-xs text-slate-500">ID: PT-01934 • 62y F</div>
                </td>
                <td className="py-4.5 px-5">
                  <div className="inline-flex items-center gap-1.5 font-semibold text-slate-800 text-sm">
                    <Clock className="w-4 h-4 text-amber-700 shrink-0" />
                    <span>Incomplete check-in — skipped questions</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    Medication adherence response omitted
                  </div>
                </td>
                <td className="py-4.5 px-5">
                  <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-semibold text-xs">
                    Low
                  </span>
                </td>
                <td className="py-4.5 px-5">
                  {isSaraResolved ? (
                    <span className="inline-flex items-center gap-1.5 text-mutedGreen-800 font-bold text-xs">
                      <CheckCircle2 className="w-4 h-4 text-mutedGreen-800" /> Followed up
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-amber-800 font-semibold text-xs">
                      <Clock className="w-4 h-4 text-amber-800" /> Pending Check
                    </span>
                  )}
                </td>
                <td className="py-4.5 px-5 text-right">
                  <button
                    type="button"
                    className="min-h-[40px] px-4 py-2 rounded-xl bg-white hover:bg-slate-100 text-navy-800 font-semibold text-xs border border-slate-300 inline-flex items-center gap-1.5 shadow-xs"
                  >
                    <span>View Case</span>
                    <ChevronRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
