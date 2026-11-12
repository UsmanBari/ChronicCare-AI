"""
BM25 Information Retrieval implementation for ChronicCare AI RAG.
Pure Python standard library (zero external dependencies).
Implements exact tokenization with medical unit normalization, Okapi BM25 scoring,
metadata filtering, and priority-based tie-breaking.
"""
from __future__ import annotations

import logging
import math
import os
import re
from pathlib import Path
from typing import Any, Optional

from rag.licences import is_source_expired
from rag.query_map import is_ramadan_text
from rag.store import ChunkStore

logger = logging.getLogger(__name__)


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

    def __new__(cls, store: ChunkStore, *args: Any, **kwargs: Any) -> Any:
        force_bm25 = kwargs.get("force_bm25", False)
        if (
            cls is BM25Retriever
            and not force_bm25
            and os.environ.get("RETRIEVER", "bm25").strip().lower() == "hybrid"
        ):
            try:
                inst = super().__new__(HybridRetriever)
                return inst
            except Exception as exc:
                logger.warning("Failed to allocate HybridRetriever: %s", exc)
        return super().__new__(cls)

    def __init__(self, store: ChunkStore, k1: float = 1.5, b: float = 0.75, force_bm25: bool = False) -> None:
        self.store = store
        self.k1 = k1
        self.b = b
        self.force_bm25 = force_bm25
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
        as_of_date: Any = None,
        exclude_source_prefixes: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        """
        Retrieve the top_k most relevant chunks matching the query.
        Applies metadata filters (condition, topics, min_priority, licence expiry, source prefix exclusions)
        and breaks ties by guideline priority.
        For diabetes queries, prefers ADA guideline sections over IDF-DAR unless fasting/Ramadan is queried.
        Returns a list of chunk dicts augmented with 'bm25_score' and 'rank'.
        """
        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        candidates = []

        # Topic normalization
        norm_topics = [t.lower().strip() for t in topics] if topics else None
        norm_cond = condition.lower().strip() if condition else None

        # Pre-lowercase exclude_source_prefixes once outside retriever loop
        clean_exclude_prefixes = (
            tuple(p.lower().strip() for p in exclude_source_prefixes)
            if exclude_source_prefixes
            else ()
        )

        is_diabetes = (norm_cond == "diabetes")
        is_ramadan = is_ramadan_text(query)

        for idx, doc in enumerate(self.corpus):
            src_id = str(doc.get("source_id", "")).strip().lower()
            chunk_id = str(doc.get("id") or doc.get("chunk_id") or "").strip().lower()

            # Exclude source prefixes filter (e.g. diabetes guidelines for non-diabetic patients)
            if clean_exclude_prefixes and any(
                src_id.startswith(p) or chunk_id.startswith(p)
                for p in clean_exclude_prefixes
            ):
                continue

            # X2: Runtime licence expiry check
            if src_id and is_source_expired(src_id, as_of=as_of_date):
                logger.warning("Filtered expired guideline chunk for source: %s", src_id)
                continue

            # IDF-DAR (idf_dar_2021) chunks may be used only for Ramadan check-ins
            if is_diabetes and not is_ramadan and src_id.startswith("idf_dar"):
                continue

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

            # Z2: Preference weighting (ADA for non-Ramadan diabetes, IDF for Ramadan diabetes)
            if is_diabetes and not is_ramadan:
                if src_id.startswith("ada_2026"):
                    pref = 2
                else:
                    pref = 1
                candidates.append((score, pref, doc_pri, doc))
            elif is_diabetes and is_ramadan:
                if src_id.startswith("idf_dar"):
                    pref = 2
                elif src_id.startswith("ada_2026"):
                    pref = 1
                else:
                    pref = 0
                candidates.append((score, pref, doc_pri, doc))
            else:
                candidates.append((score, 0, doc_pri, doc))

        if is_diabetes:
            # Sort by match (score > 0), preference, score, priority
            candidates.sort(key=lambda item: (1 if item[0] > 0.0 else 0, item[1], item[0], item[2]), reverse=True)
        else:
            # Standard sorting descending by score, ties broken by priority
            candidates.sort(key=lambda item: (item[0], item[2]), reverse=True)

        results = []
        for rank, (score, _, _, doc) in enumerate(candidates[:top_k], start=1):
            out_doc = dict(doc)
            out_doc["bm25_score"] = round(score, 4)
            out_doc["rank"] = rank
            out_doc["retriever"] = "bm25"
            results.append(out_doc)

        return results


