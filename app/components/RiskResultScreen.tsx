"use client";

import React, { useState } from "react";
import { useApp } from "../context/AppContext";
import { RiskBadge } from "./RiskBadge";
import {
  CheckCircle,
  HelpCircle,
  TrendingUp,
  ArrowRight,
  ChevronDown,
  Info,
  ShieldCheck,
  Activity,
  HeartPulse,
  FileCheck,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Pill,
  Calendar,
} from "lucide-react";
import { describeMedicationItem } from "../lib/presentation";
import { ExplanationBox } from "./ExplanationBox";
import { TriageColourChip } from "./TriageColourChip";
import { getReadingStatus } from "../lib/referenceRanges";

export const RiskResultScreen = () => {
  const { setScreen, returnToHomeAndClearRun, isLiveMode, liveCheckinResult, liveProfile, demoScenario, t, isUrdu, language } = useApp();
  const [showWhyPanel, setShowWhyPanel] = useState(false);

  // =========================================================================
  // LIVE MODE: "Check-in recorded and verified" summary (NEVER invented output)
  // =========================================================================
  if (isLiveMode) {
    const summary = liveCheckinResult?.reconciliation?.summary || {};
    const agreementCount = summary.agreement || 0;
    const missingCount = (summary.source_a_only || 0) + (summary.source_b_only || 0);
    const rawConfidence = liveCheckinResult?.intakes?.[0]?.confidence_label || liveCheckinResult?.intakes?.[0]?.confidence;
    const hasReadings = Boolean(liveCheckinResult?.intakes?.[0]?.readings && liveCheckinResult.intakes[0].readings.length > 0);
    const confidenceLabel = rawConfidence || (hasReadings ? null : "Low");

    const comparisons = liveCheckinResult?.reconciliation?.observation_comparisons || [];
    const medComparisons = liveCheckinResult?.reconciliation?.medication_comparisons || [];
    const hasRiskExplanation = Boolean(liveCheckinResult?.explanation);

    const reportedComparisons = comparisons.filter(
      (c: any) => c && c.value_b !== null && c.value_b !== undefined
    );

    const deduplicatedMeds = (() => {
      const seen = new Set<string>();
      const out: any[] = [];
      for (const m of medComparisons) {
        const nameKey = (m.medication_name || "").toLowerCase().trim();
        if (!nameKey || !seen.has(nameKey)) {
          seen.add(nameKey);
          out.push(m);
        }
      }
      return out;
    })();

    const readingsFromIntakes = (liveCheckinResult?.intakes || []).reduce((acc: number, it: any) => {
      const r = it?.readings;
      if (Array.isArray(r)) {
        return acc + r.filter((item: any) => item && item.value !== null && item.value !== undefined).length;
      }
      if (r && typeof r === "object") {
        return acc + Object.values(r).filter((v: any) => v !== null && v !== undefined).length;
      }
      return acc;
    }, 0);
    const readingsFromComparisons = reportedComparisons.length;
    const totalReadingsEntered = Math.max(readingsFromIntakes, readingsFromComparisons);
    const hasNoReadings = totalReadingsEntered === 0;

    const activeLang = liveProfile?.language || (isUrdu ? "ur" : "en");
    const isRomanUrdu = (activeLang as string) === "roman_ur";
    const isLowGlucose = (() => {
      if (!liveCheckinResult) return false;
      const intakes = liveCheckinResult.intakes || [];
      for (const it of intakes) {
        const g = it?.extracted_data?.glucose ?? it?.readings?.glucose;
        if (typeof g === "number" && g < 70) return true;
        if (it?.extracted_data?.safety_guidance || it?.extracted_data?.rule_severe_low) return true;
      }
      for (const c of reportedComparisons) {
        if (c.observation_type === "blood_glucose" && typeof c.value_b === "number" && c.value_b < 70) return true;
      }
      return false;
    })();
    const noReadingsText = activeLang === "ur"
      ? "آج کوئی ریڈنگ درج نہیں کی گئی"
      : activeLang === "roman_ur"
      ? "Aaj koi reading darj nahi ki gayi"
      : t.noReadingsEntered;

    return (
      <div className="w-full max-w-lg mx-auto glass-raised rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
        {/* Live Header Banner */}
        <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />
          <div className="w-14 h-14 rounded-2xl bg-teal-500/20 border border-teal-400/40 flex items-center justify-center mx-auto mb-3 shadow-inner text-teal-300">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1.5">
            {t.checkinSummaryTitle}
          </h1>
          <p className="text-sm text-slate-200 max-w-sm mx-auto leading-relaxed mb-3">
            {t.checkinSummarySubtitle}
          </p>

          {/* Triage Status Colour Chip (Proposal Section 15 single source of truth) */}
          <div className="flex flex-col items-center justify-center gap-2 pt-1 pb-1">
            <TriageColourChip
              level={liveCheckinResult?.provider_level || liveCheckinResult?.triage_level || liveCheckinResult?.triage?.level}
              colour={liveCheckinResult?.provider_level ? undefined : (liveCheckinResult?.triage_colour || liveCheckinResult?.triage?.triage_colour)}
            />
            {liveCheckinResult?.triage?.patient_reason_key === "trend_rising" && (
              <p className="text-xs text-amber-900 bg-amber-100/90 px-3.5 py-1.5 rounded-xl border border-amber-300/80 text-center max-w-sm shadow-xs font-medium">
                {t.patientReasonTrendRising}
              </p>
            )}
          </div>
        </div>

        <div className="p-6 sm:p-7 space-y-5">
          {/* Provider Review Card (F6 / Proposal UC-15) */}
          {(liveCheckinResult?.provider_level || liveCheckinResult?.provider_decision) && (
            <div
              data-testid="provider-reviewed-card"
              className="p-4 sm:p-5 rounded-2xl bg-teal-50/90 border-2 border-teal-600/60 shadow-sm space-y-2.5 animate-fadeIn text-left"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-teal-800 shrink-0" />
                  <span className="text-sm font-bold text-teal-950">
                    {t.reviewedByCareTeam}
                  </span>
                </div>
                {liveCheckinResult.provider_level && (
                  <TriageColourChip
                    level={liveCheckinResult.provider_level}
                  />
                )}
              </div>
              <p className="text-xs text-teal-900 font-medium">
                {liveCheckinResult.provider_decision === "approved"
                  ? t.approvedAsRecommended
                  : liveCheckinResult.provider_decision === "adjusted" && liveCheckinResult.provider_level
                  ? `${t.adjustModalTitle}: ${liveCheckinResult.provider_level.toUpperCase()}`
                  : t.approvedAsRecommended}
              </p>
              {liveCheckinResult.patient_message && (
                <div className="p-3 rounded-xl bg-white/90 border border-teal-200 text-xs text-navy-900 leading-relaxed">
                  <span className="font-semibold block text-[11px] text-teal-800 uppercase tracking-wider mb-1">
                    {t.adjustMessageLabel}
                  </span>
                  <p>{liveCheckinResult.patient_message}</p>
                </div>
              )}
            </div>
          )}

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

          {/* Summary Metric Cards */}
          {hasNoReadings ? (
            <div
              className="p-4 sm:p-5 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-1"
              data-testid="no-readings-summary"
            >
              <span className="text-sm sm:text-base font-semibold text-slate-700 block">
                {noReadingsText}
              </span>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-4 rounded-2xl bg-teal-50/80 border border-teal-200 text-center space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-teal-900 block">
                  {t.agreementsCountLabel}
                </span>
                <div className="text-2xl font-bold text-teal-900 font-mono">
                  {agreementCount}
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 block">
                  {t.missingCountLabel}
                </span>
                <div className="text-2xl font-bold text-slate-800 font-mono">
                  {missingCount}
                </div>
              </div>

              {confidenceLabel && (
                <div className="p-4 rounded-2xl bg-mutedGreen-50 border border-mutedGreen-200 text-center space-y-1">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-mutedGreen-900 block">
                    {t.confidenceLabel}
                  </span>
                  <div className="text-2xl font-bold text-mutedGreen-900 capitalize">
                    {confidenceLabel}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Patient Risk Estimates (Proposal Section 15, Clinician Approved 8 Nov, behind RISK_PATIENT_VISIBLE) */}
          {liveCheckinResult?.risk_patient && liveCheckinResult.risk_patient.length > 0 && (
            <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-xs space-y-3" data-testid="patient-risk-estimates-card">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
                <span className="font-heading font-bold text-xs uppercase tracking-wider text-slate-700">
                  {t.patientRiskEstimatesTitle}
                </span>
              </div>
              <div className="space-y-2.5">
                {liveCheckinResult.risk_patient.map((r, idx) => {
                  const b = (r.band || "").toLowerCase();
                  let bandColor = "bg-teal-50 text-teal-800 border-teal-200";
                  let bandLabel = t.riskBandLow;
                  if (b === "high") {
                    bandColor = "bg-indigo-50 text-indigo-900 border-indigo-200 font-bold";
                    bandLabel = t.riskBandHigh;
                  } else if (b === "moderate" || b === "medium") {
                    bandColor = "bg-amber-50 text-amber-900 border-amber-200 font-semibold";
                    bandLabel = t.riskBandMedium;
                  } else if (b === "not_enough_information") {
                    bandColor = "bg-slate-50 text-slate-700 border-slate-200";
                    bandLabel = t.riskMissingDataTitle;
                  }

                  const msg = (t as any)[r.message_key] || (b === "high" ? t.risk_chd_high : (b === "moderate" ? t.risk_chd_moderate : t.risk_chd_low));

                  return (
                    <div key={idx} className="p-3 rounded-xl bg-slate-50/70 border border-slate-100 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] border ${bandColor}`}>
                          {bandLabel}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {msg}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Plain words comparison details */}
          {(reportedComparisons.length > 0 || deduplicatedMeds.length > 0) && (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-left space-y-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block">
                {isUrdu ? "موازنہ کی گئی پیمائشیں اور ادویات:" : "Compared Readings & Medications:"}
              </span>
              <ul className="space-y-2 text-xs text-slate-600">
                {reportedComparisons.map((c: any, idx: number) => {
                  const type = c.observation_type ? c.observation_type.replace(/_/g, " ").replace(/\b\w/g, (ch: string) => ch.toUpperCase()) : "Observation";
                  const valToday = `${c.value_b} ${c.unit_b || ""}`.trim();
                  let recordDesc = "";
                  if (c.value_a !== null && c.value_a !== undefined) {
                    const dateStr = c.date_a ? ` (${new Date(c.date_a).toLocaleDateString()})` : "";
                    recordDesc = ` • Record: ${c.value_a} ${c.unit_a || ""}${dateStr}`;
                  }
                  let statusDesc = "Verified against baseline";
                  if (c.status === "agreement" || c.status === "agree") statusDesc = isUrdu ? "پچھلے ریکارڈ کے مطابق ہے" : "Matches saved record";
                  else if (c.status === "source_b_only") statusDesc = isUrdu ? "آج درج کیا گیا (کوئی پچھلا ریکارڈ موجود نہیں)" : "Reported today (no prior record)";
                  else if (c.status === "conflict") statusDesc = isUrdu ? "پچھلے ریکارڈ سے مختلف ہے" : "Differs from saved record";
                  const readingStatus = getReadingStatus(c.observation_type, c.value_b, language, c.unit_b);
                  return (
                    <li key={idx} className="flex items-center justify-between py-1.5 border-b border-slate-200/60 last:border-none flex-wrap gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-slate-800">{type} ({valToday}{recordDesc})</span>
                        {readingStatus.status !== "unspecified" && (
                          <span
                            data-testid={`result-reading-status-${idx}`}
                            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${readingStatus.badgeClass}`}
                          >
                            {readingStatus.label}
                          </span>
                        )}
                      </div>
                      <span className="text-slate-500 font-medium">{statusDesc}</span>
                    </li>
                  );
                })}
                {deduplicatedMeds.map((m: any, idx: number) => {
                  const medVerifs = liveCheckinResult?.verification?.medication_verifications || [];
                  const v = medVerifs.find((ver: any) => ver.medication_name === m.medication_name);
                  const medItem = describeMedicationItem(m, v);
                  const isHigh = medItem.severity === "high";
                  return (
                    <li key={`med-${idx}`} className="py-1.5 border-b border-slate-200/60 last:border-none space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-800 flex items-center gap-1.5">
                          <Pill className="w-3.5 h-3.5 text-teal-700" />
                          {medItem.title}
                        </span>
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                          isHigh ? "bg-red-100 text-red-900 border border-red-300" : "bg-slate-100 text-slate-700"
                        }`}>
                          {medItem.todayText}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-500">
                        <span>{medItem.recordText}</span>
                        <span className="font-medium text-slate-600">{medItem.reason}</span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* Guideline Explanation Box (flags on) */}
          <ExplanationBox />

          {/* Appointment Workflow Action Card (Proposal Section 15 & Section 37) */}
          {(() => {
            const apt = liveCheckinResult?.appointment;
            const level = liveCheckinResult?.triage_level || liveCheckinResult?.triage?.level;
            const isYellow = level === "review";
            const isRed = level === "urgent" || level === "emergency";

            if (isYellow) {
              return (
                <div className="p-4 rounded-2xl bg-amber-50/90 border-2 border-amber-300 text-left space-y-2.5 animate-fadeIn" data-testid="triage-appointment-card">
                  <div className="flex items-center gap-2 text-amber-900 font-bold text-sm">
                    <Calendar className="w-5 h-5 text-amber-700" />
                    <span>{t.bookRoutineAppointmentCard}</span>
                  </div>
                  <p className="text-xs text-amber-800 leading-relaxed">
                    {t.bookRoutineAppointmentDesc}
                  </p>
                  {apt?.specialty && (
                    <div className="text-xs text-slate-700 bg-white/80 p-2.5 rounded-xl border border-amber-200 flex items-center justify-between">
                      <span className="font-semibold">{t.appointmentSpecialty}:</span>
                      <span className="font-bold text-navy-800">
                        {apt.specialty === "endocrinology" ? t.specialtyEndocrinology : apt.specialty === "cardiology_im" ? t.specialtyCardiology : apt.specialty === "internal_medicine" ? t.specialtyInternalMedicine : t.specialtyGeneral}
                      </span>
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => setScreen("appointments")}
                    id="book-routine-appointment-btn"
                    className="w-full min-h-[42px] py-2.5 px-4 bg-amber-700 hover:bg-amber-800 text-white font-bold text-xs rounded-xl shadow-xs transition-all flex items-center justify-center gap-2"
                  >
                    <Calendar className="w-4 h-4" />
                    <span>{t.bookAppointmentBtn}</span>
                  </button>
                </div>
              );
            }

            if (isRed) {
              return (
                <div className="p-4 rounded-2xl bg-red-50/90 border-2 border-red-300 text-left space-y-2.5 animate-fadeIn" data-testid="triage-appointment-card">
                  <div className="flex items-center gap-2 text-red-900 font-bold text-sm">
                    <AlertCircle className="w-5 h-5 text-red-700" />
                    <span>{t.careTeamAlertedCard}</span>
                  </div>
                  <p className="text-xs text-red-800 leading-relaxed">
                    {t.careTeamAlertedDesc}
                  </p>
                  <div className="text-xs text-slate-700 bg-white/80 p-2.5 rounded-xl border border-red-200 space-y-1">
                    {apt?.provider_id && (
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">{t.appointmentWith}:</span>
                        <span className="font-bold text-navy-800 font-mono">{apt.provider_id}</span>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">{isUrdu ? "وقت اور تاریخ" : "Slot"}:</span>
                      <span className="font-bold text-navy-800">{apt?.slot_date || apt?.slot || "Today"}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setScreen("appointments")}
                    id="view-urgent-appointment-btn"
                    className="w-full min-h-[42px] py-2.5 px-4 bg-red-700 hover:bg-red-800 text-white font-bold text-xs rounded-xl shadow-xs transition-all flex items-center justify-center gap-2"
                  >
                    <Calendar className="w-4 h-4" />
                    <span>{t.myAppointmentsTitle}</span>
                  </button>
                </div>
              );
            }

            return null;
          })()}

          {/* Release scope notice when automated risk scoring is omitted/disabled */}
          {!hasRiskExplanation && (
            <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-200/70 flex items-start gap-3 text-xs text-amber-900">
              <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <p className="leading-relaxed">{t.riskScoringOmittedNote}</p>
            </div>
          )}

          {/* Navigation to Trends and Return Home */}
          <div className="pt-2 space-y-2.5">
            <button
              type="button"
              onClick={() => setScreen("trends")}
              id="view-trends-btn"
              className="w-full min-h-[48px] py-3.5 px-5 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 shadow-teal-700/20"
            >
              <TrendingUp className="w-4 h-4" />
              <span>{t.viewTrendsBtn}</span>
              <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
            </button>

            <button
              type="button"
              onClick={returnToHomeAndClearRun}
              id="result-back-home-btn"
              className="w-full min-h-[44px] py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition-all flex items-center justify-center gap-2"
            >
              <span>{t.finishBtn}</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // MOCK MODE: Original Mock Risk Badge and Explanations
  // =========================================================================
  const contributingFactors = [
    t.factor1,
    t.factor2,
    t.factor3,
    t.factor4,
  ];

  return (
    <div className="w-full max-w-lg mx-auto glass-raised rounded-3xl border border-slate-200/90 shadow-2xl overflow-hidden animate-fadeIn" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Header Banner */}
      <div className="bg-gradient-to-br from-navy-800 via-navy-800 to-teal-800 p-6 sm:p-7 text-white text-center relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-36 h-36 bg-teal-400/15 rounded-full blur-2xl pointer-events-none" />
        <div className="flex items-center justify-center gap-2 mb-1.5">
          <span className="text-xs font-bold uppercase tracking-wider text-teal-300">
            {isUrdu ? "طبی جائزہ و تخمینہ" : "Personalized Risk Assessment"}
          </span>
          <span className="px-2 py-0.5 rounded-full bg-teal-500/25 text-teal-200 text-[10px] font-bold uppercase tracking-wider border border-teal-400/30">
            {t.demoSimulationBadge}
          </span>
        </div>
        <h1 className="font-heading text-2xl sm:text-[26px] font-bold text-white mb-1.5">
          {isUrdu ? "آپ کے روزانہ نتائج" : "Daily Health Analysis"}
        </h1>
        <p className="text-sm text-slate-200 max-w-xs mx-auto leading-relaxed">
          {t.riskDescription}
        </p>
      </div>

      <div className="p-6 sm:p-7 space-y-6">
        {/* Risk Badge Display */}
        <div className="p-6 rounded-2xl bg-mutedGreen-50 border border-mutedGreen-800/20 text-center space-y-3.5">
          <div className="flex justify-center">
            <RiskBadge riskLevel="low" size="lg" />
          </div>

          <p className="text-base font-semibold text-mutedGreen-800">
            {t.riskSupportingText}
          </p>

          <p className="text-sm text-slate-600 leading-relaxed max-w-sm mx-auto">
            {isUrdu
              ? "آپ کے درج کردہ علامات اور ادویات کی پابندی سے ظاہر ہوتا ہے کہ آپ کی حالت معمول کے مطابق مستحکم ہے۔"
              : "Your self-reported symptoms, consistent medication routine, and stable baseline vitals show no current indicators of escalation."}
          </p>
        </div>

        {/* Guideline Explanation Box (flags on) */}
        {liveCheckinResult?.explanation && (
          <ExplanationBox />
        )}

        {/* Rule R8: No-readings summary card */}
        {demoScenario === "no_readings" && (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2 text-left" data-testid="no-readings-summary">
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800">
              {isUrdu ? "آج کوئی ریڈنگ درج نہیں کی گئی" : "No readings entered today"}
            </span>
            <p className="text-xs text-slate-600 leading-relaxed">
              {isUrdu ? "آج کوئی ریڈنگ درج نہیں کی گئی — روٹین مانیٹرنگ جاری ہے۔" : "Routine self-monitoring. Patient did not enter a blood sugar reading today; continuing standard routine monitoring."}
            </p>
          </div>
        )}

        {/* Patient Risk Estimates (Proposal Section 15) */}
        {liveCheckinResult?.risk_patient && liveCheckinResult.risk_patient.length > 0 && (
          <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-xs space-y-3" data-testid="patient-risk-estimates-card">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
              <span className="font-heading font-bold text-xs uppercase tracking-wider text-slate-700">
                {t.patientRiskEstimatesTitle}
              </span>
            </div>
            <div className="space-y-2.5">
              {liveCheckinResult.risk_patient.map((r, idx) => {
                const b = (r.band || "").toLowerCase();
                let bandColor = "bg-teal-50 text-teal-800 border-teal-200";
                let bandLabel = t.riskBandLow;
                if (b === "high") {
                  bandColor = "bg-indigo-50 text-indigo-900 border-indigo-200 font-bold";
                  bandLabel = t.riskBandHigh;
                } else if (b === "moderate" || b === "medium") {
                  bandColor = "bg-amber-50 text-amber-900 border-amber-200 font-semibold";
                  bandLabel = t.riskBandMedium;
                }
                const msg = (t as any)[r.message_key] || (b === "high" ? t.risk_chd_high : (b === "moderate" ? t.risk_chd_moderate : t.risk_chd_low));
                return (
                  <div key={idx} className="p-3 rounded-xl bg-slate-50/70 border border-slate-100 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] border ${bandColor}`}>
                        {bandLabel}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {msg}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Toggle to view Why / Contributing Factors */}
        {!showWhyPanel ? (
          <button
            type="button"
            onClick={() => setShowWhyPanel(true)}
            id="see-why-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-slate-100 hover:bg-slate-200 text-navy-800 font-semibold text-sm rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-2"
          >
            <HelpCircle className="w-4 h-4 text-teal-700" />
            <span>{t.seeWhyBtn}</span>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </button>
        ) : (
          <div className="p-5 sm:p-6 rounded-2xl bg-slate-50/90 border border-slate-200 space-y-4 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-slate-200/80 pb-3">
              <h2 className="font-heading text-base sm:text-lg font-bold text-navy-800 flex items-center gap-2">
                <Activity className="w-5 h-5 text-teal-700" />
                <span>{t.contributingFactorsTitle}</span>
              </h2>
            </div>

            {/* MANDATORY SAFEGUARD LABEL */}
            <div className="p-3 rounded-xl bg-teal-50 border border-teal-200 flex items-start gap-2.5 text-xs text-teal-900 leading-snug">
              <Info className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
              <span className="font-medium">
                {t.shapDisclaimer}
              </span>
            </div>

            {/* Contributing factors list */}
            <ul className="space-y-3 pt-1 text-sm text-slate-700">
              {contributingFactors.map((factor, index) => (
                <li key={index} className="flex items-start gap-2.5">
                  <CheckCircle className="w-4 h-4 text-mutedGreen-800 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{factor}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Proceed to Trend Screen or Return Home */}
        <div className="pt-2 space-y-2.5">
          <button
            type="button"
            onClick={() => setScreen("trends")}
            id="view-trends-btn"
            className="w-full min-h-[48px] py-3.5 px-5 bg-teal-700 hover:bg-teal-600 active:scale-[0.99] text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 shadow-teal-700/20"
          >
            <TrendingUp className="w-4 h-4" />
            <span>{t.viewTrendsBtn}</span>
            <ArrowRight className={`w-4 h-4 ${isUrdu ? "rotate-180" : ""}`} />
          </button>

          <button
            type="button"
            onClick={returnToHomeAndClearRun}
            id="mock-result-back-home-btn"
            className="w-full min-h-[44px] py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition-all flex items-center justify-center gap-2"
          >
            <span>{t.finishBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
