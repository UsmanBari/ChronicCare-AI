"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { AlertOctagon, PhoneCall, ShieldAlert, Home, BellRing, HeartPulse, CheckCircle2 } from "lucide-react";

export const EmergencyScreen = () => {
  const { returnToHomeAndClearRun, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-lg mx-auto surface-raised rounded-3xl border-2 border-emergencyRed-800/80 shadow-2xl overflow-hidden animate-fadeIn space-y-0" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Clinically Responsible High-Alert Header */}
      <div className="bg-emergencyRed-800 p-7 text-white text-center relative overflow-hidden">
        <div className="w-16 h-16 rounded-2xl bg-white text-emergencyRed-800 flex items-center justify-center mx-auto mb-3.5 shadow-xl">
          <AlertOctagon className="w-10 h-10 stroke-[2.5]" />
        </div>

        <span className="text-xs font-bold uppercase tracking-widest px-3.5 py-1 rounded-full bg-emergencyRed-900/60 text-red-100 mb-2 inline-block border border-emergencyRed-700">
          {isUrdu ? "فوری طبی الرٹ" : "CRITICAL CLINICAL ALERT"}
        </span>

        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1">
          {t.emergencyDetectedTitle}
        </h1>
      </div>

      <div className="p-6 sm:p-7 space-y-6">
        {/* Prompt Medical Action Guidance */}
        <div className="p-5 rounded-2xl bg-emergencyRed-50 border border-emergencyRed-800/30 text-center space-y-2">
          <p className="text-base font-bold text-emergencyRed-800 leading-snug">
            {t.emergencyGuidanceText}
          </p>
          <p className="text-sm text-emergencyRed-800/90 leading-relaxed">
            {isUrdu
              ? "اگر آپ کو شدید بے چینی، سانس لینے میں دشواری یا بے ہوشی محسوس ہو رہی ہے تو فوری 1122 یا ایمرجنسی سروسز پر رابطہ کریں۔"
              : "If you are experiencing severe shortness of breath, acute chest distress, or sudden weakness, contact emergency services (911 / 1122) immediately."}
          </p>
        </div>

        {/* Care Team Alerted Notification Receipt */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-center gap-3.5 text-sm text-slate-700">
          <div className="w-10 h-10 rounded-xl bg-teal-700 text-white flex items-center justify-center shrink-0 shadow-xs">
            <BellRing className="w-5 h-5 text-teal-200" />
          </div>
          <div>
            <p className="font-bold text-navy-800">{t.emergencyAlertedText}</p>
            <p className="text-xs text-slate-500 mt-0.5">
              {isUrdu ? "طبی نگہداشت ٹیم کو خودکار فوری پیغام بھیج دیا گیا ہے۔" : "Priority clinical notification dispatched to on-call care team."}
            </p>
          </div>
        </div>

        {/* Emergency Services Shortcut Pill */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs text-slate-600">
          <span className="font-medium">Direct Hotline Dispatch:</span>
          <span className="font-bold text-emergencyRed-800 flex items-center gap-1">
            <PhoneCall className="w-3.5 h-3.5" /> 911 / 1122
          </span>
        </div>

        {/* Return to Home button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={returnToHomeAndClearRun}
            id="emergency-return-home-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <Home className="w-4 h-4" />
            <span>{t.finishBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
