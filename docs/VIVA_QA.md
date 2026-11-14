# ChronicCare AI — FYP-1 Viva Preparation: 25 Core Examiner Q&A

> **Purpose:** Plain-language, spoken-English answers to the 25 most critical viva questions examiners ask during project evaluation.  
> **Grounding:** Every single answer is grounded in exact file citations, proven numbers, and architecture implementations.  
> **Date:** November 2026  
> **Project:** ChronicCare AI — Outpatient Chronic Disease Tele-Triage Pipeline

---

### Q1: Why did you build a multi-agent deterministic pipeline instead of just prompting a modern LLM like GPT-4 or Claude?
**Spoken Answer:**  
"In clinical medicine, safety cannot rely on probabilistic token generation. When we tested a strong single LLM (`qwen/qwen3.8-27b`) against our 51-scenario benchmark, it missed **88.9% of emergency cases** (8 out of 9), hallucinated numerical vitals twice, and gave inconsistent recommendations across repeated runs.  
Our multi-agent system divides responsibilities: LLMs handle conversational empathy and multilingual extraction, but **deterministic clinical rules** govern all triage decisions, and a dedicated **verification agent** checks every output against explicit ground truth before anything reaches the patient. The LLM can never override a safety threshold."  
**Grounding Files:**  
- `docs/SINGLE_LLM_BASELINE.md` (benchmark comparison data)
- `backend-poc-technical/agents/triage_protocol.py` (deterministic triage rules)
- `backend-poc-technical/agents/verification_agent.py` (ground truth validation)

---

### Q2: What is the "Monotonic Highest-Wins" rule, and why is it essential for patient safety?
**Spoken Answer:**  
"Monotonic highest-wins means that as data flows through the check-in stages, the triage severity level can only ever stay the same or escalate to a more severe level—it can **never be downgraded**.  
Our internal severities rank: `routine` (Green) < `review` (Yellow) < `urgent` (Red) < `emergency` (Red + 1122 dispatch). If the Stage-1 red-flag screen detects severe chest pain, the severity is immediately set to `emergency`. Even if subsequent interview steps or machine learning models report mild symptoms, the final severity remains locked at `emergency`. A later component cannot talk down an emergency."  
**Grounding Files:**  
- `backend-poc-technical/agents/triage_protocol.py` (severity ranking and monotonic merge function)
- `backend-poc-technical/test_monotonic_triage.py` (regression unit tests)

---

### Q3: How do you mathematically guarantee that your system never invents or hallucinates clinical numbers?
**Spoken Answer:**  
"We have a strict rule called 'Zero Invented Numbers'. In `agents/answer_validation.py` and `agents/verification_agent.py`, any numerical vital sign—like blood glucose or blood pressure—must match the raw string entered by the user or extracted by OCR.  
If the patient says 'my sugar is 140', the system extracts 140. If the extraction tool attempts to infer a missing systolic BP of '120', the verification agent flags an ungrounded entity and strips it. In our automated mutation proofs, we deliberately injected invented numbers across 60 tests, and our test harness killed **60 out of 60 mutations**."  
**Grounding Files:**  
- `backend-poc-technical/agents/answer_validation.py` (extraction regex and value bounds)
- `backend-poc-technical/agents/verification_agent.py` (hallucination rejection logic)
- `scripts/verify_mutations.py` (60/60 mutation proofs)

---

### Q4: Explain the difference between Stage 1 Red-Flag Screen and Stage 2 Final Triage.
**Spoken Answer:**  
"Stage 1 is the immediate emergency bypass. The moment a user types or speaks their first message, `agents/input_triage.py` scans for acute physiological crises—such as hypertensive crisis (systolic >= 180 or diastolic >= 120), severe hypoglycemia (< 54 mg/dL), or red-flag symptom phrases like crushing chest pain or sudden one-sided weakness. If detected, it bypasses the rest of the interview and issues an emergency alert.  
Stage 2 occurs at the very end of the check-in in `agents/final_triage.py`. It takes non-acute check-ins and evaluates secondary risk factors: longitudinal trends (have vitals worsened 5 check-ins in a row?) and statistical ML risk models (is cardiovascular risk >= 20%?). If triggered, Stage 2 elevates a `routine` patient to `review`."  
**Grounding Files:**  
- `backend-poc-technical/agents/input_triage.py` (Stage 1 bypass logic)
- `backend-poc-technical/agents/final_triage.py` (Stage 2 longitudinal & risk elevation)

