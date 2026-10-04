"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { api, ApiError } from "../lib/api";

export const ConsentScreen = () => {
  const { setScreen, setLiveProfile, signOutUser, isLiveMode, t, isUrdu } = useApp();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAccept = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (isLiveMode) {
        const updated = await api.setConsent(true);
        setLiveProfile(updated);
      }
      setScreen("profile");
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
            <span>Encrypted transmission & secure patient identity verification.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span>Zero PHI exposed in technical logging or analytics layers.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
            <span>Full patient control to revoke consent or disconnect EHR at any time.</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-3 pt-2">
          <button
            type="button"
            onClick={handleAccept}
            disabled={isLoading}
            id="consent-accept-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] disabled:opacity-75 text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 shadow-teal-700/20"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{t.saving}</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                <span>{t.consentAcceptBtn}</span>
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
