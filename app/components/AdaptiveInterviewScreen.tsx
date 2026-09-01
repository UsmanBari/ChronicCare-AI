"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { CheckCircle2, HelpCircle, ArrowRight, ArrowLeft, Send, Sparkles } from "lucide-react";

export const AdaptiveInterviewScreen = () => {
  const { setScreen, checkIn, setCheckIn, t, isUrdu } = useApp();

  const [q1Thirst, setQ1Thirst] = useState<boolean | null>(checkIn.thirst);
  const [q2Urination, setQ2Urination] = useState<boolean | null>(checkIn.urination);
  const [q3MissedMeds, setQ3MissedMeds] = useState<"yes" | "no" | "prefer_not_to_answer" | null>(
    checkIn.missedMeds
  );

  const handleQ1Select = (ans: boolean) => {
    setQ1Thirst(ans);
    if (!ans) {
      // If NO: skip question 2, reset urination answer
      setQ2Urination(null);
    }
  };

  const handleQ2Select = (ans: boolean) => {
    setQ2Urination(ans);
  };

  const handleQ3Select = (ans: "yes" | "no" | "prefer_not_to_answer") => {
    setQ3MissedMeds(ans);
  };

  // Determine if ready to submit
  const isQ1Answered = q1Thirst !== null;
  const isQ2Needed = q1Thirst === true;
  const isQ2Answered = !isQ2Needed || q2Urination !== null;
  const isQ3Answered = q3MissedMeds !== null;
  const canSubmit = isQ1Answered && isQ2Answered && isQ3Answered;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    // Track lowConfidence in state if user chose "prefer_not_to_answer" on Q3
    const isLowConfidence = q3MissedMeds === "prefer_not_to_answer";

    const timestamp = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

    setCheckIn((prev) => ({
      ...prev,
      thirst: q1Thirst,
      urination: isQ2Needed ? q2Urination : null,
      missedMeds: q3MissedMeds,
      lowConfidence: isLowConfidence,
      submittedAt: timestamp,
    }));

    setScreen("confirmation");
  };

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn">
      {/* Header */}
      <div className="bg-navy-800 p-6 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-teal-500/10 rounded-full blur-2xl pointer-events-none" />
        <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-500/20 text-teal-300 text-[10px] font-bold uppercase tracking-wider mb-2">
          <Sparkles className="w-3 h-3" />
          <span>{t.questionCount}</span>
        </div>
        <h1 className="font-heading text-2xl font-bold mb-1">{t.adaptiveInterviewTitle}</h1>
        <p className="text-xs text-slate-300 max-w-md mx-auto">{t.adaptiveInterviewSubtitle}</p>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* QUESTION 1 */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 transition-all">
          <div className="flex items-start gap-2.5">
            <span className="w-6 h-6 rounded-full bg-navy-800 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
              1
            </span>
            <p className="text-sm font-semibold text-navy-800 leading-relaxed flex-1">
              {t.q1Text}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <button
              type="button"
              id="q1-yes-btn"
              onClick={() => handleQ1Select(true)}
              className={`py-2.5 px-4 rounded-xl text-sm font-semibold border-2 transition-all ${
                q1Thirst === true
                  ? "bg-teal-700 text-white border-teal-700 shadow-md"
                  : "bg-white text-navy-800 border-slate-200 hover:border-teal-600 hover:bg-teal-50/50"
              }`}
            >
              {t.yes}
            </button>
            <button
              type="button"
              id="q1-no-btn"
              onClick={() => handleQ1Select(false)}
              className={`py-2.5 px-4 rounded-xl text-sm font-semibold border-2 transition-all ${
                q1Thirst === false
                  ? "bg-navy-800 text-white border-navy-800 shadow-md"
                  : "bg-white text-navy-800 border-slate-200 hover:border-slate-400 hover:bg-slate-100/50"
              }`}
            >
              {t.no}
            </button>
          </div>
        </div>

        {/* QUESTION 2 (Follow-up ONLY if Q1 is YES) */}
        {q1Thirst === true && (
          <div className="p-4 rounded-2xl bg-teal-50/60 border border-teal-200 space-y-3 transition-all animate-fadeIn">
            <div className="flex items-start gap-2.5">
              <span className="w-6 h-6 rounded-full bg-teal-700 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                2
              </span>
              <div className="flex-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-teal-800 block mb-0.5">
                  Follow-up Question
                </span>
                <p className="text-sm font-semibold text-navy-800 leading-relaxed">
                  {t.q2Text}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <button
                type="button"
                id="q2-yes-btn"
                onClick={() => handleQ2Select(true)}
                className={`py-2.5 px-4 rounded-xl text-sm font-semibold border-2 transition-all ${
                  q2Urination === true
                    ? "bg-teal-700 text-white border-teal-700 shadow-md"
                    : "bg-white text-navy-800 border-teal-200 hover:border-teal-600 hover:bg-teal-100/50"
                }`}
              >
                {t.yes}
              </button>
              <button
                type="button"
                id="q2-no-btn"
                onClick={() => handleQ2Select(false)}
                className={`py-2.5 px-4 rounded-xl text-sm font-semibold border-2 transition-all ${
                  q2Urination === false
                    ? "bg-navy-800 text-white border-navy-800 shadow-md"
                    : "bg-white text-navy-800 border-teal-200 hover:border-slate-400 hover:bg-slate-100/50"
                }`}
              >
                {t.no}
              </button>
            </div>
          </div>
        )}

        {/* QUESTION 3 (Shown for both paths) */}
        {isQ1Answered && (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 transition-all animate-fadeIn">
            <div className="flex items-start gap-2.5">
              <span className="w-6 h-6 rounded-full bg-navy-800 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                {q1Thirst === true ? "3" : "2"}
              </span>
              <p className="text-sm font-semibold text-navy-800 leading-relaxed flex-1">
                {t.q3Text}
              </p>
            </div>

            <div className="space-y-2 pt-1">
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  id="q3-yes-btn"
                  onClick={() => handleQ3Select("yes")}
                  className={`py-2.5 px-4 rounded-xl text-sm font-semibold border-2 transition-all ${
                    q3MissedMeds === "yes"
                      ? "bg-amber-800 text-white border-amber-800 shadow-md"
                      : "bg-white text-navy-800 border-slate-200 hover:border-amber-800 hover:bg-amber-50/50"
                  }`}
                >
                  {t.yes}
                </button>
                <button
                  type="button"
                  id="q3-no-btn"
                  onClick={() => handleQ3Select("no")}
                  className={`py-2.5 px-4 rounded-xl text-sm font-semibold border-2 transition-all ${
                    q3MissedMeds === "no"
                      ? "bg-mutedGreen-800 text-white border-mutedGreen-800 shadow-md"
                      : "bg-white text-navy-800 border-slate-200 hover:border-mutedGreen-800 hover:bg-mutedGreen-50/50"
                  }`}
                >
                  {t.no}
                </button>
              </div>

              {/* Option 3: Prefer not to answer (sets lowConfidence = true) */}
              <button
                type="button"
                id="q3-prefer-not-btn"
                onClick={() => handleQ3Select("prefer_not_to_answer")}
                className={`w-full py-2 px-3 rounded-xl text-xs font-medium border transition-all text-center ${
                  q3MissedMeds === "prefer_not_to_answer"
                    ? "bg-slate-700 text-white border-slate-700 shadow-sm"
                    : "bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200 hover:text-navy-800"
                }`}
              >
                {t.preferNotToAnswer}
              </button>
            </div>
          </div>
        )}

        {/* Form Controls */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={() => setScreen("checkin_entry")}
            id="back-to-checkin-btn"
            className="px-4 py-3 border border-slate-300 text-slate-700 font-semibold text-sm rounded-xl hover:bg-slate-100 transition-all flex items-center gap-1.5"
          >
            <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            <span>{t.back}</span>
          </button>

          <button
            type="submit"
            disabled={!canSubmit}
            id="submit-checkin-btn"
            className={`flex-1 py-3 px-4 font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 ${
              canSubmit
                ? "bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white shadow-teal-700/20"
                : "bg-slate-200 text-slate-400 cursor-not-allowed"
            }`}
          >
            <span>{t.submitCheckInBtn}</span>
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