---

### Q5: How does your 3-Tier Source Trust Hierarchy work?
**Spoken Answer:**  
"Not all clinical data has equal reliability. In `agents/verification_agent.py`, we assign trust tiers:  
1. **High Trust:** Verified EHR data entered or confirmed by a clinician.  
2. **Medium Trust:** Unverified patient-uploaded lab reports or prescriptions parsed by OCR.  
3. **Low Trust:** Unconfirmed self-reported numbers entered in chat.  
If a patient's self-reported medication conflicts with a hospital discharge prescription from two days ago, the reconciliation agent detects the discrepancy, tags the conflicting source, and surfaces a reconciliation alert for the doctor."  
**Grounding Files:**  
- `backend-poc-technical/agents/verification_agent.py` (trust level enumeration)
- `backend-poc-technical/agents/reconciliation_agent.py` (conflict detection)

---

### Q6: What does the Reconciliation Agent do, and how does it assist clinicians?
**Spoken Answer:**  
"The Reconciliation Agent in `agents/reconciliation_agent.py` performs source-blind comparison across four domains: active medications, reported diagnoses, vital signs, and allergy records.  
For example, if the EHR lists Metformin 500mg twice daily, but the patient reports taking Glimepiride, or reports stopping their medication, the agent generates a structured clinical conflict flag. On the provider dashboard, this appears under the Patient Summary with the conflicting sources side-by-side, allowing the physician to resolve adherence issues immediately."  
**Grounding Files:**  
- `backend-poc-technical/agents/reconciliation_agent.py`
- `app/components/provider/ReconciliationAlertDetail.tsx` (clinician UI view)

---

### Q7: How does ChronicCare AI handle vernacular Urdu and Roman Urdu without translation errors?
**Spoken Answer:**  
"We avoid error-prone external machine translation APIs. Instead, we use a two-pronged strategy:  
First, our Stage 1 danger screener includes a comprehensive, localized dictionary of vernacular phrases in Nastaliq Urdu and Roman Urdu—like 'chhati mein shadeed dard' (severe chest pain) or 'dil doob raha hai' (extreme sinking feeling).  
Second, for clinical explanations, we use verified bilingual template mappings in `rag/templates.json`. If an LLM is called, it operates with strict prompt guardrails and falls back to pre-approved clinical templates if validation fails."  
**Grounding Files:**  
- `backend-poc-technical/agents/input_triage.py` (`DANGER_WORDGROUPS`)
- `backend-poc-technical/rag/templates.json` (bilingual templates)
- `docs/BLIND_SET_3_RESULTS.md` (testing on Urdu & Roman Urdu phrases)

---

### Q8: What machine learning models are integrated into the pipeline, and what are their performance metrics?
**Spoken Answer:**  
"We have two validated machine learning models in production:  
1. **Diabetes Risk Classifier:** An XGBoost model trained on 9,254 NHANES adult patient records with 10 demographic and clinical features. It achieves an **AUROC of 0.831** and sensitivity of 0.825 at a decision threshold of 0.35, with a calibration slope of 1.04.  
2. **Cardiovascular Risk Classifier:** A Framingham 10-year coronary heart disease model calibrated on NHANES, achieving an **AUROC of 0.749** and sensitivity of 0.714.  
Both models output SHAP feature attribution values so clinicians can see exactly which factors—like systolic BP, age, or BMI—drove the risk score."  
**Grounding Files:**  
- `backend-poc-technical/ml/diabetes_nhanes_pipeline.py`
- `backend-poc-technical/ml/heart_nhanes_pipeline.py`
- `docs/EXPERIMENTS_SUMMARY.md` (metrics and calibration tables)

---

### Q9: How do you provide explainability to clinicians without confusing patients?
**Spoken Answer:**  
"We enforce a strict separation between patient-facing and clinician-facing interfaces:  
For the **patient**, we display only a clean color chip (Green, Yellow, or Red), a simple 1-sentence risk summary, and an actionable next step—never raw percentages or complex probabilities.  
For the **clinician**, the provider dashboard presents full diagnostic depth: the 10-year cardiovascular risk percentage, the risk tier, an interactive SHAP waterfall breakdown showing positive and negative contributing factors, and longitudinal vitals charts."  
**Grounding Files:**  
- `app/components/RiskResultScreen.tsx` (patient UI)
- `app/components/provider/ReconciliationAlertDetail.tsx` (provider UI with SHAP charts)
- `backend-poc-technical/agents/risk_agent.py` (SHAP explanation generator)

