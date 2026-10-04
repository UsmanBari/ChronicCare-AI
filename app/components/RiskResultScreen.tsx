"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { RiskBadge } from "./RiskBadge";
import {
  CheckCircle,
  HelpCircle,
  TrendingUp,
  ArrowRight,
  ChevronDown,
  Info,
  ShieldCheck,
  Activity,
  HeartPulse,
  FileCheck,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

export const RiskResultScreen = () => {
  const { setScreen, isLiveMode, liveCheckinResult, t, isUrdu } = useApp();
  const [showWhyPanel, setShowWhyPanel] = useState(false);

  // =========================================================================
  // LIVE MODE: "Check-in recorded and verified" summary (NEVER invented output)
  // =========================================================================
  if (isLiveMode) {
    const summary = liveCheckinResult?.reconciliation?.summary || {};
    const agreementCount = summary.agreement || 0;
    const missingCount = (summary.source_a_only || 0) + (summary.source_b_only || 0);
    const confidenceLabel = liveCheckinResult?.intakes?.[0]?.confidence_label || "High";

    return (
      <div className="w-full max-w-lg mx-auto glass-raised rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
        {/* Live Header Banner */}
        <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />
          <div className="w-14 h-14 rounded-2xl bg-teal-500/20 border border-teal-400/40 flex items-center justify-center mx-auto mb-3 shadow-inner text-teal-300">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1.5">
            {t.checkinSummaryTitle}
          </h1>
          <p className="text-sm text-slate-200 max-w-sm mx-auto leading-relaxed">
            {t.checkinSummarySubtitle}
          </p>
        </div>

        <div className="p-6 sm:p-7 space-y-5">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-4 rounded-2xl bg-teal-50/80 border border-teal-200 text-center space-y-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-teal-900 block">
                {t.agreementsCountLabel}
              </span>
              <div className="text-2xl font-bold text-teal-900 font-mono">
                {agreementCount}
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 block">
                {t.missingCountLabel}
              </span>
              <div className="text-2xl font-bold text-slate-800 font-mono">
                {missingCount}
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-mutedGreen-50 border border-mutedGreen-200 text-center space-y-1">
              <span className="text-[11px] font-bold uppercase tracking-wider text-mutedGreen-900 block">
                {t.confidenceLabel}
              </span>
              <div className="text-2xl font-bold text-mutedGreen-900 capitalize">
                {confidenceLabel}
              </div>
            </div>
          </div>

          {/* Mandatory Release Scope Note */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/90 flex items-start gap-3 text-xs text-slate-600 leading-relaxed">
            <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <span>{t.riskScoringOmittedNote}</span>
          </div>

          {/* Navigation to Trends */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setScreen("trends")}
              id="view-trends-btn"
              className="w-full min-h-[48px] py-3.5 px-5 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 shadow-teal-700/20"
            >
              <TrendingUp className="w-4 h-4" />
              <span>{t.viewTrendsBtn}</span>
              <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // MOCK MODE: Original Mock Risk Badge and Explanations
  // =========================================================================
  const contributingFactors = [
    t.factor1,
    t.factor2,
    t.factor3,
    t.factor4,
  ];

  return (
    <div className="w-full max-w-lg mx-auto glass-raised rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header Banner */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />
        <span className="text-xs font-bold uppercase tracking-wider text-teal-300 block mb-1.5">
          {isUrdu ? "طبی جائزہ و تخمینہ" : "Personalized Risk Assessment"}
        </span>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1.5">
          {isUrdu ? "آپ کے روزانہ نتائج" : "Daily Health Analysis"}
        </h1>
        <p className="text-sm text-slate-200 max-w-xs mx-auto leading-relaxed">
          {t.riskDescription}
        </p>
      </div>

      <div className="p-6 sm:p-7 space-y-6">
        {/* Risk Badge Display */}
        <div className="p-6 rounded-2xl bg-mutedGreen-50 border border-mutedGreen-800/20 text-center space-y-3.5">
          <div className="flex justify-center">
            <RiskBadge riskLevel="low" size="lg" />
          </div>

          <p className="text-base font-semibold text-mutedGreen-800">
            {t.riskSupportingText}
          </p>

          <p className="text-sm text-slate-600 leading-relaxed max-w-sm mx-auto">
            {isUrdu
              ? "آپ کے درج کردہ علامات اور ادویات کی پابندی سے ظاہر ہوتا ہے کہ آپ کی حالت معمول کے مطابق مستحکم ہے۔"
              : "Your self-reported symptoms, consistent medication routine, and stable baseline vitals show no current indicators of escalation."}
          </p>
        </div>

        {/* Toggle to view Why / Contributing Factors */}
        {!showWhyPanel ? (
          <button
            type="button"
            onClick={() => setShowWhyPanel(true)}
            id="see-why-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-slate-100 hover:bg-slate-200 text-navy-800 font-semibold text-sm rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-2"
          >
            <HelpCircle className="w-4 h-4 text-teal-700" />
            <span>{t.seeWhyBtn}</span>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </button>
        ) : (
          <div className="p-5 sm:p-6 rounded-2xl bg-slate-50/90 border border-slate-200 space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-slate-200/80 pb-3">
              <h2 className="font-heading text-base sm:text-lg font-bold text-navy-800 flex items-center gap-2">
                <Activity className="w-5 h-5 text-teal-700" />
                <span>{t.contributingFactorsTitle}</span>
              </h2>
            </div>

            {/* MANDATORY SAFEGUARD LABEL */}
            <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 flex items-start gap-2.5 text-xs text-teal-900 leading-snug">
              <Info className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
              <span className="font-medium">
                {t.shapDisclaimer}
              </span>
            </div>

            {/* Contributing factors list */}
            <ul className="space-y-3 pt-1 text-sm text-slate-700">
              {contributingFactors.map((factor, index) => (
                <li key={index} className="flex items-start gap-2.5">
                  <CheckCircle className="w-4 h-4 text-mutedGreen-800 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{factor}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Proceed to Trend Screen */}
        <div className="pt-2">
          <button
            type="button"
            onClick={() => setScreen("trends")}
            id="view-trends-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 shadow-teal-700/20"
          >
            <TrendingUp className="w-4 h-4" />
            <span>{t.viewTrendsBtn}</span>
            <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
          </button>
        </div>
      </div>
    </div>
  );
};
