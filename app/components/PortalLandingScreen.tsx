"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import { User, Stethoscope, Shield, Activity, ArrowRight } from "lucide-react";

export const PortalLandingScreen = () => {
  const { setPortal, setScreen, setProviderScreen, setAdminScreen, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6 animate-fadeIn py-4">
      {/* Brand Hero */}
      <div className="text-center space-y-2">
        <div className="w-14 h-14 rounded-2xl bg-navy-800 border border-teal-500/40 flex items-center justify-center mx-auto shadow-lg text-teal-400">
          <Activity className="w-8 h-8" />
        </div>
        <h1 className="font-heading text-3xl font-bold text-navy-800">
          {isUrdu ? "کرونک کیئر اے آئی کلینیکل سوٹ" : "ChronicCare AI Clinical Suite"}
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 max-w-md mx-auto">
          {isUrdu
            ? "دائمی نگہداشت کا انٹیگریٹڈ پلیٹ فارم — مریض، ڈاکٹر اور ایڈمنسٹریشن کے لیے۔"
            : "Integrated chronic disease care platform for Patients, Clinical Providers, and System Administrators."}
        </p>
      </div>

      {/* 3 Portal Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        {/* Card 1: Patient Portal */}
        <button
          type="button"
          onClick={() => {
            setPortal("patient");
            setScreen("login");
          }}
          id="select-patient-portal-btn"
          className="p-5 rounded-2xl border-2 border-slate-200 bg-white hover:border-teal-700 hover:shadow-xl transition-all text-left flex flex-col justify-between group active:scale-[0.98]"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center group-hover:bg-teal-700 group-hover:text-white transition-colors">
              <User className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-heading text-base font-bold text-navy-800">
                {t.patientPortal}
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider text-teal-700 block mt-0.5">
                Ali Khan (Patient)
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              {isUrdu
                ? "روزانہ علامات کا چیک ان، رسک اسکورنگ اور ذاتی ہیلتھ ٹرینڈز۔"
                : "Daily symptom check-in, adaptive clinical interview, risk feedback, and trends."}
            </p>
          </div>
          <div className="pt-4 flex items-center gap-1.5 text-xs font-semibold text-teal-700">
            <span>{isUrdu ? "داخل ہوں" : "Enter Portal"}</span>
            <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
          </div>
        </button>

        {/* Card 2: Provider Portal */}
        <button
          type="button"
          onClick={() => {
            setPortal("provider");
            setProviderScreen("login");
          }}
          id="select-provider-portal-btn"
          className="p-5 rounded-2xl border-2 border-slate-200 bg-white hover:border-navy-800 hover:shadow-xl transition-all text-left flex flex-col justify-between group active:scale-[0.98]"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-navy-50 text-navy-800 flex items-center justify-center group-hover:bg-navy-800 group-hover:text-white transition-colors">
              <Stethoscope className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-heading text-base font-bold text-navy-800">
                {t.providerPortal}
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider text-navy-800 block mt-0.5">
                Dr. Sana Malik
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              {isUrdu
                ? "مریضوں کی ریویو کیو، طبی تضادات کے الرٹس اور فالو اپ اپوائنٹمنٹس۔"
                : "Clinical triage, live counters, review queue, reconciliation alert resolution, and appointment booking."}
            </p>
          </div>
          <div className="pt-4 flex items-center gap-1.5 text-xs font-semibold text-navy-800">
            <span>{isUrdu ? "داخل ہوں" : "Enter Portal"}</span>
            <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
          </div>
        </button>

        {/* Card 3: Admin Portal */}
        <button
          type="button"
          onClick={() => {
            setPortal("admin");
            setAdminScreen("login");
          }}
          id="select-admin-portal-btn"
          className="p-5 rounded-2xl border-2 border-slate-200 bg-white hover:border-slate-600 hover:shadow-xl transition-all text-left flex flex-col justify-between group active:scale-[0.98]"
        >
          <div className="space-y-3">
            <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center group-hover:bg-slate-700 group-hover:text-white transition-colors">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-heading text-base font-bold text-navy-800">
                {t.adminPortal}
              </h2>
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-600 block mt-0.5">
                System Administrator
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              {isUrdu
                ? "پلیٹ فارم میٹرکس، صارفین کا انتظام اور سیکیورٹی آڈٹ لاگ۔"
                : "System telemetry, user directory, system alerts counter, and compliance audit trail."}
            </p>
          </div>
          <div className="pt-4 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
            <span>{isUrdu ? "داخل ہوں" : "Enter Portal"}</span>
            <ArrowRight className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
          </div>
        </button>
      </div>
    </div>
  );
};
