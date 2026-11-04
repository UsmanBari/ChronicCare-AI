# Architectural Decision Record: Retention of v2 as Production Default (Release 2)

**Decision Date:** 5 November 2026  
**Decision Maker:** Usman Bari  
**Status:** Decided & Enforced  
**Context:** Release 2 (Week 3)  

---

## 1. Context & Background

During Week 3 of the ChronicCare AI roadmap, an adaptive interview engine (v3) and a state-graph orchestrator (LangGraph) were developed to explore dynamic question ordering, multilingual slot filling, and adaptive probing based on patient-reported symptoms. 

In parallel, comprehensive parity suites, mutation proofs, and deterministic benchmark evaluations were executed comparing:
1. **Engine v2:** Rule-based deterministic interview state machine (`agents/adaptive_interview_agent.py`) paired with direct sequential orchestrator (`orchestrator/direct.py`).
2. **Engine v3:** Adaptive question bank planner (`agents/interview_planner.py`), dynamic finding tracker (`agents/interview_findings.py`), and LangGraph state graph (`orchestrator/graph.py`).

---

## 2. Decision

For **Release 2**, the production system strictly retains **v2 as the default interview and orchestrator engine**:
- `INTERVIEW_ENGINE=v2` (default)
- `ORCHESTRATOR=direct` (default)

**PR #113** (which proposed switching the defaults to v3) **remains unmerged** on the `dev` branch.

---

## 3. Rationale

1. **Deterministic Medical Safety ("The model proposes, the rules decide"):**
   - In clinical triage, predictability and reproducibility are paramount. Engine v2 follows an ironclad, deterministic finite state machine validated against all clinical protocols in `docs/CLINICAL_RULES.md`.
   - Engine v2 delivers 100% consistent turn-by-turn question paths with zero risk of slot starvation or dynamic probe drift.

2. **Proven Production Stability:**
   - The direct orchestrator and v2 interview state machine have zero runtime dependencies on external graph executors or dynamic graph compilation, ensuring ultra-low latency ($\approx 0.09\text{s}$ p50 check-in completion) and near-zero memory overhead.

3. **Clinician Trust & Verification:**
   - Clinicians have evaluated and approved the specific question order and fast-path skip rules encoded in v2 (e.g. glucose context extraction, fasting status confirmation, and red-flag escalation).

---

## 4. Status of Engine v3 & LangGraph

The v3 codebase is **not** deleted; it remains fully functional, integrated, and actively tested in the repository:
- All v3 modules (`agents/interview_planner.py`, `agents/interview_findings.py`, `agents/interview_bank/`, `agents/interview_v3_runner.py`, `orchestrator/graph.py`) are fully maintained and verified by automated CI test suites.
- Operators and researchers can run ChronicCare AI in v3 mode at any time by configuring:
  ```bash
  INTERVIEW_ENGINE=v3
  ORCHESTRATOR=graph
  ```
- All equivalence tests (`test_engine_equivalence.py`, `test_orchestrator_equivalence.py`) and mutation proofs (`test_mutation_proofs_v3.py`) remain active and green in CI to ensure that v3 continues to advance alongside v2 without bit rot.
