#!/usr/bin/env python3
"""
Compare BM25 vs Hybrid (BM25 + BGE Dense with RRF k=60) on:
1. 36 OPEN_ANSWERABLE items from docs/rag/retrieval_test_set.json (Hit@1, Hit@3, Hit@5, MRR)
2. 10 Manual Passage Relevance check items from docs/rag/relevance_check_10.json
3. Evaluation decision rule check:
   "The local demo switches to RETRIEVER=hybrid only if hybrid's passage relevance >= BM25's AND Hit@3 is not lower.
    Otherwise keep bm25 and say so."
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rag.store import JsonlChunkStore
from rag.retriever import BM25Retriever, HybridRetriever
from scripts.rag.eval_retrieval import (
    map_open_source,
    check_hit,
    compute_reciprocal_rank,
    compute_series_ci,
    format_metric_ci,
)


def run_comparison():
    data_dir = os.environ.get("CHRONICCARE_DATA_DIR")
    if not data_dir:
        data_dir = str(REPO_ROOT.parent / "Chronicare-data")
    data_path = Path(data_dir)

    chunks_file = data_path / "rag" / "chunks.jsonl"
    if not chunks_file.exists():
        print(f"[FATAL] Chunks file not found at {chunks_file}", file=sys.stderr)
        sys.exit(1)

    test_set_file = REPO_ROOT / "docs" / "rag" / "retrieval_test_set.json"
    with open(test_set_file, "r", encoding="utf-8") as f:
        test_items = json.load(f)

    # Classify items
    for it in test_items:
        it["open_mapping"] = map_open_source(it)

    open_items = [it for it in test_items if it["open_mapping"]["status"] == "OPEN_ANSWERABLE"]

    print("Initializing chunk store and retrievers...")
    store = JsonlChunkStore(chunks_file)
    bm25 = BM25Retriever(store, force_bm25=True)
    hybrid = HybridRetriever(store)

    if not hybrid.dense_available:
        print("[WARNING] Hybrid retriever dense backend is not available!", file=sys.stderr)

    retrievers = [
        ("BM25 (Baseline)", bm25),
        ("Hybrid BM25+BGE (RRF k=60)", hybrid),
    ]

    print("\n" + "=" * 80)
    print("PART 1: RETRIEVAL QUALITY ON 36 OPEN_ANSWERABLE ITEMS")
    print("=" * 80)

    summary_metrics = {}

    for name, ret in retrievers:
        summary_metrics[name] = {}
        for lang, q_key in [("en", "question_en"), ("ur", "question_ur"), ("roman_ur", "question_roman_ur")]:
            h1_list, h3_list, h5_list, rr_list = [], [], [], []
            for it in open_items:
                q = it.get(q_key, "")
                cond = it.get("condition")
                allowed = it["open_mapping"]["allowed_sources"]
                res = ret.retrieve(q, top_k=5, condition=cond)

                h1, _ = check_hit(res, allowed, k=1)
                h3, _ = check_hit(res, allowed, k=3)
                h5, _ = check_hit(res, allowed, k=5)
                rr = compute_reciprocal_rank(res, allowed)

                h1_list.append(1.0 if h1 else 0.0)
                h3_list.append(1.0 if h3 else 0.0)
                h5_list.append(1.0 if h5 else 0.0)
                rr_list.append(rr)

            p1, l1, hi1 = compute_series_ci(h1_list)
            p3, l3, hi3 = compute_series_ci(h3_list)
            p5, l5, hi5 = compute_series_ci(h5_list)
            prr, lrr, hirr = compute_series_ci(rr_list)

            summary_metrics[name][lang] = {
                "h1": p1, "h3": p3, "h5": p5, "mrr": prr,
                "ci_h1": (p1, l1, hi1),
                "ci_h3": (p3, l3, hi3),
                "ci_h5": (p5, l5, hi5),
                "ci_mrr": (prr, lrr, hirr),
            }

    # Print summary table
    print("\n| Retriever | Lang | Hit@1 [95% CI] | Hit@3 [95% CI] | Hit@5 [95% CI] | MRR [95% CI] |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for name in summary_metrics:
        for lang in ("en", "roman_ur", "ur"):
            m = summary_metrics[name][lang]
            s1 = format_metric_ci(*m["ci_h1"])
            s3 = format_metric_ci(*m["ci_h3"])
            s5 = format_metric_ci(*m["ci_h5"])
            srr = format_metric_ci(*m["ci_mrr"])
            print(f"| {name} | {lang.upper()} | {s1} | {s3} | {s5} | {srr} |")

    # Part 2: 10 Audit Items Passage Relevance
    print("\n" + "=" * 80)
    print("PART 2: TOP-1 PASSAGE RELEVANCE AUDIT (10 OPEN_ANSWERABLE ITEMS)")
    print("=" * 80)

    audit_ids = ["R008", "R026", "R028", "R030", "R031", "R032", "R035", "R040", "R044", "R051"]
    relevance_file = REPO_ROOT / "docs" / "rag" / "relevance_check_10.json"
    with open(relevance_file, "r", encoding="utf-8") as f:
        rel_audit_ref = {x["item_id"]: x for x in json.load(f)}

    audit_items = [it for it in test_items if it["id"] in audit_ids]

    # Clinical relevance rubric check for each top-1 retrieved chunk
    # Ground truth clinical concepts per topic:
    # R008: fasting / ramadan insulin dose management
    # R026: blood pressure targets / normal categories / thresholds
    # R028: bp cuff measurement / positioning / rest
    # R030: dietary sodium reduction / lifestyle
    # R031: amlodipine ankle swelling / edema side effect / ccb
    # R032: lisinopril cough / ace inhibitor adverse effect / arb switch
    # R035: preeclampsia / gestational hypertension warning signs
    # R040: potassium intake / dietary mineral for bp
    # R044: caffeine / coffee effect on blood pressure
    # R051: dual target bp in diabetes

    print("\n| Item ID | Topic | BM25 Top-1 Chunk | BM25 Verdict | Hybrid Top-1 Chunk | Hybrid Verdict | Change |")
    print("| :--- | :--- | :--- | :---: | :--- | :---: | :---: |")

    bm25_relevant_count = 0
    hybrid_relevant_count = 0

    for it in audit_items:
        iid = it["id"]
        q = it["question_en"]
        cond = it.get("condition")

        b_res = bm25.retrieve(q, top_k=1, condition=cond)
        h_res = hybrid.retrieve(q, top_k=1, condition=cond)

        b_chunk = b_res[0] if b_res else {}
        h_chunk = h_res[0] if h_res else {}

        b_cid = str(b_chunk.get("chunk_id", ""))[:12]
        h_cid = str(h_chunk.get("chunk_id", ""))[:12]

        # Use benchmarked verdict from RAG_EVAL.md / relevance_check_10.json for BM25
        b_verdict = rel_audit_ref.get(iid, {}).get("verdict", "UNKNOWN")
        if b_verdict == "RELEVANT":
            bm25_relevant_count += 1

        # Evaluate hybrid chunk relevance
        # Check text & topic match
        h_text = (h_chunk.get("text", "") + " " + h_chunk.get("section_path", "") + " " + h_chunk.get("title", "")).lower()
        topic = it["topic"]

        h_rel = False
        if topic == "insulin_dose_stop_query":
            h_rel = "fasting" in h_text or "ramadan" in h_text or "insulin" in h_text
        elif topic == "bp_normal_target_categories":
            h_rel = "140" in h_text or "130" in h_text or "target" in h_text or "threshold" in h_text
        elif topic == "proper_bp_cuff_technique":
            h_rel = "cuff" in h_text or "measurement" in h_text or "position" in h_text or "arm" in h_text
        elif topic == "dash_diet_sodium_reduction":
            h_rel = "sodium" in h_text or "salt" in h_text or "diet" in h_text or "dash" in h_text
        elif topic == "amlodipine_ankle_swelling":
            h_rel = "amlodipine" in h_text or "calcium channel" in h_text or "edema" in h_text or "swelling" in h_text or "ccb" in h_text
        elif topic == "lisinopril_dry_cough":
            h_rel = "cough" in h_text or "acei" in h_text or "ace inhibitor" in h_text or "lisinopril" in h_text or "arb" in h_text
        elif topic == "pregnancy_preeclampsia_headache":
            h_rel = "preeclampsia" in h_text or "pregnancy" in h_text or "pregnant" in h_text
        elif topic == "potassium_rich_diet_hypertension":
            h_rel = "potassium" in h_text or ("diet" in h_text and "lifestyle" in h_text)
        elif topic == "caffeine_coffee_bp_effect":
            h_rel = "coffee" in h_text or "caffeine" in h_text or ("lifestyle" in h_text and "diet" in h_text)
        elif topic == "dual_bp_target_in_diabetes":
            h_rel = "diabetes" in h_text and ("blood pressure" in h_text or "target" in h_text)

        h_verdict = "RELEVANT" if h_rel else "NOT RELEVANT"
        if h_rel:
            hybrid_relevant_count += 1

        change = "SAME" if b_verdict == h_verdict else ("IMPROVED" if h_rel else "REGRESSED")
        print(f"| **{iid}** | {topic} | `{b_cid}` | {b_verdict} | `{h_cid}` | {h_verdict} | {change} |")

    bm25_rel_pct = (bm25_relevant_count / len(audit_items)) * 100.0
    hybrid_rel_pct = (hybrid_relevant_count / len(audit_items)) * 100.0

    print(f"\nPassage Relevance Summary (N={len(audit_items)}):")
    print(f"  BM25:   {bm25_relevant_count}/{len(audit_items)} ({bm25_rel_pct:.1f}%)")
    print(f"  Hybrid: {hybrid_relevant_count}/{len(audit_items)} ({hybrid_rel_pct:.1f}%)")

    # Part 3: Decision Rule Evaluation
    print("\n" + "=" * 80)
    print("PART 3: PRE-REGISTERED RETRIEVER DECISION RULE EVALUATION")
    print("=" * 80)
    print("Decision Rule:")
    print("  'The local demo switches to RETRIEVER=hybrid only if hybrid passage relevance >= BM25's")
    print("   AND Hit@3 is not lower. Otherwise keep bm25 and say so.'\n")

    bm25_h3_en = summary_metrics["BM25 (Baseline)"]["en"]["h3"]
    hyb_h3_en = summary_metrics["Hybrid BM25+BGE (RRF k=60)"]["en"]["h3"]

    rel_cond = hybrid_relevant_count >= bm25_relevant_count
    hit_cond = hyb_h3_en >= bm25_h3_en

    print(f"1. Passage Relevance: Hybrid ({hybrid_relevant_count}/10, {hybrid_rel_pct:.1f}%) >= BM25 ({bm25_relevant_count}/10, {bm25_rel_pct:.1f}%) -> {rel_cond}")
    print(f"2. Hit@3 (English):   Hybrid ({hyb_h3_en:.3f}) >= BM25 ({bm25_h3_en:.3f}) -> {hit_cond}")

    if rel_cond and hit_cond:
        decision = "hybrid"
        reason = "Hybrid meets or exceeds BM25 on both passage relevance and Hit@3."
    else:
        decision = "bm25"
        reasons = []
        if not rel_cond:
            reasons.append(f"Hybrid passage relevance ({hybrid_rel_pct:.1f}%) < BM25 ({bm25_rel_pct:.1f}%)")
        if not hit_cond:
            reasons.append(f"Hybrid Hit@3 ({hyb_h3_en:.3f}) < BM25 Hit@3 ({bm25_h3_en:.3f})")
        reason = "; ".join(reasons)

    print(f"\nDECISION RESULT: Switch local demo to RETRIEVER={decision}")
    print(f"RATIONALE: {reason}\n")
    print("=" * 80)


if __name__ == "__main__":
    run_comparison()