---

### Q10: What is the 30-day risk raise cooldown in Stage 2, and why is it necessary?
**Spoken Answer:**  
"When a patient is high-risk—for instance, an elderly diabetic with a Framingham score over 20%—Stage 2 elevates their routine check-in to Yellow (Review) to ensure doctor review.  
However, that patient may check in every other day. If we elevated every check-in to Yellow, clinic staff would suffer from severe **alert fatigue** and begin ignoring real warnings.  
Our 30-day cooldown (`RISK_RAISE_COOLDOWN_DAYS = 30`) ensures that once a patient's baseline risk elevates their triage, that specific baseline score will not elevate them again for 30 days unless their vitals deteriorate, acute symptoms arise, or worsening trends trigger."  
**Grounding Files:**  
- `backend-poc-technical/agents/final_triage.py` (cooldown logic)
- `backend-poc-technical/test_final_triage.py` (cooldown unit tests)

---

### Q11: What is the Longitudinal Trend Agent, and how does it elevate triage?
**Spoken Answer:**  
"The Trend Agent in `agents/trend_agent.py` monitors a patient's historical vitals over time rather than looking at an isolated single-day snapshot.  
If the agent detects a persistent negative trajectory—specifically **5 consecutive check-ins of worsening systolic BP or blood glucose**—it triggers a trend elevation alert. In Stage 2 Final Triage, this automatically promotes a patient from Green (Routine) to Yellow (Review), prompting clinical intervention before an acute crisis occurs."  
**Grounding Files:**  
- `backend-poc-technical/agents/trend_agent.py` (slope and consecutive worsening calculation)
- `backend-poc-technical/agents/final_triage.py` (`elevate_from_trends`)

---

### Q12: How does the RAG (Retrieval-Augmented Generation) pipeline work for clinical guidelines?
**Spoken Answer:**  
"When generating patient explanations or provider summaries, the system queries clinical guideline chunks (from ADA 2024 and ACC/AHA 2017).  
For our production cloud deployment on Render, we use a lightweight BM25 SQLite chunk store because Render's free tier has a strict 512 MB RAM limit.  
For our local evaluation and FYP-1 demo, we built a hybrid retrieval engine pairing BM25 keyword matching with dense BGE embeddings stored in ChromaDB (`CHROMA_ENABLED=true`), achieving high retrieval relevance and a RAGAS faithfulness score of 0.88 with 0 hallucinated facts."  
**Grounding Files:**  
- `backend-poc-technical/rag/explain_jobs.py` (retrieval and explanation generation)
- `backend-poc-technical/rag/chroma_store.py` (ChromaDB BGE hybrid store)
- `docs/RAG_EVAL.md` (retrieval evaluation benchmarks)

---

### Q13: What is the Provider SOAP Summary Agent?
**Spoken Answer:**  
"The SOAP Agent in `agents/soap_agent.py` automatically synthesizes the patient's check-in into the standard clinical SOAP format:  
- **Subjective:** Patient-reported symptoms, compliance statements, and chief complaints.  
- **Objective:** Verified vitals (BP, glucose), current lab values, and ML risk scores.  
- **Assessment:** Triage category, trend trajectory, and risk tier.  
- **Plan:** Clinical guideline recommendations and follow-up appointment urgency.  
This saves doctors substantial documentation time while guaranteeing that every listed vital sign is grounded in actual check-in data."  
**Grounding Files:**  
- `backend-poc-technical/agents/soap_agent.py`
- `backend-poc-technical/test_soap_agent.py` (hermetic unit tests)

---

### Q14: How does the server-side OCR intake work, and how do you prevent OCR errors from polluting records?
**Spoken Answer:**  
"Our OCR intake uses RapidOCR with ONNX Runtime to parse uploaded prescription images and lab reports locally on the server without sending medical images to third-party APIs.  
To prevent OCR recognition errors from corrupting the medical record, OCR output is **never committed directly**. Instead, it is placed in an 'unverified staging store' in `local_store.py`. The patient is presented with an editable confirmation screen in `OnboardingPrescriptionScreen.tsx` to verify each medication, dosage, and frequency before it is saved."  
**Grounding Files:**  
- `backend-poc-technical/ocr/rapidocr_engine.py` (RapidOCR ONNX pipeline)
- `backend-poc-technical/data_sources/local_store.py` (staged prescription storage)
- `app/components/OnboardingPrescriptionScreen.tsx` (patient verification UI)

