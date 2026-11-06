"""
Comprehensive Unit & Integration Test Suite for Guideline Licences (Part W, X, Y, Z).
Tests licence parity, ingest gating (.granted token), runtime expiry filtering,
Groq vs Gemini routing restrictions (G3), attribution requirements (X4),
and diabetes retrieval preferences (Z2).
"""
import copy
import json
import logging
import os
import re
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from data_sources import app_store
from rag.explain_guards import (
    guarded_explain,
    reset_explain_guards,
    LICENCE_RESTRICTED_SOURCES,
)
from rag.explainer import explain, get_template_explanation
from rag.licences import (
    get_all_licence_specs,
    get_licence_spec,
    get_restricted_gemini_sources,
    has_complete_attribution,
    is_llm_allowed_for_source,
    is_source_allowed_for_rag,
    is_source_expired,
    set_llm_derived_text_override,
    set_attribution_override,
    reset_licence_overrides,
)
from rag.query_map import build_query_from_triage, is_ramadan_text
from rag.retriever import BM25Retriever
from rag.store import ChunkStore


class MockStore(ChunkStore):
    def __init__(self, chunks: List[Dict[str, Any]]):
        self._chunks = chunks
        self._by_id = {c["chunk_id"]: c for c in chunks}

    def get_chunk(self, chunk_id: str):
        return self._by_id.get(chunk_id)

    def get(self, chunk_id: str):
        return self._by_id.get(chunk_id)

    def list_chunks(self, condition=None, topic=None, min_priority=None):
        res = list(self._chunks)
        if condition:
            c_norm = condition.lower().strip()
            res = [c for c in res if c.get("condition", "").lower() in (c_norm, "both", "general", "")]
        return res

    def total_chunks(self) -> int:
        return len(self._chunks)

    def count(self) -> int:
        return len(self._chunks)


@pytest.fixture(autouse=True)
def cleanup_overrides():
    reset_licence_overrides()
    yield
    reset_licence_overrides()


# =============================================================================
# W: Licence Parity & Manifest Integrity
# =============================================================================
def test_w3_manifest_to_code_parity():
    """Assert 100% parity between docs/GUIDELINE_CORPUS.md and rag/licences.json."""
    manifest_path = REPO_ROOT / "docs" / "GUIDELINE_CORPUS.md"
    assert manifest_path.exists(), "docs/GUIDELINE_CORPUS.md missing"
    content = manifest_path.read_text(encoding="utf-8")

    # Extract all rows: | `source_id` | ... | Allowed for RAG? | ...
    table_pattern = re.compile(
        r"^\|\s*`([^`]+)`\s*\|.*?\|\s*(\*\*TRUE\*\*|TRUE|\*\*FALSE\*\*|FALSE)\s*\|",
        re.MULTILINE | re.IGNORECASE,
    )
    doc_specs = {}
    for match in table_pattern.finditer(content):
        sid = match.group(1).strip()
        allowed = "TRUE" in match.group(2).upper()
        doc_specs[sid] = allowed

    code_specs = get_all_licence_specs()
    assert len(doc_specs) == 12, f"Expected 12 sources in manifest table, found {len(doc_specs)}"

    for sid, doc_allowed in doc_specs.items():
        assert sid in code_specs, f"Source {sid} from manifest is missing in licences.json"
        assert code_specs[sid]["allowed_for_rag"] == doc_allowed, (
            f"Parity mismatch for {sid}: doc says {doc_allowed}, code says {code_specs[sid]['allowed_for_rag']}"
        )

    # Assert G3 Gemini-restricted set contains all 6 ADA ids + aha_acc_2025
    restricted_sources = get_restricted_gemini_sources()
    ada_ids = {f"ada_2026_sec{i:02d}" for i in (2, 5, 6, 10, 11, 13)}
    assert ada_ids.issubset(restricted_sources), "All 6 ADA IDs must be in Gemini restricted set"
    assert "aha_acc_2025" in restricted_sources, "aha_acc_2025 must be in Gemini restricted set"
    assert restricted_sources == LICENCE_RESTRICTED_SOURCES


