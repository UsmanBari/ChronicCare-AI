"""
Part C: Independent Urdu Phrase Test Runner (Hassaan).
Evaluates input_triage against tests/sim/danger_phrases_independent_hassaan_ur.json
without modifying input_triage.py.
Computes sensitivity, specificity, FNR, FPR, and logs every FN and FP.
"""

from __future__ import annotations

import json
import os
import sys

# Ensure backend agents can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend-poc-technical"))

from agents.input_triage import classify_input


def run_evaluation():
    input_file = os.path.join(
        os.path.dirname(__file__), "..", "tests", "sim", "danger_phrases_independent_hassaan_ur.json"
    )
    with open(input_file, "r", encoding="utf-8") as f:
        phrases = json.load(f)

    tp = fp = tn = fn = 0
    false_negatives = []
    false_positives = []
    results = []

    for idx, p in enumerate(phrases, 1):
        text = p["text"]
        expected = p["expected_danger"]
        category = p["category"]
        res = classify_input(text)
        actual_danger = (res.category == "danger_phrase" or res.is_emergency)

        if expected and actual_danger:
            tp += 1
            status = "TP"
        elif not expected and not actual_danger:
            tn += 1
            status = "TN"
        elif expected and not actual_danger:
            fn += 1
            status = "FN"
            false_negatives.append((idx, category, text, res.category, res.trigger_detail))
        else:
            fp += 1
            status = "FP"
            false_positives.append((idx, category, text, res.category, res.trigger_detail))

        results.append({
            "id": idx,
            "category": category,
            "expected": expected,
            "actual": actual_danger,
            "status": status,
            "detected_cat": res.trigger_detail,
            "text": text,
        })

    total = len(phrases)
    actual_pos = tp + fn
    actual_neg = tn + fp

    sens = (tp / actual_pos) * 100 if actual_pos else 0
    spec = (tn / actual_neg) * 100 if actual_neg else 0
    fnr = (fn / actual_pos) * 100 if actual_pos else 0
    fpr = (fp / actual_neg) * 100 if actual_neg else 0

    print("================================================================================")
    print("INDEPENDENT URDU PHRASE TEST RESULTS (HASSAAN)")
    print("================================================================================")
    print(f"Total phrases: {total}")
    print(f"True Positives (TP):  {tp}")
    print(f"True Negatives (TN):  {tn}")
    print(f"False Negatives (FN): {fn}")
    print(f"False Positives (FP): {fp}")
    print(f"Sensitivity:          {sens:.1f}%")
    print(f"Specificity:          {spec:.1f}%")
    print(f"False Negative Rate:  {fnr:.1f}%")
    print(f"False Positive Rate:  {fpr:.1f}%")

    print("\nFalse Negatives (FN):")
    if not false_negatives:
        print("  None")
    for f_item in false_negatives:
        print(f"  [{f_item[0]}] {f_item[1]}: \"{f_item[2]}\" -> classified as {f_item[3]} (danger_cat={f_item[4]})")

    print("\nFalse Positives (FP):")
    if not false_positives:
        print("  None")
    for f_item in false_positives:
        print(f"  [{f_item[0]}] {f_item[1]}: \"{f_item[2]}\" -> classified as {f_item[3]} (danger_cat={f_item[4]})")

    # Generate Markdown documentation
    md_content = f"""# Independent Urdu-Script Phrase Test Results (Hassaan)

**Date:** 2026-10-29  
**Evaluator:** Hassaan Mudassar  
**Test Set:** `tests/sim/danger_phrases_independent_hassaan_ur.json`  
**Total Phrases:** {total} (20 Expected Danger, 10 Expected Safe Look-alikes)  

> **Clinical Safety Invariant:**  
> `input_triage` was not changed today; any failure is logged for Usman to decide on Week 3.

---

## 1. Summary Metrics

| Metric | Formula | Value | Percentage |
|---|---|---|---|
| **True Positives (TP)** | Correctly identified red flags | {tp} / {actual_pos} | - |
| **True Negatives (TN)** | Correctly identified safe look-alikes | {tn} / {actual_neg} | - |
| **False Negatives (FN)** | Missed red flags (Safety risk) | {fn} / {actual_pos} | - |
| **False Positives (FP)** | False alarms on safe phrases | {fp} / {actual_neg} | - |
| **Sensitivity** | TP / (TP + FN) | {tp}/{actual_pos} | **{sens:.1f}%** |
| **Specificity** | TN / (TN + FP) | {tn}/{actual_neg} | **{spec:.1f}%** |
| **False Negative Rate (FNR)** | FN / (TP + FN) | {fn}/{actual_pos} | **{fnr:.1f}%** |
| **False Positive Rate (FPR)** | FP / (TN + FP) | {fp}/{actual_neg} | **{fpr:.1f}%** |

---

## 2. False Negatives (Missed Red Flags)
"""
    if not false_negatives:
        md_content += "\n*Zero False Negatives encountered.*\n"
    else:
        md_content += "\n| ID | Category | Patient Phrase | Actual Classification | Detected Category |\n|---|---|---|---|---|\n"
        for f_item in false_negatives:
            md_content += f"| {f_item[0]} | `{f_item[1]}` | {f_item[2]} | `{f_item[3]}` | `{f_item[4]}` |\n"

    md_content += "\n## 3. False Positives (Safe Look-alikes Escalated)\n"
    if not false_positives:
        md_content += "\n*Zero False Positives encountered.*\n"
    else:
        md_content += "\n| ID | Category | Patient Phrase | Actual Classification | Detected Category |\n|---|---|---|---|---|\n"
        for f_item in false_positives:
            md_content += f"| {f_item[0]} | `{f_item[1]}` | {f_item[2]} | `{f_item[3]}` | `{f_item[4]}` |\n"

    md_content += "\n## 4. Complete Test Results Breakdown\n\n| ID | Category | Expected Danger | Actual Danger | Status | Phrase |\n|---|---|---|---|---|---|\n"
    for r in results:
        md_content += f"| {r['id']} | `{r['category']}` | {r['expected']} | {r['actual']} | **{r['status']}** | {r['text']} |\n"

    md_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md"
    )
    with open(md_path, "w", encoding="utf-8") as f_out:
        f_out.write(md_content)

    print(f"\nSaved report to {md_path}")


if __name__ == "__main__":
    run_evaluation()
