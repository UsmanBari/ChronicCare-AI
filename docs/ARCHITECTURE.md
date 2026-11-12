# ChronicCare AI Architecture & System Topology

> **System Motto**: *"The model proposes, the rules decide."*  
> **Status**: Verified Against Repository Code (5 November 2026)  
> **Deployment Context**: Research prototype for adults with type 2 diabetes and hypertension. Decision support only; never diagnoses, never prescribes, never lowers a triage level.

---

## 1. System Diagrams

The system architecture is partitioned into two clear views plus reference tables:
1. **Check-In Lifecycle Overview**: Left-to-right end-to-end execution from intake to provider review.
2. **Clinical Explainer Path**: Asynchronous queue, background worker, sequential guards, validators, storage, and endpoints.
3. **Configuration & Data Topology**: Active feature flags and physical vs. volatile storage state.

---

### Diagram A: Check-In Lifecycle Overview

End-to-end check-in processing: Patient Entry & Adaptive Interview $\rightarrow$ Safety Screens $\rightarrow$ Dual Orchestrator $\rightarrow$ Deterministic Clinical Decision & Risk Gate $\rightarrow$ Checkin Save & Async Job Enqueue $\rightarrow$ Immediate Response & Clinician Review Queue.

![Check-In Lifecycle Overview](img/architecture_overview.png)

*¹ = behind a feature flag, off by default.*

*Visual renderings available in repository: [PNG](img/architecture_overview.png) | [SVG](img/architecture_overview.svg)*

---

### Diagram B: Resilient Explainer Path

End-to-end background explanation path: Bounded FIFO Queue $\rightarrow$ Daemon Worker $\rightarrow$ Multi-Provider LLM Loop with HTTP 429 Retry $\rightarrow$ Clinical Output Validators $\rightarrow$ Fallback Template Path (with H2 Consistency Guard) $\rightarrow$ Result Storage $\rightarrow$ Polling & Review Endpoints.

![Resilient Explainer Path](img/architecture_explainer.png)

*¹ = behind a feature flag, off by default.*

*Visual renderings available in repository: [PNG](img/architecture_explainer.png) | [SVG](img/architecture_explainer.svg)*

---

### Re-rendering the Diagrams

To re-render the PNG and SVG diagrams from their source files in `docs/img/src/`:

```bash
mmdc -i docs/img/src/<name>.mmd -o docs/img/<name>.png -c docs/img/src/mermaid_config.json -b white -s 3
mmdc -i docs/img/src/<name>.mmd -o docs/img/<name>.svg -c docs/img/src/mermaid_config.json -b white
```

*(replace `<name>` with `architecture_overview` or `architecture_explainer`)*

---

### Sequential Order of `guarded_explain` Execution

The clinical explanation pipeline executes in strict sequential order inside `backend-poc-technical/rag/explain_guards.py`:

1. **Candidate Chunk Retrieval** (`rag/explain_guards.py:992–1009`): Executes BM25 keyword query mapping based on triage trigger and condition (top 3 chunks).
2. **Safety Re-Validation Cache Lookup** (`rag/explain_guards.py:1010–1025`): Checks in-memory LRU cache keyed on `(trigger, level, glucose_band, bp_band, lang, cond)`. Re-validates cached output against current readings before returning hit.
3. **Condition Gate (H1)** (`rag/explain_guards.py:1060–1063`): Non-hypertension check-ins (e.g., diabetes) are gated to deterministic template fallbacks until formal guideline licensing is integrated.
4. **Candidate Chunk Existence Check** (`rag/explain_guards.py:1064–1067`): If no relevant guideline passages exist in the chunk store, falls back to `no_chunks` template.
5. **G3 Licence Restriction Gate** (`rag/explain_guards.py:1068–1073`): Inspects candidate chunk `source_id` against `LICENCE_RESTRICTED_SOURCES` (`ada_2026`, `aha_acc_2025`). If restricted, Gemini is prohibited from processing the request.
6. **Candidate Provider Resolution & Circuit Breakers** (`rag/explain_guards.py:1074–1132`): Evaluates configured providers (`groq`, `gemini`), trips on open circuit breaker (`breaker_open`), and respects 150k daily token cap (`token_cap`).
7. **Worker Concurrency Limit** (`rag/explain_guards.py:1133–1137`): Non-blocking acquire on `_WORKER_SEMAPHORE`; returns `busy` template if the worker pool is saturated.
8. **Groq Output Token Pacer** (`rag/explain_guards.py:1163–1174`): In background mode, checks the sliding 60-second output token window. If projected tokens exceed 1000 tokens/min, sleeps for the required interval or falls back to Gemini.
9. **Provider Invocation & HTTP 429 Handling** (`rag/explain_guards.py:1309–1327`): In background mode, if an LLM returns HTTP 429, the system parses the `Retry-After` header, waits that exact duration, and executes **one retry**. It does not trip the circuit breaker unless the retry fails.
10. **Clinical Output Validators (V1–V5)** (`rag/explainer.py:165–280`): Enforces JSON schema, citation format (`[S1]`), grounding within retrieved text, prohibition of false reassurance, and clinical level word consistency.
11. **Template Consistency Guard (H2)** (`rag/explainer.py:285–375`): Invariant check: if an explanation or template contradicts physiological readings, it is substituted with a neutral routine template.
12. **Cache Insertion & Provider Segregation** (`rag/explain_guards.py:1370–1390`): Caches validated responses. Segregates internal telemetry (`provider`, `providers_tried`, `provider_timings`, `tokens_used`) so it is stored exclusively for clinicians and strictly excluded from the patient view.

