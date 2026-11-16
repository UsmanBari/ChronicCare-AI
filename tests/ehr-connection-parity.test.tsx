// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { HomeScreen } from "../app/components/HomeScreen";
import { Header } from "../app/components/Header";
import { ConnectionScreen } from "../app/components/ConnectionScreen";
import { translations } from "../app/translations";
import { isEhrManaged } from "../app/lib/connection";
import { ApiError, api } from "../app/lib/api";
import { fireEvent, waitFor } from "@testing-library/react";

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
      getUserCheckins: vi.fn().mockResolvedValue([]),
      getRecord: vi.fn().mockResolvedValue({
        conditions: [],
        medications: [
          { id: "m1", name: "Metformin 500mg", dosage: "1 tablet daily", status: "active" },
        ],
        allergies: [],
        baseline_observations: [],
      }),
    },
  };
});

describe("STAGE 10E-0 Bug 3: EHR connection mode single source of truth", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();

    Object.assign(mockAppContext, {
      portal: "patient",
      screen: "home",
      setScreen: vi.fn(),
      setPortal: vi.fn(),
      profile: { conditions: ["Type 2 Diabetes"] },
      liveProfile: { conditions: ["Type 2 Diabetes"] },
      connectionMode: "fhir", // Default state in AppContext
      liveEhrConnection: null,
      isLiveMode: true,
      userIdentifier: "ali.khan@domain.org",
      userRole: "patient",
      t: translations.en,
      isUrdu: false,
      language: "en",
      setLanguage: vi.fn(),
      appointment: { isBooked: false },
      setActiveLiveCheckin: vi.fn(),
      setShowSettings: vi.fn(),
      demoScenario: "normal",
      setDemoScenario: vi.fn(),
      resetDemo: vi.fn(),
      signOutUser: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("helper isEhrManaged: correctly prioritizes liveEhrConnection in live mode and ignores stale connectionMode", () => {
    // Live mode with isolated EHR connection
    expect(isEhrManaged(true, "fhir", { mode: "isolated" } as any)).toBe(false);
    expect(isEhrManaged(true, "offline", { mode: "isolated" } as any)).toBe(false);

    // Live mode with fhir / connected EHR
    expect(isEhrManaged(true, "offline", { mode: "fhir" } as any)).toBe(true);
    expect(isEhrManaged(true, "offline", { mode: "connected" } as any)).toBe(true);

    // Live mode with unset/null EHR connection
    expect(isEhrManaged(true, "fhir", null)).toBe(false);

    // Demo / mock mode: depends purely on connectionMode
    expect(isEhrManaged(false, "fhir", null)).toBe(true);
    expect(isEhrManaged(false, "offline", null)).toBe(false);
  });

  it("live + isolated + connectionMode 'fhir': Home shows local record card and NOT 'Managed by hospital EHR', agreeing with Header", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.connectionMode = "fhir"; // Stale default
    mockAppContext.liveEhrConnection = {
      mode: "isolated",
      connection: null,
    };
    mockAppContext.t = translations.en;
    mockAppContext.isUrdu = false;

    // Render Header
    const { container: headerContainer } = render(<Header />);
    expect(headerContainer.textContent).toContain(translations.en.connectionBadgeIsolatedShort);
    expect(headerContainer.textContent).not.toContain("Connected to");

    cleanup();

    // Render HomeScreen
    const { container: homeContainer } = render(<HomeScreen />);
    // Must NOT show managed by hospital EHR
    expect(homeContainer.textContent).not.toContain("Managed by hospital EHR");
    expect(homeContainer.textContent).not.toContain("Managed by your hospital record");
    expect(homeContainer.textContent).not.toContain("FHIR Live Synced");
    expect(homeContainer.textContent).toContain("Local Mode");
    expect(homeContainer.textContent).toContain("Edit my record");
  });

  it("live + isolated + connectionMode 'fhir' in Urdu: Home and Header agree without hospital EHR text", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.connectionMode = "fhir";
    mockAppContext.liveEhrConnection = {
      mode: "isolated",
      connection: null,
    };
    mockAppContext.t = translations.ur;
    mockAppContext.isUrdu = true;

    // Render Header
    const { container: headerContainer } = render(<Header />);
    expect(headerContainer.textContent).toContain(translations.ur.connectionBadgeIsolatedShort);

    cleanup();

    // Render HomeScreen
    const { container: homeContainer } = render(<HomeScreen />);
    expect(homeContainer.textContent).not.toContain("آپ کا ریکارڈ اسپتال EHR سے منظم ہے");
    expect(homeContainer.textContent).not.toContain("آپ کے ہسپتال کے ریکارڈ سے منظم ہے");
    expect(homeContainer.textContent).toContain("ریکارڈ میں ترمیم کریں");
  });

  it("live + fhir: Home shows managed EHR card and Header shows connected badge", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.connectionMode = "offline"; // Even if connectionMode is offline, liveEhrConnection wins
    mockAppContext.liveEhrConnection = {
      mode: "fhir",
      connection: {
        display_name: "City General Hospital",
      },
    };
    mockAppContext.t = translations.en;
    mockAppContext.isUrdu = false;

    // Render Header
    const { container: headerContainer } = render(<Header />);
    expect(headerContainer.textContent).toContain("Connected to City General Hospital (test environment)");

    cleanup();

    // Render HomeScreen
    const { container: homeContainer } = render(<HomeScreen />);
    expect(homeContainer.textContent).toContain("FHIR Live Synced");
    expect(homeContainer.textContent).toContain("Managed by your hospital record. Your clinician sees the full list.");
    expect(homeContainer.textContent).not.toContain("Edit my record");
  });

  it("live + fhir in Urdu: Home shows managed EHR card and Header shows connected badge in Urdu", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.liveEhrConnection = {
      mode: "fhir",
      connection: {
        display_name: "شہر کا جنرل ہسپتال",
      },
    };
    mockAppContext.t = translations.ur;
    mockAppContext.isUrdu = true;

    // Render Header
    const { container: headerContainer } = render(<Header />);
    expect(headerContainer.textContent).toContain("شہر کا جنرل ہسپتال سے منسلک (ٹیسٹ ماحول)");

    cleanup();

    // Render HomeScreen
    const { container: homeContainer } = render(<HomeScreen />);
    expect(homeContainer.textContent).toContain("آپ کے اسپتال کے ریکارڈ سے منظم ہے۔ آپ کا معالج مکمل فہرست دیکھ سکتا ہے۔");
  });

  it("ConnectionScreen: marks suggested test IDs that are already linked and shows real reason on 409 (P2-14)", async () => {
    mockAppContext.isLiveMode = true;
    mockAppContext.connectionMode = "offline";
    mockAppContext.liveEhrConnection = { mode: "isolated", connection: null };
    mockAppContext.t = translations.en;
    mockAppContext.isUrdu = false;
    mockAppContext.setScreen = vi.fn();

    vi.spyOn(api, "getEHRSystems").mockResolvedValue([
      {
        ehr_system_id: "smart_sandbox",
        display_name: "SMART on FHIR Public Sandbox",
        kind: "public_sandbox",
        description: "Public test server",
        suggested_patient_ids: ["9bf59715-d419-4b68-b7c1-d2fb70720516", "unlinked-patient-id-1234"],
        linked_patient_ids: ["9bf59715-d419-4b68-b7c1-d2fb70720516"],
      },
    ]);

    render(<ConnectionScreen />);

    // Check linked badge on suggested ID
    await waitFor(() => {
      const linkedBadge = screen.getByTestId("badge-linked-9bf59715");
      expect(linkedBadge).toBeDefined();
      expect(linkedBadge.textContent).toContain("Already linked");
    });
    expect(screen.queryByTestId("badge-linked-unlinked")).toBeNull();

    // Trigger connect with 409 error
    vi.spyOn(api, "connectEHR").mockRejectedValue(
      new ApiError(409, "This EHR patient is already linked to another account", {
        detail: "This EHR patient is already linked to another account",
      })
    );

    // Select the suggested ID to populate patientIdInput
    const suggestedIdBtn = screen.getByTestId("suggested-id-9bf59715");
    fireEvent.click(suggestedIdBtn);

    const connectBtn = screen.getByRole("button", { name: /Connect EHR/i });
    fireEvent.click(connectBtn);

    await waitFor(() => {
      expect(screen.getByText("This EHR patient is already linked to another account")).toBeDefined();
      // Must not show generic conflict text
      expect(screen.queryByText(/A conflict occurred with existing data or state/i)).toBeNull();
    });
  });
});
