# ChronicCare AI — Release Log

## Hotfix 2 — 12 Nov 2026

- **Branch:** `fix/i3-no-invented-glucose`
- **Target Base:** `dev`
- **PR Title:** `"HOTFIX 2: no invented glucose / false emergency when the patient skips the reading"`
- **Severity:** P0 Safety Hotfix

---

### 1. Problem Description & Root Cause

During local demo rehearsal on 8 Nov 2026, a critical clinical safety defect was discovered and confirmed through the real API (`POST /api/checkins/start`, `/answer`, `/complete`) on `dev` commit `c025e46`:
A diabetic patient in isolated mode reported feeling bad, skipped their blood sugar measurement (`"skip"`), and skipped the subsequent checkpoint question (`"skip"`). Upon check-in completion, the system assigned the patient an invented glucose reading of `35.0 mg/dL`, triggered the `glucose_low` protocol, assigned triage level `EMERGENCY`, and generated reasons `["Low glucose with disorientation or acute confusion."]`, despite the patient never entering any numeric value.

**Root Cause:**
1. In `backend-poc-technical/agents/adaptive_interview_agent.py`, step `MISSING_DATA_CHECKPOINT` unconditionally called `_process_glucose_input(combined_answer, previously_asked=True)` even when no prior number was pending (`_glucose_pending_raw is None`, i.e., the "describe how you feel instead" checkpoint, not the "mg/dL or mmol/L?" unit question).
2. With `previously_asked=True`, `validate_glucose_input` in `answer_validation.py` interpreted `"skip"`, `"don't know"`, or `"not sure"` as "unit clarification failed for a low number", setting `is_possible_severe_low=True` with `value=None`.
3. In `_process_glucose_input` (line ~524), `val = float(v_res.value) if v_res.value is not None else 35.0` filled in `35.0` whenever `v_res.value` was `None`.
4. At triage completion, the rule engine evaluated `glucose == 35.0 <= 54`, immediately triggering the severe low glucose emergency protocol.

**Historical Origin:**
Introduced in commit `b8ec5f2c5f00302403174d4e557894847cfc3354`:
```text
commit b8ec5f2c5f00302403174d4e557894847cfc3354
Author: Usman Bari <usmanbari@users.noreply.github.com>
Date:   Fri Oct 9 16:55:32 2026 +0500

    feat(stage9a-4): add glucose unit safety live path fallback and update clinical rules
```
`git log -S "35.0"` confirms the fallback line was introduced in `_process_glucose_input` on 9 Oct 2026.

**Affected Users:**
Diabetic patients who skipped their blood sugar reading and replied `"skip"`, `"not sure"`, or `"don't know"` to subsequent checkpoint questions.

---

### 2. Resolution

1. **Conditional Unit Clarification Parameter (F1):**
   - In `adaptive_interview_agent.py` (`_diabetes_advance_v2_3` and `_diabetes_advance`), `previously_asked=True` is now passed to `_process_glucose_input` **only** when `pending_raw is not None` (i.e. an actual numeric value was entered on turn 1).
   - When `pending_raw is None`, the checkpoint answer is parsed with `previously_asked=False`. Non-numeric answers (`"skip"`, `"tired"`, `"not sure"`) return no reading, record `answers["symptom_only_note"] = answer`, and advance directly to symptom questions without inventing a reading.

2. **Removal of 35.0 Fallback (F2):**
   - In `_process_glucose_input` (line 524), removed the fabricated default:
     ```python
     val = float(v_res.value) if v_res.value is not None else None
     ```
   - If `is_possible_severe_low` is flagged without a number, `val = None` is returned. Safety guidance and review reason are preserved for clinician review, but no numeric reading is fabricated and no `glucose_low` emergency protocol is triggered.
   - The genuine clinical rule is preserved: a bare number $\le 40$ without unit followed by `"don't know"` continues to flag `possible_severe_low=True` with safety advice for clinician review.

3. **Emergency Screen Notification Copy Correction (F3):**
   - Updated `app/components/EmergencyScreen.tsx` and `app/translations/index.ts`.
   - Replaced inaccurate `"Priority clinical notification dispatched to on-call care team."` subtitle with `"Your check-in has been sent to your care team's review list."` (English) and `"آپ کا چیک ان نگہداشت ٹیم کی جائزہ فہرست میں بھیج دیا گیا ہے۔"` (Urdu).
   - Preserved emergency hotline (1122) dispatch button and copy unchanged.