---

### Verified Graph Node Definitions
The orchestrator graph nodes correspond directly to the compiled LangGraph `StateGraph` definition in `backend-poc-technical/orchestrator/graph.py`:

```text
backend-poc-technical\orchestrator\graph.py:407:    builder.add_node("intake", node_intake)
backend-poc-technical\orchestrator\graph.py:408:    builder.add_node("fetch_prior", node_fetch_prior)
backend-poc-technical\orchestrator\graph.py:409:    builder.add_node("build_bundles", node_build_bundles)
backend-poc-technical\orchestrator\graph.py:410:    builder.add_node("reconcile", node_reconcile)
backend-poc-technical\orchestrator\graph.py:411:    builder.add_node("verify", node_verify)
backend-poc-technical\orchestrator\graph.py:412:    builder.add_node("persist_local", node_persist_local)
backend-poc-technical\orchestrator\graph.py:413:    builder.add_node("decide_triage", node_decide_triage)
backend-poc-technical\orchestrator\graph.py:414:    builder.add_node("risk", node_risk)
backend-poc-technical\orchestrator\graph.py:415:    builder.add_node("explain", node_explain)
backend-poc-technical\orchestrator\graph.py:416:    builder.add_node("persist", node_persist)
```

---

## 2. Configuration & Feature Flags Reference

The following table documents all system feature flags, their production default states, their behavioral scope, and their exact source code call sites (reported via `GET /api/admin/config-status`):

