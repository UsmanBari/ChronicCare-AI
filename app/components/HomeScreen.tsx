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
    <div className="w-full max-w-lg mx-auto space-y-5 animate-fadeIn">
      {/* Visible Isolated Offline Mode Banner */}
      {connectionMode === "offline" && (
        <div className="p-3 rounded-xl bg-amber-50 border border-amber-800/30 text-amber-900 text-xs flex items-center justify-between animate-fadeIn shadow-xs">
          <div className="flex items-center gap-2 font-semibold">
            <Database className="w-4 h-4 text-amber-800 shrink-0" />
            <span>{isUrdu ? "آئسولیٹڈ موڈ — لوکل اسٹور استعمال ہو رہا ہے" : "Offline — using Local Store"}</span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-200/70 text-amber-900 font-bold uppercase">
            Isolated Mode
          </span>
        </div>
      )}
      {/* PRESENTER CONTROLS (Demo presentation tool, clearly demarcated) */}
      <div className="p-4 rounded-2xl border-2 border-dashed border-slate-300 bg-slate-100/90 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-wider uppercase text-slate-600">
            <SlidersHorizontal className="w-3.5 h-3.5 text-teal-700" />
            <span>{t.presenterControlsLabel}</span>
          </div>
          <button
            type="button"
            onClick={resetDemo}
            id="presenter-reset-demo-btn"
            title="Reset demo state and return to Normal"
            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-200 transition-colors shadow-xs"
          >
            <RotateCcw className="w-3 h-3 text-slate-600" />
            <span>{t.resetDemoBtn}</span>
          </button>
        </div>

        {/* 3 Scenario Selection Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {/* Scenario A: Normal */}
          <button
            type="button"
            id="scenario-normal-btn"
            onClick={() => setDemoScenario("normal")}
            className={`py-2 px-2.5 rounded-xl text-xs font-semibold border transition-all text-center flex items-center justify-center gap-1.5 ${
              demoScenario === "normal"
                ? "bg-navy-800 text-white border-navy-800 shadow-sm"
                : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
            }`}
          >
            {demoScenario === "normal" && <Check className="w-3.5 h-3.5 text-teal-400" />}
            <span>{t.scenarioNormalBtn}</span>
          </button>

          {/* Scenario B: Conflict */}
          <button
            type="button"
            id="scenario-conflict-btn"
            onClick={() => setDemoScenario("conflict")}
            className={`py-2 px-2.5 rounded-xl text-xs font-semibold border transition-all text-center flex items-center justify-center gap-1.5 ${
              demoScenario === "conflict"
                ? "bg-amber-800 text-white border-amber-800 shadow-sm"
                : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
            }`}
          >
            {demoScenario === "conflict" && <Check className="w-3.5 h-3.5 text-amber-300" />}
            <span>{t.scenarioConflictBtn}</span>
          </button>

          {/* Scenario C: Emergency */}
          <button
            type="button"
            id="scenario-emergency-btn"
            onClick={() => setDemoScenario("emergency")}
            className={`py-2 px-2.5 rounded-xl text-xs font-semibold border transition-all text-center flex items-center justify-center gap-1.5 ${
              demoScenario === "emergency"
                ? "bg-red-700 text-white border-red-700 shadow-sm"
                : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
            }`}
          >
            {demoScenario === "emergency" && <Check className="w-3.5 h-3.5 text-red-200" />}
            <span>{t.scenarioEmergencyBtn}</span>
          </button>
        </div>
      </div>

      {/* Welcome Greeting & Appointments shortcut */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-navy-800">
            {t.homeGreeting}
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {t.homeSubtitle}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setScreen("appointments")}
          id="view-my-appointments-btn"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-navy-800 text-xs font-semibold transition-all shadow-xs"
        >
          <Calendar className="w-3.5 h-3.5 text-teal-700" />
          <span>{t.patientAppointmentsBtn}</span>
          {appointment.isBooked && (
            <span className="w-2 h-2 rounded-full bg-teal-600 animate-pulse" />
          )}
        </button>
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
