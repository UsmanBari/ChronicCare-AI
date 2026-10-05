"use client";

import React, { useState, useEffect, useCallback } from "react";
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
  Calendar,
  Loader2,
  Flame,
  RotateCw,
  Info,
} from "lucide-react";
import { api, ReviewQueueItemResponse } from "../../lib/api";

export const ReviewQueueScreen = () => {
  const {
    setProviderScreen,
    setSelectedPatient,
    isLiveMode,
    demoScenario,
    resolvedCases,
    appointment,
    setAppointment,
    t,
    isUrdu,
  } = useApp();

  const [activeTab, setActiveTab] = useState<"open" | "escalated" | "resolved">("open");
  const [liveQueue, setLiveQueue] = useState<ReviewQueueItemResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(isLiveMode);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const fetchQueue = useCallback(
    async (status: "open" | "escalated" | "resolved" = activeTab) => {
      if (!isLiveMode) return;
      setIsLoading(true);
      try {
        const items = await api.getProviderReviewQueue(status);
        // Sort emergency first, then overdue, then created_at desc
        const sorted = [...items].sort((a, b) => {
          if (a.emergency !== b.emergency) return a.emergency ? -1 : 1;
          if (a.overdue !== b.overdue) return a.overdue ? -1 : 1;
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });
        setLiveQueue(sorted);
        setLastUpdated(
          new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })
        );
      } catch {
        // Silent error fallback
      } finally {
        setIsLoading(false);
      }
    },
    [activeTab, isLiveMode]
  );

  // Initial load and tab changes
  useEffect(() => {
    if (!isLiveMode) return;
    fetchQueue(activeTab);
  }, [activeTab, fetchQueue, isLiveMode]);

  // Auto-refresh every 20 seconds (P1 requirement)
  useEffect(() => {
    if (!isLiveMode) return;
    const interval = setInterval(() => {
      fetchQueue(activeTab);
    }, 20000);
    return () => clearInterval(interval);
  }, [activeTab, fetchQueue, isLiveMode]);

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

        {/* Header Controls: Last Updated & Refresh */}
        <div className="flex items-center gap-3 self-start sm:self-auto">
          {isLiveMode && (
            <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
              {lastUpdated && <span>Last updated {lastUpdated}</span>}
              <button
                type="button"
                onClick={() => fetchQueue(activeTab)}
                disabled={isLoading}
                id="review-queue-refresh-btn"
                title="Refresh review queue"
                className="p-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 transition-colors shadow-2xs"
              >
                <RotateCw className={`w-4 h-4 ${isLoading ? "animate-spin text-teal-700" : ""}`} />
              </button>
            </div>
          )}
          <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-teal-50 text-teal-800 border border-teal-200 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-teal-700" />
            <span>City General Triage Engine</span>
          </span>
        </div>
      </div>

      {/* Status Tabs: Open, Escalated, Resolved */}
      {isLiveMode && (
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
          <button
            type="button"
            onClick={() => setActiveTab("open")}
            id="tab-queue-open"
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === "open"
                ? "bg-navy-800 text-white shadow-xs"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Open Cases
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("escalated")}
            id="tab-queue-escalated"
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === "escalated"
                ? "bg-amber-800 text-white shadow-xs"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Escalated Cases
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("resolved")}
            id="tab-queue-resolved"
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === "resolved"
                ? "bg-mutedGreen-800 text-white shadow-xs"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Resolved Cases
          </button>
        </div>
      )}

      {/* Patient-Requested Follow-Up Alert Banner */}
      {appointment.isBooked && appointment.status === "Requested" && (
        <div className="p-5 rounded-3xl bg-amber-50 border-2 border-amber-300 shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fadeIn">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-2xl bg-amber-200 text-amber-900 flex items-center justify-center shrink-0 shadow-2xs">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-navy-800 text-sm">Ali Khan (PT-04821)</span>
                <span className="px-2.5 py-0.5 rounded-full bg-amber-200 text-amber-950 font-bold text-[10px] uppercase tracking-wider">
                  Patient-Requested Follow-Up
                </span>
              </div>
              <p className="text-xs text-amber-900 mt-1 leading-relaxed">
                Patient requested consultation slot ({appointment.slot}) following flagged check-in discrepancy.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
            <button
              type="button"
              onClick={() => {
                setAppointment((prev) => ({ ...prev, status: "Confirmed" }));
              }}
              id="confirm-requested-appointment-btn"
              className="min-h-[40px] px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs rounded-xl shadow-xs transition-all flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Confirm Appointment</span>
            </button>
          </div>
        </div>
      )}

      {/* Queue Table */}
      <div className="glass-resting rounded-3xl shadow-sm overflow-hidden border border-slate-200/80">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-slate-50/90 border-b border-slate-200/80 text-slate-600 font-bold uppercase text-xs tracking-wider">
                <th className="py-3.5 px-5">{t.columnPatient}</th>
                <th className="py-3.5 px-5">{t.columnReason}</th>
                <th className="py-3.5 px-5">SEVERITY</th>
                <th className="py-3.5 px-5">{t.columnStatus}</th>
                <th className="py-3.5 px-5 text-right">{t.columnActions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {/* LIVE QUEUE ROWS */}
              {isLiveMode ? (
                isLoading ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      <div className="inline-flex items-center gap-2 text-xs font-semibold">
                        <Loader2 className="w-4 h-4 animate-spin text-teal-700" />
                        <span>Loading active review queue...</span>
                      </div>
                    </td>
                  </tr>
                ) : liveQueue.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500 text-xs">
                      No {activeTab} cases in clinical review queue.
                    </td>
                  </tr>
                ) : (
                  liveQueue.map((item) => {
                    const flaggedCount = item.counts?.conflict || item.counts?.flagged || 1;
                    const reasonText = item.emergency
                      ? "Emergency Clinical Escalation"
                      : `${flaggedCount} flagged item${flaggedCount === 1 ? "" : "s"}`;
                    return (
                      <tr
                        key={item.checkin_id}
                        onClick={() => {
                          setSelectedPatient(item.checkin_id);
                          setProviderScreen("reconciliation_alert");
                        }}
                        id={`queue-row-${item.checkin_id}`}
                        className={`cursor-pointer transition-colors ${
                          item.emergency
                            ? "bg-emergencyRed-50/30 hover:bg-emergencyRed-50/60"
                            : item.overdue
                            ? "bg-amber-50/30 hover:bg-amber-50/60"
                            : "bg-white/70 hover:bg-slate-50"
                        }`}
                      >
                        <td className="py-4.5 px-5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-navy-800 text-sm">{item.patient_display}</span>
                            {item.triage_level && (
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1 ${
                                  item.triage_level === "emergency"
                                    ? "bg-emergencyRed-100 text-emergencyRed-800 border border-emergencyRed-300"
                                    : item.triage_level === "urgent"
                                    ? "bg-amber-100 text-amber-900 border border-amber-300"
                                    : "bg-teal-100 text-teal-900 border border-teal-300"
                                }`}
                              >
                                {item.triage_level === "emergency" ? (
                                  <AlertOctagon className="w-3 h-3 text-emergencyRed-700" />
                                ) : item.triage_level === "urgent" ? (
                                  <AlertTriangle className="w-3 h-3 text-amber-700" />
                                ) : (
                                  <Info className="w-3 h-3 text-teal-700" />
                                )}
                                <span>
                                  {item.triage_level === "emergency"
                                    ? isUrdu ? "ایمرجنسی" : "Emergency"
                                    : item.triage_level === "urgent"
                                    ? isUrdu ? "ارجنٹ" : "Urgent"
                                    : isUrdu ? "جائزہ" : "Review"}
                                </span>
                              </span>
                            )}
                            {item.emergency && !item.triage_level && (
                              <span className="px-2 py-0.5 rounded bg-emergencyRed-100 text-emergencyRed-800 text-[10px] font-bold uppercase tracking-wider">
                                {isUrdu ? "ایمرجنسی" : "Emergency"}
                              </span>
                            )}
                            {item.overdue && (
                              <span className="px-2 py-0.5 rounded bg-amber-200 text-amber-950 text-[10px] font-bold uppercase tracking-wider">
                                {isUrdu ? "تاخیر شدہ" : "Overdue"}
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-slate-500 font-mono">
                            ID: {item.checkin_id.slice(0, 8)}... • Mode: {item.mode}
                          </div>
                        </td>
                        <td className="py-4.5 px-5">
                          <div className="inline-flex items-center gap-1.5 font-semibold text-slate-800 text-sm">
                            {item.emergency ? (
                              <AlertOctagon className="w-4 h-4 text-emergencyRed-700 shrink-0" />
                            ) : (
                              <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
                            )}
                            <span>{reasonText}</span>
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5">
                            Received: {new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </div>
                        </td>
                        <td className="py-4.5 px-5">
                          <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase ${
                            item.emergency || item.max_severity === "critical"
                              ? "bg-emergencyRed-100 text-emergencyRed-800"
                              : item.max_severity === "high"
                              ? "bg-amber-100 text-amber-900"
                              : "bg-slate-100 text-slate-700"
                          }`}>
                            {item.emergency ? "CRITICAL" : item.max_severity || "Review"}
                          </span>
                        </td>
                        <td className="py-4.5 px-5">
                          <span className="inline-flex items-center gap-1.5 text-amber-800 font-bold text-xs">
                            <Clock className="w-4 h-4 text-amber-800" /> Pending Review
                          </span>
                        </td>
                        <td className="py-4.5 px-5 text-right">
                          <button
                            type="button"
                            className="min-h-[40px] px-4 py-2 rounded-xl bg-navy-800 hover:bg-navy-900 text-white font-semibold text-xs shadow-xs inline-flex items-center gap-1.5"
                          >
                            <span>Review</span>
                            <ChevronRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )
              ) : (
                /* MOCK QUEUE ROWS */
                <>
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
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
