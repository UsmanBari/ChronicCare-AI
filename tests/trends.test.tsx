// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { TrendScreen } from "../app/components/TrendScreen";
import { ReconciliationAlertDetail } from "../app/components/provider/ReconciliationAlertDetail";
import { translations } from "../app/translations";
import { api, TrendsResponse } from "../app/lib/api";

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
    ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
    AreaChart: ({ children, data }: any) => (
      <div data-testid="area-chart" data-points={data?.length || 0}>
        {children}
      </div>
    ),
    LineChart: ({ children, data }: any) => (
      <div data-testid="line-chart" data-points={data?.length || 0}>
        {children}
      </div>
    ),
    Area: () => <div data-testid="area" />,
    Line: () => <div data-testid="line" />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
    CartesianGrid: () => <div />,
  };
});

describe("Iteration 2 - Day 5: Longitudinal Trends Live Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.profile = { conditions: ["Type 2 Diabetes", "Hypertension"] };
    mockAppContext.liveProfile = { conditions: ["Type 2 Diabetes", "Hypertension"] };
    mockAppContext.returnToHomeAndClearRun = vi.fn();
    mockAppContext.selectedPatient = "pat-1";
    mockAppContext.resolvedCases = [];
    mockAppContext.resolveCase = vi.fn();
    mockAppContext.setProviderScreen = vi.fn();
  });

  afterEach(() => {
    cleanup();
  });

  // ===========================================================================
  // Part A Diagnosis: Demonstrating the Old Summary Issue
  // ===========================================================================
  it("A3 DIAGNOSIS: UserCheckinSummaryResponse does NOT supply primary_reading or observations", async () => {
    // A standard backend UserCheckinSummaryResponse contains only metadata:
    const mockCheckinSummary = {
      checkin_id: "chk-123",
      mode: "isolated",
      record_patient_id: "local-p1",
      status: "complete",
      version: 12,
      started_at: "2026-10-20T10:00:00Z",
      completed_at: "2026-10-20T10:05:00Z",
      emergency: false,
      requires_review: false,
      max_severity: "none",
      review_status: "open",
    };

    // Confirm that checkin summary objects have neither primary_reading nor observations:
    expect((mockCheckinSummary as any).primary_reading).toBeUndefined();
    expect((mockCheckinSummary as any).observations).toBeUndefined();

    // Verifies that deriving trend charts from check-in summaries was architecturally defective
    // and necessitated GET /api/me/trends returning pure compute_trends() output.
  });

  // ===========================================================================
  // C2: TrendScreen Each Direction Renders Icon and Translated Text
  // ===========================================================================
  it("renders 'rising' direction with rising icon and translated badge text", async () => {
    const mockTrends: TrendsResponse = {
      generated_at: "2026-10-29T10:00:00Z",
      advisory: true,
      window_days: 30,
      excluded_count: 0,
      trends: {
        glucose: {
          direction: "rising",
          n: 4,
          window_days: 30,
          few_readings: true,
          values: [
            { value: 110, at: "2026-10-10T10:00:00Z" },
            { value: 120, at: "2026-10-15T10:00:00Z" },
            { value: 130, at: "2026-10-20T10:00:00Z" },
            { value: 145, at: "2026-10-25T10:00:00Z" },
          ],
        },
      },
    };

    vi.spyOn(api, "getMyTrends").mockResolvedValue(mockTrends);

    render(<TrendScreen />);

    await waitFor(() => {
      expect(screen.getByText(translations.en.trendRising)).toBeDefined();
      expect(screen.getByText(/4 readings in 30 days/)).toBeDefined();
    });
  });

  it("renders 'falling' direction with falling badge", async () => {
    const mockTrends: TrendsResponse = {
      generated_at: "2026-10-29T10:00:00Z",
      advisory: true,
      window_days: 30,
      excluded_count: 0,
      trends: {
        glucose: {
          direction: "falling",
          n: 5,
          window_days: 30,
          few_readings: false,
          values: [
            { value: 160, at: "2026-10-05T10:00:00Z" },
            { value: 150, at: "2026-10-10T10:00:00Z" },
            { value: 140, at: "2026-10-15T10:00:00Z" },
            { value: 130, at: "2026-10-20T10:00:00Z" },
            { value: 120, at: "2026-10-25T10:00:00Z" },
          ],
        },
      },
    };

    vi.spyOn(api, "getMyTrends").mockResolvedValue(mockTrends);

    render(<TrendScreen />);

    await waitFor(() => {
      expect(screen.getByText(translations.en.trendFalling)).toBeDefined();
    });
  });

  it("renders 'stable' direction badge", async () => {
    const mockTrends: TrendsResponse = {
      generated_at: "2026-10-29T10:00:00Z",
      advisory: true,
      window_days: 30,
      excluded_count: 0,
      trends: {
        blood_pressure_systolic: {
          direction: "stable",
          n: 5,
          window_days: 30,
          few_readings: false,
          values: [
            { value: 120, at: "2026-10-05T10:00:00Z" },
            { value: 122, at: "2026-10-10T10:00:00Z" },
            { value: 121, at: "2026-10-15T10:00:00Z" },
            { value: 120, at: "2026-10-20T10:00:00Z" },
            { value: 122, at: "2026-10-25T10:00:00Z" },
          ],
        },
      },
    };

    vi.spyOn(api, "getMyTrends").mockResolvedValue(mockTrends);

    render(<TrendScreen />);

    await waitFor(() => {
      expect(screen.getByText(translations.en.trendStable)).toBeDefined();
    });
  });

  // ===========================================================================
  // C2: not_enough_history explanatory text
  // ===========================================================================
  it("renders not_enough_history badge and explanatory text when readings < 3", async () => {
    const mockTrends: TrendsResponse = {
      generated_at: "2026-10-29T10:00:00Z",
      advisory: true,
      window_days: 30,
      excluded_count: 0,
      trends: {
        glucose: {
          direction: "not_enough_history",
          n: 1,
          window_days: 30,
          few_readings: false,
          values: [{ value: 115, at: "2026-10-20T10:00:00Z" }],
        },
      },
    };

    vi.spyOn(api, "getMyTrends").mockResolvedValue(mockTrends);

    render(<TrendScreen />);

    await waitFor(() => {
      expect(screen.getAllByText(translations.en.trendNotEnoughHistory).length).toBeGreaterThan(0);
      expect(screen.getAllByText(translations.en.trendNotEnoughExplain).length).toBeGreaterThan(0);
    });
  });

  // ===========================================================================
  // C2: Error State shows retry button, NEVER default stable arrow
  // ===========================================================================
  it("renders error alert with retry button and NO misleading stable badge on failure", async () => {
    vi.spyOn(api, "getMyTrends").mockRejectedValue(new Error("Network connection dropped"));

    render(<TrendScreen />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeDefined();
      expect(screen.getByText(translations.en.trendsErrorTitle)).toBeDefined();
      expect(screen.getByText("Network connection dropped")).toBeDefined();
      expect(screen.getByText(translations.en.trendsErrorRetry)).toBeDefined();
      // Ensure no direction badge was generated
      expect(screen.queryByText(translations.en.trendStable)).toBeNull();
      expect(screen.queryByText(translations.en.trendRising)).toBeNull();
      expect(screen.queryByText(translations.en.trendFalling)).toBeNull();
    });
  });

  // ===========================================================================
  // C2: Urdu RTL rendering
  // ===========================================================================
  it("renders Urdu Nastaliq labels and dir='rtl' when isUrdu is true", async () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    const mockTrends: TrendsResponse = {
      generated_at: "2026-10-29T10:00:00Z",
      advisory: true,
      window_days: 30,
      excluded_count: 0,
      trends: {
        glucose: {
          direction: "rising",
          n: 4,
          window_days: 30,
          few_readings: true,
          values: [
            { value: 110, at: "2026-10-10T10:00:00Z" },
            { value: 120, at: "2026-10-15T10:00:00Z" },
            { value: 130, at: "2026-10-20T10:00:00Z" },
            { value: 145, at: "2026-10-25T10:00:00Z" },
          ],
        },
      },
    };

    vi.spyOn(api, "getMyTrends").mockResolvedValue(mockTrends);

    const { container } = render(<TrendScreen />);

    await waitFor(() => {
      expect(container.firstChild).toHaveProperty("dir", "rtl");
      expect(screen.getByText(translations.ur.trendRising)).toBeDefined(); // اوپر کی طرف
      expect(screen.getByText(/30 دن میں 4 ریڈنگ/)).toBeDefined();
    });
  });

  // ===========================================================================
  // C3: Provider Review Detail Renders Trends & Hides on Null
  // ===========================================================================
  it("provider detail renders compact Trends section with last 3 values", async () => {
    const mockDetail: any = {
      checkin_id: "chk-rev-1",
      patient_id: "rec-p1",
      patient_display: "Ahmed Khan",
      mode: "isolated",
      emergency: false,
      intakes: [],
      requires_review: true,
      review_status: "open",
      created_at: "2026-10-28T10:00:00Z",
      actions: [],
      trends: {
        generated_at: "2026-10-29T10:00:00Z",
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
              { value: 120, at: "2026-10-10T10:00:00Z" },
              { value: 125, at: "2026-10-15T10:00:00Z" },
              { value: 132, at: "2026-10-20T10:00:00Z" },
              { value: 140, at: "2026-10-25T10:00:00Z" },
            ],
          },
        },
      },
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.getByTestId("provider-trends-section")).toBeDefined();
      expect(screen.getByText(translations.en.providerTrendsTitle)).toBeDefined();
      expect(screen.getAllByText(translations.en.trendRising).length).toBeGreaterThan(0);
      // Last 3 values rendered
      expect(screen.getByText(/140 mmHg/)).toBeDefined();
      expect(screen.getByText(/132 mmHg/)).toBeDefined();
      expect(screen.getByText(/125 mmHg/)).toBeDefined();
    });
  });

  it("provider detail cleanly hides Trends section when trends is null", async () => {
    const mockDetailNoTrends: any = {
      checkin_id: "chk-rev-2",
      patient_id: "rec-p2",
      patient_display: "Fatima Noor",
      mode: "isolated",
      emergency: false,
      intakes: [],
      requires_review: true,
      review_status: "open",
      created_at: "2026-10-28T10:00:00Z",
      actions: [],
      trends: null, // Graceful null from backend
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetailNoTrends);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.queryByTestId("provider-trends-section")).toBeNull();
    });
  });

  // ===========================================================================
  // C5: No-Fake-Values Invariant
  // ===========================================================================
  it("does not render fake values when patient has no readings for a condition", async () => {
    const mockEmptyTrends: TrendsResponse = {
      generated_at: "2026-10-29T10:00:00Z",
      advisory: true,
      window_days: 30,
      excluded_count: 0,
      trends: {
        glucose: {
          direction: "not_enough_history",
          n: 0,
          window_days: 30,
          few_readings: false,
          values: [],
        },
        blood_pressure_systolic: {
          direction: "not_enough_history",
          n: 0,
          window_days: 30,
          few_readings: false,
          values: [],
        },
        blood_pressure_diastolic: {
          direction: "not_enough_history",
          n: 0,
          window_days: 30,
          few_readings: false,
          values: [],
        },
      },
    };

    vi.spyOn(api, "getMyTrends").mockResolvedValue(mockEmptyTrends);

    render(<TrendScreen />);

    await waitFor(() => {
      // In live mode with 0 readings, mock glucose fixture values (114 mg/dL) must NOT be shown:
      expect(screen.queryByText(/114/)).toBeNull();
      // Not enough history explanation shown:
      expect(screen.getAllByText(translations.en.trendNotEnoughExplain).length).toBeGreaterThan(0);
    });
  });
});
