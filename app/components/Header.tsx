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
  Menu,
  X,
  ArrowRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export const Header = () => {
  const {
    language,
    setLanguage,
    t,
    isUrdu,
    connectionMode,
    portal,
    screen,
    isLiveMode,
    liveEhrConnection,
    setPortal,
    setScreen,
    setProviderScreen,
    setAdminScreen,
    setShowSettings,
    setShowTour,
    returnToHomeAndClearRun,
  } = useApp();

  const [showPortalMenu, setShowPortalMenu] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleLanguage = () => {
    setLanguage(language === "en" ? "ur" : "en");
  };

  const getPortalLabel = () => {
    if (portal === "provider") return t.providerPortal;
    if (portal === "admin") return t.adminPortal;
    if (portal === "patient") return t.patientPortal;
    return "Clinical Suite";
  };

  const renderConnectionBadge = () => {
    if (isLiveMode) {
      if (screen === "consent" || !liveEhrConnection?.mode) {
        return (
          <span className="inline-flex items-center gap-1 text-slate-500 font-sans">
            <Shield className="w-3.5 h-3.5" /> {t.notConnectedYet}
          </span>
        );
      }
      if (liveEhrConnection.mode === "isolated") {
        return (
          <span className="inline-flex items-center gap-1 text-amber-800 font-sans">
            <Database className="w-3.5 h-3.5" /> {t.isolatedModeLabel}
          </span>
        );
      }
      if (liveEhrConnection.mode === "fhir") {
        return (
          <span className="inline-flex items-center gap-1 text-mutedGreen-800 font-sans">
            <ShieldCheck className="w-3.5 h-3.5" />{" "}
            {liveEhrConnection.connection?.display_name || "Hospital EHR (FHIR)"}
          </span>
        );
      }
      return (
        <span className="inline-flex items-center gap-1 text-slate-500 font-sans">
          <Shield className="w-3.5 h-3.5" /> {t.notConnectedYet}
        </span>
      );
    }

    // Mock Mode
    if (connectionMode === "fhir") {
      return (
        <span className="inline-flex items-center gap-1 text-mutedGreen-800 font-sans">
          <ShieldCheck className="w-3.5 h-3.5" /> {t.connectedHospital}
        </span>
      );
    }
    if (connectionMode === "offline") {
      return (
        <span className="inline-flex items-center gap-1 text-amber-800 font-sans">
          <Database className="w-3.5 h-3.5" /> {t.offlineMode}
        </span>
      );
    }
    return <span className="text-slate-500 font-sans">Clinical Suite</span>;
  };

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200/70 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-8 md:px-12 py-3 flex items-center justify-between">
        {/* Logo and Brand */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              setPortal("landing");
              setMobileMenuOpen(false);
            }}
            id="header-home-btn"
            title="Return to Portal Selection"
            className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-navy-800 flex items-center justify-center text-teal-400 shadow-md hover:bg-navy-900 transition-all shrink-0 min-h-[44px] min-w-[44px]"
          >
            <Activity className="w-5 h-5 sm:w-6 sm:h-6" />
          </button>
          <div>
            <span className="font-heading font-bold text-navy-800 text-base sm:text-lg leading-tight block">
              {isUrdu ? "کرونک کیئر اے آئی" : "ChronicCare AI"}
            </span>
            <span className="text-[11px] sm:text-xs uppercase tracking-wider font-semibold text-teal-700 block">
              {renderConnectionBadge()}
            </span>
          </div>
        </div>

        {/* Desktop Action Controls (Above md: - Pixel-Identical) */}
        <div className="hidden md:flex items-center gap-2.5">
          {/* Portal Switcher Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowPortalMenu(!showPortalMenu)}
              id="portal-switcher-btn"
              className="h-11 flex items-center gap-2 text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-navy-800 transition-colors shadow-xs min-h-[44px]"
            >
              <Layers className="w-4 h-4 text-teal-700" />
              <span>{getPortalLabel()}</span>
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
            className="h-11 flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-xl bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 transition-colors shadow-xs min-h-[44px]"
          >
            <HelpCircle className="w-4 h-4 text-teal-700" />
            <span>Guide</span>
          </button>

          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            id="language-toggle-btn"
            title="Toggle Language / زبان تبدیل کریں"
            className="h-11 flex items-center gap-2 text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-navy-800 transition-colors shadow-xs min-h-[44px]"
          >
            <Globe className="w-4 h-4 text-teal-700" />
            <span>{language === "en" ? "اردو" : "English"}</span>
          </button>

          {/* Settings Icon */}
          <button
            id="settings-btn"
            onClick={() => setShowSettings(true)}
            title={t.settings}
            className="w-11 h-11 rounded-xl flex items-center justify-center text-slate-700 hover:text-navy-800 bg-white hover:bg-slate-50 border border-slate-300 transition-colors shadow-xs min-h-[44px] min-w-[44px]"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>

        {/* Mobile Hamburger Button (Below md: - 48px Touch Target) */}
        <div className="flex md:hidden items-center gap-2">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            id="mobile-menu-toggle-btn"
            aria-label="Toggle navigation menu"
            className="w-12 h-12 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-navy-800 flex items-center justify-center transition-colors shadow-xs active:scale-95"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Slide-In Drawer Navigation Menu (Below md:) */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="md:hidden border-t border-slate-200 bg-white/95 backdrop-blur-md px-4 py-5 shadow-2xl overflow-hidden"
          >
            <div className="space-y-4 max-w-lg mx-auto" dir={isUrdu ? "rtl" : "ltr"}>
              {/* Portals Section */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block px-1">
                  {isUrdu ? "پورٹلز" : "Select Portal"}
                </span>

                <button
                  type="button"
                  onClick={() => {
                    setPortal("patient");
                    returnToHomeAndClearRun();
                    setMobileMenuOpen(false);
                  }}
                  id="mobile-nav-patient-btn"
                  className={`w-full min-h-[48px] px-4 py-3 rounded-xl border flex items-center justify-between text-sm font-semibold transition-colors ${
                    portal === "patient"
                      ? "bg-teal-50 border-teal-300 text-teal-900 font-bold"
                      : "bg-slate-50/80 border-slate-200 text-navy-800 hover:bg-slate-100"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <User className="w-5 h-5 text-teal-700" />
                    <span>{t.patientPortal} (Ali Khan)</span>
                  </div>
                  <ArrowRight className={`w-4 h-4 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setPortal("provider");
                    setProviderScreen("dashboard");
                    setMobileMenuOpen(false);
                  }}
                  id="mobile-nav-provider-btn"
                  className={`w-full min-h-[48px] px-4 py-3 rounded-xl border flex items-center justify-between text-sm font-semibold transition-colors ${
                    portal === "provider"
                      ? "bg-navy-900 border-navy-800 text-white font-bold"
                      : "bg-slate-50/80 border-slate-200 text-navy-800 hover:bg-slate-100"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Stethoscope className="w-5 h-5 text-teal-400" />
                    <span>{t.providerPortal} (Dr. Sana Malik)</span>
                  </div>
                  <ArrowRight className={`w-4 h-4 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setPortal("admin");
                    setAdminScreen("dashboard");
                    setMobileMenuOpen(false);
                  }}
                  id="mobile-nav-admin-btn"
                  className={`w-full min-h-[48px] px-4 py-3 rounded-xl border flex items-center justify-between text-sm font-semibold transition-colors ${
                    portal === "admin"
                      ? "bg-slate-800 border-slate-700 text-white font-bold"
                      : "bg-slate-50/80 border-slate-200 text-navy-800 hover:bg-slate-100"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Shield className="w-5 h-5 text-teal-400" />
                    <span>{t.adminPortal}</span>
                  </div>
                  <ArrowRight className={`w-4 h-4 text-slate-400 ${isUrdu ? "rotate-180" : ""}`} />
                </button>
              </div>

              <div className="border-t border-slate-200 pt-3 grid grid-cols-2 gap-2.5">
                {/* Evaluator Tour Guide Button */}
                <button
                  type="button"
                  onClick={() => {
                    setShowTour(true);
                    setMobileMenuOpen(false);
                  }}
                  id="mobile-nav-guide-btn"
                  className="min-h-[48px] px-3 py-2.5 rounded-xl bg-teal-50 border border-teal-200 text-teal-900 font-semibold text-xs flex items-center justify-center gap-2"
                >
                  <HelpCircle className="w-4 h-4 text-teal-700" />
                  <span>Evaluator Guide</span>
                </button>

                {/* Language Toggle */}
                <button
                  type="button"
                  onClick={() => {
                    toggleLanguage();
                  }}
                  id="mobile-nav-language-btn"
                  className="min-h-[48px] px-3 py-2.5 rounded-xl bg-white border border-slate-300 text-navy-800 font-semibold text-xs flex items-center justify-center gap-2"
                >
                  <Globe className="w-4 h-4 text-teal-700" />
                  <span>{language === "en" ? "اردو میں دیکھیں" : "English"}</span>
                </button>
              </div>

              {/* Settings Trigger */}
              <button
                type="button"
                onClick={() => {
                  setShowSettings(true);
                  setMobileMenuOpen(false);
                }}
                id="mobile-nav-settings-btn"
                className="w-full min-h-[48px] px-4 py-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs flex items-center justify-center gap-2"
              >
                <Settings className="w-4 h-4 text-slate-500" />
                <span>{t.settings}</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};
