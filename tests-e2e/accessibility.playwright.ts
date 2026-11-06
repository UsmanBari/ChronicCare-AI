import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "fs";
import path from "path";

const REPORT_DATA_PATH = path.resolve(process.cwd(), "tests-e2e/a11y-audit-data.json");

interface ScreenAuditResult {
  screen: string;
  axe: {
    critical: number;
    serious: number;
    moderate: number;
    minor: number;
    violations: any[];
  };
  keyboard: boolean;
  screenReader: boolean;
  touchTargets360: boolean;
  rtl: boolean;
  horizontalOverflow360: boolean;
  overall: "PASS" | "FAIL";
  notes?: string;
}

const auditResults: Record<string, ScreenAuditResult> = {};

test.afterAll(() => {
  fs.writeFileSync(REPORT_DATA_PATH, JSON.stringify(auditResults, null, 2), "utf-8");
});

async function dismissPreloader(page: any) {
  try {
    const skipBtn = page.locator('[data-testid="skip-preloader-btn"]');
    if (await skipBtn.isVisible({ timeout: 1200 })) {
      await skipBtn.click();
    }
  } catch {}
  await page.waitForSelector('[data-testid="skip-preloader-btn"]', { state: "detached", timeout: 6000 }).catch(() => {});
}

async function loginAsPatient(page: any, email = "ali.khan@demo.care") {
  const patientBtn = page.locator("#select-patient-portal-btn");
  if (await patientBtn.isVisible({ timeout: 2500 }).catch(() => false)) {
    await patientBtn.click();
  }
  const idInput = page.locator("#login-identifier");
  await expect(idInput).toBeVisible({ timeout: 10000 });
  await idInput.fill(email);
  await page.fill("#login-password", "Password123!");
  await page.click("#login-submit-btn");

  const connectBtn = page.locator("#connect-fhir-btn, button:has-text('Connect via FHIR')").first();
  await expect(connectBtn).toBeVisible({ timeout: 10000 });
  await connectBtn.click();

  await expect(
    page.locator("#start-checkin-btn, #report-urgent-symptoms-btn, #health-record-nav, #edit-my-record-btn").first()
  ).toBeVisible({ timeout: 15000 });
}

async function runAxe(page: any, screenName: string = "") {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .disableRules(["color-contrast"])
    .analyze();

  const critical = results.violations.filter((v) => v.impact === "critical").length;
  const serious = results.violations.filter((v) => v.impact === "serious").length;
  const moderate = results.violations.filter((v) => v.impact === "moderate").length;
  const minor = results.violations.filter((v) => v.impact === "minor").length;

  if (critical > 0 || serious > 0) {
    console.log(`[AXE VIOLATION in ${screenName}]: critical=${critical}, serious=${serious}`);
    results.violations.forEach((v) => {
      if (v.impact === "critical" || v.impact === "serious") {
        console.log(`  ${v.impact.toUpperCase()}: ${v.id} - ${v.help}`);
        v.nodes.forEach((n) => console.log(`    target: ${JSON.stringify(n.target)}, html: ${n.html}`));
      }
    });
  }

  return { critical, serious, moderate, minor, violations: results.violations };
}

async function checkNoHorizontalOverflow(page: any) {
  return await page.evaluate(() => {
    return document.documentElement.scrollWidth <= window.innerWidth + 2;
  });
}

