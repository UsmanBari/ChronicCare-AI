# ChronicCare AI — System Limitations & Constraints

> [!CAUTION]
> **Research prototype for decision-support evaluation only. Not a medical device.**
> "Doctor review is not clinical validation."

This document records the clinical, technical, operational, and regulatory limitations of ChronicCare AI as of Week 3 (5 November 2026). Every constraint is stated plainly to maintain scientific and engineering integrity for the FYP-1 report, academic paper, and system demonstrations.

---

### 1. Research Prototype & Lack of Clinical Validation in Pakistan
"Doctor review is not clinical validation." ChronicCare AI is an experimental academic decision-support prototype. It has not undergone clinical trials, medical device certification, or real-world testing with chronic disease patients in Pakistan. Feedback obtained from local clinicians (Dr. Shaiza Jabbar, Capt. Dr. Talha Yasin, Dr. Anam Zafar, and Doctor C in `docs/CLINICIAN_RESPONSES.md`) provided preliminary domain guidance on safety thresholds and danger phrasing, but does not constitute clinical validation or regulatory approval.

### 2. Decision Support, Not a Medical Device
The system provides non-diagnostic decision support and monitoring triage. It is not a certified Software as a Medical Device (SaMD) under Pakistan Drug Regulatory Authority (DRAP) regulations or US FDA non-device clinical decision support guidance. It never diagnoses medical conditions, never prescribes treatments, and never alters medication dosages. Its operating motto is "the model proposes, the rules decide." All clinical triage decisions and safety interventions must be supervised and confirmed by licensed healthcare practitioners.

### 3. Guideline Licences and Retrieval Restrictions
ADA Standards of Care 2026, Sections 2, 5, 6, 10, 11 and 13: written permission received on 5 Nov 2026 for academic evaluation (Nov 2026 to Jun 2027), with conditions; integration is a separate PR (Day 6b). Until it is merged and evaluated, diabetes explanations are templates. AHA/ACC 2025: not permitted, blocked. The active RAG retrieval index is strictly confined to open-access and public-domain medical guidelines (WHO 2021, ISH 2020, NICE NG136, VA/DoD 2020, and CDC diabetes factsheets, detailed in `docs/GUIDELINE_CORPUS.md`). No proprietary guideline text is committed or retrieved without explicit written licensing.

### 4. Gemini Free-Tier Data Privacy
Google Gemini API models (`gemini-2.5-flash` and `gemini-flash-latest`) operate under standard free-tier developer terms where prompts may be retained for product improvement. To protect data privacy, only synthetic and fabricated data is ever transmitted to external LLM providers. Identifiable patient health information (PHI) is strictly excluded, and all test users employ `fake-` or `TEST_` identifiers.

### 5. Exclusively Synthetic and Simulated Data
All evaluations, demonstrations, automated tests, and local databases operate entirely on synthetic datasets. Data sources comprise SMART on FHIR sandbox records, Synthea patient graphs, and 64 simulated persona configurations (`tests/sim/personas.json`). No real patient health records or genuine hospital charts have been ingested or processed by the system.

### 6. Volatile In-Memory Operational State
Key operational safeguards—including the Groq and Gemini circuit breakers, token usage meters, explanation response caches, and the asynchronous background job queue—are maintained in ephemeral process memory (`rag/explain_guards.py`, `rag/explain_jobs.py`). In this single-instance deployment architecture, restarting the backend application server or worker thread resets all rate counters, circuit breakers, and pending job queues.

### 7. Explanation Validation Scope
Deterministic template explanations have been verified by the engineering team (40/40 pass rate, median latency $p50 = 0.0\text{ ms}$, 20/20 clarity score in `docs/EXPLAIN_EVAL.md`). However, LLM-generated explanations have only been smoke-tested on synthetic "review"-level check-ins (`scripts/explain_live_smoke.py`). LLM explanations have not yet been evaluated by independent clinicians across urgent or emergency triage categories.

### 8. Interview Engine v3 Readiness & Both-Miss Personas
The conversational v3 interview engine remains gated behind the `INTERVIEW_ENGINE="v3"` flag and is deemed NO-GO for Release 2 default (`docs/V3_DECISION.md`). Across benchmark evaluation on 64 clinical personas (`docs/V3_READINESS.md`), v3 missed 4 triage decisions, and both v2 and v3 missed 8 complex multi-condition personas (P013, P015, P016, P028, P035, P044, P046, P061). Resolving these edge cases requires formal clinician consensus on complex symptom interactions, which is deferred to FYP-2.

### 9. Urdu Danger-Phrase Sensitivity on Held-Out Sets
While the composable word-groups engine (`DANGER_WORDGROUPS_ENABLED`) markedly improves vernacular Urdu red-flag detection compared to baseline v2 (65.0% vs 20.0% on Hassaan Urdu Independent; 40.0% vs 20.0% on Saad Independent; 35.0% vs 10.0% on Saad Blind Urdu; 60.0% vs 6.7% on Saad Independent R2, as reported in `docs/V3_READINESS.md:38-41`), recall remains incomplete. Non-standard phonetic spellings, colloquial regional idioms, and atypical dialect phrasing can still bypass keyword detection, requiring the mandatory presence of manual clinician review queues.

### 10. Small OCR Sample Size
Server-side prescription and lab OCR evaluation (`docs/ocr/`) was conducted on an exploratory sample of 9 handwritten and printed Pakistani medication slips. Although RapidOCR demonstrated superior item extraction relative to client-side Tesseract.js (9/9 vs 1/9 legible items), this small sample does not establish statistical reliability across the wide variation in Pakistani physician handwriting, uncalibrated mobile cameras, or damaged paper slips.

### 11. Groq Free-Tier Capacity & Rate Limits
The Groq free tier enforces a strict output token limit of 1000 tokens/min, quoted from the 429 message in the 4 Nov smoke ("Rate limit reached for model `llama-3.3-70b-versatile`... Limit 1000"). Under burst check-in loads, this capacity constraint can lead to immediate 429 rate-limiting. The system handles this through an internal rate pacer and automatic fallback to deterministic templates, but high-concurrency throughput is constrained without paid API tiers.

### 12. Pending Formal Usability Testing
No formal usability, accessibility, or human-factors studies have been completed with actual elderly or low-literacy patients in Pakistan. Formal patient and clinician usability trials using the bilingual interface are scheduled for 11–14 November 2026.