# =============================================================================
# X1: Ingest Checks (.granted token, allowed_for_rag, expiry)
# =============================================================================
def test_x1_load_chunks_skips_licensed_source_without_token(tmp_path, monkeypatch):
    """X1: load_chunks skips licensed source if its .granted token is missing."""
    from scripts.rag.load_chunks import load_chunks

    # Create dummy database
    db_file = str(tmp_path / "test_chunks.db")
    app_store.migrate(db_path=db_file, backend="sqlite")

    # Create dummy external chunks.jsonl
    external_dir = tmp_path / "ext_data"
    external_dir.mkdir()
    chunks_file = external_dir / "chunks.jsonl"
    fake_chunk = {
        "chunk_id": "ada_chunk_1",
        "source_id": "ada_2026_sec02",
        "title": "Diagnosis",
        "condition": "diabetes",
        "priority": 2,
        "text": "Fasting glucose 126 mg/dL confirms diabetes.",
    }
    chunks_file.write_text(json.dumps(fake_chunk) + "\n", encoding="utf-8")

    # Point permissions dir to empty folder (no .granted token)
    empty_perm_dir = tmp_path / "empty_permissions"
    empty_perm_dir.mkdir(parents=True)
    monkeypatch.setenv("CHRONICCARE_DATA_DIR", str(tmp_path))

    inserted, updated = load_chunks(chunks_file, backend="sqlite", db_path=db_file)
    assert inserted == 0 and updated == 0, "Chunk without .granted token must NOT be inserted"


# =============================================================================
# X2: Runtime Expiry Filtering
# =============================================================================
def test_x2_retriever_filters_expired_source(caplog):
    """X2: BM25Retriever.retrieve never returns chunks past their expires_on date."""
    now_iso = datetime.now().isoformat()
    raw_chunks = [
        {
            "chunk_id": "ada_c1",
            "source_id": "ada_2026_sec02",
            "title": "Diagnosis",
            "condition": "diabetes",
            "priority": 2,
            "text": "Fasting glucose targets are 80-130 mg/dL.",
            "loaded_at": now_iso,
        },
        {
            "chunk_id": "who_c1",
            "source_id": "who_2021_htn",
            "title": "WHO BP",
            "condition": "hypertension",
            "priority": 3,
            "text": "Blood pressure target below 130/80 mmHg.",
            "loaded_at": now_iso,
        },
    ]
    store = MockStore(raw_chunks)
    retriever = BM25Retriever(store)

    # 1. Before expiry (e.g. Dec 2026): ADA chunk is retrieved
    with caplog.at_level(logging.WARNING):
        valid_res = retriever.retrieve("fasting glucose targets", condition="diabetes", as_of_date="2026-12-01")
        assert len(valid_res) == 1
        assert valid_res[0]["chunk_id"] == "ada_c1"

    # 2. After expiry (e.g. July 2027): ADA chunk is filtered out
    with caplog.at_level(logging.WARNING):
        expired_res = retriever.retrieve("fasting glucose targets", condition="diabetes", as_of_date="2027-07-01")
        assert len(expired_res) == 0
        assert "Filtered expired guideline chunk for source: ada_2026_sec02" in caplog.text


# =============================================================================
# X3: LLM Derived Text & Provider Routing
# =============================================================================
def test_x3_llm_derived_text_disabled_falls_back_to_template(monkeypatch):
    """X3: When llm_derived_text_allowed is False, explainer falls back to template (reason=licence_restricted)."""
    monkeypatch.setenv("EXPLAIN_LLM_CONDITIONS", "hypertension,diabetes")
    # Temporarily disable derived text for ADA
    set_llm_derived_text_override("ada_2026_sec02", False)

    chunks = [
        {
            "chunk_id": "ada_c1",
            "source_id": "ada_2026_sec02",
            "title": "Diagnosis",
            "condition": "diabetes",
            "priority": 2,
            "text": "Target fasting glucose 80-130 mg/dL.",
        }
    ]
    store = MockStore(chunks)

    llm_called = []
    def fake_llm(**kw):
        llm_called.append(True)
        return json.dumps({"sentences": [{"text": "Sentence [S1].", "cites": ["S1"]}]})

    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"glucose": 110.0},
        language="en",
        store=store,
        llm=fake_llm,
        provider="groq",
        condition="diabetes",
    )
    assert len(llm_called) == 0, "LLM must NOT be called when llm_derived_text_allowed is False"
    assert res["mode"] == "template"
    assert res["reason"] == "licence_restricted"


