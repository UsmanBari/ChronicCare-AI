"""Evaluate a danger-phrase JSON set against the multilingual triage screen."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend-poc-technical"
sys.path.insert(0, str(BACKEND_ROOT))

from agents.input_triage import screen_multilingual_danger_phrases


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: python {Path(sys.argv[0]).name} <phrase-set.json>")
        return 2

    phrase_path = Path(sys.argv[1])
    if not phrase_path.is_absolute():
        phrase_path = Path.cwd() / phrase_path

    with phrase_path.open(encoding="utf-8") as phrase_file:
        rows = json.load(phrase_file)

    counts = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
    failures = []

    for index, row in enumerate(rows, start=1):
        expected = bool(row["expected_danger"])
        detected, category = screen_multilingual_danger_phrases(row["text"])

        if expected and detected:
            counts["TP"] += 1
        elif expected and not detected:
            counts["FN"] += 1
            failures.append((index, row, detected, category))
        elif not expected and detected:
            counts["FP"] += 1
            failures.append((index, row, detected, category))
        else:
            counts["TN"] += 1

    positive_total = counts["TP"] + counts["FN"]
    negative_total = counts["TN"] + counts["FP"]
    sensitivity = counts["TP"] / positive_total if positive_total else 0.0
    specificity = counts["TN"] / negative_total if negative_total else 0.0

    print(f"Total: {len(rows)}")
    print(f"TP: {counts['TP']}")
    print(f"FN: {counts['FN']}")
    print(f"FP: {counts['FP']}")
    print(f"TN: {counts['TN']}")
    print(f"Sensitivity: {sensitivity:.2%}")
    print(f"Specificity: {specificity:.2%}")

    if failures:
        print("\nFailures:")
        for index, row, detected, category in failures:
            print(
                f"{index}. expected_danger={row['expected_danger']} "
                f"detected={detected} category={row['category']} "
                f"actual_category={category}: {row['text']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
