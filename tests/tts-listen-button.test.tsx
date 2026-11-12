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

    const listenBtn = screen.getByTestId("explanation-speech-btn");
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

    const listenBtn = screen.getByTestId("explanation-speech-btn");
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

    const listenBtn = screen.getByTestId("explanation-speech-btn");
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

    const speechBtn = screen.getByTestId("emergency-speech-btn");
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

    const speechBtn = screen.getByTestId("emergency-speech-btn");
    expect(speechBtn.textContent).toContain("ایمرجنسی ہدایات سنیں");

    fireEvent.click(speechBtn);

    expect(emergencySpeechSpy).toHaveBeenCalledWith("ur");
  });

  it("handles EmergencyScreen speech errors gracefully without leaking raw server error", async () => {
    vi.spyOn(api, "getEmergencySpeech").mockRejectedValue(new Error("502 Bad Gateway Nginx stack"));

    render(<EmergencyScreen />);

    const speechBtn = screen.getByTestId("emergency-speech-btn");
    fireEvent.click(speechBtn);

    await waitFor(() => {
      const errorMsg = screen.getByTestId("emergency-speech-error");
      expect(errorMsg.textContent).toBe("Voice output unavailable");
      expect(screen.queryByText(/502 Bad Gateway/i)).toBeNull();
    });
  });
});
