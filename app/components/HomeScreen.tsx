"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { Calendar, Clock, Activity, Pill, ArrowRight, BellRing, Sparkles } from "lucide-react";

export const HomeScreen = () => {
  const { setScreen, profile, connectionMode, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-lg mx-auto space-y-5 animate-fadeIn">
      {/* Welcome Greeting */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-navy-800">
            {t.homeGreeting}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {t.homeSubtitle}
          </p>
        </div>
      </div>

      {/* PROMINENT REMINDER CARD */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-900 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden border border-teal-600/30">
        <div className="absolute -top-12 -right-12 w-36 h-36 bg-teal-500/15 rounded-full blur-2xl pointer-events-none" />
        <div className="flex items-start gap-4 relative z-10">
          <div className="w-12 h-12 rounded-xl bg-teal-700/80 border border-teal-400/30 flex items-center justify-center shrink-0 text-white shadow-md">
            <BellRing className="w-6 h-6 text-teal-300 animate-pulse" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-teal-500/20 text-teal-200 text-[10px] font-bold uppercase tracking-wider mb-2">
              <Sparkles className="w-3 h-3" />
              <span>Action Required</span>
            </div>

            <h2 className="font-heading text-xl font-bold text-white mb-1.5 leading-snug">
              {t.reminderTitle}
            </h2>

            <p className="text-xs text-slate-200 leading-relaxed mb-4">
              {t.reminderDesc}
            </p>

            <button
              type="button"
              onClick={() => setScreen("checkin_entry")}
              id="start-checkin-btn"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-teal-600 hover:bg-teal-500 active:scale-[0.98] text-white font-semibold text-sm rounded-xl shadow-lg transition-all"
            >
              <span>{t.startCheckInBtn}</span>
              <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Clinical Profile Summary Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h3 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
            <Activity className="w-4 h-4 text-teal-700" />
            <span>{t.statusTitle}</span>
          </h3>
          <span className="text-[11px] font-semibold text-slate-500">
            {connectionMode === "fhir" ? "FHIR Live Synced" : "Local Encrypted"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {/* Active Conditions */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
              {t.activeConditions}
            </span>
            <div className="font-semibold text-navy-800 space-y-0.5">
              {profile.conditions.map((cond, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal-600" />
                  <span>{cond}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tracked Prescriptions */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block flex items-center gap-1">
              <Pill className="w-3 h-3 text-teal-700" />
              <span>{t.trackedMeds}</span>
            </span>
            <div className="font-medium text-navy-800 space-y-0.5">
              {profile.medications.map((med, i) => (
                <div key={i} className="truncate">
                  • {med}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Previous Check-in Status */}
        <div className="p-3 rounded-xl bg-mutedGreen-50 border border-mutedGreen-800/20 flex items-center justify-between text-xs">
          <span className="font-medium text-mutedGreen-800 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>{t.lastCheckIn}</span>
          </span>
          <span className="font-semibold text-mutedGreen-800">
            {t.lastCheckInValue}
          </span>
        </div>
      </div>
    </div>
  );
};
