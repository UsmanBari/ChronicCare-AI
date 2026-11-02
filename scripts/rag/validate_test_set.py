#!/usr/bin/env python3
"""
Validation script for RAG retrieval test set (docs/rag/retrieval_test_set.json).

Enforces schema compliance, unique IDs, category balances, 3-language completeness,
Urdu unicode script validation, and minimum safety redirect coverage.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_KEYS = {
    "id",
    "condition",
    "topic",
    "question_en",
    "question_ur",
    "question_roman_ur",
    "expected_source",
    "expected_source_status",
    "answer_points",
    "must_not",
    "kind",
}

ALLOWED_CONDITIONS = {"diabetes", "hypertension", "both"}
ALLOWED_KINDS = {"explain", "safety_redirect"}
ALLOWED_SOURCE_STATUSES = {"TO CONFIRM against Usman's corpus", "UNSURE"}

URDU_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def validate_retrieval_test_set(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Retrieval test set file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise TypeError(f"Top-level JSON structure must be a list, got {type(data).__name__}")

    total = len(data)
    if total != 60:
        raise ValueError(f"Expected exactly 60 items in retrieval test set, found {total}")

    seen_ids: set[str] = set()
    condition_counts: dict[str, int] = {"diabetes": 0, "hypertension": 0, "both": 0}
    kind_counts: dict[str, int] = {"explain": 0, "safety_redirect": 0}

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise TypeError(f"Item at index {idx} is not a JSON object")

        # Key presence
        missing_keys = REQUIRED_KEYS - set(item.keys())
        if missing_keys:
            raise ValueError(f"Item #{idx} ({item.get('id', 'unknown')}) missing required keys: {sorted(missing_keys)}")

        item_id = item["id"]
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError(f"Item #{idx} has invalid id: {item_id!r}")
        if item_id in seen_ids:
            raise ValueError(f"Duplicate id found: {item_id}")
        seen_ids.add(item_id)

        # Condition
        cond = item["condition"]
        if cond not in ALLOWED_CONDITIONS:
            raise ValueError(f"Item {item_id} has invalid condition: {cond!r}. Allowed: {ALLOWED_CONDITIONS}")
        condition_counts[cond] += 1

        # Kind
        kind = item["kind"]
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"Item {item_id} has invalid kind: {kind!r}. Allowed: {ALLOWED_KINDS}")
        kind_counts[kind] += 1

        # Source status
        status = item["expected_source_status"]
        if status not in ALLOWED_SOURCE_STATUSES:
            raise ValueError(f"Item {item_id} has invalid expected_source_status: {status!r}. Allowed: {ALLOWED_SOURCE_STATUSES}")

        # String fields non-empty
        for str_key in ["topic", "question_en", "question_ur", "question_roman_ur", "expected_source", "must_not"]:
            val = item[str_key]
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"Item {item_id} field '{str_key}' must be a non-empty string")

        # Urdu script verification
        if not URDU_ARABIC_RE.search(item["question_ur"]):
            raise ValueError(f"Item {item_id} 'question_ur' does not contain Arabic/Urdu unicode characters: {item['question_ur']!r}")

        # Answer points: 2-4 items
        ap = item["answer_points"]
        if not isinstance(ap, list) or not (2 <= len(ap) <= 4):
            raise ValueError(f"Item {item_id} 'answer_points' must be a list of 2 to 4 items, got {len(ap) if isinstance(ap, list) else type(ap)}")
        for p_idx, point in enumerate(ap):
            if not isinstance(point, str) or not point.strip():
                raise ValueError(f"Item {item_id} answer point #{p_idx} is empty or not string")

    # Balancing constraints
    if condition_counts["diabetes"] != 25:
        raise ValueError(f"Condition 'diabetes' count must be exactly 25, got {condition_counts['diabetes']}")
    if condition_counts["hypertension"] != 25:
        raise ValueError(f"Condition 'hypertension' count must be exactly 25, got {condition_counts['hypertension']}")
    if condition_counts["both"] != 10:
        raise ValueError(f"Condition 'both' count must be exactly 10, got {condition_counts['both']}")

    if kind_counts["safety_redirect"] < 12:
        raise ValueError(f"Kind 'safety_redirect' count must be >= 12, got {kind_counts['safety_redirect']}")

    summary = {
        "total_items": total,
        "conditions": condition_counts,
        "kinds": kind_counts,
    }
    return summary


def print_summary_table(summary: dict[str, Any]) -> None:
    print("=" * 60)
    print("       RAG RETRIEVAL TEST SET VALIDATION SUMMARY       ")
    print("=" * 60)
    print(f" Total Items Checked : {summary['total_items']}")
    print("-" * 60)
    print(" Conditions Distribution:")
    for cond, count in summary["conditions"].items():
        print(f"   - {cond.capitalize():<15}: {count:>3} / 60")
    print("-" * 60)
    print(" Kind Distribution:")
    for k, count in summary["kinds"].items():
        print(f"   - {k:<15}: {count:>3} / 60")
    print("=" * 60)
    print(" Status: VALIDATION PASSED (All clinical schema constraints met)")
    print("=" * 60)


def main() -> None:
    default_path = Path(__file__).resolve().parents[2] / "docs" / "rag" / "retrieval_test_set.json"
    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path

    try:
        summary = validate_retrieval_test_set(target_path)
        print_summary_table(summary)
    except (FileNotFoundError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Validation Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
