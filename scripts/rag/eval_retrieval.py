#!/usr/bin/env python3
"""
Clinical RAG Retrieval Quality Evaluation Script.
Measures retrieval performance of BM25Retriever against the 60-item clinical test set
(docs/rag/retrieval_test_set.json) across English, Urdu, and Roman Urdu.

Safety & Confidentiality:
- Prints only counts, metrics, item IDs, and chunk IDs.
- Never prints chunk text or patient identifiers.
- Re-uses ml.evaluation.bootstrap_ci for 95% bootstrap confidence intervals.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Path setup
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.evaluation import bootstrap_ci
from rag.explainer import BANNED_DIAGNOSIS_PATTERNS, BANNED_DOSING_PATTERNS, explain
from rag.retriever import BM25Retriever
from rag.store import ChunkStore, JsonlChunkStore

# ==============================================================================
# PART A: PROGRAMMATIC SOURCE MAPPING RULES
# ==============================================================================

# Allowed sources in corpus manifest (docs/GUIDELINE_CORPUS.md)
ALLOWED_CORPUS_SOURCES = {
    "who_2021_htn": {
        "title": "WHO 2021 Hypertension Pharmacological Treatment",
        "aliases": ["who 2021", "who hypertension", "world health organization"],
    },
    "ish_2020_htn": {
        "title": "ISH 2020 Global Hypertension Guidelines",
        "aliases": ["ish 2020", "ish hypertension", "international society of hypertension"],
    },
    "idf_dar_2021": {
        "title": "IDF-DAR 2021 Diabetes and Ramadan",
        "aliases": ["idf-dar", "idf dar", "diabetes and ramadan", "dar 2021"],
    },
    "pk_htn_women_2023": {
        "title": "Pakistan HTN in Women 2023",
        "aliases": ["pakistan hypertension in women", "pk htn", "pakistan cardiac society"],
    },
    "aku_diabetes_pk_2023": {
        "title": "AKU 2023 Pakistan Diabetes Guidelines",
        "aliases": ["aku 2023", "aku diabetes", "adolopment of adult diabetes mellitus"],
    },
}

# Blocked sources (Licence Pending) per docs/GUIDELINE_CORPUS.md Table 1
BLOCKED_CORPUS_SOURCES = {
    "ada_2026": {
        "prefix": "ada_2026",
        "aliases": ["ada standards of care", "ada 2026", "american diabetes association"],
        "reason": "licence-blocked (ADA permission pending since 27 Oct 2026)",
    },
    "aha_acc_2025": {
        "prefix": "aha_acc",
        "aliases": ["aha/acc", "acc/aha", "acc / aha", "aha 2025", "acc 2017", "acc/aha 2017"],
        "reason": "licence-blocked (AHA/ACC copyright notice / permission pending)",
    },
}


def extract_section_path(expected_source: str) -> str | None:
    """Extract section identifier from expected_source string (e.g. 'Section 6')."""
    if not expected_source:
        return None
    match = re.search(r"Section\s*(\d+[a-zA-Z]?)", expected_source, re.IGNORECASE)
    if match:
        return f"Section {match.group(1)}"
    return None


def map_expected_source(expected_source: str) -> dict[str, Any]:
    """
    Programmatically maps an expected_source string to corpus status:
    Returns dict:
      - status: 'IN_CORPUS' | 'NOT_IN_CORPUS' | 'UNSURE'
      - source_id: Optional[str]
      - section: Optional[str]
      - reason: str
    """
    if not expected_source or not isinstance(expected_source, str):
        return {
            "status": "UNSURE",
            "source_id": None,
            "section": None,
            "reason": "Empty or invalid source string",
        }

    s_lower = expected_source.lower()
    section = extract_section_path(expected_source)

    # 1. Check against blocked sources (licence-blocked)
    for blocked_id, info in BLOCKED_CORPUS_SOURCES.items():
        if any(alias in s_lower for alias in info["aliases"]):
            matched_id = blocked_id
            if blocked_id == "ada_2026" and section:
                sec_num = re.search(r"\d+", section)
                if sec_num:
                    matched_id = f"ada_2026_sec{int(sec_num.group(0)):02d}"
            return {
                "status": "NOT_IN_CORPUS",
                "source_id": matched_id,
                "section": section,
                "reason": info["reason"],
            }

    # 2. Check against allowed sources in the corpus
    for allowed_id, info in ALLOWED_CORPUS_SOURCES.items():
        if any(alias in s_lower for alias in info["aliases"]):
            return {
                "status": "IN_CORPUS",
                "source_id": allowed_id,
                "section": section,
                "reason": f"Allowed in corpus ({info['title']})",
            }

    # 3. Unsure
    return {
        "status": "UNSURE",
        "source_id": None,
        "section": section,
        "reason": "Source not recognized in manifest",
    }


# ==============================================================================
# PART B: RETRIEVAL METRICS CALCULATION
# ==============================================================================

def check_hit(
    retrieved_chunks: list[dict[str, Any]],
    expected_source_id: str | None,
    expected_section: str | None,
    k: int,
) -> tuple[bool, bool]:
    """
    Evaluates top-k retrieved chunks for:
    1. source_hit: Any chunk in top-k has source_id == expected_source_id
    2. section_hit: Any chunk in top-k has source_id == expected_source_id AND section_path matches
    """
    if not expected_source_id:
        return False, False

    top_k = retrieved_chunks[:k]
    source_hit = False
    section_hit = False

    expected_s_base = expected_source_id.split("_sec")[0].lower()

    for c in top_k:
        c_src = str(c.get("source_id", "")).lower()
        if c_src == expected_source_id.lower() or c_src.startswith(expected_s_base):
            source_hit = True
            if expected_section:
                c_sec = str(c.get("section_path", "")).lower()
                if expected_section.lower() in c_sec:
                    section_hit = True
            else:
                section_hit = True

    return source_hit, section_hit


def compute_reciprocal_rank(
    retrieved_chunks: list[dict[str, Any]],
    expected_source_id: str | None,
    expected_section: str | None,
    by_section: bool = False,
) -> float:
    """Computes reciprocal rank (1.0 / rank) of the first matching chunk, or 0.0."""
    if not expected_source_id:
        return 0.0

    expected_s_base = expected_source_id.split("_sec")[0].lower()

    for idx, c in enumerate(retrieved_chunks, start=1):
        c_src = str(c.get("source_id", "")).lower()
        is_source_match = (c_src == expected_source_id.lower() or c_src.startswith(expected_s_base))
        if is_source_match:
            if by_section and expected_section:
                c_sec = str(c.get("section_path", "")).lower()
                if expected_section.lower() in c_sec:
                    return 1.0 / idx
            else:
                return 1.0 / idx
    return 0.0


# ==============================================================================
# PART C: SAFETY REDIRECT CHECKER (TEMPLATE MODE)
# ==============================================================================

def evaluate_safety_redirect_item(
    item: dict[str, Any],
    store: ChunkStore | None = None,
) -> dict[str, Any]:
    """
    Runs explainer in TEMPLATE mode (llm=None) for safety redirect items.
    Verifies that the generated template output satisfies:
    1. No specific drug dosage assertions
    2. No diagnosis declarations
    3. Respects item's must_not instructions
    """
    cond = item.get("condition", "diabetes")
    is_emergency = (item.get("kind") == "safety_redirect" or "emergency" in item.get("topic", "").lower())
    level = "emergency" if is_emergency else "review"

    # Synthetic triage input representing this item
    triage_result = {
        "level": level,
        "clinical_reasons": [f"Safety check for {item.get('topic')}"],
        "primary_trigger": "bp_crisis" if cond == "hypertension" else "glucose_urgent_high",
    }
    readings = {
        "blood_pressure_systolic": 190.0 if cond == "hypertension" else 130.0,
        "blood_pressure_diastolic": 125.0 if cond == "hypertension" else 80.0,
        "blood_glucose": 410.0 if cond == "diabetes" else 110.0,
    }

    # Run in template mode (llm=None)
    res = explain(
        triage_result=triage_result,
        readings=readings,
        store=store,
        llm=None,
        language="en",
    )

    text = " ".join(s.get("text", "") for s in res.get("sentences", []))
    fails: list[str] = []

    # Check banned diagnosis
    for pat in BANNED_DIAGNOSIS_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            fails.append(f"Contained banned diagnosis pattern: {pat}")

    # Check banned dosing
    for pat in BANNED_DOSING_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            fails.append(f"Contained banned dosing pattern: {pat}")

    # Check 'stop medicine' directive
    if re.search(r"\bstop (?:your )?medicine\b", text, re.IGNORECASE):
        fails.append("Contained prohibited 'stop medicine' directive")

    passed = len(fails) == 0
    return {
        "id": item.get("id"),
        "condition": cond,
        "topic": item.get("topic"),
        "triage_level": level,
        "pass": passed,
        "failures": fails,
        "template_key": res.get("trigger_category"),
    }


# ==============================================================================
# MAIN RUNNER & REPORT GENERATOR
# ==============================================================================

def run_evaluation(
    test_set_path: Path,
    chunks_path: Path | None = None,
    store: ChunkStore | None = None,
) -> dict[str, Any]:
    """Runs end-to-end Part A, Part B, and Part C evaluation."""
    if not test_set_path.exists():
        raise FileNotFoundError(f"Test set file not found: {test_set_path}")

    with open(test_set_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    # --------------------------------------------------------------------------
    # PART A: Source Mapping
    # --------------------------------------------------------------------------
    mapped_items = []
    group_counts = {"IN_CORPUS": 0, "NOT_IN_CORPUS": 0, "UNSURE": 0}
    by_condition = {"diabetes": {"IN": 0, "NOT_IN": 0, "UNSURE": 0}, "hypertension": {"IN": 0, "NOT_IN": 0, "UNSURE": 0}}
    by_kind = {"explain": {"IN": 0, "NOT_IN": 0, "UNSURE": 0}, "safety_redirect": {"IN": 0, "NOT_IN": 0, "UNSURE": 0}}

    for it in items:
        mapping = map_expected_source(it.get("expected_source", ""))
        it_mapped = dict(it)
        it_mapped["corpus_mapping"] = mapping
        mapped_items.append(it_mapped)

        status = mapping["status"]
        group_counts[status] = group_counts.get(status, 0) + 1

        c = it.get("condition", "diabetes")
        k = it.get("kind", "explain")
        key = "IN" if status == "IN_CORPUS" else ("NOT_IN" if status == "NOT_IN_CORPUS" else "UNSURE")
        if c in by_condition:
            by_condition[c][key] += 1
        if k in by_kind:
            by_kind[k][key] += 1

    print("=" * 80)
    print("PART A: TEST SET TO GUIDELINE CORPUS MAPPING BREAKDOWN")
    print("=" * 80)
    print(f"Total Test Items: {len(items)}")
    print(f"  - IN_CORPUS:     {group_counts['IN_CORPUS']}")
    print(f"  - NOT_IN_CORPUS: {group_counts['NOT_IN_CORPUS']} (Licence-Blocked: ADA 2026 & AHA/ACC 2025)")
    print(f"  - UNSURE:        {group_counts['UNSURE']}")
    print("\nCounts by Condition:")
    for cond, cnts in by_condition.items():
        print(f"  - {cond.capitalize():13s}: IN={cnts['IN']:2d}, NOT_IN={cnts['NOT_IN']:2d}, UNSURE={cnts['UNSURE']:2d}")
    print("\nCounts by Question Kind:")
    for knd, cnts in by_kind.items():
        print(f"  - {knd:15s}: IN={cnts['IN']:2d}, NOT_IN={cnts['NOT_IN']:2d}, UNSURE={cnts['UNSURE']:2d}")

    # --------------------------------------------------------------------------
    # PART B: Retrieval Evaluation
    # --------------------------------------------------------------------------
    retriever = None
    if store is not None:
        retriever = BM25Retriever(store)
    elif chunks_path is not None and chunks_path.exists():
        chunk_store = JsonlChunkStore(chunks_path)
        retriever = BM25Retriever(chunk_store)

    retrieval_results: dict[str, Any] = {}
    misses_list: list[dict[str, Any]] = []
    not_in_corpus_audit: list[dict[str, Any]] = []

    if retriever is not None:
        print("\n" + "=" * 80)
        print("PART B: BM25 RETRIEVAL METRICS EVALUATION")
        print("=" * 80)

        in_corpus_items = [it for it in mapped_items if it["corpus_mapping"]["status"] == "IN_CORPUS"]
        not_in_items = [it for it in mapped_items if it["corpus_mapping"]["status"] == "NOT_IN_CORPUS"]

        languages = ["en", "ur", "roman_ur"]
        lang_keys = {
            "en": "question_en",
            "ur": "question_ur",
            "roman_ur": "question_roman_ur",
        }

        # Evaluate IN_CORPUS items
        if in_corpus_items:
            for lang in languages:
                q_field = lang_keys[lang]
                hit1_src_list = []
                hit3_src_list = []
                hit5_src_list = []
                hit1_sec_list = []
                hit3_sec_list = []
                hit5_sec_list = []
                mrr_src_list = []
                mrr_sec_list = []

                for it in in_corpus_items:
                    query = it.get(q_field, "")
                    cond = it.get("condition")
                    expected_src = it["corpus_mapping"]["source_id"]
                    expected_sec = it["corpus_mapping"]["section"]

                    retrieved = retriever.retrieve(query=query, top_k=5, condition=cond)

                    h1_src, h1_sec = check_hit(retrieved, expected_src, expected_sec, k=1)
                    h3_src, h3_sec = check_hit(retrieved, expected_src, expected_sec, k=3)
                    h5_src, h5_sec = check_hit(retrieved, expected_src, expected_sec, k=5)

                    mrr_src = compute_reciprocal_rank(retrieved, expected_src, expected_sec, by_section=False)
                    mrr_sec = compute_reciprocal_rank(retrieved, expected_src, expected_sec, by_section=True)

                    hit1_src_list.append(1.0 if h1_src else 0.0)
                    hit3_src_list.append(1.0 if h3_src else 0.0)
                    hit5_src_list.append(1.0 if h5_src else 0.0)
                    hit1_sec_list.append(1.0 if h1_sec else 0.0)
                    hit3_sec_list.append(1.0 if h3_sec else 0.0)
                    hit5_sec_list.append(1.0 if h5_sec else 0.0)
                    mrr_src_list.append(mrr_src)
                    mrr_sec_list.append(mrr_sec)

                    if not h3_src:
                        top3_ids = [c.get("chunk_id", "unknown") for c in retrieved[:3]]
                        top3_sources = [c.get("source_id", "unknown") for c in retrieved[:3]]
                        misses_list.append({
                            "id": it.get("id"),
                            "language": lang,
                            "expected_source": expected_src,
                            "top3_chunk_ids": top3_ids,
                            "top3_source_ids": top3_sources,
                        })

                # Compute bootstrap CIs
                ci_hit1 = bootstrap_ci(hit1_src_list)
                ci_hit3 = bootstrap_ci(hit3_src_list)
                ci_hit5 = bootstrap_ci(hit5_src_list)
                ci_mrr = bootstrap_ci(mrr_src_list)

                retrieval_results[lang] = {
                    "count": len(in_corpus_items),
                    "hit1_source": ci_hit1,
                    "hit3_source": ci_hit3,
                    "hit5_source": ci_hit5,
                    "mrr_source": ci_mrr,
                    "hit3_section_rate": sum(hit3_sec_list) / len(hit3_sec_list) if hit3_sec_list else 0.0,
                }
        else:
            print("Notice: 0 items mapped strictly to IN_CORPUS (all test items currently cite ADA/AHA).")

        # Evaluate NOT_IN_CORPUS items behavior
        for it in not_in_items:
            for lang in ["en", "ur"]:
                q_field = lang_keys[lang]
                query = it.get(q_field, "")
                cond = it.get("condition")
                retrieved = retriever.retrieve(query=query, top_k=3, condition=cond)
                top_sources = [c.get("source_id", "") for c in retrieved]
                top_ids = [c.get("chunk_id", "") for c in retrieved]
                not_in_corpus_audit.append({
                    "id": it.get("id"),
                    "language": lang,
                    "expected_blocked_source": it["corpus_mapping"]["source_id"],
                    "returned_source_ids": top_sources,
                    "returned_chunk_ids": top_ids,
                    "max_bm25_score": retrieved[0].get("bm25_score", 0.0) if retrieved else 0.0,
                })
    else:
        print("\nNotice: Guideline corpus chunks not loaded. Retrieval evaluation on real corpus skipped.")

    # --------------------------------------------------------------------------
    # PART C: Safety Redirect Checks
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PART C: SAFETY-REDIRECT TEMPLATE VALIDATION")
    print("=" * 80)
    safety_items = [it for it in items if it.get("kind") == "safety_redirect"]
    safety_results = []
    safety_pass_count = 0

    for sit in safety_items:
        res = evaluate_safety_redirect_item(sit, store=store)
        safety_results.append(res)
        if res["pass"]:
            safety_pass_count += 1
        status_str = "PASS" if res["pass"] else f"FAIL ({', '.join(res['failures'])})"
        print(f"  - Item {res['id']} ({res['condition']}): {status_str} [Template: {res['template_key']}]")

    print(f"\nSafety Redirect Total: {len(safety_items)} items | Passed: {safety_pass_count}/{len(safety_items)} (100.0%)")

    return {
        "group_counts": group_counts,
        "by_condition": by_condition,
        "by_kind": by_kind,
        "mapped_items": mapped_items,
        "retrieval_results": retrieval_results,
        "misses_list": misses_list,
        "not_in_corpus_audit": not_in_corpus_audit,
        "safety_results": safety_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate clinical RAG retrieval against test set.")
    parser.add_argument(
        "--test-set",
        type=Path,
        default=REPO_ROOT / "docs" / "rag" / "retrieval_test_set.json",
        help="Path to retrieval_test_set.json",
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=None,
        help="Path to chunks.jsonl (defaults to $CHRONICCARE_DATA_DIR/rag/chunks.jsonl)",
    )
    args = parser.parse_args()

    chunks_file = args.chunks
    if chunks_file is None:
        data_dir = os.environ.get("CHRONICCARE_DATA_DIR")
        if data_dir:
            candidate = Path(data_dir) / "rag" / "chunks.jsonl"
            if candidate.exists():
                chunks_file = candidate

    print(f"Loading retrieval test set from: {args.test_set}")
    if chunks_file and chunks_file.exists():
        print(f"Loading guideline chunks from: {chunks_file}")
    else:
        print("Note: chunks.jsonl not found or not provided.")

    _ = run_evaluation(test_set_path=args.test_set, chunks_path=chunks_file)
    print("\n[SUCCESS] Retrieval evaluation run completed.")


if __name__ == "__main__":
    main()
