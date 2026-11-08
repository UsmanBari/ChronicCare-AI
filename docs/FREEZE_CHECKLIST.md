# ChronicCare AI — Code Freeze Checklist & Operational Plan

**Freeze Effective Date:** Tuesday, 10 November 2026, 23:59 PKT  
**Evaluation Date:** Tuesday, 17 November 2026  
**Lead & Release Owner:** Usman Bari  
**Production Target:** `https://chronicare-ai.netlify.app` / `https://chroniccare-backend-w568.onrender.com`

---

## 1. Code Freeze Policies & Boundaries (10 – 16 Nov 2026)

From **23:59 PKT on Tuesday 10 November 2026**, the ChronicCare AI repository enters strict **CODE FREEZE**:

1. **Strictly Forbidden:**
   - **NO** new functional features, capabilities, or architectural changes.
   - **NO** new database migrations (Schema version remains locked at v15).
   - **NO** new backend API endpoints or alterations to existing endpoint contract schemas.
   - **NO** new external dependencies or library updates in `requirements.txt` or `package.json`.
   - **NO** changes to protected clinical engine files (`input_triage.py`, `clinical_rules.py`, `triage_protocols.py`) without prior written clinician consensus and explicit test proofs.

2. **Permitted Changes (Fixes Only):**
   - Critical clinical safety bug fixes backed by failing regression tests and 60/60 mutation kill proofs.
   - Usability and layout adjustments arising from the 11–14 November patient/clinician usability sessions.
   - Copy corrections in UI text or non-functional documentation (FYP-1 final report, evaluation slides, user guide).
   - Test suite hardening and hermetic fixture stabilization.

3. **PR Merge Rules:**
   - **Zero Unverified Merges:** Every pull request must be reviewed, re-tested locally in both orchestrator modes (`direct` and `graph`), and merged exclusively by Usman Bari.
   - Agents (Antigravity/Claude) are strictly prohibited from merging pull requests.

---

## 2. Daily Timeline: Freeze to Evaluation (10 – 17 Nov 2026)

| Date | Phase / Milestone | Key Activities & Deliverables | Owner |
|:---|:---|:---|:---|
| **Tue 10 Nov** | **Code Freeze Finalization** | Final PR merges for remaining documentation; verify clean working tree on `dev`; verify direct + graph CI passes. Code freeze takes effect at 23:59 PKT. | Usman |
| **Wed 11 Nov** | **Usability Trials (Day 1)** | Conduct 2 bilingual patient usability sessions using `demo-hospital` test records. Test intake clarity, audio input, and Arabic-script Urdu readability. | Hassaan / Usman |
| **Thu 12 Nov** | **Usability Trials (Day 2)** | Conduct clinician usability review with Dr. Shaiza / Capt. Dr. Talha. Walk through provider review queue, reconciliation diffs, and risk advisory panel. | Usman / Hassaan |
| **Fri 13 Nov** | **Usability Hardening & Bug Bash** | Implement non-breaking frontend fixes identified in usability sessions (spacing, phrasing, mobile tap targets). Update `docs/USABILITY_FINDINGS.md`. | Hassaan / Saad |
| **Sat 14 Nov** | **Doctor Final Sign-Off & Report Finalization** | Capture formal clinician signatures / approval notes in `docs/CLINICIAN_RESPONSES.md`. Assemble final FYP-1 written report chapters with verified evidence tables. | Usman / Saad / Hassaan |
| **Sun 15 Nov** | **Full Live Demo Rehearsal** | Presentation slides finalized. Conduct complete end-to-end rehearsal on live site (`https://chronicare-ai.netlify.app`) using the 10-minute cue sheet in `DEMO_SCRIPT.md`. | Entire Team |
| **Mon 16 Nov** | **Buffer Day & Pre-Evaluation Release** | Morning dev $\to$ main sync (docs/fixes only); verify Render/Netlify zero-downtime builds; run pre-evaluation smoke check; freeze local demo laptops. | Usman |
| **Tue 17 Nov** | **FYP-1 Final Evaluation** | Present ChronicCare AI to faculty evaluation committee. Live demonstration following the rehearsed 10-minute script. | Entire Team |

---

## 3. Pre-Demo Verification Checklist (15 – 16 Nov 2026)

To be completed and signed off prior to the 17 November presentation:

### A. Infrastructure & Databases
- [ ] **Aiven MySQL Service:** Confirm status is **Running** in Aiven Console (wake the instance at least 30 minutes before demo if idling).
- [ ] **Database Integrity Check:** Run `scripts/prod_schema_readonly.py` to confirm Schema v15, 15 tables, and `guideline_chunks = 1175`.
- [ ] **Render Backend:** Verify `https://chroniccare-backend-w568.onrender.com/api/health` returns `{"status":"healthy"}` without cold-start latency.
- [ ] **Netlify Frontend:** Verify `https://chroniccare-ai.netlify.app` loads cleanly with SSL certificate valid.

### B. Feature Flags & Environment Invariants
Check via Admin status (`GET /api/admin/config-status`) or Render Dashboard:
- [ ] `RISK_ENABLED`: `true`
- [ ] `RISK_CAN_RAISE`: `false`
- [ ] `DANGER_WORDGROUPS_ENABLED`: `true`
- [ ] `EXPLAIN_MODE`: `background`
- [ ] `LLM_PROVIDER`: `groq`
- [ ] `EXPLAIN_LLM_CONDITIONS`: `hypertension,diabetes`
- [ ] `EXPLAIN_LLM_LANGUAGES`: `en`
- [ ] `EXPLAIN_ENABLED`: `true`
- [ ] `OCR_ENABLED`: `false` (absent)
- [ ] `GEMINI_API_KEY` / `GEMINI_MODEL`: `NOT SET`

### C. Live Test Accounts & Scenarios
- [ ] Demo patient accounts (`patient@demo.care`) have active profiles with consent confirmed.
- [ ] Connected sample patients in `demo-hospital` (`sim-newpatient`, `sim-ayesha`, `sim-sana`) verified accessible.
- [ ] Demo provider account (`doctor@demo.care`) accessible and mapped to `provider` role in `DEMO_ROLE_MAP`.
- [ ] Offline backup screenshots and screen recordings saved locally on USB drive in case of conference Wi-Fi failure.

---

## 4. Final Release Steps (Monday 16 Nov 2026)

1. **Step 1 — Pre-Release Read-Only Inspection:**
   ```powershell
   $env:PYTHONPATH="backend-poc-technical"
   python scripts/prod_schema_readonly.py
   ```
2. **Step 2 — Open & Merge Final Release PR:**
   - Open PR from `dev` to `main` with title `"I3: Final pre-evaluation sync"`.
   - Usman reviews and merges PR. Agent never merges.
3. **Step 3 — Post-Deploy Automated Smoke Test:**
   ```bash
   python scripts/smoke_test.py --backend https://chroniccare-backend-w568.onrender.com --frontend https://chroniccare-ai.netlify.app
   ```
4. **Step 4 — Targeted Live Sanity Check:**
   - Execute one English check-in (`python scripts/prod_live_smoke.py --case 4`) and one emergency check-in (`python scripts/prod_live_smoke.py --case 8`) to confirm 100% operational readiness.

