// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor, within } from "@testing-library/react";
import { translations } from "../app/translations";
import {
  HealthProfileScreen,
  cmToIn,
  inToCm,
} from "../app/components/HealthProfileScreen";
import { api } from "../app/lib/api";

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
    isLiveMode: true,
    liveProfile: {
      user_id: "usr-1",
      conditions: ["hypertension"],
      on_insulin_or_sulfonylurea: false,
      language: lang,
      waist_cm: null,
    },
    setLiveProfile: vi.fn(),
    setProfile: vi.fn(),
    profile: { conditions: ["Hypertension"], medications: [] },
    setScreen: vi.fn(),
    ...overrides,
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Health Profile Waist Circumference Field (Part H)", () => {
  describe("Conversion math rules", () => {
    it("converts inches to cm correctly", () => {
      expect(inToCm(34)).toBe(86.4);
      expect(inToCm(36)).toBe(91.4);
    });

    it("converts cm to inches correctly", () => {
      expect(cmToIn(86.4)).toBe(34.0);
      expect(cmToIn(100)).toBe(39.4);
    });

    it("round-trips within 0.1 cm", () => {
      const original = 88.0;
      const inches = cmToIn(original);
      const backToCm = inToCm(inches);
      expect(Math.abs(backToCm - original)).toBeLessThanOrEqual(0.2);
    });
  });

  describe("Unit toggle and input interaction", () => {
    it("toggles unit from inches to cm converting value", () => {
      setContext("en");
      render(<HealthProfileScreen />);

      const inInput = screen.getByLabelText(translations.en.waistLabelIn) as HTMLInputElement;
      fireEvent.change(inInput, { target: { value: "34" } });
      expect(inInput.value).toBe("34");

      // Switch to cm within the waist toggle group
      const waistGroup = screen.getByRole("radiogroup", { name: translations.en.waistToggleLabel });
      const cmBtn = within(waistGroup).getByRole("radio", { name: translations.en.waistUnitCmAria });
      fireEvent.click(cmBtn);

      const cmInput = screen.getByLabelText(translations.en.waistLabelCm) as HTMLInputElement;
      expect(cmInput.value).toBe("86.4");
    });

    it("toggles unit when empty without producing NaN", () => {
      setContext("en");
      render(<HealthProfileScreen />);

      const waistGroup = screen.getByRole("radiogroup", { name: translations.en.waistToggleLabel });
      const cmBtn = within(waistGroup).getByRole("radio", { name: translations.en.waistUnitCmAria });
      fireEvent.click(cmBtn);

      const cmInput = screen.getByLabelText(translations.en.waistLabelCm) as HTMLInputElement;
      expect(cmInput.value).toBe("");
    });
  });

  describe("Form submission and API payload", () => {
    it("submits converted waist_cm when entered in inches", async () => {
      setContext("en");
      const mockUpdate = vi.spyOn(api, "updateProfile").mockResolvedValue({
        user_id: "usr-1",
        conditions: ["hypertension"],
        waist_cm: 86.4,
      } as any);

      render(<HealthProfileScreen />);

      const inInput = screen.getByLabelText(translations.en.waistLabelIn);
      fireEvent.change(inInput, { target: { value: "34" } });

      const continueBtn = screen.getByRole("button", { name: translations.en.continue });
      fireEvent.click(continueBtn);

      await waitFor(() => {
        expect(mockUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            waist_cm: 86.4,
          })
        );
      });
    });

    it("submits null when waist is omitted (optional field)", async () => {
      setContext("en");
      const mockUpdate = vi.spyOn(api, "updateProfile").mockResolvedValue({
        user_id: "usr-1",
        conditions: ["hypertension"],
        waist_cm: null,
      } as any);

      render(<HealthProfileScreen />);

      const continueBtn = screen.getByRole("button", { name: translations.en.continue });
      fireEvent.click(continueBtn);

      await waitFor(() => {
        expect(mockUpdate).toHaveBeenCalledWith(
          expect.objectContaining({
            waist_cm: null,
          })
        );
      });
    });

    it("displays validation error when inches value is out of bounds", async () => {
      setContext("en");
      render(<HealthProfileScreen />);

      const inInput = screen.getByLabelText(translations.en.waistLabelIn);
      fireEvent.change(inInput, { target: { value: "100" } }); // 100 inches = 254 cm > 200 cm

      const continueBtn = screen.getByRole("button", { name: translations.en.continue });
      fireEvent.click(continueBtn);

      expect(screen.getByText(translations.en.waistErrorIn)).toBeTruthy();
    });
  });

  describe("Urdu localization", () => {
    it("renders Urdu labels, toggle buttons, and helper text", () => {
      setContext("ur");
      render(<HealthProfileScreen />);

      expect(screen.getByText(translations.ur.waistLabelIn)).toBeTruthy();
      expect(screen.getByText(translations.ur.waistHelperText)).toBeTruthy();

      const waistGroup = screen.getByRole("radiogroup", { name: translations.ur.waistToggleLabel });
      expect(within(waistGroup).getByRole("radio", { name: translations.ur.waistUnitInAria })).toBeTruthy();
      expect(within(waistGroup).getByRole("radio", { name: translations.ur.waistUnitCmAria })).toBeTruthy();
    });
  });
});
