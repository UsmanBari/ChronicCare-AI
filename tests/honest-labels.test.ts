import { describe, it, expect } from "vitest";
import { describeSide, calculateAgeFromDob } from "../app/lib/presentation";

describe("Honest Clinical Labels Matrix (FIX 10 Part 6)", () => {
  const timestamp = "2026-10-05T14:30:00Z";
  const dateStr = "2026-10-05";

  const matrix = [
    // [side, source, mode, expectedEn, expectedUr]
    // Side B (Today's check-in) is ALWAYS "Today's check-in (reported by you)" regardless of mode/source
    { side: "b", source: "local", mode: "isolated", expectedEn: "Today's check-in (reported by you)", expectedUr: "آج کا آپ کا جواب" },
    { side: "b", source: "fhir", mode: "connected", expectedEn: "Today's check-in (reported by you)", expectedUr: "آج کا آپ کا جواب" },
    { side: "b", source: "simulated", mode: "simulated", expectedEn: "Today's check-in (reported by you)", expectedUr: "آج کا آپ کا جواب" },

    // Side A - Connected FHIR mode
    { side: "a", source: "fhir", mode: "connected", expectedEn: `Hospital record, ${dateStr}`, expectedUr: `ہسپتال کا ریکارڈ, ${dateStr}` },
    
    // Side A - In-process Simulator mode
    { side: "a", source: "simulated", mode: "simulated", expectedEn: `Simulated hospital record (synthetic data), ${dateStr}`, expectedUr: `ہسپتال کا مصنوعی ریکارڈ (مصنوعی ڈیٹا), ${dateStr}` },

    // Side A - Isolated / Local Baseline Reading
    { side: "a", source: "local", mode: "isolated", expectedEn: `Your baseline reading you entered on ${dateStr}`, expectedUr: `آپ کی بنیادی ریڈنگ جو آپ نے ${dateStr} کو درج کی` },

    // Side A - Prior check-in copy
    { side: "a", source: "checkin", mode: "isolated", expectedEn: `Your check-in on ${dateStr}`, expectedUr: `آپ کا پچھلا چیک ان, ${dateStr}` },
  ];

  matrix.forEach(({ side, source, mode, expectedEn, expectedUr }) => {
    it(`correctly describes side=${side}, source=${source}, mode=${mode} in English and Urdu`, () => {
      const actualEn = describeSide(side as any, source, "low", mode, null, timestamp, false);
      expect(actualEn).toBe(expectedEn);

      const actualUr = describeSide(side as any, source, "low", mode, null, timestamp, true);
      expect(actualUr).toBe(expectedUr);

      // Verify that words 'hospital', 'clinic', 'FHIR' never appear in isolated/local mode
      if (mode === "isolated") {
        expect(actualEn.toLowerCase()).not.toContain("hospital");
        expect(actualEn.toLowerCase()).not.toContain("clinic");
        expect(actualEn.toLowerCase()).not.toContain("fhir");
      }
    });
  });
});

describe("calculateAgeFromDob Boundary Tests (FIX 10 Part 3)", () => {
  it("calculates exact age for 18th birthday today", () => {
    expect(calculateAgeFromDob("2008-10-07", "2026-10-07")).toBe(18);
  });

  it("calculates age 17 for day before 18th birthday", () => {
    expect(calculateAgeFromDob("2008-10-08", "2026-10-07")).toBe(17);
  });

  it("handles leap-day Feb 29 births properly", () => {
    // 2004-02-29 on 2022-02-28 -> 17
    expect(calculateAgeFromDob("2004-02-29", "2022-02-28")).toBe(17);
    // 2004-02-29 on 2022-03-01 -> 18
    expect(calculateAgeFromDob("2004-02-29", "2022-03-01")).toBe(18);
    // 2004-02-29 on 2024-02-29 -> 20
    expect(calculateAgeFromDob("2004-02-29", "2024-02-29")).toBe(20);
  });

  it("returns null for future dates, malformed dates, and ages > 120", () => {
    expect(calculateAgeFromDob("2030-01-01", "2026-10-07")).toBeNull();
    expect(calculateAgeFromDob("invalid-date")).toBeNull();
    expect(calculateAgeFromDob("1900-01-01", "2026-10-07")).toBeNull();
  });
});
