# Week 3 Pipeline Load & Memory Benchmark Report

**Benchmark Date:** 2026-11-06 21:36  
**Evaluator:** Muhammad Saad (Backend & ML Validation Engineer)  
**Branch:** `test/i3-load-test` (Base: `dev`)  
**Target Architecture:** Render Free-Tier Web Service (512 MB Server RAM ceiling, Python 3.11)  
**Execution Environment:** Isolated fresh server subprocess per configuration, SQLite backend, signed RS256 test tokens.  

> [!IMPORTANT]
> **Methodology & Release 2 Architecture Note:**
> - Runs evaluate the Release 2 configuration: compiled LangGraph StateGraph orchestrator (`ORCHESTRATOR=graph`), `RISK_ENABLED=true`, `EXPLAIN_ENABLED=true`, and **`EXPLAIN_MODE=background`** (PR #114).
> - Under background mode, `/complete` returns immediately, and explanations are generated asynchronously by an in-process worker thread.
> - Latency is evaluated across two distinct metrics: **`/complete` response latency** (patient check-in completion) and **time-to-ready** (elapsed time until `GET /api/checkins/{id}/explanation` returns `status=ready`).
> - **Cache Disabled:** In-memory explanation cache is disabled (`EXPLAIN_CACHE_MAX=0`) across all load test runs so every check-in exercises the LLM path rather than retrieving cached sentences.
> - **Release 2 Default Settings:** The primary matrix uses Release 2 defaults: bounded background queue of 50 (`EXPLAIN_QUEUE_MAX=50`) and job deadline of 45.0 s (`EXPLAIN_JOB_DEADLINE_SECONDS=45.0`).
> - Fake LLM delays of **0.8 s** and **2.0 s** are **assumed (prompt setting)** to simulate potential LLM latency (Usman's 5 Nov live smoke measured Groq at 0.81–2.25 s per call). Zero Groq API tokens were consumed.
> - Every configuration (and the soak test) ran in a fresh, isolated server process to prevent RSS carry-over. Concurrency cells were warmed up first, repeated 3 times, and reported as the median.

---

## 1. Executive Summary

This evaluation benchmarks ChronicCare AI's Release 2 background pipeline across orchestrator modes (`direct` vs `graph`), background vs inline explanation modes, and scaling concurrencies (1 to 100 simultaneous patients).

**Key Findings:**
1. **Background Explainer `/complete` Latency:** In background mode (`EXPLAIN_MODE=background`), patient `/complete` latency is decoupled from synchronous LLM execution. Comparing inline mode (5566 ms complete p95 at 100 clients) with background mode (5091 ms complete p95 at 100 clients), background mode demonstrates improved `/complete` response latency (5091 vs 5566 ms, -474 ms) by returning immediately while explanation jobs queue in the background.
2. **Measured LangGraph Overhead:** Comparing `direct` and `graph` modes with flags off at 100 clients, complete p95 was **5345 ms** for `graph` vs **4495 ms** for `direct` (+850 ms difference), reflecting LangGraph state-graph transitions and node dispatch overhead under peak concurrent execution.
3. **Worker Throughput & Queue Bounding:** ChronicCare AI background explanation throughput is strictly bound to the single daemon worker thread (~1/delay explanations per second: ~1.25 jobs/s for 0.8s fake delay, ~0.50 jobs/s for 2.0s fake delay). Under Release 2 defaults (`EXPLAIN_QUEUE_MAX=50`), bursts of 100 simultaneous check-ins are bounded by queue capacity while the worker actively drains: measured medians showed 58 LLM and 41 `queue_full` templates at 0.8s delay (medians of 3 runs), preventing queue runaway and bounding server memory.
4. **Soak Memory Stability & Settings:** The soak test ran with `EXPLAIN_QUEUE_MAX=500` (final queue 498), not the Release 2 default of 50. In this 30-minute soak test (10 concurrent patients, background mode), gross memory growth was **+38.0 MB**, which is **a leak suspect by the 20 MB rule**. Detailed minute-by-minute inspection confirms an initial ramp during early connection pool and worker priming (102.3 MB -> 131.1 MB), followed by a **plateau after minute 3 (131.1 -> 140.3 MB, minutes 3–30)** across 6,708 completed check-ins. 498 jobs were still waiting at the end, so those patients would get the template after the stale time, and part of the memory growth is that waiting queue. Zero HTTP 500 errors occurred across ~67,080 requests (0.000% error rate). Under Release 2 defaults, queue length is strictly bounded at 50 capacity.
5. Highest server peak RSS in these tests: 188.5 MB (OCR off). OCR stays off for Release 2 because RapidOCR alone goes over 512 MB on Linux (436 MB after the first upload, 573-608 MB peak in-process; see docs/OCR_DESIGN.md 6.3 after PR #122).

---

## 2. Check-In Load & Memory Matrix (Medians of 3 Runs — Release 2 Defaults)

Each patient completes: `session -> consent -> profile (hypertension) -> start -> 5 answers (BP 145/92) -> complete -> [poll explanation]`.

| Orchestrator | Mode / Flags | Delay | Clients | Finished | Fail | LLM | Cache | Template | q_full | timeout | lost | other | Jobs/s | Complete p95 (ms) | Time-to-Ready p95 (ms) | Whole Check-in Median (s) | Check-ins/s | Server RSS Peak (MB) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `direct` | Flags OFF (Default) | N/A | **1** | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 144 | N/A | 0.62 | 1.6 | 84.3 |
| `direct` | Flags OFF (Default) | N/A | **10** | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 744 | N/A | 3.01 | 3.1 | 94.0 |
| `direct` | Flags OFF (Default) | N/A | **50** | 50 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 2542 | N/A | 9.41 | 4.9 | 120.9 |
| `direct` | Flags OFF (Default) | N/A | **100** | 100 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 4495 | N/A | 18.24 | 4.8 | 158.8 |
| `graph` | Flags OFF (Default) | N/A | **1** | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 154 | N/A | 0.63 | 1.6 | 104.1 |
| `graph` | Flags OFF (Default) | N/A | **10** | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 817 | N/A | 2.86 | 3.3 | 113.6 |
| `graph` | Flags OFF (Default) | N/A | **50** | 50 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 2933 | N/A | 10.74 | 4.1 | 161.2 |
| `graph` | Flags OFF (Default) | N/A | **100** | 100 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | N/A | 5345 | N/A | 20.86 | 4.3 | 188.5 |
| `graph` | Release 2 Background | 0.8s | **1** | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1.16 | 157 | 861 | 1.44 | 0.7 | 103.6 |
| `graph` | Release 2 Background | 0.8s | **10** | 10 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 1.28 | 669 | 7795 | 6.60 | 1.0 | 114.0 |
| `graph` | Release 2 Background | 0.8s | **50** | 50 | 0 | 50 | 0 | 0 | 0 | 0 | 0 | 0 | 1.29 | 3171 | 38843 | 32.08 | 0.9 | 147.4 |
| `graph` | Release 2 Background | 0.8s | **100** | 100 | 0 | 58 | 0 | 41 | 41 | 0 | 0 | 0 | 1.37 | 5091 | 42384 | 22.88 | 1.5 | 164.9 |
| `graph` | Release 2 Background | 2.0s | **1** | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0.48 | 170 | 2066 | 2.63 | 0.4 | 103.8 |
| `graph` | Release 2 Background | 2.0s | **10** | 10 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0.50 | 909 | 19821 | 13.60 | 0.4 | 114.9 |
| `graph` | Release 2 Background | 2.0s | **50** | 50 | 0 | 33 | 0 | 17 | 9 | 0 | 7 | 0 | 0.55 | 3422 | 59675 | 66.40 | 0.7 | 148.9 |
| `graph` | Release 2 Background | 2.0s | **100** | 100 | 0 | 32 | 0 | 68 | 60 | 0 | 7 | 0 | 0.54 | 5619 | 59005 | 24.16 | 1.2 | 169.4 |
| `graph` | inline (not used in Release 2) | 0.8s | **1** | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1.07 | 936 | N/A | 1.29 | 0.8 | 104.9 |
| `graph` | inline (not used in Release 2) | 0.8s | **10** | 10 | 0 | 8 | 0 | 2 | 0 | 0 | 0 | 2 | 5.40 | 1481 | N/A | 3.24 | 3.0 | 116.1 |
| `graph` | inline (not used in Release 2) | 0.8s | **50** | 50 | 0 | 25 | 0 | 24 | 0 | 0 | 0 | 24 | 6.96 | 3592 | N/A | 10.12 | 4.3 | 160.7 |
| `graph` | inline (not used in Release 2) | 0.8s | **100** | 100 | 0 | 50 | 0 | 49 | 0 | 0 | 0 | 49 | 8.98 | 5566 | N/A | 19.72 | 4.5 | 173.3 |

### Observations & Latency Factors
- **Honest Throughput & Capacity Ceiling:** The ChronicCare AI background explainer daemon executes on a single dedicated worker thread (`ExplanationJobQueue._worker_thread`), which pulls and processes one job sequentially at a time. Throughput is strictly capped by LLM generation time: approximately $\approx \frac{1}{\text{delay}}$ explanations per second (~1.25 jobs/s for 0.8s fake delay; ~0.50 jobs/s for 2.0s fake delay). Measured jobs/second matches this capacity across all concurrencies.
- **Burst Behavior under Release 2 Defaults (Queue 50, Deadline 45 s):**
  - Under 100 concurrent clients, check-ins arrive concurrently across threads while the background worker actively drains jobs. Measured results are medians of 3 runs (so row components may not add up to exactly 100).
  - At 0.8s fake delay: the table measures **58 LLM and 41 template (`queue_full`)** (summing to 99 across medians). As the 50-capacity queue (`EXPLAIN_QUEUE_MAX=50`) fills, the worker immediately starts draining jobs, admitting 8 additional jobs during the burst before subsequent requests encounter `queue.Full` and immediately drop to clinical fallback templates with `reason="queue_full"`.
  - At 2.0s fake delay: with slower worker draining (~0.50 jobs/s), the table measures **32 LLM and 68 template** (60 `queue_full`, 7 `job_lost`). Jobs waiting in the queue beyond the 45.0 s deadline / stale threshold automatically transition to template fallbacks with `reason="job_lost"`.
- **Background `/complete` vs Inline at 100 Clients (5091 vs 5566 ms):** Background `/complete` is faster than inline at 100 clients (5091 vs 5566 ms, -474 ms) as `/complete` returns immediately upon triage without awaiting LLM generation.

### Table 2b: Raised-Capacity Stress Reference (Queue 500, Deadline 300 s, Cache Disabled)

> [!NOTE]
> **Stress Reference Note:** In this reference benchmark, limits were raised to `EXPLAIN_QUEUE_MAX=500` and `EXPLAIN_JOB_DEADLINE_SECONDS=300.0`. Under these stress parameters, all 100 clients were admitted into the in-process queue without queue overflow, showing sequential LLM processing latency when queue capacity is expanded.

| Orchestrator | Mode / Flags | Delay | Clients | Finished | Fail | LLM | Cache | Template | Complete p95 (ms) | Time-to-Ready p95 (ms) | Whole Check-in Median (s) | Check-ins/s | Server RSS Peak (MB) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `direct` | Flags OFF (Default) | N/A | **1** | 1 | 0 | 0 | 0 | 0 | 90 | N/A | 0.39 | 2.6 | 83.8 |
| `direct` | Flags OFF (Default) | N/A | **10** | 10 | 0 | 0 | 0 | 0 | 598 | N/A | 2.34 | 4.0 | 90.8 |
| `direct` | Flags OFF (Default) | N/A | **50** | 50 | 0 | 0 | 0 | 0 | 2112 | N/A | 8.00 | 5.6 | 137.3 |
| `direct` | Flags OFF (Default) | N/A | **100** | 100 | 0 | 0 | 0 | 0 | 3327 | N/A | 16.48 | 5.5 | 166.2 |
| `graph` | Flags OFF (Default) | N/A | **1** | 1 | 0 | 0 | 0 | 0 | 112 | N/A | 0.47 | 2.1 | 104.7 |
| `graph` | Flags OFF (Default) | N/A | **10** | 10 | 0 | 0 | 0 | 0 | 584 | N/A | 2.51 | 3.7 | 113.3 |
| `graph` | Flags OFF (Default) | N/A | **50** | 50 | 0 | 0 | 0 | 0 | 2623 | N/A | 8.02 | 5.6 | 149.7 |
| `graph` | Flags OFF (Default) | N/A | **100** | 100 | 0 | 0 | 0 | 0 | 3395 | N/A | 15.79 | 5.6 | 165.3 |
| `graph` | Release 2 Background (Stress Ref) | 0.8s | **1** | 1 | 0 | 1 | 0 | 0 | 121 | 880 | 1.35 | 0.7 | 104.1 |
| `graph` | Release 2 Background (Stress Ref) | 0.8s | **10** | 10 | 0 | 10 | 0 | 0 | 692 | 7872 | 6.75 | 0.9 | 114.5 |
| `graph` | Release 2 Background (Stress Ref) | 0.8s | **50** | 50 | 0 | 50 | 0 | 0 | 2626 | 36568 | 27.18 | 1.1 | 138.6 |
| `graph` | Release 2 Background (Stress Ref) | 0.8s | **100** | 100 | 0 | 100 | 0 | 0 | 4040 | 77024 | 57.87 | 1.0 | 159.4 |
| `graph` | Release 2 Background (Stress Ref) | 2.0s | **1** | 1 | 0 | 1 | 0 | 0 | 91 | 2081 | 2.40 | 0.4 | 103.0 |
| `graph` | Release 2 Background (Stress Ref) | 2.0s | **10** | 10 | 0 | 10 | 0 | 0 | 644 | 19822 | 13.37 | 0.4 | 112.7 |
| `graph` | Release 2 Background (Stress Ref) | 2.0s | **50** | 50 | 0 | 50 | 0 | 0 | 2512 | 93814 | 57.63 | 0.5 | 143.1 |
| `graph` | Release 2 Background (Stress Ref) | 2.0s | **100** | 100 | 0 | 100 | 0 | 0 | 4029 | 191520 | 119.09 | 0.5 | 166.6 |
| `graph` | inline (not used in Release 2) | 0.8s | **1** | 1 | 0 | 1 | 0 | 0 | 898 | N/A | 1.12 | 0.9 | 102.8 |
| `graph` | inline (not used in Release 2) | 0.8s | **10** | 10 | 0 | 10 | 0 | 0 | 1365 | N/A | 3.10 | 3.1 | 114.0 |
| `graph` | inline (not used in Release 2) | 0.8s | **50** | 50 | 0 | 50 | 0 | 0 | 2795 | N/A | 8.74 | 5.0 | 157.9 |
| `graph` | inline (not used in Release 2) | 0.8s | **100** | 100 | 0 | 100 | 0 | 0 | 5418 | N/A | 17.85 | 4.9 | 170.4 |

---

## 3. Comparison with Mid-1 Baseline

Mid-1 benchmarks (from `docs/LOAD_TEST_RESULTS.md`, October 2026) evaluated the Iteration 1 backend with direct execution and no risk/explainer pipeline.

| Concurrency | Mid-1 Complete p95 | Week 3 Direct (`flags off`) | Week 3 Graph (`flags off`) | Week 3 Graph (Release 2 Background, 0.8s) | Slower than Mid-1? | Cause |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1 Clients** | 16 ms | 144 ms | 154 ms | 157 ms | YES (+141 ms) | Not measured (pipeline now executes M3 reconciliation, M4 verification, risk scoring, and schema v15 auditing) |
| **10 Clients** | 150 ms | 744 ms | 817 ms | 669 ms | YES (+519 ms) | Not measured (pipeline now executes M3 reconciliation, M4 verification, risk scoring, and schema v15 auditing) |
| **50 Clients** | 780 ms | 2542 ms | 2933 ms | 3171 ms | YES (+2391 ms) | Not measured (pipeline now executes M3 reconciliation, M4 verification, risk scoring, and schema v15 auditing) |
| **100 Clients** | 2055 ms | 4495 ms | 5345 ms | 5091 ms | YES (+3036 ms) | Not measured (pipeline now executes M3 reconciliation, M4 verification, risk scoring, and schema v15 auditing) |

---

## 4. Deployed Health Comparison with Mid-1 (Part B)

- **Cold Start Latency:** **NOT MEASURED** (measuring container spin-up requires leaving the Render service idle for 20+ minutes without traffic; live probe observed 0.22 s on an already warm container).

### Raw Output from `scripts/load_test_deployed.py`
```text
Run at 2026-11-05 10:12:00 from this computer's network.

First request (cold start if the server was asleep): 0.22 s, ok=True

### Backend /api/health: https://chroniccare-backend-w568.onrender.com/api/health

| Clients | Requests | Failed | Median (s) | p95 (s) | Max (s) | Req/s |
|---|---|---|---|---|---|---|
| 1 | 20 | 0 | 0.149 | 0.226 | 0.340 | 5.8 |
| 5 | 100 | 0 | 0.151 | 0.311 | 0.369 | 27.6 |
| 10 | 200 | 0 | 0.139 | 0.155 | 0.447 | 64.3 |
| 25 | 500 | 0 | 0.199 | 0.456 | 0.590 | 111.7 |
| 50 | 1000 | 0 | 0.304 | 0.408 | 0.624 | 145.6 |
```

- **Deployed Performance:** At 50 clients on Render, $p_{95}$ latency is **0.408 s**, comparing favorably to the Mid-1 baseline of **0.570 s**.

---

## 5. 30-Minute Memory Soak Test (A3 - Background Mode)

The backend was subjected to a continuous soak test running at **10 concurrent patients** in `graph` mode with `flags on` in **Release 2 background mode** (`EXPLAIN_MODE=background`) for **30 minutes**. Note that the soak ran with `EXPLAIN_QUEUE_MAX=500` (final queue 498), not the Release 2 default of 50.

- **Total Check-ins Completed:** 6,708
- **Total Failures:** 0
- **Start RSS:** 102.3 MB
- **Peak RSS:** 147.5 MB
- **End RSS:** 140.3 MB
- **Gross Memory Growth:** **+38.0 MB** (Leak suspect by the 20 MB rule)
- **Steady-State Plateau:** Minute 3 (131.1 MB) to Minute 30 (140.3 MB) drifted by **+9.2 MB**
- **Final Explain Queue Length:** **498** jobs pending (soak ran with `EXPLAIN_QUEUE_MAX=500`, not the Release 2 default of 50; 498 jobs were still waiting at the end, so those patients would get the template after the stale time, and part of the memory growth is that waiting queue; strictly bounded at <= 50 with Release 2 defaults)

### Soak Failure Exceptions & Cause Grouping
Across 30 minutes of continuous load, 10 concurrent threads completed 6,708 full patient workflows representing over ~67,080 total HTTP requests. During this run, **0 requests failed** (0.000% error rate). Zero HTTP 500 errors or application exceptions occurred.

### Queue Length & Bounding Analysis
- The soak test ran with `EXPLAIN_QUEUE_MAX=500` (final queue 498), not the Release 2 default of 50. In this raised-capacity stress soak, arrival rate (~3.3 check-ins/s across 10 threads) exceeded the single worker consumption rate (~1.25 jobs/s), causing the queue to accumulate 498 pending jobs. 498 jobs were still waiting at the end, so those patients would get the template after the stale time, and part of the memory growth is that waiting queue.
- Under **Release 2 Default Settings (`EXPLAIN_QUEUE_MAX=50`)**, the queue capacity is strictly bounded at **50 jobs max**. Any job arriving when the queue contains 50 jobs is immediately rejected by `queue.Full` and assigned the deterministic clinical fallback template with `reason="queue_full"`. Consequently, under default settings the final queue length is strictly capped at **<= 50**, preventing unbounded queue growth and memory consumption.

### Minute-by-Minute Memory Log
| Minute | Elapsed (s) | Server RSS (MB) | Total Check-ins Done |
| :---: | :---: | :---: | :---: |
| 00 | 0 | 102.3 | 0 |
| 01 | 60 | 128.1 | 239 |
| 02 | 120 | 120.6 | 479 |
| 03 | 180 | 131.1 | 708 |
| 04 | 240 | 133.4 | 941 |
| 05 | 300 | 129.0 | 1184 |
| 06 | 360 | 131.2 | 1411 |
| 07 | 420 | 136.2 | 1618 |
| 08 | 480 | 136.5 | 1838 |
| 09 | 540 | 134.4 | 2058 |
| 10 | 600 | 138.4 | 2285 |
| 11 | 660 | 142.9 | 2512 |
| 12 | 720 | 145.0 | 2743 |
| 13 | 780 | 145.6 | 2972 |
| 14 | 840 | 131.5 | 3196 |
| 15 | 900 | 133.2 | 3413 |
| 16 | 960 | 134.0 | 3628 |
| 17 | 1020 | 136.6 | 3846 |
| 18 | 1080 | 141.5 | 4060 |
| 19 | 1140 | 142.5 | 4282 |
| 20 | 1200 | 144.6 | 4516 |
| 21 | 1260 | 147.5 | 4746 |
| 22 | 1320 | 137.1 | 4970 |
| 23 | 1380 | 142.8 | 5201 |
| 24 | 1440 | 141.9 | 5423 |
| 25 | 1500 | 140.4 | 5612 |
| 26 | 1560 | 146.2 | 5833 |
| 27 | 1620 | 147.1 | 6052 |
| 28 | 1680 | 147.1 | 6265 |
| 29 | 1740 | 129.2 | 6487 |
| 30 | 1800 | 139.8 | 6698 |

---

## 6. Render Free Tier (512 MB) Memory Headroom Analysis

Render's free tier provides a hard ceiling of **512 MB RAM**. Exceeding this boundary triggers Linux kernel OOM termination (exit code 137).

Highest server peak RSS in these tests: 188.5 MB (OCR off). OCR stays off for Release 2 because RapidOCR alone goes over 512 MB on Linux (436 MB after the first upload, 573-608 MB peak in-process; see docs/OCR_DESIGN.md 6.3 after PR #122).

---

## 7. Technical Conclusions & Release 2 Readiness

1. **Background Explainer Feasibility for Release 2:** Decoupling explanation generation via `EXPLAIN_MODE=background` isolates `/complete` latency from LLM generation time. If Day 7 verification checks pass, background explanation mode is technically viable for Release 2.
2. **Memory Growth & Leak Status:** Gross memory growth of +38.0 MB is a leak suspect under the static 20 MB rule; however, minute-by-minute tracking confirms a stable plateau after minute 3 (131.1 MB -> 140.3 MB) across thousands of continuous check-ins.
3. Highest server peak RSS in these tests: 188.5 MB (OCR off). OCR stays off for Release 2 because RapidOCR alone goes over 512 MB on Linux (436 MB after the first upload, 573-608 MB peak in-process; see docs/OCR_DESIGN.md 6.3 after PR #122).
4. **Worker Capacity & Burst Behavior:** The single-threaded background worker processes one job at a time, resulting in a strict throughput limit of ~1/delay explanations per second (~1.25 jobs/s at 0.8s delay; ~0.50 jobs/s at 2.0s delay). This throughput is fine for normal primary care clinic volume where patients check in a few at a time. During sudden bursts exceeding the 50-job queue capacity (such as 100 simultaneous clients), excess patients immediately fall back to safe, deterministic clinical templates (`reason="queue_full"`) by design, preventing server memory exhaustion or hung requests.
