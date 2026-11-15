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
    it("returns correct target range strings in English", () => {
      expect(getNormalRangeText("blood_pressure_systolic", "en")).toBe("Target: 90–139 mmHg");
      expect(getNormalRangeText("blood_pressure_diastolic", "en")).toBe("Target: 60–89 mmHg");
      expect(getNormalRangeText("blood_pressure", "en")).toBe("Target: 90–139 / 60–89 mmHg");
      expect(getNormalRangeText("glucose", "en", "mg/dL")).toBe("Target: 90–125 fasting / 125–200 after meals mg/dL");
      expect(getNormalRangeText("glucose", "en", "mmol/L")).toBe("Target: 5.0–6.9 fasting / 6.9–11.1 post-meal mmol/L");
    });

    it("returns correct target range strings in Urdu Script", () => {
      expect(getNormalRangeText("blood_pressure_systolic", "ur")).toBe("ہدف: 90–139 ملی میٹر ایچ جی");
      expect(getNormalRangeText("blood_pressure_diastolic", "ur")).toBe("ہدف: 60–89 ملی میٹر ایچ جی");
      expect(getNormalRangeText("blood_pressure", "ur")).toBe("ہدف: 90–139 / 60–89 ملی میٹر ایچ جی");
      expect(getNormalRangeText("glucose", "ur", "mg/dL")).toContain("ہدف: 90–125 نہار منہ");
      expect(getNormalRangeText("glucose", "ur", "mmol/L")).toContain("ہدف: 5.0–6.9 نہار منہ");
    });

    it("returns correct target range strings in Roman Urdu", () => {
      expect(getNormalRangeText("glucose", "roman_ur", "mg/dL")).toBe(
        "Target: 90–125 nihar munh / 125–200 khaney ke baad mg/dL"
      );
      expect(getNormalRangeText("glucose", "roman_ur", "mmol/L")).toBe(
        "Target: 5.0–6.9 nihar munh / 6.9–11.1 khaney ke baad mmol/L"
      );
    });

    it("correctly classifies Systolic BP as below, in target, or above", () => {
      const below = getReadingStatus("blood_pressure_systolic", 85, "en");
      expect(below.status).toBe("below_target");
      expect(below.label).toBe("Below target");

      const inTarget = getReadingStatus("blood_pressure_systolic", 120, "en");
      expect(inTarget.status).toBe("in_target");
      expect(inTarget.label).toBe("In target");

      const above = getReadingStatus("blood_pressure_systolic", 145, "en");
      expect(above.status).toBe("above_target");
      expect(above.label).toBe("Above target");
    });

    it("correctly classifies Diastolic BP as below, in target, or above", () => {
      const below = getReadingStatus("blood_pressure_diastolic", 55, "en");
      expect(below.status).toBe("below_target");
      expect(below.label).toBe("Below target");

      const inTarget = getReadingStatus("blood_pressure_diastolic", 75, "en");
      expect(inTarget.status).toBe("in_target");
      expect(inTarget.label).toBe("In target");

      const above = getReadingStatus("blood_pressure_diastolic", 95, "en");
      expect(above.status).toBe("above_target");
      expect(above.label).toBe("Above target");
    });

    it("correctly classifies Blood Glucose in mg/dL and mmol/L (Doctor Decision D6)", () => {
      // mg/dL: low < 90, in-target 90-200 (post-meal/overall), above > 200
      expect(getReadingStatus("glucose", 85, "en", "mg/dL").status).toBe("below_target");
      expect(getReadingStatus("glucose", 110, "en", "mg/dL").status).toBe("in_target");
      expect(getReadingStatus("glucose", 210, "en", "mg/dL").status).toBe("above_target");

      // Fasting context: low < 90, in-target 90-125, above > 125
      expect(getReadingStatus("glucose", 130, "en", "mg/dL", "fasting").status).toBe("above_target");
      expect(getReadingStatus("glucose", 100, "en", "mg/dL", "fasting").status).toBe("in_target");

      // mmol/L: low < 5.0, in-target 5.0-11.1, above > 11.1
      expect(getReadingStatus("glucose", 4.2, "en", "mmol/L").status).toBe("below_target");
      expect(getReadingStatus("glucose", 6.5, "en", "mmol/L").status).toBe("in_target");
      expect(getReadingStatus("glucose", 12.0, "en", "mmol/L").status).toBe("above_target");
    });

    it("returns accessible status labels in Urdu and Roman Urdu", () => {
      expect(getReadingStatus("glucose", 60, "ur").label).toBe("ہدف سے کم");
      expect(getReadingStatus("glucose", 100, "ur").label).toBe("ہدف کے مطابق");
      expect(getReadingStatus("glucose", 220, "ur").label).toBe("ہدف سے زیادہ");

      expect(getReadingStatus("glucose", 60, "roman_ur").label).toBe("Target se kam");
      expect(getReadingStatus("glucose", 100, "roman_ur").label).toBe("Target ke mutabiq");
      expect(getReadingStatus("glucose", 220, "roman_ur").label).toBe("Target se zyada");
    });

    it("ensures wording is strictly non-diagnostic", () => {
      expect(translations.en.normalRangeDisclaimer).toBe("Target range used by this app");
      expect(translations.ur.normalRangeDisclaimer).toBe("اس ایپ میں استعمال ہونے والی ہدف کی رینج");
      expect(translations.roman_ur.normalRangeDisclaimer).toBe("Is app mein istemal hone wali target range");
      expect(translations.en.normalRangeDisclaimer).not.toContain("healthy");
    });
  });

  describe("2. UI Screen Integrations", () => {
    it("HealthRecordScreen displays normal range text under reading input", () => {
      mockAppContext.isLiveMode = false;
      render(<HealthRecordScreen />);
      const rangeHint = screen.getByTestId("obs-normal-range-text");
      expect(rangeHint).toBeDefined();
      expect(rangeHint.textContent).toContain("Target: 90–125 fasting");
      expect(screen.getByText("(Target range used by this app)")).toBeDefined();
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
      expect(hint.textContent).toContain("Target: 90–125 fasting");
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
      expect(tag0.textContent).toBe("In target");

      const tag1 = screen.getByTestId("result-reading-status-1");
      expect(tag1).toBeDefined();
      expect(tag1.textContent).toBe("Above target");
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
      expect(screen.getByTestId("provider-glucose-range-label").textContent).toContain("Target: 90–125 fasting / 125–200 after meals mg/dL");
      expect(screen.getByTestId("provider-bp-range-label").textContent).toContain("Target: 90–139 / 60–89 mmHg");
    });
  });
});
