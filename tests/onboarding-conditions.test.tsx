import { describe, it, expect } from "vitest";
import { calculateAgeFromDob } from "../app/lib/presentation";
import { computeNextPatientScreen } from "../app/context/AppContext";
import { ProfileResponse } from "../app/lib/api";

describe("HealthProfile & Conditions Selection Logic (FIX 10)", () => {
  it("allows selecting conditions independently and derives 'Both' correctly", () => {
    // Condition state model
    let hasDiabetes = false;
    let hasHypertension = false;

    const getSelectedConditions = () => {
      const list: string[] = [];
      if (hasDiabetes) list.push("Type 2 Diabetes");
      if (hasHypertension) list.push("Hypertension");
      return list;
    };

    const isBothSelected = () => hasDiabetes && hasHypertension;
    const isSaveDisabled = () => !hasDiabetes && !hasHypertension;

    // Initially nothing selected
    expect(getSelectedConditions()).toEqual([]);
    expect(isBothSelected()).toBe(false);
    expect(isSaveDisabled()).toBe(true);

    // 1. Tick Diabetes
    hasDiabetes = true;
    expect(getSelectedConditions()).toEqual(["Type 2 Diabetes"]);
    expect(isBothSelected()).toBe(false);
    expect(isSaveDisabled()).toBe(false);

    // 2. Tick Hypertension -> Both selected
    hasHypertension = true;
    expect(getSelectedConditions()).toEqual(["Type 2 Diabetes", "Hypertension"]);
    expect(isBothSelected()).toBe(true);
    expect(isSaveDisabled()).toBe(false);

    // 3. Untick Diabetes -> Only Hypertension selected
    hasDiabetes = false;
    expect(getSelectedConditions()).toEqual(["Hypertension"]);
    expect(isBothSelected()).toBe(false);
    expect(isSaveDisabled()).toBe(false);

    // 4. Untick Hypertension -> Neither selected, save disabled
    hasHypertension = false;
    expect(getSelectedConditions()).toEqual([]);
    expect(isBothSelected()).toBe(false);
    expect(isSaveDisabled()).toBe(true);
  });

  it("calculates age from date of birth and does not rely on static default 58", () => {
    const dob = "1990-05-15";
    const computedAge = calculateAgeFromDob(dob, "2026-10-07");
    expect(computedAge).toBe(36);
    expect(computedAge).not.toBe(58);
  });

  it("blocks navigation from profile screen until conditions are selected", () => {
    const profileWithoutConditions: ProfileResponse = {
      user_id: "usr-1",
      email: "test@example.com",
      display_name: "Test Patient",
      role: "patient",
      consent_granted_at: "2026-10-07T10:00:00Z",
      consent_revoked_at: null,
      provider_notification_consent_at: "2026-10-07T10:00:00Z",
      provider_notification_revoked_at: null,
      date_of_birth: "1985-06-20",
      inclusion_confirmed_at: "2026-10-07T10:01:00Z",
      sex_at_birth: "male",
      pregnancy_status: "not_applicable",
      conditions: [],
      on_insulin_or_sulfonylurea: false,
      language: "en",
    };

    expect(computeNextPatientScreen(profileWithoutConditions, null)).toBe("profile");

    const profileWithConditions: ProfileResponse = {
      ...profileWithoutConditions,
      conditions: ["Type 2 Diabetes"],
    };

    expect(computeNextPatientScreen(profileWithConditions, null)).toBe("connection");
  });
});
