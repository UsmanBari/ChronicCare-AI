// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { ReconciliationAlertDetail } from "../app/components/provider/ReconciliationAlertDetail";
import { RiskResultScreen } from "../app/components/RiskResultScreen";
import { translations } from "../app/translations";
import { api, ReviewDetailResponse } from "../app/lib/api";

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

describe("Provider Approve or Adjust (Proposal UC-15, F6)", () => {
  const t = translations.en;
  let mockPostProviderReviewAction: any;

  beforeEach(() => {
    mockPostProviderReviewAction = vi.spyOn(api, "postProviderReviewAction").mockResolvedValue({
      checkin_id: "chk-001",
      patient_id: "PT-01",
      patient_display: "Test Patient (PT-01)",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: false,
      max_severity: "none",
      review_status: "resolved",
      created_at: "2026-11-14T10:00:00Z",
      actions: [],
      provider_decision: "approved",
      provider_level: "review",
    } as any);

    mockAppContext.setProviderScreen = vi.fn();
    mockAppContext.resolveCase = vi.fn();
    mockAppContext.resolvedCases = [];
    mockAppContext.selectedPatient = "chk-001";
    mockAppContext.isLiveMode = true;
    mockAppContext.demoScenario = "routine";
    mockAppContext.t = t;
    mockAppContext.isUrdu = false;
    mockAppContext.language = "en";
    mockAppContext.returnToHomeAndClearRun = vi.fn();
    mockAppContext.setScreen = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders Approve and Adjust buttons on review screen", async () => {
    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue({
      checkin_id: "chk-001",
      patient_id: "PT-01",
      patient_display: "Test Patient",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: "moderate",
      review_status: "open",
      created_at: "2026-11-14T10:00:00Z",
      actions: [],
      triage_level: "review",
      triage_colour: "yellow",
    } as any);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(document.getElementById("review-approve-btn")).toBeTruthy();
      expect(document.getElementById("review-adjust-btn")).toBeTruthy();
    });
  });

  it("clicking Approve calls api.postProviderReviewAction with action approve", async () => {
    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue({
      checkin_id: "chk-001",
      patient_id: "PT-01",
      patient_display: "Test Patient",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: "moderate",
      review_status: "open",
      created_at: "2026-11-14T10:00:00Z",
      actions: [],
      triage_level: "review",
      triage_colour: "yellow",
    } as any);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(document.getElementById("review-approve-btn")).toBeTruthy();
    });

    const approveBtn = document.getElementById("review-approve-btn")!;
    fireEvent.click(approveBtn);

    await waitFor(() => {
      expect(mockPostProviderReviewAction).toHaveBeenCalledWith(
        "chk-001",
        expect.objectContaining({
          action: "approve",
        })
      );
    });
  });

  it("clicking Adjust opens modal, validates min 5 chars reason and confirmation", async () => {
    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue({
      checkin_id: "chk-001",
      patient_id: "PT-01",
      patient_display: "Test Patient",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: "moderate",
      review_status: "open",
      created_at: "2026-11-14T10:00:00Z",
      actions: [],
      triage_level: "review",
      triage_colour: "yellow",
    } as any);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(document.getElementById("review-adjust-btn")).toBeTruthy();
    });

    // Open modal
    fireEvent.click(document.getElementById("review-adjust-btn")!);

    expect(screen.getByTestId("adjust-triage-modal")).toBeTruthy();

    const confirmBtn = document.getElementById("confirm-adjust-btn") as HTMLButtonElement;
    expect(confirmBtn.disabled).toBe(true);

    // Enter short reason (< 5 chars)
    const reasonInput = document.getElementById("adjust-reason-input") as HTMLTextAreaElement;
    fireEvent.change(reasonInput, { target: { value: "bad" } });
    expect(confirmBtn.disabled).toBe(true);

    // Enter valid reason (>= 5 chars)
    fireEvent.change(reasonInput, { target: { value: "Transient blood pressure elevation after heavy meal" } });
    expect(confirmBtn.disabled).toBe(true); // Still disabled because checkbox not checked

    // Check confirmation checkbox
    const confirmCheckbox = document.getElementById("adjust-confirm-checkbox") as HTMLInputElement;
    fireEvent.click(confirmCheckbox);

    // Now enabled
    expect(confirmBtn.disabled).toBe(false);

    // Click confirm submit
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(mockPostProviderReviewAction).toHaveBeenCalledWith(
        "chk-001",
        expect.objectContaining({
          action: "adjust",
          adjusted_level: "routine",
          reason: "Transient blood pressure elevation after heavy meal",
        })
      );
    });
  });

  it("disables Adjust button on Red / emergency check-ins with protocol 1122 notice", async () => {
    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue({
      checkin_id: "chk-emg",
      patient_id: "PT-02",
      patient_display: "Emergency Patient",
      mode: "isolated",
      emergency: true,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: "critical",
      review_status: "open",
      created_at: "2026-11-14T10:00:00Z",
      actions: [],
      triage_level: "emergency",
      triage_colour: "red",
    } as any);

    mockAppContext.selectedPatient = "chk-emg";

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const adjustBtn = document.getElementById("review-adjust-btn") as HTMLButtonElement;
      expect(adjustBtn).toBeTruthy();
      expect(adjustBtn.disabled).toBe(true);
      expect(adjustBtn.getAttribute("title")).toContain("1122");
    });
  });

  it("RiskResultScreen renders 'Reviewed by your care team' card when provider_level is set", () => {
    mockAppContext.liveCheckinResult = {
      emergency: false,
      requires_review: false,
      triage_level: "review",
      triage_colour: "yellow",
      provider_decision: "adjusted",
      provider_level: "routine",
      patient_message: "Your doctor confirmed your vitals are normal.",
      intakes: [],
      reconciliation: null,
      verification: null,
      max_severity: "none",
    };

    render(<RiskResultScreen />);

    const card = screen.getByTestId("provider-reviewed-card");
    expect(card).toBeTruthy();
    expect(screen.getByText(t.reviewedByCareTeam)).toBeTruthy();
    expect(screen.getByText("Your doctor confirmed your vitals are normal.")).toBeTruthy();
  });
});
