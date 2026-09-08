"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import {
  Globe,
  Settings,
  Activity,
  ShieldCheck,
  Database,
  ChevronDown,
  User,
  Stethoscope,
  Shield,
  Layers,
  HelpCircle,
} from "lucide-react";

export const Header = () => {
  const {
    language,
    setLanguage,
    t,
    isUrdu,
    connectionMode,
    portal,
    setPortal,
    setScreen,
    setProviderScreen,
    setAdminScreen,
    setShowSettings,
    setShowTour,
    returnToHomeAndClearRun,
  } = useApp();

  const [showPortalMenu, setShowPortalMenu] = useState(false);

  const toggleLanguage = () => {
    setLanguage(language === "en" ? "ur" : "en");
  };

  const getPortalLabel = () => {
    if (portal === "provider") return t.providerPortal;
    if (portal === "admin") return t.adminPortal;
    if (portal === "patient") return t.patientPortal;
    return "Clinical Suite";
  };

  return (
    <header className="sticky top-0 z-30 bg-white/85 backdrop-blur-md border-b border-slate-200/70 shadow-xs">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-3.5 flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setPortal("landing")}
            id="header-home-btn"
            title="Return to Portal Selection"
            className="w-11 h-11 rounded-xl bg-navy-800 flex items-center justify-center text-teal-400 shadow-md hover:bg-navy-900 transition-all shrink-0"
          >
            <Activity className="w-6 h-6" />
          </button>
          <div>
            <span className="font-heading font-bold text-navy-800 text-lg leading-tight block">
              {isUrdu ? "کرونک کیئر اے آئی" : "ChronicCare AI"}
            </span>
            <span className="text-xs uppercase tracking-wider font-semibold text-teal-700 block">
              {connectionMode === "fhir" ? (
                <span className="inline-flex items-center gap-1 text-mutedGreen-800 font-sans">
                  <ShieldCheck className="w-3.5 h-3.5" /> {t.connectedHospital}
                </span>
              ) : connectionMode === "offline" ? (
                <span className="inline-flex items-center gap-1 text-amber-800 font-sans">
                  <Database className="w-3.5 h-3.5" /> {t.offlineMode}
                </span>
              ) : (
                <span className="text-slate-500 font-sans">Clinical Suite</span>
              )}
            </span>
          </div>
        </div>

        {/* Action Controls (All touch targets >= 44-48px) */}
        <div className="flex items-center gap-2.5">
          {/* Portal Switcher Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowPortalMenu(!showPortalMenu)}
              id="portal-switcher-btn"
              className="h-11 flex items-center gap-2 text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-navy-800 transition-colors shadow-xs"
            >
              <Layers className="w-4 h-4 text-teal-700" />
              <span className="hidden sm:inline">{getPortalLabel()}</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
            </button>

            {showPortalMenu && (
              <div
                className={`absolute ${
                  isUrdu ? "left-0" : "right-0"
                } mt-2 w-52 bg-white/95 backdrop-blur-md rounded-2xl border border-slate-200 shadow-xl py-1.5 z-40 animate-fadeIn text-xs`}
              >
                <button
                  type="button"
                  onClick={() => {
                    setPortal("patient");
                    returnToHomeAndClearRun();
                    setShowPortalMenu(false);
                  }}
                  id="switch-to-patient-btn"
                  className={`w-full text-left px-3.5 py-2.5 flex items-center gap-2.5 hover:bg-slate-50 transition-colors ${
                    portal === "patient" ? "font-bold text-teal-700 bg-teal-50/70" : "text-navy-800"
                  }`}
                >
                  <User className="w-4 h-4" />
                  <span>{t.patientPortal} (Ali Khan)</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setPortal("provider");
                    setProviderScreen("dashboard");
                    setShowPortalMenu(false);
                  }}
                  id="switch-to-provider-btn"
                  className={`w-full text-left px-3.5 py-2.5 flex items-center gap-2.5 hover:bg-slate-50 transition-colors ${
                    portal === "provider" ? "font-bold text-navy-800 bg-slate-100" : "text-navy-800"
                  }`}
                >
                  <Stethoscope className="w-4 h-4" />
                  <span>{t.providerPortal} (Dr. Sana)</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setPortal("admin");
                    setAdminScreen("dashboard");
                    setShowPortalMenu(false);
                  }}
                  id="switch-to-admin-btn"
                  className={`w-full text-left px-3.5 py-2.5 flex items-center gap-2.5 hover:bg-slate-50 transition-colors ${
                    portal === "admin" ? "font-bold text-slate-700 bg-slate-100" : "text-navy-800"
                  }`}
                >
                  <Shield className="w-4 h-4" />
                  <span>{t.adminPortal}</span>
                </button>

                <div className="border-t border-slate-100 my-1" />

                <button
                  type="button"
                  onClick={() => {
                    setPortal("landing");
                    setShowPortalMenu(false);
                  }}
                  id="switch-to-landing-btn"
                  className="w-full text-left px-3.5 py-2 text-slate-500 hover:text-navy-800 hover:bg-slate-50"
                >
                  {isUrdu ? "پورٹل سلیکشن اسکرین" : "Portal Select Screen"}
                </button>
              </div>
            )}
          </div>

          {/* Evaluator Tour Guide Trigger */}
          <button
            onClick={() => setShowTour(true)}
            id="evaluator-guide-btn"
            title="Evaluator Guide & Walkthrough Instructions"
            className="h-11 flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-xl bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 transition-colors shadow-xs"
          >
            <HelpCircle className="w-4 h-4 text-teal-700" />
            <span className="hidden sm:inline">Guide</span>
          </button>

          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            id="language-toggle-btn"
            title="Toggle Language / زبان تبدیل کریں"
            className="h-11 flex items-center gap-2 text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-navy-800 transition-colors shadow-xs"
          >
            <Globe className="w-4 h-4 text-teal-700" />
            <span>{language === "en" ? "اردو" : "English"}</span>
          </button>

          {/* Settings Icon */}
          <button
            id="settings-btn"
            onClick={() => setShowSettings(true)}
            title={t.settings}
            className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-700 hover:text-navy-800 bg-white hover:bg-slate-50 border border-slate-300 transition-colors shadow-xs"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
};
