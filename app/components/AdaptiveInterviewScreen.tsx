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
  const [conversationHistory, setConversationHistory] = useState<ChatMessage[]>([]);
  const [currentStep, setCurrentStep] = useState<string | null>(activeLiveCheckin?.step || null);
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);
  const [lastFailedAnswer, setLastFailedAnswer] = useState<string | null>(null);

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

  // Scroll to bottom & focus on question update (P3 requirement)
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
    if (inputRef.current) {
      inputRef.current.focus();
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
          if (err.status === 403 && detailStr.includes("profile_incomplete")) {
            setScreen("inclusion");
            return;
          }
          if (err.status === 403 || detailStr.includes("consent")) {
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

      if (answerRes.phase) {
        setCurrentPhase(answerRes.phase);
      }

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
      let completeRes: CheckinCompleteResponse;
      try {
        completeRes = await api.completeCheckin(targetCheckinId);
      } catch (completeErr: any) {
        // Handle 409 triage_incomplete: refetch check-in once and continue
        if (
          completeErr instanceof ApiError &&
          completeErr.status === 409 &&
          (completeErr.detail?.includes("triage_incomplete") || completeErr.data?.detail === "triage_incomplete")
        ) {
          const detailRes = await api.getUserCheckinDetail(targetCheckinId);
          const detailState = detailRes.state || {};
          if (detailState.step) setCurrentStep(detailState.step);
          if (detailState.question) {
            setLiveQuestion(detailState.question);
            setConversationHistory((prev) => [
              ...prev,
              { role: "system", text: detailState.question },
            ]);
          }
          setIsSending(false);
          isSendingRef.current = false;
          return;
        }
        throw completeErr;
      }

      setLiveCheckinResult(completeRes);

      // Route by result
      if (completeRes.emergency) {
        setEscalationRecorded(true);
        setScreen("emergency");
      } else if (
        completeRes.triage &&
        (completeRes.triage.level === "urgent" || completeRes.triage.level === "review")
      ) {
        setScreen("triage_result");
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
                <button
                  type="button"
                  onClick={handleRetrySend}
                  id="interview-retry-btn"
                  className="px-3.5 py-1.5 bg-amber-800 hover:bg-amber-900 text-white font-bold text-xs rounded-xl transition-colors inline-flex items-center gap-1.5 shadow-xs"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>{isUrdu ? "دوبارہ کوشش کریں" : "Retry"}</span>
                </button>
                {isConsentError && (
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

          {/* Active Input Area */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleLiveSendAnswer(liveAnswerInput);
            }}
            className="space-y-3 pt-2 border-t border-slate-200"
          >
            {/* Phase / Step Indicator Chip */}
            {currentPhase === "triage" || currentStep?.startsWith("triage:") ? (
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 text-amber-950 border border-amber-300 text-xs font-bold uppercase tracking-wider w-fit">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-700" />
                  <span>{isUrdu ? "حفاظتی سوالات" : "Safety questions"}</span>
                </div>
                {isUrdu && (
                  <span className="text-[11px] text-slate-500 italic">
                    یہ سوالات انگریزی میں دکھائے گئے ہیں۔
                  </span>
                )}
              </div>
            ) : currentStep?.startsWith("medication_check") ? (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-100 text-teal-900 border border-teal-300 text-xs font-bold uppercase tracking-wider w-fit">
                <Pill className="w-3.5 h-3.5 text-teal-700" />
                <span>{isUrdu ? "ادویات کی تصدیق" : "Medication check"}</span>
              </div>
            ) : null}

            <div className="relative">
              <input
                ref={inputRef}
                type="text"
                value={liveAnswerInput}
                onChange={(e) => setLiveAnswerInput(e.target.value)}
                disabled={isSending}
                placeholder={
                  (currentPhase === "triage" || currentStep?.startsWith("triage:")) && liveQuestion.includes("type: cannot")
                    ? isUrdu
                      ? "مثال کے طور پر 150/90"
                      : "for example 150/90"
                    : isUrdu
                    ? "اپنا جواب یہاں لکھیں..."
                    : "Type your response..."
                }
                className={`w-full h-12 text-sm rounded-xl border border-slate-300 bg-white ${
                  isUrdu ? "pr-4 pl-12" : "pl-4 pr-12"
                } text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 shadow-xs`}
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

            {/* Quick-answer buttons for Triage "Answer yes or no" questions */}
            {(currentPhase === "triage" || currentStep?.startsWith("triage:")) && liveQuestion.includes("Answer yes or no") && (
              <div className="grid grid-cols-2 gap-2.5 pt-1">
                <button
                  type="button"
                  onClick={() => handleLiveSendAnswer("yes")}
                  disabled={isSending}
                  id="triage-yes-btn"
                  className="min-h-[42px] py-2 px-3 rounded-xl bg-teal-50 hover:bg-teal-100 border-2 border-teal-600 text-teal-900 font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-1.5 shadow-2xs"
                >
                  <CheckCircle2 className="w-4 h-4 text-teal-700" />
                  <span>{isUrdu ? "ہاں (Yes)" : "Yes"}</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleLiveSendAnswer("no")}
                  disabled={isSending}
                  id="triage-no-btn"
                  className="min-h-[42px] py-2 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 border-2 border-slate-300 text-slate-800 font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-1.5 shadow-2xs"
                >
                  <RotateCcw className="w-4 h-4 text-slate-600" />
                  <span>{isUrdu ? "نہیں (No)" : "No"}</span>
                </button>
              </div>
            )}

            {/* Quick-answer button for Triage "type: cannot" re-measure question */}
            {(currentPhase === "triage" || currentStep?.startsWith("triage:")) && liveQuestion.includes("type: cannot") && (
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => handleLiveSendAnswer("cannot")}
                  disabled={isSending}
                  id="triage-cannot-measure-btn"
                  className="w-full min-h-[42px] py-2 px-3 rounded-xl bg-amber-50 hover:bg-amber-100 border-2 border-amber-400 text-amber-950 font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-1.5 shadow-2xs"
                >
                  <RotateCcw className="w-4 h-4 text-amber-700" />
                  <span>{isUrdu ? "میں دوبارہ ناپ نہیں سکتا (I can't measure again)" : "I can't measure again"}</span>
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
