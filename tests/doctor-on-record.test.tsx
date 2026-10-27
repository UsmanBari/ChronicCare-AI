// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { ConnectionScreen } from "../app/components/ConnectionScreen";
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
      getEHRSystems: vi.fn().mockResolvedValue([]),
      getEHRConnection: vi.fn().mockImplementation(() => Promise.resolve(mockAppContext.liveEhrConnection)),
      connectEHR: vi.fn().mockResolvedValue({}),
      disconnectEHR: vi.fn().mockResolvedValue({ mode: "isolated" }),
      testEHRSystem: vi.fn().mockResolvedValue({ status: "ok" }),
    },
  };
});

describe("Doctor on record & Hospital Allergies display in ConnectionScreen (Day 1 Part D)", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();

    Object.assign(mockAppContext, {
      portal: "patient",
      screen: "connection",
      setScreen: vi.fn(),
      connectionMode: "fhir",
      setConnectionMode: vi.fn(),
      setLiveEhrConnection: vi.fn(),
      isLiveMode: true,
      t: translations.en,
      isUrdu: false,
      language: "en",
      liveEhrConnection: {
        mode: "connected",
        connection: {
          ehr_system_id: "demo-hospital",
          display_name: "Demo Hospital",
          masked_patient_id: "...esha",
          linked_at: "2026-10-26T12:00:00Z",
          last_verified_at: "2026-10-26T12:00:00Z",
        },
        doctor_on_record: {
          name: "Dr. Fatima Tariq",
          identifier: "PRAC-101",
          source: "ehr_general_practitioner",
          as_of: "2026-10-26T12:00:00Z",
        },
        ehr_allergies: [
          {
            substance: "Penicillin G",
            criticality: "high",
            verification_status: "confirmed",
            origin: "ehr",
            trust: "high",
          },
        ],
        record_source_label: "Demo Hospital (synthetic)",
        system_id: "demo-hospital",
        kind: "simulated",
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders doctor on record in English when doctor_on_record is present", async () => {
    render(<ConnectionScreen />);

    await waitFor(() => {
      const banner = screen.getByTestId("doctor-on-record");
      expect(banner).toBeDefined();
      expect(banner.textContent).toContain("Doctor on record: Dr. Fatima Tariq (from your hospital record)");
    });
  });

  it("renders doctor on record in Urdu when doctor_on_record is present", async () => {
    mockAppContext.t = translations.ur;
    mockAppContext.isUrdu = true;
    mockAppContext.language = "ur";

    render(<ConnectionScreen />);

    await waitFor(() => {
      const banner = screen.getByTestId("doctor-on-record");
      expect(banner).toBeDefined();
      expect(banner.textContent).toContain("ریکارڈ پر ڈاکٹر: Dr. Fatima Tariq (آپ کے ہسپتال کے ریکارڈ سے)");
    });
  });

  it("hides doctor on record when doctor_on_record is null", async () => {
    mockAppContext.liveEhrConnection = {
      ...mockAppContext.liveEhrConnection,
      doctor_on_record: null,
    };

    render(<ConnectionScreen />);

    await waitFor(() => {
      expect(screen.queryByTestId("doctor-on-record")).toBeNull();
    });
  });

  it("renders hospital allergies and EHR badge in English", async () => {
    render(<ConnectionScreen />);

    await waitFor(() => {
      const section = screen.getByTestId("ehr-allergies-section");
      expect(section).toBeDefined();
      expect(section.textContent).toContain("Penicillin G");
      expect(section.textContent).toContain("Allergies in your hospital record");
      expect(section.textContent).toContain("FHIR");
    });
  });

  it("renders fallback message when ehr_allergies is empty", async () => {
    mockAppContext.liveEhrConnection = {
      ...mockAppContext.liveEhrConnection,
      ehr_allergies: [],
    };

    render(<ConnectionScreen />);

    await waitFor(() => {
      const section = screen.getByTestId("ehr-allergies-section");
      expect(section).toBeDefined();
      expect(section.textContent).toContain("None recorded");
    });
  });

  it("never words the doctor text as if the doctor reviewed this app's results", async () => {
    render(<ConnectionScreen />);

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
