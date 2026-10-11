// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { translations } from "../app/translations";
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

vi.mock("../app/lib/api", () => ({
  api: {
    updateProfile: vi.fn(),
    getProfile: vi.fn(),
    getEHRConnection: vi.fn(),
    getRecord: vi.fn().mockResolvedValue({ conditions: [], medications: [], allergies: [], baseline_observations: [] }),
    createRecordMedication: vi.fn(),
    updateRecordMedication: vi.fn(),
    deleteRecordMedication: vi.fn(),
    createRecordAllergy: vi.fn(),
    deleteRecordAllergy: vi.fn(),
    createRecordObservation: vi.fn(),
    deleteRecordObservation: vi.fn(),
    getUserCheckins: vi.fn().mockResolvedValue([]),
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

import { HealthProfileScreen } from "../app/components/HealthProfileScreen";
import { HomeScreen } from "../app/components/HomeScreen";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";

function setContext(lang: "en" | "ur", overrides: Record<string, any> = {}) {
  for (const k of Object.keys(ctx)) delete ctx[k];
  Object.assign(ctx, {
    language: lang,
    t: translations[lang],
    isUrdu: lang === "ur",
    setLanguage: vi.fn(),
    connectionMode: "offline",
    portal: "patient",
    screen: "profile",
    providerScreen: "dashboard",
    adminScreen: "dashboard",
    isLiveMode: false,
    liveEhrConnection: null,
    liveProfile: null,
    setPortal: vi.fn(),
    setScreen: vi.fn(),
    setProviderScreen: vi.fn(),
    setAdminScreen: vi.fn(),
    setShowSettings: vi.fn(),
    setShowTour: vi.fn(),
    returnToHomeAndClearRun: vi.fn(),
    signOutUser: vi.fn().mockResolvedValue(undefined),
    setUserIdentifier: vi.fn(),
    setUserRole: vi.fn(),
    setLiveProfile: vi.fn(),
    setProfile: vi.fn(),
    profile: {
      conditions: [],
      medications: [],
      date_of_birth: "1980-01-01",
      sex_at_birth: "female",
      pregnancy_status: "no",
    },
    demoScenario: "normal",
    setDemoScenario: vi.fn(),
    resetDemo: vi.fn(),
    appointment: { isBooked: false },
    setActiveLiveCheckin: vi.fn(),
    showSettings: false,
    userIdentifier: "patient@example.com",
    activeConditions: ["Hypertension"],
    ...overrides,
  });
}

describe("STAGE 10B: One Clear Medication Flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("HealthProfileScreen in Live Mode", () => {
    it("renders hint line and NO medication inputs or add button in live mode (EN)", () => {
      setContext("en", {
        isLiveMode: true,
        liveProfile: {
          user_id: "usr-live-01",
          email: "patient@example.com",
          role: "patient",
          conditions: ["Hypertension"],
          language: "en",
          date_of_birth: "1980-01-01",
          inclusion_confirmed_at: "2026-10-01T00:00:00Z",
        },
      });

      render(<HealthProfileScreen />);

      // The hint line must be visible
      expect(screen.getByText("You can add your medicines in the next step.")).toBeTruthy();

      // No medication input controls or add medication button
      expect(document.getElementById("add-med-btn")).toBeNull();
      expect(document.getElementById("medication-input-0")).toBeNull();
    });

    it("renders hint line and NO medication inputs in live mode in Urdu (RTL)", () => {
      setContext("ur", {
        isLiveMode: true,
        liveProfile: {
          user_id: "usr-live-01",
          email: "patient@example.com",
          role: "patient",
          conditions: ["Hypertension"],
          language: "ur",
          date_of_birth: "1980-01-01",
          inclusion_confirmed_at: "2026-10-01T00:00:00Z",
        },
      });

      render(<HealthProfileScreen />);

      // Urdu hint line
      expect(screen.getByText("آپ اگلے مرحلے میں اپنی ادویات شامل کر سکتے ہیں۔")).toBeTruthy();
      expect(document.getElementById("add-med-btn")).toBeNull();
      expect(document.getElementById("medication-input-0")).toBeNull();
    });

    it("submits live-mode profile save with NO medicines and NEVER inserts Metformin for hypertension-only user", async () => {
      const mockSetProfile = vi.fn();
      const mockSetScreen = vi.fn();
      const mockUpdateProfile = vi.mocked(api.updateProfile).mockResolvedValue({
        user_id: "usr-live-01",
        email: "patient@example.com",
        role: "patient",
        conditions: ["Hypertension"],
        language: "en",
        date_of_birth: "1980-01-01",
        inclusion_confirmed_at: "2026-10-01T00:00:00Z",
      });

      setContext("en", {
        isLiveMode: true,
        setProfile: mockSetProfile,
        setScreen: mockSetScreen,
        liveProfile: {
          user_id: "usr-live-01",
          email: "patient@example.com",
          role: "patient",
          conditions: ["Hypertension"],
          language: "en",
          date_of_birth: "1980-01-01",
          inclusion_confirmed_at: "2026-10-01T00:00:00Z",
        },
        profile: {
          conditions: ["Hypertension"],
          medications: [],
          date_of_birth: "1980-01-01",
        },
      });

      render(<HealthProfileScreen />);

      // Ensure Hypertension is selected
      const htnCheckbox = document.getElementById("condition-htn") as HTMLInputElement;
      expect(htnCheckbox).not.toBeNull();
      expect(htnCheckbox.checked).toBe(true);

      const saveBtn = document.getElementById("profile-continue-btn");
      expect(saveBtn).not.toBeNull();
      fireEvent.click(saveBtn!);

      await waitFor(() => {
        expect(mockUpdateProfile).toHaveBeenCalledTimes(1);
      });

      // Verify payload to API has conditions and NO medications field
      const sentPayload = mockUpdateProfile.mock.calls[0][0];
      expect(sentPayload.conditions).toEqual(["hypertension"]);
      expect((sentPayload as any).medications).toBeUndefined();

      // Verify local setProfile was called with medications: [] (NOT Metformin!)
      expect(mockSetProfile).toHaveBeenCalled();
      const localProfileSaved = mockSetProfile.mock.calls[0][0];
      expect(localProfileSaved.medications).toEqual([]);
      expect(JSON.stringify(localProfileSaved)).not.toContain("Metformin");
    });
  });

  describe("HealthProfileScreen in Mock/Demo Mode", () => {
    it("renders demo patient notice and allows editing demo medicines", () => {
      setContext("en", {
        isLiveMode: false,
        profile: {
          conditions: ["Type 2 Diabetes"],
          medications: ["Metformin 500mg (1+1)"],
        },
      });

      render(<HealthProfileScreen />);

      // Demo patient notice is present
      expect(screen.getByText("Demo patient")).toBeTruthy();

      // Medication inputs and add button are present
      expect(document.getElementById("add-med-btn")).not.toBeNull();
      expect(document.getElementById("medication-input-0")).not.toBeNull();
    });

    it("does NOT fallback to Metformin if user clears all medications in mock mode", async () => {
      const mockSetProfile = vi.fn();
      setContext("en", {
        isLiveMode: false,
        setProfile: mockSetProfile,
        profile: {
          conditions: ["Hypertension"],
          medications: [""],
        },
      });

      render(<HealthProfileScreen />);

      // Clear the medication input
      const medInput = document.getElementById("medication-input-0") as HTMLInputElement;
      expect(medInput).not.toBeNull();
      fireEvent.change(medInput, { target: { value: "" } });

      const saveBtn = document.getElementById("profile-continue-btn");
      fireEvent.click(saveBtn!);

      expect(mockSetProfile).toHaveBeenCalled();
      const localProfileSaved = mockSetProfile.mock.calls[0][0];
      // Empty must stay empty
      expect(localProfileSaved.medications).toEqual([]);
      expect(JSON.stringify(localProfileSaved)).not.toContain("Metformin");
    });
  });

  describe("HomeScreen: EHR-Connected vs Isolated Mode", () => {
    it("renders read-only EHR medication title and NO 'Add medications' / 'Edit my record' button for EHR patient (EN)", () => {
      setContext("en", {
        isLiveMode: true,
        connectionMode: "fhir",
        liveEhrConnection: {
          mode: "fhir",
          connection: {
            ehr_system_id: "sim-city-general",
            display_name: "City General Hospital",
            masked_patient_id: "P-***45",
            linked_at: "2026-10-01T00:00:00Z",
            last_verified_at: null,
          },
          summary: {
            recent_observations: 5,
            active_medications: 2,
          },
        },
        activeConditions: ["Hypertension"],
      });

      render(<HomeScreen />);

      // Title reads "Medicines from your hospital record"
      expect(screen.getByText("Medicines from your hospital record")).toBeTruthy();
      expect(screen.getByText("Managed by hospital EHR")).toBeTruthy();
      expect(screen.getByText("Something is different?")).toBeTruthy();

      // "Edit my record" button MUST NOT be present
      expect(document.getElementById("edit-my-record-btn")).toBeNull();
      expect(document.getElementById("add-medication-btn")).toBeNull();
      expect(document.getElementById("add-med-btn")).toBeNull();
    });

    it("renders read-only EHR medication title in Urdu", () => {
      setContext("ur", {
        isLiveMode: true,
        connectionMode: "fhir",
        liveEhrConnection: {
          mode: "fhir",
          connection: {
            ehr_system_id: "sim-city-general",
            display_name: "City General Hospital",
            masked_patient_id: "P-***45",
            linked_at: "2026-10-01T00:00:00Z",
            last_verified_at: null,
          },
        },
        activeConditions: ["Hypertension"],
      });

      render(<HomeScreen />);

      expect(screen.getByText("آپ کے اسپتال ریکارڈ سے ادویات")).toBeTruthy();
      expect(screen.getByText("آپ کا ریکارڈ اسپتال EHR سے منظم ہے۔")).toBeTruthy();
      expect(screen.getByText("کچھ مختلف ہے؟")).toBeTruthy();
      expect(document.getElementById("edit-my-record-btn")).toBeNull();
    });

    it("renders 'Edit my record' button for isolated-mode patient", () => {
      setContext("en", {
        isLiveMode: true,
        connectionMode: "offline",
        liveEhrConnection: { mode: "isolated", connection: null },
        activeConditions: ["Hypertension"],
      });

      render(<HomeScreen />);

      expect(document.getElementById("edit-my-record-btn")).not.toBeNull();
    });
  });

  describe("HealthRecordScreen in Isolated Mode", () => {
    it("displays the explicit medication purpose text in EN and UR", async () => {
      vi.mocked(api.getRecord).mockResolvedValue({
        conditions: [{ name: "Hypertension", basis: null }],
        medications: [],
        allergies: [],
        baseline_observations: [],
      });

      setContext("en", {
        isLiveMode: true,
      });

      const { unmount } = render(<HealthRecordScreen />);
      await waitFor(() => {
        expect(screen.getByText("Your medicines. We use this to check what you tell us in each check-in.")).toBeTruthy();
      });
      unmount();

      // Urdu purpose check
      setContext("ur", {
        isLiveMode: true,
      });

      render(<HealthRecordScreen />);
      await waitFor(() => {
        expect(screen.getByText("آپ کی ادویات۔ ہم اسے ہر چیک ان میں آپ کی بتائی ہوئی باتوں کی تصدیق کے لیے استعمال کرتے ہیں۔")).toBeTruthy();
      });
    });

    it("allows adding and removing medications for isolated patients", async () => {
      vi.mocked(api.getRecord).mockResolvedValue({
        conditions: [{ name: "Hypertension", basis: null }],
        medications: [
          { id: "med-1", name: "Amlodipine 5mg", dosage: "5mg once daily", status: "active" },
        ],
        allergies: [],
        baseline_observations: [],
      });

      const mockCreateMed = vi.mocked(api.createRecordMedication).mockResolvedValue({
        id: "med-2",
        name: "Lisinopril 10mg",
        dosage: "10mg once daily",
        status: "active",
      });

      setContext("en", {
        isLiveMode: true,
      });

      render(<HealthRecordScreen />);

      await waitFor(() => {
        expect(screen.getByText("Amlodipine 5mg")).toBeTruthy();
      });

      // Add a medication
      const nameInput = screen.getByPlaceholderText(/Medication name/i);
      const doseInput = screen.getByPlaceholderText(/Dosage/i);
      const addBtn = document.getElementById("add-medication-btn");

      fireEvent.change(nameInput, { target: { value: "Lisinopril 10mg" } });
      fireEvent.change(doseInput, { target: { value: "10mg once daily" } });
      fireEvent.click(addBtn!);

      await waitFor(() => {
        expect(mockCreateMed).toHaveBeenCalledWith(
          expect.objectContaining({
            name: "Lisinopril 10mg",
            dosage: "10mg once daily",
          })
        );
      });
    });
  });
});
