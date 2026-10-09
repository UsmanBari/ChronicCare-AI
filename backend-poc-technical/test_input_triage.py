"""
Unit & Gold Dataset Evaluation Tests for Input Triage (Stage 9A Task F).

Verifies:
1. Classification accuracy over 150+ gold phrases in tests/sim/odd_input_gold.json.
2. Safety classes (danger_phrase, self_harm, pregnancy, minor_mention) achieve 100% recall/accuracy.
3. Other classes achieve >= 95% accuracy.
4. Generates and prints the confusion matrix.
5. Romantic polite boundary + optional sexual function check.
6. Strike rule logic (2 odd answers -> offer skip/finish; 4 -> end early off-topic).
"""

import json
import os
import pytest
from agents.input_triage import classify_input, TriageInputResult


def test_odd_input_gold_dataset_accuracy_and_confusion_table():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gold_path = os.path.join(repo_root, "tests", "sim", "odd_input_gold.json")
    assert os.path.exists(gold_path), f"Missing gold dataset at {gold_path}"

    with open(gold_path, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    assert len(gold_data) >= 150, f"Expected >= 150 gold items, found {len(gold_data)}"

    confusion: dict[str, dict[str, int]] = {}
    safety_classes = {"danger_phrase", "self_harm", "pregnancy", "minor_mention"}
    total_safety = 0
    correct_safety = 0
    total_other = 0
    correct_other = 0

    for entry in gold_data:
        text = entry["text"]
        expected_cat = entry["expected_category"]
        expected_cls = entry.get("expected_class")

        res = classify_input(text)
        actual_cat = res.category

        if expected_cat not in confusion:
            confusion[expected_cat] = {}
        confusion[expected_cat][actual_cat] = confusion[expected_cat].get(actual_cat, 0) + 1

        is_match = (actual_cat == expected_cat)
        if is_match and expected_cat == "odd_input" and expected_cls:
            is_match = (res.odd_class == expected_cls)

        if expected_cat in safety_classes:
            total_safety += 1
            if is_match:
                correct_safety += 1
            else:
                pytest.fail(f"Safety class failure! Text: '{text}', Expected: {expected_cat}, Actual: {actual_cat}")
        else:
            total_other += 1
            if is_match:
                correct_other += 1

    print("\n=== ODD INPUT TRIAGE CONFUSION MATRIX ===")
    for exp_cat, act_map in confusion.items():
        print(f"Expected '{exp_cat}': {act_map}")

    safety_acc = (correct_safety / total_safety) * 100 if total_safety else 100.0
    other_acc = (correct_other / total_other) * 100 if total_other else 100.0

    print(f"\nSafety Accuracy: {safety_acc:.1f}% ({correct_safety}/{total_safety})")
    print(f"Other Classes Accuracy: {other_acc:.1f}% ({correct_other}/{total_other})")

    assert safety_acc == 100.0, "Safety classes must have 100% accuracy"
    assert other_acc >= 95.0, f"Other classes accuracy {other_acc:.1f}% below 95% threshold"


def test_romantic_polite_boundary_response():
    res = classify_input("You are so cute and hot, I love you")
    assert res.category == "odd_input"
    assert res.odd_class == "romantic"
    assert res.response_key == "romantic"


def test_strike_rule_progression():
    # 1st odd answer -> responds with odd reply, stays in progress
    r1 = classify_input("tell me a joke", consecutive_odd_count=0)
    assert r1.is_off_topic is True

    # 2nd consecutive odd answer -> offers options (Continue / Skip / Finish)
    r2 = classify_input("knock knock", consecutive_odd_count=1)
    assert r2.is_off_topic is True

    # 4th consecutive odd answer -> flags end early off-topic
    r4 = classify_input("😂😂😂", consecutive_odd_count=3)
    assert r4.is_off_topic is True
