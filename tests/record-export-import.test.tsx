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
  const mockRecord: PatientRecordResponse = {
    mode: "isolated",
    conditions: [{ name: "diabetes", basis: "clinician_diagnosed" }],
    medications: [{ id: "med-1", name: "Metformin 500mg", dosage: "1 tablet BD", status: "active" }],
    allergies: [],
    baseline_observations: [],
  };

  const mockImportPreview: RecordImportResponse = {
    dry_run: true,
    counts: { to_add: 2, duplicates: 1, invalid: 0 },
    imported_counts: { medications: 1, observations: 1, allergies: 0 },
    duplicate_counts: { medications: 1, observations: 0, allergies: 0 },
    preview: {
      medications: [
        { name: "Empagliflozin 10mg", dosage: "1 tab daily", will_import: true },
        { name: "Metformin 500mg", dosage: "1 tablet BD", will_import: false, reason: "duplicate" },
      ],
      observations: [
        { observation_type: "glucose", value: 125, unit: "mg/dL", will_import: true },
      ],
      allergies: [],
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

    vi.spyOn(api, "getRecord").mockResolvedValue(mockRecord);
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

  it("handles record import preview and commit flow", async () => {
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("import-record-btn")).toBeTruthy();
    });

    const fileInput = screen.getByTestId("record-file-input") as HTMLInputElement;
    const testFile = new File(['{"medications": [{"name": "Empagliflozin 10mg", "dosage": "1 tab daily"}]}'], "record.json", {
      type: "application/json",
    });
    testFile.text = vi.fn().mockResolvedValue('{"medications": [{"name": "Empagliflozin 10mg", "dosage": "1 tab daily"}]}');

    fireEvent.change(fileInput, { target: { files: [testFile] } });

    await waitFor(() => {
      expect(api.importRecord).toHaveBeenCalledWith(expect.anything(), false, true);
      expect(screen.getByTestId("record-import-modal")).toBeTruthy();
    });

    // Verify preview numbers displayed
    expect(screen.getByText("Items to add")).toBeTruthy();
    expect(screen.getByText("Duplicates (will skip)")).toBeTruthy();

    // Confirm import
    const confirmBtn = screen.getByTestId("confirm-import-btn");
    expect(confirmBtn).toBeTruthy();

    vi.spyOn(api, "importRecord").mockResolvedValue({
      dry_run: false,
      status: "ok",
      imported: 2,
      duplicates: 1,
      invalid: 0,
    });

    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.importRecord).toHaveBeenCalledWith(expect.anything(), false, false);
      expect(screen.queryByTestId("record-import-modal")).toBeNull();
    });
  });
});
