// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { ExplanationBox } from "../app/components/ExplanationBox";
import { EmergencyScreen } from "../app/components/EmergencyScreen";
import { translations } from "../app/translations";
import { api, PatientExplanation } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("TTS Listen Button & Speech Integration (Part I4-I)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.liveCheckinResult = null;
    mockAppContext.activeLiveCheckin = { checkin_id: "chk-123" };
    mockAppContext.escalationRecorded = false;
    mockAppContext.returnToHomeAndClearRun = vi.fn();

    // Mock Audio API
    window.HTMLMediaElement.prototype.play = vi.fn().mockImplementation(function (this: any) {
      if (this.onplay) this.onplay();
      return Promise.resolve();
    });
    window.HTMLMediaElement.prototype.pause = vi.fn();

    // Mock URL.createObjectURL and revokeObjectURL
    window.URL.createObjectURL = vi.fn(() => "blob:http://localhost/fake-audio");
    window.URL.revokeObjectURL = vi.fn();

    // Default voice status: enabled
    vi.spyOn(api, "getVoiceStatus").mockResolvedValue({ tts_enabled: true });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders Listen button in English inside ExplanationBox when expanded", async () => {
    const explanation: PatientExplanation = {
      status: "ready",
      sentences: [
        { text: "Your blood pressure is within expected clinical range [c1].", cites: ["c1"] },
      ],
      sources: [],
    };

    render(<ExplanationBox explanation={explanation} emergency={false} checkinId="chk-123" />);

    // Expand accordion
    const toggleBtn = screen.getByTestId("explanation-toggle-btn");
    fireEvent.click(toggleBtn);

    const listenBtn = await screen.findByTestId("explanation-speech-btn");
    expect(listenBtn).toBeDefined();
    expect(listenBtn.textContent).toContain("Listen");

    // Mock speech api
    const fakeBlob = new Blob(["RIFFfakeWAVdata"], { type: "audio/wav" });
    const speechSpy = vi.spyOn(api, "getCheckinSpeech").mockResolvedValue(fakeBlob);

    fireEvent.click(listenBtn);

    expect(speechSpy).toHaveBeenCalledWith("chk-123");
    await waitFor(() => {
      expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalled();
    });
  });

  it("renders Listen button in Urdu inside ExplanationBox when isUrdu is true", async () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    const explanation: PatientExplanation = {
      status: "ready",
      sentences: [
        { text: "آپ کا بلڈ پریشر معمول کے مطابق ہے [c1]۔", cites: ["c1"] },
      ],
      sources: [],
    };

    render(<ExplanationBox explanation={explanation} emergency={false} checkinId="chk-123" />);

    const toggleBtn = screen.getByTestId("explanation-toggle-btn");
    fireEvent.click(toggleBtn);

    const listenBtn = await screen.findByTestId("explanation-speech-btn");
    expect(listenBtn.textContent).toContain("وضاحت سنیں");
  });

  it("handles speech errors gracefully in ExplanationBox without showing raw server error", async () => {
    const explanation: PatientExplanation = {
      status: "ready",
      sentences: [
        { text: "Your blood pressure is elevated.", cites: [] },
      ],
      sources: [],
    };

    vi.spyOn(api, "getCheckinSpeech").mockRejectedValue(new Error("500 Internal Server Traceback raw error"));

    render(<ExplanationBox explanation={explanation} emergency={false} checkinId="chk-123" />);

    const toggleBtn = screen.getByTestId("explanation-toggle-btn");
    fireEvent.click(toggleBtn);

    const listenBtn = await screen.findByTestId("explanation-speech-btn");
    fireEvent.click(listenBtn);

    await waitFor(() => {
      const errorMsg = screen.getByTestId("explanation-speech-error");
      expect(errorMsg.textContent).toBe("Voice output unavailable");
      // Raw server error should never leak
      expect(screen.queryByText(/500 Internal Server Traceback/i)).toBeNull();
    });
  });

  it("renders Listen to Instructions button on EmergencyScreen and triggers speech", async () => {
    const fakeBlob = new Blob(["RIFFfakeWAVdata"], { type: "audio/wav" });
    const emergencySpeechSpy = vi.spyOn(api, "getEmergencySpeech").mockResolvedValue(fakeBlob);

    render(<EmergencyScreen />);

    const speechBtn = await screen.findByTestId("emergency-speech-btn");
    expect(speechBtn.textContent).toContain("Listen to Instructions");

    fireEvent.click(speechBtn);

    expect(emergencySpeechSpy).toHaveBeenCalledWith("en");
    await waitFor(() => {
      expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalled();
    });
  });

  it("renders EmergencyScreen speech button in Urdu when isUrdu is true", async () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    const fakeBlob = new Blob(["RIFFfakeWAVdata"], { type: "audio/wav" });
    const emergencySpeechSpy = vi.spyOn(api, "getEmergencySpeech").mockResolvedValue(fakeBlob);

    render(<EmergencyScreen />);

    const speechBtn = await screen.findByTestId("emergency-speech-btn");
    expect(speechBtn.textContent).toContain("ایمرجنسی ہدایات سنیں");

    fireEvent.click(speechBtn);

    expect(emergencySpeechSpy).toHaveBeenCalledWith("ur");
  });

  it("handles EmergencyScreen speech errors gracefully without leaking raw server error", async () => {
    vi.spyOn(api, "getEmergencySpeech").mockRejectedValue(new Error("502 Bad Gateway Nginx stack"));

    render(<EmergencyScreen />);

    const speechBtn = await screen.findByTestId("emergency-speech-btn");
    fireEvent.click(speechBtn);

    await waitFor(() => {
      const errorMsg = screen.getByTestId("emergency-speech-error");
      expect(errorMsg.textContent).toBe("Voice output unavailable");
      expect(screen.queryByText(/502 Bad Gateway/i)).toBeNull();
    });
  });

  describe("Voice Flag Gating (TTS_ENABLED)", () => {
    it("hides Listen button in ExplanationBox when voice is off (tts_enabled=false)", async () => {
      vi.spyOn(api, "getVoiceStatus").mockResolvedValue({ tts_enabled: false });

      const explanation: PatientExplanation = {
        status: "ready",
        sentences: [{ text: "Normal findings.", cites: [] }],
        sources: [],
      };

      render(<ExplanationBox explanation={explanation} emergency={false} checkinId="chk-off" />);

      const toggleBtn = screen.getByTestId("explanation-toggle-btn");
      fireEvent.click(toggleBtn);

      await waitFor(() => {
        expect(screen.getByTestId("explanation-content")).toBeDefined();
      });

      expect(screen.queryByTestId("explanation-speech-btn")).toBeNull();
    });

    it("hides Listen to Instructions button on EmergencyScreen when voice is off (tts_enabled=false)", async () => {
      vi.spyOn(api, "getVoiceStatus").mockResolvedValue({ tts_enabled: false });

      render(<EmergencyScreen />);

      await waitFor(() => {
        expect(screen.getByTestId("emergency-alert-status-text")).toBeDefined();
      });

      expect(screen.queryByTestId("emergency-speech-btn")).toBeNull();

      // Invariant: 1122 call shortcut remains visible and unchanged
      const call1122 = screen.getByRole("link", { name: /1122/i });
      expect(call1122).toBeDefined();
      expect(call1122.getAttribute("href")).toBe("tel:1122");
    });

    it("preserves 1122 call button as first and unchanged regardless of voice flag", async () => {
      vi.spyOn(api, "getVoiceStatus").mockResolvedValue({ tts_enabled: true });

      render(<EmergencyScreen />);

      const call1122 = screen.getByRole("link", { name: /1122/i });
      expect(call1122).toBeDefined();
      expect(call1122.getAttribute("href")).toBe("tel:1122");
    });
  });
});
