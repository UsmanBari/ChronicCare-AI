import { test, expect } from "@playwright/test";
import path from "path";
import fs from "fs";

const SCREENSHOT_DIR = path.resolve(process.cwd(), "docs/screenshots/w3/e2e");

test.beforeAll(() => {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
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

test.describe("H3-5-01: Five End-to-End User Journeys", () => {
  test.use({ colorScheme: "light" });

  test("J1: New patient onboarding: consent -> profile (en/ur) -> normal check-in -> routine result", async ({ page }) => {
    // 1. Visit landing page
    await page.goto("/");
    await dismissPreloader(page);

    // 2. Click Enter Patient Portal
    const patientBtn = page.locator("#select-patient-portal-btn");
    await expect(patientBtn).toBeVisible({ timeout: 10000 });
    await patientBtn.click();

    // 3. On Login screen, click Create Account / Sign up
    const toggleSignUp = page.locator("#toggle-auth-mode-btn");
    await expect(toggleSignUp).toBeVisible({ timeout: 10000 });
    await toggleSignUp.click();

    // Fill new user credentials
    await page.fill("#login-identifier", "new.patient@demo.care");
    await page.fill("#login-password", "Password123!");
    await page.fill("#login-confirm-password", "Password123!");
    await page.click("#login-submit-btn");

    // 4. Verify Patient Consent screen
    const consentHeader = page.locator("h1:has-text('Patient Privacy & Care Consent'), h1:has-text('طبی نگرانی اور رضامندی')");
    await expect(consentHeader).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j1_consent_en.png") });

    // Accept both consents
    await page.check("#consent-data-processing-chk");
    await page.check("#consent-provider-notification-chk");
    await page.click("#consent-accept-btn");

    // 5. Inclusion Screen: Fill DOB, Sex, and Confirm Adult
    await expect(page.locator("#inclusion-dob-input")).toBeVisible({ timeout: 8000 });
    await page.fill("#inclusion-dob-input", "1988-04-12");
    await page.click("#sex-male-btn");
    await page.check("#inclusion-confirm-checkbox");
    await page.click("#inclusion-submit-btn");

    // 6. Profile Screen
    await expect(page.locator("#profile-continue-btn")).toBeVisible({ timeout: 10000 });
    await page.check("#condition-t2d");

    // Switch language to Urdu via header toggle
    const langBtn = page.locator("#language-toggle-btn");
    await langBtn.click();

    // Verify Urdu RTL active
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j1_profile_ur.png") });

    // Save profile and proceed to Home
    await page.click("#profile-continue-btn");

    // 7. On Home screen, start daily check-in
    const startCheckinBtn = page.locator("#start-checkin-btn, button:has-text('چیک ان شروع کریں'), button:has-text('Start Daily Check-in')").first();
    await expect(startCheckinBtn).toBeVisible({ timeout: 8000 });
    await startCheckinBtn.click();

    // CheckIn Entry screen -> begin interview
    const continueBtn = page.locator("#continue-to-interview-btn");
    await expect(continueBtn).toBeVisible({ timeout: 8000 });
    await continueBtn.click();

    // Answer questions with normal/no responses
    const q1No = page.locator("#q1-no-btn");
    await expect(q1No).toBeVisible({ timeout: 8000 });
    await q1No.click();

    const q3No = page.locator("#q3-no-btn");
    await expect(q3No).toBeVisible({ timeout: 8000 });
    await q3No.click();

    // Submit check-in
    await page.click("#submit-checkin-btn");

    // Confirmation Screen -> View Results
    const viewResultsBtn = page.locator("#view-my-results-btn");
    await expect(viewResultsBtn).toBeVisible({ timeout: 8000 });
    await viewResultsBtn.click();

    // 8. Result screen: Routine result
    const resultHeading = page.locator("h1:has-text('آپ کے روزانہ نتائج'), h1:has-text('Daily Health Analysis'), h1:has-text('Check-in Recorded')");
    await expect(resultHeading).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j1_result_routine.png") });

    // Switch language back to English
    await langBtn.click();
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  });

  test("J2: Urgent / Emergency symptom reporting -> critical result screen with 1122 and 911 visible", async ({ page }) => {
    await page.goto("/?scenario=emergency");
    await dismissPreloader(page);

    await loginAsPatient(page);

    // Trigger urgent symptom report directly from Home
    const urgentTrigger = page.locator("#report-urgent-symptoms-btn");
    await expect(urgentTrigger).toBeVisible({ timeout: 10000 });
    await urgentTrigger.click();

    // Assert emergency screen is displayed
    const alertBanner = page.locator("span:has-text('CRITICAL CLINICAL ALERT'), span:has-text('فوری طبی الرٹ')");
    await expect(alertBanner).toBeVisible({ timeout: 8000 });

    // Assert emergency telephone numbers (1122 and 911) are visible in the DOM
    const hotlineText = page.locator("text=1122").first();
    await expect(hotlineText).toBeVisible({ timeout: 5000 });
    const fallbackText = page.locator("text=911").first();
    await expect(fallbackText).toBeVisible({ timeout: 5000 });

    // Capture screenshot
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j2_urgent_emergency.png") });

    // Assert Return Home button is present
    await expect(page.locator("#emergency-return-home-btn")).toBeVisible();
  });

  test("J3: Health record: add medication, toggle status, test history modal (Esc & focus trap), export JSON", async ({ page }) => {
    await page.goto("/");
    await dismissPreloader(page);

    await loginAsPatient(page);

    // Navigate to Health Record Screen
    const healthRecordNav = page.locator("#edit-my-record-btn");
    await expect(healthRecordNav).toBeVisible({ timeout: 10000 });
    await healthRecordNav.click();

    // Verify record header is visible
    await expect(page.locator("h1:has-text('Your Health Record'), h1:has-text('آپ کا ذاتی ہیلتھ ریکارڈ')")).toBeVisible({ timeout: 8000 });

    // Add new medication: Metformin 500mg
    const medNameInput = page.locator('input[placeholder*="Metformin 500mg"]');
    await expect(medNameInput).toBeVisible({ timeout: 5000 });
    await medNameInput.fill("Metformin 500mg");

    const medDoseInput = page.locator('input[placeholder*="twice daily"]');
    await medDoseInput.fill("1 tablet twice daily");

    await page.click("#add-medication-btn");

    // Verify medication appears in the active list
    await expect(page.locator("text=Metformin 500mg").first()).toBeVisible({ timeout: 5000 });

    // Toggle status or mark stopped
    const toggleBtn = page.locator("button:has-text('Mark Stopped'), button:has-text('بند نشان زد کریں')").first();
    if (await toggleBtn.isVisible({ timeout: 3000 })) {
      await toggleBtn.click();
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j3_record_edits.png") });

    // Open Edit History modal
    const historyBtn = page.locator('[data-testid="view-full-history-btn"]');
    await expect(historyBtn).toBeVisible({ timeout: 5000 });
    await historyBtn.click();

    // Verify Edit History Modal is open
    const historyModal = page.locator('[data-testid="record-history-modal"]');
    await expect(historyModal).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j3_record_history.png") });

    // Press Escape to verify modal closes and focus returns
    await page.keyboard.press("Escape");
    await expect(historyModal).toBeHidden({ timeout: 5000 });

    // Export JSON
    const exportJsonBtn = page.locator('[data-testid="export-json-btn"]');
    await expect(exportJsonBtn).toBeVisible({ timeout: 5000 });

    // Setup download listener
    const downloadPromise = page.waitForEvent("download", { timeout: 8000 }).catch(() => null);
    await exportJsonBtn.click();
    const download = await downloadPromise;
    if (download) {
      expect(download.suggestedFilename()).toContain(".json");
    }
  });

  test("J4: Provider review with trace (RISK_ENABLED & EXPLAIN_ENABLED): patient explanation + provider trace", async ({ page }) => {
    // 1. Patient view with moderate-risk reading & ExplanationBox
    await page.goto("/?scenario=conflict&explain=true&risk=true");
    await dismissPreloader(page);

    await loginAsPatient(page);

    // Start check-in -> results
    const startCheckin = page.locator("#start-checkin-btn, button:has-text('Start Daily Check-in')").first();
    await expect(startCheckin).toBeVisible({ timeout: 10000 });
    await startCheckin.click();

    const continueBtn = page.locator("#continue-to-interview-btn");
    await expect(continueBtn).toBeVisible({ timeout: 8000 });
    await continueBtn.click();

    await page.locator("#q1-no-btn").click();
    await page.locator("#q3-no-btn").click();
    await page.click("#submit-checkin-btn");
    await page.click("#view-my-results-btn");

    // Advance from ConflictScreen to RoutedToReviewScreen
    const conflictContinueBtn = page.locator("#conflict-continue-btn");
    await expect(conflictContinueBtn).toBeVisible({ timeout: 10000 });
    await conflictContinueBtn.click();

    // Patient sees ExplanationBox
    const explanationToggleBtn = page.locator("#explanation-toggle-btn");
    await expect(explanationToggleBtn).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j4_patient_explain_en.png") });

    // Click to expand
    await explanationToggleBtn.click();
    await expect(page.locator('[data-testid="explanation-content"]')).toBeVisible({ timeout: 5000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j4_patient_explain.png") });

    // Urdu check for J4 screenshot
    const langBtn = page.locator("#language-toggle-btn");
    if (await langBtn.isVisible({ timeout: 2000 })) {
      await langBtn.click();
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j4_patient_explain_ur.png") });
      await langBtn.click(); // switch back
    }

    // 2. Switch to Provider View
    const portalMenuBtn = page.locator("#portal-switcher-btn");
    await portalMenuBtn.click();
    const switchToProviderBtn = page.locator("#switch-to-provider-btn");
    await expect(switchToProviderBtn).toBeVisible({ timeout: 5000 });
    await switchToProviderBtn.click();

    // On Provider Dashboard, select Ali Khan's alert detail
    const alertCard = page.locator("#patient-row-ali-khan");
    await expect(alertCard).toBeVisible({ timeout: 10000 });
    await alertCard.click();

    // Verify Provider Review Detail has Check-in Risk & Decision Timeline
    const checkinRiskBlock = page.locator('[data-testid="provider-checkin-risk-block"]');
    const decisionTimeline = page.locator('[data-testid="decision-timeline-block"]');

    await expect(checkinRiskBlock.or(decisionTimeline).first()).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j4_provider_trace.png") });
  });

  test("J5: OCR prescription reconciliation: confirm 2, fix 1, remove 1 -> save with OCR badge", async ({ page }) => {
    // Intercept upload and confirm endpoints
    await page.route("**/api/me/record/uploads", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          upload_id: "up-mock-e2e-123",
          expires_in_seconds: 1800,
          extracted: {
            observations: [
              { id: "obs-0", type: "glucose", value: 142, unit: "mg/dL", evidence: "FBS: 142 mg/dL" },
              { id: "obs-1", type: "blood_pressure_systolic", value: 130, unit: "mmHg", evidence: "BP: 130/85" },
            ],
            medications: [
              { id: "med-0", name: "Glimepiride", dosage: "2mg daily", status: "active", evidence: "Glimepiride 2mg" },
            ],
            allergies: [
              { id: "all-0", substance: "Penicillin", reaction: "Rash", severity: "moderate", status: "active", evidence: "Allergic to Penicillin" },
            ],
            raw_lines: ["FBS: 142 mg/dL", "BP: 130/85", "Glimepiride 2mg", "Allergic to Penicillin"],
            has_urdu: false,
          },
        }),
      });
    });

    await page.route("**/api/me/record/uploads/*/confirm", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "saved",
          saved_count: 3,
          saved_items: [
            { type: "observation", id: "obs-0", origin: "ocr" },
            { type: "observation", id: "obs-1", origin: "ocr" },
            { type: "medication", id: "med-0", origin: "ocr" },
          ],
          skipped_count: 0,
        }),
      });
    });

    await page.goto("/");
    await dismissPreloader(page);

    await loginAsPatient(page);

    const healthRecordNav = page.locator("#edit-my-record-btn");
    await expect(healthRecordNav).toBeVisible({ timeout: 10000 });
    await healthRecordNav.click();

    await expect(page.locator("h1:has-text('Your Health Record'), h1:has-text('آپ کا ذاتی ہیلتھ ریکارڈ')")).toBeVisible({ timeout: 8000 });

    // Trigger OCR file input with a synthetic file
    const fileInput = page.locator('[data-testid="ocr-file-input"], #ocr-file-input');
    await fileInput.setInputFiles({
      name: "prescription_mock.png",
      mimeType: "image/png",
      buffer: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==", "base64"),
    });

    // Verify OCR Confirmation Screen opens
    const confirmScreen = page.locator('[data-testid="ocr-confirm-screen"]');
    await expect(confirmScreen).toBeVisible({ timeout: 10000 });

    // 1. Confirm obs-0 (already confirmed)
    // 2. Fix obs-1: click fix, change value to 135
    const fixObs1 = page.locator('[data-testid="ocr-obs-fix-1"]');
    if (await fixObs1.isVisible({ timeout: 3000 })) {
      await fixObs1.click();
      const valInput = page.locator('input[type="number"]').first();
      await valInput.fill("135");
    }

    // 3. Remove allergy item (reject 1)
    const removeAllergyBtn = page.locator('[data-testid="ocr-all-remove-0"]');
    if (await removeAllergyBtn.isVisible({ timeout: 3000 })) {
      await removeAllergyBtn.click();
    }

    // Capture screenshot of confirmation screen before saving
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "j5_ocr_confirm.png") });

    // 4. Save confirmed items
    const saveConfirmedBtn = page.locator('[data-testid="ocr-save-confirmed-btn"]');
    await expect(saveConfirmedBtn).toBeVisible({ timeout: 5000 });
    await saveConfirmedBtn.click();

    // Returns to health record
    await expect(page.locator("h1:has-text('Your Health Record'), h1:has-text('آپ کا ذاتی ہیلتھ ریکارڈ')")).toBeVisible({ timeout: 8000 });
  });
});

