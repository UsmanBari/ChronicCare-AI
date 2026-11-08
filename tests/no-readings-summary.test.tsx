// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { RiskResultScreen } from "../app/components/RiskResultScreen";
import { translations } from "../app/translations";
import { CheckinCompleteResponse } from "../app/lib/api";

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

describe("Frontend Result Summary for No Readings (Day 7b)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.language = "en";
    mockAppContext.t = translations.en;
    mockAppContext.setScreen = vi.fn();
    mockAppContext.returnToHomeAndClearRun = vi.fn();
    mockAppContext.liveProfile = null;
    mockAppContext.liveCheckinResult = null;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows 'No readings entered today' in English when 0 readings were entered", () => {
    const zeroReadingsResult: CheckinCompleteResponse = {
      emergency: false,
      intakes: [
        {
          readings: [],
          confidence_label: "High",
        },
      ],
      reconciliation: {
        summary: { agreement: 0, source_a_only: 0, source_b_only: 0 },
        observation_comparisons: [],
        medication_comparisons: [],
      },
      verification: null,
      requires_review: false,
      max_severity: "none",
      triage: {
        level: "routine",
        guidance: "Continue routine self-monitoring and care plan.",
      },
      explanation: {
        status: "ready",
        sentences: [
          { text: "You did not enter a blood sugar or blood pressure reading today." },
          { text: "No warning symptoms were reported, so no doctor review is needed today." },
          { text: "Adding a reading next time helps track your health over time." },
        ],
        sources: [],
      },
    };
    mockAppContext.liveCheckinResult = zeroReadingsResult;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.liveProfile = { language: "en" };

    render(<RiskResultScreen />);

    // Invariant: "No readings entered today" must be rendered
    expect(screen.getByText("No readings entered today")).toBeDefined();

    // Invariant: Parameter counts and confidence label must NOT be rendered
    expect(screen.queryByText("Verified In-Range Parameters")).toBeNull();
    expect(screen.queryByText("Omitted / Incomplete Data Points")).toBeNull();
    expect(screen.queryByText("Assessment Confidence")).toBeNull();
    expect(screen.queryByText("High")).toBeNull();
  });

  it("shows 'آج کوئی ریڈنگ درج نہیں کی گئی' in Urdu when 0 readings were entered", () => {
    const zeroReadingsResult: CheckinCompleteResponse = {
      emergency: false,
      intakes: [
        {
          readings: [],
          confidence_label: "High",
        },
      ],
      reconciliation: {
        summary: { agreement: 0, source_a_only: 0, source_b_only: 0 },
        observation_comparisons: [],
        medication_comparisons: [],
      },
      verification: null,
      requires_review: false,
      max_severity: "none",
      triage: {
        level: "routine",
        guidance: "Continue routine self-monitoring and care plan.",
      },
      explanation: {
        status: "ready",
        sentences: [
          { text: "آپ نے آج بلڈ شوگر یا بلڈ پریشر کی کوئی ریڈنگ درج نہیں کی۔" },
          { text: "کسی خطرے کی علامت کی اطلاع نہیں دی گئی، اس لیے آج ڈاکٹر کے جائزے کی ضرورت نہیں ہے۔" },
          { text: "اگلی بار ریڈنگ شامل کرنا وقت کے ساتھ آپ کی صحت کی نگرانی میں مدد کرتا ہے۔" },
        ],
        sources: [],
      },
    };
    mockAppContext.liveCheckinResult = zeroReadingsResult;
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;
    mockAppContext.liveProfile = { language: "ur" };

    render(<RiskResultScreen />);

    // Invariant: Urdu "No readings entered today" must be rendered
    expect(screen.getByText("آج کوئی ریڈنگ درج نہیں کی گئی")).toBeDefined();

    // Invariant: Urdu parameter counts and confidence label must NOT be rendered
    expect(screen.queryByText("تصدیق شدہ درست اشارے")).toBeNull();
    expect(screen.queryByText("نامکمل یا چھوٹی ہوئی معلومات")).toBeNull();
    expect(screen.queryByText("تجزیاتی اعتماد")).toBeNull();
  });

  it("shows 'Aaj koi reading darj nahi ki gayi' in Roman Urdu when 0 readings were entered", () => {
    const zeroReadingsResult: CheckinCompleteResponse = {
      emergency: false,
      intakes: [
        {
          readings: [],
          confidence_label: "High",
        },
      ],
      reconciliation: {
        summary: { agreement: 0, source_a_only: 0, source_b_only: 0 },
        observation_comparisons: [],
        medication_comparisons: [],
      },
      verification: null,
      requires_review: false,
      max_severity: "none",
      triage: {
        level: "routine",
      },
    };
    mockAppContext.liveCheckinResult = zeroReadingsResult;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.liveProfile = { language: "roman_ur" };

    render(<RiskResultScreen />);

    expect(screen.getByText("Aaj koi reading darj nahi ki gayi")).toBeDefined();
    expect(screen.queryByText("Verified In-Range Parameters")).toBeNull();
    expect(screen.queryByText("Assessment Confidence")).toBeNull();
  });

  it("preserves old behaviour with parameter counts and confidence when >= 1 reading entered", () => {
    const withReadingResult: CheckinCompleteResponse = {
      emergency: false,
      intakes: [
        {
          readings: [
            {
              observation_type: "glucose",
              value: 110.0,
              unit: "mg/dL",
            },
          ],
          confidence_label: "High",
        },
      ],
      reconciliation: {
        summary: { agreement: 1, source_a_only: 0, source_b_only: 0 },
        observation_comparisons: [
          {
            observation_type: "glucose",
            status: "agreement",
            value_a: 110.0,
            value_b: 110.0,
          },
        ],
        medication_comparisons: [],
      },
      verification: null,
      requires_review: false,
      max_severity: "none",
      triage: {
        level: "routine",
      },
    };
    mockAppContext.liveCheckinResult = withReadingResult;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.liveProfile = { language: "en" };

    render(<RiskResultScreen />);

    // Invariant: Parameter counts and confidence must be visible
    expect(screen.getByText("Verified In-Range Parameters")).toBeDefined();
    expect(screen.getByText("Omitted / Incomplete Data Points")).toBeDefined();
    expect(screen.getByText("Assessment Confidence")).toBeDefined();
    expect(screen.getByText("High")).toBeDefined();

    // Invariant: "No readings entered today" must NOT be present
    expect(screen.queryByText("No readings entered today")).toBeNull();
  });
});

