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
ADA Standards of Care in Diabetes—2026, Sections 2, 5, 6, 10, 11, and 13: written permission received on 5 Nov 2026 for academic evaluation at FAST-NUCES Islamabad (1 Nov 2026 to 30 Jun 2027) with conditions (details in `docs/licences/ADA_2026_PERMISSION.md`). Plain-language explanations are generated from these sections exclusively via the Groq API and are strictly prohibited from being sent to Google Gemini (Rule G3). All stored ADA material will be permanently deleted upon conclusion of the approved period on 30 June 2027 (`scripts/rag/delete_source.py --licence ada_2026 --yes`). AHA/ACC 2025: not permitted, completely blocked. The active RAG retrieval index incorporates these permitted ADA sections alongside open-access and public-domain medical guidelines (WHO 2021, ISH 2020, IDF-DAR 2021, detailed in `docs/GUIDELINE_CORPUS.md`). No proprietary guideline text is committed into Git or retrieved without explicit written licensing.

### 4. Gemini Free-Tier Data Privacy
Google Gemini API models (`gemini-2.5-flash` and `gemini-flash-latest`) operate under standard free-tier developer terms where prompts may be retained for product improvement. To protect data privacy, only synthetic and fabricated data is ever transmitted to external LLM providers. Identifiable patient health information (PHI) is strictly excluded, and all test users employ `fake-` or `TEST_` identifiers.

### 5. Exclusively Synthetic and Simulated Data
All evaluations, demonstrations, automated tests, and local databases operate entirely on synthetic datasets. Data sources comprise SMART on FHIR sandbox records, Synthea patient graphs, and 64 simulated persona configurations (`tests/sim/personas.json`). No real patient health records or genuine hospital charts have been ingested or processed by the system.

### 6. Volatile In-Memory Operational State
Key operational safeguards—including the Groq and Gemini circuit breakers, token usage meters, explanation response caches, and the asynchronous background job queue—are maintained in ephemeral process memory (`rag/explain_guards.py`, `rag/explain_jobs.py`). In this single-instance deployment architecture, restarting the backend application server or worker thread resets all rate counters, circuit breakers, and pending job queues.

### 7. Explanation Validation Scope & Live Smoke Test Corpus
Deterministic template explanations have been verified by the engineering team (40/40 pass rate, median latency $p50 = 0.0\text{ ms}$, 20/20 clarity score in `docs/EXPLAIN_EVAL.md`). However, LLM-generated explanations have only been smoke-tested on synthetic "review"-level check-ins (`scripts/explain_live_smoke.py`). Crucially, earlier live smoke runs on 5 November and 6 November 2026 operated against a fixture of 4 hand-written synthetic test chunks (`c_htn_1`, `c_htn_2`, `c_dm_1`, `c_dm_2`) rather than the full guideline corpus.

When Usman executed live smoke evaluation against the complete loaded corpus (6 Nov, `--real-chunks`, 1,175 chunks including 6 permitted ADA sections), both conditions failed the Release 2 operational threshold ($\ge 9/10$ LLM or cache resolution):
- **Diabetes:** 4/10 (3 LLM + 1 cache), with 6 template fallbacks caused by 4 Urdu/Roman Urdu `JSONDecodeError` events and 2 subsequent circuit-breaker open fallbacks.
- **Hypertension:** 4/10, where 7 of 10 rows incorrectly retrieved and cited ADA diabetes guidelines (`ada_2026_sec05`, `ada_2026_sec10`).

Three root causes were diagnosed:
1. Shared completion token cap (`max_tokens: 250`) truncated higher-density Urdu script JSON translations mid-string.
2. Truncation and malformed JSON errors were caught generically as upstream execution outages, incrementing the circuit breaker failure counter and tripping the breaker after 3 failures.
3. Retriever queries without condition bounds or broad fallback matching allowed ADA diabetes sections to leak into hypertension-only check-in candidates.

These issues were addressed in Day 6e by decoupling translation token budgets (`EXPLAIN_TRANSLATION_MAX_TOKENS=700`), classifying parse errors strictly as `validation_failed` without tripping circuit breakers, and enforcing patient-level condition filtering.

Following PR #123, Usman's real-corpus smoke re-run (6 Nov, 22:20) showed diabetes passed the operational threshold at 10/10 (6 LLM + 4 cache, 0 fallbacks), while hypertension reached only 3/10 (3 LLM, 0 cache, 7 template fallbacks on routine check-ins with reason `no_chunks`). Because the post-retrieval filter operated after BM25 ranking had already selected the top 3 chunks, the routine query (`condition='both'`) scored diabetes chunks (ADA, IDF-DAR, AKU) above hypertension chunks; stripping them post-retrieval left zero chunks for hypertension-only patients. In Day 6f, diabetes guidelines (ADA, IDF-DAR, AKU) are left out before ranking for patients without diabetes (`exclude_source_prefixes=DIABETES_ONLY_SOURCE_PREFIXES`), allowing hypertension guidelines to occupy the top 3 rankings. Dual-condition and diabetic patients retain access.