def test_x3_gemini_blocked_on_ada_chunks_even_when_derived_text_true(monkeypatch):
    """X3 & G3: Gemini is strictly prohibited on ADA chunks (falls back to template with reason licence_restricted)."""
    monkeypatch.setenv("EXPLAIN_LLM_CONDITIONS", "hypertension,diabetes")
    chunks = [
        {
            "chunk_id": "ada_c1",
            "source_id": "ada_2026_sec02",
            "title": "Diagnosis",
            "condition": "diabetes",
            "priority": 2,
            "text": "Target fasting glucose 80-130 mg/dL.",
        }
    ]
    store = MockStore(chunks)

    gemini_called = []
    def fake_gemini(**kw):
        gemini_called.append(True)
        return "{}"

    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"glucose": 110.0},
        language="en",
        store=store,
        llm={"gemini": fake_gemini},
        provider="gemini",
        condition="diabetes",
    )
    assert len(gemini_called) == 0, "Gemini must NEVER be called on ADA chunks"
    assert res["mode"] == "template"
    assert res["reason"] == "licence_restricted"


def test_x3_mix_of_allowed_and_restricted_chunks_filters_restricted_before_llm(monkeypatch):
    """X3: With a mix of allowed (WHO) and restricted (AHA) chunks, restricted is filtered before LLM call."""
    chunks = [
        {
            "chunk_id": "aha_c1",
            "source_id": "aha_acc_2025",
            "title": "AHA",
            "condition": "hypertension",
            "priority": 2,
            "text": "BP target 130/80.",
        },
        {
            "chunk_id": "who_c1",
            "source_id": "who_2021_htn",
            "title": "WHO",
            "condition": "hypertension",
            "priority": 3,
            "text": "Blood pressure management guidance.",
        },
    ]
    store = MockStore(chunks)

    llm_received_prompts = []
    def fake_groq(prompt="", **kw):
        llm_received_prompts.append(prompt)
        return json.dumps({
            "sentences": [
                {"text": "Your blood pressure is within recommended targets [who_c1].", "cites": ["who_c1"]},
                {"text": "Maintain healthy lifestyle habits [who_c1].", "cites": ["who_c1"]},
            ]
        })

    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 125.0, "blood_pressure_diastolic": 80.0},
        language="en",
        store=store,
        llm=fake_groq,
        provider="groq",
        condition="hypertension",
    )
    assert res["mode"] == "llm"
    assert len(llm_received_prompts) == 1
    # aha_acc_2025 text or chunk ID must NOT have been sent in prompt
    assert "aha_acc_2025" not in llm_received_prompts[0]
    assert "aha_c1" not in llm_received_prompts[0]


# =============================================================================
# X4: Attribution Completeness
# =============================================================================
def test_x4_incomplete_attribution_excludes_source_from_patient():
    """X4: Sources with 'TO FILL BY USMAN' citation or DOI are excluded from patient sources."""
    assert has_complete_attribution("aha_acc_2025") is False
    assert has_complete_attribution("who_2021_htn") is True
    assert has_complete_attribution("ada_2026_sec02") is True

    # Override to simulate incomplete attribution for ADA
    set_attribution_override("ada_2026_sec02", "TO FILL BY USMAN", "TO FILL BY USMAN")
    assert has_complete_attribution("ada_2026_sec02") is False

    # When attribution is incomplete, explainer falls back to template or excludes source
    chunks = [
        {
            "chunk_id": "ada_c1",
            "source_id": "ada_2026_sec02",
            "title": "ADA Section",
            "condition": "diabetes",
            "priority": 2,
            "text": "Glucose guidance text.",
        }
    ]
    store = MockStore(chunks)
    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"glucose": 110.0},
        language="en",
        store=store,
        llm=lambda **k: "{}",
        provider="groq",
        condition="diabetes",
    )
    assert res["mode"] == "template"
    # Patient explanation sources list must not display unverified ADA source
    assert not any(s.get("chunk_id") == "ada_c1" for s in res.get("sources", []))


