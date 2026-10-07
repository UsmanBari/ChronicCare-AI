"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { UserCheck, ShieldAlert, ArrowRight, Calendar, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { api, ApiError, ProfileUpdateRequest } from "../lib/api";

export const InclusionScreen = () => {
  const {
    setScreen,
    liveProfile,
    setLiveProfile,
    liveEhrConnection,
    isLiveMode,
    language,
    t,
    isUrdu,
  } = useApp();

  const [dateOfBirth, setDateOfBirth] = useState<string>(liveProfile?.date_of_birth || "");
  const [confirmedAdult, setConfirmedAdult] = useState<boolean>(Boolean(liveProfile?.inclusion_confirmed_at));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (liveProfile?.date_of_birth) {
      setDateOfBirth(liveProfile.date_of_birth);
    }
    if (liveProfile?.inclusion_confirmed_at) {
      setConfirmedAdult(true);
    }
  }, [liveProfile]);

  const calculateAge = (dobString: string): number | null => {
    if (!dobString || !/^\d{4}-\d{2}-\d{2}$/.test(dobString)) return null;
    const parts = dobString.split("-").map(Number);
    const birthDate = new Date(parts[0], parts[1] - 1, parts[2]);
    if (isNaN(birthDate.getTime())) return null;

    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  };

  const handleContinue = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanDob = dateOfBirth.trim();
    if (!cleanDob) {
      setError(
        isUrdu
          ? "براہ کرم اپنی تاریخ پیدائش درج کریں۔"
          : "Please enter your date of birth."
      );
      return;
    }

    if (!/^\d{4}-\d{2}-\d{2}$/.test(cleanDob)) {
      setError(
        isUrdu
          ? "تاریخ پیدائش درست فارمیٹ (YYYY-MM-DD) میں درج کریں۔"
          : "Please enter a valid date in YYYY-MM-DD format."
      );
      return;
    }

    const age = calculateAge(cleanDob);
    if (age === null || age > 120 || age < 0) {
      setError(
        isUrdu
          ? "براہ کرم ایک درست تاریخ پیدائش درج کریں۔"
          : "Please enter a valid date of birth."
      );
      return;
    }

    if (age < 18) {
      setError(
        isUrdu
          ? "یہ سروس صرف ۱۸ سال یا اس سے زائد عمر کے بالغ افراد کے لیے ہے۔"
          : "Service is for adults aged 18 and older only."
      );
      return;
    }

    if (!confirmedAdult) {
      setError(
        isUrdu
          ? "براہ کرم تصدیق کریں کہ آپ کی عمر ۱۸ سال سے زیادہ ہے اور آپ حاملہ نہیں ہیں۔"
          : "Please confirm that you are 18 or older and not currently pregnant."
      );
      return;
    }

    setIsLoading(true);

    if (isLiveMode) {
      try {
        const payload: ProfileUpdateRequest = {
          date_of_birth: cleanDob,
          inclusion_confirmed: true,
          language: liveProfile?.language || language || "en",
        };
        if (liveProfile?.conditions && liveProfile.conditions.length > 0) {
          payload.conditions = liveProfile.conditions;
          payload.on_insulin_or_sulfonylurea = Boolean(liveProfile.on_insulin_or_sulfonylurea);
        }

        const updated = await api.updateProfile(payload);
        setLiveProfile(updated);

        // Determine next step: if conditions empty -> profile, else if connection needed -> connection, else -> home
        if (!updated.conditions || updated.conditions.length === 0) {
          setScreen("profile");
        } else if (!liveEhrConnection || (liveEhrConnection.mode !== "connected" && liveEhrConnection.mode !== "isolated" && liveEhrConnection.mode !== "fhir")) {
          setScreen("connection");
        } else {
          setScreen("home");
        }
      } catch (err: any) {
        if (err instanceof ApiError) {
          setError(err.getFriendlyMessage(isUrdu));
        } else {
          setError(err?.message || "Failed to save inclusion details.");
        }
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // Mock Mode
    setIsLoading(false);
    if (!liveProfile?.conditions || liveProfile.conditions.length === 0) {
      setScreen("profile");
    } else {
      setScreen("home");
    }
  };

  const computedAge = calculateAge(dateOfBirth);

  return (
    <div
      className="w-full max-w-lg mx-auto bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      {/* Hero Header */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-7 text-white text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-teal-500/20 border border-teal-400/40 flex items-center justify-center mx-auto mb-3.5 shadow-inner text-teal-300">
          <UserCheck className="w-7 h-7" />
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold tracking-tight text-white mb-1.5">
          {isUrdu ? "طبی شمولیت اور عمر کی تصدیق" : "Clinical Inclusion & Eligibility"}
        </h1>
        <p className="text-slate-200 text-xs sm:text-sm leading-relaxed max-w-sm mx-auto">
          {isUrdu
            ? "محفوظ طبی رہنمائی کے لیے تاریخ پیدائش اور بالغ ہونے کی تصدیق ضروری ہے۔"
            : "ChronicCare AI decision-support requires confirmed adult eligibility (18+ non-pregnant)."}
        </p>
      </div>

      {/* Form Content */}
      <form onSubmit={handleContinue} className="p-6 sm:p-7 space-y-6">
        {error && (
          <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2 animate-fadeIn">
            <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Date of Birth Input */}
        <div className="space-y-2">
          <label className="block text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-teal-700" />
              <span>{isUrdu ? "تاریخ پیدائش (YYYY-MM-DD):" : "Date of Birth (YYYY-MM-DD):"}</span>
            </span>
            {computedAge !== null && computedAge >= 0 && computedAge <= 120 && (
              <span className="text-[11px] font-semibold text-teal-800 bg-teal-50 px-2 py-0.5 rounded-full">
                {isUrdu ? `${computedAge} سال` : `Age: ${computedAge} yrs`}
              </span>
            )}
          </label>
          <input
            type="date"
            id="inclusion-dob-input"
            value={dateOfBirth}
            max={new Date().toISOString().split("T")[0]}
            onChange={(e) => {
              setDateOfBirth(e.target.value);
              setError(null);
            }}
            required
            className="w-full text-sm font-medium rounded-xl border border-slate-300 bg-white p-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
          />
          <p className="text-[11px] text-slate-500">
            {isUrdu
              ? "پروٹوکول کے مطابق صرف ۱۸ سال یا اس سے زائد عمر کے مریض اہل ہیں۔"
              : "Clinical protocol safety guidelines require adult patients (18 years or older)."}
          </p>
        </div>

        {/* Inclusion Checkbox */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              id="inclusion-confirm-checkbox"
              checked={confirmedAdult}
              onChange={(e) => {
                setConfirmedAdult(e.target.checked);
                setError(null);
              }}
              className="w-5 h-5 mt-0.5 text-teal-700 rounded border-slate-300 focus:ring-teal-700 cursor-pointer"
            />
            <div className="space-y-1 min-w-0 flex-1">
              <span className="text-xs sm:text-sm font-semibold text-navy-900 leading-snug block">
                {isUrdu
                  ? "میں تصدیق کرتا/کرتی ہوں کہ میری عمر ۱۸ سال یا اس سے زیادہ ہے اور میں فی الوقت حاملہ نہیں ہوں۔"
                  : "I confirm that I am 18 years of age or older, and I am not currently pregnant."}
              </span>
              <p className="text-[11px] text-slate-500 leading-normal">
                {isUrdu
                  ? "یہ پروٹوکول صرف غیر حاملہ بالغ افراد کے لیے کونسل کی رہنمائی کے مطابق ڈیزائن کیا گیا ہے۔"
                  : "Protocols are designed for non-pregnant adult chronic disease management."}
              </p>
            </div>
          </label>
        </div>

        {/* Action Buttons */}
        <div className="pt-2 flex items-center justify-between gap-3">
          <button
            type="submit"
            disabled={isLoading || !dateOfBirth || !confirmedAdult}
            id="inclusion-submit-btn"
            className="w-full py-3.5 px-5 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white font-bold text-sm rounded-xl transition-all shadow-md flex items-center justify-center gap-2 active:scale-[0.99]"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>{isUrdu ? "محفوظ کریں اور آگے بڑھیں" : "Save & Continue"}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
