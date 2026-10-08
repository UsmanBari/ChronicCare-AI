"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import { Plus, Trash2, ArrowRight, Activity, Pill, User, ShieldCheck, ShieldAlert, Loader2, Globe, CheckCircle2 } from "lucide-react";
import { api, ApiError, ProfileUpdateRequest } from "../lib/api";
import { Language } from "../translations";
import { calculateAgeFromDob } from "../lib/presentation";

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

  const [hasT2D, setHasT2D] = useState<boolean>(() => {
    const conds = liveProfile?.conditions || profile.conditions || [];
    return conds.some((c) => c.toLowerCase().includes("diabet"));
  });

  const [hasHTN, setHasHTN] = useState<boolean>(() => {
    const conds = liveProfile?.conditions || profile.conditions || [];
    return conds.some((c) => c.toLowerCase().includes("hyper"));
  });

  const [onInsulin, setOnInsulin] = useState<boolean>(
    liveProfile?.on_insulin_or_sulfonylurea !== undefined
      ? liveProfile.on_insulin_or_sulfonylurea
      : false
  );

  const [selectedLang, setSelectedLang] = useState<string>(
    liveProfile?.language || language || "en"
  );

  const [heightCm, setHeightCm] = useState<string>(
    liveProfile?.height_cm !== undefined && liveProfile?.height_cm !== null ? String(liveProfile.height_cm) : ""
  );
  const [weightKg, setWeightKg] = useState<string>(
    liveProfile?.weight_kg !== undefined && liveProfile?.weight_kg !== null ? String(liveProfile.weight_kg) : ""
  );
  const [diagYearDiabetes, setDiagYearDiabetes] = useState<string>(
    liveProfile?.diagnosis_year_diabetes !== undefined && liveProfile?.diagnosis_year_diabetes !== null ? String(liveProfile.diagnosis_year_diabetes) : ""
  );
  const [diagYearHtn, setDiagYearHtn] = useState<string>(
    liveProfile?.diagnosis_year_hypertension !== undefined && liveProfile?.diagnosis_year_hypertension !== null ? String(liveProfile.diagnosis_year_hypertension) : ""
  );
  const [smokingStatus, setSmokingStatus] = useState<string>(
    liveProfile?.smoking_status || "prefer_not_to_say"
  );
  const [voiceEnabled, setVoiceEnabled] = useState<boolean>(
    Boolean(liveProfile?.voice_enabled)
  );

  // Comorbidities checklist state
  const [comorbKidney, setComorbKidney] = useState<boolean>(Boolean(liveProfile?.comorbidities?.kidney_disease));
  const [comorbHeart, setComorbHeart] = useState<boolean>(Boolean(liveProfile?.comorbidities?.heart_disease));
  const [comorbStroke, setComorbStroke] = useState<boolean>(Boolean(liveProfile?.comorbidities?.stroke_or_tia));
  const [comorbEye, setComorbEye] = useState<boolean>(Boolean(liveProfile?.comorbidities?.eye_problems));
  const [comorbNerve, setComorbNerve] = useState<boolean>(Boolean(liveProfile?.comorbidities?.nerve_or_foot_problems));

  const [medications, setMedications] = useState<string[]>(
    profile.medications && profile.medications.length > 0 ? profile.medications : ["Metformin 500mg (1+1)"]
  );

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isLiveMode && liveProfile) {
      if (liveProfile.conditions) {
        setHasT2D(liveProfile.conditions.some((c) => c.toLowerCase().includes("diabet")));
        setHasHTN(liveProfile.conditions.some((c) => c.toLowerCase().includes("hyper")));
      }
      setOnInsulin(Boolean(liveProfile.on_insulin_or_sulfonylurea));
      if (liveProfile.language) {
        setSelectedLang(liveProfile.language);
      }
      if (liveProfile.height_cm !== undefined && liveProfile.height_cm !== null) {
        setHeightCm(String(liveProfile.height_cm));
      }
      if (liveProfile.weight_kg !== undefined && liveProfile.weight_kg !== null) {
        setWeightKg(String(liveProfile.weight_kg));
      }
      if (liveProfile.diagnosis_year_diabetes !== undefined && liveProfile.diagnosis_year_diabetes !== null) {
        setDiagYearDiabetes(String(liveProfile.diagnosis_year_diabetes));
      }
      if (liveProfile.diagnosis_year_hypertension !== undefined && liveProfile.diagnosis_year_hypertension !== null) {
        setDiagYearHtn(String(liveProfile.diagnosis_year_hypertension));
      }
      if (liveProfile.smoking_status) {
        setSmokingStatus(liveProfile.smoking_status);
      }
      if (liveProfile.voice_enabled !== undefined && liveProfile.voice_enabled !== null) {
        setVoiceEnabled(Boolean(liveProfile.voice_enabled));
      }
      if (liveProfile.comorbidities) {
        setComorbKidney(Boolean(liveProfile.comorbidities.kidney_disease));
        setComorbHeart(Boolean(liveProfile.comorbidities.heart_disease));
        setComorbStroke(Boolean(liveProfile.comorbidities.stroke_or_tia));
        setComorbEye(Boolean(liveProfile.comorbidities.eye_problems));
        setComorbNerve(Boolean(liveProfile.comorbidities.nerve_or_foot_problems));
      }
    }
  }, [isLiveMode, liveProfile]);

  const hasBoth = hasT2D && hasHTN;
  const canContinue = hasT2D || hasHTN;

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

  const dob = liveProfile?.date_of_birth || profile.date_of_birth || null;
  const computedAge = calculateAgeFromDob(dob);
  const birthYear = dob ? parseInt(dob.split("-")[0], 10) : null;
  const currentYear = new Date().getFullYear();

  const handleContinue = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!canContinue) {
      setError(
        isUrdu
          ? "آگے بڑھنے کے لیے براہ کرم کم از کم ایک بیماری کا انتخاب کریں۔"
          : "Please select at least one condition to continue."
      );
      return;
    }

    // Validate Height if provided
    let parsedHeight: number | null = null;
    if (heightCm.trim()) {
      const h = parseFloat(heightCm.trim());
      if (isNaN(h) || h < 50 || h > 250) {
        setError(isUrdu ? "قد ۵۰ سے ۲۵۰ سینٹی میٹر کے درمیان ہونا چاہیے۔" : "Height must be between 50 and 250 cm.");
        return;
      }
      parsedHeight = h;
    }

    // Validate Weight if provided
    let parsedWeight: number | null = null;
    if (weightKg.trim()) {
      const w = parseFloat(weightKg.trim());
      if (isNaN(w) || w < 20 || w > 400) {
        setError(isUrdu ? "وزن ۲۰ سے ۴۰۰ کلوگرام کے درمیان ہونا چاہیے۔" : "Weight must be between 20 and 400 kg.");
        return;
      }
      parsedWeight = w;
    }

    // Validate Diagnosis Years
    let parsedDiagYearT2D: number | null = null;
    if (hasT2D && diagYearDiabetes.trim()) {
      const yr = parseInt(diagYearDiabetes.trim(), 10);
      if (isNaN(yr) || yr < 1900 || yr > currentYear || (birthYear !== null && yr < birthYear)) {
        setError(isUrdu ? `ذیابیطس کی تشخیص کا سال درست درج کریں (${birthYear || 1900}-${currentYear})` : `Diabetes diagnosis year must be between ${birthYear || 1900} and ${currentYear}.`);
        return;
      }
      parsedDiagYearT2D = yr;
    }

    let parsedDiagYearHtn: number | null = null;
    if (hasHTN && diagYearHtn.trim()) {
      const yr = parseInt(diagYearHtn.trim(), 10);
      if (isNaN(yr) || yr < 1900 || yr > currentYear || (birthYear !== null && yr < birthYear)) {
        setError(isUrdu ? `بلڈ پریشر کی تشخیص کا سال درست درج کریں (${birthYear || 1900}-${currentYear})` : `Hypertension diagnosis year must be between ${birthYear || 1900} and ${currentYear}.`);
        return;
      }
      parsedDiagYearHtn = yr;
    }

    setIsLoading(true);

    const cleanConditions: string[] = [];
    if (hasT2D) cleanConditions.push("Type 2 Diabetes");
    if (hasHTN) cleanConditions.push("Hypertension");

    const cleanMeds = medications.filter((m) => m.trim().length > 0);

    // Save mock state representation
    setProfile({
      ...profile,
      conditions: cleanConditions,
      medications: cleanMeds.length > 0 ? cleanMeds : ["Metformin 500mg (1+1)"],
    });

    if (isLiveMode) {
      try {
        const payload: ProfileUpdateRequest = {
          conditions: cleanConditions.map((c) =>
            c.toLowerCase().includes("diabet") ? "diabetes" : "hypertension"
          ),
          on_insulin_or_sulfonylurea: onInsulin,
          language: selectedLang,
          height_cm: parsedHeight,
          weight_kg: parsedWeight,
          diagnosis_year_diabetes: parsedDiagYearT2D,
          diagnosis_year_hypertension: parsedDiagYearHtn,
          smoking_status: smokingStatus || "prefer_not_to_say",
          voice_enabled: voiceEnabled,
          comorbidities: {
            kidney_disease: comorbKidney,
            heart_disease: comorbHeart,
            stroke_or_tia: comorbStroke,
            eye_problems: comorbEye,
            nerve_or_foot_problems: comorbNerve,
          },
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

  return (
    <div className="w-full max-w-lg mx-auto bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header */}
      <div className="bg-navy-800 p-6 sm:p-7 text-white text-center">
        <h1 className="font-heading text-2xl font-bold mb-1">{t.profileTitle}</h1>
        <p className="text-xs sm:text-sm text-slate-300 max-w-md mx-auto">{t.profileSubtitle}</p>
      </div>

      <form onSubmit={handleContinue} className="p-6 sm:p-7 space-y-6">
        {error && (
          <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2 animate-fadeIn">
            <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Independent Conditions Selection */}
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
                onChange={(e) => {
                  setHasT2D(e.target.checked);
                  setError(null);
                }}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span className="text-sm font-medium text-navy-800">
                {isUrdu
                  ? "ٹائپ ۲ ذیابیطس (ٹائپ ۱ یا دوران حمل ذیابیطس کے علاوہ)"
                  : "Type 2 diabetes (not Type 1 or pregnancy-related diabetes)"}
              </span>
            </label>

            {/* Hypertension */}
            <label className="flex items-center gap-3 p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer transition-colors">
              <input
                type="checkbox"
                id="condition-htn"
                checked={hasHTN}
                onChange={(e) => {
                  setHasHTN(e.target.checked);
                  setError(null);
                }}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span className="text-sm font-medium text-navy-800">
                {isUrdu ? "بلند فشار خون (ہائپر ٹینشن)" : "Hypertension"}
              </span>
            </label>

            {/* Derived Both Summary Indicator */}
            {hasBoth && (
              <div className="p-3 rounded-xl border border-teal-200 bg-teal-50/70 text-xs font-semibold text-teal-900 flex items-center gap-2 animate-fadeIn">
                <CheckCircle2 className="w-4 h-4 text-teal-700 shrink-0" />
                <span>
                  {isUrdu
                    ? "دونوں تشخیصات منتخب ہیں: ٹائپ ۲ ذیابیطس اور ہائپر ٹینشن۔"
                    : "Both conditions selected: Type 2 Diabetes and Hypertension (Dual Diagnosis Path)."}
                </span>
              </div>
            )}
          </div>
          {!canContinue && (
            <p className="text-[11px] text-amber-800 mt-2 font-medium">
              {isUrdu
                ? "براہ کرم آگے بڑھنے کے لیے کم از کم ایک بیماری منتخب کریں۔"
                : "Please select at least one condition to enable Save & Continue."}
            </p>
          )}
        </div>

        {/* Diagnosis Years (Optional) */}
        {(hasT2D || hasHTN) && (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800 block">
              {isUrdu ? "تشخیص کا سال (اختیاری)" : "Diagnosis Years (Optional)"}
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {hasT2D && (
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    {isUrdu ? "ذیابیطس کی تشخیص کا سال" : "Diabetes Year of Diagnosis"}
                  </label>
                  <input
                    type="number"
                    min="1900"
                    max={currentYear}
                    id="diag-year-diabetes-input"
                    value={diagYearDiabetes}
                    onChange={(e) => setDiagYearDiabetes(e.target.value)}
                    placeholder="e.g. 2018"
                    className="w-full text-sm rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
                  />
                </div>
              )}
              {hasHTN && (
                <div>
                  <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                    {isUrdu ? "بلڈ پریشر کی تشخیص کا سال" : "Hypertension Year of Diagnosis"}
                  </label>
                  <input
                    type="number"
                    min="1900"
                    max={currentYear}
                    id="diag-year-htn-input"
                    value={diagYearHtn}
                    onChange={(e) => setDiagYearHtn(e.target.value)}
                    placeholder="e.g. 2020"
                    className="w-full text-sm rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Physical Measurements: Height & Weight (Optional) */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-navy-800 block">
            {isUrdu ? "جسمانی پیمائش (اختیاری)" : "Body Measurements (Optional)"}
          </span>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                {isUrdu ? "قد (سینٹی میٹر)" : "Height (cm)"}
              </label>
              <input
                type="number"
                min="50"
                max="250"
                step="0.1"
                id="height-cm-input"
                value={heightCm}
                onChange={(e) => setHeightCm(e.target.value)}
                placeholder="e.g. 175"
                className="w-full text-sm rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-700 block mb-1">
                {isUrdu ? "وزن (کلوگرام)" : "Weight (kg)"}
              </label>
              <input
                type="number"
                min="20"
                max="400"
                step="0.1"
                id="weight-kg-input"
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value)}
                placeholder="e.g. 78"
                className="w-full text-sm rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
              />
            </div>
          </div>
        </div>

        {/* Smoking Status */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-navy-800 block">
            {isUrdu ? "تمباکو نوشی کی کیفیت" : "Smoking Status"}
          </label>
          <select
            id="smoking-status-select"
            value={smokingStatus}
            onChange={(e) => setSmokingStatus(e.target.value)}
            className="w-full text-sm rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
          >
            <option value="prefer_not_to_say">{isUrdu ? "بتانا مناسب نہیں" : "Prefer not to say"}</option>
            <option value="never">{isUrdu ? "کبھی نہیں پی" : "Never smoked"}</option>
            <option value="former">{isUrdu ? "سابقہ تمباکو نوش (چھوڑ چکے ہیں)" : "Former smoker"}</option>
            <option value="current">{isUrdu ? "موجودہ تمباکو نوش" : "Current smoker"}</option>
          </select>
        </div>

        {/* Comorbidities Checklist (Optional) */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-navy-800 block">
            {isUrdu ? "دیگر طبی کیفیات (اختیاری)" : "Other Medical History (Optional)"}
          </span>
          <div className="space-y-2">
            <label className="flex items-center gap-2.5 text-xs text-navy-800 cursor-pointer">
              <input
                type="checkbox"
                id="comorb-kidney"
                checked={comorbKidney}
                onChange={(e) => setComorbKidney(e.target.checked)}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span>{isUrdu ? "گردے کی بیماری (Kidney Disease)" : "Kidney disease"}</span>
            </label>
            <label className="flex items-center gap-2.5 text-xs text-navy-800 cursor-pointer">
              <input
                type="checkbox"
                id="comorb-heart"
                checked={comorbHeart}
                onChange={(e) => setComorbHeart(e.target.checked)}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span>{isUrdu ? "دل کی بیماری (Heart Disease / CAD)" : "Heart disease (Coronary Artery Disease)"}</span>
            </label>
            <label className="flex items-center gap-2.5 text-xs text-navy-800 cursor-pointer">
              <input
                type="checkbox"
                id="comorb-stroke"
                checked={comorbStroke}
                onChange={(e) => setComorbStroke(e.target.checked)}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span>{isUrdu ? "فالج یا وقتی دورہ (Stroke / TIA)" : "Stroke or TIA"}</span>
            </label>
            <label className="flex items-center gap-2.5 text-xs text-navy-800 cursor-pointer">
              <input
                type="checkbox"
                id="comorb-eye"
                checked={comorbEye}
                onChange={(e) => setComorbEye(e.target.checked)}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span>{isUrdu ? "آنکھوں کے مسائل (Diabetic Eye / Retinopathy)" : "Eye problems (Retinopathy)"}</span>
            </label>
            <label className="flex items-center gap-2.5 text-xs text-navy-800 cursor-pointer">
              <input
                type="checkbox"
                id="comorb-nerve"
                checked={comorbNerve}
                onChange={(e) => setComorbNerve(e.target.checked)}
                className="w-4 h-4 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
              />
              <span>{isUrdu ? "اعصابی یا پاؤں کی تکلیف (Neuropathy / Foot Ulcers)" : "Nerve or foot problems (Neuropathy)"}</span>
            </label>
          </div>
        </div>

        {/* Voice Input Privacy Toggle */}
        <div className="p-4 rounded-2xl bg-teal-50/50 border border-teal-200 space-y-2">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <span className="text-xs font-bold text-navy-900 block">
                {isUrdu ? "آواز سے جواب دینے کی سہولت فعال کریں" : "Enable Voice Input (Speech-to-Text)"}
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {isUrdu
                  ? "آواز صرف عارضی طور پر ٹیکسٹ بنانے کے لیے میموری میں پراسیس کی جاتی ہے اور کبھی محفوظ نہیں ہوتی۔"
                  : "Transcribed in memory only; audio is never stored on disk or server."}
              </p>
            </div>
            <input
              type="checkbox"
              id="voice-enabled-toggle"
              checked={voiceEnabled}
              onChange={(e) => setVoiceEnabled(e.target.checked)}
              className="w-5 h-5 text-teal-700 rounded border-slate-300 focus:ring-teal-700"
            />
          </label>
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

        {/* Read-Only Computed Age from DOB */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1 text-left">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <User className="w-4 h-4 text-teal-700" />
              <span>{t.ageLabel}</span>
            </label>
            {dob && (
              <span className="text-[11px] text-slate-500 font-mono">DOB: {dob}</span>
            )}
          </div>
          <p className="text-sm font-semibold text-navy-900 pt-0.5">
            {computedAge !== null
              ? isUrdu
                ? `عمر: ${computedAge} سال (آپ کی تاریخ پیدائش سے)`
                : `Age ${computedAge}, from your date of birth`
              : isUrdu
              ? "تاریخ پیدائش شمولیت کے اسکرین پر فراہم کی گئی ہے"
              : "Age calculated from your date of birth"}
          </p>
        </div>

        {/* Continue Button */}
        <button
          type="submit"
          id="profile-continue-btn"
          disabled={isLoading || !canContinue}
          className="w-full min-h-[48px] py-3 px-4 bg-navy-800 hover:bg-navy-700 active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
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
