"use client";

import React, { useState, useEffect, useCallback } from "react";
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
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  Home,
  Activity,
  Heart,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { api, TrendsResponse, TrendSeries } from "../lib/api";
import { getConditionFlags } from "../lib/conditions";

// Fixed seeded sample data points across 8 check-in days for mock / demo mode
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

interface TrendBadgeProps {
  metricLabel: string;
  series?: TrendSeries;
  t: any;
  isUrdu: boolean;
}

export const TrendDirectionBadge: React.FC<TrendBadgeProps> = ({
  metricLabel,
  series,
  t,
}) => {
  if (!series) return null;

  const n = series.n;
  const days = series.window_days;
  const countText = t.trendsReadingsInDays
    .replace("{n}", String(n))
    .replace("{days}", String(days));

  let icon = <Minus className="w-3.5 h-3.5 text-slate-700" />;
  let labelText = t.trendStable;
  let badgeStyle = "bg-slate-100 text-slate-800 border-slate-300";

  if (series.direction === "rising") {
    icon = <TrendingUp className="w-3.5 h-3.5 text-amber-700" />;
    labelText = t.trendRising;
    badgeStyle = "bg-amber-50 text-amber-900 border-amber-300";
  } else if (series.direction === "falling") {
    icon = <TrendingDown className="w-3.5 h-3.5 text-teal-700" />;
    labelText = t.trendFalling;
    badgeStyle = "bg-teal-50 text-teal-900 border-teal-300";
  } else if (series.direction === "not_enough_history") {
    icon = <Clock className="w-3.5 h-3.5 text-slate-500" />;
    labelText = t.trendNotEnoughHistory;
    badgeStyle = "bg-slate-100 text-slate-700 border-slate-200";
  }

  const ariaLabel = `${metricLabel} ${labelText}, ${countText}`;

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold ${badgeStyle}`}
      aria-label={ariaLabel}
      role="status"
    >
      <span aria-hidden="true">{icon}</span>
      <span>{labelText}</span>
      <span className="text-slate-400 font-normal" aria-hidden="true">•</span>
      <bdi className="font-medium text-slate-600">{countText}</bdi>
    </div>
  );
};

export const TrendScreen = () => {
  const { returnToHomeAndClearRun, profile, liveProfile, isLiveMode, t, isUrdu } = useApp();
  const [liveTrends, setLiveTrends] = useState<TrendsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(isLiveMode);
  const [error, setError] = useState<string | null>(null);

  const conditionFlags = getConditionFlags(isLiveMode ? liveProfile?.conditions : profile.conditions);

  const fetchTrends = useCallback(() => {
    if (!isLiveMode) return;
    setIsLoading(true);
    setError(null);

    // Live mode always retrieves real trends from backend API
    api
      .getMyTrends(30)
      .then((data) => {
        setLiveTrends(data);
        setIsLoading(false);
      })
      .catch((err) => {
        setError(err?.message || "Failed to load trends");
        setIsLoading(false);
      });
  }, [isLiveMode]);

  useEffect(() => {
    fetchTrends();
  }, [fetchTrends]);

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(isUrdu ? "ur-PK" : "en-US", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return iso;
    }
  };

  const glucoseSeries = liveTrends?.trends?.glucose;
  const systolicSeries = liveTrends?.trends?.blood_pressure_systolic;
  const diastolicSeries = liveTrends?.trends?.blood_pressure_diastolic;

  // Chart Rendering for Glucose
  const renderGlucoseChart = () => {
    const isLive = isLiveMode;
    const hasReadings = isLive && (glucoseSeries?.values?.length ?? 0) > 0;
    const chartData: Array<{ day: string; value: number }> = isLive
      ? (hasReadings && glucoseSeries
          ? glucoseSeries.values.map((v) => ({
              day: formatDate(v.at),
              value: v.value,
            }))
          : [])
      : mockGlucoseData;

    return (
      <div key="glucose-chart" className="surface-card rounded-3xl p-6 shadow-sm space-y-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-3.5">
          <div className="space-y-1">
            <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
              <Activity className="w-5 h-5 text-teal-700" />
              <span>{t.glucoseChartTitle}</span>
            </h2>
            {isLive && glucoseSeries && (
              <div className="pt-1">
                <TrendDirectionBadge
                  metricLabel={t.glucoseChartTitle}
                  series={glucoseSeries}
                  t={t}
                  isUrdu={isUrdu}
                />
              </div>
            )}
          </div>
          <span className="text-xs font-bold px-3 py-1 rounded-full bg-teal-50 text-teal-800 border border-teal-200 self-start sm:self-auto">
            {t.targetRangeLabel}: <bdi>90–130 mg/dL</bdi>
          </span>
        </div>

        {isLive && glucoseSeries?.direction === "not_enough_history" && (
          <p className="text-xs text-slate-600 bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
            {t.trendNotEnoughExplain}
          </p>
        )}

        {isLive && chartData.length === 0 ? (
          <div className="h-44 flex flex-col items-center justify-center text-center p-4 rounded-2xl bg-slate-50 border border-dashed border-slate-200 space-y-1.5">
            <Clock className="w-6 h-6 text-slate-400" />
            <p className="text-xs font-bold text-slate-700">{t.trendNotEnoughHistory}</p>
            <p className="text-[11px] text-slate-500 max-w-sm">
              {t.trendNotEnoughExplain}
            </p>
          </div>
        ) : (
          <div className="h-56 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="glucoseGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0B6E70" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#0B6E70" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#64748B" }} />
                <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#64748B" }} />
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
        )}
      </div>
    );
  };

  // Chart Rendering for Blood Pressure
  const renderBpChart = () => {
    const isLive = isLiveMode;
    const hasSys = isLive && (systolicSeries?.values?.length ?? 0) > 0;
    const hasDia = isLive && (diastolicSeries?.values?.length ?? 0) > 0;
    let chartData: Array<{ day: string; systolic?: number; diastolic?: number }> = [];

    if (!isLive) {
      chartData = mockBpData;
    } else if (hasSys || hasDia) {
      const map = new Map<string, { day: string; systolic?: number; diastolic?: number }>();
      (systolicSeries?.values || []).forEach((v) => {
        const d = formatDate(v.at);
        const cur = map.get(d) || { day: d };
        cur.systolic = v.value;
        map.set(d, cur);
      });
      (diastolicSeries?.values || []).forEach((v) => {
        const d = formatDate(v.at);
        const cur = map.get(d) || { day: d };
        cur.diastolic = v.value;
        map.set(d, cur);
      });
      chartData = Array.from(map.values());
    }

    return (
      <div key="bp-chart" className="surface-card rounded-3xl p-6 shadow-sm space-y-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-3.5">
          <div className="space-y-1">
            <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
              <Heart className="w-5 h-5 text-amber-800" />
              <span>{t.bloodPressureChartTitle}</span>
            </h2>
            {isLive && (systolicSeries || diastolicSeries) && (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {systolicSeries && (
                  <TrendDirectionBadge
                    metricLabel={t.systolicLabel}
                    series={systolicSeries}
                    t={t}
                    isUrdu={isUrdu}
                  />
                )}
                {diastolicSeries && (
                  <TrendDirectionBadge
                    metricLabel={t.diastolicLabel}
                    series={diastolicSeries}
                    t={t}
                    isUrdu={isUrdu}
                  />
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs font-semibold text-slate-600">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-navy-800" />
              {t.systolicLabel} (<bdi>mmHg</bdi>)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-teal-600" />
              {t.diastolicLabel} (<bdi>mmHg</bdi>)
            </span>
          </div>
        </div>

        {isLive && (systolicSeries?.direction === "not_enough_history" || diastolicSeries?.direction === "not_enough_history") && (
          <p className="text-xs text-slate-600 bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
            {t.trendNotEnoughExplain}
          </p>
        )}

        {isLive && chartData.length === 0 ? (
          <div className="h-44 flex flex-col items-center justify-center text-center p-4 rounded-2xl bg-slate-50 border border-dashed border-slate-200 space-y-1.5">
            <Clock className="w-6 h-6 text-slate-400" />
            <p className="text-xs font-bold text-slate-700">{t.trendNotEnoughHistory}</p>
            <p className="text-[11px] text-slate-500 max-w-sm">
              {t.trendNotEnoughExplain}
            </p>
          </div>
        ) : (
          <div className="h-56 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#64748B" }} />
                <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#64748B" }} />
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
        )}
      </div>
    );
  };

  const renderAdherenceChart = () => (
    <div key="adherence-chart" className="surface-card rounded-3xl p-6 shadow-sm space-y-3.5">
      <div className="flex items-center justify-between border-b border-slate-200/80 pb-3.5">
        <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-mutedGreen-800" />
          <span>{t.adherenceChartTitle}</span>
        </h2>
        <span className="text-xs font-bold px-3 py-1 rounded-full bg-mutedGreen-50 text-mutedGreen-800 border border-mutedGreen-800/30">
          <bdi>100% Adherent</bdi>
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
  );

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="bg-navy-800 rounded-3xl p-6 sm:p-8 text-white text-center shadow-lg relative overflow-hidden border border-teal-500/30">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-teal-500/25 text-teal-200 text-xs font-bold uppercase tracking-wider mb-2.5">
          <TrendingUp className="w-3.5 h-3.5" />
          <span>{isLiveMode ? t.trendLongitudinalTrajectory : t.clinicalObservationWindow8Day}</span>
        </div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold text-white mb-1.5">
          {t.trendsTitle}
        </h1>
        <p className="text-sm text-slate-200 max-w-md mx-auto leading-relaxed">
          {t.trendsSubtitle}
        </p>
      </div>

      {isLiveMode && isLoading ? (
        /* Loading Skeleton */
        <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading trends">
          <div className="surface-card rounded-3xl p-8 h-60 bg-slate-100 flex flex-col items-center justify-center space-y-3">
            <RefreshCw className="w-8 h-8 text-slate-400 animate-spin" />
            <p className="text-sm font-semibold text-slate-500">
              {isUrdu ? "رجحانات لوڈ ہو رہے ہیں..." : "Loading health trends..."}
            </p>
          </div>
          <div className="surface-card rounded-3xl p-8 h-60 bg-slate-100" />
        </div>
      ) : isLiveMode && error ? (
        /* Error State with Retry Button */
        <div className="surface-card rounded-3xl p-8 sm:p-10 text-center space-y-4 border border-red-200 bg-red-50/40 shadow-sm" role="alert">
          <div className="w-16 h-16 rounded-2xl bg-red-100 text-red-800 flex items-center justify-center mx-auto shadow-inner">
            <AlertCircle className="w-8 h-8" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h2 className="font-heading text-xl font-bold text-navy-800">
              {t.trendsErrorTitle}
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              {error}
            </p>
          </div>
          <div className="pt-2">
            <button
              type="button"
              onClick={fetchTrends}
              id="trends-retry-btn"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-xs rounded-xl shadow-md transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              <span>{t.trendsErrorRetry}</span>
            </button>
          </div>
        </div>
      ) : (
        <>
          {conditionFlags.hasHypertension ? (
            <>
              {renderBpChart()}
              {conditionFlags.hasDiabetes && renderGlucoseChart()}
              {!isLiveMode && renderAdherenceChart()}
            </>
          ) : (
            <>
              {renderGlucoseChart()}
              {renderBpChart()}
              {!isLiveMode && renderAdherenceChart()}
            </>
          )}
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
