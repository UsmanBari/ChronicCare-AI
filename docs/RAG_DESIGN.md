# ChronicCare AI: RAG Architecture & Retrieval Design (RAG_DESIGN.md)

> **Document Status:** Complete (Benchmarked 28 Oct 2026)  
> **Author:** Usman Bari / Engineering Team  
> **Context:** Retrieval-Augmented Generation for Grounded Clinical Explanations

---

## 1. System Overview

ChronicCare AI pairs a deterministic clinical rule engine with grounded, evidence-backed explanations. When a patient completes a check-in, the rule engine evaluates safety protocols and assigns one of four triage levels: **emergency, urgent, review, routine**.

The RAG subsystem retrieves verified guideline chunks from international and local clinical guidelines:
- **ISH 2020:** International Society of Hypertension Global Practice Guidelines (`ish_2020_htn`)
- **WHO 2021:** Pharmacological Treatment of Hypertension in Adults (`who_2021_htn`)
- **IDF-DAR 2021:** Diabetes and Ramadan Practical Guidelines (`idf_dar_2021`)
- **Pakistan Hypertension in Women 2023:** (`pk_htn_women_2023`)
- **AKU Diabetes Pakistan 2023:** (`aku_diabetes_pk_2023`)

The retriever retrieves evidence passages citing specific guideline recommendations to explain the assigned triage level to the patient and clinician.

---

## 2. Chunk Store Architecture (`store.py`)

The chunk store is decoupled via the `ChunkStore` Python protocol:
```python
class ChunkStore(Protocol):
    def get_chunk(self, chunk_id: str) -> dict | None: ...
    def list_chunks(
        self,
        condition: str | None = None,
        topic: str | None = None,
        min_priority: int | None = None,
    ) -> list[dict]: ...
    def total_chunks(self) -> int: ...
```

### Implementations:
1. **`JsonlChunkStore(path)`:** Loads JSONL-serialized guideline chunks into memory with primary key index on `chunk_id` and secondary indices on `condition` and `topics`. Used in development, unit testing, and initial CI runs.
2. **Database Chunk Store (Day 7):** Connects to the local SQLite / MariaDB instance to query chunks stored as database records.

---

## 3. Dense Retrieval vs. BM25 Empirical Benchmark (Decision B5)

### Benchmark Protocol & Setup
To fairly evaluate whether a dense embedding model (`BAAI/bge-small-en-v1.5` via FastEmbed) should run in the production backend alongside or instead of BM25:
1. **Offline Pre-computation (`emb_bge_small.npy`):**
   - Chunks (498 items) were embedded offline using FastEmbed `BAAI/bge-small-en-v1.5` with single-threaded execution (`threads=1`, `batch_size=32`), producing an embedding matrix of shape `(498, 384)`.
2. **Fresh Process Runtime Evaluation (`measure_dense_vs_bm25.py`):**
   - Executed in an isolated process to profile true steady-state runtime memory (model weights loaded + vector matrix loaded in memory) and query encoding without build-time compilation overhead.
3. **Backend Baseline Memory Measurement:**
   - FastAPI / Uvicorn server was launched locally on SQLite with default flags (no production `DATABASE_URL`, no Render environment variables) listening strictly on `127.0.0.1:8008`.
   - Polled `http://127.0.0.1:8008/api/health`, confirmed response, and captured parent + child process RSS before cleanly terminating.
4. **Gates Evaluated:**
   - **Memory Gate:** Combined RSS (Dense Model + Vectors + Backend Baseline) must be $< 400\text{ MB}$ to guarantee safety within the Render 512 MB RAM container limit.
   - **Accuracy Gate:** Dense retrieval must achieve at least $\ge 2$ more hits in top-4 ($\text{Hits}@4$) than BM25 on the 15 standardized smoke questions.

### Empirical Results (Raw Output from `logs/day3/rag_measurement.txt`)

