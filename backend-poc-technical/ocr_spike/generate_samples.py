"""
Deterministic Synthetic Sample Generator for OCR Spike.

Generates 16 standardized synthetic medical documents (10 lab reports, 6 prescriptions)
with fixed seed (42), controlled variations (fonts, sizes, rotation, blur, noise, low-contrast),
and ground-truth JSON annotations.
"""

from __future__ import annotations

import json
import os
import random
import sys
from typing import Any, Dict, List, Tuple

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from PIL import Image, ImageDraw, ImageFilter, ImageFont, features
from data_sources.medication_scope import DIABETES_MEDICATIONS, HYPERTENSION_MEDICATIONS


def check_urdu_rendering_support() -> bool:
    """Checks whether Pillow supports connected complex script layout (libraqm)."""
    return bool(features.check("raqm"))


def get_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Safely retrieves a TrueType font on Windows, with fallback to default."""
    font_paths = {
        "arial": r"C:\Windows\Fonts\arial.ttf",
        "calibri": r"C:\Windows\Fonts\calibri.ttf",
        "times": r"C:\Windows\Fonts\times.ttf",
        "tahoma": r"C:\Windows\Fonts\tahoma.ttf",
    }
    path = font_paths.get(name.lower(), font_paths["arial"])
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def apply_salt_and_pepper_noise(img: Image.Image, amount: float = 0.015, seed: int = 42) -> Image.Image:
    """Applies deterministic salt-and-pepper noise to an image."""
    rng = random.Random(seed)
    noisy = img.copy()
    pixels = noisy.load()
    w, h = noisy.size
    num_noisy = int(w * h * amount)

    for _ in range(num_noisy):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        # Salt (white) or pepper (dark gray/black)
        color = (255, 255, 255) if rng.random() > 0.5 else (20, 20, 20)
        pixels[x, y] = color

    return noisy


def generate_all_samples(output_dir: str, force_urdu: bool = False) -> Tuple[int, int, Dict[str, Any]]:
    """
    Generates synthetic sample images and returns (generated_count, skipped_count, ground_truth).
    Fixed seed 42 guarantees 100% byte-for-byte reproducibility across runs.
    """
    random.seed(42)
    os.makedirs(output_dir, exist_ok=True)
    has_raqm = check_urdu_rendering_support()

    samples_meta = [
        # --- 10 LAB REPORTS ---
        {
            "filename": "lab_01.png",
            "type": "lab",
            "font": "calibri",
            "font_size": 22,
            "patient": "Test Patient 01",
            "lines": [
                "SAMPLE LAB - DIAGNOSTIC REPORT",
                "Patient: Test Patient 01    Age: 58    Gender: M",
                "Date: 2026-10-15",
                "--------------------------------------------------",
                "TEST NAME                   RESULT       REFERENCE",
                "HbA1c:                      7.8 %        < 5.7 %",
                "Fasting Blood Glucose:      126 mg/dL    70-99 mg/dL",
                "Total Cholesterol:          195 mg/dL    < 200 mg/dL",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 7.8,
                "glucose": {"value": 126.0, "unit": "mg/dL", "context": "fasting"},
                "total_chol": 195.0,
            },
            "effects": [],
            "urdu": False,
        },
        {
            "filename": "lab_02.png",
            "type": "lab",
            "font": "arial",
            "font_size": 20,
            "patient": "Test Patient 02",
            "lines": [
                "SAMPLE LAB SERVICES",
                "Patient: Test Patient 02    DOB: 1968-05-12",
                "==================================================",
                "Investigation              Observation",
                "Glycated haemoglobin       8.1%",
                "Blood Glucose (Fasting)    7.2 mmol/L",
                "BP:                        148/92 mmHg",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 8.1,
                "glucose": {"value": 7.2, "unit": "mmol/L", "context": "fasting"},
                "bp": [148, 92],
            },
            "effects": [],
            "urdu": False,
        },
        {
            "filename": "lab_03.png",
            "type": "lab",
            "font": "times",
            "font_size": 24,
            "patient": "Test Patient 03",
            "lines": [
                "SAMPLE CLINICAL LABORATORIES",
                "Name: Test Patient 03",
                "--------------------------------------------------",
                "HbA1c: 6.9 %",
                "Random Glucose: 160 mg/dL",
                "Blood Pressure: 130/85 mmHg",
                "Total Cholesterol: 212 mg/dL",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 6.9,
                "glucose": {"value": 160.0, "unit": "mg/dL", "context": "random"},
                "bp": [130, 85],
                "total_chol": 212.0,
            },
            "effects": [],
            "urdu": False,
        },
        {
            "filename": "lab_04.png",
            "type": "lab",
            "font": "arial",
            "font_size": 22,
            "patient": "Test Patient 04",
            "lines": [
                "SAMPLE LAB - ENDOCRINE PANEL",
                "Patient: Test Patient 04",
                "HbA1c: 7.4 %",
                "Fasting Glucose: 6.8 mmol/L",
                "Total Cholesterol: 180 mg/dL",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 7.4,
                "glucose": {"value": 6.8, "unit": "mmol/L", "context": "fasting"},
                "total_chol": 180.0,
            },
            "effects": ["rotate_pos"],
            "urdu": False,
        },
        {
            "filename": "lab_05.png",
            "type": "lab",
            "font": "calibri",
            "font_size": 20,
            "patient": "Test Patient 05",
            "lines": [
                "SAMPLE LAB PATHOLOGY",
                "Patient: Test Patient 05",
                "Test                       Result",
                "Glycated haemoglobin       9.0%",
                "Glucose (RBS)              210 mg/dL",
                "BP                         155/95 mmHg",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 9.0,
                "glucose": {"value": 210.0, "unit": "mg/dL", "context": "random"},
                "bp": [155, 95],
            },
            "effects": [],
            "urdu": False,
        },
        {
            "filename": "lab_06.png",
            "type": "lab",
            "font": "times",
            "font_size": 26,
            "patient": "Test Patient 06",
            "lines": [
                "SAMPLE LAB - GENERAL PROFILE",
                "Patient: Test Patient 06",
                "Fasting Blood Sugar: 115 mg/dL",
                "BP: 120/80 mmHg",
                "Total Cholesterol: 175 mg/dL",
            ],
            "ground_truth": {
                "type": "lab",
                "glucose": {"value": 115.0, "unit": "mg/dL", "context": "fasting"},
                "bp": [120, 80],
                "total_chol": 175.0,
            },
            "effects": [],
            "urdu": False,
        },
        {
            "filename": "lab_07.png",
            "type": "lab",
            "font": "arial",
            "font_size": 22,
            "patient": "Test Patient 07",
            "lines": [
                "SAMPLE LAB BIOCHEMISTRY",
                "Patient: Test Patient 07",
                "HbA1c: 7.1 %",
                "Glucose (Post-prandial): 165 mg/dL",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 7.1,
                "glucose": {"value": 165.0, "unit": "mg/dL", "context": "post-prandial"},
            },
            "effects": ["blur"],
            "urdu": False,
        },
        {
            "filename": "lab_08.png",
            "type": "lab",
            "font": "calibri",
            "font_size": 20,
            "patient": "Test Patient 08",
            "lines": [
                "SAMPLE LAB - METABOLIC CHECK",
                "Patient: Test Patient 08",
                "HbA1c: 8.5 %",
                "Fasting Glucose: 8.4 mmol/L",
                "BP: 142/88 mmHg",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 8.5,
                "glucose": {"value": 8.4, "unit": "mmol/L", "context": "fasting"},
                "bp": [142, 88],
            },
            "effects": ["noise"],
            "urdu": False,
        },
        {
            "filename": "lab_09.png",
            "type": "lab",
            "font": "times",
            "font_size": 20,
            "patient": "Test Patient 09",
            "lines": [
                "SAMPLE LAB - ROUTINE REPORT",
                "Patient: Test Patient 09",
                "HbA1c: 6.5 %",
                "Random Glucose: 140 mg/dL",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 6.5,
                "glucose": {"value": 140.0, "unit": "mg/dL", "context": "random"},
            },
            "effects": ["low_contrast"],
            "urdu": False,
        },
        {
            "filename": "lab_10.png",
            "type": "lab",
            "font": "tahoma",
            "font_size": 22,
            "patient": "Test Patient 10 (ٹیسٹ مریض ۱۰)",
            "lines": [
                "SAMPLE LAB - لیبارٹری رپورٹ",
                "مریض: Test Patient 10",
                "HbA1c: 7.6 %",
                "Fasting Glucose: 135 mg/dL",
            ],
            "ground_truth": {
                "type": "lab",
                "hba1c_pct": 7.6,
                "glucose": {"value": 135.0, "unit": "mg/dL", "context": "fasting"},
            },
            "effects": [],
            "urdu": True,
        },
        # --- 6 PRESCRIPTIONS ---
        {
            "filename": "rx_01.png",
            "type": "prescription",
            "font": "calibri",
            "font_size": 22,
            "patient": "Test Patient 11",
            "lines": [
                "SAMPLE CLINIC PRESCRIPTION",
                "Dr. Sample Physician, MBBS, FCPS",
                "Patient: Test Patient 11",
                "Rx:",
                "1. Tab. Metformin 500 mg BD",
                "2. Tab. Amlodipine 5mg OD",
            ],
            "ground_truth": {
                "type": "prescription",
                "medicines": [
                    {"name": "metformin", "dose": "500 mg", "frequency": "BD"},
                    {"name": "amlodipine", "dose": "5 mg", "frequency": "OD"},
                ],
            },
            "effects": [],
            "urdu": False,
        },
        {
            "filename": "rx_02.png",
            "type": "prescription",
            "font": "arial",
            "font_size": 24,
            "patient": "Test Patient 12",
            "lines": [
                "SAMPLE MEDICAL CLINIC",
                "Patient: Test Patient 12",
                "Rx:",
                "1. Tab. Gliclazide 80mg 1+0+1",
                "2. Tab. Losartan 50 mg — once daily",
            ],
            "ground_truth": {
                "type": "prescription",
                "medicines": [
                    {"name": "gliclazide", "dose": "80 mg", "frequency": "1+0+1"},
                    {"name": "losartan", "dose": "50 mg", "frequency": "once daily"},
                ],
            },
            "effects": ["rotate_neg"],
            "urdu": False,
        },
        {
            "filename": "rx_03.png",
            "type": "prescription",
            "font": "times",
            "font_size": 22,
            "patient": "Test Patient 13",
            "lines": [
                "SAMPLE FAMILY HEALTH CLINIC",
                "Patient: Test Patient 13",
                "Rx:",
                "1. Tab. Sitagliptin 100 mg OD",
                "2. Tab. Lisinopril 10 mg OD",
                "3. Tab. Empagliflozin 10 mg OD",
            ],
            "ground_truth": {
                "type": "prescription",
                "medicines": [
                    {"name": "sitagliptin", "dose": "100 mg", "frequency": "OD"},
                    {"name": "lisinopril", "dose": "10 mg", "frequency": "OD"},
                    {"name": "empagliflozin", "dose": "10 mg", "frequency": "OD"},
                ],
            },
            "effects": ["blur"],
            "urdu": False,
        },
        {
            "filename": "rx_04.png",
            "type": "prescription",
            "font": "tahoma",
            "font_size": 22,
            "patient": "Test Patient 14",
            "lines": [
                "SAMPLE HEALTH CLINIC",
                "Patient: Test Patient 14",
                "Rx:",
                "1. Tab. Metformin 500 mg روزانہ دو بار",
            ],
            "ground_truth": {
                "type": "prescription",
                "medicines": [
                    {"name": "metformin", "dose": "500 mg", "frequency": "روزانہ دو بار"},
                ],
            },
            "effects": [],
            "urdu": True,
        },
        {
            "filename": "rx_05.png",
            "type": "prescription",
            "font": "tahoma",
            "font_size": 22,
            "patient": "Test Patient 15",
            "lines": [
                "SAMPLE MEDICAL CENTER",
                "Patient: Test Patient 15",
                "Rx:",
                "1. Tab. Glimepiride 2 mg OD کھانے کے بعد",
            ],
            "ground_truth": {
                "type": "prescription",
                "medicines": [
                    {"name": "glimepiride", "dose": "2 mg", "frequency": "OD"},
                ],
            },
            "effects": ["rotate_pos"],
            "urdu": True,
        },
        {
            "filename": "rx_06.png",
            "type": "prescription",
            "font": "arial",
            "font_size": 20,
            "patient": "Test Patient 16",
            "lines": [
                "SAMPLE SPECIALIST CLINIC",
                "Patient: Test Patient 16",
                "Rx:",
                "1. Tab. Metformin 850 mg BD",
                "2. Tab. Telmisartan 40 mg OD",
                "3. Insulin glargine 10 units at night",
            ],
            "ground_truth": {
                "type": "prescription",
                "medicines": [
                    {"name": "metformin", "dose": "850 mg", "frequency": "BD"},
                    {"name": "telmisartan", "dose": "40 mg", "frequency": "OD"},
                    {"name": "insulin glargine", "dose": "10 units", "frequency": "at night"},
                ],
            },
            "effects": ["noise"],
            "urdu": False,
        },
    ]

    generated_count = 0
    skipped_count = 0
    final_ground_truth: Dict[str, Any] = {}

    for idx, item in enumerate(samples_meta):
        is_urdu_sample = item["urdu"]

        if is_urdu_sample and not has_raqm and not force_urdu:
            print(
                f"[TRAP TRIGGERED] Skipping Urdu sample '{item['filename']}' because "
                f"PIL.features.check('raqm') is False (libraqm not present). "
                f"Will report NOT DONE per prompt instructions."
            )
            skipped_count += 1
            continue

        # Create canvas
        width, height = 800, 1000
        bg_color = (245, 245, 245) if "low_contrast" in item["effects"] else (255, 255, 255)
        text_color = (130, 130, 130) if "low_contrast" in item["effects"] else (30, 30, 30)

        img = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        # Header watermark
        stamp_font = get_font("arial", 20)
        draw.text(
            (50, 30),
            "SAMPLE — NOT A REAL REPORT",
            fill=(190, 0, 0) if "low_contrast" not in item["effects"] else (160, 100, 100),
            font=stamp_font,
        )

        font = get_font(item["font"], item["font_size"])
        y_cursor = 80
        for line in item["lines"]:
            draw.text((50, y_cursor), line, fill=text_color, font=font)
            y_cursor += int(item["font_size"] * 1.7)

        # Apply transformations deterministically
        if "rotate_pos" in item["effects"]:
            img = img.rotate(2.5, expand=False, fillcolor=bg_color, resample=Image.Resampling.BILINEAR)
        elif "rotate_neg" in item["effects"]:
            img = img.rotate(-2.5, expand=False, fillcolor=bg_color, resample=Image.Resampling.BILINEAR)

        if "blur" in item["effects"]:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.9))

        if "noise" in item["effects"]:
            img = apply_salt_and_pepper_noise(img, amount=0.015, seed=42 + idx)

        out_path = os.path.join(output_dir, item["filename"])
        img.save(out_path, format="PNG", optimize=True)
        final_ground_truth[item["filename"]] = item["ground_truth"]
        generated_count += 1

    gt_path = os.path.join(os.path.dirname(output_dir), "ground_truth.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(final_ground_truth, f, indent=2, ensure_ascii=False)

    return generated_count, skipped_count, final_ground_truth


if __name__ == "__main__":
    force = "--force-urdu" in sys.argv
    samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "samples", "synthetic"))
    gen, skp, gt = generate_all_samples(samples_dir, force_urdu=force)
    print(f"\nSample generation complete: {gen} images generated, {skp} skipped.")

