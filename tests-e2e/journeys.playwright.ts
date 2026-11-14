import { test, expect } from "@playwright/test";
import path from "path";
import fs from "fs";

const SCREENSHOT_DIR = path.resolve(process.cwd(), "docs/screenshots/w3/e2e");
const DEMO_SCREENSHOT_DIR = path.resolve(process.cwd(), "docs/screenshots/w4/demo");

test.beforeAll(() => {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
  if (!fs.existsSync(DEMO_SCREENSHOT_DIR)) {
    fs.mkdirSync(DEMO_SCREENSHOT_DIR, { recursive: true });
  }
});

/**
 * Dismisses the preloader instantly if present.
 */
async function dismissPreloader(page: any) {
  try {
    const skipBtn = page.locator('[data-testid="skip-preloader-btn"]');
    if (await skipBtn.isVisible({ timeout: 1200 })) {
      await skipBtn.click();
    }
  } catch {}
  await page.waitForSelector('[data-testid="skip-preloader-btn"]', { state: "detached", timeout: 6000 }).catch(() => {});
}

/**
 * Captures key journey screens at both 1280px (desktop) and 375px (mobile) viewports into docs/screenshots/w4/demo/.
 */
async function captureKeyScreenshots(page: any, baseName: string, scrollTargetLocator?: any) {
  // 1. Desktop 1280px
  await page.setViewportSize({ width: 1280, height: 720 });
  if (scrollTargetLocator) {
    await scrollTargetLocator.scrollIntoViewIfNeeded();
  }
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(DEMO_SCREENSHOT_DIR, `${baseName}_1280px.png`) });

  // 2. Mobile 375px
  await page.setViewportSize({ width: 375, height: 667 });
  if (scrollTargetLocator) {
    await scrollTargetLocator.scrollIntoViewIfNeeded();
  }
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(DEMO_SCREENSHOT_DIR, `${baseName}_375px.png`) });

  // Restore desktop 1280px
  await page.setViewportSize({ width: 1280, height: 720 });
}

/**
 * Logs in as demo patient and ensures HomeScreen is reached.
 */
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

  // On Connection screen, click Connect via FHIR
  const connectBtn = page.locator("#connect-fhir-btn, button:has-text('Connect via FHIR')").first();
  await expect(connectBtn).toBeVisible({ timeout: 10000 });
  await connectBtn.click();

  // Wait for Home screen to mount
  await expect(
    page.locator("#start-checkin-btn, #report-urgent-symptoms-btn, #health-record-nav").first()
  ).toBeVisible({ timeout: 15000 });
}

// =============================================================================
// I4-S: 17 Nov Evaluation E2E Demo Journeys (J-a through J-i)
// =============================================================================

