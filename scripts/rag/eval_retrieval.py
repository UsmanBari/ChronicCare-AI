#!/usr/bin/env python3
"""Clinical RAG Retrieval Quality Evaluation Script.

Measures retrieval performance of BM25Retriever against the 60-item clinical test set
(docs/rag/retrieval_test_set.json) across English, Urdu, and Roman Urdu.

Safety & Confidentiality:
- Prints only counts, metrics, item IDs, and chunk IDs.
- Never prints chunk text or patient identifiers.
- Re-uses ml.evaluation.bootstrap_ci for 95% bootstrap confidence intervals.
- Stops with exit code 1 if chunks.jsonl is missing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

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
# PART A: PROGRAMMATIC SOURCE MAPPING RULES (ORIGINAL CITED SOURCES)
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
        "prefix": "aha_acc_2025",
        "aliases": ["acc/aha", "aha/acc", "acc / aha", "aha 2017", "acc 2017", "american heart association"],
        "reason": "licence-blocked (AHA/ACC permission pending since 27 Oct 2026)",
    },
}


def extract_section_path(expected_source: str) -> str | None:
    """Extracts a section designator from an expected source string."""
    m = re.search(r"Section\s+([0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)", expected_source, re.IGNORECASE)
    if m:
        return f"Section {m.group(1)}"
    return None


def map_expected_source(expected_source: str) -> dict[str, Any]:
    """Classifies an item's expected_source into IN_CORPUS, NOT_IN_CORPUS, or UNSURE.

    Rule-based mapping per docs/GUIDELINE_CORPUS.md manifest.
    """
    clean_src = expected_source.strip().lower()
    sec = extract_section_path(expected_source)

    for blocked_id, meta in BLOCKED_CORPUS_SOURCES.items():
        if any(alias in clean_src for alias in meta["aliases"]):
            mapped_id = blocked_id
            if blocked_id == "ada_2026":
                m_sec = re.search(r"Section\s+([0-9]+)", expected_source, re.IGNORECASE)
                if m_sec:
                    mapped_id = f"ada_2026_sec{int(m_sec.group(1)):02d}"
            return {
                "status": "NOT_IN_CORPUS",
                "source_id": mapped_id,
                "section": sec,
                "reason": meta["reason"],
                "allowed_for_rag": False,
            }

    for source_id, meta in ALLOWED_CORPUS_SOURCES.items():
        if any(alias in clean_src for alias in meta["aliases"]):
            return {
                "status": "IN_CORPUS",
                "source_id": source_id,
                "section": sec,
                "reason": "Allowed by copyright manifest",
                "allowed_for_rag": True,
            }

    return {
        "status": "UNSURE",
        "source_id": None,
        "section": sec,
        "reason": "No matching pattern in manifest",
        "allowed_for_rag": False,
    }


# ==============================================================================
# PART A2: OPEN SOURCE MAPPING RULES (SECOND LABEL SET)
# ==============================================================================

def map_open_source(item: dict[str, Any]) -> dict[str, Any]:
    """Maps a test item to available OPEN guideline sources or NONE.

    Decided strictly by programmatic rules from item condition, topic, and
    manifest titles / section paths (never reading chunk text).
    """
    topic = item.get("topic", "")
    cond = item.get("condition", "")
    all_text = " ".join([
        item.get("question_en", ""),
        item.get("question_ur", ""),
        item.get("question_roman_ur", ""),
        " ".join(item.get("answer_points", [])),
    ])

    # Rule 1: Ramadan / Fasting Diabetes
    if cond == "diabetes" and (re.search(r"\b(?:roza|ramadan)\b", all_text, re.IGNORECASE) or "روزہ" in all_text):
        return {
            "status": "OPEN_ANSWERABLE",
            "open_source_id": "idf_dar_2021",
            "label": "idf_dar_2021",
            "allowed_sources": ["idf_dar_2021"],
            "rule_name": "rule_diabetes_ramadan_idf_dar",
        }

    # Rule 2: General Diabetes without Ramadan context
    # No comprehensive open general T2DM clinical management guideline exists in corpus
    # (ADA 2026 is licence-blocked; AKU 2023 is methodology-only).
    if cond == "diabetes":
        return {
            "status": "NONE",
            "open_source_id": "NONE",
            "label": "NONE",
            "allowed_sources": [],
            "rule_name": "rule_diabetes_general_ada_blocked_no_open_source",
        }

    # Rule 3: Pregnancy / Women Hypertension
    if "pregnancy" in topic or "preeclampsia" in topic:
        return {
            "status": "OPEN_ANSWERABLE",
            "open_source_id": "pk_htn_women_2023, ish_2020_htn",
            "label": "pk_htn_women_2023, ish_2020_htn",
            "allowed_sources": ["pk_htn_women_2023", "ish_2020_htn", "who_2021_htn"],
            "rule_name": "rule_htn_pregnancy_women",
        }

    # Rule 4: Blood Pressure Measurement & Monitoring
    if topic in (
        "proper_bp_cuff_technique",
        "white_coat_hypertension",
        "orthostatic_hypotension_elderly",
        "morning_blood_pressure_surge",
    ):
        return {
            "status": "OPEN_ANSWERABLE",
            "open_source_id": "ish_2020_htn, pk_htn_women_2023",
            "label": "ish_2020_htn, pk_htn_women_2023",
            "allowed_sources": ["ish_2020_htn", "pk_htn_women_2023"],
            "rule_name": "rule_htn_measurement_monitoring",
        }

    # Rule 5: Blood Pressure Targets & Categories
    if topic in (
        "bp_normal_target_categories",
        "isolated_systolic_hypertension_elderly",
        "dual_bp_target_in_diabetes",
    ):
        return {
            "status": "OPEN_ANSWERABLE",
            "open_source_id": "who_2021_htn, ish_2020_htn",
            "label": "who_2021_htn, ish_2020_htn",
            "allowed_sources": ["who_2021_htn", "ish_2020_htn"],
            "rule_name": "rule_htn_bp_targets_categories",
        }

    # Rule 6: Pharmacological Treatment & Antihypertensive Agents
    if topic in (
        "amlodipine_ankle_swelling",
        "lisinopril_dry_cough",
        "angioedema_lip_swelling_emergency",
        "abrupt_beta_blocker_cessation_danger",
        "thiazide_diuretic_gout_uric_acid",
        "spironolactone_hyperkalemia_weakness",
        "ace_arb_renal_protection",
        "beta_blocker_hypo_masking",
    ):
        return {
            "status": "OPEN_ANSWERABLE",
            "open_source_id": "who_2021_htn, ish_2020_htn",
            "label": "who_2021_htn, ish_2020_htn",
            "allowed_sources": ["who_2021_htn", "ish_2020_htn"],
            "rule_name": "rule_htn_pharmacological_treatment",
        }

    # Rule 7: Hypertensive Emergencies & Crises
    if topic in (
        "hypertensive_crisis_chest_pain_emergency",
        "stroke_signs_high_bp_emergency",
        "acute_pulmonary_edema_emergency",
        "aortic_dissection_tearing_back_pain_emergency",
        "acute_anuria_hypertensive_emergency",
        "acute_mi_silent_ischemia_emergency",
    ):
        return {
            "status": "OPEN_ANSWERABLE",
            "open_source_id": "ish_2020_htn, pk_htn_women_2023",
            "label": "ish_2020_htn, pk_htn_women_2023",
            "allowed_sources": ["ish_2020_htn", "pk_htn_women_2023", "who_2021_htn"],
            "rule_name": "rule_htn_crises_emergencies",
        }

    # Rule 8: Lifestyle Modifications & Diet
    if topic in (
        "dash_diet_sodium_reduction",
        "potassium_rich_diet_hypertension",
        "caffeine_coffee_bp_effect",
        "weight_loss_bp_benefit",
        "alcohol_intake_hypertension",
        "lifestyle_dual_benefit",
    ):
        return {
            "status": "OPEN_ANSWERABLE",
            "open_source_id": "ish_2020_htn, pk_htn_women_2023",
            "label": "ish_2020_htn, pk_htn_women_2023",
            "allowed_sources": ["ish_2020_htn", "pk_htn_women_2023"],
            "rule_name": "rule_htn_lifestyle_diet",
        }

    # Rule 9: Secondary HTN, Interactions & Comorbidities
    if topic in (
        "cold_medication_pseudoephedrine_spike",
        "nsaid_ibuprofen_blood_pressure_interaction",
        "snoring_sleep_apnea_resistant_bp",
        "ckd_creatinine_egfr_monitoring",
        "statins_cardiovascular_prevention",
        "metabolic_syndrome_concept",
    ):
        return {
            "status": "OPEN_ANSWERABLE",
            "open_source_id": "ish_2020_htn, who_2021_htn",
            "label": "ish_2020_htn, who_2021_htn",
            "allowed_sources": ["ish_2020_htn", "who_2021_htn", "pk_htn_women_2023"],
            "rule_name": "rule_htn_secondary_and_comorbidities",
        }

    return {
        "status": "UNSURE",
        "open_source_id": "UNSURE",
        "label": "UNSURE",
        "allowed_sources": [],
        "rule_name": "rule_unmapped",
    }


def save_open_source_labels(items: list[dict[str, Any]], output_path: Path) -> list[dict[str, Any]]:
    """Generates and saves the open source labels JSON file.

    Format per prompt: ids + label + rule name only.
    """
    labels = []
    for it in items:
        m = map_open_source(it)
        labels.append({
            "id": it["id"],
            "label": m["label"],
            "rule_name": m["rule_name"],
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2, ensure_ascii=False)
    return labels


# ==============================================================================
# PART B: RETRIEVAL METRICS CALCULATION
# ==============================================================================

def check_hit(
    retrieved_chunks: list[dict[str, Any]],
    expected_source_ids: list[str] | set[str] | str,
    expected_section: str | None = None,
    k: int = 5,
) -> tuple[bool, bool]:
    """Checks whether any chunk in top-k matches expected_source_ids and expected_section.

    Returns tuple (source_hit, section_hit).
    """
    if isinstance(expected_source_ids, str):
        allowed = {expected_source_ids.lower()}
    else:
        allowed = {s.lower() for s in expected_source_ids}

    src_hit = False
    sec_hit = False

    for c in retrieved_chunks[:k]:
        src = (c.get("source_id") or "").lower()
        sec_path = (c.get("section_path") or "").lower()
        if src in allowed:
            src_hit = True
            if expected_section and expected_section.lower() in sec_path:
                sec_hit = True

    return (src_hit, sec_hit)


def compute_reciprocal_rank(
    retrieved_chunks: list[dict[str, Any]],
    expected_source_ids: list[str] | set[str] | str,
    expected_section: str | None = None,
    by_section: bool = False,
) -> float:
    """Computes reciprocal rank (1/rank) for the first chunk matching criteria."""
    if isinstance(expected_source_ids, str):
        allowed = {expected_source_ids.lower()}
    else:
        allowed = {s.lower() for s in expected_source_ids}

    for rank, c in enumerate(retrieved_chunks, start=1):
        src = (c.get("source_id") or "").lower()
        sec_path = (c.get("section_path") or "").lower()
        if src in allowed:
            if by_section:
                if expected_section and expected_section.lower() in sec_path:
                    return 1.0 / rank
            else:
                return 1.0 / rank
    return 0.0


def compute_series_ci(scores: list[float], n_boot: int = 1000) -> tuple[float, float | None, float | None]:
    """Computes mean and 95% bootstrap confidence interval using ml.evaluation.bootstrap_ci."""
    if not scores:
        return (0.0, None, None)
    if len(scores) == 1:
        return (float(scores[0]), None, None)

    # bootstrap_ci expects binary y and continuous p. Pass alternating dummy y to satisfy non-empty class check.
    y = np.array([i % 2 for i in range(len(scores))], dtype=int)
    p = np.array(scores, dtype=float)

    def mean_metric(_y: np.ndarray, p_arr: np.ndarray) -> float:
        return float(np.mean(p_arr))

    try:
        ci = bootstrap_ci(y=y, p=p, metric_fn=mean_metric, n_boot=n_boot, stratified=False)
        return (float(ci.point), ci.low, ci.high)
    except (ValueError, ZeroDivisionError, RuntimeError):
        point = float(np.mean(p))
        return (point, None, None)


def format_metric_ci(point: float, low: float | None, high: float | None) -> str:
    """Formats point estimate and bootstrap 95% CI."""
    if low is None or high is None:
        return f"{point:.3f} [N/A, N/A]"
    return f"{point:.3f} [{low:.3f}, {high:.3f}]"


# ==============================================================================
# PART C: SAFETY REDIRECT VALIDATION (TEMPLATE MODE)
# ==============================================================================

def evaluate_safety_redirect_item(
    item: dict[str, Any],
    store: ChunkStore | None = None,
) -> dict[str, Any]:
    """Evaluates a safety-redirect item in template mode (llm=None)."""
    cond = item.get("condition", "hypertension")
    is_emergency = (item.get("kind") == "safety_redirect" or "emergency" in item.get("topic", "").lower())
    level = "emergency" if is_emergency else "review"

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

    res = explain(
        triage_result=triage_result,
        readings=readings,
        store=store,
        llm=None,
        language="en",
    )

    text = " ".join(s.get("text", "") for s in res.get("sentences", []))
    fails: list[str] = []

    for pat in BANNED_DIAGNOSIS_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            fails.append(f"Contained banned diagnosis pattern: {pat}")

    for pat in BANNED_DOSING_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            fails.append(f"Contained banned dosing pattern: {pat}")

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
# MAIN EVALUATION RUNNER
# ==============================================================================

def run_evaluation(
    test_set_path: Path,
    chunks_path: Path | None = None,
    store: ChunkStore | None = None,
    open_labels_path: Path | None = None,
) -> dict[str, Any]:
    """Runs complete RAG retrieval evaluation on real or provided chunks."""
    if not test_set_path.exists():
        print(f"[FATAL] Test set not found at {test_set_path}", file=sys.stderr)
        sys.exit(1)

    with open(test_set_path, encoding="utf-8") as f:
        test_items = json.load(f)

    # 1. Enforce chunks.jsonl presence
    chunk_store = store
    if chunk_store is None:
        if chunks_path is None or not Path(chunks_path).exists():
            print(f"[FATAL] chunks.jsonl is missing at '{chunks_path}'! Cannot run retrieval evaluation.", file=sys.stderr)
            sys.exit(1)
        chunk_store = JsonlChunkStore(str(chunks_path))

    # Print chunk inventory (counts and IDs only, never chunk text)
    all_chunks = chunk_store.list_chunks()
    total_chunk_count = len(all_chunks)
    counts_by_source = Counter(c.get("source_id", "unknown") for c in all_chunks)
    sample_chunk_ids = [c.get("chunk_id", "") for c in all_chunks[:5]]

    print("================================================================================")
    print("CLINICAL RAG RETRIEVAL EVALUATION (DAY 1)")
    print("================================================================================")
    print(f"Corpus Chunk Count: {total_chunk_count}")
    print("Chunks by Source ID:")
    for src, cnt in sorted(counts_by_source.items()):
        print(f"  - {src}: {cnt} chunks")
    print("Sample Chunk IDs (first 5):")
    for cid in sample_chunk_ids:
        print(f"  - {cid}")
    print("================================================================================\n")

    # 2. Part A: Original cited source mapping
    for it in test_items:
        it["original_mapping"] = map_expected_source(it.get("expected_source", ""))
        it["open_mapping"] = map_open_source(it)

    orig_status_counts = Counter(it["original_mapping"]["status"] for it in test_items)
    print("--- PART A: Original Expected Source Manifest Mapping ---")
    print(f"Total benchmark items: {len(test_items)}")
    for st, c in sorted(orig_status_counts.items()):
        print(f"  {st}: {c}")

    # 3. Part A2: Open Source Mapping (Second label set)
    if open_labels_path is not None:
        save_open_source_labels(test_items, open_labels_path)
        print(f"\nSaved open source labels to: {open_labels_path}")

    open_status_counts = Counter(it["open_mapping"]["status"] for it in test_items)
    cond_status_counts: Counter[tuple[str, str]] = Counter()
    for it in test_items:
        cond_status_counts[(it["condition"], it["open_mapping"]["status"])] += 1

    print("\n--- PART A2: Open Source Second Label Set Mapping ---")
    print("Counts by status across all items:")
    for st, c in sorted(open_status_counts.items()):
        print(f"  {st}: {c}")

    print("\nCounts by condition and status:")
    for cond in ("diabetes", "hypertension", "both"):
        print(f"Condition: {cond}")
        for st in ("OPEN_ANSWERABLE", "NONE", "UNSURE"):
            print(f"  {st}: {cond_status_counts[(cond, st)]}")

    # 4. Part B: Retrieval Metrics on OPEN_ANSWERABLE items
    open_items = [it for it in test_items if it["open_mapping"]["status"] == "OPEN_ANSWERABLE"]
    none_items = [it for it in test_items if it["open_mapping"]["status"] == "NONE"]

    retriever = BM25Retriever(chunk_store)
    lang_keys = {
        "en": "question_en",
        "ur": "question_ur",
        "roman_ur": "question_roman_ur",
    }

    metrics_by_lang: dict[str, Any] = {}
    misses_list: list[dict[str, Any]] = []

    print(f"\n--- PART B: Retrieval Evaluation on OPEN_ANSWERABLE Items (N={len(open_items)}) ---")

    for lang in ("en", "ur", "roman_ur"):
        q_key = lang_keys[lang]
        h1_list, h3_list, h5_list, rr_list = [], [], [], []

        for it in open_items:
            q = it.get(q_key, "")
            cond = it.get("condition")
            allowed = it["open_mapping"]["allowed_sources"]

            retrieved = retriever.retrieve(query=q, top_k=5, condition=cond)

            h1, _ = check_hit(retrieved, allowed, k=1)
            h3, _ = check_hit(retrieved, allowed, k=3)
            h5, _ = check_hit(retrieved, allowed, k=5)
            rr = compute_reciprocal_rank(retrieved, allowed)

            h1_list.append(1.0 if h1 else 0.0)
            h3_list.append(1.0 if h3 else 0.0)
            h5_list.append(1.0 if h5 else 0.0)
            rr_list.append(rr)

            if not h3:
                top3_ids = [c.get("chunk_id", "") for c in retrieved[:3]]
                top3_sources = [c.get("source_id", "") for c in retrieved[:3]]
                misses_list.append({
                    "id": it.get("id"),
                    "language": lang,
                    "condition": cond,
                    "allowed_sources": allowed,
                    "top3_chunk_ids": top3_ids,
                    "top3_source_ids": top3_sources,
                })

        pt_h1, lo_h1, hi_h1 = compute_series_ci(h1_list)
        pt_h3, lo_h3, hi_h3 = compute_series_ci(h3_list)
        pt_h5, lo_h5, hi_h5 = compute_series_ci(h5_list)
        pt_mrr, lo_mrr, hi_mrr = compute_series_ci(rr_list)

        metrics_by_lang[lang] = {
            "count": len(open_items),
            "hit1": (pt_h1, lo_h1, hi_h1),
            "hit3": (pt_h3, lo_h3, hi_h3),
            "hit5": (pt_h5, lo_h5, hi_h5),
            "mrr": (pt_mrr, lo_mrr, hi_mrr),
        }

        print(f"\nLanguage: {lang.upper()} (N={len(open_items)})")
        print(f"  Hit@1: {format_metric_ci(pt_h1, lo_h1, hi_h1)}")
        print(f"  Hit@3: {format_metric_ci(pt_h3, lo_h3, hi_h3)}")
        print(f"  Hit@5: {format_metric_ci(pt_h5, lo_h5, hi_h5)}")
        print(f"  MRR:   {format_metric_ci(pt_mrr, lo_mrr, hi_mrr)}")

    # Slices: By condition across English
    print("\n--- Slices by Condition (English, N=36) ---")
    for cond in ("hypertension", "both", "diabetes"):
        cond_items = [it for it in open_items if it["condition"] == cond]
        h1_c, h3_c, h5_c, rr_c = [], [], [], []
        for it in cond_items:
            q = it.get("question_en", "")
            allowed = it["open_mapping"]["allowed_sources"]
            retrieved = retriever.retrieve(query=q, top_k=5, condition=cond)
            h1_c.append(1.0 if check_hit(retrieved, allowed, k=1)[0] else 0.0)
            h3_c.append(1.0 if check_hit(retrieved, allowed, k=3)[0] else 0.0)
            h5_c.append(1.0 if check_hit(retrieved, allowed, k=5)[0] else 0.0)
            rr_c.append(compute_reciprocal_rank(retrieved, allowed))

        pt_h1, lo_h1, hi_h1 = compute_series_ci(h1_c)
        pt_h3, lo_h3, hi_h3 = compute_series_ci(h3_c)
        pt_h5, lo_h5, hi_h5 = compute_series_ci(h5_c)
        pt_mrr, lo_mrr, hi_mrr = compute_series_ci(rr_c)

        print(f"Condition: {cond} (N={len(cond_items)})")
        print(f"  Hit@1: {format_metric_ci(pt_h1, lo_h1, hi_h1)} | Hit@3: {format_metric_ci(pt_h3, lo_h3, hi_h3)} | Hit@5: {format_metric_ci(pt_h5, lo_h5, hi_h5)} | MRR: {format_metric_ci(pt_mrr, lo_mrr, hi_mrr)}")

    # Slices: By kind across English
    print("\n--- Slices by Kind (English, N=36) ---")
    for kind in ("explain", "safety_redirect"):
        kind_items = [it for it in open_items if it.get("kind") == kind]
        h1_k, h3_k, h5_k, rr_k = [], [], [], []
        for it in kind_items:
            q = it.get("question_en", "")
            cond = it.get("condition")
            allowed = it["open_mapping"]["allowed_sources"]
            retrieved = retriever.retrieve(query=q, top_k=5, condition=cond)
            h1_k.append(1.0 if check_hit(retrieved, allowed, k=1)[0] else 0.0)
            h3_k.append(1.0 if check_hit(retrieved, allowed, k=3)[0] else 0.0)
            h5_k.append(1.0 if check_hit(retrieved, allowed, k=5)[0] else 0.0)
            rr_k.append(compute_reciprocal_rank(retrieved, allowed))

        pt_h1, lo_h1, hi_h1 = compute_series_ci(h1_k)
        pt_h3, lo_h3, hi_h3 = compute_series_ci(h3_k)
        pt_h5, lo_h5, hi_h5 = compute_series_ci(h5_k)
        pt_mrr, lo_mrr, hi_mrr = compute_series_ci(rr_k)

        print(f"Kind: {kind} (N={len(kind_items)})")
        print(f"  Hit@1: {format_metric_ci(pt_h1, lo_h1, hi_h1)} | Hit@3: {format_metric_ci(pt_h3, lo_h3, hi_h3)} | Hit@5: {format_metric_ci(pt_h5, lo_h5, hi_h5)} | MRR: {format_metric_ci(pt_mrr, lo_mrr, hi_mrr)}")

    # Misses list (Zero chunk text)
    print("\n--- Retrieval Misses on OPEN_ANSWERABLE Items (Hit@3 Failure) ---")
    print(f"Total Misses Logged: {len(misses_list)}")
    for m in misses_list:
        print(f"  Item {m['id']} [{m['language']}] ({m['condition']}) -> Target: {m['allowed_sources']}")
        print(f"    Returned Sources: {m['top3_source_ids']}")
        print(f"    Returned Chunk IDs: {m['top3_chunk_ids']}")

    # 5. Part B4: Out-of-Corpus NONE items audit
    print(f"\n--- PART B4: Out-of-Corpus NONE Items Audit (N={len(none_items)}) ---")
    none_audit_results = []
    for it in none_items:
        q = it.get("question_en", "")
        cond = it.get("condition")
        retrieved = retriever.retrieve(query=q, top_k=2, condition=cond)
        top_src = retrieved[0].get("source_id") if retrieved else "none"
        top_cid = retrieved[0].get("chunk_id") if retrieved else "none"
        score = retrieved[0].get("bm25_score", 0.0) if retrieved else 0.0
        none_audit_results.append({
            "id": it["id"],
            "topic": it["topic"],
            "returned_source_id": top_src,
            "returned_chunk_id": top_cid,
            "bm25_score": score,
        })
        print(f"  {it['id']} ({it['topic']}): top_source={top_src} chunk={top_cid[:10]}... bm25={score:.2f}")

    # 6. Part C: Safety-Redirect Template Evaluation
    safety_items = [it for it in test_items if it.get("kind") == "safety_redirect"]
    safety_results = []
    for it in safety_items:
        res = evaluate_safety_redirect_item(it, store=chunk_store)
        safety_results.append(res)

    pass_count = sum(1 for r in safety_results if r["pass"])
    pass_pct = (pass_count / len(safety_results) * 100.0) if safety_results else 0.0

    print("\n--- PART C: Safety-Redirect Template Evaluation ---")
    print(f"Safety Redirect Total: {len(safety_results)} items | Passed: {pass_count}/{len(safety_results)} ({pass_pct:.1f}%)")
    for r in safety_results:
        status_str = "PASS" if r["pass"] else "FAIL"
        print(f"  [{status_str}] {r['id']} ({r['topic']}) - Template: {r['template_key']}")

    return {
        "chunk_count": total_chunk_count,
        "counts_by_source": counts_by_source,
        "original_status_counts": orig_status_counts,
        "open_status_counts": open_status_counts,
        "metrics_by_lang": metrics_by_lang,
        "misses_list": misses_list,
        "none_audit_results": none_audit_results,
        "safety_pass_count": pass_count,
        "safety_total": len(safety_results),
        "safety_pass_pct": pass_pct,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval against clinical test set.")
    parser.add_argument(
        "--test-set",
        type=Path,
        default=REPO_ROOT / "docs" / "rag" / "retrieval_test_set.json",
        help="Path to retrieval test set JSON file.",
    )
    parser.add_argument(
        "--chunks",
        type=Path,
        default=None,
        help="Path to chunks.jsonl file.",
    )
    parser.add_argument(
        "--open-labels",
        type=Path,
        default=REPO_ROOT / "docs" / "rag" / "retrieval_test_set_open_labels.json",
        help="Output path for open source labels JSON file.",
    )
    args = parser.parse_args()

    chunks_file = args.chunks
    if chunks_file is None:
        data_dir = os.environ.get("CHRONICCARE_DATA_DIR")
        if data_dir:
            chunks_file = Path(data_dir) / "rag" / "chunks.jsonl"

    if chunks_file is None or not chunks_file.exists():
        print(f"[FATAL] chunks.jsonl not found at '{chunks_file}'. Evaluation cannot proceed.", file=sys.stderr)
        print("Please place chunks.jsonl in $env:CHRONICCARE_DATA_DIR\\rag\\chunks.jsonl or pass --chunks.", file=sys.stderr)
        sys.exit(1)

    _ = run_evaluation(
        test_set_path=args.test_set,
        chunks_path=chunks_file,
        open_labels_path=args.open_labels,
    )
    print("\n[SUCCESS] Retrieval evaluation run completed.")


if __name__ == "__main__":
    main()
