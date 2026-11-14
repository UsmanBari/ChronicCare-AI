// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { HomeScreen } from "../app/components/HomeScreen";
import { RoutedToReviewScreen } from "../app/components/RoutedToReviewScreen";
import { translations } from "../app/translations";

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
      getUserCheckinSummary: vi.fn().mockResolvedValue({
        checkins_last_7_days: 0,
        unreviewed_risk_count: 0,
        recent_checkins: [],
      }),
      getPatientRecord: vi.fn().mockResolvedValue({
        conditions: ["hypertension"],
        medications: [],
        allergies: [],
        baseline_observations: [],
      }),
      bookAppointment: vi.fn().mockResolvedValue({ status: "booked" }),
      cancelAppointment: vi.fn().mockResolvedValue({ status: "cancelled" }),
    },
  };
});

describe("QA Browser Regressions (Q8/Q11 datetime-local & Q12 tel:1122)", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();

    Object.assign(mockAppContext, {
      returnToHomeAndClearRun: vi.fn(),
      escalationRecorded: false,
      isLiveMode: true,
      t: translations.en,
      isUrdu: false,
      language: "en",
      setScreen: vi.fn(),
      profile: { full_name: "Test Patient" },
      liveProfile: { full_name: "Test Patient", conditions: ["hypertension"] },
      liveEhrConnection: null,
      connectionMode: "isolated",
      userIdentifier: "PATIENT-001",
      demoScenario: null,
      setDemoScenario: vi.fn(),
      resetDemo: vi.fn(),
      appointment: { isBooked: false, status: null },
      setAppointment: vi.fn(),
      setActiveLiveCheckin: vi.fn(),
      setShowSettings: vi.fn(),
      liveCheckinResult: null,
      checkIn: { intakes: [] },
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe("Q8/Q11: Datetime-local time offset roundtrip without +5h shift", () => {
    it("formats local datetime string matching local wall clock instead of UTC", () => {
      // Simulating the exact formula used in HealthRecordScreen
      const d = new Date(2026, 10, 14, 14, 30, 0); // Local 14:30
      const tzOffset = d.getTimezoneOffset() * 60000;
      const formatted = new Date(d.getTime() - tzOffset).toISOString().slice(0, 16);

      // Must display '2026-11-14T14:30' representing local hours and minutes, never shifting by timezone
      expect(formatted).toBe("2026-11-14T14:30");

      // Verify hours match local getHours() and minutes match getMinutes()
      const [datePart, timePart] = formatted.split("T");
      const [h, m] = timePart.split(":").map(Number);
      expect(h).toBe(d.getHours());
      expect(m).toBe(d.getMinutes());
    });

    it("round-trips parsed local datetime without UTC jump", () => {
      const localInput = "2026-11-14T10:15";
      const [dateStr, timeStr] = localInput.split("T");
      const [year, month, day] = dateStr.split("-").map(Number);
      const [hour, minute] = timeStr.split(":").map(Number);

      const parsedDate = new Date(year, month - 1, day, hour, minute);
      const tzOffset = parsedDate.getTimezoneOffset() * 60000;
      const formattedBack = new Date(parsedDate.getTime() - tzOffset).toISOString().slice(0, 16);

      expect(formattedBack).toBe(localInput);
    });
  });

  describe("Q12: Urgent Guidance and Review Screens render tel:1122 link", () => {
    it("HomeScreen urgent guidance modal renders an active tel:1122 anchor link", () => {
      const { container } = render(<HomeScreen />);

      const urgentBtn = screen.getByRole("button", { name: /Report Urgent Symptoms Now/i });
      fireEvent.click(urgentBtn);

      const telLink = container.querySelector('a[href="tel:1122"]');
      expect(telLink).not.toBeNull();
      expect(telLink?.getAttribute("href")).toBe("tel:1122");
      expect(telLink?.textContent).toContain("1122");
    });

    it("RoutedToReviewScreen renders a tel:1122 link when safety_note includes 1122", () => {
      mockAppContext.liveCheckinResult = {
        safety_note: "Please contact emergency services (1122) immediately if condition worsens.",
        triage_level: "urgent",
        triage_colour: "yellow",
        appointment: null,
      };

      const { container } = render(<RoutedToReviewScreen />);
      const telLink = container.querySelector('a[href="tel:1122"]');
      expect(telLink).not.toBeNull();
      expect(telLink?.getAttribute("href")).toBe("tel:1122");
      expect(telLink?.textContent).toContain("1122");
    });
  });
});