Following PR #125, Usman re-ran the real-corpus smoke (7 Nov, 06:45). Diabetes passed again at 10/10 (100%), but hypertension reached 6/10 (4 LLM + 2 cache, 4 fallbacks). The PR #125 pre-ranking fix was verified: routine rows cited `ish_2020_htn` and `who_2021_htn` without ADA/IDF/AKU and with zero `no_chunks` rejections. All 4 failures were Urdu and Roman Urdu routine rows. In background mode when Gemini was a possible next provider, Groq was allocated a 20 s per-call provider timeout (`EXPLAIN_CALL_TIMEOUT_SECONDS`), and the OTPM pacer evaluated its wait against this 20 s provider deadline rather than the 45 s overall job deadline. Needing ~30 s of wait for the 700-token Urdu translation, Groq timed out with `Pacer wait exceeds deadline` and fell back to Gemini, which then failed under free-tier concurrency limits. In Day 6g, pacer waits evaluate against the overall job deadline, extending the provider join deadline to enable successful Groq Urdu generation within the job window. Independent clinician evaluations across urgent and emergency triage categories remain pending for Release 2.

### 8. Interview Engine v3 Readiness & Both-Miss Personas
The conversational v3 interview engine remains gated behind the `INTERVIEW_ENGINE="v3"` flag and is deemed NO-GO for Release 2 default (`docs/V3_DECISION.md`). Across benchmark evaluation on 64 clinical personas (`docs/V3_READINESS.md`), v3 missed 4 triage decisions, and both v2 and v3 missed 8 complex multi-condition personas (P013, P015, P016, P028, P035, P044, P046, P061). Resolving these edge cases requires formal clinician consensus on complex symptom interactions, which is deferred to FYP-2.

### 9. Urdu Danger-Phrase Sensitivity on Held-Out Sets
While the composable word-groups engine (`DANGER_WORDGROUPS_ENABLED`) markedly improves vernacular Urdu red-flag detection compared to baseline v2 (65.0% vs 20.0% on Hassaan Urdu Independent; 40.0% vs 20.0% on Saad Independent; 35.0% vs 10.0% on Saad Blind Urdu; 60.0% vs 6.7% on Saad Independent R2, as reported in `docs/V3_READINESS.md:38-41`), recall remains incomplete. Non-standard phonetic spellings, colloquial regional idioms, and atypical dialect phrasing can still bypass keyword detection, requiring the mandatory presence of manual clinician review queues.

### 10. Small OCR Sample Size
Server-side prescription and lab OCR evaluation (`docs/ocr/`) was conducted on an exploratory sample of 9 handwritten and printed Pakistani medication slips. Although RapidOCR demonstrated superior item extraction relative to client-side Tesseract.js (9/9 vs 1/9 legible items), this small sample does not establish statistical reliability across the wide variation in Pakistani physician handwriting, uncalibrated mobile cameras, or damaged paper slips.

### 11. Groq Free-Tier Capacity & Gemini Free-Tier Reliability Limits
The Groq free tier enforces a strict output token limit of 1000 tokens/min, quoted from the 429 message in the 4 Nov smoke ("Rate limit reached for model `llama-3.3-70b-versatile`... Limit 1000"). Under burst check-in loads, this capacity constraint can lead to immediate 429 rate-limiting. For bilingual Urdu explanations (which require ~200-250 tokens for English generation followed by ~500-700 tokens for Urdu translation due to Nastaliq Unicode density in JSON), each Urdu check-in consumes 700–950 completion tokens in a single request pair. As a result, the Groq free tier capacity is effectively limited to **~1 Urdu explanation per minute**. Consecutive Urdu check-ins trigger pacing waits of ~30 s from the rolling token pacer, extending background completion latency.

Furthermore, Google Gemini API free tier (`gemini-2.5-flash`, `gemini-flash-latest`) has exhibited operational unreliability under burst requests, including upstream HTTP 503 Service Unavailable and ReadTimeout errors. Relying on Gemini as an automated fallback when Groq experiences pacing delays proved fragile during real-corpus smoke testing, emphasizing the importance of permitting the primary Groq worker to wait within the 45 s job deadline rather than failing over prematurely to an unstable free-tier secondary provider.

### 12. Pending Formal Usability Testing
No formal usability, accessibility, or human-factors studies have been completed with actual elderly or low-literacy patients in Pakistan. Formal patient and clinician usability trials using the bilingual interface are scheduled for 11–14 November 2026.

