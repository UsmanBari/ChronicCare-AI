import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { Settings, Globe, ShieldCheck, Database, X, Activity, User, Hospital, ShieldAlert, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { titleCaseName } from "../lib/presentation";

export const UnifiedSettingsModal = () => {
  const {
    showSettings,
    setShowSettings,
    language,
    setLanguage,
    connectionMode,
    liveProfile,
    setLiveProfile,
    isLiveMode,
    profile,
    portal,
    t,
    isUrdu,
    userRole,
    userIdentifier,
    setScreen,
  } = useApp();

  const [confirmRevokeType, setConfirmRevokeType] = useState<"data" | "provider" | null>(null);
  const [isUpdatingConsent, setIsUpdatingConsent] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);

  if (!showSettings) return null;

  const hasDataConsent = Boolean(
    liveProfile?.consent_granted_at && !liveProfile.consent_revoked_at
  );
  const hasProviderConsent = Boolean(
    liveProfile?.provider_notification_consent_at && !liveProfile.provider_notification_revoked_at
  );

  const handleToggleDataConsent = async () => {
    if (hasDataConsent) {
      setConfirmRevokeType("data");
      return;
    }
    // Turning ON
    setIsUpdatingConsent(true);
    setConsentError(null);
    try {
      const updated = await api.setConsent(true);
      setLiveProfile(updated);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setConsentError(err.getFriendlyMessage(isUrdu));
      } else {
        setConsentError(err?.message || "Failed to update consent");
      }
    } finally {
      setIsUpdatingConsent(false);
    }
  };

  const handleToggleProviderConsent = async () => {
    if (hasProviderConsent) {
      setConfirmRevokeType("provider");
      return;
    }
    // Turning ON
    setIsUpdatingConsent(true);
    setConsentError(null);
    try {
      const updated = await api.setProviderNotificationConsent(true);
      setLiveProfile(updated);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setConsentError(err.getFriendlyMessage(isUrdu));
      } else {
        setConsentError(err?.message || "Failed to update consent");
      }
    } finally {
      setIsUpdatingConsent(false);
    }
  };

  const hasVoiceEnabled = Boolean(liveProfile?.voice_enabled);

  const handleToggleVoice = async () => {
    setIsUpdatingConsent(true);
    setConsentError(null);
    try {
      const updated = await api.updateProfile({ voice_enabled: !hasVoiceEnabled });
      setLiveProfile(updated);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setConsentError(err.getFriendlyMessage(isUrdu));
      } else {
        setConsentError(err?.message || "Failed to update voice setting");
      }
    } finally {
      setIsUpdatingConsent(false);
    }
  };

  const handleConfirmRevoke = async () => {
    if (!confirmRevokeType) return;
    setIsUpdatingConsent(true);
    setConsentError(null);
    try {
      if (confirmRevokeType === "data") {
        const updated = await api.setConsent(false);
        setLiveProfile(updated);
      } else if (confirmRevokeType === "provider") {
        const updated = await api.setProviderNotificationConsent(false);
        setLiveProfile(updated);
      }
      setConfirmRevokeType(null);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setConsentError(err.getFriendlyMessage(isUrdu));
      } else {
        setConsentError(err?.message || "Failed to update consent");
      }
    } finally {
      setIsUpdatingConsent(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-lg bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden animate-slideUp max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-navy-800 p-5 text-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-navy-700 flex items-center justify-center text-teal-400">
              <Settings className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-heading text-lg font-bold text-white leading-tight">
                {t.unifiedSettingsTitle}
              </h2>
              <span className="text-[10px] text-slate-300">
                {t.unifiedSettingsSubtitle}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowSettings(false)}
            id="close-settings-btn"
            className="w-8 h-8 rounded-full bg-navy-700 hover:bg-navy-600 text-slate-300 hover:text-white flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {consentError && (
            <div className="p-3 text-xs bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
              <span>{consentError}</span>
            </div>
          )}

          {/* Setting 1: Language Toggle */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <Globe className="w-4 h-4 text-teal-700" />
              <span>{t.languageSettingLabel}</span>
            </label>
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                type="button"
                onClick={() => setLanguage("en")}
                id="settings-lang-en-btn"
                className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                  language === "en"
                    ? "bg-teal-700 text-white border-teal-700 shadow-sm"
                    : "bg-white text-navy-800 border-slate-300 hover:bg-slate-100"
                }`}
              >
                English (Default)
              </button>
              <button
                type="button"
                onClick={() => setLanguage("ur")}
                id="settings-lang-ur-btn"
                className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                  language === "ur"
                    ? "bg-teal-700 text-white border-teal-700 shadow-sm font-urdu"
                    : "bg-white text-navy-800 border-slate-300 hover:bg-slate-100 font-urdu"
                }`}
              >
                اردو (Urdu)
              </button>
            </div>
          </div>

          {/* Setting 2: Privacy & Consent Management (Patient Portal / Live Mode) */}
          {isLiveMode && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
              <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-teal-700" />
                <span>{isUrdu ? "رازداری و اجازت نامہ" : "Privacy & Consent Settings"}</span>
              </span>

              <div className="space-y-2.5 pt-1">
                {/* Consent Toggle 1: Data Processing & Storage */}
                <div className="p-3 rounded-xl bg-white border border-slate-200 flex items-center justify-between gap-3">
                  <div className="space-y-0.5 min-w-0 flex-1">
                    <span className="text-xs font-bold text-navy-900 block truncate">
                      {isUrdu ? "ڈیٹا پروسیسنگ اور اسٹوریج" : "Data Processing & Storage"}
                    </span>
                    <p className="text-[11px] text-slate-500 leading-snug">
                      {isUrdu
                        ? "چیک ان کے جوابات اور ریکارڈ کا اندراج پراسیس اور محفوظ کرنے کی اجازت۔"
                        : "Process and store check-in answers and record entries."}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleToggleDataConsent}
                    disabled={isUpdatingConsent}
                    id="toggle-data-consent-btn"
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                      hasDataConsent
                        ? "bg-teal-100 text-teal-900 hover:bg-teal-200"
                        : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                    }`}
                  >
                    {hasDataConsent ? (isUrdu ? "فعال ✓" : "Active ✓") : (isUrdu ? "اجازت نہیں دی گئی" : "Not given")}
                  </button>
                </div>

                {/* Consent Toggle 2: Provider Notification */}
                <div className="p-3 rounded-xl bg-white border border-slate-200 flex items-center justify-between gap-3">
                  <div className="space-y-0.5 min-w-0 flex-1">
                    <span className="text-xs font-bold text-navy-900 block truncate">
                      {isUrdu ? "معالج کی اطلاع اور جائزہ" : "Clinician Review & Notification"}
                    </span>
                    <p className="text-[11px] text-slate-500 leading-snug">
                      {isUrdu
                        ? "جائزے کی ضرورت والے چیک ان معالجین کو دکھانے کی اجازت۔"
                        : "Allow check-ins needing review to be shown to clinicians."}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleToggleProviderConsent}
                    disabled={isUpdatingConsent}
                    id="toggle-provider-consent-btn"
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                      hasProviderConsent
                        ? "bg-teal-100 text-teal-900 hover:bg-teal-200"
                        : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                    }`}
                  >
                    {hasProviderConsent ? (isUrdu ? "فعال ✓" : "Active ✓") : (isUrdu ? "اجازت نہیں دی گئی" : "Not given")}
                  </button>
                </div>

                {/* Consent Toggle 3: Voice Input */}
                <div className="p-3 rounded-xl bg-white border border-slate-200 flex items-center justify-between gap-3">
                  <div className="space-y-0.5 min-w-0 flex-1">
                    <span className="text-xs font-bold text-navy-900 block truncate">
                      {isUrdu ? "آواز سے جواب (اسپیچ ٹو ٹیکسٹ)" : "Voice Input (Speech-to-Text)"}
                    </span>
                    <p className="text-[11px] text-slate-500 leading-snug">
                      {isUrdu
                        ? "آواز صرف عارضی طور پر ٹیکسٹ بنانے کے لیے میموری میں استعمال ہوتی ہے اور کبھی ڈسک یا ڈیٹا بیس پر محفوظ نہیں کی جاتی۔"
                        : "Audio is transcribed in-memory only and is never stored on disk or server databases."}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleToggleVoice}
                    disabled={isUpdatingConsent}
                    id="toggle-voice-enabled-btn"
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all shrink-0 ${
                      hasVoiceEnabled
                        ? "bg-teal-100 text-teal-900 hover:bg-teal-200"
                        : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                    }`}
                  >
                    {hasVoiceEnabled ? (isUrdu ? "فعال ✓" : "Enabled ✓") : (isUrdu ? "بند ہے" : "Disabled")}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Setting 3: Connection Mode Indicator */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <Hospital className="w-4 h-4 text-teal-700" />
              <span>{t.connectionModeSettingLabel}</span>
            </span>
            <div className="p-3 rounded-lg bg-white border border-slate-200 text-xs">
              {connectionMode === "fhir" ? (
                <div className="flex items-center gap-2 text-mutedGreen-800 font-semibold">
                  <ShieldCheck className="w-4 h-4 text-mutedGreen-800 shrink-0" />
                  <span>{t.connectedHospital}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-amber-800 font-semibold">
                  <Database className="w-4 h-4 text-amber-800 shrink-0" />
                  <span>{t.offlineMode}</span>
                </div>
              )}
              <p className="text-[11px] text-slate-500 mt-1">
                {connectionMode === "fhir"
                  ? "Live HL7® FHIR® bridge active with configured EHR system."
                  : "Isolated device storage mode using the local store."}
              </p>
            </div>
          </div>

          {/* Setting 4: Active Profile Parameters */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <User className="w-4 h-4 text-teal-700" />
              <span>{t.activeProfileLabel}</span>
            </span>
            <div className="p-3 rounded-xl bg-white border border-slate-200 space-y-2 text-slate-600">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-slate-400 block uppercase font-bold">
                    {userRole ? userRole.charAt(0).toUpperCase() + userRole.slice(1) : (portal === "patient" ? "Patient" : portal === "provider" ? "Provider" : "Admin")}
                  </span>
                  <span className="font-semibold text-navy-800">
                    {titleCaseName(userIdentifier) || userIdentifier}
                  </span>
                </div>
                {portal === "patient" && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowSettings(false);
                      setScreen("inclusion");
                    }}
                    id="settings-my-details-btn"
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-teal-50 hover:bg-teal-100 text-teal-900 border border-teal-200 transition-colors"
                  >
                    {isUrdu ? "میری تفصیلات" : "My details"}
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Close button */}
          <button
            type="button"
            onClick={() => setShowSettings(false)}
            id="dismiss-settings-btn"
            className="w-full py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all"
          >
            {t.close}
          </button>
        </div>
      </div>

      {/* Confirmation Dialog for Revoking Consent */}
      {confirmRevokeType && (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fadeIn">
          <div className="w-full max-w-md bg-white rounded-2xl border-2 border-amber-600 p-6 shadow-2xl space-y-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-heading text-base font-bold text-navy-900">
                  {isUrdu ? "کیا آپ اجازت واپس لینا چاہتے ہیں؟" : "Revoke Consent Confirmation"}
                </h3>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  {isUrdu
                    ? "اسے بند کرنے سے نئے چیک ان رک جائیں گے۔ جو جائزے آپ کے معالج کو پہلے ہی بھیجے جا چکے ہیں وہ ان کے پاس رہیں گے۔"
                    : "Turning this off stops new check-ins. Reviews that were already sent stay with your clinician."}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setConfirmRevokeType(null)}
                disabled={isUpdatingConsent}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold border border-slate-300 hover:bg-slate-100 text-slate-700 transition-colors"
              >
                {isUrdu ? "منسوخ کریں" : "Cancel"}
              </button>
              <button
                type="button"
                onClick={handleConfirmRevoke}
                disabled={isUpdatingConsent}
                id="confirm-revoke-consent-btn"
                className="px-4 py-2 rounded-xl text-xs font-bold bg-amber-800 hover:bg-amber-900 text-white transition-colors shadow-xs"
              >
                {isUpdatingConsent ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : (isUrdu ? "بند کرنے کی تصدیق کریں" : "Confirm Turn Off")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
