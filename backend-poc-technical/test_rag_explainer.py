"""
Unit tests for ChronicCare AI Grounded Explainer and Validators (V1-V5).
Hermetic and fast, using fake chunk store and mock LLM functions.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import pytest

from rag.explainer import (
    explain,
    extract_numbers,
    get_allowed_numbers,
    validate_banned_patterns,
    validate_citations,
    validate_level_consistency,
    validate_number_grounding,
    validate_sentence_structure,
)
from rag.store import JsonlChunkStore


@pytest.fixture
def mock_chunk_store(tmp_path: Path) -> JsonlChunkStore:
    p = tmp_path / "mock_chunks.jsonl"
    chunks = [
        {
            "chunk_id": "chunk_htn_01",
            "source_id": "ish_2020_htn",
            "title": "ISH 2020 Guidelines",
            "edition": "2020",
            "priority": 1,
            "section_path": "Emergencies > Severe BP",
            "page_start": 15,
            "page_end": 15,
            "grade": "Essential",
            "condition": "hypertension",
            "topics": ["crisis", "emergency", "bp_targets"],
            "text": "Hypertensive crisis requires immediate medical attention when systolic blood pressure exceeds 180 mmHg or diastolic exceeds 120 mmHg.",
            "word_count": 20,
        },
        {
            "chunk_id": "chunk_diab_01",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR 2021",
            "edition": "2021",
            "priority": 1,
            "section_path": "Hypoglycemia Management",
            "page_start": 40,
            "page_end": 40,
            "grade": "Essential",
            "condition": "diabetes",
            "topics": ["hypoglycemia", "emergency"],
            "text": "When blood glucose is below 70 mg/dL, patients should take 15 grams of fast-acting carbohydrates immediately.",
            "word_count": 18,
        },
    ]
    with open(p, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    return JsonlChunkStore(p)


# -----------------------------------------------------------------------------
# 1. Immutability Tests
# -----------------------------------------------------------------------------
def test_explain_inputs_remain_byte_identical(mock_chunk_store: JsonlChunkStore):
    triage_input = {
        "level": "emergency",
        "trigger_category": "bp_severe",
        "reasons": ["bp_severe: SBP >= 180 or DBP >= 120"],
        "systolic": 185,
        "diastolic": 125,
    }
    readings_input = {"blood_pressure_systolic": 185, "blood_pressure_diastolic": 125}

    triage_before = copy.deepcopy(triage_input)
    readings_before = copy.deepcopy(readings_input)

    res = explain(triage_input, readings_input, language="en", store=mock_chunk_store, llm=None)

    assert triage_input == triage_before
    assert readings_input == readings_before
    assert res["mode"] == "template"


# -----------------------------------------------------------------------------
# 2. Validator Unit Tests
# -----------------------------------------------------------------------------
def test_validator_v1_sentence_structure():
    # Valid 2 sentences
    good = {
        "sentences": [
            {"text": "Your blood pressure is elevated [S1].", "cites": ["S1"]},
            {"text": "Please rest quietly before re-checking [S1].", "cites": ["S1"]},
        ]
    }
    assert validate_sentence_structure(good) == []

    # Invalid: 1 sentence only
    too_few = {"sentences": [{"text": "Just one sentence [S1].", "cites": ["S1"]}]}
    errs = validate_sentence_structure(too_few)
    assert any("Expected 2 to 3 sentences" in e for e in errs)

    # Invalid: > 35 words
    long_sentence = "word " * 36
    too_long = {
        "sentences": [
            {"text": long_sentence, "cites": ["S1"]},
            {"text": "Short sentence [S1].", "cites": ["S1"]},
        ]
    }
    errs_long = validate_sentence_structure(too_long)
    assert any("exceeds 35 words" in e for e in errs_long)


def test_validator_v2_citations():
    candidates = [{"chunk_id": "c1"}, {"chunk_id": "c2"}]

    # Valid citations
    sentences = [
        {"text": "Blood pressure is high [S1].", "cites": ["S1"]},
        {"text": "Re-check after 5 minutes [S2].", "cites": ["S2"]},
    ]
    errs, resolved = validate_citations(sentences, candidates)
    assert errs == []
    assert resolved[0]["cites"] == ["c1"]
    assert resolved[1]["cites"] == ["c2"]

    # Invalid: missing citation
    no_cite = [{"text": "No citation here.", "cites": []}]
    errs_no_cite, _ = validate_citations(no_cite, candidates)
    assert any("contains no citations" in e for e in errs_no_cite)

    # Invalid: citing unretrieved source
    bad_cite = [{"text": "Wrong citation [S99].", "cites": ["S99"]}]
    errs_bad, _ = validate_citations(bad_cite, candidates)
    assert any("cites unretrieved sources" in e for e in errs_bad)


def test_validator_v3_number_grounding():
    allowed = {"180", "120", "185", "125"}

    # Good: only allowed numbers
    good = [{"text": "Your reading of 185/125 mmHg is above 180/120 mmHg [S1]."}]
    assert validate_number_grounding(good, allowed) == []

    # Bad: hallucinated number 220
    hallucinated = [{"text": "Your reading of 185 mmHg might reach 220 mmHg [S1]."}]
    errs = validate_number_grounding(hallucinated, allowed)
    assert any("hallucinated/unverified numbers" in e for e in errs)
    assert any("220" in e for e in errs)


def test_validator_v4_banned_patterns():
    # Diagnostic pattern
    diag = [{"text": "You have diabetes and need care [S1]."}]
    errs_diag = validate_banned_patterns(diag, "review")
    assert any("forbidden diagnostic phrasing" in e for e in errs_diag)

    # Dosing pattern
    dose = [{"text": "Please take metformin 500 mg right away [S1]."}]
    errs_dose = validate_banned_patterns(dose, "review")
    assert any("forbidden dosing/prescribing phrasing" in e for e in errs_dose)

    # False reassurance on severe level
    reassure = [{"text": "Don't worry, you are fine and all is well [S1]."}]
    errs_reassure = validate_banned_patterns(reassure, "emergency")
    assert any("forbidden reassurance" in e for e in errs_reassure)

    # Allowed reassurance on routine level
    errs_routine = validate_banned_patterns(reassure, "routine")
    assert errs_routine == []


def test_validator_v5_level_consistency():
    # Conflicting level word in urgent case
    conflict = [{"text": "This is a routine blood pressure reading [S1]."}]
    errs = validate_level_consistency(conflict, "urgent")
    assert any("conflicting with decided level 'urgent'" in e for e in errs)

    # Matching level word
    matching = [{"text": "This is an urgent situation requiring prompt medical attention [S1]."}]
    assert validate_level_consistency(matching, "urgent") == []


# -----------------------------------------------------------------------------
# 3. Full explain() Pipeline with Mock LLM
# -----------------------------------------------------------------------------
def test_explain_happy_path(mock_chunk_store: JsonlChunkStore):
    def mock_llm(**kwargs):
        return json.dumps({
            "sentences": [
                {
                    "text": "Your blood pressure is 185/125 mmHg, which is severely high [S1].",
                    "cites": ["S1"],
                },
                {
                    "text": "Guidelines recommend immediate emergency medical care for these readings [S1].",
                    "cites": ["S1"],
                },
            ]
        })

    triage = {
        "level": "emergency",
        "trigger_category": "bp_severe",
        "systolic": 185,
        "diastolic": 125,
    }
    readings = {"blood_pressure_systolic": 185, "blood_pressure_diastolic": 125}

    res = explain(triage, readings, language="en", store=mock_chunk_store, llm=mock_llm)
    assert res["mode"] == "llm"
    assert res["language"] == "en"
    assert len(res["sentences"]) == 2
    assert res["sentences"][0]["cites"] == ["chunk_htn_01"]
    assert len(res["sources"]) >= 1
    assert res["rejected_reasons"] == []


def test_explain_fallback_on_validator_failure(mock_chunk_store: JsonlChunkStore):
    # Mock LLM returns hallucinated number 999
    def mock_bad_llm(**kwargs):
        return json.dumps({
            "sentences": [
                {"text": "Your reading reached 999 mmHg [S1].", "cites": ["S1"]},
                {"text": "Seek medical help immediately [S1].", "cites": ["S1"]},
            ]
        })

    triage = {
        "level": "emergency",
        "trigger_category": "bp_severe",
        "systolic": 185,
        "diastolic": 125,
    }
    readings = {"blood_pressure_systolic": 185, "blood_pressure_diastolic": 125}

    res = explain(triage, readings, language="en", store=mock_chunk_store, llm=mock_bad_llm)
    assert res["mode"] == "template"
    assert any("V3:" in r for r in res["rejected_reasons"])
    # Template has formatted placeholders
    assert "185/125" in res["sentences"][0]["text"]


def test_explain_urdu_translation_pipeline(mock_chunk_store: JsonlChunkStore):
    call_count = 0

    def mock_multilingual_llm(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # English generation
            return json.dumps({
                "sentences": [
                    {"text": "Your blood pressure is 185/125 mmHg [S1].", "cites": ["S1"]},
                    {"text": "Please seek emergency care immediately [S1].", "cites": ["S1"]},
                ]
            })
        else:
            # Urdu translation keeping numbers and citations intact
            return json.dumps({
                "sentences": [
                    {"text": "آپ کا بلڈ پریشر 185/125 mmHg ہے [S1]۔", "cites": ["S1"]},
                    {"text": "براہ کرم فوری ہنگامی طبی امداد طلب کریں [S1]۔", "cites": ["S1"]},
                ]
            })

    triage = {
        "level": "emergency",
        "trigger_category": "bp_severe",
        "systolic": 185,
        "diastolic": 125,
    }
    readings = {"blood_pressure_systolic": 185, "blood_pressure_diastolic": 125}

    res = explain(triage, readings, language="ur", store=mock_chunk_store, llm=mock_multilingual_llm)
    assert res["mode"] == "llm"
    assert res["language"] == "ur"
    assert "185/125" in res["sentences"][0]["text"]
    assert res["rejected_reasons"] == []
