"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { AlertCircle, UserCheck, Home, ArrowLeft, Clock, ShieldCheck, Calendar, CheckCircle2, Pill, AlertTriangle, ShieldAlert } from "lucide-react";
import { describeMedicationItem } from "../lib/presentation";

export const RoutedToReviewScreen = () => {
  const { returnToHomeAndClearRun, appointment, setAppointment, isLiveMode, liveCheckinResult, checkIn, t, isUrdu } = useApp();
  const [requestedLocal, setRequestedLocal] = useState(appointment.status === "Requested");

  const handleRequestFollowUp = () => {
    setAppointment({
      isBooked: true,
      slot: "Next available — Thu, 10:30 AM",
      reason: "Patient-requested: flagged for clinical review",
      provider: "Dr. Sana Malik",
      status: "Requested",
      bookedAt: new Date().toISOString(),
    });
    setRequestedLocal(true);
  };

  const isLowConfidence =
    (isLiveMode && liveCheckinResult?.intakes?.[0]?.confidence_label?.toLowerCase() === "low") ||
    checkIn?.lowConfidence;

  const headline = isLiveMode ? t.routedToReviewHeadline : t.routedToReviewTitle;
  const description = isLiveMode ? t.routedToReviewExplanation : t.routedToReviewDesc;

  const medComparisons = liveCheckinResult?.reconciliation?.medication_comparisons || [];
  const medVerifications = liveCheckinResult?.verification?.medication_verifications || [];
  const flaggedMeds = isLiveMode
    ? medComparisons.map((c: any) => {
        const v = medVerifications.find((ver: any) => ver.medication_name === c.medication_name);
        return {
          desc: describeMedicationItem(c, v),
          comparison: c,
          verification: v,
        };
      })
    : [];

  return (
    <div className="w-full max-w-lg mx-auto surface-raised rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn text-center space-y-0" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Top Banner */}
      <div className="bg-gradient-to-b from-amber-50 to-white p-8 pb-4">
        <div className="w-20 h-20 rounded-full bg-amber-100 border-4 border-white shadow-md flex items-center justify-center mx-auto mb-4 text-amber-800 animate-fadeIn">
          <AlertCircle className="w-10 h-10" />
        </div>

        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-navy-800 mb-1.5 leading-snug">
          {headline}
        </h1>

        {isLowConfidence && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-semibold border border-amber-300 mt-2">
            <AlertCircle className="w-3.5 h-3.5 text-amber-700" />
            <span>{t.confidenceLowChip}</span>
          </div>
        )}
      </div>

      {/* Details Box */}
      <div className="p-6 sm:p-7 space-y-5">
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-sm text-slate-700 leading-relaxed text-left flex items-start gap-3.5">
          <UserCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
          <p>{description}</p>
        </div>

        {/* Flagged Medication Review Items */}
        {isLiveMode && flaggedMeds.length > 0 && (
          <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-300 text-left space-y-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-950 block">
              {isUrdu ? "جائزے کے لیے بھیجی گئی ادویات:" : "Medications Flagged for Review:"}
            </span>
            <div className="space-y-2">
              {flaggedMeds.map((m, idx) => {
                const isHigh = m.desc.severity === "high";
                return (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border text-xs space-y-1 ${
                      isHigh
                        ? "bg-red-50 border-emergencyRed-400 text-emergencyRed-950 shadow-2xs ring-1 ring-emergencyRed-300"
                        : "bg-white border-amber-200 text-slate-800"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold flex items-center gap-1.5">
                        <Pill className={`w-3.5 h-3.5 ${isHigh ? "text-emergencyRed-700" : "text-amber-700"}`} />
                        {m.desc.title}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${
                          isHigh
                            ? "bg-emergencyRed-100 text-emergencyRed-900 border border-emergencyRed-300 font-extrabold"
                            : "bg-amber-100 text-amber-900 border border-amber-300"
                        }`}
                      >
                        {isHigh ? (
                          <AlertTriangle className="w-3 h-3 text-emergencyRed-700" />
                        ) : (
                          <ShieldAlert className="w-3 h-3 text-amber-700" />
                        )}
                        <span>{m.desc.severity.toUpperCase()}</span>
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-600 flex items-center justify-between">
                      <span>{m.desc.recordText}</span>
                      <span className="font-semibold text-navy-800">{m.desc.todayText}</span>
                    </div>
                    <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 text-[11px]">
                      <span className={`font-semibold ${isHigh ? "text-emergencyRed-900 font-bold" : "text-amber-900"}`}>
                        {m.desc.reason}
                      </span>
                      <span className="text-[10px] font-bold text-slate-500">
                        Needs clinician review
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 flex items-center justify-between text-sm text-amber-900">
          <span className="flex items-center gap-2 font-medium">
            <Clock className="w-4 h-4 text-amber-800" />
            <span>Triage Status</span>
          </span>
          <span className="font-bold">Pending Provider Review</span>
        </div>

        {/* Request Follow-Up Appointment CTA - Mock Mode Only */}
        {!isLiveMode && (
          requestedLocal ? (
            <div className="p-4 rounded-2xl bg-mutedGreen-50 border border-mutedGreen-800/30 text-mutedGreen-900 text-sm font-semibold flex items-center justify-center gap-2.5 shadow-2xs animate-fadeIn">
              <CheckCircle2 className="w-5 h-5 text-mutedGreen-800 shrink-0" />
              <span>Follow-up consultation requested (Thu, 10:30 AM). Forwarded to Dr. Sana Malik.</span>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleRequestFollowUp}
              id="request-followup-appointment-btn"
              className="w-full min-h-[48px] py-3.5 px-4 bg-amber-600 hover:bg-amber-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
            >
              <Calendar className="w-4 h-4" />
              <span>Request Follow-Up Appointment</span>
            </button>
          )
        )}

        {/* Return to Home button */}
        <button
          type="button"
          onClick={returnToHomeAndClearRun}
          id="routed-review-return-home-btn"
          className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <Home className="w-4 h-4" />
          <span>{t.finishBtn}</span>
        </button>
      </div>
    </div>
  );
};
