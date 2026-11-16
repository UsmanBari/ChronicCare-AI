// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { AppointmentSchedulingScreen } from "../app/components/provider/AppointmentSchedulingScreen";
import { ReconciliationAlertDetail } from "../app/components/provider/ReconciliationAlertDetail";
import { api } from "../app/lib/api";
import { translations } from "../app/translations";

const mockContext: any = {
  portal: "provider" as const,
  screen: "home" as const,
  providerScreen: "schedule_appointment" as const,
  adminScreen: "dashboard" as const,
  language: "en" as const,
  isUrdu: false,
  isRomanUrdu: false,
  t: translations.en,
  isLiveMode: true,
  selectedPatient: "278f0a97-9999-4444-bbbb-0123456789ab",
  selectedPatientDisplay: "Tariq Mahmood (local_tariq_001)",
  selectedPatientId: "local_tariq_001",
  setSelectedPatientDisplay: vi.fn(),
  setSelectedPatientId: vi.fn(),
  resolvedCases: [],
  demoScenario: "normal",
  providerIdentifier: "prov-demo-im",
  providerDisplayName: "Dr. Demo Internal Med",
  appointment: null,
  setAppointment: vi.fn(),
  setProviderScreen: vi.fn(),
  resolveCase: vi.fn(),
};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockContext,
}));

describe("Item 2: Provider Schedule Appointment from a Case", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("shows case patient display name and NOT generic Hospital Patient (278f0a97)", async () => {
    mockContext.appointment = null;
    mockContext.providerScreen = "schedule_appointment";

    vi.spyOn(api, "getProviderAppointments").mockResolvedValue({ appointments: [] });
    const createSpy = vi.spyOn(api, "createAppointment").mockResolvedValue({
      id: "apt-123",
      patient_id: "local_tariq_001",
      status: "booked",
      slot_date: "Tomorrow • 10:00 AM",
    } as any);

    render(<AppointmentSchedulingScreen />);

    // Subtitle must show Tariq Mahmood (local_tariq_001)
    const subtitle = screen.getByTestId("schedule-subtitle");
    expect(subtitle.textContent).toContain("Tariq Mahmood (local_tariq_001)");
    expect(subtitle.textContent).not.toContain("Hospital Patient (278f0a97)");

    // Patient name in slot context card
    const patientName = screen.getByTestId("schedule-patient-name");
    expect(patientName.textContent).toBe("Tariq Mahmood (local_tariq_001)");

    // Confirm booking calls api.createAppointment
    const confirmBtn = screen.getByRole("button", { name: /confirm appointment/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          patient_id: "local_tariq_001",
        })
      );
    });

    expect(mockContext.setAppointment).toHaveBeenCalledWith(
      expect.objectContaining({
        isBooked: true,
        patientName: "Tariq Mahmood (local_tariq_001)",
        patientId: "local_tariq_001",
      })
    );
  });

  it("scheduled appointment appears on the case review card", async () => {
    mockContext.providerScreen = "reconciliation_alert";
    mockContext.appointment = {
      isBooked: true,
      slot: "Tomorrow • 10:00 AM",
      provider: "Dr. Sana Malik",
      status: "Confirmed",
      reason: "Follow-up consultation for Tariq Mahmood (local_tariq_001)",
      bookedAt: "Just now",
    };

    vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue({
      checkin_id: "278f0a97-9999-4444-bbbb-0123456789ab",
      patient_id: "local_tariq_001",
      patient_display: "Tariq Mahmood (local_tariq_001)",
      patient_background: {},
      reconciliation: { observation_comparisons: [] },
      verification: { observation_verifications: [] },
      triage_level: "review",
      triage_colour: "amber",
      emergency: false,
      mode: "isolated",
    } as any);

    vi.spyOn(api, "getProviderSoapNote").mockResolvedValue({
      subjective: ["Patient check-in"],
      objective: ["Readings"],
      assessment: ["Review"],
      plan: ["Follow-up"],
    } as any);

    render(<ReconciliationAlertDetail />);

    await waitFor(() => {
      const banner = screen.getByTestId("review-scheduled-appointment");
      expect(banner).toBeTruthy();
      expect(banner.textContent).toContain("Tomorrow • 10:00 AM");
      expect(banner.textContent).toContain("Dr. Sana Malik");
      expect(banner.textContent).toContain("Confirmed");
    });
  });
});
