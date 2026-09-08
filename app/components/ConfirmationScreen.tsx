"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { CheckCircle2, Home, CalendarCheck, ShieldCheck, ArrowRight, Activity } from "lucide-react";

export const ConfirmationScreen = () => {
  const { setScreen, returnToHomeAndClearRun, checkIn, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-lg mx-auto surface-raised rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn text-center" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Top Banner */}
      <div className="bg-gradient-to-b from-mutedGreen-50 to-white p-8 pb-4">
        <div className="w-20 h-20 rounded-full bg-mutedGreen-100 border-4 border-white shadow-md flex items-center justify-center mx-auto mb-4 text-mutedGreen-800 animate-fadeIn">
          <CheckCircle2 className="w-10 h-10" />
        </div>

        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-navy-800 mb-1">
          {t.confirmationTitle}
        </h1>

        <p className="text-sm font-semibold text-mutedGreen-800">
          {t.confirmationSubtitle}
        </p>
      </div>

      {/* Details Box */}
      <div className="p-6 sm:p-7 space-y-5">
        <p className="text-sm text-slate-600 leading-relaxed max-w-sm mx-auto">
          {t.confirmationMessage}
        </p>

        {/* Submission Meta */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 text-sm text-slate-600 space-y-2 text-left">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-medium text-slate-600">
              <CalendarCheck className="w-4 h-4 text-teal-700" />
              <span>{t.submittedAt}</span>
            </span>
            <span className="font-bold text-navy-800">
              {checkIn.submittedAt || "Just now"}
            </span>
          </div>
          <div className="flex items-center justify-between pt-2 border-t border-slate-200/80">
            <span className="flex items-center gap-1.5 text-slate-600">
              <ShieldCheck className="w-4 h-4 text-teal-700" />
              <span>Status</span>
            </span>
            <span className="font-bold text-mutedGreen-800 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Logged & Encrypted
            </span>
          </div>
        </div>

        {/* Primary Action: View Results */}
        <button
          type="button"
          onClick={() => setScreen("processing")}
          id="view-my-results-btn"
          className="w-full min-h-[48px] py-3.5 px-5 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <Activity className="w-4 h-4" />
          <span>{t.viewResultsBtn}</span>
          <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>

        {/* Secondary Return Button */}
        <button
          type="button"
          onClick={returnToHomeAndClearRun}
          id="finish-return-home-btn"
          className="w-full min-h-[44px] py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition-all flex items-center justify-center gap-2"
        >
          <Home className="w-4 h-4" />
          <span>{t.finishBtn}</span>
        </button>
      </div>
    </div>
  );
};
