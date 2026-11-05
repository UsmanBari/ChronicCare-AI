// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ExplanationBox } from "../app/components/ExplanationBox";
import { translations } from "../app/translations";
import { PatientExplanation } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("Explanation Sources & Citation Attribution (Part X7)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = true;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
    mockAppContext.liveCheckinResult = null;
    mockAppContext.activeLiveCheckin = null;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders full citation and external DOI link in English when present", () => {
    const explanation: PatientExplanation = {
      status: "ready",
      sentences: [
        { text: "Your blood pressure is within expected clinical range [c1].", cites: ["c1"] },
      ],
      sources: [
        {
          chunk_id: "c1",
          title: "WHO Guideline",
          edition: "2021",
          section_path: "hypertension/targets",
          page_start: 12,
          full_citation: "World Health Organization. Guideline for pharmacological treatment. 2021.",
          doi: "https://doi.org/10.1234/who.example",
        },
      ],
    };

    render(<ExplanationBox explanation={explanation} emergency={false} />);

    // Expand accordion
    const toggleBtn = screen.getByTestId("explanation-toggle-btn");
    fireEvent.click(toggleBtn);

    // Verify citation text is displayed
    expect(screen.getByText(/World Health Organization\. Guideline for pharmacological treatment\. 2021\./i)).toBeDefined();

    // Verify DOI link
    const doiLink = screen.getByTestId("explanation-source-doi") as HTMLAnchorElement;
    expect(doiLink).toBeDefined();
    expect(doiLink.href).toBe("https://doi.org/10.1234/who.example");
    expect(doiLink.target).toBe("_blank");
    expect(doiLink.rel).toContain("noopener");
    expect(doiLink.rel).toContain("noreferrer");
  });

  it("renders in Urdu with Urdu labels when isUrdu is true", () => {
    mockAppContext.isUrdu = true;
    mockAppContext.t = translations.ur;

    const explanation: PatientExplanation = {
      status: "ready",
      sentences: [
        { text: "آپ کا بلڈ پریشر طے شدہ حدود میں ہے [c1]۔", cites: ["c1"] },
      ],
      sources: [
        {
          chunk_id: "c1",
          title: "WHO Guideline",
          full_citation: "عالمی ادارہ صحت، گائیڈ لائن 2021",
          doi: "10.1234/ur.example",
        },
      ],
    };

    render(<ExplanationBox explanation={explanation} emergency={false} />);

    const toggleBtn = screen.getByTestId("explanation-toggle-btn");
    fireEvent.click(toggleBtn);

    expect(screen.getByText("طبی ذرائع:")).toBeDefined();
    expect(screen.getByText(/عالمی ادارہ صحت، گائیڈ لائن 2021/i)).toBeDefined();

    const doiLink = screen.getByTestId("explanation-source-doi") as HTMLAnchorElement;
    expect(doiLink).toBeDefined();
    expect(doiLink.href).toBe("https://doi.org/10.1234/ur.example");
    expect(doiLink.textContent).toContain("طبی حوالہ / ربط");
  });

  it("does not render DOI link if doi is missing or 'TO FILL BY USMAN'", () => {
    const explanation: PatientExplanation = {
      status: "ready",
      sentences: [
        { text: "Lifestyle modifications are recommended [c1].", cites: ["c1"] },
      ],
      sources: [
        {
          chunk_id: "c1",
          title: "ISH Guideline",
          full_citation: "ISH Hypertension Guidelines 2020.",
          doi: "TO FILL BY USMAN",
        },
      ],
    };

    render(<ExplanationBox explanation={explanation} emergency={false} />);
    fireEvent.click(screen.getByTestId("explanation-toggle-btn"));

    expect(screen.getByText(/ISH Hypertension Guidelines 2020\./i)).toBeDefined();
    expect(screen.queryByTestId("explanation-source-doi")).toBeNull();
  });

  it("strictly contains NO ADA logo anywhere in the DOM", () => {
    const explanation: PatientExplanation = {
      status: "ready",
      sentences: [
        { text: "Sentence 1 [c1].", cites: ["c1"] },
      ],
      sources: [
        {
          chunk_id: "c1",
          title: "Diabetes Care Guidelines",
          full_citation: "American Diabetes Association. Standards of Care. 2026.",
          doi: "https://doi.org/10.2337/example",
        },
      ],
    };

    const { container } = render(<ExplanationBox explanation={explanation} emergency={false} />);
    fireEvent.click(screen.getByTestId("explanation-toggle-btn"));

    // Check no img tag has ADA logo or alt containing ADA
    const images = container.querySelectorAll("img");
    images.forEach((img) => {
      const src = img.getAttribute("src") || "";
      const alt = img.getAttribute("alt") || "";
      expect(src.toLowerCase()).not.toContain("ada");
      expect(alt.toLowerCase()).not.toContain("ada");
    });
  });
});

