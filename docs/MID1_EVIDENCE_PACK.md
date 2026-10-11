# ChronicCare AI — Mid-1 Evidence Pack

> **Document Status**: Production Verified Mid-1 Evidence Pack  
> **Repository**: ChronicCare AI (FastAPI + Next.js 14)  
> **Project Context**: Student Final Year Project (FYP-1)  
> **Verification Date**: October 11, 2026  

---

## 1. Snapshot

| Attribute | Verified Value |
|---|---|
| **Commit SHA (dev base)** | `1de0e9b4931bf896874ec8d5459080e66aed51a3` |
| **Branch** | `chore/stage-10f-evidence-pack` |
| **Timestamp** | 2026-10-11T17:40:00+05:00 |
| **Verification Operators** | Usman Bari & Antigravity AI Pair Programmer |
| **Deployed Production Frontend** | `https://chronicare-ai.netlify.app/` |
| **Deployed Production Backend** | `https://chroniccare-backend-w568.onrender.com` |

---

## 2. Test and Build Results

All tests and builds were executed on the clean worktree. Raw counts and statuses are tabulated below:

| Test Suite / Build Step | Exact Command | Result | Tests / Pages Count | Duration |
|---|---|---|---|---|
| **Frontend Unit / Integration Tests** | `npm test` (`vitest run`) | **PASS** | 18 passed (18 files), 183 passed (183 tests) | 41.69s |
| **Frontend Production Build** | `npm run build` (`next build`) | **PASS** | 4 static pages generated (4/4 static export) | 26.2s |
| **Frontend Static Linter** | `npm run lint` (`next lint`) | **PASS** | 0 errors, 0 warnings | 4.8s |
| **Backend Pytest Hermetic Suite** | Exact pytest file list from CI workflow (46 test targets) | **PASS** | 671 passed, 1 deselected, 0 failed (14 warnings) | 295.96s (4m 55s) |
| **Python Ruff Correctness Gate** | `python -m ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output` | **PASS** | All checks passed! | 1.8s |
| **Mutation Proof Verification** | `python scripts/verify_mutations.py` | **PASS** | 23/23 mutations killed & verified | 38.2s |
| **Production Cloud Smoke Test** | `python scripts/smoke_test.py --backend <BACKEND> --frontend <FRONTEND>` | **PASS** | 5/5 checks passed | 23s |

---

## 3. Safety-Critical Modules (SHA-256 Integrity Verification)

The 5 safety-critical clinical agents were verified against `origin/main` object hashes in Git. All 5 modules are 100% byte-for-byte identical with `origin/main` (`git diff origin/main..HEAD` produces 0 lines of diff):

| Module Path | Git Object SHA-256 (`origin/main`) | Git Object SHA-256 (Current `HEAD`) | Git Status |
|---|---|---|---|
| `backend-poc-technical/agents/adaptive_interview_agent.py` | `c0123cb711c9a204c9608638bad82fca029ffc83f21629205a201e2016678161` | `c0123cb711c9a204c9608638bad82fca029ffc83f21629205a201e2016678161` | **MATCH** |
| `backend-poc-technical/agents/triage_protocol.py` | `52a1d77d896ce9348fa7ccb5b9c22a39e43aefa1c1a2a9b7677b5a20921a84c3` | `52a1d77d896ce9348fa7ccb5b9c22a39e43aefa1c1a2a9b7677b5a20921a84c3` | **MATCH** |
| `backend-poc-technical/agents/medication_confirmation.py` | `9a91810832480375af5fb32981b3ae2567a466d2161e1e23c2e45e02576d61c2` | `9a91810832480375af5fb32981b3ae2567a466d2161e1e23c2e45e02576d61c2` | **MATCH** |
| `backend-poc-technical/agents/verification_agent.py` | `4f12578573889da60197bddd312a2ea9cb784f228bf5d7a276dcec20a8db3340` | `4f12578573889da60197bddd312a2ea9cb784f228bf5d7a276dcec20a8db3340` | **MATCH** |
| `backend-poc-technical/agents/reconciliation_agent.py` | `2591226048e6757f13701493d758896c618bea5cbd20cd777bb5c322ca812988` | `2591226048e6757f13701493d758896c618bea5cbd20cd777bb5c322ca812988` | **MATCH** |

