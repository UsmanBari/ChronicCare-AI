"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import {
  User,
  Stethoscope,
  Shield,
  Activity,
  ArrowRight,
  ShieldCheck,
  HeartPulse,
  Sparkles,
  CheckCircle2,
  Lock,
  FileCheck2,
  Database,
  ArrowDown,
  Layers,
  ChevronRight,
  TrendingUp,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { motion } from "framer-motion";

export const PortalLandingScreen = () => {
  const { setPortal, setScreen, setProviderScreen, setAdminScreen, t, isUrdu } = useApp();

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="w-full pb-16 animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* 1. Landing Navigation Sub-Bar */}
      <nav className="sticky top-[69px] z-20 bg-white/90 backdrop-blur-md border-b border-slate-200/80 shadow-2xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-2.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-1 sm:gap-6 text-xs font-semibold text-slate-600">
            <button
              onClick={() => scrollToSection("patients")}
              className="hover:text-teal-700 py-1 px-2 rounded-lg hover:bg-slate-100 transition-colors"
            >
              {isUrdu ? "مریضوں کے لیے" : "For Patients"}
            </button>
            <button
              onClick={() => scrollToSection("providers")}
              className="hover:text-teal-700 py-1 px-2 rounded-lg hover:bg-slate-100 transition-colors"
            >
              {isUrdu ? "معالجین کے لیے" : "For Providers"}
            </button>
            <button
              onClick={() => scrollToSection("admins")}
              className="hover:text-teal-700 py-1 px-2 rounded-lg hover:bg-slate-100 transition-colors"
            >
              {isUrdu ? "منتظمین کے لیے" : "For Admins"}
            </button>
            <button
              onClick={() => scrollToSection("standards")}
              className="hidden sm:inline hover:text-teal-700 py-1 px-2 rounded-lg hover:bg-slate-100 transition-colors"
            >
              {isUrdu ? "طبی معیارات" : "Standards"}
            </button>
          </div>

          <button
            type="button"
            onClick={() => scrollToSection("portal-picker")}
            className="px-3.5 py-1.5 rounded-xl bg-navy-800 hover:bg-navy-900 text-white font-semibold text-xs transition-all shadow-xs flex items-center gap-1.5"
          >
            <span>{isUrdu ? "پورٹل منتخب کریں" : "Select Portal"}</span>
            <ArrowDown className="w-3.5 h-3.5" />
          </button>
        </div>
      </nav>

      {/* 2. Enterprise Hero Section */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 pt-8 md:pt-14 pb-12 md:pb-16">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* Hero Left Content */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold tracking-wide uppercase shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-teal-700" />
              <span>{isUrdu ? "دائمی امراض کا ذہین کلینیکل سوٹ" : "Intelligent Chronic Care Suite"}</span>
            </div>

            <h1 className="font-heading text-3xl sm:text-4xl lg:text-[42px] font-bold text-navy-800 leading-[1.2] tracking-tight">
              {isUrdu
                ? "دائمی امراض کی نگہداشت اور کلینیکل ہم آہنگی"
                : "Continuous chronic care with real-time clinical reconciliation."}
            </h1>

            {/* Consistent Brand Motto Line */}
            <p className="font-serif italic text-teal-700 text-lg sm:text-xl leading-snug">
              {isUrdu
                ? "«دائمی نگہداشت کا تسلسل، ہر چیک اپ کے درمیان۔»"
                : '"Continuity of care, between every visit."'}
            </p>

            <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-xl">
              {isUrdu
                ? "ذیابیطس اور ہائی بلڈ پریشر کے مریضوں کے روزانہ علامات، ہسپتال کے FHIR ریکارڈز کا خودکار موازنہ، اور معالجین کے لیے فوری ٹریاج ورک اسپیس۔"
                : "A multi-portal platform uniting daily patient symptom monitoring, automated HL7® FHIR® EHR telemetry reconciliation, and clinician-in-the-loop decision support."}
            </p>

            {/* Hero CTAs */}
            <div className="flex flex-wrap items-center gap-3.5 pt-2">
              <button
                type="button"
                onClick={() => scrollToSection("portal-picker")}
                className="min-h-[48px] px-6 py-3 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center gap-2"
              >
                <span>{isUrdu ? "پورٹل میں داخل ہوں" : "Enter Interactive Prototype"}</span>
                <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
              </button>

              <button
                type="button"
                onClick={() => scrollToSection("patients")}
                className="min-h-[48px] px-5 py-3 border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl transition-all shadow-xs"
              >
                {isUrdu ? "پلیٹ فارم کیسے کام کرتا ہے؟" : "See How It Works"}
              </button>
            </div>
          </div>

          {/* Hero Right Visual: Clean Vector SVG Illustration Card */}
          <div className="lg:col-span-5 flex justify-center">
            <div className="w-full max-w-md rounded-3xl bg-teal-50/90 border border-teal-200/90 p-6 sm:p-7 shadow-lg relative overflow-hidden">
              {/* Monoline watermark */}
              <div className="absolute top-2 right-2 text-teal-700/10 pointer-events-none">
                <Activity className="w-44 h-44" strokeWidth={1} />
              </div>

              <div className="relative z-10 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-teal-200/80">
                  <div className="flex items-center gap-2 text-navy-800">
                    <HeartPulse className="w-5 h-5 text-teal-700" />
                    <span className="font-heading font-bold text-sm">ChronicCare Engine</span>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full bg-mutedGreen-100 text-mutedGreen-800 text-[10px] font-bold flex items-center gap-1">
                    <ShieldCheck className="w-3 h-3" /> Live
                  </span>
                </div>

                {/* Simulated Telemetry Card */}
                <div className="p-3.5 rounded-2xl bg-white border border-teal-100 shadow-xs space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="font-bold text-navy-800">Ali Khan (58y M)</span>
                    <span className="text-[11px] text-teal-700 font-bold bg-teal-50 px-2 py-0.5 rounded">T2D</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-600 pt-1">
                    <span>Blood Glucose</span>
                    <span className="font-mono font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded">180 mg/dL</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-600">
                    <span>Hospital FHIR Baseline</span>
                    <span className="font-mono font-bold text-slate-700">140 mg/dL</span>
                  </div>
                </div>

                {/* AI Detection Insight */}
                <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold text-amber-800">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>Reconciliation Discrepancy Flagged</span>
                  </div>
                  <p className="text-[11px] text-amber-800/90 leading-tight">
                    Patient check-in diverges from hospital EHR. Routed to Dr. Sana Malik for review.
                  </p>
                </div>

                {/* Closed loop resolution */}
                <div className="p-3 rounded-xl bg-teal-900 text-white flex items-center justify-between text-xs">
                  <span className="text-teal-200 font-medium">Provider Triage Action:</span>
                  <span className="font-bold text-teal-300">✓ Follow-Up Booked</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Three Product Sections (Glooko-style alternating cards) */}
      <section className="space-y-12 md:space-y-16 py-8">
        {/* Product 1: For Patients (Image Left, Text Right) */}
        <div id="patients" className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 scroll-mt-28">
          <div className="surface-card rounded-3xl p-6 sm:p-10 shadow-sm border border-slate-200/90">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Visual Panel Left */}
              <div className="lg:col-span-5 bg-teal-50 rounded-2xl p-6 border border-teal-100 flex flex-col justify-center items-center text-center space-y-4">
                <div className="w-16 h-16 rounded-2xl bg-teal-700 text-white flex items-center justify-center shadow-md">
                  <User className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="font-heading font-bold text-lg text-navy-800">Patient Companion</h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-xs">
                    Designed for adults managing Type 2 Diabetes & Hypertension with minimal cognitive friction.
                  </p>
                </div>
                <div className="w-full bg-white rounded-xl p-3 border border-teal-100 text-left text-xs space-y-1.5 shadow-2xs">
                  <div className="flex items-center justify-between font-bold text-navy-800">
                    <span>Daily Check-In</span>
                    <span className="text-mutedGreen-800">✓ Ready</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div className="bg-teal-600 h-full rounded-full w-3/4" />
                  </div>
                </div>
              </div>

              {/* Text Content Right */}
              <div className="lg:col-span-7 space-y-4">
                <span className="px-3 py-1 rounded-full bg-teal-100 text-teal-900 text-xs font-bold uppercase tracking-wider">
                  Patient Experience
                </span>
                <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
                  {isUrdu ? "روزانہ علامات کا چیک ان اور ایڈاپٹیو انٹرویو" : "Daily Check-Ins, Adaptive Interview & Trend Insights"}
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Patients check in through an intuitive survey supporting voice notes and simple touch controls. The system dynamically generates context-aware follow-up questions to distinguish normal day-to-day fluctuations from emerging health risks.
                </p>
                <div className="space-y-2.5 pt-2 text-xs sm:text-sm text-navy-800">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Dynamic follow-up questions tailored to reported symptoms (thirst, missed meds)</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Visual blood glucose and blood pressure trends with clinical target reference bands</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Operates seamlessly in both live HL7® FHIR® connected mode and fully offline</span>
                  </div>
                </div>
                <div className="pt-3">
                  <button
                    type="button"
                    onClick={() => {
                      setPortal("patient");
                      setScreen("login");
                    }}
                    className="min-h-[44px] px-5 py-2.5 bg-teal-700 hover:bg-teal-800 text-white font-semibold text-xs rounded-xl shadow-xs transition-all inline-flex items-center gap-2"
                  >
                    <span>{isUrdu ? "مریض پورٹل کھولیں" : "Launch Patient Portal Demo"}</span>
                    <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Product 2: For Providers (Text Left, Image Right) */}
        <div id="providers" className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 scroll-mt-28">
          <div className="surface-card rounded-3xl p-6 sm:p-10 shadow-sm border border-slate-200/90">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Text Content Left */}
              <div className="lg:col-span-7 space-y-4 order-2 lg:order-1">
                <span className="px-3 py-1 rounded-full bg-navy-100 text-navy-900 text-xs font-bold uppercase tracking-wider">
                  Provider Workspace
                </span>
                <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
                  {isUrdu ? "طبی ٹریاج اور FHIR ڈیٹا کا موازنہ" : "Clinical Triage & Multi-Source Reconciliation Workspace"}
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Equips clinicians with a prioritized triage queue and instant reconciliation alerts. When patient telemetry conflicts with hospital EHR records, the AI engine surfaces confidence ratings, supporting evidence, and single-click resolution pathways.
                </p>
                <div className="space-y-2.5 pt-2 text-xs sm:text-sm text-navy-800">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Real-time case counters with instant urgency notifications for acute escalations</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Side-by-side telemetry diffing (Patient vs. EHR) with AI confidence ratings</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Closed-loop follow-up scheduling with instant cross-portal patient synchronization</span>
                  </div>
                </div>
                <div className="pt-3">
                  <button
                    type="button"
                    onClick={() => {
                      setPortal("provider");
                      setProviderScreen("login");
                    }}
                    className="min-h-[44px] px-5 py-2.5 bg-navy-800 hover:bg-navy-900 text-white font-semibold text-xs rounded-xl shadow-xs transition-all inline-flex items-center gap-2"
                  >
                    <span>{isUrdu ? "معالج پورٹل کھولیں" : "Launch Provider Portal Demo"}</span>
                    <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                  </button>
                </div>
              </div>

              {/* Visual Panel Right */}
              <div className="lg:col-span-5 bg-navy-900 text-white rounded-2xl p-6 border border-navy-800 flex flex-col justify-center items-center text-center space-y-4 order-1 lg:order-2">
                <div className="w-16 h-16 rounded-2xl bg-teal-600 text-white flex items-center justify-center shadow-md">
                  <Stethoscope className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="font-heading font-bold text-lg text-white">Clinical Command Center</h3>
                  <p className="text-xs text-slate-300 mt-1 max-w-xs">
                    Dr. Sana Malik • City General Hospital
                  </p>
                </div>
                <div className="w-full bg-navy-800/90 rounded-xl p-3 border border-teal-500/30 text-left text-xs space-y-1.5 shadow-2xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300">Active Review Queue</span>
                    <span className="px-2 py-0.5 rounded bg-amber-400 text-navy-950 font-bold text-[10px]">1 Pending</span>
                  </div>
                  <div className="text-[11px] text-teal-300">Glucose Discrepancy Flagged: Ali Khan</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Product 3: For Admins (Image Left, Text Right) */}
        <div id="admins" className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 scroll-mt-28">
          <div className="surface-card rounded-3xl p-6 sm:p-10 shadow-sm border border-slate-200/90">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              {/* Visual Panel Left */}
              <div className="lg:col-span-5 bg-slate-100 rounded-2xl p-6 border border-slate-200 flex flex-col justify-center items-center text-center space-y-4">
                <div className="w-16 h-16 rounded-2xl bg-slate-800 text-white flex items-center justify-center shadow-md">
                  <Shield className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="font-heading font-bold text-lg text-navy-800">System Administration</h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-xs">
                    Directory security, platform telemetry, and immutable audit logs.
                  </p>
                </div>
                <div className="w-full bg-white rounded-xl p-3 border border-slate-200 text-left text-xs space-y-1.5 shadow-2xs">
                  <div className="flex items-center justify-between font-bold text-navy-800">
                    <span>FHIR Endpoint Status</span>
                    <span className="text-mutedGreen-800 font-mono">200 OK</span>
                  </div>
                  <div className="text-[11px] text-slate-500">126 Tracked Users • 18 Providers</div>
                </div>
              </div>

              {/* Text Content Right */}
              <div className="lg:col-span-7 space-y-4">
                <span className="px-3 py-1 rounded-full bg-slate-200 text-slate-800 text-xs font-bold uppercase tracking-wider">
                  Enterprise Administration
                </span>
                <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
                  {isUrdu ? "پلیٹ فارم مانیٹرنگ اور سیکیورٹی لاگز" : "Platform Telemetry, Role Directory & Audit Trail"}
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed">
                  Provides administrators with real-time platform health monitoring, user directory access across clinical staff and patients, and an immutable audit log of every clinical intervention and EHR sync.
                </p>
                <div className="space-y-2.5 pt-2 text-xs sm:text-sm text-navy-800">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Real-time platform usage metrics and active clinical alert counters</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Comprehensive user directory with role-based access control</span>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                    <span>Immutable audit log tracking security, integration, and clinical events</span>
                  </div>
                </div>
                <div className="pt-3">
                  <button
                    type="button"
                    onClick={() => {
                      setPortal("admin");
                      setAdminScreen("login");
                    }}
                    className="min-h-[44px] px-5 py-2.5 bg-slate-800 hover:bg-slate-900 text-white font-semibold text-xs rounded-xl shadow-xs transition-all inline-flex items-center gap-2"
                  >
                    <span>{isUrdu ? "ایڈمن پورٹل کھولیں" : "Launch Admin Portal Demo"}</span>
                    <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Stats / Credibility Section (Real Project Facts) */}
      <section id="stats" className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-8 scroll-mt-28">
        <div className="bg-gradient-to-br from-navy-900 via-navy-800 to-teal-900 rounded-3xl p-8 sm:p-10 text-white shadow-xl border border-teal-500/30">
          <div className="text-center max-w-xl mx-auto mb-8">
            <span className="text-xs font-bold uppercase tracking-widest text-teal-300 block mb-1">
              {isUrdu ? "پروجیکٹ کی تصدیق اور نتائج" : "PROJECT CAPABILITIES & VALIDATION"}
            </span>
            <h2 className="font-heading text-2xl sm:text-3xl font-bold text-white">
              {isUrdu ? "ٹھوس پروٹوٹائپ میٹرکس" : "Engineered for Clinical Continuity"}
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xs">
              <div className="font-heading text-3xl sm:text-4xl font-bold text-teal-300 mb-1">5</div>
              <div className="text-xs text-slate-200 font-semibold uppercase tracking-wider">Milestones Built & Demonstrated</div>
            </div>

            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xs">
              <div className="font-heading text-3xl sm:text-4xl font-bold text-teal-300 mb-1">3</div>
              <div className="text-xs text-slate-200 font-semibold uppercase tracking-wider">Live Interactive Demo Scenarios</div>
            </div>

            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xs">
              <div className="font-heading text-3xl sm:text-4xl font-bold text-teal-300 mb-1">7 / 7</div>
              <div className="text-xs text-slate-200 font-semibold uppercase tracking-wider">Backend Verification Tests Passed</div>
            </div>

            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xs">
              <div className="font-heading text-3xl sm:text-4xl font-bold text-teal-300 mb-1">2</div>
              <div className="text-xs text-slate-200 font-semibold uppercase tracking-wider">Modes: FHIR Sync & Fully Offline</div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Trust / Standards Section */}
      <section id="standards" className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-8 scroll-mt-28">
        <div className="text-center max-w-xl mx-auto mb-8">
          <span className="text-xs font-bold uppercase tracking-widest text-teal-700 block mb-1">
            {isUrdu ? "تکنیکی اور طبی بنیادیں" : "CLINICAL & TECHNICAL FOUNDATIONS"}
          </span>
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
            {isUrdu ? "تسلیم شدہ کلینیکل معیارات پر مبنی" : "Built on Established Healthcare Standards"}
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="surface-card rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-2">
            <div className="w-9 h-9 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
            <h3 className="font-heading font-bold text-sm text-navy-800">HL7® FHIR® Interoperability</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Standardized Patient, Observation, and MedicationStatement resources based on FHIR Release 4.
            </p>
          </div>

          <div className="surface-card rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-2">
            <div className="w-9 h-9 rounded-xl bg-navy-100 text-navy-800 flex items-center justify-center">
              <Lock className="w-5 h-5" />
            </div>
            <h3 className="font-heading font-bold text-sm text-navy-800">SMART on FHIR / OAuth 2.0</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Granular scope-based access tokens separating patient-entered and provider-verified scopes.
            </p>
          </div>

          <div className="surface-card rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-2">
            <div className="w-9 h-9 rounded-xl bg-mutedGreen-100 text-mutedGreen-800 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="font-heading font-bold text-sm text-navy-800">HIPAA-Inspired Security</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Zero plain-text patient telemetry exposure, role-separated portals, and client-side memory safety.
            </p>
          </div>

          <div className="surface-card rounded-2xl p-5 border border-slate-200/90 shadow-2xs space-y-2">
            <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <h3 className="font-heading font-bold text-sm text-navy-800">Schmitt-Thompson Triage</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Clinical decision support protocols governing symptom follow-ups and emergency escalations.
            </p>
          </div>
        </div>
      </section>

      {/* 6. Portal Picker Section (Interactive Prototype Entrance) */}
      <section id="portal-picker" className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 pt-10 scroll-mt-28">
        <div className="text-center max-w-xl mx-auto mb-8">
          <span className="text-xs font-bold uppercase tracking-widest text-teal-700 block mb-1">
            {isUrdu ? "پروٹوٹائپ تک رسائی" : "PROTOTYPE DEMONSTRATION ACCESS"}
          </span>
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
            {isUrdu ? "اپنا پورٹل منتخب کریں" : "Select a Portal to Begin Evaluation"}
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            {isUrdu
              ? "ہر پورٹل اپنے متعلقہ رول کا حقیقی تجربہ پیش کرتا ہے۔"
              : "Choose an entry point below to explore the high-fidelity FYP demonstration flows."}
          </p>
        </div>

        {/* Portal Cards: Deliberate Asymmetric Hierarchy */}
        <div className="space-y-4 max-w-4xl mx-auto">
          {/* Primary Card: Patient Portal */}
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
            className="w-full p-6 sm:p-7 rounded-3xl surface-teal-subtle border-2 border-teal-400/80 hover:border-teal-700 shadow-md hover:shadow-xl transition-all duration-200 text-left flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 group"
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
                    Primary Flow
                  </span>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed max-w-md">
                  {isUrdu
                    ? "روزانہ علامات کا چیک ان، رسک فیڈ بیک اور ذاتی صحت کے رجحانات۔"
                    : "Daily symptom check-in, adaptive clinical interview, risk feedback, and health trends."}
                </p>
                <span className="text-xs font-semibold text-teal-800 block pt-0.5">
                  Demo Patient: Ali Khan (Type 2 Diabetes)
                </span>
              </div>
            </div>

            <div className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-teal-700 text-white font-semibold text-sm shadow-md group-hover:bg-teal-800 transition-colors shrink-0 self-stretch sm:self-auto justify-center">
              <span>{isUrdu ? "داخل ہوں" : "Enter Patient Portal"}</span>
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
              className="p-5 sm:p-6 rounded-2xl surface-card border border-slate-200/90 hover:border-navy-800 hover:shadow-lg transition-all duration-200 text-left flex flex-col justify-between group min-h-[190px]"
            >
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-xl bg-navy-100 text-navy-800 flex items-center justify-center group-hover:bg-navy-800 group-hover:text-white transition-colors duration-200 shadow-2xs">
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
                <span>{isUrdu ? "داخل ہوں" : "Enter Provider Portal"}</span>
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
              className="p-5 sm:p-6 rounded-2xl surface-card border border-slate-200/90 hover:border-slate-700 hover:shadow-lg transition-all duration-200 text-left flex flex-col justify-between group min-h-[190px]"
            >
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center group-hover:bg-slate-700 group-hover:text-white transition-colors duration-200 shadow-2xs">
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
                <span>{isUrdu ? "داخل ہوں" : "Enter Admin Portal"}</span>
                <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
              </div>
            </motion.button>
          </div>
        </div>
      </section>

      {/* 7. Academic FYP Context Note */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 pt-10 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-100 border border-slate-200 text-slate-600 text-xs font-medium">
          <span>FYP-1 Proposal Defense</span>
          <span>•</span>
          <span>FAST-NUCES Department of Computer Science</span>
          <span>•</span>
          <span className="font-semibold text-teal-700">Spring 2026</span>
        </div>
      </div>
    </div>
  );
};
