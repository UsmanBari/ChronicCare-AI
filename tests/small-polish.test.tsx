// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Mock AppContext
const mockContext: any = {
  returnToHomeAndClearRun: vi.fn(),
  escalationRecorded: true,
  isLiveMode: true,
  isUrdu: false,
  language: "en",
  t: {
    emergencyGuidanceText: "Based on your responses, please seek medical attention promptly.",
    directHotlineDispatch: "Direct Emergency Hotline:",
    finishBtn: "Return to Home",
    emergencyDetectedTitle: "Emergency Pattern Detected",
    emergencyAlertedText: "Your care provider has been alerted.",
    appointmentSpecialty: "Specialty",
    bookAppointmentBtn: "Book Offered Appointment",
    cancelAppointmentBtn: "Decline Appointment",
  },
  liveCheckinResult: null,
  activeLiveCheckin: null,
  appointment: { status: "Requested", isBooked: false, slot: "", reason: "", provider: "", bookedAt: "" },
  setAppointment: vi.fn(),
  checkIn: { note: "", thirst: null, urination: null, missedMeds: null, lowConfidence: false, submittedAt: null },
  activeTab: "open",
  setActiveTab: vi.fn(),
  reviewQueue: [],
  isLoadingQueue: false,
  refreshQueue: vi.fn(),
  selectedFilter: "all",
  setSelectedFilter: vi.fn(),
  resolvedCases: [],
  acknowledgedPatients: [],
};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockContext,
}));

vi.mock("../app/lib/api", () => ({
  api: {
    getVoiceStatus: vi.fn().mockResolvedValue({ tts_enabled: false }),
    getEmergencySpeech: vi.fn(),
    bookAppointment: vi.fn(),
    cancelAppointment: vi.fn(),
    getReviewQueue: vi.fn().mockResolvedValue([]),
    getNotifications: vi.fn().mockResolvedValue([]),
  },
}));

import { ReviewQueueScreen } from "../app/components/provider/ReviewQueueScreen";
import { RoutedToReviewScreen } from "../app/components/RoutedToReviewScreen";
import { EmergencyScreen } from "../app/components/EmergencyScreen";

describe("Item 6: Small Polish (c, d, e)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockContext.liveCheckinResult = null;
    mockContext.activeLiveCheckin = null;
  });

  it("(c) ReviewQueueScreen displays 'ChronicCare Triage Engine' instead of 'City General'", () => {
    render(<ReviewQueueScreen />);
    expect(screen.getByText("ChronicCare Triage Engine")).toBeDefined();
    expect(screen.queryByText("City General Triage Engine")).toBeNull();
  });

  it("(d) RoutedToReviewScreen default selected slot has working hour 10:00", () => {
    mockContext.liveCheckinResult = {
      appointment: { id: "apt-1", status: "offered", slot_date: "" },
    };
    render(<RoutedToReviewScreen />);
    const picker = screen.getByLabelText("Appointment Slot") as HTMLInputElement;
    expect(picker.value).toContain("T10:00");
  });

  it("(e) EmergencyScreen shows 'If awake and able to swallow, take sugar or juice now' alongside 1122 for severe hypoglycaemia", () => {
    mockContext.activeLiveCheckin = {
      emergency: true,
      emergency_reason: "glucose low: glucose 45 mg/dL; Low glucose with disorientation or acute confusion.",
      intakes: [
        {
          readings: [{ observation_type: "glucose", value: 45, unit: "mg/dL" }],
        },
      ],
    };

    render(<EmergencyScreen />);

    // Check swallow note is displayed
    const swallowNote = screen.getByTestId("severe-hypo-guidance");
    expect(swallowNote.textContent).toContain("If awake and able to swallow, take sugar or juice now");

    // Check hotline instruction alongside 1122
    const hotlineInstruction = screen.getByTestId("emergency-hotline-hypo-instruction");
    expect(hotlineInstruction.textContent).toContain("If awake and able to swallow, take sugar or juice now");

    // Verify 1122 is present
    expect(screen.getByRole("link", { name: /1122/i })).toBeDefined();
  });
});