*(Note: On Windows workstations with `core.autocrlf=true`, local working tree checkouts store CRLF newlines; raw disk hashes reflect local line endings, while Git tree content and LF-normalized hashes match identically).*

---

## 4. Production Smoke Test and DB Preflight Results

### A. Production Smoke Test (`scripts/smoke_test.py`)
Executed against live Render backend and Netlify frontend:
```text
[PASS] backend health: status=200 after 1 attempt(s), 23s
[PASS] protected route is closed: status=401
[PASS] sign-in configured: status=401
[PASS] CORS allows the frontend: status=200, allow-origin='https://chronicare-ai.netlify.app', expected='https://chronicare-ai.netlify.app'
[PASS] frontend is served: status=200

5/5 checks passed
```

### B. MySQL Database Preflight Check (`scripts/mysql_preflight.py`)
- **Status**: `NOT RUN: credentials not available here`
- **Reason**: Production database connection strings (`MYSQL_URL`, `MYSQL_SSL_CA`) are restricted credentials stored only within the Render production dashboard environment. They are intentionally absent from local developer shells and Git repositories to protect clinical infrastructure secrets.

### C. Offline Mutation Verification Engine (`scripts/verify_mutations.py`)
```text
[MUT-1] Danger Screen on Free Text -> KILLED (PASS)
[MUT-2] Negation Handling in Danger Screen -> KILLED (PASS)
[MUT-3] Unknown / Skip Retention Invariant -> KILLED (PASS)
[MUT-4] Planner Never Re-asks Filled Slot -> KILLED (PASS)
[MUT-5] Interview Budget Hard Cap (14) -> KILLED (PASS)
[MUT-6] Probe Depth Limit (2) -> KILLED (PASS)
[MUT-7] Unit Guessing Prevented -> KILLED (PASS)
[MUT-8] Contradiction Flag Preserved -> KILLED (PASS)
[MUT-9] Odd / Hostile Input After Danger -> KILLED (PASS)
[MUT-10] Self-Harm Screen Immediate Exit -> KILLED (PASS)
[MUT-11] Romantic Remark Classified as Non-Symptom -> KILLED (PASS)
[MUT-12] Fixed Reply Set Invariant -> KILLED (PASS)
[MUT-13] Safety Priority First in Classification -> KILLED (PASS)
[MUT-14] Answered by Third Party Flag -> KILLED (PASS)
[MUT-15] Extra Danger Detections (Vomiting/Breathing) -> KILLED (PASS)
[MUT-8B-1] Stage 8b: Fast Path Glucose Context Skip Rule -> KILLED (PASS)
[MUT-8B-2] Stage 8b: Hypo-Events Question Rule -> KILLED (PASS)
[MUT-8B-3] Stage 8b: Sick-Day Flags Prompt Rule -> KILLED (PASS)
[MUT-8B-4] Stage 8b: BP Technique Question Rule -> KILLED (PASS)
[MUT-8B-5] Stage 8b: OTC Meds BP Check Rule -> KILLED (PASS)
[MUT-8B-6] Stage 8b: Missed-Dose Reason Rule -> KILLED (PASS)
[MUT-8B-7] Stage 8b: Free-Text Note Passed Through -> KILLED (PASS)
[MUT-9A7-1] Stage 9A-7: Cannot Keep Fluids Down Red Flag Rule -> KILLED (PASS)

DIAGNOSTIC TEST: Demonstrating harness exits non-zero on invalid target...
PASS: Harness caught missing target with expected ValueError: Target string error in input_triage.py for MUT-FAKE: expected 1 occurrence, found 0

All 23 Mutations Verified & Killed: YES
```