```text
================================================================================
STEP B & D: FRESH PROCESS RUNTIME RSS & SMOKE RETRIEVAL EVALUATION
================================================================================

--- BM25 RETRIEVAL PERFORMANCE (15 SMOKE QUESTIONS) ---
ID           | Expected     | Top-4 Retrieved Sources                  | Hit@4  | Rank
----------------------------------------------------------------------------------
Q01          | ish_2020_htn | pk_htn_women_2023, pk_htn_women_2023, pk_htn_women_2023, pk_htn_women_2023 | YES    | 1
Q02          | ish_2020_htn | ish_2020_htn, ish_2020_htn, pk_htn_women_2023, pk_htn_women_2023 | YES    | 1
Q03          | ish_2020_htn | who_2021_htn, who_2021_htn, who_2021_htn, who_2021_htn | NO     | -
Q04          | idf_dar_2021 | idf_dar_2021, idf_dar_2021, idf_dar_2021, idf_dar_2021 | YES    | 1
Q05          | idf_dar_2021 | idf_dar_2021, idf_dar_2021, idf_dar_2021, idf_dar_2021 | YES    | 1
Q06          | idf_dar_2021 | idf_dar_2021, idf_dar_2021, idf_dar_2021, idf_dar_2021 | YES    | 1
Q07          | ish_2020_htn | pk_htn_women_2023, pk_htn_women_2023, ish_2020_htn, idf_dar_2021 | YES    | 1
Q08          | ish_2020_htn | who_2021_htn, pk_htn_women_2023, who_2021_htn, ish_2020_htn | YES    | 1
Q09          | who_2021_htn | who_2021_htn, who_2021_htn, who_2021_htn, pk_htn_women_2023 | YES    | 1
Q10          | pk_htn_women_2023 | pk_htn_women_2023, ish_2020_htn, pk_htn_women_2023, ish_2020_htn | YES    | 1
Q11          | pk_htn_women_2023 | pk_htn_women_2023, pk_htn_women_2023, pk_htn_women_2023, who_2021_htn | YES    | 1
Q12          | who_2021_htn | pk_htn_women_2023, who_2021_htn, who_2021_htn, ish_2020_htn | YES    | 2
Q13          | who_2021_htn | ish_2020_htn, who_2021_htn, who_2021_htn, who_2021_htn | YES    | 2
Q14          | aku_diabetes_pk_2023 | aku_diabetes_pk_2023, who_2021_htn, aku_diabetes_pk_2023, who_2021_htn | YES    | 1
Q15          | idf_dar_2021 | idf_dar_2021, idf_dar_2021, idf_dar_2021, idf_dar_2021 | YES    | 1

BM25 Recall@4: 93.3% (14/15) | BM25 MRR: 0.8667

--- DENSE (BGE-SMALL-EN-V1.5) RETRIEVAL PERFORMANCE (15 SMOKE QUESTIONS) ---
ID           | Expected     | Top-4 Retrieved Sources                  | Hit@4  | Rank
----------------------------------------------------------------------------------
Q01          | ish_2020_htn | ish_2020_htn, ish_2020_htn, pk_htn_women_2023, pk_htn_women_2023 | YES    | 1
Q02          | ish_2020_htn | ish_2020_htn, pk_htn_women_2023, pk_htn_women_2023, pk_htn_women_2023 | YES    | 1
Q03          | ish_2020_htn | pk_htn_women_2023, pk_htn_women_2023, ish_2020_htn, ish_2020_htn | YES    | 1
Q04          | idf_dar_2021 | idf_dar_2021, idf_dar_2021, idf_dar_2021, idf_dar_2021 | YES    | 1
Q05          | idf_dar_2021 | idf_dar_2021, idf_dar_2021, idf_dar_2021, idf_dar_2021 | YES    | 1
Q06          | idf_dar_2021 | idf_dar_2021, idf_dar_2021, idf_dar_2021, idf_dar_2021 | YES    | 1
Q07          | ish_2020_htn | ish_2020_htn, ish_2020_htn, pk_htn_women_2023, pk_htn_women_2023 | YES    | 1
Q08          | ish_2020_htn | pk_htn_women_2023, pk_htn_women_2023, ish_2020_htn, pk_htn_women_2023 | YES    | 1
Q09          | who_2021_htn | who_2021_htn, who_2021_htn, pk_htn_women_2023, pk_htn_women_2023 | YES    | 1
Q10          | pk_htn_women_2023 | ish_2020_htn, who_2021_htn, pk_htn_women_2023, pk_htn_women_2023 | YES    | 1
Q11          | pk_htn_women_2023 | pk_htn_women_2023, pk_htn_women_2023, pk_htn_women_2023, pk_htn_women_2023 | YES    | 1
Q12          | who_2021_htn | who_2021_htn, who_2021_htn, who_2021_htn, who_2021_htn | YES    | 1
Q13          | who_2021_htn | who_2021_htn, who_2021_htn, who_2021_htn, ish_2020_htn | YES    | 1
Q14          | aku_diabetes_pk_2023 | aku_diabetes_pk_2023, aku_diabetes_pk_2023, aku_diabetes_pk_2023, aku_diabetes_pk_2023 | YES    | 1
Q15          | idf_dar_2021 | idf_dar_2021, idf_dar_2021, idf_dar_2021, idf_dar_2021 | YES    | 1

Dense Recall@4: 100.0% (15/15) | Dense MRR: 1.0000

Dense Model + Vectors Peak RSS: 213.97 MB (Baseline RSS was 33.82 MB)

================================================================================
STEP C: MEASURE BACKEND BASELINE RSS (uvicorn on SQLite, 127.0.0.1)
================================================================================
Pinged http://127.0.0.1:8008/api/health -> Response: {"status":"healthy","service":"chroniccare-backend","version":"0.1.0"}
Uvicorn Process PID 2972 RSS: 69.52 MB
Uvicorn process PID 2972 terminated and confirmed stopped: True (poll exit code: 1)

================================================================================
STEP E: RAG ARCHITECTURE DECISION RULE EVALUATION
================================================================================
1. Memory Gate: (b) Dense Model+Vectors RSS (213.97 MB) + (c) Backend Baseline RSS (69.52 MB)
   Combined Memory = 283.49 MB (Gate Threshold: < 400 MB)
   Memory Gate Passed: True
2. Accuracy Gate: Dense Hits@4 (15/15) vs BM25 Hits@4 (14/15)
   Delta Hits@4 = +1 (Gate Threshold: >= 2 more questions right)
   Accuracy Gate Passed: False

FINAL DECISION: BM25
Reason: Dense failed the accuracy gate (did not get >= 2 more questions right than BM25).
```

