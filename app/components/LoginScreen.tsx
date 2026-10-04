"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { Lock, Mail, UserCheck, ArrowRight, Activity, ShieldCheck, ShieldAlert, Loader2 } from "lucide-react";
import { isFirebaseEnabled, getFirebaseAuth, getAuthErrorMessage } from "../lib/firebase";
import { getRoleFromEmail } from "../lib/roles";
import { signInWithEmailAndPassword, signOut } from "firebase/auth";

export const LoginScreen = () => {
  const { setScreen, setUserIdentifier, t, isUrdu } = useApp();
  const [isSignUp, setIsSignUp] = useState(false);
  const [identifier, setIdentifier] = useState(
    process.env.NEXT_PUBLIC_DEMO_PATIENT_EMAIL || "patient@demo.care"
  );
  const [password, setPassword] = useState("••••••••");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = identifier.trim();
    const cleanPass = password.trim();

    if (!cleanId || !cleanPass) {
      setError(isUrdu ? "براہ کرم تمام خانے پُر کریں۔" : "Please enter both fields to proceed.");
      return;
    }

    if (!isFirebaseEnabled()) {
      // Mock / Offline Demo Mode (Exact current behavior)
      setError("");
      setUserIdentifier(cleanId);
      setScreen("connection");
      return;
    }

    // Firebase Auth Mode
    setIsLoading(true);
    setError("");

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

      if (role !== "patient") {
        await signOut(auth);
        setError(t.authRoleMismatch);
        setIsLoading(false);
        return;
      }

      setUserIdentifier(email);
      setScreen("connection");
    } catch (err: any) {
      const errorCode = err?.code || "";
      setError(getAuthErrorMessage(errorCode, t));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto glass-raised rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn">
      {/* Soft Navy-to-Teal Gradient Hero Header */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-7 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />
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
      <form onSubmit={handleSubmit} className="p-6 sm:p-7 space-y-5" dir={isUrdu ? "rtl" : "ltr"}>
        {error && (
          <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Email or Phone Input (48px Touch Target) */}
        <div>
          <label className="block text-sm font-semibold text-navy-800 mb-2" htmlFor="login-identifier">
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
              placeholder={t.emailOrPhonePlaceholder}
              className={`w-full h-12 text-sm rounded-xl border border-slate-300 bg-white/90 ${isUrdu ? "pr-11 pl-4" : "pl-11 pr-4"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 focus:border-transparent transition-all shadow-xs`}
            />
          </div>
        </div>

        {/* Password Input (48px Touch Target) */}
        <div>
          <label className="block text-sm font-semibold text-navy-800 mb-2" htmlFor="login-password">
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

        {/* Primary Action Button (48px Touch Target) */}
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

        {/* Toggle Mode Button */}
        <div className="text-center pt-1">
          <button
            type="button"
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError("");
            }}
            id="toggle-auth-mode-btn"
            className="text-sm font-medium text-teal-700 hover:text-teal-800 underline underline-offset-4 transition-colors py-1"
          >
            {isSignUp ? t.toggleToSignIn : t.toggleToSignUp}
          </button>
        </div>

        {/* Visible Trust Signal Badge */}
        <div className="p-3 rounded-xl bg-teal-50/70 border border-teal-200/70 flex items-center justify-center gap-2 text-xs font-medium text-teal-900">
          <ShieldCheck className="w-4 h-4 text-teal-700 shrink-0" />
          <span>Your health data is kept private • HIPAA Compliant</span>
        </div>

        {/* Non-functional Auth Note */}
        <div className="pt-2 text-center text-xs text-slate-400">
          {t.loginHelpText}
        </div>
      </form>
    </div>
  );
};
