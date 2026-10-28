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

### Benchmark Setup
To evaluate whether a dense transformer model (`BAAI/bge-small-en-v1.5` via FastEmbed) should be used in the backend alongside or instead of BM25:
- A dedicated scratch virtual environment was created outside the backend venv.
- `fastembed` with `BAAI/bge-small-en-v1.5` and `psutil` were installed.
- All 498 ingested guideline chunks from `chunks.jsonl` were indexed.
- The 15 clinical smoke questions (`smoke_questions.json`) covering hypertension, diabetes, Ramadan fasting, pregnancy, and local Pakistan screening thresholds were evaluated across:
  1. **BM25 (Pure Python stdlib, zero external dependencies)**
  2. **FastEmbed (BAAI/bge-small-en-v1.5, ONNX Runtime)**
  3. **Hybrid RRF (Reciprocal Rank Fusion, $k=60$)**
- Memory RSS was continuously profiled using `psutil.Process().memory_info().rss`.

### Empirical Results (Verbatim Command Output)

```text
================================================================================
RETRIEVAL EVALUATION SUMMARY ON 15 SMOKE QUESTIONS
================================================================================
Method                         | Recall@1   | Recall@4   | MRR        | Peak RSS (MB) 
--------------------------------------------------------------------------------
BM25 (Pure Python Stdlib)      | 80.0% (12/15) | 93.3% (14/15) | 0.8667     | 18.41 MB
FastEmbed (bge-small-en-v1.5)  | 100.0% (15/15) | 100.0% (15/15) | 1.0000     | 5085.59 MB
Hybrid (BM25 + FastEmbed RRF)  | 86.7% (13/15) | 100.0% (15/15) | 0.9333     | 5085.59 MB
================================================================================

PER-QUESTION RANK COMPARISON:
ID    | Expected Source      | BM25 Rank  | Dense Rank | Hybrid Rank
-----------------------------------------------------------------
Q01   | ish_2020_htn         | 1          | 1          | 1         
Q02   | ish_2020_htn         | 1          | 1          | 1         
Q03   | ish_2020_htn         | >10        | 1          | 2         
Q04   | idf_dar_2021         | 1          | 1          | 1         
Q05   | idf_dar_2021         | 1          | 1          | 1         
Q06   | idf_dar_2021         | 1          | 1          | 1         
Q07   | ish_2020_htn         | 1          | 1          | 1         
Q08   | ish_2020_htn         | 1          | 1          | 1         
Q09   | who_2021_htn         | 1          | 1          | 1         
Q10   | pk_htn_women_2023    | 1          | 1          | 1         
Q11   | pk_htn_women_2023    | 1          | 1          | 1         
Q12   | who_2021_htn         | 2          | 1          | 1         
Q13   | who_2021_htn         | 2          | 1          | 2         
Q14   | aku_diabetes_pk_2023 | 1          | 1          | 1         
Q15   | idf_dar_2021         | 1          | 1          | 1         
```

### Retrieval Decision: BM25 Only in Production Backend

**Decision: BM25 only (pure Python stdlib). Do NOT load dense transformer models in the backend container.**

#### Technical Rationale:
1. **Severe Memory Limit Violation:**
   - **Render Free Tier Limit:** **512 MB RAM**.
   - Loading `fastembed` with `bge-small-en-v1.5` increased baseline memory to **231.18 MB** (45.1% of the entire container limit).
   - During embedding generation, peak process RSS reached **5,085.59 MB (~5.08 GB)** due to ONNX Runtime internal buffer allocations on Windows/Linux multi-core CPU inference. This is nearly **10x the hard memory ceiling** of the production server and would cause an instant OOM container kill.
2. **Deterministic Clinical Query Generation:**
   - Unlike generic open-domain search engines, ChronicCare AI does not query the knowledge base using noisy conversational patient speech.
   - Queries are constructed deterministically by `query_map.py` from standardized triage codes (e.g. `glucose_low`, `bp_severe`, `ramadan_fasting`).
   - BM25 achieves **93.3% Recall@4** and **0.8667 MRR** with a process footprint of only **18.41 MB**.
3. **Corpus Scale (~500 Chunks):**
   - The entire non-blocked guideline corpus consists of 498 chunks (~111,000 words).
   - Inverted indexing in pure Python takes under 5 milliseconds on startup, requires zero external database servers (no ChromaDB, Milvus, or Qdrant required), and executes retrieval in $< 1$ millisecond per request.

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
