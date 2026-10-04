"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import {
  Calendar,
  Clock,
  Activity,
  Pill,
  ArrowRight,
  Sparkles,
  SlidersHorizontal,
  RotateCcw,
  Check,
  Database,
  ShieldCheck,
  HeartPulse,
  ChevronRight,
  AlertTriangle,
  RefreshCw,
  Loader2,
  ShieldAlert,
} from "lucide-react";
import { FhirSourceBadge } from "./FhirSourceBadge";
import { api, ApiError } from "../lib/api";

export const HomeScreen = () => {
  const {
    setScreen,
    profile,
    liveProfile,
    liveEhrConnection,
    connectionMode,
    isLiveMode,
    userIdentifier,
    t,
    isUrdu,
    demoScenario,
    setDemoScenario,
    resetDemo,
    appointment,
    setActiveLiveCheckin,
  } = useApp();

  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dynamic medication dosage update for Scenario D (EHR update)
  const displayedMedications =
    demoScenario === "ehr_update"
      ? profile.medications.map((m) =>
          m.includes("Lisinopril") ? "Lisinopril 20mg (1+0)" : m
        )
      : profile.medications;

  const handleStartCheckIn = async () => {
    setError(null);
    if (isLiveMode) {
      setIsStarting(true);
      try {
        const startRes = await api.startCheckin();
        setActiveLiveCheckin(startRes);
        setScreen("checkin_entry");
      } catch (err: any) {
        if (err instanceof ApiError) {
          setError(err.getFriendlyMessage(isUrdu));
        } else {
          setError(err?.message || "Failed to start check-in session");
        }
      } finally {
        setIsStarting(false);
      }
      return;
    }

    setScreen("checkin_entry");
  };

  const activeConditions =
    isLiveMode && liveProfile?.conditions && liveProfile.conditions.length > 0
      ? liveProfile.conditions.map((c) =>
          c === "diabetes" ? "Type 2 Diabetes" : c === "hypertension" ? "Hypertension" : c
        )
      : profile.conditions;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Demo / Presenter Controls Bar (HIDDEN in Live Mode per Design Decision 2) */}
      {!isLiveMode && (
        <div className="p-4 sm:p-5 rounded-2xl border border-slate-300/80 bg-white/95 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-teal-600 animate-pulse" />
              <span className="text-xs font-bold tracking-wider uppercase text-slate-700">
                {t.presenterControlsLabel} (Interactive Prototype)
              </span>
            </div>
            <button
              type="button"
              onClick={resetDemo}
              id="presenter-reset-demo-btn"
              title="Reset demo state and return to Normal"
              className="min-h-[38px] inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 transition-colors shadow-2xs"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-600" />
              <span>{t.resetDemoBtn}</span>
            </button>
          </div>

          {/* 4 Scenario Selector Buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            <button
              type="button"
              id="scenario-normal-btn"
              onClick={() => setDemoScenario("normal")}
              className={`min-h-[44px] py-2.5 px-3.5 rounded-xl text-xs sm:text-sm font-semibold border transition-all text-center flex items-center justify-center gap-2 ${
                demoScenario === "normal"
                  ? "bg-navy-800 text-white border-navy-800 shadow-sm font-bold"
                  : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100 hover:border-slate-300"
              }`}
            >
              {demoScenario === "normal" && <Check className="w-4 h-4 text-teal-400 shrink-0" />}
              <span>{t.scenarioNormalBtn}</span>
            </button>

            <button
              type="button"
              id="scenario-conflict-btn"
              onClick={() => setDemoScenario("conflict")}
              className={`min-h-[44px] py-2.5 px-3.5 rounded-xl text-xs sm:text-sm font-semibold border transition-all text-center flex items-center justify-center gap-2 ${
                demoScenario === "conflict"
                  ? "bg-amber-800 text-white border-amber-800 shadow-sm font-bold"
                  : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100 hover:border-slate-300"
              }`}
            >
              {demoScenario === "conflict" && <Check className="w-4 h-4 text-amber-300 shrink-0" />}
              <span>{t.scenarioConflictBtn}</span>
            </button>

            <button
              type="button"
              id="scenario-emergency-btn"
              onClick={() => setDemoScenario("emergency")}
              className={`min-h-[44px] py-2.5 px-3.5 rounded-xl text-xs sm:text-sm font-semibold border transition-all text-center flex items-center justify-center gap-2 ${
                demoScenario === "emergency"
                  ? "bg-emergencyRed-800 text-white border-emergencyRed-800 shadow-sm font-bold"
                  : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100 hover:border-slate-300"
              }`}
            >
              {demoScenario === "emergency" && <Check className="w-4 h-4 text-red-200 shrink-0" />}
              <span>{t.scenarioEmergencyBtn}</span>
            </button>

            <button
              type="button"
              id="scenario-ehr-update-btn"
              onClick={() => setDemoScenario("ehr_update")}
              className={`min-h-[44px] py-2.5 px-3.5 rounded-xl text-xs sm:text-sm font-semibold border transition-all text-center flex items-center justify-center gap-2 ${
                demoScenario === "ehr_update"
                  ? "bg-teal-700 text-white border-teal-700 shadow-sm font-bold"
                  : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100 hover:border-slate-300"
              }`}
            >
              {demoScenario === "ehr_update" && <Check className="w-4 h-4 text-teal-200 shrink-0" />}
              <span>Scenario D: EHR Update</span>
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Visible Isolated Offline Mode Banner */}
      {connectionMode === "offline" && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-800/30 text-amber-900 text-sm flex items-center justify-between animate-fadeIn shadow-xs">
          <div className="flex items-center gap-2.5 font-semibold">
            <Database className="w-5 h-5 text-amber-800 shrink-0" />
            <span>{isUrdu ? "آئسولیٹڈ موڈ — لوکل اسٹور استعمال ہو رہا ہے" : "Isolated Mode — Operating from Local Private Record"}</span>
          </div>
          <span className="text-xs px-3 py-1 rounded-full bg-amber-200/80 text-amber-900 font-bold uppercase tracking-wider">
            {t.isolatedBadgeTitle}
          </span>
        </div>
      )}

      {/* Patient Greeting & Consultation Shortcut */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-1">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-teal-800 block mb-1">
            {isUrdu ? "روزانہ صحت کا جائزہ" : "Daily Care Companion"}
          </span>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800 tracking-tight">
            {isLiveMode ? `Good day, ${userIdentifier.split("@")[0]}` : t.homeGreeting}
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-lg">
            {t.homeSubtitle}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setScreen("appointments")}
          id="view-my-appointments-btn"
          className="min-h-[48px] inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-navy-800 text-sm font-semibold transition-all shadow-xs shrink-0 self-start sm:self-auto"
        >
          <Calendar className="w-4 h-4 text-teal-700" />
          <span>{t.patientAppointmentsBtn}</span>
          {appointment.isBooked && (
            <span className="w-2.5 h-2.5 rounded-full bg-teal-600 animate-pulse" />
          )}
        </button>
      </div>

      {/* Dominant Primary Action Card: Start Daily Check-in */}
      <div className="bg-navy-800 rounded-3xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden border border-teal-500/30">
        <div className="flex flex-col sm:flex-row items-start gap-5 relative z-10">
          <div className="w-14 h-14 rounded-2xl bg-teal-700/80 border border-teal-400/40 flex items-center justify-center shrink-0 text-white shadow-md">
            <HeartPulse className="w-7 h-7 text-teal-300" />
          </div>

          <div className="flex-1 min-w-0 space-y-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-500/25 text-teal-200 text-xs font-bold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isUrdu ? "آج کا ضروری قدم" : "Today's Primary Step"}</span>
            </div>

            <h2 className="font-heading text-xl sm:text-2xl font-bold text-white leading-snug">
              {t.reminderTitle}
            </h2>

            <p className="text-sm sm:text-base text-slate-200 leading-relaxed max-w-xl">
              {t.reminderDesc}
            </p>

            <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <button
                type="button"
                onClick={handleStartCheckIn}
                disabled={isStarting}
                id="start-checkin-btn"
                className="w-full sm:w-auto min-h-[48px] inline-flex items-center justify-center gap-2.5 px-8 py-3.5 bg-teal-600 hover:bg-teal-500 active:scale-[0.98] disabled:opacity-75 text-white font-bold text-sm sm:text-base rounded-xl shadow-lg transition-all"
              >
                {isStarting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Starting Session...</span>
                  </>
                ) : (
                  <>
                    <span>{t.startCheckInBtn}</span>
                    <ArrowRight className={`w-5 h-5 ${isUrdu ? "rotate-180" : ""}`} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Direct Emergency Reporting Entry Point Button */}
      <button
        type="button"
        onClick={() => setScreen("emergency")}
        id="report-urgent-symptoms-btn"
        className="w-full py-3.5 px-4 rounded-2xl border-2 border-red-200/90 text-emergencyRed-800 font-bold text-sm bg-white hover:bg-red-50/80 transition-colors flex items-center justify-center gap-2 shadow-xs"
      >
        <AlertTriangle className="w-4 h-4 text-emergencyRed-700" />
        <span>Report Urgent Symptoms Now</span>
      </button>

      {/* Health Snapshot */}
      <div className="surface-card rounded-3xl p-6 sm:p-7 space-y-5">
        <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
          <h3 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-teal-700" />
            <span>{t.statusTitle}</span>
          </h3>
          <span className="text-xs font-semibold px-3 py-1 rounded-full bg-slate-100 text-slate-700">
            {connectionMode === "fhir" ? "FHIR Live Synced" : "Local Encrypted"}
          </span>
        </div>

        {/* Scenario D: EHR Update Notification Banner (Mock only) */}
        {!isLiveMode && demoScenario === "ehr_update" && (
          <div className="p-3.5 rounded-2xl bg-teal-50 border border-teal-200 text-xs flex items-start gap-2.5 animate-fadeIn">
            <RefreshCw className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-teal-800 block">Updated from your recent visit</span>
              <span className="text-teal-700 leading-relaxed">
                Dr. Sana Malik updated your prescription on {new Date().toLocaleDateString()} — Lisinopril dosage changed to 20mg (1+0). Synced from City General Hospital&apos;s FHIR record.
              </span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          {/* Active Conditions */}
          <div className="p-4 rounded-2xl bg-slate-50/90 border border-slate-200/70 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
              {t.activeConditions}
            </span>
            <div className="font-semibold text-navy-800 space-y-1.5">
              {activeConditions.map((cond, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-teal-600 shrink-0" />
                    <span>{cond}</span>
                  </div>
                  {connectionMode === "fhir" && <FhirSourceBadge />}
                </div>
              ))}
            </div>
          </div>

          {/* Tracked Prescriptions */}
          <div className="p-4 rounded-2xl bg-slate-50/90 border border-slate-200/70 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block flex items-center gap-1.5">
              <Pill className="w-4 h-4 text-teal-700" />
              <span>{t.trackedMeds}</span>
            </span>
            <div className="font-medium text-navy-800 space-y-1.5">
              {displayedMedications.map((med, i) => (
                <div key={i} className="flex items-center justify-between text-xs sm:text-sm">
                  <span className="truncate">• {med}</span>
                  {connectionMode === "fhir" && <FhirSourceBadge />}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Previous Check-in Status */}
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
