"use client";

import React, { useState, useEffect, useRef } from "react";
import { useApp } from "../context/AppContext";
import { api, RecordMedicationItem } from "../lib/api";
import {
  FileText,
  UploadCloud,
  ArrowRight,
  ArrowLeft,
  Loader2,
  Plus,
  Trash2,
  CheckCircle2,
  Sparkles,
  AlertCircle,
} from "lucide-react";

export default function OnboardingPrescriptionScreen() {
  const {
    setScreen,
    setStagedOcrUpload,
    setOcrReturnScreen,
    t,
    isUrdu,
    isLiveMode,
    liveProfile,
  } = useApp();

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [ocrEnabled, setOcrEnabled] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Manual fallback state
  const [showManualForm, setShowManualForm] = useState<boolean>(false);
  const [manualMedName, setManualMedName] = useState("");
  const [manualMedDosage, setManualMedDosage] = useState("");
  const [manualMeds, setManualMeds] = useState<RecordMedicationItem[]>([]);
  const [isSavingManual, setIsSavingManual] = useState(false);

  useEffect(() => {
    // Check OCR capability from record endpoint if live
    let mounted = true;
    if (isLiveMode) {
      api
        .getRecord()
        .then((rec) => {
          if (mounted) {
            const enabled = rec.ocr_enabled !== false;
            setOcrEnabled(enabled);
            if (!enabled) {
              setShowManualForm(true);
            }
            if (rec.medications) {
              setManualMeds(rec.medications);
            }
          }
        })
        .catch(() => {
          // Defaults to enabled or manual fallback
        });
    }
    return () => {
      mounted = false;
    };
  }, [isLiveMode]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setIsUploading(true);

    try {
      const res = await api.uploadOcrImage(file);
      setStagedOcrUpload(res);
      setOcrReturnScreen("home");
      setScreen("ocr_confirm");
    } catch {
      // Never show server error text to patients (K6)
      setError(
        isUrdu
          ? "دستاویز پر کارروائی نہیں ہو سکی۔ براہ کرم واضح تصویر فراہم کریں یا نیچے ادویات خود درج کریں۔"
          : "Could not process document. Please ensure it is a clear JPEG or PNG under 5MB, or type your medicines below."
      );
      setShowManualForm(true);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleAddManualMed = async () => {
    if (!manualMedName.trim()) return;
    setError(null);
    setIsSavingManual(true);

    const name = manualMedName.trim();
    const dosage = manualMedDosage.trim() || "As directed";

    try {
      if (isLiveMode) {
        const created = await api.createRecordMedication({
          name,
          dosage,
          status: "active",
        });
        setManualMeds((prev) => [...prev, created]);
      } else {
        const mockItem: RecordMedicationItem = {
          id: `med-${Date.now()}`,
          name,
          dosage,
          status: "active",
          origin: "patient",
        };
        setManualMeds((prev) => [...prev, mockItem]);
      }
      setManualMedName("");
      setManualMedDosage("");
    } catch {
      setError(
        isUrdu
          ? "دوا محفوظ نہیں کی جا سکی۔ براہ کرم دوبارہ کوشش کریں۔"
          : "Could not save medication. Please try again."
      );
    } finally {
      setIsSavingManual(false);
    }
  };

  const handleRemoveManualMed = async (medId: string) => {
    try {
      if (isLiveMode) {
        await api.deleteRecordMedication(medId);
      }
      setManualMeds((prev) => prev.filter((m) => m.id !== medId));
    } catch {
      // Best effort
    }
  };

  const handleSkipOrDone = () => {
    setScreen("home");
  };

  const isRomanUrdu = liveProfile?.language === "roman_ur" || liveProfile?.language === "ur_roman";

  return (
    <div
      className="w-full max-w-xl mx-auto space-y-6 animate-fadeIn py-6 px-4"
      dir={isUrdu ? "rtl" : "ltr"}
      data-testid="onboarding-prescription-screen"
    >
      {/* Header Banner */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-purple-900 p-6 sm:p-7 text-white rounded-3xl relative overflow-hidden shadow-xl text-center">
        <div className="absolute -top-10 -right-10 w-36 h-36 bg-purple-400/20 rounded-full blur-2xl pointer-events-none" />
        <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-purple-500/30 text-purple-200 text-xs font-bold uppercase tracking-wider mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          <span>{isUrdu ? "اختیاری مرحلہ" : "Optional Step"}</span>
        </div>
        <h1 className="font-heading text-xl sm:text-2xl font-bold mb-2">
          {t.onboardingPrescriptionTitle}
        </h1>
        <p className="text-slate-200 text-xs sm:text-sm leading-relaxed max-w-md mx-auto">
          {t.onboardingPrescriptionSubtitle}
        </p>
        {isRomanUrdu && (
          <p className="text-purple-200 text-xs italic mt-2">
            {t.onboardingPrescriptionRomanHelper}
          </p>
        )}
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs sm:text-sm flex items-start gap-2 shadow-2xs">
          <AlertCircle className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* OCR Upload Card (Only if OCR is enabled) */}
      {ocrEnabled && !showManualForm && (
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm text-center space-y-5">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="image/png,image/jpeg,image/jpg"
            className="hidden"
            data-testid="onboarding-prescription-file-input"
          />

          <div
            onClick={() => !isUploading && fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 transition-all cursor-pointer flex flex-col items-center justify-center space-y-3 ${
              isUploading
                ? "border-purple-300 bg-purple-50/50 cursor-not-allowed"
                : "border-purple-200 hover:border-purple-400 hover:bg-purple-50/30"
            }`}
          >
            <div className="w-14 h-14 rounded-2xl bg-purple-100 flex items-center justify-center text-purple-800">
              {isUploading ? (
                <Loader2 className="w-7 h-7 animate-spin text-purple-700" />
              ) : (
                <UploadCloud className="w-7 h-7" />
              )}
            </div>

            <div className="space-y-1">
              <span className="font-bold text-sm sm:text-base text-navy-900 block">
                {isUploading ? t.ocrUploading : t.onboardingPrescriptionUploadBtn}
              </span>
              <span className="text-xs text-slate-500 block">
                {isUrdu
                  ? "JPEG یا PNG تصویر (زیادہ سے زیادہ 5MB)"
                  : "JPEG or PNG photo (maximum 5MB)"}
              </span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowManualForm(true)}
              className="text-xs font-semibold text-purple-800 hover:text-purple-900 underline"
              data-testid="switch-to-manual-btn"
            >
              {isUrdu ? "یا ہاتھ سے ادویات درج کریں" : "Or type your medicines manually"}
            </button>

            <button
              type="button"
              onClick={handleSkipOrDone}
              data-testid="onboarding-skip-btn"
              className="px-5 py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs sm:text-sm font-semibold transition-all flex items-center gap-1.5 self-stretch sm:self-auto justify-center"
            >
              <span>{t.onboardingPrescriptionSkipBtn}</span>
              {isUrdu ? <ArrowLeft className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )}

      {/* Manual Entry Fallback Form (Shown when OCR_ENABLED=false or toggled) */}
      {(showManualForm || !ocrEnabled) && (
        <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200 shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-base font-bold text-navy-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-teal-700" />
                <span>{t.onboardingManualTitle}</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">{t.onboardingManualSubtitle}</p>
            </div>
            {ocrEnabled && (
              <button
                type="button"
                onClick={() => setShowManualForm(false)}
                className="text-xs text-purple-700 hover:text-purple-900 font-semibold underline"
              >
                {isUrdu ? "تصویر اپ لوڈ کریں" : "Upload photo instead"}
              </button>
            )}
          </div>

          {/* Active Manual Meds List */}
          {manualMeds.length > 0 && (
            <div className="space-y-2 border-t border-slate-100 pt-3">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                {isUrdu ? "درج شدہ ادویات" : "Added Medications"} ({manualMeds.length})
              </span>
              <div className="space-y-1.5">
                {manualMeds.map((m) => (
                  <div
                    key={m.id}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-2"
                  >
                    <div>
                      <span className="font-bold text-xs sm:text-sm text-navy-900 block">
                        {m.name}
                      </span>
                      <span className="text-[11px] text-slate-600 font-mono">{m.dosage}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleRemoveManualMed(m.id)}
                      className="p-1 text-slate-400 hover:text-red-700 rounded-lg hover:bg-red-50 text-xs"
                      title={t.ocrRemoveBtn}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Add Medicine Inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                {isUrdu ? "دوا کا نام" : "Medicine Name"}
              </label>
              <input
                type="text"
                value={manualMedName}
                onChange={(e) => setManualMedName(e.target.value)}
                placeholder={t.onboardingManualMedName}
                data-testid="onboarding-manual-med-name"
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>
            <div>
              <label className="text-[10px] font-bold text-slate-500 uppercase block mb-1">
                {isUrdu ? "خوراک / طریقہ" : "Dosage"}
              </label>
              <input
                type="text"
                value={manualMedDosage}
                onChange={(e) => setManualMedDosage(e.target.value)}
                placeholder={t.onboardingManualMedDosage}
                data-testid="onboarding-manual-med-dosage"
                className="w-full text-xs p-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleAddManualMed}
              disabled={isSavingManual || !manualMedName.trim()}
              data-testid="onboarding-manual-add-btn"
              className="px-4 py-2 rounded-xl bg-teal-800 text-white text-xs font-semibold hover:bg-teal-900 disabled:opacity-50 transition-all flex items-center gap-1.5"
            >
              {isSavingManual ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Plus className="w-3.5 h-3.5" />
              )}
              <span>{t.onboardingManualAddBtn}</span>
            </button>
          </div>

          {/* Bottom Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={handleSkipOrDone}
              data-testid="onboarding-manual-skip-btn"
              className="text-xs text-slate-500 hover:text-slate-800 font-semibold"
            >
              {t.onboardingPrescriptionSkipBtn}
            </button>

            <button
              type="button"
              onClick={handleSkipOrDone}
              data-testid="onboarding-save-continue-btn"
              className="px-6 py-2.5 rounded-xl bg-navy-800 hover:bg-navy-900 text-white text-xs sm:text-sm font-semibold transition-all flex items-center gap-1.5 self-stretch sm:self-auto justify-center"
            >
              <span>{t.onboardingManualSaveBtn}</span>
              {isUrdu ? <ArrowLeft className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
