"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "../context/AppContext";
import {
  CheckCircle2,
  HelpCircle,
  ArrowRight,
  ArrowLeft,
  Send,
  Sparkles,
  Loader2,
  MessageCircle,
  ShieldAlert,
  AlertTriangle,
  Bot,
  RotateCcw,
  Pill,
  ShieldCheck,
  User,
  Mic,
  MicOff,
  Square,
  Volume2,
} from "lucide-react";
import {
  api,
  ApiError,
  CheckinStartResponse,
  CheckinAnswerResponse,
  CheckinCompleteResponse,
} from "../lib/api";

interface ChatMessage {
  role: "system" | "user";
  text: string;
}

export const AdaptiveInterviewScreen = () => {
  const {
    setScreen,
    checkIn,
    setCheckIn,
    isLiveMode,
    liveProfile,
    activeLiveCheckin,
    setActiveLiveCheckin,
    setLiveCheckinResult,
    setEscalationRecorded,
    setShowSettings,
    t,
    isUrdu,
  } = useApp();

  // --- LIVE MODE STATE ---
  const [liveQuestion, setLiveQuestion] = useState<string>("");
  const [liveAnswerInput, setLiveAnswerInput] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [isConsentError, setIsConsentError] = useState<boolean>(false);
  const [isPregnancyIneligible, setIsPregnancyIneligible] = useState<boolean>(false);
  const [conversationHistory, setConversationHistory] = useState<ChatMessage[]>([]);
  const [currentStep, setCurrentStep] = useState<string | null>(activeLiveCheckin?.step || null);
  const [lastFailedAnswer, setLastFailedAnswer] = useState<string | null>(null);

  // --- VOICE RECORDING STATE ---
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [transcribedSafetyNotice, setTranscribedSafetyNotice] = useState<boolean>(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // Stop recording timer & stream cleanly
  const cleanupMediaStream = () => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  };

  const handleStartRecording = async () => {
    setVoiceError(null);

    if (liveProfile && liveProfile.voice_enabled === false) {
      setVoiceError(
        isUrdu
          ? "آواز کا فیچر سیٹنگز میں بند ہے۔ براہ کرم سیٹنگز میں جا کر اسے آن کریں۔"
          : "Voice input is disabled in your profile. Enable it in Settings (Privacy & Consent) to speak your answers."
      );
      return;
    }

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setVoiceError(
        isUrdu
          ? "آپ کے براؤزر میں مائیکروفون دستیاب نہیں ہے۔ براہ کرم جواب ٹائپ کریں۔"
          : "Microphone recording is not supported in this browser. Please type your answer."
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      let mimeType = "";
      if (typeof MediaRecorder !== "undefined") {
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
          mimeType = "audio/webm;codecs=opus";
        } else if (MediaRecorder.isTypeSupported("audio/webm")) {
          mimeType = "audio/webm";
        } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
          mimeType = "audio/mp4";
        }
      }

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const chunks = audioChunksRef.current;
        cleanupMediaStream();
        setIsRecording(false);

        if (!chunks || chunks.length === 0) return;

        const audioBlob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });

        // Check 5MB limit
        if (audioBlob.size > 5 * 1024 * 1024) {
          setVoiceError(
            isUrdu
              ? "آواز کی فائل ۵ ایم بی سے زیادہ ہے۔ براہ کرم مختصر جواب ریکارڈ کریں۔"
              : "Audio recording exceeds the 5MB limit. Please record a shorter answer."
          );
          return;
        }

        if (audioBlob.size < 100) {
          setVoiceError(isUrdu ? "کوئی آواز ریکارڈ نہیں ہوئی۔" : "No audio detected. Please try again.");
          return;
        }

        setIsTranscribing(true);
        setVoiceError(null);

        try {
          const res = await api.transcribeVoice(audioBlob, "recording.webm");
          const text = (res.text || "").trim();
          if (text) {
            setLiveAnswerInput((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text));
            setTranscribedSafetyNotice(true);
          } else {
            setVoiceError(
              isUrdu
                ? "کوئی الفاظ سمجھ نہیں آئے۔ براہ کرم دوبارہ بولیں یا لکھ کر جواب دیں۔"
                : "No speech recognized. Please try speaking clearly or type your answer."
            );
          }
        } catch (err: any) {
          if (err instanceof ApiError) {
            if (err.status === 403) {
              setVoiceError(
                isUrdu
                  ? "آواز کا فیچر آپ کی پروفائل میں بند ہے۔ سیٹنگز میں فعال کریں۔"
                  : "Voice input is not enabled in your profile settings."
              );
            } else if (err.status === 429) {
              setVoiceError(
                isUrdu
                  ? "آواز کی حد ختم ہو گئی ہے۔ براہ کرم کچھ دیر بعد کوشش کریں یا ٹائپ کریں۔"
                  : "Voice transcription rate limit reached. Please type your answer or wait a minute."
              );
            } else if (err.status === 502 || err.status === 503) {
              setVoiceError(
                isUrdu
                  ? "آواز کی سروس عارضی طور پر غیر فعال ہے۔ براہ کرم جواب ٹائپ کریں۔"
                  : "Voice transcription service temporarily unavailable. Please type your answer."
              );
            } else {
              setVoiceError(err.getFriendlyMessage(isUrdu));
            }
          } else {
            setVoiceError(
              isUrdu
                ? "آواز کی منتقلی میں خرابی پیش آئی۔ براہ کرم جواب ٹائپ کریں۔"
                : "Failed to transcribe voice audio. Please type your answer."
            );
          }
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start(1000); // 1s timeslices
      setIsRecording(true);
      setRecordingSeconds(0);

      let sec = 0;
      recordingTimerRef.current = setInterval(() => {
        sec += 1;
        setRecordingSeconds(sec);
        if (sec >= 60) {
          handleStopRecording();
        }
      }, 1000);
    } catch (err: any) {
      cleanupMediaStream();
      setIsRecording(false);
      setVoiceError(
        isUrdu
          ? "مائیکروفون تک رسائی کی اجازت نہیں ملی۔ براہ کرم براؤزر میں مائیک کی اجازت دیں یا ٹائپ کریں۔"
          : "Microphone access denied. Please allow microphone permissions or type your answer."
      );
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        cleanupMediaStream();
        setIsRecording(false);
      }
    } else {
      cleanupMediaStream();
      setIsRecording(false);
    }
  };

  const handleCancelRecording = () => {
    audioChunksRef.current = [];
    cleanupMediaStream();
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    setIsRecording(false);
    setRecordingSeconds(0);
    setVoiceError(null);
  };

  // Ref guards to prevent double flights
  const isSendingRef = useRef<boolean>(false);
  const isStartingRef = useRef<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // --- MOCK MODE STATE ---
  const [q1Thirst, setQ1Thirst] = useState<boolean | null>(checkIn.thirst);
  const [q2Urination, setQ2Urination] = useState<boolean | null>(checkIn.urination);
  const [q3MissedMeds, setQ3MissedMeds] = useState<"yes" | "no" | "prefer_not_to_answer" | null>(
    checkIn.missedMeds
  );

  // Scroll to newest question within question list container only (prevent page jump)
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    if (inputRef.current) {
      inputRef.current.focus({ preventScroll: true });
    }
  }, [conversationHistory, liveQuestion]);

  // Initialize Live Mode Interview Session
  useEffect(() => {
    if (!isLiveMode) return;
    if (isStartingRef.current) return;
    isStartingRef.current = true;

    let isMounted = true;
    const initLiveSession = async () => {
      setLiveError(null);
      try {
        let currentCheckin = activeLiveCheckin;
        if (!currentCheckin || !currentCheckin.checkin_id) {
          setIsSending(true);
          isSendingRef.current = true;
          currentCheckin = await api.startCheckin();
          if (!isMounted) return;
          setActiveLiveCheckin(currentCheckin);
          setCurrentStep(currentCheckin.step || null);
          setIsSending(false);
          isSendingRef.current = false;
        } else {
          setCurrentStep(currentCheckin.step || null);
        }

        const firstQ =
          currentCheckin.question ||
          (isUrdu
            ? "آج آپ اپنی علامات اور ادویات کے ساتھ کیسا محسوس کر رہے ہیں؟"
            : "How are you feeling today with your symptoms and medications?");
        setLiveQuestion(firstQ);
        setConversationHistory([{ role: "system", text: firstQ }]);

        // If user provided a note in CheckInEntryScreen, send it as initial answer
        if (checkIn.note && checkIn.note.trim()) {
          const initialAnswer = checkIn.note.trim();
          await handleLiveSendAnswerInternal(initialAnswer, currentCheckin.checkin_id, currentCheckin.step || null);
        }
      } catch (err: any) {
        if (!isMounted) return;
        setIsSending(false);
        isSendingRef.current = false;
        if (err instanceof ApiError) {
          const detailStr = (err.detail || "").toLowerCase();
          const reasonStr = (err.data?.reason || "").toLowerCase();
          if (detailStr === "not_eligible" || reasonStr === "pregnant" || reasonStr === "pregnancy_unconfirmed") {
            setIsPregnancyIneligible(true);
            setLiveError(
              isUrdu
                ? "یہ سروس صرف غیر حاملہ بالغ افراد کے لیے ہے۔ دوران حمل بلڈ پریشر اور شوگر کے اہداف مختلف ہوتے ہیں۔ براہ کرم اپنے ڈاکٹر یا معالج سے رابطہ کریں۔"
                : "ChronicCare AI is designed for non-pregnant adults. Target ranges and clinical protocols differ during pregnancy. Please consult your clinician or physician."
            );
            return;
          }
          if (err.status === 403 && detailStr.includes("consent")) {
            setIsConsentError(true);
          }
          setLiveError(err.getFriendlyMessage(isUrdu));
        } else {
          setLiveError(
            isUrdu
              ? "ہم آپ کا سیشن شروع نہیں کر سکے۔ اگر یہ ہنگامی صورتحال ہے تو فوراً اپنے مقامی ایمرجنسی نمبر پر کال کریں۔"
              : "We could not start your check-in session. If this is an emergency, call your local emergency number now."
          );
        }
      }
    };

    initLiveSession();

    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLiveMode]);

  const handleLiveSendAnswerInternal = async (
    answerText: string,
    checkinId?: string,
    stepToSend?: string | null
  ) => {
    const cleanAnswer = answerText.trim();
    const targetCheckinId = checkinId || activeLiveCheckin?.checkin_id;
    if (!cleanAnswer || isSendingRef.current || !targetCheckinId) return;

    isSendingRef.current = true;
    setIsSending(true);
    setLiveError(null);
    setLastFailedAnswer(null);

    // Keep the typed input in case of error; only clear on success/handling
    const previousInput = liveAnswerInput;

    // Append user message to history
    setConversationHistory((prev) => [...prev, { role: "user", text: cleanAnswer }]);

    const currentStepValue = stepToSend !== undefined ? stepToSend : currentStep;

    try {
      const answerRes: CheckinAnswerResponse = await api.answerCheckin(
        targetCheckinId,
        cleanAnswer,
        currentStepValue
      );

      // Successfully processed by server: clear the input
      setLiveAnswerInput("");

      if (answerRes.emergency) {
        setEscalationRecorded(answerRes.escalation_recorded === true);
        setScreen("emergency");
        return;
      }

      if (answerRes.step) {
        setCurrentStep(answerRes.step);
      }

      if (!answerRes.complete && answerRes.question) {
        setLiveQuestion(answerRes.question);
        setConversationHistory((prev) => [
          ...prev,
          { role: "system", text: answerRes.question! },
        ]);
        setIsSending(false);
        isSendingRef.current = false;
        return;
      }

      // If complete -> call /complete endpoint
      const completeRes: CheckinCompleteResponse = await api.completeCheckin(targetCheckinId);
      setLiveCheckinResult(completeRes);

      // Route by result
      if (completeRes.emergency) {
        setEscalationRecorded(true);
        setScreen("emergency");
      } else if (completeRes.requires_review) {
        setScreen("conflict_detail");
      } else {
        setScreen("risk_result");
      }
    } catch (err: any) {
      setIsSending(false);
      isSendingRef.current = false;

      // Handle 409 stale_step: do not show error, replace shown question with response question, keep typed text
      if (err instanceof ApiError && err.status === 409) {
        const errorData = err.data;
        if (errorData?.detail === "stale_step" || err.detail === "stale_step") {
          const newQ = errorData?.question || "Please answer the current question:";
          const newStep = errorData?.step || null;
          setCurrentStep(newStep);
          setLiveQuestion(newQ);
          setConversationHistory((prev) => [
            ...prev,
            { role: "system", text: newQ },
          ]);
          // Retain user's input text in input box
          setLiveAnswerInput(cleanAnswer);
          return;
        }

        // Handle 409 concurrent_update: refetch checkin detail once and continue
        if (errorData?.detail === "concurrent_update" || err.detail === "concurrent_update") {
          try {
            const updatedDetail = await api.getUserCheckinDetail(targetCheckinId);
            const updatedState = updatedDetail.state || {};
            if (updatedState.step) {
              setCurrentStep(updatedState.step);
            }
          } catch {
            // Refetch error fallback
          }
        }
      }

      // Keep typed text and record last failed answer for retry
      setLastFailedAnswer(cleanAnswer);
      setLiveAnswerInput(cleanAnswer);

      // Check for pregnancy ineligibility error from answer
      if (err instanceof ApiError) {
        const detailStr = (err.detail || "").toLowerCase();
        const reasonStr = (err.data?.reason || "").toLowerCase();
        if (detailStr === "not_eligible" || reasonStr === "pregnant" || reasonStr === "pregnancy_unconfirmed") {
          setIsPregnancyIneligible(true);
          setLiveError(
            isUrdu
              ? "چیک ان روک دیا گیا ہے۔ یہ سروس صرف غیر حاملہ بالغ افراد کے لیے ہے۔ دوران حمل اہداف مختلف ہوتے ہیں۔ براہ کرم اپنے معالج سے رابطہ کریں۔"
              : "Check-in stopped. ChronicCare AI is designed for non-pregnant adults. Protocol guidelines differ during pregnancy. Please consult your clinician."
          );
          return;
        }
      }

      // Non-409 errors (network or 5xx): Fail-closed error with emergency notice
      const errorMsg = isUrdu
        ? "ہم آپ کا جواب نہیں بھیج سکے۔ اگر یہ ہنگامی صورتحال ہے تو فوراً اپنے مقامی ایمرجنسی نمبر پر کال کریں۔"
        : "We could not send your answer. If this is an emergency, call your local emergency number now.";
      setLiveError(errorMsg);
    }
  };

  // Live Mode Answer Submit Wrapper
  const handleLiveSendAnswer = async (answerText: string) => {
    await handleLiveSendAnswerInternal(answerText);
  };

  // Retry handler for failed answer send
  const handleRetrySend = async () => {
    if (lastFailedAnswer) {
      await handleLiveSendAnswerInternal(lastFailedAnswer);
    } else if (liveAnswerInput.trim()) {
      await handleLiveSendAnswerInternal(liveAnswerInput);
    }
  };

  // --- MOCK MODE LOGIC ---
  const handleQ1Select = (ans: boolean) => {
    setQ1Thirst(ans);
    if (!ans) {
      setQ2Urination(null);
    }
  };

  const handleQ2Select = (ans: boolean) => {
    setQ2Urination(ans);
  };

  const handleQ3Select = (ans: "yes" | "no" | "prefer_not_to_answer") => {
    setQ3MissedMeds(ans);
  };

  const isQ1Answered = q1Thirst !== null;
  const isQ2Needed = q1Thirst === true;
  const isQ2Answered = !isQ2Needed || q2Urination !== null;
  const isQ3Answered = q3MissedMeds !== null;
  const canSubmitMock = isQ1Answered && isQ2Answered && isQ3Answered;

  const handleMockSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmitMock) return;

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

  // =========================================================================
  // LIVE MODE INTERFACE
  // =========================================================================
  if (isLiveMode) {
    return (
      <div
        className="w-full max-w-xl mx-auto glass-raised rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn"
        dir={isUrdu ? "rtl" : "ltr"}
      >
        {/* Header */}
        <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/25 text-teal-200 text-xs font-bold uppercase tracking-wider mb-2.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Adaptive Interview</span>
          </div>
          <h1 className="font-heading text-2xl sm:text-[26px] font-bold mb-1.5">
            {t.adaptiveInterviewTitle}
          </h1>
          <p className="text-sm text-slate-200 max-w-md mx-auto leading-relaxed">
            {t.adaptiveInterviewSubtitle}
          </p>
        </div>

        <div className="p-6 sm:p-7 space-y-5">
          {/* Fail-closed error alert with Retry */}
          {liveError && (
            <div className="p-4 text-sm bg-amber-50 border-2 border-amber-600/60 text-amber-950 rounded-2xl space-y-2.5 animate-fadeIn">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-5 h-5 text-emergencyRed-700 shrink-0 mt-0.5" />
                <span className="font-semibold leading-relaxed">{liveError}</span>
              </div>
              <div className="flex items-center gap-2 pt-1">
                {!isPregnancyIneligible && (
                  <button
                    type="button"
                    onClick={handleRetrySend}
                    id="interview-retry-btn"
                    className="px-3.5 py-1.5 bg-amber-800 hover:bg-amber-900 text-white font-bold text-xs rounded-xl transition-colors inline-flex items-center gap-1.5 shadow-xs"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>{isUrdu ? "دوبارہ کوشش کریں" : "Retry"}</span>
                  </button>
                )}
                {isPregnancyIneligible && (
                  <button
                    type="button"
                    onClick={() => setShowSettings(true)}
                    id="interview-pregnancy-settings-btn"
                    className="px-3.5 py-1.5 bg-navy-800 hover:bg-navy-900 text-white font-bold text-xs rounded-xl transition-colors inline-flex items-center gap-1.5 shadow-xs"
                  >
                    <User className="w-3.5 h-3.5" />
                    <span>{isUrdu ? "ترتیبات میں تفصیلات اپ ڈیٹ کریں" : "Update Details in Settings"}</span>
                  </button>
                )}
                {isConsentError && !isPregnancyIneligible && (
                  <button
                    type="button"
                    onClick={() => setShowSettings(true)}
                    id="interview-consent-settings-btn"
                    className="px-3.5 py-1.5 bg-teal-700 hover:bg-teal-600 text-white font-bold text-xs rounded-xl transition-colors inline-flex items-center gap-1.5 shadow-xs"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>{isUrdu ? "اجازت نامہ کی ترتیبات کھولیں" : "Open Consent Settings"}</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Conversation Stream with aria-live */}
          <div
            className="space-y-3.5 max-h-[360px] overflow-y-auto p-1 pr-2"
            aria-live="polite"
            role="log"
          >
            {conversationHistory.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 animate-fadeIn ${
                  msg.role === "user"
                    ? isUrdu
                      ? "justify-start flex-row-reverse"
                      : "justify-end"
                    : "justify-start"
                }`}
              >
                {msg.role === "system" && (
                  <div className="w-8 h-8 rounded-full bg-navy-800 text-teal-300 flex items-center justify-center shrink-0 shadow-2xs mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`p-4 rounded-2xl text-sm leading-relaxed max-w-[85%] ${
                    msg.role === "user"
                      ? "bg-teal-700 text-white rounded-br-xs shadow-xs"
                      : "bg-slate-100/90 text-navy-900 border border-slate-200 rounded-bl-xs shadow-xs font-medium"
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}

            {isSending && (
              <div className="flex gap-3 items-center animate-fadeIn">
                <div className="w-8 h-8 rounded-full bg-navy-800 text-teal-300 flex items-center justify-center shrink-0 shadow-2xs">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-3.5 rounded-2xl bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-600 inline-flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-teal-700" />
                  <span>{t.serverTyping}</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Voice Error Notice */}
          {voiceError && (
            <div className="p-3 text-xs bg-amber-50 border border-amber-800/30 text-amber-950 rounded-xl flex items-center justify-between gap-2 animate-fadeIn">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
                <span>{voiceError}</span>
              </div>
              <button
                type="button"
                onClick={() => setVoiceError(null)}
                className="text-slate-400 hover:text-slate-700 text-xs px-1.5"
              >
                ✕
              </button>
            </div>
          )}

          {/* Transcribed Safety Review Banner */}
          {transcribedSafetyNotice && (
            <div className="p-3 rounded-xl bg-teal-50 border-2 border-teal-600 text-teal-950 text-xs font-bold flex items-center justify-between gap-2 animate-fadeIn shadow-xs">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-teal-700 shrink-0" />
                <span>
                  {isUrdu
                    ? "آواز سے لکھا گیا — براہ کرم بھیجنے سے پہلے الفاظ کی تصدیق کر لیں۔"
                    : "Transcribed from voice — check what was heard, then press Send"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setTranscribedSafetyNotice(false)}
                className="text-teal-700 hover:text-teal-900 text-xs px-1"
              >
                ✕
              </button>
            </div>
          )}

          {/* Active Input Area */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setTranscribedSafetyNotice(false);
              handleLiveSendAnswer(liveAnswerInput);
            }}
            className="space-y-3 pt-2 border-t border-slate-200"
          >
            {currentStep?.startsWith("medication_check") && (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-100 text-teal-900 border border-teal-300 text-xs font-bold uppercase tracking-wider w-fit">
                <Pill className="w-3.5 h-3.5 text-teal-700" />
                <span>{isUrdu ? "ادویات کی تصدیق" : "Medication check"}</span>
              </div>
            )}

            {/* Recording in Progress UI */}
            {isRecording ? (
              <div className="p-3.5 rounded-2xl bg-red-50 border-2 border-red-500 flex items-center justify-between gap-3 animate-pulse">
                <div className="flex items-center gap-2.5">
                  <span className="w-3 h-3 rounded-full bg-red-600 animate-ping shrink-0" />
                  <span className="text-xs font-bold text-red-900">
                    {isUrdu
                      ? `ریکارڈنگ جاری ہے (${recordingSeconds}/۶۰ سیکنڈ)`
                      : `Recording voice... (${recordingSeconds}s / 60s)`}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCancelRecording}
                    id="cancel-voice-btn"
                    className="px-2.5 py-1 text-xs font-semibold text-slate-600 hover:text-slate-900 border border-slate-300 rounded-lg bg-white"
                  >
                    {isUrdu ? "منسوخ" : "Cancel"}
                  </button>
                  <button
                    type="button"
                    onClick={handleStopRecording}
                    id="stop-voice-btn"
                    className="px-3 py-1 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg flex items-center gap-1 shadow-xs"
                  >
                    <Square className="w-3 h-3 fill-current" />
                    <span>{isUrdu ? "روکیں اور لکھیں" : "Done"}</span>
                  </button>
                </div>
              </div>
            ) : isTranscribing ? (
              <div className="p-3.5 rounded-2xl bg-teal-50 border border-teal-300 flex items-center justify-center gap-2 text-xs font-bold text-teal-900 animate-fadeIn">
                <Loader2 className="w-4 h-4 animate-spin text-teal-700" />
                <span>{isUrdu ? "آواز کا متن تیار ہو رہا ہے..." : "Transcribing your audio with Whisper..."}</span>
              </div>
            ) : (
              <div className="relative flex items-center gap-2">
                <div className="relative flex-1">
                  <input
                    ref={inputRef}
                    type="text"
                    value={liveAnswerInput}
                    onChange={(e) => {
                      setLiveAnswerInput(e.target.value);
                    }}
                    disabled={isSending}
                    placeholder={isUrdu ? "اپنا جواب یہاں لکھیں یا مائیک دبائیں..." : "Type your response or tap mic..."}
                    className={`w-full h-12 text-sm rounded-xl border ${
                      transcribedSafetyNotice ? "border-teal-500 ring-2 ring-teal-200 bg-teal-50/20" : "border-slate-300 bg-white"
                    } ${isUrdu ? "pr-4 pl-12" : "pl-4 pr-12"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 shadow-xs`}
                  />
                  <button
                    type="submit"
                    disabled={!liveAnswerInput.trim() || isSending}
                    id="live-send-answer-btn"
                    className={`absolute ${
                      isUrdu ? "left-1.5" : "right-1.5"
                    } top-1.5 bottom-1.5 px-3 bg-teal-700 hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg transition-all flex items-center justify-center`}
                  >
                    {isSending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>

                {/* Voice Input Mic Button */}
                <button
                  type="button"
                  onClick={handleStartRecording}
                  disabled={isSending}
                  id="interview-mic-btn"
                  title={
                    liveProfile?.voice_enabled === false
                      ? (isUrdu ? "سیٹنگز میں آواز کا فیچر آن کریں" : "Voice disabled - enable in Settings")
                      : (isUrdu ? "بول کر جواب دیں" : "Speak your answer")
                  }
                  className={`h-12 w-12 rounded-xl flex items-center justify-center shrink-0 transition-all border shadow-xs ${
                    liveProfile?.voice_enabled === false
                      ? "bg-slate-100 text-slate-400 border-slate-200 hover:bg-slate-200"
                      : "bg-teal-50 text-teal-800 border-teal-300 hover:bg-teal-100 active:scale-95"
                  }`}
                >
                  <Mic className="w-5 h-5" />
                </button>
              </div>
            )}

            {/* Quick-answer buttons for Medication Check Step */}
            {currentStep?.startsWith("medication_check") && (
              <div className="grid grid-cols-2 gap-2.5 pt-1">
                <button
                  type="button"
                  onClick={() => handleLiveSendAnswer("yes")}
                  disabled={isSending}
                  id="med-check-yes-btn"
                  className="min-h-[42px] py-2 px-3 rounded-xl bg-teal-50 hover:bg-teal-100 border-2 border-teal-600 text-teal-900 font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-1.5 shadow-2xs"
                >
                  <CheckCircle2 className="w-4 h-4 text-teal-700" />
                  <span>{isUrdu ? "ہاں، وہی مقدار" : "Yes, same dose"}</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleLiveSendAnswer("no")}
                  disabled={isSending}
                  id="med-check-no-btn"
                  className="min-h-[42px] py-2 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 border-2 border-slate-300 text-slate-800 font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-1.5 shadow-2xs"
                >
                  <RotateCcw className="w-4 h-4 text-slate-600" />
                  <span>{isUrdu ? "نہیں، میں نے بند کر دی ہے" : "No, I stopped it"}</span>
                </button>
              </div>
            )}

            {/* "I don't have this information" helper button */}
            <div className="flex items-center justify-between gap-3 pt-1">
              <button
                type="button"
                onClick={() => handleLiveSendAnswer("I don't have this information")}
                disabled={isSending}
                id="dont-have-info-btn"
                className="min-h-[38px] px-3 py-1.5 rounded-xl border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-600 font-semibold text-xs transition-colors"
              >
                {t.dontHaveInfoBtn}
              </button>

              <button
                type="button"
                onClick={() => setScreen("checkin_entry")}
                disabled={isSending}
                className="text-xs text-slate-500 hover:text-navy-800 transition-colors"
              >
                {t.back}
              </button>
            </div>
          </form>

          {/* Permanent Emergency Disclaimer on Interview Screen */}
          <div className="pt-2 text-center border-t border-slate-100">
            <p className="text-[11px] font-medium text-slate-500">
              {isUrdu
                ? "ہنگامی صورتحال میں اپنے مقامی ایمرجنسی نمبر پر رابطہ کریں۔"
                : "In an emergency, call your local emergency number."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // MOCK MODE INTERFACE (Preserves original 3-question flow)
  // =========================================================================
  return (
    <div className="w-full max-w-lg mx-auto glass-raised rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/25 text-teal-200 text-xs font-bold uppercase tracking-wider mb-2.5">
          <Sparkles className="w-3.5 h-3.5" />
          <span>{t.questionCount}</span>
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold mb-1.5">{t.adaptiveInterviewTitle}</h1>
        <p className="text-sm text-slate-200 max-w-md mx-auto leading-relaxed">{t.adaptiveInterviewSubtitle}</p>
      </div>

      <form onSubmit={handleMockSubmit} className="p-6 sm:p-7 space-y-6">
        {/* QUESTION 1 */}
        <div className="p-5 rounded-2xl bg-slate-50/90 border border-slate-200 space-y-4 transition-all">
          <div className="flex items-start gap-3">
            <span className="w-7 h-7 rounded-full bg-navy-800 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
              1
            </span>
            <p className="text-base font-semibold text-navy-800 leading-relaxed flex-1">
              {t.q1Text}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <button
              type="button"
              id="q1-yes-btn"
              onClick={() => handleQ1Select(true)}
              className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border-2 transition-all flex items-center justify-center ${
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
              className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border-2 transition-all flex items-center justify-center ${
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
          <div className="p-5 rounded-2xl bg-teal-50/70 border border-teal-300 space-y-4 transition-all animate-fadeIn">
            <div className="flex items-start gap-3">
              <span className="w-7 h-7 rounded-full bg-teal-700 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                2
              </span>
              <div className="flex-1">
                <span className="text-xs font-bold uppercase tracking-wider text-teal-800 block mb-0.5">
                  Follow-up Question
                </span>
                <p className="text-base font-semibold text-navy-800 leading-relaxed">
                  {t.q2Text}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <button
                type="button"
                id="q2-yes-btn"
                onClick={() => handleQ2Select(true)}
                className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border-2 transition-all flex items-center justify-center ${
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
                className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border-2 transition-all flex items-center justify-center ${
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

        {/* QUESTION 3 */}
        {isQ1Answered && (
          <div className="p-5 rounded-2xl bg-slate-50/90 border border-slate-200 space-y-4 transition-all animate-fadeIn">
            <div className="flex items-start gap-3">
              <span className="w-7 h-7 rounded-full bg-navy-800 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
                {q1Thirst === true ? "3" : "2"}
              </span>
              <p className="text-base font-semibold text-navy-800 leading-relaxed flex-1">
                {t.q3Text}
              </p>
            </div>

            <div className="space-y-3 pt-1">
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  id="q3-yes-btn"
                  onClick={() => handleQ3Select("yes")}
                  className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border-2 transition-all flex items-center justify-center ${
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
                  className={`min-h-[48px] py-3 px-4 rounded-xl text-sm font-semibold border-2 transition-all flex items-center justify-center ${
                    q3MissedMeds === "no"
                      ? "bg-mutedGreen-800 text-white border-mutedGreen-800 shadow-md"
                      : "bg-white text-navy-800 border-slate-200 hover:border-mutedGreen-800 hover:bg-mutedGreen-50/50"
                  }`}
                >
                  {t.no}
                </button>
              </div>

              <button
                type="button"
                id="q3-prefer-not-btn"
                onClick={() => handleQ3Select("prefer_not_to_answer")}
                className={`w-full min-h-[44px] py-2.5 px-4 rounded-xl text-xs font-semibold border transition-all text-center flex items-center justify-center ${
                  q3MissedMeds === "prefer_not_to_answer"
                    ? "bg-slate-700 text-white border-slate-700 shadow-sm"
                    : "bg-white text-slate-600 border-slate-300 hover:bg-slate-100 hover:text-navy-800"
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
            className="min-h-[48px] px-5 py-3 border border-slate-300 bg-white text-slate-700 font-semibold text-sm rounded-xl hover:bg-slate-50 transition-all flex items-center gap-2 shadow-xs"
          >
            <ArrowLeft className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            <span>{t.back}</span>
          </button>

          <button
            type="submit"
            disabled={!canSubmitMock}
            id="submit-checkin-btn"
            className={`flex-1 min-h-[48px] py-3 px-5 font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 ${
              canSubmitMock
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
