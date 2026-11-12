// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor, fireEvent } from "@testing-library/react";
import { ProviderDashboardScreen } from "../app/components/provider/ProviderDashboardScreen";
import { AdminDashboardScreen } from "../app/components/admin/AdminDashboardScreen";
import { Header } from "../app/components/Header";
import { translations } from "../app/translations";
import { api } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("Live Mode Demo Identities Gating (Part E)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(mockAppContext, {
      portal: "provider",
      screen: "dashboard",
      providerScreen: "dashboard",
      adminScreen: "dashboard",
      language: "en",
      t: translations.en,
      isUrdu: false,
      isLiveMode: true,
      providerIdentifier: "dr.usman@care.org",
      providerDisplayName: "Dr. Usman Bari",
      userIdentifier: "patient@care.org",
      adminIdentifier: "admin@care.org",
      demoScenario: "normal",
      resolvedCases: [],
      acknowledgedPatients: [],
      appointment: { isBooked: false, slot: "", reason: "", provider: "", status: "Confirmed", bookedAt: "" },
      setPortal: vi.fn(),
      setScreen: vi.fn(),
      setProviderScreen: vi.fn(),
      setAdminScreen: vi.fn(),
      setShowSettings: vi.fn(),
      setShowTour: vi.fn(),
      returnToHomeAndClearRun: vi.fn(),
      signOutUser: vi.fn(),
      setAppointment: vi.fn(),
      setSelectedPatient: vi.fn(),
      setLanguage: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("ProviderDashboardScreen", () => {
    it("in live mode shows signed-in user's display name and never 'Sana'", () => {
      mockAppContext.isLiveMode = true;
      mockAppContext.providerDisplayName = "Dr. Fatima Zahra";
      mockAppContext.providerIdentifier = "dr.fatima@hospital.org";

      const { container } = render(<ProviderDashboardScreen />);

      expect(screen.getByText("Dr. Fatima Zahra")).toBeTruthy();
      expect(container.textContent).not.toContain("Sana");
      expect(container.textContent).not.toContain("City General Clinic");
      expect(container.textContent).not.toContain("Sara Ahmed");
      expect(screen.getByText("No assigned patients yet")).toBeTruthy();
      expect(screen.getByText("No activity yet")).toBeTruthy();
    });

    it("in live mode with no display name falls back to provider email", () => {
      mockAppContext.isLiveMode = true;
      mockAppContext.providerDisplayName = null;
      mockAppContext.providerIdentifier = "dr.tariq@hospital.org";

      const { container } = render(<ProviderDashboardScreen />);

      expect(screen.getByText("dr.tariq@hospital.org")).toBeTruthy();
      expect(container.textContent).not.toContain("Sana");
    });

    it("in live mode with neither name nor email falls back to translated 'Provider'", () => {
      mockAppContext.isLiveMode = true;
      mockAppContext.providerDisplayName = null;
      mockAppContext.providerIdentifier = "";

      const { container } = render(<ProviderDashboardScreen />);

      expect(screen.getByText("Provider")).toBeTruthy();
      expect(container.textContent).not.toContain("Sana");
    });

    it("in live mode with Urdu language falls back to 'ڈاکٹر'", () => {
      mockAppContext.isLiveMode = true;
      mockAppContext.isUrdu = true;
      mockAppContext.language = "ur";
      mockAppContext.t = translations.ur;
      mockAppContext.providerDisplayName = null;
      mockAppContext.providerIdentifier = "";

      const { container } = render(<ProviderDashboardScreen />);

      expect(screen.getByText("ڈاکٹر")).toBeTruthy();
      expect(container.textContent).not.toContain("Sana");
    });

    it("in demo mode (isLiveMode false) preserves the scripted Dr. Sana story", () => {
      mockAppContext.isLiveMode = false;
      mockAppContext.providerDisplayName = null;
      mockAppContext.providerIdentifier = "dr.sanamalik@citygeneral.org";

      const { container } = render(<ProviderDashboardScreen />);

      expect(screen.getByText("Dr. Sana Malik — City General Clinic")).toBeTruthy();
      expect(container.textContent).toContain("Ali Khan");
      expect(container.textContent).toContain("Sara Ahmed");
      expect(container.textContent).toContain("Ahmed");
      expect(container.textContent).toContain("City General EHR nightly reconciliation");
    });
  });

  describe("AdminDashboardScreen", () => {
    it("in live mode shows no hardcoded providers, appointments, or fake activity", async () => {
      mockAppContext.isLiveMode = true;
      vi.spyOn(api, "getAdminAudit").mockResolvedValue([]);

      const { container } = render(<AdminDashboardScreen />);

      await waitFor(() => {
        expect(screen.getByText("No activity yet")).toBeTruthy();
      });

      expect(container.textContent).not.toContain("Dr. Sana Malik reviewed Ali Khan's case");
      expect(container.textContent).not.toContain("Dr. Sana Malik");
      expect(screen.getByText("No providers registered yet")).toBeTruthy();
      expect(screen.getByText("No appointments scheduled")).toBeTruthy();
      expect(screen.getByText("No patients enrolled yet")).toBeTruthy();
    });

    it("in live mode renders real API audit logs without falling back to fake logs", async () => {
      mockAppContext.isLiveMode = true;
      vi.spyOn(api, "getAdminAudit").mockResolvedValue([
        {
          id: 101,
          action: "security_policy_updated",
          ts: "2026-11-08T12:00:00Z",
          outcome: "ok",
          target: "system",
          actor_user_id: "admin-1",
          detail: {},
        },
      ]);

      const { container } = render(<AdminDashboardScreen />);

      await waitFor(() => {
        expect(screen.getByText("security_policy_updated")).toBeTruthy();
      });

      expect(container.textContent).not.toContain("Dr. Sana Malik reviewed Ali Khan's case");
      expect(container.textContent).not.toContain("Dr. Sana Malik");
    });

    it("in demo mode (isLiveMode false) retains the scripted admin demo data", () => {
      mockAppContext.isLiveMode = false;

      const { container } = render(<AdminDashboardScreen />);

      expect(container.textContent).toContain("Dr. Sana Malik reviewed Ali Khan's case");
      expect(container.textContent).toContain("Dr. Sana Malik");
      expect(container.textContent).toContain("Northside Community Clinic");
    });
  });

  describe("Header Portal Labels", () => {
    it("in live mode displays signed-in provider in portal label and omits (Dr. Sana)", () => {
      mockAppContext.isLiveMode = true;
      mockAppContext.portal = "provider";
      mockAppContext.providerDisplayName = "Dr. Usman Bari";
      mockAppContext.providerIdentifier = "dr.usman@care.org";

      const { container } = render(<Header />);

      // The switcher button shows the signed-in provider's name
      expect(container.textContent).toContain("Dr. Usman Bari");

      // Open the dropdown menu
      const switcher = container.querySelector("#portal-switcher-btn");
      if (switcher) fireEvent.click(switcher);

      expect(container.textContent).not.toContain("(Dr. Sana)");
      expect(container.textContent).not.toContain("(Dr. Sana Malik)");
      expect(container.textContent).not.toContain("(Ali Khan)");
    });

    it("in demo mode displays (Dr. Sana) in dropdown and mobile menus", () => {
      mockAppContext.isLiveMode = false;
      mockAppContext.portal = "provider";

      const { container } = render(<Header />);

      // Open the dropdown menu
      const switcher = container.querySelector("#portal-switcher-btn");
      if (switcher) fireEvent.click(switcher);

      expect(container.textContent).toContain("(Dr. Sana)");
      expect(container.textContent).toContain("(Ali Khan)");
    });
  });
});
