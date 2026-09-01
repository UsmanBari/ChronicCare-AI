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
    <header className="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setPortal("landing")}
            id="header-home-btn"
            title="Return to Portal Selection"
            className="w-9 h-9 rounded-lg bg-navy-800 flex items-center justify-center text-teal-500 shadow-md hover:opacity-90 transition-opacity"
          >
            <Activity className="w-5 h-5 text-teal-400" />
          </button>
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
                <span className="text-slate-500 font-sans">M4 Prototype</span>
              )}
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Portal Switcher Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowPortalMenu(!showPortalMenu)}
              id="portal-switcher-btn"
              className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 text-navy-800 transition-colors shadow-xs"
            >
              <Layers className="w-3.5 h-3.5 text-teal-700" />
              <span className="hidden sm:inline">{getPortalLabel()}</span>
              <ChevronDown className="w-3 h-3 text-slate-500" />
            </button>

            {showPortalMenu && (
              <div
                className={`absolute ${
                  isUrdu ? "left-0" : "right-0"
                } mt-1.5 w-48 bg-white rounded-xl border border-slate-200 shadow-xl py-1 z-40 animate-fadeIn text-xs`}
              >
                <button
                  type="button"
                  onClick={() => {
                    setPortal("patient");
                    setScreen("home");
                    setShowPortalMenu(false);
                  }}
                  id="switch-to-patient-btn"
                  className={`w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-slate-50 ${
                    portal === "patient" ? "font-bold text-teal-700 bg-teal-50/50" : "text-navy-800"
                  }`}
                >
                  <User className="w-3.5 h-3.5" />
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
                  className={`w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-slate-50 ${
                    portal === "provider" ? "font-bold text-navy-800 bg-slate-100" : "text-navy-800"
                  }`}
                >
                  <Stethoscope className="w-3.5 h-3.5" />
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
                  className={`w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-slate-50 ${
                    portal === "admin" ? "font-bold text-slate-700 bg-slate-100" : "text-navy-800"
                  }`}
                >
                  <Shield className="w-3.5 h-3.5" />
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
                  className="w-full text-left px-3 py-1.5 text-slate-500 hover:text-navy-800 hover:bg-slate-50"
                >
                  {isUrdu ? "پورٹل سلیکشن اسکرین" : "Portal Select Screen"}
                </button>
              </div>
            )}
          </div>

          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            id="language-toggle-btn"
            title="Toggle Language / زبان تبدیل کریں"
            className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-full border border-slate-300 bg-slate-50 hover:bg-slate-100 text-navy-800 transition-colors shadow-xs"
          >
            <Globe className="w-3.5 h-3.5 text-teal-700" />
            <span>{language === "en" ? "اردو" : "English"}</span>
          </button>

          {/* Settings Icon (Wired up in M4) */}
          <button
            id="settings-btn"
            onClick={() => setShowSettings(true)}
            title={t.settings}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-600 hover:text-navy-800 bg-slate-50 hover:bg-slate-100 border border-slate-200 transition-colors shadow-xs"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
