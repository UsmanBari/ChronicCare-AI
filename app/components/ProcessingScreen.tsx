"use client";

import React, { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { Loader2, ShieldCheck, CheckCircle2, Activity } from "lucide-react";

export const ProcessingScreen = () => {
  const { setScreen, demoScenario, t, isUrdu } = useApp();
  const [phase, setPhase] = useState<"analyzing" | "verified">("analyzing");
  const [progress, setProgress] = useState(15);

  useEffect(() => {
    if (demoScenario === "emergency") {
      // Scenario C (Emergency): Quick ~1 second analysis, skips verification flash entirely
      const progressInterval = setInterval(() => {
        setProgress((prev) => (prev < 90 ? prev + 35 : prev));
      }, 180);

      const emergencyTimer = setTimeout(() => {
        setProgress(100);
        setScreen("emergency");
      }, 1000);

      return () => {
        clearInterval(progressInterval);
        clearTimeout(emergencyTimer);
      };
    } else if (demoScenario === "conflict") {
      // Scenario B (Conflict): Standard 2.2 second analysis, transitions to Conflict screen (no verified flash)
      const progressInterval = setInterval(() => {
        setProgress((prev) => (prev < 90 ? prev + 12 : prev));
      }, 280);

      const conflictTimer = setTimeout(() => {
        setProgress(100);
        setScreen("conflict_detail");
      }, 2200);

      return () => {
        clearInterval(progressInterval);
        clearTimeout(conflictTimer);
      };
    } else {
      // Scenario A (Normal): Standard 2.2 second analysis -> 1 second "✓ Verified" flash -> Risk Result
      const progressInterval = setInterval(() => {
        setProgress((prev) => (prev < 90 ? prev + 12 : prev));
      }, 280);

      const analyzeTimer = setTimeout(() => {
        setProgress(100);
        setPhase("verified");
      }, 2200);

      const verifiedTimer = setTimeout(() => {
        setScreen("risk_result");
      }, 3200);

      return () => {
        clearInterval(progressInterval);
        clearTimeout(analyzeTimer);
        clearTimeout(verifiedTimer);
      };
    }
  }, [demoScenario, setScreen]);

  return (
    <div className="w-full max-w-md mx-auto surface-raised rounded-3xl border border-slate-200 shadow-xl overflow-hidden p-8 text-center animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {phase === "analyzing" ? (
        <div className="space-y-6 py-4 animate-fadeIn">
          {/* Animated Spinner with Clinical Brand Rings */}
          <div className="relative w-20 h-20 mx-auto flex items-center justify-center">
            <div
              className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-md relative z-10 ${
                demoScenario === "emergency" ? "bg-emergencyRed-800 text-white" : "bg-navy-800 text-teal-300"
              }`}
            >
              <Activity className="w-8 h-8 animate-pulse" />
            </div>
          </div>

          <div className="space-y-2">
            <h1 className="font-heading text-2xl font-bold text-navy-800 leading-snug">
              {t.processingTitle}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 max-w-xs mx-auto">
              {t.processingSubtitle}
            </p>
          </div>

          {/* Progress bar */}
          <div className="w-full max-w-xs mx-auto bg-slate-100 rounded-full h-2.5 overflow-hidden border border-slate-200">
            <div
              className={`h-full rounded-full transition-all duration-300 ease-out ${
                demoScenario === "emergency"
                  ? "bg-emergencyRed-800"
                  : "bg-teal-700"
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="flex items-center justify-center gap-2 text-xs font-semibold text-teal-800">
            <Loader2 className="w-4 h-4 animate-spin text-teal-700" />
            <span>Analyzing clinical inputs & observations...</span>
          </div>
        </div>
      ) : (
        /* Brief Verification Flash State (~1s) - Scenario A Normal only */
        <div className="space-y-5 py-4 animate-fadeIn">
          <div className="w-20 h-20 rounded-full bg-mutedGreen-100 border-4 border-white shadow-md flex items-center justify-center mx-auto text-mutedGreen-800 animate-fadeIn">
            <CheckCircle2 className="w-10 h-10" />
          </div>

          <div className="space-y-2">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-mutedGreen-100 text-mutedGreen-800 text-xs font-bold">
              <ShieldCheck className="w-4 h-4" />
              <span>{t.verifiedTitle}</span>
            </div>
            <h2 className="font-heading text-2xl font-bold text-navy-800">
              {isUrdu ? "طبی تصدیق مکمل ✓" : "Clinical Assessment Verified ✓"}
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 max-w-xs mx-auto">
              {t.verifiedSubtitle}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
