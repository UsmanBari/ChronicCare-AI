"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import {
  Calendar,
  Clock,
  Activity,
  Pill,
  ArrowRight,
  BellRing,
  Sparkles,
  SlidersHorizontal,
  RotateCcw,
  Check,
  Database,
  ShieldCheck,
} from "lucide-react";

export const HomeScreen = () => {
  const {
    setScreen,
    profile,
    connectionMode,
    t,
    isUrdu,
    demoScenario,
    setDemoScenario,
    resetDemo,
    appointment,
  } = useApp();

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6 animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Visible Isolated Offline Mode Banner */}
      {connectionMode === "offline" && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-800/30 text-amber-900 text-sm flex items-center justify-between animate-fadeIn shadow-xs">
          <div className="flex items-center gap-2.5 font-semibold">
            <Database className="w-5 h-5 text-amber-800 shrink-0" />
            <span>{isUrdu ? "آئسولیٹڈ موڈ — لوکل اسٹور استعمال ہو رہا ہے" : "Isolated Offline Mode — using Local Encrypted Store"}</span>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-amber-200/80 text-amber-900 font-bold uppercase tracking-wider">
            Offline
          </span>
        </div>
      )}

      {/* PRESENTER CONTROLS (Demo presentation tool with 48px touch targets) */}
      <div className="p-5 sm:p-6 rounded-3xl border-2 border-dashed border-slate-300 bg-slate-100/90 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold tracking-wider uppercase text-slate-700">
            <SlidersHorizontal className="w-4 h-4 text-teal-700" />
            <span>{t.presenterControlsLabel}</span>
          </div>
          <button
            type="button"
            onClick={resetDemo}
            id="presenter-reset-demo-btn"
            title="Reset demo state and return to Normal"
            className="h-10 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-white border border-slate-300 text-slate-700 hover:bg-slate-200 transition-colors shadow-xs"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-600" />
            <span>{t.resetDemoBtn}</span>
          </button>
        </div>

        {/* 3 Scenario Selection Buttons (Min 48px height) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Scenario A: Normal */}
          <button
            type="button"
            id="scenario-normal-btn"
            onClick={() => setDemoScenario("normal")}
            className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border transition-all text-center flex items-center justify-center gap-2 ${
              demoScenario === "normal"
                ? "bg-navy-800 text-white border-navy-800 shadow-sm"
                : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
            }`}
          >
            {demoScenario === "normal" && <Check className="w-4 h-4 text-teal-400 shrink-0" />}
            <span>{t.scenarioNormalBtn}</span>
          </button>

          {/* Scenario B: Conflict */}
          <button
            type="button"
            id="scenario-conflict-btn"
            onClick={() => setDemoScenario("conflict")}
            className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border transition-all text-center flex items-center justify-center gap-2 ${
              demoScenario === "conflict"
                ? "bg-amber-800 text-white border-amber-800 shadow-sm"
                : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
            }`}
          >
            {demoScenario === "conflict" && <Check className="w-4 h-4 text-amber-300 shrink-0" />}
            <span>{t.scenarioConflictBtn}</span>
          </button>

          {/* Scenario C: Emergency */}
          <button
            type="button"
            id="scenario-emergency-btn"
            onClick={() => setDemoScenario("emergency")}
            className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border transition-all text-center flex items-center justify-center gap-2 ${
              demoScenario === "emergency"
                ? "bg-red-800 text-white border-red-800 shadow-sm"
                : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
            }`}
          >
            {demoScenario === "emergency" && <Check className="w-4 h-4 text-red-200 shrink-0" />}
            <span>{t.scenarioEmergencyBtn}</span>
          </button>
        </div>
      </div>

      {/* Welcome Greeting & Appointments shortcut */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
            {t.homeGreeting}
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            {t.homeSubtitle}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setScreen("appointments")}
          id="view-my-appointments-btn"
          className="h-12 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-navy-800 text-sm font-semibold transition-all shadow-xs shrink-0 self-start sm:self-auto"
        >
          <Calendar className="w-4 h-4 text-teal-700" />
          <span>{t.patientAppointmentsBtn}</span>
          {appointment.isBooked && (
            <span className="w-2.5 h-2.5 rounded-full bg-teal-600 animate-pulse" />
          )}
        </button>
      </div>

      {/* PROMINENT REMINDER CARD (Soft Glass with Gradient) */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 rounded-3xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden border border-teal-500/40">
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-teal-400/15 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col sm:flex-row items-start gap-5 relative z-10">
          <div className="w-14 h-14 rounded-2xl bg-teal-700/80 border border-teal-400/40 flex items-center justify-center shrink-0 text-white shadow-md">
            <BellRing className="w-7 h-7 text-teal-300 animate-pulse" />
          </div>

          <div className="flex-1 min-w-0 space-y-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-500/25 text-teal-200 text-xs font-bold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Action Required</span>
            </div>

            <h2 className="font-heading text-xl sm:text-2xl font-bold text-white leading-snug">
              {t.reminderTitle}
            </h2>

            <p className="text-sm sm:text-base text-slate-200 leading-relaxed max-w-xl">
              {t.reminderDesc}
            </p>

            <div className="pt-2">
              <button
                type="button"
                onClick={() => setScreen("checkin_entry")}
                id="start-checkin-btn"
                className="w-full sm:w-auto min-h-[48px] inline-flex items-center justify-center gap-2.5 px-7 py-3.5 bg-teal-600 hover:bg-teal-500 active:scale-[0.98] text-white font-semibold text-sm rounded-xl shadow-lg transition-all"
              >
                <span>{t.startCheckInBtn}</span>
                <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Clinical Profile Summary Card (Soft Glass Elevation) */}
      <div className="glass-resting rounded-3xl p-6 sm:p-7 shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
          <h3 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2">
            <Activity className="w-5 h-5 text-teal-700" />
            <span>{t.statusTitle}</span>
          </h3>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            {connectionMode === "fhir" ? "FHIR Live Synced" : "Local Encrypted"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          {/* Active Conditions */}
          <div className="p-4 rounded-2xl bg-slate-50/90 border border-slate-200/60 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
              {t.activeConditions}
            </span>
            <div className="font-semibold text-navy-800 space-y-1">
              {profile.conditions.map((cond, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-teal-600 shrink-0" />
                  <span>{cond}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tracked Prescriptions */}
          <div className="p-4 rounded-2xl bg-slate-50/90 border border-slate-200/60 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block flex items-center gap-1.5">
              <Pill className="w-4 h-4 text-teal-700" />
              <span>{t.trackedMeds}</span>
            </span>
            <div className="font-medium text-navy-800 space-y-1">
              {profile.medications.map((med, i) => (
                <div key={i} className="truncate">
                  • {med}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Previous Check-in Status (Non-color-only: Icon + Color + Text) */}
        <div className="p-4 rounded-2xl bg-mutedGreen-50 border border-mutedGreen-800/20 flex items-center justify-between text-sm">
          <span className="font-medium text-mutedGreen-800 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            <span>{t.lastCheckIn}</span>
          </span>
          <span className="font-semibold text-mutedGreen-800 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-mutedGreen-800" />
            <span>{t.lastCheckInValue}</span>
          </span>
        </div>
      </div>
    </div>
  );
};
