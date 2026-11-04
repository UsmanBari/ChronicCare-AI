// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { ReconciliationAlertDetail } from "../app/components/provider/ReconciliationAlertDetail";
import { DecisionTimeline } from "../app/components/provider/DecisionTimeline";
import { translations } from "../app/translations";
import { api, ReviewDetailResponse, TraceStepItem } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => false,
  isFirebaseConfigured: () => false,
  getFirebaseAuth: () => null,
  getAuthErrorMessage: () => "",
}));

// Mock recharts for clean jsdom rendering
vi.mock("recharts", async () => {
  const actual: any = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
    AreaChart: ({ children }: any) => <div>{children}</div>,
    LineChart: ({ children }: any) => <div>{children}</div>,
    Area: () => <div />,
    Line: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
    CartesianGrid: () => <div />,
  };
});

describe("Provider Check-in Risk, Explanation & Decision Trace (I3 Day 3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.selectedPatient = "pat-review-1";
    mockAppContext.resolvedCases = [];
    mockAppContext.resolveCase = vi.fn();
    mockAppContext.setProviderScreen = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // -------------------------------------------------------------------------
  // 1. Flags Off Invariant: All three blocks absent when fields are null
  // -------------------------------------------------------------------------
  it("omits check-in risk, patient explanation, and decision timeline when fields are missing (flags off)", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-flags-off",
      patient_id: "pat-1",
      patient_display: "Tariq Mahmood",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-11-04T10:00:00Z",
      actions: [],
      trends: null,
      risk: null,
      checkin_risk: null,
      explanation: null,
      trace: null,
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.queryByTestId("provider-checkin-risk-block")).toBeNull();
      expect(screen.queryByTestId("provider-patient-explanation-block")).toBeNull();
      expect(screen.queryByTestId("decision-timeline-block")).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // 2. Separate Live vs Check-in Risk Display (Never merged)
  // -------------------------------------------------------------------------
  it("renders checkin_risk and live risk separately with their distinct labels and never merges them", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-both-risks",
      patient_id: "pat-2",
      patient_display: "Suleman Javed",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-11-04T10:00:00Z",
      actions: [],
      trends: null,
      // Live panel (computed dynamically today)
      risk: {
        disease: "diabetes",
        model_name: "diabetes_full_nhanes",
        model_version: "1.0.0",
        status: "ok",
        band: "moderate",
        probability: 0.142,
        label_text: { en: "Live risk assessment" },
        reasons: [{ feature: "waist", label: "Waist circumference" }],
        caveats: ["home_bp_not_exam_bp"],
      },
      // Check-in risk (snapshot at check-in time)
      checkin_risk: {
        status: "ok",
        disease: "diabetes",
        model_name: "diabetes_full_nhanes",
        model_version: "1.0.0",
        band: "low",
        probability: 0.048,
        raised: false,
        reasons: [{ feature: "sbp", label: "Systolic blood pressure" }],
        caveats: ["not_validated_pakistan"],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      // Both blocks are rendered
      const checkinBlock = screen.getByTestId("provider-checkin-risk-block");
      const liveBlock = screen.getByTestId("provider-risk-panel");
      expect(checkinBlock).toBeTruthy();
      expect(liveBlock).toBeTruthy();

      // Check-in risk badge is "Low"
      expect(checkinBlock.textContent).toContain(translations.en.riskBandLow);
      expect(checkinBlock.textContent).toContain(translations.en.checkinRiskLabelAtCheckin);
      expect(checkinBlock.textContent).toContain(translations.en.checkinRiskRaisedNo);

      // Live risk badge is "Moderate" and distinct
      expect(liveBlock.textContent).toContain(translations.en.riskBandMedium);
      expect(liveBlock.textContent).toContain(translations.en.liveRiskLabelToday);
    });
  });

  // -------------------------------------------------------------------------
  // 3. Strict Anti-Leak: NO percentage or probability number anywhere
  // -------------------------------------------------------------------------
  it("strictly withholds numerical percentages and raw probability numbers from provider risk UI (docs/RISK_PANEL.md section 3)", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-anti-leak",
      patient_id: "pat-3",
      patient_display: "Zainab Bibi",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-11-04T10:00:00Z",
      actions: [],
      trends: null,
      risk: {
        disease: "diabetes",
        status: "ok",
        band: "high",
        probability: 0.2854,
        reasons: [],
        caveats: [],
      },
      checkin_risk: {
        status: "ok",
        disease: "diabetes",
        model_name: "diabetes_full_nhanes",
        model_version: "1.0.0",
        band: "high",
        probability: 0.3129,
        raised: true,
        reasons: [],
        caveats: [],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const checkinBlock = screen.getByTestId("provider-checkin-risk-block");
      const liveBlock = screen.getByTestId("provider-risk-panel");

      const checkinText = checkinBlock.textContent || "";
      const liveText = liveBlock.textContent || "";

      // 1. Zero % character
      expect(checkinText.includes("%")).toBe(false);
      expect(liveText.includes("%")).toBe(false);

      // 2. Zero floating-point decimals matching probabilities
      expect(/\b0\.\d+\b/.test(checkinText)).toBe(false);
      expect(/\b0\.\d+\b/.test(liveText)).toBe(false);
      expect(checkinText).not.toContain("0.3129");
      expect(liveText).not.toContain("0.2854");
    });
  });

  // -------------------------------------------------------------------------
  // 4. Raised Yes/No & Caveats Translations (en & ur)
  // -------------------------------------------------------------------------
  it("renders raised: true as 'Raised this check-in to review: Yes' and translates caveats in English", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-raised-en",
      patient_id: "pat-4",
      patient_display: "Hamza Ali",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-11-04T10:00:00Z",
      actions: [],
      trends: null,
      checkin_risk: {
        status: "ok",
        disease: "diabetes",
        model_name: "diabetes_full_nhanes",
        model_version: "1.0.0",
        band: "high",
        probability: 0.25,
        raised: true,
        caveats: ["home_bp_not_exam_bp", "not_validated_pakistan"],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const raisedEl = screen.getByTestId("checkin-risk-raised");
      expect(raisedEl.textContent).toContain(translations.en.checkinRiskRaisedYes);

      const caveatItems = screen.getAllByTestId("checkin-risk-caveat-item");
      expect(caveatItems.length).toBe(2);
      expect(caveatItems[0].textContent).toContain(translations.en.riskCaveatHomeBp);
      expect(caveatItems[1].textContent).toContain(translations.en.riskCaveatNotValidatedPakistan);
    });
  });

  it("renders checkin_risk and caveats translated in Urdu when isUrdu is true", async () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    const mockDetailUrdu: ReviewDetailResponse = {
      checkin_id: "chk-raised-ur",
      patient_id: "pat-5",
      patient_display: "حمزہ علی",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-11-04T10:00:00Z",
      actions: [],
      trends: null,
      checkin_risk: {
        status: "ok",
        disease: "diabetes",
        model_name: "diabetes_full_nhanes",
        model_version: "1.0.0",
        band: "moderate",
        probability: 0.15,
        raised: false,
        caveats: ["home_bp_not_exam_bp"],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetailUrdu);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const block = screen.getByTestId("provider-checkin-risk-block");
      expect(block.textContent).toContain(translations.ur.checkinRiskTitle);
      expect(block.textContent).toContain(translations.ur.riskBandMedium);

      const raisedEl = screen.getByTestId("checkin-risk-raised");
      expect(raisedEl.textContent).toContain(translations.ur.checkinRiskRaisedNo);

      const caveatItem = screen.getByTestId("checkin-risk-caveat-item");
      expect(caveatItem.textContent).toContain(translations.ur.riskCaveatHomeBp);
    });
  });

  // -------------------------------------------------------------------------
  // 5. Incomplete / Error checkin_risk states (One-line note, no numbers)
  // -------------------------------------------------------------------------
  it("renders one-line notes without numbers when checkin_risk status is not_enough_information or error", async () => {
    const mockDetailMissing: ReviewDetailResponse = {
      checkin_id: "chk-missing",
      patient_id: "pat-6",
      patient_display: "Ayesha Bibi",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-11-04T10:00:00Z",
      actions: [],
      trends: null,
      checkin_risk: {
        status: "not_enough_information",
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetailMissing);

    const { unmount } = render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const missingEl = screen.getByTestId("checkin-risk-missing");
      expect(missingEl.textContent).toBe(translations.en.checkinRiskMissingData);
      expect(screen.queryByTestId("checkin-risk-band-badge")).toBeNull();
    });

    unmount();

    mockDetailMissing.checkin_risk = { status: "error" };
    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const errorEl = screen.getByTestId("checkin-risk-error");
      expect(errorEl.textContent).toBe(translations.en.checkinRiskError);
      expect(screen.queryByTestId("checkin-risk-band-badge")).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // 6. Patient Explanation Block (Sentences, Sources, Mode, Rejected Reasons)
  // -------------------------------------------------------------------------
  it("renders what the patient was told, including sources, generation mode, and rejected reasons", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-expl",
      patient_id: "pat-7",
      patient_display: "Rashid Minhas",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-11-04T10:00:00Z",
      actions: [],
      trends: null,
      explanation: {
        mode: "llm",
        status: "ok",
        sentences: [
          { text: "Your systolic reading of 145 mmHg is stage 2 hypertension." },
          { text: "Consult your clinician regarding medication adherence." },
        ],
        sources: [
          { chunk_id: "chunk_htn_1", edition: "AHA 2026", section_path: "Section 4", title: "Hypertension Guidelines" },
        ],
        rejected_reasons: ["candidate 1 was too verbose", "candidate 2 mentioned ungrounded diagnosis"],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const explBlock = screen.getByTestId("provider-patient-explanation-block");
      expect(explBlock).toBeTruthy();
      expect(screen.getByText(translations.en.providerExplanationTitle)).toBeTruthy();

      // Mode badge
      const modeBadge = screen.getByTestId("provider-explanation-mode");
      expect(modeBadge.textContent).toContain("LLM");

      // Sentences
      const sentences = screen.getAllByTestId("provider-explanation-sentence");
      expect(sentences.length).toBe(2);
      expect(sentences[0].textContent).toContain("145 mmHg");

      // Source
      const source = screen.getByTestId("provider-explanation-source");
      expect(source.textContent).toContain("AHA 2026, Section 4, Hypertension Guidelines");

      // Rejected reasons
      const rejectedBlock = screen.getByTestId("provider-explanation-rejected-reasons");
      expect(rejectedBlock.textContent).toContain("candidate 1 was too verbose");
      expect(rejectedBlock.textContent).toContain("candidate 2 mentioned ungrounded diagnosis");
    });
  });

  it("renders fallback reason when explanation mode is template", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-expl-template",
      patient_id: "pat-8",
      patient_display: "Farhan Saeed",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-11-04T10:00:00Z",
      actions: [],
      trends: null,
      explanation: {
        mode: "template",
        reason: "budget_timeout",
        sentences: [{ text: "Routine monitoring advisory." }],
        sources: [],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const explBlock = screen.getByTestId("provider-patient-explanation-block");
      expect(explBlock.textContent).toContain("TEMPLATE");
      expect(explBlock.textContent).toContain("budget_timeout");
    });
  });

  // -------------------------------------------------------------------------
  // 7. Decision Timeline Component (Mapping, Collapse/Expand, Emergency Shortcut)
  // -------------------------------------------------------------------------
  describe("DecisionTimeline Component", () => {
    const fullTrace: TraceStepItem[] = [
      { node: "node_intake", started_at: "2026-11-04T10:00:00Z", summary: "intake validated; 1 intakes, emergency=False", duration_ms: 12 },
      { node: "node_fetch_prior", started_at: "2026-11-04T10:00:00.012Z", summary: "prior bundle fetched; 2 obs, 1 meds", duration_ms: 8 },
      { node: "node_build_bundles", started_at: "2026-11-04T10:00:00.020Z", summary: "bundles built; 2 obs, 1 meds", duration_ms: 5 },
      { node: "node_reconcile", started_at: "2026-11-04T10:00:00.025Z", summary: "reconciled; 2 obs compared, 0 conflicts", duration_ms: 18 },
      { node: "node_decide_triage", started_at: "2026-11-04T10:00:00.043Z", summary: "triage decided; level=review, requires_review=True", duration_ms: 6 },
      { node: "node_risk", started_at: "2026-11-04T10:00:00.049Z", summary: "risk assessed; status=ok, band=low, raised=False", duration_ms: 22 },
      { node: "node_persist", started_at: "2026-11-04T10:00:00.071Z", summary: "persisted checkin result; level=review, status=complete", duration_ms: 15 },
    ];

    it("renders first 3 steps collapsed by default with friendly node names and expands on toggle", () => {
      render(<DecisionTimeline trace={fullTrace} />);

      const timeline = screen.getByTestId("decision-timeline-block");
      expect(timeline).toBeTruthy();

      // Only first 3 steps visible initially
      let steps = screen.getAllByTestId("trace-step-item");
      expect(steps.length).toBe(3);

      // Verify node mapping to plain words
      expect(steps[0].textContent).toContain(translations.en.traceNodeIntake);
      expect(steps[1].textContent).toContain(translations.en.traceNodeFetchPrior);
      expect(steps[2].textContent).toContain(translations.en.traceNodeBuildBundles);

      // Toggle button
      const toggleBtn = screen.getByTestId("trace-toggle-btn");
      expect(toggleBtn.textContent).toContain(translations.en.traceShowAll);

      // Expand to view all steps
      fireEvent.click(toggleBtn);

      steps = screen.getAllByTestId("trace-step-item");
      expect(steps.length).toBe(7);
      expect(steps[3].textContent).toContain(translations.en.traceNodeReconcile);
      expect(steps[4].textContent).toContain(translations.en.traceNodeDecideTriage);
      expect(steps[5].textContent).toContain(translations.en.traceNodeRisk);
      expect(steps[6].textContent).toContain(translations.en.traceNodePersist);

      expect(toggleBtn.textContent).toContain(translations.en.traceShowFewer);

      // Collapse back
      fireEvent.click(toggleBtn);
      expect(screen.getAllByTestId("trace-step-item").length).toBe(3);
    });

    it("labels emergency step with 'Emergency path: reconciliation skipped'", () => {
      const emergencyTrace: TraceStepItem[] = [
        { node: "node_intake", started_at: "2026-11-04T10:00:00Z", summary: "intake validated; emergency=True, red flag detected", duration_ms: 10 },
        { node: "node_persist", started_at: "2026-11-04T10:00:00.010Z", summary: "persisted checkin result; level=emergency", duration_ms: 12 },
      ];

      render(<DecisionTimeline trace={emergencyTrace} />);

      const emergencyBanner = screen.getByTestId("trace-emergency-shortcut");
      expect(emergencyBanner).toBeTruthy();
      expect(emergencyBanner.textContent).toContain(translations.en.traceEmergencyShortcut);
    });

    it("renders nothing when trace is null or empty", () => {
      const { rerender } = render(<DecisionTimeline trace={null} />);
      expect(screen.queryByTestId("decision-timeline-block")).toBeNull();

      rerender(<DecisionTimeline trace={[]} />);
      expect(screen.queryByTestId("decision-timeline-block")).toBeNull();
    });
  });
});

