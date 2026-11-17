// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";

// Mock firebase/auth
const { mockSignInWithPopup, mockSignInWithRedirect, mockSignOut, MockGoogleAuthProvider } = vi.hoisted(() => {
  return {
    mockSignInWithPopup: vi.fn(),
    mockSignInWithRedirect: vi.fn(),
    mockSignOut: vi.fn(),
    MockGoogleAuthProvider: class {},
  };
});

vi.mock("firebase/auth", () => ({
  GoogleAuthProvider: MockGoogleAuthProvider,
  signInWithPopup: (...args: any[]) => mockSignInWithPopup(...args),
  signInWithRedirect: (...args: any[]) => mockSignInWithRedirect(...args),
  signOut: (...args: any[]) => mockSignOut(...args),
  signInWithEmailAndPassword: vi.fn(),
  createUserWithEmailAndPassword: vi.fn(),
  sendPasswordResetEmail: vi.fn(),
}));

// Mock AppContext
const mockContext: any = {
  setScreen: vi.fn(),
  setUserIdentifier: vi.fn(),
  setUserRole: vi.fn(),
  setLiveProfile: vi.fn(),
  setProfile: vi.fn(),
  sessionNotice: null,
  setSessionNotice: vi.fn(),
  t: {
    authSigningIn: "Signing in...",
    signInBtn: "Sign In",
    signUpBtn: "Sign Up",
    authEmptyFields: "Please fill in all fields",
    authGeneralError: "An authentication error occurred",
    authRoleMismatch: "Access denied. Role mismatch.",
    authModeFirebase: "Firebase Auth Mode",
    authModeMock: "Mock Mode",
    providerLoginTitle: "Clinical Provider Portal",
    providerLoginSubtitle: "Secure clinical access",
    adminLoginTitle: "System Administration",
    adminLoginSubtitle: "Platform configuration",
  },
  isUrdu: false,
  language: "en",
  isLiveMode: true,
  setProviderScreen: vi.fn(),
  setPortal: vi.fn(),
  setProviderIdentifier: vi.fn(),
  setProviderDisplayName: vi.fn(),
  setAdminScreen: vi.fn(),
  setAdminIdentifier: vi.fn(),
};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockContext,
}));

// Mock api
const mockAuthSession = vi.fn();
const mockReportAccessDenied = vi.fn();
const mockGetProfile = vi.fn();

vi.mock("../app/lib/api", () => ({
  api: {
    authSession: () => mockAuthSession(),
    reportAccessDenied: (...args: any[]) => mockReportAccessDenied(...args),
    getProfile: () => mockGetProfile(),
  },
  ApiError: class ApiError extends Error {
    getFriendlyMessage() {
      return this.message;
    }
  },
}));

import { isFirebaseEnabled, signInWithGoogle } from "../app/lib/firebase";
import { LoginScreen } from "../app/components/LoginScreen";
import { PatientLoginScreen } from "../app/components/PatientLoginScreen";
import { PatientSignupScreen } from "../app/components/PatientSignupScreen";
import { ProviderLoginScreen } from "../app/components/provider/ProviderLoginScreen";
import { AdminLoginScreen } from "../app/components/admin/AdminLoginScreen";