---

## 5. Feature Map

Every user-facing feature has been cross-referenced with its UI implementation file, backend REST endpoint, and test suite. Every referenced file was verified with `git ls-files`:

| Feature Name | Primary UI Screen File | Backend API Endpoint(s) | Covering Automated Test File(s) |
|---|---|---|---|
| **Sign-Up & Sign-In** | `app/components/LoginScreen.tsx` | `POST /api/auth/session`, `GET /api/me` | `tests/auth-session.test.tsx`, `tests/ux-logout-eye.test.tsx` |
| **Informed Consent** | `app/components/ConsentScreen.tsx` | `POST /api/me/consent`, `POST /api/me/consent/provider-notification` | `tests/new-user-journey.test.tsx` |
| **Inclusion / Eligibility** | `app/components/InclusionScreen.tsx` | `PUT /api/me/profile` | `tests/pregnancy-eligibility.test.tsx`, `tests/new-user-journey.test.tsx` |
| **Health Profile Onboarding** | `app/components/HealthProfileScreen.tsx` | `PUT /api/me/profile` | `tests/onboarding-conditions.test.tsx`, `tests/demo-readiness.test.tsx` |
| **Isolated Health Record** | `app/components/HealthRecordScreen.tsx` | `GET /api/me/record`, `POST/PATCH/DELETE /api/me/record/*` | `tests/medication-flow.test.tsx` |
| **EHR Connection (FHIR)** | `app/components/ConnectionScreen.tsx` | `GET /api/ehr/systems`, `POST /api/ehr/connect`, `GET /api/ehr/connection` | `tests/ehr-connection-parity.test.tsx` |
| **Patient Home Dashboard** | `app/components/HomeScreen.tsx` | `GET /api/checkins`, `GET /api/me/record` | `tests/demo-readiness.test.tsx`, `tests/no-fake-values.test.tsx` |
| **Adaptive Check-In Entry & Speech** | `app/components/CheckInEntryScreen.tsx` | `POST /api/voice/transcribe`, `POST /api/checkins/start` | `tests/voice-checkin-entry.test.tsx`, `tests/voice-input.test.ts` |
| **Adaptive Interview Flow** | `app/components/AdaptiveInterviewScreen.tsx` | `POST /api/checkins/{id}/answer` | `tests/new-user-journey.test.tsx`, `tests/presentation.test.ts` |
| **Results & Risk Assessment** | `app/components/ResultScreen.tsx` | `POST /api/checkins/{id}/complete` | `tests/medication-result.test.ts`, `tests/no-fake-values.test.tsx` |
| **Reconciliation & Conflict Triage** | `app/components/ConflictScreen.tsx` | `POST /api/checkins/{id}/complete` | `tests/no-fake-values.test.tsx`, `tests/presentation.test.ts` |
| **Emergency Red-Flag Escalation** | `app/components/EmergencyScreen.tsx` | `POST /api/checkins/{id}/answer` | `tests/demo-readiness.test.tsx`, `tests/presentation.test.ts` |
| **Longitudinal Trends** | `app/components/TrendScreen.tsx` | `GET /api/checkins` | `tests/demo-readiness.test.tsx`, `tests/hypertension-parity.test.tsx` |
| **User Sign-Out / Session Expiry** | `app/context/AppContext.tsx` | `POST /api/auth/session` (401 interceptor) | `tests/ux-logout-eye.test.tsx`, `tests/auth-session.test.tsx` |

---

## 6. Defect Log (D1 to D9)

