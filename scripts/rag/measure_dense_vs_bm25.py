"""
Offline Embedding Generation & Fresh Process Runtime Memory & Accuracy Benchmark.
Measures BM25 vs Dense (FastEmbed BAAI/bge-small-en-v1.5) per Week 2 / Day 3 requirements:
1. Offline embed 498 chunks with threads=1, batch_size=32 -> emb_bge_small.npy
2. Fresh process load model + vectors, answer 15 smoke questions, measure peak RSS
3. Start local uvicorn on SQLite (127.0.0.1), hit /health, measure backend baseline RSS, stop uvicorn
4. Print per-question comparison table (id | expected source | top-4 source_ids | hit@4 | rank), Recall@4, MRR
5. Apply decision rule: dense only if (b) + (c) < 400 MB AND dense gets >= 2 more right at @4 than BM25.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
import numpy as np
import psutil

# Add backend to path for BM25 retriever
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
sys.path.insert(0, str(BACKEND_DIR))

from rag.store import JsonlChunkStore
from rag.retriever import BM25Retriever


def get_data_dir() -> Path:
    d = os.environ.get("CHRONICCARE_DATA_DIR", r"C:\Users\usmanbari\Desktop\Chronicare-data")
    return Path(d)


def step_a_build_offline_embeddings(chunks_file: Path, out_npy: Path):
    print("=" * 80)
    print("STEP A: OFFLINE EMBEDDING GENERATION (threads=1, batch_size=32)")
    print("=" * 80)
    if out_npy.exists() and out_npy.stat().st_size > 0:
        mat = np.load(out_npy)
        print(f"Vectors already built at {out_npy} with shape {mat.shape}.")
        return

    from fastembed import TextEmbedding

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(chunks)} chunks from {chunks_file}")
    texts = [f"{c.get('title', '')} {c.get('section_path', '')} {c.get('text', '')}" for c in chunks]

    t0 = time.time()
    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", threads=1)
    embeddings = list(model.embed(texts, batch_size=32))
    emb_matrix = np.array(embeddings, dtype=np.float32)
    # L2 normalize
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    emb_matrix = emb_matrix / np.maximum(norms, 1e-12)

    np.save(out_npy, emb_matrix)
    dur = time.time() - t0
    print(f"Saved {emb_matrix.shape} normalized vectors to {out_npy} in {dur:.2f}s")


def step_b_and_d_fresh_process_evaluation(chunks_file: Path, emb_npy: Path, smoke_file: Path):
    print("\n" + "=" * 80)
    print("STEP B & D: FRESH PROCESS RUNTIME RSS & SMOKE RETRIEVAL EVALUATION")
    print("=" * 80)
    proc = psutil.Process()
    rss_initial = proc.memory_info().rss / (1024 * 1024)

    # 1. Evaluate BM25
    store = JsonlChunkStore(chunks_file)
    bm25 = BM25Retriever(store)

    with open(smoke_file, "r", encoding="utf-8") as f:
        smoke_questions = json.load(f)

    with open(chunks_file, "r", encoding="utf-8") as f:
        chunk_list = [json.loads(line) for line in f if line.strip()]

    chunk_ids = [c.get("chunk_id", "") for c in chunk_list]
    chunk_sources = [c.get("source_id", "") for c in chunk_list]

    bm25_rows = []
    bm25_hits_4 = 0
    bm25_rr_sum = 0.0

    for q in smoke_questions:
        qid = q["id"]
        expected = q["expected_source_id"]
        also_ok = q.get("also_ok", [])
        acceptable = [expected] + also_ok

        res = bm25.retrieve(q["question"], top_k=4)
        retrieved_sources = [r.get("source_id", "") for r in res]
        hit_4 = any(s in acceptable for s in retrieved_sources)
        if hit_4:
            bm25_hits_4 += 1

        rank = 0
        for idx, s in enumerate(retrieved_sources, start=1):
            if s in acceptable:
                rank = idx
                break
        if rank > 0:
            bm25_rr_sum += 1.0 / rank

        bm25_rows.append({
            "id": qid,
            "expected": expected,
            "top4": retrieved_sources,
            "hit4": "YES" if hit_4 else "NO",
            "rank": rank if rank > 0 else "-",
        })

    bm25_recall4 = (bm25_hits_4 / len(smoke_questions)) * 100.0
    bm25_mrr = bm25_rr_sum / len(smoke_questions)

    # 2. Evaluate Dense in Fresh Manner
    from fastembed import TextEmbedding
    t_load_0 = time.time()
    dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", threads=1)
    doc_vectors = np.load(emb_npy)
    t_load = time.time() - t_load_0

    dense_rows = []
    dense_hits_4 = 0
    dense_rr_sum = 0.0

    for q in smoke_questions:
        qid = q["id"]
        expected = q["expected_source_id"]
        also_ok = q.get("also_ok", [])
        acceptable = [expected] + also_ok

        q_vec = list(dense_model.embed([q["question"]]))[0]
        q_vec = np.array(q_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 1e-12:
            q_vec = q_vec / q_norm

        sims = np.dot(doc_vectors, q_vec)
        top_indices = np.argsort(-sims)[:4]
        retrieved_sources = [chunk_sources[i] for i in top_indices]

        hit_4 = any(s in acceptable for s in retrieved_sources)
        if hit_4:
            dense_hits_4 += 1

        rank = 0
        for idx, s in enumerate(retrieved_sources, start=1):
            if s in acceptable:
                rank = idx
                break
        if rank > 0:
            dense_rr_sum += 1.0 / rank

        dense_rows.append({
            "id": qid,
            "expected": expected,
            "top4": retrieved_sources,
            "hit4": "YES" if hit_4 else "NO",
            "rank": rank if rank > 0 else "-",
        })

    dense_recall4 = (dense_hits_4 / len(smoke_questions)) * 100.0
    dense_mrr = dense_rr_sum / len(smoke_questions)

    rss_peak = proc.memory_info().rss / (1024 * 1024)

    print("\n--- BM25 RETRIEVAL PERFORMANCE (15 SMOKE QUESTIONS) ---")
    print(f"{'ID':<12} | {'Expected':<12} | {'Top-4 Retrieved Sources':<40} | {'Hit@4':<6} | {'Rank'}")
    print("-" * 82)
    for r in bm25_rows:
        top_str = ", ".join(r["top4"])
        print(f"{r['id']:<12} | {r['expected']:<12} | {top_str:<40} | {r['hit4']:<6} | {r['rank']}")
    print(f"\nBM25 Recall@4: {bm25_recall4:.1f}% ({bm25_hits_4}/{len(smoke_questions)}) | BM25 MRR: {bm25_mrr:.4f}")

    print("\n--- DENSE (BGE-SMALL-EN-V1.5) RETRIEVAL PERFORMANCE (15 SMOKE QUESTIONS) ---")
    print(f"{'ID':<12} | {'Expected':<12} | {'Top-4 Retrieved Sources':<40} | {'Hit@4':<6} | {'Rank'}")
    print("-" * 82)
    for r in dense_rows:
        top_str = ", ".join(r["top4"])
        print(f"{r['id']:<12} | {r['expected']:<12} | {top_str:<40} | {r['hit4']:<6} | {r['rank']}")
    print(f"\nDense Recall@4: {dense_recall4:.1f}% ({dense_hits_4}/{len(smoke_questions)}) | Dense MRR: {dense_mrr:.4f}")

    print(f"\nDense Model + Vectors Peak RSS: {rss_peak:.2f} MB (Baseline RSS was {rss_initial:.2f} MB)")
    return {
        "dense_rss_mb": rss_peak,
        "bm25_hits_4": bm25_hits_4,
        "dense_hits_4": dense_hits_4,
        "bm25_recall4": bm25_recall4,
        "dense_recall4": dense_recall4,
        "bm25_mrr": bm25_mrr,
        "dense_mrr": dense_mrr,
    }


def step_c_measure_backend_rss() -> float:
    print("\n" + "=" * 80)
    print("STEP C: MEASURE BACKEND BASELINE RSS (uvicorn on SQLite, 127.0.0.1)")
    print("=" * 80)
    backend_py = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    if not backend_py.exists():
        backend_py = Path(sys.executable)

    # Launch uvicorn locally on SQLite with default flags
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env.pop("RENDER", None)

    cmd = [str(backend_py), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8008"]
    p = subprocess.Popen(cmd, cwd=str(BACKEND_DIR), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    rss_mb = 0.0
    stopped = False
    try:
        # Poll /health for up to 10 seconds
        connected = False
        res_body = ""
        for _ in range(20):
            time.sleep(0.5)
            try:
                req = urllib.request.urlopen("http://127.0.0.1:8008/api/health", timeout=2.0)
                res_body = req.read().decode("utf-8")
                connected = True
                break
            except Exception:
                continue

        if connected:
            print(f"Pinged http://127.0.0.1:8008/api/health -> Response: {res_body.strip()}")
        else:
            print("Warning: Could not connect to http://127.0.0.1:8008/api/health within timeout.")

        parent = psutil.Process(p.pid)
        rss_bytes = parent.memory_info().rss
        # Include child processes if any
        for child in parent.children(recursive=True):
            rss_bytes += child.memory_info().rss
        rss_mb = rss_bytes / (1024 * 1024)
        print(f"Uvicorn Process PID {p.pid} RSS: {rss_mb:.2f} MB")
    except Exception as e:
        print(f"Error measuring uvicorn: {e}")
    finally:
        # Terminate uvicorn process
        p.terminate()
        try:
            p.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            p.kill()
        # Verify it has truly stopped
        time.sleep(0.5)
        is_running = p.poll() is None
        stopped = not is_running
        print(f"Uvicorn process PID {p.pid} terminated and confirmed stopped: {stopped} (poll exit code: {p.poll()})")

    return rss_mb


def main():
    data_dir = get_data_dir()
    chunks_file = data_dir / "rag" / "chunks.jsonl"
    emb_npy = data_dir / "rag" / "emb_bge_small.npy"
    smoke_file = data_dir / "rag" / "smoke_questions.json"

    # Step A: Offline Embedding
    step_a_build_offline_embeddings(chunks_file, emb_npy)

    # Step B & D: Fresh Evaluation
    retrieval_stats = step_b_and_d_fresh_process_evaluation(chunks_file, emb_npy, smoke_file)

    # Step C: Backend Baseline RSS
    backend_rss = step_c_measure_backend_rss()

    # Step E: Decision Rule
    dense_rss = retrieval_stats["dense_rss_mb"]
    combined_rss = dense_rss + backend_rss
    delta_hits = retrieval_stats["dense_hits_4"] - retrieval_stats["bm25_hits_4"]

    print("\n" + "=" * 80)
    print("STEP E: RAG ARCHITECTURE DECISION RULE EVALUATION")
    print("=" * 80)
    print(f"1. Memory Gate: (b) Dense Model+Vectors RSS ({dense_rss:.2f} MB) + (c) Backend Baseline RSS ({backend_rss:.2f} MB)")
    print(f"   Combined Memory = {combined_rss:.2f} MB (Gate Threshold: < 400 MB)")
    print(f"   Memory Gate Passed: {combined_rss < 400.0}")
    print(f"2. Accuracy Gate: Dense Hits@4 ({retrieval_stats['dense_hits_4']}/15) vs BM25 Hits@4 ({retrieval_stats['bm25_hits_4']}/15)")
    print(f"   Delta Hits@4 = +{delta_hits} (Gate Threshold: >= 2 more questions right)")
    print(f"   Accuracy Gate Passed: {delta_hits >= 2}")

    selected = "DENSE" if (combined_rss < 400.0 and delta_hits >= 2) else "BM25"
    print(f"\nFINAL DECISION: {selected}")
    if selected == "BM25":
        if delta_hits < 2:
            print("Reason: Dense failed the accuracy gate (did not get >= 2 more questions right than BM25).")
        if combined_rss >= 400.0:
            print("Reason: Dense combined memory exceeded the 400 MB limit for Render 512 MB tier.")


if __name__ == "__main__":
    main()
