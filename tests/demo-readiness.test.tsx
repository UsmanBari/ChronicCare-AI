// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, act, waitFor } from "@testing-library/react";
import { ProviderLoginScreen } from "../app/components/provider/ProviderLoginScreen";
import { AdminLoginScreen } from "../app/components/admin/AdminLoginScreen";
import { HomeScreen } from "../app/components/HomeScreen";
import { HealthProfileScreen } from "../app/components/HealthProfileScreen";
import { PortalLandingScreen } from "../app/components/PortalLandingScreen";
import { TrendScreen } from "../app/components/TrendScreen";
import { ErrorBoundary } from "../app/components/ErrorBoundary";
import NotFound from "../app/not-found";
import { translations } from "../app/translations";
import { api, subscribeServerWaking, resetServerWakingState } from "../app/lib/api";
import { AppProvider, useApp } from "../app/context/AppContext";

const mockContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", async () => {
  const actual: any = await vi.importActual("../app/context/AppContext");
  return {
    ...actual,
    useApp: () => {
      // If mockContext is populated with overrides, use it, else return actual context
      if (Object.keys(mockContext).length > 0) {
        return mockContext;
      }
      return actual.useApp();
    },
  };
});

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => false,
  isFirebaseConfigured: () => false,
  getFirebaseAuth: () => null,
  getAuthErrorMessage: () => "",
}));

// Mock recharts
vi.mock("recharts", async () => {
  const actual: any = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
  };
});

