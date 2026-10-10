"""
Unit & Gold Dataset Evaluation Tests for Input Triage (Stage 9A Task F & Stage 9A-2 Tasks A/B).

Verifies:
1. Classification accuracy over 150+ gold phrases in tests/sim/odd_input_gold.json.
2. Safety classes (danger_phrase, self_harm, pregnancy, minor_mention) achieve 100% recall/accuracy.
3. Other classes achieve >= 95% accuracy.
4. Generates and prints the confusion matrix and per-class metrics.
5. All gold dataset files contain explicit author attribution ('author': 'engineer').
6. Authoritative danger screen parity: every phrase caught by base run_stage1_red_flag_screen is caught by classify_input.
"""

import json
import os
import pytest
from agents.input_triage import classify_input, TriageInputResult
from agents.adaptive_interview_agent import run_stage1_red_flag_screen as _run_base_screen


def test_gold_files_have_author_field():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    danger_gold_path = os.path.join(repo_root, "tests", "sim", "danger_phrases_gold.json")
    odd_gold_path = os.path.join(repo_root, "tests", "sim", "odd_input_gold.json")

    assert os.path.exists(danger_gold_path), f"Missing {danger_gold_path}"
    assert os.path.exists(odd_gold_path), f"Missing {odd_gold_path}"

    with open(danger_gold_path, "r", encoding="utf-8") as f:
        danger_data = json.load(f)
    for entry in danger_data:
        assert "author" in entry, f"Missing author in danger gold: {entry}"
        assert entry["author"] == "engineer"

    with open(odd_gold_path, "r", encoding="utf-8") as f:
        odd_data = json.load(f)
    for entry in odd_data:
        assert "author" in entry, f"Missing author in odd gold: {entry}"
        assert entry["author"] == "engineer"


def test_authoritative_danger_screen_parity():
    # Verify that classify_input delegates authoritatively to run_stage1_red_flag_screen
    test_phrases = [
        "I have crushing chest pain right now",
        "cannot breathe at all",
        "confused and slurred speech",
        "passed out on the floor",
        "one side weak and face drooping",
        "vomiting non-stop with high sugar",
        "worst headache of my life",
        "sudden vision loss and went blind",
        "سینے میں درد ہو رہا ہے",
        "بے ہوش ہو گیا تھا",
    ]
    for phrase in test_phrases:
        base_flag, base_cat = _run_base_screen(phrase)
        assert base_flag is True, f"Base screen failed to flag: {phrase}"

        triage_res = classify_input(phrase)
        assert triage_res.is_emergency is True, f"classify_input failed to flag emergency for: {phrase}"
        assert triage_res.category == "danger_phrase"


def test_odd_input_gold_dataset_accuracy_and_confusion_table():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gold_path = os.path.join(repo_root, "tests", "sim", "odd_input_gold.json")
    assert os.path.exists(gold_path), f"Missing gold dataset at {gold_path}"

    with open(gold_path, "r", encoding="utf-8") as f:
        gold_data = json.load(f)

    assert len(gold_data) >= 150, f"Expected >= 150 gold items, found {len(gold_data)}"

    confusion: dict[str, dict[str, int]] = {}
    classes_tp: dict[str, int] = {}
    classes_fp: dict[str, int] = {}
    classes_fn: dict[str, int] = {}

    safety_classes = {"danger_phrase", "self_harm", "pregnancy", "minor_mention"}
    total_safety = 0
    correct_safety = 0
    total_other = 0
    correct_other = 0

    for entry in gold_data:
        text = entry["text"]
        expected_cat = entry["expected_category"]
        expected_cls = entry.get("expected_class") or expected_cat

        res = classify_input(text)
        actual_cat = res.category
        actual_cls = res.odd_class if actual_cat == "odd_input" and res.odd_class else actual_cat

        if expected_cls not in confusion:
            confusion[expected_cls] = {}
        confusion[expected_cls][actual_cls] = confusion[expected_cls].get(actual_cls, 0) + 1

        is_match = (actual_cat == expected_cat) or (expected_cat == "none" and actual_cat == "normal_clinical")
        if is_match and expected_cat == "odd_input" and entry.get("expected_class"):
            is_match = (res.odd_class == entry["expected_class"])

        if is_match:
            classes_tp[expected_cls] = classes_tp.get(expected_cls, 0) + 1
        else:
            classes_fn[expected_cls] = classes_fn.get(expected_cls, 0) + 1
            classes_fp[actual_cls] = classes_fp.get(actual_cls, 0) + 1

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
    print(f"{'Expected Class':<25} | {'Actual Counts'}")
    print("-" * 60)
    for exp_cls, act_map in sorted(confusion.items()):
        act_str = ", ".join([f"{k}: {v}" for k, v in act_map.items()])
        print(f"{exp_cls:<25} | {act_str}")

    safety_acc = (correct_safety / total_safety) * 100 if total_safety else 100.0
    other_acc = (correct_other / total_other) * 100 if total_other else 100.0

    print(f"\nSafety Recall/Accuracy: {safety_acc:.1f}% ({correct_safety}/{total_safety})")
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

    # 2nd consecutive odd answer -> offers options
    r2 = classify_input("knock knock", consecutive_odd_count=1)
    assert r2.is_off_topic is True

    # 4th consecutive odd answer -> flags end early off-topic
    r4 = classify_input("😂😂😂", consecutive_odd_count=3)
    assert r4.is_off_topic is True


def test_weather_and_symptoms_not_swallowed_by_romantic():
    # Weather and symptom statements containing 'so hot' must remain normal clinical
    s1 = classify_input("It is so hot today and I feel dizzy")
    assert s1.category == "normal_clinical"
    assert s1.odd_class is None

    s2 = classify_input("so hot outside, sugar 110")
    assert s2.category == "normal_clinical"
    assert s2.odd_class is None

    s3 = classify_input("my feet feel so hot and burning")
    assert s3.category == "normal_clinical"
    assert s3.odd_class is None

    # Third party compliment on baby must not be classified as romantic towards bot
    s4 = classify_input("the baby is so cute")
    assert s4.category == "normal_clinical"
    assert s4.odd_class is None

    # Bot compliments must be classified as romantic
    s5 = classify_input("you are so cute")
    assert s5.category == "odd_input"
    assert s5.odd_class == "romantic"


def test_non_medication_questions_not_classified_as_dose_request():
    # Lifestyle and administrative queries must not trigger dose change advice
    s1 = classify_input("Can I skip breakfast?")
    assert s1.category == "normal_clinical"
    assert s1.odd_class is None

    s2 = classify_input("Can I change my appointment?")
    assert s2.category == "normal_clinical"
    assert s2.odd_class is None

    # Medication discontinuation query must trigger advice request
    s3 = classify_input("can I stop taking metformin since my sugar is normal")
    assert s3.category == "odd_input"
    assert s3.odd_class == "medical_advice_dose_request"
    assert s3.needs_clinician_flag is True
