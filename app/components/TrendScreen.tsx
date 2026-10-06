"use client";

import React, { useState, useEffect } from "react";
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
import { TrendingUp, Home, Activity, Heart, CheckCircle2, History, AlertCircle, Loader2 } from "lucide-react";
import { api, UserCheckinSummaryResponse } from "../lib/api";

// Fixed seeded sample data points across 8 check-in days for mock mode
const mockGlucoseData = [
  { day: "Day 1", value: 114, targetMin: 90, targetMax: 130 },
  { day: "Day 2", value: 110, targetMin: 90, targetMax: 130 },
  { day: "Day 3", value: 118, targetMin: 90, targetMax: 130 },
  { day: "Day 4", value: 108, targetMin: 90, targetMax: 130 },
  { day: "Day 5", value: 112, targetMin: 90, targetMax: 130 },
  { day: "Day 6", value: 106, targetMin: 90, targetMax: 130 },
  { day: "Day 7", value: 110, targetMin: 90, targetMax: 130 },
  { day: "Day 8", value: 109, targetMin: 90, targetMax: 130 },
];

const mockBpData = [
  { day: "Day 1", systolic: 122, diastolic: 82 },
  { day: "Day 2", systolic: 120, diastolic: 80 },
  { day: "Day 3", systolic: 124, diastolic: 81 },
  { day: "Day 4", systolic: 119, diastolic: 79 },
  { day: "Day 5", systolic: 121, diastolic: 80 },
  { day: "Day 6", systolic: 118, diastolic: 78 },
  { day: "Day 7", systolic: 120, diastolic: 80 },
  { day: "Day 8", systolic: 119, diastolic: 80 },
];

const mockAdherenceData = [
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
  const { returnToHomeAndClearRun, checkIn, isLiveMode, t, isUrdu } = useApp();
  const [liveCheckins, setLiveCheckins] = useState<UserCheckinSummaryResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(isLiveMode);

  useEffect(() => {
    if (!isLiveMode) return;
    let isMounted = true;
    api
      .getUserCheckins()
      .then((data) => {
        if (isMounted) {
          setLiveCheckins(data || []);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [isLiveMode]);

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="bg-navy-800 rounded-3xl p-6 sm:p-8 text-white text-center shadow-lg relative overflow-hidden border border-teal-500/30">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-teal-500/25 text-teal-200 text-xs font-bold uppercase tracking-wider mb-2.5">
          <TrendingUp className="w-3.5 h-3.5" />
          <span>{isLiveMode ? "Real Longitudinal History" : "8-Day Clinical Observation Window"}</span>
        </div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold text-white mb-1.5">
          {t.trendsTitle}
        </h1>
        <p className="text-sm text-slate-200 max-w-md mx-auto leading-relaxed">
          {t.trendsSubtitle}
        </p>
      </div>

      {/* Live Mode: Handle Fewer Than 3 Check-ins (The System's Rule) */}
      {isLiveMode && !isLoading && liveCheckins.length < 3 ? (
        <div className="surface-card rounded-3xl p-8 sm:p-10 text-center space-y-4 border border-slate-200 shadow-sm">
          <div className="w-16 h-16 rounded-2xl bg-amber-100 text-amber-800 flex items-center justify-center mx-auto shadow-inner">
            <History className="w-8 h-8" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h2 className="font-heading text-xl font-bold text-navy-800">
              {isUrdu ? "ناکافی تاریخی ڈیٹا" : "Not Enough History Yet"}
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              {t.notEnoughHistory}
            </p>
          </div>

          <div className="pt-3">
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-100 text-slate-700 text-xs font-semibold">
              <span>Recorded Check-ins: {liveCheckins.length} / 3 required</span>
            </span>
          </div>
        </div>
      ) : (
        <>
          {/* Chart 1: Blood Glucose */}
          <div className="surface-card rounded-3xl p-6 shadow-sm space-y-3.5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-3.5">
              <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
                <Activity className="w-5 h-5 text-teal-700" />
                <span>{t.glucoseChartTitle}</span>
              </h2>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-teal-50 text-teal-800 border border-teal-200 self-start sm:self-auto">
                Target Range: 90–130 mg/dL
              </span>
            </div>

            <div className="h-56 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockGlucoseData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="glucoseGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0B6E70" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#0B6E70" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#64748B" }} />
                  <YAxis domain={[80, 150]} tick={{ fontSize: 11, fill: "#64748B" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#16233F",
                      borderRadius: "12px",
                      color: "#FFFFFF",
                      fontSize: "12px",
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
                    dot={{ r: 4, fill: "#0B6E70" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Blood Pressure */}
          <div className="surface-card rounded-3xl p-6 shadow-sm space-y-3.5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-3.5">
              <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
                <Heart className="w-5 h-5 text-amber-800" />
                <span>{t.bloodPressureChartTitle}</span>
              </h2>
              <div className="flex items-center gap-3 text-xs font-semibold text-slate-600">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-navy-800" />
                  {t.systolicLabel} (mmHg)
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-600" />
                  {t.diastolicLabel} (mmHg)
                </span>
              </div>
            </div>

            <div className="h-56 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={mockBpData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#64748B" }} />
                  <YAxis domain={[60, 140]} tick={{ fontSize: 11, fill: "#64748B" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#16233F",
                      borderRadius: "12px",
                      color: "#FFFFFF",
                      fontSize: "12px",
                      border: "none",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="systolic"
                    name={t.systolicLabel}
                    stroke="#16233F"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#16233F" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="diastolic"
                    name={t.diastolicLabel}
                    stroke="#108B8D"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#108B8D" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 3: Medication Adherence */}
          <div className="surface-card rounded-3xl p-6 shadow-sm space-y-3.5">
            <div className="flex items-center justify-between border-b border-slate-200/80 pb-3.5">
              <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-mutedGreen-800" />
                <span>{t.adherenceChartTitle}</span>
              </h2>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-mutedGreen-50 text-mutedGreen-800 border border-mutedGreen-800/30">
                100% Adherent
              </span>
            </div>

            <div className="h-44 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockAdherenceData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="adherenceGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#24623F" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#24623F" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#64748B" }} />
                  <YAxis domain={[0, 110]} tick={{ fontSize: 11, fill: "#64748B" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#16233F",
                      borderRadius: "12px",
                      color: "#FFFFFF",
                      fontSize: "12px",
                      border: "none",
                    }}
                  />
                  <Area
                    type="stepAfter"
                    dataKey="adherence"
                    name={isUrdu ? "پابندی" : "Adherence (%)"}
                    stroke="#24623F"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#adherenceGrad)"
                    dot={{ r: 4, fill: "#24623F" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* Return to Home (End of Flow) */}
      <div className="pt-2">
        <button
          type="button"
          onClick={returnToHomeAndClearRun}
          id="trends-return-home-btn"
          className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <Home className="w-4 h-4" />
          <span>{t.finishBtn}</span>
        </button>
      </div>
    </div>
  );
};
