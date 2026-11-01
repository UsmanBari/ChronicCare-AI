# Weekly Engineering Log: Week 44 (Iteration 2)

**Engineer:** Hassaan Mudassar (Frontend & Integration Engineer)  
**Period:** Monday 26 October 2026 – Sunday 1 November 2026  
**Branch / Target:** `feat/i2-5-ocr-v1` -> `dev`  

---

## 1. Executive Summary

During Week 44, engineering efforts focused on advancing Iteration 2 across two principal pillars:
1. **Adaptive Clinical Interview v3 Localization & Safety:** Hardening understanding, multi-turn slot filling, dual-diagnosis management (diabetes + hypertension), full Urdu localization with zero English leakage, and independent danger phrase screening.
2. **Patient Health Record Integrity & OCR Ingestion (I2-5):** Implementing immutable record edit history (`record_edits`, schema v14), all-or-nothing JSON/FHIR import/export with preview, and building OCR v1 behind a server-side feature flag (`OCR_ENABLED=false`) using server RapidOCR and human-in-the-loop review.

All 7 milestones for Week 2 were completed, tested, and verified against project safety guidelines ("the model proposes, the rules decide").

---

## 2. Daily Engineering Deliverables

### Day 1 & Day 2 — Interview v3 Answer Understanding & Slot Filling
- **Deliverables:** Built deterministic understanding rules for free-text check-in responses, extracting blood glucose and blood pressure numbers, units (mg/dL vs mmol/L, mmHg), and missing reading reasons.
- **Testing:** Implemented automated probe harness across 107 clinical scenarios to verify that safe triage and boundary rules are preserved.
- **PR:** #71 (Merged into `dev`). Note: PR #74 was superseded by #76 and closed without merging.

### Day 3 — Dual Diagnosis, Caregiver Reporting, and Confirmation Summary
- **Deliverables:** Extended the interview planner to support dual-diagnosis patients (T2D and HTN simultaneously), eliminating duplicate questions and isolating condition-specific red flags. Added caregiver reporting awareness and a pre-submission review summary.
- **PR:** #76 / #77 (Merged into `dev`).

### Day 4 — Full Urdu Localization & Independent Danger Phrase Testing
- **Deliverables:** Localized the complete interview catalogue to Urdu (100% zero English leakage across 12 test personas). Ensured proper typography using RTL layout and `<bdi>` directional isolation.
- **Testing:** Authored an independent 30-phrase Urdu evaluation set and proposed whole-number numeric boundary rules for blood sugar/BP danger phrases.
- **PR:** #80 / #89 (Merged into `dev`).

### Day 5 — OCR Feasibility Spike & Benchmark
- **Deliverables:** Evaluated 3 free OCR engines (Desktop Tesseract, RapidOCR ONNX, Tesseract.js in-browser). Measured Character Error Rate (CER), latency, memory, and field extraction accuracy across printed and handwritten prescription/lab photos.
- **Outcome:** Formally recommended server-side RapidOCR due to lightweight ONNX footprint (Option B RapidOCR peak footprint: 108.99 MB peak RSS, ~2-3s latency, 9/9 handwritten medicines recognized vs 1/9 for Tesseract.js).
- **PR:** #84 (Approved & Merged into `dev`).

### Day 6 — Record Edit History (Schema v14) & Export/Import
- **Deliverables:** Added `record_edits` table (schema v14) recording who, what, when, old/new values, and origin (`self_reported`, `ocr`, `import`, `clinician`). Built JSON and FHIR Bundle export and previewed import with atomic transaction rollback.
- **PR:** #92 (Merged into `dev`). Followed up on Day 7 with MySQL import cursor parameterization, Esc key focus restoration, and localized preview labels.

### Day 7 — OCR v1 Behind a Feature Flag
- **Deliverables:**
  1. **Flagged Endpoints:** Built `POST /api/me/record/uploads` and `POST /api/me/record/uploads/{upload_id}/confirm` gated behind `OCR_ENABLED=false` (returns HTTP 503 when disabled; refuses connected mode with HTTP 409).
  2. **Zero PHI Persistence:** Implemented ephemeral in-memory staging store (max 3 uploads per user, 30-minute TTL, automatic cleanup). Raw image bytes are never written to disk or database.
  3. **Strict Re-Validation:** Clinical bounds (glucose 20–600 mg/dL, systolic BP 60–260 mmHg, diastolic BP 40–150 mmHg) and dosage formatting are strictly re-verified on server confirmation before writing to the database with `origin="ocr"` and medium trust.
  4. **Frontend Confirmation UI:** Built `OcrConfirmScreen.tsx` allowing patients to review each detected value with its evidence snippet, and Confirm, Fix, or Remove each item. Added Urdu notice banner for Urdu-script documents.
  5. **Screenshots:** Generated documentation screenshots for English review (`ocr_confirm_en.png`), Urdu review (`ocr_confirm_ur.png`), Health Record badge (`ocr_badge_record_en.png`), and invalid-item clinical rejection highlight in English (`ocr_invalid_item_en.png`) and Urdu (`ocr_invalid_item_ur.png`).
- **PR:** PR #96 (`feat/i2-5-ocr-v1`, open). Merged PRs this week: #71, #76, #77, #80, #84, #89, #92.

---

## 3. Architecture & Safety Design Choices

- **Server-Side RapidOCR:** RapidOCR with ONNX Runtime is isolated in an optional `requirements-ocr.txt` dependency set. The server loads the OCR engine lazily upon the first upload request, leaving the base process memory footprint at 61.8 MB.
- **Production Guard:** A hard check in `provider.py` refuses `OCR_PROVIDER=fake` whenever `APP_ENV=production`, preventing mock providers from being inadvertently deployed.
- **Human-in-the-Loop Safeguard:** Extracted values are never auto-committed to the patient's record. Every value requires explicit patient confirmation, saving with `origin="ocr"` (medium trust) and creating immutable `record_edits` audit records.
- **No Schema Conflicts:** Day 7 stays strictly on schema v14, avoiding collisions with lead developer Usman's schema v15 migration.

---

## 4. Test & Verification Metrics

| Gate | Target / Requirement | Result | Status |
|---|---|---|---|
| Backend Hermetic Pytest Suite | All test files hermetic | **1,412 passed**, 1 deselected | **PASS** |
| Frontend Vitest Suite | All test files passing | **247 passed** (28 test files) | **PASS** |
| Mutation Coverage | 39 / 39 killed | **39 / 39 killed** (100%) | **PASS** |
| Next.js Production Build | `npm run build` static export | Export completed without errors | **PASS** |
| Protected Core Files | 8 protected files byte-identical | Verified identical SHA-256 | **PASS** |
| Static Linting | Ruff correctness gate | Clean (0 errors) | **PASS** |

---

## 5. Next Steps (Week 3 Outlook)

1. Assist with the upcoming cross-team bug bash and usability trials with ~5 test users.
2. Coordinate with clinical reviewers on danger phrase screening rules for edge-case Urdu expressions.
3. Prepare production rollout of OCR feature flag pending Usman's cloud runtime validation.