---

### 3. Verification & Test Evidence

- **T1 API Reproduction (`test_hotfix2_no_invented_glucose.py`):**
  Exact reproduction through the real API (`POST /api/checkins/start`, `/answer`, `/complete`) in both `direct` and `graph` orchestrator modes:
  - Fails on unedited `dev` code (`emergency=True`, `glucose=35.0`).
  - Passes on hotfix branch (`emergency=False`, triage level != `emergency`, `readings` contains no glucose, "35" absent from JSON).
- **T2 Checkpoint Variations:**
  Diabetic patient skipping reading and answering `"not sure"`, `"don't know"`, `"dont know"`, `"maloom nahi"`, or `"nahi pata"` produces no fabricated reading and non-emergency triage (5 passed).
- **T3 Invariant Test ("no invented readings"):**
  Across diabetes, hypertension, and dual patients, answer scripts containing zero digits (English, Roman Urdu, Urdu) strictly yield an empty `readings` dictionary `{}` in final triage (12 passed).
- **T4 Real Low Path Verification:**
  Patient entering bare `"35"` followed by `"don't know"` to unit clarification retains `possible_severe_low=True`, low-sugar safety guidance, review reason, and `requires_review=True` (1 passed).
- **Regression Suites:**
  - 52 simulated personas in `test_sim_personas.py` pass 100% with zero level shifts.
  - Subprocess mutation verification (`scripts/verify_mutations.py`): all 60 mutations killed (60/60).
  - Existing glucose safety tests (`test_glucose_v2_low_gap.py`, `test_glucose_unit_safety.py`) pass 100%.

---

## Hotfix 1 — 8/9 Nov 2026

- **Branch:** `fix/i3-mysql-id-width`
- **Target Base:** `dev`
- **PR Title:** `"HOTFIX: widen MySQL id columns that receive generated check-in ids (isolated-mode /complete 500)"`
- **Severity:** P0 Production Hotfix

---

### 1. Problem Description & Root Cause

