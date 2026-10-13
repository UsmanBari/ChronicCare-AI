import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend-poc-technical"
sys.path.insert(0, str(BACKEND_DIR))

from agents.input_triage import screen_multilingual_danger_phrases


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/eval_phrase_set.py <json_file>")
        sys.exit(1)

    json_path = Path(sys.argv[1])

    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as file:
        items = json.load(file)

    tp = 0
    fn = 0
    fp = 0
    tn = 0
    failures = []

    for item in items:
        text = item["text"]
        expected = item["expected_danger"]

        detected, category = screen_multilingual_danger_phrases(text)

        if expected and detected:
            tp += 1
        elif expected and not detected:
            fn += 1
            failures.append((item, detected, category))
        elif not expected and detected:
            fp += 1
            failures.append((item, detected, category))
        else:
            tn += 1

    sensitivity = tp / (tp + fn) if (tp + fn) else 0
    specificity = tn / (tn + fp) if (tn + fp) else 0

    print(f"Total: {len(items)}")
    print(f"TP: {tp}")
    print(f"FN: {fn}")
    print(f"FP: {fp}")
    print(f"TN: {tn}")
    print(f"Sensitivity: {sensitivity:.2%}")
    print(f"Specificity: {specificity:.2%}")

    print("\nFailing items:")

    if not failures:
        print("None")
    else:
        for item, detected, category in failures:
            print(
                f'- Text: "{item["text"]}" | '
                f'Category: {item["category"]} | '
                f'Expected: {item["expected_danger"]} | '
                f'Detected: {detected} | '
                f'Detected category: {category}'
            )


if __name__ == "__main__":
    main()