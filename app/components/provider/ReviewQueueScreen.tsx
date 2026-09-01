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
    <div className="w-full max-w-4xl mx-auto space-y-5 animate-fadeIn py-2">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setProviderScreen("dashboard")}
              id="review-queue-back-btn"
              className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 transition-colors"
            >
              <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            </button>
            <h1 className="font-heading text-2xl font-bold text-navy-800">
              {t.reviewQueueTitle}
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {isUrdu
              ? "طبی تجزیے اور تضاد کے حل کے لیے کیسز کی فہرست۔"
              : "Review flagged cases requiring clinical clinician intervention or reconciliation."}
          </p>
        </div>

        <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 text-navy-800 border border-slate-200 self-start sm:self-auto">
          City General Triage Engine
        </span>
      </div>

      {/* Queue Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px] tracking-wider">
                <th className="py-3 px-4">{t.columnPatient}</th>
                <th className="py-3 px-4">{t.columnReason}</th>
                <th className="py-3 px-4">{t.columnConfidence}</th>
                <th className="py-3 px-4">{t.columnStatus}</th>
                <th className="py-3 px-4 text-right">{t.columnActions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {/* Row 1: Ali Khan (Present if Scenario is conflict or emergency) */}
              {demoScenario === "conflict" && (
                <tr
                  onClick={() => {
                    setSelectedPatient("Ali Khan");
                    setProviderScreen("reconciliation_alert");
                  }}
                  id="queue-row-ali-khan-conflict"
                  className="hover:bg-amber-50/50 cursor-pointer transition-colors"
                >
                  <td className="py-4 px-4">
                    <div className="font-bold text-navy-800 text-sm">Ali Khan</div>
                    <div className="text-[10px] text-slate-500">ID: PT-04821 • 58y M</div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="inline-flex items-center gap-1.5 font-semibold text-amber-800">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0" />
                      <span>Conflicting Glucose (180 vs 140 mg/dL)</span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">
                      Patient Check-in vs. FHIR EHR Record
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-900 font-bold text-[10px]">
                      Low
                    </span>
                  </td>
                  <td className="py-4 px-4">
                    {isAliResolved ? (
                      <span className="inline-flex items-center gap-1 text-mutedGreen-800 font-bold">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-amber-800 font-bold">
                        <Clock className="w-3.5 h-3.5" /> Pending Review
                      </span>
                    )}
                  </td>
                  <td className="py-4 px-4 text-right">
                    <button
                      type="button"
                      className="px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 text-white font-semibold text-[11px] shadow-xs inline-flex items-center gap-1"
                    >
                      <span>Review Discrepancy</span>
                      <ChevronRight className={`w-3 h-3 ${isUrdu ? "rotate-180" : ""}`} />
                    </button>
                  </td>
                </tr>
              )}

              {demoScenario === "emergency" && (
                <tr
                  onClick={() => {
                    setSelectedPatient("Ali Khan");
                    setProviderScreen("reconciliation_alert");
                  }}
                  id="queue-row-ali-khan-emergency"
                  className="hover:bg-red-50/50 bg-red-50/20 cursor-pointer transition-colors"
                >
                  <td className="py-4 px-4">
                    <div className="font-bold text-navy-800 text-sm">Ali Khan</div>
                    <div className="text-[10px] text-slate-500">ID: PT-04821 • 58y M</div>
                  </td>
                  <td className="py-4 px-4">
                    <div className="inline-flex items-center gap-1.5 font-bold text-red-700">
                      <AlertOctagon className="w-4 h-4 text-red-600 shrink-0" />
                      <span>🚨 Acute Escalation & Critical Pattern</span>
                    </div>
                    <div className="text-[10px] text-red-600 mt-0.5">
                      Emergency Alert Dispatched to Care Team
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <span className="px-2 py-0.5 rounded bg-red-100 text-red-900 font-bold text-[10px]">
                      High Urgency
                    </span>
                  </td>
                  <td className="py-4 px-4">
                    {isAliResolved ? (
                      <span className="inline-flex items-center gap-1 text-mutedGreen-800 font-bold">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-red-700 font-bold animate-pulse">
                        <Clock className="w-3.5 h-3.5" /> Urgent Action Required
                      </span>
                    )}
                  </td>
                  <td className="py-4 px-4 text-right">
                    <button
                      type="button"
                      className="px-3 py-1.5 rounded-lg bg-red-700 hover:bg-red-600 text-white font-semibold text-[11px] shadow-xs inline-flex items-center gap-1"
                    >
                      <span>Emergency Triage</span>
                      <ChevronRight className={`w-3 h-3 ${isUrdu ? "rotate-180" : ""}`} />
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
                className="hover:bg-slate-50 cursor-pointer transition-colors"
              >
                <td className="py-4 px-4">
                  <div className="font-bold text-navy-800 text-sm">Sara Ahmed</div>
                  <div className="text-[10px] text-slate-500">ID: PT-01934 • 62y F</div>
                </td>
                <td className="py-4 px-4">
                  <div className="inline-flex items-center gap-1.5 font-semibold text-slate-800">
                    <Clock className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>Incomplete check-in — skipped questions</span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Medication adherence response omitted
                  </div>
                </td>
                <td className="py-4 px-4">
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold text-[10px]">
                    Low
                  </span>
                </td>
                <td className="py-4 px-4">
                  {isSaraResolved ? (
                    <span className="inline-flex items-center gap-1 text-mutedGreen-800 font-bold">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Followed up
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-amber-800 font-semibold">
                      <Clock className="w-3.5 h-3.5" /> Pending Check
                    </span>
                  )}
                </td>
                <td className="py-4 px-4 text-right">
                  <button
                    type="button"
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-navy-800 font-semibold text-[11px] border border-slate-300 inline-flex items-center gap-1"
                  >
                    <span>View Case</span>
                    <ChevronRight className={`w-3 h-3 ${isUrdu ? "rotate-180" : ""}`} />
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
