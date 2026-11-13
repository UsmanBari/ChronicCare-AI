# ChronicCare AI — Proposal Promise Tracker & Acceptance Matrix

> **FYP-1 "FINISH SPRINT" Local Baseline Tracker (Iteration 4 / Week 4)**  
> Tracks every single commitment and promise made in the original ChronicCare AI Project Proposal across Objectives 1–5, Section 13.1 (Agents 1–10), Section 13.2 (Services), Section 15 (Appointments & Escalation), Section 16 (Trends), Section 17 (Confidence & Trust), Section 21.1 (OCR), Section 23 (Technology Stack), Section 36 (Evaluation Suite), and Section 37 (Traceability).
> 
> **Evaluation Rule:** A promised feature is **DONE** only when its corresponding check in `scripts/local_acceptance.py` passes locally on SQLite on the laptop. Every feature PR replaces its placeholder check with real code and updates its row here.

---

## 1. Core Objectives (Proposal Section A6)

| Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| Multi-agent, dual-mode reconciliation pipeline with clinically structured adaptive interview | Objective 1 | `backend-poc-technical/agents/reconciliation_agent.py` | LA-02, LA-09 | **PASS** | Usman | Done (PR #80, #135) |
| Two explainable risk classifiers (diabetes full NHANES, hypertension/heart) with SHAP | Objective 2 | `backend-poc-technical/agents/risk_agent.py` | LA-13, LA-24, LA-27 | **PASS** (NHANES & Framingham CHD10 merged; Diabetes Control in PR #142 draft) | Usman / Saad | 13 Nov 2026 |
| Verification step checking outputs against explicit ground truth | Objective 3 | `backend-poc-technical/agents/verification_agent.py` | LA-09, LA-12 | **PASS** | Usman | Done (PR #80, #128) |
| Plain-language explanations in English and Urdu with guideline citations | Objective 4 | `backend-poc-technical/rag/explain_jobs.py` | LA-10, LA-11, LA-12 | **PASS** | Usman | Done (PR #128) |
| Multi-tier validation: scenarios, mutation proofs, single-LLM baseline | Objective 5 | `scripts/verify_mutations.py` & `scripts/eval/single_llm_baseline.py` | LA-18, LA-31 | **PASS** (Mutations PASS, Single-LLM built in PR #144) | Usman | 13 Nov 2026 |

---

## 2. Reasoning Agents (Proposal Section 13.1)

| Agent Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| Agent 1: Stage 1 Red-Flag Screen (Danger phrases, BP crisis, emergency bypass) | Sec 13.1 | `backend-poc-technical/agents/input_triage.py` | LA-04, LA-05 | **PASS** | Usman | Done |
| Agent 2: Adaptive Interview Agent (Condition-specific, missing-data handling) | Sec 13.1 | `backend-poc-technical/agents/adaptive_interview_agent.py` | LA-02, LA-03, LA-06 | **PASS** | Hassaan / Usman | Done |
| Agent 3: Confirmation Protocols (5 physiological protocols confirming danger) | Sec 13.1 | `backend-poc-technical/agents/input_triage.py` | LA-03, LA-04 | **PASS** | Usman | Done |
| Agent 4: Medication Confirmation Agent (Active medication inquiry & status) | Sec 13.1 | `backend-poc-technical/agents/medication_confirmation.py` | LA-07 | **PASS** | Usman | Done |
| Agent 5: Record Retrieval Agent (Unified DataSource: FHIR vs Local Store) | Sec 13.1 | `backend-poc-technical/data_sources/local_store.py` | LA-02, LA-09 | **PASS** | Usman | Done |
| Agent 6: Clinical Reconciliation Agent (Source-blind comparison & conflict flag) | Sec 13.1 | `backend-poc-technical/agents/reconciliation_agent.py` | LA-09 | **PASS** | Usman | Done |
| Agent 7: Verification Agent (Source trust levels, clinical severity rating) | Sec 13.1 | `backend-poc-technical/agents/verification_agent.py` | LA-09 | **PASS** | Usman | Done |
| Agent 8: Longitudinal Trend Agent (Direction calculation, escalation trigger) | Sec 13.1, 16 | `backend-poc-technical/agents/trend_agent.py` & `agents/final_triage.py` | LA-14, LA-22 | **PASS** | Saad / Usman | Done (PR A) |
| Agent 9: Advisory Risk Models (NHANES Diabetes, Framingham CHD10) | Sec 13.1 | `backend-poc-technical/agents/risk_agent.py` | LA-13, LA-24 | **PASS** | Usman / Saad | Done (PR A) |
| Agent 10: Provider SOAP Summary Agent (Structured clinical synthesis) | Sec 13.1 | `backend-poc-technical/agents/soap_agent.py` | LA-26 | **PASS** | Usman | Done (PR E) |

---

## 3. Deterministic Services (Proposal Section 13.2)

| Service Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| Final Deterministic Triage Merge (Monotonic highest-wins safety rule) | Sec 13.2 | `backend-poc-technical/agents/triage_protocol.py` | LA-02, LA-03, LA-04, LA-05 | **PASS** | Usman | Done |
| Append-Only Zero-PHI Audit Logging | Sec 13.2 | `backend-poc-technical/main.py` | LA-18 | **PASS** | Usman | Done |
| Authentication & Role Mapping Service (Firebase RS256 + DEMO_ROLE_MAP) | Sec 13.2 | `backend-poc-technical/auth/firebase_verify.py` | LA-01 | **PASS** | Usman | Done |
| Guideline RAG Pipeline (Chunk retrieval, safety guards, citations) | Sec 13.2 | `backend-poc-technical/rag/explain_jobs.py` | LA-12 | **PASS** | Usman | Done |
| Multilingual Template Engine (English, Urdu script, Roman Urdu) | Sec 13.2 | `backend-poc-technical/rag/templates.json` | LA-08, LA-10, LA-11 | **PARTIAL** (Ur/Roman PASS, R8 no-readings PR #134) | Hassaan / Usman | 09 Nov 2026 |
| System Health & Admin Configuration Status Endpoint | Sec 13.2 | `backend-poc-technical/main.py` | LA-01 | **PASS** | Usman | Done |
| Patient Record History, Export and Import Service | Sec 13.2 | `backend-poc-technical/main.py` | LA-17 | **PASS** | Usman | Done |
| Server-Side OCR Intake Service (Prescriptions & lab reports) | Sec 13.2, 21.1 | `backend-poc-technical/main.py` | LA-15 | **PASS** | Hassaan / Saad | Done (PR #96) |
| Notification Service (In-App notification centre, daily reminders & FCM Web Push) | Sec 13.2, 15, 35 | `backend-poc-technical/services/notification_service.py` | LA-29 | **OPEN PR** (PR #146 by Hassaan, pending review) | Hassaan | 13 Nov 2026 |

---

## 4. Clinical Workflow, Triage & Appointments (Proposal Section 15)

| Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| Triage Severity Colors (Green=Routine, Yellow=Review, Red=Urgent/Emergency) | Sec 15 | `backend-poc-technical/agents/final_triage.py` & `app/components/TriageColourChip.tsx` | LA-20 | **PASS** | Usman | Done (PR A) |
| Stage-2 Clinical Risk Elevation (Routine -> Review on high risk band) | Sec 15 | `backend-poc-technical/agents/final_triage.py` | LA-21, LA-21b, LA-21c | **PASS** | Usman | Done (PR A) |
| Patient-Facing Risk Band Display (Plain sentence + action only) | Sec 15 | `app/components/RiskResultScreen.tsx` & `backend-poc-technical/orchestrator/steps.py` | LA-23 | **PASS** | Usman | Done (PR A) |
| Appointment Booking by Triage Level & Clinical Specialty | Sec 15 | `backend-poc-technical/services/appointment_service.py` | LA-25 | **OPEN PR** (PR #145 by Hassaan, pending review) | Hassaan | 13 Nov 2026 |
| Red-Flag Escalation Notification & Timeout Tracking | Sec 15 | `backend-poc-technical/services/appointment_service.py` | LA-25 | **OPEN PR** (PR #145 by Hassaan, pending review) | Hassaan | 13 Nov 2026 |

---

## 5. Trends & Longitudinal Monitoring (Proposal Section 16)

| Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| Longitudinal Observation Series Retrieval | Sec 16 | `backend-poc-technical/main.py` | LA-14 | **PASS** | Saad / Usman | Done |
| Trend Elevation Trigger (5 consecutive worsening check-ins -> Review) | Sec 16 | `backend-poc-technical/agents/final_triage.py` | LA-22 | **PASS** | Usman / Saad | Done (PR A) |
| Clinician Review Longitudinal BP & Glucose Charts | Sec 16 | `app/components/provider/ReconciliationAlertDetail.tsx` | LA-22 | **PASS** | Usman | Done (PR A) |

---

## 6. Confidence & Trust Framework (Proposal Section 17)

| Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| 3-Tier Source Trust Hierarchy (High: EHR/Clinician; Med: OCR/Upload; Low: Self-Report) | Sec 17 | `backend-poc-technical/agents/verification_agent.py` | LA-09, LA-15 | **PASS** | Usman | Done |
| Assessment Confidence Label (High / Medium / Low based on completeness) | Sec 17 | `backend-poc-technical/agents/verification_agent.py` | LA-02, LA-08 | **PASS** | Usman | Done |
| Risk Assessment Confidence Hierarchy (High: EHR same-day; Med: Patient/7d+; Low: Unconfirmed OCR) | Sec 17 | `backend-poc-technical/agents/risk_agent.py` | LA-23b | **PASS** | Usman | Done (PR A) |

---

## 7. OCR & Ingestion (Proposal Section 21.1)

| Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| RapidOCR Onnxruntime Local Pipeline | Sec 21.1 | `backend-poc-technical/ocr/` | LA-15 | **PASS** | Hassaan | Done (PR #96) |
| Prescription Intake Staging & Patient Confirmation | Sec 21.1 | `backend-poc-technical/main.py` | LA-15 | **PASS** | Hassaan / Saad | Done (PR #96) |
| Prescription Upload in Isolated Onboarding (Confidence, Headers & Fallback) | Sec 18, 21.1 | `app/components/OnboardingPrescriptionScreen.tsx` | LA-15b | **PASS** | Hassaan | Done (PR #138) |
| Unverified / Medium Trust Tagging in Local Store | Sec 21.1 | `backend-poc-technical/data_sources/local_store.py` | LA-15, LA-15b | **PASS** | Usman / Hassaan | Done |

---

## 8. Technology Stack & Multi-Modal Interfaces (Proposal Section 23)

| Component Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| Next.js 14 Frontend with Static Export & Responsive Mobile UI | Sec 23 | `app/` | Frontend Build | **PASS** | Usman | Done |
| FastAPI Asynchronous High-Performance Python Backend | Sec 23 | `backend-poc-technical/main.py` | LA-01 | **PASS** | Usman | Done |
| Pure SQLite Local Storage for Fully Isolated Operation | Sec 23 | `backend-poc-technical/data_sources/local_store.py` | LA-01, LA-02 | **PASS** | Usman | Done |
| PyJWT Google Public Key Token Verification (RS256) | Sec 23 | `backend-poc-technical/auth/firebase_verify.py` | LA-01 | **PASS** | Usman | Done |
| Voice Transcription Input (Whisper STT endpoint) | Sec 23 | `backend-poc-technical/main.py` | LA-16 | **PASS** | Hassaan | Done |
| Urdu Speech Synthesis Voice Output (Meta MMS-TTS Urdu) | Sec 23 | `backend-poc-technical/voice/` | LA-30 | **OPEN PR** (PR #147 by Hassaan, pending review) | Hassaan | 13 Nov 2026 |
| LangGraph State-Graph Orchestrator Execution | Sec 23 | `backend-poc-technical/orchestrator/graph.py` | LA-01 | **PASS** | Usman | Done |

---

## 9. Evaluation, Safety & Research Questions (Proposal Section 36 & 37)

| Promise | Proposal Section | Built Where (File) | Local Check ID | Status Today | Owner | Target Date |
|:---|:---:|:---|:---:|:---:|:---:|:---:|
| Automated Mutation Proofs (23 deliberate rule breaks killed in CI) | Sec 36 | `scripts/verify_mutations.py` | CI Gate 3 | **PASS** | Usman | Done |
| Deterministic Engine Scenarios Regression Testing | Sec 36 | `backend-poc-technical/scenarios/` | CI Gate 2 | **PASS** | Usman | Done |
| Blind Set Danger Phrase Generalization Benchmark | Sec 36 | `docs/BLIND_SET_3_RESULTS.md` | Doc Record | **PASS** | Saad / Hassaan | Done |
| Single-LLM Baseline Benchmark Comparison (RQ3) | Sec 36 | `scripts/eval/single_llm_baseline.py` | LA-31 | **PASS** (Built in PR #144; benchmark suite executed) | Usman | 13 Nov 2026 |
| Requirements Traceability Matrix Verification | Sec 37 | `docs/TRACEABILITY.md` | `test_traceability_links.py` | **PASS** | Usman | Done |
| Demo Seed & Local Acceptance Test Harness | Sec 36 | `scripts/seed_demo_local.py` & `scripts/start_local_demo.ps1` | LA-32 | **PASS** (Built in PR #149; 3 demo personas seeded) | Usman | 13 Nov 2026 |

---

## 10. Change Control Log (Architectural Evolution from Proposal)

| Original Proposal Specification | Actual Implementation | Reason for Change | Impact & Safety Rationale | Approval Date |
|:---|:---|:---|:---|:---:|
| **T5 / FLAN-T5 Local LLM** for clinical explanations | **Groq Llama-3 / Template Fallback** | Render free-tier RAM limit (512 MB) cannot run heavy PyTorch T5 checkpoints without crashing. | Cloud API with strict deterministic template fallback; safe and responsive. | 02 Nov 2026 |
| **Coqui TTS** for vernacular Urdu voice synthesis | **Meta MMS-TTS (Urdu)** | Coqui TTS repository is unmaintained and introduces incompatible torch wheel dependencies. | Meta MMS-TTS provides officially supported Urdu acoustic models with smaller footprint. | 08 Nov 2026 |
| **ChromaDB Vector Store** | **Hybrid BM25 + ChromaDB BGE Retrieval (Flagged)** | Render free-tier RAM limit (512 MB) cannot run in-process embedding models continuously without OOM risk. BM25 is live default; ChromaDB + BGE dense vector store is fully implemented and enabled via flags (`CHROMA_ENABLED=true`, `HYBRID_RETRIEVAL=true`) for local evaluation and FYP-1 demo. | Dual-mode retrieval: lightweight BM25 for production cloud hosting; high-accuracy dense/hybrid vector retrieval with ChromaDB and RAGAS faithfulness eval for local FYP-1 evaluation. | 12 Nov 2026 |
| **3 Triage Colors (Green/Yellow/Red)** | **4 Internal Severity Levels (Routine / Review / Urgent / Emergency)** | Internal clinical logic requires distinguishing urgent doctor visits from immediate 1122 ambulance calls. | Green maps to Routine, Yellow to Review, Red to Urgent & Emergency. Safe monotonic ordering preserved. | 08 Nov 2026 |

