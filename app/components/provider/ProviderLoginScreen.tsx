"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { Stethoscope, Lock, Mail, ArrowRight, ArrowLeft, Loader2, KeyRound } from "lucide-react";
import { isFirebaseEnabled, isFirebaseConfigured, getFirebaseAuth, getAuthErrorMessage } from "../../lib/firebase";
import { getRoleFromEmail } from "../../lib/roles";
import { signInWithEmailAndPassword, signOut } from "firebase/auth";

export const ProviderLoginScreen = () => {
  const { setProviderScreen, setPortal, providerIdentifier, setProviderIdentifier, t, isUrdu } = useApp();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = identifier.trim();
    const cleanPass = password.trim();

    // 1. Strict Empty Field Validation across both modes
    if (!cleanId || !cleanPass) {
      setError(t.authEmptyFields);
      return;
    }

    // 2. Firebase Auth Mode
    if (isFirebaseEnabled()) {
      setIsLoading(true);
      setError("");

      if (!isFirebaseConfigured()) {
        setError(t.authConfigError);
        setIsLoading(false);
        return;
      }

      const auth = getFirebaseAuth();
      if (!auth) {
        setError(t.authInvalidApiKey);
        setIsLoading(false);
        return;
      }

      try {
        const userCredential = await signInWithEmailAndPassword(auth, cleanId, cleanPass);
        const email = userCredential.user.email || cleanId;
        const role = getRoleFromEmail(email);

        // Fail-closed role check: must explicitly be "provider"
        if (role !== "provider") {
          await signOut(auth);
          setError(t.authRoleMismatch);
          setIsLoading(false);
          return;
        }

        setProviderIdentifier(email);
        setProviderScreen("dashboard");
      } catch (err: any) {
        const errorCode = err?.code || "";
        setError(getAuthErrorMessage(errorCode, t));
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // 3. Mock / Offline Demo Mode (Strictly when AUTH_MODE is unset or mock)
    setError("");
    setProviderIdentifier(cleanId);
    setProviderScreen("dashboard");
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn">
      {/* Hero Header */}
      <div className="bg-navy-800 p-6 text-white text-center relative overflow-hidden">
        {/* Unobtrusive Mode Indicator Badge */}
        <div className="mb-2.5 flex justify-center">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-navy-900/80 border border-teal-400/30 text-[11px] font-medium text-teal-200 tracking-wide">
            <KeyRound className="w-3 h-3 text-teal-300" />
            <span>{isFirebaseEnabled() ? t.authModeFirebase : t.authModeMock}</span>
          </span>
        </div>

        <div className="w-12 h-12 rounded-xl bg-navy-700/80 border border-teal-500/30 flex items-center justify-center mx-auto mb-3 shadow-inner">
          <Stethoscope className="w-6 h-6 text-teal-400" />
        </div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-white mb-1.5">
          {t.providerLoginTitle}
        </h1>
        <p className="text-slate-300 text-xs leading-relaxed max-w-xs mx-auto">
          {t.providerLoginSubtitle}
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="p-6 space-y-4" dir={isUrdu ? "rtl" : "ltr"}>
        {error && (
          <div className="p-3 text-xs bg-amber-50 border border-amber-800/30 text-amber-800 rounded-lg">
            {error}
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-navy-800 mb-1.5" htmlFor="provider-identifier">
            {t.providerIdLabel}
          </label>
          <div className="relative">
            <div className={`absolute inset-y-0 ${isUrdu ? "right-0 pr-3" : "left-0 pl-3"} flex items-center pointer-events-none text-slate-400`}>
              <Mail className="w-4 h-4" />
            </div>
            <input
              id="provider-identifier"
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={process.env.NEXT_PUBLIC_DEMO_PROVIDER_EMAIL || "dr.sanamalik@citygeneral.org"}
              className={`w-full text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2.5 ${isUrdu ? "pr-9 pl-3" : "pl-9 pr-3"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-navy-800 transition-all`}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-navy-800 mb-1.5" htmlFor="provider-password">
            {t.passwordLabel}
          </label>
          <div className="relative">
            <div className={`absolute inset-y-0 ${isUrdu ? "right-0 pr-3" : "left-0 pl-3"} flex items-center pointer-events-none text-slate-400`}>
              <Lock className="w-4 h-4" />
            </div>
            <input
              id="provider-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t.passwordPlaceholder}
              className={`w-full text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2.5 ${isUrdu ? "pr-9 pl-3" : "pl-9 pr-3"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-navy-800 transition-all`}
            />
          </div>
        </div>

        <button
          type="submit"
          id="provider-login-btn"
          disabled={isLoading}
          className="w-full mt-2 py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] disabled:opacity-75 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{t.authSigningIn}</span>
            </>
          ) : (
            <>
              <span>{t.signInBtn}</span>
              <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            </>
          )}
        </button>

        <div className="text-center pt-2">
          <button
            type="button"
            onClick={() => setPortal("landing")}
            id="provider-back-to-landing-btn"
            className="text-xs text-slate-500 hover:text-navy-800 inline-flex items-center gap-1 transition-colors"
          >
            <ArrowLeft className={`w-3.5 h-3.5 ${isUrdu ? "rotate-180" : ""}`} />
            <span>{isUrdu ? "پورٹل منتخب کریں" : "Back to Portal Selection"}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
