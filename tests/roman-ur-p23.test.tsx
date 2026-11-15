// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { translations } from "../app/translations";
import { AdaptiveInterviewScreen } from "../app/components/AdaptiveInterviewScreen";
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

window.HTMLElement.prototype.scrollIntoView = vi.fn();

describe("P3-23 Roman Urdu translations and chip display parity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("provides Roman Urdu translations for assist controls and confirmation", () => {
    const tRo = translations.roman_ur;
    expect(tRo.whyAmIAskedThisBtn).toBe("Yeh kyun poocha ja raha hai?");
    expect(tRo.dontKnowBtn).toBe("Maloom nahi");
    expect(tRo.skipQuestionBtn).toBe("Chhor dein");
    expect(tRo.someoneElseAnsweringBtn).toBe("Koi aur jawab de raha hai");
    expect(tRo.submitCheckInBtn).toBe("Check-in jama karein");
    expect(tRo.confirmationTitle).toBe("Check-in jama ho gaya!");
  });

  it("displays tapped chip label in chat conversation history rather than English value", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.isRomanUrdu = true;
    mockAppContext.language = "roman_ur";
    mockAppContext.t = translations.roman_ur;
    mockAppContext.checkIn = { note: "" };
    mockAppContext.liveProfile = { voice_enabled: false };
    mockAppContext.activeLiveCheckin = {
      checkin_id: "chk-v3-ro-1",
      question: "Kya aap ko kisi qisam ki takleef hai?",
      mode: "live",
      is_cold_start: false,
      step: "hyperglycemia_symptoms",
      version: 0,
      options: ["Haan", "Nahi"],
      option_items: [
        { value: "yes", label: "Haan" },
        { value: "no", label: "Nahi" },
      ],
      progress_hint: "2/8",
      can_skip: true,
      can_say_unknown: true,
    };
    mockAppContext.setActiveLiveCheckin = vi.fn();

    vi.mocked(api.answerCheckin).mockResolvedValue({
      engine: "v3",
      question: "Agla sawal?",
      complete: false,
      step: "adherence",
      options: ["Haan", "Nahi"],
      option_items: [
        { value: "yes", label: "Haan" },
        { value: "no", label: "Nahi" },
      ],
    } as any);

    render(<AdaptiveInterviewScreen />);

    // Find and click the localized chip "Nahi"
    const chipBtn = await screen.findByRole("button", { name: "Nahi" });
    fireEvent.click(chipBtn);

    // Verify backend received canonical value "no"
    await waitFor(() => {
      expect(api.answerCheckin).toHaveBeenCalledWith(
        "chk-v3-ro-1",
        "no",
        "hyperglycemia_symptoms"
      );
    });

    // Verify the chat bubble renders the tapped label "Nahi", NOT "no"
    expect(screen.getAllByText("Nahi").length).toBeGreaterThanOrEqual(2);
    // And ensure no bubble literally displays "no"
    const noElements = screen.queryAllByText("no");
    expect(noElements.length).toBe(0);
  });
});
