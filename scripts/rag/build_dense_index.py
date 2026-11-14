#!/usr/bin/env python3
"""
Build Dense ChromaDB Index for ChronicCare AI Guideline Retrieval.
Embeds chunks from $env:CHRONICCARE_DATA_DIR/rag/chunks.jsonl using
FastEmbed (BAAI/bge-small-en-v1.5) and stores them in a persistent
ChromaDB collection at $env:CHRONICCARE_DATA_DIR/rag/chroma.

Safety & Licensing:
- Strictly enforces that the destination path is OUTSIDE the git repository.
- Idempotent: Skips re-embedding if collection count and chunk IDs are unchanged.
- Prints counts and metrics only; never prints licensed guideline text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def get_data_dir() -> Path:
    d = os.environ.get("CHRONICCARE_DATA_DIR")
    if not d:
        d = str(REPO_ROOT.parent / "Chronicare-data")
    return Path(d).resolve()


def is_path_inside_repo(path: Path) -> bool:
    try:
        res_path = path.resolve()
        res_repo = REPO_ROOT.resolve()
        return res_path.is_relative_to(res_repo)
    except Exception:
        return str(path.resolve()).startswith(str(REPO_ROOT.resolve()))


def verify_path_safety(chroma_dir: Path) -> None:
    if is_path_inside_repo(chroma_dir):
        print(f"[FATAL ERROR] Target ChromaDB directory is inside the repository: {chroma_dir}", file=sys.stderr)
        print("Guideline text is licensed and must never be stored inside git tree!", file=sys.stderr)
        sys.exit(1)

    # Secondary check with git check-ignore
    try:
        res = subprocess.run(
            ["git", "check-ignore", str(chroma_dir)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        # If check-ignore returns 0 or path is outside repo, path is safe
    except Exception:
        pass


def compute_chunks_signature(chunks: list[dict[str, Any]]) -> str:
    h = hashlib.sha256()
    h.update(str(len(chunks)).encode("utf-8"))
    for c in chunks:
        cid = str(c.get("chunk_id") or c.get("id") or "")
        h.update(cid.encode("utf-8"))
    return h.hexdigest()


def build_dense_index(
    chunks_path: Path | str | None = None,
    chroma_path: Path | str | None = None,
    force: bool = False,
    batch_size: int = 64,
) -> int:
    data_dir = get_data_dir()
    if chunks_path is None:
        chunks_file = data_dir / "rag" / "chunks.jsonl"
    else:
        chunks_file = Path(chunks_path).resolve()

    if not chunks_file.exists():
        print(f"[FATAL] Chunks file not found at: {chunks_file}", file=sys.stderr)
        sys.exit(1)

    if chroma_path is None:
        chroma_dir = data_dir / "rag" / "chroma"
    else:
        chroma_dir = Path(chroma_path).resolve()

    verify_path_safety(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading chunks from: {chunks_file}")
    raw_chunks: list[dict[str, Any]] = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                raw_chunks.append(json.loads(stripped))

    # Deduplicate by chunk_id (ChromaDB requires unique IDs; prefer chunk with richer text if duplicated)
    deduped_map: dict[str, dict[str, Any]] = {}
    for c in raw_chunks:
        cid = str(c.get("chunk_id") or c.get("id") or "").strip()
        if not cid:
            continue
        if cid in deduped_map:
            old_len = len(deduped_map[cid].get("text", ""))
            new_len = len(c.get("text", ""))
            if new_len > old_len:
                deduped_map[cid] = c
        else:
            deduped_map[cid] = c

    chunks = list(deduped_map.values())
    total_chunks = len(chunks)
    print(f"Total chunks loaded: {len(raw_chunks)} (Unique by ID: {total_chunks})")
    if total_chunks == 0:
        print("[WARNING] Zero chunks loaded; aborting index build.", file=sys.stderr)
        return 0

    sig = compute_chunks_signature(chunks)
    meta_path = chroma_dir / "index_meta.json"

    # Lazy imports of optional dependencies
    import chromadb
    from fastembed import TextEmbedding

    client = chromadb.PersistentClient(path=str(chroma_dir))

    # Check idempotency
    if not force and meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as mf:
                meta = json.load(mf)
            if meta.get("signature") == sig and meta.get("chunk_count") == total_chunks:
                try:
                    col = client.get_collection(name="guideline_chunks")
                    if col.count() == total_chunks:
                        print(f"[IDEMPOTENT] Dense ChromaDB index is already up to date ({total_chunks} chunks). Skipping rebuild.")
                        return total_chunks
                except Exception:
                    pass
        except Exception:
            pass

    print(f"Building dense index in ChromaDB at: {chroma_dir}")
    t0 = time.time()

    # Recreate collection to ensure clean state
    try:
        client.delete_collection(name="guideline_chunks")
    except Exception:
        pass

    collection = client.create_collection(
        name="guideline_chunks",
        metadata={"hnsw:space": "cosine"},
    )

    print("Initializing FastEmbed model: BAAI/bge-small-en-v1.5 (threads=1)...")
    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", threads=1)

    texts = [
        f"{c.get('title', '')} {c.get('section_path', '')} {c.get('text', '')}"
        for c in chunks
    ]
    ids = [str(c.get("chunk_id") or c.get("id")) for c in chunks]

    metadatas: list[dict[str, Any]] = []
    for c in chunks:
        cid = str(c.get("chunk_id") or c.get("id") or "")
        src = str(c.get("source_id", "")).strip().lower()
        cond = str(c.get("condition", "")).strip().lower()
        pri = int(c.get("priority", 0))
        topics_val = c.get("topics", [])
        if isinstance(topics_val, list):
            topics_str = ",".join(str(t).strip().lower() for t in topics_val)
        else:
            topics_str = str(topics_val).strip().lower()

        metadatas.append({
            "chunk_id": cid,
            "source_id": src,
            "condition": cond,
            "priority": pri,
            "topics": topics_str,
            "title": str(c.get("title", ""))[:200],
            "section_path": str(c.get("section_path", ""))[:200],
        })

    print(f"Embedding and indexing {total_chunks} chunks in batches of {batch_size}...")
    for start_idx in range(0, total_chunks, batch_size):
        end_idx = min(start_idx + batch_size, total_chunks)
        batch_texts = texts[start_idx:end_idx]
        batch_ids = ids[start_idx:end_idx]
        batch_meta = metadatas[start_idx:end_idx]

        emb_gen = model.embed(batch_texts)
        batch_embs = [e.tolist() for e in emb_gen]

        collection.upsert(
            ids=batch_ids,
            embeddings=batch_embs,
            documents=batch_texts,
            metadatas=batch_meta,
        )

    elapsed = time.time() - t0
    final_count = collection.count()
    print(f"[SUCCESS] Indexed {final_count} chunks in {elapsed:.2f}s ({final_count/max(elapsed, 0.001):.1f} chunks/sec).")

    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump(
            {
                "signature": sig,
                "chunk_count": final_count,
                "model": "BAAI/bge-small-en-v1.5",
                "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            mf,
            indent=2,
        )

    return final_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build ChromaDB Dense Index for ChronicCare AI RAG")
    parser.add_argument("--chunks", type=str, default=None, help="Path to chunks.jsonl")
    parser.add_argument("--chroma", type=str, default=None, help="Path to chroma persistent directory")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if index is up to date")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding batch size")
    args = parser.parse_args()

    build_dense_index(
        chunks_path=args.chunks,
        chroma_path=args.chroma,
        force=args.force,
        batch_size=args.batch_size,
    )