| Feature Flag | Default | Functional Description | Source Call Site (`file:line`) |
|---|:---:|---|---|
| `RISK_ENABLED` | `false` | NHANES diabetes risk model (`agents/risk_agent.py`) + raise-only rule (`agents/risk_rules.py`), provider view only. Strictly hidden from patients. | [`backend-poc-technical/orchestrator/steps.py:692`](../backend-poc-technical/orchestrator/steps.py#L692)<br>[`backend-poc-technical/agents/risk_rules.py:46`](../backend-poc-technical/agents/risk_rules.py#L46) |
| `RISK_CAN_RAISE` | `false` | When true, permits an elevated high-risk score to elevate a `routine` check-in to `review`. Strictly prohibited from lowering any triage level or altering urgent/emergency levels. | [`backend-poc-technical/agents/risk_rules.py:47`](../backend-poc-technical/agents/risk_rules.py#L47) |
| `EXPLAIN_ENABLED` | `false` | Master switch for the clinical explainer layer. When false, check-ins return static neutral template explanations and zero external LLM provider calls occur. | [`backend-poc-technical/orchestrator/steps.py:779`](../backend-poc-technical/orchestrator/steps.py#L779) |
| `EXPLAIN_MODE` | `background` | Controls execution mode of the explainer: `background` queues jobs to an asynchronous in-process worker returning pending immediately; `inline` executes within the HTTP completion cycle. | [`backend-poc-technical/rag/explain_guards.py:182`](../backend-poc-technical/rag/explain_guards.py#L182) |
| `OCR_ENABLED` | `false` | Enables upload and client-side/server-side processing of lab reports and prescriptions via OCR endpoints (`/api/ocr/upload`). | [`backend-poc-technical/main.py:2769`](../backend-poc-technical/main.py#L2769)<br>[`backend-poc-technical/main.py:2920`](../backend-poc-technical/main.py#L2920) |
| `DANGER_WORDGROUPS_ENABLED` | `false` | Activates regex word-group screening layer v1.1 (`agents/danger_wordgroups.py`) to catch red flags and elevate routine check-ins to `review`. Raise-only invariant enforced. | [`backend-poc-technical/agents/danger_wordgroups.py:41`](../backend-poc-technical/agents/danger_wordgroups.py#L41) |
| `ORCHESTRATOR` | `direct` | Selects between the direct in-process step pipeline (`direct`) and the compiled LangGraph pipeline (`graph`). Both paths are verified 100% equivalent (78/78 cases). | [`backend-poc-technical/main.py:913`](../backend-poc-technical/main.py#L913)<br>[`backend-poc-technical/main.py:4833`](../backend-poc-technical/main.py#L4833) |
| `INTERVIEW_ENGINE` | `v2` | Selects the active patient interview engine. Retained at `v2` default for Release 2 based on measured NO-GO in `docs/V3_READINESS.md`. `v3` accessible behind flag. | [`backend-poc-technical/agents/interview_v3_runner.py:58`](../backend-poc-technical/agents/interview_v3_runner.py#L58) |
| `LLM_PROVIDER` | `auto` | Routing policy across LLM providers (`auto`, `groq`, `gemini`). In `auto`, attempts primary provider (Groq) with transparent fallback to secondary (Gemini) on 429/timeout. | [`backend-poc-technical/rag/explain_guards.py:143`](../backend-poc-technical/rag/explain_guards.py#L143) |
| `SCREENING_REMINDER_INTERVAL_DAYS` | `90` | Clinical cadence interval in days for diabetic foot and retinopathy screening reminders. | [`backend-poc-technical/agents/screening_reminder.py:19`](../backend-poc-technical/agents/screening_reminder.py#L19) |

---

## 3. Data Storage & Volatile State Architecture

The following table delineates physical persistent stores, guideline corpora, and volatile in-memory resiliency state:

| Layer / Store | Technology / Scope | Entities Stored | Lifecycle / Invariants |
|---|---|---|---|
| **Production Application Database** | Aiven Cloud Managed MySQL (InnoDB, UTF8mb4) | `users`, `patient_profiles`, `checkins`, `checkin_results`, `review_actions`, `record_edits`, `guideline_chunks`, `schema_version` (v15) | Persistent relational store. Enforces foreign key cascades, role segregation, and immutable audit logs. |
| **Local Development Database** | SQLite 3 (`app_data.db` / `local_store.db`) | Application tables matching MySQL schema v15 + synthetic EHR tables (`patients`, `observations`, `conditions`, `medications`). | Isolated hermetic development and test execution. Supports offline automated CI suites. |
| **Guideline Chunk Knowledgebase** | Relational table `guideline_chunks` (SQLite & MySQL) | Validated medical guideline passages (WHO, ISH, CDC, NICE, ADA). Fields: `chunk_id`, `source_id`, `title`, `condition`, `text`, `loaded_at`. | Seeded via `scripts/seed_guideline_chunks.py`. Licence rule G3 prohibits sending ADA restricted chunks to Gemini. |
| **Explainer Token Cap Trackers** | In-Memory Volatile Singletons (`TokenCapGuard`) | `tokens_used_today` tracked separately for Groq and Gemini. | Hard caps (150,000 tokens/day). Resets automatically per UTC midnight. Resets on process restart. |
| **Provider Circuit Breakers** | In-Memory Volatile Singletons (`CircuitBreaker`) | State (`closed`, `open`, `half-open`), failure counters, trip timestamps. | Trips after 3 consecutive timeouts/errors or HTTP 429 rate limits. Cooldown 600s. Resets on restart. |
| **Explainer LRU Cache** | In-Memory Volatile OrderedDict (`ExplainCache`) | Up to 100 validated clinical explanations keyed by `(condition, reading_band, language, decided_level)`. | Prevents redundant LLM calls on identical physiological ranges. Re-validates citations on hit. Resets on restart. |
| **Groq Output Token Pacer** | In-Memory Volatile Deque (`TokenPacer`) | Sliding 60-second window recording Groq completion token usage. | Prevents hitting Groq free-tier rate limits (1000 output tokens/min). Waits before call if limit reached. Resets on restart. |
| **Background Job Queue** | In-Memory Volatile FIFO Queue (`ExplanationJobQueue`) | Bounded queue (`queue.Queue(maxsize=50)`) holding pending `ExplanationJob` instances. | Decouples check-in completion from LLM latency. In-flight jobs drop to template on process termination. |
| **SMART FHIR Client Cache** | In-Memory Volatile Dictionary (`_FHIR_CACHE`) | Transient FHIR observation bundles keyed by patient ID. | 300s TTL. Cleared on demand when patient revokes EHR connection. |
| **SOAP Clinical Summary Agent (Agent 7)** | In-Process Agent (`agents/soap_agent.py`) | Deterministic S/O/A/P clinical synthesis; exports FHIR R4 `DocumentReference` to FhirSim in connected mode. | Provider-only endpoint `GET /api/provider/review/{checkin_id}/soap`. Zero LLM, zero invented values. |
