"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../lib/api";
import { AlertOctagon, PhoneCall, ShieldAlert, Home, BellRing, HeartPulse, CheckCircle2, Loader2, Volume2 } from "lucide-react";

export const EmergencyScreen = () => {
  const { returnToHomeAndClearRun, escalationRecorded, isLiveMode, t, isUrdu } = useApp();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoadingSpeech, setIsLoadingSpeech] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [isTtsEnabled, setIsTtsEnabled] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let isMounted = true;
    api.getVoiceStatus().then((res) => {
      if (isMounted && res && res.tts_enabled) {
        setIsTtsEnabled(true);
      }
    }).catch(() => {
      // Offline / unconfigured: keep voice button hidden
    });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handlePlayEmergencySpeech = async () => {
    if (isLoadingSpeech) return;

    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setIsPlaying(false);
      return;
    }

    setIsLoadingSpeech(true);
    setSpeechError(null);

    try {
      const blob = await api.getEmergencySpeech(isUrdu ? "ur" : "en");
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onplay = () => {
        setIsPlaying(true);
        setIsLoadingSpeech(false);
      };
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        setIsPlaying(false);
        setIsLoadingSpeech(false);
        setSpeechError(t.speechError || "Voice output unavailable");
        URL.revokeObjectURL(url);
      };

      await audio.play();
    } catch {
      setIsLoadingSpeech(false);
      setIsPlaying(false);
      setSpeechError(t.speechError || "Voice output unavailable");
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto surface-raised rounded-3xl border-2 border-emergencyRed-800/80 shadow-2xl overflow-hidden animate-fadeIn space-y-0" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Clinically Responsible High-Alert Header */}
      <div className="bg-emergencyRed-800 p-7 text-white text-center relative overflow-hidden">
        <div className="w-16 h-16 rounded-2xl bg-white text-emergencyRed-800 flex items-center justify-center mx-auto mb-3.5 shadow-xl">
          <AlertOctagon className="w-10 h-10 stroke-[2.5]" />
        </div>

        <span className="text-xs font-bold uppercase tracking-widest px-3.5 py-1 rounded-full bg-emergencyRed-900/60 text-red-100 mb-2 inline-block border border-emergencyRed-700">
          {isUrdu ? "فوری طبی الرٹ" : "CRITICAL CLINICAL ALERT"}
        </span>

        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1">
          {t.emergencyDetectedTitle}
        </h1>
      </div>

      <div className="p-6 sm:p-7 space-y-6">
        {/* Prompt Medical Action Guidance */}
        <div className="p-5 rounded-2xl bg-emergencyRed-50 border border-emergencyRed-800/30 text-center space-y-3">
          <p className="text-base font-bold text-emergencyRed-800 leading-snug">
            {t.emergencyGuidanceText}
          </p>
          <p className="text-sm text-emergencyRed-800/90 leading-relaxed">
            {isUrdu
              ? "اگر آپ کو شدید بے چینی، سانس لینے میں دشواری یا بے ہوشی محسوس ہو رہی ہے تو فوری 1122 یا ایمرجنسی سروسز پر رابطہ کریں۔"
              : "If you are experiencing severe shortness of breath, acute chest distress, or sudden weakness, contact emergency services (1122) immediately."}
          </p>
          {isTtsEnabled && (
            <div className="pt-1">
              <button
                type="button"
                data-testid="emergency-speech-btn"
                onClick={handlePlayEmergencySpeech}
                disabled={isLoadingSpeech}
                className="w-full py-2.5 px-4 bg-white hover:bg-red-50 text-emergencyRed-800 border border-emergencyRed-200 rounded-xl font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isLoadingSpeech ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-emergencyRed-700" />
                    <span>{t.speechLoading || "Generating voice..."}</span>
                  </>
                ) : isPlaying ? (
                  <>
                    <Volume2 className="w-4 h-4 text-emergencyRed-700 animate-pulse" />
                    <span>{t.listeningToExplanation || "Playing..."}</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="w-4 h-4 text-emergencyRed-700" />
                    <span>{t.listenToEmergencyInstructions || "Listen to Instructions"}</span>
                  </>
                )}
              </button>
              {speechError && (
                <p data-testid="emergency-speech-error" className="text-xs text-emergencyRed-700 font-medium text-center mt-2">
                  {speechError}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Care Team Alerted Notification Receipt - ONLY shown when escalationRecorded is true; otherwise review list */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-center gap-3.5 text-sm text-slate-700">
          <div className="w-10 h-10 rounded-xl bg-teal-700 text-white flex items-center justify-center shrink-0 shadow-xs">
            <BellRing className="w-5 h-5 text-teal-200" />
          </div>
          <div>
            <p className="font-bold text-navy-800" data-testid="emergency-alert-status-text">
              {escalationRecorded === true ? t.emergencyAlertedText : (t.emergencyReviewListText || t.emergencyReviewNotice)}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {escalationRecorded === true
                ? (isUrdu ? "طبی نگہداشت ٹیم کو خودکار فوری پیغام بھیج دیا گیا ہے۔" : "Priority clinical notification dispatched to on-call care team.")
                : (isUrdu ? "طبی معائنے کے لیے تفصیلی رپورٹ جمع کر دی گئی ہے۔" : "Detailed report queued for physician review.")}
            </p>
          </div>
        </div>

        {/* Emergency Services Shortcut Pill */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs text-slate-600">
          <span className="font-medium">{t.directHotlineDispatch}</span>
             <a
               href="tel:1122"
               className="font-bold text-emergencyRed-800 hover:underline flex items-center gap-1"
             >
               <PhoneCall className="w-3.5 h-3.5" /> 1122
             </a>
        </div>

        {/* Return to Home button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={returnToHomeAndClearRun}
            id="emergency-return-home-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
          >
            <Home className="w-4 h-4" />
            <span>{t.finishBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
