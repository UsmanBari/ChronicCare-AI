# System Test Results: Release 1 live check (flags off), 7 Nov 2026 — Muhammad Saad

**Test Date:** 7 Nov 2026 (Iteration 3 Day 7)  
**Target Frontend:** `https://chronicare-ai.netlify.app/`  
**Target Backend:** `https://chroniccare-backend-w568.onrender.com`  
**Evaluator:** Muhammad Saad (tested on live site with synthetic demo accounts; zero real patient data)  
**Evidence Pack:** `docs/screenshots/w3/release/st*.png`

---

## 1. System Test Results (ST-01 to ST-20)

Every scenario below was executed directly on `https://chronicare-ai.netlify.app/` by Muhammad Saad using fake credentials (`saad.release.check@demo.care`, `ali.khan@demo.care`, and test user inputs). Unit tests are listed solely as secondary code citations.

| ID | Test Scenario | Owner | Live Result | Evidence / Screenshot | Additional Test Citation |
|---|---|:---:|:---:|---|---|
| **ST-01** | Sign-up and onboarding (consent lines, profile, DOB) | Saad | **PASS** | `docs/screenshots/w3/release/st01_signup_onboarding.png` | `tests/auth-session.test.tsx` |
| **ST-02** | Under-18 age validation refused with translated alert | Saad | **PASS** | `docs/screenshots/w3/release/st02_under18_refused.png` | `tests/pregnancy-eligibility.test.tsx` |
| **ST-03** | First check-in, no earlier record (verified routine completion) | Saad | **PASS** | `docs/screenshots/w3/release/st03_first_checkin.png` | `tests/new-user-journey.test.tsx` |
| **ST-04** | Second check-in shows a conflict (reconciliation discrepancy flagged) | Saad | **PASS** | `docs/screenshots/w3/release/st04_conflict_checkin.png` | `tests/presentation.test.ts` |
| **ST-05** | Emergency phrase halts interview immediately; 1122 guidance | Hassaan | **PASS** | `docs/screenshots/w3/release/st05_emergency_phrase.png` | `tests/presentation.test.ts` |
| **ST-06** | Negation is not an emergency ("no chest pain", "koi dard nahi") | Hassaan | **PASS** | `docs/screenshots/w3/release/st06_negation_safe.png` | `tests/presentation.test.ts` |
| **ST-07** | Safety questions for very high blood pressure ($\ge 160/100$) | Hassaan | **PASS** | `docs/screenshots/w3/release/st07_high_bp_safety.png` | `tests/hypertension-parity.test.tsx` |
| **ST-08** | Warning symptom becomes an emergency (persistent chest pain / SOB) | Hassaan | **PASS** | `docs/screenshots/w3/release/st08_warning_to_emergency.png` | `tests/presentation.test.ts` |
| **ST-09** | Still severe after rest escalates to emergency hotline | Hassaan | **PASS** | `docs/screenshots/w3/release/st09_severe_after_rest.png` | `tests/presentation.test.ts` |
| **ST-10** | Medication check (stopping active medication triggers high conflict) | Saad | **PASS** | `docs/screenshots/w3/release/st10_medication_check.png` | `tests/medication-flow.test.tsx` |
| **ST-11** | Provider portal (`/provider` review queue and detail view) | Hassaan | **PASS** | `docs/screenshots/w3/release/st11_provider_portal.png` | `tests/provider-trace.test.tsx` |
| **ST-12** | Wrong portal is refused (patient account blocked from `/provider`) | Hassaan | **PASS** | `docs/screenshots/w3/release/st12_wrong_portal_refused.png` | `tests/auth-session.test.tsx` |
| **ST-13** | Admin portal (`/admin` config status and system telemetry) | Usman | **PASS** | `docs/screenshots/w3/release/st13_admin_portal.png` | `tests/admin-config-status.test.tsx` |
| **ST-14** | Simulated hospital (Isolated mode uses honest self-reported labels) | Saad | **PASS** | `docs/screenshots/w3/release/st14_simulated_hospital.png` | `tests/honest-labels.test.ts` |
| **ST-15** | Public test server (Live Render health check 200, Netlify CORS) | Saad | **PASS** | `docs/screenshots/w3/release/st15_public_test_server.png` | `scripts/smoke_test.py` (5/5 PASS) |
| **ST-16** | Bad inputs (non-numeric, blanks, out-of-range polite re-asking) | Saad | **PASS** | `docs/screenshots/w3/release/st16_bad_inputs.png` | `tests/presentation.test.ts` |
| **ST-17** | Urdu & Roman Urdu support (RTL layout, zero English leak) | Saad | **PASS** | `docs/screenshots/w3/release/st17_urdu_interface.png` | `tests/interview-urdu.test.tsx` |
| **ST-18** | Session survives a refresh (token persistence in localStorage) | Hassaan | **PASS** | `docs/screenshots/w3/release/st18_session_refresh.png` | `tests/ux-logout-eye.test.tsx` |
| **ST-19** | Revoking and restoring consent (revoked consent blocks check-in) | Saad | **PASS** | `docs/screenshots/w3/release/st19_consent_revocation.png` | `tests/demo-readiness.test.tsx` |
| **ST-20** | Older adult gets an extra question (age $\ge 65$ safety check) | Hassaan | **PASS** | `docs/screenshots/w3/release/st20_older_adult_checkin.png` | `tests/presentation.test.ts` |

---

## 2. Iteration 3 Feature Screens (Flags-Off Verification)

Per Release 1 deployment architecture, experimental features remain gated behind feature flags on production until clinician sign-off:

| Screen / Feature | Production Flag | Status on Live Deployment | Action / Note |
|---|---|:---:|---|
| **Patient Risk Card** | `RISK_ENABLED` | **OFF** | **flag off: NOT RUN** (Saad repeats after Usman deploys Release 2 on Sunday) |
| **Patient Explanation** | `EXPLAIN_ENABLED` | **OFF** | **flag off: NOT RUN** (Saad repeats after Usman deploys Release 2 on Sunday) |
| **Provider Check-in Risk** | `RISK_ENABLED` | **OFF** | **flag off: NOT RUN** (Saad repeats after Usman deploys Release 2 on Sunday) |
| **Provider Guideline Explanation** | `EXPLAIN_ENABLED` | **OFF** | **flag off: NOT RUN** (Saad repeats after Usman deploys Release 2 on Sunday) |
| **OCR Lab Report Upload** | `OCR_ENABLED` | **OFF** | **flag off: NOT RUN** (Saad repeats after Usman deploys Release 2 on Sunday) |
| **Audit Decision Trace** | Always On (Internal) | **READY** | Verified in `st11_provider_portal.png` |
| **Record Edits & History** | Always On | **READY** | Verified in `st10_medication_check.png` |

---

## 3. Defects & Deployment Verdict

- **Blocking Defects:** **0**
- **Live Smoke Test:** 5/5 checks passed (`backend health: 200`, `protected route: 401`, `auth configured: 401`, `CORS allow-origin: https://chronicare-ai.netlify.app`, `frontend: 200`).
- **Verdict:** **Release 1 live check (flags off), 7 Nov 2026**. Core safety flows (ST-01..20), honest labelling, emergency 1122 escalation, and Urdu localization operate without failure on live production infrastructure. Experimental features remain safely disabled behind production flags.
