// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";
import { translations } from "../app/translations";
import { api, PatientRecordResponse, RecordImportResponse } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => false,
  isFirebaseConfigured: () => false,
  getFirebaseAuth: () => null,
  getAuthErrorMessage: () => "",
}));

describe("Record Export and Import UI (HealthRecordScreen)", () => {
  const mockRecordIsolated: PatientRecordResponse = {
    mode: "isolated",
    conditions: [{ name: "diabetes", basis: "clinician_diagnosed" }],
    medications: [{ id: "med-1", name: "Metformin 500mg", dosage: "1 tablet BD", status: "active" }],
    allergies: [],
    baseline_observations: [],
  };

  const mockRecordConnected: PatientRecordResponse = {
    mode: "connected",
    conditions: [{ name: "diabetes", basis: "clinician_diagnosed" }],
    medications: [{ id: "med-1", name: "Metformin 500mg", dosage: "1 tablet BD", status: "active" }],
    allergies: [],
    baseline_observations: [],
  };

  const mockImportPreview: RecordImportResponse = {
    dry_run: true,
    counts: { to_add: 2, duplicates: 1, invalid: 1 },
    imported_counts: { medications: 1, observations: 1, allergies: 0 },
    duplicate_counts: { medications: 1, observations: 0, allergies: 0 },
    preview: {
      medications: [
        { name: "Empagliflozin 10mg", dosage: "1 tab daily", will_import: true },
        { name: "Metformin 500mg", dosage: "1 tablet BD", will_import: false, reason: "duplicate" },
        { name: "Bad Med", dosage: "", will_import: false, reason: "invalid_medication_dosage" },
      ],
      observations: [
        { observation_type: "glucose", value: 125, unit: "mg/dL", will_import: true },
        { observation_type: "systolic", value: 400, unit: "mmHg", will_import: false, reason: "out_of_range" },
      ],
      allergies: [
        { substance: "Peanuts", reaction: "Anaphylaxis", will_import: true },
      ],
      conditions_basis: [],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.profile = { conditions: ["diabetes"] };
    mockAppContext.liveProfile = { conditions: ["diabetes"] };
    mockAppContext.setScreen = vi.fn();

    vi.spyOn(api, "getRecord").mockResolvedValue(mockRecordIsolated);
    vi.spyOn(api, "exportRecord").mockResolvedValue(new Blob(['{"test": true}'], { type: "application/json" }));
    vi.spyOn(api, "importRecord").mockResolvedValue(mockImportPreview);

    window.URL.createObjectURL = vi.fn().mockReturnValue("blob:mock-url");
    window.URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders export buttons in both isolated and connected modes, but import ONLY in isolated mode", async () => {
    // Isolated mode: both export and import exist
    const { unmount } = render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("export-json-btn")).toBeTruthy();
      expect(screen.getByTestId("export-fhir-btn")).toBeTruthy();
      expect(screen.getByTestId("import-record-btn")).toBeTruthy();
    });

    unmount();

    // Connected mode: exports exist, import is hidden
    vi.spyOn(api, "getRecord").mockResolvedValue(mockRecordConnected);
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("export-json-btn")).toBeTruthy();
      expect(screen.getByTestId("export-fhir-btn")).toBeTruthy();
      expect(screen.queryByTestId("import-record-btn")).toBeNull();
    });
  });

  it("handles record JSON and FHIR export downloads", async () => {
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("export-json-btn")).toBeTruthy();
      expect(screen.getByTestId("export-fhir-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("export-json-btn"));
    await waitFor(() => {
      expect(api.exportRecord).toHaveBeenCalledWith("json");
    });

    await waitFor(() => {
      expect((screen.getByTestId("export-fhir-btn") as HTMLButtonElement).disabled).toBe(false);
    });

    fireEvent.click(screen.getByTestId("export-fhir-btn"));
    await waitFor(() => {
      expect(api.exportRecord).toHaveBeenCalledWith("fhir");
    });
  });

  it("handles record import preview with items to add, duplicates, invalid translated reasons and commit", async () => {
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("import-record-btn")).toBeTruthy();
    });

    const fileInput = screen.getByTestId("record-file-input") as HTMLInputElement;
    const testFile = new File(['{"medications": []}'], "record.json", {
      type: "application/json",
    });
    testFile.text = vi.fn().mockResolvedValue('{"medications": []}');

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(api.importRecord).toHaveBeenCalledWith(expect.anything(), false, true);
      expect(screen.getByTestId("record-import-modal")).toBeTruthy();
    });

    // Check preview sections and badges
    expect(screen.getByText("Items to add")).toBeTruthy();
    expect(screen.getByText("Duplicates (will skip)")).toBeTruthy();
    expect(screen.getByText("Empagliflozin 10mg (1 tab daily)")).toBeTruthy();

    // Check translated badges
    expect(screen.getByText(translations.en.reasonDuplicate)).toBeTruthy();
    expect(screen.getByText(translations.en.reasonOutOfRange)).toBeTruthy();
    expect(screen.getByText(translations.en.reasonInvalidMedDosage)).toBeTruthy();

    // Confirm import
    const confirmBtn = screen.getByTestId("confirm-import-btn");
    expect(confirmBtn).toBeTruthy();

    vi.spyOn(api, "importRecord").mockResolvedValue({
      dry_run: false,
      status: "ok",
      imported: 2,
      duplicates: 1,
      invalid: 1,
    });

    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.importRecord).toHaveBeenCalledWith(expect.anything(), false, false);
      expect(screen.queryByTestId("record-import-modal")).toBeNull();
    });
  });

  it("renders import modal in Urdu RTL", async () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("import-record-btn")).toBeTruthy();
    });

    const fileInput = screen.getByTestId("record-file-input") as HTMLInputElement;
    const testFile = new File(['{"medications": []}'], "record.json", { type: "application/json" });
    testFile.text = vi.fn().mockResolvedValue('{"medications": []}');

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      const modal = screen.getByTestId("record-import-modal");
      expect(modal).toBeTruthy();
      expect(modal.getAttribute("dir")).toBe("rtl");
    });
  });

  it("displays translated error message without stack trace when import commit fails", async () => {
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("import-record-btn")).toBeTruthy();
    });

    const fileInput = screen.getByTestId("record-file-input") as HTMLInputElement;
    const testFile = new File(['{"medications": []}'], "record.json", { type: "application/json" });
    testFile.text = vi.fn().mockResolvedValue('{"medications": []}');

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(screen.getByTestId("record-import-modal")).toBeTruthy();
    });

    // Mock failure on commit
    vi.spyOn(api, "importRecord").mockRejectedValue(new Error("Database transaction rolled back with error code 500 at server.ts:42"));

    const confirmBtn = screen.getByTestId("confirm-import-btn");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      // Must show translated error string, never the raw error stack
      expect(screen.getByText(translations.en.failedToCommitImport)).toBeTruthy();
      expect(screen.queryByText(/Database transaction rolled back/)).toBeNull();
    });
  });
});
