"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { AlertOctagon, PhoneCall, ShieldAlert, Home, BellRing, HeartPulse } from "lucide-react";

export const EmergencyScreen = () => {
  const { returnToHomeAndClearRun, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-2xl border-2 border-red-300 shadow-2xl overflow-hidden animate-fadeIn space-y-0">
      {/* High-Alert Header Banner */}
      <div className="bg-red-700 p-7 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-white/10 rounded-full blur-xl pointer-events-none" />
        
        {/* Pulsing Emergency Alert Icon */}
        <div className="w-20 h-20 rounded-2xl bg-white text-red-700 flex items-center justify-center mx-auto mb-4 shadow-xl border-2 border-red-100 animate-pulse">
          <AlertOctagon className="w-12 h-12 stroke-[2.5]" />
        </div>

        <span className="text-[10px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full bg-red-900/60 text-red-100 mb-2 inline-block">
          CRITICAL CLINICAL ALERT
        </span>

        <h1 className="font-heading text-2xl font-bold text-white mb-1">
          {t.emergencyDetectedTitle}
        </h1>
      </div>

      <div className="p-6 space-y-5">
        {/* Prompt Medical Action Guidance */}
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-center space-y-2">
          <p className="text-sm font-bold text-red-900 leading-snug">
            {t.emergencyGuidanceText}
          </p>
          <p className="text-xs text-red-700">
            {isUrdu
              ? "اگر آپ کو شدید بے چینی، سانس لینے میں دشواری یا بے ہوشی محسوس ہو رہی ہے تو فوری 1122 یا ایمرجنسی سروسز پر رابطہ کریں۔"
              : "If you are experiencing severe shortness of breath, confusion, or acute distress, call 911 or local emergency services immediately."}
          </p>
        </div>

        {/* Provider Alerted Confirmation */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center gap-3 text-xs text-slate-700">
          <div className="w-8 h-8 rounded-lg bg-teal-700 text-white flex items-center justify-center shrink-0">
            <BellRing className="w-4 h-4" />
          </div>
          <div>
            <p className="font-bold text-navy-800">{t.emergencyAlertedText}</p>
            <p className="text-[11px] text-slate-500">
              {isUrdu ? "طبی نگہداشت ٹیم کو خودکار فوری پیغام بھیج دیا گیا ہے۔" : "Priority clinical notification dispatched to on-call care team."}
            </p>
          </div>
        </div>

        {/* Return to Home button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={returnToHomeAndClearRun}
            id="emergency-return-home-btn"
            className="w-full py-3.5 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <Home className="w-4 h-4" />
            <span>{t.finishBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
