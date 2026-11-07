# Weekly Engineering Log: Week 45 (Iteration 3)

**Engineer:** Hassaan Mudassar (Frontend & Integration Engineer)  
**Period:** Monday 2 November 2026 – Sunday 8 November 2026  
**Branch / Target:** `docs/i3-user-guide-final` -> `dev` (PR #127)  

---

## 1. Executive Summary

During Week 45, engineering efforts finalized Iteration 3 ("Features Done") across four primary domains:
1. **Explainability & Risk UI (I3-Patient & Provider):** Built the patient-facing Explanation Box and Provider Review Detail panels (Live vs. Check-in Risk Tiering, Decision Timeline, and Audit Trail) with strict flag gating (`RISK_ENABLED=false`, `EXPLAIN_ENABLED=false`).
2. **Clinical Interview v3 Readiness (I3-Interview):** Closed readiness blockers G-02 and G-14, ensuring strict INCOMPLETE handling on drop-off, eliminating caregiver yes/no leaks, and produced the readiness report: NO-GO, v2 stays default (`docs/V3_READINESS.md`).
3. **End-to-End Testing & Accessibility (I3-A11y & E2E):** Authored Playwright E2E journeys covering 5 key flows and executed a 9-screen WCAG 2.1 AA accessibility audit (100% compliant across contrast, discernible names, and mobile viewports; `docs/ACCESSIBILITY_CHECK_W3.md`).
4. **OCR Worker Hardening & Memory Isolation (I3-OCR):** Redesigned the OCR architecture to run RapidOCR in an isolated worker subprocess (`OCR_USE_SUBPROCESS=true`), hardened extraction on 5 script-generated synthetic lab layouts (+2 generated held-out) achieving 15/15 recall on dev and 6/6 on held-out, and characterized true Linux container memory limits.
5. **Documentation & Native Urdu Polish:** Authored the comprehensive User Guide (`docs/USER_GUIDE.md`) with 11 real UI screenshots, and conducted the native-speaker linguistic audit of all 158 frontend interface strings and 28 message catalog items.

---

## 2. Daily Engineering Deliverables & Landed PRs

### PR Tracking Reference
PR numbers traced from repository git merge history on `origin/dev` and current active branch:

| PR # | Branch | Description / Status |
|---|---|---|
| **#104** | `fix/i3-bugbash-h` | Bug bash fixes & observation input card mmol/L conversion (Merged) |
| **#108** | `feat/i3-patient-risk-explain-ui` | Patient explanation box with strict doctor-only risk suppression (Merged) |
| **#109** | `feat/i3-provider-trace-ui` | Provider review detail, check-in risk snapshot, decision timeline (Merged) |
| **#113** | `feat/i3-v3-readiness` | Interview v3 readiness gaps G-02 & G-14, 64-persona audit (Merged) |
| **#119** | `test/i3-e2e-a11y` | Hermetic Playwright 5 journeys, 9-screen WCAG 2.1 AA audit (Merged) |
| **#122** | `feat/i3-ocr-hardening` | OCR worker memory isolation and synthetic PK lab layout hardening (Merged) |
| **#127** | `docs/i3-user-guide-final` | User guide, final Urdu review, and weekly log (Current PR) |

*(Note: `gh pr list --author "@me"` failed locally due to CLI authentication requirement; all PR numbers above are traced directly from `git log origin/dev --grep="Merge pull request"` commit references).*

### Day 1 (Mon 2 Nov) — Bug Bash Remediation & Danger Word Groups
- **Deliverables:** Fixed UI edge cases identified during cross-team bug bash, updated observation input card unit label conversion for mmol/L, and supported danger word group safety banner integration.
- **PR:** #104 (`fix/i3-bugbash-h`, Merged into `dev`).

### Day 2 (Tue 3 Nov) — Patient Risk Card & Explanation Box UI
- **Deliverables:** Built `ExplanationBox.tsx` and updated `RiskResultScreen.tsx`. Maintained strict doctor-only risk suppression on the patient portal, displaying only vetted, 2–3 sentence non-prescriptive lifestyle explanations with medical literature citations (DOI links) behind feature flags.
- **PR:** #108 (`feat/i3-patient-risk-explain-ui`, Merged into `dev`).

### Day 3 (Wed 4 Nov) — Provider Decision Trace & Check-in Risk Panel
- **Deliverables:** Implemented Provider Review Detail screen enhancements: Live Risk vs Check-in Risk snapshot comparison, orchestration Decision Timeline (graph/direct pipeline execution trace), and recent record edit audit log.
- **PR:** #109 (`feat/i3-provider-trace-ui`, Merged into `dev`).

### Day 4 (Thu 5 Nov) — Interview v3 Readiness Gaps G-02 & G-14
- **Deliverables:** Resolved G-14 safety drop-off handling (marking abandoned check-ins strictly INCOMPLETE without down-triaging), fixed caregiver yes/no leakage, updated doctor probe audit, and generated the dynamic 64-persona readiness verification report resulting in recommendation NO-GO (v2 remains default).
- **PR:** #113 (`feat/i3-v3-readiness`, Merged into `dev`).

### Day 5 (Fri 6 Nov) — Playwright E2E Suite & 9-Screen WCAG 2.1 AA Audit
- **Deliverables:** Authored hermetic Playwright journeys (J1–J3 demo runs; J4–J5 authenticated live specs documented). Audited 9 application screens using `@axe-core/playwright` and manual checks, resolving form control label bindings, color contrast ratios (all >= 4.5:1), discernible back-button names, and 375px mobile viewport overflow. Emergency number asserted strictly 1122.
- **PR:** #119 (`test/i3-e2e-a11y`, Merged into `dev`).

### Day 6 (Sat 7 Nov) — OCR Subprocess Memory Isolation & Synthetic Lab Layout Hardening
- **Deliverables:** Implemented spawn subprocess worker pattern (`OCR_USE_SUBPROCESS=true`) in `rapidocr_provider.py` with `OCR_SUBPROCESS_TIMEOUT` (default 30.0s) and multiprocessing Queue to isolate inference memory and allow immediate OS memory reclamation upon worker process exit. Hardened regex patterns in `extract_fields.py` for 5 script-generated synthetic lab layouts (+2 generated held-out), achieving 15/15 recall on development layouts and 6/6 on held-out tests. Measured Linux memory profile: idle 70 MB, first call 139 MB, peak 529 MB (parent + worker).
- **PR:** #122 (`feat/i3-ocr-hardening`, Merged into `dev`).

### Day 7 (Sun 8 Nov) — User Guide, Final Urdu Review & Weekly Log
- **Deliverables:**
  1. Authored `docs/USER_GUIDE.md` covering patient and provider journeys with 11 real UI screenshots and an Urdu summary section.
  2. Built `scripts/list_new_strings.py` and audited all 158 frontend strings and 28 backend messages. Documented native-speaker refinements in `docs/URDU_REVIEW_LIST.md` (e.g. aligning button labels with instruction hints, fixing clinical terminology).
  3. Compiled Week 45 weekly log.
- **PR:** #127 (`docs/i3-user-guide-final`, Current PR).

---

## 3. Test & Quality Metrics

| Gate / Metric | Prior Baseline (W44) | Current Result (W45) | Status | Citation / Evidence |
|---|---|---|---|---|
| Frontend Vitest Suite | 247 passed (28 files) | **311 passed** (38 files) | **PASS** (100%) | `npm test` run on 7 Nov 2026; baseline from `docs/weekly/2026-W44-hassaan.md` Table 4 |
| Backend Hermetic Pytest Suite | 1,412 passed | **1,861 passed**, 1 deselected | **PASS** | CI command run on 7 Nov 2026; baseline from `docs/weekly/2026-W44-hassaan.md` Table 4 |
| Playwright E2E Journeys | 0 journeys | **5 journeys** | **PASS** | J1–J3 hermetic demo runs pass; J4–J5 authenticated live specs documented |
| WCAG 2.1 AA Accessibility | Unmeasured | **9 / 9 screens PASS** (0 axe violations) | **PASS** | `docs/ACCESSIBILITY_CHECK_W3.md` Section 1 |
| OCR Layout Recall | 0 / 15 | **15 / 15 (Dev)**, **6 / 6 (Held-out)** | **PASS** | `docs/ocr/pk_labs_results.md` (evaluated on synthetic layouts) |
| Protected Core Safety Files | 8 files verified | **8 files verified byte-identical** | **PASS** | SHA-256 hashes verified against baseline |
| TypeScript Type Check (`tsc`) | Clean | `npx tsc --noEmit` exited 0 | **PASS** | Exit code 0, 0 type errors |
| Frontend Linting (`next lint`) | Clean | 0 warnings or errors | **PASS** | `npm run lint` clean |

---

## 4. Slips, Root Cause Analysis & Lessons Learned

1. **Linux Container Memory Limits vs Free Tier Expectations:**
   - *Issue:* Initial Windows memory measurements suggested lower peak overhead (~314–385 MB), but testing on standard Linux containers demonstrated combined parent + worker peak memory of 529 MB (exceeding Render's 512 MB free tier ceiling).
   - *Remediation:* Explicitly updated `OCR_DESIGN.md` (Sections 1.3, 6.3, Table 1.2) confirming: `Safe to enable on Render free tier: NO`. Kept `OCR_ENABLED=false` as default, ensuring server stability in production.

---

## 5. Items Waiting on Doctor / Clinical Review

Traced directly from `docs/CLINICIAN_RESPONSES.md` and `docs/V3_READINESS.md`:

1. **V3 Persona Both-Miss Clinical Handling (`docs/V3_READINESS.md` Section 3):**
   - *Persona 21 (`p21_low_mood_distress`):* Whether psychological distress / low mood without somatic red flags should trigger clinical review.
   - *Persona 44 (`p44_diabetic_foot_ulcer`):* Triage severity distinction for long-standing stable ulcer vs newly acute lesion.
   - *Persona 52 (`p52_swollen_ankles_salty_diet`):* Bilateral dependent edema following acute high-salt dietary trigger vs progressive cardiopulmonary worsening.
2. **Longitudinal Trend Thresholds (Decision 9 in `docs/CLINICIAN_RESPONSES.md`):**
   - Confirmation on whether a 10 mg/dL or 20 mg/dL blood glucose shift over the 8-day observation window constitutes a clinically actionable rising/falling trajectory.

---

## 6. Next Week Top 3 Priorities (Week 46 — Freeze Week)

Next week is freeze week (code freeze Tuesday 10 November: only bug fixes, tests, and documentation):
1. **Final Bug Bash Fixes:** Resolve any remaining edge cases found across patient and provider portals.
2. **Usability Testing:** Run supervised usability trials with 3–5 participants using fake test accounts and synthetic data.
3. **Documentation, Test Evidence & Screenshot Support:** Finalize audit reports, trace evidence, and screenshot assets for final project submission.
