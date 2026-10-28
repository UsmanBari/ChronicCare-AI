"""
BM25 Information Retrieval implementation for ChronicCare AI RAG.
Pure Python standard library (zero external dependencies).
Implements exact tokenization with medical unit normalization, Okapi BM25 scoring,
metadata filtering, and priority-based tie-breaking.
"""
from __future__ import annotations

import math
import re
from typing import Any

from rag.store import ChunkStore


def normalize_medical_units(text: str) -> str:
    """Normalize medical units and formatting before token extraction."""
    t = text.lower()
    t = re.sub(r"\bmg\s*/\s*dl\b", "mgdl", t)
    t = re.sub(r"\bmmol\s*/\s*l\b", "mmoll", t)
    t = re.sub(r"\bmm\s*hg\b", "mmhg", t)
    t = re.sub(r"\bbeats\s*/\s*min(?:ute)?\b", "bpm", t)
    t = re.sub(r"\bbpm\b", "bpm", t)
    return t


def tokenize(text: str) -> list[str]:
    """
    Tokenize text for BM25 indexing and retrieval:
    - Lowercase
    - Unit normalization (mg/dl -> mgdl, mm hg -> mmhg)
    - Preserve numbers and alphanumeric words
    """
    normalized = normalize_medical_units(text)
    # Match alphanumeric sequences including digits (e.g. 140, 90, 180, 120, 70, 54, t2dm)
    tokens = re.findall(r"\b[a-z0-9_]+\b", normalized)
    return tokens


class BM25Retriever:
    """
    In-memory Okapi BM25 retriever for medical guideline chunks.
    Parameters:
    - k1: Term frequency saturation parameter (default 1.5)
    - b: Document length normalization parameter (default 0.75)
    """

    def __init__(self, store: ChunkStore, k1: float = 1.5, b: float = 0.75) -> None:
        self.store = store
        self.k1 = k1
        self.b = b
        self._build_index()

    def _build_index(self) -> None:
        """Build term frequency and document length inverted indices from ChunkStore."""
        self.corpus = self.store.list_chunks()
        self.N = len(self.corpus)

        self.doc_tokens: list[list[str]] = []
        self.doc_lens: list[int] = []
        self.term_freqs: list[dict[str, int]] = []
        self.df: dict[str, int] = {}

        for doc in self.corpus:
            # Index title, section path, and main body text
            combined_text = f"{doc.get('title', '')} {doc.get('section_path', '')} {doc.get('text', '')}"
            tokens = tokenize(combined_text)
            self.doc_tokens.append(tokens)
            self.doc_lens.append(len(tokens))

            tf: dict[str, int] = {}
            for tok in tokens:
                tf[tok] = tf.get(tok, 0) + 1
            self.term_freqs.append(tf)

            for tok in tf.keys():
                self.df[tok] = self.df.get(tok, 0) + 1

        self.avgdl = sum(self.doc_lens) / self.N if self.N > 0 else 1.0

        # Precompute standard Okapi BM25 IDF: ln((N - df + 0.5) / (df + 0.5) + 1.0)
        self.idf: dict[str, float] = {}
        for tok, doc_freq in self.df.items():
            self.idf[tok] = math.log((self.N - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        condition: str | None = None,
        topics: list[str] | None = None,
        min_priority: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the top_k most relevant chunks matching the query.
        Applies metadata filters (condition, topics, min_priority) and breaks ties by guideline priority.
        Returns a list of chunk dicts augmented with 'bm25_score' and 'rank'.
        """
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        candidates = []

        # Topic normalization
        norm_topics = [t.lower().strip() for t in topics] if topics else None
        norm_cond = condition.lower().strip() if condition else None

        for idx, doc in enumerate(self.corpus):
            # 1. Condition filter
            if norm_cond:
                doc_cond = str(doc.get("condition", "")).lower().strip()
                if doc_cond not in (norm_cond, "both", "general", ""):
                    continue

            # 2. Topic filter (any match)
            if norm_topics:
                doc_topics = [str(t).lower().strip() for t in doc.get("topics", [])]
                if not any(t in doc_topics for t in norm_topics):
                    continue

            # 3. Minimum priority filter
            doc_pri = int(doc.get("priority", 0))
            if min_priority is not None and doc_pri < min_priority:
                continue

            # 4. Calculate Okapi BM25 score
            tf_map = self.term_freqs[idx]
            dl = self.doc_lens[idx]
            score = 0.0

            for tok in q_tokens:
                if tok in tf_map:
                    freq = tf_map[tok]
                    idf_val = self.idf.get(tok, 0.0)
                    denom = freq + self.k1 * (1.0 - self.b + self.b * (dl / self.avgdl))
                    score += idf_val * (freq * (self.k1 + 1.0)) / denom

            # Only include if score > 0 (or if query has matching terms)
            candidates.append((score, doc_pri, doc))

        # Sort descending by score; ties broken by priority (higher priority first)
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)

        results = []
        for rank, (score, _, doc) in enumerate(candidates[:top_k], start=1):
            out_doc = dict(doc)
            out_doc["bm25_score"] = round(score, 4)
            out_doc["rank"] = rank
            results.append(out_doc)

        return results
