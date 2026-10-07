import { describe, it, expect } from "vitest";
import { describeMedicationItem } from "../app/lib/presentation";

describe("Medication Result & Confirmation Presentation (FIX 10 Part 7)", () => {
  it("marks a matching medicine as confirmed with no severity badge and no contradictory review text", () => {
    const comparison = {
      medication_name: "Metformin 500mg",
      status_a: "active",
      status_b: "active",
      dosage_a: "1 tablet twice daily",
      dosage_b: "1 tablet twice daily",
      comparison_status: "agree",
    };
    const verification = {
      medication_name: "Metformin 500mg",
      reconciliation_status: "agree",
      severity: "low",
      requires_human_review: false,
    };

    const resultEn = describeMedicationItem(comparison, verification, false);
    expect(resultEn.isConfirmed).toBe(true);
    expect(resultEn.reason).toBe("Matches the record.");
    expect(resultEn.severity).toBe("low");

    const resultUr = describeMedicationItem(comparison, verification, true);
    expect(resultUr.isConfirmed).toBe(true);
    expect(resultUr.reason).toBe("ریکارڈ کے مطابق ہے۔");
  });

  it("flags a stopped medicine with high severity and clear clinical reason", () => {
    const comparison = {
      medication_name: "Lisinopril 10mg",
      status_a: "active",
      status_b: "stopped",
      dosage_a: "1 tablet daily",
      dosage_b: null,
      comparison_status: "conflict",
    };
    const verification = {
      medication_name: "Lisinopril 10mg",
      reconciliation_status: "conflict",
      severity: "high",
      requires_human_review: true,
      review_reason: "The record says you take this medication; you said you stopped it.",
    };

    const result = describeMedicationItem(comparison, verification, false);
    expect(result.isConfirmed).toBe(false);
    expect(result.severity).toBe("high");
    expect(result.todayText).toBe("Today: stopped");
    expect(result.reason).toContain("you said you stopped it");
  });

  it("flags a changed dose with correct comparison text", () => {
    const comparison = {
      medication_name: "Atorvastatin 20mg",
      status_a: "active",
      status_b: "active",
      dosage_a: "20mg daily",
      dosage_b: "40mg daily",
      comparison_status: "conflict",
    };
    const verification = {
      medication_name: "Atorvastatin 20mg",
      reconciliation_status: "conflict",
      severity: "low",
      requires_human_review: true,
    };

    const result = describeMedicationItem(comparison, verification, false);
    expect(result.isConfirmed).toBe(false);
    expect(result.todayText).toBe("Today: active, new dose: 40mg daily");
    expect(result.reason).toContain("different dose");
  });

  it("handles missing in today checkin (not reported)", () => {
    const comparison = {
      medication_name: "Aspirin 81mg",
      status_a: "active",
      status_b: null,
      dosage_a: "81mg daily",
      dosage_b: null,
      comparison_status: "missing_in_b",
    };

    const result = describeMedicationItem(comparison, null, false);
    expect(result.isConfirmed).toBe(false);
    expect(result.todayText).toBe("Not reported today");
    expect(result.reason).toBe("Not reported today.");
  });

  it("handles up to the maximum 8 chronic care medications correctly", () => {
    const meds = [
      { name: "Metformin 500mg", status: "agree" },
      { name: "Lisinopril 10mg", status: "agree" },
      { name: "Atorvastatin 20mg", status: "conflict" },
      { name: "Amlodipine 5mg", status: "agree" },
      { name: "Empagliflozin 10mg", status: "agree" },
      { name: "Losartan 50mg", status: "conflict" },
      { name: "Glimepiride 2mg", status: "agree" },
      { name: "Aspirin 81mg", status: "agree" },
    ];

    const results = meds.map((m) =>
      describeMedicationItem(
        {
          medication_name: m.name,
          status_a: "active",
          status_b: m.status === "agree" ? "active" : "stopped",
          comparison_status: m.status,
        },
        null,
        false
      )
    );

    expect(results).toHaveLength(8);
    const confirmed = results.filter((r) => r.isConfirmed);
    const flagged = results.filter((r) => !r.isConfirmed);
    expect(confirmed).toHaveLength(6);
    expect(flagged).toHaveLength(2);
  });
});
