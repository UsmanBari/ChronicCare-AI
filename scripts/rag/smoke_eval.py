"""
Local Smoke Evaluation for ChronicCare AI RAG.
Evaluates BM25 retriever against the 15 clinical smoke questions and produces
sample grounded explanations across English, Urdu, and Roman Urdu.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend-poc-technical"))

from rag.explainer import explain
from rag.retriever import BM25Retriever
from rag.store import JsonlChunkStore


def run_smoke_evaluation():
    data_dir_env = os.environ.get("CHRONICCARE_DATA_DIR")
    if not data_dir_env:
        data_dir = Path(__file__).resolve().parent.parent.parent.parent / "Chronicare-data"
    else:
        data_dir = Path(data_dir_env)

    chunks_file = data_dir / "rag" / "chunks.jsonl"
    smoke_file = data_dir / "rag" / "smoke_questions.json"
    benchmark_file = data_dir / "rag" / "dense_vs_bm25_benchmark.json"

    if not chunks_file.exists():
        raise FileNotFoundError(f"Chunks file missing: {chunks_file}")
    if not smoke_file.exists():
        raise FileNotFoundError(f"Smoke questions missing: {smoke_file}")

    print("================================================================================")
    print("CHRONICCARE AI — RAG RETRIEVAL SMOKE EVALUATION (15 CLINICAL QUESTIONS)")
    print("================================================================================")

    store = JsonlChunkStore(chunks_file)
    retriever = BM25Retriever(store)
    print(f"Loaded {store.total_chunks()} guideline chunks from: {chunks_file}")

    with open(smoke_file, "r", encoding="utf-8") as f:
        questions = json.load(f)
    print(f"Evaluating {len(questions)} smoke questions from: {smoke_file}\n")

    hits_at_1 = 0
    hits_at_4 = 0
    rr_list = []
    question_rows = []

    for q in questions:
        qid = q["id"]
        q_text = q["question"]
        expected_src = q["expected_source_id"]
        also_ok = q.get("also_ok", [])
        acceptable = [expected_src] + also_ok

        results = retriever.retrieve(q_text, top_k=10)
        found_rank = None
        for rank, doc in enumerate(results, start=1):
            if doc["source_id"] in acceptable:
                found_rank = rank
                break

        if found_rank == 1:
            hits_at_1 += 1
        if found_rank is not None and found_rank <= 4:
            hits_at_4 += 1

        rr = (1.0 / found_rank) if found_rank is not None else 0.0
        rr_list.append(rr)

        top_src = results[0]["source_id"] if results else "none"
        top_sec = results[0]["section_path"][:35] if results else ""
        top_score = results[0]["bm25_score"] if results else 0.0

        question_rows.append({
            "id": qid,
            "expected": expected_src,
            "rank": str(found_rank) if found_rank is not None else ">10",
            "top_match": top_src,
            "score": f"{top_score:.2f}",
            "section": top_sec,
        })

    mrr = sum(rr_list) / len(rr_list) if rr_list else 0.0
    rec1 = hits_at_1 / len(questions)
    rec4 = hits_at_4 / len(questions)

    # Print summary metrics
    print(f"{'Metric':<25} | {'BM25 Score':<15}")
    print("-" * 43)
    print(f"{'Recall@1 (Hit@1)':<25} | {rec1*100:.1f}% ({hits_at_1}/{len(questions)})")
    print(f"{'Recall@4 (Hit@4)':<25} | {rec4*100:.1f}% ({hits_at_4}/{len(questions)})")
    print(f"{'Mean Reciprocal Rank (MRR)':<25} | {mrr:.4f}")
    print("-" * 43)

    if benchmark_file.exists():
        try:
            with open(benchmark_file, "r", encoding="utf-8") as f:
                bdata = json.load(f)
            dense_info = bdata.get("dense", {})
            print(f"\n[Comparison from Scratch Benchmark with FastEmbed BAAI/bge-small-en-v1.5]")
            print(f"  FastEmbed Recall@4: {dense_info.get('recall@4', 0)*100:.1f}% | MRR: {dense_info.get('mrr', 0):.4f} | Peak RSS: {bdata.get('peak_rss_mb', 0):.2f} MB")
            print(f"  BM25 Recall@4:      {rec4*100:.1f}% | MRR: {mrr:.4f} | Peak RSS: {bdata.get('initial_rss_mb', 0):.2f} MB")
        except Exception:
            pass

    print("\nPER-QUESTION RETRIEVAL BREAKDOWN:")
    print(f"{'ID':<5} | {'Expected':<20} | {'Rank':<6} | {'Top Source':<20} | {'Score':<8} | {'Top Section':<35}")
    print("-" * 105)
    for r in question_rows:
        print(f"{r['id']:<5} | {r['expected']:<20} | {r['rank']:<6} | {r['top_match']:<20} | {r['score']:<8} | {r['section']:<35}")

    print("\n" + "=" * 80)
    print("CHRONICCARE AI — SAMPLE GROUNDED CLINICAL EXPLANATIONS (3 FAKE CASES)")
    print("=" * 80)

    # 3 Example Cases
    sample_cases = [
        {
            "title": "Case 1: Severe Hypertensive Crisis (Emergency)",
            "triage": {
                "level": "emergency",
                "trigger_category": "bp_severe",
                "reasons": ["bp_severe: SBP >= 180 or DBP >= 120"],
                "systolic": 185,
                "diastolic": 125,
            },
            "readings": {"blood_pressure_systolic": 185, "blood_pressure_diastolic": 125},
        },
        {
            "title": "Case 2: Hypoglycemia Trigger (Urgent)",
            "triage": {
                "level": "urgent",
                "trigger_category": "glucose_low",
                "reasons": ["glucose_low: glucose < 70 mg/dL"],
                "glucose": 62,
            },
            "readings": {"glucose": 62},
        },
        {
            "title": "Case 3: Stable Metabolic Check-in (Routine)",
            "triage": {
                "level": "routine",
                "trigger_category": "routine",
                "reasons": ["All parameters within target limits"],
            },
            "readings": {"blood_pressure_systolic": 124, "blood_pressure_diastolic": 78, "glucose": 110},
        },
    ]

    for case in sample_cases:
        print(f"\n--- {case['title']} ---")
        for lang, lang_label in [("en", "English"), ("ur", "Urdu"), ("roman_ur", "Roman Urdu")]:
            res = explain(
                triage_result=case["triage"],
                readings=case["readings"],
                language=lang,
                store=store,
                llm=None,  # Verified fallback template demonstration
            )
            print(f"[{lang_label} Explanation (Mode: {res['mode']})]")
            for s in res["sentences"]:
                print(f"  • {s['text']} (Cites: {s['cites']})")
            if res.get("sources"):
                src = res["sources"][0]
                print(f"    Primary Source: {src['title']} ({src['edition']}) - Section: {src['section_path']}")

    print("\n[Done] Smoke evaluation and demonstration complete.")


if __name__ == "__main__":
    run_smoke_evaluation()