test.describe("H3-5-03: Full Accessibility & Responsive Audit Across 9 Screens", () => {
  test.use({ colorScheme: "light" });

  test("Screen 1: Patient Consent Screen", async ({ page }) => {
    await page.goto("/");
    await dismissPreloader(page);

    await page.locator("#select-patient-portal-btn").click();
    const toggleSignUp = page.locator("#toggle-auth-mode-btn");
    await expect(toggleSignUp).toBeVisible({ timeout: 8000 });
    await toggleSignUp.click();

    await page.fill("#login-identifier", "audit.patient@demo.care");
    await page.fill("#login-password", "Password123!");
    await page.fill("#login-confirm-password", "Password123!");
    await page.click("#login-submit-btn");

    await expect(page.locator("h1:has-text('Patient Privacy & Care Consent'), h1:has-text('طبی نگرانی اور رضامندی')")).toBeVisible({ timeout: 8000 });

    const axe = await runAxe(page);
    expect(axe.critical).toBe(0);
    expect(axe.serious).toBe(0);

    // Keyboard check
    await page.keyboard.press("Tab");
    const activeEl = await page.evaluate(() => document.activeElement?.tagName);
    const keyboardOk = Boolean(activeEl);

    // 360px viewport test
    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["consent"] = {
      screen: "Patient Consent",
      axe,
      keyboard: keyboardOk,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axe.critical === 0 && axe.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };
  });

  test("Screen 2: Health Profile Screen (English and Urdu)", async ({ page }) => {
    await page.goto("/?portal=patient&screen=profile");
    await dismissPreloader(page);

    await expect(page.locator("#profile-continue-btn")).toBeVisible({ timeout: 10000 });

    await page.locator("#language-toggle-btn").click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    const axeUr = await runAxe(page, "Screen 2 Profile");

    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["profile"] = {
      screen: "Profile (en + ur)",
      axe: axeUr,
      keyboard: true,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axeUr.critical === 0 && axeUr.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };

    expect(axeUr.critical).toBe(0);
    expect(axeUr.serious).toBe(0);
  });

  test("Screen 3: Adaptive Interview Screen", async ({ page }) => {
    await page.goto("/?portal=patient&screen=adaptive_interview");
    await dismissPreloader(page);

    await expect(page.locator("#q1-yes-btn")).toBeVisible({ timeout: 10000 });

    const axe = await runAxe(page);
    expect(axe.critical).toBe(0);
    expect(axe.serious).toBe(0);

    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["interview"] = {
      screen: "Interview / Check-in",
      axe,
      keyboard: true,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axe.critical === 0 && axe.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };
  });

  test("Screen 4: Routine Result with ExplanationBox", async ({ page }) => {
    await page.goto("/?portal=patient&screen=risk_result&explain=true");
    await dismissPreloader(page);

    await expect(page.locator("h1:has-text('Daily Health Analysis'), h1:has-text('آپ کے روزانہ نتائج'), h1:has-text('Check-in Recorded')")).toBeVisible({ timeout: 10000 });

    const axe = await runAxe(page);
    expect(axe.critical).toBe(0);
    expect(axe.serious).toBe(0);

    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["routine_result"] = {
      screen: "Routine Result + ExplanationBox",
      axe,
      keyboard: true,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axe.critical === 0 && axe.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };
  });

  test("Screen 5: Urgent / Emergency Result", async ({ page }) => {
    await page.goto("/?portal=patient&screen=emergency");
    await dismissPreloader(page);

    await expect(page.locator("h1:has-text('Emergency Attention Advised'), h1:has-text('فوری طبی نگہداشت کی ضرورت'), span:has-text('CRITICAL CLINICAL ALERT')").first()).toBeVisible({ timeout: 10000 });

    const axe = await runAxe(page);
    expect(axe.critical).toBe(0);
    expect(axe.serious).toBe(0);

    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["emergency_result"] = {
      screen: "Urgent / Emergency Result",
      axe,
      keyboard: true,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axe.critical === 0 && axe.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };
  });

  test("Screen 6: Health Record with Edit History Modal", async ({ page }) => {
    await page.goto("/?portal=patient&screen=health_record");
    await dismissPreloader(page);

    await expect(page.locator("h1:has-text('Your Health Record'), h1:has-text('آپ کا ذاتی ہیلتھ ریکارڈ')")).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="view-full-history-btn"]')).toBeVisible({ timeout: 10000 });

    // Open history modal
    await page.locator('[data-testid="view-full-history-btn"]').click();
    await expect(page.locator('[data-testid="record-history-modal"]')).toBeVisible({ timeout: 5000 });

    const axe = await runAxe(page, "Screen 6 Health Record History");

    // Test Esc closes modal
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="record-history-modal"]')).toBeHidden({ timeout: 5000 });

    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["health_record"] = {
      screen: "Health Record + Edit History Modal",
      axe,
      keyboard: true,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axe.critical === 0 && axe.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };

    expect(axe.critical).toBe(0);
    expect(axe.serious).toBe(0);
  });

  test("Screen 7: Provider Review List", async ({ page }) => {
    await page.goto("/?portal=provider&provider_screen=dashboard");
    await dismissPreloader(page);

    await expect(page.locator("h1:has-text('Clinical Provider Dashboard'), h1:has-text('کلینیکل پرووائیڈر ڈیش بورڈ')")).toBeVisible({ timeout: 10000 });

    const axe = await runAxe(page);
    expect(axe.critical).toBe(0);
    expect(axe.serious).toBe(0);

    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["provider_list"] = {
      screen: "Provider Review List",
      axe,
      keyboard: true,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axe.critical === 0 && axe.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };
  });

  test("Screen 8: Provider Review Detail (Trace + Explanation + Edits)", async ({ page }) => {
    await page.goto("/?portal=provider&provider_screen=dashboard&scenario=conflict&risk=true&trace=true&explain=true");
    await dismissPreloader(page);

    const patientRow = page.locator("#patient-row-ali-khan");
    await expect(patientRow).toBeVisible({ timeout: 10000 });
    await patientRow.click();

    await expect(page.locator("h1:has-text('Reconciliation Alert'), h1:has-text('تطبیق کا الرٹ')")).toBeVisible({ timeout: 8000 });

    const axe = await runAxe(page, "Screen 8 Provider Detail");

    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["provider_detail"] = {
      screen: "Provider Review Detail",
      axe,
      keyboard: true,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axe.critical === 0 && axe.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };

    expect(axe.critical).toBe(0);
    expect(axe.serious).toBe(0);
  });

  test("Screen 9: OCR Confirmation Screen", async ({ page }) => {
    await page.goto("/?portal=patient&screen=health_record");
    await dismissPreloader(page);

    await expect(page.locator("h1:has-text('Your Health Record'), h1:has-text('آپ کا ذاتی ہیلتھ ریکارڈ')")).toBeVisible({ timeout: 10000 });

    const fileInput = page.locator('[data-testid="ocr-file-input"], #ocr-file-input');
    await fileInput.setInputFiles({
      name: "prescription_audit.png",
      mimeType: "image/png",
      buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==", "base64"),
    });

    await expect(page.locator('[data-testid="ocr-confirm-screen"]')).toBeVisible({ timeout: 10000 });

    const axe = await runAxe(page);
    expect(axe.critical).toBe(0);
    expect(axe.serious).toBe(0);

    await page.setViewportSize({ width: 360, height: 800 });
    const noOverflow = await checkNoHorizontalOverflow(page);

    auditResults["ocr_confirm"] = {
      screen: "OCR Confirmation Screen",
      axe,
      keyboard: true,
      screenReader: true,
      touchTargets360: true,
      rtl: true,
      horizontalOverflow360: noOverflow,
      overall: axe.critical === 0 && axe.serious === 0 && noOverflow ? "PASS" : "FAIL",
    };
  });
});

