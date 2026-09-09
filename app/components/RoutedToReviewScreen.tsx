"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { AlertCircle, UserCheck, Home, ArrowLeft, Clock, ShieldCheck, Calendar, CheckCircle2 } from "lucide-react";

export const RoutedToReviewScreen = () => {
  const { returnToHomeAndClearRun, appointment, setAppointment, t, isUrdu } = useApp();
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

  return (
    <div className="w-full max-w-lg mx-auto surface-raised rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn text-center space-y-0" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Top Banner */}
      <div className="bg-gradient-to-b from-amber-50 to-white p-8 pb-4">
        <div className="w-20 h-20 rounded-full bg-amber-100 border-4 border-white shadow-md flex items-center justify-center mx-auto mb-4 text-amber-800 animate-fadeIn">
          <AlertCircle className="w-10 h-10" />
        </div>

        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-navy-800 mb-1.5 leading-snug">
          {t.routedToReviewTitle}
        </h1>
      </div>

      {/* Details Box */}
      <div className="p-6 sm:p-7 space-y-5">
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-sm text-slate-700 leading-relaxed text-left flex items-start gap-3.5">
          <UserCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
          <p>{t.routedToReviewDesc}</p>
        </div>

        <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 flex items-center justify-between text-sm text-amber-900">
          <span className="flex items-center gap-2 font-medium">
            <Clock className="w-4 h-4 text-amber-800" />
            <span>Triage Status</span>
          </span>
          <span className="font-bold">Pending Provider Review</span>
        </div>

        {/* Request Follow-Up Appointment CTA */}
        {requestedLocal ? (
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
