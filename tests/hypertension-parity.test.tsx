// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, act } from "@testing-library/react";
import { translations } from "../app/translations";
import { getConditionFlags } from "../app/lib/conditions";

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
    updateProfile: vi.fn(),
    getProfile: vi.fn(),
    getEHRConnection: vi.fn(),
    getRecord: vi.fn().mockResolvedValue({
      conditions: [],
      medications: [],
      allergies: [],
      baseline_observations: [],
    }),
    createRecordMedication: vi.fn(),
    updateRecordMedication: vi.fn(),
    deleteRecordMedication: vi.fn(),
    createRecordAllergy: vi.fn(),
    deleteRecordAllergy: vi.fn(),
    createRecordObservation: vi.fn(),
    deleteRecordObservation: vi.fn(),
    getUserCheckins: vi.fn().mockResolvedValue([]),
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

// Mock recharts responsive container to cleanly render in jsdom
vi.mock("recharts", async () => {
  const actual: any = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  };
});

import { HomeScreen } from "../app/components/HomeScreen";
import { CheckInEntryScreen } from "../app/components/CheckInEntryScreen";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";
import { TrendScreen } from "../app/components/TrendScreen";
import { PortalLandingScreen } from "../app/components/PortalLandingScreen";

function setContext(lang: "en" | "ur", overrides: Record<string, any> = {}) {
  for (const k of Object.keys(ctx)) delete ctx[k];
  Object.assign(ctx, {
    language: lang,
    t: translations[lang],
    isUrdu: lang === "ur",
    setLanguage: vi.fn(),
    connectionMode: "offline",
    portal: "patient",
    screen: "home",
    setScreen: vi.fn(),
    userIdentifier: "test@example.com",
    profile: {
      conditions: ["Type 2 Diabetes"],
      medications: ["Metformin 500mg"],
      date_of_birth: "1975-06-15",
      sex_at_birth: "female",
      pregnancy_status: "no",
    },
    liveProfile: null,
    liveEhrConnection: null,
    isLiveMode: false,
    checkIn: { note: "", answers: {}, responses: [] },
    setCheckIn: vi.fn(),
    returnToHomeAndClearRun: vi.fn(),
    demoScenario: "normal",
    setDemoScenario: vi.fn(),
    resetDemo: vi.fn(),
    appointment: { isBooked: false, slot: "" },
    setActiveLiveCheckin: vi.fn(),
    setShowSettings: vi.fn(),
    setPortal: vi.fn(),
    setProviderScreen: vi.fn(),
    setAdminScreen: vi.fn(),
    ...overrides,
  });
}

