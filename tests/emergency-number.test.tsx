// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import fs from "fs";
import path from "path";
import { EmergencyScreen } from "../app/components/EmergencyScreen";
import { HomeScreen } from "../app/components/HomeScreen";
import { translations } from "../app/translations";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

vi.mock("../app/lib/api", async () => {
  const actual: any = await vi.importActual("../app/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getUserCheckinSummary: vi.fn().mockResolvedValue({
        checkins_last_7_days: 0,
        unreviewed_risk_count: 0,
        recent_checkins: [],
      }),
      getPatientRecord: vi.fn().mockResolvedValue({
        conditions: ["diabetes"],
        medications: [],
        allergies: [],
        baseline_observations: [],
      }),
    },
  };
});

describe("Emergency Number 1122 Only (Day 6c: Remove 911 Regression Guard)", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();

    Object.assign(mockAppContext, {
      returnToHomeAndClearRun: vi.fn(),
      escalationRecorded: true,
      isLiveMode: true,
      t: translations.en,
      isUrdu: false,
      setScreen: vi.fn(),
      profile: { full_name: "Test Patient" },
      liveProfile: { full_name: "Test Patient" },
      liveEhrConnection: null,
      connectionMode: "isolated",
      userIdentifier: "PATIENT-001",
      demoScenario: null,
      setDemoScenario: vi.fn(),
      resetDemo: vi.fn(),
      appointment: null,
      setActiveLiveCheckin: vi.fn(),
      setShowSettings: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe("EmergencyScreen", () => {
    it("renders English emergency screen with 1122 and zero occurrences of 911", () => {
      mockAppContext.isUrdu = false;
      mockAppContext.t = translations.en;

      const { container } = render(<EmergencyScreen />);
      const text = container.textContent || "";

      // 1122 must be present
      expect(text).toContain("1122");
      // 911 must NOT be present anywhere in the screen
      expect(text).not.toContain("911");

      // Verify the phone link points to tel:1122
      const telLink = container.querySelector('a[href="tel:1122"]');
      expect(telLink).not.toBeNull();
      expect(telLink?.textContent).toContain("1122");
      expect(telLink?.textContent).not.toContain("911");
    });

    it("renders Urdu emergency screen with 1122 and zero occurrences of 911", () => {
      mockAppContext.isUrdu = true;
      mockAppContext.t = translations.ur;

      const { container } = render(<EmergencyScreen />);
      const text = container.textContent || "";

      // 1122 must be present
      expect(text).toContain("1122");
      // 911 must NOT be present anywhere in the screen
      expect(text).not.toContain("911");

      // Verify the phone link points to tel:1122
      const telLink = container.querySelector('a[href="tel:1122"]');
      expect(telLink).not.toBeNull();
      expect(telLink?.textContent).toContain("1122");
      expect(telLink?.textContent).not.toContain("911");
    });
  });

  describe("HomeScreen Urgent Medical Guidance Modal", () => {
    it("renders English urgent guidance modal with 1122 and zero occurrences of 911", () => {
      mockAppContext.isUrdu = false;
      mockAppContext.t = translations.en;
      mockAppContext.isLiveMode = true;

      const { container } = render(<HomeScreen />);

      // Trigger the urgent guidance modal
      const urgentBtn = screen.getByRole("button", { name: /Report Urgent Symptoms Now/i });
      fireEvent.click(urgentBtn);

      const modalText = container.textContent || "";
      expect(modalText).toContain("1122");
      expect(modalText).not.toContain("911");
      expect(modalText).toContain("contact emergency services (1122) immediately");
    });

    it("renders Urdu urgent guidance modal with 1122 and zero occurrences of 911", () => {
      mockAppContext.isUrdu = true;
      mockAppContext.t = translations.ur;
      mockAppContext.isLiveMode = true;

      const { container } = render(<HomeScreen />);

      // Trigger the urgent guidance modal
      const urgentBtn = screen.getByRole("button", { name: /فوری علامات کی اطلاع دیں/i });
      fireEvent.click(urgentBtn);

      const modalText = container.textContent || "";
      expect(modalText).toContain("1122");
      expect(modalText).not.toContain("911");
      expect(modalText).toContain("ایمرجنسی سروسز (1122) پر کال کریں");
    });
  });

  describe("Static Source Code Regression Guard", () => {
    it("ensures no patient-facing source file in app/ contains the string 911", () => {
      const appDir = path.resolve(__dirname, "../app");
      const codeExtensions = new Set([".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html"]);

      function scanDir(dir: string): { file: string; line: number; text: string }[] {
        const violations: { file: string; line: number; text: string }[] = [];
        const entries = fs.readdirSync(dir, { withFileTypes: true });

        for (const entry of entries) {
          const fullPath = path.join(dir, entry.name);
          if (entry.isDirectory()) {
            violations.push(...scanDir(fullPath));
          } else if (entry.isFile()) {
            const ext = path.extname(entry.name).toLowerCase();
            if (codeExtensions.has(ext)) {
              const content = fs.readFileSync(fullPath, "utf-8");
              const lines = content.split("\n");
              lines.forEach((lineText, idx) => {
                if (lineText.includes("911")) {
                  violations.push({
                    file: path.relative(appDir, fullPath),
                    line: idx + 1,
                    text: lineText.trim(),
                  });
                }
              });
            }
          }
        }
        return violations;
      }

      const violations = scanDir(appDir);
      expect(violations).toEqual([]);
    });
  });
});
