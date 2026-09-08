"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { User, Stethoscope, Shield, Activity, ArrowRight, ShieldCheck, HeartPulse, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

export const PortalLandingScreen = () => {
  const { setPortal, setScreen, setProviderScreen, setAdminScreen, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 md:px-8 pt-4 md:pt-10 pb-12 animate-fadeIn relative">
      {/* Asymmetric 2-Zone Desktop Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start relative z-10">
        
        {/* Left Zone: ~58% of Viewport on Desktop */}
        <div className="lg:col-span-7 space-y-7 text-left" dir={isUrdu ? "rtl" : "ltr"}>
          
          {/* Eyebrow & Hero Header */}
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-[13px] font-semibold tracking-wide uppercase shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-teal-700" />
              <span>{isUrdu ? "کرونک کیئر اے آئی کلینیکل سوٹ" : "CHRONICCARE AI CLINICAL SUITE"}</span>
            </div>

            <h1 className="font-heading text-3xl sm:text-4xl lg:text-[36px] font-bold text-navy-800 leading-[1.22] tracking-tight">
              {isUrdu ? "اپنی نگہداشت کی ٹیم میں خوش آمدید" : "Welcome back to your care team"}
            </h1>

            {/* Consistent Brand Motto Line */}
            <p className="font-serif italic text-teal-700 text-lg sm:text-xl leading-snug">
              {isUrdu
                ? "«دائمی نگہداشت کا تسلسل، ہر چیک اپ کے درمیان۔»"
                : '"Continuity of care, between every visit."'}
            </p>

            <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-xl">
              {isUrdu
                ? "دائمی امراض (ذیابیطس و بلڈ پریشر) کی فعال مانیٹرنگ اور کلینیکل ہم آہنگی — مریضوں، معالجین اور منتظمین کے لیے۔"
                : "Continuous chronic disease management, telemetry reconciliation, and care escalation — for patients, providers, and administrators."}
            </p>
          </div>

          {/* Portal Cards: Deliberate Asymmetric Hierarchy */}
          <div className="space-y-4 pt-1">
            
            {/* Primary Card: Patient Portal (Visually Prominent, Soft Teal Glass) */}
            <motion.button
              whileHover={{ y: -3, scale: 1.005 }}
              whileTap={{ scale: 0.99 }}
              transition={{ type: "spring", stiffness: 350, damping: 22 }}
              type="button"
              onClick={() => {
                setPortal("patient");
                setScreen("login");
              }}
              id="select-patient-portal-btn"
              className="w-full p-6 sm:p-7 rounded-3xl glass-teal-subtle border-2 border-teal-400/70 hover:border-teal-700 shadow-md hover:shadow-xl transition-all duration-200 text-left flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 group"
            >
              <div className="flex items-start sm:items-center gap-4.5">
                <div className="w-14 h-14 rounded-2xl bg-teal-100 text-teal-700 flex items-center justify-center shrink-0 group-hover:bg-teal-700 group-hover:text-white transition-colors duration-200 shadow-sm">
                  <User className="w-7 h-7" />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h2 className="font-heading text-lg sm:text-xl font-bold text-navy-800">
                      {t.patientPortal}
                    </h2>
                    <span className="px-2.5 py-0.5 rounded-full bg-teal-100 text-teal-800 text-[11px] font-bold uppercase tracking-wider">
                      Patient
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed max-w-md">
                    {isUrdu
                      ? "روزانہ علامات کا چیک ان، رسک فیڈ بیک اور ذاتی صحت کے رجحانات۔"
                      : "Daily symptom check-in, adaptive clinical interview, risk feedback, and health trends."}
                  </p>
                  <span className="text-xs font-semibold text-teal-800 block pt-0.5">
                    Demo User: Ali Khan (Type 2 Diabetes)
                  </span>
                </div>
              </div>

              <div className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-teal-700 text-white font-semibold text-sm shadow-md group-hover:bg-teal-800 transition-colors shrink-0 self-stretch sm:self-auto justify-center">
                <span>{isUrdu ? "داخل ہوں" : "Enter Portal"}</span>
                <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
              </div>
            </motion.button>

            {/* Secondary Cards: Provider & Admin */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              
              {/* Secondary Card 1: Provider Portal */}
              <motion.button
                whileHover={{ y: -3 }}
                whileTap={{ scale: 0.99 }}
                transition={{ type: "spring", stiffness: 350, damping: 22 }}
                type="button"
                onClick={() => {
                  setPortal("provider");
                  setProviderScreen("login");
                }}
                id="select-provider-portal-btn"
                className="p-5 sm:p-6 rounded-2xl glass-resting border border-slate-200/80 hover:border-navy-800 hover:shadow-lg transition-all duration-200 text-left flex flex-col justify-between group min-h-[200px]"
              >
                <div className="space-y-3">
                  <div className="w-12 h-12 rounded-xl bg-navy-100 text-navy-800 flex items-center justify-center group-hover:bg-navy-800 group-hover:text-white transition-colors duration-200 shadow-xs">
                    <Stethoscope className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="font-heading text-base sm:text-lg font-bold text-navy-800">
                      {t.providerPortal}
                    </h2>
                    <span className="text-xs font-semibold text-navy-700 block mt-0.5">
                      Dr. Sana Malik (City General)
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
                    {isUrdu
                      ? "طبی ٹریاج، ریویو کیو اور تضادات کے الرٹس کا حل۔"
                      : "Clinical triage, live counters, review queue, and reconciliation alerts."}
                  </p>
                </div>
                <div className="pt-4 flex items-center gap-1.5 text-xs font-bold text-navy-800 group-hover:text-teal-700 transition-colors">
                  <span>{isUrdu ? "داخل ہوں" : "Enter Portal"}</span>
                  <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                </div>
              </motion.button>

              {/* Secondary Card 2: Admin Portal */}
              <motion.button
                whileHover={{ y: -3 }}
                whileTap={{ scale: 0.99 }}
                transition={{ type: "spring", stiffness: 350, damping: 22 }}
                type="button"
                onClick={() => {
                  setPortal("admin");
                  setAdminScreen("login");
                }}
                id="select-admin-portal-btn"
                className="p-5 sm:p-6 rounded-2xl glass-resting border border-slate-200/80 hover:border-slate-700 hover:shadow-lg transition-all duration-200 text-left flex flex-col justify-between group min-h-[200px]"
              >
                <div className="space-y-3">
                  <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center group-hover:bg-slate-700 group-hover:text-white transition-colors duration-200 shadow-xs">
                    <Shield className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="font-heading text-base sm:text-lg font-bold text-navy-800">
                      {t.adminPortal}
                    </h2>
                    <span className="text-xs font-semibold text-slate-600 block mt-0.5">
                      System Administrator
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-slate-500 leading-relaxed">
                    {isUrdu
                      ? "سسٹم ٹیلی میٹری، یوزر ڈائرکٹری اور سیکیورٹی آڈٹ ٹریل۔"
                      : "System telemetry, user directory, alerts counter, and audit trail."}
                  </p>
                </div>
                <div className="pt-4 flex items-center gap-1.5 text-xs font-bold text-slate-700 group-hover:text-teal-700 transition-colors">
                  <span>{isUrdu ? "داخل ہوں" : "Enter Portal"}</span>
                  <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                </div>
              </motion.button>
            </div>
          </div>
        </div>

        {/* Right Zone: ~42% Decorative Ambient Zone with Living Motion Blobs */}
        <div className="lg:col-span-5 hidden lg:flex flex-col justify-center items-center relative min-h-[500px] p-6">
          
          {/* Layered Blurred Gradient Blobs with Slow Continuous Float Physics */}
          <motion.div
            animate={{ x: [0, 24, 0], y: [0, -20, 0] }}
            transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
            className="absolute top-6 right-2 w-80 h-80 bg-teal-600/20 rounded-full blur-3xl pointer-events-none"
          />
          <motion.div
            animate={{ x: [0, -20, 0], y: [0, 22, 0] }}
            transition={{ duration: 14, repeat: Infinity, ease: "easeInOut", delay: 1 }}
            className="absolute bottom-6 left-2 w-72 h-72 bg-navy-800/18 rounded-full blur-3xl pointer-events-none"
          />
          <motion.div
            animate={{ scale: [1, 1.15, 1], opacity: [0.15, 0.25, 0.15] }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-56 h-56 bg-teal-400/25 rounded-full blur-2xl pointer-events-none"
          />

          {/* Ambient Glass Feature Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15, ease: "easeOut" }}
            className="relative z-10 w-full max-w-sm rounded-3xl glass-resting p-7 border border-slate-200/90 shadow-lg space-y-6"
          >
            {/* Watermark Icon */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2 text-navy-800">
                <HeartPulse className="w-5 h-5 text-teal-700" />
                <span className="font-heading font-bold text-sm">ChronicCare Ecosystem</span>
              </div>
              <span className="px-2.5 py-1 rounded-full bg-mutedGreen-100 text-mutedGreen-800 text-[10px] font-bold flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" /> Active Sync
              </span>
            </div>

            {/* Feature Badges */}
            <div className="space-y-3.5 text-xs">
              <div className="flex items-start gap-3 p-3.5 rounded-2xl bg-white/80 border border-slate-200/70 shadow-2xs">
                <div className="w-7 h-7 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">
                  1
                </div>
                <div>
                  <div className="font-bold text-navy-800 text-sm">Adaptive Check-in</div>
                  <div className="text-slate-500 text-xs mt-0.5">Dynamic clinical interview targeting T2D and Hypertension markers.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3.5 rounded-2xl bg-white/80 border border-slate-200/70 shadow-2xs">
                <div className="w-7 h-7 rounded-xl bg-navy-100 text-navy-800 flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">
                  2
                </div>
                <div>
                  <div className="font-bold text-navy-800 text-sm">HL7® FHIR® Reconciliation</div>
                  <div className="text-slate-500 text-xs mt-0.5">Automated detection of telemetry discrepancies against hospital records.</div>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3.5 rounded-2xl bg-white/80 border border-slate-200/70 shadow-2xs">
                <div className="w-7 h-7 rounded-xl bg-mutedGreen-100 text-mutedGreen-800 flex items-center justify-center shrink-0 mt-0.5 font-bold text-xs">
                  3
                </div>
                <div>
                  <div className="font-bold text-navy-800 text-sm">Closed-Loop Care</div>
                  <div className="text-slate-500 text-xs mt-0.5">Direct provider escalation, follow-up scheduling, and compliance logs.</div>
                </div>
              </div>
            </div>

            {/* Subtle Footnote */}
            <div className="pt-2 text-center text-xs text-slate-400">
              End-to-End Encrypted • HIPAA & WCAG 2.1 AA Aligned
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};
