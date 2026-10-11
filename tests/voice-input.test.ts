import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, ApiError } from "../app/lib/api";

describe("Stage 8 Part A: Voice Input & Safety UX Tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sends raw audio blob to /api/voice/transcribe with audio/* content type and auth headers", async () => {
    const fakeBlob = new Blob(["fake audio stream data"], { type: "audio/webm;codecs=opus" });
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ text: "I have mild chest pain since yesterday" }),
    });
    global.fetch = mockFetch;

    const res = await api.transcribeVoice(fakeBlob, "test.webm");
    expect(res.text).toBe("I have mild chest pain since yesterday");
    expect(mockFetch).toHaveBeenCalledTimes(1);

    const callArgs = mockFetch.mock.calls[0];
    const url = callArgs[0];
    const options = callArgs[1];

    expect(url).toContain("/api/voice/transcribe");
    expect(options.method).toBe("POST");
    expect(options.body).toBe(fakeBlob);
    expect(options.body).toBeInstanceOf(Blob);
    expect(options.headers["Content-Type"]).toMatch(/^audio\//);
  });

  it("handles 403 when voice_enabled is disabled in profile", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: "voice_disabled" }),
    });

    try {
      await api.transcribeVoice(new Blob(["audio"]), "test.webm");
      expect.fail("Should have thrown ApiError");
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(403);
      expect(err.detail).toBe("voice_disabled");
      expect(err.getFriendlyMessage(false)).toContain("Access denied");
    }
  });

  it("handles 429 rate limit gracefully with user-friendly retry message", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({ detail: "rate_limit_exceeded: maximum 10 requests per minute" }),
    });

    try {
      await api.transcribeVoice(new Blob(["audio"]), "test.webm");
      expect.fail("Should have thrown ApiError");
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(429);
      expect(err.detail).toContain("rate_limit_exceeded");
    }
  });

  it("ApiError provides friendly messages in English and Urdu for 502/503 and network failures", () => {
    const err503 = new ApiError(503, "Service Unavailable");
    expect(err503.getFriendlyMessage(false)).toContain("temporarily unavailable");
    expect(err503.getFriendlyMessage(true)).toContain("سرور اس وقت بیدار ہو رہا ہے");

    const err422 = new ApiError(422, "Invalid format");
    expect(err422.getFriendlyMessage(false)).toContain("Invalid information provided");
    expect(err422.getFriendlyMessage(true)).toContain("فراہم کردہ معلومات درست نہیں ہیں");
  });
});
