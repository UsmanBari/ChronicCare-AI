"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { api, ConfirmOcrItem } from "../lib/api";
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Edit2,
  Trash2,
  ArrowLeft,
  ArrowRight,
  Loader2,
  Save,
  Check,
  X,
} from "lucide-react";

interface EditableObservation {
  id: string;
  type: string;
  value: number;
  unit: string;
  date?: string | null;
  evidence?: string | null;
  confirmed: boolean;
  isEditing: boolean;
}

interface EditableMedication {
  id: string;
  name: string;
  dosage: string;
  status: string;
  evidence?: string | null;
  confirmed: boolean;
  isEditing: boolean;
}

interface EditableAllergy {
  id: string;
  substance: string;
  reaction?: string | null;
  severity?: string | null;
  status?: string | null;
  evidence?: string | null;
  confirmed: boolean;
  isEditing: boolean;
}

export default function OcrConfirmScreen() {
  const { stagedOcrUpload, setStagedOcrUpload, setScreen, t, isUrdu } = useApp();

  const [observations, setObservations] = useState<EditableObservation[]>(() => {
    return (stagedOcrUpload?.extracted?.observations || []).map((o, idx) => ({
      id: o.id || `obs-${idx}`,
      type: o.type,
      value: o.value,
      unit: o.unit || "",
      date: o.date || null,
      evidence: o.evidence || null,
      confirmed: true,
      isEditing: false,
    }));
  });

  const [medications, setMedications] = useState<EditableMedication[]>(() => {
    return (stagedOcrUpload?.extracted?.medications || []).map((m, idx) => ({
      id: m.id || `med-${idx}`,
      name: m.name,
      dosage: m.dosage || "",
      status: m.status || "active",
      evidence: m.evidence || null,
      confirmed: true,
      isEditing: false,
    }));
  });

  const [allergies, setAllergies] = useState<EditableAllergy[]>(() => {
    return (stagedOcrUpload?.extracted?.allergies || []).map((a, idx) => ({
      id: a.id || `all-${idx}`,
      substance: a.substance,
      reaction: a.reaction || null,
      severity: a.severity || null,
      status: a.status || "active",
      evidence: a.evidence || null,
      confirmed: true,
      isEditing: false,
    }));
  });

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasUrdu = Boolean(stagedOcrUpload?.extracted?.has_urdu);
  const uploadId = stagedOcrUpload?.upload_id;

  const handleCancel = async () => {
    if (uploadId) {
      try {
        await api.cancelOcrUpload(uploadId);
      } catch {
        // Best effort cancellation
      }
    }
    setStagedOcrUpload(null);
    setScreen("health_record");
  };

  const handleConfirmAndSave = async () => {
    if (!uploadId) {
      setScreen("health_record");
      return;
    }
    setError(null);
    setIsSaving(true);

    try {
      const confirmedItems: ConfirmOcrItem[] = [];

      observations
        .filter((o) => o.confirmed)
        .forEach((o) => {
          confirmedItems.push({
            id: o.id,
            type: o.type,
            value: Number(o.value),
            unit: o.unit,
            date: o.date,
            evidence: o.evidence,
          });
        });

      medications
        .filter((m) => m.confirmed)
        .forEach((m) => {
          confirmedItems.push({
            id: m.id,
            name: m.name,
            dosage: m.dosage,
            status: m.status,
            evidence: m.evidence,
          });
        });

      allergies
        .filter((a) => a.confirmed)
        .forEach((a) => {
          confirmedItems.push({
            id: a.id,
            substance: a.substance,
            reaction: a.reaction || undefined,
            severity: a.severity || undefined,
            status: a.status || undefined,
            evidence: a.evidence || undefined,
          });
        });

      if (confirmedItems.length === 0) {
        setError(isUrdu ? "براہ کرم محفوظ کرنے کے لیے کم از کم ایک اندراج منتخب کریں۔" : "Please confirm at least one item to save.");
        setIsSaving(false);
        return;
      }

      await api.confirmOcrUpload(uploadId, confirmedItems);
      setStagedOcrUpload(null);
      setScreen("health_record");
    } catch (err: any) {
      setError(err?.detail || err?.message || (isUrdu ? "محفوظ کرنے میں خرابی واقع ہوئی" : "Failed to save confirmed items."));
      setIsSaving(false);
    }
  };

  const confirmedCount =
    observations.filter((o) => o.confirmed).length +
    medications.filter((m) => m.confirmed).length +
    allergies.filter((a) => a.confirmed).length;

  const totalCount = observations.length + medications.length + allergies.length;

  return (
    <div className="space-y-6 animate-fadeIn pb-12" data-testid="ocr-confirm-screen">
      {/* Header Banner */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-purple-900 p-6 sm:p-7 text-white rounded-3xl relative overflow-hidden shadow-xl">
        <div className="absolute -top-10 -right-10 w-36 h-36 bg-purple-400/20 rounded-full blur-2xl pointer-events-none" />
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-purple-500/30 text-purple-200 text-xs font-bold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            <span>{t.ocrBadge}</span>
          </div>
          <button
            type="button"
            onClick={handleCancel}
            data-testid="ocr-back-to-record-btn"
            className="px-3 py-1 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-all flex items-center gap-1"
          >
            {isUrdu ? <ArrowRight className="w-3.5 h-3.5" /> : <ArrowLeft className="w-3.5 h-3.5" />}
            <span>{t.ocrCancelBtn}</span>
          </button>
        </div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold mb-1.5">
          {t.ocrConfirmTitle}
        </h1>
        <p className="text-slate-200 text-xs sm:text-sm leading-relaxed max-w-xl">
          {t.ocrConfirmSubtitle}
        </p>
      </div>

      {/* Urdu Document Notice Banner if detected */}
      {hasUrdu && (
        <div
          data-testid="ocr-urdu-notice"
          className="p-4 rounded-2xl bg-amber-50 border-2 border-amber-300 text-amber-900 flex items-start gap-3 shadow-2xs"
        >
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs sm:text-sm leading-relaxed space-y-1">
            <p className="font-bold">{isUrdu ? "اہم اطلاع" : "Notice"}</p>
            <p>{t.ocrNoticeUrdu}</p>
          </div>
        </div>
      )}

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-50 border border-red-200 text-red-800 text-xs sm:text-sm font-semibold flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {totalCount === 0 && (
        <div className="p-8 rounded-3xl bg-white border border-slate-200 text-center text-slate-500 text-sm">
          <FileText className="w-10 h-10 mx-auto text-slate-400 mb-2 opacity-50" />
          <p>{t.ocrEmptyExtracted}</p>
        </div>
      )}

      {/* 1. Extracted Observations */}
      {observations.length > 0 && (
        <section className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-base font-bold text-navy-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-600" />
              <span>{t.ocrObservationsTitle}</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800">
                {observations.length}
              </span>
            </h2>
          </div>

          <div className="space-y-3">
            {observations.map((obs, idx) => (
              <div
                key={obs.id}
                data-testid={`ocr-obs-item-${idx}`}
                className={`p-4 rounded-2xl border-2 transition-all space-y-2.5 ${
                  obs.confirmed
                    ? "bg-purple-50/40 border-purple-200"
                    : "bg-slate-50 border-slate-200 opacity-60"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      data-testid={`ocr-obs-toggle-${idx}`}
                      onClick={() =>
                        setObservations((prev) =>
                          prev.map((o) =>
                            o.id === obs.id ? { ...o, confirmed: !o.confirmed } : o
                          )
                        )
                      }
                      className={`px-2.5 py-1 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                        obs.confirmed
                          ? "bg-purple-600 text-white shadow-2xs"
                          : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                      }`}
                    >
                      {obs.confirmed ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{t.ocrConfirmedBadge}</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>{t.ocrConfirmItem}</span>
                        </>
                      )}
                    </button>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-100 text-purple-900 border border-purple-200">
                      {t.ocrBadge}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      data-testid={`ocr-obs-fix-${idx}`}
                      onClick={() =>
                        setObservations((prev) =>
                          prev.map((o) =>
                            o.id === obs.id ? { ...o, isEditing: !o.isEditing } : o
                          )
                        )
                      }
                      className="p-1.5 text-slate-600 hover:text-purple-800 rounded-lg hover:bg-purple-100/50 text-xs font-semibold flex items-center gap-1"
                      title={t.ocrFixBtn}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      <span>{t.ocrFixBtn}</span>
                    </button>
                    <button
                      type="button"
                      data-testid={`ocr-obs-remove-${idx}`}
                      onClick={() =>
                        setObservations((prev) => prev.filter((o) => o.id !== obs.id))
                      }
                      className="p-1.5 text-slate-400 hover:text-red-700 rounded-lg hover:bg-red-50 text-xs"
                      title={t.ocrRemoveBtn}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {obs.isEditing ? (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2">
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Type</label>
                      <input
                        type="text"
                        value={obs.type}
                        onChange={(e) =>
                          setObservations((prev) =>
                            prev.map((o) =>
                              o.id === obs.id ? { ...o, type: e.target.value } : o
                            )
                          )
                        }
                        className="w-full text-xs p-2 rounded-lg border border-slate-300"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Value</label>
                      <input
                        type="number"
                        step="any"
                        value={obs.value}
                        onChange={(e) =>
                          setObservations((prev) =>
                            prev.map((o) =>
                              o.id === obs.id ? { ...o, value: Number(e.target.value) } : o
                            )
                          )
                        }
                        className="w-full text-xs p-2 rounded-lg border border-slate-300"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Unit</label>
                      <input
                        type="text"
                        value={obs.unit}
                        onChange={(e) =>
                          setObservations((prev) =>
                            prev.map((o) =>
                              o.id === obs.id ? { ...o, unit: e.target.value } : o
                            )
                          )
                        }
                        className="w-full text-xs p-2 rounded-lg border border-slate-300"
                      />
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="font-bold text-sm text-navy-900 capitalize">
                      {obs.type.replace(/_/g, " ")}:{" "}
                      <bdi className="font-mono text-purple-900">
                        {obs.value} {obs.unit}
                      </bdi>
                    </div>
                  </div>
                )}

                {obs.evidence && (
                  <div className="text-[11px] text-slate-600 bg-white/80 p-2 rounded-xl border border-slate-200">
                    <span className="font-semibold text-slate-500 mr-1">{t.ocrEvidenceLabel}</span>
                    <span className="italic font-mono text-slate-700">&quot;{obs.evidence}&quot;</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 2. Extracted Medications */}
      {medications.length > 0 && (
        <section className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-base font-bold text-navy-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span>{t.ocrMedicationsTitle}</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800">
                {medications.length}
              </span>
            </h2>
          </div>

          <div className="space-y-3">
            {medications.map((med, idx) => (
              <div
                key={med.id}
                data-testid={`ocr-med-item-${idx}`}
                className={`p-4 rounded-2xl border-2 transition-all space-y-2.5 ${
                  med.confirmed
                    ? "bg-purple-50/40 border-purple-200"
                    : "bg-slate-50 border-slate-200 opacity-60"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      data-testid={`ocr-med-toggle-${idx}`}
                      onClick={() =>
                        setMedications((prev) =>
                          prev.map((m) =>
                            m.id === med.id ? { ...m, confirmed: !m.confirmed } : m
                          )
                        )
                      }
                      className={`px-2.5 py-1 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                        med.confirmed
                          ? "bg-purple-600 text-white shadow-2xs"
                          : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                      }`}
                    >
                      {med.confirmed ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{t.ocrConfirmedBadge}</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>{t.ocrConfirmItem}</span>
                        </>
                      )}
                    </button>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-100 text-purple-900 border border-purple-200">
                      {t.ocrBadge}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      data-testid={`ocr-med-fix-${idx}`}
                      onClick={() =>
                        setMedications((prev) =>
                          prev.map((m) =>
                            m.id === med.id ? { ...m, isEditing: !m.isEditing } : m
                          )
                        )
                      }
                      className="p-1.5 text-slate-600 hover:text-purple-800 rounded-lg hover:bg-purple-100/50 text-xs font-semibold flex items-center gap-1"
                      title={t.ocrFixBtn}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      <span>{t.ocrFixBtn}</span>
                    </button>
                    <button
                      type="button"
                      data-testid={`ocr-med-remove-${idx}`}
                      onClick={() =>
                        setMedications((prev) => prev.filter((m) => m.id !== med.id))
                      }
                      className="p-1.5 text-slate-400 hover:text-red-700 rounded-lg hover:bg-red-50 text-xs"
                      title={t.ocrRemoveBtn}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {med.isEditing ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Name</label>
                      <input
                        type="text"
                        value={med.name}
                        onChange={(e) =>
                          setMedications((prev) =>
                            prev.map((m) =>
                              m.id === med.id ? { ...m, name: e.target.value } : m
                            )
                          )
                        }
                        className="w-full text-xs p-2 rounded-lg border border-slate-300"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Dosage</label>
                      <input
                        type="text"
                        value={med.dosage}
                        onChange={(e) =>
                          setMedications((prev) =>
                            prev.map((m) =>
                              m.id === med.id ? { ...m, dosage: e.target.value } : m
                            )
                          )
                        }
                        className="w-full text-xs p-2 rounded-lg border border-slate-300"
                      />
                    </div>
                  </div>
                ) : (
                  <div>
                    <span className="font-bold text-sm text-navy-900 block">{med.name}</span>
                    <span className="text-xs text-slate-600 font-mono">
                      {med.dosage || (isUrdu ? "کوئی مقدار درج نہیں ہے" : "No dose specified")}
                    </span>
                  </div>
                )}

                {med.evidence && (
                  <div className="text-[11px] text-slate-600 bg-white/80 p-2 rounded-xl border border-slate-200">
                    <span className="font-semibold text-slate-500 mr-1">{t.ocrEvidenceLabel}</span>
                    <span className="italic font-mono text-slate-700">&quot;{med.evidence}&quot;</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 3. Extracted Allergies */}
      {allergies.length > 0 && (
        <section className="bg-white rounded-3xl p-5 sm:p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-base font-bold text-navy-900 flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-600" />
              <span>{t.ocrAllergiesTitle}</span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800">
                {allergies.length}
              </span>
            </h2>
          </div>

          <div className="space-y-3">
            {allergies.map((all, idx) => (
              <div
                key={all.id}
                data-testid={`ocr-all-item-${idx}`}
                className={`p-4 rounded-2xl border-2 transition-all space-y-2.5 ${
                  all.confirmed
                    ? "bg-purple-50/40 border-purple-200"
                    : "bg-slate-50 border-slate-200 opacity-60"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      data-testid={`ocr-all-toggle-${idx}`}
                      onClick={() =>
                        setAllergies((prev) =>
                          prev.map((a) =>
                            a.id === all.id ? { ...a, confirmed: !a.confirmed } : a
                          )
                        )
                      }
                      className={`px-2.5 py-1 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                        all.confirmed
                          ? "bg-purple-600 text-white shadow-2xs"
                          : "bg-slate-200 text-slate-700 hover:bg-slate-300"
                      }`}
                    >
                      {all.confirmed ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{t.ocrConfirmedBadge}</span>
                        </>
                      ) : (
                        <>
                          <Check className="w-3.5 h-3.5" />
                          <span>{t.ocrConfirmItem}</span>
                        </>
                      )}
                    </button>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-100 text-purple-900 border border-purple-200">
                      {t.ocrBadge}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      data-testid={`ocr-all-fix-${idx}`}
                      onClick={() =>
                        setAllergies((prev) =>
                          prev.map((a) =>
                            a.id === all.id ? { ...a, isEditing: !a.isEditing } : a
                          )
                        )
                      }
                      className="p-1.5 text-slate-600 hover:text-purple-800 rounded-lg hover:bg-purple-100/50 text-xs font-semibold flex items-center gap-1"
                      title={t.ocrFixBtn}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      <span>{t.ocrFixBtn}</span>
                    </button>
                    <button
                      type="button"
                      data-testid={`ocr-all-remove-${idx}`}
                      onClick={() =>
                        setAllergies((prev) => prev.filter((a) => a.id !== all.id))
                      }
                      className="p-1.5 text-slate-400 hover:text-red-700 rounded-lg hover:bg-red-50 text-xs"
                      title={t.ocrRemoveBtn}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {all.isEditing ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Substance</label>
                      <input
                        type="text"
                        value={all.substance}
                        onChange={(e) =>
                          setAllergies((prev) =>
                            prev.map((a) =>
                              a.id === all.id ? { ...a, substance: e.target.value } : a
                            )
                          )
                        }
                        className="w-full text-xs p-2 rounded-lg border border-slate-300"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 uppercase">Reaction</label>
                      <input
                        type="text"
                        value={all.reaction || ""}
                        onChange={(e) =>
                          setAllergies((prev) =>
                            prev.map((a) =>
                              a.id === all.id ? { ...a, reaction: e.target.value } : a
                            )
                          )
                        }
                        className="w-full text-xs p-2 rounded-lg border border-slate-300"
                      />
                    </div>
                  </div>
                ) : (
                  <div>
                    <span className="font-bold text-sm text-navy-900 block">{all.substance}</span>
                    {all.reaction && (
                      <span className="text-xs text-slate-600">Reaction: {all.reaction}</span>
                    )}
                  </div>
                )}

                {all.evidence && (
                  <div className="text-[11px] text-slate-600 bg-white/80 p-2 rounded-xl border border-slate-200">
                    <span className="font-semibold text-slate-500 mr-1">{t.ocrEvidenceLabel}</span>
                    <span className="italic font-mono text-slate-700">&quot;{all.evidence}&quot;</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Bottom Sticky Action Bar */}
      <div className="p-4 bg-white/95 backdrop-blur-md border border-slate-200 rounded-3xl shadow-xl flex flex-wrap items-center justify-between gap-3 sticky bottom-4 z-20">
        <div className="text-xs text-slate-600">
          <span className="font-bold text-navy-900">{confirmedCount}</span>{" "}
          <span>{isUrdu ? "اقدار تصدیق شدہ ہیں" : "values ready to save"}</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="ocr-cancel-btn"
            onClick={handleCancel}
            disabled={isSaving}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all"
          >
            {t.ocrCancelBtn}
          </button>
          <button
            type="button"
            data-testid="ocr-save-confirmed-btn"
            onClick={handleConfirmAndSave}
            disabled={isSaving || confirmedCount === 0}
            className="px-5 py-2.5 rounded-xl bg-purple-700 hover:bg-purple-800 disabled:bg-purple-300 text-white text-xs font-bold transition-all shadow-md flex items-center gap-2 cursor-pointer disabled:cursor-not-allowed"
          >
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span>{t.ocrConfirmSaveBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
