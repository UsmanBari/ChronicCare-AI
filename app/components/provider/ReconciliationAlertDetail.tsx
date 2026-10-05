"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "../../context/AppContext";
import {
  AlertTriangle,
  FileText,
  Hospital,
  ShieldAlert,
  Calendar,
  CheckCircle2,
  ArrowLeft,
  Info,
  ShieldCheck,
  AlertOctagon,
  Scale,
  Sparkles,
  Loader2,
  Pill,
} from "lucide-react";
import { api, ApiError, ReviewDetailResponse } from "../../lib/api";
import {
  describeSide,
  describeReviewReason,
  describeMedicationItem,
  describeProtocol,
  describeTriageLevel,
} from "../../lib/presentation";

export const ReconciliationAlertDetail = () => {
  const {
    setProviderScreen,
    resolveCase,
    resolvedCases,
    selectedPatient,
    isLiveMode,
    demoScenario,
    t,
    isUrdu,
  } = useApp();

  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [actionNote, setActionNote] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Live state
  const [liveDetail, setLiveDetail] = useState<ReviewDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(isLiveMode);

  useEffect(() => {
    if (!isLiveMode || !selectedPatient) return;
    let isMounted = true;
    api
      .getProviderReviewDetail(selectedPatient)
      .then((detail) => {
        if (isMounted) {
          setLiveDetail(detail);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setIsLoading(false);
          // If checkin ID not found directly, keep default display
        }
      });
    return () => {
      isMounted = false;
    };
  }, [isLiveMode, selectedPatient]);

  const isResolved =
    resolvedCases.includes(selectedPatient || "Ali Khan") ||
    liveDetail?.review_status === "resolved";

  const handleAction = async (actionType: "resolve" | "escalate" | "acknowledge") => {
    setError(null);

    if (actionType !== "acknowledge" && !actionNote.trim()) {
      setError("Please enter a short review note before taking action.");
      return;
    }

    if (isLiveMode && selectedPatient) {
      setIsSubmitting(true);
      try {
        const updated = await api.postProviderReviewAction(
          selectedPatient,
          actionType,
          actionNote.trim() || undefined
        );
        setLiveDetail(updated);
        if (actionType === "resolve") {
          resolveCase(selectedPatient);
          setToastMessage(t.caseResolvedToast || "Case marked as resolved.");
        } else if (actionType === "escalate") {
          setToastMessage("Case escalated to care team.");
        } else {
          setToastMessage(t.caseAcknowledgedToast || "Case acknowledged.");
        }
        setActionNote("");
        setTimeout(() => {
          setToastMessage(null);
          setProviderScreen("review_queue");
        }, 1200);
      } catch (err: any) {
        if (err instanceof ApiError) {
          setError(err.getFriendlyMessage(isUrdu));
        } else {
          setError(err?.message || "Failed to submit action");
        }
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    // Mock mode resolution
    if (actionType === "resolve") {
      resolveCase(selectedPatient || "Ali Khan");
      setToastMessage(t.caseResolvedToast);
    } else if (actionType === "escalate") {
      setToastMessage("Case escalated to specialist team.");
    } else {
      setToastMessage(t.caseAcknowledgedToast);
    }
    setTimeout(() => {
      setToastMessage(null);
      setProviderScreen("review_queue");
    }, 1200);
  };

  // Live comparison resolution
  let patientDisplayName = liveDetail?.patient_display || (selectedPatient && selectedPatient.includes("@") ? selectedPatient : "Ali Khan (PT-04821)");
  let obsComparison = liveDetail?.reconciliation?.observation_comparisons?.[0];
  let obsVerification = liveDetail?.verification?.observation_verifications?.[0];

  const sourceAType = obsComparison?.source_a || obsVerification?.source_a || "local";
  const sourceBType = obsComparison?.source_b || obsVerification?.source_b || "local";
  const trustLevelA = obsVerification?.trust_level_a || "low";
  const trustLevelB = obsVerification?.trust_level_b || "low";
  const mode = liveDetail?.mode || "isolated";

  let sideALabel = isLiveMode
    ? describeSide("a", sourceAType, trustLevelA, mode)
    : "Source A: Patient Telemetry";
  let sideBLabel = isLiveMode
    ? describeSide("b", sourceBType, trustLevelB, mode)
    : "Source B: Hospital EHR";

  let sourceAVal = obsComparison?.value_a !== null && obsComparison?.value_a !== undefined
    ? `${obsComparison.value_a} ${obsComparison.unit_a || ""}`
    : "180 mg/dL";
  let sourceBVal = obsComparison?.value_b !== null && obsComparison?.value_b !== undefined
    ? `${obsComparison.value_b} ${obsComparison.unit_b || ""}`
    : "140 mg/dL";
  let comparisonTitle = obsComparison?.observation_type
    ? `${obsComparison.observation_type.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())} Review`
    : "Clinical Telemetry Review";

  const isEmergencyItem = liveDetail?.emergency === true;

  // Format trigger category in plain words
  const triggerCategoryPlain = liveDetail?.trigger_category
    ? liveDetail.trigger_category.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
    : "Clinical Emergency Escalation";

  // Format trigger reading
  let triggerReadingText: string | null = null;
  if (liveDetail?.trigger_reading) {
    if (typeof liveDetail.trigger_reading === "string") {
      triggerReadingText = liveDetail.trigger_reading;
    } else if (typeof liveDetail.trigger_reading === "object") {
      const tr = liveDetail.trigger_reading as any;
      if (tr.systolic && tr.diastolic) {
        triggerReadingText = `Blood pressure ${tr.systolic}/${tr.diastolic} ${tr.unit || "mmHg"}, at or above the crisis limit`;
      } else if (tr.reading) {
        triggerReadingText = String(tr.reading);
      } else {
        triggerReadingText = JSON.stringify(tr);
      }
    }
  }

  const formatReadings = (val: any): string => {
    if (!val) return "Not recorded";
    if (typeof val === "string") return val;
    if (Array.isArray(val)) {
      return val.map((item) => formatReadings(item)).join(", ");
    }
    if (typeof val === "object") {
      if (val.systolic !== undefined && val.diastolic !== undefined) {
        return `${val.systolic}/${val.diastolic} ${val.unit || "mmHg"}`;
      }
      if (val.value !== undefined) {
        return `${val.value} ${val.unit || ""}`.trim();
      }
      if (val.reading !== undefined) {
        return String(val.reading);
      }
      return Object.entries(val)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
    }
    return String(val);
  };

  const formatAgeBand = (band?: string | null): string => {
    if (!band) return "Adult";
    const norm = band.toLowerCase().trim();
    if (norm === "65_plus" || norm === "65+" || norm.includes("65")) return "Age 65 and over";
    if (norm === "18_64" || norm === "18-64" || norm.includes("18")) return "Adult 18 to 64";
    return band;
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6 animate-fadeIn py-2" dir={isUrdu ? "rtl" : "ltr"}>
      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-4 rounded-2xl bg-mutedGreen-100 border border-mutedGreen-800 text-mutedGreen-900 text-sm font-bold shadow-lg flex items-center justify-between animate-slideUp">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-mutedGreen-800 shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}

      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setProviderScreen("review_queue")}
            id="reconciliation-back-btn"
            className="w-11 h-11 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 flex items-center justify-center transition-colors shadow-xs"
          >
            <ArrowLeft className={`w-5 h-5 ${isUrdu ? "rotate-180" : ""}`} />
          </button>
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold text-navy-800">
              {isEmergencyItem ? "Emergency Clinical Review" : t.alertDetailsTitle}
            </h1>
            <span className="text-xs font-semibold text-slate-500">
              Patient: {patientDisplayName} • Mode: {liveDetail?.mode || "FHIR Live"}
            </span>
          </div>
        </div>

        {isResolved ? (
          <span className="px-3.5 py-1.5 rounded-full bg-mutedGreen-100 text-mutedGreen-800 text-xs font-bold inline-flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" /> Case Resolved
          </span>
        ) : (
          <span className={`px-3.5 py-1.5 rounded-full text-xs font-bold inline-flex items-center gap-1.5 border ${
            isEmergencyItem
              ? "bg-emergencyRed-100 text-emergencyRed-900 border-emergencyRed-300"
              : "bg-amber-100 text-amber-900 border-amber-300"
          }`}>
            {isEmergencyItem ? <AlertOctagon className="w-4 h-4 text-emergencyRed-800" /> : <ShieldAlert className="w-4 h-4 text-amber-800" />}
            {isEmergencyItem ? "Emergency Action Required" : "Action Required"}
          </span>
        )}
      </div>

      {error && (
        <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Triage Card (Rendered at top for items with triage) */}
      {liveDetail?.triage && (
        <div className="surface-card rounded-3xl p-6 sm:p-7 space-y-5 border-2 border-teal-600/40 bg-white shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3.5">
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-5 h-5 text-teal-700 shrink-0" />
              <div>
                <h2 className="font-heading font-bold text-lg text-navy-900">
                  Triage: {describeProtocol(liveDetail.triage.protocol)}
                </h2>
                <span className="text-xs text-slate-500 font-medium">
                  Protocol: {liveDetail.triage.protocol} • Age Band: {formatAgeBand(liveDetail.triage.age_band)}
                </span>
              </div>
            </div>

            {/* Triage Level Tag */}
            {(() => {
              const triageLvl = (liveDetail.triage.level || "routine").toLowerCase();
              const triageDesc = describeTriageLevel(triageLvl, liveDetail.triage.guidance);
              return (
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider inline-flex items-center gap-1.5 self-start sm:self-auto ${
                    triageLvl === "emergency"
                      ? "bg-emergencyRed-100 text-emergencyRed-900 border border-emergencyRed-300"
                      : triageLvl === "urgent"
                      ? "bg-amber-100 text-amber-950 border border-amber-300"
                      : triageLvl === "review"
                      ? "bg-teal-100 text-teal-900 border border-teal-300"
                      : "bg-slate-100 text-slate-800 border border-slate-200"
                  }`}
                >
                  {triageLvl === "emergency" ? (
                    <AlertOctagon className="w-3.5 h-3.5 text-emergencyRed-700" />
                  ) : triageLvl === "urgent" ? (
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                  ) : (
                    <Info className="w-3.5 h-3.5 text-teal-700" />
                  )}
                  <span>{triageDesc.label}</span>
                </span>
              );
            })()}
          </div>

          <div className="space-y-4 text-xs sm:text-sm">
            {/* Reasons */}
            {liveDetail.triage.reasons && Array.isArray(liveDetail.triage.reasons) && liveDetail.triage.reasons.length > 0 && (
              <div className="space-y-1.5">
                <span className="font-bold text-navy-800 uppercase tracking-wider text-xs block">
                  Triage Rationale & Reasons:
                </span>
                <ul className="space-y-1 list-disc list-inside text-slate-700 pl-1">
                  {liveDetail.triage.reasons.map((reason: string, rIdx: number) => (
                    <li key={rIdx} className="leading-relaxed">
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Contributing Factors (only when present and non-empty) */}
            {liveDetail.triage.factors && Array.isArray(liveDetail.triage.factors) && liveDetail.triage.factors.length > 0 && (
              <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200 text-amber-950 font-semibold text-xs">
                Possible contributing factors: {liveDetail.triage.factors.join(", ")}
              </div>
            )}

            {/* Telemetry Readings & Recheck Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Initial Reading
                </span>
                <div className="text-base font-bold text-navy-900 font-mono">
                  {formatReadings(liveDetail.triage.readings)}
                </div>
              </div>

              {liveDetail.triage.recheck && (
                <div className="p-3.5 rounded-xl bg-teal-50/70 border border-teal-200 space-y-1">
                  <span className="text-[11px] font-bold text-teal-800 uppercase tracking-wider block">
                    Re-measure After Rest
                  </span>
                  <div className="text-base font-bold text-teal-950 font-mono">
                    {formatReadings(liveDetail.triage.recheck)}
                  </div>
                </div>
              )}
            </div>

            {/* Patient Guidance Shown */}
            {liveDetail.triage.guidance && (
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1 text-xs">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Guidance Shown to Patient:
                </span>
                <p className="font-semibold text-navy-900 leading-relaxed italic">
                  &ldquo;{liveDetail.triage.guidance}&rdquo;
                </p>
              </div>
            )}

            {/* Disclaimer line */}
            <div className="pt-1 text-center">
              <p className="text-[11px] font-medium text-slate-400">
                Thresholds are illustrative and not clinically validated.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Emergency Detail View or Reconciliation Comparison Card */}
      {isEmergencyItem ? (
        /* Dedicated Emergency Review Card (No reconciliation cards rendered) */
        <div className="surface-card rounded-3xl p-6 sm:p-8 space-y-6 border-2 border-emergencyRed-800/60 bg-red-50/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-red-200 pb-4">
            <div className="flex items-center gap-2.5 text-emergencyRed-800">
              <AlertOctagon className="w-6 h-6 stroke-[2.5]" />
              <span className="font-heading font-bold text-xl">
                {triggerCategoryPlain}
              </span>
            </div>
            <span className="text-xs font-bold uppercase tracking-wider px-3.5 py-1 rounded-full bg-emergencyRed-100 text-emergencyRed-900 border border-emergencyRed-300">
              CRITICAL EMERGENCY
            </span>
          </div>

          <div className="space-y-4">
            {/* Patient's reported statement */}
            {liveDetail?.trigger_text && (
              <div className="space-y-1.5">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                  Patient&apos;s Reported Statement:
                </span>
                <blockquote className="p-4 rounded-2xl bg-white border-2 border-emergencyRed-300 text-sm font-semibold text-navy-900 italic shadow-xs">
                  &ldquo;{liveDetail.trigger_text}&rdquo;
                </blockquote>
              </div>
            )}

            {/* Trigger Reading if available */}
            {triggerReadingText && (
              <div className="p-4 rounded-2xl bg-white border border-slate-200 space-y-1">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                  Clinical Threshold Reading:
                </span>
                <p className="text-base font-bold text-emergencyRed-800 font-mono">
                  {triggerReadingText}
                </p>
              </div>
            )}

            {/* Incident Timestamp & Metadata */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-600">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="font-semibold text-slate-700 block mb-0.5">Escalated At:</span>
                <span>{liveDetail?.escalated_at || liveDetail?.created_at || "Just now"}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <span className="font-semibold text-slate-700 block mb-0.5">Patient Identifier:</span>
                <span>{patientDisplayName} (ID: {liveDetail?.patient_id})</span>
              </div>
            </div>
          </div>

          {/* Action Note Input (Required for Resolve & Escalate) */}
          <div className="space-y-2 pt-2 border-t border-slate-200">
            <label className="block text-xs font-bold text-navy-800 uppercase tracking-wider" htmlFor="action-note-input">
              {t.actionNoteLabel}
            </label>
            <textarea
              id="action-note-input"
              rows={2}
              value={actionNote}
              onChange={(e) => setActionNote(e.target.value)}
              placeholder="Enter clinical review notes or escalation details..."
              className="w-full text-xs sm:text-sm rounded-xl border border-slate-300 bg-white p-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emergencyRed-700 resize-none shadow-xs"
            />
          </div>

          {/* Action Buttons for Emergency */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <button
              type="button"
              onClick={() => handleAction("resolve")}
              disabled={isResolved || isSubmitting || !actionNote.trim()}
              id="reconciliation-resolve-btn"
              className={`min-h-[48px] py-3 px-4 rounded-xl font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-2 ${
                isResolved || !actionNote.trim()
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                  : "bg-mutedGreen-800 hover:bg-mutedGreen-700 active:scale-[0.98] text-white shadow-md"
              }`}
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              <span>{isResolved ? "Case Resolved ✓" : "Mark Emergency Resolved"}</span>
            </button>

            <button
              type="button"
              onClick={() => handleAction("escalate")}
              disabled={isSubmitting || !actionNote.trim()}
              id="reconciliation-escalate-btn"
              className={`min-h-[48px] py-3 px-4 rounded-xl font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-2 ${
                !actionNote.trim()
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                  : "bg-emergencyRed-800 hover:bg-emergencyRed-700 active:scale-[0.98] text-white shadow-md"
              }`}
            >
              <AlertOctagon className="w-4 h-4" />
              <span>Escalate to Rapid Response Team</span>
            </button>
          </div>
        </div>
      ) : (
        /* Standard Discrepancy & Reconciliation Card */
        <div className="surface-card rounded-3xl p-6 sm:p-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-4">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
              <span className="font-heading font-bold text-lg text-navy-800">
                {comparisonTitle}
              </span>
            </div>
            <span className="text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-amber-100 text-amber-900 self-start sm:self-auto border border-amber-300/80">
              Severity: {liveDetail?.max_severity?.toUpperCase() || "REVIEW REQUIRED"}
            </span>
          </div>

          {/* Source Comparison Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {/* Side A: Earlier / Baseline Record */}
            <div className="p-5 rounded-2xl bg-slate-50 border-2 border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-slate-200 text-slate-800 inline-flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" />
                  {sideALabel}
                </span>
                <span className="text-xs text-slate-500 font-medium">
                  {isLiveMode ? `Trust: ${trustLevelA.toUpperCase()}` : "Daily Check-in"}
                </span>
              </div>
              <div className="text-3xl font-bold text-navy-800 pt-1 font-mono">
                {sourceAVal}
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isLiveMode
                  ? sourceAType === "fhir"
                    ? "Verified lab and observation telemetry from hospital system record."
                    : trustLevelA === "high"
                    ? "Clinician-entered baseline record in local clinical store."
                    : "Prior self-reported telemetry recorded during an earlier check-in."
                  : "Self-reported telemetry via adaptive symptom check-in survey."}
              </p>
            </div>

            {/* Side B: Today's Check-in */}
            <div className="p-5 rounded-2xl bg-amber-50/80 border-2 border-amber-300 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-0.5 rounded bg-teal-100 text-teal-900 inline-flex items-center gap-1">
                  <Hospital className="w-3.5 h-3.5" />
                  {sideBLabel}
                </span>
                <span className="text-xs text-slate-500 font-medium">
                  {isLiveMode ? `Trust: ${trustLevelB.toUpperCase()}` : "Lab Record"}
                </span>
              </div>
              <div className="text-3xl font-bold text-navy-800 pt-1 font-mono">
                {sourceBVal}
              </div>
              <p className="text-xs text-amber-950 leading-relaxed">
                {isLiveMode
                  ? "Self-reported telemetry via today's adaptive symptom check-in."
                  : "Verified lab and observation telemetry from hospital system record."}
              </p>
            </div>
          </div>

          {/* AI Reconciliation Reasoning */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5">
            <div className="flex items-center gap-2 font-bold text-xs text-navy-800 uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-teal-700" />
              <span>Automated Reconciliation Analysis</span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              {isLiveMode
                ? describeReviewReason(
                    obsComparison?.status,
                    obsVerification?.review_reason,
                    { delta: obsComparison?.delta, unit: obsComparison?.unit_a || obsComparison?.unit_b }
                  )
                : "Cross-source validation identified delta between patient-reported input and baseline records. Clinician review is recommended to reconcile telemetry before updating longitudinal care targets."}
            </p>
          </div>

          {/* Medication Reconciliation Items (if present) */}
          {isLiveMode && liveDetail?.reconciliation?.medication_comparisons && liveDetail.reconciliation.medication_comparisons.length > 0 && (
            <div className="space-y-4 pt-2 border-t border-slate-200">
              <div className="flex items-center gap-2 text-xs font-bold text-navy-800 uppercase tracking-wider">
                <Pill className="w-4 h-4 text-teal-700" />
                <span>Medication Discrepancies & Reconciliation ({liveDetail.reconciliation.medication_comparisons.length})</span>
              </div>
              <div className="space-y-3">
                {liveDetail.reconciliation.medication_comparisons.map((m: any, idx: number) => {
                  const v = (liveDetail?.verification?.medication_verifications || []).find(
                    (ver: any) => ver.medication_name === m.medication_name
                  );
                  const medDesc = describeMedicationItem(m, v);
                  const isHigh = medDesc.severity === "high";
                  const sideALbl = describeSide("a", m.source_a, v?.trust_level_a, liveDetail?.mode);
                  const sideBLbl = describeSide("b", m.source_b, v?.trust_level_b, liveDetail?.mode);

                  return (
                    <div
                      key={idx}
                      className={`p-4 rounded-2xl border-2 space-y-3 ${
                        isHigh
                          ? "bg-red-50/50 border-emergencyRed-400"
                          : "bg-slate-50 border-slate-200"
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-2">
                        <div className="flex items-center gap-2">
                          <Pill className={`w-4 h-4 ${isHigh ? "text-emergencyRed-700" : "text-slate-700"}`} />
                          <span className="font-bold text-sm text-navy-900">{medDesc.title}</span>
                        </div>
                        <span
                          className={`text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full inline-flex items-center gap-1 ${
                            isHigh
                              ? "bg-emergencyRed-100 text-emergencyRed-900 border border-emergencyRed-300"
                              : "bg-amber-100 text-amber-900 border border-amber-300"
                          }`}
                        >
                          {isHigh ? <AlertTriangle className="w-3.5 h-3.5 text-emergencyRed-700" /> : <ShieldAlert className="w-3.5 h-3.5 text-amber-700" />}
                          <span>Severity: {medDesc.severity.toUpperCase()}</span>
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div className="p-3 rounded-xl bg-white border border-slate-200 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold uppercase text-[10px] text-slate-500">{sideALbl}</span>
                            {v?.trust_level_a && (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                                Trust: {v.trust_level_a.toUpperCase()}
                              </span>
                            )}
                          </div>
                          <p className="font-semibold text-navy-900">{medDesc.recordText}</p>
                        </div>

                        <div className="p-3 rounded-xl bg-white border border-slate-200 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold uppercase text-[10px] text-teal-800">{sideBLbl}</span>
                            {v?.trust_level_b && (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-teal-50 text-teal-900">
                                Trust: {v.trust_level_b.toUpperCase()}
                              </span>
                            )}
                          </div>
                          <p className="font-semibold text-navy-900">{medDesc.todayText}</p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-xs pt-1 text-slate-600">
                        <span className="font-semibold">{medDesc.reason}</span>
                        {liveDetail?.created_at && (
                          <span className="text-[11px] text-slate-400">
                            Logged: {new Date(liveDetail.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Action Note Input (Required for Resolve & Escalate) */}
          <div className="space-y-2 pt-2 border-t border-slate-200">
            <label className="block text-xs font-bold text-navy-800 uppercase tracking-wider" htmlFor="action-note-input">
              {t.actionNoteLabel}
            </label>
            <textarea
              id="action-note-input"
              rows={2}
              value={actionNote}
              onChange={(e) => setActionNote(e.target.value)}
              placeholder={t.actionNotePlaceholder}
              className="w-full text-xs sm:text-sm rounded-xl border border-slate-300 bg-white p-3 text-navy-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-700 resize-none shadow-xs"
            />
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            {/* 1. Resolve */}
            <button
              type="button"
              onClick={() => handleAction("resolve")}
              disabled={isResolved || isSubmitting || !actionNote.trim()}
              id="reconciliation-resolve-btn"
              className={`min-h-[48px] py-3 px-4 rounded-xl font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-2 ${
                isResolved || !actionNote.trim()
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                  : "bg-mutedGreen-800 hover:bg-mutedGreen-700 active:scale-[0.98] text-white shadow-md"
              }`}
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )}
              <span>{isResolved ? "Case Resolved ✓" : t.actionResolveBtn}</span>
            </button>

            {/* 2. Escalate */}
            <button
              type="button"
              onClick={() => handleAction("escalate")}
              disabled={isSubmitting || !actionNote.trim()}
              id="reconciliation-escalate-btn"
              className={`min-h-[48px] py-3 px-4 rounded-xl font-bold text-xs sm:text-sm transition-all flex items-center justify-center gap-2 ${
                !actionNote.trim()
                  ? "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                  : "bg-amber-800 hover:bg-amber-700 active:scale-[0.98] text-white shadow-md"
              }`}
            >
              <AlertOctagon className="w-4 h-4" />
              <span>{t.actionEscalateBtn}</span>
            </button>

            {/* 3. Schedule Appointment (Cross-portal demo labeled) */}
            <button
              type="button"
              onClick={() => setProviderScreen("schedule_appointment")}
              id="reconciliation-schedule-btn"
              className="min-h-[48px] py-3 px-4 bg-teal-700 hover:bg-teal-600 active:scale-[0.98] text-white font-bold text-xs sm:text-sm rounded-xl shadow-md transition-all flex items-center justify-center gap-2 relative"
            >
              <Calendar className="w-4 h-4" />
              <span>{t.scheduleAppointment}</span>
              {isLiveMode && (
                <span className="text-[10px] bg-teal-900/60 px-1.5 py-0.5 rounded font-mono text-teal-200">
                  demo
                </span>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
