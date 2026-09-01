"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { Lock, Mail, UserCheck, ArrowRight, Activity, Shield } from "lucide-react";

export const LoginScreen = () => {
  const { setScreen, setUserIdentifier, t, isUrdu } = useApp();
  const [isSignUp, setIsSignUp] = useState(false);
  const [identifier, setIdentifier] = useState("patient@demo.care");
  const [password, setPassword] = useState("••••••••");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password.trim()) {
      setError(isUrdu ? "براہ کرم تمام خانے پُر کریں۔" : "Please enter both fields to proceed.");
      return;
    }
    setError("");
    setUserIdentifier(identifier.trim());
    setScreen("connection");
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn">
      {/* Hero Header */}
      <div className="bg-navy-800 p-6 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-teal-700/20 rounded-full blur-2xl pointer-events-none" />
        <div className="w-12 h-12 rounded-xl bg-navy-700/80 border border-teal-500/30 flex items-center justify-center mx-auto mb-3 shadow-inner">
          <Activity className="w-6 h-6 text-teal-400" />
        </div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-white mb-1.5">
          {isSignUp ? t.createAccountTitle : t.loginTitle}
        </h1>
        <p className="text-slate-300 text-xs leading-relaxed max-w-xs mx-auto">
          {isSignUp ? t.createAccountSubtitle : t.loginSubtitle}
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="p-6 space-y-4">
        {error && (
          <div className="p-3 text-xs bg-amber-50 border border-amber-800/30 text-amber-800 rounded-lg">
            {error}
          </div>
        )}

        {/* Email or Phone */}
        <div>
          <label className="block text-xs font-semibold text-navy-800 mb-1.5" htmlFor="login-identifier">
            {t.emailOrPhoneLabel}
          </label>
          <div className="relative">
            <div className={`absolute inset-y-0 ${isUrdu ? "right-0 pr-3" : "left-0 pl-3"} flex items-center pointer-events-none text-slate-400`}>
              <Mail className="w-4 h-4" />
            </div>
            <input
              id="login-identifier"
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={t.emailOrPhonePlaceholder}
              className={`w-full text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2.5 ${isUrdu ? "pr-9 pl-3" : "pl-9 pr-3"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 focus:border-transparent transition-all`}
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label className="block text-xs font-semibold text-navy-800 mb-1.5" htmlFor="login-password">
            {t.passwordLabel}
          </label>
          <div className="relative">
            <div className={`absolute inset-y-0 ${isUrdu ? "right-0 pr-3" : "left-0 pl-3"} flex items-center pointer-events-none text-slate-400`}>
              <Lock className="w-4 h-4" />
            </div>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t.passwordPlaceholder}
              className={`w-full text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2.5 ${isUrdu ? "pr-9 pl-3" : "pl-9 pr-3"} text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 focus:border-transparent transition-all`}
            />
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          id="login-submit-btn"
          className="w-full mt-2 py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <span>{isSignUp ? t.signUpBtn : t.signInBtn}</span>
          <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>

        {/* Toggle Sign Up / Sign In */}
        <div className="text-center pt-2">
          <button
            type="button"
            onClick={() => {
              setIsSignUp(!isSignUp);
              setError("");
            }}
            id="toggle-auth-mode-btn"
            className="text-xs font-medium text-teal-700 hover:text-teal-800 underline underline-offset-4 transition-colors"
          >
            {isSignUp ? t.toggleToSignIn : t.toggleToSignUp}
          </button>
        </div>

        {/* Non-functional Auth Note */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-center gap-1 text-[11px] text-slate-400">
          <Shield className="w-3.5 h-3.5 text-slate-400" />
          <span>{t.loginHelpText}</span>
        </div>
      </form>
    </div>
  );
};
