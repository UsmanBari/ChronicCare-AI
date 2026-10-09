"""
Question Bank Loader & Schema Validator (Interview Engine v3).

Loads all modular question files, validates schema integrity against SOURCES.json,
checks for duplicate IDs, missing templates, unmapped rule triggers, and returns
an indexed in-memory Question Bank.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


VALID_MODULES = {
    "core",
    "diabetes",
    "hypertension",
    "insulin_or_sulfonylurea",
    "fasting",
    "access_barriers",
    "sick_day",
    "wellbeing",
    "caregiver",
}

VALID_PRIORITY_CLASSES = {
    "safety",
    "contradiction",
    "trend",
    "barrier",
    "open",
    "wellbeing",
}

VALID_ANSWER_TYPES = {
    "number",
    "choice",
    "yes_no",
    "free_text",
    "rating_scale",
    "multiple_choice",
}


@dataclass(frozen=True)
class BankItem:
    id: str
    module: str
    slot: str
    why_text: str
    template_en: str
    template_ur: str
    template_roman_ur: str
    answer_type: str
    choices: Optional[List[str]]
    valid_range: Optional[List[float]]
    unit_options: Optional[List[str]]
    requires: Dict[str, Any]
    priority_class: str
    can_raise_level: bool
    rule_id: Optional[str]
    source: str
    review_status: str
    bank_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class QuestionBank:
    """Indexed storage of all validated bank questions, probes, responses, and sources."""

    def __init__(
        self,
        items: List[BankItem],
        sources: Dict[str, Any],
        probes: Dict[str, List[Dict[str, Any]]],
        responses: Dict[str, Dict[str, str]],
    ):
        self._items = items
        self._items_by_id: Dict[str, BankItem] = {it.id: it for it in items}
        self._items_by_slot: Dict[str, BankItem] = {it.slot: it for it in items}
        self._sources = sources
        self._probes = probes
        self._responses = responses

    def all_items(self) -> List[BankItem]:
        return list(self._items)

    def get_by_id(self, item_id: str) -> Optional[BankItem]:
        return self._items_by_id.get(item_id)

    def get_by_slot(self, slot: str) -> Optional[BankItem]:
        return self._items_by_slot.get(slot)

    def get_by_module(self, module: str) -> List[BankItem]:
        return [it for it in self._items if it.module == module]

    def get_sources(self) -> Dict[str, Any]:
        return dict(self._sources)

    def get_probes(self) -> Dict[str, List[Dict[str, Any]]]:
        return dict(self._probes)

    def get_responses(self) -> Dict[str, Dict[str, str]]:
        return dict(self._responses)


def load_question_bank(bank_dir: Optional[str] = None) -> QuestionBank:
    """
    Loads and validates all question bank data from bank_dir.
    Raises ValueError on any schema violation, missing template, duplicate ID,
    or source mismatch.
    """
    if bank_dir is None:
        bank_dir = os.path.dirname(os.path.abspath(__file__))

    sources_path = os.path.join(bank_dir, "SOURCES.json")
    if not os.path.exists(sources_path):
        raise FileNotFoundError(f"SOURCES.json not found in {bank_dir}")
    with open(sources_path, "r", encoding="utf-8") as f:
        sources = json.load(f)

    probes_path = os.path.join(bank_dir, "probes.json")
    probes = {}
    if os.path.exists(probes_path):
        with open(probes_path, "r", encoding="utf-8") as f:
            probes = json.load(f)

    responses_path = os.path.join(bank_dir, "responses.json")
    responses = {}
    if os.path.exists(responses_path):
        with open(responses_path, "r", encoding="utf-8") as f:
            responses = json.load(f)

    items: List[BankItem] = []
    seen_ids: Set[str] = set()

    for filename in sorted(os.listdir(bank_dir)):
        if not filename.endswith(".json") or filename in ("SOURCES.json", "probes.json", "responses.json"):
            continue

        file_path = os.path.join(bank_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if not isinstance(raw_data, list):
            raise ValueError(f"Module file {filename} must contain a JSON list of items.")

        for raw_item in raw_data:
            item_id = raw_item.get("id")
            if not item_id:
                raise ValueError(f"Missing id in item in {filename}")
            if item_id in seen_ids:
                raise ValueError(f"Duplicate question bank id '{item_id}' in {filename}")
            seen_ids.add(item_id)

            module = raw_item.get("module")
            if module not in VALID_MODULES:
                raise ValueError(f"Invalid module '{module}' in item '{item_id}'")

            slot = raw_item.get("slot")
            if not slot:
                raise ValueError(f"Missing slot in item '{item_id}'")

            # Check templates in 3 languages
            for lang_key in ("template_en", "template_ur", "template_roman_ur"):
                val = raw_item.get(lang_key)
                if not val or not isinstance(val, str) or not val.strip():
                    raise ValueError(f"Missing or empty template '{lang_key}' in item '{item_id}'")

            why_text = raw_item.get("why_text")
            if not why_text or not isinstance(why_text, str) or not why_text.strip():
                raise ValueError(f"Missing or empty why_text in item '{item_id}'")

            answer_type = raw_item.get("answer_type")
            if answer_type not in VALID_ANSWER_TYPES:
                raise ValueError(f"Invalid answer_type '{answer_type}' in item '{item_id}'")

            p_class = raw_item.get("priority_class")
            if p_class not in VALID_PRIORITY_CLASSES:
                raise ValueError(f"Invalid priority_class '{p_class}' in item '{item_id}'")

            can_raise = bool(raw_item.get("can_raise_level", False))
            rule_id = raw_item.get("rule_id")
            if can_raise and not rule_id:
                raise ValueError(f"Item '{item_id}' has can_raise_level=True but rule_id is empty/missing")

            source_key = raw_item.get("source")
            if not source_key or source_key not in sources:
                raise ValueError(f"Item '{item_id}' references unknown or missing source key '{source_key}'")

            item = BankItem(
                id=item_id,
                module=module,
                slot=slot,
                why_text=why_text.strip(),
                template_en=raw_item["template_en"].strip(),
                template_ur=raw_item["template_ur"].strip(),
                template_roman_ur=raw_item["template_roman_ur"].strip(),
                answer_type=answer_type,
                choices=raw_item.get("choices"),
                valid_range=raw_item.get("valid_range"),
                unit_options=raw_item.get("unit_options"),
                requires=raw_item.get("requires") or {},
                priority_class=p_class,
                can_raise_level=can_raise,
                rule_id=rule_id,
                source=source_key,
                review_status=raw_item.get("review_status", "proposed, not reviewed by a clinician"),
                bank_version=raw_item.get("bank_version", "3.0"),
            )
            items.append(item)

    return QuestionBank(items, sources, probes, responses)


_GLOBAL_BANK: Optional[QuestionBank] = None


def get_default_bank() -> QuestionBank:
    global _GLOBAL_BANK
    if _GLOBAL_BANK is None:
        _GLOBAL_BANK = load_question_bank()
    return _GLOBAL_BANK
