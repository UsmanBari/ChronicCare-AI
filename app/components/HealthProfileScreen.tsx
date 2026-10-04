"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { Plus, Trash2, ArrowRight, Activity, Pill, User, ShieldCheck, ShieldAlert, Loader2, Globe } from "lucide-react";
import { api, ApiError, ProfileUpdateRequest } from "../lib/api";
import { Language } from "../translations";

export const HealthProfileScreen = () => {
  const {
    setScreen,
    profile,
    setProfile,
    liveProfile,
    setLiveProfile,
    isLiveMode,
    language,
    setLanguage,
    t,
    isUrdu,
  } = useApp();

  const [conditions, setConditions] = useState<string[]>(
    liveProfile?.conditions && liveProfile.conditions.length > 0
      ? liveProfile.conditions
      : profile.conditions || ["Type 2 Diabetes"]
  );

  const [onInsulin, setOnInsulin] = useState<boolean>(
    liveProfile?.on_insulin_or_sulfonylurea !== undefined
      ? liveProfile.on_insulin_or_sulfonylurea
      : false
  );

  const [selectedLang, setSelectedLang] = useState<string>(
    liveProfile?.language || language || "en"
  );

  const [medications, setMedications] = useState<string[]>(
    profile.medications.length > 0 ? profile.medications : ["Metformin 500mg (1+1)"]
  );
  const [age, setAge] = useState<string>(profile.age || "58");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isLiveMode && liveProfile) {
      if (liveProfile.conditions && liveProfile.conditions.length > 0) {
        setConditions(liveProfile.conditions);
      }
      setOnInsulin(Boolean(liveProfile.on_insulin_or_sulfonylurea));
      if (liveProfile.language) {
        setSelectedLang(liveProfile.language);
      }
    }
  }, [isLiveMode, liveProfile]);

  const handleConditionToggle = (conditionValue: "t2d" | "htn" | "both") => {
    if (conditionValue === "both") {
      setConditions(["Type 2 Diabetes", "Hypertension"]);
    } else if (conditionValue === "t2d") {
      if (conditions.includes("Type 2 Diabetes") && conditions.length > 1) {
        setConditions(conditions.filter((c) => c !== "Type 2 Diabetes"));
      } else {
        setConditions([...conditions.filter((c) => c !== "Type 2 Diabetes"), "Type 2 Diabetes"]);
      }
    } else if (conditionValue === "htn") {
      if (conditions.includes("Hypertension") && conditions.length > 1) {
        setConditions(conditions.filter((c) => c !== "Hypertension"));
      } else {
        setConditions([...conditions.filter((c) => c !== "Hypertension"), "Hypertension"]);
      }
    }
  };

  const handleAddMedication = () => {
    setMedications([...medications, ""]);
  };

  const handleMedChange = (index: number, value: string) => {
    const updated = [...medications];
    updated[index] = value;
    setMedications(updated);
  };

  const handleRemoveMedication = (index: number) => {
    if (medications.length <= 1) {
      setMedications([""]);
      return;
    }
    setMedications(medications.filter((_, i) => i !== index));
  };

  const handleContinue = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    const cleanConditions = conditions.length > 0 ? conditions : ["Type 2 Diabetes"];
    const cleanMeds = medications.filter((m) => m.trim().length > 0);

    // Save mock state representation
    setProfile({
      conditions: cleanConditions,
      medications: cleanMeds.length > 0 ? cleanMeds : ["Metformin 500mg (1+1)"],
      age: age || "58",
    });

    if (isLiveMode) {
      try {
        const payload: ProfileUpdateRequest = {
          conditions: cleanConditions.map((c) =>
            c.toLowerCase().includes("diabet") ? "diabetes" : "hypertension"
          ),
          on_insulin_or_sulfonylurea: onInsulin,
          language: selectedLang,
        };

        const updated = await api.updateProfile(payload);
        setLiveProfile(updated);
        if (selectedLang === "en" || selectedLang === "ur") {
          setLanguage(selectedLang as Language);
        }
        setScreen("connection");
      } catch (err: any) {
        if (err instanceof ApiError) {
          setError(err.getFriendlyMessage(isUrdu));
        } else {
          setError(err?.message || "Failed to update profile");
        }
      } finally {
        setIsLoading(false);
      }
      return;
    }

    setIsLoading(false);
    setScreen("home");
  };

  const hasT2D = conditions.some((c) => c.toLowerCase().includes("diabet"));
  const hasHTN = conditions.some((c) => c.toLowerCase().includes("hyper"));
  const hasBoth = hasT2D && hasHTN;

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="bg-navy-800 p-6 sm:p-7 text-white text-center">
        <h1 className="font-heading text-2xl font-bold mb-1">{t.profileTitle}</h1>
        <p className="text-xs sm:text-sm text-slate-300 max-w-md mx-auto">{t.profileSubtitle}</p>
      </div>

      <form onSubmit={handleContinue} className="p-6 sm:p-7 space-y-6">
        {error && (
          <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Conditions selection */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-navy-800 mb-3 flex items-center gap-1.5">
            <Activity className="w-4 h-4 text-teal-700" />
            <span>{t.conditionsLabel}</span>
          </label>
          <div className="space-y-2.5">
            {/* Type 2 Diabetes */}
            <label className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer transition-colors">
              <input
                type="checkbox"
                id="condition-t2d"
                checked={hasT2D}
                onChange={() => handleConditionToggle("t2d")}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span className="text-sm font-medium text-navy-800">{t.type2Diabetes}</span>
            </label>

            {/* Hypertension */}
            <label className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer transition-colors">
              <input
                type="checkbox"
                id="condition-htn"
                checked={hasHTN}
                onChange={() => handleConditionToggle("htn")}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span className="text-sm font-medium text-navy-800">{t.hypertension}</span>
            </label>

            {/* Both shortcut */}
            <label className="flex items-center gap-3 p-3.5 rounded-xl border border-teal-200 bg-teal-50/50 hover:bg-teal-50 cursor-pointer transition-colors">
              <input
                type="checkbox"
                id="condition-both"
                checked={hasBoth}
                onChange={() => handleConditionToggle("both")}
                className="w-4 h-4 text-teal-700 rounded border-teal-300 focus:ring-teal-700"
              />
              <span className="text-sm font-semibold text-teal-900">{t.bothConditions}</span>
            </label>
          </div>
        </div>

        {/* Insulin / Sulfonylurea Question (Stage 2B requirement) */}
        <div className="p-4 rounded-2xl bg-teal-50/60 border border-teal-200 space-y-2.5">
          <label className="block text-xs font-bold text-navy-800 leading-snug">
            {t.insulinOrSulfonylureaLabel}
          </label>
          <p className="text-[11px] text-slate-500">{t.insulinOrSulfonylureaHint}</p>
          <div className="grid grid-cols-2 gap-2.5 pt-1">
            <button
              type="button"
              onClick={() => setOnInsulin(true)}
              id="insulin-yes-btn"
              className={`min-h-[40px] px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                onInsulin
                  ? "bg-teal-700 text-white border-teal-700 shadow-xs"
                  : "bg-white text-navy-800 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {t.insulinYes}
            </button>
            <button
              type="button"
              onClick={() => setOnInsulin(false)}
              id="insulin-no-btn"
              className={`min-h-[40px] px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                !onInsulin
                  ? "bg-navy-800 text-white border-navy-800 shadow-xs"
                  : "bg-white text-navy-800 border-slate-200 hover:bg-slate-50"
              }`}
            >
              {t.insulinNo}
            </button>
          </div>
        </div>

        {/* Language Selection */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-navy-800 mb-2 flex items-center gap-1.5">
            <Globe className="w-4 h-4 text-teal-700" />
            <span>{t.languageSettingLabel}</span>
          </label>
          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => setSelectedLang("en")}
              id="lang-en-btn"
              className={`min-h-[40px] px-3 py-2 rounded-xl text-xs font-semibold border transition-all ${
                selectedLang === "en"
                  ? "bg-navy-800 text-white border-navy-800 shadow-xs"
                  : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
              }`}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => setSelectedLang("ur")}
              id="lang-ur-btn"
              className={`min-h-[40px] px-3 py-2 rounded-xl text-xs font-semibold border transition-all font-urdu ${
                selectedLang === "ur"
                  ? "bg-navy-800 text-white border-navy-800 shadow-xs"
                  : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
              }`}
            >
              اردو (Urdu)
            </button>
          </div>
        </div>

        {/* Current Medications */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <Pill className="w-4 h-4 text-teal-700" />
              <span>{t.medicationsLabel}</span>
            </label>
            <button
              type="button"
              onClick={handleAddMedication}
              id="add-med-btn"
              className="text-xs font-semibold text-teal-700 hover:text-teal-800 transition-colors"
            >
              {t.addMedication}
            </button>
          </div>
          <p className="text-[11px] text-slate-500 mb-2.5">{t.medicationsHint}</p>

          <div className="space-y-2">
            {medications.map((med, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <input
                  type="text"
                  value={med}
                  id={`medication-input-${idx}`}
                  onChange={(e) => handleMedChange(idx, e.target.value)}
                  placeholder={t.medicationPlaceholder}
                  className="flex-1 text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2 px-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
                />
                {medications.length > 1 && (
                  <button
                    type="button"
                    onClick={() => handleRemoveMedication(idx)}
                    title={t.removeMedication}
                    className="p-2 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Age */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-navy-800 mb-1.5 flex items-center gap-1.5" htmlFor="patient-age">
            <User className="w-4 h-4 text-teal-700" />
            <span>{t.ageLabel}</span>
          </label>
          <input
            id="patient-age"
            type="number"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder={t.agePlaceholder}
            className="w-full text-sm rounded-xl border border-slate-300 bg-slate-50/50 py-2.5 px-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
          />
        </div>

        {/* Continue Button */}
        <button
          type="submit"
          id="profile-continue-btn"
          disabled={isLoading}
          className="w-full min-h-[48px] py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] disabled:opacity-75 text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{t.saving}</span>
            </>
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
