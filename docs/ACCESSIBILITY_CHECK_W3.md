# Week 3 Accessibility & Responsive Audit (9 Screens)

**Date**: Friday 6 November 2026  
**Auditor**: Hassaan (Day 5, I3)  
**Tools**: `@axe-core/playwright` (WCAG 2.1 AA ruleset), Playwright 1.65 Chromium headless, keyboard tab order analysis, mobile 360 px viewport overflow evaluation.  
**Execution Command**: `npm run test:e2e` (hermetic, offline).

---

## 1. Summary of Results Across 9 Screens

| # | Screen | axe-core Violations (Crit / Ser / Mod) | Keyboard Nav | Screen Reader | Touch Targets $\ge 44\text{px}$ | RTL Support | 360 px Overflow | Overall Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Patient Consent Screen** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:102`, `j1_consent_en.png` |
| 2 | **Health Profile Screen** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:146`, `j1_profile_ur.png` |
| 3 | **Adaptive Interview Screen** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:178` |
| 4 | **Routine Result Screen (+ ExplanationBox)** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:203`, `j1_result_routine.png` |
| 5 | **Urgent / Emergency Result Screen** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:231`, `j2_urgent_emergency.png` |
| 6 | **Health Record Screen (+ Edit History Modal)** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:259`, `j3_record_edits.png`, `j3_record_history.png` |
| 7 | **Provider Review List** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:300` |
| 8 | **Provider Review Detail (+ Trace & Risk)** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:325`, `j4_provider_trace.png` |
| 9 | **OCR Confirmation Screen** | 0 / 0 / 0 | PASS | PASS | PASS | PASS | PASS (no overflow) | **PASS** | `tests-e2e/accessibility.playwright.ts:358`, `j5_ocr_confirm.png` |

---

## 2. Issues Found and Remediated During Audit

During initial axe-core testing, 4 critical accessibility issues were detected on legacy markup and resolved directly on `test/i3-e2e-a11y`:

1. **`HealthProfileScreen.tsx` (Screen 2)**:
   - *Violation*: `select-name` (Select element must have an accessible name) on `#smoking-status-select`.
   - *Fix*: Connected `<label htmlFor="smoking-status-select">` and added explicit localized `aria-label={isUrdu ? "تمباکو نوشی کی کیفیت" : "Smoking Status"}`.
2. **`HealthRecordScreen.tsx` (Screen 6)**:
   - *Violation*: `select-name` on `#med-status-select`.
   - *Fix*: Added `id="med-status-select"`, `<label htmlFor="med-status-select">`, and `aria-label="Medication status"`.
3. **`HealthRecordScreen.tsx` (Screen 6)**:
   - *Violation*: `select-name` on observation type dropdown and missing `label` association on observation datetime input (`type="datetime-local"`).
   - *Fix*: Added explicit `htmlFor` / `id` bindings (`obs-type-select`, `obs-measured-at-input`) and `aria-label` attributes (`"Observation type"`, `"Observation date and time"`).
4. **`ReconciliationAlertDetail.tsx` (Screen 8)**:
   - *Violation*: `button-name` (discernible text) on `#reconciliation-back-btn`.
   - *Fix*: Added localized `aria-label={isUrdu ? "واپس جائیں" : "Back to review queue"}`.

All 4 fixes are verified in `tests-e2e/accessibility.playwright.ts` and confirmed at 0 critical and 0 serious violations.

---

## 3. Keyboard & Screen Reader Verification

- **Tab Traversal**: No focus traps were observed in any screen. Modals (`record-history-modal`) trap focus internally while open and restore focus cleanly to the trigger element on close.
- **Escape Key**: Pressing `Escape` closes the History modal and returns focus to `[data-testid="view-full-history-btn"]`.
- **Expandable Accordion**: `ExplanationBox` (`#explanation-toggle-btn`) exposes `aria-expanded="true|false"` and responds to both `Enter` and `Space`.
- **Emergency Telephony**: Verified emergency hotlines (`1122` and `911`) are prominent and accessible to assistive technology.

---

## 4. Mobile Responsiveness (360 px Viewport)

- Evaluated using `page.setViewportSize({ width: 360, height: 800 })`.
- `document.documentElement.scrollWidth <= window.innerWidth + 2` passed on all 9 screens (no horizontal scrollbar or element truncation).
- Interactive touch targets adhere to WCAG 2.5.5 / 2.5.8 recommendations ($\ge 44 \times 44\text{ px}$).

---

## 5. End-to-End User Journey Audit (H3-5-01)

| Journey | Status | Outcome / Reason |
|---|---|---|
| **J1: Onboarding -> Routine Result** | **RUN & PASS** | Complete flow: Consent -> Profile (EN/UR) -> Check-in -> Routine Result verified. |
| **J2: Urgent Emergency Reporting** | **RUN & PASS** | Complete flow: Urgent trigger from Home -> Critical Alert screen with emergency hotlines 1122 & 911 visible. |
| **J3: Health Record Management** | **RUN & PASS** | Complete flow: Add medication -> Toggle active/stopped -> Edit History modal (Esc key & focus trap) -> JSON Export download. |
| **J4: Provider Review with Trace** | **NOT RUN (Live System)** | Requires end-to-end Firebase authentication session tokens to complete check-in against live backend `/api/checkins/start` and `/api/checkins/.../complete`. In offline hermetic testing without live Firebase credentials, live backend returns 401/503. Demo screen accessibility is independently audited in Screen 8. |
| **J5: OCR Prescription Reconciliation** | **NOT RUN (Live System without Mocks)** | `POST /api/me/record/uploads` enforces `require_role('patient')`, returning 401 Unauthorized in offline environment without cloud Firebase credentials. Per safety review, fake route intercepts were removed. Screen accessibility is independently audited in Screen 9. |

---

## 6. Demo Mocks Maintained for Offline / Demo Presentation

Per PR #119 instructions, client-side fallback mocks are strictly isolated to presenter/demo mode (which displays the banner `"DEMO — DATA NOT REAL"`):
1. **Demo Baseline Profile**: Fallback conditions/medications when `!isLiveMode` (`AppContext.tsx`).
2. **Demo Record Edit History**: Preset synthetic edit history items when `!isLiveMode` (`HealthRecordScreen.tsx`).
3. **Demo Record Export**: JSON blob export generated client-side from staged state when `!isLiveMode` (`HealthRecordScreen.tsx`).
4. **Demo Provider Review Detail**: Synthetic review case for Ali Khan with label `"Demo example (not real guidance)"`, empty citations, and empty sources (`ReconciliationAlertDetail.tsx`).
