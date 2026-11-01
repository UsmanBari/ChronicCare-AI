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

describe("Provider Recent Record Edits Panel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.selectedPatient = "pat-123";
    mockAppContext.resolvedCases = [];
    mockAppContext.resolveCase = vi.fn();
    mockAppContext.setProviderScreen = vi.fn();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("omits the recent record edits block when list is empty or null (never renders empty card)", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-no-edits",
      patient_id: "pat-123",
      patient_display: "Test Patient",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      review_status: "open",
      created_at: "2026-10-31T10:00:00Z",
      actions: [],
      recent_record_edits: [],
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.queryByTestId("provider-recent-edits-block")).toBeNull();
    });
  });

  it("renders recent record changes and displays OCR badge ONLY when origin === 'ocr'", async () => {
    const mockDetail: ReviewDetailResponse = {
      checkin_id: "chk-with-edits",
      patient_id: "pat-123",
      patient_display: "Test Patient",
      mode: "isolated",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      review_status: "open",
      created_at: "2026-10-31T10:00:00Z",
      actions: [],
      recent_record_edits: [
        {
          edit_id: "edit-ocr-1",
          record_type: "medication",
          record_id: "med-1",
          field: "dosage",
          old_value: "500mg daily",
          new_value: "1000mg daily",
          origin: "ocr",
          changed_by_user_id: "pat-123",
          changed_at: "2026-10-31T12:00:00Z",
          reason: "Prescription scan update",
        },
        {
          edit_id: "edit-imp-2",
          record_type: "observation",
          record_id: "obs-1",
          field: "value",
          old_value: null,
          new_value: 125,
          origin: "import",
          changed_by_user_id: "pat-123",
          changed_at: "2026-10-31T11:00:00Z",
        },
        {
          edit_id: "edit-cli-3",
          record_type: "conditions_basis",
          record_id: "basis-1",
          field: "basis",
          old_value: "self_reported",
          new_value: "clinical_record",
          origin: "clinician",
          changed_by_user_id: "dr-456",
          changed_at: "2026-10-31T10:30:00Z",
        },
        {
          edit_id: "edit-pat-4",
          record_type: "allergy",
          record_id: "all-1",
          field: "created",
          old_value: null,
          new_value: "Penicillin",
          origin: "patient",
          changed_by_user_id: "pat-123",
          changed_at: "2026-10-31T09:00:00Z",
        },
      ],
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(mockDetail);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      expect(screen.getByTestId("provider-recent-edits-block")).toBeTruthy();
    });

    const rows = screen.getAllByTestId("provider-edit-row");
    expect(rows.length).toBe(4);

    // Verify OCR badge renders ONLY for origin === 'ocr' (exactly 1 occurrence)
    const ocrBadges = screen.getAllByTestId("edit-badge-ocr");
    expect(ocrBadges.length).toBe(1);
    expect(ocrBadges[0].textContent).toContain("OCR");

    // Verify clinician, import, and patient badges render appropriately
    const importBadges = screen.getAllByTestId("edit-badge-import");
    expect(importBadges.length).toBe(1);

    const clinicianBadges = screen.getAllByTestId("edit-badge-clinician");
    expect(clinicianBadges.length).toBe(1);

    const patientBadges = screen.getAllByTestId("edit-badge-patient");
    expect(patientBadges.length).toBe(1);

    // Verify values rendered
    expect(screen.getByText(/"500mg daily"/)).toBeTruthy();
    expect(screen.getByText(/"1000mg daily"/)).toBeTruthy();
  });
});
