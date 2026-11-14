"use client";

import React, { useState, useEffect } from "react";
import { api, AdminConfigStatusResponse } from "../../lib/api";
import { useApp } from "../../context/AppContext";
import {
  Sliders,
  KeyRound,
  Activity,
  Cpu,
  RefreshCw,
  CheckCircle,
  XCircle,
  ShieldAlert,
} from "lucide-react";

export const AdminConfigStatusSection: React.FC = () => {
  const { isLiveMode, t, isUrdu } = useApp();
  const [data, setData] = useState<AdminConfigStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = () => {
    if (!isLiveMode) {
      // Mock data for demo
      setData({
        settings: [
          { name: "FIREBASE_PROJECT_ID", set: true },
          { name: "DB_BACKEND", set: true },
          { name: "FHIR_BASE_URL", set: true },
          { name: "DEMO_ROLE_MAP", set: true },
        ],
        flags: {
          RISK_ENABLED: false,
          RISK_CAN_RAISE: false,
          EXPLAIN_ENABLED: false,
          EXPLAIN_MODE: "background",
          EXPLAIN_LLM_CONDITIONS: "hypertension",
          EXPLAIN_LLM_LANGUAGES: "en,ur,roman_ur",
          OCR_ENABLED: false,
          DANGER_WORDGROUPS_ENABLED: false,
          ORCHESTRATOR: "direct",
          INTERVIEW_ENGINE: "v2",
          LLM_PROVIDER: "auto",
          SCREENING_REMINDER_INTERVAL_DAYS: "90",
          TREND_CAN_RAISE: false,
          RISK_PATIENT_VISIBLE: false,
          NO_READING_SYMPTOM_RAISE: false,
          RISK_RAISE_COOLDOWN_DAYS: "0",
          RETRIEVER: "bm25",
        },
        keys_and_models: {
          GROQ_API_KEY: "SET",
          GROQ_MODEL: "SET",
          GEMINI_API_KEY: "SET",
          GEMINI_MODEL: "SET",
        },
        explainer_metrics: {
          tokens_used_today: 0,
          tokens_used_by_provider: { groq: 0, gemini: 0 },
          cap: 150000,
          caps: { groq: 150000, gemini: 150000 },
          breaker_state: "closed",
          breaker_states: { groq: "closed", gemini: "closed" },
          cache_size: 0,
          cache_hits: 0,
          cache_misses: 0,
          llm_calls: 0,
          llm_calls_by_provider: { groq: 0, gemini: 0 },
          queue_length: 0,
          mode: "background",
          template_fallbacks_by_reason: {},
        },
      });
      return;
    }

    setLoading(true);
    setError(null);
    api
      .getAdminConfigStatus()
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load config status");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLiveMode]);

  const flags = data?.flags || {};
  const keysAndModels = data?.keys_and_models || {};
  const metrics = data?.explainer_metrics || {};

  return (
    <div
      data-testid="admin-config-status-section"
      className="bg-white rounded-3xl p-6 sm:p-7 shadow-xs border border-slate-200/90 space-y-6"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200/70">
        <div>
          <h2 className="font-heading text-lg font-bold text-navy-800 flex items-center gap-2.5">
            <Sliders className="w-5 h-5 text-teal-700" />
            <span>{t.adminConfigTitle || "System Configuration & Guards Status"}</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            {t.adminConfigSubtitle ||
              "Live runtime feature flags, LLM keys presence, and explainer performance metrics"}
          </p>
        </div>
        <button
          type="button"
          onClick={fetchStatus}
          disabled={loading}
          data-testid="refresh-config-btn"
          className="self-start sm:self-auto px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold inline-flex items-center gap-2 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>{loading ? "Refreshing..." : "Refresh"}</span>
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-50 text-red-700 text-xs border border-red-200">
          {error}
        </div>
      )}

      {/* Grid: 3 Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Feature Flags */}
        <div className="rounded-2xl border border-slate-200/80 p-4 bg-slate-50/50 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-teal-700" />
            <span>Feature Flags</span>
          </h3>
          <div className="space-y-2 text-xs divide-y divide-slate-200/60">
            {Object.entries(flags).map(([k, v]) => {
              const isBool = typeof v === "boolean";
              const isPositive = isBool ? v : v === "background" || v === "direct" || v === "auto";
              return (
                <div key={k} className="pt-2 first:pt-0 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-[11px] text-slate-700">{k}</span>
                    {k === "NO_READING_SYMPTOM_RAISE" && (
                      <span className="text-[9px] bg-teal-100 text-teal-900 px-1.5 py-0.5 rounded font-bold uppercase tracking-wide">
                        Approved by the doctor on record
                      </span>
                    )}
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      isPositive
                        ? "bg-teal-100 text-teal-800"
                        : "bg-slate-200 text-slate-700"
                    }`}
                  >
                    {String(v).toUpperCase()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Card 2: Keys and Models */}
        <div className="rounded-2xl border border-slate-200/80 p-4 bg-slate-50/50 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-teal-700" />
            <span>LLM Providers & Keys</span>
          </h3>
          <div className="space-y-2 text-xs divide-y divide-slate-200/60">
            {Object.entries(keysAndModels).map(([k, statusVal]) => {
              const isSet = statusVal === "SET";
              return (
                <div key={k} className="pt-2 first:pt-0 flex items-center justify-between">
                  <span className="font-mono text-[11px] text-slate-700">{k}</span>
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      isSet
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {isSet ? (
                      <CheckCircle className="w-3 h-3 text-emerald-600" />
                    ) : (
                      <XCircle className="w-3 h-3 text-rose-600" />
                    )}
                    <span>{statusVal}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Card 3: Explainer Runtime & Queue */}
        <div className="rounded-2xl border border-slate-200/80 p-4 bg-slate-50/50 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-2">
            <Activity className="w-4 h-4 text-teal-700" />
            <span>Explainer & Queue</span>
          </h3>
          <div className="space-y-2 text-xs divide-y divide-slate-200/60">
            <div className="pt-2 first:pt-0 flex items-center justify-between">
              <span className="text-slate-600">Queue Length:</span>
              <span className="font-bold text-navy-900 font-mono">
                {metrics.queue_length ?? 0}
              </span>
            </div>
            <div className="pt-2 flex items-center justify-between">
              <span className="text-slate-600">Mode:</span>
              <span className="font-bold text-teal-700 font-mono">
                {metrics.mode || flags.EXPLAIN_MODE || "background"}
              </span>
            </div>
            <div className="pt-2 flex items-center justify-between">
              <span className="text-slate-600">Tokens Groq (Today / Cap):</span>
              <span className="font-mono text-[11px] text-slate-700">
                {metrics.tokens_used_by_provider?.groq ?? 0} /{" "}
                {metrics.caps?.groq ?? 150000}
              </span>
            </div>
            <div className="pt-2 flex items-center justify-between">
              <span className="text-slate-600">Tokens Gemini (Today / Cap):</span>
              <span className="font-mono text-[11px] text-slate-700">
                {metrics.tokens_used_by_provider?.gemini ?? 0} /{" "}
                {metrics.caps?.gemini ?? 150000}
              </span>
            </div>
            <div className="pt-2 flex items-center justify-between">
              <span className="text-slate-600">Breaker Groq:</span>
              <span
                className={`font-bold uppercase text-[10px] ${
                  metrics.breaker_states?.groq === "closed"
                    ? "text-emerald-700"
                    : "text-amber-700"
                }`}
              >
                {metrics.breaker_states?.groq || "CLOSED"}
              </span>
            </div>
            <div className="pt-2 flex items-center justify-between">
              <span className="text-slate-600">Breaker Gemini:</span>
              <span
                className={`font-bold uppercase text-[10px] ${
                  metrics.breaker_states?.gemini === "closed"
                    ? "text-emerald-700"
                    : "text-amber-700"
                }`}
              >
                {metrics.breaker_states?.gemini || "CLOSED"}
              </span>
            </div>
            <div className="pt-2 flex items-center justify-between">
              <span className="text-slate-600">Cache Hits / Misses:</span>
              <span className="font-mono text-[11px] text-slate-700">
                {metrics.cache_hits ?? 0} / {metrics.cache_misses ?? 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Environment Settings */}
      {data?.settings && data.settings.length > 0 && (
        <div className="rounded-2xl border border-slate-200/80 p-4 bg-slate-50/50 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-teal-700" />
            <span>Environment Settings</span>
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
            {data.settings.map((s) => (
              <div key={s.name} className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/70">
                <span className="font-mono text-[11px] text-slate-700">{s.name}</span>
                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  {s.set ? "SET" : "NOT SET"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