---

### Q15: What were the key findings when you benchmarked the full pipeline against the Single-LLM baseline?
**Spoken Answer:**  
"We benchmarked both systems against 51 evaluable clinical scenarios using Groq's `qwen/qwen3.8-27b` over 3 independent trials per scenario (153 total baseline runs):  
- **Emergency Safety Recall:** The pipeline achieved **100.0% emergency recall** (3/3), while the single LLM achieved only **11.1% recall** (1/9), missing 8 out of 9 life-threatening emergency evaluations (crushing chest pain, hypertensive crisis, DKA vomiting).  
- **Urgent Recall:** The pipeline caught 100.0% of urgent hypoglycemia (48 mg/dL), while the single LLM under-triaged 100.0% of urgent cases to review.  
- **Invented Numbers:** The pipeline had **0 hallucinations** (0.0%), while the single LLM hallucinated invented vitals twice.  
- **Multi-Run Consistency:** The pipeline was **100.0% deterministic**, whereas the single LLM fluctuated across runs in 11.8% of scenarios.  
- **Failure Mode & Over-Triage:** The single LLM over-triaged routine check-ins by 67.7% (63/93 runs). It collapsed temporal horizons (treating past resolved symptoms like 'mild headache yesterday' as active complaints) and lacked clinical threshold bounds (treating 135/88 mmHg as slightly elevated needing clinician review without recognizing expected chronic baseline variance)."  
**Grounding Files:**  
- `docs/eval/SECTION36_RESULTS.md`
- `docs/eval/SINGLE_LLM_BASELINE.md`
- `scripts/eval/single_llm_baseline.py`

---

### Q16: What is Mutation Testing, and what do your 64/64 mutation proofs prove?
**Spoken Answer:**  
"Mutation testing is how we verify that our test suite actually catches safety regressions. In `scripts/verify_mutations.py`, we inject deliberate bugs into critical files—like reversing an emergency BP threshold, disabling the verification agent, ignoring red-flag phrases, or altering planner safety loops.  
We ran 64 deliberate mutations across clinical rules, the adaptive DAG planner, input triage, verification, and explainers. Our test suite killed **all 64 out of 64 mutations** (100% mutation kill score), proving that any code change that weakens clinical safety or violates architectural invariants immediately breaks our test build."  
**Grounding Files:**  
- `scripts/verify_mutations.py`
- `docs/FYP1_EVIDENCE.md`

---

### Q17: What was the Blind Set 3 benchmark, and what did it demonstrate?
**Spoken Answer:**  
"Blind Set 3 evaluated whether our danger phrase detection could generalize to unseen vernacular Urdu, Roman Urdu, and colloquial phrasing written by clinical peers who did not inspect our source code.  
Across **42 clinical danger phrases**, the system achieved **100% sensitivity** (42/42 detected), with zero false negatives on acute red flags. This proved that our keyword stem clusters and vernacular dictionaries generalize robustly across Pakistani linguistic patterns."  
**Grounding Files:**  
- `docs/BLIND_SET_3_RESULTS.md`
- `backend-poc-technical/test_blind_set_3.py`

---

### Q18: How does user authentication and data privacy work in ChronicCare AI?
**Spoken Answer:**  
"Authentication supports production Firebase JWT verification using Google public keys with RS256 cryptography in `auth/firebase_verify.py`. For local offline evaluation and testing, we use a deterministic mock role map (`DEMO_ROLE_MAP`).  
For privacy, all audit logging in `main.py` is strictly append-only and zero-PHI: log entries record event timestamps, agent execution status, and anonymized user IDs, but never record patient names, phone numbers, or free-text clinical notes."  
**Grounding Files:**  
- `backend-poc-technical/auth/firebase_verify.py`
- `backend-poc-technical/main.py` (audit log implementation)

---

### Q19: Why did you choose SQLite for the local demo instead of PostgreSQL or MySQL?
**Spoken Answer:**  
"For the FYP-1 local evaluation, SQLite provides a zero-configuration, self-contained, and completely hermetic relational database that runs anywhere without requiring external database server processes.  
Our `LocalDataStore` in `local_store.py` uses standard relational tables (patients, observations, appointments, staged prescriptions) with WAL mode enabled. It allows 100% reproducible demo seeding via `scripts/seed_demo_local.py` in under one second."  
**Grounding Files:**  
- `backend-poc-technical/data_sources/local_store.py`
- `scripts/seed_demo_local.py`

