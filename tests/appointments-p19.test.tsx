// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { AppointmentSchedulingScreen } from "../app/components/provider/AppointmentSchedulingScreen";
import { api, Appointment } from "../app/lib/api";
import { translations } from "../app/translations";
import { resolveHumanName } from "../app/lib/presentation";

const mockAppContext = {
  portal: "provider" as const,
  screen: "home" as const,
  providerScreen: "schedule_appointment" as const,
  adminScreen: "dashboard" as const,
  language: "en" as const,
  isUrdu: false,
  isRomanUrdu: false,
  t: translations.en,
  isLiveMode: true,
  selectedPatient: "sim-bilal",
  resolvedCases: [],
  demoScenario: "normal",
  providerIdentifier: "prov-demo-im",
  providerDisplayName: "Dr. Demo Internal Med (fictional)",
  appointment: null,
  setAppointment: vi.fn(),
  setProviderScreen: vi.fn(),
};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("P2-19: Provider Scheduling, Priority Elevation, and Clean Names", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("resolves raw IDs to human-readable names", () => {
    expect(resolveHumanName("prov-demo-im")).toBe("Dr. Demo Internal Med (fictional)");
    expect(resolveHumanName("sim-bilal")).toBe("Bilal A. (age 67)");
    expect(resolveHumanName("12edb5a0-ec71-45b7-aff6-0fef1c382881")).toBe("SMART Patient (Age 75, Dual)");
  });

  it("renders dynamic subtitle and patient context for the case patient (Bilal A.)", async () => {
    vi.spyOn(api, "getProviderAppointments").mockResolvedValue({ appointments: [] });

    render(<AppointmentSchedulingScreen />);

    // Subtitle shows case patient's name, not hardcoded Ali Khan
    const sub = screen.getByTestId("schedule-subtitle");
    expect(sub.textContent).toContain("Bilal A. (age 67)");
    expect(sub.textContent).not.toContain("Ali Khan");

    // Slot picker tab is active by default when selectedPatient is set
    const nameEl = screen.getByTestId("schedule-patient-name");
    expect(nameEl.textContent).toBe("Bilal A. (age 67)");

    // Confirm booking records appointment for that patient
    const confirmBtn = screen.getByRole("button", { name: /confirm appointment/i });
    fireEvent.click(confirmBtn);

    expect(mockAppContext.setAppointment).toHaveBeenCalledWith(
      expect.objectContaining({
        isBooked: true,
        reason: expect.stringContaining("Bilal A. (age 67)"),
      })
    );
  });

  it("never says 'Routine clinical review' on urgent appointments", async () => {
    const mockAppointments: Appointment[] = [
      {
        id: "apt-urg-1",
        checkin_id: "chk-123",
        patient_id: "sim-bilal",
        provider_id: "prov-demo-im",
        specialty: "cardiology_im",
        urgency: "urgent",
        mode: "in_person",
        status: "booked",
        slot_date: "2026-11-16",
        created_at: "2026-11-15T12:00:00Z",
      },
    ];

    vi.spyOn(api, "getProviderAppointments").mockResolvedValue({ appointments: mockAppointments });

    render(<AppointmentSchedulingScreen />);

    // Switch to roster tab
    const rosterTab = document.getElementById("tab-appointments-roster")!;
    fireEvent.click(rosterTab);

    await waitFor(() => {
      // Reason text must not say 'Routine clinical review' on urgent row
      expect(screen.queryByText(/Routine clinical review/i)).toBeNull();
      expect(screen.getByText(/Urgent clinical review/i)).toBeTruthy();

      // Names are human-readable, not raw IDs
      expect(screen.getAllByText(/Bilal A\. \(age 67\)/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Dr\. Demo Internal Med/i)).toBeTruthy();
    });
  });
});
