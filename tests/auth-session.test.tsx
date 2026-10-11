// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor, act } from "@testing-library/react";
import { translations } from "../app/translations";
import { getAuthErrorMessage } from "../app/lib/firebase";
import { notifyUnauthorized } from "../app/lib/api";

const mockFirebase = {
  signInWithEmailAndPassword: vi.fn(),
  createUserWithEmailAndPassword: vi.fn(),
  sendPasswordResetEmail: vi.fn(),
  signOut: vi.fn().mockResolvedValue(undefined),
};

vi.mock("firebase/auth", () => ({
  signInWithEmailAndPassword: (...args: any[]) => mockFirebase.signInWithEmailAndPassword(...args),
  createUserWithEmailAndPassword: (...args: any[]) => mockFirebase.createUserWithEmailAndPassword(...args),
  sendPasswordResetEmail: (...args: any[]) => mockFirebase.sendPasswordResetEmail(...args),
  signOut: (...args: any[]) => mockFirebase.signOut(...args),
  onAuthStateChanged: () => () => {},
  getAuth: () => ({ currentUser: null }),
}));

let firebaseEnabled = false;
let firebaseConfigured = false;

vi.mock("../app/lib/firebase", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../app/lib/firebase")>();
  return {
    ...actual,
    isFirebaseEnabled: () => firebaseEnabled,
    isFirebaseConfigured: () => firebaseConfigured,
    getFirebaseAuth: () => ({ currentUser: null }),
  };
});

vi.mock("../app/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../app/lib/api")>();
  return {
    ...actual,
    api: {
      authSession: vi.fn().mockResolvedValue({ role: "patient", user_id: "p1", email: "p@care.org", status: "active" }),
      getProfile: vi.fn().mockResolvedValue({ consent_granted_at: "2026-01-01" }),
      getEHRConnection: vi.fn().mockResolvedValue({ mode: "isolated" }),
    },
  };
});

import { AppProvider, useApp } from "../app/context/AppContext";
import { LoginScreen } from "../app/components/LoginScreen";
import { ProviderLoginScreen } from "../app/components/provider/ProviderLoginScreen";
import { AdminLoginScreen } from "../app/components/admin/AdminLoginScreen";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  firebaseEnabled = false;
  firebaseConfigured = false;
});

describe("Phase 1a: Logout cleanup and history protection in AppContext", () => {
  it("clears user role, identifiers, clinical profile, check-in, appointments and replaces history state", async () => {
    const replaceStateSpy = vi.spyOn(window.history, "replaceState");

    let contextValues: any = null;
    const TestConsumer = () => {
      contextValues = useApp();
      return (
        <div>
          <button id="test-logout-btn" onClick={() => contextValues.signOutUser()}>
            Logout
          </button>
          <button
            id="test-populate-btn"
            onClick={() => {
              contextValues.setUserRole("patient");
              contextValues.setUserIdentifier("ali.khan@demo.care");
              contextValues.setProviderIdentifier("dr.sana@citygeneral.org");
              contextValues.setAdminIdentifier("admin@citygeneral.org");
              contextValues.setSelectedPatient("Patient Alpha");
              contextValues.setCheckIn({ note: "Patient feels tired", thirst: true, urination: null, missedMeds: "no", lowConfidence: false, submittedAt: "now" });
              contextValues.setAppointment({ isBooked: true, slot: "10:00", reason: "Follow-up", provider: "Dr. Sana", status: "Confirmed", bookedAt: "now" });
              contextValues.resolveCase("Patient Alpha");
              contextValues.setShowSettings(true);
              contextValues.setShowTour(true);
            }}
          >
            Populate
          </button>
        </div>
      );
    };

    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );

    act(() => {
      document.getElementById("test-populate-btn")!.click();
    });

    expect(contextValues.userRole).toBe("patient");
    expect(contextValues.userIdentifier).toBe("ali.khan@demo.care");
    expect(contextValues.selectedPatient).toBe("Patient Alpha");
    expect(contextValues.showSettings).toBe(true);
    expect(contextValues.showTour).toBe(true);

    await act(async () => {
      await contextValues.signOutUser();
    });

    expect(contextValues.userRole).toBeNull();
    expect(contextValues.userIdentifier).toBe("");
    expect(contextValues.providerIdentifier).toBe("");
    expect(contextValues.adminIdentifier).toBe("");
    expect(contextValues.selectedPatient).toBeNull();
    expect(contextValues.liveProfile).toBeNull();
    expect(contextValues.liveEhrConnection).toBeNull();
    expect(contextValues.activeLiveCheckin).toBeNull();
    expect(contextValues.liveCheckinResult).toBeNull();
    expect(contextValues.escalationRecorded).toBeNull();
    expect(contextValues.checkIn.note).toBe("");
    expect(contextValues.appointment.isBooked).toBe(false);
    expect(contextValues.resolvedCases).toEqual([]);
    expect(contextValues.acknowledgedPatients).toEqual([]);
    expect(contextValues.showSettings).toBe(false);
    expect(contextValues.showTour).toBe(false);

    expect(replaceStateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ screen: "login" }),
      ""
    );
  });

  it("prevents Back button access to logged-in screens when unauthenticated", async () => {
    let contextValues: any = null;
    const TestConsumer = () => {
      contextValues = useApp();
      return <div id="screen-display">{contextValues.screen}</div>;
    };

    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );

    // Ensure logged out
    await act(async () => {
      await contextValues.signOutUser();
    });

    // Simulate user pressing browser Back to navigate to a protected screen
    act(() => {
      window.dispatchEvent(
        new PopStateEvent("popstate", {
          state: { portal: "patient", screen: "home", providerScreen: "dashboard", adminScreen: "dashboard" },
        })
      );
    });

    expect(contextValues.screen).toBe("login");
  });
});

