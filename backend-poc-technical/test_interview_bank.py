"""
Unit Tests for Question Bank and Loader (Stage 9A Task B).

Verifies:
1. All module JSON files validate against the strict BankItem schema.
2. Loader rejects duplicate IDs.
3. Loader rejects missing or empty templates in any of the 3 languages.
4. Loader rejects can_raise_level=True without a valid rule_id.
5. Loader rejects items referencing unlisted or unknown sources.
6. Probes bank and odd-input response templates load completely.
"""

import json
import os
import pytest
from agents.interview_bank.loader import (
    BankItem,
    QuestionBank,
    load_question_bank,
    get_default_bank,
)


def test_question_bank_loads_successfully():
    bank = load_question_bank()
    items = bank.all_items()
    assert len(items) >= 30, f"Expected >= 30 bank items, found {len(items)}"
    sources = bank.get_sources()
    assert len(sources) >= 5
    probes = bank.get_probes()
    assert len(probes) >= 5
    responses = bank.get_responses()
    assert len(responses) >= 8


def test_question_bank_item_fields_and_languages():
    bank = load_question_bank()
    for item in bank.all_items():
        assert item.id, "Item missing id"
        assert item.module, f"Item {item.id} missing module"
        assert item.slot, f"Item {item.id} missing slot"
        assert item.why_text, f"Item {item.id} missing why_text"
        assert item.template_en, f"Item {item.id} missing template_en"
        assert item.template_ur, f"Item {item.id} missing template_ur"
        assert item.template_roman_ur, f"Item {item.id} missing template_roman_ur"
        assert item.answer_type in ("number", "choice", "yes_no", "free_text", "rating_scale", "multiple_choice")
        assert item.priority_class in ("safety", "contradiction", "trend", "barrier", "open", "wellbeing")
        assert item.review_status == "proposed, not reviewed by a clinician"

        if item.can_raise_level:
            assert item.rule_id is not None, f"Item {item.id} has can_raise_level=True but rule_id is None"


def test_loader_rejects_duplicate_id(tmp_path):
    sources = {"ada_2026": {"title": "ADA 2026", "status": "title exists, claim not checked"}}
    with open(tmp_path / "SOURCES.json", "w", encoding="utf-8") as f:
        json.dump(sources, f)

    bad_module = [
        {
            "id": "dup_item_1",
            "module": "core",
            "slot": "slot_a",
            "why_text": "Why A",
            "template_en": "English A",
            "template_ur": "Urdu A",
            "template_roman_ur": "Roman A",
            "answer_type": "yes_no",
            "priority_class": "open",
            "source": "ada_2026",
        },
        {
            "id": "dup_item_1",
            "module": "core",
            "slot": "slot_b",
            "why_text": "Why B",
            "template_en": "English B",
            "template_ur": "Urdu B",
            "template_roman_ur": "Roman B",
            "answer_type": "yes_no",
            "priority_class": "open",
            "source": "ada_2026",
        }
    ]
    with open(tmp_path / "core.json", "w", encoding="utf-8") as f:
        json.dump(bad_module, f)

    with pytest.raises(ValueError, match="Duplicate question bank id 'dup_item_1'"):
        load_question_bank(str(tmp_path))


def test_loader_rejects_missing_template(tmp_path):
    sources = {"ada_2026": {"title": "ADA 2026", "status": "title exists, claim not checked"}}
    with open(tmp_path / "SOURCES.json", "w", encoding="utf-8") as f:
        json.dump(sources, f)

    bad_module = [
        {
            "id": "item_missing_ur",
            "module": "core",
            "slot": "slot_a",
            "why_text": "Why A",
            "template_en": "English A",
            "template_ur": "",  # Empty template
            "template_roman_ur": "Roman A",
            "answer_type": "yes_no",
            "priority_class": "open",
            "source": "ada_2026",
        }
    ]
    with open(tmp_path / "core.json", "w", encoding="utf-8") as f:
        json.dump(bad_module, f)

    with pytest.raises(ValueError, match="Missing or empty template 'template_ur'"):
        load_question_bank(str(tmp_path))


def test_loader_rejects_unmapped_raise_level(tmp_path):
    sources = {"ada_2026": {"title": "ADA 2026", "status": "title exists, claim not checked"}}
    with open(tmp_path / "SOURCES.json", "w", encoding="utf-8") as f:
        json.dump(sources, f)

    bad_module = [
        {
            "id": "item_bad_raise",
            "module": "core",
            "slot": "slot_a",
            "why_text": "Why A",
            "template_en": "English A",
            "template_ur": "Urdu A",
            "template_roman_ur": "Roman A",
            "answer_type": "yes_no",
            "priority_class": "safety",
            "can_raise_level": True,
            "rule_id": None,  # Missing rule ID
            "source": "ada_2026",
        }
    ]
    with open(tmp_path / "core.json", "w", encoding="utf-8") as f:
        json.dump(bad_module, f)

    with pytest.raises(ValueError, match="has can_raise_level=True but rule_id is empty/missing"):
        load_question_bank(str(tmp_path))


def test_loader_rejects_unknown_source(tmp_path):
    sources = {"ada_2026": {"title": "ADA 2026", "status": "title exists, claim not checked"}}
    with open(tmp_path / "SOURCES.json", "w", encoding="utf-8") as f:
        json.dump(sources, f)

    bad_module = [
        {
            "id": "item_bad_source",
            "module": "core",
            "slot": "slot_a",
            "why_text": "Why A",
            "template_en": "English A",
            "template_ur": "Urdu A",
            "template_roman_ur": "Roman A",
            "answer_type": "yes_no",
            "priority_class": "open",
            "source": "invented_fake_source_123",
        }
    ]
    with open(tmp_path / "core.json", "w", encoding="utf-8") as f:
        json.dump(bad_module, f)

    with pytest.raises(ValueError, match="unknown or missing source key 'invented_fake_source_123'"):
        load_question_bank(str(tmp_path))
