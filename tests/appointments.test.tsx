// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { PatientAppointmentsScreen } from "../app/components/PatientAppointmentsScreen";
import { RiskResultScreen } from "../app/components/RiskResultScreen";
import { RoutedToReviewScreen } from "../app/components/RoutedToReviewScreen";
import { AppointmentSchedulingScreen } from "../app/components/provider/AppointmentSchedulingScreen";
import { AdminDashboardScreen } from "../app/components/admin/AdminDashboardScreen";
import { translations } from "../app/translations";
import { api, Appointment, ProviderDirectoryEntry } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("Appointments Workflow & Provider Directory (I4-D)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.appointment = { isBooked: false };
    mockAppContext.setScreen = vi.fn();
    mockAppContext.setProviderScreen = vi.fn();
    mockAppContext.setPortal = vi.fn();
    mockAppContext.returnToHomeAndClearRun = vi.fn();
    mockAppContext.demoScenario = "normal";
    mockAppContext.resolvedCases = [];
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("PatientAppointmentsScreen", () => {
    it("renders empty state when no appointments exist", async () => {
      vi.spyOn(api, "getMyAppointments").mockResolvedValue({ appointments: [] });

      render(<PatientAppointmentsScreen />);

      await waitFor(() => {
        expect(screen.getByText(translations.en.noAppointmentsTitle)).toBeTruthy();
      });
    });

    it("renders offered appointment with booking controls and books slot", async () => {
      const mockOffered: Appointment = {
        id: "apt-offered-1",
        patient_id: "p1",
        checkin_id: "chk-1",
        provider_id: "prov-demo-endo",
        specialty: "endocrinology",
        urgency: "routine",
        mode: "telehealth",
        status: "offered",
        slot_date: null,
        created_at: new Date().toISOString(),
      };

      const spyGet = vi.spyOn(api, "getMyAppointments")
        .mockResolvedValueOnce({ appointments: [mockOffered] })
        .mockResolvedValueOnce({
          appointments: [{ ...mockOffered, status: "booked", slot_date: "2026-11-15 10:00" }],
        });

      const spyBook = vi.spyOn(api, "bookAppointment").mockResolvedValue({
        id: "apt-offered-1",
        status: "booked",
        slot_date: "2026-11-15 10:00",
      } as any);

      render(<PatientAppointmentsScreen />);

      await waitFor(() => {
        expect(screen.getByTestId("appointment-card-apt-offered-1")).toBeTruthy();
        expect(screen.getByText(translations.en.appointmentOffered)).toBeTruthy();
        expect(screen.getByText(translations.en.specialtyEndocrinology)).toBeTruthy();
      });

      const bookBtn = screen.getByText(translations.en.bookAppointmentBtn);
      fireEvent.click(bookBtn);

      await waitFor(() => {
        expect(spyBook).toHaveBeenCalledWith("apt-offered-1", expect.any(String));
      });
    });

    it("renders booked appointment with cancel option and cancels it", async () => {
      const mockBooked: Appointment = {
        id: "apt-booked-2",
        patient_id: "p1",
        checkin_id: "chk-2",
        provider_id: "prov-demo-cardio",
        specialty: "cardiology_im",
        urgency: "urgent",
        mode: "in_person",
        status: "booked",
        slot_date: "2026-11-13 14:00",
        created_at: new Date().toISOString(),
        escalation_state: "admin_flag",
      };

      vi.spyOn(api, "getMyAppointments")
        .mockResolvedValueOnce({ appointments: [mockBooked] })
        .mockResolvedValueOnce({
          appointments: [{ ...mockBooked, status: "cancelled" }],
        });

      const spyCancel = vi.spyOn(api, "cancelAppointment").mockResolvedValue({
        id: "apt-booked-2",
        status: "cancelled",
      } as any);

      render(<PatientAppointmentsScreen />);

      await waitFor(() => {
        expect(screen.getByTestId("appointment-card-apt-booked-2")).toBeTruthy();
        expect(screen.getByText(translations.en.escalationAdminFlag)).toBeTruthy();
        expect(screen.getByText(translations.en.cancelAppointmentBtn)).toBeTruthy();
      });

      fireEvent.click(screen.getByText(translations.en.cancelAppointmentBtn));

      await waitFor(() => {
        expect(spyCancel).toHaveBeenCalledWith("apt-booked-2");
      });
    });
  });

  describe("RiskResultScreen Appointment Cards", () => {
    it("renders routine appointment booking card for Yellow review triage", () => {
      mockAppContext.liveCheckinResult = {
        triage_level: "review",
        triage_colour: "yellow",
        appointment: {
          id: "apt-rev-1",
          specialty: "internal_medicine",
          status: "offered",
        },
      };

      render(<RiskResultScreen />);

      expect(screen.getByTestId("triage-appointment-card")).toBeTruthy();
      expect(screen.getByText(translations.en.bookRoutineAppointmentCard)).toBeTruthy();
      expect(screen.getByText(translations.en.specialtyInternalMedicine)).toBeTruthy();

      const btn = screen.getByRole("button", { name: new RegExp(translations.en.bookAppointmentBtn, "i") });
      fireEvent.click(btn);
      expect(mockAppContext.setScreen).toHaveBeenCalledWith("appointments");
    });

    it("renders urgent care team alerted card for Red emergency triage", () => {
      mockAppContext.liveCheckinResult = {
        triage_level: "emergency",
        triage_colour: "red",
        appointment: {
          id: "apt-red-1",
          provider_id: "prov-demo-cardio",
          specialty: "cardiology_im",
          status: "booked",
          slot_date: "Today (Urgent)",
        },
      };

      render(<RiskResultScreen />);

      expect(screen.getByTestId("triage-appointment-card")).toBeTruthy();
      expect(screen.getByText(translations.en.careTeamAlertedCard)).toBeTruthy();
      expect(screen.getByText("prov-demo-cardio")).toBeTruthy();

      const btn = screen.getByRole("button", { name: new RegExp(translations.en.myAppointmentsTitle, "i") });
      fireEvent.click(btn);
      expect(mockAppContext.setScreen).toHaveBeenCalledWith("appointments");
    });
  });

  describe("AppointmentSchedulingScreen (Provider)", () => {
    it("renders provider appointment queue with acknowledge and attended actions", async () => {
      const mockAppointments: Appointment[] = [
        {
          id: "apt-prov-1",
          patient_id: "p-42",
          checkin_id: "chk-42",
          provider_id: "prov-demo-endo",
          specialty: "endocrinology",
          urgency: "urgent",
          mode: "telehealth",
          status: "booked",
          slot_date: "2026-11-13 10:00",
          created_at: new Date().toISOString(),
          escalation_state: "re_notify",
        },
        {
          id: "apt-prov-2",
          patient_id: "p-88",
          checkin_id: "chk-88",
          provider_id: "prov-demo-endo",
          specialty: "endocrinology",
          urgency: "routine",
          mode: "telehealth",
          status: "booked",
          acknowledged_at: new Date().toISOString(),
          slot_date: "2026-11-14 11:30",
          created_at: new Date().toISOString(),
          escalation_state: "acknowledged",
        },
      ];

      vi.spyOn(api, "getProviderAppointments").mockResolvedValue({
        appointments: mockAppointments,
      });

      const spyAck = vi.spyOn(api, "acknowledgeAppointment").mockResolvedValue({
        id: "apt-prov-1",
        acknowledged_at: new Date().toISOString(),
      } as any);

      const spyAtt = vi.spyOn(api, "markAppointmentAttended").mockResolvedValue({
        id: "apt-prov-2",
        status: "attended",
      } as any);

      render(<AppointmentSchedulingScreen />);

      await waitFor(() => {
        expect(screen.getByText("Patient: p-42")).toBeTruthy();
        expect(screen.getByText("Patient: p-88")).toBeTruthy();
      });

      // Acknowledge apt-prov-1
      const ackBtn = screen.getByText(translations.en.acknowledgeAppointmentBtn);
      fireEvent.click(ackBtn);
      await waitFor(() => {
        expect(spyAck).toHaveBeenCalledWith("apt-prov-1");
      });

      // Mark attended apt-prov-2
      const attBtn = screen.getByText(translations.en.markAttendedBtn);
      fireEvent.click(attBtn);
      await waitFor(() => {
        expect(spyAtt).toHaveBeenCalledWith("apt-prov-2");
      });
    });
  });

  describe("AdminDashboardScreen Provider Directory & Escalations", () => {
    it("renders provider directory and toggles provider availability", async () => {
      const mockProviders: ProviderDirectoryEntry[] = [
        {
          id: "prov-demo-endo",
          display_name: "Dr. Ayesha Siddiqa",
          specialty: "endocrinology",
          available: true,
          created_at: new Date().toISOString(),
        },
      ];

      const mockEscalations: Appointment[] = [
        {
          id: "apt-esc-1",
          patient_id: "p-esc",
          checkin_id: "chk-esc",
          provider_id: "prov-demo-endo",
          specialty: "endocrinology",
          urgency: "urgent",
          mode: "telehealth",
          status: "booked",
          created_at: new Date(Date.now() - 25 * 3600 * 1000).toISOString(),
          escalation_state: "admin_flag",
        },
      ];

      vi.spyOn(api, "getAdminConfigStatus").mockResolvedValue({
        settings: [],
        flags: {},
      });
      vi.spyOn(api, "getAdminProviders").mockResolvedValue({ providers: mockProviders });
      vi.spyOn(api, "getAdminEscalations").mockResolvedValue({ escalations: mockEscalations });
      vi.spyOn(api, "getAdminAudit").mockResolvedValue([]);

      const spyToggle = vi.spyOn(api, "updateProviderAvailability").mockResolvedValue({
        ...mockProviders[0],
        available: false,
      });

      render(<AdminDashboardScreen />);

      await waitFor(() => {
        expect(screen.getByText(translations.en.adminProviderDirectoryTitle)).toBeTruthy();
        expect(screen.getByText("Dr. Ayesha Siddiqa")).toBeTruthy();
        expect(screen.getByText(translations.en.adminEscalationAlertsTitle)).toBeTruthy();
        expect(screen.getByText(translations.en.escalationAdminFlag)).toBeTruthy();
      });

      const toggleBtn = screen.getByLabelText("Toggle availability for Dr. Ayesha Siddiqa");
      fireEvent.click(toggleBtn);

      await waitFor(() => {
        expect(spyToggle).toHaveBeenCalledWith("prov-demo-endo", false);
      });
    });
  });

  // =========================================================================
  // P1-7: APPOINTMENT BOOKING CONTRACT & UI SLOT PICKER TESTS
  // =========================================================================
  describe("P1-7: Appointment Booking Shared Contract & Friendly Errors", () => {
    it("RoutedToReviewScreen lets patient pick slot instead of inventing one, books slot, and confirms", async () => {
      const mockLiveApt = {
        id: "apt-review-1",
        patient_id: "pat-1",
        checkin_id: "chk-rev-1",
        specialty: "endocrinology",
        urgency: "routine",
        status: "offered",
        created_at: new Date().toISOString(),
      };

      const spyBook = vi.spyOn(api, "bookAppointment").mockResolvedValue({
        ...mockLiveApt,
        status: "booked",
        slot_date: "2026-11-17T11:00",
      } as any);

      mockAppContext.liveCheckinResult = {
        requires_review: true,
        appointment: mockLiveApt,
      };
      mockAppContext.setAppointment = vi.fn();

      const { container } = render(<RoutedToReviewScreen />);

      // Verify slot picker input exists
      const slotInput = screen.getByLabelText("Appointment Slot") as HTMLInputElement;
      expect(slotInput).toBeTruthy();

      // Change slot to 2026-11-17T11:00
      fireEvent.change(slotInput, { target: { value: "2026-11-17T11:00" } });
      expect(slotInput.value).toBe("2026-11-17T11:00");

      // Click Book Appointment button
      const bookBtn = screen.getByRole("button", { name: /book appointment/i });
      fireEvent.click(bookBtn);

      await waitFor(() => {
        expect(spyBook).toHaveBeenCalledWith("apt-review-1", "2026-11-17T11:00");
      });

      await waitFor(() => {
        expect(container.textContent?.includes("Appointment confirmed with your clinic")).toBe(true);
      });
    });

    it("RoutedToReviewScreen displays friendly error instead of raw API Error 422", async () => {
      const mockLiveApt = {
        id: "apt-review-err",
        status: "offered",
        specialty: "general",
      };

      vi.spyOn(api, "bookAppointment").mockRejectedValue(
        new Error("API Error 422: The selected appointment date is outside the allowed 3-day booking window")
      );

      mockAppContext.liveCheckinResult = {
        requires_review: true,
        appointment: mockLiveApt,
      };

      const { container } = render(<RoutedToReviewScreen />);
      const bookBtn = screen.getByRole("button", { name: /book appointment/i });
      fireEvent.click(bookBtn);

      await waitFor(() => {
        const text = container.textContent || "";
        expect(text.includes("API Error 422:")).toBe(false);
        expect(text.includes("outside the allowed 3-day booking window")).toBe(true);
      });
    });

    it("Provider AppointmentSchedulingScreen shows Confirmed with the booked slot", async () => {
      const mockBookedApt: Appointment = {
        id: "apt-provider-view",
        patient_id: "pat-sandbox-78",
        checkin_id: "chk-sb-78",
        provider_id: "prov-demo-endo",
        specialty: "endocrinology",
        urgency: "routine",
        mode: "telehealth",
        status: "booked",
        slot_date: "2026-11-17 10:30",
        created_at: new Date().toISOString(),
      };

      vi.spyOn(api, "getProviderAppointments").mockResolvedValue({
        appointments: [mockBookedApt],
      });

      const { container } = render(<AppointmentSchedulingScreen />);

      await waitFor(() => {
        expect(container.textContent?.includes("Confirmed")).toBe(true);
        expect(container.textContent?.includes("2026-11-17 10:30")).toBe(true);
      });
    });
  });
});
