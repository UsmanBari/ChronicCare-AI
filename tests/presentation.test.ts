import { describe, it, expect } from "vitest";
import {
  describeSide,
  describeReviewReason,
  titleCaseName,
  mapApiError,
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

    it("maps generic 500 errors", () => {
      expect(mapApiError(500)).toBe("An unexpected error occurred. Please try again.");
    });
  });
});