| Defect ID | Description | Status | Fixing Commit SHA | Verification Notes |
|---|---|---|---|---|
| **D1** | CI import error due to working directory assumptions | **Fixed** | `5b1c046` | Path independence enforced across sim and bank tests in CI. |
| **D2** | Invented design documentation removed | **Fixed** | `0c85f1e` | Restored authoritative v3 research and design specification. |
| **D3** | Non-real mutation proofs rebuilt with real subprocess harness | **Fixed** | `4249d9f`, `8191c87` | Rebuilt real mutation verification harness killing 23 mutations with live pytest subprocesses. |
| **D4** | v3 interview engine dropped mmol/L unit recognition | **Fixed** | `444ce38` | Restored 18.0182 conversion factor and bare 41–54 clarification in v3. |
| **D5** | v2 interview engine low-glucose gap (bare readings 41–54 mg/dL) | **Fixed** | `0a4ee5c` | Added mmol/L recognition and clarification loop for bare values 41–54 mg/dL. |
| **D6** | Stale `.pyc` bytecode cache caused mutation test survival | **Fixed** | `79cfaf0` | Added automatic `.pyc` cache purging in mutation runner before each test execution. |
| **D7** | Romantic remark and advice regex patterns were overly broad | **Fixed** | `2842e20` | Narrowed regexes and added clinician expectations pack parity test in CI. |
| **D8** | First-check-in conflict wording confusing on isolated patient | **Fixed** | `ed43071` (`d874b34`) | Removed fabricated numbers; updated conflict screen to explain human review honestly. |
| **D9** | Missing sign-out button and password eye visibility toggle | **Fixed** | `5cccef9` (`8b85d7b`), `625e179` | Added accessible password toggle and role-aware sign-out across all three portals. |

---

## 7. Known Limitations

The prototype operates under the following documented clinical and technical constraints:

