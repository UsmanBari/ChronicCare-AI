// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { translations } from "../app/translations";
import {
  HealthProfileScreen,
  cmToFtIn,
  ftInToCm,
  kgToLb,
  lbToKg,
} from "../app/components/HealthProfileScreen";
import { api, ProfileUpdateRequest } from "../app/lib/api";

const ctx: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => ctx,
}));

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => false,
  isFirebaseConfigured: () => false,
  getFirebaseAuth: () => null,
  getAuthErrorMessage: () => "",
}));

function setContext(lang: "en" | "ur", overrides: Record<string, any> = {}) {
  for (const k of Object.keys(ctx)) delete ctx[k];
  Object.assign(ctx, {
    language: lang,
    t: translations[lang],
    isUrdu: lang === "ur",
    setLanguage: vi.fn(),
    connectionMode: null,
    portal: "patient",
    screen: "profile",
    providerScreen: "dashboard",
    adminScreen: "dashboard",
    isLiveMode: false,
    liveProfile: null,
    setLiveProfile: vi.fn(),
    setProfile: vi.fn(),
    profile: { conditions: ["Type 2 Diabetes"], medications: [] },
    setScreen: vi.fn(),
    ...overrides,
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Health Profile Unit Conversions & Toggles (Task 1)", () => {
  describe("Conversion math rules", () => {
    it("5 ft 10 in is converted to 177.8 cm; 6 ft 0 in as 182.9 cm", () => {
      expect(ftInToCm(5, 10)).toBe(177.8);
      expect(ftInToCm(6, 0)).toBe(182.9);
    });

    it("154 lb is converted to 69.9 kg; 220 lb as 99.8 kg", () => {
      expect(lbToKg(154)).toBe(69.9);
      expect(lbToKg(220)).toBe(99.8);
    });

    it("cm and kg values convert to imperial and back within rounding", () => {
      // 170 cm -> 5 ft 6.9 in
      const { feet, inches } = cmToFtIn(170);
      expect(feet).toBe(5);
      expect(inches).toBe(6.9);

      // 5 ft 6.9 in -> 169.9 cm (within 0.1 cm rounding)
      expect(ftInToCm(feet, inches)).toBe(169.9);

      // 177.8 cm -> 5 ft 10 in -> 177.8 cm
      const exactConv = cmToFtIn(177.8);
      expect(exactConv.feet).toBe(5);
      expect(exactConv.inches).toBe(10);
      expect(ftInToCm(exactConv.feet, exactConv.inches)).toBe(177.8);

      // 70 kg -> 154.3 lb -> 70.0 kg
      const lb = kgToLb(70);
      expect(lb).toBe(154.3);
      expect(lbToKg(lb)).toBe(70.0);
    });

    it("inches 12 or more is normalised into the next foot when converting from cm or toggle", () => {
      // If a measurement produces inches >= 12, normalise 12 in into the next foot
      // e.g. 182.88 cm -> 72 inches = 6 ft 0.0 in (not 5 ft 12 in)
      const conv = cmToFtIn(182.88);
      expect(conv.feet).toBe(6);
      expect(conv.inches).toBe(0);
    });
  });

  describe("Localization dictionary completeness", () => {
    it("the Urdu strings exist for every new label and error", () => {
      const keys = [
        "heightToggleLabel",
        "weightToggleLabel",
        "heightUnitCm",
        "heightUnitFtIn",
        "weightUnitLb",
        "weightUnitKg",
        "heightLabelCm",
        "heightLabelFtIn",
        "feetLabel",
        "inchesLabel",
        "weightLabelLb",
        "weightLabelKg",
        "heightErrorCm",
        "heightErrorFtIn",
        "heightFeetError",
        "heightInchesError",
        "weightErrorKg",
        "weightErrorLb",
        "bodyMeasurementsOptional",
      ] as const;

      for (const k of keys) {
        expect(translations.en[k]).toBeTruthy();
        expect(translations.ur[k]).toBeTruthy();
        // Urdu string must not be identical to English
        expect(translations.ur[k]).not.toBe(translations.en[k]);
      }
    });
  });

  describe("Component Rendering & Interactions", () => {
    it("a saved profile of 170 cm / 70 kg shows as 5 ft 6.9 in / 154.3 lb by default", () => {
      setContext("en", {
        isLiveMode: true,
        liveProfile: {
          user_id: "u1",
          conditions: ["diabetes"],
          height_cm: 170,
          weight_kg: 70,
        },
      });

      render(<HealthProfileScreen />);

      const ftInput = screen.getByLabelText(translations.en.feetLabel) as HTMLInputElement;
      const inInput = screen.getByLabelText(translations.en.inchesLabel) as HTMLInputElement;
      const lbInput = screen.getByLabelText(translations.en.weightLabelLb) as HTMLInputElement;

      expect(ftInput.value).toBe("5");
      expect(inInput.value).toBe("6.9");
      expect(lbInput.value).toBe("154.3");
    });

    it("5 ft 10 in is sent as 177.8 cm; 154 lb is sent as 69.9 kg", async () => {
      const updateMock = vi.fn().mockResolvedValue({
        conditions: ["diabetes"],
        height_cm: 177.8,
        weight_kg: 69.9,
      });
      vi.spyOn(api, "updateProfile").mockImplementation(updateMock);

      setContext("en", {
        isLiveMode: true,
        liveProfile: {
          user_id: "u1",
          conditions: ["diabetes"],
        },
      });

      render(<HealthProfileScreen />);

      const ftInput = screen.getByLabelText(translations.en.feetLabel);
      const inInput = screen.getByLabelText(translations.en.inchesLabel);
      const lbInput = screen.getByLabelText(translations.en.weightLabelLb);

      fireEvent.change(ftInput, { target: { value: "5" } });
      fireEvent.change(inInput, { target: { value: "10" } });
      fireEvent.change(lbInput, { target: { value: "154" } });

      const continueBtn = screen.getByRole("button", { name: translations.en.continue });
      fireEvent.click(continueBtn);

      await waitFor(() => {
        expect(updateMock).toHaveBeenCalledTimes(1);
      });

      const payload: ProfileUpdateRequest = updateMock.mock.calls[0][0];
      expect(payload.height_cm).toBe(177.8);
      expect(payload.weight_kg).toBe(69.9);
    });

    it("6 ft 0 in is sent as 182.9 cm; 220 lb is sent as 99.8 kg", async () => {
      const updateMock = vi.fn().mockResolvedValue({
        conditions: ["diabetes"],
        height_cm: 182.9,
        weight_kg: 99.8,
      });
      vi.spyOn(api, "updateProfile").mockImplementation(updateMock);

      setContext("en", {
        isLiveMode: true,
        liveProfile: {
          user_id: "u1",
          conditions: ["diabetes"],
        },
      });

      render(<HealthProfileScreen />);

      const ftInput = screen.getByLabelText(translations.en.feetLabel);
      const inInput = screen.getByLabelText(translations.en.inchesLabel);
      const lbInput = screen.getByLabelText(translations.en.weightLabelLb);

      fireEvent.change(ftInput, { target: { value: "6" } });
      fireEvent.change(inInput, { target: { value: "0" } });
      fireEvent.change(lbInput, { target: { value: "220" } });

      const continueBtn = screen.getByRole("button", { name: translations.en.continue });
      fireEvent.click(continueBtn);

      await waitFor(() => {
        expect(updateMock).toHaveBeenCalledTimes(1);
      });

      const payload: ProfileUpdateRequest = updateMock.mock.calls[0][0];
      expect(payload.height_cm).toBe(182.9);
      expect(payload.weight_kg).toBe(99.8);
    });

    it("cm and kg input are sent unchanged when respective toggles are switched", async () => {
      const updateMock = vi.fn().mockResolvedValue({
        conditions: ["diabetes"],
        height_cm: 175,
        weight_kg: 78,
      });
      vi.spyOn(api, "updateProfile").mockImplementation(updateMock);

      setContext("en", {
        isLiveMode: true,
        liveProfile: {
          user_id: "u1",
          conditions: ["diabetes"],
        },
      });

      render(<HealthProfileScreen />);

      // Switch height toggle to cm
      const cmToggle = screen.getByRole("radio", { name: translations.en.heightUnitCm });
      fireEvent.click(cmToggle);

      // Switch weight toggle to kg
      const kgToggle = screen.getByRole("radio", { name: translations.en.weightUnitKg });
      fireEvent.click(kgToggle);

      const cmInput = screen.getByLabelText(translations.en.heightLabelCm);
      const kgInput = screen.getByLabelText(translations.en.weightLabelKg);

      fireEvent.change(cmInput, { target: { value: "175" } });
      fireEvent.change(kgInput, { target: { value: "78" } });

      const continueBtn = screen.getByRole("button", { name: translations.en.continue });
      fireEvent.click(continueBtn);

      await waitFor(() => {
        expect(updateMock).toHaveBeenCalledTimes(1);
      });

      const payload: ProfileUpdateRequest = updateMock.mock.calls[0][0];
      expect(payload.height_cm).toBe(175);
      expect(payload.weight_kg).toBe(78);
    });

    it("toggling cm to ft+in and back keeps the same height (within rounding)", () => {
      setContext("en", { isLiveMode: false });
      render(<HealthProfileScreen />);

      // Switch to cm
      const cmToggle = screen.getByRole("radio", { name: translations.en.heightUnitCm });
      fireEvent.click(cmToggle);

      const cmInput = screen.getByLabelText(translations.en.heightLabelCm) as HTMLInputElement;
      fireEvent.change(cmInput, { target: { value: "177.8" } });

      // Toggle to ft+in
      const ftInToggle = screen.getByRole("radio", { name: translations.en.heightUnitFtIn });
      fireEvent.click(ftInToggle);

      const ftInput = screen.getByLabelText(translations.en.feetLabel) as HTMLInputElement;
      const inInput = screen.getByLabelText(translations.en.inchesLabel) as HTMLInputElement;
      expect(ftInput.value).toBe("5");
      expect(inInput.value).toBe("10");

      // Toggle back to cm
      fireEvent.click(cmToggle);
      const cmInputAgain = screen.getByLabelText(translations.en.heightLabelCm) as HTMLInputElement;
      expect(cmInputAgain.value).toBe("177.8");
    });

    it("inches 12 or more is rejected during form validation with inches error message", async () => {
      setContext("en", { isLiveMode: false });
      render(<HealthProfileScreen />);

      const ftInput = screen.getByLabelText(translations.en.feetLabel);
      const inInput = screen.getByLabelText(translations.en.inchesLabel);

      fireEvent.change(ftInput, { target: { value: "5" } });
      fireEvent.change(inInput, { target: { value: "12" } });

      const continueBtn = screen.getByRole("button", { name: translations.en.continue });
      fireEvent.click(continueBtn);

      expect(await screen.findByText(translations.en.heightInchesError)).toBeTruthy();
    });

    it("out-of-range values are rejected using converted metric limits (9 ft, 20 lb, 1000 lb)", async () => {
      setContext("en", { isLiveMode: false });
      const { unmount } = render(<HealthProfileScreen />);

      // 1. 9 ft rejected
      const ftInput = screen.getByLabelText(translations.en.feetLabel);
      fireEvent.change(ftInput, { target: { value: "9" } });
      const continueBtn = screen.getByRole("button", { name: translations.en.continue });
      fireEvent.click(continueBtn);
      expect(await screen.findByText(translations.en.heightFeetError)).toBeTruthy();

      unmount();

      // 2. 20 lb rejected (converted ~9.1 kg < 20 kg minimum)
      setContext("en", { isLiveMode: false });
      const r2 = render(<HealthProfileScreen />);
      const lbInput1 = screen.getByLabelText(translations.en.weightLabelLb);
      fireEvent.change(lbInput1, { target: { value: "20" } });
      fireEvent.click(screen.getByRole("button", { name: translations.en.continue }));
      expect(await screen.findByText(translations.en.weightErrorLb)).toBeTruthy();

      r2.unmount();

      // 3. 1000 lb rejected (converted ~453.6 kg > 400 kg maximum)
      setContext("en", { isLiveMode: false });
      render(<HealthProfileScreen />);
      const lbInput2 = screen.getByLabelText(translations.en.weightLabelLb);
      fireEvent.change(lbInput2, { target: { value: "1000" } });
      fireEvent.click(screen.getByRole("button", { name: translations.en.continue }));
      expect(await screen.findByText(translations.en.weightErrorLb)).toBeTruthy();
    });

    it("displays Urdu error strings when language is set to Urdu", async () => {
      setContext("ur", { isLiveMode: false });
      render(<HealthProfileScreen />);

      const lbInput = screen.getByLabelText(translations.ur.weightLabelLb);
      fireEvent.change(lbInput, { target: { value: "1000" } });

      const continueBtn = screen.getByRole("button", { name: translations.ur.continue });
      fireEvent.click(continueBtn);

      expect(await screen.findByText(translations.ur.weightErrorLb)).toBeTruthy();
    });
  });
});
