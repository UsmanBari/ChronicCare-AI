"use client";

import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { Stethoscope, Lock, Mail, ArrowRight, ShieldCheck, ArrowLeft, Loader2 } from "lucide-react";
import { isFirebaseEnabled, getFirebaseAuth, getAuthErrorMessage } from "../../lib/firebase";
import { getRoleFromEmail } from "../../lib/roles";
import { signInWithEmailAndPassword, signOut } from "firebase/auth";

export const ProviderLoginScreen = () => {
  const { setProviderScreen, setPortal, providerIdentifier, setProviderIdentifier, t, isUrdu } = useApp();
  const [password, setPassword] = useState("••••••••");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = providerIdentifier.trim();
    const cleanPass = password.trim();

    if (!cleanId || !cleanPass) {
      setError(isUrdu ? "براہ کرم تمام خانے پُر کریں۔" : "Please enter your provider credentials.");
      return;
    }

    if (!isFirebaseEnabled()) {
      // Mock Demo Mode
      setError("");
      setProviderScreen("dashboard");
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
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn">
      {/* Hero Header */}
      <div className="bg-navy-800 p-6 text-white text-center relative overflow-hidden">
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
      <form onSubmit={handleSubmit} className="p-6 space-y-4">
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
              value={providerIdentifier}
              onChange={(e) => setProviderIdentifier(e.target.value)}
              placeholder={t.providerIdPlaceholder}
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