---

### Q20: How does the Adaptive Interview Agent handle missing vitals and avoid repetitive loops?
**Spoken Answer:**  
"The Adaptive Interview Agent (Engine v3 in `agents/interview_planner.py` and `agents/interview_v3_runner.py`) uses a dynamic priority DAG planner rather than a static script:  
1. **Zero Repeated Questions:** Once a clinical slot is satisfied or answered, it is permanently marked and never re-asked across the check-in (0 repeats across all 52 personas).  
2. **Strict Clinical Branching:** If glucose is < 70 mg/dL, it strictly asks acute hypoglycemia questions and suppresses high-sugar/DKA questions; if glucose is >= 250 mg/dL, it routes to sick-day fluids and suppresses acute hypo questions.  
3. **Multi-Intent Extraction:** If a patient answers multiple items at once (e.g. 'sugar 180 and took metformin'), both slots are extracted immediately, preventing redundant follow-up questions.  
4. **Hard Budget Cap:** A strict hard cap of 14 questions is enforced, preventing interrogation fatigue."  
**Grounding Files:**  
- `docs/eval/INTERVIEW_V2_VS_V3.md`
- `backend-poc-technical/agents/interview_planner.py`
- `backend-poc-technical/test_adaptive_flow.py`

---

### Q21: What is the difference between your LangGraph orchestrator and Direct orchestrator?
**Spoken Answer:**  
"ChronicCare AI supports dual orchestration modes toggled by the `ORCHESTRATOR` environment variable:  
- `ORCHESTRATOR=direct`: A deterministic sequential state pipeline in `orchestrator/steps.py`, optimized for low-latency production execution on resource-constrained servers.  
- `ORCHESTRATOR=langgraph`: A compiled StateGraph in `orchestrator/graph.py` with explicit state nodes, conditional routing edges, and checkpointing.  
Both orchestrators execute the exact same agent logic and pass the exact same 2,331+ pytest suite."  
**Grounding Files:**  
- `backend-poc-technical/orchestrator/steps.py` (direct pipeline)
- `backend-poc-technical/orchestrator/graph.py` (LangGraph state graph)

---

### Q22: How does the Frontend adhere to accessibility and medical usability standards?
**Spoken Answer:**  
"The Next.js 14 frontend adheres to WCAG 2.1 AA standards:  
1. Every triage color chip pairs its color with an explicit text label and icon so color-blind users can distinguish levels (`TriageColourChip.tsx`).  
2. Interactive components meet 44px minimum tap targets.  
3. Full RTL (Right-to-Left) support is implemented for vernacular Urdu text rendering.  
4. In our Playwright end-to-end test suite (`test/i4-e2e-demo`), all 9 core application screens passed axe accessibility scans with 0 critical violations."  
**Grounding Files:**  
- `app/components/TriageColourChip.tsx`
- `tests/e2e/demo_journeys.spec.ts` (axe accessibility checks)

---

### Q23: How do speech-to-text (Whisper) and text-to-speech (Meta MMS-TTS) operate in the system?
**Spoken Answer:**  
"For vernacular audio interaction, `backend-poc-technical/main.py` provides an audio transcription endpoint using OpenAI Whisper to convert spoken Urdu or English voice notes into text, complemented by the browser's native Web Speech API.  
For audio responses, we integrated Meta MMS-TTS for Urdu (`voice/`), which synthesizes localized spoken guidance for low-literacy patients. Both services operate behind clean feature flags (`TTS_ENABLED=true`) so the application degrades gracefully to text if audio hardware is absent."  
**Grounding Files:**  
- `backend-poc-technical/main.py` (`/api/voice/transcribe`)
- `backend-poc-technical/voice/` (Meta MMS-TTS)

---

