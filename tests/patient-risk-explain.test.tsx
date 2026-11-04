// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, act, waitFor } from "@testing-library/react";
import { ExplanationBox } from "../app/components/ExplanationBox";
import { RiskResultScreen } from "../app/components/RiskResultScreen";
import { RoutedToReviewScreen } from "../app/components/RoutedToReviewScreen";
import { translations } from "../app/translations";
import { api, PatientExplanation, CheckinCompleteResponse } from "../app/lib/api";

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

describe("Patient Explanation Box & Strict Patient Risk Suppression (I3 Day 2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.setScreen = vi.fn();
    mockAppContext.returnToHomeAndClearRun = vi.fn();
    mockAppContext.setAppointment = vi.fn();
    mockAppContext.appointment = { status: "None" };
    mockAppContext.checkIn = { lowConfidence: false };
    mockAppContext.liveCheckinResult = null;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // -------------------------------------------------------------------------
  // 1. Flags Off Invariant (Screens render baseline without explanation)
  // -------------------------------------------------------------------------
  it("renders RiskResultScreen unchanged when flags are off (explanation null)", () => {
    const baselineResult: CheckinCompleteResponse = {
      emergency: false,
      intakes: [],
      reconciliation: { summary: { agreement: 2, source_a_only: 0, source_b_only: 0 } },
      verification: null,
      requires_review: false,
      max_severity: null,
      explanation: null,
    };
    mockAppContext.liveCheckinResult = baselineResult;

    render(<RiskResultScreen />);

    // Verify explanation box is absent
    expect(screen.queryByTestId("patient-explanation-box")).toBeNull();

    // Verify baseline scope note is unconditionally rendered
    expect(screen.getByText(translations.en.riskScoringOmittedNote)).toBeTruthy();
  });

  it("renders RoutedToReviewScreen unchanged when flags are off", () => {
    const reviewResult: CheckinCompleteResponse = {
      emergency: false,
      intakes: [],
      reconciliation: { summary: { agreement: 0, source_a_only: 1, source_b_only: 1 } },
      verification: null,
      requires_review: true,
      max_severity: "moderate",
      explanation: null,
    };
    mockAppContext.liveCheckinResult = reviewResult;

    render(<RoutedToReviewScreen />);

    expect(screen.queryByTestId("patient-explanation-box")).toBeNull();
    expect(screen.getByText("Pending Provider Review")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 2. Strict Patient Risk Suppression (Doctors only; patients never see it)
  // -------------------------------------------------------------------------
  it("strictly suppresses patient risk: a /complete response containing a 'risk' object renders NO risk band, NO low/moderate/high risk wording, and NOTHING from risk anywhere on patient screens", () => {
    const responseWithRisk: Record<string, any> = {
      emergency: false,
      intakes: [],
      reconciliation: { summary: { agreement: 2, source_a_only: 0, source_b_only: 0 } },
      verification: null,
      requires_review: false,
      max_severity: null,
      // Backend may return a risk object (for providers), but patient screens must ignore it completely
      risk: {
        status: "ok",
        band: "high",
        reasons: [
          { feature: "told_high_bp", contribution: 0.156, label: { en: "history of high blood pressure", ur: "ہائی بلڈ پریشر کی تاریخ" } },
          { feature: "age", contribution: 0.1168, label: { en: "your age", ur: "آپ کی عمر" } },
        ],
        advisory: "Advisory risk assessment, not a clinical diagnosis.",
        missing: [],
      },
      explanation: null,
    };
    mockAppContext.liveCheckinResult = responseWithRisk;

    // 1. Verify on RiskResultScreen
    const { unmount } = render(<RiskResultScreen />);

    expect(screen.queryByTestId("patient-risk-card")).toBeNull();
    expect(screen.queryByTestId("patient-risk-badge")).toBeNull();

    // Ensure no risk band wording leaked
    const textContent = document.body.textContent || "";
    expect(textContent).not.toContain("High Risk");
    expect(textContent).not.toContain("Moderate Risk");
    expect(textContent).not.toContain("Low Risk");
    expect(textContent).not.toContain("Health Risk Advisory");
    expect(textContent).not.toContain("Advisory risk assessment");
    expect(textContent).not.toContain("history of high blood pressure");

    // The release scope note must be displayed unconditionally
    expect(screen.getByText(translations.en.riskScoringOmittedNote)).toBeTruthy();

    unmount();

    // 2. Verify on RoutedToReviewScreen
    responseWithRisk.requires_review = true;
    responseWithRisk.max_severity = "moderate";
    mockAppContext.liveCheckinResult = responseWithRisk;

    render(<RoutedToReviewScreen />);

    expect(screen.queryByTestId("patient-risk-card")).toBeNull();
    expect(screen.queryByTestId("patient-risk-badge")).toBeNull();

    const reviewText = document.body.textContent || "";
    expect(reviewText).not.toContain("High Risk");
    expect(reviewText).not.toContain("Moderate Risk");
    expect(reviewText).not.toContain("Health Risk Advisory");
    expect(reviewText).not.toContain("history of high blood pressure");
  });

  // -------------------------------------------------------------------------
  // 3. ExplanationBox: Collapsed/Expand, Sources, Keyboard & Template Mode
  // -------------------------------------------------------------------------
  describe("ExplanationBox functionality", () => {
    const sampleExplanation: PatientExplanation = {
      status: "ok",
      sentences: [
        {
          text: "Your systolic blood pressure reading of 136 mmHg is slightly elevated according to clinical guidelines.",
          cites: ["chunk_dm_routine"],
        },
        {
          text: "Regular blood pressure monitoring helps track cardiovascular risk over time.",
          cites: ["chunk_dm_routine"],
        },
      ],
      sources: [
        {
          chunk_id: "chunk_dm_routine",
          title: "Glycemic Targets",
          edition: "ADA 2026",
          section_path: "Section 6",
        },
      ],
    };

    it("is collapsed by default, expands on click, and displays sentences and formatted sources", () => {
      render(<ExplanationBox explanation={sampleExplanation} emergency={false} />);

      const toggleBtn = screen.getByTestId("explanation-toggle-btn");
      expect(toggleBtn).toBeTruthy();
      expect(toggleBtn.getAttribute("aria-expanded")).toBe("false");
      expect(toggleBtn.textContent).toContain(translations.en.whyThisResultBtn);

      // Content is not visible when collapsed
      expect(screen.queryByTestId("explanation-content")).toBeNull();

      // Click to expand
      fireEvent.click(toggleBtn);
      expect(toggleBtn.getAttribute("aria-expanded")).toBe("true");
      expect(toggleBtn.textContent).toContain(translations.en.hideWhyThisResultBtn);

      const content = screen.getByTestId("explanation-content");
      expect(content).toBeTruthy();

      // Verify sentences
      const sentenceElements = screen.getAllByTestId("explanation-sentence");
      expect(sentenceElements.length).toBe(2);
      expect(sentenceElements[0].textContent).toContain("136 mmHg");

      // Verify formatted sources line (e.g. ADA 2026, Section 6, Glycemic Targets)
      const sourcesEl = screen.getByTestId("explanation-sources");
      expect(sourcesEl.textContent).toContain("ADA 2026");
      expect(sourcesEl.textContent).toContain("Section 6");
      expect(sourcesEl.textContent).toContain("Glycemic Targets");

      // Click again to collapse
      fireEvent.click(toggleBtn);
      expect(toggleBtn.getAttribute("aria-expanded")).toBe("false");
      expect(screen.queryByTestId("explanation-content")).toBeNull();
    });

    it("supports keyboard toggling via Enter and Space while keeping focus", () => {
      render(<ExplanationBox explanation={sampleExplanation} emergency={false} />);

      const toggleBtn = screen.getByTestId("explanation-toggle-btn");
      toggleBtn.focus();
      expect(document.activeElement).toBe(toggleBtn);

      // Press Enter to expand
      fireEvent.keyDown(toggleBtn, { key: "Enter", code: "Enter" });
      expect(toggleBtn.getAttribute("aria-expanded")).toBe("true");
      expect(screen.getByTestId("explanation-content")).toBeTruthy();
      expect(document.activeElement).toBe(toggleBtn);

      // Press Space to collapse
      fireEvent.keyDown(toggleBtn, { key: " ", code: "Space" });
      expect(toggleBtn.getAttribute("aria-expanded")).toBe("false");
      expect(screen.queryByTestId("explanation-content")).toBeNull();
      expect(document.activeElement).toBe(toggleBtn);
    });

    it("renders template-mode explanations identically without 'AI' branding", () => {
      const templateExplanation: PatientExplanation = {
        status: "ok",
        sentences: [
          {
            text: "Elevated systolic readings indicate increased cardiovascular resistance.",
            cites: ["chunk_htn_stage1"],
          },
        ],
        sources: [
          {
            chunk_id: "chunk_htn_stage1",
            title: "Blood Pressure Thresholds",
            edition: "AHA 2026",
            section_path: "Section 4",
          },
        ],
      };

      render(<ExplanationBox explanation={templateExplanation} emergency={false} />);

      const toggleBtn = screen.getByTestId("explanation-toggle-btn");
      fireEvent.click(toggleBtn);

      const content = screen.getByTestId("explanation-content");
      expect(content.textContent).toContain("Elevated systolic readings");
      expect(content.textContent).toContain("AHA 2026, Section 4, Blood Pressure Thresholds");

      // Zero AI buzzwords
      expect(content.textContent?.toLowerCase()).not.toContain("ai");
      expect(content.textContent?.toLowerCase()).not.toContain("artificial intelligence");
      expect(content.textContent?.toLowerCase()).not.toContain("llm");
    });

    it("renders nothing when explanation is null, error status, or has empty sentences", () => {
      const { rerender } = render(<ExplanationBox explanation={null} emergency={false} />);
      expect(screen.queryByTestId("patient-explanation-box")).toBeNull();

      rerender(<ExplanationBox explanation={{ status: "error", sentences: [], sources: [] }} emergency={false} />);
      expect(screen.queryByTestId("patient-explanation-box")).toBeNull();

      rerender(<ExplanationBox explanation={{ status: "ok", sentences: [], sources: [] }} emergency={false} />);
      expect(screen.queryByTestId("patient-explanation-box")).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // 4. Emergency Invariant: NEVER shown during an emergency
  // -------------------------------------------------------------------------
  it("never renders explanation box during an emergency check-in", () => {
    const sampleExplanation: PatientExplanation = {
      status: "ok",
      sentences: [{ text: "Emergency vitals require immediate intervention." }],
      sources: [],
    };

    // Explicitly pass emergency=true
    render(
      <div>
        <ExplanationBox explanation={sampleExplanation} emergency={true} />
      </div>
    );

    expect(screen.queryByTestId("patient-explanation-box")).toBeNull();
  });

  // -------------------------------------------------------------------------
  // 5. Urdu Language, RTL, and Nastaliq Typography
  // -------------------------------------------------------------------------
  it("renders explanation box in Urdu with dir='rtl', font-urdu", () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    const urduExplanation: PatientExplanation = {
      status: "ok",
      sentences: [
        {
          text: "آپ کا بلڈ پریشر قدرے بلند ہے جس کے لیے باقاعدہ جانچ ضروری ہے۔",
        },
      ],
      sources: [
        {
          chunk_id: "chunk_dm_routine",
          title: "بلڈ پریشر گائیڈ لائنز",
          edition: "ADA 2026",
          section_path: "سیکشن 6",
        },
      ],
    };

    render(
      <div>
        <ExplanationBox explanation={urduExplanation} emergency={false} />
      </div>
    );

    // Explanation Box in Urdu
    const explBox = screen.getByTestId("patient-explanation-box");
    expect(explBox.getAttribute("dir")).toBe("rtl");
    expect(explBox.className).toContain("font-urdu");

    const toggleBtn = screen.getByTestId("explanation-toggle-btn");
    expect(toggleBtn.textContent).toContain("یہ نتیجہ کیوں؟");
    fireEvent.click(toggleBtn);

    expect(screen.getByTestId("explanation-content").textContent).toContain("آپ کا بلڈ پریشر قدرے بلند ہے");
  });

  // -------------------------------------------------------------------------
  // 6. Live Mode Never Shows Fixed Demo Example
  // -------------------------------------------------------------------------
  it("never shows the 'Example' demo label when in live mode", () => {
    mockAppContext.isLiveMode = true;

    const expl: PatientExplanation = {
      status: "ok",
      sentences: [{ text: "Reading is in target." }],
      sources: [],
    };

    render(
      <div>
        <ExplanationBox explanation={expl} emergency={false} isDemo={false} />
      </div>
    );

    const toggleBtn = screen.getByTestId("explanation-toggle-btn");
    expect(toggleBtn.textContent).not.toContain("Example");
    expect(toggleBtn.textContent).not.toContain("مثال");
  });

  // -------------------------------------------------------------------------
  // 7. Background Mode: Pending State & Polling (I3 Day 5)
  // -------------------------------------------------------------------------
  it("renders pending state banner with spinner when status is pending", () => {
    const pendingExplanation: PatientExplanation = {
      status: "pending",
      sentences: [],
      sources: [],
    };

    render(
      <div>
        <ExplanationBox
          explanation={pendingExplanation}
          emergency={false}
          checkinId="chk_test_123"
        />
      </div>
    );

    const pendingEl = screen.getByTestId("explanation-pending");
    expect(pendingEl).toBeTruthy();
    expect(pendingEl.textContent).toContain(translations.en.explanationPending);
    expect(screen.queryByTestId("patient-explanation-box")).toBeNull();
  });

  it("polls getCheckinExplanation until status becomes ready and renders explanation", async () => {
    vi.useFakeTimers();

    const readyExplanation: PatientExplanation = {
      status: "ready",
      sentences: [
        {
          text: "Blood pressure is well controlled within target range.",
          cites: ["chunk_bp_norm"],
        },
      ],
      sources: [
        {
          chunk_id: "chunk_bp_norm",
          title: "Hypertension Guidelines",
          edition: "AHA 2026",
          section_path: "Section 3",
        },
      ],
    };

    const spyGetExplanation = vi
      .spyOn(api, "getCheckinExplanation")
      .mockResolvedValueOnce(readyExplanation);

    const pendingExplanation: PatientExplanation = {
      status: "pending",
      sentences: [],
      sources: [],
    };

    render(
      <div>
        <ExplanationBox
          explanation={pendingExplanation}
          emergency={false}
          checkinId="chk_poll_456"
        />
      </div>
    );

    expect(screen.getByTestId("explanation-pending")).toBeTruthy();

    // Advance fake timers by 3500ms and flush promises
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3500);
    });

    expect(spyGetExplanation).toHaveBeenCalledWith("chk_poll_456");
    expect(screen.getByTestId("patient-explanation-box")).toBeTruthy();

    vi.useRealTimers();
  });
});
