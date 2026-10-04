"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { Lock, Mail, ArrowRight, Activity, ShieldCheck, ShieldAlert, Loader2, KeyRound, CheckCircle2 } from "lucide-react";
import { isFirebaseEnabled, isFirebaseConfigured, getFirebaseAuth, getAuthErrorMessage } from "../lib/firebase";
import { api, ApiError } from "../lib/api";
import { signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from "firebase/auth";

export const LoginScreen = () => {
  const { setScreen, setUserIdentifier, setUserRole, setLiveProfile, t, isUrdu } = useApp();
  const [isSignUp, setIsSignUp] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const validateEmail = (email: string) => {
    return /\S+@\S+\.\S+/.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = identifier.trim();
    const cleanPass = password.trim();
    const cleanConfirm = confirmPassword.trim();

    // 1. Strict Empty Field Validation
    if (!cleanId || !cleanPass || (isSignUp && !cleanConfirm)) {
      setError(t.authEmptyFields);
      return;
    }

    // 2. Client-side Validation for Sign-Up
    if (isSignUp) {
      if (!validateEmail(cleanId)) {
        setError(t.authInvalidEmail);
        return;
      }
      if (cleanPass.length < 8) {
        setError(t.authPasswordTooShort);
        return;
      }
      if (cleanPass !== cleanConfirm) {
        setError(t.authPasswordMismatch);
        return;
      }
    }

    // 3. Firebase Auth Mode
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
        let userCredential;
        if (isSignUp) {
          userCredential = await createUserWithEmailAndPassword(auth, cleanId, cleanPass);
        } else {
          userCredential = await signInWithEmailAndPassword(auth, cleanId, cleanPass);
        }

        const email = userCredential.user.email || cleanId;

        // In Live Mode: establish session with backend
        const session = await api.authSession();
        if (session.role !== "patient") {
          await signOut(auth);
          setError(t.authRoleMismatch);
          setIsLoading(false);
          return;
        }

        setUserIdentifier(email);
        setUserRole(session.role);

        // Check if patient has completed consent and onboarding
        try {
          const prof = await api.getProfile();
          setLiveProfile(prof);
          if (!prof.consent_granted_at) {
            setScreen("consent");
          } else {
            setScreen("connection");
          }
        } catch {
          setScreen("consent");
        }
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

    // 4. Mock / Offline Demo Mode (Strictly when AUTH_MODE is unset or mock)
    setError("");
    setUserIdentifier(cleanId);
    setScreen("connection");
  };

  return (
    <div className="w-full max-w-md mx-auto glass-raised rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn">
      {/* Soft Navy-to-Teal Gradient Hero Header */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-7 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />

        {/* Unobtrusive Mode Indicator Badge */}
        <div className="mb-3 flex justify-center">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-navy-900/60 border border-teal-400/30 text-[11px] font-medium text-teal-200 tracking-wide backdrop-blur-xs">
            <KeyRound className="w-3 h-3 text-teal-300" />
            <span>{isFirebaseEnabled() ? t.authModeFirebase : t.authModeMock}</span>
          </span>
        </div>

        <div className="w-14 h-14 rounded-2xl bg-navy-700/80 border border-teal-400/40 flex items-center justify-center mx-auto mb-3.5 shadow-inner text-teal-300">
          <Activity className="w-7 h-7" />
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold tracking-tight text-white mb-1.5">
          {isSignUp ? t.createAccountTitle : t.loginTitle}
        </h1>
        <p className="text-slate-200 text-sm leading-relaxed max-w-xs mx-auto">
          {isSignUp ? t.createAccountSubtitle : t.loginSubtitle}
        </p>
      </div>

      {/* Form Area */}
      <form onSubmit={handleSubmit} className="p-6 sm:p-7 space-y-4" dir={isUrdu ? "rtl" : "ltr"}>
        {error && (
          <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Email Input */}
        <div>
          <label className="block text-sm font-semibold text-navy-800 mb-1.5" htmlFor="login-identifier">
            {t.emailOrPhoneLabel}
          </label>
          <div className="relative">
            <div className={`absolute inset-y-0 ${isUrdu ? "right-0 pr-3.5" : "left-0 pl-3.5"} flex items-center pointer-events-none text-slate-400`}>
              <Mail className="w-5 h-5" />
            </div>
            <input
              id="login-identifier"
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={process.env.NEXT_PUBLIC_DEMO_PATIENT_EMAIL || "patient@example.com"}
              className={`w-full h-12 text-sm rounded-xl border border-slate-300 bg-white/90 ${isUrdu ? "pr-11 pl-4" : "pl-11 pr-4"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 focus:border-transparent transition-all shadow-xs`}
            />
          </div>
        </div>

        {/* Password Input */}
        <div>
          <label className="block text-sm font-semibold text-navy-800 mb-1.5" htmlFor="login-password">
            {t.passwordLabel}
          </label>
          <div className="relative">
            <div className={`absolute inset-y-0 ${isUrdu ? "right-0 pr-3.5" : "left-0 pl-3.5"} flex items-center pointer-events-none text-slate-400`}>
              <Lock className="w-5 h-5" />
            </div>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t.passwordPlaceholder}
              className={`w-full h-12 text-sm rounded-xl border border-slate-300 bg-white/90 ${isUrdu ? "pr-11 pl-4" : "pl-11 pr-4"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 focus:border-transparent transition-all shadow-xs`}
            />
          </div>
        </div>

        {/* Confirm Password (Only during Sign-Up) */}
        {isSignUp && (
          <div className="animate-fadeIn">
            <label className="block text-sm font-semibold text-navy-800 mb-1.5" htmlFor="login-confirm-password">
              {t.confirmPasswordLabel}
            </label>
            <div className="relative">
              <div className={`absolute inset-y-0 ${isUrdu ? "right-0 pr-3.5" : "left-0 pl-3.5"} flex items-center pointer-events-none text-slate-400`}>
                <Lock className="w-5 h-5" />
              </div>
              <input
                id="login-confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder={t.confirmPasswordPlaceholder}
                className={`w-full h-12 text-sm rounded-xl border border-slate-300 bg-white/90 ${isUrdu ? "pr-11 pl-4" : "pl-11 pr-4"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 focus:border-transparent transition-all shadow-xs`}
              />
            </div>
          </div>
        )}

        {/* Primary Action Button */}
        <button
          type="submit"
          id="login-submit-btn"
          disabled={isLoading}
          className="w-full h-12 mt-2 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] disabled:opacity-75 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{t.authSigningIn}</span>
            </>
          ) : (
            <>
              <span>{isSignUp ? t.signUpBtn : t.signInBtn}</span>
              <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            </>
          )}
        </button>

        {/* Toggle Sign-In / Sign-Up */}
        <div className="text-center pt-1">
          <button
            type="button"
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError("");
              setConfirmPassword("");
            }}
            id="toggle-auth-mode-btn"
            className="text-sm font-medium text-teal-700 hover:text-teal-800 underline underline-offset-4 transition-colors py-1"
          >
            {isSignUp ? t.toggleToSignIn : t.toggleToSignUp}
          </button>
        </div>

        {/* Trust Signal Badge */}
        <div className="p-3 rounded-xl bg-teal-50/70 border border-teal-200/70 flex items-center justify-center gap-2 text-xs font-medium text-teal-900">
          <ShieldCheck className="w-4 h-4 text-teal-700 shrink-0" />
          <span>Research Prototype • Role-Based Access & Audit Logging</span>
        </div>

        {/* Note */}
        <div className="pt-1 text-center text-xs text-slate-400">
          {t.loginHelpText}
        </div>
      </form>
    </div>
  );
};
