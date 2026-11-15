// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AdminLoginScreen } from "../app/components/admin/AdminLoginScreen";
import { AppProvider } from "../app/context/AppContext";
import { api } from "../app/lib/api";
import * as firebaseAuth from "firebase/auth";

vi.mock("firebase/auth", async () => {
  const actual: any = await vi.importActual("firebase/auth");
  return {
    ...actual,
    signInWithEmailAndPassword: vi.fn(),
    signOut: vi.fn(),
    getAuth: vi.fn(() => ({})),
    onAuthStateChanged: () => () => {},
  };
});

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => true,
  isFirebaseConfigured: () => true,
  getFirebaseAuth: () => ({}),
  getAuthErrorMessage: (_code: string, t: any) => t.authInvalidCredentials,
}));

vi.mock("../app/lib/api", async () => {
  const actual: any = await vi.importActual("../app/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      authSession: vi.fn(),
      reportAccessDenied: vi.fn(),
    },
  };
});

describe("P3-25 Admin portal refusal writes ACCESS_DENIED audit row", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls reportAccessDenied when provider attempts to log in to admin portal", async () => {
    vi.mocked(firebaseAuth.signInWithEmailAndPassword).mockResolvedValue({
      user: { email: "provider.demo@demo.care" },
    } as any);

    // Backend returns role 'provider' instead of 'admin'
    vi.mocked(api.authSession).mockResolvedValue({
      user_id: "prov-123",
      email: "provider.demo@demo.care",
      role: "provider",
      status: "active",
      display_name: "Dr. Provider",
    });

    vi.mocked(api.reportAccessDenied).mockResolvedValue(undefined);

    render(
      <AppProvider>
        <AdminLoginScreen />
      </AppProvider>
    );

    const emailInput = screen.getByLabelText(/Administrator Email/i);
    const passInput = screen.getByLabelText(/^Password$/i);
    const submitBtn = screen.getByRole("button", { name: /Sign In/i });

    fireEvent.change(emailInput, { target: { value: "provider.demo@demo.care" } });
    fireEvent.change(passInput, { target: { value: "ValidPass123!" } });
    fireEvent.click(submitBtn);

    // Verify reportAccessDenied was called with "admin"
    await waitFor(() => {
      expect(api.reportAccessDenied).toHaveBeenCalledWith("admin");
    });

    // Verify signOut was called and error message is displayed
    expect(firebaseAuth.signOut).toHaveBeenCalled();
    await waitFor(() => {
      expect(
        screen.getByText(/Access denied: this account does not have permission for this portal/i)
      ).toBeDefined();
    });
  });
});