describe("STAGE 10E: Demo Readiness Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetServerWakingState();
    for (const key of Object.keys(mockContext)) {
      delete mockContext[key];
    }
  });

  afterEach(() => {
    cleanup();
  });

  // 1. Password eye toggle on ProviderLoginScreen
  it("ProviderLoginScreen: toggles password visibility with eye button and accessible label (EN & UR)", () => {
    mockContext.setProviderScreen = vi.fn();
    mockContext.setPortal = vi.fn();
    mockContext.setProviderIdentifier = vi.fn();
    mockContext.setUserRole = vi.fn();
    mockContext.sessionNotice = null;
    mockContext.setSessionNotice = vi.fn();
    mockContext.t = translations.en;
    mockContext.isUrdu = false;

    const { rerender } = render(<ProviderLoginScreen />);
    const passInput = document.getElementById("provider-password") as HTMLInputElement;
    const toggleBtn = document.getElementById("toggle-provider-password-visibility-btn") as HTMLButtonElement;

    expect(passInput.type).toBe("password");
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.en.showPassword);

    // Toggle on
    fireEvent.click(toggleBtn);
    expect(passInput.type).toBe("text");
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.en.hidePassword);

    // Toggle off
    fireEvent.click(toggleBtn);
    expect(passInput.type).toBe("password");
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.en.showPassword);

    // Test Urdu labels
    mockContext.t = translations.ur;
    mockContext.isUrdu = true;
    rerender(<ProviderLoginScreen />);
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.ur.showPassword);
    fireEvent.click(toggleBtn);
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.ur.hidePassword);
  });

  // 2. Password eye toggle on AdminLoginScreen
  it("AdminLoginScreen: toggles password visibility with eye button and accessible label (EN & UR)", () => {
    mockContext.setAdminScreen = vi.fn();
    mockContext.setPortal = vi.fn();
    mockContext.setAdminIdentifier = vi.fn();
    mockContext.setUserRole = vi.fn();
    mockContext.sessionNotice = null;
    mockContext.setSessionNotice = vi.fn();
    mockContext.t = translations.en;
    mockContext.isUrdu = false;

    const { rerender } = render(<AdminLoginScreen />);
    const passInput = document.getElementById("admin-password") as HTMLInputElement;
    const toggleBtn = document.getElementById("toggle-admin-password-visibility-btn") as HTMLButtonElement;

    expect(passInput.type).toBe("password");
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.en.showPassword);

    // Toggle on
    fireEvent.click(toggleBtn);
    expect(passInput.type).toBe("text");
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.en.hidePassword);

    // Toggle off
    fireEvent.click(toggleBtn);
    expect(passInput.type).toBe("password");
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.en.showPassword);

    // Test Urdu labels
    mockContext.t = translations.ur;
    mockContext.isUrdu = true;
    rerender(<AdminLoginScreen />);
    expect(toggleBtn.getAttribute("aria-label")).toBe(translations.ur.showPassword);
  });

  // 3. Honest EHR-connected medicines card on HomeScreen
  it("HomeScreen: shows honest 'Your medicines' title and clinician informational note with no dead button", () => {
    vi.spyOn(api, "getUserCheckins").mockResolvedValue([]);
    vi.spyOn(api, "getRecord").mockResolvedValue({
      conditions: [],
      medications: [],
      allergies: [],
      baseline_observations: [],
    });

    Object.assign(mockContext, {
      isLiveMode: true,
      isManaged: true,
      connectionMode: "fhir",
      liveEhrConnection: { mode: "fhir", connection: { display_name: "City General" } },
      liveRecord: { medications: [] },
      profile: { conditions: ["Type 2 Diabetes"] },
      liveProfile: { conditions: ["Type 2 Diabetes"] },
      activeConditions: ["Type 2 Diabetes"],
      t: translations.en,
      isUrdu: false,
      setScreen: vi.fn(),
      demoScenario: "normal",
      setDemoScenario: vi.fn(),
      blockedAction: null,
      setBlockedAction: vi.fn(),
      userIdentifier: "ali.khan@demo.care",
      appointment: { isBooked: false },
    });

    const { container } = render(<HomeScreen />);
    expect(screen.getByText("Your medicines")).toBeTruthy();
    expect(screen.getByText("Managed by your hospital record. Your clinician sees the full list.")).toBeTruthy();
    expect(screen.getByText("If this looks wrong, tell your clinician.")).toBeTruthy();
    expect(container.textContent).not.toContain("Something is different?");
    expect(container.textContent).not.toContain("Medicines from your hospital record");
  });

  // 4. HealthProfileScreen reworded hint before connection pick
  it("HealthProfileScreen: shows reworded conditional hint in English and Urdu", () => {
    Object.assign(mockContext, {
      isLiveMode: true,
      liveProfile: {
        user_id: "usr-live",
        conditions: ["Type 2 Diabetes"],
      },
      t: translations.en,
      isUrdu: false,
      setScreen: vi.fn(),
      setLanguage: vi.fn(),
      setLiveProfile: vi.fn(),
      profile: { conditions: ["Type 2 Diabetes"] },
    });

    const { rerender } = render(<HealthProfileScreen />);
    expect(
      screen.getByText("If you do not link a hospital record, you can add your medicines in the next steps.")
    ).toBeTruthy();

    mockContext.t = translations.ur;
    mockContext.isUrdu = true;
    rerender(<HealthProfileScreen />);
    expect(
      screen.getByText("اگر آپ اسپتال کا ریکارڈ منسلک نہیں کرتے تو اگلے مراحل میں اپنی ادویات شامل کر سکتے ہیں۔")
    ).toBeTruthy();
  });

  // 5. PortalLandingScreen simulated example badges
  it("PortalLandingScreen: visibly labels both diabetes and hypertension telemetry cards as 'Simulated example'", () => {
    Object.assign(mockContext, {
      setPortal: vi.fn(),
      setScreen: vi.fn(),
      t: translations.en,
      isUrdu: false,
      language: "en",
      setLanguage: vi.fn(),
      setShowTour: vi.fn(),
      setShowSettings: vi.fn(),
    });

    const { rerender } = render(<PortalLandingScreen />);
    const simBadges = screen.getAllByText("Simulated example");
    expect(simBadges.length).toBeGreaterThanOrEqual(2);

    mockContext.t = translations.ur;
    mockContext.isUrdu = true;
    rerender(<PortalLandingScreen />);
    const urSimBadges = screen.getAllByText("فرضی مثال");
    expect(urSimBadges.length).toBeGreaterThanOrEqual(2);
  });

  // 6. TrendScreen chart order and empty-data state
  describe("TrendScreen ordering and empty state", () => {
    it("renders Glucose chart first for diabetes-only, BP chart first for hypertension-only and dual", () => {
      // Diabetes only
      Object.assign(mockContext, {
        profile: { conditions: ["Type 2 Diabetes"] },
        liveProfile: null,
        isLiveMode: false,
        t: translations.en,
        isUrdu: false,
        returnToHomeAndClearRun: vi.fn(),
      });

      const { rerender } = render(<TrendScreen />);
      let headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
      expect(headings[0]).toContain(translations.en.glucoseChartTitle);

      // Hypertension only
      mockContext.profile = { conditions: ["Hypertension"] };
      rerender(<TrendScreen />);
      headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
      expect(headings[0]).toContain(translations.en.bloodPressureChartTitle);
      expect(screen.queryByText(translations.en.glucoseChartTitle)).toBeNull();

      // Dual conditions
      mockContext.profile = { conditions: ["Type 2 Diabetes", "Hypertension"] };
      rerender(<TrendScreen />);
      headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
      expect(headings[0]).toContain(translations.en.bloodPressureChartTitle);
      expect(headings[1]).toContain(translations.en.glucoseChartTitle);
    });

    it("renders empty state without crashing when live mode has fewer than 3 check-ins", async () => {
      vi.spyOn(api, "getMyTrends").mockResolvedValue({
        generated_at: new Date().toISOString(),
        advisory: true,
        window_days: 30,
        excluded_count: 0,
        trends: {
          glucose: {
            metric: "glucose",
            direction: "not_enough_history",
            n: 1,
            values: [{ at: new Date().toISOString(), value: 120 }],
            change: 0,
            slope_per_week: 0,
            window_days: 30,
          },
        },
      });

      Object.assign(mockContext, {
        profile: { conditions: ["Type 2 Diabetes"] },
        liveProfile: { conditions: ["Type 2 Diabetes"] },
        isLiveMode: true,
        t: translations.en,
        isUrdu: false,
        returnToHomeAndClearRun: vi.fn(),
      });

      render(<TrendScreen />);

      await waitFor(() => {
        expect(screen.getAllByText("Not enough history").length).toBeGreaterThan(0);
        expect(screen.getAllByText("Not enough readings yet. Trends appear after 3 check-ins.").length).toBeGreaterThan(0);
      });
    });
  });

  // 7. ErrorBoundary fallback and honest disclaimer
  it("ErrorBoundary: renders fallback UI with research prototype disclaimer and reset button", () => {
    const ProblemComponent = () => {
      throw new Error("Simulated component explosion");
    };

    // Suppress console.error in test
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <ProblemComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText("Application Interface Error")).toBeTruthy();
    expect(screen.getByText("Simulated component explosion")).toBeTruthy();
    expect(screen.getByText("Research prototype, not a medical device.")).toBeTruthy();
    expect(screen.getByText("Reset & Reload Application")).toBeTruthy();

    consoleErrorSpy.mockRestore();
  });

  // 8. NotFound component renders 404 page with research prototype disclaimer
  it("NotFound: renders 404 page with research prototype disclaimer and link to home", () => {
    render(<NotFound />);
    expect(screen.getByText("Page Not Found")).toBeTruthy();
    expect(screen.getByText("The requested page does not exist or has been moved.")).toBeTruthy();
    expect(screen.getByText("Research prototype, not a medical device.")).toBeTruthy();
    const homeBtn = document.getElementById("not-found-return-home-btn");
    expect(homeBtn).not.toBeNull();
  });

  // 9. Document lang and dir synchronization on language change
  it("AppProvider: synchronizes document.documentElement lang and dir attributes when language changes", () => {
    const LanguageSwitcher = () => {
      const { setLanguage, isUrdu } = useApp();
      return (
        <div>
          <span data-testid="current-lang">{isUrdu ? "ur" : "en"}</span>
          <button id="switch-to-ur" onClick={() => setLanguage("ur")}>
            Urdu
          </button>
          <button id="switch-to-en" onClick={() => setLanguage("en")}>
            English
          </button>
        </div>
      );
    };

    render(
      <AppProvider>
        <LanguageSwitcher />
      </AppProvider>
    );

    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");

    // Switch to Urdu
    fireEvent.click(screen.getByRole("button", { name: "Urdu" }));
    expect(document.documentElement.lang).toBe("ur");
    expect(document.documentElement.dir).toBe("rtl");

    // Switch back to English
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
  });

  // 10. Cold-start server waking banner
  it("Cold start: displays calm server waking banner with accessible role and clears on response", async () => {
    vi.useFakeTimers();

    let reqPromise: Promise<any> | null = null;
    let resolveFetch: any;
    const originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn().mockImplementation(() => {
      return new Promise((resolve) => {
        resolveFetch = resolve;
      });
    });

    const TestHarness = () => {
      const { serverWaking } = useApp();
      return (
        <div>
          <span data-testid="waking-state">{serverWaking ? "waking" : "idle"}</span>
          <button
            id="trigger-call-btn"
            onClick={() => {
              reqPromise = api.getMe().catch(() => {});
            }}
          >
            Make Request
          </button>
        </div>
      );
    };

    render(
      <AppProvider>
        <TestHarness />
      </AppProvider>
    );

    // Initial state: banner absent
    expect(document.getElementById("server-waking-banner")).toBeNull();

    // Trigger request
    fireEvent.click(screen.getByRole("button", { name: "Make Request" }));

    // Flush promise microtasks so async request() proceeds to schedule slowTimer
    await act(async () => {
      await Promise.resolve();
    });

    // Advance 2s: request in-flight, but under 4s threshold -> banner still not shown
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(document.getElementById("server-waking-banner")).toBeNull();

    // Advance past 4s threshold (e.g. +2500ms -> total 4500ms) -> banner appears!
    act(() => {
      vi.advanceTimersByTime(2500);
    });
    const banner = document.getElementById("server-waking-banner");
    expect(banner).not.toBeNull();
    expect(banner?.getAttribute("role")).toBe("status");
    expect(banner?.textContent).toContain("Waking up the server, this can take up to a minute on the free test plan");

    // Complete the fetch response and wait for request finally block to run
    await act(async () => {
      resolveFetch(
        new Response(JSON.stringify({ status: "healthy" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );
      if (reqPromise) await reqPromise;
      await Promise.resolve();
    });

    // Banner clears
    expect(document.getElementById("server-waking-banner")).toBeNull();

    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });
});
