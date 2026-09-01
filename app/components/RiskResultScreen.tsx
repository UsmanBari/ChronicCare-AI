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
} from "lucide-react";

export const RiskResultScreen = () => {
  const { setScreen, t, isUrdu } = useApp();
  const [showWhyPanel, setShowWhyPanel] = useState(false);

  const contributingFactors = [
    t.factor1,
    t.factor2,
    t.factor3,
    t.factor4,
  ];

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn space-y-0">
      {/* Header Banner */}
      <div className="bg-navy-800 p-6 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-teal-500/10 rounded-full blur-2xl pointer-events-none" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-teal-300 block mb-1">
          {isUrdu ? "طبی جائزہ و تخمینہ" : "Personalized Risk Assessment"}
        </span>
        <h1 className="font-heading text-2xl font-bold text-white mb-1">
          {isUrdu ? "آپ کے روزانہ نتائج" : "Daily Health Analysis"}
        </h1>
        <p className="text-xs text-slate-300 max-w-xs mx-auto">
          {t.riskDescription}
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Risk Badge Display (Hardcoded riskLevel="low" per M2 rules) */}
        <div className="p-5 rounded-2xl bg-mutedGreen-50 border border-mutedGreen-800/20 text-center space-y-3">
          <div className="flex justify-center">
            {/* Purely presentational RiskBadge with hardcoded 'low' */}
            <RiskBadge riskLevel="low" size="lg" />
          </div>

          <p className="text-sm font-semibold text-mutedGreen-800">
            {t.riskSupportingText}
          </p>

          <p className="text-xs text-slate-600 leading-relaxed max-w-sm mx-auto">
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
            className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 text-navy-800 font-semibold text-sm rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-2"
          >
            <HelpCircle className="w-4 h-4 text-teal-700" />
            <span>{t.seeWhyBtn}</span>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </button>
        ) : (
          /* "WHY" / CONTRIBUTING FACTORS PANEL */
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-slate-200/80 pb-2.5">
              <h2 className="font-heading text-base font-bold text-navy-800 flex items-center gap-2">
                <Activity className="w-4 h-4 text-teal-700" />
                <span>{t.contributingFactorsTitle}</span>
              </h2>
            </div>

            {/* MANDATORY SAFEGUARD LABEL */}
            <div className="p-2.5 rounded-lg bg-teal-50 border border-teal-200 flex items-start gap-2 text-[11px] text-teal-900 leading-snug">
              <Info className="w-3.5 h-3.5 text-teal-700 shrink-0 mt-0.5" />
              <span className="font-medium">
                {t.shapDisclaimer}
              </span>
            </div>

            {/* Contributing factors list */}
            <ul className="space-y-2.5 pt-1 text-xs text-slate-700">
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
            className="w-full py-3.5 px-4 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 shadow-teal-700/20"
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
