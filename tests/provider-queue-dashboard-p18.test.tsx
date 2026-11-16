// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { ProviderDashboardScreen } from "../app/components/provider/ProviderDashboardScreen";
import { ReviewQueueScreen } from "../app/components/provider/ReviewQueueScreen";
import { api, ReviewQueueItemResponse } from "../app/lib/api";
import { translations } from "../app/translations";

const mockAppContext = {
  portal: "provider" as const,
  screen: "home" as const,
  providerScreen: "dashboard" as const,
  adminScreen: "dashboard" as const,
  language: "en" as const,
  isUrdu: false,
  isRomanUrdu: false,
  t: translations.en,
  isLiveMode: true,
  resolvedCases: [],
  acknowledgedPatients: [],
  providerIdentifier: "dr-test",
  providerDisplayName: "Dr. Test Provider",
  setSelectedPatient: vi.fn(),
  setProviderScreen: vi.fn(),
};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("P2-18: Provider Queue and Dashboard Robustness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("counts all emergencies in Urgent Cases and does not hard-code '1 Urgent'", async () => {
    const mockQueue: ReviewQueueItemResponse[] = Array.from({ length: 10 }, (_, i) => ({
      checkin_id: `chk-emg-${i}`,
      patient_display: `Patient ${i}`,
      user_id: `pat-${i}`,
      patient_id: `pat-${i}`,
      mode: "isolated",
      created_at: "2026-11-15T10:00:00Z",
      max_severity: "high",
      emergency: true,
      overdue: false,
      counts: { conflict: 0, flagged: 1 },
      triage_level: "emergency",
      triage_colour: "red",
    }));

    vi.spyOn(api, "getProviderReviewQueue").mockResolvedValue(mockQueue);
    vi.spyOn(api, "getProviderNotifications").mockResolvedValue({ notifications: [], unread_count: 0 });

    render(<ProviderDashboardScreen />);

    await waitFor(() => {
      const badge = screen.getByTestId("urgent-cases-badge");
      expect(badge.textContent).toContain("10 Urgent Cases");
      expect(badge.textContent).not.toBe("1 Urgent");
    });
  });

  it("deduplicates assigned patient cohort by patient identity when 1 patient has many check-ins", async () => {
    // 55 check-ins for the same patient 'Ali Khan'
    const mockQueue: ReviewQueueItemResponse[] = Array.from({ length: 55 }, (_, i) => ({
      checkin_id: `chk-ali-${i}`,
      patient_display: "Ali Khan",
      user_id: "pat-ali",
      patient_id: "pat-ali",
      mode: "connected",
      created_at: "2026-11-15T10:00:00Z",
      max_severity: "moderate",
      emergency: false,
      overdue: false,
      counts: { conflict: 1, flagged: 1 },
      triage_level: "urgent",
      triage_colour: "yellow",
    }));

    vi.spyOn(api, "getProviderReviewQueue").mockResolvedValue(mockQueue);
    vi.spyOn(api, "getProviderNotifications").mockResolvedValue({ notifications: [], unread_count: 0 });

    render(<ProviderDashboardScreen />);

    await waitFor(() => {
      // Cohort header badge shows 1 Assigned Patient, not 55
      expect(screen.getByText("1 Assigned Patients")).toBeTruthy();
    });
  });

  it("in resolved queue: hides OVERDUE, displays provider decision ('Adjusted to Urgent by provider'), and shows date in Received", async () => {
    const mockResolvedQueue: ReviewQueueItemResponse[] = [
      {
        checkin_id: "chk-res-1",
        patient_display: "Zainab Bibi",
        user_id: "pat-zainab",
        patient_id: "pat-zainab",
        mode: "isolated",
        created_at: "2026-11-15T14:30:00Z",
        max_severity: "high",
        emergency: false,
        overdue: true, // Backend or old age flagged overdue, but case is resolved
        review_status: "resolved",
        provider_decision: "adjusted",
        provider_level: "urgent",
        provider_reason: "Elevated BP warrants closer review",
        counts: { conflict: 0, flagged: 1 },
        triage_level: "routine",
        triage_colour: "green",
      },
    ];

    vi.spyOn(api, "getProviderReviewQueue").mockResolvedValue(mockResolvedQueue);

    render(<ReviewQueueScreen />);

    await waitFor(() => {
      // OVERDUE badge is NOT displayed for resolved case
      expect(screen.queryByTestId("queue-row-overdue")).toBeNull();

      // Shows 'Adjusted to Urgent by provider'
      const decisionEl = screen.getByTestId("queue-row-decision");
      expect(decisionEl.textContent).toContain("Adjusted to Urgent by provider");

      // Shows both date and time in Received
      expect(screen.getByText(/Received:\s*Nov\s*15,\s*\d{1,2}:\d{2}/i)).toBeTruthy();
    });
  });
});
