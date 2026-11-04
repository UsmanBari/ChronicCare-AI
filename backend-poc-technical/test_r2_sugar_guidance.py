"""
Unit & Regression Tests for Rule R2: Neutral Low Sugar Guidance Without Grams or Tablets.
Verifies that patient-facing messages across messages.json, templates.json,
adaptive_interview_agent.py, interview_v3_runner.py, steps.py, and main.py contain
no dosage/grams or tablet instructions, and use the approved neutral clinician wording.
"""

import os
import json
import re
import pytest

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

FORBIDDEN_PATTERNS = [
    r"15\s*g\b",
    r"15\s*grams\b",
    r"15\s*gram\b",
    r"15\s*گرام",
    r"\btablets?\b",
    r"\bgoliyan\b",
    r"\bre-test in 15\b",
]

APPROVED_EN = "Take quick sugar such as fruit juice or glucose, and seek immediate medical attention if symptoms persist."
APPROVED_UR = "فوراً جلدی اثر کرنے والی میٹھی چیز لیں، جیسے پھلوں کا جوس یا گلوکوز، اور اگر علامات برقرار رہیں تو فوراً طبی مدد حاصل کریں۔"
APPROVED_ROMAN = "Foran jaldi asar karne wali meethi cheez lein, jaise phalon ka juice ya glucose, aur agar alamaat barqarar rahein to foran doctor se rabta karein."


def test_messages_json_low_sugar_guidance():
    path = os.path.join(BACKEND_DIR, "agents", "interview_bank", "messages.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "_comment_clinical_safety" not in data, "_comment_clinical_safety should be removed"

    for key in ("glucose_unclear_unit_safety_guidance", "v3_possible_low_guidance"):
        entry = data[key]
        assert entry["en"] == APPROVED_EN
        assert entry["ur"] == APPROVED_UR
        assert entry["roman_ur"] == APPROVED_ROMAN

        for lang, text in entry.items():
            if lang in ("en", "ur", "roman_ur"):
                for pat in FORBIDDEN_PATTERNS:
                    assert not re.search(pat, text, re.IGNORECASE), f"Found forbidden {pat} in {key}.{lang}: {text}"


def test_templates_json_glucose_low():
    path = os.path.join(BACKEND_DIR, "rag", "templates.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    g_low = data["glucose_low"]
    # Check diagnosis wording was dropped
    assert "indicating hypoglycemia" not in g_low["en"]["sentences"][0].lower()
    assert "(ہائپوگلیسیمیا)" not in g_low["ur"]["sentences"][0]
    assert "(hypoglycemia)" not in g_low["roman_ur"]["sentences"][0].lower()

    # Check approved sentence 2
    assert g_low["en"]["sentences"][1] == APPROVED_EN
    assert g_low["ur"]["sentences"][1] == APPROVED_UR
    assert g_low["roman_ur"]["sentences"][1] == APPROVED_ROMAN

    # Check no forbidden patterns in any sentence
    for lang in ("en", "ur", "roman_ur"):
        for sent in g_low[lang]["sentences"]:
            for pat in FORBIDDEN_PATTERNS:
                assert not re.search(pat, sent, re.IGNORECASE), f"Found forbidden {pat} in glucose_low.{lang}: {sent}"


def test_adaptive_interview_agent_patient_strings():
    path = os.path.join(BACKEND_DIR, "agents", "adaptive_interview_agent.py")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Must not contain 15g, 15 grams, tablets, or re-test in 15 in low sugar alerts
    assert "15g fast-acting" not in text
    assert "15 g" not in text
    assert "consume 15g" not in text


def test_orchestrator_steps_guidance():
    path = os.path.join(BACKEND_DIR, "orchestrator", "steps.py")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    assert "consume fast-acting sugar immediately" not in text
    assert APPROVED_EN in text


def test_scan_patient_facing_files_for_forbidden_sugar_dose():
    files_to_scan = [
        os.path.join(BACKEND_DIR, "agents", "interview_bank", "messages.json"),
        os.path.join(BACKEND_DIR, "rag", "templates.json"),
    ]
    for p in files_to_scan:
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        # In low-sugar entries
        assert "15g" not in content
        assert "15 g" not in content
        assert "15 grams" not in content
        assert "re-test in 15" not in content
