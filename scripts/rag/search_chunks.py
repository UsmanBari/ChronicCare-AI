"""Deterministic Search Tool for Ingested Guideline Chunks.

Searches $CHRONICCARE_DATA_DIR/rag/chunks.jsonl using keywords, topics,
and section paths without an LLM.
"""

import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = Path(os.getenv("CHRONICCARE_DATA_DIR", r"C:\Users\usmanbari\Desktop\Chronicare-data"))
CHUNKS_JSONL = DATA_DIR / "rag" / "chunks.jsonl"


def load_chunks() -> List[Dict[str, Any]]:
    if not CHUNKS_JSONL.exists():
        print(f"Error: {CHUNKS_JSONL} does not exist. Run ingest.py first.")
        return []
    chunks = []
    with open(CHUNKS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


def search_chunks(
    keywords: List[str],
    source_id: Optional[str] = None,
    topic: Optional[str] = None,
    section_pattern: Optional[str] = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    chunks = load_chunks()
    matches = []

    for c in chunks:
        if source_id and c["source_id"] != source_id:
            continue
        if topic and topic not in c.get("topics", []):
            continue
        if section_pattern and not re.search(section_pattern, c["section_path"], re.IGNORECASE):
            continue

        text_lower = c["text"].lower()
        # All keywords must appear in text
        if all(re.search(r"\b" + re.escape(kw.lower()) + r"\b", text_lower) for kw in keywords):
            matches.append(c)

    return matches[:max_results]


def main():
    if len(sys.argv) < 2:
        print("Usage: python search_chunks.py <keyword1> [keyword2 ...]")
        return

    keywords = sys.argv[1:]
    results = search_chunks(keywords)
    print(f"Found {len(results)} matches for keywords {keywords}:")
    for r in results:
        first_80 = r["text"][:80].replace("\n", " ")
        print(f"- [{r['source_id']}] {r['chunk_id'][:12]} | p.{r['page_start']} | {r['section_path']}")
        print(f"  Excerpt: \"{first_80}...\"")


if __name__ == "__main__":
    main()