# =============================================================================
# X5: Patient Explanation Never Contains Raw Chunk Text
# =============================================================================
def test_x5_patient_explanation_never_contains_verbatim_chunk_text():
    """X5: Patient explanation sentences never reproduce verbatim chunk text."""
    secret_passage = "SPECIFIC_PROPRIETARY_GUIDELINE_PHRASE_THAT_CANNOT_LEAK_INTO_PATIENT_TEXT"
    chunks = [
        {
            "chunk_id": "ish_c1",
            "source_id": "ish_2020_htn",
            "title": "Targets",
            "condition": "hypertension",
            "priority": 2,
            "text": f"Guideline recommendation: {secret_passage} should be considered.",
        }
    ]
    store = MockStore(chunks)

    # Valid LLM response synthesizing in plain words
    def plain_llm(**kw):
        return json.dumps({
            "sentences": [
                {"text": "Your blood pressure reading is within routine limits [ish_c1].", "cites": ["ish_c1"]},
                {"text": "Regular daily activity helps maintain healthy blood pressure [ish_c1].", "cites": ["ish_c1"]},
            ]
        })

    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"blood_pressure_systolic": 125.0, "blood_pressure_diastolic": 80.0},
        language="en",
        store=store,
        llm=plain_llm,
        provider="groq",
        condition="hypertension",
    )
    all_sentence_text = " ".join(s["text"] for s in res.get("sentences", []))
    assert secret_passage not in all_sentence_text


# =============================================================================
# X6: Deletion CLI Tool
# =============================================================================
def test_x6_delete_source_cli(tmp_path):
    """X6: scripts/rag/delete_source.py dry run vs permanent deletion (--yes)."""
    from scripts.rag.delete_source import delete_guideline_sources

    db_file = str(tmp_path / "test_delete.db")
    app_store.migrate(db_path=db_file, backend="sqlite")

    # Seed 3 dummy ADA chunks
    now = datetime.now().isoformat()
    with app_store.get_db_cursor(backend="sqlite", db_path=db_file) as (cur, be, ph):
        for i in range(1, 4):
            cur.execute(
                f"INSERT INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (f"ada_chunk_{i}", "ada_2026_sec02", "Diagnosis", "diabetes", "Text", now),
            )

    # 1. Dry run (execute=False)
    count_before, count_after = delete_guideline_sources(
        target_sources={"ada_2026_sec02"},
        execute=False,
        backend="sqlite",
        db_path=db_file,
    )
    assert count_before == 3
    assert count_after == 3, "Dry run must not delete rows"

    # 2. Real deletion (execute=True)
    count_before, count_after = delete_guideline_sources(
        target_sources={"ada_2026_sec02"},
        execute=True,
        backend="sqlite",
        db_path=db_file,
    )
    assert count_before == 3
    assert count_after == 0, "Deletion with execute=True must delete target rows"


# =============================================================================
# Z2: Diabetes Retrieval Preference & Hypertension Byte-Identical Invariance
# =============================================================================
def test_z2_diabetes_retrieval_prefers_ada_over_idf_dar_unless_fasting():
    """Z2: Non-fasting diabetes check-in prefers ADA over IDF-DAR; fasting query ranks IDF-DAR."""
    chunks = [
        {
            "chunk_id": "idf_c1",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR Ramadan Guidelines",
            "condition": "diabetes",
            "priority": 4,  # High priority in old spec
            "text": "Blood glucose monitoring and targets during daily activity.",
        },
        {
            "chunk_id": "ada_c1",
            "source_id": "ada_2026_sec06",
            "title": "ADA Glycemic Targets",
            "condition": "diabetes",
            "priority": 2,
            "text": "Blood glucose monitoring and targets for diabetes management.",
        },
    ]
    store = MockStore(chunks)
    retriever = BM25Retriever(store)

    # 1. Non-fasting query: ADA must rank ahead of IDF-DAR (IDF-DAR excluded for non-Ramadan)
    res_normal = retriever.retrieve("blood glucose monitoring targets", condition="diabetes")
    assert len(res_normal) == 1
    assert res_normal[0]["chunk_id"] == "ada_c1", "ADA must be preferred over IDF-DAR for standard diabetes check-in"

    # 2. Fasting / Ramadan query: IDF-DAR ranks ahead due to term match / normal priority
    res_fasting = retriever.retrieve("blood glucose monitoring during ramadan fasting", condition="diabetes")
    assert len(res_fasting) == 2
    assert res_fasting[0]["chunk_id"] == "idf_c1", "IDF-DAR must rank ahead when fasting / Ramadan is queried"


