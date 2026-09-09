"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { RiskBadge } from "../RiskBadge";
import {
  ArrowLeft,
  CheckCircle2,
  Activity,
  Heart,
  HelpCircle,
  Info,
  Calendar,
  User,
  Pill,
  ShieldCheck,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { FhirSourceBadge } from "../FhirSourceBadge";

const ahmedGlucoseData = [
  { day: "Day 1", value: 108 },
  { day: "Day 2", value: 112 },
  { day: "Day 3", value: 105 },
  { day: "Day 4", value: 110 },
  { day: "Day 5", value: 107 },
  { day: "Day 6", value: 111 },
  { day: "Day 7", value: 109 },
  { day: "Day 8", value: 108 },
];

const ahmedBpData = [
  { day: "Day 1", systolic: 118, diastolic: 78 },
  { day: "Day 2", systolic: 120, diastolic: 80 },
  { day: "Day 3", systolic: 119, diastolic: 79 },
  { day: "Day 4", systolic: 121, diastolic: 80 },
  { day: "Day 5", systolic: 118, diastolic: 78 },
  { day: "Day 6", systolic: 120, diastolic: 80 },
  { day: "Day 7", systolic: 119, diastolic: 79 },
  { day: "Day 8", systolic: 120, diastolic: 80 },
];

export const PatientDetailScreen = () => {
  const {
    selectedPatient,
    setProviderScreen,
    acknowledgePatient,
    acknowledgedPatients,
    resolveCase,
    connectionMode,
    profile,
    t,
    isUrdu,
  } = useApp();

  const patientName = selectedPatient || "Ahmed";
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const isAcknowledged = acknowledgedPatients.includes(patientName);

  const handleAcknowledge = () => {
    acknowledgePatient(patientName);
    resolveCase(patientName);
    setToastMessage(t.caseAcknowledgedToast);
    setTimeout(() => {
      setToastMessage(null);
    }, 2500);
  };

  const isSara = patientName === "Sara Ahmed";

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn py-2" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Toast */}
      {toastMessage && (
        <div className="p-4 rounded-2xl bg-mutedGreen-100 border border-mutedGreen-800 text-mutedGreen-900 text-sm font-bold shadow-lg flex items-center justify-between animate-slideUp">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-mutedGreen-800 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setProviderScreen("dashboard")}
            id="patient-detail-back-btn"
            className="w-11 h-11 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 flex items-center justify-center transition-colors shadow-xs"
          >
            <ArrowLeft className={`w-5 h-5 ${isUrdu ? "rotate-180" : ""}`} />
          </button>
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
              {patientName}
            </h1>
            <span className="text-xs font-semibold text-slate-500">
              {isSara ? "62y F • Hypertension • Baseline ID: PT-01934" : "45y M • Type 2 Diabetes & Hypertension • Baseline ID: PT-00318"}
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleAcknowledge}
          id="patient-acknowledge-btn"
          className={`min-h-[44px] py-2.5 px-5 rounded-xl font-bold text-xs sm:text-sm transition-all flex items-center gap-2 ${
            isAcknowledged
              ? "bg-mutedGreen-100 text-mutedGreen-800 border border-mutedGreen-800/30"
              : "bg-teal-700 hover:bg-teal-600 text-white shadow-sm active:scale-[0.98]"
          }`}
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>{isAcknowledged ? "Acknowledged ✓" : t.acknowledge}</span>
        </button>
      </div>

      {/* Sara Ahmed Incomplete Check-in Notice */}
      {isSara && (
        <div className="p-5 rounded-2xl bg-amber-50 border border-amber-300 space-y-2">
          <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
            <Info className="w-4 h-4 text-amber-700" />
            <span>{t.incompleteCheckInTitle}</span>
          </div>
          <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
            {t.incompleteCheckInDesc}
          </p>
        </div>
      )}

      {/* Overview Card */}
      <div className="surface-card rounded-3xl p-6 sm:p-7 shadow-sm space-y-5">
        <div className="flex items-center justify-between border-b border-slate-200/80 pb-4">
          <span className="font-heading text-base font-bold text-navy-800">
            Automated Clinical Assessment
          </span>
          {/* Reusable RiskBadge */}
          <RiskBadge riskLevel={isSara ? "moderate" : "low"} size="md" />
        </div>

        {/* Contributing Factors & SHAP Disclaimer */}
        <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-navy-800 uppercase tracking-wider">
            <Activity className="w-4 h-4 text-teal-700" />
            <span>{t.contributingFactorsTitle}</span>
          </div>

          <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 flex items-start gap-2.5 text-xs text-teal-900 leading-snug">
            <Info className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span className="font-medium">{t.shapDisclaimer}</span>
          </div>

          <ul className="space-y-2 text-xs sm:text-sm text-slate-700 pt-1">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-mutedGreen-800 shrink-0" />
              <span>
                {isSara
                  ? "Baseline BP stable at 128/84 mmHg; pending medication log"
                  : "Mean fasting blood glucose stable at 108 mg/dL (100% in-range)"}
              </span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-mutedGreen-800 shrink-0" />
              <span>
                {isSara
                  ? "No reported acute distress or symptoms in previous 14 days"
                  : "No missed medication doses reported in last 30 days"}
              </span>
            </li>
          </ul>
        </div>

        {/* Clinical Regimen & EHR Diagnoses Card */}
        <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200/80 pb-3">
            <div className="flex items-center gap-2 text-xs font-bold text-navy-800 uppercase tracking-wider">
              <Pill className="w-4 h-4 text-teal-700" />
              <span>Prescription Regimen & Sourced Diagnoses</span>
            </div>
            {connectionMode === "fhir" && <FhirSourceBadge />}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
            {/* Conditions */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                Confirmed Diagnoses
              </span>
              <div className="space-y-1 font-semibold text-navy-800">
                {patientName === "Sara Ahmed" ? (
                  <div className="flex items-center justify-between">
                    <span>• Essential Hypertension</span>
                    {connectionMode === "fhir" && <FhirSourceBadge />}
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <span>• Type 2 Diabetes Mellitus</span>
                      {connectionMode === "fhir" && <FhirSourceBadge />}
                    </div>
                    <div className="flex items-center justify-between">
                      <span>• Essential Hypertension</span>
                      {connectionMode === "fhir" && <FhirSourceBadge />}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Medications */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                Active Medications
              </span>
              <div className="space-y-1 text-slate-700">
                {patientName === "Sara Ahmed" ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span>• Amlodipine 5mg (Daily)</span>
                      {connectionMode === "fhir" && <FhirSourceBadge />}
                    </div>
                    <div className="flex items-center justify-between">
                      <span>• Hydrochlorothiazide 12.5mg</span>
                      {connectionMode === "fhir" && <FhirSourceBadge />}
                    </div>
                  </>
                ) : (
                  (patientName === "Ali Khan" ? profile.medications : [
                    "Metformin 500mg (Twice daily)",
                    "Lisinopril 10mg (Once daily)",
                    "Atorvastatin 20mg (Once daily, evening)",
                    "Aspirin 81mg (Once daily)",
                  ]).map((med, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span>• {med}</span>
                      {connectionMode === "fhir" && <FhirSourceBadge />}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Multi-Day Observation Charts */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-2">
          {/* Glucose Chart */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-navy-800">
              <span>{t.glucoseChartTitle}</span>
              <span className="text-[10px] text-teal-800 bg-teal-100/60 px-2 py-0.5 rounded font-bold">
                Target: 90–130 mg/dL
              </span>
            </div>
            <div className="h-44 w-full pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={ahmedGlucoseData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="ahmedGlucGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0B6E70" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#0B6E70" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#64748B" }} />
                  <YAxis domain={[80, 140]} tick={{ fontSize: 10, fill: "#64748B" }} />
                  <Tooltip />
                  <Area type="monotone" dataKey="value" stroke="#0B6E70" strokeWidth={2.5} fill="url(#ahmedGlucGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Blood Pressure Chart */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-navy-800">
              <span>{t.bloodPressureChartTitle}</span>
              <span className="text-[10px] text-slate-500 font-semibold">Systolic / Diastolic</span>
            </div>
            <div className="h-44 w-full pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={ahmedBpData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#64748B" }} />
                  <YAxis domain={[60, 140]} tick={{ fontSize: 10, fill: "#64748B" }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="systolic" stroke="#16233F" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="diastolic" stroke="#108B8D" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
