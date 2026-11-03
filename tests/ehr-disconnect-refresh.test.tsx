// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { translations } from "../app/translations";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";
import { api } from "../app/lib/api";

const ctx: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => ctx,
}));

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => false,
  isFirebaseConfigured: () => false,
  getFirebaseAuth: () => null,
  getAuthErrorMessage: () => "",
}));

let mockRecordResponse = {
  mode: "connected",
  conditions: [{ name: "diabetes", condition: "diabetes", basis: "clinician_diagnosed", origin: "ehr" }],
  medications: [
    {
      id: "med-ehr-1",
      name: "Metformin 500mg",
      dosage: "1 tablet daily",
      status: "active",
      origin: "ehr",
      trust_level: "high",
    },
  ],
  observations: [
    {
      id: "obs-ehr-1",
      observation_type: "glucose",
      value: 120,
      unit: "mg/dL",
      measured_at: "2026-11-01T10:00:00Z",
      origin: "ehr",
      trust_level: "high",
    },
  ],
  allergies: [],
  ocr_enabled: false,
};

vi.mock("../app/lib/api", () => ({
  api: {
    getRecord: vi.fn().mockImplementation(() => Promise.resolve(mockRecordResponse)),
    getRecordHistory: vi.fn().mockResolvedValue({ edits: [] }),
  },
  ApiError: class ApiError extends Error {
    status: number;
    detail: any;
    constructor(status: number, detail: any) {
      super(typeof detail === "string" ? detail : JSON.stringify(detail));
      this.status = status;
      this.detail = detail;
    }
  },
}));

function setupContext(mode: "connected" | "isolated") {
  for (const k of Object.keys(ctx)) delete ctx[k];
  Object.assign(ctx, {
    language: "en",
    t: translations.en,
    isUrdu: false,
    setLanguage: vi.fn(),
    connectionMode: mode === "connected" ? "fhir" : "offline",
    portal: "patient",
    screen: "health_record",
    isLiveMode: true,
    liveProfile: {
      user_id: "patient-1",
      conditions: ["Type 2 Diabetes"],
    },
    liveEhrConnection:
      mode === "connected"
        ? {
            mode: "connected",
            connection: { ehr_system_id: "simulated_hospital", display_name: "Simulated Hospital" },
          }
        : { mode: "isolated", connection: null },
    setLiveEhrConnection: vi.fn((newConn) => {
      ctx.liveEhrConnection = newConn;
    }),
    setLiveProfile: vi.fn(),
    setProfile: vi.fn(),
    profile: {
      conditions: ["Type 2 Diabetes"],
      medications: [],
    },
    setScreen: vi.fn(),
    setStagedOcrUpload: vi.fn(),
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Bug Bash #88: EHR Disconnection Refetches Record and Clears Stale Badges", () => {
  it("renders EHR provenance badge in connected mode, then clears badge upon disconnection without page reload", async () => {
    // 1. Initial State: Connected EHR mode
    mockRecordResponse = {
      mode: "connected",
      conditions: [{ name: "diabetes", condition: "diabetes", basis: "clinician_diagnosed", origin: "ehr" }],
      medications: [
        {
          id: "med-ehr-1",
          name: "Metformin 500mg",
          dosage: "1 tablet daily",
          status: "active",
          origin: "ehr",
          trust_level: "high",
        },
      ],
      observations: [
        {
          id: "obs-ehr-1",
          observation_type: "glucose",
          value: 120,
          unit: "mg/dL",
          measured_at: "2026-11-01T10:00:00Z",
          origin: "ehr",
          trust_level: "high",
        },
      ],
      allergies: [],
      ocr_enabled: false,
    };
    setupContext("connected");

    const { rerender } = render(<HealthRecordScreen />);

    // Connected mode header and EHR badges must be present
    await waitFor(() => {
      expect(screen.getByText("Connected EHR Mode (High Trust)")).toBeTruthy();
    });

    const ehrBadges = screen.getAllByTestId("ehr-badge");
    expect(ehrBadges.length).toBeGreaterThan(0);

    // 2. Disconnect EHR: backend returns isolated record mode with local observations
    mockRecordResponse = {
      mode: "isolated",
      conditions: [{ name: "diabetes", condition: "diabetes", basis: "self_reported", origin: "self_reported" }],
      medications: [
        {
          id: "med-local-1",
          name: "Metformin 500mg",
          dosage: "1 tablet daily",
          status: "active",
          origin: "manual",
          trust_level: "medium",
        },
      ],
      observations: [
        {
          id: "obs-local-1",
          observation_type: "glucose",
          value: 120,
          unit: "mg/dL",
          measured_at: "2026-11-01T10:00:00Z",
          origin: "manual",
          trust_level: "medium",
        },
      ],
      allergies: [],
      ocr_enabled: false,
    };

    // Simulate AppContext updating liveEhrConnection after disconnect
    setupContext("isolated");
    rerender(<HealthRecordScreen />);

    // 3. HealthRecordScreen must automatically refetch and switch to Isolated Mode
    await waitFor(() => {
      expect(screen.getByText("Isolated Mode Clinical Record")).toBeTruthy();
    });

    // Stale EHR badges must be completely gone without manual reload
    expect(screen.queryByTestId("ehr-badge")).toBeNull();
  });
});

