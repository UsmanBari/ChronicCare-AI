"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { AlertCircle, UserCheck, Home, ArrowLeft, Clock, ShieldCheck, Calendar, CheckCircle2, Pill, AlertTriangle, ShieldAlert, XCircle, Loader2 } from "lucide-react";
import { describeMedicationItem } from "../lib/presentation";
import { api } from "../lib/api";
import { ExplanationBox } from "./ExplanationBox";
import { TriageColourChip } from "./TriageColourChip";

export const RoutedToReviewScreen = () => {
  const { returnToHomeAndClearRun, appointment, setAppointment, isLiveMode, liveCheckinResult, checkIn, t, isUrdu, language } = useApp();
  const [requestedLocal, setRequestedLocal] = useState(appointment.status === "Requested");

  const liveApt = liveCheckinResult?.appointment;
  const [aptStatus, setAptStatus] = useState<string | null>(liveApt?.status || null);
  const [aptLoading, setAptLoading] = useState(false);
  const [aptMessage, setAptMessage] = useState<string | null>(null);

  const handleLiveBookApt = async () => {
    const aptId = liveApt?.id || (liveApt as any)?.appointment_id;
    if (!aptId) return;
    setAptLoading(true);
    try {
      const slot = liveApt?.slot_date || new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 16).replace("T", " ");
      await api.bookAppointment(aptId, slot);
      setAptStatus("booked");
      setAptMessage(isUrdu ? "ملاقات کامیابی سے طے ہو گئی ہے۔" : "Appointment successfully booked.");
    } catch (e: any) {
      setAptMessage(e?.message || "Failed to book appointment");
    } finally {
      setAptLoading(false);
    }
  };

  const handleLiveCancelApt = async () => {
    const aptId = liveApt?.id || (liveApt as any)?.appointment_id;
    if (!aptId) return;
    setAptLoading(true);
    try {
      await api.cancelAppointment(aptId);
      setAptStatus("cancelled");
      setAptMessage(isUrdu ? "ملاقات منسوخ کر دی گئی ہے۔" : "Appointment cancelled.");
    } catch (e: any) {
      setAptMessage(e?.message || "Failed to cancel appointment");
    } finally {
      setAptLoading(false);
    }
  };

  const handleRequestFollowUp = () => {
    setAppointment({
      isBooked: true,
      slot: "Next available — Thu, 10:30 AM",
      reason: "Patient-requested: flagged for clinical review",
      provider: "Dr. Sana Malik",
      status: "Requested",
      bookedAt: new Date().toISOString(),
    });
    setRequestedLocal(true);
  };

  const isLowConfidence =
    (isLiveMode && liveCheckinResult?.intakes?.[0]?.confidence_label?.toLowerCase() === "low") ||
    checkIn?.lowConfidence;

  const headline = isLiveMode ? t.routedToReviewHeadline : t.routedToReviewTitle;
  const description = isLiveMode ? t.routedToReviewExplanation : t.routedToReviewDesc;

  const medComparisons = liveCheckinResult?.reconciliation?.medication_comparisons || [];
  const medVerifications = liveCheckinResult?.verification?.medication_verifications || [];

  const allMeds: Array<{
    desc: ReturnType<typeof describeMedicationItem>;
    comparison: any;
    verification: any;
  }> = isLiveMode
    ? medComparisons.map((c: any) => {
        const v = medVerifications.find((ver: any) => ver.medication_name === c.medication_name);
        return {
          desc: describeMedicationItem(c, v, isUrdu),
          comparison: c,
          verification: v,
        };
      })
    : [];

  const isRomanUrdu = (language as string) === "roman_ur";
  const isLowGlucose = (() => {
    if (!liveCheckinResult) return false;
    const intakes = liveCheckinResult.intakes || [];
    for (const it of intakes) {
      const g = it?.extracted_data?.glucose ?? it?.readings?.glucose;
      if (typeof g === "number" && g < 70) return true;
      if (it?.extracted_data?.safety_guidance || it?.extracted_data?.rule_severe_low) return true;
    }
    const comps = liveCheckinResult.reconciliation?.observation_comparisons || [];
    for (const c of comps) {
      if (c.observation_type === "blood_glucose" && typeof c.value_b === "number" && c.value_b < 70) return true;
    }
    return false;
  })();

  const flaggedMeds = allMeds.filter((m) => !m.desc.isConfirmed);
  const confirmedMeds = allMeds.filter((m) => m.desc.isConfirmed);

  return (
    <div className="w-full max-w-lg mx-auto surface-raised rounded-3xl border border-slate-200 shadow-xl overflow-hidden animate-fadeIn text-center space-y-0" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Top Banner */}
      <div className="bg-gradient-to-b from-amber-50 to-white p-8 pb-4">
        <div className="w-20 h-20 rounded-full bg-amber-100 border-4 border-white shadow-md flex items-center justify-center mx-auto mb-4 text-amber-800 animate-fadeIn">
          <AlertCircle className="w-10 h-10" />
        </div>

        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-navy-800 mb-1.5 leading-snug">
          {headline}
        </h1>

        {isLowConfidence && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100 text-amber-900 text-xs font-semibold border border-amber-300 mt-2">
            <AlertCircle className="w-3.5 h-3.5 text-amber-700" />
            <span>{t.confidenceLowChip}</span>
          </div>
        )}
      </div>

      {/* Details Box */}
      <div className="p-6 sm:p-7 space-y-5">
        {/* Low Blood Sugar Safety Advice Banner */}
        {isLowGlucose && (
          <div data-testid="low-glucose-safety-banner" className="p-4 rounded-2xl bg-amber-50 border-2 border-amber-600 text-amber-950 text-sm font-bold flex items-center gap-3 animate-fadeIn shadow-xs text-left">
            <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
            <span dir="auto">
              {isUrdu
                ? "فوراً جلدی اثر کرنے والی میٹھی چیز لیں، جیسے پھلوں کا جوس یا گلوکوز، اور اگر علامات برقرار رہیں تو فوراً طبی مدد حاصل کریں۔"
                : isRomanUrdu
                ? "Foran jaldi asar karne wali meethi cheez lein, jaise phalon ka juice ya glucose, aur agar alamaat barqarar rahein to foran doctor se rabta karein."
                : "Take quick sugar such as fruit juice or glucose, and seek immediate medical attention if symptoms persist."}
            </span>
          </div>
        )}

        {/* Danger Wordgroup Emergency Advisory Banner */}
        {liveCheckinResult?.safety_note && (
          <div data-testid="danger-wordgroup-review-banner" className="p-4 rounded-2xl bg-amber-50 border-2 border-amber-600 text-amber-950 text-sm font-bold flex items-center gap-3 animate-fadeIn shadow-xs text-left">
            <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
            <span dir="auto">
              {liveCheckinResult.safety_note.includes("1122") ? (
                <>
                  {liveCheckinResult.safety_note.split("1122")[0]}
                  <a href="tel:1122" className="underline font-extrabold hover:text-amber-900">
                    1122
                  </a>
                  {liveCheckinResult.safety_note.split("1122")[1]}
                </>
              ) : (
                liveCheckinResult.safety_note
              )}
            </span>
          </div>
        )}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-sm text-slate-700 leading-relaxed text-left flex items-start gap-3.5">
          <UserCheck className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
          <p>{description}</p>
        </div>

        {/* Confirmed Medicines Section (Calm, separate line) */}
        {isLiveMode && confirmedMeds.length > 0 && (
          <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-300 text-left space-y-2 animate-fadeIn">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-950 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-700" />
              <span>{isUrdu ? "تصدیق شدہ ادویات:" : "Confirmed medicines:"}</span>
            </span>
            <div className="space-y-1.5">
              {confirmedMeds.map((m, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-xl bg-white border border-emerald-200 text-xs flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Pill className="w-3.5 h-3.5 text-emerald-700" />
                    <span className="font-bold text-navy-900">{m.desc.title}</span>
                    <span className="text-slate-600">{m.desc.recordText.replace(/^Record:\s*/i, "")}</span>
                  </div>
                  <span className="text-[11px] font-semibold text-emerald-800">
                    {m.desc.reason}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Flagged Medication Review Items */}
        {isLiveMode && flaggedMeds.length > 0 && (
          <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-300 text-left space-y-2.5 animate-fadeIn">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-950 block">
              {isUrdu ? "جائزے کے لیے بھیجی گئی ادویات:" : "Medications Flagged for Review:"}
            </span>
            <div className="space-y-2">
              {flaggedMeds.map((m, idx) => {
                const isHigh = m.desc.severity === "high";
                return (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border text-xs space-y-1 ${
                      isHigh
                        ? "bg-red-50 border-emergencyRed-400 text-emergencyRed-950 shadow-2xs ring-1 ring-emergencyRed-300"
                        : "bg-white border-amber-200 text-slate-800"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold flex items-center gap-1.5">
                        <Pill className={`w-3.5 h-3.5 ${isHigh ? "text-emergencyRed-700" : "text-amber-700"}`} />
                        {m.desc.title}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${
                          isHigh
                            ? "bg-emergencyRed-100 text-emergencyRed-900 border border-emergencyRed-300 font-extrabold"
                            : "bg-amber-100 text-amber-900 border border-amber-300"
                        }`}
                      >
                        {isHigh ? (
                          <AlertTriangle className="w-3 h-3 text-emergencyRed-700" />
                        ) : (
                          <ShieldAlert className="w-3 h-3 text-amber-700" />
                        )}
                        <span>{m.desc.severity.toUpperCase()}</span>
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-600 flex items-center justify-between">
                      <span>{m.desc.recordText}</span>
                      <span className="font-semibold text-navy-800">{m.desc.todayText}</span>
                    </div>
                    <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 text-[11px]">
                      <span className={`font-semibold ${isHigh ? "text-emergencyRed-900 font-bold" : "text-amber-900"}`}>
                        {m.desc.reason}
                      </span>
                      <span className="text-[10px] font-bold text-slate-500">
                        Needs clinician review
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 flex items-center justify-between text-sm text-amber-900">
          <span className="flex items-center gap-2 font-medium">
            <Clock className="w-4 h-4 text-amber-800" />
            <span>Triage Status</span>
            <span className="sr-only">Pending Provider Review</span>
          </span>
          <TriageColourChip
            level={liveCheckinResult?.triage_level || liveCheckinResult?.triage?.level || "review"}
            colour={liveCheckinResult?.triage_colour || liveCheckinResult?.triage?.triage_colour || "yellow"}
          />
        </div>

        {/* Guideline Explanation Box (flags on) */}
        <ExplanationBox />

        {/* Live Offered Appointment Card */}
        {isLiveMode && liveApt && (
          <div className="p-4 rounded-2xl bg-amber-50/90 border-2 border-amber-300 text-left space-y-2.5 animate-fadeIn" data-testid="triage-appointment-card">
            <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
              <Calendar className="w-5 h-5 text-amber-700" />
              <span>{isUrdu ? "تجویز کردہ ملاقات" : "Offered Appointment"}</span>
            </div>
            <p className="text-xs text-amber-800 leading-relaxed">
              {isUrdu
                ? "آپ کے معائنے کے نتائج کی بنیاد پر فالو اپ ملاقات تجویز کی گئی ہے۔"
                : "Based on your check-in review, a follow-up consultation has been offered."}
            </p>
            {liveApt?.specialty && (
              <div className="text-xs text-slate-700 bg-white/80 p-2.5 rounded-xl border border-amber-200 flex items-center justify-between">
                <span className="font-semibold">{t.appointmentSpecialty}:</span>
                <span className="font-bold text-navy-800">
                  {liveApt.specialty === "endocrinology"
                    ? t.specialtyEndocrinology
                    : liveApt.specialty === "cardiology_im"
                    ? t.specialtyCardiology
                    : liveApt.specialty === "internal_medicine"
                    ? t.specialtyInternalMedicine
                    : t.specialtyGeneral}
                </span>
              </div>
            )}
            {aptMessage && (
              <div className="p-2.5 rounded-xl bg-white/90 text-xs font-semibold text-navy-800 border border-amber-200">
                {aptMessage}
              </div>
            )}
            {aptStatus === "offered" ? (
              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleLiveBookApt}
                  disabled={aptLoading}
                  id="book-offered-appointment-btn"
                  className="flex-1 min-h-[40px] py-2 px-3 bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs rounded-xl shadow-xs transition-all flex items-center justify-center gap-1.5"
                >
                  {aptLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  <span>{t.bookAppointmentBtn}</span>
                </button>
                <button
                  type="button"
                  onClick={handleLiveCancelApt}
                  disabled={aptLoading}
                  id="cancel-offered-appointment-btn"
                  className="flex-1 min-h-[40px] py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all flex items-center justify-center gap-1.5"
                >
                  {aptLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-4 h-4" />}
                  <span>{t.cancelAppointmentBtn}</span>
                </button>
              </div>
            ) : aptStatus === "booked" ? (
              <div className="p-3 rounded-xl bg-emerald-100 text-emerald-900 text-xs font-bold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                <span>{isUrdu ? "ملاقات کامیابی سے طے ہو گئی ہے۔" : "Appointment confirmed with your clinic."}</span>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold flex items-center gap-2">
                <XCircle className="w-4 h-4 text-slate-500" />
                <span>{isUrdu ? "ملاقات منسوخ کر دی گئی ہے۔" : "Appointment was declined or cancelled."}</span>
              </div>
            )}
          </div>
        )}

        {/* Request Follow-Up Appointment CTA - Mock Mode Only */}
        {!isLiveMode && (
          requestedLocal ? (
            <div className="p-4 rounded-2xl bg-mutedGreen-50 border border-mutedGreen-800/30 text-mutedGreen-900 text-sm font-semibold flex items-center justify-center gap-2.5 shadow-2xs animate-fadeIn">
              <CheckCircle2 className="w-5 h-5 text-mutedGreen-800 shrink-0" />
              <span>Follow-up consultation requested (Thu, 10:30 AM). Forwarded to Dr. Sana Malik.</span>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleRequestFollowUp}
              id="request-followup-appointment-btn"
              className="w-full min-h-[48px] py-3.5 px-4 bg-amber-600 hover:bg-amber-700 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
            >
              <Calendar className="w-4 h-4" />
              <span>Request Follow-Up Appointment</span>
            </button>
          )
        )}

        {/* Return to Home button */}
        <button
          type="button"
          onClick={returnToHomeAndClearRun}
          id="routed-review-return-home-btn"
          className="w-full min-h-[48px] py-3.5 px-5 bg-navy-800 hover:bg-navy-900 active:scale-[0.99] text-white font-bold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2"
        >
          <Home className="w-4 h-4" />
          <span>{isUrdu ? "ڈیش بورڈ پر واپس جائیں" : "Return to Home"}</span>
        </button>
      </div>
    </div>
  );
};
