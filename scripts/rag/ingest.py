"""Clinical Guideline Corpus Ingestion Script.

Processes allowed guideline PDFs, cleans page text, segments sections,
chunks recommendations and body text deterministically, and writes
$CHRONICCARE_DATA_DIR/rag/chunks.jsonl and chunks_meta.json.

Skips any source where allowed_for_rag is False (unless .granted file exists).
"""

import json
import os
from pathlib import Path
import random
import sys
from typing import Any, Dict, List
import pypdf

# Ensure project root is in sys.path so backend-poc-technical.rag.chunking can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend-poc-technical"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rag.chunking import (
    clean_page_text,
    split_sections,
    chunk_section,
    build_chunk_record,
)
from scripts.rag.build_manifest import build_manifest, GUIDELINES_DIR, DATA_DIR, LOGS_DIR

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAG_DIR = DATA_DIR / "rag"
CHUNKS_JSONL = RAG_DIR / "chunks.jsonl"
CHUNKS_META_JSON = RAG_DIR / "chunks_meta.json"


def ingest_corpus() -> Dict[str, Any]:
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_records = build_manifest()
    all_chunks: List[Dict[str, Any]] = []
    source_stats: List[Dict[str, Any]] = []

    for spec in manifest_records:
        source_id = spec["source_id"]
        filename = spec["filename"]
        pdf_path = GUIDELINES_DIR / filename
        allowed = spec.get("allowed_for_rag", False)

        if not allowed:
            print(f"[BLOCKED: licence] Skipping {source_id} ({filename}) - permission pending")
            source_stats.append({
                "source_id": source_id,
                "status": "BLOCKED: licence",
                "pages": spec.get("page_count", 0),
                "sections": 0,
                "chunks": 0,
                "rec_chunks": 0,
                "mean_words": 0,
                "sample_headings": [],
            })
            continue

        if not pdf_path.exists():
            print(f"[MISSING] {filename} not found.")
            continue

        print(f"[INGESTING] {source_id} from {filename}...")
        reader = pypdf.PdfReader(str(pdf_path))
        raw_pages: List[str] = []
        for p in reader.pages:
            raw_pages.append(p.extract_text() or "")

        # 1. Clean pages
        cleaned_pages, dropped_ref_blocks = clean_page_text(raw_pages)

        # 2. Split sections
        sections = split_sections(cleaned_pages)

        # 3. Chunk sections with per-source deduplication
        source_chunks: List[Dict[str, Any]] = []
        rec_count = 0
        seen_texts = set()
        duplicates_dropped = 0

        for sec in sections:
            sec_chunks = chunk_section(sec)
            for c in sec_chunks:
                norm_text = " ".join(c["text"].split())
                if norm_text in seen_texts:
                    duplicates_dropped += 1
                    continue
                seen_texts.add(norm_text)

                record = build_chunk_record(
                    chunk_dict=c,
                    source_id=source_id,
                    title=spec["title"],
                    edition=spec["edition"],
                    priority=spec["priority"],
                )
                source_chunks.append(record)
                if c.get("is_recommendation"):
                    rec_count += 1

        all_chunks.extend(source_chunks)

        word_counts = [c["word_count"] for c in source_chunks]
        mean_words = round(sum(word_counts) / len(word_counts), 1) if word_counts else 0

        # Sample 3 random headings deterministically
        headings = list({c["section_path"].split(" > ")[-1] for c in source_chunks})
        rng = random.Random(42)
        sample_headings = rng.sample(headings, min(3, len(headings))) if headings else []

        source_stats.append({
            "source_id": source_id,
            "status": "INGESTED",
            "pages": len(cleaned_pages),
            "sections": len(sections),
            "chunks": len(source_chunks),
            "rec_chunks": rec_count,
            "mean_words": mean_words,
            "ref_blocks_dropped": dropped_ref_blocks,
            "duplicates_dropped": duplicates_dropped,
            "sample_headings": sample_headings,
        })

    # Write chunks.jsonl
    with open(CHUNKS_JSONL, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    # Write chunks_meta.json
    manifest_hashes = {r["source_id"]: r["sha256"] for r in manifest_records if r.get("sha256")}
    meta = {
        "total_chunks": len(all_chunks),
        "total_words": sum(c["word_count"] for c in all_chunks),
        "source_stats": source_stats,
        "manifest_hashes": manifest_hashes,
    }
    with open(CHUNKS_META_JSON, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return {"meta": meta, "all_chunks": all_chunks, "source_stats": source_stats}


def print_and_save_reports(results: Dict[str, Any]):
    log_file = LOGS_DIR / "ingest_output.txt"
    source_stats = results["source_stats"]
    all_chunks = results["all_chunks"]

    lines = []
    lines.append("=" * 80)
    lines.append("CHRONICCARE AI — RAG INGESTION REPORT")
    lines.append("=" * 80)
    lines.append(f"{'Source ID':<22} | {'Status':<16} | {'Pages':<5} | {'Secs':<4} | {'Chunks':<6} | {'Recs':<4} | {'Mean Wds':<8}")
    lines.append("-" * 80)

    for s in source_stats:
        lines.append(
            f"{s['source_id']:<22} | {s['status']:<16} | {s['pages']:<5} | {s['sections']:<4} | {s['chunks']:<6} | {s['rec_chunks']:<4} | {s['mean_words']:<8}"
        )

    lines.append("-" * 80)
    total_chunks = len(all_chunks)
    total_words = sum(c["word_count"] for c in all_chunks)
    total_ref_dropped = sum(s.get("ref_blocks_dropped", 0) for s in source_stats)
    total_dup_dropped = sum(s.get("duplicates_dropped", 0) for s in source_stats)
    lines.append(f"TOTAL CHUNKS: {total_chunks} | TOTAL WORDS: {total_words}")
    lines.append(f"REFERENCE BLOCKS DROPPED: {total_ref_dropped} | DUPLICATES DROPPED: {total_dup_dropped}")
    lines.append("")


    lines.append("=" * 80)
    lines.append("SAMPLE HEADINGS PER INGESTED SOURCE (3 randomly sampled headings):")
    lines.append("=" * 80)
    for s in source_stats:
        if s["status"] == "INGESTED":
            lines.append(f"[{s['source_id']}]")
            for h in s["sample_headings"]:
                lines.append(f"  • {h}")
    lines.append("")

    lines.append("=" * 80)
    lines.append("QUALITY CHECK: 10 SHORTEST CHUNKS")
    lines.append("=" * 80)
    sorted_chunks = sorted(all_chunks, key=lambda x: x["word_count"])
    for i, c in enumerate(sorted_chunks[:10], 1):
        first_60 = c["text"][:60].replace("\n", " ")
        lines.append(f"{i:2d}. [{c['source_id']}] {c['word_count']} words | {c['section_path']} | Grade: {c['grade']}")
        lines.append(f"    Excerpt: \"{first_60}...\"")
    lines.append("")

    lines.append("=" * 80)
    lines.append("QUALITY CHECK: 10 LONGEST CHUNKS")
    lines.append("=" * 80)
    for i, c in enumerate(reversed(sorted_chunks[-10:]), 1):
        first_60 = c["text"][:60].replace("\n", " ")
        lines.append(f"{i:2d}. [{c['source_id']}] {c['word_count']} words | {c['section_path']}")
        lines.append(f"    Excerpt: \"{first_60}...\"")
    lines.append("")

    full_output = "\n".join(lines)
    print(full_output)

    with open(log_file, "w", encoding="utf-8") as lf:
        lf.write(full_output)
    print(f"\nIngest log saved to: {log_file}")


def main():
    results = ingest_corpus()
    print_and_save_reports(results)


if __name__ == "__main__":
    main()
