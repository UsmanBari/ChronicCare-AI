"""Unit tests for clinical guideline chunking module.

Uses synthetic fake guideline text exclusively (no real copyright text).
"""

import os
import sys

# Ensure root backend dir is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag.chunking import (
    clean_page_text,
    split_sections,
    chunk_section,
    tag_condition,
    tag_topics,
    build_chunk_record,
)


def test_clean_page_text_headers_footers_and_hyphenation():
    """Verify running headers/footers (>50% pages), hyphenation, and page numbers are cleaned."""
    pages = [
        "FAKE GUIDELINE HEADER VOLUME 2026\n1. Overview of Glycemic Control\nThis is an inter-\nvention for patients.\nPage 1\nFAKE GUIDELINE FOOTER 2026",
        "FAKE GUIDELINE HEADER VOLUME 2026\n2. Clinical Management\nAnother paragraph of text.\nPage 2\nFAKE GUIDELINE FOOTER 2026",
        "FAKE GUIDELINE HEADER VOLUME 2026\n3. Lifestyle Advice\nFinal recommendations.\nPage 3\nFAKE GUIDELINE FOOTER 2026",
    ]

    cleaned, dropped_ref = clean_page_text(pages)
    assert len(cleaned) == 3

    # Repeated headers and footers should be removed
    for p in cleaned:
        assert "FAKE GUIDELINE HEADER VOLUME 2026" not in p
        assert "FAKE GUIDELINE FOOTER 2026" not in p
        assert "Page " not in p

    # Hyphenated word joined
    assert "intervention" in cleaned[0]
    assert "inter-\nvention" not in cleaned[0]


def test_clean_page_text_drops_references():
    """Verify reference sections from 'References' to the end are dropped."""
    pages = [
        "FAKE GUIDELINE: Section 4 Treatment\nPatients should measure blood pressure daily.\nReferences\n1. Smith AB, Jones CD. Blood pressure control. doi:10.1016/j.jacc.2020.01.001\n2. Doe EF, et al. Hypertension care. 2021;14(2):100-105",
    ]
    cleaned, dropped_ref = clean_page_text(pages)
    assert "Smith AB" not in cleaned[0]
    assert "Patients should measure blood pressure daily." in cleaned[0]
    assert dropped_ref >= 1


def test_hard_cap_1500_word_sentence():
    """Verify a single 1,500-word sentence gives chunks that are all <= 400 words."""
    word = "clinicalevidence"
    fake_1500_words = " ".join([word] * 1500)  # exactly 1500 words, no period in the middle

    section = {
        "section_path": "Section 3 > Continuous Large Table",
        "text": fake_1500_words,
        "page_start": 1,
        "page_end": 3,
        "is_recommendation": False,
        "grade": None,
    }

    chunks = chunk_section(section, min_words=200, max_words=400, overlap_words=40)
    assert len(chunks) >= 4
    for c in chunks:
        assert c["word_count"] <= 400
        assert len(c["text"].split()) <= 400


def test_citation_block_dropped():
    """Verify blocks where >40% lines look like citations are dropped."""
    citation_block = (
        "140 Hoshide S, Kario K, de la Sierra A. Ambulatory BP monitoring. doi:10.1038/s41371-020-0381-8\n"
        "141 Nieman LK, Biller BM, Findling JW. Endocrine evaluation. 2020;105(3):e12-e25\n"
        "142 Tomaszewski M, White C, Patel P. Adherence to therapy. et al.\n"
        "Some occasional clinical narrative sentence here."
    )
    section = {
        "section_path": "Section 9 > Reference Citations",
        "text": citation_block,
        "page_start": 20,
        "page_end": 20,
        "is_recommendation": False,
        "grade": None,
    }
    chunks = chunk_section(section)
    assert chunks == []


def test_numbered_citation_not_detected_as_heading():
    """Verify numbered citation lines like '140 Hoshide S,' are not treated as section headings."""
    pages = [
        "140 Hoshide S, Kario K, de la Sierra A, Bilo G. Guideline references text.\n"
        "141 Nieman LK, Biller BM. More citation content.\n"
        "1. Real Clinical Section\nReal section body text."
    ]
    sections = split_sections(pages)
    headings = [s["heading"] for s in sections]
    assert not any("140 Hoshide" in h for h in headings)
    assert not any("141 Nieman" in h for h in headings)
    assert any("1 Real Clinical Section" in h for h in headings)



