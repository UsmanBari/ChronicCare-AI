// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { translations } from "../app/translations";

const ctx: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => ctx,
}));

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => false,
  isFirebaseConfigured: () => false,
  getFirebaseAuth: () => null,
  getAuthErrorMessage: () => "",
}));

import { LoginScreen } from "../app/components/LoginScreen";
import { Header } from "../app/components/Header";

function setContext(lang: "en" | "ur", overrides: Record<string, any> = {}) {
  for (const k of Object.keys(ctx)) delete ctx[k];
  Object.assign(ctx, {
    language: lang,
    t: translations[lang],
    isUrdu: lang === "ur",
    setLanguage: vi.fn(),
    connectionMode: null,
    portal: "patient",
    screen: "home",
    providerScreen: "dashboard",
    adminScreen: "dashboard",
    isLiveMode: false,
    liveEhrConnection: null,
    setPortal: vi.fn(),
    setScreen: vi.fn(),
    setProviderScreen: vi.fn(),
    setAdminScreen: vi.fn(),
    setShowSettings: vi.fn(),
    setShowTour: vi.fn(),
    returnToHomeAndClearRun: vi.fn(),
    signOutUser: vi.fn().mockResolvedValue(undefined),
    setUserIdentifier: vi.fn(),
    setUserRole: vi.fn(),
    setLiveProfile: vi.fn(),
    ...overrides,
  });
}

afterEach(cleanup);

describe("LoginScreen password visibility toggles", () => {
  beforeEach(() => setContext("en"));

  it("has EN and UR strings for every toggle label", () => {
    for (const lang of ["en", "ur"] as const) {
      const t = translations[lang];
      for (const key of ["showPassword", "hidePassword", "showConfirmPassword", "hideConfirmPassword"] as const) {
        expect(t[key]).toBeTruthy();
      }
    }
    expect(translations.ur.showPassword).not.toBe(translations.en.showPassword);
  });

  it("toggles the password field between hidden and visible and updates aria-label", () => {
    render(<LoginScreen />);
    const input = document.getElementById("login-password") as HTMLInputElement;
    expect(input.type).toBe("password");

    const toggle = screen.getByRole("button", { name: "Show password" });
    expect(toggle.getAttribute("type")).toBe("button");
    expect(toggle.getAttribute("aria-controls")).toBe("login-password");

    fireEvent.click(toggle);
    expect(input.type).toBe("text");
    expect(screen.getByRole("button", { name: "Hide password" })).toBe(toggle);

    fireEvent.click(toggle);
    expect(input.type).toBe("password");
  });

  it("toggles the confirm-password field independently in sign-up mode", () => {
    render(<LoginScreen />);
    fireEvent.click(document.getElementById("toggle-auth-mode-btn")!);

    const password = document.getElementById("login-password") as HTMLInputElement;
    const confirm = document.getElementById("login-confirm-password") as HTMLInputElement;
    expect(confirm.type).toBe("password");

    fireEvent.click(screen.getByRole("button", { name: "Show confirm password" }));
    expect(confirm.type).toBe("text");
    expect(password.type).toBe("password");
    expect(screen.getByRole("button", { name: "Hide confirm password" })).toBeTruthy();
  });

  it("toggle is keyboard reachable and does not submit the form", () => {
    render(<LoginScreen />);
    const toggle = screen.getByRole("button", { name: "Show password" }) as HTMLButtonElement;
    expect(toggle.tabIndex).toBe(0);
    toggle.focus();
    expect(document.activeElement).toBe(toggle);

    // A type="button" click inside the form must not trigger submit validation.
    fireEvent.click(toggle);
    expect(screen.queryByText(translations.en.authEmptyFields)).toBeNull();
  });

  it("uses Urdu labels and mirrors the toggle to the left in RTL", () => {
    setContext("ur");
    render(<LoginScreen />);
    const toggle = screen.getByRole("button", { name: translations.ur.showPassword });
    expect(toggle.className).toMatch(/\bleft-0\b/);
    expect(toggle.className).not.toMatch(/\bright-0\b/);

    const input = document.getElementById("login-password") as HTMLInputElement;
    expect(input.className).toMatch(/\bpl-11\b/);
    expect(input.className).toMatch(/\bpr-11\b/);
  });

  it("places the toggle on the right in LTR with padding on both sides of the input", () => {
    render(<LoginScreen />);
    const toggle = screen.getByRole("button", { name: "Show password" });
    expect(toggle.className).toMatch(/\bright-0\b/);
    const input = document.getElementById("login-password") as HTMLInputElement;
    expect(input.className).toMatch(/\bpl-11\b/);
    expect(input.className).toMatch(/\bpr-11\b/);
  });
});

describe("Header log out button", () => {
  it("has EN and UR strings", () => {
    expect(translations.en.logoutBtn).toBeTruthy();
    expect(translations.ur.logoutBtn).toBeTruthy();
  });

  it("desktop button signs out and routes to the patient login screen", async () => {
    setContext("en");
    render(<Header />);
    fireEvent.click(document.getElementById("header-logout-btn")!);
    await waitFor(() => expect(ctx.setScreen).toHaveBeenCalledWith("login"));
    expect(ctx.signOutUser).toHaveBeenCalledTimes(1);
  });

  it("calls signOutUser before navigating", async () => {
    const order: string[] = [];
    setContext("en", {
      signOutUser: vi.fn(async () => {
        order.push("signOut");
      }),
      setScreen: vi.fn(() => order.push("setScreen")),
    });
    render(<Header />);
    fireEvent.click(document.getElementById("header-logout-btn")!);
    await waitFor(() => expect(order).toEqual(["signOut", "setScreen"]));
  });

  it("mobile menu shows a log out button that signs out and routes to login", async () => {
    setContext("ur");
    render(<Header />);
    fireEvent.click(document.getElementById("mobile-menu-toggle-btn")!);
    const btn = document.getElementById("mobile-nav-logout-btn")!;
    expect(btn.textContent).toContain(translations.ur.logoutBtn);
    fireEvent.click(btn);
    await waitFor(() => expect(ctx.setScreen).toHaveBeenCalledWith("login"));
    expect(ctx.signOutUser).toHaveBeenCalledTimes(1);
  });

  it("routes provider and admin portals to their own login screens", async () => {
    setContext("en", { portal: "provider" });
    render(<Header />);
    fireEvent.click(document.getElementById("header-logout-btn")!);
    await waitFor(() => expect(ctx.setProviderScreen).toHaveBeenCalledWith("login"));
    cleanup();

    setContext("en", { portal: "admin" });
    render(<Header />);
    fireEvent.click(document.getElementById("header-logout-btn")!);
    await waitFor(() => expect(ctx.setAdminScreen).toHaveBeenCalledWith("login"));
  });

  it("is hidden on the landing page and on login screens", () => {
    const hiddenCases = [
      { portal: "landing" },
      { portal: "patient", screen: "login" },
      { portal: "provider", providerScreen: "login" },
      { portal: "admin", adminScreen: "login" },
    ];
    for (const overrides of hiddenCases) {
      setContext("en", overrides);
      render(<Header />);
      expect(document.getElementById("header-logout-btn")).toBeNull();
      fireEvent.click(document.getElementById("mobile-menu-toggle-btn")!);
      expect(document.getElementById("mobile-nav-logout-btn")).toBeNull();
      cleanup();
    }
  });

  it("has an accessible name", () => {
    setContext("en");
    render(<Header />);
    expect(screen.getByRole("button", { name: translations.en.logoutBtn })).toBeTruthy();
  });
});
