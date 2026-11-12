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
  User,
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  FileCheck,
  Copy,
  Printer,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { api, ApiError, ReviewDetailResponse, SoapNoteResponse } from "../../lib/api";
import { DecisionTimeline } from "./DecisionTimeline";
import { describeSide, describeReviewReason, describeMedicationItem } from "../../lib/presentation";
import { TriageColourChip } from "../TriageColourChip";

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

  // SOAP Note state
  const [soapNote, setSoapNote] = useState<SoapNoteResponse | null>(null);
  const [isSoapLoading, setIsSoapLoading] = useState<boolean>(false);
  const [isSoapExpanded, setIsSoapExpanded] = useState<boolean>(true);
  const [copiedSoap, setCopiedSoap] = useState<boolean>(false);

  useEffect(() => {
    if (!isLiveMode || selectedPatient === "Ali Khan") {
      const isRiskEnabled =
        process.env.NEXT_PUBLIC_RISK_ENABLED === "true" ||
        (process.env.NEXT_PUBLIC_E2E_HOOKS === "1" &&
          typeof window !== "undefined" &&
          (new URLSearchParams(window.location.search).get("risk") === "true" ||
            new URLSearchParams(window.location.search).get("risk") === "1"));

      setLiveDetail({
        checkin_id: "demo-chk-ali",
        patient_id: "PT-04821",
        patient_display: "Ali Khan (PT-04821)",
        mode: "isolated",
        emergency: demoScenario === "emergency",
        intakes: [],
        reconciliation: null,
        verification: null,
        requires_review: true,
        max_severity: "moderate",
        review_status: "open",
        actions: [],
        created_at: new Date().toISOString(),
        patient_background: {
          height_cm: 172,
          weight_kg: 82,
          bmi: 27.7,
          waist_cm: 98,
          diagnosis_year_hypertension: 2019,
          smoking_status: "former",
          comorbidities: {},
          disclaimer:
            "Self-reported background details provided by patient during enrolment. Not clinically verified.",
        },
        trends: {
          generated_at: new Date().toISOString(),
          advisory: true,
          window_days: 30,
          excluded_count: 0,
          trends: {
            blood_pressure_systolic: {
              direction: "rising",
              n: 4,
              window_days: 30,
              few_readings: true,
              values: [
                { value: 135, at: new Date().toISOString() },
                { value: 142, at: new Date().toISOString() },
                { value: 148, at: new Date().toISOString() },
              ],
            },
            blood_pressure_diastolic: {
              direction: "stable",
              n: 4,
              window_days: 30,
              few_readings: true,
              values: [
                { value: 88, at: new Date().toISOString() },
                { value: 90, at: new Date().toISOString() },
                { value: 92, at: new Date().toISOString() },
              ],
            },
          },
        },
        risk: isRiskEnabled
          ? {
              disease: "diabetes",
              model_name: "diabetes_full_nhanes",
              model_version: "1.0.0",
              status: "ok",
              band: "moderate",
              probability: 0.145,
              label_text: {
                en: "Estimated 10-year risk of developing type 2 diabetes based on age, sex, BMI, waist, BP, and smoking.",
                ur: "ذیابیطس کا ۱۰ سالہ تخمینہ شدہ خطرہ۔",
              },
              reasons: [
                {
                  feature: "waist",
                  contribution: 0.45,
                  label: {
                    en: "Waist circumference",
                    ur: "کمر کی پیمائش",
                    roman_ur: "Kamar",
                  },
                },
                {
                  feature: "systolic",
                  contribution: 0.38,
                  label: {
                    en: "Systolic blood pressure",
                    ur: "سسٹولک بلڈ پریشر",
                    roman_ur: "BP",
                  },
                },
                {
                  feature: "bmi",
                  contribution: 0.28,
                  label: {
                    en: "Body Mass Index (BMI)",
                    ur: "باڈی ماس انڈیکس (BMI)",
                    roman_ur: "BMI",
                  },
                },
              ],
              caveats: ["home_bp_not_exam_bp", "not_validated_pakistan"],
            }
          : null,
        checkin_risk: isRiskEnabled
          ? {
              disease: "diabetes",
              model_name: "diabetes_full_nhanes",
              model_version: "1.0.0",
              status: "ok",
              band: "moderate",
              probability: 0.145,
              raised: false,
              label_text: {
                en: "Cardiometabolic risk assessment computed from check-in vitals.",
                ur: "چیک ان وائٹلز سے کارڈیک خطرے کا تخمینہ۔",
              },
              reasons: [
                {
                  feature: "systolic",
                  contribution: 0.38,
                  label: { en: "Systolic blood pressure", ur: "سسٹولک بلڈ پریشر" },
                },
              ],
              caveats: ["home_bp_not_exam_bp"],
            }
          : null,
        explanation: isRiskEnabled
          ? {
              status: "ready",
              mode: "background",
              sentences: [
                {
                  text: isUrdu
                    ? "ڈیمو مثال (حقیقی رہنمائی نہیں ہے)۔"
                    : "Demo example (not real guidance).",
                  cites: [],
                },
              ],
              sources: [],
              reason: "Demo example (not real guidance)",
            }
          : null,
        trace: isRiskEnabled
          ? [
              { node: "intake", started_at: "2026-11-06T10:00:00Z", summary: "Parsed BP 142/90", duration_ms: 120 },
              { node: "reconcile", started_at: "2026-11-06T10:00:01Z", summary: "Compared with baseline", duration_ms: 85 },
              { node: "verify", started_at: "2026-11-06T10:00:02Z", summary: "Verified adherence", duration_ms: 95 },
              { node: "decide_triage", started_at: "2026-11-06T10:00:03Z", summary: "Assigned moderate review", duration_ms: 110 },
              { node: "risk", started_at: "2026-11-06T10:00:04Z", summary: "Calculated risk band: moderate", duration_ms: 340 },
              { node: "explain", started_at: "2026-11-06T10:00:05Z", summary: "Generated patient guidance", duration_ms: 450 },
            ]
          : null,
      });
      setIsLoading(false);
      return;
    }

    if (!selectedPatient) return;
    let isMounted = true;
    api
      .getProviderReviewDetail(selectedPatient)
      .then((detail) => {
        if (isMounted) {
          setLiveDetail(detail);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [isLiveMode, selectedPatient, demoScenario, isUrdu]);

  useEffect(() => {
    if (isLiveMode && selectedPatient && selectedPatient !== "Ali Khan") {
      setIsSoapLoading(true);
      api
        .getProviderSoapNote(selectedPatient)
        .then((note) => {
          setSoapNote(note);
        })
        .catch((err) => {
          console.warn("SOAP note fetch failed:", err);
        })
        .finally(() => {
          setIsSoapLoading(false);
        });
    }
  }, [isLiveMode, selectedPatient]);

  const mockSoapNote: SoapNoteResponse = {
    checkin_id: "chk-demo-001",
    patient_id: "PT-04821",
    generated_at: new Date().toISOString(),
    subjective: [
      "General condition: Feeling slightly fatigued",
      "Reported symptoms: Mild morning thirst reported",
      "Danger words: None detected",
      "Medication adherence: Reported taking medications as prescribed",
    ],
    objective: [
      "Reading - glucose: 142.0 mg/dL [Source: Patient-reported, Trust: Low]",
      "Reading - blood_pressure: 135/85 mmHg [Source: FHIR, Trust: High]",
      "Reconciliation: Reconciled with baseline; no discrepancies detected",
      "Trend - glucose: stable (12 readings over 30 days)",
    ],
    assessment: [
      "Triage evaluation: routine (Green)",
      "Clinical rules rationale: Routine check-in protocol completed within expected bounds",
      "Stage-2 escalation: None (rules level maintained)",
      "Risk model (t2d_3yr): Band Moderate, Probability 0.42",
      "Risk drivers (t2d_3yr): bmi: 0.15, sbp: 0.12, age: 0.08",
      "Investigational caveat: Risk model scores are investigational decision support tools and do not represent a clinical diagnosis.",
      "Data confidence: High",
    ],
    plan: [
      "Patient guidance provided: Continue routine self-monitoring and care plan.",
      "Appointment action: appointment workflow: not available in this build",
      "Clinician review: Routine monitoring, no clinician review required",
      "Guideline sources:",
      "- 2020 International Society of Hypertension Global Hypertension Practice Guidelines (Section: HMOD, CKD)",
    ],
    data_sources: [
      "FHIR R4 in-process simulator (sim://demo)",
      "Check-in interview responses",
      "Deterministic clinical rules engine",
      "Investigational risk models",
      "Longitudinal reading history (30-day window)",
      "Clinical practice guideline corpus",
    ],
    plain_text:
      "SOAP NOTE - CHRONICCARE AI CLINICAL DECISION SUPPORT\nCheck-in ID: chk-demo-001\nPatient ID: PT-04821\n...",
  };

  const activeSoap = soapNote || (!isLiveMode || selectedPatient === "Ali Khan" ? mockSoapNote : null);

  const handleCopySoap = async () => {
    if (!activeSoap?.plain_text) return;
    try {
      await navigator.clipboard.writeText(activeSoap.plain_text);
      setCopiedSoap(true);
      setTimeout(() => setCopiedSoap(false), 2500);
    } catch (e) {
      console.warn("Copy failed:", e);
    }
  };

  const handlePrintSoap = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

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
    : (isLiveMode ? "Not on file" : "180 mg/dL");
  let sourceBVal = obsComparison?.value_b !== null && obsComparison?.value_b !== undefined
    ? `${obsComparison.value_b} ${obsComparison.unit_b || ""}`
    : (isLiveMode ? "Not reported today" : "140 mg/dL");
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
            aria-label={isUrdu ? "واپس جائیں" : "Back to review queue"}
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

        <div className="flex flex-wrap items-center gap-2">
          <TriageColourChip
            level={liveDetail?.triage_level || (isEmergencyItem ? "emergency" : "review")}
            colour={liveDetail?.triage_colour}
          />
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
      </div>

      {/* Stage-2 Escalation Reason Banner */}
      {liveDetail?.raised_by && liveDetail.raised_by.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-50 border-2 border-amber-300 text-amber-950 text-xs flex items-center gap-3 shadow-xs" data-testid="raised-by-banner">
          <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
          <div className="space-y-0.5">
            <span className="font-bold block uppercase tracking-wide text-[10px] text-amber-800">
              Stage-2 Clinical Escalation (Proposal Section 13.1 Agent 10)
            </span>
            <span className="font-semibold text-sm">
              Raised by: {liveDetail.raised_by.map((r: any) => r.detail || `${r.source}`).join("; ")}
            </span>
          </div>
        </div>
      )}

      {error && (
        <div className="p-3.5 text-sm bg-amber-50 border border-amber-800/30 text-amber-900 rounded-xl flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-800 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Patient Background Card (Self-Reported, Not Verified) */}
      {liveDetail?.patient_background && (
        <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <User className="w-4 h-4 text-teal-700" />
              <span>Background (reported by the patient, not verified)</span>
            </span>
            <span className="text-[10px] text-slate-500 font-medium italic">
              Self-reported at enrolment
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-navy-900">
            <div className="p-2.5 rounded-xl bg-white border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Physical Metrics</span>
              <span className="font-semibold">
                {liveDetail.patient_background.height_cm ? `${liveDetail.patient_background.height_cm} cm` : "Height unrecorded"} •{" "}
                {liveDetail.patient_background.weight_kg ? `${liveDetail.patient_background.weight_kg} kg` : "Weight unrecorded"}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-white border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Clinician BMI</span>
              <span className="font-bold text-teal-800">
                {liveDetail.patient_background.bmi !== null && liveDetail.patient_background.bmi !== undefined
                  ? `${liveDetail.patient_background.bmi} kg/m²`
                  : "N/A"}
              </span>
              <span className="text-[9px] text-slate-400 block font-normal">(Clinician reference only)</span>
            </div>

            <div className="p-2.5 rounded-xl bg-white border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Diagnosis Years</span>
              <span className="font-semibold text-slate-700 block">
                {liveDetail.patient_background.diagnosis_year_diabetes ? `T2D: ${liveDetail.patient_background.diagnosis_year_diabetes}` : "T2D: —"}{" "}
                • {liveDetail.patient_background.diagnosis_year_hypertension ? `HTN: ${liveDetail.patient_background.diagnosis_year_hypertension}` : "HTN: —"}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-white border border-slate-200">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Smoking Status</span>
              <span className="font-semibold capitalize text-slate-700">
                {(liveDetail.patient_background.smoking_status || "prefer_not_to_say").replace(/_/g, " ")}
              </span>
            </div>
          </div>

          {/* Comorbidities */}
          {liveDetail.patient_background.comorbidities && Object.keys(liveDetail.patient_background.comorbidities).length > 0 && (
            <div className="pt-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Reported Comorbidities:</span>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(liveDetail.patient_background.comorbidities)
                  .filter(([_, val]) => Boolean(val))
                  .map(([key]) => (
                    <span key={key} className="px-2.5 py-0.5 bg-slate-200/80 text-navy-800 rounded-lg text-xs font-medium capitalize">
                      {key.replace(/_/g, " ")}
                    </span>
                  ))}
                {Object.values(liveDetail.patient_background.comorbidities).every((v) => !v) && (
                  <span className="text-xs text-slate-500 italic">None reported</span>
                )}
              </div>
            </div>
          )}

          <p className="text-[10px] text-slate-400 italic pt-1">
            {liveDetail.patient_background.disclaimer || "Self-reported background details provided by patient during enrolment. Not clinically verified."}
          </p>
        </div>
      )}

      {/* Provider Longitudinal Trends (30 Days) — Hidden if liveDetail?.trends is null */}
      {liveDetail?.trends && (
        <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3" data-testid="provider-trends-section">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-navy-800 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-teal-700" />
              <span>{t.providerTrendsTitle}</span>
            </span>
            <span className="text-[10px] text-slate-500 font-medium italic">
              {t.providerLongitudinalWindow.replace("{days}", String(liveDetail.trends.window_days))}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { key: "blood_pressure_systolic", label: t.systolicLabel, unit: "mmHg" },
              { key: "blood_pressure_diastolic", label: t.diastolicLabel, unit: "mmHg" },
              { key: "glucose", label: t.glucoseChartTitle, unit: "mg/dL" },
            ].map(({ key, label, unit }) => {
              const series = liveDetail.trends?.trends?.[key];
              if (!series) return null;

              const isNotEnough = series.direction === "not_enough_history";
              const lastThree = (series.values || []).slice(-3).reverse();

              let badgeColor = "bg-slate-100 text-slate-800 border-slate-300";
              let badgeText = t.trendStable;
              let badgeIcon = <Minus className="w-3 h-3 text-slate-600" />;

              if (series.direction === "rising") {
                badgeColor = "bg-amber-50 text-amber-900 border-amber-300";
                badgeText = t.trendRising;
                badgeIcon = <TrendingUp className="w-3 h-3 text-amber-700" />;
              } else if (series.direction === "falling") {
                badgeColor = "bg-teal-50 text-teal-900 border-teal-300";
                badgeText = t.trendFalling;
                badgeIcon = <TrendingDown className="w-3 h-3 text-teal-700" />;
              } else if (isNotEnough) {
                badgeColor = "bg-slate-100 text-slate-600 border-slate-200";
                badgeText = t.trendNotEnoughHistory;
                badgeIcon = <Clock className="w-3 h-3 text-slate-500" />;
              }

              return (
                <div key={key} className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-xs font-bold text-navy-900">{label}</span>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-bold ${badgeColor}`}>
                      {badgeIcon}
                      <span>{badgeText}</span>
                    </span>
                  </div>

                  {isNotEnough ? (
                    <p className="text-[11px] text-slate-500 italic">
                      {t.trendNotEnoughExplain}
                    </p>
                  ) : lastThree.length > 0 ? (
                    <div className="space-y-1 pt-1">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">Recent readings:</span>
                      <div className="space-y-0.5">
                        {lastThree.map((v, i) => (
                          <div key={i} className="text-xs flex items-center justify-between text-slate-700 font-mono">
                            <bdi className="font-semibold text-navy-800">{v.value} {unit}</bdi>
                            <span className="text-[10px] text-slate-500 font-sans">
                              {new Date(v.at).toLocaleDateString(isUrdu ? "ur-PK" : "en-US", { month: "short", day: "numeric" })}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-400 italic">No readings in window</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Provider: Risk at Check-in (Frozen record from check-in time) */}
      {((liveDetail?.checkin_risk_results && liveDetail.checkin_risk_results.length > 0) || liveDetail?.checkin_risk) && (
        <div
          className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4"
          data-testid="provider-checkin-risk-block"
        >
          {(() => {
            const applicableModels = (liveDetail?.checkin_risk_results && liveDetail.checkin_risk_results.length > 0)
              ? liveDetail.checkin_risk_results
              : (liveDetail?.checkin_risk ? [liveDetail.checkin_risk] : []);

            return (
              <div className="space-y-6">
                {applicableModels.map((riskModel, mIdx) => (
                  <div key={riskModel.model_name || riskModel.model || mIdx} className="space-y-4 border-b border-slate-100 pb-4 last:border-b-0 last:pb-0" data-testid="checkin-risk-model-card">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-3">
                      <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-teal-700" />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-navy-800">
                              {t.checkinRiskTitle}
                            </span>
                            <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium border border-slate-200">
                              {t.checkinRiskLabelAtCheckin}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500">
                            {t.checkinRiskSubtitle}
                          </p>
                        </div>
                      </div>
                      {/* Model & Version */}
                      {(riskModel.model_name || riskModel.model) && (
                        <span
                          className="text-[11px] font-mono text-slate-600 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200 self-start sm:self-auto"
                          data-testid="checkin-risk-model"
                        >
                          {t.checkinRiskModelLabel}: {riskModel.model_name || riskModel.model}
                          {(riskModel.model_version || riskModel.version)
                            ? ` v${riskModel.model_version || riskModel.version}`
                            : ""}
                        </span>
                      )}
                    </div>

                    {riskModel.status === "ok" ? (
                      <div className="space-y-4">
                        {/* Band badge + Probability + Raised flag */}
                        <div className="flex flex-wrap items-center gap-3">
                          {(() => {
                            const b = (riskModel.band || "").toLowerCase();
                            if (b === "high") {
                              return (
                                <span
                                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold bg-rose-50 text-rose-900 border-rose-300"
                                  data-testid="checkin-risk-band-badge"
                                >
                                  <AlertOctagon className="w-4 h-4 text-rose-700" />
                                  <span>{t.riskBandHigh}</span>
                                </span>
                              );
                            }
                            if (b === "moderate" || b === "medium") {
                              return (
                                <span
                                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold bg-amber-50 text-amber-900 border-amber-300"
                                  data-testid="checkin-risk-band-badge"
                                >
                                  <AlertTriangle className="w-4 h-4 text-amber-700" />
                                  <span>{t.riskBandMedium}</span>
                                </span>
                              );
                            }
                            return (
                              <span
                                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold bg-emerald-50 text-emerald-900 border-emerald-300"
                                data-testid="checkin-risk-band-badge"
                              >
                                <ShieldCheck className="w-4 h-4 text-emerald-700" />
                                <span>{t.riskBandLow}</span>
                              </span>
                            );
                          })()}

                          {/* Raised to review indicator */}
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border ${
                              riskModel.raised
                                ? "bg-amber-50 text-amber-900 border-amber-300"
                                : "bg-slate-50 text-slate-700 border-slate-200"
                            }`}
                            data-testid="checkin-risk-raised"
                          >
                            {riskModel.raised ? t.checkinRiskRaisedYes : t.checkinRiskRaisedNo}
                          </span>

                          {riskModel.label_text && (
                            <span className="text-xs text-slate-600 font-medium">
                              {riskModel.label_text[isUrdu ? "ur" : "en"] || riskModel.label_text["en"]}
                            </span>
                          )}
                        </div>

                        {/* Reasons / drivers if present */}
                        {(riskModel.reasons || riskModel.top_reasons) &&
                          (riskModel.reasons || riskModel.top_reasons)!.length > 0 && (
                            <div className="space-y-1.5">
                              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                                {t.riskReasonsTitle}
                              </span>
                              <ul className="list-disc list-inside space-y-1 text-xs text-slate-700">
                                {(riskModel.reasons || riskModel.top_reasons)!.map((r, idx) => {
                                  let labelStr = r.feature;
                                  if (typeof r.label === "object" && r.label !== null) {
                                    labelStr = r.label[isUrdu ? "ur" : "en"] || r.label["en"] || r.feature;
                                  } else if (typeof r.label === "string") {
                                    labelStr = r.label;
                                  }
                                  return (
                                    <li key={idx} data-testid="checkin-risk-reason-item">
                                      <span className="font-semibold text-navy-800">{labelStr}</span>
                                    </li>
                                  );
                                })}
                              </ul>
                            </div>
                          )}

                        {/* Clinical Caveat chips */}
                        {riskModel.caveats && riskModel.caveats.length > 0 && (
                          <div className="space-y-1.5 p-3 rounded-xl bg-amber-50/60 border border-amber-200">
                            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1">
                              <Info className="w-3.5 h-3.5 text-amber-700" />
                              <span>{t.riskCaveatsTitle}</span>
                            </span>
                            <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800">
                              {riskModel.caveats.map((c, idx) => {
                                let text = c;
                                if (c === "home_bp_not_exam_bp") text = t.riskCaveatHomeBp;
                                else if (c === "not_validated_pakistan") text = t.riskCaveatNotValidatedPakistan;
                                return (
                                  <li key={idx} data-testid="checkin-risk-caveat-item">
                                    {text}
                                  </li>
                                );
                              })}
                            </ul>
                          </div>
                        )}
                      </div>
                    ) : riskModel.status === "not_enough_information" ? (
                      <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200" data-testid="checkin-risk-missing">
                        {t.checkinRiskMissingData}
                      </p>
                    ) : (
                      <p className="text-xs text-rose-700 bg-rose-50 p-3 rounded-xl border border-rose-200" data-testid="checkin-risk-error">
                        {t.checkinRiskError}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      )}

      {/* Provider Risk Assessment (Experimental Multi-Model) — Hidden if liveDetail?.risk is null */}
      {liveDetail?.risk && (
        <div
          className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4"
          data-testid="provider-risk-panel"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-700" />
              <span className="text-xs font-bold uppercase tracking-wider text-navy-800">
                {t.providerRiskTitle}
              </span>
              <span className="text-[10px] bg-teal-50 text-teal-800 px-2 py-0.5 rounded-full font-medium border border-teal-200">
                {t.liveRiskLabelToday}
              </span>
            </div>
            <span className="text-[10px] text-slate-500 font-medium italic">
              {t.providerRiskNotice}
            </span>
          </div>

          <div className="space-y-4">
            {(Array.isArray(liveDetail.risk) ? liveDetail.risk : [liveDetail.risk]).map((modelItem: any, mIdx: number) => {
              const modelTitle = modelItem.model_name || modelItem.model || "Clinical Risk Model";
              const modelVersion = modelItem.model_version || modelItem.version ? `v${modelItem.model_version || modelItem.version}` : "";
              const confLabel = modelItem.confidence_label || modelItem.confidence || "Medium";

              return (
                <div key={mIdx} className="p-4 rounded-xl bg-slate-50/80 border border-slate-200 space-y-3" data-testid="provider-risk-model-card">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/70 pb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-heading font-bold text-sm text-navy-900" data-testid="checkin-risk-model">
                        {modelTitle} {modelVersion}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                        Confidence: <b className="capitalize text-navy-800">{confLabel}</b>
                      </span>
                    </div>
                  </div>

                  {modelItem.status === "ok" ? (
                    <div className="space-y-3">
                      {/* Risk Band Badge + Probability + Model notice */}
                      <div className="flex flex-wrap items-center gap-3">
                        {(() => {
                          const b = (modelItem.band || "").toLowerCase();
                          if (b === "high") {
                            return (
                              <span
                                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold bg-rose-50 text-rose-900 border-rose-300"
                                data-testid="risk-band-badge"
                              >
                                <AlertOctagon className="w-4 h-4 text-rose-700" />
                                <span>{t.riskBandHigh}</span>
                              </span>
                            );
                          }
                          if (b === "moderate" || b === "medium") {
                            return (
                              <span
                                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold bg-amber-50 text-amber-900 border-amber-300"
                                data-testid="risk-band-badge"
                              >
                                <AlertTriangle className="w-4 h-4 text-amber-700" />
                                <span>{t.riskBandMedium}</span>
                              </span>
                            );
                          }
                          return (
                            <span
                              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold bg-emerald-50 text-emerald-900 border-emerald-300"
                              data-testid="risk-band-badge"
                            >
                              <ShieldCheck className="w-4 h-4 text-emerald-700" />
                              <span>{t.riskBandLow}</span>
                            </span>
                          );
                        })()}

                        {modelItem.label_text && (
                          <span className="text-xs text-slate-600 font-medium">
                            {modelItem.label_text[isUrdu ? "ur" : "en"] || modelItem.label_text["en"]}
                          </span>
                        )}
                      </div>

                      {/* Top Contributing Factors (SHAP Drivers with arrows) */}
                      {(modelItem.reasons || modelItem.top_reasons) && (modelItem.reasons || modelItem.top_reasons)!.length > 0 && (
                        <div className="space-y-1.5 bg-white p-3 rounded-xl border border-slate-200/80">
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block">
                            {t.riskReasonsTitle} (SHAP Drivers)
                          </span>
                          <ul className="space-y-1.5 text-xs text-slate-700">
                            {(modelItem.reasons || modelItem.top_reasons)!.map((r: any, idx: number) => {
                              let labelStr = r.feature;
                              if (typeof r.label === "object" && r.label !== null) {
                                labelStr = r.label[isUrdu ? "ur" : "en"] || r.label["en"] || r.feature;
                              } else if (typeof r.label === "string") {
                                labelStr = r.label;
                              }
                              const isNegative = r.sign === "-" || (typeof r.contribution === "number" && r.contribution < 0);
                              return (
                                <li key={idx} data-testid="risk-reason-item" className="flex items-center justify-between border-b border-slate-100 last:border-none pb-1">
                                  <div className="flex items-center gap-1.5 font-semibold text-navy-800">
                                    {isNegative ? (
                                      <TrendingDown className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                                    ) : (
                                      <TrendingUp className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                                    )}
                                    <span>{labelStr}</span>
                                  </div>
                                  {r.contribution !== undefined && (
                                    <span className="font-mono text-[11px] text-slate-500">
                                      {r.sign || (isNegative ? "-" : "+")}{Math.abs(Number(r.contribution)).toFixed(2)} log-odds
                                    </span>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}

                      {/* Clinical Caveats */}
                      {modelItem.caveats && modelItem.caveats.length > 0 && (
                        <div className="space-y-1.5 p-3 rounded-xl bg-amber-50/60 border border-amber-200">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-900 flex items-center gap-1">
                            <Info className="w-3.5 h-3.5 text-amber-700" />
                            <span>{t.riskCaveatsTitle}</span>
                          </span>
                          <ul className="list-disc list-inside space-y-0.5 text-[11px] text-amber-800">
                            {modelItem.caveats.map((c: string, idx: number) => {
                              let text = c;
                              if (c === "home_bp_not_exam_bp") text = t.riskCaveatHomeBp;
                              else if (c === "not_validated_pakistan") text = t.riskCaveatNotValidatedPakistan;
                              return (
                                <li key={idx} data-testid="risk-caveat-item">
                                  {text}
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : modelItem.status === "not_enough_information" ? (
                    <div className="space-y-2.5 bg-white p-3 rounded-xl border border-slate-200" data-testid="risk-missing-section">
                      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border bg-slate-100 text-slate-700 border-slate-300 text-xs font-semibold" data-testid="risk-missing-badge">
                        <Info className="w-3.5 h-3.5 text-slate-500" />
                        <span>{t.riskMissingDataTitle}</span>
                      </div>
                      <p className="text-xs text-slate-600">
                        {t.riskMissingDataDescription}
                      </p>
                      <ul className="list-disc list-inside space-y-1 text-xs text-slate-600">
                        {(modelItem.missing || []).map((m: string, idx: number) => {
                          let missingText = m;
                          if (m === "latest_readings" || m === "bp" || m === "blood_pressure" || m === "sbp" || m === "dbp") missingText = t.riskMissingBp;
                          else if (m === "waist" || m === "waist_cm") missingText = t.riskMissingWaist;
                          else if (m === "smoking_status" || m === "ever_smoked_100" || m === "current_smoker") missingText = t.riskMissingSmoking;
                          else if (m === "bmi" || m === "height" || m === "weight" || m === "age" || m === "sex_male") missingText = t.riskMissingHeightWeight;
                          return (
                            <li key={idx} data-testid="risk-missing-item">
                              {missingText}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* What the patient was told (Guideline Explanation + Generation Mode) */}
      {liveDetail?.explanation && (
        <div
          className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-4"
          data-testid="provider-patient-explanation-block"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200 pb-3">
            <div className="flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-teal-700" />
              <span className="text-xs font-bold uppercase tracking-wider text-navy-800">
                {t.providerExplanationTitle}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {liveDetail.explanation.mode && (
                <span
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-teal-50 text-teal-900 border border-teal-200"
                  data-testid="provider-explanation-mode"
                >
                  {t.providerExplanationMode}: {liveDetail.explanation.mode.toUpperCase()}
                </span>
              )}
              {liveDetail.explanation.mode === "template" && liveDetail.explanation.reason && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-900 border border-amber-200">
                  {t.providerExplanationReason}: {liveDetail.explanation.reason}
                </span>
              )}
            </div>
          </div>

          {/* Explanation Sentences */}
          {liveDetail.explanation.sentences && liveDetail.explanation.sentences.length > 0 && (
            <div className="space-y-2">
              {liveDetail.explanation.sentences.map((s, idx) => (
                <p
                  key={idx}
                  className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-200/80"
                  data-testid="provider-explanation-sentence"
                >
                  {s.text}
                </p>
              ))}
            </div>
          )}

          {/* Clinical Sources Line */}
          {liveDetail.explanation.sources && liveDetail.explanation.sources.length > 0 && (
            <div className="pt-1 text-xs text-slate-500 flex flex-wrap items-center gap-1.5" data-testid="provider-explanation-source">
              <span className="font-semibold text-slate-600">{t.explanationSourcesTitle}:</span>
              {liveDetail.explanation.sources.map((src, idx) => {
                const parts: string[] = [];
                if (src.edition) parts.push(src.edition);
                if (src.section_path) parts.push(src.section_path);
                if (src.title) parts.push(src.title);
                const sourceStr = parts.length > 0 ? parts.join(", ") : src.chunk_id;
                return (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-slate-700 text-[11px]"
                  >
                    {sourceStr}
                  </span>
                );
              })}
            </div>
          )}

          {/* Rejected Candidates (Provider only) */}
          {liveDetail.explanation.rejected_reasons && liveDetail.explanation.rejected_reasons.length > 0 && (
            <div
              className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 text-xs text-slate-600"
              data-testid="provider-explanation-rejected-reasons"
            >
              <span className="font-semibold text-slate-700 block">
                {t.providerExplanationRejectedReasons}:
              </span>
              <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-600 font-mono">
                {liveDetail.explanation.rejected_reasons.map((r, idx) => (
                  <li key={idx}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Decision Timeline (Trace) */}
      {liveDetail?.trace && liveDetail.trace.length > 0 && (
        <DecisionTimeline trace={liveDetail.trace} />
      )}

      {/* Provider: Recent Patient Record Changes (Edit History) */}
      {liveDetail?.recent_record_edits && liveDetail.recent_record_edits.length > 0 && (
        <div className="surface-card rounded-3xl p-5 sm:p-6 space-y-3.5 border border-slate-200" data-testid="provider-recent-edits-block">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-teal-700" />
              <div>
                <h3 className="font-heading font-bold text-base text-navy-900">
                  {t.recentRecordChangesTitle}
                </h3>
                <p className="text-xs text-slate-500">
                  {t.recentRecordChangesSubtitle}
                </p>
              </div>
            </div>
            <span className="text-xs font-mono font-bold text-slate-400">
              {liveDetail.recent_record_edits.length}
            </span>
          </div>

          <div className="space-y-2.5">
            {liveDetail.recent_record_edits.map((edit) => {
              const isOcr = edit.origin === "ocr";
              return (
                <div
                  key={edit.edit_id || edit.id}
                  data-testid="provider-edit-row"
                  className={`p-3 rounded-2xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 transition-all ${
                    isOcr ? "bg-purple-50/50 border-purple-200 shadow-2xs" : "bg-slate-50 border-slate-200"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-navy-900 capitalize">
                        {edit.record_type} ({edit.field})
                      </span>
                      {isOcr ? (
                        <span
                          data-testid="edit-badge-ocr"
                          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-900 border border-purple-300 text-[10px] font-bold uppercase tracking-wider"
                        >
                          <Sparkles className="w-3 h-3 text-purple-700" /> OCR
                        </span>
                      ) : edit.origin === "import" ? (
                        <span
                          data-testid="edit-badge-import"
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-900 border border-blue-200 text-[10px] font-bold"
                        >
                          Import
                        </span>
                      ) : edit.origin === "clinician" ? (
                        <span
                          data-testid="edit-badge-clinician"
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-teal-100 text-teal-900 border border-teal-200 text-[10px] font-bold"
                        >
                          Clinician
                        </span>
                      ) : (
                        <span
                          data-testid="edit-badge-patient"
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 text-[10px] font-semibold"
                        >
                          Patient
                        </span>
                      )}
                    </div>

                    <div className="font-mono text-[11px] text-slate-600">
                      {edit.field === "created" ? (
                        <span>Added: <bdi className="font-bold text-teal-900">{JSON.stringify(edit.new_value)}</bdi></span>
                      ) : edit.field === "deleted" ? (
                        <span>Removed: <bdi className="text-red-900 line-through">{JSON.stringify(edit.old_value)}</bdi></span>
                      ) : (
                        <span>
                          <bdi className="line-through text-slate-500">{JSON.stringify(edit.old_value)}</bdi> &rarr; <bdi className="font-bold text-teal-900">{JSON.stringify(edit.new_value)}</bdi>
                        </span>
                      )}
                    </div>
                  </div>

                  <span className="text-[11px] text-slate-500 font-mono self-end sm:self-center shrink-0">
                    <bdi>{new Date(edit.changed_at).toLocaleString()}</bdi>
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* SOAP Note Generation Panel (Proposal Section 13.1 Agent 7) */}
      <div
        className="surface-card rounded-3xl p-5 sm:p-6 space-y-4 border border-slate-200"
        data-testid="provider-soap-note-panel"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
          <button
            type="button"
            onClick={() => setIsSoapExpanded(!isSoapExpanded)}
            className="flex items-center gap-2 text-left group cursor-pointer"
            aria-expanded={isSoapExpanded}
          >
            <FileText className="w-5 h-5 text-teal-700 shrink-0" />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-heading font-bold text-base text-navy-900 group-hover:text-teal-700 transition-colors">
                  {t.soapNoteTitle}
                </h3>
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-teal-50 text-teal-800 border border-teal-200">
                  Agent 7
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Deterministic S/O/A/P summary for clinical records
              </p>
            </div>
            {isSoapExpanded ? (
              <ChevronUp className="w-4 h-4 text-slate-400 group-hover:text-slate-600 ml-1" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-slate-600 ml-1" />
            )}
          </button>

          {activeSoap && (
            <div className="flex items-center gap-2 self-end sm:self-center">
              <button
                type="button"
                onClick={handleCopySoap}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-navy-800 shadow-xs transition-colors cursor-pointer"
                title={t.soapCopyNote}
              >
                {copiedSoap ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700 font-bold">{t.soapCopied}</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-slate-600" />
                    <span>{t.soapCopyNote}</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handlePrintSoap}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-navy-800 shadow-xs transition-colors cursor-pointer"
                title={t.soapPrintNote}
              >
                <Printer className="w-3.5 h-3.5 text-slate-600" />
                <span>{t.soapPrintNote}</span>
              </button>
            </div>
          )}
        </div>

        {isSoapLoading ? (
          <div className="py-6 flex items-center justify-center gap-2 text-xs text-slate-500">
            <Loader2 className="w-4 h-4 animate-spin text-teal-600" />
            <span>{t.soapLoading}</span>
          </div>
        ) : isSoapExpanded && activeSoap ? (
          <div className="space-y-4 pt-1">
            {/* Subjective */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5" data-testid="soap-section-subjective">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-900 block">
                {t.soapSubjective}
              </span>
              <ul className="list-disc list-inside space-y-1 text-xs text-navy-900">
                {activeSoap.subjective.map((line, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {line}
                  </li>
                ))}
              </ul>
            </div>

            {/* Objective */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5" data-testid="soap-section-objective">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-900 block">
                {t.soapObjective}
              </span>
              <ul className="list-disc list-inside space-y-1 text-xs text-navy-900">
                {activeSoap.objective.map((line, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {line}
                  </li>
                ))}
              </ul>
            </div>

            {/* Assessment */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5" data-testid="soap-section-assessment">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-900 block">
                {t.soapAssessment}
              </span>
              <ul className="list-disc list-inside space-y-1 text-xs text-navy-900">
                {activeSoap.assessment.map((line, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {line}
                  </li>
                ))}
              </ul>
            </div>

            {/* Plan */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5" data-testid="soap-section-plan">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-900 block">
                {t.soapPlan}
              </span>
              <ul className="list-disc list-inside space-y-1 text-xs text-navy-900">
                {activeSoap.plan.map((line, idx) => (
                  <li key={idx} className="leading-relaxed">
                    {line}
                  </li>
                ))}
              </ul>
            </div>

            {/* Data Sources Provenance Footer */}
            {activeSoap.data_sources && activeSoap.data_sources.length > 0 && (
              <div className="pt-2 border-t border-slate-200 flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] font-semibold text-slate-500 mr-1">Sources:</span>
                {activeSoap.data_sources.map((ds, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded-md bg-slate-200/70 text-slate-700 text-[10px] font-medium"
                  >
                    {ds}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </div>

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
          {(!isLiveMode || obsComparison) ? (
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
          ) : (
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
              <span>No observation comparisons on file for this review item.</span>
            </div>
          )}

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
