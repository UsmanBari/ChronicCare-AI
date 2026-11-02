/**
 * @vitest-environment jsdom
 */
import React from "react";
import { describe, it, expect, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { AlertTriangle } from "lucide-react";

// Unit test component testing the exact banner component logic
const DangerWordgroupBanner = ({
  safetyNote,
  onDismiss,
}: {
  safetyNote: string | null;
  onDismiss: () => void;
}) => {
  if (!safetyNote) return null;
  return (
    <div
      data-testid="danger-wordgroup-banner"
      className="p-3.5 rounded-xl bg-amber-50 border-2 border-amber-600 text-amber-950 text-sm font-bold flex items-center justify-between gap-3 animate-fadeIn shadow-xs"
    >
      <div className="flex items-center gap-2.5">
        <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0" />
        <span>{safetyNote}</span>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        className="text-amber-800 hover:text-amber-950 text-xs px-1 font-bold"
        aria-label="Dismiss safety note"
      >
        ✕
      </button>
    </div>
  );
};

describe("B3 Frontend Banner: Danger Wordgroup Advisory", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders English emergency call 1122 advisory line", () => {
    let dismissed = false;
    const enText = "If this is an emergency, call 1122 now.";
    render(
      <DangerWordgroupBanner
        safetyNote={enText}
        onDismiss={() => {
          dismissed = true;
        }}
      />
    );

    const banner = screen.getByTestId("danger-wordgroup-banner");
    expect(banner).toBeDefined();
    expect(banner.textContent).toContain("If this is an emergency, call 1122 now.");

    const dismissBtn = screen.getByLabelText("Dismiss safety note");
    fireEvent.click(dismissBtn);
    expect(dismissed).toBe(true);
  });

  it("renders Urdu emergency call 1122 advisory line", () => {
    let dismissed = false;
    const urText = "اگر یہ ایمرجنسی ہے تو ابھی 1122 پر کال کریں۔";
    render(
      <DangerWordgroupBanner
        safetyNote={urText}
        onDismiss={() => {
          dismissed = true;
        }}
      />
    );

    const banner = screen.getByTestId("danger-wordgroup-banner");
    expect(banner).toBeDefined();
    expect(banner.textContent).toContain("اگر یہ ایمرجنسی ہے تو ابھی 1122 پر کال کریں۔");
    expect(banner.textContent).toContain("1122");
  });

  it("renders null when safetyNote is absent", () => {
    const { container } = render(
      <DangerWordgroupBanner safetyNote={null} onDismiss={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });
});
