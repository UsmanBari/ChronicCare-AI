// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup, waitFor } from "@testing-library/react";
import { AdminConfigStatusSection } from "../app/components/admin/AdminConfigStatusSection";
import { translations } from "../app/translations";
import { api, AdminConfigStatusResponse } from "../app/lib/api";

const mockAppContext: Record<string, any> = {};

vi.mock("../app/context/AppContext", () => ({
  useApp: () => mockAppContext,
}));

describe("AdminConfigStatusSection (I3 Day 5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAppContext.isLiveMode = false;
    mockAppContext.isUrdu = false;
    mockAppContext.t = translations.en;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders demo mode config status without making network calls", () => {
    const spyApi = vi.spyOn(api, "getAdminConfigStatus");

    render(<AdminConfigStatusSection />);

    expect(screen.getByTestId("admin-config-status-section")).toBeTruthy();
    expect(screen.getByText("System Configuration & Guards Status")).toBeTruthy();
    expect(screen.getByText("EXPLAIN_MODE")).toBeTruthy();
    expect(screen.getByText("GROQ_API_KEY")).toBeTruthy();
    expect(screen.getByText("GEMINI_API_KEY")).toBeTruthy();
    expect(screen.getByText("Queue Length:")).toBeTruthy();

    expect(spyApi).not.toHaveBeenCalled();
  });

  it("fetches and renders live config status when in live mode", async () => {
    mockAppContext.isLiveMode = true;

    const mockResponse: AdminConfigStatusResponse = {
      settings: [
        { name: "DB_BACKEND", set: true },
        { name: "FHIR_BASE_URL", set: true },
      ],
      flags: {
        EXPLAIN_ENABLED: true,
        EXPLAIN_MODE: "background",
        RISK_ENABLED: false,
        ORCHESTRATOR: "direct",
        LLM_PROVIDER: "auto",
      },
      keys_and_models: {
        GROQ_API_KEY: "SET",
        GROQ_MODEL: "SET",
        GEMINI_API_KEY: "NOT SET",
        GEMINI_MODEL: "SET",
      },
      explainer_metrics: {
        tokens_used_today: 1240,
        tokens_used_by_provider: { groq: 1240, gemini: 0 },
        cap: 150000,
        caps: { groq: 150000, gemini: 150000 },
        breaker_state: "closed",
        breaker_states: { groq: "closed", gemini: "closed" },
        cache_size: 12,
        cache_hits: 4,
        cache_misses: 8,
        llm_calls: 3,
        llm_calls_by_provider: { groq: 3, gemini: 0 },
        queue_length: 2,
        mode: "background",
        template_fallbacks_by_reason: {},
      },
    };

    const spyApi = vi
      .spyOn(api, "getAdminConfigStatus")
      .mockResolvedValue(mockResponse);

    render(<AdminConfigStatusSection />);

    await waitFor(() => {
      expect(screen.getByText("EXPLAIN_MODE")).toBeTruthy();
    });

    expect(spyApi).toHaveBeenCalledTimes(1);
    expect(screen.getByText("BACKGROUND")).toBeTruthy();
    expect(screen.getByText("GROQ_API_KEY")).toBeTruthy();
    expect(screen.getByText("GEMINI_API_KEY")).toBeTruthy();
    expect(screen.getByText("NOT SET")).toBeTruthy();
    expect(screen.getByText("Queue Length:")).toBeTruthy();
  });

  it("supports manual refresh via refresh button", async () => {
    mockAppContext.isLiveMode = true;

    const mockResponse: AdminConfigStatusResponse = {
      settings: [],
      flags: { EXPLAIN_MODE: "background" },
      keys_and_models: { GROQ_API_KEY: "SET" },
      explainer_metrics: {
        tokens_used_today: 0,
        tokens_used_by_provider: {},
        cap: 150000,
        caps: {},
        breaker_state: "closed",
        breaker_states: {},
        cache_size: 0,
        cache_hits: 0,
        cache_misses: 0,
        llm_calls: 0,
        llm_calls_by_provider: {},
        queue_length: 5,
        mode: "background",
        template_fallbacks_by_reason: {},
      },
    };

    const spyApi = vi
      .spyOn(api, "getAdminConfigStatus")
      .mockResolvedValue(mockResponse);

    render(<AdminConfigStatusSection />);

    await waitFor(() => {
      expect(screen.getByText("EXPLAIN_MODE")).toBeTruthy();
    });
    expect(spyApi).toHaveBeenCalledTimes(1);

    const refreshBtn = screen.getByTestId("refresh-config-btn");
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(spyApi).toHaveBeenCalledTimes(2);
    });
  });
});
