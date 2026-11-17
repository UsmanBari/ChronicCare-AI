// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import App from "../app/page";
import { translations } from "../app/translations";
import { api } from "../app/lib/api";

const mockContext: any = {
  portal: "admin" as const,
  screen: "home" as const,
  providerScreen: "dashboard" as const,
  adminScreen: "dashboard" as const,
  adminIdentifier: "", // Unauthenticated!
  userRole: null,
  language: "en" as const,
  isUrdu: false,
  isRomanUrdu: false,
  t: translations.en,
  isLiveMode: false,
  demoScenario: "normal",
  resolvedCases: [],
  appointment: { isBooked: false, provider: "Dr. Sana Malik", slot: "" },
  showTour: false,
  setShowTour: vi.fn(),
  setPortal: vi.fn(),
  setScreen: vi.fn(),
  setProviderScreen: vi.fn(),
  setAdminScreen: vi.fn(),
};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockContext,
}));

describe("Item 4: Admin Portal Auth Guard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.matchMedia = window.matchMedia || vi.fn().mockImplementation(() => ({
      matches: false,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }));
  });

  afterEach(() => {
    cleanup();
  });

  it("unauthenticated admin portal renders the login screen, not the dashboard", () => {
    mockContext.portal = "admin";
    mockContext.adminScreen = "dashboard"; // Even if adminScreen was requested as dashboard
    mockContext.adminIdentifier = ""; // Nobody signed in!

    render(<App />);

    // Must render Admin Login Screen
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeTruthy();
    expect(screen.getByPlaceholderText(/admin@citygeneral\.org/i)).toBeTruthy();
    expect(screen.getByText(/System Administration Portal/i)).toBeTruthy();

    // Must NOT render Dashboard Shell components (Total Users, Clinical Audit Log)
    expect(screen.queryByText(/CLINICAL AUDIT LOG/i)).toBeNull();
    expect(screen.queryByText(/TOTAL USERS/i)).toBeNull();
  });

  it("authenticated admin portal renders the admin dashboard", async () => {
    mockContext.portal = "admin";
    mockContext.adminScreen = "dashboard";
    mockContext.adminIdentifier = "admin@citygeneral.org";
    mockContext.userRole = "admin";

    vi.spyOn(api, "getAdminConfigStatus").mockResolvedValue({ settings: [], flags: {} });
    vi.spyOn(api, "getAdminProviders").mockResolvedValue({ providers: [] });
    vi.spyOn(api, "getAdminEscalations").mockResolvedValue({ escalations: [] });
    vi.spyOn(api, "getAdminAudit").mockResolvedValue([]);
    vi.spyOn(api, "getAdminStats").mockResolvedValue({
      total_users: 10,
      total_patients: 6,
      total_providers: 3,
      total_appointments: 4,
      total_checkins: 12,
      active_escalations: 0,
    });

    render(<App />);

    // Must render Admin Dashboard
    expect(screen.getByText(/TOTAL USERS/i)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /sign in to admin portal/i })).toBeNull();
  });
});
