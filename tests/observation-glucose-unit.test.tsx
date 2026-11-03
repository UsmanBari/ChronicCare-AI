// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { translations } from "../app/translations";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";
import { api } from "../app/lib/api";

const ctx: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => ctx,
}));

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => false,
  isFirebaseConfigured: () => false,
  getFirebaseAuth: () => null,
  getAuthErrorMessage: () => "",
}));

vi.mock("../app/lib/api", () => ({
  api: {
    getRecord: vi.fn().mockResolvedValue({
      mode: "isolated",
      conditions: [{ name: "diabetes", condition: "diabetes", basis: "doctor_diagnosed", origin: "self_reported" }],
      medications: [],
      observations: [],
      allergies: [],
      ocr_enabled: false,
    }),
    createRecordObservation: vi.fn().mockImplementation((payload) =>
      Promise.resolve({
        id: "obs-123",
        observation_type: payload.observation_type,
        type: payload.observation_type,
        value: payload.value,
        unit: "mg/dL",
        measured_at: payload.measured_at || new Date().toISOString(),
        origin: "manual",
        trust_level: "medium",
      })
    ),
  },
  ApiError: class ApiError extends Error {
    status: number;
    detail: any;
    constructor(status: number, detail: any) {
      super(typeof detail === "string" ? detail : JSON.stringify(detail));
      this.status = status;
      this.detail = detail;
    }
  },
}));

function setContext(lang: "en" | "ur", glucoseUnit: "mg/dL" | "mmol/L" = "mg/dL") {
  for (const k of Object.keys(ctx)) delete ctx[k];
  Object.assign(ctx, {
    language: lang,
    t: translations[lang],
    isUrdu: lang === "ur",
    setLanguage: vi.fn(),
    connectionMode: null,
    portal: "patient",
    screen: "health_record",
    isLiveMode: true,
    liveProfile: {
      user_id: "patient-1",
      conditions: ["Type 2 Diabetes"],
      glucose_unit: glucoseUnit,
    },
    setLiveProfile: vi.fn(),
    setProfile: vi.fn(),
    profile: {
      conditions: ["Type 2 Diabetes"],
      medications: [],
      glucose_unit: glucoseUnit,
    },
    setScreen: vi.fn(),
    setStagedOcrUpload: vi.fn(),
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Bug Bash #85: Observation Input Card Glucose Unit Preference", () => {
  it("displays mmol/L in label and placeholder when profile preferred unit is mmol/L (English)", async () => {
    setContext("en", "mmol/L");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    // The option label in select must reflect mmol/L
    const glucoseOption = screen.getByRole("option", { name: /Blood Glucose \(mmol\/L\)/i });
    expect(glucoseOption).toBeTruthy();

    // The input placeholder must reflect mmol/L (e.g. 7.0)
    const input = screen.getByPlaceholderText("e.g. 7.0");
    expect(input).toBeTruthy();
  });

  it("converts mmol/L value to mg/dL via 18.0 factor when submitted (English)", async () => {
    setContext("en", "mmol/L");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    const input = screen.getByPlaceholderText("e.g. 7.0");
    fireEvent.change(input, { target: { value: "6.5" } });

    const submitBtn = screen.getByRole("button", { name: /Add Reading/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.createRecordObservation).toHaveBeenCalledWith(
        expect.objectContaining({
          observation_type: "glucose",
          value: 117.0, // 6.5 * 18.0
        })
      );
    });
  });

  it("validates range in mmol/L (2.2 - 33.3 mmol/L) when unit is mmol/L", async () => {
    setContext("en", "mmol/L");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    const input = screen.getByPlaceholderText("e.g. 7.0");
    fireEvent.change(input, { target: { value: "1.5" } });

    const submitBtn = screen.getByRole("button", { name: /Add Reading/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Glucose reading must be between 2.2 and 33.3 mmol\/L/i)).toBeTruthy();
      expect(api.createRecordObservation).not.toHaveBeenCalled();
    });
  });

  it("displays localized Urdu labels and placeholder for mmol/L", async () => {
    setContext("ur", "mmol/L");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("نئی پیمائش شامل کریں:")).toBeTruthy();
    });

    // Option contains mmol/L
    const glucoseOption = screen.getByRole("option", { name: /mmol\/L/i });
    expect(glucoseOption).toBeTruthy();

    // Placeholder has Urdu e.g. 7.0
    const input = screen.getByPlaceholderText("مثلاً 7.0");
    expect(input).toBeTruthy();
  });

  it("preserves mg/dL labels and range validation when profile preferred unit is mg/dL", async () => {
    setContext("en", "mg/dL");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    const glucoseOption = screen.getByRole("option", { name: /Blood Glucose \(mg\/dL\)/i });
    expect(glucoseOption).toBeTruthy();

    const input = screen.getByPlaceholderText("e.g. 140");
    expect(input).toBeTruthy();

    // Submitting 140 sends 140 directly
    fireEvent.change(input, { target: { value: "140" } });
    const submitBtn = screen.getByRole("button", { name: /Add Reading/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.createRecordObservation).toHaveBeenCalledWith(
        expect.objectContaining({
          observation_type: "glucose",
          value: 140,
        })
      );
    });
  });
});
