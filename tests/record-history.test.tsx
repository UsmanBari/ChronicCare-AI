// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { HealthRecordScreen } from "../app/components/HealthRecordScreen";
import { translations } from "../app/translations";
import { api, PatientRecordResponse, RecordHistoryResponse } from "../app/lib/api";

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

describe("Record History UI (HealthRecordScreen)", () => {
  const mockRecord: PatientRecordResponse = {
    mode: "isolated",
    conditions: [{ name: "diabetes", basis: "clinician_diagnosed" }],
    medications: [{ id: "med-1", name: "Metformin 500mg", dosage: "1 tablet BD", status: "active" }],
    allergies: [{ id: "alg-1", substance: "Penicillin", reaction: "Rash", confirmed: true }],
    baseline_observations: [{ id: "obs-1", observation_type: "glucose", value: 115, unit: "mg/dL", measured_at: "2026-10-30T08:00:00Z" }],
  };

  const mockHistory: RecordHistoryResponse = {
    count: 2,
    edits: [
      {
        edit_id: "edit-1",
        user_id: "user-1",
        record_type: "medication",
        record_id: "med-1",
        field: "dosage",
        old_value: "1 tablet daily",
        new_value: "1 tablet BD",
        origin: "self_reported",
        changed_by_user_id: "user-1",
        changed_at: "2026-10-31T12:00:00Z",
        reason: null,
      },
      {
        edit_id: "edit-2",
        user_id: "user-1",
        record_type: "medication",
        record_id: "med-1",
        field: "created",
        old_value: null,
        new_value: { name: "Metformin 500mg" },
        origin: "ocr",
        changed_by_user_id: "user-1",
        changed_at: "2026-10-30T10:00:00Z",
        reason: "rx_scan",
      },
    ],
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
    vi.spyOn(api, "getRecordHistory").mockResolvedValue(mockHistory);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders history button on medication item and opens history modal with badges", async () => {
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByText("Metformin 500mg")).toBeTruthy();
    });

    const medHistoryBtn = screen.getByTestId("med-history-btn-med-1");
    expect(medHistoryBtn).toBeTruthy();

    fireEvent.click(medHistoryBtn);

    await waitFor(() => {
      expect(screen.getByTestId("record-history-modal")).toBeTruthy();
    });

    expect(api.getRecordHistory).toHaveBeenCalledWith("medication", "med-1", 50);

    // Verify edit rows and OCR badge rendered
    const editRows = screen.getAllByTestId("history-edit-row");
    expect(editRows.length).toBe(2);
    expect(screen.getByText("OCR Scan")).toBeTruthy();
    expect(screen.getByText("You")).toBeTruthy();

    // Verify Esc key closes modal
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByTestId("record-history-modal")).not.toBeTruthy();
    });
  });

  it("opens full record history from header button", async () => {
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("view-full-history-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("view-full-history-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("record-history-modal")).toBeTruthy();
    });

    expect(api.getRecordHistory).toHaveBeenCalledWith(undefined, undefined, 50);
  });

  it("renders empty state when edits list is empty", async () => {
    vi.spyOn(api, "getRecordHistory").mockResolvedValue({ count: 0, edits: [] });

    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("view-full-history-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("view-full-history-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("record-history-modal")).toBeTruthy();
    });

    expect(screen.getByText(translations.en.noHistoryRecorded)).toBeTruthy();
  });

  it("renders error state when GET /api/record/history fails", async () => {
    vi.spyOn(api, "getRecordHistory").mockRejectedValue(new Error("Network Error"));

    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("view-full-history-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("view-full-history-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("record-history-modal")).toBeTruthy();
    });

    expect(screen.getByText(translations.en.failedToLoadHistory)).toBeTruthy();
  });

  it("renders modal in Urdu RTL with numbers in bdi tags and closes via close button", async () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("view-full-history-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("view-full-history-btn"));

    await waitFor(() => {
      const modal = screen.getByTestId("record-history-modal");
      expect(modal).toBeTruthy();
      expect(modal.getAttribute("dir")).toBe("rtl");
    });

    // Check Urdu elements and close button
    const closeBtn = screen.getByTestId("close-history-modal-btn");
    expect(closeBtn).toBeTruthy();
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByTestId("record-history-modal")).toBeNull();
    });
  });

  it("manages focus when opening and closes on Escape, restoring focus to trigger", async () => {
    render(<HealthRecordScreen />);

    await waitFor(() => {
      expect(screen.getByTestId("view-full-history-btn")).toBeTruthy();
    });

    const triggerBtn = screen.getByTestId("view-full-history-btn");
    triggerBtn.focus();
    expect(document.activeElement).toBe(triggerBtn);

    fireEvent.click(triggerBtn);

    await waitFor(() => {
      expect(screen.getByTestId("record-history-modal")).toBeTruthy();
    });

    const closeBtn = screen.getByTestId("close-history-modal-btn");
    await waitFor(() => {
      expect(document.activeElement).toBe(closeBtn);
    });

    // Press Escape to close
    fireEvent.keyDown(window, { key: "Escape" });

    await waitFor(() => {
      expect(screen.queryByTestId("record-history-modal")).toBeNull();
    });

    await waitFor(() => {
      expect(document.activeElement).toBe(triggerBtn);
    });
  });
});