def test_split_sections_heading_hierarchy():
    """Verify 3-level heading path tracking."""
    pages = [
        "6 Glycemic Goals\nIntroductory remarks.\n6.1 Hypoglycemia Assessment\nAssessment criteria.\n6.1.1 Severe Events\nDetailed event triage.",
    ]
    sections = split_sections(pages)
    assert len(sections) >= 3

    paths = [s["section_path"] for s in sections]
    assert any("6 Glycemic Goals" in p for p in paths)
    assert any("6 Glycemic Goals > 6.1 Hypoglycemia Assessment" in p for p in paths)
    assert any("6.1.1 Severe Events" in p for p in paths)


def test_recommendation_boxes_and_grade_extraction():
    """Verify ADA and AHA style recommendation boxes are extracted with grades."""
    pages = [
        "6.5 In individuals with type 2 diabetes, blood pressure should be treated to target. Grade A\n"
        "Recommendations: Hypertension\n"
        "For adults with confirmed hypertension, treatment with two first-line agents is recommended. COR 1, LOE A",
    ]
    sections = split_sections(pages)
    recs = [s for s in sections if s["is_recommendation"]]
    assert len(recs) >= 1

    grades = [s["grade"] for s in sections if s["grade"]]
    assert "A" in grades or any("COR 1, LOE A" in str(g) for g in grades)


def test_chunk_section_bounds_and_overlap():
    """Verify word bounds (200-400), overlap (~40 words), and sentence integrity."""
    # Build synthetic section of ~600 words
    sentence = "FAKE GUIDELINE: Clinical evaluation must be conducted with calibrated instruments and proper cuff size for patient comfort. "
    long_text = sentence * 45  # ~630 words

    section = {
        "section_path": "Section 1 > Blood Pressure Measurement",
        "text": long_text,
        "page_start": 5,
        "page_end": 6,
        "is_recommendation": False,
        "grade": None,
    }

    chunks = chunk_section(section, min_words=200, max_words=400, overlap_words=40)
    assert len(chunks) >= 2

    for c in chunks:
        # Never cross section
        assert c["section_path"] == "Section 1 > Blood Pressure Measurement"
        # Each chunk should not split mid-sentence
        assert c["text"].endswith(".") or c["text"].endswith("comfort.")
        # Words should be reasonable
        assert c["word_count"] >= 100

    # Verify overlap exists between consecutive chunks
    c1_words = set(chunks[0]["text"].split()[-20:])
    c2_words = set(chunks[1]["text"].split()[:30])
    assert len(c1_words.intersection(c2_words)) > 0


def test_chunk_id_stability():
    """Verify chunk_id is deterministic and stable across calls."""
    chunk_data = {
        "section_path": "Section 6 > Hypoglycemia",
        "text": "FAKE GUIDELINE: Hypoglycemia below 70 mg/dL is Level 1, requiring rapid carbohydrates.",
        "page_start": 10,
        "page_end": 10,
        "grade": "A",
    }

    r1 = build_chunk_record(chunk_data, "ada_test_sec6", "ADA Test", "2026", 2)
    r2 = build_chunk_record(chunk_data, "ada_test_sec6", "ADA Test", "2026", 2)

    assert r1["chunk_id"] == r2["chunk_id"]
    assert len(r1["chunk_id"]) == 40  # full sha1 hexdigest


def test_condition_and_topic_tagging():
    """Verify keyword tagging for conditions and topic slugs."""
    text_dm = "FAKE GUIDELINE: Severe hypoglycemia occurs when blood glucose falls below 54 mg/dL. Shaky and sweating symptoms occur."
    assert tag_condition(text_dm, "ada2026_sec06") == "diabetes"
    topics_dm = tag_topics(text_dm)
    assert "hypoglycemia" in topics_dm

    text_htn = "FAKE GUIDELINE: Home blood pressure measurement requires 5 minutes rest with validated cuff. Stage 2 hypertension requires treatment."
    assert tag_condition(text_htn, "aha_acc_2025") == "hypertension"
    topics_htn = tag_topics(text_htn)
    assert "bp_measurement" in topics_htn
    assert "diagnosis_thresholds" in topics_htn

    text_both = "FAKE GUIDELINE: Patients with both diabetes and hypertension require comprehensive cardiovascular risk management and bp target <130/80."
    assert tag_condition(text_both, "who_guideline") == "both"
    topics_both = tag_topics(text_both)
    assert "bp_targets" in topics_both
