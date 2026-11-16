"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../lib/api";
import { AlertOctagon, PhoneCall, ShieldAlert, Home, BellRing, HeartPulse, CheckCircle2, Loader2, Volume2 } from "lucide-react";

export const EmergencyScreen = () => {
  const { returnToHomeAndClearRun, escalationRecorded, isLiveMode, t, isUrdu, liveCheckinResult, activeLiveCheckin } = useApp();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoadingSpeech, setIsLoadingSpeech] = useState(false);
  const [isWarmingUpHint, setIsWarmingUpHint] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [isTtsEnabled, setIsTtsEnabled] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const warmupTimerRef = useRef<NodeJS.Timeout | null>(null);

  const isSevereHypoglycemia = (() => {
    // 1. Check activeLiveCheckin / liveCheckinResult emergency_reason / reasons / triggers
    const reasonStr = [
      activeLiveCheckin?.emergency_reason,
      (activeLiveCheckin as any)?.reason,
      ...(activeLiveCheckin?.reasons || []),
      ...(liveCheckinResult?.triage?.reasons || []),
      liveCheckinResult?.triage?.trigger_detail,
      liveCheckinResult?.safety_note,
      activeLiveCheckin?.safety_note,
    ].filter(Boolean).join(" ").toLowerCase();

    if (
      reasonStr.includes("severe acute hypoglycemia") ||
      reasonStr.includes("glucose low") ||
      reasonStr.includes("low glucose") ||
      reasonStr.includes("hypoglycemia") ||
      reasonStr.includes("glucose < 54") ||
      reasonStr.includes("glucose (< 54") ||
      reasonStr.includes("sugar < 54")
    ) {
      return true;
    }

    // 2. Check readings in activeLiveCheckin or liveCheckinResult
    const allIntakes = [
      ...(activeLiveCheckin?.intakes || []),
      ...(liveCheckinResult?.intakes || []),
    ];
    for (const it of allIntakes) {
      const readings = it?.readings || [];
      for (const r of readings) {
        const type = (r.observation_type || r.type || "").toLowerCase();
        if (type.includes("glucose") || type.includes("sugar")) {
          const val = Number(r.value);
          const unit = (r.unit || "").toLowerCase();
          if (!isNaN(val)) {
            if (unit.includes("mmol") ? val < 3.0 : val < 54) {
              return true;
            }
          }
        }
      }
    }

    // 3. Check known slots or answers
    const slots = (activeLiveCheckin as any)?.known_slots || (activeLiveCheckin as any)?.answers || {};
    const glucoseSlot = slots.glucose_reading || slots.diabetes_glucose_reading || slots.fasting_blood_sugar;
    if (glucoseSlot !== undefined) {
      const val = parseFloat(String(glucoseSlot));
      if (!isNaN(val) && val > 0 && val < 54) {
        return true;
      }
    }

    return false;
  })();

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

  const clearWarmup = () => {
    if (warmupTimerRef.current) {
      clearTimeout(warmupTimerRef.current);
      warmupTimerRef.current = null;
    }
    setIsWarmingUpHint(false);
  };

  useEffect(() => {
    return () => {
      clearWarmup();
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
    setIsWarmingUpHint(false);
    setSpeechError(null);
    if (warmupTimerRef.current) clearTimeout(warmupTimerRef.current);
    warmupTimerRef.current = setTimeout(() => {
      setIsWarmingUpHint(true);
    }, 3000);

    try {
      const blob = await api.getEmergencySpeech(isUrdu ? "ur" : "en");
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onplay = () => {
        clearWarmup();
        setIsPlaying(true);
        setIsLoadingSpeech(false);
      };
      audio.onended = () => {
        clearWarmup();
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        clearWarmup();
        setIsPlaying(false);
        setIsLoadingSpeech(false);
        setSpeechError(t.speechError || "Voice output unavailable");
        URL.revokeObjectURL(url);
      };

      await audio.play();
    } catch {
      clearWarmup();
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
          {isSevereHypoglycemia && (
            <div data-testid="severe-hypo-guidance" className="p-3.5 rounded-xl bg-amber-100 border border-amber-300 text-amber-950 font-bold text-sm text-center">
              {isUrdu
                ? "اگر ہوش میں ہیں اور نگل سکتے ہیں، تو فوراً چینی یا جوس لیں۔"
                : "If awake and able to swallow, take sugar or juice now."}
            </div>
          )}
          {isTtsEnabled && (
            <div className="space-y-1.5 pt-1">
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
                    <span>{isWarmingUpHint ? (t.speechPreparingWarmup || "Preparing voice, the first time can take up to a minute") : (t.speechLoading || "Generating voice...")}</span>
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
              {isLoadingSpeech && isWarmingUpHint && (
                <p data-testid="emergency-speech-warmup-hint" className="text-[11px] text-slate-500 italic text-center">
                  {t.speechPreparingWarmup || "Preparing voice, the first time can take up to a minute"}
                </p>
              )}
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
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs text-slate-600">
          <div className="flex items-center justify-between">
            <span className="font-medium">{t.directHotlineDispatch}</span>
            <a
              href="tel:1122"
              className="font-bold text-emergencyRed-800 hover:underline flex items-center gap-1"
            >
              <PhoneCall className="w-3.5 h-3.5" /> 1122
            </a>
          </div>
          {isSevereHypoglycemia && (
            <p className="font-semibold text-emergencyRed-900 border-t border-slate-200 pt-2 text-center" data-testid="emergency-hotline-hypo-instruction">
              {isUrdu
                ? "اگر ہوش میں ہیں اور نگل سکتے ہیں، تو فوراً چینی یا جوس لیں (1122 کے ساتھ ساتھ)۔"
                : "If awake and able to swallow, take sugar or juice now alongside calling 1122."}
            </p>
          )}
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
