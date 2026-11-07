# System Test Results: Release 1 live check (flags off), 7 Nov 2026 — Muhammad Saad

**Test Date:** 7 Nov 2026 (Iteration 3 Day 7)  
**Target Frontend:** `https://chronicare-ai.netlify.app/`  
**Target Backend:** `https://chroniccare-backend-w568.onrender.com`  
**Evaluator:** Muhammad Saad  
**Evidence Pack:** `docs/screenshots/w3/release/st15_public_test_server.png`

> [!NOTE]
> **Live Release Check Status:**
> Live check: NOT RUN on 7 Nov except ST-15; full ST-01..20 runs on Sunday after Release 2.
> On Sunday, Saad runs ST-01..20 himself (by hand with a fake account), capturing one genuine screenshot per row showing the outcome. That goes into a new small PR after Usman deploys Release 2.

---

## 1. System Test Results (ST-01 to ST-20)

| ID | Test Scenario | Owner | Live Result | Evidence / Note | Additional Test Citation |
|---|---|:---:|:---:|---|---|
| **ST-01** | Sign-up and onboarding (consent lines, profile, DOB) | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/auth-session.test.tsx` |
| **ST-02** | Under-18 age validation refused with translated alert | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/pregnancy-eligibility.test.tsx` |
| **ST-03** | First check-in, no earlier record (verified routine completion) | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/new-user-journey.test.tsx` |
| **ST-04** | Second check-in shows a conflict (reconciliation discrepancy flagged) | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/presentation.test.ts` |
| **ST-05** | Emergency phrase halts interview immediately; 1122 guidance | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/presentation.test.ts` |
| **ST-06** | Negation is not an emergency ("no chest pain", "koi dard nahi") | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/presentation.test.ts` |
| **ST-07** | Safety questions for very high blood pressure ($\ge 160/100$) | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/hypertension-parity.test.tsx` |
| **ST-08** | Warning symptom becomes an emergency (persistent chest pain / SOB) | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/presentation.test.ts` |
| **ST-09** | Still severe after rest escalates to emergency hotline | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/presentation.test.ts` |
| **ST-10** | Medication check (stopping active medication triggers high conflict) | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/medication-flow.test.tsx` |
| **ST-11** | Provider portal (`/provider` review queue and detail view) | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/provider-trace.test.tsx` |
| **ST-12** | Wrong portal is refused (patient account blocked from `/provider`) | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/auth-session.test.tsx` |
| **ST-13** | Admin portal (`/admin` config status and system telemetry) | Usman | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/admin-config-status.test.tsx` |
| **ST-14** | Simulated hospital (Isolated mode uses honest self-reported labels) | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/honest-labels.test.ts` |
| **ST-15** | Public test server (Live Render health check 200, Netlify CORS) | Saad | **PASS** | `docs/screenshots/w3/release/st15_public_test_server.png` (status=200, healthy) | `scripts/smoke_test.py` (5/5 PASS) |
| **ST-16** | Bad inputs (non-numeric, blanks, out-of-range polite re-asking) | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/presentation.test.ts` |
| **ST-17** | Urdu & Roman Urdu support (RTL layout, zero English leak) | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/interview-urdu.test.tsx` |
| **ST-18** | Session survives a refresh (token persistence in localStorage) | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/ux-logout-eye.test.tsx` |
| **ST-19** | Revoking and restoring consent (revoked consent blocks check-in) | Saad | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/demo-readiness.test.tsx` |
| **ST-20** | Older adult gets an extra question (age $\ge 65$ safety check) | Hassaan | **NOT RUN** | Live check moves to Sunday, after Release 2 | `tests/presentation.test.ts` |

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
| **Audit Decision Trace** | Always On (Internal) | **READY** | To be verified on live deployment on Sunday |
| **Record Edits & History** | Always On | **READY** | To be verified on live deployment on Sunday |

---

## 3. Defects & Deployment Verdict

- **Blocking Defects:** **0**
- **Live Smoke Test:** 5/5 checks passed (`backend health: 200`, `protected route: 401`, `auth configured: 401`, `CORS allow-origin: https://chronicare-ai.netlify.app`, `frontend: 200`).
- **Verdict:** **Live check: NOT RUN on 7 Nov except ST-15; full ST-01..20 runs on Sunday after Release 2.** Deployed backend server is verified healthy via ST-15; full user journey verification will be completed by Saad on Sunday following Usman's Release 2 deployment.
