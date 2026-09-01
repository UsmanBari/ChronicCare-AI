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
    <div className="w-full max-w-3xl mx-auto space-y-5 animate-fadeIn py-2">
      {/* Toast */}
      {toastMessage && (
        <div className="p-3.5 rounded-xl bg-mutedGreen-100 border border-mutedGreen-800 text-mutedGreen-800 text-xs font-bold shadow-lg flex items-center justify-between animate-slideUp">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-mutedGreen-800 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setProviderScreen("dashboard")}
            id="patient-detail-back-btn"
            className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 transition-colors"
          >
            <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
          </button>
          <div>
            <h1 className="font-heading text-2xl font-bold text-navy-800">
              {patientName}
            </h1>
            <span className="text-xs text-slate-500">
              {isSara ? "62y F • Hypertension" : "45y M • Type 2 Diabetes & Hypertension"}
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleAcknowledge}
          id="patient-acknowledge-btn"
          className={`py-2 px-4 rounded-xl font-bold text-xs transition-all flex items-center gap-1.5 ${
            isAcknowledged
              ? "bg-mutedGreen-100 text-mutedGreen-800 border border-mutedGreen-800/30"
              : "bg-teal-700 hover:bg-teal-600 text-white shadow-sm active:scale-[0.98]"
          }`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>{isAcknowledged ? "Acknowledged ✓" : t.acknowledge}</span>
        </button>
      </div>

      {/* Sara Ahmed Incomplete Check-in Notice */}
      {isSara && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 space-y-2">
          <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
            <Info className="w-4 h-4 text-amber-700" />
            <span>{t.incompleteCheckInTitle}</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {t.incompleteCheckInDesc}
          </p>
        </div>
      )}

      {/* Overview Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <span className="font-heading text-sm font-bold text-navy-800">
            Automated Clinical Assessment
          </span>
          {/* Reusable RiskBadge */}
          <RiskBadge riskLevel={isSara ? "moderate" : "low"} size="md" />
        </div>

        {/* Contributing Factors & SHAP Disclaimer */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-bold text-navy-800">
            <Activity className="w-4 h-4 text-teal-700" />
            <span>{t.contributingFactorsTitle}</span>
          </div>

          <div className="p-2.5 rounded-lg bg-teal-50 border border-teal-200 flex items-start gap-2 text-[11px] text-teal-900 leading-snug">
            <Info className="w-3.5 h-3.5 text-teal-700 shrink-0 mt-0.5" />
            <span className="font-medium">{t.shapDisclaimer}</span>
          </div>

          <ul className="space-y-1.5 text-xs text-slate-700 pt-1">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-mutedGreen-800 shrink-0" />
              <span>
                {isSara
                  ? "Baseline BP stable at 128/84 mmHg; pending medication log"
                  : "Mean fasting blood glucose stable at 108 mg/dL (100% in-range)"}
              </span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-mutedGreen-800 shrink-0" />
              <span>
                {isSara
                  ? "No reported acute distress or symptoms in previous 14 days"
                  : "No missed medication doses reported in last 30 days"}
              </span>
            </li>
          </ul>
        </div>

        {/* Multi-Day Observation Charts */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          {/* Glucose Chart */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-navy-800">
              <span>{t.glucoseChartTitle}</span>
              <span className="text-[10px] text-teal-800 bg-teal-100/60 px-2 py-0.5 rounded">
                Target: 90–130
              </span>
            </div>
            <div className="h-36 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={ahmedGlucoseData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="ahmedGlucGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0B6E70" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#0B6E70" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="day" tick={{ fontSize: 9, fill: "#64748B" }} />
                  <YAxis domain={[80, 140]} tick={{ fontSize: 9, fill: "#64748B" }} />
                  <Tooltip />
                  <Area type="monotone" dataKey="value" stroke="#0B6E70" strokeWidth={2} fill="url(#ahmedGlucGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Blood Pressure Chart */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-navy-800">
              <span>{t.bloodPressureChartTitle}</span>
              <span className="text-[10px] text-slate-500 font-normal">Systolic / Diastolic</span>
            </div>
            <div className="h-36 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={ahmedBpData} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="day" tick={{ fontSize: 9, fill: "#64748B" }} />
                  <YAxis domain={[60, 140]} tick={{ fontSize: 9, fill: "#64748B" }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="systolic" stroke="#16233F" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="diastolic" stroke="#108B8D" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
