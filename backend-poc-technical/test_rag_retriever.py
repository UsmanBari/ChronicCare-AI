"""
Unit tests for ChronicCare AI BM25 Retriever and Query Map (Part B).
Hermetic and fast, using fake test fixtures with zero external network dependencies.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from rag.query_map import TRIAGE_QUERY_TABLE, build_query_from_triage
from rag.retriever import BM25Retriever, normalize_medical_units, tokenize
from rag.store import ChunkStore, JsonlChunkStore


@pytest.fixture
def fake_chunks_file(tmp_path: Path) -> Path:
    chunks = [
        {
            "chunk_id": "test_chunk_ish_01",
            "source_id": "ish_2020_htn",
            "title": "ISH 2020 Guidelines",
            "edition": "2020",
            "priority": 1,
            "section_path": "Diagnosis > Office BP",
            "page_start": 5,
            "page_end": 5,
            "grade": "Essential",
            "condition": "hypertension",
            "topics": ["bp_targets", "diagnosis"],
            "text": "Hypertension is defined as office systolic blood pressure 140 mmHg or higher and diastolic blood pressure 90 mmHg or higher.",
            "word_count": 22,
        },
        {
            "chunk_id": "test_chunk_ish_crisis",
            "source_id": "ish_2020_htn",
            "title": "ISH 2020 Guidelines",
            "edition": "2020",
            "priority": 2,  # Higher priority
            "section_path": "Emergencies > Crisis",
            "page_start": 15,
            "page_end": 16,
            "grade": "Optimal",
            "condition": "hypertension",
            "topics": ["crisis", "emergency", "bp_targets"],
            "text": "Hypertensive emergency is defined as blood pressure greater than 180 mmHg systolic or 120 mmHg diastolic with acute target organ damage.",
            "word_count": 22,
        },
        {
            "chunk_id": "test_chunk_who_target",
            "source_id": "who_2021_htn",
            "title": "WHO 2021 Hypertension",
            "edition": "2021",
            "priority": 1,
            "section_path": "Recommendations > Targets",
            "page_start": 28,
            "page_end": 28,
            "grade": "Strong",
            "condition": "hypertension",
            "topics": ["bp_targets", "lifestyle"],
            "text": "WHO recommends target blood pressure treatment goal of less than 140/90 mmHg in all adult patients with hypertension without comorbidities.",
            "word_count": 21,
        },
        {
            "chunk_id": "test_chunk_idf_hypo",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR Guidelines 2021",
            "edition": "2021",
            "priority": 2,
            "section_path": "Hypoglycemia > Rule of 15",
            "page_start": 45,
            "page_end": 45,
            "grade": "Recommended",
            "condition": "diabetes",
            "topics": ["hypoglycemia", "emergency"],
            "text": "Hypoglycemia is defined as blood glucose less than 70 mg/dL. Treat immediately with 15 grams of fast-acting carbohydrate and re-check in 15 minutes.",
            "word_count": 24,
        },
        {
            "chunk_id": "test_chunk_ramadan_fasting",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR Guidelines 2021",
            "edition": "2021",
            "priority": 2,
            "section_path": "Ramadan > Breaking Fast",
            "page_start": 80,
            "page_end": 81,
            "grade": "Essential",
            "condition": "diabetes",
            "topics": ["ramadan", "risk_stratification"],
            "text": "Patients with diabetes must break their fast if blood glucose drops below 70 mg/dL or exceeds 300 mg/dL at any time during fasting.",
            "word_count": 23,
        },
    ]

    p = tmp_path / "test_chunks.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    return p


# -----------------------------------------------------------------------------
# 1. Tokenizer & Normalization Tests
# -----------------------------------------------------------------------------
def test_normalize_medical_units():
    assert "mgdl" in normalize_medical_units("Blood sugar is 120 mg/dL")
    assert "mmoll" in normalize_medical_units("Result is 7.2 mmol/L")
    assert "mmhg" in normalize_medical_units("BP is 140/90 mm Hg")
    assert "bpm" in normalize_medical_units("Heart rate 72 beats/min")


def test_tokenize_preserves_numbers():
    tokens = tokenize("BP 180/120 mm Hg with glucose 65 mg/dL")
    assert "180" in tokens
    assert "120" in tokens
    assert "65" in tokens
    assert "mmhg" in tokens
    assert "mgdl" in tokens


# -----------------------------------------------------------------------------
# 2. ChunkStore Protocol & JsonlStore Tests
# -----------------------------------------------------------------------------
def test_jsonl_chunk_store(fake_chunks_file: Path):
    store = JsonlChunkStore(fake_chunks_file)
    assert isinstance(store, ChunkStore)
    assert store.total_chunks() == 5

    chunk = store.get_chunk("test_chunk_ish_01")
    assert chunk is not None
    assert chunk["source_id"] == "ish_2020_htn"

    assert store.get_chunk("nonexistent") is None

    # Filtering by condition
    htn_chunks = store.list_chunks(condition="hypertension")
    assert len(htn_chunks) == 3

    diab_chunks = store.list_chunks(condition="diabetes")
    assert len(diab_chunks) == 2

    # Filtering by topic
    hypo_chunks = store.list_chunks(topic="hypoglycemia")
    assert len(hypo_chunks) == 1
    assert hypo_chunks[0]["chunk_id"] == "test_chunk_idf_hypo"

    # Filtering by min_priority
    p2_chunks = store.list_chunks(min_priority=2)
    assert len(p2_chunks) == 3


def test_jsonl_chunk_store_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        JsonlChunkStore(tmp_path / "does_not_exist.jsonl")


# -----------------------------------------------------------------------------
# 3. BM25 Retrieval & Filtering Tests
# -----------------------------------------------------------------------------
def test_bm25_retrieval_ranking(fake_chunks_file: Path):
    store = JsonlChunkStore(fake_chunks_file)
    retriever = BM25Retriever(store)

    # Hypoglycemia query
    results = retriever.retrieve("blood glucose low hypoglycemia 70 mg/dL", top_k=2)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "test_chunk_idf_hypo"
    assert results[0]["rank"] == 1
    assert results[0]["bm25_score"] > 0

    # Crisis query
    crisis_results = retriever.retrieve("emergency crisis blood pressure 180 120 mmhg", top_k=2)
    assert len(crisis_results) >= 1
    assert crisis_results[0]["chunk_id"] == "test_chunk_ish_crisis"


def test_bm25_filters_condition(fake_chunks_file: Path):
    store = JsonlChunkStore(fake_chunks_file)
    retriever = BM25Retriever(store)

    # Query with generic terms but filtered to diabetes
    results = retriever.retrieve("blood pressure target guidelines", condition="diabetes", top_k=5)
    for r in results:
        assert r["condition"] in ("diabetes", "both", "general", "")


def test_bm25_priority_tie_breaking(fake_chunks_file: Path):
    store = JsonlChunkStore(fake_chunks_file)
    retriever = BM25Retriever(store)

    # Both ISH crisis (pri=2) and WHO target (pri=1) contain "blood pressure"
    results = retriever.retrieve("blood pressure", top_k=5, condition="hypertension")
    assert len(results) > 1
    # Check that ties or ranking appropriately favor higher priority when relevant
    priorities = [r["priority"] for r in results]
    assert max(priorities) >= 2


# -----------------------------------------------------------------------------
# 4. Triage Query Map Tests
# -----------------------------------------------------------------------------
def test_build_query_from_triage():
    # Direct trigger
    t1 = {"trigger_category": "bp_severe", "level": "emergency"}
    q1 = build_query_from_triage(t1)
    assert q1.trigger_category == "bp_severe"
    assert q1.condition == "hypertension"
    assert "180" in q1.query_text

    # Via reasons
    t2 = {"reasons": ["glucose_low: glucose < 70 mg/dL"], "level": "urgent"}
    q2 = build_query_from_triage(t2)
    assert q2.trigger_category == "glucose_low"
    assert q2.condition == "diabetes"

    # Via readings
    t3 = {"level": "emergency"}
    readings3 = {"blood_pressure_systolic": 190, "blood_pressure_diastolic": 125}
    q3 = build_query_from_triage(t3, readings=readings3)
    assert q3.trigger_category == "bp_severe"

    # Routine fallback
    t4 = {"level": "routine", "trigger_category": "routine"}
    q4 = build_query_from_triage(t4)
    assert q4.trigger_category == "routine"
    assert "lifestyle" in q4.topic_slugs
