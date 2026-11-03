import { describe, it, expect } from "vitest";
import { mapMicrophoneError } from "../app/lib/useVoiceRecorder";

describe("Bug Bash #86: Microphone Error Localization & Safe Mappings", () => {
  const errorCases = [
    { name: "NotAllowedError", message: "Permission denied" },
    { name: "NotFoundError", message: "Requested device not found" },
    { name: "NotReadableError", message: "Could not start audio source" },
    { name: "UnknownError", message: "Something went wrong" },
  ];

  describe("Urdu mappings (zero raw English error leaks)", () => {
    it.each(errorCases)("maps $name in Urdu with actionable next step and no English leak", (err) => {
      const domError = new Error(err.message);
      domError.name = err.name;

      const result = mapMicrophoneError(domError, true);

      // Must never contain raw English error class names
      expect(result).not.toContain("NotAllowedError");
      expect(result).not.toContain("NotFoundError");
      expect(result).not.toContain("NotReadableError");
      expect(result).not.toContain("Permission denied");

      // Must contain actionable next steps in Urdu (settings / permissions / type your answer)
      expect(result).toContain("ٹائپ کریں");
    });

    it("maps NotAllowedError specifically to browser settings guidance in Urdu", () => {
      const err = { name: "NotAllowedError", message: "Permission denied" };
      const result = mapMicrophoneError(err, true);
      expect(result).toContain("مائیکروفون کی اجازت نہیں ملی");
      expect(result).toContain("براؤزر کی ترتیبات");
      expect(result).toContain("ٹائپ کریں");
    });

    it("maps NotFoundError specifically to device connection guidance in Urdu", () => {
      const err = { name: "NotFoundError", message: "Requested device not found" };
      const result = mapMicrophoneError(err, true);
      expect(result).toContain("مائیکروفون نہیں ملا");
      expect(result).toContain("ٹائپ کریں");
    });

    it("maps NotReadableError specifically to hardware/busy guidance in Urdu", () => {
      const err = { name: "NotReadableError", message: "Device in use" };
      const result = mapMicrophoneError(err, true);
      expect(result).toContain("مصروف");
      expect(result).toContain("ٹائپ کریں");
    });
  });

  describe("English mappings with actionable next steps", () => {
    it("maps NotAllowedError to browser settings guidance in English", () => {
      const err = { name: "NotAllowedError", message: "Permission denied" };
      const result = mapMicrophoneError(err, false);
      expect(result).not.toContain("NotAllowedError");
      expect(result).toContain("browser settings");
      expect(result).toContain("type your answer instead");
    });

    it("maps NotFoundError to connection guidance in English", () => {
      const err = { name: "NotFoundError", message: "No mic" };
      const result = mapMicrophoneError(err, false);
      expect(result).not.toContain("NotFoundError");
      expect(result).toContain("No microphone found");
      expect(result).toContain("type your answer instead");
    });

    it("maps NotReadableError to hardware in-use guidance in English", () => {
      const err = { name: "NotReadableError", message: "Audio device occupied" };
      const result = mapMicrophoneError(err, false);
      expect(result).not.toContain("NotReadableError");
      expect(result).toContain("busy");
      expect(result).toContain("type your answer instead");
    });

    it("maps unknown error to safe fallback guidance in English", () => {
      const err = { name: "CustomError", message: "Crash" };
      const result = mapMicrophoneError(err, false);
      expect(result).not.toContain("CustomError");
      expect(result).toContain("type your answer instead");
    });
  });
});