### Retrieval Decision: BM25 Only in Production Backend

**Decision: BM25 only (pure Python stdlib). Dense embedding models are not deployed in the backend container.**

#### Decision Evaluation:
1. **Memory Gate (Passed):**
   - Dense Model + Vectors peak RSS in a fresh process is **213.97 MB**.
   - Backend baseline RSS on SQLite is **69.52 MB**.
   - Combined memory footprint is **283.49 MB**, which is below the $< 400\text{ MB}$ gate.
2. **Accuracy Gate (Failed):**
   - BM25 gets **14/15** questions right (93.3% Recall@4, MRR 0.8667).
   - Dense gets **15/15** questions right (100.0% Recall@4, MRR 1.0000).
   - The accuracy margin is **+1 question right** (Q03), which fails the required threshold of **$\ge 2$ more questions right** to justify embedding dependency complexity.
3. **Engineering & Deployment Advantages:**
   - Pure Python BM25 has **zero binary/C++ dependencies** (no ONNX Runtime, no PyTorch, no C-compiler requirements).
   - Memory footprint of BM25 on the 498-chunk corpus is $< 1\text{ MB}$, leaving >440 MB free RAM in Render's 512 MB tier.
   - Startup time is $< 5\text{ ms}$, versus several seconds for ONNX Runtime initialization.

---

## 4. BM25 Retrieval Algorithm (`retriever.py`)

The retriever is implemented in pure Python (no `rank_bm25` dependency):
- **Hyperparameters:** $k_1 = 1.5$, $b = 0.75$.
- **Tokenizer:**
  - Case folding (lower-casing).
  - Medical unit normalisation: `mg/dl` $\rightarrow$ `mgdl`, `mmol/l` $\rightarrow$ `mmoll`, `mm hg` / `mmhg` $\rightarrow$ `mmhg`.
  - Numerical token preservation (e.g., `140`, `90`, `180`, `120`, `70`, `54`).
- **Scoring:**
  $$\text{IDF}(q) = \ln \left( \frac{N - n(q) + 0.5}{n(q) + 0.5} + 1 \right)$$
  $$\text{Score}(D, Q) = \sum_{q \in Q} \text{IDF}(q) \cdot \frac{f(q, D) \cdot (k_1 + 1)}{f(q, D) + k_1 \cdot (1 - b + b \cdot \frac{|D|}{\text{avgdl}})}$$
- **Filtering & Tie-breaking:**
  - Optional filters: `condition` (`diabetes` | `hypertension`), `topics` (`list[str]`), `min_priority` (`int`).
  - Score ties are broken by guideline `priority` (higher integer priority wins).

---

## 5. Query Construction Map (`query_map.py`)

The retriever does not accept free-form user text. Queries are constructed deterministically from rule engine outputs:

| Trigger Code | Condition | Topic Slugs | Query Terms | Min Priority |
|---|---|---|---|---|
| `glucose_emergency_low` | diabetes | `hypoglycemia`, `emergency` | `glucose severe hypoglycemia 54 mgdl emergency glucagon` | 1 |
| `glucose_urgent_low` | diabetes | `hypoglycemia` | `glucose hypoglycemia 70 mgdl fast acting carbohydrate rule of 15` | 1 |
| `glucose_emergency_high` | diabetes | `hyperglycemia`, `emergency` | `glucose severe hyperglycemia 400 mgdl diabetic ketoacidosis dka symptoms` | 1 |
| `glucose_urgent_high` | diabetes | `hyperglycemia` | `glucose high blood sugar 300 mgdl ketones hydration follow up` | 1 |
| `bp_crisis` | hypertension | `crisis`, `emergency` | `blood pressure 180 120 mmhg hypertensive emergency crisis organ damage` | 1 |
| `bp_urgent` | hypertension | `bp_targets`, `stage2` | `blood pressure stage 2 hypertension 140 90 mmhg re-check rest 5 minutes` | 1 |
| `bp_low` | hypertension | `hypotension` | `low blood pressure 90 60 mmhg dizziness orthostatic review` | 1 |
| `ramadan_fasting_high_risk` | diabetes | `ramadan`, `risk_stratification` | `ramadan fasting high risk insulin hypoglycemia break fast` | 2 |
| `pregnancy_hypertension` | hypertension | `pregnancy` | `hypertension pregnancy pre-eclampsia blood pressure monitoring safe medicines` | 2 |
| `routine_review` | both | `lifestyle`, `targets` | `routine chronic care targets blood pressure glucose lifestyle exercise diet` | 1 |

---

## 6. Citations and Grounding Verification

Retrieved chunks are passed directly into the explanation generator (`explainer.py`). Every generated sentence must include an explicit citation marker `[C{chunk_id}]` referencing a chunk returned by `retriever.py`, which is validated by five automated integrity checks (V1–V5) before delivery.
