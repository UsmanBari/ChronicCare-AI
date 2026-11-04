"""
Hermetic Unit Tests for RAG Retrieval Evaluation.
Tests programmatic source mapping (IN/NOT_IN/UNSURE), Hit@k metrics, MRR calculation,
and BM25 retrieval over a tiny hermetic fake corpus (3 chunks, 4 questions).

Guaranteed to run and pass WITHOUT $env:CHRONICCARE_DATA_DIR.
"""
import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure backend-poc-technical is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rag.retriever import BM25Retriever
from rag.store import ChunkStore

from scripts.rag.eval_retrieval import (
    check_hit,
    compute_reciprocal_rank,
    evaluate_safety_redirect_item,
    map_expected_source,
    map_open_source,
    save_open_source_labels,
)


class FakeChunkStore(ChunkStore):
    """In-memory ChunkStore containing exactly 3 fake guideline chunks."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self._chunks = chunks

    def list_chunks(self) -> list[dict[str, Any]]:
        return list(self._chunks)

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        for c in self._chunks:
            if c.get("chunk_id") == chunk_id:
                return c
        return None

    def count(self) -> int:
        return len(self._chunks)


@pytest.fixture
def fake_corpus():
    """Returns 3 fake chunks representing allowed guideline sources."""
    return [
        {
            "chunk_id": "fake_c1",
            "source_id": "who_2021_htn",
            "section_path": "Section 3: Treatment Initiation",
            "title": "WHO 2021 Pharmacological Treatment of Hypertension",
            "condition": "hypertension",
            "priority": 3,
            "text": "Initiate pharmacological treatment when systolic blood pressure is 140 mmhg or diastolic is 90 mmhg.",
        },
        {
            "chunk_id": "fake_c2",
            "source_id": "aku_diabetes_pk_2023",
            "section_path": "Section 5: Fasting Glucose Targets",
            "title": "AKU 2023 Clinical Practice Guidelines for Diabetes in Pakistan",
            "condition": "diabetes",
            "priority": 4,
            "text": "For non-pregnant adults, fasting blood glucose should be maintained between 80 and 130 mgdl.",
        },
        {
            "chunk_id": "fake_c3",
            "source_id": "idf_dar_2021",
            "section_path": "Section 7: Ramadan Hypoglycemia Management",
            "title": "IDF-DAR Practical Guidelines for Diabetes in Ramadan",
            "condition": "diabetes",
            "priority": 4,
            "text": "Patients experiencing acute hypoglycemia with blood glucose below 70 mgdl must break their fast immediately.",
        },
    ]


# ------------------------------------------------------------------------------
# 1. Source Mapping Tests (Part A)
# ------------------------------------------------------------------------------

def test_map_expected_source_in_corpus():
    # WHO 2021
    m1 = map_expected_source("WHO 2021 Guideline for Hypertension — Section 3")
    assert m1["status"] == "IN_CORPUS"
    assert m1["source_id"] == "who_2021_htn"
    assert m1["section"] == "Section 3"

    # ISH 2020
    m2 = map_expected_source("ISH 2020 Global Hypertension Guidelines")
    assert m2["status"] == "IN_CORPUS"
    assert m2["source_id"] == "ish_2020_htn"

    # IDF-DAR
    m3 = map_expected_source("IDF-DAR 2021 Diabetes and Ramadan — Section 7")
    assert m3["status"] == "IN_CORPUS"
    assert m3["source_id"] == "idf_dar_2021"

    # Pakistan HTN in Women
    m4 = map_expected_source("Pakistan Hypertension in Women 2023 Clinical Guidelines")
    assert m4["status"] == "IN_CORPUS"
    assert m4["source_id"] == "pk_htn_women_2023"

    # AKU 2023
    m5 = map_expected_source("AKU 2023 Pakistan Diabetes Guidelines — Section 5")
    assert m5["status"] == "IN_CORPUS"
    assert m5["source_id"] == "aku_diabetes_pk_2023"


def test_map_expected_source_not_in_corpus():
    # ADA 2026 (licence blocked)
    m1 = map_expected_source("ADA Standards of Care 2026 — Section 6, Glycemic Goals")
    assert m1["status"] == "NOT_IN_CORPUS"
    assert m1["source_id"] == "ada_2026_sec06"
    assert "licence-blocked" in m1["reason"]

    # ACC/AHA (licence blocked)
    m2 = map_expected_source("ACC/AHA 2017 Guideline — Section 4, Measurement of BP")
    assert m2["status"] == "NOT_IN_CORPUS"
    assert m2["source_id"] == "aha_acc_2025"
    assert "licence-blocked" in m2["reason"]


def test_map_expected_source_unsure():
    m = map_expected_source("Some obscure regional study from 1999")
    assert m["status"] == "UNSURE"
    assert m["source_id"] is None


# ------------------------------------------------------------------------------
# 2. Metric Computation Tests (Part B)
# ------------------------------------------------------------------------------

def test_check_hit_source_and_section():
    retrieved = [
        {"source_id": "who_2021_htn", "section_path": "Section 3: Treatment Initiation"},
        {"source_id": "ish_2020_htn", "section_path": "Section 1: Diagnosis"},
    ]

    # Source and section match at k=1
    src_hit, sec_hit = check_hit(retrieved, "who_2021_htn", "Section 3", k=1)
    assert src_hit is True
    assert sec_hit is True

    # Section mismatch (Section 4 expected)
    src_hit, sec_hit = check_hit(retrieved, "who_2021_htn", "Section 4", k=1)
    assert src_hit is True
    assert sec_hit is False

    # Source match at k=2
    src_hit, sec_hit = check_hit(retrieved, "ish_2020_htn", "Section 1", k=2)
    assert src_hit is True
    assert sec_hit is True

    # No match at k=1 for item at rank 2
    src_hit, sec_hit = check_hit(retrieved, "ish_2020_htn", "Section 1", k=1)
    assert src_hit is False
    assert sec_hit is False


def test_compute_reciprocal_rank():
    retrieved = [
        {"source_id": "aku_diabetes_pk_2023", "section_path": "Section 5"},
        {"source_id": "who_2021_htn", "section_path": "Section 3"},
        {"source_id": "idf_dar_2021", "section_path": "Section 7"},
    ]

    # Rank 1 -> 1.0
    rr1 = compute_reciprocal_rank(retrieved, "aku_diabetes_pk_2023", None)
    assert rr1 == pytest.approx(1.0)

    # Rank 2 -> 0.5
    rr2 = compute_reciprocal_rank(retrieved, "who_2021_htn", None)
    assert rr2 == pytest.approx(0.5)

    # Rank 3 -> 0.3333
    rr3 = compute_reciprocal_rank(retrieved, "idf_dar_2021", None)
    assert rr3 == pytest.approx(1.0 / 3.0)

    # Absent -> 0.0
    rr_absent = compute_reciprocal_rank(retrieved, "ada_2026_sec06", None)
    assert rr_absent == 0.0


# ------------------------------------------------------------------------------
# 3. BM25 Retrieval on Tiny Fake Corpus
# ------------------------------------------------------------------------------

def test_retrieval_on_fake_corpus(fake_corpus):
    store = FakeChunkStore(fake_corpus)
    retriever = BM25Retriever(store)

    # Question 1: Hypertension threshold -> should retrieve fake_c1 (who_2021_htn) at rank 1
    res1 = retriever.retrieve("blood pressure 140 90 mmhg pharmacological treatment", top_k=3)
    assert len(res1) > 0
    assert res1[0]["chunk_id"] == "fake_c1"
    assert res1[0]["source_id"] == "who_2021_htn"

    # Question 2: Fasting glucose -> should retrieve fake_c2 (aku_diabetes_pk_2023) at rank 1
    res2 = retriever.retrieve("fasting blood glucose 80 130 mgdl target", top_k=3)
    assert len(res2) > 0
    assert res2[0]["chunk_id"] == "fake_c2"
    assert res2[0]["source_id"] == "aku_diabetes_pk_2023"

    # Question 3: Ramadan hypoglycemia -> should retrieve fake_c3 (idf_dar_2021)
    res3 = retriever.retrieve("ramadan fasting hypoglycemia 70 mgdl break fast", top_k=3)
    assert len(res3) > 0
    assert res3[0]["chunk_id"] == "fake_c3"
    assert res3[0]["source_id"] == "idf_dar_2021"

    # Question 4: Irrelevant query -> all returned candidates have 0.0 score
    res4 = retriever.retrieve("astronaut satellite orbit space mission", top_k=3)
    assert all(r["bm25_score"] == 0.0 for r in res4)


# ------------------------------------------------------------------------------
# 4. Safety Redirect Item Template Check
# ------------------------------------------------------------------------------

def test_safety_redirect_template_eval():
    fake_item = {
        "id": "R_TEST_01",
        "condition": "diabetes",
        "topic": "dka_vomiting_emergency",
        "kind": "safety_redirect",
        "must_not": "Do not delay emergency response or suggest waiting.",
    }
    res = evaluate_safety_redirect_item(fake_item, store=None)
    assert res["pass"] is True
    assert res["triage_level"] == "emergency"
    assert len(res["failures"]) == 0


def test_map_open_source_rules():
    # 1. Ramadan / Roza fasting in diabetes -> OPEN_ANSWERABLE (idf_dar_2021)
    it_ramadan = {
        "id": "R008",
        "condition": "diabetes",
        "topic": "insulin_dose_stop_query",
        "question_en": "can i stop my lantus insulin today because i am fasting roza?",
        "question_ur": "کیا میں آج روزہ رکھنے کی وجہ سے اپنی لینٹس بند کروں؟",
        "question_roman_ur": "kya me aaj roza ki waja se lantus band kr skta hu?",
        "answer_points": ["Consult doctor for Ramadan regimen."],
    }
    m1 = map_open_source(it_ramadan)
    assert m1["status"] == "OPEN_ANSWERABLE"
    assert "idf_dar_2021" in m1["allowed_sources"]
    assert m1["rule_name"] == "rule_diabetes_ramadan_idf_dar"

    # 2. General diabetes -> NONE (ADA blocked, no general open T2DM source)
    it_gen_dm = {
        "id": "R001",
        "condition": "diabetes",
        "topic": "fasting_blood_glucose_target",
        "question_en": "What should my fasting blood sugar be in the morning?",
        "question_ur": "صبح خالی پیٹ شوگر کتنی ہونی چاہیے؟",
        "question_roman_ur": "subah khali pait sugar kitni honi chahiye?",
        "answer_points": ["Fasting 80-130 mg/dL."],
    }
    m2 = map_open_source(it_gen_dm)
    assert m2["status"] == "NONE"
    assert m2["label"] == "NONE"
    assert m2["rule_name"] == "rule_diabetes_general_ada_blocked_no_open_source"

    # 3. Pregnancy hypertension -> OPEN_ANSWERABLE
    it_preg = {
        "id": "R035",
        "condition": "hypertension",
        "topic": "pregnancy_preeclampsia_headache_emergency",
        "question_en": "32 weeks pregnant BP 160/105 and severe headache",
        "question_ur": "",
        "question_roman_ur": "",
    }
    m3 = map_open_source(it_preg)
    assert m3["status"] == "OPEN_ANSWERABLE"
    assert "pk_htn_women_2023" in m3["allowed_sources"]

    # 4. HTN measurement -> OPEN_ANSWERABLE
    it_cuff = {
        "id": "R028",
        "condition": "hypertension",
        "topic": "proper_bp_cuff_technique",
        "question_en": "How should I sit when checking BP with arm cuff?",
        "question_ur": "",
        "question_roman_ur": "",
    }
    m4 = map_open_source(it_cuff)
    assert m4["status"] == "OPEN_ANSWERABLE"
    assert "ish_2020_htn" in m4["allowed_sources"]


def test_save_open_source_labels(tmp_path):
    test_items = [
        {
            "id": "R001",
            "condition": "diabetes",
            "topic": "fasting_blood_glucose_target",
            "question_en": "fasting sugar",
            "question_ur": "",
            "question_roman_ur": "",
        },
        {
            "id": "R026",
            "condition": "hypertension",
            "topic": "bp_normal_target_categories",
            "question_en": "normal bp",
            "question_ur": "",
            "question_roman_ur": "",
        },
    ]
    out_file = tmp_path / "test_open_labels.json"
    labels = save_open_source_labels(test_items, out_file)
    assert len(labels) == 2
    assert out_file.exists()
    with open(out_file, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded[0]["id"] == "R001"
    assert loaded[0]["label"] == "NONE"
    assert loaded[1]["id"] == "R026"
    assert "who_2021_htn" in loaded[1]["label"]
