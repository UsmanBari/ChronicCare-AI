"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { Globe, Settings, Activity, ShieldCheck, Database } from "lucide-react";

export const Header = () => {
  const { language, setLanguage, t, isUrdu, connectionMode, screen } = useApp();

  const toggleLanguage = () => {
    setLanguage(language === "en" ? "ur" : "en");
  };

  return (
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="max-w-xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-navy-800 flex items-center justify-center text-teal-500 shadow-md">
            <Activity className="w-5 h-5 text-teal-400" />
          </div>
          <div>
            <span className="font-heading font-bold text-navy-800 text-lg leading-tight block">
              {isUrdu ? "کرونک کیئر اے آئی" : "ChronicCare AI"}
            </span>
            <span className="text-[10px] uppercase tracking-wider font-semibold text-teal-700 block">
              {connectionMode === "fhir" ? (
                <span className="inline-flex items-center gap-1 text-mutedGreen-800 font-sans">
                  <ShieldCheck className="w-3 h-3" /> {t.connectedHospital}
                </span>
              ) : connectionMode === "offline" ? (
                <span className="inline-flex items-center gap-1 text-amber-800 font-sans">
                  <Database className="w-3 h-3" /> {t.offlineMode}
                </span>
              ) : (
                <span className="text-slate-500 font-sans">M1 Prototype</span>
              )}
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            id="language-toggle-btn"
            title="Toggle Language / زبان تبدیل کریں"
            className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-full border border-slate-300 bg-slate-50 hover:bg-slate-100 text-navy-800 transition-colors shadow-sm"
          >
            <Globe className="w-3.5 h-3.5 text-teal-700" />
            <span>{language === "en" ? "اردو" : "English"}</span>
          </button>

          {/* Settings Icon (Non-functional in M1) */}
          <button
            id="settings-btn"
            disabled
            title={t.settings}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 bg-slate-50 border border-slate-200 cursor-not-allowed opacity-75"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
