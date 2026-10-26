// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";
import { translations } from "../app/translations";
import { api } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

vi.mock("../app/lib/api", async () => {
  const actual: any = await vi.importActual("../app/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getRecord: vi.fn(),
      updateConditionsBasis: vi.fn().mockResolvedValue({}),
      createRecordMedication: vi.fn().mockResolvedValue({}),
      deleteRecordMedication: vi.fn().mockResolvedValue({}),
      createRecordAllergy: vi.fn().mockResolvedValue({}),
      deleteRecordAllergy: vi.fn().mockResolvedValue({}),
      createRecordObservation: vi.fn().mockResolvedValue({}),
      deleteRecordObservation: vi.fn().mockResolvedValue({}),
    },
  };
});

describe("Doctor on record display in HealthRecordScreen (Day 1 Part D)", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();

    Object.assign(mockAppContext, {
      portal: "patient",
      screen: "healthRecord",
      setScreen: vi.fn(),
      profile: { conditions: ["diabetes"] },
      liveProfile: { conditions: ["diabetes"] },
      isLiveMode: true,
      t: translations.en,
      isUrdu: false,
      language: "en",
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders doctor on record banner in English when doctor_on_record is present", async () => {
    (api.getRecord as any).mockResolvedValueOnce({
      conditions: [{ name: "diabetes", basis: "clinician_diagnosed" }],
      medications: [],
      allergies: [],
      baseline_observations: [],
      doctor_on_record: {
        name: "Dr. Fatima Tariq",
        identifier: "PRAC-101",
        source: "ehr_general_practitioner",
        as_of: "2026-10-26T12:00:00Z",
      },
    });

    render(<HealthRecordScreen />);

    await waitFor(() => {
      const banner = screen.getByTestId("doctor-on-record");
      expect(banner).toBeDefined();
      expect(banner.textContent).toContain("Doctor on record: Dr. Fatima Tariq (from your hospital record)");
    });
  });

  it("renders doctor on record banner in Urdu when doctor_on_record is present", async () => {
    mockAppContext.t = translations.ur;
    mockAppContext.isUrdu = true;
    mockAppContext.language = "ur";

    (api.getRecord as any).mockResolvedValueOnce({
      conditions: [{ name: "diabetes", basis: "clinician_diagnosed" }],
      medications: [],
      allergies: [],
      baseline_observations: [],
      doctor_on_record: {
        name: "Dr. Fatima Tariq",
        identifier: "PRAC-101",
        source: "ehr_general_practitioner",
        as_of: "2026-10-26T12:00:00Z",
      },
    });

    render(<HealthRecordScreen />);

    await waitFor(() => {
      const banner = screen.getByTestId("doctor-on-record");
      expect(banner).toBeDefined();
      expect(banner.textContent).toContain("ریکارڈ پر ڈاکٹر: Dr. Fatima Tariq (آپ کے ہسپتال کے ریکارڈ سے)");
    });
  });

  it("hides doctor on record banner when doctor_on_record is null", async () => {
    (api.getRecord as any).mockResolvedValueOnce({
      conditions: [{ name: "diabetes", basis: "clinician_diagnosed" }],
      medications: [],
      allergies: [],
      baseline_observations: [],
      doctor_on_record: null,
    });

    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.queryByTestId("doctor-on-record")).toBeNull();
    });
  });

  it("never words the banner as if the doctor reviewed this app's results", async () => {
    (api.getRecord as any).mockResolvedValueOnce({
      conditions: [],
      medications: [],
      allergies: [],
      baseline_observations: [],
      doctor_on_record: {
        name: "Dr. Fatima Tariq",
        identifier: "PRAC-101",
        source: "ehr_general_practitioner",
      },
    });

    render(<HealthRecordScreen />);

    await waitFor(() => {
      const banner = screen.getByTestId("doctor-on-record");
      const text = banner.textContent?.toLowerCase() || "";
      expect(text).not.toContain("reviewed");
      expect(text).not.toContain("approved");
      expect(text).not.toContain("validated");
      expect(text).toContain("from your hospital record");
    });
  });
});
