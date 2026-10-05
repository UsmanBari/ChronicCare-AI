import { describe, it, expect } from "vitest";
import {
  describeSide,
  describeReviewReason,
  describeMedicationItem,
  titleCaseName,
  mapApiError,
  describeTriageLevel,
  describeProtocol,
} from "../app/lib/presentation";

describe("presentation logic unit tests", () => {
  describe("describeSide", () => {
    it("returns 'Hospital EHR (FHIR)' for side 'a' when source is 'fhir'", () => {
      const result = describeSide("a", "fhir", "high", "fhir");
      expect(result).toBe("Hospital EHR (FHIR)");
      expect(result.toLowerCase()).toContain("hospital");
    });

    it("returns 'Your earlier self-reported record' for side 'a' when local and low trust", () => {
      const result = describeSide("a", "local", "low", "isolated");
      expect(result).toBe("Your earlier self-reported record");
      expect(result.toLowerCase()).not.toContain("hospital");
    });

    it("returns 'Clinician-entered record' for side 'a' when local and high trust", () => {
      const result = describeSide("a", "local", "high", "isolated");
      expect(result).toBe("Clinician-entered record");
      expect(result.toLowerCase()).not.toContain("hospital");
    });

    it("returns 'Saved record (unverified)' for side 'a' when trust is unknown or other", () => {
      const result1 = describeSide("a", "local", "medium", "isolated");
      expect(result1).toBe("Saved record (unverified)");
      expect(result1.toLowerCase()).not.toContain("hospital");

      const result2 = describeSide("a", null, null, null);
      expect(result2).toBe("Saved record (unverified)");
      expect(result2.toLowerCase()).not.toContain("hospital");
    });

    it("returns 'Today\'s check-in (reported by you)' for side 'b'", () => {
      const result = describeSide("b", "local", "low", "isolated");
      expect(result).toBe("Today's check-in (reported by you)");
      expect(result.toLowerCase()).not.toContain("hospital");
    });

    it("ensures the word 'hospital' appears ONLY when source is 'fhir'", () => {
      const nonFhir1 = describeSide("a", "local", "low", "isolated");
      const nonFhir2 = describeSide("a", "local", "high", "isolated");
      const nonFhir3 = describeSide("a", "other", null, "isolated");
      const nonFhir4 = describeSide("b", "local", null, "isolated");

      expect(nonFhir1.toLowerCase()).not.toContain("hospital");
      expect(nonFhir2.toLowerCase()).not.toContain("hospital");
      expect(nonFhir3.toLowerCase()).not.toContain("hospital");
      expect(nonFhir4.toLowerCase()).not.toContain("hospital");

      const fhirResult = describeSide("a", "fhir", "high", "fhir");
      expect(fhirResult.toLowerCase()).toContain("hospital");
    });
  });

  describe("describeReviewReason", () => {
    it("handles agree / agreement with review required", () => {
      const r1 = describeReviewReason("agree", "Review required");
      expect(r1).toBe("Matches an earlier self-reported value only; no trusted source confirms it.");

      const r2 = describeReviewReason("agreement", "Review required");
      expect(r2).toBe("Matches an earlier self-reported value only; no trusted source confirms it.");

      const r3 = describeReviewReason("review_required");
      expect(r3).toBe("Matches an earlier self-reported value only; no trusted source confirms it.");
    });

    it("handles conflict status with delta information", () => {
      const result = describeReviewReason("conflict", null, { delta: 40, unit: "mg/dL" });
      expect(result).toBe("Differs from the earlier value by 40 mg/dL.");
    });

    it("handles conflict status without delta info", () => {
      const result = describeReviewReason("conflict", null);
      expect(result).toBe("Differs from the earlier value.");
    });

    it("handles missing_in_a / source_b_only", () => {
      const r1 = describeReviewReason("missing_in_a");
      expect(r1).toBe("No earlier record to compare with.");

      const r2 = describeReviewReason("source_b_only");
      expect(r2).toBe("No earlier record to compare with.");
    });

    it("handles missing_in_b / source_a_only", () => {
      const r1 = describeReviewReason("missing_in_b");
      expect(r1).toBe("Not reported today.");

      const r2 = describeReviewReason("source_a_only");
      expect(r2).toBe("Not reported today.");
    });

    it("handles insufficient_data", () => {
      const result = describeReviewReason("insufficient_data");
      expect(result).toBe("Could not be compared (missing or incompatible value).");
    });

    it("falls back to server review_reason when unknown status", () => {
      const result = describeReviewReason("unknown_status", "Custom clinician note from server");
      expect(result).toBe("Custom clinician note from server");
    });

    it("falls back to generic message when status and review_reason are null", () => {
      const result = describeReviewReason(null, null);
      expect(result).toBe("Requires clinician review.");
    });
  });

  describe("titleCaseName", () => {
    it("capitalizes single name 'ali' to 'Ali'", () => {
      expect(titleCaseName("ali")).toBe("Ali");
    });

    it("capitalizes all-caps 'ALI KHAN' to 'Ali Khan'", () => {
      expect(titleCaseName("ALI KHAN")).toBe("Ali Khan");
    });

    it("handles whitespace '  ali  ' to 'Ali'", () => {
      expect(titleCaseName("  ali  ")).toBe("Ali");
    });

    it("handles empty string and whitespace", () => {
      expect(titleCaseName("")).toBe("");
      expect(titleCaseName("   ")).toBe("");
    });

    it("extracts and formats email usernames", () => {
      expect(titleCaseName("ali.khan@example.com")).toBe("Ali Khan");
      expect(titleCaseName("dr_sana@hospital.org")).toBe("Dr Sana");
    });
  });

  describe("mapApiError", () => {
    it("maps 401 and 403 to authentication/authorization keys", () => {
      expect(mapApiError(401)).toBe("Your session has expired. Please sign in again.");
      expect(mapApiError(403)).toBe("Access denied. You do not have permission for this action.");
    });

    it("maps 409 stale_step and concurrent_update", () => {
      expect(mapApiError(409, "stale_step")).toBe("The check-in question was updated. Please answer the current question.");
      expect(mapApiError(409, "concurrent_update")).toBe("A conflict occurred while saving your answer. Please try again.");
    });

    it("maps 422 validation errors", () => {
      expect(mapApiError(422)).toBe("Invalid information provided. Please verify your input.");
    });

    it("maps 502, 503, and server gateway errors", () => {
      expect(mapApiError(502)).toBe("The clinical service is temporarily unavailable. Please try again in a moment.");
      expect(mapApiError(503)).toBe("The clinical service is currently waking up or busy. Please try again in a moment.");
    });

    it("maps network and client timeout errors (0 / null)", () => {
      expect(mapApiError(0)).toBe("Network request failed. Please check your connection and try again.");
      expect(mapApiError(null)).toBe("Network request failed. Please check your connection and try again.");
    });

    it("maps 400 record limit and validation errors", () => {
      expect(mapApiError(400, "maximum_medications_exceeded")).toBe("You have reached the maximum limit of 30 medications.");
      expect(mapApiError(400, "maximum_allergies_exceeded")).toBe("You have reached the maximum limit of 30 allergies.");
      expect(mapApiError(400, "maximum_observations_exceeded")).toBe("You have reached the maximum limit of 20 baseline readings.");
      expect(mapApiError(400, "Glucose reading outside plausible range (20-600 mg/dL)")).toBe("Glucose reading outside plausible range (20-600 mg/dL)");
    });

    it("maps 403 consent error codes", () => {
      expect(mapApiError(403, "consent_required")).toBe("Active consent is required before proceeding.");
      expect(mapApiError(403, "provider_notification_consent_required")).toBe("Provider notification consent is required before starting a check-in.");
    });

    it("maps 409 duplicate and ehr-managed conflict errors", () => {
      expect(mapApiError(409, "record_managed_by_ehr")).toBe("Your record is managed by your hospital EHR.");
      expect(mapApiError(409, "duplicate_medication")).toBe("A medication with this name already exists in your record.");
    });

    it("maps generic 500 errors", () => {
      expect(mapApiError(500)).toBe("An unexpected error occurred. Please try again.");
    });
  });

  describe("describeMedicationItem", () => {
    it("handles active against stopped conflict (severity high)", () => {
      const comp = {
        medication_name: "Metformin 500mg",
        dosage_a: "1 tablet twice daily",
        status_a: "active",
        status_b: "stopped",
        dosage_b: null,
        source_a: "local",
        source_b: "local",
        comparison_status: "conflict",
      };
      const verif = {
        medication_name: "Metformin 500mg",
        reconciliation_status: "conflict",
        trust_level_a: "low",
        trust_level_b: "low",
        severity: "high",
        requires_human_review: true,
        review_reason: "Patient reported stopping active medication.",
      };

      const result = describeMedicationItem(comp, verif);
      expect(result.title).toBe("Metformin 500mg");
      expect(result.recordText).toBe("Record: Metformin 500mg, 1 tablet twice daily (active)");
      expect(result.todayText).toBe("Today: stopped");
      expect(result.reason).toBe("The record says you take this medication; you said you stopped it.");
      expect(result.severity).toBe("high");
    });

    it("handles dose change conflict with different dosage reported", () => {
      const comp = {
        medication_name: "Lisinopril 10mg",
        dosage_a: "1 tablet daily",
        status_a: "active",
        status_b: "active",
        dosage_b: "2 tablets daily",
        source_a: "fhir",
        source_b: "local",
        comparison_status: "conflict",
      };
      const verif = {
        medication_name: "Lisinopril 10mg",
        reconciliation_status: "conflict",
        severity: "moderate",
        requires_human_review: true,
      };

      const result = describeMedicationItem(comp, verif);
      expect(result.title).toBe("Lisinopril 10mg");
      expect(result.recordText).toBe("Record: Lisinopril 10mg, 1 tablet daily (active)");
      expect(result.todayText).toBe("Today: active, new dose: 2 tablets daily");
      expect(result.reason).toBe("You reported a different dose from the record.");
      expect(result.severity).toBe("moderate");
    });

    it("handles missing_in_b where medication was not reported today", () => {
      const comp = {
        medication_name: "Atorvastatin 20mg",
        dosage_a: "1 tablet at bedtime",
        status_a: "active",
        status_b: null,
        dosage_b: null,
        source_a: "local",
        source_b: null,
        comparison_status: "missing_in_b",
      };
      const verif = {
        medication_name: "Atorvastatin 20mg",
        reconciliation_status: "missing_in_b",
        severity: "low",
      };

      const result = describeMedicationItem(comp, verif);
      expect(result.title).toBe("Atorvastatin 20mg");
      expect(result.recordText).toBe("Record: Atorvastatin 20mg, 1 tablet at bedtime (active)");
      expect(result.todayText).toBe("Not reported today");
      expect(result.reason).toBe("Not reported today.");
      expect(result.severity).toBe("low");
    });

    it("handles agreement where patient confirmed same dose", () => {
      const comp = {
        medication_name: "Amlodipine 5mg",
        dosage_a: "1 tablet daily",
        status_a: "active",
        status_b: "active",
        dosage_b: "1 tablet daily",
        source_a: "local",
        source_b: "local",
        comparison_status: "agree",
      };
      const verif = {
        medication_name: "Amlodipine 5mg",
        reconciliation_status: "agree",
        severity: "low",
      };

      const result = describeMedicationItem(comp, verif);
      expect(result.title).toBe("Amlodipine 5mg");
      expect(result.recordText).toBe("Record: Amlodipine 5mg, 1 tablet daily (active)");
      expect(result.todayText).toBe("Today: active, 1 tablet daily");
      expect(result.reason).toBe("Matches the record.");
      expect(result.severity).toBe("low");
    });

    it("verifies source side descriptions for fhir vs local self-reported medications", () => {
      const fhirSideA = describeSide("a", "fhir", "high", "fhir");
      expect(fhirSideA).toBe("Hospital EHR (FHIR)");
      expect(fhirSideA.toLowerCase()).toContain("hospital");

      const localSideA = describeSide("a", "local", "low", "isolated");
      expect(localSideA).toBe("Your earlier self-reported record");
      expect(localSideA.toLowerCase()).not.toContain("hospital");

      const patientSideB = describeSide("b", "local", "low", "isolated");
      expect(patientSideB).toBe("Today's check-in (reported by you)");
      expect(patientSideB.toLowerCase()).not.toContain("hospital");
    });

    it("handles fallback defaults when comparison or verification fields are missing", () => {
      const result = describeMedicationItem(null, null);
      expect(result.title).toBe("Medication");
      expect(result.recordText).toBe("Record: Medication, (active)");
      expect(result.todayText).toBe("Not reported today");
      expect(result.reason).toBe("Requires clinician review.");
      expect(result.severity).toBe("low");
    });
  });

  describe("describeTriageLevel", () => {
    it("handles emergency level with default patient text", () => {
      const res = describeTriageLevel("emergency");
      expect(res.label).toBe("Emergency");
      expect(res.tone).toBe("danger");
      expect(res.icon).toBe("AlertOctagon");
      expect(res.headline).toBe("Emergency");
      expect(res.patientText).toBe("Call your local emergency number now.");
    });

    it("ensures server guidance wins over default text for emergency level", () => {
      const customGuidance = "Call emergency services immediately due to critical blood pressure.";
      const res = describeTriageLevel("emergency", customGuidance);
      expect(res.label).toBe("Emergency");
      expect(res.tone).toBe("danger");
      expect(res.patientText).toBe(customGuidance);
    });

    it("handles urgent level with default patient text", () => {
      const res = describeTriageLevel("urgent");
      expect(res.label).toBe("Needs a clinician today");
      expect(res.tone).toBe("warning");
      expect(res.icon).toBe("AlertTriangle");
      expect(res.headline).toBe("Needs a clinician today");
      expect(res.patientText).toBe(
        "Please contact your clinician today. If you feel worse, call your local emergency number."
      );
    });

    it("ensures server guidance wins over default text for urgent level", () => {
      const customGuidance = "Your reading remained high after rest. Contact your care team today.";
      const res = describeTriageLevel("urgent", customGuidance);
      expect(res.label).toBe("Needs a clinician today");
      expect(res.tone).toBe("warning");
      expect(res.patientText).toBe(customGuidance);
    });

    it("handles review level with default patient text", () => {
      const res = describeTriageLevel("review");
      expect(res.label).toBe("A clinician will review this");
      expect(res.tone).toBe("info");
      expect(res.icon).toBe("Info");
      expect(res.headline).toBe("A clinician will review this");
      expect(res.patientText).toBe(
        "A clinician will review this. Please measure again later today and at the same time tomorrow."
      );
    });

    it("ensures server guidance wins over default text for review level", () => {
      const customGuidance = "Your repeat reading normalized. A clinician will review your log.";
      const res = describeTriageLevel("review", customGuidance);
      expect(res.label).toBe("A clinician will review this");
      expect(res.tone).toBe("info");
      expect(res.patientText).toBe(customGuidance);
    });

    it("handles routine level and unknown/null level fallbacks", () => {
      const resRoutine = describeTriageLevel("routine");
      expect(resRoutine.label).toBe("Routine");
      expect(resRoutine.tone).toBe("neutral");
      expect(resRoutine.icon).toBe("CheckCircle2");
      expect(resRoutine.headline).toBe("Routine check-in");
      expect(resRoutine.patientText).toBe("");

      const resNull = describeTriageLevel(null);
      expect(resNull.label).toBe("Routine");
      expect(resNull.tone).toBe("neutral");

      const resCustomRoutine = describeTriageLevel("routine", "All parameters in target range.");
      expect(resCustomRoutine.patientText).toBe("All parameters in target range.");
    });
  });

  describe("describeProtocol", () => {
    it("describes all 5 triage protocols in truthful plain words", () => {
      expect(describeProtocol("bp_severe")).toBe("Blood pressure in the crisis range");
      expect(describeProtocol("bp_change")).toBe("Blood pressure above the patient's usual");
      expect(describeProtocol("bp_low")).toBe("Low blood pressure");
      expect(describeProtocol("glucose_high")).toBe("High glucose");
      expect(describeProtocol("glucose_low")).toBe("Low glucose");
    });

    it("handles unknown or custom protocol names gracefully", () => {
      expect(describeProtocol("custom_protocol_name")).toBe("custom protocol name");
      expect(describeProtocol(null)).toBe("Protocol");
      expect(describeProtocol(undefined)).toBe("Protocol");
      expect(describeProtocol("")).toBe("Protocol");
    });
  });

  describe("new mapApiError cases for triage and inclusion", () => {
    it("maps 403 profile_incomplete error", () => {
      expect(mapApiError(403, "profile_incomplete")).toBe(
        "Please complete your date of birth and inclusion confirmation."
      );
    });

    it("maps 422 adults_only error", () => {
      expect(mapApiError(422, "adults_only")).toBe(
        "ChronicCare AI is for adults (18 and over) in this release."
      );
    });

    it("maps 422 invalid_date_of_birth error", () => {
      expect(mapApiError(422, "invalid_date_of_birth")).toBe(
        "Please enter a valid date of birth (age 18 to 120)."
      );
    });

    it("maps 409 triage_incomplete error", () => {
      expect(mapApiError(409, "triage_incomplete")).toBe(
        "Please finish answering all safety questions."
      );
    });
  });
});