describe("Item 7: Google Sign-in with Firebase", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    process.env.NEXT_PUBLIC_AUTH_MODE = "firebase";
    process.env.NEXT_PUBLIC_FIREBASE_API_KEY = "test-api-key";
    process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID = "test-project-id";

    // Setup global auth instance
    (window as any).__CHRONICARE_FIREBASE_AUTH__ = { currentUser: { getIdToken: vi.fn().mockResolvedValue("fake-token") } };
  });

  afterEach(() => {
    cleanup();
  });

  describe("signInWithGoogle helper unit tests", () => {
    it("success: returns userCredential when popup completes", async () => {
      const fakeCred = { user: { email: "patient@example.com", displayName: "Test Patient" } };
      mockSignInWithPopup.mockResolvedValueOnce(fakeCred);

      const res = await signInWithGoogle();
      expect(res.userCredential).toEqual(fakeCred);
      expect(res.cancelled).toBeUndefined();
      expect(res.error).toBeUndefined();
    });

    it("popup closed: returns cancelled: true silently when user dismisses popup", async () => {
      mockSignInWithPopup.mockRejectedValueOnce({ code: "auth/popup-closed-by-user" });

      const res = await signInWithGoogle();
      expect(res.cancelled).toBe(true);
      expect(res.error).toBeUndefined();
      expect(res.userCredential).toBeUndefined();
    });

    it("operation not allowed: returns friendly console notice", async () => {
      mockSignInWithPopup.mockRejectedValueOnce({ code: "auth/operation-not-allowed" });

      const res = await signInWithGoogle();
      expect(res.error).toBe("Google sign-in is not enabled in Firebase Console");
    });

    it("account exists with different credential: returns friendly notice", async () => {
      mockSignInWithPopup.mockRejectedValueOnce({ code: "auth/account-exists-with-different-credential" });

      const res = await signInWithGoogle();
      expect(res.error).toBe("An account already exists with this email using a different sign-in method");
    });

    it("unauthorized domain: returns friendly domain notice", async () => {
      mockSignInWithPopup.mockRejectedValueOnce({ code: "auth/unauthorized-domain" });

      const res = await signInWithGoogle();
      expect(res.error).toBe("This domain is not authorized in Firebase Console");
    });

    it("popup blocked fallback: calls signInWithRedirect", async () => {
      mockSignInWithPopup.mockRejectedValueOnce({ code: "auth/popup-blocked" });
      mockSignInWithRedirect.mockResolvedValueOnce(undefined);

      const res = await signInWithGoogle();
      expect(mockSignInWithRedirect).toHaveBeenCalled();
      expect(res.cancelled).toBe(true);
    });
  });

  describe("UI & Role Guard Integration", () => {
    it("renders 'Continue with Google' button when Firebase is active on Patient Login & Signup", () => {
      const { unmount } = render(<PatientLoginScreen />);
      expect(screen.getByTestId("google-signin-btn")).toBeDefined();
      expect(screen.getByText("Continue with Google")).toBeDefined();
      unmount();

      render(<PatientSignupScreen />);
      expect(screen.getByTestId("google-signin-btn")).toBeDefined();
    });

    it("renders 'Continue with Google' button on Provider and Admin Login screens", () => {
      const { unmount } = render(<ProviderLoginScreen />);
      expect(screen.getByTestId("google-signin-btn")).toBeDefined();
      unmount();

      render(<AdminLoginScreen />);
      expect(screen.getByTestId("google-signin-btn")).toBeDefined();
    });

    it("does NOT render 'Continue with Google' in mock mode", () => {
      process.env.NEXT_PUBLIC_AUTH_MODE = "mock";
      render(<PatientLoginScreen />);
      expect(screen.queryByTestId("google-signin-btn")).toBeNull();
    });

    it("Provider screen: refuses Google sign-in if account role is patient, and records audit row", async () => {
      mockSignInWithPopup.mockResolvedValueOnce({
        user: { email: "regular.patient@gmail.com", displayName: "Regular Patient" },
      });
      mockAuthSession.mockResolvedValueOnce({ role: "patient", user_id: "usr-p1" });

      render(<ProviderLoginScreen />);
      const btn = screen.getByTestId("google-signin-btn");
      fireEvent.click(btn);

      await waitFor(() => {
        expect(mockReportAccessDenied).toHaveBeenCalledWith("provider");
        expect(mockSignOut).toHaveBeenCalled();
        expect(screen.getByText("This Google account is registered as a patient, not a provider")).toBeDefined();
        expect(mockContext.setProviderScreen).not.toHaveBeenCalled();
      });
    });

    it("Admin screen: refuses Google sign-in if account role is patient, and records audit row", async () => {
      mockSignInWithPopup.mockResolvedValueOnce({
        user: { email: "regular.patient@gmail.com", displayName: "Regular Patient" },
      });
      mockAuthSession.mockResolvedValueOnce({ role: "patient", user_id: "usr-p1" });

      render(<AdminLoginScreen />);
      const btn = screen.getByTestId("google-signin-btn");
      fireEvent.click(btn);

      await waitFor(() => {
        expect(mockReportAccessDenied).toHaveBeenCalledWith("admin");
        expect(mockSignOut).toHaveBeenCalled();
        expect(screen.getByText("This Google account is registered as a patient, not an admin")).toBeDefined();
        expect(mockContext.setAdminScreen).not.toHaveBeenCalled();
      });
    });

    it("Provider screen: allows Google sign-in if account role is provider", async () => {
      mockSignInWithPopup.mockResolvedValueOnce({
        user: { email: "dr.usman@hospital.org", displayName: "Dr. Usman" },
      });
      mockAuthSession.mockResolvedValueOnce({ role: "provider", user_id: "usr-dr1", display_name: "Dr. Usman" });

      render(<ProviderLoginScreen />);
      const btn = screen.getByTestId("google-signin-btn");
      fireEvent.click(btn);

      await waitFor(() => {
        expect(mockContext.setProviderIdentifier).toHaveBeenCalledWith("dr.usman@hospital.org");
        expect(mockContext.setProviderScreen).toHaveBeenCalledWith("dashboard");
      });
    });
  });
});
