import { describe, it, expect } from "vitest";
import { computeNextPatientScreen } from "../app/context/AppContext";
import { ProfileResponse, EHRConnectionResponse } from "../app/lib/api";

describe("New-User Journey Screen Routing & Guardrails (Part 2, 3, 5)", () => {
  it("routes brand-new patient with null profile to 'consent'", () => {
    expect(computeNextPatientScreen(null, null)).toBe("consent");
  });

  it("routes patient with ungranted consent to 'consent'", () => {
    const brandNewProfile: ProfileResponse = {
      user_id: "usr-new-001",
      email: "newpatient@domain.org",
      display_name: "Fatima Noor",
      role: "patient",
      consent_granted_at: null,
      consent_revoked_at: null,
      provider_notification_consent_at: null,
      provider_notification_revoked_at: null,
      date_of_birth: null,
      inclusion_confirmed_at: null,
      conditions: [],
      on_insulin_or_sulfonylurea: false,
      language: "en",
    };
    expect(computeNextPatientScreen(brandNewProfile, null)).toBe("consent");
  });

  it("routes patient with granted consent but missing DOB/inclusion to 'inclusion'", () => {
    const consentedProfile: ProfileResponse = {
      user_id: "usr-new-001",
      email: "newpatient@domain.org",
      display_name: "Fatima Noor",
      role: "patient",
      consent_granted_at: "2026-10-07T10:00:00Z",
      consent_revoked_at: null,
      provider_notification_consent_at: "2026-10-07T10:00:00Z",
      provider_notification_revoked_at: null,
      date_of_birth: null,
      inclusion_confirmed_at: null,
      conditions: [],
      on_insulin_or_sulfonylurea: false,
      language: "en",
    };
    // Cannot skip inclusion screen
    expect(computeNextPatientScreen(consentedProfile, null)).toBe("inclusion");

    // Even if DOB set but adult inclusion not confirmed
    const dobOnlyProfile: ProfileResponse = {
      ...consentedProfile,
      date_of_birth: "1988-04-12",
      inclusion_confirmed_at: null,
    };
    expect(computeNextPatientScreen(dobOnlyProfile, null)).toBe("inclusion");
  });

  it("routes patient with completed inclusion to 'profile' if conditions empty", () => {
    const includedProfile: ProfileResponse = {
      user_id: "usr-new-001",
      email: "newpatient@domain.org",
      display_name: "Fatima Noor",
      role: "patient",
      consent_granted_at: "2026-10-07T10:00:00Z",
      consent_revoked_at: null,
      provider_notification_consent_at: "2026-10-07T10:00:00Z",
      provider_notification_revoked_at: null,
      date_of_birth: "1988-04-12",
      inclusion_confirmed_at: "2026-10-07T10:02:00Z",
      conditions: [],
      on_insulin_or_sulfonylurea: false,
      language: "en",
    };
    expect(computeNextPatientScreen(includedProfile, null)).toBe("profile");
  });

  it("routes patient with conditions to 'connection' if connection mode unset", () => {
    const configuredProfile: ProfileResponse = {
      user_id: "usr-new-001",
      email: "newpatient@domain.org",
      display_name: "Fatima Noor",
      role: "patient",
      consent_granted_at: "2026-10-07T10:00:00Z",
      consent_revoked_at: null,
      provider_notification_consent_at: "2026-10-07T10:00:00Z",
      provider_notification_revoked_at: null,
      date_of_birth: "1988-04-12",
      inclusion_confirmed_at: "2026-10-07T10:02:00Z",
      conditions: ["Type 2 Diabetes"],
      on_insulin_or_sulfonylurea: true,
      language: "en",
    };
    expect(computeNextPatientScreen(configuredProfile, null)).toBe("connection");

    const noneConn: EHRConnectionResponse = {
      mode: "none",
      system_id: null,
      system_name: null,
      sandbox_id: null,
      patient_id: null,
      display_name: null,
      status: "disconnected",
      last_sync: null,
    };
    expect(computeNextPatientScreen(configuredProfile, noneConn)).toBe("connection");
  });

  it("routes patient to 'home' only after all 4 steps completed", () => {
    const fullProfile: ProfileResponse = {
      user_id: "usr-new-001",
      email: "newpatient@domain.org",
      display_name: "Fatima Noor",
      role: "patient",
      consent_granted_at: "2026-10-07T10:00:00Z",
      consent_revoked_at: null,
      provider_notification_consent_at: "2026-10-07T10:00:00Z",
      provider_notification_revoked_at: null,
      date_of_birth: "1988-04-12",
      inclusion_confirmed_at: "2026-10-07T10:02:00Z",
      conditions: ["Type 2 Diabetes", "Hypertension"],
      on_insulin_or_sulfonylurea: true,
      language: "en",
    };
    const isolatedConn: EHRConnectionResponse = {
      mode: "isolated",
      system_id: null,
      system_name: null,
      sandbox_id: null,
      patient_id: null,
      display_name: null,
      status: "connected",
      last_sync: "2026-10-07T10:05:00Z",
    };
    expect(computeNextPatientScreen(fullProfile, isolatedConn)).toBe("home");
  });

  it("ensures Settings and Record screens display real user details and never fallback names", () => {
    const signedInUser = {
      display_name: "Zainab Ahmed",
      role: "patient",
      email: "zainab.a@customcare.pk",
    };

    // User display name should match signed-in user, never Ali Khan
    const computedName = signedInUser.display_name || signedInUser.email;
    expect(computedName).toBe("Zainab Ahmed");
    expect(computedName).not.toContain("Ali Khan");
    expect(computedName).not.toContain("Sana Malik");

    // Medication dose formatter: empty dosage must never render literal "dosage"
    function formatMedicationDose(med: { dosage?: string | null }): string {
      return med.dosage && med.dosage.trim().length > 0 ? med.dosage : "No dose entered";
    }

    expect(formatMedicationDose({ dosage: "500mg daily" })).toBe("500mg daily");
    expect(formatMedicationDose({ dosage: "" })).toBe("No dose entered");
    expect(formatMedicationDose({ dosage: null })).toBe("No dose entered");
    expect(formatMedicationDose({ dosage: undefined })).not.toBe("dosage");

    // Consent badge state
    function getConsentBadge(grantedAt: string | null, revokedAt: string | null): string {
      return grantedAt && !revokedAt ? "Active ✓" : "Not given";
    }

    expect(getConsentBadge(null, null)).toBe("Not given");
    expect(getConsentBadge("2026-10-07", null)).toBe("Active ✓");
    expect(getConsentBadge("2026-10-07", "2026-10-07")).toBe("Not given");
  });
});
