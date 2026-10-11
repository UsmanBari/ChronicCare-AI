// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConflictScreen } from "../app/components/ConflictScreen";
import { Header } from "../app/components/Header";
import { RiskResultScreen } from "../app/components/RiskResultScreen";
import { ReconciliationAlertDetail } from "../app/components/provider/ReconciliationAlertDetail";
import { ReviewQueueScreen } from "../app/components/provider/ReviewQueueScreen";
import { ProviderDashboardScreen } from "../app/components/provider/ProviderDashboardScreen";
import { translations } from "../app/translations";
import { api } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

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
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  };
});

describe("STAGE 10D: No Fake Values & Honest State Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Live ConflictScreen with NO observation comparisons
  it("renders live ConflictScreen with NO observation comparisons without 180 or 140 mg/dL, with neutral title and no readings grid", () => {
    const liveResultNoObs = {
      requires_review: true,
      max_severity: "moderate",
      reconciliation: {
        observation_comparisons: [],
        medication_comparisons: [
          {
            medication_name: "Metformin 500mg",
            status_a: "active",
            status_b: "stopped",
            dosage_a: "1 tablet twice daily",
            dosage_b: "1 tablet twice daily",
            comparison_status: "conflict",
          },
        ],
      },
      verification: {
        observation_verifications: [],
        medication_verifications: [
          {
            medication_name: "Metformin 500mg",
            severity: "high",
            reconciliation_status: "conflict",
            review_reason: "Stopped active medicine",
          },
        ],
      },
    };

    Object.assign(mockAppContext, {
      setScreen: vi.fn(),
      checkIn: { lowConfidence: false },
      liveCheckinResult: liveResultNoObs,
      liveEhrConnection: { mode: "isolated" },
      isLiveMode: true,
      t: translations.en,
      isUrdu: false,
    });

    const { container } = render(<ConflictScreen />);
    const text = container.textContent || "";

    // DOM never contains fabricated values
    expect(text.includes("180")).toBe(false);
    expect(text.includes("140")).toBe(false);

    // Neutral title is used in heading
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(translations.en.needsClinicianReviewTitle);
    expect(screen.queryByText(translations.en.readingDiffersTitle)).toBeNull();

    // Honest explanation card is shown
    expect(screen.getByText(translations.en.clinicianReviewAnswers)).toBeTruthy();

    // Severity chip reflects actual data
    expect(screen.getByText("Severity: MODERATE")).toBeTruthy();
  });

  // 2. Live ConflictScreen with real comparisons
  it("renders live ConflictScreen with real glucose comparison (130 vs 150) and 'differs' title", () => {
    const liveResultWithRealObs = {
      requires_review: true,
      max_severity: "high",
      reconciliation: {
        observation_comparisons: [
          {
            observation_type: "glucose",
            value_a: 130,
            value_b: 150,
            unit_a: "mg/dL",
            unit_b: "mg/dL",
            status: "conflict",
            source_a: "local",
            source_b: "local",
          },
        ],
        medication_comparisons: [],
      },
      verification: {
        observation_verifications: [
          {
            observation_type: "glucose",
            severity: "high",
          },
        ],
        medication_verifications: [],
      },
    };

    Object.assign(mockAppContext, {
      setScreen: vi.fn(),
      checkIn: { lowConfidence: false },
      liveCheckinResult: liveResultWithRealObs,
      liveEhrConnection: { mode: "isolated" },
      isLiveMode: true,
      t: translations.en,
      isUrdu: false,
    });

    const { container } = render(<ConflictScreen />);
    const text = container.textContent || "";

    // Exactly real numbers appear
    expect(text.includes("130 mg/dL")).toBe(true);
    expect(text.includes("150 mg/dL")).toBe(true);

    // Title is 'Your reading differs from the record'
    expect(screen.getByText(translations.en.readingDiffersTitle)).toBeTruthy();
  });

  // 3. Three label cases in English and Urdu
  describe("Three observation label cases in EN and UR", () => {
    it("handles case 1: Not on file (first check-in) in EN and UR", () => {
      const liveResultNotOnFile = {
        requires_review: true,
        max_severity: "moderate",
        reconciliation: {
          observation_comparisons: [
            {
              observation_type: "glucose",
              value_a: null,
              value_b: 135,
              unit_b: "mg/dL",
              status: "missing_in_a",
              source_a: null,
              source_b: "local",
            },
          ],
        },
      };

      // English
      Object.assign(mockAppContext, {
        setScreen: vi.fn(),
        checkIn: { lowConfidence: false },
        liveCheckinResult: liveResultNotOnFile,
        liveEhrConnection: { mode: "isolated" },
        isLiveMode: true,
        t: translations.en,
        isUrdu: false,
      });

      const { container: enContainer, unmount: unmountEn } = render(<ConflictScreen />);
      expect(enContainer.textContent?.includes(translations.en.firstCheckinNoRecordTitle)).toBe(true);
      expect(enContainer.textContent?.includes(translations.en.firstCheckinNoRecordDesc)).toBe(true);
      expect(enContainer.textContent?.includes(translations.en.notOnFile)).toBe(true);
      unmountEn();

      // Urdu
      Object.assign(mockAppContext, {
        setScreen: vi.fn(),
        checkIn: { lowConfidence: false },
        liveCheckinResult: liveResultNotOnFile,
        liveEhrConnection: { mode: "isolated" },
        isLiveMode: true,
        t: translations.ur,
        isUrdu: true,
      });

      const { container: urContainer } = render(<ConflictScreen />);
      expect(urContainer.textContent?.includes(translations.ur.firstCheckinNoRecordTitle)).toBe(true);
      expect(urContainer.textContent?.includes(translations.ur.firstCheckinNoRecordDesc)).toBe(true);
      expect(urContainer.textContent?.includes(translations.ur.notOnFile)).toBe(true);
    });

    it("handles case 2: Earlier check-in label with timestamp in EN and UR", () => {
      const liveResultEarlierCheckin = {
        requires_review: true,
        max_severity: "moderate",
        reconciliation: {
          observation_comparisons: [
            {
              observation_type: "glucose",
              value_a: 142,
              value_b: 158,
              unit_a: "mg/dL",
              unit_b: "mg/dL",
              status: "conflict",
              source_a: "checkin",
              source_record_id_a: "CHECKIN-prior-uuid",
              timestamp_a: "2026-10-10T08:30:00Z",
            },
          ],
        },
      };

      // English
      Object.assign(mockAppContext, {
        setScreen: vi.fn(),
        checkIn: { lowConfidence: false },
        liveCheckinResult: liveResultEarlierCheckin,
        liveEhrConnection: { mode: "isolated" },
        isLiveMode: true,
        t: translations.en,
        isUrdu: false,
      });

      const { container: enContainer, unmount: unmountEn } = render(<ConflictScreen />);
      expect(enContainer.textContent?.includes(translations.en.earlierCheckinLabel)).toBe(true);
      unmountEn();

      // Urdu
      Object.assign(mockAppContext, {
        setScreen: vi.fn(),
        checkIn: { lowConfidence: false },
        liveCheckinResult: liveResultEarlierCheckin,
        liveEhrConnection: { mode: "isolated" },
        isLiveMode: true,
        t: translations.ur,
        isUrdu: true,
      });

      const { container: urContainer } = render(<ConflictScreen />);
      expect(urContainer.textContent?.includes(translations.ur.earlierCheckinLabel)).toBe(true);
    });

    it("handles case 3: Saved baseline reading label in EN and UR", () => {
      const liveResultBaseline = {
        requires_review: true,
        max_severity: "moderate",
        reconciliation: {
          observation_comparisons: [
            {
              observation_type: "glucose",
              value_a: 120,
              value_b: 165,
              unit_a: "mg/dL",
              unit_b: "mg/dL",
              status: "conflict",
              source_a: "local",
              source_record_id_a: "local-obs-1234",
              timestamp_a: "2026-10-08T12:00:00Z",
            },
          ],
        },
      };

      // English
      Object.assign(mockAppContext, {
        setScreen: vi.fn(),
        checkIn: { lowConfidence: false },
        liveCheckinResult: liveResultBaseline,
        liveEhrConnection: { mode: "isolated" },
        isLiveMode: true,
        t: translations.en,
        isUrdu: false,
      });

      const { container: enContainer, unmount: unmountEn } = render(<ConflictScreen />);
      expect(enContainer.textContent?.includes(translations.en.savedReadingLabel)).toBe(true);
      unmountEn();

      // Urdu
      Object.assign(mockAppContext, {
        setScreen: vi.fn(),
        checkIn: { lowConfidence: false },
        liveCheckinResult: liveResultBaseline,
        liveEhrConnection: { mode: "isolated" },
        isLiveMode: true,
        t: translations.ur,
        isUrdu: true,
      });

      const { container: urContainer } = render(<ConflictScreen />);
      expect(urContainer.textContent?.includes(translations.ur.savedReadingLabel)).toBe(true);
    });
  });

  // 4. Medicine deduplication
  it("deduplicates medicine display so each medicine name appears once without repeated words", () => {
    const liveResultDuplicateMeds = {
      requires_review: true,
      max_severity: "low",
      reconciliation: {
        observation_comparisons: [],
        medication_comparisons: [
          {
            medication_name: "Metformin 500mg",
            dosage_a: "1 tablet twice daily",
            status_a: "active",
            dosage_b: "1 tablet twice daily",
            status_b: "active",
            comparison_status: "agree",
          },
          {
            medication_name: "metformin 500mg",
            dosage_a: "1 tablet twice daily",
            status_a: "active",
            dosage_b: "1 tablet twice daily",
            status_b: "active",
            comparison_status: "agree",
          },
        ],
      },
      verification: {
        medication_verifications: [
          {
            medication_name: "Metformin 500mg",
            reconciliation_status: "agree",
            severity: "none",
          },
          {
            medication_name: "metformin 500mg",
            reconciliation_status: "agree",
            severity: "none",
          },
        ],
      },
    };

    Object.assign(mockAppContext, {
      setScreen: vi.fn(),
      checkIn: { lowConfidence: false },
      liveCheckinResult: liveResultDuplicateMeds,
      liveEhrConnection: { mode: "isolated" },
      isLiveMode: true,
      t: translations.en,
      isUrdu: false,
    });

    const { container } = render(<ConflictScreen />);
    const text = container.textContent || "";

    // Exactly one instance of confirmed medicine card
    const matches = text.match(/Metformin 500mg/gi);
    expect(matches).not.toBeNull();
    // In the item title, rendered exactly once (not "Metformin 500mg, Metformin 500mg")
    expect(text.includes("Metformin 500mg, Metformin 500mg")).toBe(false);
    expect(text.includes("Metformin, Metformin")).toBe(false);
    expect(matches?.length).toBe(1);
  });

  // 5. Single-flight complete API test
  it("coalesces concurrent calls to api.completeCheckin into a single flight", async () => {
    const originalFetch = global.fetch;
    let fetchCount = 0;

    global.fetch = vi.fn().mockImplementation(async () => {
      fetchCount++;
      await new Promise((r) => setTimeout(r, 20));
      return {
        ok: true,
        status: 200,
        json: async () => ({
          emergency: false,
          requires_review: false,
          max_severity: "none",
        }),
      } as any;
    });

    try {
      const flight1 = api.completeCheckin("checkin-flight-coalesce-1");
      const flight2 = api.completeCheckin("checkin-flight-coalesce-1");

      const [res1, res2] = await Promise.all([flight1, flight2]);
      expect(res1.emergency).toBe(false);
      expect(res2.emergency).toBe(false);
      expect(fetchCount).toBe(1);
    } finally {
      global.fetch = originalFetch;
    }
  });

  // 6. Guard test: No component renders hard-coded demo numbers in live mode
  it("guard: in live mode, no audited screen renders hard-coded '180 mg/dL' or '140 mg/dL'", () => {
    const liveEmptyData = {
      requires_review: true,
      max_severity: "low",
      reconciliation: {
        observation_comparisons: [],
        medication_comparisons: [],
      },
      verification: {
        observation_verifications: [],
        medication_verifications: [],
      },
    };

    Object.assign(mockAppContext, {
      setScreen: vi.fn(),
      setProviderScreen: vi.fn(),
      setSelectedPatient: vi.fn(),
      returnToHomeAndClearRun: vi.fn(),
      checkIn: { lowConfidence: false },
      liveCheckinResult: liveEmptyData,
      liveEhrConnection: { mode: "isolated" },
      liveDetail: null,
      isLiveMode: true,
      demoScenario: "conflict",
      resolvedCases: [],
      acknowledgedPatients: [],
      appointment: { isBooked: false },
      t: translations.en,
      isUrdu: false,
    });

    // ConflictScreen in live mode
    const { container: c1, unmount: u1 } = render(<ConflictScreen />);
    expect(c1.textContent?.includes("180")).toBe(false);
    expect(c1.textContent?.includes("140")).toBe(false);
    u1();

    // RiskResultScreen in live mode
    const { container: c2, unmount: u2 } = render(<RiskResultScreen />);
    expect(c2.textContent?.includes("110 mg/dL")).toBe(false);
    expect(c2.textContent?.includes("180")).toBe(false);
    u2();

    // ReconciliationAlertDetail in live mode with null liveDetail
    const { container: c3, unmount: u3 } = render(<ReconciliationAlertDetail />);
    expect(c3.textContent?.includes("180 mg/dL")).toBe(false);
    expect(c3.textContent?.includes("140 mg/dL")).toBe(false);
    u3();

    // ReviewQueueScreen in live mode
    const { container: c4, unmount: u4 } = render(<ReviewQueueScreen />);
    expect(c4.textContent?.includes("180 vs 140 mg/dL")).toBe(false);
    u4();
  });

  // 7. Connection badge text for isolated vs connected in EN and UR
  describe("Connection badge text and tooltips", () => {
    it("renders plain wording for isolated mode with tooltip in EN and UR", () => {
      // English isolated
      Object.assign(mockAppContext, {
        portal: "patient",
        screen: "home",
        isLiveMode: true,
        liveEhrConnection: { mode: "isolated" },
        t: translations.en,
        isUrdu: false,
        signOutUser: vi.fn(),
      });

      const { container: enHeader, unmount: unmountEn } = render(<Header />);
      expect(enHeader.textContent?.includes(translations.en.connectionBadgeIsolatedShort)).toBe(true);
      const enBadge = enHeader.querySelector(`[aria-label="${translations.en.connectionBadgeIsolated}"]`);
      expect(enBadge).toBeTruthy();
      expect(enBadge?.getAttribute("title")).toBe(translations.en.connectionBadgeIsolated);
      unmountEn();

      // Urdu isolated
      Object.assign(mockAppContext, {
        portal: "patient",
        screen: "home",
        isLiveMode: true,
        liveEhrConnection: { mode: "isolated" },
        t: translations.ur,
        isUrdu: true,
        signOutUser: vi.fn(),
      });

      const { container: urHeader } = render(<Header />);
      expect(urHeader.textContent?.includes(translations.ur.connectionBadgeIsolatedShort)).toBe(true);
      const urBadge = urHeader.querySelector(`[aria-label="${translations.ur.connectionBadgeIsolated}"]`);
      expect(urBadge).toBeTruthy();
      expect(urBadge?.getAttribute("title")).toBe(translations.ur.connectionBadgeIsolated);
    });

    it("renders connected badge with test environment designation in EN and UR", () => {
      // English connected
      Object.assign(mockAppContext, {
        portal: "patient",
        screen: "home",
        isLiveMode: true,
        liveEhrConnection: {
          mode: "fhir",
          connection: { display_name: "City General Hospital" },
        },
        t: translations.en,
        isUrdu: false,
        signOutUser: vi.fn(),
      });

      const { container: enHeader, unmount: unmountEn } = render(<Header />);
      expect(enHeader.textContent?.includes("Connected to City General Hospital (test environment)")).toBe(true);
      unmountEn();

      // Urdu connected
      Object.assign(mockAppContext, {
        portal: "patient",
        screen: "home",
        isLiveMode: true,
        liveEhrConnection: {
          mode: "fhir",
          connection: { display_name: "City General Hospital" },
        },
        t: translations.ur,
        isUrdu: true,
        signOutUser: vi.fn(),
      });

      const { container: urHeader } = render(<Header />);
      expect(urHeader.textContent?.includes("City General Hospital سے منسلک (ٹیسٹ ماحول)")).toBe(true);
    });
  });
});
