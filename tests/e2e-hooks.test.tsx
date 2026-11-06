// @vitest-environment jsdom
import React from "react";
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { AppProvider, useApp } from "../app/context/AppContext";

function StateViewer() {
  const { portal, screen: currentScreen, providerScreen, demoScenario } = useApp();
  return (
    <div>
      <div data-testid="portal-val">{portal}</div>
      <div data-testid="screen-val">{currentScreen}</div>
      <div data-testid="provider-screen-val">{providerScreen}</div>
      <div data-testid="scenario-val">{demoScenario}</div>
    </div>
  );
}

describe("E2E URL Hooks Build-Time Gating (PR #119)", () => {
  const origEnv = process.env.NEXT_PUBLIC_E2E_HOOKS;

  beforeEach(() => {
    cleanup();
    delete (window as any).location;
    window.location = new URL("http://localhost:3000/?portal=provider&screen=profile&provider_screen=alerts&scenario=emergency") as any;
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_E2E_HOOKS = origEnv;
    cleanup();
  });

  it("without NEXT_PUBLIC_E2E_HOOKS=1, URL search parameters change nothing (defaults preserved)", () => {
    delete process.env.NEXT_PUBLIC_E2E_HOOKS;

    render(
      <AppProvider>
        <StateViewer />
      </AppProvider>
    );

    expect(screen.getByTestId("portal-val").textContent).toBe("landing");
    expect(screen.getByTestId("screen-val").textContent).toBe("home");
    expect(screen.getByTestId("provider-screen-val").textContent).toBe("dashboard");
    expect(screen.getByTestId("scenario-val").textContent).toBe("normal");
  });

  it("with NEXT_PUBLIC_E2E_HOOKS=1, URL search parameters are parsed into state for e2e test navigation", () => {
    process.env.NEXT_PUBLIC_E2E_HOOKS = "1";

    render(
      <AppProvider>
        <StateViewer />
      </AppProvider>
    );

    expect(screen.getByTestId("portal-val").textContent).toBe("provider");
    expect(screen.getByTestId("screen-val").textContent).toBe("profile");
    expect(screen.getByTestId("provider-screen-val").textContent).toBe("alerts");
    expect(screen.getByTestId("scenario-val").textContent).toBe("emergency");
  });
});

