"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { AlertCircle, UserCheck, Home, ArrowLeft, Clock } from "lucide-react";

export const RoutedToReviewScreen = () => {
  const { returnToHomeAndClearRun, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn text-center space-y-0">
      {/* Top Banner */}
      <div className="bg-gradient-to-b from-amber-50 to-white p-8 pb-4">
        <div className="w-20 h-20 rounded-full bg-amber-100 border-4 border-white shadow-lg flex items-center justify-center mx-auto mb-4 text-amber-800 animate-fadeIn">
          <AlertCircle className="w-10 h-10" />
        </div>

        <h1 className="font-heading text-2xl font-bold text-navy-800 mb-1.5 leading-snug">
          {t.routedToReviewTitle}
        </h1>
      </div>

      {/* Details Box */}
      <div className="p-6 space-y-6">
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 leading-relaxed text-left flex items-start gap-3">
          <UserCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
          <p>{t.routedToReviewDesc}</p>
        </div>

        <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200/60 flex items-center justify-between text-xs text-amber-900">
          <span className="flex items-center gap-1.5 font-medium">
            <Clock className="w-3.5 h-3.5" />
            <span>Status</span>
          </span>
          <span className="font-bold">Pending Clinical Queue</span>
        </div>

        {/* Return to Home button */}
        <button
          type="button"
          onClick={returnToHomeAndClearRun}
          id="routed-review-return-home-btn"
          className="w-full py-3.5 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <Home className="w-4 h-4" />
          <span>{t.finishBtn}</span>
        </button>
      </div>
    </div>
  );
};
