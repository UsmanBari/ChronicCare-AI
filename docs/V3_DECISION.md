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

## 3. Rationale: Measured NO-GO in docs/V3_READINESS.md

The objective readiness criteria defined in `docs/INTERVIEW_AUDIT.md` Section 6 require that an interview engine change must introduce zero demotions on clinical triage levels and satisfy full persona invariance.

The measured readiness evaluation documented in `docs/V3_READINESS.md` yielded a computed **NO-GO** verdict across the 64 persona evaluation suite:

1. **Gate 3 (Persona Invariance & Demotion Audit) FAILED:**
   - **Total Personas Simulated:** 64
   - **V3 Misses (v3 below expected level, v2 not):** 4
   - **Both Miss (both v2 and v3 below expected):** 8
   - **Demotions Below v2 (`v3 < v2`):** 1 (`p24_dont_know_to_everything`: v2 emergency $\rightarrow$ v3 review)
   - **Incomplete Runs (v2 / v3):** 0 / 0
   - **V2 Over-triages Resolved:** 7
   - While zero chest pain emergencies were missed, our core medical safety invariant is: *"the model proposes, the rules decide; never lower a triage level"*. Because v3 exhibits 4 V3 misses below expected level and 1 demotion below v2, v2 stays the default for Release 2.

2. **Progress in PR #113 (Non-Doctor Gaps Resolved):**
   - PR #113 successfully resolved and verified non-doctor readiness gaps:
     - **G-02 Unclear Adherence Handling:** Clarifies once; unresolved routes to clinician review (`test_v3_adherence_unclear.py` 32/32 pass).
     - **G-14 Caregiver Vernacular & Slot Safety:** Correctly preserves readings with `answered_by="caregiver"` in Roman Urdu without leaking yes/no (`test_v3_caregiver_roman_ur.py` 39/39 pass).
     - **No English-Only Leakage:** 0 leaks across 79 patient-facing strings in Urdu and Roman Urdu.
     - **Hermetic Equivalence:** 7/7 clinical scenario tests pass in `test_engine_equivalence.py`.
   - However, until the rule questions behind the 4 V3 misses and 8 both-misses are resolved with clinical advisors, v3 cannot be promoted to the production default. Thus, v2 stays the default for Release 2.

---

## 4. Preservation of v3 for Continued Development

The v3 codebase is **not** deleted; it remains fully functional, integrated, and actively tested in the repository:
- All v3 modules (`agents/interview_planner.py`, `agents/interview_findings.py`, `agents/interview_bank/`, `agents/interview_v3_runner.py`) remain active.
- Operators and researchers can run ChronicCare AI in v3 mode at any time by configuring:
  ```bash
  INTERVIEW_ENGINE=v3
  ```
- All equivalence tests (`test_engine_equivalence.py`) and mutation proofs (`test_mutation_proofs_v3.py`) remain active and green in CI to ensure that v3 continues to advance alongside v2 without bit rot.
