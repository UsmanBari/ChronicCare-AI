"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { ShieldCheck, ShieldAlert, Calendar, CheckCircle2, ArrowRight, Loader2, Info } from "lucide-react";
import { api, ApiError, ProfileUpdateRequest } from "../lib/api";
import { mapApiError } from "../lib/presentation";

export const InclusionScreen = () => {
  const {
    setScreen,
    liveProfile,
    setLiveProfile,
    liveEhrConnection,
    isLiveMode,
    t,
    isUrdu,
  } = useApp();

  const [dateOfBirth, setDateOfBirth] = useState<string>("");
  const [inclusionConfirmed, setInclusionConfirmed] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const calculateAge = (dobString: string): number | null => {
    if (!dobString) return null;
    const parts = dobString.split("-");
    if (parts.length !== 3) return null;
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    if (isNaN(year) || isNaN(month) || isNaN(day)) return null;

    const dob = new Date(year, month, day);
    if (isNaN(dob.getTime())) return null;

    const today = new Date();
    if (dob > today) return -1; // Future date indicator

    let age = today.getFullYear() - dob.getFullYear();
    const monthDiff = today.getMonth() - dob.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
      age--;
    }
    return age;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!dateOfBirth) {
      setError(
        isUrdu
          ? "براہ کرم اپنی تاریخ پیدائش درج کریں۔"
          : "Please enter your date of birth."
      );
      return;
    }

    const age = calculateAge(dateOfBirth);
    if (age === null || age < 0 || age > 120) {
      setError(
        isUrdu
          ? "براہ کرم درست تاریخ پیدائش درج کریں (عمر 18 تا 120 سال)۔"
          : "Please enter a valid date of birth (age 18 to 120)."
      );
      return;
    }

    if (age < 18) {
      setError(
        isUrdu
          ? "ChronicCare AI اس ریلیز میں صرف بالغوں (18 اور اس سے زیادہ) کے لیے ہے۔"
          : "ChronicCare AI is for adults (18 and over) in this release."
      );
      return;
    }

    if (!inclusionConfirmed) {
      setError(
        isUrdu
          ? "براہ کرم شمولیت کے معیار کی تصدیق کریں۔"
          : "Please confirm that you meet the inclusion criteria."
      );
      return;
    }

    setIsLoading(true);

    try {
      if (isLiveMode) {
        const payload: ProfileUpdateRequest = {
          conditions: liveProfile?.conditions && liveProfile.conditions.length > 0
            ? liveProfile.conditions
            : ["diabetes"],
          on_insulin_or_sulfonylurea: Boolean(liveProfile?.on_insulin_or_sulfonylurea),
          language: liveProfile?.language || (isUrdu ? "ur" : "en"),
          date_of_birth: dateOfBirth,
          inclusion_confirmed: true,
        };

        const updated = await api.updateProfile(payload);
        setLiveProfile(updated);
      }

      // Route based on whether EHR connection setup was previously completed
      if (!liveEhrConnection?.mode) {
        setScreen("connection");
      } else {
        setScreen("home");
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        const detailStr = (err.detail || "").toLowerCase();
        if (detailStr.includes("adults_only")) {
          setError(
            isUrdu
              ? "ChronicCare AI اس ریلیز میں صرف بالغوں (18 اور اس سے زیادہ) کے لیے ہے۔"
              : "ChronicCare AI is for adults (18 and over) in this release."
          );
        } else if (detailStr.includes("invalid_date_of_birth")) {
          setError(
            isUrdu
              ? "براہ کرم درست تاریخ پیدائش درج کریں (عمر 18 تا 120 سال)۔"
              : "Please enter a valid date of birth (age 18 to 120)."
          );
        } else {
          setError(mapApiError(err.status, err.detail));
        }
      } else {
        setError(err?.message || "Failed to save inclusion criteria.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="w-full max-w-lg mx-auto bg-white rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn"
      dir={isUrdu ? "rtl" : "ltr"}
    >
      {/* Header */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-7 text-white text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-teal-500/20 border border-teal-400/40 flex items-center justify-center mx-auto mb-3.5 shadow-inner text-teal-300">
          <ShieldCheck className="w-7 h-7" />
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold tracking-tight text-white mb-1.5">
          {t.inclusionTitle}
        </h1>
        <p className="text-slate-200 text-xs sm:text-sm leading-relaxed max-w-sm mx-auto">
          {t.inclusionSubtitle}
        </p>
      </div>

      {/* Form Content */}
      <form onSubmit={handleSubmit} className="p-6 sm:p-7 space-y-6">
        {error && (
          <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Date of Birth Input */}
        <div className="space-y-2">
          <label
            htmlFor="date-of-birth-input"
            className="block text-xs font-bold text-navy-800 uppercase tracking-wider"
          >
            {t.dateOfBirthLabel}
          </label>
          <div className="relative">
            <input
              id="date-of-birth-input"
              type="date"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
              max={new Date().toISOString().split("T")[0]}
              required
              className="w-full h-12 text-sm rounded-xl border border-slate-300 bg-white px-4 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700 shadow-xs"
            />
          </div>
          <p className="text-xs text-slate-500">
            {t.dateOfBirthHint}
          </p>
        </div>

        {/* Research Prototype & Inclusion Explanation Card */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2.5">
          <div className="flex items-start gap-2 text-xs text-slate-700 leading-relaxed">
            <Info className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span>
              {t.inclusionExplanation}
            </span>
          </div>
        </div>

        {/* Required Confirmation Checkbox */}
        <label className="flex items-start gap-3 p-4 rounded-2xl border-2 border-slate-200 hover:border-teal-500 bg-white cursor-pointer transition-all">
          <input
            id="inclusion-checkbox"
            type="checkbox"
            checked={inclusionConfirmed}
            onChange={(e) => setInclusionConfirmed(e.target.checked)}
            className="w-5 h-5 rounded border-slate-300 text-teal-700 focus:ring-teal-700 mt-0.5"
          />
          <div className="text-xs sm:text-sm text-navy-900 font-semibold leading-relaxed">
            {t.inclusionCheckboxLabel}
          </div>
        </label>

        {/* Submit / Continue Button */}
        <button
          type="submit"
          disabled={isLoading || !dateOfBirth || !inclusionConfirmed}
          id="inclusion-continue-btn"
          className={`w-full min-h-[48px] py-3.5 px-5 font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 ${
            isLoading || !dateOfBirth || !inclusionConfirmed
              ? "bg-slate-200 text-slate-400 cursor-not-allowed"
              : "bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white shadow-teal-700/20"
          }`}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <span>{t.continue}</span>
              <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            </>
          )}
        </button>
      </form>
    </div>
  );
};