describe("Phase 1b: 401 session expiration handling", () => {
  it("clears session, sets expiration message in EN, and routes to login screen", async () => {
    let contextValues: any = null;
    const TestConsumer = () => {
      contextValues = useApp();
      return (
        <div>
          <div id="screen">{contextValues.screen}</div>
          {contextValues.screen === "login" && <LoginScreen />}
        </div>
      );
    };

    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );

    act(() => {
      contextValues.setUserRole("patient");
      contextValues.setScreen("home");
    });

    expect(contextValues.screen).toBe("home");

    // Simulate API 401 unauthorized trigger
    await act(async () => {
      notifyUnauthorized();
    });

    expect(contextValues.userRole).toBeNull();
    expect(contextValues.screen).toBe("login");
    expect(contextValues.sessionNotice).toBe(translations.en.sessionExpired);
    expect(document.getElementById("session-notice-banner")?.textContent).toContain(translations.en.sessionExpired);
  });

  it("sets expiration message in Urdu when language is ur", async () => {
    let contextValues: any = null;
    const TestConsumer = () => {
      contextValues = useApp();
      return <div>{contextValues.sessionNotice}</div>;
    };

    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>
    );

    act(() => {
      contextValues.setLanguage("ur");
      contextValues.setUserRole("patient");
    });

    await act(async () => {
      notifyUnauthorized();
    });

    expect(contextValues.sessionNotice).toBe(translations.ur.sessionExpired);
  });
});

describe("Phase 1c: Non-revealing auth error messages (Q4 coverage)", () => {
  it("maps wrong-password and user-not-found to identical generic message in EN and UR", () => {
    for (const lang of ["en", "ur"] as const) {
      const t = translations[lang];
      const wrongPassMsg = getAuthErrorMessage("auth/wrong-password", t);
      const notFoundMsg = getAuthErrorMessage("auth/user-not-found", t);
      const invalidCredMsg = getAuthErrorMessage("auth/invalid-credential", t);

      expect(wrongPassMsg).toBe(notFoundMsg);
      expect(wrongPassMsg).toBe(invalidCredMsg);
      expect(wrongPassMsg).toBe(t.authInvalidCredentials);
    }
  });

  it("maps all remaining Q4 error codes to localized plain text", () => {
    for (const lang of ["en", "ur"] as const) {
      const t = translations[lang];
      expect(getAuthErrorMessage("auth/email-already-in-use", t)).toBe(t.authEmailAlreadyInUse);
      expect(getAuthErrorMessage("auth/weak-password", t)).toBe(t.authWeakPassword);
      expect(getAuthErrorMessage("auth/too-many-requests", t)).toBe(t.authTooManyRequests);
      expect(getAuthErrorMessage("auth/network-request-failed", t)).toBe(t.authNetworkError);
      expect(getAuthErrorMessage("auth/invalid-email", t)).toBe(t.authInvalidEmail);
      expect(getAuthErrorMessage("auth/invalid-api-key", t)).toBe(t.authInvalidApiKey);
      expect(getAuthErrorMessage("auth/unknown-error-code", t)).toBe(t.authGeneralError);
    }
  });
});

