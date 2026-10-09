"""
Honest Confusion Matrix & Per-Class Evaluation Script (Stage 9A-3 Task F).
Evaluates classify_input over tests/sim/odd_input_gold.json including the 'none' normal clinical class.
Prints the complete confusion matrix, precision, recall, and failing items by name.
"""

import os
import sys
import json
from collections import defaultdict

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend-poc-technical")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from agents.input_triage import classify_input

def run_confusion_analysis():
    gold_path = os.path.join(REPO_ROOT, "tests", "sim", "odd_input_gold.json")
    with open(gold_path, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    # Normalize classes
    # Categories: danger_phrase, self_harm, pregnancy, minor_mention, none
    # Odd classes: chitchat_joke, romantic, abuse, gibberish_emoji_empty,
    # medical_advice_dose_request, fear_prognosis, about_bot, third_party_report, prompt_injection, non_answer

    CLASSES = [
        "danger_phrase",
        "self_harm",
        "pregnancy",
        "minor_mention",
        "prompt_injection",
        "romantic",
        "chitchat_joke",
        "abuse",
        "gibberish_emoji_empty",
        "medical_advice_dose_request",
        "fear_prognosis",
        "about_bot",
        "third_party_report",
        "none",
    ]

    matrix = {c: {pred: 0 for pred in CLASSES} for c in CLASSES}
    failures = []

    for entry in gold_data:
        text = entry["text"]
        author = entry.get("author")
        if not author:
            failures.append({"text": text, "error": "Missing author field"})

        exp_cat = entry.get("expected_category")
        exp_cls = entry.get("expected_class") or exp_cat
        if exp_cat in ("none", "normal_clinical"):
            true_class = "none"
        elif exp_cat in ("danger_phrase", "self_harm", "pregnancy", "minor_mention"):
            true_class = exp_cat
        else:
            true_class = exp_cls if exp_cls in CLASSES else "none"

        res = classify_input(text)
        if res.is_emergency and res.category == "danger_phrase":
            pred_class = "danger_phrase"
        elif res.is_urgent_safety or res.category == "self_harm":
            pred_class = "self_harm"
        elif res.category == "pregnancy":
            pred_class = "pregnancy"
        elif res.category == "minor_mention":
            pred_class = "minor_mention"
        elif res.category == "odd_input":
            pred_class = res.odd_class if res.odd_class in CLASSES else "none"
        else:
            pred_class = "none"

        if true_class in matrix and pred_class in matrix[true_class]:
            matrix[true_class][pred_class] += 1
        
        if true_class != pred_class:
            failures.append({
                "text": text,
                "language": entry.get("language"),
                "true_class": true_class,
                "pred_class": pred_class,
            })

    print("# Honest Confusion Matrix and Per-Class Evaluation Table\n")
    print(f"Total phrases evaluated: {len(gold_data)}")
    print(f"Classes evaluated: {len(CLASSES)}\n")

    # Markdown Confusion Matrix
    header = "| True Class \\ Predicted | " + " | ".join(CLASSES) + " | Total |"
    sep = "|:---|:" + ":|:".join(["---"] * len(CLASSES)) + ":|:---:|"
    print(header)
    print(sep)

    for true_c in CLASSES:
        row = [f"`{true_c}`"]
        total_true = sum(matrix[true_c].values())
        for pred_c in CLASSES:
            val = matrix[true_c][pred_c]
            row.append(str(val) if val > 0 else "-")
        row.append(str(total_true))
        print("| " + " | ".join(row) + " |")

    print("\n## Per-Class Precision, Recall, and F1-Score\n")
    print("| Class | Support | TP | FP | FN | Precision | Recall | F1-Score | Status |")
    print("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")

    for c in CLASSES:
        tp = matrix[c][c]
        fn = sum(matrix[c][other] for other in CLASSES if other != c)
        fp = sum(matrix[other][c] for other in CLASSES if other != c)
        support = tp + fn
        
        prec = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        rec = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 1.0

        is_safety = c in ("danger_phrase", "self_harm", "pregnancy", "minor_mention")
        if is_safety:
            status = "PASS (100% Safety)" if rec == 1.0 and prec == 1.0 else "FAIL (<100% Safety)"
        else:
            status = "PASS (>=95%)" if rec >= 0.95 and prec >= 0.95 else "FINDING (<95%)"

        print(f"| `{c}` | {support} | {tp} | {fp} | {fn} | {prec:.3f} | {rec:.3f} | {f1:.3f} | {status} |")

    print(f"\nTotal misclassifications / failures: {len(failures)}")
    if failures:
        print("\nFailing Phrases by Name & Class:")
        for f in failures:
            print(f"- Text: \"{f['text']}\" (Lang: {f.get('language')}) | True: `{f['true_class']}` -> Predicted: `{f['pred_class']}`")

if __name__ == "__main__":
    run_confusion_analysis()
