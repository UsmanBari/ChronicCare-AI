// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";
import OcrConfirmScreen from "../app/components/OcrConfirmScreen";
import { translations } from "../app/translations";
import { api, PatientRecordResponse, OcrUploadResponse } from "../app/lib/api";

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

describe("OCR v1 UI (HealthRecordScreen & OcrConfirmScreen)", () => {
  beforeEach(() => {
    mockAppContext.language = "en";
    mockAppContext.t = translations["en"];
    mockAppContext.isUrdu = false;
    mockAppContext.isLiveMode = true;
    mockAppContext.profile = { conditions: ["diabetes"] };
    mockAppContext.liveProfile = null;
    mockAppContext.setScreen = vi.fn();
    mockAppContext.stagedOcrUpload = null;
    mockAppContext.setStagedOcrUpload = vi.fn((val) => {
      mockAppContext.stagedOcrUpload = val;
    });

    vi.spyOn(api, "getRecord").mockResolvedValue({
      mode: "isolated",
      ocr_enabled: true,
      conditions: [{ name: "diabetes", basis: "clinician_diagnosed" }],
      medications: [
        { id: "m1", name: "Metformin 500mg", dosage: "1 tab BD", status: "active", origin: "ocr" },
      ],
      allergies: [],
      baseline_observations: [
        { id: "o1", observation_type: "glucose", value: 135, unit: "mg/dL", measured_at: "2026-11-01T10:00:00Z", origin: "ocr" },
      ],
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows Upload Lab Report / Prescription button when ocr_enabled is true", async () => {
    render(<HealthRecordScreen />);
    await waitFor(() => {
      expect(screen.getByTestId("upload-ocr-btn")).toBeTruthy();
    });
  });

  it("hides Upload Lab Report / Prescription button when ocr_enabled is false", async () => {
    vi.spyOn(api, "getRecord").mockResolvedValue({
      mode: "isolated",
      ocr_enabled: false,
      conditions: [],
      medications: [],
      allergies: [],
      baseline_observations: [],
    });

    render(<HealthRecordScreen />);
    await waitFor(() => {
      expect(screen.queryByTestId("upload-ocr-btn")).toBeNull();
    });
  });

  it("displays OCR badge on medications and observations with origin='ocr'", async () => {
    render(<HealthRecordScreen />);
    await waitFor(() => {
      const ocrBadges = screen.getAllByText("OCR");
      expect(ocrBadges.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("renders extracted items on OcrConfirmScreen with evidence and allows Confirm/Fix/Remove", async () => {
    const staged: OcrUploadResponse = {
      upload_id: "up-test-123",
      expires_in_seconds: 1800,
      extracted: {
        observations: [
          { id: "obs-0", type: "fasting_blood_glucose", value: 142, unit: "mg/dL", evidence: "Fasting Blood Sugar: 142 mg/dL" },
        ],
        medications: [
          { id: "med-0", name: "Glimepiride", dosage: "2mg daily", status: "active", evidence: "Tab Glimepiride 2mg 1-0-0" },
        ],
        allergies: [
          { id: "all-0", substance: "Penicillin", reaction: "Rash", severity: "moderate", status: "active", evidence: "Allergic to Penicillin" },
        ],
        raw_lines: ["Fasting Blood Sugar: 142 mg/dL", "Tab Glimepiride 2mg 1-0-0", "Allergic to Penicillin"],
        has_urdu: false,
      },
    };

    mockAppContext.stagedOcrUpload = staged;
    render(<OcrConfirmScreen />);

    // Renders title and items
    expect(screen.getByTestId("ocr-confirm-screen")).toBeTruthy();
    expect(screen.getByText(/Confirm Extracted Values/i)).toBeTruthy();
    expect(screen.getByText(/Fasting Blood Sugar: 142 mg\/dL/i)).toBeTruthy();
    expect(screen.getByText(/Tab Glimepiride 2mg 1-0-0/i)).toBeTruthy();
    expect(screen.getByText(/Allergic to Penicillin/i)).toBeTruthy();

    // Toggle observation confirmation
    const toggleBtn = screen.getByTestId("ocr-obs-toggle-0");
    expect(toggleBtn.textContent).toContain("Confirmed");
    fireEvent.click(toggleBtn);
    expect(toggleBtn.textContent).toContain("Confirm");

    // Re-confirm it
    fireEvent.click(toggleBtn);
    expect(toggleBtn.textContent).toContain("Confirmed");

    // Toggle Fix mode for observation
    const fixBtn = screen.getByTestId("ocr-obs-fix-0");
    fireEvent.click(fixBtn);
    const valInput = screen.getByDisplayValue("142") as HTMLInputElement;
    fireEvent.change(valInput, { target: { value: "145" } });
    expect(screen.getByDisplayValue("145")).toBeTruthy();

    // Remove allergy item
    expect(screen.getByTestId("ocr-all-item-0")).toBeTruthy();
    const removeAllergyBtn = screen.getByTestId("ocr-all-remove-0");
    fireEvent.click(removeAllergyBtn);
    expect(screen.queryByTestId("ocr-all-item-0")).toBeNull();

    // Confirm & Save
    const confirmSpy = vi.spyOn(api, "confirmOcrUpload").mockResolvedValue({
      status: "saved",
      saved_count: 2,
      saved_items: [
        { type: "observation", id: "o-new", origin: "ocr" },
        { type: "medication", id: "m-new", origin: "ocr" },
      ],
      skipped_count: 0,
    });

    const saveBtn = screen.getByTestId("ocr-save-confirmed-btn");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalledWith("up-test-123", expect.arrayContaining([
        expect.objectContaining({ type: "fasting_blood_glucose", value: 145 }),
        expect.objectContaining({ name: "Glimepiride", dosage: "2mg daily" }),
      ]));
      expect(mockAppContext.setScreen).toHaveBeenCalledWith("health_record");
    });
  });

  it("shows Urdu document notice when has_urdu is true", () => {
    mockAppContext.language = "ur";
    mockAppContext.t = translations["ur"];
    mockAppContext.isUrdu = true;

    const staged: OcrUploadResponse = {
      upload_id: "up-test-urdu",
      expires_in_seconds: 1800,
      extracted: {
        observations: [],
        medications: [],
        allergies: [],
        raw_lines: ["یہ نسخہ اردو میں لکھا ہے"],
        has_urdu: true,
      },
    };

    mockAppContext.stagedOcrUpload = staged;
    render(<OcrConfirmScreen />);

    expect(screen.getByTestId("ocr-urdu-notice")).toBeTruthy();
    expect(screen.getByText(/ہم فی الحال صرف انگریزی رپورٹس پڑھ سکتے ہیں/i)).toBeTruthy();
  });

  it("cancels upload and navigates back to health_record", async () => {
    const cancelSpy = vi.spyOn(api, "cancelOcrUpload").mockResolvedValue({ status: "cancelled" });

    mockAppContext.stagedOcrUpload = {
      upload_id: "up-cancel-test",
      expires_in_seconds: 1800,
      extracted: { observations: [], medications: [], allergies: [] },
    };

    render(<OcrConfirmScreen />);

    const cancelBtn = screen.getByTestId("ocr-cancel-btn");
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(cancelSpy).toHaveBeenCalledWith("up-cancel-test");
      expect(mockAppContext.setScreen).toHaveBeenCalledWith("health_record");
    });
  });
});
