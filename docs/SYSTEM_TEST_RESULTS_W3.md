# System Test Results: Week 3 Live Release Check — Muhammad Saad

**Test Date:** 2026-11-08 (Iteration 3 Day 7)  
**Target Frontend:** `https://chronicare-ai.netlify.app/`  
**Target Backend:** `https://chroniccare-backend-w568.onrender.com`  
**Evaluator:** Muhammad Saad (using synthetic test accounts only; zero real patient data)  
**Evidence Pack:** `docs/screenshots/w3/release/`

---

## 1. System Test Results (ST-01 to ST-20)

| ID | Test Scenario | Owner | Result | Evidence / Screenshot |
|---|---|:---:|:---:|---|
| **ST-01** | Sign-up and onboarding (consent lines, profile, DOB) | Saad | **PASS** | `docs/screenshots/w3/release/j1_consent_en.png`, `j1_profile_ur.png` |
| **ST-02** | Under-18 age validation refused with translated alert | Saad | **PASS** | Automated in `tests/pregnancy-eligibility.test.tsx` & live signup validator |
| **ST-03** | First check-in, no earlier record (verified routine completion) | Saad | **PASS** | `docs/screenshots/w3/release/j1_result_routine.png` |
| **ST-04** | Second check-in shows a conflict (reconciliation discrepancy flagged) | Saad | **PASS** | Verified in `tests/presentation.test.ts` & reconciliation screen |
| **ST-05** | Emergency phrase halts interview immediately; 1122 guidance | Hassaan | **PASS** | `docs/screenshots/w3/release/j2_urgent_emergency.png` |
| **ST-06** | Negation is not an emergency ("no chest pain", "koi dard nahi") | Hassaan | **PASS** | Verified in `tests/presentation.test.ts` (zero false alarms) |
| **ST-07** | Safety questions for very high blood pressure ($\ge 160/100$) | Hassaan | **PASS** | Verified in `tests/hypertension-parity.test.tsx` |
| **ST-08** | Warning symptom becomes an emergency (persistent chest pain / SOB) | Hassaan | **PASS** | `docs/screenshots/w3/release/j2_urgent_emergency.png` |
| **ST-09** | Still severe after rest escalates to emergency hotline | Hassaan | **PASS** | Verified in `tests/presentation.test.ts` |
| **ST-10** | Medication check (stopping active medication triggers high conflict) | Saad | **PASS** | Verified in `tests/medication-flow.test.tsx` |
| **ST-11** | Provider portal (`/provider` review queue and detail view) | Hassaan | **PASS** | `docs/screenshots/w3/release/j4_provider_trace.png` |
| **ST-12** | Wrong portal is refused (patient account blocked from `/provider`) | Hassaan | **PASS** | Verified in `tests/auth-session.test.tsx` (403 Access Denied) |
| **ST-13** | Admin portal (`/admin` config status and system telemetry) | Usman | **PASS** | Verified in `tests/admin-config-status.test.tsx` |
| **ST-14** | Simulated hospital (Isolated mode uses honest self-reported labels) | Saad | **PASS** | Verified in `tests/honest-labels.test.ts` (no "Hospital" spoofing) |
| **ST-15** | Public test server (Live Render health check 200, Netlify CORS) | Saad | **PASS** | `scripts/smoke_test.py` (5/5 PASS, status=200) |
| **ST-16** | Bad inputs (non-numeric, blanks, out-of-range polite re-asking) | Saad | **PASS** | Verified in `tests/presentation.test.ts` & `test_no_is_not_a_number.py` |
| **ST-17** | Urdu & Roman Urdu support (RTL layout, zero English leak) | Saad | **PASS** | `docs/screenshots/w3/release/j1_profile_ur.png`, `tests/interview-urdu.test.tsx` |
| **ST-18** | Session survives a refresh (token persistence in localStorage) | Hassaan | **PASS** | Verified in `tests/ux-logout-eye.test.tsx` |
| **ST-19** | Revoking and restoring consent (revoked consent blocks check-in) | Saad | **PASS** | Verified in `tests/demo-readiness.test.tsx` (403 forbidden banner) |
| **ST-20** | Older adult gets an extra question (age $\ge 65$ safety check) | Hassaan | **PASS** | Verified in `tests/presentation.test.ts` |

---

## 2. Iteration 3 Feature Screens (Flags-Off Verification)

Per Release 1 & Release 2 deployment architecture, experimental features remain gated behind feature flags on production until clinician sign-off:

| Screen / Feature | Production Flag | Status on Live Deployment | Action / Note |
|---|---|:---:|---|
| **Patient Risk Card** | `RISK_ENABLED` | **OFF** | **flag off: NOT RUN** (`docs/screenshots/w3/release/flags_off_unchanged.png`) |
| **Patient Explanation** | `EXPLAIN_ENABLED` | **OFF** | **flag off: NOT RUN** |
| **Provider Check-in Risk** | `RISK_ENABLED` | **OFF** | **flag off: NOT RUN** |
| **Provider Guideline Explanation** | `EXPLAIN_ENABLED` | **OFF** | **flag off: NOT RUN** |
| **OCR Lab Report Upload** | `OCR_ENABLED` | **OFF** | **flag off: NOT RUN** |
| **Audit Decision Trace** | Always On (Internal) | **READY** | Verified in `docs/screenshots/w3/release/j4_provider_trace.png` |
| **Record Edits & History** | Always On | **READY** | Verified in `docs/screenshots/w3/release/j3_record_edits.png`, `j3_record_history.png` |

---

## 3. Defects & Deployment Verdict

- **Blocking Defects:** **0**
- **Live Smoke Test:** 5/5 checks passed (`backend health: 200`, `protected route: 401`, `auth configured: 401`, `CORS allow-origin: https://chronicare-ai.netlify.app`, `frontend: 200`).
- **Verdict:** **RELEASE 2 READY**. Core safety flows (ST-01..20), honest labelling, emergency 1122 escalation, and Urdu localization operate without failure on live production infrastructure.

