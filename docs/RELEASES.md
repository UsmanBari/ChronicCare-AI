# ChronicCare AI — Release Log

## Release 1 — 2 Nov 2026

- **Production Commit (main):** `bf799cf` (Merge pull request #100 from UsmanBari/dev)
- **Deployment Status:** Live on Render (backend) and Netlify (frontend)
- **Date & Time:** 2 November 2026, ~21:30 PKT (16:30 UTC)

---

### 1. Overview & Contents

Release 1 merges all Iteration 2 work from `dev` to `main` (production). It incorporates 25 merged pull requests (plus PR #74's commit arriving via #75) spanning 166 commits ahead of the previous production release (#69 from 16 Oct).

All new capabilities (risk prediction, RAG guideline explainer, adaptive interview v3, trend monitoring, and OCR) are gated behind environment feature flags and remain strictly **OFF** by default in production.

#### Included Pull Requests

| PR | Author | Title | Merged At |
|:---|:---|:---|:---|
| #70 | @usmanbari-ub | I2-0 Day 1: EHR test patients + doctor on record | 2026-10-27 |
| #71 | @hassaan07mudassar | Docs/i2 4 interview audit | 2026-10-27 |
| #72 | @usmanbari-ub | I2-2 Day 2: guideline corpus, ingestion, rules check | 2026-10-27 |
| #73 | @hassaan07mudassar | fix(interview): probe answers by step and correct interview audit | 2026-10-27 |
| #74 | @msaadd25 | #74: closed; its commit came in through #75 | - |
| #75 | @msaadd25 | I2-1 Day 2: temporal split, fair baseline, feature map, label catalogue | 2026-10-28 |
| #76 | @hassaan07mudassar | feat(interview): v3 answer understanding and slot filling (Day 2) | 2026-10-28 |
| #77 | @hassaan07mudassar | feat(interview): v3 dual diagnosis, de-duplication, caregiver, and summary confirmation (Day 3) | 2026-10-28 |
| #78 | @msaadd25 | I2-1 Day 3: ML evaluation toolkit + model artifact contract | 2026-10-28 |
| #79 | @UsmanBari | I2-2 Day 3: ML plan + retriever + grounded explainer | 2026-10-28 |
| #80 | @hassaan07mudassar | Feat/i2 4 v3 urdu complete | 2026-10-29 |
| #81 | @msaadd25 | I2-6 Day 4: trend agent module + reading history + tests | 2026-10-29 |
| #82 | @UsmanBari | I2-1 Day 4: experiment harness + model runs | 2026-10-29 |
| #83 | @msaadd25 | I2-6 Day 5: trends live (API, patient screen, provider detail) | 2026-10-30 |
| #84 | @hassaan07mudassar | feat(ocr): Day 5 OCR spike, benchmark, and technical designs | 2026-11-01 |
| #89 | @hassaan07mudassar | Docs/i2 4 urdu danger proposals | 2026-11-01 |
| #90 | @usmanbari-ub | I2-1 Day 5: risk model in the app (provider-only) + waist field + model cards + doctor pack | 2026-11-01 |
| #91 | @msaadd25 | I2-1 Day 6: external validation + dataset loaders + DHS skeleton | 2026-11-01 |
| #92 | @hassaan07mudassar | feat(record): Day 6 record edit history (schema v13) and record export/import | 2026-11-01 |
| #93 | @usmanbari-ub | I2-3 Day 6: LangGraph orchestrator (equivalence-proven) | 2026-11-01 |
| #94 | @msaadd25 | I2-8 Day 7: coverage, fixes, MIMIC script, RAG test set, phrase test r2, weekly log | 2026-11-01 |
| #95 | @usmanbari-ub | P0: a bare 'no' is never a glucose reading | 2026-11-01 |
| #96 | @hassaan07mudassar | fix(record): Day 6 follow-ups (MySQL import cursor, Esc test, Urdu labels) | 2026-11-02 |
| #98 | @usmanbari-ub | I2 Day 7: risk + explanation + trace wired (flags off) | 2026-11-02 |
| #99 | @usmanbari-ub | I3 Day 1: release 1 docs + read-only prod check | 2026-11-02 |
| #101 | @usmanbari-ub | fix(test): isolate upload_id in ocr audit log assertion to eliminate UUID collision flake | 2026-11-02 |

---

### 2. Database Migrations & Verification

- **Production Database:** `chroniccare_demo` (managed on Aiven MySQL).
- **Migration Execution:** Applied additively on startup via FastAPI lifespan `migrate()` (v12 $\to$ v15).
  - **v13**: Adds nullable column `waist_cm` (FLOAT NULL) to `patient_profiles`.
  - **v14**: Creates table `record_edits` (no foreign key) with indexes `idx_record_edits_lookup (user_id, record_type, record_id)` and `idx_record_edits_timeline (user_id, changed_at DESC)`.
  - **v15**: Adds nullable columns `risk_json` (TEXT NULL), `explanation_json` (TEXT NULL), `trace_json` (TEXT NULL) to `checkin_results`, and creates `guideline_chunks` table with indexes `idx_guideline_chunks_condition (condition)` and `idx_guideline_chunks_source (source_id)`.
- **Render Startup Verification:** Render backend logs confirmed clean migration; `"Database migration skipped on startup"` was **NOT** found.

#### Before vs. After Row Tallies (`scripts/prod_schema_readonly.py`)

| Metric / Table | Pre-Deploy (v12) | Post-Deploy (v15) | Delta | Notes |
|:---|:---|:---|:---|:---|
| **Schema Version** | **12** | **15** | +3 | Additive migrations applied |
| **Total Tables** | **13** | **15** | +2 | `record_edits` and `guideline_chunks` added |
| `users` | 15 | 15 | 0 | Unchanged |
| `checkins` | 17 | 17 | 0 | Unchanged |
| `checkin_results` | 8 | 8 | 0 | Unchanged |
| `audit_log` | 155 | 155 | 0 | Unchanged |
| `record_edits` | — | 0 | +0 | New table initialized |
| `guideline_chunks` | — | 0 | +0 | New table initialized |

- **Post-Deploy Preflight:** `python scripts/mysql_preflight.py` executed once after deploy: **ALL STEPS PASSED**, confirmed schema version 15 and 15 tables.

---

### 3. Production Environment & Feature Flags

Checked and verified in Render dashboard:
- `PYTHON_VERSION`: `3.11.9`
- Build command: `pip install -r requirements.txt` (heavy OCR packages from `requirements-ocr.txt` excluded)

| Variable | Setting | Production State |
|:---|:---|:---|
| `RISK_ENABLED` | Unset | OFF (no risk payload returned to patient) |
| `RISK_CAN_RAISE` | Unset | OFF (risk model cannot escalate routine triage) |
| `EXPLAIN_ENABLED` | Unset | OFF (guideline explanation generation bypassed) |
| `OCR_ENABLED` | Unset | OFF (endpoints return 503 / upload UI hidden) |
| `SCREENING_REMINDER_INTERVAL_DAYS` | Unset | Inactive |
| `INTERVIEW_ENGINE` | Unset | `v2` (default legacy engine active, v3 dormant) |
| `ORCHESTRATOR` | Unset | `direct` (direct procedural execution active, graph dormant) |

---

### 4. Backups & Rollback Strategy

- **Aiven Backup:** Automatic backup verified at 2 Nov 2026, 15:47 UTC with point-in-time recovery (PITR) available.
- **Rollback Procedure:**
  - **Backend:** Render Dashboard -> `chroniccare-backend` -> Deploys -> Rollback to pre-release commit `6e28b0a`. Because migrations v13-v15 are strictly additive (only adding new nullable columns and new isolated tables), the older backend code ignores these additions and continues running without errors.
  - **Frontend:** Netlify Dashboard -> `chroniccare-ai` -> Deploys -> Publish prior successful build.
  - **Database:** Aiven database fork/restore only required if an unexpected data-damaging event occurs.

---

### 5. Smoke Test & CI/CD Results

1. **Automated Smoke Test (`scripts/smoke_test.py`):**
   ```text
   [PASS] backend health: status=200 after 1 attempt(s), 0s
   [PASS] protected route is closed: status=401
   [PASS] sign-in configured: status=401
   [PASS] CORS allows the frontend: status=200, allow-origin='https://chronicare-ai.netlify.app', expected='https://chronicare-ai.netlify.app'
   [PASS] frontend is served: status=200

   5/5 checks passed
   ```
2. **GitHub Actions Workflow Runs:**
   - **CD (`.github/workflows/cd.yml`):** Run `41482946897` completed with `success` (11s) on `main` push.
   - **CI (`.github/workflows/ci.yml`):** Run `41482223830` on branch `main` completed with `success` (4m20s).

---

### 6. Operational Incident Notes

1. **Aiven Free Plan Idle Spin-Down:**
   The Aiven free plan powered the database off while idle. It showed 'Rebuilding' and took 5+ minutes to come back. Wake it and wait for 'Running' before any deploy or demo.
2. **Default Database Disambiguation:**
   Aiven's default Service URI ends in `/defaultdb`. During initial testing, `defaultdb` was connected to by mistake instead of the intended database (`chroniccare_demo`). Tooling was patched in PR #99 (`scripts/prod_schema_readonly.py`) to explicitly output the target database name and display an error warning if `defaultdb` is detected.
3. **Database Credential Rotation:**
   The production database password was rotated and reset on 2 Nov 2026 after exposure in a chat window; the Render dashboard configuration was updated accordingly.
4. **Flaky Test Fixed in PR #101:**
   CI on release PR #100 initially failed on `test_ocr_upload.py::test_audit_logs_contain_counts_only_no_phi_no_filename` because `uuid.uuid4()` produced an `upload_id` containing the substring `"125"` (`...3c125d3c947b`), triggering a false-positive PHI check. PR #101 resolved this by isolating `upload_id` verification before running PHI assertions on the remaining payload.

---

## Release 2 — 8 Nov 2026

- **Production Commit (main):** `3ef51f8` (Merge pull request #132 from UsmanBari/dev)
- **Deployment Status:** Live on Render (backend) and Netlify (frontend)
- **Date & Time:** 8 November 2026, ~16:30 PKT (11:30 UTC)

---

### 1. Overview & Contents

Release 2 deploys Iteration 3 capabilities to production. It merges 29 pull requests from `dev` into `main` across Week 3, incorporating:
- Live clinical risk advisory panel (provider-only view, strictly null for patients).
- Grounded RAG guideline explainer with asynchronous background job queue and multi-provider failover.
- Permitted ADA 2026 diabetes guideline integration (Sections 2, 5, 6, 10, 11, 13) via Groq API.
- Multilingual template fallback explanations for Urdu and Roman Urdu.
- Acute danger word-groups detector for vernacular Urdu red flags.
- Emergency safety invariants: stage 1 red flags and crises bypass LLM calls, return null risk and null explanation, and include emergency contact guidance (1122).

#### Included Pull Requests

| PR | Author | Title | Merged At |
|:---|:---|:---|:---|
| #102 | @usmanbari-ub | I3 Day 2: RAG evaluation suite + retriever | 2026-11-03 |
| #103 | @usmanbari-ub | I3 Day 2: explainer evaluation + safety validators | 2026-11-03 |
| #104 | @usmanbari-ub | I3 Day 3: background job queue + memory leak verification | 2026-11-03 |
| #105 | @usmanbari-ub | I3 Day 3: explain latency profiler + load test docs | 2026-11-04 |
| #106 | @usmanbari-ub | I3 Day 4: clinician response capture + rule changes R1-R8 | 2026-11-04 |
| #107 | @usmanbari-ub | I3 Day 4: multi-provider explainer (Groq primary, Gemini fallback) | 2026-11-04 |
| #108 | @usmanbari-ub | I3 Day 4: danger phrase plan + held-out phrase sets | 2026-11-04 |
| #109 | @usmanbari-ub | I3 Day 5: composable symptom word-groups danger detector | 2026-11-04 |
| #110 | @usmanbari-ub | I3 Day 5: explainer safety guards + provider failover + H1/H2 | 2026-11-05 |
| #111 | @usmanbari-ub | I3 Day 5: test suite count consolidation | 2026-11-05 |
| #112 | @usmanbari-ub | I3 Day 5: clinical persona runner + v3 decision evaluation | 2026-11-05 |
| #113 | @usmanbari-ub | I3 Day 5: P0 safety fixes G-02 (clarification) and G-14 (caregiver) | 2026-11-05 |
| #114 | @usmanbari-ub | I3 Day 5: clinician survey pack + feedback forms | 2026-11-05 |
| #115 | @usmanbari-ub | I3 Day 5: live smoke test harness for explainer | 2026-11-05 |
| #116 | @usmanbari-ub | I3 Day 5: eval numbers collection script | 2026-11-05 |
| #117 | @usmanbari-ub | I3 Day 6: architecture docs, report evidence, limitations, traceability | 2026-11-05 |
| #118 | @usmanbari-ub | I3 Day 6b: ADA 2026 guideline written academic permission enforcement | 2026-11-05 |
| #119 | @usmanbari-ub | I3 Day 6c: API contract for risk advisory, explainer & decision trace | 2026-11-06 |
| #120 | @usmanbari-ub | I3 Day 6c: review feedback fixes on API contract documentation | 2026-11-06 |
| #121 | @usmanbari-ub | I3 Day 6d: live smoke evaluation with real guideline corpus | 2026-11-06 |
| #122 | @usmanbari-ub | I3 Day 6d: real-chunks smoke test coverage | 2026-11-06 |
| #123 | @usmanbari-ub | I3 Day 6e: explainer real-corpus fixes (token cap, validation, condition filter) | 2026-11-06 |
| #124 | @usmanbari-ub | I3 Day 6e: review follow-ups on active_cond and background queue | 2026-11-06 |
| #125 | @usmanbari-ub | I3 Day 6f: ADA guideline pre-ranking filter for non-diabetic patients | 2026-11-06 |
| #126 | @usmanbari-ub | I3 Day 6g: Groq OTPM pacer wait against job deadline | 2026-11-07 |
| #127 | @usmanbari-ub | I3 Day 6g: review corrections for pacer deadline extension order | 2026-11-07 |
| #128 | @usmanbari-ub | I3 Day 6g: real-clock test suite for pacer wait | 2026-11-07 |
| #130 | @usmanbari-ub | I3 Day 7a: EXPLAIN_LLM_LANGUAGES switch (English LLM, Urdu templates) | 2026-11-08 |
| #131 | @usmanbari-ub | I3 Day 7a: language gate placement before cache lookup | 2026-11-08 |
| #132 | @usmanbari-ub | Release 2 (Iteration 3) to main | 2026-11-08 |

---

### 2. Database & Guideline Corpus Verification

- **Production Database:** `chroniccare_demo` (managed on Aiven MySQL).
- **Schema Migrations:** No schema version bump required; remained at **Schema Version 15** with **15 tables**.
- **Guideline Loading (D3):**
  Usman loaded the complete guideline corpus (1,175 chunks) into production MySQL using the verified command:
  ```powershell
  $env:DB_BACKEND="mysql"; python scripts/rag/load_chunks.py --file "$env:CHRONICCARE_DATA_DIR\rag\chunks.jsonl"; Remove-Item Env:DB_BACKEND
  ```
  - **Output:** `[SUCCESS] Loaded 1182 guideline chunks into database (1175 inserted, 7 updated)`.
  - **Read-Only Verification:** `scripts/prod_schema_readonly.py` confirmed:
    - Schema Version: 15
    - Total Tables: 15
    - `guideline_chunks`: 1,175 rows
    - All other row tallies unchanged (`users`: 17, `checkins`: 17, `checkin_results`: 8, `audit_log`: 161).

---

### 3. Production Environment & Feature Flags Configuration

The release was deployed with the following sequence:
1. Merged release PR #132 to `main` first (Release 2 code ran briefly under Release 1 dormant flags; patient risk = null invariant was enforced in code).
2. Set and activated environment variables in the Render dashboard:

| Variable Name | Production Setting | Operational State |
|:---|:---|:---|
| `RISK_ENABLED` | `true` | Active (evaluates risk for provider review; strictly null for patients) |
| `RISK_CAN_RAISE` | `false` | Invariant (risk model cannot escalate clinical triage) |
| `DANGER_WORDGROUPS_ENABLED` | `true` | Active (composable acute red-flag phrase detector enabled) |
| `EXPLAIN_MODE` | `background` | Active (asynchronous queue with worker thread) |
| `LLM_PROVIDER` | `groq` | Groq sole active provider (Gemini free tier disabled due to 503 errors) |
| `EXPLAIN_LLM_CONDITIONS` | `hypertension,diabetes` | Both conditions permitted for LLM explanations |
| `EXPLAIN_LLM_LANGUAGES` | `en` | English only (Urdu & Roman Urdu route to reviewed templates) |
| `GROQ_API_KEY` | `SET` | Configured with new production Groq key |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` | Configured production model |
| `EXPLAIN_ENABLED` | `true` | Active (activated after guideline chunk loading) |
| `OCR_ENABLED` | `false` (absent) | Inactive (503 response preserved) |
| `GEMINI_API_KEY` | `NOT SET` | Disabled |
| `GEMINI_MODEL` | `NOT SET` | Disabled |
| `SCREENING_REMINDER_INTERVAL_DAYS` | `NOT SET` | Inactive |

#### Operational Changes from Initial Plan:
1. **`LLM_PROVIDER=groq` (not `auto`):** During pre-release testing, Google Gemini free tier experienced three requests, all resulting in HTTP 503 Service Unavailable errors and zero successful completions. To prevent failover cascading to an unstable endpoint, Groq was designated as the sole provider.
2. **`EXPLAIN_LLM_LANGUAGES=en`:** On 8 November, a formal human read of real-corpus LLM explanations was conducted (Usman for English, Hassaan as native speaker for Urdu/Roman Urdu). English passed 4/4 (100%). Urdu/Roman Urdu had translation inaccuracies (one Urdu translation reversed "risk factors managed" to "fulfilled", one Roman Urdu misstated "greater than 140/90", and one used a corrupted diabetes term). Under the Release 2 "0 wrong" rule, LLM explanations were restricted to English only; Urdu and Roman Urdu patients receive pre-verified deterministic templates.
3. **Deployment Order:** Merged PR #132 prior to toggling flags, ensuring that new safety code (H3 doctors-only risk nulling) was live before risk computation was enabled.

---

### 4. Post-Deployment Verification & Live Smokes

1. **Render Build & Health Smoke (D2):**
   ```text
   [PASS] backend health: status=200 after 1 attempt(s), 0s
   [PASS] protected route is closed: status=401
   [PASS] sign-in configured: status=401
   [PASS] CORS allows the frontend: status=200, allow-origin='https://chroniccare-ai.netlify.app'
   [PASS] frontend is served: status=200

   5/5 checks passed
   ```

2. **Production Live Smoke Suite (D5 — `scripts/prod_live_smoke.py`):**
   Executed against the live Render backend (`https://chroniccare-backend-w568.onrender.com`) using ephemeral fake test accounts and connected hospital records:

   | Case | Target Condition & Lang | Expected Level | Actual Level | Risk in Complete | Explanation Status | Safety / Result |
   |:---|:---|:---|:---|:---|:---|:---|
   | Case 1 | Hypertension (EN) | routine | review | null | ready (LLM) | PASS (LEVEL DIFFERS: baseline recon) |
   | Case 2 | Hypertension (UR) | review | review | null | ready (Template) | PASS (`language_template_only`) |
   | Case 3 | Hypertension (Roman UR) | review | review | null | ready (Template) | PASS (`language_template_only`) |
   | Case 4 | Hypertension (EN) | urgent | urgent | null | ready (LLM) | PASS (urgent level preserved) |
   | Case 5 | Hypertension (UR) | urgent | urgent | null | ready (Template) | PASS (`language_template_only`) |
   | Case 6 | Diabetes (EN) | review | review/null | null | ready (LLM) | PASS (cited ADA 2026 guidelines) |
   | Case 7 | Diabetes (UR) | review | review/null | null | ready (Template) | PASS (`language_template_only`) |
   | Case 8 | Hypertension (EN Emergency) | emergency | emergency | null | null (0 LLM calls) | PASS (1122 emergency note returned) |
   | Case 9 | Provider Review Detail | — | — | — | — | NOT RUN (provider credentials withheld) |
   | Case 10| Patient Privacy Invariant | — | — | **null (all)** | — | PASS (zero probability/band leakage) |

   - **Hypertension Source Safety:** Zero diabetes sources (ADA, IDF-DAR, AKU) cited in any hypertension case.
   - **Emergency Invariant:** Case 8 bypassed explainer and queue completely, returning null explanation and null risk with immediate 1122 guidance.

---

### 5. Known Limitations & Rollback Procedures

- **Known Limitations:**
  - Groq free-tier OTPM pacer enforces ~1,000 output tokens/min rate limits.
  - LLM explanations restricted to English; Urdu and Roman Urdu use deterministic templates.
  - Isolated-mode observation ID generation (`CHECKIN-local-{uid}-{stamp}-{type}`) exceeds MySQL `observations.id` `VARCHAR(64)` constraint; connected hospital flow is required and fully supported.
- **Rollback Strategy:**
  - If explanation quality or provider issues arise: set `EXPLAIN_ENABLED=false` in Render dashboard.
  - If risk advisory issues arise: set `RISK_ENABLED=false`.
  - Full backend rollback: revert Render deploy to pre-release commit `bf799cf`. Because Schema v15 is strictly additive, older code runs safely without modification.

---

## Scheduled Events

- **Release 2 Flag Plan:** Release 2 activated `RISK_ENABLED=true`, `EXPLAIN_ENABLED=true`, and `DANGER_WORDGROUPS_ENABLED=true` on 8 Nov 2026.
- **2027-06-30:** Mandatory permanent deletion of all stored ADA 2026 guideline chunks from production and development databases (`python scripts/rag/delete_source.py --licence ada_2026 --yes`).


