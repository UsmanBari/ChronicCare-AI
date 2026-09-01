"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { Mic, ArrowRight, ArrowLeft, Sparkles, MessageSquare, Volume2 } from "lucide-react";

export const CheckInEntryScreen = () => {
  const { setScreen, checkIn, setCheckIn, t, isUrdu } = useApp();
  const [note, setNote] = useState(checkIn.note || "");
  const [isListening, setIsListening] = useState(false);

  const handleVoiceInput = () => {
    if (isListening) return;
    setIsListening(true);

    // Mock speech-to-text: pulse for 2 seconds then autofill hardcoded sample response
    setTimeout(() => {
      const sampleVoiceNote = "I've been feeling a bit tired and thirsty lately";
      setNote(sampleVoiceNote);
      setIsListening(false);
    }, 2000);
  };

  const handleContinue = (e: React.FormEvent) => {
    e.preventDefault();
    setCheckIn((prev) => ({
      ...prev,
      note: note.trim(),
    }));
    setScreen("adaptive_interview");
  };

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn">
      {/* Header */}
      <div className="bg-navy-800 p-6 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-teal-500/10 rounded-full blur-2xl pointer-events-none" />
        <h1 className="font-heading text-2xl font-bold mb-1">{t.checkInEntryTitle}</h1>
        <p className="text-xs text-slate-300 max-w-md mx-auto">{t.checkInEntrySubtitle}</p>
      </div>

      <form onSubmit={handleContinue} className="p-6 space-y-6">
        {/* Text Input */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-navy-800 mb-2 flex items-center justify-between" htmlFor="feeling-input">
            <span className="flex items-center gap-1.5">
              <MessageSquare className="w-4 h-4 text-teal-700" />
              <span>{t.howAreYouFeelingLabel}</span>
            </span>
          </label>
          <textarea
            id="feeling-input"
            rows={4}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={t.howAreYouFeelingPlaceholder}
            className="w-full text-sm rounded-xl border border-slate-300 bg-slate-50/50 p-3.5 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 resize-none transition-all leading-relaxed"
          />
        </div>

        {/* Voice Input Section */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-3">
          <div className="flex flex-col items-center justify-center">
            <button
              type="button"
              onClick={handleVoiceInput}
              disabled={isListening}
              id="voice-input-btn"
              title={t.voiceInputTitle}
              className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
                isListening
                  ? "bg-teal-700 text-white pulse-active scale-110 shadow-lg"
                  : "bg-navy-800 text-teal-400 hover:bg-navy-700 hover:scale-105 shadow-md active:scale-95"
              }`}
            >
              <Mic className={`w-7 h-7 ${isListening ? "animate-pulse" : ""}`} />
            </button>

            {/* Listening state or helper text */}
            <div className="mt-3">
              {isListening ? (
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-100 text-teal-800 text-xs font-semibold animate-pulse">
                  <span className="w-2 h-2 rounded-full bg-teal-600 animate-ping" />
                  <span>{t.listeningAnimationText}</span>
                </div>
              ) : (
                <div className="space-y-0.5">
                  <p className="text-xs font-semibold text-navy-800">{t.voiceInputTitle}</p>
                  <p className="text-[11px] text-slate-500">{t.voiceHelperText}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={() => setScreen("home")}
            id="back-to-home-btn"
            className="px-4 py-3 border border-slate-300 text-slate-700 font-semibold text-sm rounded-xl hover:bg-slate-100 transition-all flex items-center gap-1.5"
          >
            <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            <span>{t.back}</span>
          </button>

          <button
            type="submit"
            id="continue-to-interview-btn"
            className="flex-1 py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <span>{t.continue}</span>
            <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
          </button>
        </div>
      </form>
    </div>
  );
};