def test_z2_hypertension_retrieval_is_byte_identical_invariance():
    """Addition 2 (Usman): Hypertension retrieval output is byte-identical to baseline ranking."""
    htn_chunks = [
        {
            "chunk_id": "ish_1",
            "source_id": "ish_2020_htn",
            "title": "ISH BP Targets",
            "condition": "hypertension",
            "priority": 3,
            "text": "Target blood pressure for adults with hypertension is below 130/80 mmHg.",
        },
        {
            "chunk_id": "who_1",
            "source_id": "who_2021_htn",
            "title": "WHO Stage 2",
            "condition": "hypertension",
            "priority": 3,
            "text": "Blood pressure 140/90 mmHg or higher requires clinical management.",
        },
        {
            "chunk_id": "pk_1",
            "source_id": "pk_htn_women_2023",
            "title": "Pakistan Guidelines",
            "condition": "hypertension",
            "priority": 4,
            "text": "Hypertension in adult women: lifestyle and medical management.",
        },
    ]
    store = MockStore(htn_chunks)
    retriever = BM25Retriever(store)

    query = "blood pressure target below 130 80"
    res = retriever.retrieve(query, condition="hypertension")

    # Baseline expected ranking: ish_1 matches query terms best
    assert len(res) == 3
    assert res[0]["chunk_id"] == "ish_1"
    assert res[0]["rank"] == 1
    # Verify deterministic output
    res2 = retriever.retrieve(query, condition="hypertension")
    assert json.dumps(res, sort_keys=True) == json.dumps(res2, sort_keys=True)


# =============================================================================
# Z4: Diabetes Check-in with ADA via Groq
# =============================================================================
def test_z4_diabetes_checkin_with_ada_and_groq(monkeypatch):
    """Z4: Diabetes check-in with EXPLAIN_LLM_CONDITIONS=hypertension,diabetes uses Groq on ADA chunks."""
    monkeypatch.setenv("EXPLAIN_LLM_CONDITIONS", "hypertension,diabetes")

    # Mock ADA chunk with populated attribution
    ada_chunk = {
        "chunk_id": "ada_test_c1",
        "source_id": "ada_2026_sec02",
        "title": "ADA Classification",
        "condition": "diabetes",
        "priority": 2,
        "text": "Fasting glucose targets are 80-130 mg/dL.",
        "full_citation": "American Diabetes Association. Standards of Care in Diabetes 2026.",
        "doi": "https://doi.org/10.2337/dc26-S002",
    }
    store = MockStore([ada_chunk])

    groq_called = []
    def fake_groq(**kw):
        groq_called.append(True)
        return json.dumps({
            "sentences": [
                {"text": "Your blood sugar reading of 120 mg/dL is within target range [ada_test_c1].", "cites": ["ada_test_c1"]},
                {"text": "Continue your healthy dietary habits and daily monitoring [ada_test_c1].", "cites": ["ada_test_c1"]},
            ]
        })

    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"glucose": 120.0},
        language="en",
        store=store,
        llm=fake_groq,
        provider="groq",
        condition="diabetes",
    )

    assert len(groq_called) == 1, "Groq must be called for diabetes check-in with ADA chunks"
    assert res["mode"] == "llm"
    assert len(res["sources"]) == 1
    src = res["sources"][0]
    assert src["chunk_id"] == "ada_test_c1"
    assert src["full_citation"] == "American Diabetes Association. Standards of Care in Diabetes 2026."
    assert src["doi"] == "https://doi.org/10.2337/dc26-S002"


