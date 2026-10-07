import { describe, it, expect } from "vitest";
import { computeNextPatientScreen } from "../app/context/AppContext";
import { ProfileResponse } from "../app/lib/api";

describe("Sex at Birth & Pregnancy Eligibility Logic (FIX 10)", () => {
  const baseProfile: ProfileResponse = {
    user_id: "usr-preg-001",
    email: "patient@domain.org",
    display_name: "Patient Name",
    role: "patient",
    consent_granted_at: "2026-10-07T10:00:00Z",
    consent_revoked_at: null,
    provider_notification_consent_at: "2026-10-07T10:00:00Z",
    provider_notification_revoked_at: null,
    date_of_birth: "1992-03-15",
    inclusion_confirmed_at: "2026-10-07T10:02:00Z",
    conditions: ["Type 2 Diabetes"],
    on_insulin_or_sulfonylurea: false,
    language: "en",
  };

  it("permits progression when sex is male and pregnancy_status is not_applicable", () => {
    const maleProfile: ProfileResponse = {
      ...baseProfile,
      sex_at_birth: "male",
      pregnancy_status: "not_applicable",
    };
    expect(computeNextPatientScreen(maleProfile, null)).toBe("connection");
  });

  it("permits progression when sex is female/prefer_not_to_say and pregnancy_status is not_pregnant", () => {
    const femaleNotPregnantProfile: ProfileResponse = {
      ...baseProfile,
      sex_at_birth: "female",
      pregnancy_status: "not_pregnant",
    };
    expect(computeNextPatientScreen(femaleNotPregnantProfile, null)).toBe("connection");

    const undisclosedNotPregnantProfile: ProfileResponse = {
      ...baseProfile,
      sex_at_birth: "prefer_not_to_say",
      pregnancy_status: "not_pregnant",
    };
    expect(computeNextPatientScreen(undisclosedNotPregnantProfile, null)).toBe("connection");
  });

  it("gates patient at 'inclusion' when pregnancy_status is pregnant", () => {
    const pregnantProfile: ProfileResponse = {
      ...baseProfile,
      sex_at_birth: "female",
      pregnancy_status: "pregnant",
    };
    // Must remain on inclusion screen so clinical advisory is presented
    expect(computeNextPatientScreen(pregnantProfile, null)).toBe("inclusion");
  });

  it("gates patient at 'inclusion' when pregnancy_status is pregnancy_unconfirmed (not sure)", () => {
    const unconfirmedProfile: ProfileResponse = {
      ...baseProfile,
      sex_at_birth: "female",
      pregnancy_status: "pregnancy_unconfirmed",
    };
    expect(computeNextPatientScreen(unconfirmedProfile, null)).toBe("inclusion");
  });

  it("gates patient at 'inclusion' if date_of_birth or inclusion_confirmed_at is unset", () => {
    const missingDobProfile: ProfileResponse = {
      ...baseProfile,
      date_of_birth: null,
      inclusion_confirmed_at: null,
    };
    expect(computeNextPatientScreen(missingDobProfile, null)).toBe("inclusion");
  });
});
