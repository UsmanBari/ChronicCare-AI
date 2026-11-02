// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AdaptiveInterviewScreen } from "../app/components/AdaptiveInterviewScreen";
import { translations } from "../app/translations";
import { api } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

vi.mock("../app/lib/api", async () => {
  const actual: any = await vi.importActual("../app/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      startCheckin: vi.fn(),
      answerCheckin: vi.fn(),
      completeCheckin: vi.fn(),
    },
  };
});

// Mock scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

describe("Adaptive Interview Urdu & Localized Options Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders option_items labels in Urdu, sends canonical value, and applies RTL", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = true;
    mockAppContext.language = "ur";
    mockAppContext.t = translations.ur;
    mockAppContext.checkIn = { note: "" };
    mockAppContext.liveProfile = { voice_enabled: false };
    mockAppContext.activeLiveCheckin = {
      checkin_id: "chk-v3-urdu-1",
      question: "کیا آپ نے آج اپنی شوگر کی دوا لی؟",
      mode: "live",
      is_cold_start: false,
      step: "diabetes_adherence",
      version: 0,
      why_text: "یہ جاننا ضروری ہے کہ کیا آپ نے دوا باقاعدگی سے لی۔",
      options: ["yes", "no"],
      option_items: [
        { value: "yes", label: "ہاں" },
        { value: "no", label: "نہیں" },
      ],
      progress_hint: "1/8",
      can_skip: true,
      can_say_unknown: true,
    };
    mockAppContext.setActiveLiveCheckin = vi.fn();
    mockAppContext.setLiveCheckinResult = vi.fn();
    mockAppContext.setEscalationRecorded = vi.fn();
    mockAppContext.setShowSettings = vi.fn();
    mockAppContext.setScreen = vi.fn();

    vi.mocked(api.answerCheckin).mockResolvedValueOnce({
      question: "آپ کا بلڈ پریشر کیا ہے؟",
      complete: false,
      emergency: false,
      emergency_reason: null,
      step: "hypertension_bp_reading",
      version: 1,
      options: null,
      option_items: null,
    });

    const { container } = render(<AdaptiveInterviewScreen />);

    // 1. Verify RTL attribute is applied
    const rootDiv = container.querySelector('[dir="rtl"]');
    expect(rootDiv).not.toBeNull();

    // 2. Verify localized option labels are rendered
    const yesBtn = screen.getByRole("button", { name: "ہاں" });
    const noBtn = screen.getByRole("button", { name: "نہیں" });
    expect(yesBtn).toBeDefined();
    expect(noBtn).toBeDefined();

    // 3. Click the localized "ہاں" button and verify canonical "yes" is submitted to backend
    fireEvent.click(yesBtn);

    await waitFor(() => {
      expect(api.answerCheckin).toHaveBeenCalledWith(
        "chk-v3-urdu-1",
        "yes",
        "diabetes_adherence"
      );
    });
  });

  it("falls back gracefully to v2 string options when option_items is absent", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.language = "en";
    mockAppContext.t = translations.en;
    mockAppContext.checkIn = { note: "" };
    mockAppContext.liveProfile = { voice_enabled: false };
    mockAppContext.activeLiveCheckin = {
      checkin_id: "chk-v2-fallback",
      question: "Did you take your medication today?",
      mode: "live",
      is_cold_start: false,
      step: "q_adherence",
      version: 0,
      options: ["Yes, taken", "No, missed"],
      option_items: null, // v2 legacy mode
    };
    mockAppContext.setActiveLiveCheckin = vi.fn();
    mockAppContext.setLiveCheckinResult = vi.fn();
    mockAppContext.setEscalationRecorded = vi.fn();
    mockAppContext.setShowSettings = vi.fn();
    mockAppContext.setScreen = vi.fn();

    vi.mocked(api.answerCheckin).mockResolvedValueOnce({
      question: "Thank you",
      complete: true,
      emergency: false,
      emergency_reason: null,
      step: "COMPLETE",
      version: 1,
    });

    render(<AdaptiveInterviewScreen />);

    // Verify v2 string buttons are rendered
    const yesTakenBtn = screen.getByRole("button", { name: "Yes, taken" });
    expect(yesTakenBtn).toBeDefined();

    fireEvent.click(yesTakenBtn);

    await waitFor(() => {
      expect(api.answerCheckin).toHaveBeenCalledWith(
        "chk-v2-fallback",
        "Yes, taken",
        "q_adherence"
      );
    });
  });
});

