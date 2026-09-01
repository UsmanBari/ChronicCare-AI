"use client";

import React from "react";
import { useApp } from "../context/AppContext";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { TrendingUp, Home, Activity, Heart, CheckCircle2 } from "lucide-react";

// Fixed seeded sample data points across 8 check-in days
const glucoseData = [
  { day: "Day 1", value: 114, targetMin: 90, targetMax: 130 },
  { day: "Day 2", value: 110, targetMin: 90, targetMax: 130 },
  { day: "Day 3", value: 118, targetMin: 90, targetMax: 130 },
  { day: "Day 4", value: 108, targetMin: 90, targetMax: 130 },
  { day: "Day 5", value: 112, targetMin: 90, targetMax: 130 },
  { day: "Day 6", value: 106, targetMin: 90, targetMax: 130 },
  { day: "Day 7", value: 110, targetMin: 90, targetMax: 130 },
  { day: "Day 8", value: 109, targetMin: 90, targetMax: 130 },
];

const bpData = [
  { day: "Day 1", systolic: 122, diastolic: 82 },
  { day: "Day 2", systolic: 120, diastolic: 80 },
  { day: "Day 3", systolic: 124, diastolic: 81 },
  { day: "Day 4", systolic: 119, diastolic: 79 },
  { day: "Day 5", systolic: 121, diastolic: 80 },
  { day: "Day 6", systolic: 118, diastolic: 78 },
  { day: "Day 7", systolic: 120, diastolic: 80 },
  { day: "Day 8", systolic: 119, diastolic: 80 },
];

const adherenceData = [
  { day: "Day 1", adherence: 100 },
  { day: "Day 2", adherence: 100 },
  { day: "Day 3", adherence: 100 },
  { day: "Day 4", adherence: 100 },
  { day: "Day 5", adherence: 100 },
  { day: "Day 6", adherence: 100 },
  { day: "Day 7", adherence: 100 },
  { day: "Day 8", adherence: 100 },
];

export const TrendScreen = () => {
  const { resetSession, t, isUrdu } = useApp();

  return (
    <div className="w-full max-w-xl mx-auto space-y-5 animate-fadeIn">
      {/* Header */}
      <div className="bg-navy-800 rounded-2xl p-6 text-white text-center shadow-lg relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-teal-500/15 rounded-full blur-2xl pointer-events-none" />
        <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-500/20 text-teal-300 text-[10px] font-bold uppercase tracking-wider mb-2">
          <TrendingUp className="w-3 h-3" />
          <span>8-Day Observation Window</span>
        </div>
        <h1 className="font-heading text-2xl font-bold text-white mb-1">
          {t.trendsTitle}
        </h1>
        <p className="text-xs text-slate-300 max-w-md mx-auto">
          {t.trendsSubtitle}
        </p>
      </div>

      {/* Chart 1: Blood Glucose */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
          <h2 className="font-heading text-sm font-bold text-navy-800 flex items-center gap-2">
            <Activity className="w-4 h-4 text-teal-700" />
            <span>{t.glucoseChartTitle}</span>
          </h2>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200/60">
            Target: 90–130 mg/dL
          </span>
        </div>

        <div className="h-48 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={glucoseData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="glucoseGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0B6E70" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#0B6E70" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#64748B" }} />
              <YAxis domain={[80, 150]} tick={{ fontSize: 10, fill: "#64748B" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#16233F",
                  borderRadius: "8px",
                  color: "#FFFFFF",
                  fontSize: "11px",
                  border: "none",
                }}
              />
              <Area
                type="monotone"
                dataKey="value"
                name={isUrdu ? "بلڈ شوگر" : "Blood Glucose"}
                stroke="#0B6E70"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#glucoseGrad)"
                dot={{ r: 3, fill: "#0B6E70" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 2: Blood Pressure */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
          <h2 className="font-heading text-sm font-bold text-navy-800 flex items-center gap-2">
            <Heart className="w-4 h-4 text-amber-800" />
            <span>{t.bloodPressureChartTitle}</span>
          </h2>
          <div className="flex items-center gap-2 text-[10px] font-semibold text-slate-500">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-navy-800" />
              {t.systolicLabel}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-teal-600" />
              {t.diastolicLabel}
            </span>
          </div>
        </div>

        <div className="h-48 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={bpData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#64748B" }} />
              <YAxis domain={[60, 140]} tick={{ fontSize: 10, fill: "#64748B" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#16233F",
                  borderRadius: "8px",
                  color: "#FFFFFF",
                  fontSize: "11px",
                  border: "none",
                }}
              />
              <Line
                type="monotone"
                dataKey="systolic"
                name={t.systolicLabel}
                stroke="#16233F"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "#16233F" }}
              />
              <Line
                type="monotone"
                dataKey="diastolic"
                name={t.diastolicLabel}
                stroke="#108B8D"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "#108B8D" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 3: Medication Adherence */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
          <h2 className="font-heading text-sm font-bold text-navy-800 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-mutedGreen-800" />
            <span>{t.adherenceChartTitle}</span>
          </h2>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-mutedGreen-50 text-mutedGreen-800 border border-mutedGreen-800/30">
            100% Adherent
          </span>
        </div>

        <div className="h-36 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={adherenceData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="adherenceGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#24623F" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#24623F" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "#64748B" }} />
              <YAxis domain={[0, 110]} tick={{ fontSize: 10, fill: "#64748B" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#16233F",
                  borderRadius: "8px",
                  color: "#FFFFFF",
                  fontSize: "11px",
                  border: "none",
                }}
              />
              <Area
                type="stepAfter"
                dataKey="adherence"
                name={isUrdu ? "پابندی" : "Adherence"}
                stroke="#24623F"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#adherenceGrad)"
                dot={{ r: 3, fill: "#24623F" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Return to Home (End of M2 Flow) */}
      <div className="pt-2">
        <button
          type="button"
          onClick={resetSession}
          id="trends-return-home-btn"
          className="w-full py-3.5 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <Home className="w-4 h-4" />
          <span>{t.finishBtn}</span>
        </button>
      </div>
    </div>
  );
};
