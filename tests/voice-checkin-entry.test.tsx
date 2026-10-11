// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act, cleanup } from "@testing-library/react";
import { CheckInEntryScreen } from "../app/components/CheckInEntryScreen";
import { translations } from "../app/translations";
import { api, ApiError } from "../app/lib/api";

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
      transcribeVoice: vi.fn(),
    },
  };
});

class MockMediaRecorder {
  state = "inactive";
  mimeType = "audio/webm";
  ondataavailable: ((e: any) => void) | null = null;
  onstop: (() => void) | null = null;
  static isTypeSupported = vi.fn().mockReturnValue(true);

  start() {
    this.state = "recording";
  }

  stop() {
    this.state = "inactive";
    if (this.ondataavailable) {
      this.ondataavailable({ data: new Blob(["recorded audio bytes longer than 100 bytes to pass size check 1234567890123456789012345678901234567890123456789012345678901234567890"], { type: "audio/webm" }) });
    }
    if (this.onstop) {
      this.onstop();
    }
  }
}

describe("STAGE 10E-0 Bug 2: CheckInEntryScreen voice recording", () => {
  const originalMediaDevices = navigator.mediaDevices;
  const originalMediaRecorder = (global as any).MediaRecorder;

  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    (global as any).MediaRecorder = MockMediaRecorder;
    Object.defineProperty(navigator, "mediaDevices", {
      value: {
        getUserMedia: vi.fn(),
      },
      writable: true,
      configurable: true,
    });

    Object.assign(mockAppContext, {
      setScreen: vi.fn(),
      returnToHomeAndClearRun: vi.fn(),
      checkIn: { note: "" },
      setCheckIn: vi.fn(),
      profile: { conditions: ["Type 2 Diabetes"] },
      liveProfile: null,
      isLiveMode: false,
      t: translations.en,
      isUrdu: false,
    });
  });

  afterEach(() => {
    cleanup();
    Object.defineProperty(navigator, "mediaDevices", {
      value: originalMediaDevices,
      writable: true,
      configurable: true,
    });
    (global as any).MediaRecorder = originalMediaRecorder;
    vi.useRealTimers();
  });

  it("demo mode: clicking voice button does NOT call getUserMedia, shows demo sample badge and fills sample note after timeout", () => {
    vi.useFakeTimers();
    mockAppContext.isLiveMode = false;

    render(<CheckInEntryScreen />);
    const voiceBtn = screen.getByRole("button", { name: translations.en.voiceInputTitle });
    const textarea = screen.getByPlaceholderText(translations.en.howAreYouFeelingPlaceholder);

    expect(screen.getByText(translations.en.demoVoiceSampleBadge)).toBeDefined();

    fireEvent.click(voiceBtn);

    // getUserMedia must NOT be called in demo mode
    expect(navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled();

    // Fast-forward 2 seconds
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect((textarea as HTMLTextAreaElement).value).toBe(translations.en.sampleVoiceNoteDiabetes);
  });

  it("live mode: clicking voice button calls getUserMedia and does NOT insert fake sample text", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.liveProfile = { voice_enabled: true, conditions: ["Type 2 Diabetes"] };

    const mockStream = {
      getTracks: vi.fn().mockReturnValue([{ stop: vi.fn() }]),
    };
    (navigator.mediaDevices.getUserMedia as any).mockResolvedValue(mockStream);

    render(<CheckInEntryScreen />);
    const voiceBtn = screen.getByRole("button", { name: translations.en.voiceInputTitle });
    const textarea = screen.getByPlaceholderText(translations.en.howAreYouFeelingPlaceholder);

    await act(async () => {
      fireEvent.click(voiceBtn);
    });

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
    // Textarea must not contain hardcoded demo voice sample
    expect((textarea as HTMLTextAreaElement).value).toBe("");
    expect(screen.queryByText(translations.en.demoVoiceSampleBadge)).toBeNull();
  });

  it("live mode: permission denied shows clear microphone error message", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.liveProfile = { voice_enabled: true };

    (navigator.mediaDevices.getUserMedia as any).mockRejectedValue(new Error("Permission denied"));

    render(<CheckInEntryScreen />);
    const voiceBtn = screen.getByRole("button", { name: translations.en.voiceInputTitle });

    await act(async () => {
      fireEvent.click(voiceBtn);
    });

    expect(
      screen.getByText("Microphone access denied. Please allow microphone permissions or type your answer.")
    ).toBeDefined();
  });

  it("live mode: voice disabled in profile settings shows disabled message immediately", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.liveProfile = { voice_enabled: false };

    render(<CheckInEntryScreen />);
    const voiceBtn = screen.getByRole("button", { name: translations.en.voiceInputTitle });

    await act(async () => {
      fireEvent.click(voiceBtn);
    });

    expect(navigator.mediaDevices.getUserMedia).not.toHaveBeenCalled();
    expect(
      screen.getByText("Voice input is disabled in your profile. Enable it in Settings (Privacy & Consent) to speak your answers.")
    ).toBeDefined();
  });

  it("live mode: stopping recording calls api.transcribeVoice and fills note with real transcribed text", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.liveProfile = { voice_enabled: true };

    const mockStream = {
      getTracks: vi.fn().mockReturnValue([{ stop: vi.fn() }]),
    };
    (navigator.mediaDevices.getUserMedia as any).mockResolvedValue(mockStream);
    (api.transcribeVoice as any).mockResolvedValue({ text: "Feeling slightly nauseous after taking morning dose" });

    render(<CheckInEntryScreen />);
    const voiceBtn = screen.getByRole("button", { name: translations.en.voiceInputTitle });
    const textarea = screen.getByPlaceholderText(translations.en.howAreYouFeelingPlaceholder);

    // Start recording
    await act(async () => {
      fireEvent.click(voiceBtn);
    });

    // Stop recording by clicking again
    await act(async () => {
      fireEvent.click(voiceBtn);
    });

    await waitFor(() => {
      expect(api.transcribeVoice).toHaveBeenCalledTimes(1);
    });

    expect((textarea as HTMLTextAreaElement).value).toBe("Feeling slightly nauseous after taking morning dose");
  });
});