describe("Phase 1d: Autocomplete, spellcheck, autocapitalize and inputmode attributes", () => {
  it("provides correct accessibility and autocomplete attributes on LoginScreen", () => {
    render(
      <AppProvider>
        <LoginScreen />
      </AppProvider>
    );

    const emailInput = document.getElementById("login-identifier") as HTMLInputElement;
    expect(emailInput.getAttribute("autocomplete")).toBe("username");
    expect(emailInput.getAttribute("autocapitalize")).toBe("none");
    expect(emailInput.getAttribute("spellcheck")).toBe("false");
    expect(emailInput.getAttribute("inputmode")).toBe("email");

    const passwordInput = document.getElementById("login-password") as HTMLInputElement;
    expect(passwordInput.getAttribute("autocomplete")).toBe("current-password");

    // Toggle to Sign Up
    fireEvent.click(document.getElementById("toggle-auth-mode-btn")!);
    expect(passwordInput.getAttribute("autocomplete")).toBe("new-password");

    const confirmInput = document.getElementById("login-confirm-password") as HTMLInputElement;
    expect(confirmInput.getAttribute("autocomplete")).toBe("new-password");
  });

  it("provides correct attributes on ProviderLoginScreen and AdminLoginScreen", () => {
    const { unmount } = render(
      <AppProvider>
        <ProviderLoginScreen />
      </AppProvider>
    );

    const pEmail = document.getElementById("provider-identifier") as HTMLInputElement;
    expect(pEmail.getAttribute("autocomplete")).toBe("username");
    expect(pEmail.getAttribute("autocapitalize")).toBe("none");
    expect(pEmail.getAttribute("inputmode")).toBe("email");
    expect(pEmail.getAttribute("spellcheck")).toBe("false");

    const pPass = document.getElementById("provider-password") as HTMLInputElement;
    expect(pPass.getAttribute("autocomplete")).toBe("current-password");

    unmount();

    render(
      <AppProvider>
        <AdminLoginScreen />
      </AppProvider>
    );

    const aEmail = document.getElementById("admin-identifier") as HTMLInputElement;
    expect(aEmail.getAttribute("autocomplete")).toBe("username");
    expect(aEmail.getAttribute("autocapitalize")).toBe("none");
    expect(aEmail.getAttribute("inputmode")).toBe("email");
    expect(aEmail.getAttribute("spellcheck")).toBe("false");

    const aPass = document.getElementById("admin-password") as HTMLInputElement;
    expect(aPass.getAttribute("autocomplete")).toBe("current-password");
  });
});

describe("Phase 1e: Forgot password flow", () => {
  beforeEach(() => {
    firebaseEnabled = true;
    firebaseConfigured = true;
  });

  it("shows the neutral message when email exists and sendPasswordResetEmail succeeds", async () => {
    mockFirebase.sendPasswordResetEmail.mockResolvedValueOnce(undefined);

    render(
      <AppProvider>
        <LoginScreen />
      </AppProvider>
    );

    const emailInput = document.getElementById("login-identifier") as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: "  Patient.User@Care.Org  " } });

    const forgotBtn = document.getElementById("forgot-password-btn")!;
    fireEvent.click(forgotBtn);

    await waitFor(() => {
      expect(mockFirebase.sendPasswordResetEmail).toHaveBeenCalledWith(
        expect.anything(),
        "patient.user@care.org"
      );
    });

    expect(screen.getByText(translations.en.resetPasswordSent)).toBeTruthy();
  });

  it("shows the identical neutral message when Firebase throws user-not-found (no enumeration)", async () => {
    mockFirebase.sendPasswordResetEmail.mockRejectedValueOnce({ code: "auth/user-not-found" });

    render(
      <AppProvider>
        <LoginScreen />
      </AppProvider>
    );

    const emailInput = document.getElementById("login-identifier") as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: "nonexistent@care.org" } });

    const forgotBtn = document.getElementById("forgot-password-btn")!;
    fireEvent.click(forgotBtn);

    await waitFor(() => {
      expect(mockFirebase.sendPasswordResetEmail).toHaveBeenCalledWith(
        expect.anything(),
        "nonexistent@care.org"
      );
    });

    expect(screen.getByText(translations.en.resetPasswordSent)).toBeTruthy();
  });
});

describe("Phase 1f: Email trimming, lower-casing and submit button state", () => {
  beforeEach(() => {
    firebaseEnabled = true;
    firebaseConfigured = true;
  });

  it("trims and lower-cases email when signing in", async () => {
    mockFirebase.signInWithEmailAndPassword.mockResolvedValueOnce({
      user: { email: "patient.clean@care.org" },
    });

    render(
      <AppProvider>
        <LoginScreen />
      </AppProvider>
    );

    fireEvent.change(document.getElementById("login-identifier")!, {
      target: { value: "  Patient.Clean@Care.Org  " },
    });
    fireEvent.change(document.getElementById("login-password")!, {
      target: { value: "secret12345" },
    });

    const submitBtn = document.getElementById("login-submit-btn")!;
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockFirebase.signInWithEmailAndPassword).toHaveBeenCalledWith(
        expect.anything(),
        "patient.clean@care.org",
        "secret12345"
      );
    });
  });

  it("submits the form on Enter press", async () => {
    mockFirebase.signInWithEmailAndPassword.mockResolvedValueOnce({
      user: { email: "enter.test@care.org" },
    });

    render(
      <AppProvider>
        <LoginScreen />
      </AppProvider>
    );

    const emailInput = document.getElementById("login-identifier")!;
    fireEvent.change(emailInput, { target: { value: "enter.test@care.org" } });
    fireEvent.change(document.getElementById("login-password")!, { target: { value: "password123" } });

    fireEvent.submit(emailInput.closest("form")!);

    await waitFor(() => {
      expect(mockFirebase.signInWithEmailAndPassword).toHaveBeenCalledWith(
        expect.anything(),
        "enter.test@care.org",
        "password123"
      );
    });
  });
});
