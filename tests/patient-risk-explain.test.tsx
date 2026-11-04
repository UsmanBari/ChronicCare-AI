// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { PatientRiskCard } from "../app/components/PatientRiskCard";
import { ExplanationBox } from "../app/components/ExplanationBox";
import { RiskResultScreen } from "../app/components/RiskResultScreen";
import { RoutedToReviewScreen } from "../app/components/RoutedToReviewScreen";
import { translations } from "../app/translations";
import { PatientRisk, PatientExplanation, CheckinCompleteResponse } from "../app/lib/api";

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

describe("Patient Risk Card & Explanation Box (I3 Day 2)", () => {
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
  // 1. Flags Off Invariant (Screens render exactly as before)
  // -------------------------------------------------------------------------
  it("renders RiskResultScreen unchanged when flags are off (risk and explanation null)", () => {
    const baselineResult: CheckinCompleteResponse = {
      emergency: false,
      intakes: [],
      reconciliation: { summary: { agreement: 2, source_a_only: 0, source_b_only: 0 } },
      verification: null,
      requires_review: false,
      max_severity: null,
      risk: null,
      explanation: null,
    };
    mockAppContext.liveCheckinResult = baselineResult;

    render(<RiskResultScreen />);

    // Verify new components are completely absent
    expect(screen.queryByTestId("patient-risk-card")).toBeNull();
    expect(screen.queryByTestId("patient-explanation-box")).toBeNull();

    // Verify baseline scope note is still rendered
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
      risk: null,
      explanation: null,
    };
    mockAppContext.liveCheckinResult = reviewResult;

    render(<RoutedToReviewScreen />);

    expect(screen.queryByTestId("patient-risk-card")).toBeNull();
    expect(screen.queryByTestId("patient-explanation-box")).toBeNull();
    expect(screen.getByText("Pending Provider Review")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 2. PatientRiskCard States: ok, not_enough_information, null, error
  // -------------------------------------------------------------------------
  describe("PatientRiskCard states", () => {
    it("renders qualitative band (low) and up to 3 contributing reasons with <bdi> when status is ok", () => {
      const okRisk: PatientRisk = {
        status: "ok",
        band: "low",
        reasons: [
          {
            feature: "told_high_bp",
            contribution: 0.156,
            label: { en: "history of high blood pressure", ur: "ہائی بلڈ پریشر کی تاریخ" },
          },
          {
            feature: "age",
            contribution: 0.1168,
            label: { en: "your age", ur: "آپ کی عمر" },
          },
          {
            feature: "sbp",
            contribution: 0.104,
            label: { en: "your recent blood pressure", ur: "آپ کا حالیہ بلڈ پریشر" },
          },
          {
            feature: "bmi",
            contribution: 0.08,
            label: { en: "elevated body mass index", ur: "وزن کی زیادتی" },
          },
        ],
        advisory: "Advisory risk assessment, not a clinical diagnosis. Consult your healthcare provider.",
      };

      render(<PatientRiskCard risk={okRisk} emergency={false} />);

      const card = screen.getByTestId("patient-risk-card");
      expect(card).toBeTruthy();

      // Accessible Badge (text + icon, never color alone)
      const badge = screen.getByTestId("patient-risk-badge");
      expect(badge.textContent).toContain(translations.en.riskLowTitle);

      // Exactly 3 top reasons rendered (4th sliced off)
      const reasonItems = screen.getAllByTestId("patient-risk-reason-item");
      expect(reasonItems.length).toBe(3);
      expect(reasonItems[0].textContent).toContain("history of high blood pressure");
      expect(reasonItems[1].textContent).toContain("your age");
      expect(reasonItems[2].textContent).toContain("your recent blood pressure");

      // Verify <bdi> tag wraps reason content
      const bdiElements = card.querySelectorAll("bdi");
      expect(bdiElements.length).toBe(3);
      expect(bdiElements[0].textContent).toBe("history of high blood pressure");

      // Advisory notice
      expect(card.textContent).toContain(translations.en.patientRiskAdvisory);
    });

    it("renders moderate and high risk badges correctly with accessible icons", () => {
      const moderateRisk: PatientRisk = {
        status: "ok",
        band: "moderate",
        reasons: [{ feature: "sbp", label: { en: "elevated blood pressure", ur: "بلند فشار خون" } }],
      };
      const { unmount } = render(<PatientRiskCard risk={moderateRisk} emergency={false} />);
      expect(screen.getByTestId("patient-risk-badge").textContent).toContain(translations.en.riskModerateTitle);
      unmount();

      const highRisk: PatientRisk = {
        status: "ok",
        band: "high",
        reasons: [{ feature: "sbp", label: { en: "stage 2 blood pressure", ur: "اسٹیج 2 بلڈ پریشر" } }],
      };
      render(<PatientRiskCard risk={highRisk} emergency={false} />);
      expect(screen.getByTestId("patient-risk-badge").textContent).toContain(translations.en.riskHighTitle);
    });

    it("renders not_enough_information state with single guidance line (waist circumference)", () => {
      const missingRisk: PatientRisk = {
        status: "not_enough_information",
        band: null,
        reasons: [],
        advisory: "Advisory risk assessment, not a clinical diagnosis. Consult your healthcare provider.",
      };

      render(<PatientRiskCard risk={missingRisk} emergency={false} />);

      const card = screen.getByTestId("patient-risk-card");
      expect(card).toBeTruthy();
      expect(screen.getByText(translations.en.patientRiskMissingWaist)).toBeTruthy();
      expect(screen.queryByTestId("patient-risk-badge")).toBeNull();
      expect(screen.queryByTestId("patient-risk-reasons")).toBeNull();
    });

    it("renders null (nothing) when risk is null, undefined, error, or not_applicable", () => {
      const { rerender } = render(<PatientRiskCard risk={null} emergency={false} />);
      expect(screen.queryByTestId("patient-risk-card")).toBeNull();

      rerender(<PatientRiskCard risk={undefined} emergency={false} />);
      expect(screen.queryByTestId("patient-risk-card")).toBeNull();

      const errorRisk: PatientRisk = { status: "error" };
      rerender(<PatientRiskCard risk={errorRisk} emergency={false} />);
      expect(screen.queryByTestId("patient-risk-card")).toBeNull();

      const notApplicableRisk: PatientRisk = { status: "not_applicable" };
      rerender(<PatientRiskCard risk={notApplicableRisk} emergency={false} />);
      expect(screen.queryByTestId("patient-risk-card")).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // 3. Strict Anti-Leak Invariant: ZERO numbers or "%" in the patient card
  // -------------------------------------------------------------------------
  it("enforces strict anti-leak invariant: NO percentage or numeric probabilities anywhere in the card DOM", () => {
    const okRisk: PatientRisk = {
      status: "ok",
      band: "low",
      reasons: [
        {
          feature: "told_high_bp",
          contribution: 0.156,
          label: { en: "history of high blood pressure", ur: "ہائی بلڈ پریشر کی تاریخ" },
        },
        {
          feature: "age",
          contribution: 0.1168,
          label: { en: "your age", ur: "آپ کی عمر" },
        },
      ],
      advisory: "Advisory risk assessment, not a clinical diagnosis. Consult your healthcare provider.",
    };

    render(<PatientRiskCard risk={okRisk} emergency={false} />);

    const card = screen.getByTestId("patient-risk-card");
    const text = card.textContent || "";

    // 1. No percent character
    expect(text.includes("%")).toBe(false);

    // 2. No floating-point or integer probabilities
    expect(/\b0\.\d+\b/.test(text)).toBe(false);
    expect(/\b\d+(\.\d+)?%/.test(text)).toBe(false);

    // 3. No internal machine-learning terminology
    expect(text.toLowerCase()).not.toContain("nhanes");
    expect(text.toLowerCase()).not.toContain("model");
    expect(text.toLowerCase()).not.toContain("version");
    expect(text.toLowerCase()).not.toContain("logit");
  });

  // -------------------------------------------------------------------------
  // 4. ExplanationBox: Collapsed/Expand, Sources, Keyboard & Template Mode
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
  // 5. Emergency Invariant: NEVER shown during an emergency
  // -------------------------------------------------------------------------
  it("never renders risk card or explanation box during an emergency check-in", () => {
    const okRisk: PatientRisk = {
      status: "ok",
      band: "high",
      reasons: [{ feature: "sbp", label: { en: "crisis bp", ur: "شدید بلڈ پریشر" } }],
    };
    const sampleExplanation: PatientExplanation = {
      status: "ok",
      sentences: [{ text: "Emergency vitals require immediate intervention." }],
      sources: [],
    };

    // Explicitly pass emergency=true
    render(
      <div>
        <PatientRiskCard risk={okRisk} emergency={true} />
        <ExplanationBox explanation={sampleExplanation} emergency={true} />
      </div>
    );

    expect(screen.queryByTestId("patient-risk-card")).toBeNull();
    expect(screen.queryByTestId("patient-explanation-box")).toBeNull();
  });

  // -------------------------------------------------------------------------
  // 6. Urdu Language, RTL, and Nastaliq Typography
  // -------------------------------------------------------------------------
  it("renders risk card and explanation box in Urdu with dir='rtl', font-urdu, and <bdi> protection", () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    const urduRisk: PatientRisk = {
      status: "ok",
      band: "moderate",
      reasons: [
        {
          feature: "told_high_bp",
          contribution: 0.156,
          label: { en: "history of high blood pressure", ur: "ہائی بلڈ پریشر کی تاریخ" },
        },
      ],
      advisory: "مشاورتی خطرے کا تخمینہ، طبی تشخیص نہیں۔ اپنے ہیلتھ کیئر فراہم کنندہ سے مشورہ کریں۔",
    };

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
        <PatientRiskCard risk={urduRisk} emergency={false} />
        <ExplanationBox explanation={urduExplanation} emergency={false} />
      </div>
    );

    const card = screen.getByTestId("patient-risk-card");
    expect(card.getAttribute("dir")).toBe("rtl");
    expect(card.className).toContain("font-urdu");

    // Urdu badge and reasons
    expect(screen.getByTestId("patient-risk-badge").textContent).toContain("معتدل خطرہ");
    const reasonItem = screen.getByTestId("patient-risk-reason-item");
    expect(reasonItem.textContent).toContain("ہائی بلڈ پریشر کی تاریخ");
    expect(reasonItem.querySelector("bdi")?.textContent).toBe("ہائی بلڈ پریشر کی تاریخ");

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
  // 7. Live Mode Never Shows Fixed Demo Example
  // -------------------------------------------------------------------------
  it("never shows the 'Example' demo label when in live mode", () => {
    mockAppContext.isLiveMode = true;

    const okRisk: PatientRisk = {
      status: "ok",
      band: "low",
      reasons: [{ feature: "age", label: { en: "your age", ur: "آپ کی عمر" } }],
    };
    const expl: PatientExplanation = {
      status: "ok",
      sentences: [{ text: "Reading is in target." }],
      sources: [],
    };

    render(
      <div>
        <PatientRiskCard risk={okRisk} emergency={false} isDemo={false} />
        <ExplanationBox explanation={expl} emergency={false} isDemo={false} />
      </div>
    );

    const card = screen.getByTestId("patient-risk-card");
    expect(card.textContent).not.toContain("Example");
    expect(card.textContent).not.toContain("مثال");

    const toggleBtn = screen.getByTestId("explanation-toggle-btn");
    expect(toggleBtn.textContent).not.toContain("Example");
    expect(toggleBtn.textContent).not.toContain("مثال");
  });
});

