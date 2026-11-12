// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { RiskResultScreen } from "../app/components/RiskResultScreen";
import { TriageColourChip } from "../app/components/TriageColourChip";
import { translations } from "../app/translations";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("TriageColourChip & RiskResultScreen Confidence Fix (A1, A4, A7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.setScreen = vi.fn();
    mockAppContext.returnToHomeAndClearRun = vi.fn();
  });

  afterEach(() => {
    cleanup();
  });

  describe("TriageColourChip", () => {
    it("renders Green - Routine for routine level", () => {
      render(<TriageColourChip level="routine" colour="green" />);
      const chip = screen.getByTestId("triage-colour-chip");
      expect(chip).toBeTruthy();
      expect(chip.getAttribute("data-colour")).toBe("green");
      expect(chip.textContent).toContain("Green - Routine");
    });

    it("renders Yellow - Review for review level", () => {
      render(<TriageColourChip level="review" colour="yellow" />);
      const chip = screen.getByTestId("triage-colour-chip");
      expect(chip).toBeTruthy();
      expect(chip.getAttribute("data-colour")).toBe("yellow");
      expect(chip.textContent).toContain("Yellow - Review");
    });

    it("renders Red - Urgent for urgent level", () => {
      render(<TriageColourChip level="urgent" colour="red" />);
      const chip = screen.getByTestId("triage-colour-chip");
      expect(chip).toBeTruthy();
      expect(chip.getAttribute("data-colour")).toBe("red");
      expect(chip.textContent).toContain("Red - Urgent");
    });

    it("renders Red - Emergency for emergency level", () => {
      render(<TriageColourChip level="emergency" colour="red" />);
      const chip = screen.getByTestId("triage-colour-chip");
      expect(chip).toBeTruthy();
      expect(chip.getAttribute("data-colour")).toBe("red");
      expect(chip.textContent).toContain("Red - Emergency");
    });

    it("renders Urdu labels when isUrdu is true", () => {
      mockAppContext.isUrdu = true;
      mockAppContext.t = translations.ur;

      render(<TriageColourChip level="routine" colour="green" />);
      const chip = screen.getByTestId("triage-colour-chip");
      expect(chip.textContent).toContain("سبز - معمول");
    });
  });

  describe("RiskResultScreen Confidence Bugfix (A4)", () => {
    it("does NOT fall back to 'High' confidence when no readings are provided", () => {
      // Live check-in with NO readings (ambiguous symptom / cold start)
      mockAppContext.liveCheckinResult = {
        emergency: false,
        requires_review: false,
        intakes: [
          {
            answered_by: "patient",
            readings: [], // NO readings
            // confidence_label omitted / undefined
          },
        ],
        reconciliation: { summary: { agreement: 0, source_a_only: 0, source_b_only: 0 } },
        triage: { level: "routine", triage_colour: "green" },
        triage_level: "routine",
        triage_colour: "green",
      };

      render(<RiskResultScreen />);

      // Must NOT display "High" for confidence
      const fullText = document.body.textContent || "";
      // Confidence card must show Low (or not High)
      expect(fullText).not.toContain("High");
      expect(fullText).toContain("Low");
    });
  });

  describe("Patient-Facing Risk Band (A7)", () => {
    it("renders patient risk estimates card when risk_patient is present", () => {
      mockAppContext.liveCheckinResult = {
        emergency: false,
        requires_review: false,
        intakes: [
          {
            answered_by: "patient",
            readings: [{ observation_type: "blood_pressure_systolic", value: 120 }],
            confidence: "Medium",
          },
        ],
        reconciliation: { summary: { agreement: 1, source_a_only: 0, source_b_only: 0 } },
        triage: { level: "routine", triage_colour: "green" },
        triage_level: "routine",
        triage_colour: "green",
        risk_patient: [
          {
            model_key: "chd10_framingham",
            band: "low",
            message_key: "risk_chd_low",
          },
        ],
      };

      render(<RiskResultScreen />);

      const riskCard = screen.getByTestId("patient-risk-estimates-card");
      expect(riskCard).toBeTruthy();
      expect(riskCard.textContent).toContain("Your Risk Estimates");
      expect(riskCard.textContent).toContain("Low");
      expect(riskCard.textContent).toContain("research model, not a diagnosis");
      // Never emergency styling
      expect(riskCard.textContent).not.toContain("1122");
      expect(riskCard.textContent).not.toContain("Emergency");
    });
  });
});

