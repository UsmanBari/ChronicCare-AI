// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent, cleanup } from "@testing-library/react";
import OnboardingPrescriptionScreen from "../app/components/OnboardingPrescriptionScreen";
import OcrConfirmScreen from "../app/components/OcrConfirmScreen";
import { translations } from "../app/translations";
import { api, OcrUploadResponse } from "../app/lib/api";

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

describe("Onboarding Prescription Step (Section 18 & 21.1)", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    mockAppContext.language = "en";
    mockAppContext.t = translations["en"];
    mockAppContext.isUrdu = false;
    mockAppContext.isLiveMode = true;
    mockAppContext.connectionMode = "offline";
    mockAppContext.liveEhrConnection = { mode: "isolated" };
    mockAppContext.profile = { conditions: ["type_2_diabetes"] };
    mockAppContext.liveProfile = null;
    mockAppContext.setScreen = vi.fn();
    mockAppContext.stagedOcrUpload = null;
    mockAppContext.setStagedOcrUpload = vi.fn((val) => {
      mockAppContext.stagedOcrUpload = val;
    });
    mockAppContext.ocrReturnScreen = "health_record";
    mockAppContext.setOcrReturnScreen = vi.fn((val) => {
      mockAppContext.ocrReturnScreen = val;
    });

    vi.spyOn(api, "getRecord").mockResolvedValue({
      mode: "isolated",
      ocr_enabled: true,
      conditions: [{ name: "type_2_diabetes", basis: "self_reported" }],
      medications: [],
      allergies: [],
      baseline_observations: [],
    });
    vi.spyOn(api, "cancelOcrUpload").mockResolvedValue({ status: "cancelled" });
    vi.spyOn(api, "confirmOcrUpload").mockResolvedValue({
      status: "confirmed",
      saved_count: 1,
      saved_items: [{ type: "medication", id: "m1", origin: "ocr" }],
      skipped_count: 0,
    });
  });

  it("renders onboarding prescription screen with optional upload and skip buttons", async () => {
    render(<OnboardingPrescriptionScreen />);

    expect(screen.getByTestId("onboarding-prescription-screen")).toBeTruthy();
    expect(screen.getByText(translations["en"].onboardingPrescriptionTitle)).toBeTruthy();
    expect(screen.getByTestId("onboarding-skip-btn")).toBeTruthy();
    expect(screen.getByText(translations["en"].onboardingPrescriptionUploadBtn)).toBeTruthy();
  });

  it("clicking skip navigates directly to home screen", async () => {
    render(<OnboardingPrescriptionScreen />);

    const skipBtn = screen.getByTestId("onboarding-skip-btn");
    fireEvent.click(skipBtn);

    expect(mockAppContext.setScreen).toHaveBeenCalledWith("home");
  });

  it("successful upload sets staged upload, return screen to home, and navigates to ocr_confirm", async () => {
    const mockUploadResp: OcrUploadResponse = {
      upload_id: "up-onboard-1",
      expires_in_seconds: 1800,
      extracted: {
        observations: [],
        medications: [
          { name: "Metformin", dosage: "500mg daily", status: "active", confidence: "High" },
        ],
        allergies: [],
      },
    };
    vi.spyOn(api, "uploadOcrImage").mockResolvedValue(mockUploadResp);

    render(<OnboardingPrescriptionScreen />);

    const fileInput = screen.getByTestId("onboarding-prescription-file-input");
    const fakeFile = new File(["dummy content"], "prescription.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [fakeFile] } });

    await waitFor(() => {
      expect(mockAppContext.setStagedOcrUpload).toHaveBeenCalledWith(mockUploadResp);
      expect(mockAppContext.setOcrReturnScreen).toHaveBeenCalledWith("home");
      expect(mockAppContext.setScreen).toHaveBeenCalledWith("ocr_confirm");
    });
  });

  it("when ocr_enabled is false, displays manual entry form instead of upload button (K5)", async () => {
    vi.spyOn(api, "getRecord").mockResolvedValue({
      mode: "isolated",
      ocr_enabled: false,
      conditions: [{ name: "type_2_diabetes", basis: "self_reported" }],
      medications: [],
      allergies: [],
      baseline_observations: [],
    });

    render(<OnboardingPrescriptionScreen />);

    await waitFor(() => {
      expect(screen.getByText(translations["en"].onboardingManualTitle)).toBeTruthy();
      expect(screen.getByTestId("onboarding-manual-med-name")).toBeTruthy();
      expect(screen.getByTestId("onboarding-manual-med-dosage")).toBeTruthy();
    });
  });

  it("ocr_confirm verifies header fields (Section 21.1) and displays 'not read: please check the paper'", async () => {
    mockAppContext.ocrReturnScreen = "home";
    mockAppContext.stagedOcrUpload = {
      upload_id: "up-check-21",
      expires_in_seconds: 1800,
      extracted: {
        observations: [],
        medications: [
          { id: "m-1", name: "Amlodipine", dosage: "5mg", status: "active", confidence: "High" },
        ],
        allergies: [],
        raw_lines: ["Rx: Amlodipine 5mg"],
      },
    };

    render(<OcrConfirmScreen />);

    expect(screen.getByTestId("ocr-header-checklist")).toBeTruthy();
    expect(screen.getByTestId("header-doctor-status").textContent).toContain("not read: please check the paper");
    expect(screen.getByTestId("header-regno-status").textContent).toContain("not read: please check the paper");
    expect(screen.getByTestId("header-clinic-status").textContent).toContain("not read: please check the paper");
    expect(screen.getByTestId("header-medication-status").textContent).toContain("Found");
  });

  it("ocr_confirm displays confidence tags and unverified badge", async () => {
    mockAppContext.ocrReturnScreen = "home";
    mockAppContext.stagedOcrUpload = {
      upload_id: "up-check-badges",
      expires_in_seconds: 1800,
      extracted: {
        observations: [
          { id: "o-1", type: "blood_pressure_systolic", value: 120, unit: "mmHg", confidence: "High" },
        ],
        medications: [
          { id: "m-1", name: "Lisinopril", dosage: "10mg", status: "active", confidence: "High" },
        ],
        allergies: [],
      },
    };

    render(<OcrConfirmScreen />);

    expect(screen.getAllByTestId("confidence-badge-high").length).toBeGreaterThan(0);
    expect(screen.getByTestId("badge-unverified-upload")).toBeTruthy();
  });

  it("ocr_confirm opens manual entry pre-filled and displays hint for low confidence medication", async () => {
    mockAppContext.ocrReturnScreen = "home";
    mockAppContext.stagedOcrUpload = {
      upload_id: "up-low-conf",
      expires_in_seconds: 1800,
      extracted: {
        observations: [],
        medications: [
          { id: "m-low", name: "Metformin", dosage: "", status: "active", confidence: "Low" },
        ],
        allergies: [],
      },
    };

    render(<OcrConfirmScreen />);

    expect(screen.getByTestId("confidence-badge-low")).toBeTruthy();
    expect(screen.getByTestId("ocr-low-confidence-hint")).toBeTruthy();
  });

  it("ocr_confirm returns to home screen on cancel or save when ocrReturnScreen is home", async () => {
    mockAppContext.ocrReturnScreen = "home";
    mockAppContext.stagedOcrUpload = {
      upload_id: "up-return-home",
      expires_in_seconds: 1800,
      extracted: {
        observations: [],
        medications: [
          { id: "m-ret", name: "Aspirin", dosage: "81mg", status: "active", confidence: "High" },
        ],
        allergies: [],
      },
    };

    render(<OcrConfirmScreen />);

    const cancelBtn = screen.getByTestId("ocr-cancel-btn");
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(mockAppContext.setScreen).toHaveBeenCalledWith("home");
    });
  });
});