class HybridRetriever(BM25Retriever):
    """
    Hybrid Retriever combining Okapi BM25 and Dense BGE embeddings with Reciprocal Rank Fusion (k=60).
    Lazy-loads ChromaDB and FastEmbed only when instantiated.
    Applies identical clinical metadata filters on both BM25 and dense candidate sets:
    - exclude_source_prefixes: Pre-ranking exclusion (e.g. non-diabetic exclusion of diabetes guidelines)
    - is_source_expired: Runtime license expiry check
    - IDF-DAR Ramadan restriction: idf_dar chunks only used for Ramadan check-ins
    - condition filter: patient condition vs chunk condition
    - topic filter: matching topic tags
    - min_priority: minimum chunk guideline priority
    - ADA preference weighting for diabetes
    Falls back gracefully to BM25 if ChromaDB or model is missing or fails.
    """
    _warned_unavailable: bool = False

    def __init__(
        self,
        store: ChunkStore,
        chroma_path: Path | str | None = None,
        k: int = 60,
        bge_model_name: str = "BAAI/bge-small-en-v1.5",
        threads: int = 1,
        force_bm25: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(store, force_bm25=True)
        self.k = k
        self.bge_model_name = bge_model_name
        self.threads = threads
        self.chroma_path = chroma_path
        self.force_bm25 = force_bm25

        self.dense_available = False
        self.collection: Any = None
        self.embed_model: Any = None

        if not force_bm25:
            self._init_dense()

    def _init_dense(self) -> None:
        try:
            import chromadb
            from fastembed import TextEmbedding

            if self.chroma_path is None:
                data_dir = os.environ.get("CHRONICCARE_DATA_DIR")
                if data_dir:
                    c_path = Path(data_dir) / "rag" / "chroma"
                else:
                    repo_root = Path(__file__).resolve().parent.parent.parent
                    c_path = repo_root.parent / "Chronicare-data" / "rag" / "chroma"
            else:
                c_path = Path(self.chroma_path)

            if not c_path.exists():
                if not HybridRetriever._warned_unavailable:
                    logger.warning("ChromaDB index path '%s' does not exist. Falling back to BM25.", c_path)
                    HybridRetriever._warned_unavailable = True
                self.dense_available = False
                return

            client = chromadb.PersistentClient(path=str(c_path))
            try:
                self.collection = client.get_collection(name="guideline_chunks")
                cnt = self.collection.count()
                if cnt == 0:
                    if not HybridRetriever._warned_unavailable:
                        logger.warning("ChromaDB collection 'guideline_chunks' is empty. Falling back to BM25.")
                        HybridRetriever._warned_unavailable = True
                    self.dense_available = False
                    return
            except Exception as e:
                if not HybridRetriever._warned_unavailable:
                    logger.warning("ChromaDB collection 'guideline_chunks' not accessible: %s. Falling back to BM25.", e)
                    HybridRetriever._warned_unavailable = True
                self.dense_available = False
                return

            self.embed_model = TextEmbedding(model_name=self.bge_model_name, threads=self.threads)
            self.dense_available = True
            logger.info("HybridRetriever initialized successfully with ChromaDB collection (%d chunks).", cnt)
        except Exception as exc:
            if not HybridRetriever._warned_unavailable:
                logger.warning("HybridRetriever dense backend failed to initialize: %s. Falling back to BM25.", exc)
                HybridRetriever._warned_unavailable = True
            self.dense_available = False

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        condition: str | None = None,
        topics: list[str] | None = None,
        min_priority: int | None = None,
        as_of_date: Any = None,
        exclude_source_prefixes: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        # If dense backend is not available, execute pure BM25
        if not self.dense_available or self.collection is None or self.embed_model is None:
            return super().retrieve(
                query=query,
                top_k=top_k,
                condition=condition,
                topics=topics,
                min_priority=min_priority,
                as_of_date=as_of_date,
                exclude_source_prefixes=exclude_source_prefixes,
            )

        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        # 1. Run BM25 candidate retrieval over full corpus
        bm25_results = super().retrieve(
            query=query,
            top_k=self.N,
            condition=condition,
            topics=topics,
            min_priority=min_priority,
            as_of_date=as_of_date,
            exclude_source_prefixes=exclude_source_prefixes,
        )

        bm25_ranks: dict[str, int] = {}
        bm25_scores: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {}

        for rank, doc in enumerate(bm25_results, start=1):
            cid = str(doc.get("chunk_id") or doc.get("id") or "").strip()
            if cid:
                bm25_ranks[cid] = rank
                bm25_scores[cid] = float(doc.get("bm25_score", 0.0))
                doc_map[cid] = doc

        # 2. Run Dense candidate retrieval with identical filtering
        try:
            dense_results = self._retrieve_dense(
                query=query,
                top_k=min(100, self.N),
                condition=condition,
                topics=topics,
                min_priority=min_priority,
                as_of_date=as_of_date,
                exclude_source_prefixes=exclude_source_prefixes,
            )
        except Exception as exc:
            logger.warning("Dense retrieval query failed: %s. Falling back to BM25.", exc)
            return bm25_results[:top_k]

        dense_ranks: dict[str, int] = {}
        dense_scores: dict[str, float] = {}
        for rank, doc in enumerate(dense_results, start=1):
            cid = str(doc.get("chunk_id") or doc.get("id") or "").strip()
            if cid:
                dense_ranks[cid] = rank
                dense_scores[cid] = float(doc.get("dense_score", 0.0))
                if cid not in doc_map:
                    doc_map[cid] = doc

        # 3. Reciprocal Rank Fusion (k=60)
        norm_cond = condition.lower().strip() if condition else None
        is_diabetes = (norm_cond == "diabetes")
        is_ramadan = is_ramadan_text(query)

        all_cids = set(bm25_ranks.keys()) | set(dense_ranks.keys())
        candidates = []

        for cid in all_cids:
            doc = doc_map.get(cid)
            if doc is None:
                continue

            r_bm25 = bm25_ranks.get(cid)
            r_dense = dense_ranks.get(cid)

            rrf_score = 0.0
            if r_bm25 is not None:
                rrf_score += 1.0 / (self.k + r_bm25)
            if r_dense is not None:
                rrf_score += 1.0 / (self.k + r_dense)

            src_id = str(doc.get("source_id", "")).strip().lower()
            doc_pri = int(doc.get("priority", 0))

            # Z2: Preference weighting
            if is_diabetes and not is_ramadan:
                pref = 2 if src_id.startswith("ada_2026") else 1
            elif is_diabetes and is_ramadan:
                if src_id.startswith("idf_dar"):
                    pref = 2
                elif src_id.startswith("ada_2026"):
                    pref = 1
                else:
                    pref = 0
            else:
                pref = 0

            candidates.append({
                "doc": doc,
                "cid": cid,
                "rrf_score": rrf_score,
                "bm25_score": bm25_scores.get(cid, 0.0),
                "dense_score": dense_scores.get(cid, 0.0),
                "bm25_rank": r_bm25,
                "dense_rank": r_dense,
                "pref": pref,
                "priority": doc_pri,
            })

        # Sort candidates
        if is_diabetes:
            candidates.sort(
                key=lambda x: (x["pref"], x["rrf_score"], x["priority"]),
                reverse=True,
            )
        else:
            candidates.sort(
                key=lambda x: (x["rrf_score"], x["priority"]),
                reverse=True,
            )

        results = []
        for rank, item in enumerate(candidates[:top_k], start=1):
            out_doc = dict(item["doc"])
            out_doc["rrf_score"] = round(item["rrf_score"], 6)
            out_doc["bm25_score"] = round(item["bm25_score"], 4)
            out_doc["dense_score"] = round(item["dense_score"], 4)
            out_doc["bm25_rank"] = item["bm25_rank"]
            out_doc["dense_rank"] = item["dense_rank"]
            out_doc["rank"] = rank
            out_doc["retriever"] = "hybrid"
            results.append(out_doc)

        return results

    def _retrieve_dense(
        self,
        query: str,
        top_k: int = 50,
        condition: str | None = None,
        topics: list[str] | None = None,
        min_priority: int | None = None,
        as_of_date: Any = None,
        exclude_source_prefixes: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        if self.collection is None or self.embed_model is None:
            return []

        # Embed query text
        query_embs = list(self.embed_model.embed([query]))
        if not query_embs:
            return []
        q_emb = [float(x) for x in query_embs[0]]

        # Query ChromaDB collection
        total_in_col = self.collection.count()
        n_query = min(max(top_k * 3, 50), total_in_col)
        if n_query <= 0:
            return []

        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=n_query,
            include=["metadatas", "distances", "documents"],
        )

        ids = res.get("ids", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0] if "distances" in res else [0.0] * len(ids)

        norm_topics = [t.lower().strip() for t in topics] if topics else None
        norm_cond = condition.lower().strip() if condition else None
        clean_exclude_prefixes = (
            tuple(p.lower().strip() for p in exclude_source_prefixes)
            if exclude_source_prefixes
            else ()
        )
        is_diabetes = (norm_cond == "diabetes")
        is_ramadan = is_ramadan_text(query)

        # Build lookup for original store documents by chunk_id
        store_map = {str(d.get("chunk_id") or d.get("id")): d for d in self.corpus}

        filtered = []
        for cid, meta, dist in zip(ids, metas, distances):
            cid_str = str(cid).strip().lower()
            orig_doc = store_map.get(str(cid).strip())
            if orig_doc is None:
                orig_doc = meta or {}

            src_id = str(orig_doc.get("source_id") or (meta or {}).get("source_id") or "").strip().lower()

            # 1. Exclude source prefixes filter (e.g. diabetes guidelines for non-diabetic patients)
            if clean_exclude_prefixes and any(
                src_id.startswith(p) or cid_str.startswith(p)
                for p in clean_exclude_prefixes
            ):
                continue

            # 2. Runtime licence expiry check
            if src_id and is_source_expired(src_id, as_of=as_of_date):
                continue

            # 3. IDF-DAR Ramadan restriction
            if is_diabetes and not is_ramadan and src_id.startswith("idf_dar"):
                continue

            # 4. Condition filter
            if norm_cond:
                doc_cond = str(orig_doc.get("condition") or (meta or {}).get("condition") or "").lower().strip()
                if doc_cond not in (norm_cond, "both", "general", ""):
                    continue

            # 5. Topic filter
            if norm_topics:
                doc_topics_raw = orig_doc.get("topics")
                if doc_topics_raw is None and meta:
                    doc_topics_raw = meta.get("topics", "")
                if isinstance(doc_topics_raw, str):
                    doc_topics = [t.strip().lower() for t in doc_topics_raw.split(",") if t.strip()]
                elif isinstance(doc_topics_raw, list):
                    doc_topics = [str(t).strip().lower() for t in doc_topics_raw]
                else:
                    doc_topics = []

                if not any(t in doc_topics for t in norm_topics):
                    continue

            # 6. Minimum priority filter
            doc_pri = int(orig_doc.get("priority") or (meta or {}).get("priority") or 0)
            if min_priority is not None and doc_pri < min_priority:
                continue

            doc_out = dict(orig_doc)
            # Cosine distance to similarity: 1.0 - dist
            doc_out["dense_score"] = max(0.0, 1.0 - float(dist))
            filtered.append(doc_out)

        return filtered


def get_default_retriever(store: ChunkStore) -> BM25Retriever:
    mode = os.environ.get("RETRIEVER", "bm25").strip().lower()
    if mode == "hybrid":
        return HybridRetriever(store)
    return BM25Retriever(store, force_bm25=True)

