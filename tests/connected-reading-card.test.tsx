// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import { ConflictScreen } from "../app/components/ConflictScreen";
import { translations } from "../app/translations";

const mockContext: any = {
  portal: "patient" as const,
  screen: "conflict" as const,
  providerScreen: "dashboard" as const,
  adminScreen: "dashboard" as const,
  language: "en" as const,
  isUrdu: false,
  isRomanUrdu: false,
  t: translations.en,
  isLiveMode: true,
  checkIn: {
    blood_glucose: "180",
    systolic_blood_pressure: "142",
    diastolic_blood_pressure: "90",
  },
  liveCheckinResult: null,
  liveEhrConnection: {
    mode: "connected",
    connection: {
      display_name: "City General Hospital FHIR",
      masked_patient_id: "12ed...2881",
    },
  },
  setScreen: vi.fn(),
};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockContext,
}));

describe("Item 3: Connected-Mode Reading Card Wording & Also Reported Today", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("case 1: hospital record has older value (>48h old) -> shows 'too old to compare' and NOT 'first check-in'", () => {
    // Patient reports BP 142/90 and glucose 180 today.
    // Hospital record has prior BP 130/80 from 2021 and prior glucose 140 from 2021.
    mockContext.liveCheckinResult = {
      emergency: false,
      requires_review: true,
      max_severity: "medium",
      reconciliation: {
        observation_comparisons: [
          // Older hospital readings (>48h old)
          {
            observation_type: "glucose",
            value_a: 140,
            value_b: null,
            unit_a: "mg/dL",
            timestamp_a: "2021-01-11T10:00:00Z",
            status: "missing_in_b",
          },
          {
            observation_type: "blood_pressure_systolic",
            value_a: 130,
            value_b: null,
            unit_a: "mmHg",
            timestamp_a: "2021-01-11T10:00:00Z",
            status: "missing_in_b",
          },
          {
            observation_type: "blood_pressure_diastolic",
            value_a: 80,
            value_b: null,
            unit_a: "mmHg",
            timestamp_a: "2021-01-11T10:00:00Z",
            status: "missing_in_b",
          },
          // Today's readings (missing_in_a because older baseline is outside 48h match window)
          {
            observation_type: "glucose",
            value_a: null,
            value_b: 180,
            unit_b: "mg/dL",
            status: "missing_in_a",
          },
          {
            observation_type: "blood_pressure_systolic",
            value_a: null,
            value_b: 142,
            unit_b: "mmHg",
            status: "missing_in_a",
          },
          {
            observation_type: "blood_pressure_diastolic",
            value_a: null,
            value_b: 90,
            unit_b: "mmHg",
            status: "missing_in_a",
          },
        ],
        medication_comparisons: [],
      },
      verification: {
        medication_verifications: [],
        observation_verifications: [],
      },
    };

    render(<ConflictScreen />);

    // 1. Must say "Last hospital reading: 140 mg/dL (2021-01-11) — too old to compare (readings are compared within 48 hours)"
    const desc0 = screen.getByTestId("first-checkin-desc-0");
    const desc1 = screen.getByTestId("first-checkin-desc-1");
    const combinedDesc = `${desc0.textContent} ${desc1.textContent}`;

    expect(combinedDesc).toContain("too old to compare (readings are compared within 48 hours)");
    expect(combinedDesc).toContain("Last hospital reading: 140 mg/dL (2021-01-11)");
    expect(combinedDesc).toContain("Last hospital reading: 130/80 mmHg (2021-01-11)");

    // 2. Must NEVER say "this is the patient's first check-in" when older readings exist
    expect(combinedDesc).not.toContain("this is the patient's first check-in");

    // 3. Narrative must not say "This is your first check-in"
    expect(screen.queryByText("This is your first check-in")).toBeNull();

    // 4. "ALSO REPORTED TODAY" block must render ONCE at the bottom, not under each card
    const alsoReportedSections = screen.getAllByTestId("also-reported-today-section");
    expect(alsoReportedSections.length).toBe(1);
  });

  it("case 2: hospital record truly has NO reading on file -> says 'this is the patient's first check-in'", () => {
    // Truly new patient: no prior readings in hospital bundle A
    mockContext.liveCheckinResult = {
      emergency: false,
      requires_review: true,
      max_severity: "medium",
      reconciliation: {
        observation_comparisons: [
          {
            observation_type: "glucose",
            value_a: null,
            value_b: 180,
            unit_b: "mg/dL",
            status: "missing_in_a",
          },
        ],
        medication_comparisons: [],
      },
      verification: {
        medication_verifications: [],
        observation_verifications: [],
      },
    };

    render(<ConflictScreen />);

    const desc0 = screen.getByTestId("first-checkin-desc-0");
    expect(desc0.textContent).toContain("Hospital EHR: No prior reading on file — this is the patient's first check-in");
    expect(desc0.textContent).not.toContain("too old to compare");
  });
});
