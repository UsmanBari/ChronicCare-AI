// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { translations } from "../app/translations";
import {
  getNormalRangeText,
  getReadingStatus,
} from "../app/lib/referenceRanges";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";
import { AdaptiveInterviewScreen } from "../app/components/AdaptiveInterviewScreen";
import { RiskResultScreen } from "../app/components/RiskResultScreen";
import { TrendScreen } from "../app/components/TrendScreen";
import { PatientDetailScreen } from "../app/components/provider/PatientDetailScreen";

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

// Mock recharts
vi.mock("recharts", async () => {
  const actual: any = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
    AreaChart: ({ children }: any) => <div data-testid="area-chart">{children}</div>,
    LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
    Area: () => <div data-testid="area" />,
    Line: () => <div data-testid="line" />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
    CartesianGrid: () => <div />,
    ReferenceArea: (props: any) => (
      <div
        data-testid="reference-area"
        data-y1={props.y1}
        data-y2={props.y2}
        data-fill={props.fill}
      />
    ),
  };
});

describe("F2: Physiological Reference Ranges & Normal Parameters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.language = "en";
    mockAppContext.t = translations.en;
    mockAppContext.profile = { conditions: ["Type 2 Diabetes", "Hypertension"], glucose_unit: "mg/dL" };
    mockAppContext.liveProfile = { conditions: ["Type 2 Diabetes", "Hypertension"], glucose_unit: "mg/dL" };
    mockAppContext.liveEhrConnection = { connected: false };
    mockAppContext.setScreen = vi.fn();
    mockAppContext.returnToHomeAndClearRun = vi.fn();
  });

  describe("1. Reference Range Helper Logic (All 3 Languages)", () => {
    it("returns correct normal range strings in English", () => {
      expect(getNormalRangeText("blood_pressure_systolic", "en")).toBe("Normal: 90–139 mmHg");
      expect(getNormalRangeText("blood_pressure_diastolic", "en")).toBe("Normal: 60–89 mmHg");
      expect(getNormalRangeText("blood_pressure", "en")).toBe("Normal: 90–139 / 60–89 mmHg");
      expect(getNormalRangeText("glucose", "en", "mg/dL")).toBe("Normal: 70–130 fasting / 70–180 post-meal mg/dL");
      expect(getNormalRangeText("glucose", "en", "mmol/L")).toBe("Normal: 3.9–7.2 fasting / 3.9–10.0 post-meal mmol/L");
    });

    it("returns correct normal range strings in Urdu Script", () => {
      expect(getNormalRangeText("blood_pressure_systolic", "ur")).toBe("نارمل: 90–139 ملی میٹر ایچ جی");
      expect(getNormalRangeText("blood_pressure_diastolic", "ur")).toBe("نارمل: 60–89 ملی میٹر ایچ جی");
      expect(getNormalRangeText("blood_pressure", "ur")).toBe("نارمل: 90–139 / 60–89 ملی میٹر ایچ جی");
      expect(getNormalRangeText("glucose", "ur", "mg/dL")).toContain("نارمل: 70–130 نہار منہ");
      expect(getNormalRangeText("glucose", "ur", "mmol/L")).toContain("نارمل: 3.9–7.2 نہار منہ");
    });

    it("returns correct normal range strings in Roman Urdu", () => {
      expect(getNormalRangeText("glucose", "roman_ur", "mg/dL")).toBe(
        "Normal: 70–130 nihar munh / 70–180 khaney ke baad mg/dL"
      );
      expect(getNormalRangeText("glucose", "roman_ur", "mmol/L")).toBe(
        "Normal: 3.9–7.2 nihar munh / 3.9–10.0 khaney ke baad mmol/L"
      );
    });

    it("correctly classifies Systolic BP as below, normal, or above", () => {
      const below = getReadingStatus("blood_pressure_systolic", 85, "en");
      expect(below.status).toBe("below");
      expect(below.label).toBe("Below normal");

      const normal = getReadingStatus("blood_pressure_systolic", 120, "en");
      expect(normal.status).toBe("normal");
      expect(normal.label).toBe("Normal");

      const above = getReadingStatus("blood_pressure_systolic", 145, "en");
      expect(above.status).toBe("above");
      expect(above.label).toBe("Above normal");
    });

    it("correctly classifies Diastolic BP as below, normal, or above", () => {
      const below = getReadingStatus("blood_pressure_diastolic", 55, "en");
      expect(below.status).toBe("below");
      expect(below.label).toBe("Below normal");

      const normal = getReadingStatus("blood_pressure_diastolic", 75, "en");
      expect(normal.status).toBe("normal");
      expect(normal.label).toBe("Normal");

      const above = getReadingStatus("blood_pressure_diastolic", 95, "en");
      expect(above.status).toBe("above");
      expect(above.label).toBe("Above normal");
    });

    it("correctly classifies Blood Glucose in mg/dL and mmol/L", () => {
      // mg/dL: low < 70, normal 70-180, above > 180
      expect(getReadingStatus("glucose", 65, "en", "mg/dL").status).toBe("below");
      expect(getReadingStatus("glucose", 110, "en", "mg/dL").status).toBe("normal");
      expect(getReadingStatus("glucose", 210, "en", "mg/dL").status).toBe("above");

      // mmol/L: low < 3.9, normal 3.9-10.0, above > 10.0
      expect(getReadingStatus("glucose", 3.2, "en", "mmol/L").status).toBe("below");
      expect(getReadingStatus("glucose", 6.5, "en", "mmol/L").status).toBe("normal");
      expect(getReadingStatus("glucose", 12.0, "en", "mmol/L").status).toBe("above");
    });

    it("returns accessible status labels in Urdu and Roman Urdu", () => {
      expect(getReadingStatus("glucose", 60, "ur").label).toBe("نارمل سے کم");
      expect(getReadingStatus("glucose", 100, "ur").label).toBe("نارمل");
      expect(getReadingStatus("glucose", 220, "ur").label).toBe("نارمل سے زیادہ");

      expect(getReadingStatus("glucose", 60, "roman_ur").label).toBe("Normal se kam");
      expect(getReadingStatus("glucose", 100, "roman_ur").label).toBe("Normal");
      expect(getReadingStatus("glucose", 220, "roman_ur").label).toBe("Normal se zyada");
    });

    it("ensures wording is strictly non-diagnostic", () => {
      expect(translations.en.normalRangeDisclaimer).toBe("Normal range used by this app");
      expect(translations.ur.normalRangeDisclaimer).toBe("اس ایپ میں استعمال ہونے والی نارمل رینج");
      expect(translations.roman_ur.normalRangeDisclaimer).toBe("Is app mein istemal hone wali normal range");
      expect(translations.en.normalRangeDisclaimer).not.toContain("healthy");
    });
  });

  describe("2. UI Screen Integrations", () => {
    it("HealthRecordScreen displays normal range text under reading input", () => {
      mockAppContext.isLiveMode = false;
      render(<HealthRecordScreen />);
      const rangeHint = screen.getByTestId("obs-normal-range-text");
      expect(rangeHint).toBeDefined();
      expect(rangeHint.textContent).toContain("Normal: 70–130 fasting");
      expect(screen.getByText("(Normal range used by this app)")).toBeDefined();
    });

    it("AdaptiveInterviewScreen displays normal range hint when BP/Glucose question is asked", () => {
      mockAppContext.isLiveMode = true;
      mockAppContext.checkIn = {
        thirst: false,
        confusion: false,
        shortnessOfBreath: false,
        fever: false,
        headache: false,
      };
      mockAppContext.activeLiveCheckin = {
        question: "Please enter your blood glucose reading:",
        step: "glucose_reading",
      };
      render(<AdaptiveInterviewScreen />);
      const hint = screen.getByTestId("interview-normal-range-hint");
      expect(hint).toBeDefined();
      expect(hint.textContent).toContain("Normal: 70–130 fasting");
    });

    it("RiskResultScreen displays accessible reading status tags on reported comparisons", () => {
      mockAppContext.liveCheckinResult = {
        reconciliation: {
          summary: { agreement: 1, source_a_only: 0, source_b_only: 0 },
          observation_comparisons: [
            {
              observation_type: "glucose",
              value_b: 110,
              unit_b: "mg/dL",
              status: "agreement",
              value_a: 112,
              unit_a: "mg/dL",
            },
            {
              observation_type: "blood_pressure_systolic",
              value_b: 155,
              unit_b: "mmHg",
              status: "agreement",
              value_a: 150,
              unit_a: "mmHg",
            },
          ],
        },
      };

      render(<RiskResultScreen />);
      const tag0 = screen.getByTestId("result-reading-status-0");
      expect(tag0).toBeDefined();
      expect(tag0.textContent).toBe("Normal");

      const tag1 = screen.getByTestId("result-reading-status-1");
      expect(tag1).toBeDefined();
      expect(tag1.textContent).toBe("Above normal");
    });

    it("TrendScreen renders reference area normal bands and disclaimer", () => {
      mockAppContext.isLiveMode = false;
      render(<TrendScreen />);
      expect(screen.getByTestId("glucose-normal-range-note")).toBeDefined();
      expect(screen.getByTestId("bp-normal-range-note")).toBeDefined();
    });

    it("PatientDetailScreen renders provider normal bands and labels", () => {
      mockAppContext.acknowledgedPatients = [];
      mockAppContext.selectedPatient = "Ahmed";
      render(<PatientDetailScreen />);
      expect(screen.getByTestId("provider-glucose-range-label").textContent).toContain("Normal: 70–180 mg/dL");
      expect(screen.getByTestId("provider-bp-range-label").textContent).toContain("Normal: 90–139 / 60–89 mmHg");
    });
  });
});
