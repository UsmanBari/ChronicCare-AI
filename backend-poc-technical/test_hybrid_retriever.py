"""
Hermetic Unit Tests for Hybrid BM25 + Dense Retriever (ChronicCare AI RAG).
Runs in CI without model download or external network calls.
Verifies:
1. Reciprocal Rank Fusion (k=60) mathematics calculation.
2. Clinical filters applied on both BM25 and Dense candidate sets:
   - exclude_source_prefixes (pre-ranking exclusion of diabetes sources for non-diabetic check-ins)
   - is_source_expired (runtime licence expiry)
   - condition filter
   - topics filter
   - min_priority filter
   - IDF-DAR Ramadan restriction
3. Graceful fallback to BM25 when ChromaDB is missing or throws.
4. Equivalence to pure BM25 when RETRIEVER is unset.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

from rag.store import JsonlChunkStore
from rag.retriever import BM25Retriever, HybridRetriever, get_default_retriever


@pytest.fixture
def mock_chunk_store(tmp_path):
    chunks_file = tmp_path / "chunks.jsonl"
    data = [
        '{"chunk_id": "ish_001", "source_id": "ish_2020_htn", "title": "ISH BP Targets", "section_path": "Blood Pressure Targets", "condition": "hypertension", "topics": ["bp_targets", "stage1"], "priority": 2, "text": "Blood pressure target for adults is 130 80 mmhg lifestyle changes firstline."}',
        '{"chunk_id": "who_001", "source_id": "who_2021_htn", "title": "WHO BP Thresholds", "section_path": "Treatment Initiation", "condition": "hypertension", "topics": ["bp_targets"], "priority": 1, "text": "Initiate treatment when blood pressure is 140 90 mmhg in individuals with hypertension."}',
        '{"chunk_id": "ada_001", "source_id": "ada_2026_sec06", "title": "ADA Glucose Targets", "section_path": "Glycemic Goals", "condition": "diabetes", "topics": ["glucose_targets", "hypoglycemia"], "priority": 2, "text": "Fasting blood sugar target is 80 to 130 mgdl and bedtime glucose 180 mgdl."}',
        '{"chunk_id": "idf_001", "source_id": "idf_dar_2021", "title": "IDF-DAR Fasting", "section_path": "Ramadan Management", "condition": "diabetes", "topics": ["ramadan", "fasting"], "priority": 2, "text": "Patients fasting during Ramadan with high risk should monitor blood glucose."}',
        '{"chunk_id": "expired_001", "source_id": "expired_source", "title": "Expired Guideline", "section_path": "Historical", "condition": "hypertension", "topics": ["bp_targets"], "priority": 1, "text": "Older guidelines for blood pressure monitoring."}',
    ]
    chunks_file.write_text("\n".join(data), encoding="utf-8")
    return JsonlChunkStore(chunks_file)


class FakeDenseCollection:
    """Mock ChromaDB collection returning canned candidate IDs with distances."""

    def __init__(self, canned_ids: list[str], canned_distances: list[float] | None = None):
        self._ids = canned_ids
        self._distances = canned_distances or [0.1 * i for i in range(len(canned_ids))]

    def count(self) -> int:
        return len(self._ids)

    def query(self, query_embeddings, n_results, include=None):
        return {
            "ids": [self._ids[:n_results]],
            "distances": [self._distances[:n_results]],
            "metadatas": [[{}] * min(n_results, len(self._ids))],
            "documents": [[""] * min(n_results, len(self._ids))],
        }


class FakeEmbedModel:
    """Mock FastEmbed model returning dummy fixed-dimension vector."""

    def embed(self, texts):
        for _ in texts:
            yield [0.1] * 384


def test_rrf_math_calculation_exact(mock_chunk_store):
    """Verifies that RRF fusion formula 1/(60 + r_bm25) + 1/(60 + r_dense) is calculated accurately."""
    retriever = HybridRetriever(mock_chunk_store, force_bm25=True)
    retriever.dense_available = True
    retriever.embed_model = FakeEmbedModel()

    # Document ish_001 will be rank 1 in BM25 and rank 1 in Dense
    # Document who_001 will be rank 2 in BM25 and rank 2 in Dense
    retriever.collection = FakeDenseCollection(["ish_001", "who_001", "ada_001"])

    results = retriever.retrieve("blood pressure 130 80 mmhg targets", top_k=2, condition="hypertension")
    assert len(results) >= 1

    first = results[0]
    assert first["chunk_id"] == "ish_001"
    # Rank 1 in both: 1/(60 + 1) + 1/(60 + 1) = 2/61 = 0.03278688...
    expected_rrf_rank1 = round(1.0 / 61.0 + 1.0 / 61.0, 6)
    assert abs(first["rrf_score"] - expected_rrf_rank1) < 1e-5
    assert first["retriever"] == "hybrid"
    assert first["bm25_rank"] == 1
    assert first["dense_rank"] == 1


def test_filters_applied_on_dense_side_exclude_prefixes(mock_chunk_store):
    """Dense candidates with prefixes in exclude_source_prefixes are discarded before fusion."""
    retriever = HybridRetriever(mock_chunk_store, force_bm25=True)
    retriever.dense_available = True
    retriever.embed_model = FakeEmbedModel()

    # Dense candidate list puts ada_001 at rank 1
    retriever.collection = FakeDenseCollection(["ada_001", "ish_001"])

    # Non-diabetic check-in excludes diabetes guidelines
    exclude_prefixes = ("ada_2026", "idf_dar")
    results = retriever.retrieve(
        "blood pressure targets",
        top_k=2,
        condition="hypertension",
        exclude_source_prefixes=exclude_prefixes,
    )

    result_ids = [r["chunk_id"] for r in results]
    assert "ada_001" not in result_ids
    assert "ish_001" in result_ids


def test_filters_applied_on_dense_side_condition_filter(mock_chunk_store):
    """Dense candidates matching another condition are filtered out."""
    retriever = HybridRetriever(mock_chunk_store, force_bm25=True)
    retriever.dense_available = True
    retriever.embed_model = FakeEmbedModel()

    retriever.collection = FakeDenseCollection(["ada_001", "who_001"])

    results = retriever.retrieve("targets", top_k=2, condition="hypertension")
    result_ids = [r["chunk_id"] for r in results]
    # ada_001 is condition=diabetes, should be excluded
    assert "ada_001" not in result_ids
    assert "who_001" in result_ids


def test_filters_applied_on_dense_side_topic_filter(mock_chunk_store):
    """Dense candidates missing requested topics are filtered out."""
    retriever = HybridRetriever(mock_chunk_store, force_bm25=True)
    retriever.dense_available = True
    retriever.embed_model = FakeEmbedModel()

    retriever.collection = FakeDenseCollection(["who_001", "ish_001"])

    # Only request stage1 topic
    results = retriever.retrieve("blood pressure", top_k=2, condition="hypertension", topics=["stage1"])
    result_ids = [r["chunk_id"] for r in results]
    # ish_001 has stage1, who_001 only has bp_targets
    assert "ish_001" in result_ids
    assert "who_001" not in result_ids


def test_filters_applied_on_dense_side_priority_filter(mock_chunk_store):
    """Dense candidates below min_priority are filtered out."""
    retriever = HybridRetriever(mock_chunk_store, force_bm25=True)
    retriever.dense_available = True
    retriever.embed_model = FakeEmbedModel()

    # who_001 has priority 1, ish_001 has priority 2
    retriever.collection = FakeDenseCollection(["who_001", "ish_001"])

    results = retriever.retrieve("blood pressure", top_k=2, condition="hypertension", min_priority=2)
    result_ids = [r["chunk_id"] for r in results]
    assert "ish_001" in result_ids
    assert "who_001" not in result_ids


def test_filters_applied_on_dense_side_licence_expiry(mock_chunk_store):
    """Dense candidates with expired licences are discarded."""
    retriever = HybridRetriever(mock_chunk_store, force_bm25=True)
    retriever.dense_available = True
    retriever.embed_model = FakeEmbedModel()

    retriever.collection = FakeDenseCollection(["expired_001", "ish_001"])

    with patch("rag.retriever.is_source_expired", side_effect=lambda src, as_of=None: src == "expired_source"):
        results = retriever.retrieve("blood pressure", top_k=2, condition="hypertension")
        result_ids = [r["chunk_id"] for r in results]
        assert "expired_001" not in result_ids
        assert "ish_001" in result_ids


def test_filters_applied_on_dense_side_idf_dar_ramadan_restriction(mock_chunk_store):
    """IDF-DAR chunks are excluded on dense side for non-Ramadan diabetes check-ins."""
    retriever = HybridRetriever(mock_chunk_store, force_bm25=True)
    retriever.dense_available = True
    retriever.embed_model = FakeEmbedModel()

    retriever.collection = FakeDenseCollection(["idf_001", "ada_001"])

    # Non-Ramadan query
    results = retriever.retrieve("regular glucose checkin", top_k=2, condition="diabetes")
    result_ids = [r["chunk_id"] for r in results]
    assert "idf_001" not in result_ids
    assert "ada_001" in result_ids

    # Ramadan query allows idf_001
    results_ramadan = retriever.retrieve("ramadan fasting glucose management", top_k=2, condition="diabetes")
    result_ids_ramadan = [r["chunk_id"] for r in results_ramadan]
    assert "idf_001" in result_ids_ramadan


def test_fallback_to_bm25_when_chromadb_unavailable(mock_chunk_store):
    """When ChromaDB collection is unavailable or fails, gracefully falls back to pure BM25."""
    retriever = HybridRetriever(mock_chunk_store, chroma_path="/nonexistent/chroma/path")
    assert not retriever.dense_available

    results = retriever.retrieve("blood pressure 130 80 mmhg targets", top_k=2, condition="hypertension")
    assert len(results) > 0
    # Returns pure BM25 scores
    assert "bm25_score" in results[0]
    assert results[0]["chunk_id"] == "ish_001"


def test_fallback_to_bm25_when_dense_query_throws(mock_chunk_store):
    """When dense query raises an unexpected exception, gracefully falls back to BM25."""
    retriever = HybridRetriever(mock_chunk_store, force_bm25=True)
    retriever.dense_available = True
    retriever.embed_model = FakeEmbedModel()

    mock_col = MagicMock()
    mock_col.count.return_value = 10
    mock_col.query.side_effect = RuntimeError("Chroma query internal failure")
    retriever.collection = mock_col

    results = retriever.retrieve("blood pressure 130 80 mmhg targets", top_k=2, condition="hypertension")
    assert len(results) > 0
    assert results[0]["chunk_id"] == "ish_001"


def test_retriever_unset_gives_exact_bm25_equivalence(mock_chunk_store, monkeypatch):
    """When RETRIEVER is unset or 'bm25', BM25Retriever behaves identically to original BM25."""
    monkeypatch.delenv("RETRIEVER", raising=False)

    retriever = BM25Retriever(mock_chunk_store)
    # Confirm it is an instance of BM25Retriever and NOT HybridRetriever
    assert type(retriever) is BM25Retriever

    results = retriever.retrieve("blood pressure targets", top_k=2, condition="hypertension")
    assert len(results) > 0
    assert "bm25_score" in results[0]
    assert "rrf_score" not in results[0]


def test_get_default_retriever_respects_flag(mock_chunk_store, monkeypatch):
    """get_default_retriever returns HybridRetriever when RETRIEVER=hybrid, else BM25Retriever."""
    monkeypatch.setenv("RETRIEVER", "bm25")
    r_bm25 = get_default_retriever(mock_chunk_store)
    assert type(r_bm25) is BM25Retriever

    monkeypatch.setenv("RETRIEVER", "hybrid")
    r_hybrid = get_default_retriever(mock_chunk_store)
    assert isinstance(r_hybrid, HybridRetriever)