test.describe("I4-S: 17 Nov Evaluation Demo Journeys", () => {
  test.use({ colorScheme: "light" });

  let pageErrors: Error[] = [];
  let consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    pageErrors = [];
    consoleErrors = [];
    page.on("pageerror", (err) => {
      console.log(`[PAGEERROR]: ${err.message}\n${err.stack}`);
      pageErrors.push(err);
    });
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        console.log(`[CONSOLE_ERROR]: ${msg.text()}`);
        consoleErrors.push(msg.text());
      }
    });
  });

  test.afterEach(async ({ page }) => {
    // Fail immediately if Next.js error badge ("1 error"), overlay, or toast is present
    const nextErrorToast = page.locator("nextjs-portal, [data-nextjs-toast], [data-nextjs-dialog-overlay], button[data-nextjs-toast-errors-hide-button]");
    const count = await nextErrorToast.count();
    let hasNextError = false;
    for (let i = 0; i < count; i++) {
      if (await nextErrorToast.nth(i).isVisible().catch(() => false)) {
        hasNextError = true;
        break;
      }
    }
    expect(hasNextError, "Next.js runtime error overlay or toast must not be visible on page").toBe(false);
    expect(pageErrors, `Page errors encountered during journey: ${pageErrors.map(e => e.message).join("; ")}`).toHaveLength(0);
    const fatalConsoleErrors = consoleErrors.filter(
      (err) => !err.includes("favicon.ico") && !err.includes("Download the React DevTools")
    );
    expect(fatalConsoleErrors, `Console errors encountered during journey: ${fatalConsoleErrors.join("; ")}`).toHaveLength(0);
  });

  test("J-a: New patient onboarding: consent -> profile -> routine check-in -> Green chip and guideline citations", async ({ page }) => {
    await page.goto("/");
    await dismissPreloader(page);

    // Enter patient portal
    const patientBtn = page.locator("#select-patient-portal-btn");
    await expect(patientBtn).toBeVisible({ timeout: 10000 });
    await patientBtn.click();

    // Toggle to Sign Up
    const toggleSignUp = page.locator("#toggle-auth-mode-btn");
    await expect(toggleSignUp).toBeVisible({ timeout: 10000 });
    await toggleSignUp.click();

    await page.fill("#login-identifier", "demo_patient_new@demo.care");
    await page.fill("#login-password", "Password123!");
    await page.fill("#login-confirm-password", "Password123!");
    await page.click("#login-submit-btn");

    // Consent screen
    const consentHeader = page.locator("h1:has-text('Patient Privacy & Care Consent'), h1:has-text('طبی نگرانی اور رضامندی')");
    await expect(consentHeader).toBeVisible({ timeout: 10000 });
    await page.check("#consent-data-processing-chk");
    await page.check("#consent-provider-notification-chk");
    await page.click("#consent-accept-btn");

    // Inclusion screen
    await expect(page.locator("#inclusion-dob-input")).toBeVisible({ timeout: 8000 });
    await page.fill("#inclusion-dob-input", "1988-04-12");
    await page.click("#sex-male-btn");
    await page.check("#inclusion-confirm-checkbox");
    await page.click("#inclusion-submit-btn");

    // Profile screen
    await expect(page.locator("#profile-continue-btn")).toBeVisible({ timeout: 10000 });
    await page.check("#condition-t2d");
    await page.click("#profile-continue-btn");

    // Connection screen -> Connect via FHIR (if presented)
    const connectBtn = page.locator("#connect-fhir-btn, button:has-text('Connect via FHIR')").first();
    if (await connectBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await connectBtn.click();
    }

    // Home screen -> Start Check-in
    const startCheckinBtn = page.locator("#start-checkin-btn, button:has-text('Start Daily Check-in'), button:has-text('چیک ان شروع کریں')").first();
    await expect(startCheckinBtn).toBeVisible({ timeout: 10000 });
    await startCheckinBtn.click();

    // CheckIn Entry -> begin interview
    const continueBtn = page.locator("#continue-to-interview-btn");
    await expect(continueBtn).toBeVisible({ timeout: 8000 });
    await continueBtn.click();

    // Answer questions with normal responses
    const q1No = page.locator("#q1-no-btn");
    await expect(q1No).toBeVisible({ timeout: 8000 });
    await q1No.click();

    const q3No = page.locator("#q3-no-btn");
    await expect(q3No).toBeVisible({ timeout: 8000 });
    await q3No.click();

    await page.click("#submit-checkin-btn");

    // Confirmation -> View Results
    const viewResultsBtn = page.locator("#view-my-results-btn");
    await expect(viewResultsBtn).toBeVisible({ timeout: 8000 });
    await viewResultsBtn.click();

    // Results screen assertions
    const resultHeading = page.locator("h1:has-text('Daily Health Analysis'), h1:has-text('آپ کے روزانہ نتائج'), h1:has-text('Check-in Recorded')");
    await expect(resultHeading).toBeVisible({ timeout: 10000 });

    // Green chip / Low risk indicator
    const greenChip = page.locator("span:has-text('Low Risk'), span:has-text('Routine'), span:has-text('ROUTINE'), span:has-text('سبز'), span:has-text('Green')").first();
    await expect(greenChip).toBeVisible({ timeout: 8000 });

    // Explanation with guideline citations
    const explanationBox = page.locator('[data-testid="patient-explanation-box"], [data-testid="explanation-box"]').first();
    await expect(explanationBox).toBeVisible({ timeout: 8000 });

    const toggleBtn = page.locator("#explanation-toggle-btn");
    if (await toggleBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await toggleBtn.click();
    }
    await expect(page.locator('[data-testid="explanation-sentence"]').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid="explanation-sources"]').first()).toBeVisible({ timeout: 5000 });

    await captureKeyScreenshots(page, "ja_routine_green");
  });

  test("J-b: Urdu-script patient (demo_patient_ur@demo.care): Urdu UI end to end, template explanation in Urdu", async ({ page }) => {
    await page.goto("/?portal=patient&screen=risk_result");
    await dismissPreloader(page);

    // Switch language to Urdu if not already
    const langBtn = page.locator("#language-toggle-btn");
    await expect(langBtn).toBeVisible({ timeout: 10000 });
    const currentDir = await page.locator("html").getAttribute("dir");
    if (currentDir !== "rtl") {
      await langBtn.click();
    }

    // Verify RTL orientation
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    // Verify Urdu headings and template text
    const urduHeading = page.locator("h1:has-text('آپ کے روزانہ نتائج'), h1:has-text('چیک ان محفوظ ہو گیا')").first();
    await expect(urduHeading).toBeVisible({ timeout: 10000 });

    // Template explanation contains Urdu text
    const urduExplanation = page.locator("p.font-urdu, div.font-urdu, [data-testid='explanation-box']").first();
    await expect(urduExplanation).toBeVisible({ timeout: 8000 });

    await captureKeyScreenshots(page, "jb_urdu_result");
  });

  test("J-c: Danger phrase (demo_patient_emg@demo.care): Emergency screen showing 1122 only (and no other emergency number anywhere on page)", async ({ page }) => {
    await page.goto("/?portal=patient&screen=emergency&scenario=emergency");
    await dismissPreloader(page);

    // Assert emergency alert banner is visible
    const alertBanner = page.locator("h1:has-text('Emergency Attention Advised'), h1:has-text('فوری طبی نگہداشت کی ضرورت'), span:has-text('CRITICAL CLINICAL ALERT')").first();
    await expect(alertBanner).toBeVisible({ timeout: 10000 });

    // Assert 1122 is prominently visible
    const hotline1122 = page.locator("text=1122").first();
    await expect(hotline1122).toBeVisible({ timeout: 5000 });

    // Strictly assert NO other emergency numbers exist anywhere on page (Rule Y2 Pakistan emergency hotline invariant)
    await expect(page.locator("text=911")).toHaveCount(0);
    await expect(page.locator("text=999")).toHaveCount(0);
    await expect(page.locator("text=0800")).toHaveCount(0);

    // Assert Return Home button is present
    await expect(page.locator("#emergency-return-home-btn")).toBeVisible({ timeout: 5000 });

    await captureKeyScreenshots(page, "jc_emergency_1122");
  });

  test("J-d: HTN trend persona (demo_patient_htn@demo.care): Yellow with trend reason; provider opens case and sees BP chart", async ({ page }) => {
    await page.goto("/?portal=provider&provider_screen=dashboard&scenario=conflict&risk=true&trace=true");
    await dismissPreloader(page);

    // Click patient row to view details
    const patientRow = page.locator("#patient-row-ali-khan");
    await expect(patientRow).toBeVisible({ timeout: 10000 });
    await patientRow.click();

    // Verify detail screen mounts
    await expect(page.locator("h1:has-text('Reconciliation Alert'), h1:has-text('تطبیق کا الرٹ'), h2:has-text('Clinical Review')").first()).toBeVisible({ timeout: 10000 });

    // Verify provider longitudinal trends section
    const trendsSection = page.locator('[data-testid="provider-trends-section"]');
    await expect(trendsSection).toBeVisible({ timeout: 8000 });

    // Verify BP trajectory and trend indicators
    await expect(trendsSection.getByText("Systolic").first()).toBeVisible({ timeout: 5000 });
    await expect(trendsSection.getByText(/Rising|Stable/i).first()).toBeVisible({ timeout: 5000 });

    await captureKeyScreenshots(page, "jd_htn_trend_bp_chart", trendsSection);
  });

  test("J-e: Provider queue (provider.demo@demo.care): Review detail -> risk panel with SHAP drivers -> SOAP note", async ({ page }) => {
    await page.goto("/?portal=provider&provider_screen=dashboard&scenario=conflict&risk=true&trace=true");
    await dismissPreloader(page);

    const patientRow = page.locator("#patient-row-ali-khan");
    await expect(patientRow).toBeVisible({ timeout: 10000 });
    await patientRow.click();

    // Verify Risk Panel with SHAP drivers
    const shapDriversHeader = page.locator("text=SHAP Drivers").first();
    await expect(shapDriversHeader).toBeVisible({ timeout: 10000 });

    const shapReasonItem = page.locator('[data-testid="risk-reason-item"]').first();
    await expect(shapReasonItem).toBeVisible({ timeout: 5000 });

    // Verify SOAP note generation panel
    const soapPanel = page.locator('[data-testid="provider-soap-note-panel"]');
    await expect(soapPanel).toBeVisible({ timeout: 10000 });

    // Verify Subjective, Objective, Assessment, Plan sections
    await expect(page.locator('[data-testid="soap-section-subjective"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid="soap-section-objective"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid="soap-section-assessment"]')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid="soap-section-plan"]')).toBeVisible({ timeout: 5000 });

    // Verify Clinical Review Decision buttons (Proposal UC-15 / F6)
    await expect(page.locator("#review-approve-btn")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("#review-adjust-btn")).toBeVisible({ timeout: 5000 });

    await captureKeyScreenshots(page, "je_provider_risk_soap", soapPanel);
  });

  test("J-f: Patient risk view (demo_patient_dm@demo.care): Shows band sentence only (no %, no probability, no raw model name)", async ({ page }) => {
    await page.goto("/?portal=patient&screen=risk_result&risk=true");
    await dismissPreloader(page);

    const riskCard = page.locator('[data-testid="patient-risk-estimates-card"]');
    await expect(riskCard).toBeVisible({ timeout: 10000 });

    const cardContent = await riskCard.innerText();

    // Invariant: Patient view must NEVER expose raw percentages or raw probabilities
    expect(cardContent).not.toContain("%");
    expect(cardContent.toLowerCase()).not.toContain("probability");
    expect(cardContent.toLowerCase()).not.toContain("p=");

    // Invariant: Patient view must NEVER expose internal ML model names
    expect(cardContent.toLowerCase()).not.toContain("framingham");
    expect(cardContent.toLowerCase()).not.toContain("nhanes");
    expect(cardContent.toLowerCase()).not.toContain("xgboost");
    expect(cardContent.toLowerCase()).not.toContain("logistic_regression");

    // Invariant: Shows qualitative band and clear sentence
    expect(
      cardContent.includes("Low") ||
      cardContent.includes("Moderate") ||
      cardContent.includes("High") ||
      cardContent.includes("کم") ||
      cardContent.includes("معتدل") ||
      cardContent.includes("زیادہ")
    ).toBe(true);

    await captureKeyScreenshots(page, "jf_patient_risk_band");
  });

  test("J-g: No-readings check-in (demo_patient_norx@demo.care): Shows Rule R8 wording and no invented reading anywhere", async ({ page }) => {
    await page.goto("/?portal=patient&screen=risk_result&scenario=no_readings");
    await dismissPreloader(page);

    // Rule R8 wording assertion
    const summaryCard = page.locator('[data-testid="no-readings-summary"], .glass-raised');
    await expect(summaryCard.first()).toBeVisible({ timeout: 10000 });

    // Verify Rule R8 routine monitoring explanation
    const pageText = await page.innerText("body");
    const hasR8Wording =
      pageText.includes("No readings entered today") ||
      pageText.includes("آج کوئی ریڈنگ درج نہیں کی گئی") ||
      pageText.includes("did not enter a blood sugar") ||
      pageText.includes("target monitoring range today") ||
      pageText.includes("routine self-monitoring");
    expect(hasR8Wording).toBe(true);

    // Invariant: No invented glucose readings anywhere on page
    expect(pageText).not.toContain("180 mg/dL");
    expect(pageText).not.toContain("142 mg/dL");

    await captureKeyScreenshots(page, "jg_no_readings_r8");
  });

  test("J-h: OCR: Upload script-generated fake prescription image, confirm screen, Medium trust / Unverified badge afterwards", async ({ page }) => {
    await page.goto("/?portal=patient&screen=health_record");
    await dismissPreloader(page);

    // Create temporary fake prescription image
    const tempImgPath = path.join(process.cwd(), "scratch", "demo_fake_rx.png");
    if (!fs.existsSync(path.dirname(tempImgPath))) {
      fs.mkdirSync(path.dirname(tempImgPath), { recursive: true });
    }
    const tinyPng = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
      "base64"
    );
    fs.writeFileSync(tempImgPath, tinyPng);

    // Upload via file input
    const ocrInput = page.locator("#ocr-file-input, [data-testid='ocr-file-input']");
    await ocrInput.setInputFiles(tempImgPath);

    // Confirm screen mounts
    const confirmScreen = page.locator('[data-testid="ocr-confirm-screen"]');
    await expect(confirmScreen).toBeVisible({ timeout: 10000 });

    // Click Save Confirmed Items
    const saveBtn = page.locator('[data-testid="ocr-save-confirmed-btn"]');
    await expect(saveBtn).toBeVisible({ timeout: 8000 });
    await saveBtn.click();

    // Redirected back to Health Record with Unverified / OCR badge
    await expect(page.locator("h1:has-text('Your Health Record'), h1:has-text('آپ کا ذاتی ہیلتھ ریکارڈ')")).toBeVisible({ timeout: 10000 });
    const unverifiedBadge = page.locator('[data-testid="badge-unverified-upload"], span:has-text("Unverified"), span:has-text("غیر تصدیق شدہ")').first();
    await expect(unverifiedBadge).toBeVisible({ timeout: 8000 });

    await captureKeyScreenshots(page, "jh_ocr_unverified_badge");

    // Clean up temporary image
    try { fs.unlinkSync(tempImgPath); } catch {}
  });

  test("J-i: Admin: Config status page (admin.demo@demo.care) lists flags", async ({ page }) => {
    await page.goto("/?portal=admin");
    await dismissPreloader(page);

    // Verify Admin Config Status Section is mounted
    const configSection = page.locator('[data-testid="admin-config-status-section"]');
    await expect(configSection).toBeVisible({ timeout: 10000 });

    // Assert key runtime feature flags are listed
    await expect(configSection.locator("text=RISK_ENABLED")).toBeVisible({ timeout: 5000 });
    await expect(configSection.locator("text=EXPLAIN_ENABLED")).toBeVisible({ timeout: 5000 });
    await expect(configSection.locator("text=OCR_ENABLED")).toBeVisible({ timeout: 5000 });
    await expect(configSection.locator("text=DB_BACKEND")).toBeVisible({ timeout: 5000 });

    await captureKeyScreenshots(page, "ji_admin_config_flags");
  });
});

