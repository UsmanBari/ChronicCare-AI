// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { NotificationBell } from "../app/components/NotificationBell";
import { PatientAppointmentsScreen } from "../app/components/PatientAppointmentsScreen";
import { AppointmentSchedulingScreen } from "../app/components/provider/AppointmentSchedulingScreen";
import OcrConfirmScreen from "../app/components/OcrConfirmScreen";
import { getRoleFromEmail } from "../app/lib/roles";
import { translations } from "../app/translations";
import { api } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("Mock Mode Graceful Fallback & Accessibility (I4-S / U9)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = false;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.portal = "patient";
    mockAppContext.setScreen = vi.fn();
    mockAppContext.setProviderScreen = vi.fn();
    mockAppContext.setPortal = vi.fn();
    mockAppContext.appointment = { isBooked: false };
    mockAppContext.demoScenario = "normal";
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("NotificationBell does not call api.getMyNotifications in mock mode", () => {
    const spy = vi.spyOn(api, "getMyNotifications").mockResolvedValue({ notifications: [], unread_count: 0 });
    render(<NotificationBell />);
    expect(spy).not.toHaveBeenCalled();
  });

  it("PatientAppointmentsScreen does not call api.getMyAppointments in mock mode", () => {
    const spy = vi.spyOn(api, "getMyAppointments").mockResolvedValue({ appointments: [] });
    render(<PatientAppointmentsScreen />);
    expect(spy).not.toHaveBeenCalled();
  });

  it("AppointmentSchedulingScreen does not call api.getProviderAppointments in mock mode", () => {
    const spy = vi.spyOn(api, "getProviderAppointments").mockResolvedValue({ appointments: [] });
    render(<AppointmentSchedulingScreen />);
    expect(spy).not.toHaveBeenCalled();
  });

  it("roles.ts correctly maps U8 demo personas in mock mode", () => {
    expect(getRoleFromEmail("demo_patient_new@demo.care")).toBe("patient");
    expect(getRoleFromEmail("demo_patient_htn@demo.care")).toBe("patient");
    expect(getRoleFromEmail("demo_patient_dm@demo.care")).toBe("patient");
    expect(getRoleFromEmail("demo_patient_ur@demo.care")).toBe("patient");
    expect(getRoleFromEmail("provider.demo@demo.care")).toBe("provider");
    expect(getRoleFromEmail("admin.demo@demo.care")).toBe("admin");
  });

  it("OcrConfirmScreen renders accessible aria-labels on editable input fields", () => {
    mockAppContext.stagedOcrUpload = {
      upload_id: "test-upload",
      expires_in_seconds: 3600,
      extracted: {
        observations: [{ id: "obs-1", type: "glucose", value: 140, unit: "mg/dL", evidence: "FBS: 140" }],
        medications: [{ id: "med-1", name: "Glimepiride", dosage: "2mg", status: "active", evidence: "Glimepiride 2mg" }],
        allergies: [{ id: "all-1", substance: "Penicillin", reaction: "Rash", severity: "moderate", status: "active", evidence: "Penicillin" }],
      },
    };

    const { container } = render(<OcrConfirmScreen />);

    // Since confidence defaults to Low, isEditing is true on mount
    const nameInput = container.querySelector('input[aria-label="Medication Name"]') as HTMLInputElement;
    expect(nameInput).toBeTruthy();
    expect(nameInput.value).toBe("Glimepiride");

    const doseInput = container.querySelector('input[aria-label="Medication Dosage"]') as HTMLInputElement;
    expect(doseInput).toBeTruthy();
    expect(doseInput.value).toBe("2mg");
  });
});