describe("STAGE 10C: Hypertension Parity & Condition Awareness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // 1. Condition Helper Tests
  describe("getConditionFlags helper", () => {
    it("handles all spelling variations for diabetes", () => {
      expect(getConditionFlags(["diabetes"]).hasDiabetes).toBe(true);
      expect(getConditionFlags(["Type 2 Diabetes"]).hasDiabetes).toBe(true);
      expect(getConditionFlags(["type-2 diabetes"]).hasDiabetes).toBe(true);
      expect(getConditionFlags(["T2D"]).hasDiabetes).toBe(true);
      expect(getConditionFlags(["Diabetes Mellitus"]).hasDiabetes).toBe(true);
      expect(getConditionFlags(["diabetes"]).isDiabetesOnly).toBe(true);
    });

    it("handles all spelling variations for hypertension", () => {
      expect(getConditionFlags(["hypertension"]).hasHypertension).toBe(true);
      expect(getConditionFlags(["Hypertension"]).hasHypertension).toBe(true);
      expect(getConditionFlags(["HTN"]).hasHypertension).toBe(true);
      expect(getConditionFlags(["High Blood Pressure"]).hasHypertension).toBe(true);
      expect(getConditionFlags(["hypertension"]).isHypertensionOnly).toBe(true);
    });

    it("detects dual diagnoses correctly", () => {
      const flags = getConditionFlags(["Type 2 Diabetes", "Hypertension"]);
      expect(flags.hasDiabetes).toBe(true);
      expect(flags.hasHypertension).toBe(true);
      expect(flags.hasBoth).toBe(true);
      expect(flags.isHypertensionOnly).toBe(false);
      expect(flags.isDiabetesOnly).toBe(false);
    });

    it("handles profile objects, empty arrays, null and undefined safely", () => {
      expect(getConditionFlags({ conditions: ["hypertension"] }).hasHypertension).toBe(true);
      expect(getConditionFlags([]).hasHypertension).toBe(false);
      expect(getConditionFlags(null).hasDiabetes).toBe(false);
      expect(getConditionFlags(undefined).hasBoth).toBe(false);
    });
  });

  // 2. HomeScreen Component Tests
  describe("HomeScreen", () => {
    it("renders BP-first reminder description and condition chip for hypertension-only patient", () => {
      setContext("en", {
        profile: { conditions: ["Hypertension"] },
      });
      render(<HomeScreen />);

      expect(screen.getByText(translations.en.reminderDescHypertension)).toBeTruthy();
      expect(screen.queryByText(translations.en.reminderDesc)).toBeNull();
      expect(screen.getByText("Hypertension")).toBeTruthy();
      expect(screen.queryByText("Type 2 Diabetes")).toBeNull();
    });

    it("renders standard reminder description and condition chip for diabetes-only patient", () => {
      setContext("en", {
        profile: { conditions: ["Type 2 Diabetes"] },
      });
      render(<HomeScreen />);

      expect(screen.getByText(translations.en.reminderDesc)).toBeTruthy();
      expect(screen.queryByText(translations.en.reminderDescHypertension)).toBeNull();
      expect(screen.getByText("Type 2 Diabetes")).toBeTruthy();
      expect(screen.queryByText("Hypertension")).toBeNull();
    });

    it("renders dual reminder description when patient has both conditions", () => {
      setContext("en", {
        profile: { conditions: ["Type 2 Diabetes", "Hypertension"] },
      });
      render(<HomeScreen />);

      expect(screen.getByText(translations.en.reminderDescBoth)).toBeTruthy();
      expect(screen.getByText("Type 2 Diabetes")).toBeTruthy();
      expect(screen.getByText("Hypertension")).toBeTruthy();
    });

    it("renders accurately in Urdu for hypertension-only patient", () => {
      setContext("ur", {
        profile: { conditions: ["hypertension"] },
      });
      render(<HomeScreen />);

      expect(screen.getByText(translations.ur.reminderDescHypertension)).toBeTruthy();
      expect(screen.getByText("ہائی بلڈ پریشر (Hypertension)")).toBeTruthy();
    });
  });

  // 3. CheckInEntryScreen Component Tests
  describe("CheckInEntryScreen", () => {
    it("shows BP-first subtitle and placeholder for hypertension-only patient", () => {
      setContext("en", {
        profile: { conditions: ["Hypertension"] },
      });
      render(<CheckInEntryScreen />);

      expect(screen.getByText(translations.en.checkInEntrySubtitleHypertension)).toBeTruthy();
      const input = screen.getByPlaceholderText(translations.en.howAreYouFeelingPlaceholderHypertension);
      expect(input).toBeTruthy();
    });

    it("autofills BP-oriented sample note on voice input for hypertension-only patient", () => {
      vi.useFakeTimers();
      setContext("en", {
        profile: { conditions: ["Hypertension"] },
      });
      render(<CheckInEntryScreen />);

      const voiceBtn = screen.getByTitle(translations.en.voiceInputTitle);
      act(() => {
        fireEvent.click(voiceBtn);
        vi.advanceTimersByTime(2000);
      });

      const textarea = screen.getByPlaceholderText(translations.en.howAreYouFeelingPlaceholderHypertension) as HTMLTextAreaElement;
      expect(textarea.value).toBe(translations.en.sampleVoiceNoteHypertension);
      expect(textarea.value).not.toContain("thirsty");

      vi.useRealTimers();
    });

    it("shows standard subtitle and placeholder for diabetes-only patient", () => {
      setContext("en", {
        profile: { conditions: ["Type 2 Diabetes"] },
      });
      render(<CheckInEntryScreen />);

      expect(screen.getByText(translations.en.checkInEntrySubtitle)).toBeTruthy();
      expect(screen.getByPlaceholderText(translations.en.howAreYouFeelingPlaceholder)).toBeTruthy();
    });
  });

  // 4. HealthRecordScreen Baseline Readings Tests
  describe("HealthRecordScreen Baseline Readings", () => {
    it("defaults observation type selector to systolic BP and shows BP placeholder for hypertension-only", () => {
      setContext("en", {
        profile: { conditions: ["Hypertension"] },
      });
      render(<HealthRecordScreen />);

      const select = screen.getByDisplayValue("Systolic BP (mmHg)") as HTMLSelectElement;
      expect(select).toBeTruthy();
      expect(select.value).toBe("blood_pressure_systolic");

      const valueInput = screen.getByPlaceholderText(translations.en.obsPlaceholderSystolic) as HTMLInputElement;
      expect(valueInput).toBeTruthy();

      // Changing to diastolic updates placeholder
      fireEvent.change(select, { target: { value: "blood_pressure_diastolic" } });
      expect(screen.getByPlaceholderText(translations.en.obsPlaceholderDiastolic)).toBeTruthy();

      // Glucose is still available in the selector
      fireEvent.change(select, { target: { value: "glucose" } });
      expect(screen.getByPlaceholderText(translations.en.obsPlaceholderGlucose)).toBeTruthy();
    });

    it("defaults observation type selector to glucose for diabetes-only patient", () => {
      setContext("en", {
        profile: { conditions: ["Type 2 Diabetes"] },
      });
      render(<HealthRecordScreen />);

      const select = screen.getByDisplayValue("Blood Glucose (mg/dL)") as HTMLSelectElement;
      expect(select).toBeTruthy();
      expect(select.value).toBe("glucose");

      expect(screen.getByPlaceholderText(translations.en.obsPlaceholderGlucose)).toBeTruthy();
    });
  });

  // 5. TrendScreen Tests
  describe("TrendScreen", () => {
    it("renders Blood Pressure chart first and hides Glucose chart for hypertension patient with no glucose data", () => {
      setContext("en", {
        profile: { conditions: ["Hypertension"] },
      });
      render(<TrendScreen />);

      expect(screen.getByText(translations.en.bloodPressureChartTitle)).toBeTruthy();
      expect(screen.getByText(translations.en.adherenceChartTitle)).toBeTruthy();
      expect(screen.queryByText(translations.en.glucoseChartTitle)).toBeNull();
    });

    it("renders Blood Glucose chart first for diabetes-only patient", () => {
      setContext("en", {
        profile: { conditions: ["Type 2 Diabetes"] },
      });
      render(<TrendScreen />);

      const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
      expect(headings[0]).toContain(translations.en.glucoseChartTitle);
      expect(headings[1]).toContain(translations.en.bloodPressureChartTitle);
    });

    it("renders Blood Pressure chart first when patient has both conditions", () => {
      setContext("en", {
        profile: { conditions: ["Type 2 Diabetes", "Hypertension"] },
      });
      render(<TrendScreen />);

      const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
      expect(headings[0]).toContain(translations.en.bloodPressureChartTitle);
      expect(headings[1]).toContain(translations.en.glucoseChartTitle);
    });
  });

  // 6. PortalLandingScreen Tests
  describe("PortalLandingScreen", () => {
    it("renders hypertension telemetry alongside glucose card and mentions monitoring", () => {
      setContext("en");
      render(<PortalLandingScreen />);

      // Ali Khan T2D reading
      expect(screen.getByText("Ali Khan (58y M)")).toBeTruthy();
      expect(screen.getByText("180 mg/dL")).toBeTruthy();

      // Bilal Ahmed HTN reading
      expect(screen.getByText("Bilal Ahmed (62y M)")).toBeTruthy();
      expect(screen.getByText("150/95 mmHg")).toBeTruthy();

      // Monitoring note
      expect(screen.getByText(translations.en.landingHtnMonitoringNote)).toBeTruthy();
    });

    it("renders in Urdu correctly", () => {
      setContext("ur");
      render(<PortalLandingScreen />);

      expect(screen.getByText(translations.ur.landingHtnDemoPatient)).toBeTruthy();
      expect(screen.getByText("150/95 mmHg")).toBeTruthy();
      expect(screen.getByText(translations.ur.landingHtnMonitoringNote)).toBeTruthy();
    });
  });
});
