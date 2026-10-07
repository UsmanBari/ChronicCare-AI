"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../context/AppContext";
import {
  FileText,
  Pill,
  ShieldCheck,
  Activity,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Loader2,
  Info,
  ChevronDown,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import {
  api,
  ApiError,
  PatientRecordResponse,
  RecordMedicationItem,
  RecordAllergyItem,
  RecordObservationItem,
  RecordConditionItem,
} from "../lib/api";
import { mapApiError } from "../lib/presentation";

export const HealthRecordScreen = () => {
  const { setScreen, liveProfile, isLiveMode, t, isUrdu } = useApp();

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Record data
  const [conditions, setConditions] = useState<RecordConditionItem[]>([]);
  const [conditionsBasis, setConditionsBasis] = useState<Record<string, string>>({});
  const [medications, setMedications] = useState<RecordMedicationItem[]>([]);
  const [allergies, setAllergies] = useState<RecordAllergyItem[]>([]);
  const [observations, setObservations] = useState<RecordObservationItem[]>([]);

  // Medication form state
  const [medName, setMedName] = useState("");
  const [medDose, setMedDose] = useState("");
  const [medStatus, setMedStatus] = useState<"active" | "stopped">("active");
  const [isAddingMed, setIsAddingMed] = useState(false);

  // Allergy form state
  const [allergySubstance, setAllergySubstance] = useState("");
  const [allergyReaction, setAllergyReaction] = useState("");
  const [allergyConfirmed, setAllergyConfirmed] = useState(false);
  const [isAddingAllergy, setIsAddingAllergy] = useState(false);

  // Observation form state
  const [obsType, setObsType] = useState<string>("glucose");
  const [obsValue, setObsValue] = useState<string>("");
  const [obsMeasuredAt, setObsMeasuredAt] = useState<string>(
    new Date().toISOString().slice(0, 16)
  );
  const [isAddingObs, setIsAddingObs] = useState(false);

  // Fetch record on mount
  useEffect(() => {
    if (!isLiveMode) {
      setIsLoading(false);
      return;
    }
    loadRecord();
  }, [isLiveMode]);

  const loadRecord = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const rec: PatientRecordResponse = await api.getRecord();
      setConditions(rec.conditions || []);
      const basisMap: Record<string, string> = {};
      (rec.conditions || []).forEach((c) => {
        if (c.basis) {
          basisMap[c.name] = c.basis;
        }
      });
      setConditionsBasis(basisMap);
      setMedications(rec.medications || []);
      setAllergies(rec.allergies || []);
      setObservations(rec.baseline_observations || []);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to load clinical record");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const showToast = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  // 1. Conditions Basis Update
  const handleBasisChange = async (conditionName: string, newBasis: string) => {
    setError(null);
    const updated = { ...conditionsBasis, [conditionName]: newBasis };
    setConditionsBasis(updated);
    try {
      await api.updateConditionsBasis({ [conditionName]: newBasis || null });
      showToast(isUrdu ? "تشخیصی بنیاد محفوظ کر لی گئی ہے" : "Condition diagnostic basis updated");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to update diagnostic basis");
      }
    }
  };

  // 2. Add Medication
  const handleAddMedication = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const cleanName = medName.trim();
    const cleanDose = medDose.trim();

    if (!cleanName) {
      setError(isUrdu ? "براہ کرم دوا کا نام درج کریں" : "Please enter a medication name");
      return;
    }
    if (!cleanDose) {
      setError(isUrdu ? "براہ کرم دوا کی مقدار درج کریں" : "Please enter the medication dosage");
      return;
    }
    if (cleanName.length > 80) {
      setError("Medication name must be 80 characters or fewer.");
      return;
    }
    if (cleanDose.length > 100) {
      setError("Dosage must be 100 characters or fewer.");
      return;
    }

    setIsAddingMed(true);
    try {
      const added = await api.createRecordMedication({
        name: cleanName,
        dosage: cleanDose,
        status: medStatus,
      });
      setMedications((prev) => [...prev, added]);
      setMedName("");
      setMedDose("");
      setMedStatus("active");
      showToast(isUrdu ? "دوا شامل کر دی گئی ہے" : "Medication added to record");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to add medication");
      }
    } finally {
      setIsAddingMed(false);
    }
  };

  // Toggle Medication Status (Active <-> Stopped)
  const handleToggleMedStatus = async (med: RecordMedicationItem) => {
    setError(null);
    const nextStatus: "active" | "stopped" = med.status === "active" ? "stopped" : "active";
    try {
      const updated = await api.updateRecordMedication(med.id, { status: nextStatus });
      setMedications((prev) => prev.map((m) => (m.id === med.id ? updated : m)));
      showToast(
        nextStatus === "active"
          ? isUrdu
            ? "دوا کو فعال کر دیا گیا ہے"
            : "Medication marked as active"
          : isUrdu
          ? "دوا کو بند شدہ نشان زد کیا گیا ہے"
          : "Medication marked as stopped"
      );
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to update medication");
      }
    }
  };

  // Delete Medication
  const handleDeleteMed = async (medId: string) => {
    setError(null);
    try {
      await api.deleteRecordMedication(medId);
      setMedications((prev) => prev.filter((m) => m.id !== medId));
      showToast(isUrdu ? "دوا خارج کر دی گئی ہے" : "Medication removed from record");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to delete medication");
      }
    }
  };

  // 3. Add Allergy
  const handleAddAllergy = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const cleanSubstance = allergySubstance.trim();
    const cleanReaction = allergyReaction.trim() || undefined;

    if (!cleanSubstance) {
      setError(isUrdu ? "براہ کرم الرجی کا مادہ درج کریں" : "Please enter the allergy substance");
      return;
    }
    if (cleanSubstance.length > 80) {
      setError("Allergy substance must be 80 characters or fewer.");
      return;
    }
    if (cleanReaction && cleanReaction.length > 120) {
      setError("Reaction must be 120 characters or fewer.");
      return;
    }

    setIsAddingAllergy(true);
    try {
      const added = await api.createRecordAllergy({
        substance: cleanSubstance,
        reaction: cleanReaction,
        confirmed: allergyConfirmed,
      });
      setAllergies((prev) => [...prev, added]);
      setAllergySubstance("");
      setAllergyReaction("");
      setAllergyConfirmed(false);
      showToast(isUrdu ? "الرجی شامل کر دی گئی ہے" : "Allergy added to record");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to add allergy");
      }
    } finally {
      setIsAddingAllergy(false);
    }
  };

  // Delete Allergy
  const handleDeleteAllergy = async (allergyId: string) => {
    setError(null);
    try {
      await api.deleteRecordAllergy(allergyId);
      setAllergies((prev) => prev.filter((a) => a.id !== allergyId));
      showToast(isUrdu ? "الرجی خارج کر دی گئی ہے" : "Allergy removed from record");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to delete allergy");
      }
    }
  };

  // 4. Add Baseline Observation
  const handleAddObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const val = parseFloat(obsValue);
    if (isNaN(val)) {
      setError(isUrdu ? "براہ کرم درست نمبر درج کریں" : "Please enter a valid numeric reading");
      return;
    }

    // Client-side range validation mirroring server
    if (obsType === "glucose" && (val < 20 || val > 600)) {
      setError("Glucose reading must be between 20 and 600 mg/dL.");
      return;
    }
    if (obsType === "blood_pressure_systolic" && (val < 60 || val > 260)) {
      setError("Systolic blood pressure must be between 60 and 260 mmHg.");
      return;
    }
    if (obsType === "blood_pressure_diastolic" && (val < 30 || val > 160)) {
      setError("Diastolic blood pressure must be between 30 and 160 mmHg.");
      return;
    }
    if (obsType === "weight" && (val < 20 || val > 300)) {
      setError("Weight must be between 20 and 300 kg.");
      return;
    }
    if (obsType === "hba1c" && (val < 3 || val > 20)) {
      setError("HbA1c must be between 3% and 20%.");
      return;
    }

    let isoTimestamp = new Date().toISOString();
    if (obsMeasuredAt) {
      try {
        const parsed = new Date(obsMeasuredAt);
        if (parsed.getTime() > Date.now() + 60000) {
          setError(isUrdu ? "پیمائش کا وقت مستقبل میں نہیں ہو سکتا" : "Reading time cannot be in the future");
          return;
        }
        isoTimestamp = parsed.toISOString();
      } catch {
        // Fallback to now
      }
    }

    setIsAddingObs(true);
    try {
      const added = await api.createRecordObservation({
        observation_type: obsType,
        value: val,
        measured_at: isoTimestamp,
      });
      setObservations((prev) => [...prev, added]);
      setObsValue("");
      showToast(isUrdu ? "پیمائش ریکارڈ میں شامل کر دی گئی ہے" : "Baseline reading added to record");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to add observation");
      }
    } finally {
      setIsAddingObs(false);
    }
  };

  // Delete Observation
  const handleDeleteObservation = async (obsId: string) => {
    setError(null);
    try {
      await api.deleteRecordObservation(obsId);
      setObservations((prev) => prev.filter((o) => o.id !== obsId));
      showToast(isUrdu ? "پیمائش خارج کر دی گئی ہے" : "Baseline reading removed");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(mapApiError(err.status, err.detail));
      } else {
        setError(err?.message || "Failed to delete observation");
      }
    }
  };

  if (isLoading) {
    return (
      <div className="w-full max-w-2xl mx-auto surface-card rounded-3xl p-12 text-center space-y-4 animate-fadeIn">
        <Loader2 className="w-8 h-8 animate-spin text-teal-700 mx-auto" />
        <p className="text-sm font-semibold text-slate-600">
          {isUrdu ? "آپ کا کلینیکل ریکارڈ لوڈ ہو رہا ہے..." : "Loading your health record..."}
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6 animate-fadeIn pb-8" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header Banner */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-6 sm:p-7 text-white rounded-3xl relative overflow-hidden shadow-xl">
        <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-teal-500/25 text-teal-200 text-xs font-bold uppercase tracking-wider">
            <FileText className="w-3.5 h-3.5" />
            <span>{isUrdu ? "آئسولیٹڈ موڈ کلینیکل ریکارڈ" : "Isolated Mode Clinical Record"}</span>
          </div>
        </div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold mb-1.5">
          {isUrdu ? "آپ کا ذاتی ہیلتھ ریکارڈ" : "Your Health Record"}
        </h1>
        <p className="text-slate-200 text-xs sm:text-sm leading-relaxed max-w-xl">
          {isUrdu
            ? "اپنے حالات، ادویات، الرجی اور بنیادی پیمائشیں درج کریں تاکہ خودکار چیک ان کا صحیح موازنہ ہو سکے۔"
            : "Enter your conditions, medications, allergies, and baseline vitals. This establishes your private health baseline for accurate check-in comparisons."}
        </p>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-2xl bg-amber-50 border-2 border-amber-600/60 text-amber-950 text-sm font-semibold flex items-center gap-2.5 animate-fadeIn">
          <AlertTriangle className="w-5 h-5 text-emergencyRed-700 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-2xl bg-mutedGreen-100 border border-mutedGreen-800 text-mutedGreen-900 text-sm font-bold flex items-center gap-2.5 animate-fadeIn">
          <CheckCircle2 className="w-5 h-5 text-mutedGreen-800 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* SECTION 1: CONDITIONS DIAGNOSTIC BASIS */}
      <div className="surface-card rounded-3xl p-6 space-y-4">
        <div className="flex items-center gap-2.5 border-b border-slate-200 pb-3">
          <Activity className="w-5 h-5 text-teal-700 shrink-0" />
          <div>
            <h2 className="font-heading text-lg font-bold text-navy-800">
              {isUrdu ? "۱. طبی حالات اور تشخیصی بنیاد" : "1. Conditions & Diagnostic Basis"}
            </h2>
            <p className="text-xs text-slate-500">
              {isUrdu
                ? "ہر حالت کے لیے بتائیں کہ اس کی تشخیص کیسے ہوئی تھی۔"
                : "For each condition in your profile, select how it was established."}
            </p>
          </div>
        </div>

        {conditions.length === 0 ? (
          <p className="text-xs text-slate-500 italic">
            {isUrdu ? "پروفائل میں کوئی حالت درج نہیں ہے۔" : "No conditions recorded in your profile yet."}
          </p>
        ) : (
          <div className="space-y-3">
            {conditions.map((cond, idx) => {
              const currentBasis = conditionsBasis[cond.name] || cond.basis || "unsure";
              return (
                <div
                  key={idx}
                  className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <span className="font-bold text-sm text-navy-800 capitalize">
                    {cond.name.replace(/_/g, " ")}
                  </span>
                  <div className="flex items-center gap-2">
                    <select
                      value={currentBasis}
                      onChange={(e) => handleBasisChange(cond.name, e.target.value)}
                      className="text-xs font-semibold rounded-xl border border-slate-300 bg-white py-2 px-3 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
                    >
                      <option value="clinician_diagnosed">
                        {isUrdu ? "طبیب کی تصدیق شدہ" : "Diagnosed by a clinician"}
                      </option>
                      <option value="self_reported">
                        {isUrdu ? "خود سے رپورٹ کردہ" : "Self-reported"}
                      </option>
                      <option value="unsure">
                        {isUrdu ? "یقین سے نہیں معلوم" : "Not sure"}
                      </option>
                    </select>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: MEDICATIONS */}
      <div className="surface-card rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2.5">
            <Pill className="w-5 h-5 text-teal-700 shrink-0" />
            <div>
              <h2 className="font-heading text-lg font-bold text-navy-800">
                {isUrdu ? "۲. باقاعدہ ادویات" : "2. Medications"}
              </h2>
              <p className="text-xs text-slate-500">
                {isUrdu
                  ? "صرف فعال ادویات کے بارے میں ہر چیک ان میں پوچھا جاتا ہے۔"
                  : "Only active medications are asked about in each check-in."}
              </p>
            </div>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400">
            {medications.length}/30
          </span>
        </div>

        {/* Existing Medications List */}
        {medications.length === 0 ? (
          <div className="p-4 rounded-2xl bg-slate-50 border border-dashed border-slate-300 text-center text-xs text-slate-500">
            {isUrdu ? "کوئی دوا درج نہیں ہے۔ نیچے فارم کے ذریعے شامل کریں۔" : "No medications added yet. Use the form below to add your prescriptions."}
          </div>
        ) : (
          <div className="space-y-2.5">
            {medications.map((med) => {
              const isActive = med.status === "active";
              return (
                <div
                  key={med.id}
                  className={`p-3.5 rounded-2xl border-2 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    isActive ? "bg-white border-teal-200 shadow-2xs" : "bg-slate-50 border-slate-200 opacity-75"
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-navy-900">{med.name}</span>
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                          isActive ? "bg-teal-100 text-teal-900" : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {isActive ? (isUrdu ? "فعال" : "Active") : (isUrdu ? "بند شدہ" : "Stopped")}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 font-mono">
                      {med.dosage && med.dosage.trim() && med.dosage.trim().toLowerCase() !== "dosage"
                        ? med.dosage
                        : (isUrdu ? "کوئی مقدار درج نہیں ہے" : "No dose entered")}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      type="button"
                      onClick={() => handleToggleMedStatus(med)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                        isActive
                          ? "bg-amber-50 hover:bg-amber-100 text-amber-900 border-amber-300"
                          : "bg-teal-50 hover:bg-teal-100 text-teal-900 border-teal-300"
                      }`}
                    >
                      {isActive ? (isUrdu ? "بند نشان زد کریں" : "Mark Stopped") : (isUrdu ? "فعال کریں" : "Mark Active")}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteMed(med.id)}
                      className="p-1.5 text-slate-400 hover:text-red-700 rounded-lg hover:bg-red-50 transition-colors"
                      title="Delete medication"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Add Medication Form */}
        <form onSubmit={handleAddMedication} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3 pt-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
            {isUrdu ? "نئی دوا شامل کریں:" : "Add New Medication:"}
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              value={medName}
              onChange={(e) => setMedName(e.target.value)}
              placeholder={isUrdu ? "دوا کا نام (جیسے Metformin 500mg)" : "Medication name (e.g. Metformin 500mg)"}
              maxLength={80}
              className="text-xs rounded-xl border border-slate-300 bg-white p-2.5 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
            />
            <input
              type="text"
              value={medDose}
              onChange={(e) => setMedDose(e.target.value)}
              placeholder={isUrdu ? "مقدار و وقت (جیسے 1 tablet twice daily)" : "Dosage (e.g. 1 tablet twice daily)"}
              maxLength={100}
              className="text-xs rounded-xl border border-slate-300 bg-white p-2.5 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
            />
          </div>
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center gap-2 text-xs">
              <label className="font-semibold text-slate-700">Status:</label>
              <select
                value={medStatus}
                onChange={(e) => setMedStatus(e.target.value as "active" | "stopped")}
                className="text-xs rounded-lg border border-slate-300 bg-white py-1 px-2 text-navy-800"
              >
                <option value="active">Active</option>
                <option value="stopped">Stopped</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={isAddingMed || !medName.trim() || !medDose.trim()}
              id="add-medication-btn"
              className="px-4 py-2 bg-teal-700 hover:bg-teal-600 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition-all flex items-center gap-1.5 shadow-xs"
            >
              {isAddingMed ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              <span>{isUrdu ? "دوا شامل کریں" : "Add Medication"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* SECTION 3: ALLERGIES */}
      <div className="surface-card rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-teal-700 shrink-0" />
            <div>
              <h2 className="font-heading text-lg font-bold text-navy-800">
                {isUrdu ? "۳. الرجی کا ریکارڈ" : "3. Allergies"}
              </h2>
              <p className="text-xs text-slate-500">
                {isUrdu
                  ? "الرجی آپ کے معالج کے لیے محفوظ کی جاتی ہے؛ ابھی یہ موازنے میں استعمال نہیں ہوتی۔"
                  : "Allergies are stored for your clinician; they are not used in comparisons yet."}
              </p>
            </div>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400">
            {allergies.length}/30
          </span>
        </div>

        {/* Existing Allergies List */}
        {allergies.length === 0 ? (
          <div className="p-4 rounded-2xl bg-slate-50 border border-dashed border-slate-300 text-center text-xs text-slate-500">
            {isUrdu ? "کوئی الرجی درج نہیں ہے۔" : "No known allergies recorded."}
          </div>
        ) : (
          <div className="space-y-2">
            {allergies.map((alg) => (
              <div
                key={alg.id}
                className="p-3.5 rounded-2xl bg-white border border-slate-200 flex items-center justify-between text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-navy-900">
                      {alg.substance && alg.substance.trim() && alg.substance.trim().toLowerCase() !== "substance"
                        ? alg.substance
                        : (isUrdu ? "کوئی مادہ درج نہیں ہے" : "No substance entered")}
                    </span>
                    {alg.confirmed && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Confirmed
                      </span>
                    )}
                  </div>
                  {alg.reaction && (
                    <p className="text-slate-500 text-[11px] mt-0.5">Reaction: {alg.reaction}</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteAllergy(alg.id)}
                  className="p-1.5 text-slate-400 hover:text-red-700 rounded-lg hover:bg-red-50 transition-colors"
                  title="Delete allergy"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add Allergy Form */}
        <form onSubmit={handleAddAllergy} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
            {isUrdu ? "نئی الرجی شامل کریں:" : "Add Allergy:"}
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              value={allergySubstance}
              onChange={(e) => setAllergySubstance(e.target.value)}
              placeholder={isUrdu ? "مادہ (جیسے Penicillin)" : "Substance (e.g. Penicillin)"}
              maxLength={80}
              className="text-xs rounded-xl border border-slate-300 bg-white p-2.5 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
            />
            <input
              type="text"
              value={allergyReaction}
              onChange={(e) => setAllergyReaction(e.target.value)}
              placeholder={isUrdu ? "ردعمل (اختیاری، جیسے Skin rash)" : "Reaction (optional, e.g. Skin rash)"}
              maxLength={120}
              className="text-xs rounded-xl border border-slate-300 bg-white p-2.5 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
            />
          </div>
          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={allergyConfirmed}
                onChange={(e) => setAllergyConfirmed(e.target.checked)}
                className="w-4 h-4 text-teal-700 rounded border-slate-300"
              />
              <span>{isUrdu ? "طبیب کی تصدیق شدہ ہے" : "Confirmed by a clinician"}</span>
            </label>
            <button
              type="submit"
              disabled={isAddingAllergy || !allergySubstance.trim()}
              id="add-allergy-btn"
              className="px-4 py-2 bg-teal-700 hover:bg-teal-600 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition-all flex items-center gap-1.5 shadow-xs"
            >
              {isAddingAllergy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              <span>{isUrdu ? "الرجی شامل کریں" : "Add Allergy"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* SECTION 4: BASELINE OBSERVATIONS */}
      <div className="surface-card rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-teal-700 shrink-0" />
            <div>
              <h2 className="font-heading text-lg font-bold text-navy-800">
                {isUrdu ? "۴. بنیادی پیمائشیں (اختیاری)" : "4. Baseline Readings (Optional)"}
              </h2>
              <p className="text-xs text-slate-500">
                {isUrdu
                  ? "پیمائش کا موازنہ ۴۸ گھنٹوں کے اندر کیے گئے چیک ان سے کیا جاتا ہے۔"
                  : "A reading is compared with a check-in taken within 48 hours. Older readings are kept as history for the trend feature in a later version."}
              </p>
            </div>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400">
            {observations.length}/20
          </span>
        </div>

        {/* Existing Observations List */}
        {observations.length === 0 ? (
          <div className="p-4 rounded-2xl bg-slate-50 border border-dashed border-slate-300 text-center text-xs text-slate-500">
            {isUrdu ? "کوئی بنیادی پیمائش درج نہیں ہے۔" : "No baseline readings entered yet."}
          </div>
        ) : (
          <div className="space-y-2">
            {observations.map((obs) => (
              <div
                key={obs.id}
                className="p-3.5 rounded-2xl bg-white border border-slate-200 flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-bold text-navy-900 capitalize block">
                    {obs.observation_type.replace(/_/g, " ")}: {obs.value} {obs.unit}
                  </span>
                  <span className="text-[11px] text-slate-400">
                    Measured: {new Date(obs.measured_at).toLocaleString()}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteObservation(obs.id)}
                  className="p-1.5 text-slate-400 hover:text-red-700 rounded-lg hover:bg-red-50 transition-colors"
                  title="Delete observation"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add Observation Form */}
        <form onSubmit={handleAddObservation} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
            {isUrdu ? "نئی پیمائش شامل کریں:" : "Add Reading:"}
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Type</label>
              <select
                value={obsType}
                onChange={(e) => setObsType(e.target.value)}
                className="w-full text-xs rounded-xl border border-slate-300 bg-white p-2.5 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
              >
                <option value="glucose">Blood Glucose (mg/dL)</option>
                <option value="blood_pressure_systolic">Systolic BP (mmHg)</option>
                <option value="blood_pressure_diastolic">Diastolic BP (mmHg)</option>
                <option value="weight">Weight (kg)</option>
                <option value="hba1c">HbA1c (%)</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Value</label>
              <input
                type="number"
                step="any"
                value={obsValue}
                onChange={(e) => setObsValue(e.target.value)}
                placeholder="e.g. 140"
                className="w-full text-xs rounded-xl border border-slate-300 bg-white p-2.5 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Date & Time</label>
              <input
                type="datetime-local"
                value={obsMeasuredAt}
                onChange={(e) => setObsMeasuredAt(e.target.value)}
                className="w-full text-xs rounded-xl border border-slate-300 bg-white p-2 text-navy-800 focus:outline-none focus:ring-2 focus:ring-teal-700"
              />
            </div>
          </div>

          <div className="flex justify-end pt-1">
            <button
              type="submit"
              disabled={isAddingObs || !obsValue.trim()}
              id="add-observation-btn"
              className="px-4 py-2 bg-teal-700 hover:bg-teal-600 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition-all flex items-center gap-1.5 shadow-xs"
            >
              {isAddingObs ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              <span>{isUrdu ? "پیمائش شامل کریں" : "Add Reading"}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Navigation Buttons: Skip for now and Done */}
      <div className="flex items-center justify-between gap-4 pt-2">
        <button
          type="button"
          onClick={() => setScreen("home")}
          id="skip-record-btn"
          className="min-h-[48px] px-6 py-3 border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl transition-all shadow-xs"
        >
          {isUrdu ? "ابھی چھوڑ دیں" : "Skip for now"}
        </button>

        <button
          type="button"
          onClick={() => setScreen("home")}
          id="done-record-btn"
          className="min-h-[48px] px-8 py-3 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center gap-2"
        >
          <span>{isUrdu ? "مکمل" : "Done"}</span>
          <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
        </button>
      </div>
    </div>
  );
};
