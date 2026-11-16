// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConflictScreen } from "../app/components/ConflictScreen";
import { ReconciliationAlertDetail } from "../app/components/provider/ReconciliationAlertDetail";
import { translations } from "../app/translations";
import { api } from "../app/lib/api";
import {
  isObservationThatMatters,
  isObservationDiscrepancy,
  formatObservationTitle,
} from "../app/lib/presentation";

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

// Mock recharts for provider components
vi.mock("recharts", async () => {
  const actual: any = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
  };
});

describe("P1-6: Reconciliation Observation Cards (SMART Sandbox Fixture)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Presentation helper unit tests
  describe("Pure presentation helpers for observation discrepancies", () => {
    it("isObservationThatMatters correctly identifies vital signs and rejects routine labs", () => {
      // In-scope chronic care observations
      expect(isObservationThatMatters("blood_pressure_systolic")).toBe(true);
      expect(isObservationThatMatters("blood_pressure_diastolic")).toBe(true);
      expect(isObservationThatMatters("systolic")).toBe(true);
      expect(isObservationThatMatters("diastolic")).toBe(true);
      expect(isObservationThatMatters("glucose")).toBe(true);
      expect(isObservationThatMatters("blood_glucose")).toBe(true);
      expect(isObservationThatMatters("blood_sugar")).toBe(true);
      expect(isObservationThatMatters("hba1c")).toBe(true);
      expect(isObservationThatMatters("glycated_hemoglobin")).toBe(true);

      // Unasked hospital labs
      expect(isObservationThatMatters("sodium")).toBe(false);
      expect(isObservationThatMatters("potassium")).toBe(false);
      expect(isObservationThatMatters("chloride")).toBe(false);
      expect(isObservationThatMatters("calcium")).toBe(false);
      expect(isObservationThatMatters("creatinine")).toBe(false);
      expect(isObservationThatMatters("urea_nitrogen")).toBe(false);
      expect(isObservationThatMatters(null)).toBe(false);
      expect(isObservationThatMatters(undefined)).toBe(false);
    });

    it("isObservationDiscrepancy enforces: hospital observation with no reading today is NOT a discrepancy", () => {
      // Sodium missing_in_b -> not reported today -> NEVER a discrepancy
      const sodiumMissing = {
        observation_type: "sodium",
        value_a: 143.4,
        value_b: null,
        status: "missing_in_b",
        timestamp_a: "2021-01-11T00:00:00Z",
      };
      expect(isObservationDiscrepancy(sodiumMissing)).toBe(false);

      // Blood pressure systolic missing_in_b -> also not reported today -> NOT a discrepancy
      const bpMissing = {
        observation_type: "blood_pressure_systolic",
        value_a: 120,
        value_b: null,
        status: "missing_in_b",
        timestamp_a: "2021-01-11T00:00:00Z",
      };
      expect(isObservationDiscrepancy(bpMissing)).toBe(false);

      // Blood pressure systolic conflict -> both values present -> YES discrepancy
      const bpConflict = {
        observation_type: "blood_pressure_systolic",
        value_a: 120,
        value_b: 148,
        delta: 28,
        status: "conflict",
        timestamp_a: "2021-01-11T00:00:00Z",
      };
      expect(isObservationDiscrepancy(bpConflict)).toBe(true);

      // Blood pressure diastolic agree -> NOT a discrepancy
      const bpAgree = {
        observation_type: "blood_pressure_diastolic",
        value_a: 80,
        value_b: 82,
        delta: 2,
        status: "agree",
        timestamp_a: "2021-01-11T00:00:00Z",
      };
      expect(isObservationDiscrepancy(bpAgree)).toBe(false);
    });

    it("formatObservationTitle formats titles in English and Urdu", () => {
      expect(formatObservationTitle("blood_pressure_systolic", false)).toBe("Blood Pressure (Systolic)");
      expect(formatObservationTitle("blood_pressure_systolic", true)).toBe("بلڈ پریشر (سسٹولک)");
      expect(formatObservationTitle("blood_pressure_diastolic", false)).toBe("Blood Pressure (Diastolic)");
      expect(formatObservationTitle("blood_pressure_diastolic", true)).toBe("بلڈ پریشر (ڈائیسٹولک)");
      expect(formatObservationTitle("glucose", false)).toBe("Blood Glucose");
      expect(formatObservationTitle("glucose", true)).toBe("خون میں گلوکوز (شوگر)");
      expect(formatObservationTitle("hba1c", false)).toBe("HbA1c");
      expect(formatObservationTitle("hba1c", true)).toBe("ایچ بی اے ون سی (HbA1c)");
    });
  });

  // 2. Integration test with SMART sandbox fixture: 9bf59715-246f-4ce2-85a6-58c1757f8d21
  describe("SMART sandbox fixture (9bf59715-246f-4ce2-85a6-58c1757f8d21): BP 148/94, glucose 165", () => {
    const sandboxReconResult = {
      patient_id: "9bf59715-246f-4ce2-85a6-58c1757f8d21",
      requires_review: true,
      max_severity: "moderate",
      reconciliation: {
        observation_comparisons: [
          // Index 0: Sodium from hospital bundle (unasked, no reading today)
          {
            observation_type: "sodium",
            value_a: 143.4,
            value_b: null,
            unit_a: "mmol/L",
            unit_b: null,
            source_a: "fhir",
            source_b: null,
            timestamp_a: "2021-01-11T10:00:00Z",
            timestamp_b: null,
            status: "missing_in_b",
            delta: null,
          },
          // Index 1: Systolic BP discrepancy (hospital 120 vs today 148)
          {
            observation_type: "blood_pressure_systolic",
            value_a: 120,
            value_b: 148,
            unit_a: "mmHg",
            unit_b: "mmHg",
            source_a: "fhir",
            source_b: "local",
            timestamp_a: "2021-01-11T10:00:00Z",
            timestamp_b: "2026-11-15T18:00:00Z",
            status: "conflict",
            delta: 28,
          },
          // Index 2: Diastolic BP discrepancy (hospital 80 vs today 94)
          {
            observation_type: "blood_pressure_diastolic",
            value_a: 80,
            value_b: 94,
            unit_a: "mmHg",
            unit_b: "mmHg",
            source_a: "fhir",
            source_b: "local",
            timestamp_a: "2021-01-11T10:00:00Z",
            timestamp_b: "2026-11-15T18:00:00Z",
            status: "conflict",
            delta: 14,
          },
          // Index 3: Glucose discrepancy (hospital 110 vs today 165)
          {
            observation_type: "glucose",
            value_a: 110,
            value_b: 165,
            unit_a: "mg/dL",
            unit_b: "mg/dL",
            source_a: "fhir",
            source_b: "local",
            timestamp_a: "2021-01-11T10:00:00Z",
            timestamp_b: "2026-11-15T18:00:00Z",
            status: "conflict",
            delta: 55,
          },
        ],
        medication_comparisons: [],
        summary: { agreements: 0, conflicts: 3, missing_in_a: 0, missing_in_b: 1, insufficient_data: 0 },
      },
      verification: {
        observation_verifications: [
          {
            observation_type: "sodium",
            trust_level_a: "high",
            trust_level_b: null,
            severity: "low",
            requires_human_review: false,
            review_reason: "Record missing in one source (missing_in_b); present side is high-trust (auto-resolved)",
          },
          {
            observation_type: "blood_pressure_systolic",
            trust_level_a: "high",
            trust_level_b: "low",
            severity: "moderate",
            requires_human_review: true,
            review_reason: "Observation conflict exceeding threshold (delta 28.0 > 10.0)",
          },
          {
            observation_type: "blood_pressure_diastolic",
            trust_level_a: "high",
            trust_level_b: "low",
            severity: "moderate",
            requires_human_review: true,
            review_reason: "Observation conflict exceeding threshold (delta 14.0 > 10.0)",
          },
          {
            observation_type: "glucose",
            trust_level_a: "high",
            trust_level_b: "low",
            severity: "moderate",
            requires_human_review: true,
            review_reason: "Observation conflict exceeding threshold (delta 55.0 > 15.0)",
          },
        ],
        medication_verifications: [],
        summary: { auto_resolved: 1, requires_review: 3, severity_moderate: 3 },
      },
    };

    it("Patient ConflictScreen: shows one card per discrepancy that matters (BP sys, BP dia, glucose); NEVER headlines Sodium", () => {
      Object.assign(mockAppContext, {
        setScreen: vi.fn(),
        checkIn: { lowConfidence: false },
        liveCheckinResult: sandboxReconResult,
        liveEhrConnection: { mode: "connected" },
        isLiveMode: true,
        t: translations.en,
        isUrdu: false,
      });

      const { container } = render(<ConflictScreen />);
      const text = container.textContent || "";

      // 1. Sodium is NEVER shown as a headline or card
      expect(text.includes("Sodium")).toBe(false);
      expect(text.includes("143.4")).toBe(false);
      expect(text.includes("Not reported today")).toBe(false);

      // 2. Systolic BP card is shown comparing hospital value (with date) to today's reading
      expect(text.includes("Blood Pressure (Systolic)")).toBe(true);
      expect(text.includes("120 mmHg")).toBe(true);
      expect(text.includes("148 mmHg")).toBe(true);
      expect(text.includes("2021-01-11")).toBe(true);

      // 3. Diastolic BP card is shown comparing hospital value (with date) to today's reading
      expect(text.includes("Blood Pressure (Diastolic)")).toBe(true);
      expect(text.includes("80 mmHg")).toBe(true);
      expect(text.includes("94 mmHg")).toBe(true);

      // 4. Glucose card is shown comparing hospital value to today's reading
      expect(text.includes("Blood Glucose")).toBe(true);
      expect(text.includes("110 mg/dL")).toBe(true);
      expect(text.includes("165 mg/dL")).toBe(true);

      // 5. P2-11: Shows every reading given (BP too) with the target tag
      expect(text.includes("Above target")).toBe(true);
      expect(text.includes("Also reported today:")).toBe(true);
      expect(text.includes("148/94 mmHg")).toBe(true);
    });

    it("Provider ReconciliationAlertDetail: shows one card per discrepancy; NEVER headlines 'Sodium Review'", async () => {
      // Provide live detail directly to match the fixture
      const liveDetail = {
        checkin_id: "checkin-sandbox-123",
        patient_id: "9bf59715-246f-4ce2-85a6-58c1757f8d21",
        patient_display: "SMART Sandbox Patient (Age 78)",
        mode: "connected",
        max_severity: "moderate",
        reconciliation: sandboxReconResult.reconciliation,
        verification: sandboxReconResult.verification,
      };

      vi.spyOn(api, "getProviderReviewDetail").mockResolvedValue(liveDetail as any);
      vi.spyOn(api, "getProviderSoapNote").mockResolvedValue({
        subjective: [],
        objective: [],
        assessment: [],
        plan: [],
        data_sources: [],
      } as any);

      Object.assign(mockAppContext, {
        setProviderScreen: vi.fn(),
        resolvedCases: [],
        selectedPatient: "checkin-sandbox-123",
        isLiveMode: true,
        t: translations.en,
        isUrdu: false,
      });

      const { container } = render(<ReconciliationAlertDetail />);
      // Wait for async load to finish
      await vi.waitFor(() => {
        expect(container.textContent?.includes("Blood Pressure (Systolic)")).toBe(true);
      });

      const text = container.textContent || "";

      // 1. Ensure NO "Sodium Review" headline exists
      expect(text.includes("Sodium Review")).toBe(false);
      expect(text.includes("143.4 mmol/L")).toBe(false);
      expect(text.includes("Not reported today")).toBe(false);

      // 2. Both systolic and diastolic discrepancies appear as distinct cards
      expect(text.includes("Blood Pressure (Systolic)")).toBe(true);
      expect(text.includes("120 mmHg")).toBe(true);
      expect(text.includes("148 mmHg")).toBe(true);

      expect(text.includes("Blood Pressure (Diastolic)")).toBe(true);
      expect(text.includes("80 mmHg")).toBe(true);
      expect(text.includes("94 mmHg")).toBe(true);

      // 3. Glucose discrepancy appears as a distinct card
      expect(text.includes("Blood Glucose")).toBe(true);
      expect(text.includes("110 mg/dL")).toBe(true);
      expect(text.includes("165 mg/dL")).toBe(true);
    });
  });

  // 3. Edge case: Only unasked hospital observation exists (Sodium missing_in_b)
  describe("Edge case: Hospital has Sodium on file, patient had no reading today", () => {
    it("ConflictScreen renders honest review card without displaying Sodium or 'Not reported today'", () => {
      const liveResultOnlySodium = {
        requires_review: true,
        max_severity: "low",
        reconciliation: {
          observation_comparisons: [
            {
              observation_type: "sodium",
              value_a: 143.4,
              value_b: null,
              unit_a: "mmol/L",
              status: "missing_in_b",
              timestamp_a: "2021-01-11T10:00:00Z",
            },
          ],
          medication_comparisons: [],
        },
        verification: {
          observation_verifications: [
            {
              observation_type: "sodium",
              severity: "low",
              requires_human_review: false,
            },
          ],
        },
      };

      Object.assign(mockAppContext, {
        setScreen: vi.fn(),
        checkIn: { lowConfidence: false },
        liveCheckinResult: liveResultOnlySodium,
        liveEhrConnection: { mode: "connected" },
        isLiveMode: true,
        t: translations.en,
        isUrdu: false,
      });

      const { container } = render(<ConflictScreen />);
      const text = container.textContent || "";

      expect(text.includes("Sodium")).toBe(false);
      expect(text.includes("143.4")).toBe(false);
      expect(text.includes("Not reported today")).toBe(false);
      expect(text.includes(translations.en.needsClinicianReviewTitle)).toBe(true);
    });
  });
});