### Q24: What are the three seeded demo patient journeys prepared for the FYP-1 evaluation?
**Spoken Answer:**  
"In `scripts/seed_demo_local.py`, we prepared three clinically distinct archetypes:  
1. **Patient 1: Tariq Mehmood (Routine Diabetes Check-in):** Stable fasting glucose (118 mg/dL) and BP (124/82 mmHg). Completes an adaptive check-in resulting in Green (Routine) triage and bilingual lifestyle advice.  
2. **Patient 2: Parveen Akhtar (Hypertensive Crisis Red-Flag Bypass):** Enters systolic BP 185 mmHg and chest tightness. Stage 1 immediately triggers an Emergency Red triage with 1122 ambulance guidance.  
3. **Patient 3: Ali Khan (Longitudinal Deterioration & Risk Elevation):** Chronic patient with 5 consecutive rising BP readings and high Framingham risk (22.4%), triggering Stage 2 Yellow (Review) elevation and SHAP factor attribution."  
**Grounding Files:**  
- `scripts/seed_demo_local.py`
- `docs/FYP1_EVIDENCE.md` (Table 7: Demo Seed Profiles)

---

### Q25: What are the honest known limitations of ChronicCare AI today?
**Spoken Answer:**  
"We maintain strict academic honesty regarding our system's current limitations:  
1. **Small Simulated Persona Cohort:** Our 52 benchmark personas are synthetic engineer-authored personas. While grounded in published ACC/AHA and ADA clinical guidelines, they have not yet been evaluated in a 1,000-patient live clinical cohort.  
2. **Doctor Signoff on 3 Decisions Only:** The doctor on record provided clinical decisions on three specific pending protocol questions in November 2026 (D1 no-reading symptom raise, D2 high-risk requires symptoms for review raise, D3 30-day cooldown). The system has not undergone comprehensive institutional medical signoff, and doctor review is not clinical validation.  
3. **Mock EHR Sandbox:** Interoperability was validated on SMART Health IT open sandbox endpoints and a local SQLite FHIR simulation store, not on live hospital production EHR systems.  
4. **Urdu Speech-to-Text Browser Dependency:** Voice transcription relies on browser Web Speech API with server Whisper fallback; performance varies significantly based on client microphone quality, browser engine, and ambient room noise.  
5. **Model Training Data:** Our ML risk models were trained on US NHANES data (1999–2023) and Framingham Heart Study data; prospective validation on Pakistani cohorts where cardiometabolic disease occurs at earlier ages remains future work.  
6. **Pediatric & Obstetric Exclusion:** The prototype explicitly excludes pregnancy and pediatric patients, exiting with an immediate referral."  
**Grounding Files:**  
- `docs/FYP1_EVIDENCE.md` (Section 8: Honest Known Limitations)
- `docs/PROMISE_TRACKER.md` (Section 10: Change Control Log)

---

### Q26: What decisions were made by the doctor on record in November 2026?
**Spoken Answer:**  
"The doctor on record answered three critical pending clinical questions:  
1. **Decision D1 (No-Reading Symptom Raise):** When a patient reports feeling unwell with no vital reading entered, does this raise Routine (Green) to Review (Yellow)? The doctor approved: Yes (`NO_READING_SYMPTOM_RAISE=true`).  
2. **Decision D2 (Heart Risk Triage Elevation):** The doctor decided: 'Just having heart risk doesn't need a review unless associated with any symptoms.' If a patient is high-risk but asymptomatic in this check-in, they remain Green (Routine). If symptoms are present alongside high risk, they escalate to Yellow (Review).  
3. **Decision D3 (Risk Raise Cooldown Period):** To prevent alert fatigue for patients with chronic unchangeable high risk, a 30-day cooldown applies before risk alone can raise them again (`RISK_RAISE_COOLDOWN_DAYS=30`)."  
**Grounding Files:**  
- `docs/LOCAL_DEMO.md` (Step 8b)
- `backend-poc-technical/agents/final_triage.py`
- `backend-poc-technical/test_doctor_decisions_d2.py`

---

### Q27: How does your Stage 1 Red-Flag detection work across three languages without missing subtle emergencies?
**Spoken Answer:**  
"Rather than rigid whole-sentence regexes, our red-flag engine in `agents/red_flag_patterns.py` uses word-window proximity matching across distinct vocabulary lists (body/person nouns, emergency verbs, severity cues) within an 8-word window across English, Urdu Nastaliq script, and Roman Urdu. It supports family subjects (ammi, abba, nana, nani), plural and respect verb forms, and failure verbs (kaam nahi kar raha, band ho gaya). Furthermore, fainting recovery suppression is strictly scoped to loss of consciousness and can never cancel acute chest pain, severe dyspnea, or stroke symptoms."  
**Grounding Files:**  
- `backend-poc-technical/agents/red_flag_patterns.py`
- `backend-poc-technical/test_red_flag_patterns.py`


