"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { api, ApiError } from "../lib/api";

export const ConsentScreen = () => {
  const { setScreen, setLiveProfile, signOutUser, isLiveMode, t, isUrdu } = useApp();
  const [dataConsent, setDataConsent] = useState(false);
  const [providerConsent, setProviderConsent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canContinue = dataConsent && providerConsent;

  const handleAccept = async () => {
    if (!canContinue) return;
    setIsLoading(true);
    setError(null);
    try {
      if (isLiveMode) {
        const updated = await api.setConsent(true, providerConsent);
        setLiveProfile(updated);
      }
      setScreen("inclusion");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.getFriendlyMessage(isUrdu));
      } else {
        setError(err?.message || "Failed to record consent");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDecline = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (isLiveMode) {
        await api.setConsent(false);
      }
      await signOutUser();
      setScreen("login");
    } catch {
      await signOutUser();
      setScreen("login");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Hero Header */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-7 text-white text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-teal-500/20 border border-teal-400/40 flex items-center justify-center mx-auto mb-3.5 shadow-inner text-teal-300">
          <ShieldCheck className="w-7 h-7" />
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold tracking-tight text-white mb-1.5">
          {t.consentTitle}
        </h1>
        <p className="text-slate-200 text-xs sm:text-sm leading-relaxed max-w-sm mx-auto">
          {t.consentSubtitle}
        </p>
      </div>

      {/* Content */}
      <div className="p-6 sm:p-7 space-y-6">
        {error && (
          <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Consent Details Card */}
        <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <div className="flex items-center gap-2 font-bold text-xs text-navy-800 uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4 text-teal-700" />
            <span>Clinical Monitoring & Data Privacy Notice</span>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed">
            {t.consentBody}
          </p>
        </div>

        {/* Privacy Bullet Points */}
        <div className="space-y-2.5 text-xs text-slate-600">
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span>{t.consentBulletRoleAccess}</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span>{t.consentBulletWithdrawConsent}</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span>{t.consentBulletNotForEmergencies}</span>
          </div>
        </div>

        {/* Two Required Consent Checkboxes */}
        <div className="p-4 rounded-2xl bg-teal-50/70 border-2 border-teal-200 space-y-3.5">
          <label className="flex items-start gap-3 cursor-pointer text-xs sm:text-sm font-semibold text-navy-900">
            <input
              type="checkbox"
              id="consent-data-processing-chk"
              checked={dataConsent}
              onChange={(e) => setDataConsent(e.target.checked)}
              className="w-4 h-4 text-teal-700 rounded border-slate-300 mt-0.5"
            />
            <span className="leading-snug">
              {isUrdu
                ? "میں اس بات سے اتفاق کرتا ہوں کہ ChronicCare AI میرے چیک ان کے جوابات اور ریکارڈ کا اندراج پراسیس اور محفوظ کر سکتا ہے۔"
                : "I agree that ChronicCare AI may process and store my check-in answers and record entries."}
            </span>
          </label>

          <label className="flex items-start gap-3 cursor-pointer text-xs sm:text-sm font-semibold text-navy-900 border-t border-teal-200/80 pt-3">
            <input
              type="checkbox"
              id="consent-provider-notification-chk"
              checked={providerConsent}
              onChange={(e) => setProviderConsent(e.target.checked)}
              className="w-4 h-4 text-teal-700 rounded border-slate-300 mt-0.5"
            />
            <span className="leading-snug">
              {isUrdu
                ? "میں اس بات سے اتفاق کرتا ہوں کہ جائزے کی ضرورت والے چیک ان اس پروٹوٹائپ کے معالجین کے کھاتوں کو دکھائے جا سکتے ہیں۔"
                : "I agree that check-ins needing review may be shown to clinician accounts of this prototype."}
            </span>
          </label>

          {!canContinue && (
            <p className="text-[11px] font-bold text-teal-900 pt-1">
              {isUrdu
                ? "اس پروٹوٹائپ میں چیک ان استعمال کرنے کے لیے دونوں ضروری ہیں۔"
                : "Both are needed to use check-ins in this prototype."}
            </p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="space-y-3 pt-2">
          <button
            type="button"
            onClick={handleAccept}
            disabled={isLoading || !canContinue}
            id="consent-accept-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 shadow-teal-700/20"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{t.saving}</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                <span>{t.continue || "Continue"}</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleDecline}
            disabled={isLoading}
            id="consent-decline-btn"
            className="w-full min-h-[44px] py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-2"
          >
            <XCircle className="w-4 h-4 text-slate-500" />
            <span>{t.consentDeclineBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
