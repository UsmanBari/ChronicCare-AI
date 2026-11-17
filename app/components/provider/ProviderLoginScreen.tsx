"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { Stethoscope, Lock, Mail, ArrowRight, ArrowLeft, Loader2, KeyRound, Eye, EyeOff } from "lucide-react";
import { isFirebaseEnabled, isFirebaseConfigured, getFirebaseAuth, getAuthErrorMessage, signInWithGoogle } from "../../lib/firebase";
import { getRoleFromEmail } from "../../lib/roles";
import { api, ApiError } from "../../lib/api";
import { signInWithEmailAndPassword, signOut } from "firebase/auth";

export const ProviderLoginScreen = () => {
  const {
    setProviderScreen,
    setPortal,
    setProviderIdentifier,
    setProviderDisplayName,
    setUserRole,
    sessionNotice,
    setSessionNotice,
    isLiveMode,
    t,
    isUrdu,
  } = useApp();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (sessionNotice && setSessionNotice) setSessionNotice(null);
    const cleanId = identifier.trim().toLowerCase();
    const cleanPass = password.trim();

    // 1. Strict Empty Field Validation
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

        // In Live Mode: Role is strictly validated against backend session
        const session = await api.authSession();
        if (session.role !== "provider" && session.role !== "admin") {
          await signOut(auth);
          setError(t.authRoleMismatch);
          setIsLoading(false);
          return;
        }

        setProviderIdentifier(email);
        setProviderDisplayName(session.display_name || userCredential.user.displayName || null);
        setUserRole(session.role);
        setProviderScreen("dashboard");
      } catch (err: any) {
        if (err instanceof ApiError) {
          setError(err.getFriendlyMessage(isUrdu));
        } else {
          const errorCode = err?.code || "";
          setError(getAuthErrorMessage(errorCode, t));
        }
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // 3. Mock / Offline Demo Mode (Strictly when AUTH_MODE is unset or mock)
    const mockRole = getRoleFromEmail(cleanId);
    if (mockRole && mockRole !== "provider" && mockRole !== "admin") {
      setError(t.authRoleMismatch);
      return;
    }
    setError("");
    setProviderIdentifier(cleanId);
    setProviderDisplayName(null);
    setProviderScreen("dashboard");
  };

  const handleGoogleSignIn = async () => {
    setError("");
    if (sessionNotice && setSessionNotice) setSessionNotice(null);
    setIsLoading(true);
    try {
      const res = await signInWithGoogle();
      if (res.cancelled) {
        setIsLoading(false);
        return;
      }
      if (res.error) {
        setError(res.error);
        setIsLoading(false);
        return;
      }
      const cred = res.userCredential!;
      const email = cred.user.email || "";

      const session = await api.authSession();
      if (session.role !== "provider" && session.role !== "admin") {
        try {
          await api.reportAccessDenied("provider");
        } catch {}
        const auth = getFirebaseAuth();
        if (auth) await signOut(auth);
        setError("This Google account is registered as a patient, not a provider");
        setIsLoading(false);
        return;
      }

      setProviderIdentifier(email);
      setProviderDisplayName(session.display_name || cred.user.displayName || null);
      setUserRole(session.role);
      setProviderScreen("dashboard");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.getFriendlyMessage(isUrdu));
      } else {
        setError(err?.message || t.authGeneralError);
      }
    } finally {
      setIsLoading(false);
    }
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
        {sessionNotice && (
          <div id="provider-session-notice-banner" className="p-3 text-xs bg-amber-50 border border-amber-800/30 text-amber-800 rounded-lg">
            {sessionNotice}
          </div>
        )}

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
              onChange={(e) => {
                setIdentifier(e.target.value);
                if (sessionNotice && setSessionNotice) setSessionNotice(null);
              }}
              placeholder={
                process.env.NEXT_PUBLIC_DEMO_PROVIDER_EMAIL ||
                (isLiveMode ? "provider@example.com" : "dr.sanamalik@citygeneral.org")
              }
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              inputMode="email"
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
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t.passwordPlaceholder}
              autoComplete="current-password"
              className={`w-full text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2.5 ${isUrdu ? "pr-9 pl-9" : "pl-9 pr-9"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-navy-800 transition-all`}
            />
            <button
              type="button"
              id="toggle-provider-password-visibility-btn"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-controls="provider-password"
              aria-label={showPassword ? t.hidePassword : t.showPassword}
              title={showPassword ? t.hidePassword : t.showPassword}
              className={`absolute inset-y-0 ${isUrdu ? "left-0 pl-2.5" : "right-0 pr-2.5"} flex items-center text-slate-400 hover:text-navy-800 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-navy-800 rounded-lg`}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
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

        {/* Continue with Google (Firebase Auth Mode Only) */}
        {isFirebaseEnabled() && (
          <div className="space-y-3 pt-1">
            <div className="relative flex items-center justify-center">
              <div className="border-t border-slate-200 w-full" />
              <span className="bg-white px-3 text-xs text-slate-500 font-medium uppercase tracking-wider">
                {isUrdu ? "یا" : "or"}
              </span>
            </div>
            <button
              type="button"
              id="google-signin-btn"
              data-testid="google-signin-btn"
              onClick={handleGoogleSignIn}
              disabled={isLoading}
              className="w-full min-h-[44px] py-2.5 px-4 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-semibold text-sm rounded-xl shadow-2xs transition-all flex items-center justify-center gap-3 disabled:opacity-50"
            >
              <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>{isUrdu ? "گوگل کے ساتھ جاری رکھیں" : "Continue with Google"}</span>
            </button>
          </div>
        )}

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
