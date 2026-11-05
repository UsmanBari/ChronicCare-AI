# Architectural Decision Record: Retention of v2 as Production Default (Release 2)

**Decision Date:** 5 November 2026  
**Decision Maker:** Usman Bari  
**Status:** Decided & Enforced  
**Context:** Release 2 (Week 3)  

---

## 1. Context & Status of PR #113

During Week 3 of the ChronicCare AI roadmap, Muhammad Hassaan Mudassar developed PR #113 on branch `feat/i3-v3-readiness` to address v3 interview readiness gaps (G-02 unclear adherence handling, G-14 caregiver vernacular in Roman Urdu) and evaluate production readiness:

```text
113	feat(interview): v3 readiness gaps G-02 and G-14, readiness report, a…	feat/i3-v3-readiness	OPEN	2026-11-04T16:49:35Z
```

As part of PR #113, Hassaan evaluated 64 standardized clinical personas dynamically simulated across both engines (`scripts/v3_readiness_report.py`) and documented the measured evaluation in `docs/V3_READINESS.md`.

---

## 2. Decision

For **Release 2**, the production system strictly retains **v2 as the default interview engine**:
- `INTERVIEW_ENGINE=v2` (default)
- `v2` remains the active production engine in all deployments.
- `v3` remains intact in the codebase behind the `INTERVIEW_ENGINE=v3` configuration flag for continued validation and testing.

---

## 3. Rationale: Measured NO-GO in PR #113 Readiness Report

The objective readiness criteria defined in `docs/INTERVIEW_AUDIT.md` Section 6 require that an interview engine change must introduce **zero demotions** on clinical triage levels.

The measured readiness evaluation conducted on 4 November 2026 in PR #113 yielded a computed **NO-GO** verdict:

1. **Gate 3 (Persona Invariance & Demotion Audit) FAILED:**
   - Out of 64 standardized clinical personas evaluated across both engines, v3 resulted in **18 demotions** where the final triage level assigned was lower than the v2 baseline (`v3 < v2`).
   - While zero chest pain emergencies were missed, our core medical safety invariant is: *"never lower a triage level"*. Under no circumstance can an interview engine demote clinical triage levels compared to established protocol.

2. **Progress in PR #113 (Non-Doctor Gaps Resolved):**
   - PR #113 successfully validated:
     - **G-02 Unclear Adherence:** Clarifies once; routes to clinician review if unresolved (`test_v3_adherence_unclear.py` 32/32 pass).
     - **G-14 Caregiver Vernacular:** Correctly preserves readings with `answered_by="caregiver"` (`test_v3_caregiver_roman_ur.py` 36/36 pass).
     - **No English-Only Leakage:** 0 leaks across 79 patient-facing strings in Urdu and Roman Urdu.
     - **Hermetic Equivalence:** 7/7 clinical scenario tests pass in `test_engine_equivalence.py`.
   - However, until the 18 persona demotions are fully resolved and eliminated, v3 cannot be promoted to the production default.

---

## 4. Preservation of v3 for Continued Development

The v3 codebase is **not** deleted; it remains fully functional, integrated, and actively tested in the repository:
- All v3 modules (`agents/interview_planner.py`, `agents/interview_findings.py`, `agents/interview_bank/`, `agents/interview_v3_runner.py`) remain active.
- Operators and researchers can run ChronicCare AI in v3 mode at any time by configuring:
  ```bash
  INTERVIEW_ENGINE=v3
  ```
- All equivalence tests (`test_engine_equivalence.py`) and mutation proofs (`test_mutation_proofs_v3.py`) remain active and green in CI to ensure that v3 continues to advance alongside v2 without bit rot.