# =============================================================================
# Review Points 1-3 Tests
# =============================================================================
def test_review_point1_diabetes_non_ramadan_without_ada_citation_yields_template(monkeypatch):
    """
    Review Point 1: Diabetes, non-Ramadan check-ins:
    If ADA citation is not filled (or no ADA chunk survives), do NOT send other chunks (e.g. IDF-DAR) to the LLM.
    Use the template, reason 'licence_restricted', and zero LLM calls.
    """
    monkeypatch.setenv("EXPLAIN_LLM_CONDITIONS", "hypertension,diabetes")
    # Simulate ADA citation not filled
    set_attribution_override("ada_2026_sec02", "TO FILL BY USMAN", "TO FILL BY USMAN")

    chunks = [
        {
            "chunk_id": "ada_c1",
            "source_id": "ada_2026_sec02",
            "title": "ADA Diagnostic Targets",
            "condition": "diabetes",
            "priority": 2,
            "text": "Target glucose levels for adults with diabetes.",
        },
        {
            "chunk_id": "idf_c1",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR Ramadan Guidelines",
            "condition": "diabetes",
            "priority": 2,
            "text": "Fasting and diabetes management during Ramadan.",
        },
    ]
    store = MockStore(chunks)

    llm_called = []
    def fake_llm(**kw):
        llm_called.append(True)
        return json.dumps({"sentences": [{"text": "Sample explanation [idf_c1].", "cites": ["idf_c1"]}]})

    res = guarded_explain(
        triage_result={"level": "routine"},
        readings={"glucose": 250.0},
        language="en",
        store=store,
        llm=fake_llm,
        provider="groq",
        condition="diabetes",
    )

    assert len(llm_called) == 0, "LLM must NOT be called when no ADA chunk survives attribution for non-Ramadan diabetes"
    assert res["mode"] == "template"
    assert res["reason"] == "licence_restricted"


def test_review_point2_ramadan_detection_and_retrieval_preferences():
    """
    Review Point 2: Ramadan detection only uses real Ramadan words.
    - glucose_low query -> ADA preferred.
    - fasting glucose reading -> ADA preferred.
    - 'roza mein sugar 60' -> IDF allowed.
    """
    chunks = [
        {
            "chunk_id": "ada_hypo",
            "source_id": "ada_2026_sec06",
            "title": "ADA Hypoglycemia Management",
            "condition": "diabetes",
            "priority": 2,
            "text": "Hypoglycemia rule of 15 fast acting carbohydrate 15 grams glucose.",
        },
        {
            "chunk_id": "idf_ramadan",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR Ramadan Fasting",
            "condition": "diabetes",
            "priority": 2,
            "text": "Ramadan fasting risk management hypoglycemia roza iftar sehri sugar 60.",
        },
    ]
    store = MockStore(chunks)
    retriever = BM25Retriever(store)

    # 1. glucose_low query (contains 'fast acting carbohydrate') -> ADA preferred over IDF
    query_low = "glucose hypoglycemia 70 54 mgdl fast acting carbohydrate 15 grams rule of 15"
    res_low = retriever.retrieve(query_low, condition="diabetes")
    assert len(res_low) > 0
    assert res_low[0]["source_id"].startswith("ada_2026"), "ADA must be preferred for glucose_low query"

    # 2. Fasting glucose reading (e.g. 'fasting glucose 110 mg/dL') -> ADA preferred over IDF
    query_fasting = "fasting glucose 110 mgdl normal targets"
    res_fasting = retriever.retrieve(query_fasting, condition="diabetes")
    assert len(res_fasting) > 0
    assert res_fasting[0]["source_id"].startswith("ada_2026"), "ADA must be preferred for fasting glucose reading"

    # 3. 'roza mein sugar 60' (real Ramadan term 'roza') -> IDF allowed
    query_roza = "roza mein sugar 60"
    res_roza = retriever.retrieve(query_roza, condition="diabetes")
    assert any(c["source_id"].startswith("idf_dar") for c in res_roza), "IDF-DAR must be allowed for Ramadan query ('roza')"


def test_review_point3_reason_fasting_glucose_does_not_map_to_ramadan():
    """Review Point 3: Reason containing 'fasting glucose 145' does NOT map to ramadan_fasting query."""
    triage_result = {
        "level": "routine",
        "reasons": ["fasting glucose 145"],
    }
    mapping = build_query_from_triage(triage_result, readings={"glucose": 145.0})
    assert mapping.trigger_category != "ramadan_fasting", "Fasting glucose must NOT map to ramadan_fasting"
