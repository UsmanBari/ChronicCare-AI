// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { ReconciliationAlertDetail } from "../app/components/provider/ReconciliationAlertDetail";
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

describe("Provider Diabetes Risk Panel (Part I)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.selectedPatient = "pat-htn-1";
    mockAppContext.resolvedCases = [];
    mockAppContext.resolveCase = vi.fn();
    mockAppContext.setProviderScreen = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("omits the risk panel entirely when detail.risk is null", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-norisk-1",
      patient_id: "rec-p1",
      patient_display: "Tariq Mahmood",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-10-30T10:00:00Z",
      actions: [],
      trends: null,
      risk: null, // RISK_ENABLED=false or inapplicable
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.queryByTestId("provider-risk-panel")).toBeNull();
    });
  });

  it("renders risk panel with band badge, reasons, and caveats when status is ok", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-risk-ok",
      patient_id: "rec-p2",
      patient_display: "Suleman Javed",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-10-30T10:00:00Z",
      actions: [],
      trends: null,
      risk: {
        disease: "diabetes",
        model_name: "diabetes_full_nhanes",
        model_version: "1.0.0",
        status: "ok",
        band: "moderate",
        probability: 0.142,
        label_text: {
          en: "Estimated 10-year risk of developing type 2 diabetes based on age, sex, BMI, waist, BP, and smoking.",
          ur: "ذیابیطس کا ۱۰ سالہ تخمینہ شدہ خطرہ۔",
        },
        reasons: [
          {
            feature: "waist",
            contribution: 0.45,
            label: { en: "Waist circumference", ur: "کمر کی پیمائش", roman_ur: "Kamar" },
          },
          {
            feature: "systolic",
            contribution: 0.38,
            label: { en: "Systolic blood pressure", ur: "سسٹولک بلڈ پریشر", roman_ur: "BP" },
          },
        ],
        caveats: ["home_bp_not_exam_bp", "not_validated_pakistan"],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const panel = screen.getByTestId("provider-risk-panel");
      expect(panel).toBeTruthy();

      // Title and notice
      expect(screen.getByText(translations.en.providerRiskTitle)).toBeTruthy();
      expect(screen.getByText(translations.en.providerRiskNotice)).toBeTruthy();

      // Band badge: icon + text (never color alone)
      const badge = screen.getByTestId("risk-band-badge");
      expect(badge).toBeTruthy();
      expect(badge.textContent).toContain(translations.en.riskBandMedium);

      // Reasons list
      const reasonItems = screen.getAllByTestId("risk-reason-item");
      expect(reasonItems.length).toBe(2);
      expect(reasonItems[0].textContent).toContain("Waist circumference");
      expect(reasonItems[1].textContent).toContain("Systolic blood pressure");

      // Caveats list
      const caveatItems = screen.getAllByTestId("risk-caveat-item");
      expect(caveatItems.length).toBe(2);
      expect(caveatItems[0].textContent).toContain(translations.en.riskCaveatHomeBp);
      expect(caveatItems[1].textContent).toContain(translations.en.riskCaveatNotValidatedPakistan);

      // NEVER show raw percentage probability
      expect(panel.textContent).not.toContain("14.2%");
      expect(panel.textContent).not.toContain("0.142");
      expect(panel.textContent).not.toContain("%");
    });
  });

  it("renders not_enough_information state with missing measurement items", async () => {
    const mockDetailMissing: ReviewDetailResponse = {
      checkin_id: "chk-risk-missing",
      patient_id: "rec-p3",
      patient_display: "Zainab Bibi",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-10-30T10:00:00Z",
      actions: [],
      trends: null,
      risk: {
        disease: "diabetes",
        status: "not_enough_information",
        missing: ["waist_cm", "latest_readings", "smoking_status"],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetailMissing);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.getByTestId("provider-risk-panel")).toBeTruthy();
      expect(screen.getByTestId("risk-missing-section")).toBeTruthy();
      expect(screen.getByText(translations.en.riskMissingDataTitle)).toBeTruthy();
      expect(screen.getByText(translations.en.riskMissingDataDescription)).toBeTruthy();

      const missingItems = screen.getAllByTestId("risk-missing-item");
      expect(missingItems.length).toBe(3);
      expect(missingItems.some((item) => item.textContent?.includes(translations.en.riskMissingWaist))).toBe(true);
      expect(missingItems.some((item) => item.textContent?.includes(translations.en.riskMissingBp))).toBe(true);
      expect(missingItems.some((item) => item.textContent?.includes(translations.en.riskMissingSmoking))).toBe(true);
    });
  });

  it("correctly renders in Urdu when isUrdu is true", async () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    const mockDetailUrdu: ReviewDetailResponse = {
      checkin_id: "chk-risk-ur",
      patient_id: "rec-p4",
      patient_display: "کامران اختر",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: null,
      review_status: "open",
      created_at: "2026-10-30T10:00:00Z",
      actions: [],
      trends: null,
      risk: {
        disease: "diabetes",
        status: "ok",
        band: "high",
        probability: 0.32,
        label_text: {
          en: "High risk",
          ur: "زیادہ خطرہ",
        },
        reasons: [
          {
            feature: "waist",
            contribution: 0.6,
            label: { en: "Waist circumference", ur: "کمر کی پیمائش", roman_ur: "Kamar" },
          },
        ],
        caveats: ["home_bp_not_exam_bp"],
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetailUrdu);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.getByTestId("provider-risk-panel")).toBeTruthy();
      expect(screen.getByText(translations.ur.providerRiskTitle)).toBeTruthy();
      expect(screen.getByText(translations.ur.providerRiskNotice)).toBeTruthy();

      const badge = screen.getByTestId("risk-band-badge");
      expect(badge.textContent).toContain(translations.ur.riskBandHigh);

      const reasons = screen.getAllByTestId("risk-reason-item");
      expect(reasons[0].textContent).toContain("کمر کی پیمائش");

      const caveats = screen.getAllByTestId("risk-caveat-item");
      expect(caveats[0].textContent).toContain(translations.ur.riskCaveatHomeBp);
    });
  });
});