1. **No Clinical Certification**: The application is an academic research prototype and has not undergone formal clinical trial validation or regulatory certification (FDA 510(k), CE mark, or SaMD).
2. **Normal-Vitals Narrative Questions**: Narrative-yes questions (reported hypo events, sick-day flags, associated symptoms, foot problems) record clinical flags for provider review but do not automatically escalate numerical triage levels when vitals are normal.
3. **Severe Vomiting / Fluid Retention**: Inability to keep fluids down currently directs patients to the emergency red-flag screen pending final clinical committee decision on whether to classify it as Emergency or Urgent Triage.
4. **Altered Mental Status / "Confused"**: The exact classification threshold for patient confusion remains pending final clinical panel review.
5. **Non-Answer Detection Recall**: Automated recognition of non-answers and ambiguous responses operates at approximately 40% recall by conservative design to prevent false positive classifications.
6. **Adaptive Interview Engine v3 Inactive in Production**: The modular v3 interview engine is simulation-tested in CI and remains behind the `INTERVIEW_ENGINE=v3` flag; production uses the verified v2 state-machine.
7. **Free-Tier Cloud Latency**: Render backend free tier enters sleep after 15 minutes of inactivity, resulting in a 30–60 second cold-start delay on first wake-up (mitigated by the UI's server waking notification bar).
8. **First Self-Reported Check-In Routing**: In isolated mode without an EHR record, rule 3 routes the first self-reported reading to clinician review (`requires_review=True`, severity moderate) to establish an initial verified baseline.

---

## 8. Screenshot Checklist (S01 to S27)

Usman can capture these 27 key screens across the Patient, Provider, and Admin portals during the live walkthrough:

- [ ] **S01 — Landing Screen**: Portal selection with "Simulated example" badges on condition cards.
- [ ] **S02 — Patient Login**: Email/password inputs with accessible password show/hide eye toggle.
- [ ] **S03 — Patient Consent**: Dual consent toggles (data processing and provider notification).
- [ ] **S04 — Inclusion & Eligibility**: Age calculation and pregnancy status screening.
- [ ] **S05 — Health Profile**: Condition selection (Type 2 Diabetes, Hypertension, or both).
- [ ] **S06 — Connection Choice**: EHR vs. Isolated mode selection screen.
- [ ] **S07 — EHR Linking**: Simulated FHIR hospital connection with handshake animation.
- [ ] **S08 — Isolated Health Record**: "Edit my record" interface for self-managed medicines and baseline vitals.
- [ ] **S09 — Patient Home Dashboard**: Condition-aware cards and honest "Your medicines" card.
- [ ] **S10 — Check-In Entry**: Voice dictation entry with live recording / demo audio indicator.
- [ ] **S11 — Adaptive Interview (Q1)**: Initial symptom probe with skip and negation support.
- [ ] **S12 — Adaptive Interview (Q2)**: Dynamic branching follow-up question.
- [ ] **S13 — Check-In Review & Confirmation**: Summary of answers before submission.
- [ ] **S14 — Analysis & Processing**: 2.2s calculation screen with clinical validation flash.
- [ ] **S15 — Result Screen (Scenario A - Normal)**: Stable risk badge and contributing factor breakdown.
- [ ] **S16 — Conflict Screen (Scenario B - Discrepancy)**: Honest conflict notice without fabricated metrics.
- [ ] **S17 — Low Confidence Route**: Human review routing notice for conflicting check-ins.
- [ ] **S18 — Emergency Screen (Scenario C - Red Flag)**: Immediate emergency alert with 1122 helpline guidance.
- [ ] **S19 — Longitudinal Trends (Diabetes)**: Fasting blood glucose history chart.
- [ ] **S20 — Longitudinal Trends (Hypertension)**: Blood pressure systolic/diastolic dual-line chart.
- [ ] **S21 — Provider Login**: Clinician authentication screen with eye toggle.
- [ ] **S22 — Provider Dashboard**: Live case tracker (Active, Urgent, Routine) and patient cohort table.
- [ ] **S23 — Provider Review Queue**: Triage queue highlighting flagged patient rows.
- [ ] **S24 — Provider Review Detail**: Reconciliation detail comparing check-in data with EHR baseline.
- [ ] **S25 — Admin Login & Dashboard**: Administrator sign-in and system telemetry status.
- [ ] **S26 — Error Boundary Fallback**: Prototype error page displaying honest research disclaimer.
- [ ] **S27 — 404 Not Found Page**: Custom not-found screen with link back to application home.

---

## 9. Dependency Advisories (`npm audit --omit=dev`)

Production dependencies were audited via `npm audit --omit=dev`. 7 advisories across 4 production packages were identified:

| Package | Severity | Advisory Title & Reference | Installed Version | Vulnerable Code Path Can Run in App? | Recommended Fix |
|---|---|---|---|---|---|
| `@grpc/grpc-js` | High | Unauthorized certificates in `getAuthContext` ([GHSA-m9gg-hp2v-232j](https://github.com/advisories/GHSA-m9gg-hp2v-232j)) | `1.9.16` | **Does not apply**: App only imports client-side `firebase/auth`. gRPC server code is not executed in the browser. | `>=1.13.5` via Firebase upgrade |
| `@grpc/grpc-js` | High | Server transmits error messages in status messages ([GHSA-f596-whhp-79r4](https://github.com/advisories/GHSA-f596-whhp-79r4)) | `1.9.16` | **Does not apply**: No gRPC server handler runs in the browser client. | `>=1.13.5` via Firebase upgrade |
| `next` | Critical | HTTP request deserialization DoS in React Server Components ([GHSA-h25m-26qc-wcjf](https://github.com/advisories/GHSA-h25m-26qc-wcjf)) | `14.2.35` | **Does not apply**: The frontend is a static export (`output: 'export'`) hosted on Netlify CDN; no Next.js Node server runs at runtime. | `next@>=16.4.0` |
| `next` | High | DoS via Image Optimizer remotePatterns ([GHSA-9g9p-9gw9-jx7f](https://github.com/advisories/GHSA-9g9p-9gw9-jx7f)) | `14.2.35` | **Does not apply**: Static export compiles images at build-time; Next.js image optimization API server is disabled. | `next@>=16.4.0` |
| `next` | High | Denial of Service in App Router Server Actions ([GHSA-m99w-x7hq-7vfj](https://github.com/advisories/GHSA-m99w-x7hq-7vfj)) | `14.2.35` | **Does not apply**: The app does not utilize Server Actions; all data exchange occurs via client-side fetch to FastAPI backend. | `next@>=16.4.0` |
| `postcss` | High | CSS stringify unescaped style tags ([GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93)) | `8.4.31` | **Does not apply**: PostCSS executes solely during build compilation (`npm run build`); no PostCSS code runs in the client browser. | `postcss@>=8.5.22` |
| `source-map-js` | High | Event-loop DoS via source-map section offsets ([GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q)) | `1.2.1` | **Does not apply**: Source map processing occurs during local build only. | Upstream patch |

> **Advisories were reviewed, not upgraded before submission, to avoid build risk; upgrade planned for FYP-2.**

---

## 10. Commands to Reproduce Everything Above

To reproduce every result and verify the evidence locally from scratch:

```bash
# 1. Clone repository and check out verified stage branch
git checkout chore/stage-10f-evidence-pack

# 2. Frontend Dependencies, Linter, Test Suite, and Static Build
npm ci
npm run lint
npm test
npm run build

# 3. Backend Database Init, Linter, and Hermetic Pytest Suite
python backend-poc-technical/init_local_db.py
python -m ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output
python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_main.py backend-poc-technical/test_llm.py backend-poc-technical/test_auth.py backend-poc-technical/test_profile_ehr.py backend-poc-technical/test_adaptive_interview_agent.py backend-poc-technical/test_checkin_api.py backend-poc-technical/test_checkin_safety.py backend-poc-technical/test_medication_confirmation.py backend-poc-technical/test_checkin_medications.py backend-poc-technical/test_record.py backend-poc-technical/test_consent_lines.py backend-poc-technical/test_triage_protocol.py backend-poc-technical/test_checkin_triage.py backend-poc-technical/test_inclusion.py backend-poc-technical/test_clinical_rules_doc.py backend-poc-technical/test_fhir_sim.py backend-poc-technical/test_fhir_client.py backend-poc-technical/test_ehr_connected.py backend-poc-technical/test_production_guard.py backend-poc-technical/test_mysql_preflight.py backend-poc-technical/test_new_user_journey.py backend-poc-technical/test_age_calculation.py backend-poc-technical/test_pregnancy_eligibility.py backend-poc-technical/test_schema_v10_to_v11.py backend-poc-technical/test_voice_transcribe.py backend-poc-technical/test_richer_enrolment.py backend-poc-technical/test_adversarial_edge_cases.py backend-poc-technical/test_schema_v11_to_v12.py backend-poc-technical/test_interview_v2_3_questions.py backend-poc-technical/test_interview_bank.py backend-poc-technical/test_interview_findings.py backend-poc-technical/test_interview_planner.py backend-poc-technical/test_answer_validation.py backend-poc-technical/test_input_triage.py backend-poc-technical/test_sim_personas.py backend-poc-technical/test_sim_report.py backend-poc-technical/test_mutation_proofs_v3.py backend-poc-technical/test_glucose_unit_safety.py backend-poc-technical/test_interview_v3_wire.py backend-poc-technical/test_engine_equivalence.py backend-poc-technical/test_mutation_proofs.py backend-poc-technical/test_mutation_runner.py backend-poc-technical/test_glucose_unit_conversion_v3.py backend-poc-technical/test_glucose_v2_low_gap.py backend-poc-technical/test_vomiting_fluids_red_flags.py backend-poc-technical/test_clinician_pack_parity.py -v -k "not run_source_blind_test"

# 4. Mutation Proof Verification Engine
python scripts/verify_mutations.py

# 5. Production Smoke Test (Live Cloud Services)
python scripts/smoke_test.py --backend https://chroniccare-backend-w568.onrender.com --frontend https://chronicare-ai.netlify.app --wait 120

# 6. Production Dependencies Audit
npm audit --omit=dev
```