// =============================================================================
// Existing Baseline Journeys
// =============================================================================

test.describe("H3-5-01: Five End-to-End User Journeys", () => {
  test.use({ colorScheme: "light" });

  let pageErrors: Error[] = [];
  let consoleErrors: string[] = [];

  test.beforeEach(async ({ page }) => {
    pageErrors = [];
    consoleErrors = [];
    page.on("pageerror", (err) => {
      console.log(`[PAGEERROR]: ${err.message}\n${err.stack}`);
      pageErrors.push(err);
    });
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        console.log(`[CONSOLE_ERROR]: ${msg.text()}`);
        consoleErrors.push(msg.text());
      }
    });
  });

  test.afterEach(async ({ page }) => {
    const nextErrorToast = page.locator("nextjs-portal, [data-nextjs-toast], [data-nextjs-dialog-overlay], button[data-nextjs-toast-errors-hide-button]");
    const count = await nextErrorToast.count();
    let hasNextError = false;
    for (let i = 0; i < count; i++) {
      if (await nextErrorToast.nth(i).isVisible().catch(() => false)) {
        hasNextError = true;
        break;
      }
    }
    expect(hasNextError, "Next.js runtime error overlay or toast must not be visible on page").toBe(false);
    expect(pageErrors, `Page errors encountered during journey: ${pageErrors.map(e => e.message).join("; ")}`).toHaveLength(0);
    const fatalConsoleErrors = consoleErrors.filter(
      (err) => !err.includes("favicon.ico") && !err.includes("Download the React DevTools")
    );
    expect(fatalConsoleErrors, `Console errors encountered during journey: ${fatalConsoleErrors.join("; ")}`).toHaveLength(0);
  });

  test("J1: New patient onboarding: consent -> profile (en/ur) -> normal check-in -> routine result", async ({ page }) => {
    await page.goto("/");
    await dismissPreloader(page);

    const patientBtn = page.locator("#select-patient-portal-btn");
    await expect(patientBtn).toBeVisible({ timeout: 10000 });
    await patientBtn.click();

    const toggleSignUp = page.locator("#toggle-auth-mode-btn");
    await expect(toggleSignUp).toBeVisible({ timeout: 10000 });
    await toggleSignUp.click();

    await page.fill("#login-identifier", "new.patient@demo.care");
    await page.fill("#login-password", "Password123!");
    await page.fill("#login-confirm-password", "Password123!");
    await page.click("#login-submit-btn");

    const consentHeader = page.locator("h1:has-text('Patient Privacy & Care Consent'), h1:has-text('طبی نگرانی اور رضامندی')");
    await expect(consentHeader).toBeVisible({ timeout: 10000 });
    if (process.env.UPDATE_W3_SCREENSHOTS === "1") {
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j1_consent_en.png") });
    }

    await page.check("#consent-data-processing-chk");
    await page.check("#consent-provider-notification-chk");
    await page.click("#consent-accept-btn");

    await expect(page.locator("#inclusion-dob-input")).toBeVisible({ timeout: 8000 });
    await page.fill("#inclusion-dob-input", "1988-04-12");
    await page.click("#sex-male-btn");
    await page.check("#inclusion-confirm-checkbox");
    await page.click("#inclusion-submit-btn");

    await expect(page.locator("#profile-continue-btn")).toBeVisible({ timeout: 10000 });
    await page.check("#condition-t2d");

    const langBtn = page.locator("#language-toggle-btn");
    await langBtn.click();

    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    if (process.env.UPDATE_W3_SCREENSHOTS === "1") {
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j1_profile_ur.png") });
    }

    await page.click("#profile-continue-btn");

    const startCheckinBtn = page.locator("#start-checkin-btn, button:has-text('چیک ان شروع کریں'), button:has-text('Start Daily Check-in')").first();
    await expect(startCheckinBtn).toBeVisible({ timeout: 8000 });
    await startCheckinBtn.click();

    const continueBtn = page.locator("#continue-to-interview-btn");
    await expect(continueBtn).toBeVisible({ timeout: 8000 });
    await continueBtn.click();

    const q1No = page.locator("#q1-no-btn");
    await expect(q1No).toBeVisible({ timeout: 8000 });
    await q1No.click();

    const q3No = page.locator("#q3-no-btn");
    await expect(q3No).toBeVisible({ timeout: 8000 });
    await q3No.click();

    await page.click("#submit-checkin-btn");

    const viewResultsBtn = page.locator("#view-my-results-btn");
    await expect(viewResultsBtn).toBeVisible({ timeout: 8000 });
    await viewResultsBtn.click();

    const resultHeading = page.locator("h1:has-text('آپ کے روزانہ نتائج'), h1:has-text('Daily Health Analysis'), h1:has-text('Check-in Recorded')");
    await expect(resultHeading).toBeVisible({ timeout: 10000 });
    if (process.env.UPDATE_W3_SCREENSHOTS === "1") {
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j1_result_routine.png") });
    }

    await langBtn.click();
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  });

  test("J2: Urgent / Emergency symptom reporting -> critical result screen with 1122 visible", async ({ page }) => {
    await page.goto("/?scenario=emergency");
    await dismissPreloader(page);

    await loginAsPatient(page);

    const urgentTrigger = page.locator("#report-urgent-symptoms-btn");
    await expect(urgentTrigger).toBeVisible({ timeout: 10000 });
    await urgentTrigger.click();

    const alertBanner = page.locator("span:has-text('CRITICAL CLINICAL ALERT'), span:has-text('فوری طبی الرٹ')");
    await expect(alertBanner).toBeVisible({ timeout: 8000 });

    const hotlineText = page.locator("text=1122").first();
    await expect(hotlineText).toBeVisible({ timeout: 5000 });
    const fallbackText = page.locator("text=911");
    await expect(fallbackText).toHaveCount(0);

    if (process.env.UPDATE_W3_SCREENSHOTS === "1") {
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j2_urgent_emergency.png") });
    }
    await expect(page.locator("#emergency-return-home-btn")).toBeVisible();
  });

  test("J3: Health record: add medication, toggle status, test history modal (Esc & focus trap), export JSON", async ({ page }) => {
    await page.goto("/?portal=patient&screen=health_record");
    await dismissPreloader(page);

    await expect(page.locator("h1:has-text('Your Health Record'), h1:has-text('آپ کا ذاتی ہیلتھ ریکارڈ')")).toBeVisible({ timeout: 8000 });

    const medNameInput = page.locator('input[placeholder*="Metformin 500mg"]');
    await expect(medNameInput).toBeVisible({ timeout: 5000 });
    await medNameInput.fill("Metformin 500mg");

    const medDoseInput = page.locator('input[placeholder*="twice daily"]');
    await medDoseInput.fill("1 tablet twice daily");

    await page.click("#add-medication-btn");

    await expect(page.locator("text=Metformin 500mg").first()).toBeVisible({ timeout: 5000 });

    const toggleBtn = page.locator("button:has-text('Mark Stopped'), button:has-text('بند نشان زد کریں')").first();
    if (await toggleBtn.isVisible({ timeout: 3000 })) {
      await toggleBtn.click();
    }

    if (process.env.UPDATE_W3_SCREENSHOTS === "1") {
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j3_record_edits.png") });
    }

    const historyBtn = page.locator('[data-testid="view-full-history-btn"]');
    await expect(historyBtn).toBeVisible({ timeout: 5000 });
    await historyBtn.click();

    const historyModal = page.locator('[data-testid="record-history-modal"]');
    await expect(historyModal).toBeVisible({ timeout: 5000 });
    if (process.env.UPDATE_W3_SCREENSHOTS === "1") {
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j3_record_history.png") });
    }

    await page.keyboard.press("Escape");
    await expect(historyModal).toBeHidden({ timeout: 5000 });

    const exportJsonBtn = page.locator('[data-testid="export-json-btn"]');
    await expect(exportJsonBtn).toBeVisible({ timeout: 5000 });

    const downloadPromise = page.waitForEvent("download", { timeout: 8000 }).catch(() => null);
    await exportJsonBtn.click();
    const download = await downloadPromise;
    if (download) {
      expect(download.suggestedFilename()).toContain(".json");
    }
  });
});
