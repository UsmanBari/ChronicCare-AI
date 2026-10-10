import json
import sys
from collections import defaultdict
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path("backend-poc-technical").resolve()))
from agents.input_triage import classify_input

def main():
    odd_file = Path("tests/sim/odd_input_gold.json")
    with open(odd_file, "r", encoding="utf-8") as f:
        odd_data = json.load(f)

    matrix = defaultdict(lambda: defaultdict(int))
    classes = set()

    for row in odd_data:
        text = row["text"]
        exp_class = row.get("expected_class")
        exp_cat = row.get("expected_category")

        if exp_class and exp_class != "none":
            gold = exp_class
        elif exp_cat and exp_cat not in ("none", "minor_mention"):
            gold = exp_cat
        else:
            gold = "normal_clinical"

        res = classify_input(text)
        pred_cat = res.category
        pred_class = res.odd_class

        if pred_class:
            pred = pred_class
        elif pred_cat in ("danger_phrase", "self_harm", "pregnancy"):
            pred = pred_cat
        else:
            pred = "normal_clinical"

        matrix[gold][pred] += 1
        classes.add(gold)
        classes.add(pred)

    sorted_classes = sorted(list(classes))
    print(f"Total samples evaluated: {len(odd_data)}")
    print("\n=== CONFUSION MATRIX (Rows: Gold, Cols: Predicted) ===")
    
    header = f"{'Gold \\ Pred':<28}" + "".join(f"{c[:10]:>12}" for c in sorted_classes)
    print(header)
    print("-" * len(header))
    for g in sorted_classes:
        row_str = f"{g:<28}" + "".join(f"{matrix[g][c]:>12}" for c in sorted_classes)
        print(row_str)

    print("\n=== PER-CLASS PRECISION & RECALL ===")
    print(f"{'Class':<28} {'TP':>5} {'FP':>5} {'FN':>5} {'Precision':>10} {'Recall':>10}")
    print("-" * 72)
    for c in sorted_classes:
        tp = matrix[c][c]
        fp = sum(matrix[other][c] for other in sorted_classes if other != c)
        fn = sum(matrix[c][other] for other in sorted_classes if other != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        print(f"{c:<28} {tp:>5} {fp:>5} {fn:>5} {prec:>10.2%} {rec:>10.2%}")

if __name__ == "__main__":
    main()
