"use client";

import React, { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { Loader2, ShieldCheck, CheckCircle2, Sparkles, Activity } from "lucide-react";

export const ProcessingScreen = () => {
  const { setScreen, t, isUrdu } = useApp();
  const [phase, setPhase] = useState<"analyzing" | "verified">("analyzing");
  const [progress, setProgress] = useState(15);

  useEffect(() => {
    // Increment progress bar over 2.2 seconds
    const interval = setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + 12 : prev));
    }, 280);

    // After 2.2 seconds, transition to the brief "✓ Verified" flash state
    const analyzeTimer = setTimeout(() => {
      setProgress(100);
      setPhase("verified");
    }, 2200);

    // After 1 second of "✓ Verified" flash, reveal the Risk Result screen
    const verifiedTimer = setTimeout(() => {
      setScreen("risk_result");
    }, 3200);

    return () => {
      clearInterval(interval);
      clearTimeout(analyzeTimer);
      clearTimeout(verifiedTimer);
    };
  }, [setScreen]);

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden p-8 text-center animate-fadeIn">
      {phase === "analyzing" ? (
        <div className="space-y-6 py-4 animate-fadeIn">
          {/* Animated Spinner with Pulsing Brand Rings */}
          <div className="relative w-20 h-20 mx-auto flex items-center justify-center">
            <div className="absolute inset-0 rounded-full bg-teal-500/20 pulse-active" />
            <div className="w-16 h-16 rounded-full bg-navy-800 text-teal-400 flex items-center justify-center shadow-lg relative z-10">
              <Activity className="w-7 h-7 animate-pulse text-teal-400" />
            </div>
          </div>

          <div className="space-y-2">
            <h1 className="font-heading text-xl font-bold text-navy-800 leading-snug">
              {t.processingTitle}
            </h1>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              {t.processingSubtitle}
            </p>
          </div>

          {/* Progress bar */}
          <div className="w-full max-w-xs mx-auto bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
            <div
              className="bg-gradient-to-r from-navy-800 to-teal-600 h-full rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="flex items-center justify-center gap-2 text-[11px] font-semibold text-teal-700">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Processing inputs...</span>
          </div>
        </div>
      ) : (
        /* Brief Verification Flash State (~1s) */
        <div className="space-y-5 py-4 animate-fadeIn">
          <div className="w-20 h-20 rounded-full bg-mutedGreen-100 border-4 border-white shadow-lg flex items-center justify-center mx-auto text-mutedGreen-800 animate-fadeIn">
            <CheckCircle2 className="w-10 h-10 animate-scale" />
          </div>

          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-mutedGreen-100 text-mutedGreen-800 text-xs font-bold">
              <ShieldCheck className="w-4 h-4" />
              <span>{t.verifiedTitle}</span>
            </div>
            <h2 className="font-heading text-xl font-bold text-navy-800">
              {isUrdu ? "طبی تصدیق مکمل ✓" : "Clinical Assessment Verified ✓"}
            </h2>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              {t.verifiedSubtitle}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