During live smoke testing of Release 2 (PR #133), isolated-mode patients attempting to finalize a check-in with a reading (e.g., blood pressure, glucose) or medication confirmation experienced HTTP 500 on `POST /api/checkins/{id}/complete`.

**Root Cause:**
In isolated mode (standard mode for patients without an active hospital EHR linkage), the check-in completion pipeline generates observation IDs with the pattern:
```text
CHECKIN-local-<28-char Firebase uid>-<timestamp>-<observation_type>
```
For example:
`CHECKIN-local-usr_firebase_28_chars_long12-20261108T155002Z-blood_pressure_systolic` (~83 to 90 characters).

In MySQL (`data_sources/local_store.py`), `observations.id` and `medications.id` were declared as `VARCHAR(64) PRIMARY KEY`. Similarly, `record_edits.record_id` in `data_sources/app_store.py` was declared as `VARCHAR(64)`. When inserting an 83+ character string into a `VARCHAR(64)` column, MySQL rejected the write with error 1406 (`Data truncation: Data too long for column 'id' at row 1`), crashing check-in completion.

SQLite (used in local development and standard test runners) enforces dynamic typing without strict VARCHAR length constraints, which allowed every test to pass unnoticed prior to deployment on production Aiven MySQL.

**Historical Origin:**
Introduced in commit `6c1e12a` on Sun Oct 4 20:08:37 2026:
```text
commit 6c1e12a488c919a32c253fc3fa98e1694f420e6a
Author: Usman Bari <usmanbari@users.noreply.github.com>
Date:   Sun Oct 4 20:08:37 2026 +0500

    feat(backend): reconcile MySQL support for Local Store and App Store
```
`git log -S "VARCHAR(64) PRIMARY KEY"` reveals `observations.id` and `medications.id` were declared `VARCHAR(64)` in `local_store.py` at that initial MySQL backend commit.

**Affected Users:**
Isolated-mode patients completing a check-in with any physiological reading or medication confirmation. Connected-mode patients remained unaffected because external EHR observation identifiers are shorter.

---

### 2. Resolution

1. **Schema DDL Widening:**
   - Widened `observations.id` from `VARCHAR(64)` to `VARCHAR(191)` in `local_store.py`.
   - Widened `medications.id` from `VARCHAR(64)` to `VARCHAR(191)` in `local_store.py`.
   - Widened `record_edits.record_id` from `VARCHAR(64)` to `VARCHAR(191)` in `app_store.py` (`MYSQL_RECORD_EDITS_DDL`).
   - `191` characters is the maximum safe column width for utf8mb4 indexing on MySQL InnoDB engines (767 bytes / 4 bytes per character = 191).
   - Preserves `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL` and retains PRIMARY KEY constraints.

2. **Idempotent Database Migration:**
   - In `data_sources/local_store.py`, `_init_mysql_db` calls `apply_id_width_migration(cursor)`.
   - Inspects `INFORMATION_SCHEMA.COLUMNS` for each target column and modifies the column only if `CHARACTER_MAXIMUM_LENGTH < 191`.
   - Added failsafe per-column error handling that logs errors at ERROR level (`id-width migration FAILED: <column>: <error class>`) without crashing server startup.
   - Outputs startup log lines:
     - On first application: `"id-width migration: applied 3 columns (observations.id, medications.id, record_edits.record_id)"`
     - On subsequent restarts: `"id-width migration: already wide"`
   - Provides dry-run function `get_id_width_alter_statements() -> List[str]`.
   - In `data_sources/app_store.py`, bumped `LATEST_SCHEMA_VERSION = 16` (SQLite advances `schema_version` to 16 cleanly; MySQL records version 16).

3. **Production Read-Only Inspection Tooling:**
   - Extended `scripts/prod_schema_readonly.py` to inspect and output column widths within a strictly read-only session (`SET SESSION TRANSACTION READ ONLY` + `ROLLBACK`).

4. **Correct Guideline Chunks Loading Command:**
   Documented the verified command used by Usman to populate `guideline_chunks` in production MySQL:
   ```powershell
   $env:DB_BACKEND="mysql"; python scripts/rag/load_chunks.py --file "$env:CHRONICCARE_DATA_DIR\rag\chunks.jsonl"; Remove-Item Env:DB_BACKEND
   ```

---

### 3. Verification & Test Evidence

- **C1 Contract Test (`test_mysql_id_width_contract.py`):**
  Parses MySQL DDL strings from code; generates maximum possible IDs for all code generators (28-char Firebase UID, longest observation types, 99 meds); asserts `len(id) <= declared_width`.
  - Failed on unedited dev code (assert 84 <= 64).
  - Passes on hotfix branch (5 passed).
- **C2 Guard Test (`test_isolated_mode_checkin_length_guard.py`):**
  Executes isolated-mode check-in with BP reading and medication confirmation through `POST /complete` with a 28-char user ID in both direct and graph modes, intercepting store writes with MySQL column width checks.
  - Failed on unedited dev code with `ValueError: Data truncation: observations.id ... (length 83) exceeds MySQL column width 64`.
  - Passes on hotfix branch in both direct and graph modes (2 passed).
- **C3 Schema Migration Test (`test_schema_v15_to_v16.py`):**
  Verifies SQLite upgrade v15 $\to$ v16, fresh DB upgrade, idempotence, data preservation, and tests `apply_id_width_migration` with fake MySQL cursors across narrow, already wide, and error-handling conditions (7 passed).

---

### 4. Rollback Plan

- **Backend Rollback:** In Render Dashboard, revert to previous deploy or redeploy prior commit (`3ef51f8`).
- **Database Schema Compatibility:** Widening column limits is backward-compatible. Older application code reading and writing to `VARCHAR(191)` columns functions without error.
- **Manual Column Reversion (Emergency only):**
  If reverting column widths to 64 is ever strictly necessary (note: records longer than 64 characters would be truncated):
  ```sql
  ALTER TABLE observations MODIFY id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
  ALTER TABLE medications MODIFY id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
  ALTER TABLE record_edits MODIFY record_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;
  ```

---

### 5. Deployment Runbook for Usman

Follow these steps in this exact order:

0. **Aiven Console Backup Check:**
   - Log into Aiven console -> select MySQL service -> Overview.
   - Confirm an automatic backup exists from today (no sensitive data or connection strings printed).

1. **Merge & Deploy:**
   - Merge PR #135 into `dev`.
   - Open a PR `dev` -> `main` and merge it (following the same procedure as Release 2).
   - Wait for Render to build and deploy.

2. **Render Startup Logs Verification:**
   - In Render backend deployment logs, verify the exact startup sequence:
     ```text
     id-width migration: applied 3 columns (observations.id, medications.id, record_edits.record_id)
     local store ready
     DbChunkStore loaded at startup: 1175 chunks
     ```
   - (On any subsequent restart where columns are already widened, it logs `id-width migration: already wide`).

3. **Run Read-Only Production Schema Inspector:**
   In local PowerShell:
   ```powershell
   $env:MYSQL_URL = Read-Host "Paste MYSQL_URL"
   $env:MYSQL_SSL_CA = Read-Host "Full path to your Aiven ca.pem"
   python scripts/prod_schema_readonly.py
   Remove-Item Env:MYSQL_URL
   Remove-Item Env:MYSQL_SSL_CA
   ```
   Confirm output displays:
   - Schema Version: `16`
   - Total Tables: `15`
   - `guideline_chunks`: `1175`
   - Column Widths:
     - `medications.id`: `VARCHAR(191)`
     - `observations.id`: `VARCHAR(191)`
     - `record_edits.record_id`: `VARCHAR(191)`

4. **Run Isolated-Mode Smoke Verification:**
   - Execute the updated live smoke script with isolated-mode cases (PR #133 corrections R3: hypertension BP 118/76 routine, BP 145/92 review, diabetes glucose 190 review, medication confirmation, and no-readings all-'no' check-in).
   - Confirm every case completes with HTTP 200.

---

### 6. Part E: Analysis of Empty Sources (`sources: []`) in D5 Live Smoke

1. **Confirmed Event Sequence on 8 Nov:**
   - Deploy & Restart: Release 2 was merged and deployed to Render, restarting the FastAPI container.
   - At process startup, `main.py` executed:
     ```python
     if os.environ.get("EXPLAIN_ENABLED", "").strip().lower() == "true":
         from rag.store import get_db_chunk_store
         store = get_db_chunk_store()
         logger.info("DbChunkStore loaded at startup: %d chunks", store.total_chunks())
     ```
   - Chunks Not Yet Loaded: At that moment, `load_chunks.py` had NOT yet been run against production MySQL. The store initialized with `0` chunks.
   - Loading Chunks Post-Startup: Usman subsequently loaded 1,175 chunks into MySQL (~16:58 PKT). However, because `_GLOBAL_DB_CHUNK_STORE` in `rag/store.py` was a static in-memory singleton loaded once, it remained populated with 0 chunks in memory on the running container.
   - Result: During the D5 smoke run, `step_explain()` queried the chunk store, received `candidate_chunks == []`, and both the LLM pipeline and the template fallback yielded `sources = []`.

2. **The H3 Resolution:**
   - In `backend-poc-technical/rag/store.py`, `get_db_chunk_store()` now checks `_GLOBAL_DB_CHUNK_STORE.total_chunks() == 0`.
   - If empty, it automatically triggers a reload (`force_reload=True`) on use, throttled to at most once every 60 seconds to prevent reload storms.
   - Logs: `"DbChunkStore reloaded: %d chunks"`.
   - Non-empty stores (`total_chunks() > 0`) are never reloaded.

3. **D5 "ready (LLM)" Status Disambiguation:**
   - The D5 smoke table in PR #133 labeled several cases as `"ready (LLM)"`.
   - This label was **not** evidence of LLM execution; it was copied directly from `case['expected_mode']` in `scripts/prod_live_smoke.py`:
     ```python
     "expected_mode": "llm",
     ```
   - The patient-facing check-in API response returns only:
     ```json
     {"explanation": {"status": "ready", ...}}
     ```
   - The patient endpoint strips internal audit fields and never reveals `mode`. Explanation `mode` (`llm` vs `template`) is only visible in the provider review view.
   - Because the live chunk store held 0 chunks during the D5 run, no LLM explanation could have utilized guideline passages that day. D5 did **not** prove that any LLM explanation ran.

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

## Scheduled Events

- **Release 2 Flag Plan:** Release 2 sets `EXPLAIN_LLM_CONDITIONS=hypertension,diabetes` on Render to activate LLM explanations for diabetes check-ins using permitted ADA 2026 guideline sections via Groq.
- **2027-06-30:** Purge all stored ADA 2026 guideline chunks upon conclusion of academic evaluation period (`python scripts/rag/delete_source.py --licence ada_2026 --yes`).

