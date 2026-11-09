// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { ReconciliationAlertDetail } from "../app/components/provider/ReconciliationAlertDetail";
import { translations } from "../app/translations";
import { api, ReviewDetailResponse, SoapNoteResponse } from "../app/lib/api";

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

describe("Provider SOAP Note Panel (Agent 7, Proposal Sec 13.1)", () => {
  const mockSoap: SoapNoteResponse = {
    checkin_id: "chk-soap-001",
    patient_id: "pat-live-1",
    generated_at: "2026-11-09T04:00:00Z",
    subjective: [
      "General condition: Feeling slightly tired",
      "Reported symptoms: Mild thirst",
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
    plain_text: "SOAP NOTE - CHRONICCARE AI CLINICAL DECISION SUPPORT\nCheck-in ID: chk-soap-001\n...",
  };

  const mockDetail: ReviewDetailResponse = {
    checkin_id: "chk-soap-001",
    patient_id: "pat-live-1",
    patient_display: "Tariq Mahmood",
    mode: "connected",
    emergency: false,
    intakes: [],
    reconciliation: null,
    verification: null,
    requires_review: false,
    max_severity: null,
    review_status: "resolved",
    created_at: "2026-11-09T04:00:00Z",
    actions: [],
    trends: null,
    risk: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.selectedPatient = "chk-soap-001";
    mockAppContext.resolvedCases = [];
    mockAppContext.resolveCase = vi.fn();
    mockAppContext.setProviderScreen = vi.fn();

    // Mock clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    });

    // Mock window.print
    window.print = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the SOAP Note panel with all 4 clinical sections", async () => {
    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);
    vi.spyOn(api, "getProviderSoapNote").mockResolvedValue(mockSoap);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.getByTestId("provider-soap-note-panel")).toBeTruthy();
    });

    // Check all 4 sections exist
    expect(screen.getByTestId("soap-section-subjective")).toBeTruthy();
    expect(screen.getByTestId("soap-section-objective")).toBeTruthy();
    expect(screen.getByTestId("soap-section-assessment")).toBeTruthy();
    expect(screen.getByTestId("soap-section-plan")).toBeTruthy();

    // Check section contents
    expect(screen.getByText(/General condition: Feeling slightly tired/i)).toBeTruthy();
    expect(screen.getByText(/Reading - glucose: 142.0 mg\/dL/i)).toBeTruthy();
    expect(screen.getByText(/Triage evaluation: routine \(Green\)/i)).toBeTruthy();
    expect(screen.getByText(/Appointment action: appointment workflow: not available in this build/i)).toBeTruthy();
  });

  it("allows copying the plain-text SOAP note to clipboard", async () => {
    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);
    vi.spyOn(api, "getProviderSoapNote").mockResolvedValue(mockSoap);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.getByTitle("Copy Note")).toBeTruthy();
    });

    const copyBtn = screen.getByTitle("Copy Note");
    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockSoap.plain_text);
  });

  it("allows triggering browser print for the clinical summary", async () => {
    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);
    vi.spyOn(api, "getProviderSoapNote").mockResolvedValue(mockSoap);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.getByTitle("Print Note")).toBeTruthy();
    });

    const printBtn = screen.getByTitle("Print Note");
    fireEvent.click(printBtn);

    expect(window.print).toHaveBeenCalledTimes(1);
  });

  it("supports collapsing and expanding the SOAP note accordion", async () => {
    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);
    vi.spyOn(api, "getProviderSoapNote").mockResolvedValue(mockSoap);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.getByTestId("soap-section-subjective")).toBeTruthy();
    });

    // Click header button to collapse
    const toggleBtn = screen.getByRole("button", { name: /Clinical Summary \(SOAP Note\)/i });
    fireEvent.click(toggleBtn);

    // After collapse, sections are hidden
    expect(screen.queryByTestId("soap-section-subjective")).toBeNull();

    // Click again to expand
    fireEvent.click(toggleBtn);
    expect(screen.getByTestId("soap-section-subjective")).toBeTruthy();
  });
});
