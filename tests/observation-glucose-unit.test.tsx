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

function setContext(lang: "en" | "ur") {
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
    },
    setLiveProfile: vi.fn(),
    setProfile: vi.fn(),
    profile: {
      conditions: ["Type 2 Diabetes"],
      medications: [],
    },
    setScreen: vi.fn(),
    setStagedOcrUpload: vi.fn(),
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Bug Bash #85: Observation Input Card Glucose Unit Selector", () => {
  it("defaults to mg/dL with placeholder e.g. 140, submitting 140 sends 140 mg/dL", async () => {
    setContext("en");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    const mgdlBtn = document.getElementById("glucose-unit-mgdl-btn");
    expect(mgdlBtn).toBeTruthy();

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

  it("switches to mmol/L upon clicking mmol/L unit selector, updating label and placeholder", async () => {
    setContext("en");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    const mmolBtn = document.getElementById("glucose-unit-mmol-btn");
    expect(mmolBtn).toBeTruthy();
    fireEvent.click(mmolBtn!);

    // The option label in select must reflect mmol/L
    const glucoseOption = screen.getByRole("option", { name: /Blood Glucose \(mmol\/L\)/i });
    expect(glucoseOption).toBeTruthy();

    // The input placeholder must reflect mmol/L (e.g. 7.0)
    const input = screen.getByPlaceholderText("e.g. 7.0");
    expect(input).toBeTruthy();
  });

  it("accepts 1.5 mmol/L (dangerous low = 27 mg/dL) and sends converted 27 to api", async () => {
    setContext("en");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    // Select mmol/L
    const mmolBtn = document.getElementById("glucose-unit-mmol-btn");
    fireEvent.click(mmolBtn!);

    const input = screen.getByPlaceholderText("e.g. 7.0");
    fireEvent.change(input, { target: { value: "1.5" } });

    const submitBtn = screen.getByRole("button", { name: /Add Reading/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.createRecordObservation).toHaveBeenCalledWith(
        expect.objectContaining({
          observation_type: "glucose",
          value: 27, // 1.5 * 18.0 = 27
        })
      );
    });
  });

  it("rejects 1.0 mmol/L (18 mg/dL < 20 mg/dL server limit) with error saying 1.1 and 33.3 mmol/L", async () => {
    setContext("en");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    const mmolBtn = document.getElementById("glucose-unit-mmol-btn");
    fireEvent.click(mmolBtn!);

    const input = screen.getByPlaceholderText("e.g. 7.0");
    fireEvent.change(input, { target: { value: "1.0" } });

    const submitBtn = screen.getByRole("button", { name: /Add Reading/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/1\.1 and 33\.3 mmol\/L/i)).toBeTruthy();
      expect(api.createRecordObservation).not.toHaveBeenCalled();
    });
  });

  it("rejects 34.0 mmol/L (612 mg/dL > 600 mg/dL server limit) with error saying 1.1 and 33.3 mmol/L", async () => {
    setContext("en");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Add Reading:")).toBeTruthy();
    });

    const mmolBtn = document.getElementById("glucose-unit-mmol-btn");
    fireEvent.click(mmolBtn!);

    const input = screen.getByPlaceholderText("e.g. 7.0");
    fireEvent.change(input, { target: { value: "34" } });

    const submitBtn = screen.getByRole("button", { name: /Add Reading/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/1\.1 and 33\.3 mmol\/L/i)).toBeTruthy();
      expect(api.createRecordObservation).not.toHaveBeenCalled();
    });
  });

  it("displays localized Urdu labels, placeholder, and error for mmol/L", async () => {
    setContext("ur");
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("نئی پیمائش شامل کریں:")).toBeTruthy();
    });

    const mmolBtn = document.getElementById("glucose-unit-mmol-btn");
    expect(mmolBtn).toBeTruthy();
    fireEvent.click(mmolBtn!);

    // Placeholder has Urdu e.g. 7.0
    const input = screen.getByPlaceholderText("مثلاً 7.0");
    expect(input).toBeTruthy();

    // Trigger validation error on 1.0
    fireEvent.change(input, { target: { value: "1.0" } });
    const submitBtn = screen.getByRole("button", { name: /پیمائش شامل کریں/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/1\.1 اور 33\.3 mmol\/L/i)).toBeTruthy();
    });
  });
});
