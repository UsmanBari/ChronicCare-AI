import { describe, it, expect } from "vitest";
import { describeBlockedAction } from "../app/lib/presentation";

describe("Blocked-Action Messaging and Routing Tests (Part 2)", () => {
  it("maps 403 profile_incomplete with missing date_of_birth to inclusion action", () => {
    const resEn = describeBlockedAction(403, "profile_incomplete", ["date_of_birth", "inclusion_confirmed"], false);
    expect(resEn.target).toBe("inclusion");
    expect(resEn.message.toLowerCase()).toContain("inclusion");
    expect(resEn.message.toLowerCase()).not.toContain("consent");
    expect(resEn.actionText).toBe("Complete Eligibility Details");

    const resUr = describeBlockedAction(403, "profile_incomplete", ["date_of_birth"], true);
    expect(resUr.target).toBe("inclusion");
    expect(resUr.actionText).toBe("شمولیت کی تفصیلات درج کریں");
  });

  it("maps 403 profile_incomplete with missing conditions to profile action", () => {
    const res = describeBlockedAction(403, "profile_incomplete", ["conditions"], false);
    expect(res.target).toBe("profile");
    expect(res.message.toLowerCase()).toContain("conditions");
    expect(res.message.toLowerCase()).not.toContain("consent");
    expect(res.actionText).toBe("Complete Health Profile");
  });

  it("ensures profile_incomplete NEVER produces a consent message or action", () => {
    const res = describeBlockedAction(403, "profile_incomplete", [], false);
    expect(res.target).not.toBe("consent");
    expect(res.message.toLowerCase()).not.toContain("consent");
    expect(res.actionText?.toLowerCase()).not.toContain("consent");
  });

  it("maps 403 consent_required to consent settings action", () => {
    const resEn = describeBlockedAction(403, "consent_required", null, false);
    expect(resEn.target).toBe("consent");
    expect(resEn.message.toLowerCase()).toContain("consent");
    expect(resEn.actionText).toBe("Open Consent Settings");

    const resUr = describeBlockedAction(403, "consent_required", null, true);
    expect(resUr.target).toBe("consent");
    expect(resUr.actionText).toBe("اجازت نامہ کی ترتیبات کھولیں");
  });

  it("maps 403 provider_notification_consent_required to consent settings action", () => {
    const res = describeBlockedAction(403, "provider_notification_consent_required", null, false);
    expect(res.target).toBe("consent");
    expect(res.message.toLowerCase()).toContain("provider notification");
    expect(res.actionText).toBe("Open Consent Settings");
  });

  it("maps 403 wrong-role / forbidden account to none target with portal warning", () => {
    const resEn = describeBlockedAction(403, "Provider token rejected on patient endpoint", null, false);
    expect(resEn.target).toBe("none");
    expect(resEn.message.toLowerCase()).toContain("cannot use this portal");

    const resUr = describeBlockedAction(403, "Admin token cannot access patient checkins", null, true);
    expect(resUr.target).toBe("none");
    expect(resUr.message).toBe("یہ اکاؤنٹ اس پورٹل کو استعمال کرنے کی اجازت نہیں رکھتا۔");
  });

  it("maps generic 403 to neutral message without raw JSON", () => {
    const res = describeBlockedAction(403, "some_internal_secret_error", null, false);
    expect(res.target).toBe("none");
    expect(res.message).toBe("You do not have permission to perform this action.");
    expect(res.message).not.toContain("some_internal_secret_error");
  });

  it("maps 500 error to retry action and NEVER says 'Access denied'", () => {
    const resEn = describeBlockedAction(500, "Internal database failure", null, false);
    expect(resEn.target).toBe("retry");
    expect(resEn.message.toLowerCase()).not.toContain("access denied");
    expect(resEn.message.toLowerCase()).toContain("server could not complete");
    expect(resEn.actionText).toBe("Retry");

    const resUr = describeBlockedAction(500, null, null, true);
    expect(resUr.target).toBe("retry");
    expect(resUr.actionText).toBe("دوبارہ کوشش کریں");
  });

  it("maps network failure (status 0 / null) to retry action and NEVER says 'Access denied'", () => {
    const res = describeBlockedAction(0, null, null, false);
    expect(res.target).toBe("retry");
    expect(res.message.toLowerCase()).not.toContain("access denied");
    expect(res.message.toLowerCase()).toContain("server could not complete");
    expect(res.actionText).toBe("Retry");
  });
});
