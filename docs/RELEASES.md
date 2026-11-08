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

## Scheduled Events

- **Release 2 Flag Plan:** Release 2 sets `EXPLAIN_LLM_CONDITIONS=hypertension,diabetes` on Render to activate LLM explanations for diabetes check-ins using permitted ADA 2026 guideline sections via Groq.
- **2027-06-30:** Purge all stored ADA 2026 guideline chunks upon conclusion of academic evaluation period (`python scripts/rag/delete_source.py --licence ada_2026 --yes`).

