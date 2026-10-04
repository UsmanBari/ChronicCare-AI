"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { Settings, Globe, ShieldCheck, Database, X, Activity, User, Hospital } from "lucide-react";

export const UnifiedSettingsModal = () => {
  const {
    showSettings,
    setShowSettings,
    language,
    setLanguage,
    connectionMode,
    profile,
    portal,
    t,
    isUrdu,
  } = useApp();

  if (!showSettings) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-lg bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden animate-slideUp">
        {/* Header */}
        <div className="bg-navy-800 p-5 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center text-teal-400">
              <Settings className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-heading text-lg font-bold text-white leading-tight">
                {t.unifiedSettingsTitle}
              </h2>
              <span className="text-[10px] text-slate-300">
                {t.unifiedSettingsSubtitle}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowSettings(false)}
            id="close-settings-btn"
            className="w-8 h-8 rounded-full bg-navy-700 hover:bg-navy-600 text-slate-300 hover:text-white flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {/* Setting 1: Language Toggle */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <Globe className="w-4 h-4 text-teal-700" />
              <span>{t.languageSettingLabel}</span>
            </label>
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                type="button"
                onClick={() => setLanguage("en")}
                id="settings-lang-en-btn"
                className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                  language === "en"
                    ? "bg-teal-700 text-white border-teal-700 shadow-sm"
                    : "bg-white text-navy-800 border-slate-300 hover:bg-slate-100"
                }`}
              >
                English (Default)
              </button>
              <button
                type="button"
                onClick={() => setLanguage("ur")}
                id="settings-lang-ur-btn"
                className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                  language === "ur"
                    ? "bg-teal-700 text-white border-teal-700 shadow-sm font-urdu"
                    : "bg-white text-navy-800 border-slate-300 hover:bg-slate-100 font-urdu"
                }`}
              >
                اردو (Urdu)
              </button>
            </div>
          </div>

          {/* Setting 2: Connection Mode Indicator */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <Hospital className="w-4 h-4 text-teal-700" />
              <span>{t.connectionModeSettingLabel}</span>
            </span>
            <div className="p-3 rounded-lg bg-white border border-slate-200 text-xs">
              {connectionMode === "fhir" ? (
                <div className="flex items-center gap-2 text-mutedGreen-800 font-semibold">
                  <ShieldCheck className="w-4 h-4 text-mutedGreen-800 shrink-0" />
                  <span>{t.connectedHospital}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-amber-800 font-semibold">
                  <Database className="w-4 h-4 text-amber-800 shrink-0" />
                  <span>{t.offlineMode}</span>
                </div>
              )}
              <p className="text-[11px] text-slate-500 mt-1">
                {connectionMode === "fhir"
                  ? "Live HL7® FHIR® bridge active with City General Hospital."
                  : "Isolated device storage mode using the local store."}
              </p>
            </div>
          </div>

          {/* Setting 3: Active Profile Parameters */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <User className="w-4 h-4 text-teal-700" />
              <span>{t.activeProfileLabel}</span>
            </span>
            <div className="grid grid-cols-2 gap-2 text-slate-600">
              <div className="p-2 rounded bg-white border border-slate-200">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Patient</span>
                <span className="font-semibold text-navy-800">Ali Khan (58y)</span>
              </div>
              <div className="p-2 rounded bg-white border border-slate-200">
                <span className="text-[10px] text-slate-400 block uppercase font-bold">Provider</span>
                <span className="font-semibold text-navy-800">Dr. Sana Malik</span>
              </div>
            </div>
          </div>

          {/* Close button */}
          <button
            type="button"
            onClick={() => setShowSettings(false)}
            id="dismiss-settings-btn"
            className="w-full py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all"
          >
            {t.close}
          </button>
        </div>
      </div>
    </div>
  );
};
