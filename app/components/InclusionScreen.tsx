"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { UserCheck, ShieldAlert, ArrowRight, Calendar, CheckCircle2, Loader2, Sparkles, AlertCircle, HeartHandshake } from "lucide-react";
import { api, ApiError, ProfileUpdateRequest } from "../lib/api";
import { calculateAgeFromDob } from "../lib/presentation";

export const InclusionScreen = () => {
  const {
    setScreen,
    profile,
    setProfile,
    liveProfile,
    setLiveProfile,
    liveEhrConnection,
    isLiveMode,
    language,
    t,
    isUrdu,
  } = useApp();

  const [dateOfBirth, setDateOfBirth] = useState<string>(liveProfile?.date_of_birth || profile.date_of_birth || "");
  const [sexAtBirth, setSexAtBirth] = useState<"female" | "male" | "prefer_not_to_say" | "">(
    (liveProfile?.sex_at_birth as any) || (profile.sex_at_birth as any) || ""
  );
  const [pregnancyStatus, setPregnancyStatus] = useState<"no" | "yes" | "not_sure" | "not_applicable" | "">(
    (liveProfile?.pregnancy_status as any) || (profile.pregnancy_status as any) || ""
  );
  const [confirmedAdult, setConfirmedAdult] = useState<boolean>(Boolean(liveProfile?.inclusion_confirmed_at));
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showIneligibleNotice, setShowIneligibleNotice] = useState<boolean>(false);

  useEffect(() => {
    if (liveProfile?.date_of_birth) {
      setDateOfBirth(liveProfile.date_of_birth);
    }
    if (liveProfile?.sex_at_birth) {
      setSexAtBirth(liveProfile.sex_at_birth as any);
    }
    if (liveProfile?.pregnancy_status) {
      setPregnancyStatus(liveProfile.pregnancy_status as any);
      if (liveProfile.pregnancy_status === "yes" || liveProfile.pregnancy_status === "not_sure") {
        setShowIneligibleNotice(true);
      }
    }
    if (liveProfile?.inclusion_confirmed_at) {
      setConfirmedAdult(true);
    }
  }, [liveProfile]);

  const computedAge = calculateAgeFromDob(dateOfBirth);

  const handleSexChange = (newSex: "female" | "male" | "prefer_not_to_say") => {
    setSexAtBirth(newSex);
    setError(null);
    if (newSex === "male") {
      setPregnancyStatus("not_applicable");
      setShowIneligibleNotice(false);
    } else {
      if (pregnancyStatus === "not_applicable") {
        setPregnancyStatus("");
      }
    }
  };

  const handlePregnancyChange = (status: "no" | "yes" | "not_sure") => {
    setPregnancyStatus(status);
    setError(null);
    if (status === "yes" || status === "not_sure") {
      setShowIneligibleNotice(true);
    } else {
      setShowIneligibleNotice(false);
    }
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

    const age = calculateAgeFromDob(cleanDob);
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

    if (!sexAtBirth) {
      setError(
        isUrdu
          ? "براہ کرم پیدائشی جنس کا انتخاب کریں۔"
          : "Please select your sex at birth."
      );
      return;
    }

    if ((sexAtBirth === "female" || sexAtBirth === "prefer_not_to_say") && !pregnancyStatus) {
      setError(
        isUrdu
          ? "براہ کرم حمل سے متعلق سوال کا جواب دیں۔"
          : "Please answer the pregnancy screening question."
      );
      return;
    }

    if (!confirmedAdult) {
      setError(
        isUrdu
          ? "براہ کرم تصدیق کریں کہ آپ کی عمر ۱۸ سال یا اس سے زیادہ ہے۔"
          : "Please confirm that you are 18 years of age or older."
      );
      return;
    }

    const effectivePreg = sexAtBirth === "male" ? "not_applicable" : pregnancyStatus;

    // If patient is pregnant or unconfirmed, persist and show ineligible screen
    if (effectivePreg === "yes" || effectivePreg === "not_sure") {
      setIsLoading(true);
      if (isLiveMode) {
        try {
          const payload: ProfileUpdateRequest = {
            date_of_birth: cleanDob,
            inclusion_confirmed: false,
            sex_at_birth: sexAtBirth,
            pregnancy_status: effectivePreg,
            language: liveProfile?.language || language || "en",
          };
          const updated = await api.updateProfile(payload);
          setLiveProfile(updated);
        } catch {
          // ignore
        } finally {
          setIsLoading(false);
          setShowIneligibleNotice(true);
        }
      } else {
        setProfile({
          ...profile,
          date_of_birth: cleanDob,
          sex_at_birth: sexAtBirth,
          pregnancy_status: effectivePreg,
        });
        setIsLoading(false);
        setShowIneligibleNotice(true);
      }
      return;
    }

    setIsLoading(true);

    if (isLiveMode) {
      try {
        const payload: ProfileUpdateRequest = {
          date_of_birth: cleanDob,
          inclusion_confirmed: true,
          sex_at_birth: sexAtBirth,
          pregnancy_status: effectivePreg,
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
    setProfile({
      ...profile,
      date_of_birth: cleanDob,
      sex_at_birth: sexAtBirth,
      pregnancy_status: effectivePreg,
    });
    setIsLoading(false);
    if (!profile.conditions || profile.conditions.length === 0) {
      setScreen("profile");
    } else {
      setScreen("home");
    }
  };

  // If patient selected Yes or Not Sure for pregnancy, render the clinical ineligibility screen
  if (showIneligibleNotice) {
    return (
      <div
        className="w-full max-w-lg mx-auto bg-white rounded-3xl border border-amber-200 shadow-xl overflow-hidden animate-fadeIn text-center"
        dir={isUrdu ? "rtl" : "ltr"}
      >
        <div className="bg-amber-800 p-7 text-white text-center">
          <div className="w-16 h-16 rounded-2xl bg-amber-700 border border-amber-500/50 flex items-center justify-center mx-auto mb-3 shadow-md text-amber-200">
            <HeartHandshake className="w-8 h-8" />
          </div>
          <h1 className="font-heading text-2xl font-bold text-white mb-1.5">
            {isUrdu ? "براہ کرم اپنے معالج سے رابطہ کریں" : "Please Consult Your Healthcare Clinician"}
          </h1>
          <p className="text-xs sm:text-sm text-amber-100 max-w-sm mx-auto leading-relaxed">
            {isUrdu
              ? "دوران حمل محفوظ طبی رہنمائی کے لیے خصوصی طبی نگہداشت ضروری ہے۔"
              : "Specialized clinical guidelines apply during pregnancy."}
          </p>
        </div>

        <div className="p-6 sm:p-7 space-y-5 text-left">
          <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-sm text-amber-950 space-y-2 leading-relaxed">
            <p className="font-semibold">
              {isUrdu
                ? "یہ ایپلیکیشن صرف غیر حاملہ بالغ افراد کے لیے ڈیزائن کی گئی ہے۔"
                : "ChronicCare AI decision-support checks and target ranges are designed exclusively for non-pregnant adults."}
            </p>
            <p className="text-xs text-amber-900 leading-normal">
              {isUrdu
                ? "دوران حمل خون میں شوگر اور بلڈ پریشر کے معیاری اہداف مختلف ہوتے ہیں اور ان کے لیے قریبی طبی نگرانی درکار ہوتی ہے۔ کوئی خودکار تشخیصی تجزیہ نہیں کیا جائے گا۔"
                : "During pregnancy, blood pressure thresholds and glycemic targets differ significantly and require personalized direct obstetric and medical care. No check-in readings will be assessed."}
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1">
            <span className="font-bold text-navy-900 block">
              {isUrdu ? "معلومات میں تبدیلی کی صورت میں:" : "When your situation changes:"}
            </span>
            <p>
              {isUrdu
                ? "جب آپ کی حالت تبدیل ہو، آپ ترتیبات (Settings) میں 'میری تفصیلات' (My Details) میں جا کر اپنے جوابات کو اپ ڈیٹ کر سکتے ہیں۔"
                : "You can return to 'My Details' in Settings at any time to update your health profile."}
            </p>
          </div>

          <div className="pt-2">
            <button
              type="button"
              id="ineligible-back-btn"
              onClick={() => {
                setShowIneligibleNotice(false);
                setPregnancyStatus("");
              }}
              className="w-full py-3.5 px-4 bg-navy-800 hover:bg-navy-700 text-white font-bold text-sm rounded-xl transition-all shadow-md"
            >
              {isUrdu ? "معلومات درست کریں" : "Update My Details"}
            </button>
          </div>
        </div>
      </div>
    );
  }

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

        {Boolean(liveProfile?.inclusion_confirmed_at && !liveProfile?.sex_at_birth) && (
          <div className="p-3.5 rounded-xl bg-teal-50 border border-teal-200 text-xs text-teal-950 flex items-start gap-2.5 animate-fadeIn">
            <Sparkles className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span>
              {isUrdu
                ? "ایک نیا حفاظتی سوال شامل کیا گیا ہے۔ براہ کرم جاری رکھنے سے پہلے پیدائشی جنس اور حمل کا سوال مکمل کریں۔"
                : "A new clinical safety question has been added. Please answer the sex at birth and pregnancy screening below to proceed."}
            </span>
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

        {/* Sex at Birth Selection */}
        <div className="space-y-2">
          <label className="block text-xs font-bold uppercase tracking-wider text-navy-800">
            {isUrdu ? "پیدائشی جنس:" : "Sex at birth:"}
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              id="sex-female-btn"
              onClick={() => handleSexChange("female")}
              className={`min-h-[40px] px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                sexAtBirth === "female"
                  ? "bg-teal-700 text-white border-teal-700 shadow-xs"
                  : "bg-white text-navy-800 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {isUrdu ? "خاتون (Female)" : "Female"}
            </button>
            <button
              type="button"
              id="sex-male-btn"
              onClick={() => handleSexChange("male")}
              className={`min-h-[40px] px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                sexAtBirth === "male"
                  ? "bg-navy-800 text-white border-navy-800 shadow-xs"
                  : "bg-white text-navy-800 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {isUrdu ? "مرد (Male)" : "Male"}
            </button>
            <button
              type="button"
              id="sex-prefer-not-btn"
              onClick={() => handleSexChange("prefer_not_to_say")}
              className={`min-h-[40px] px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                sexAtBirth === "prefer_not_to_say"
                  ? "bg-teal-700 text-white border-teal-700 shadow-xs"
                  : "bg-white text-navy-800 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {isUrdu ? "بتانا نہیں چاہتے" : "Prefer not to say"}
            </button>
          </div>
        </div>

        {/* Pregnancy Question (Female or Prefer not to say) */}
        {(sexAtBirth === "female" || sexAtBirth === "prefer_not_to_say") && (
          <div className="p-4 rounded-2xl bg-teal-50/70 border border-teal-200 space-y-2.5 animate-fadeIn">
            <label className="block text-xs font-bold text-navy-900 leading-snug">
              {isUrdu ? "کیا آپ فی الوقت حاملہ ہیں؟" : "Are you currently pregnant?"}
            </label>
            <p className="text-[11px] text-slate-600">
              {isUrdu
                ? "دوران حمل خون میں شوگر اور بلڈ پریشر کے اہداف مختلف ہوتے ہیں۔"
                : "Pregnancy requires specialized clinical management."}
            </p>
            <div className="grid grid-cols-3 gap-2 pt-1">
              <button
                type="button"
                id="pregnancy-no-btn"
                onClick={() => handlePregnancyChange("no")}
                className={`min-h-[38px] px-2 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                  pregnancyStatus === "no"
                    ? "bg-teal-700 text-white border-teal-700 shadow-xs"
                    : "bg-white text-navy-800 border-slate-200 hover:bg-slate-50"
                }`}
              >
                {isUrdu ? "نہیں (No)" : "No"}
              </button>
              <button
                type="button"
                id="pregnancy-yes-btn"
                onClick={() => handlePregnancyChange("yes")}
                className={`min-h-[38px] px-2 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                  pregnancyStatus === "yes"
                    ? "bg-amber-800 text-white border-amber-800 shadow-xs"
                    : "bg-white text-navy-800 border-slate-200 hover:bg-slate-50"
                }`}
              >
                {isUrdu ? "ہاں (Yes)" : "Yes"}
              </button>
              <button
                type="button"
                id="pregnancy-notsure-btn"
                onClick={() => handlePregnancyChange("not_sure")}
                className={`min-h-[38px] px-2 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                  pregnancyStatus === "not_sure"
                    ? "bg-amber-800 text-white border-amber-800 shadow-xs"
                    : "bg-white text-navy-800 border-slate-200 hover:bg-slate-50"
                }`}
              >
                {isUrdu ? "یقین نہیں ہے" : "I am not sure"}
              </button>
            </div>
          </div>
        )}

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
                  ? "میں تصدیق کرتا/کرتی ہوں کہ میری عمر ۱۸ سال یا اس سے زیادہ ہے۔"
                  : "I confirm that I am 18 years of age or older."}
              </span>
              <p className="text-[11px] text-slate-500 leading-normal">
                {isUrdu
                  ? "یہ پروٹوکول صرف بالغ افراد کے لیے کونسل کی رہنمائی کے مطابق ڈیزائن کیا گیا ہے۔"
                  : "Protocols are designed for non-pregnant adult chronic disease management."}
              </p>
            </div>
          </label>
        </div>

        {/* Action Buttons */}
        <div className="pt-2 flex items-center justify-between gap-3">
          <button
            type="submit"
            disabled={isLoading || !dateOfBirth || !sexAtBirth || (!pregnancyStatus && sexAtBirth !== "male") || !confirmedAdult}
            id="inclusion-submit-btn"
            className="w-full py-3.5 px-5 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm rounded-xl transition-all shadow-md flex items-center justify-center gap-2 active:scale-[0.99]"
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
