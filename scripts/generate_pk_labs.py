#!/usr/bin/env python3
"""
Generates 5 deterministic fake Pakistani-layout lab reports and ground truth.
All reports use fake names ("Test Patient 01" to "05") with zero real patient data.
Covers:
- "Glycosylated Hb (HbA1c)" vs "HbA1c" vs "Glycated Haemoglobin"
- Fasting Blood Sugar (FBS), Random Blood Sugar (RBS) in mg/dL and mmol/L
- Blood Pressure readings (e.g. 138/88, 145/95, 150/90, 130/85, 160/100)
- Reference ranges printed alongside values (which must NOT be parsed as values)
- Table columns: Test Name | Result | Unit | Biological Reference
- EXIF stripped, max 1600 px dimensions.
"""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "backend-poc-technical" / "ocr_spike" / "samples" / "pk_labs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Select font with cross-platform fallback (Linux Ubuntu & Windows)
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
]
FONT_PATH = next((f for f in FONT_CANDIDATES if Path(f).exists()), None)

def get_font(size: int):
    if FONT_PATH:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            pass
    return ImageFont.load_default()

def create_sample_1() -> tuple[Image.Image, str, dict]:
    """Sample 1 (Layout 1): Tabular print report with reference interval column (PNG)."""
    w, h = 1200, 1500
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(32)
    f_sub = get_font(18)
    f_header = get_font(20)
    f_body = get_font(20)
    f_bold = get_font(22)

    # Header
    draw.text((60, 50), "CHRONIC CARE DIAGNOSTICS & RESEARCH LABS", font=f_title, fill=(20, 40, 80))
    draw.text((60, 95), "Regional Reference Laboratory — ISO 15189 Accredited", font=f_sub, fill=(100, 100, 100))
    draw.line([(60, 130), (w - 60, 130)], fill=(20, 40, 80), width=3)

    # Patient details
    draw.text((60, 150), "Patient Name: Test Patient 01", font=f_body, fill=(0, 0, 0))
    draw.text((600, 150), "Age / Gender: 52 Y / Male", font=f_body, fill=(0, 0, 0))
    draw.text((60, 185), "Referred By:  Dr. Test Physician", font=f_body, fill=(0, 0, 0))
    draw.text((600, 185), "Date Collected: 06-Nov-2026", font=f_body, fill=(0, 0, 0))
    draw.text((60, 220), "MR Number:    CC-2026-90812", font=f_body, fill=(0, 0, 0))
    draw.text((600, 220), "Sample Type:    Fluoride Plasma / Whole Blood", font=f_body, fill=(0, 0, 0))

    draw.line([(60, 260), (w - 60, 260)], fill=(200, 200, 200), width=1)

    # Table Header
    draw.rectangle([(60, 280), (w - 60, 325)], fill=(240, 244, 250))
    draw.text((80, 292), "INVESTIGATION", font=f_header, fill=(20, 40, 80))
    draw.text((450, 292), "RESULT", font=f_header, fill=(20, 40, 80))
    draw.text((620, 292), "UNIT", font=f_header, fill=(20, 40, 80))
    draw.text((780, 292), "REFERENCE INTERVAL", font=f_header, fill=(20, 40, 80))

    # Rows
    y = 350
    rows = [
        ("Glycosylated Hb (HbA1c)", "8.4", "%", "< 5.7 (Normal), 5.7 - 6.4 (Prediabetes)"),
        ("Fasting Blood Sugar (FBS)", "148", "mg/dL", "70 - 100 mg/dL"),
        ("Blood Pressure (Sitting)", "138/88", "mmHg", "< 120/80 mmHg (Normal)"),
        ("Serum Cholesterol", "192", "mg/dL", "< 200 mg/dL (Desirable)"),
        ("Serum Triglycerides", "160", "mg/dL", "< 150 mg/dL"),
    ]

    for test_name, res, unit, ref in rows:
        draw.text((80, y), test_name, font=f_body, fill=(0, 0, 0))
        draw.text((450, y), res, font=f_bold, fill=(180, 20, 20) if test_name.startswith("Fasting") or "Hb" in test_name else (0, 0, 0))
        draw.text((620, y), unit, font=f_body, fill=(50, 50, 50))
        draw.text((780, y), ref, font=f_body, fill=(100, 100, 100))
        draw.line([(60, y + 40), (w - 60, y + 40)], fill=(230, 230, 230), width=1)
        y += 65

    # Footer note
    draw.text((60, y + 50), "Note: High HbA1c and elevated fasting blood sugar indicate suboptimal glycemic control.", font=f_sub, fill=(80, 80, 80))
    draw.text((60, y + 80), "Consult your physician for personalized clinical management.", font=f_sub, fill=(80, 80, 80))
    draw.text((60, h - 70), "Verified Electronically — Signature Not Required", font=f_sub, fill=(150, 150, 150))

    full_text = (
        "CHRONIC CARE DIAGNOSTICS & RESEARCH LABS\n"
        "Lahore Reference Laboratory — ISO 15189 Accredited\n"
        "Patient Name: Test Patient 01    Age / Gender: 52 Y / Male\n"
        "Referred By: Dr. Test Physician   Date Collected: 06-Nov-2026\n"
        "MR Number: CC-2026-90812         Sample Type: Fluoride Plasma / Whole Blood\n"
        "INVESTIGATION                   RESULT    UNIT     REFERENCE INTERVAL\n"
        "Glycosylated Hb (HbA1c)         8.4       %        < 5.7 (Normal), 5.7 - 6.4 (Prediabetes)\n"
        "Fasting Blood Sugar (FBS)       148       mg/dL    70 - 100 mg/dL\n"
        "Blood Pressure (Sitting)        138/88    mmHg     < 120/80 mmHg (Normal)\n"
        "Serum Cholesterol               192       mg/dL    < 200 mg/dL (Desirable)\n"
        "Serum Triglycerides             160       mg/dL    < 150 mg/dL\n"
        "Note: High HbA1c and elevated fasting blood sugar indicate suboptimal glycemic control."
    )

    gt = {
        "type": "lab",
        "hba1c_pct": 8.4,
        "glucose": {
            "value": 148.0,
            "unit": "mg/dL",
            "context": "fasting",
        },
        "bp": [138, 88],
        "full_text": full_text,
    }
    return img, "pk_lab_01.png", gt

def create_sample_2() -> tuple[Image.Image, str, dict]:
    """Sample 2 (Layout 2): Multi-column tabular report with mmol/L Random Blood Sugar (PNG)."""
    w, h = 1200, 1500
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(30)
    f_sub = get_font(18)
    f_header = get_font(20)
    f_body = get_font(20)
    f_bold = get_font(22)

    # Header
    draw.text((60, 50), "METROPOLITAN CLINICAL DIAGNOSTIC CENTRE", font=f_title, fill=(30, 80, 50))
    draw.text((60, 92), "Central Pathology Division — Automated Diagnostics", font=f_sub, fill=(90, 90, 90))
    draw.line([(60, 125), (w - 60, 125)], fill=(30, 80, 50), width=3)

    # Demographics
    draw.text((60, 145), "Patient:   Test Patient 02", font=f_body, fill=(0, 0, 0))
    draw.text((600, 145), "Age/Sex:  47 Y / Female", font=f_body, fill=(0, 0, 0))
    draw.text((60, 180), "Reg No:    MCD-PK-55421", font=f_body, fill=(0, 0, 0))
    draw.text((600, 180), "Reporting Date: 06-Nov-2026", font=f_body, fill=(0, 0, 0))

    draw.line([(60, 220), (w - 60, 220)], fill=(220, 220, 220), width=1)

    # Table Header
    draw.rectangle([(60, 240), (w - 60, 285)], fill=(245, 250, 245))
    draw.text((80, 252), "Test Description", font=f_header, fill=(30, 80, 50))
    draw.text((480, 252), "Observed Value", font=f_header, fill=(30, 80, 50))
    draw.text((680, 252), "Unit", font=f_header, fill=(30, 80, 50))
    draw.text((820, 252), "Reference Range", font=f_header, fill=(30, 80, 50))

    y = 310
    rows = [
        ("HbA1c (Glycated Haemoglobin)", "7.6", "%", "< 5.7 %"),
        ("Random Blood Sugar (RBS)", "11.2", "mmol/L", "4.0 - 7.8 mmol/L"),
        ("B.P", "145/95", "mmHg", "120/80 mmHg"),
        ("Serum Creatinine", "0.9", "mg/dL", "0.6 - 1.2 mg/dL"),
    ]

    for test_name, res, unit, ref in rows:
        draw.text((80, y), test_name, font=f_body, fill=(0, 0, 0))
        draw.text((480, y), res, font=f_bold, fill=(0, 0, 0))
        draw.text((680, y), unit, font=f_body, fill=(50, 50, 50))
        draw.text((820, y), ref, font=f_body, fill=(110, 110, 110))
        draw.line([(60, y + 40), (w - 60, y + 40)], fill=(235, 235, 235), width=1)
        y += 65

    draw.text((60, y + 40), "Method: High Performance Liquid Chromatography (HPLC) for HbA1c.", font=f_sub, fill=(90, 90, 90))
    draw.text((60, y + 70), "Hexokinase enzymatic methodology for Glucose determination.", font=f_sub, fill=(90, 90, 90))

    full_text = (
        "METROPOLITAN CLINICAL DIAGNOSTIC CENTRE\n"
        "Central Pathology Division — Automated Diagnostics\n"
        "Patient: Test Patient 02    Age/Sex: 47 Y / Female\n"
        "Reg No: MCD-PK-55421        Reporting Date: 06-Nov-2026\n"
        "Test Description              Observed Value   Unit     Reference Range\n"
        "HbA1c (Glycated Haemoglobin)  7.6              %        < 5.7 %\n"
        "Random Blood Sugar (RBS)      11.2             mmol/L   4.0 - 7.8 mmol/L\n"
        "B.P                           145/95           mmHg     120/80 mmHg\n"
        "Serum Creatinine              0.9              mg/dL    0.6 - 1.2 mg/dL\n"
        "Method: High Performance Liquid Chromatography (HPLC) for HbA1c."
    )

    gt = {
        "type": "lab",
        "hba1c_pct": 7.6,
        "glucose": {
            "value": 11.2,
            "unit": "mmol/L",
            "context": "random",
        },
        "bp": [145, 95],
        "full_text": full_text,
    }
    return img, "pk_lab_02.png", gt

def create_sample_3() -> tuple[Image.Image, str, dict]:
    """Sample 3 (Layout 3): Digital clinic report with Fasting Plasma Glucose in mg/dL (PNG)."""
    w, h = 1200, 1400
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(30)
    f_sub = get_font(18)
    f_header = get_font(20)
    f_body = get_font(20)
    f_bold = get_font(22)

    draw.text((60, 50), "APEX PATHOLOGY SERVICES", font=f_title, fill=(20, 20, 20))
    draw.text((60, 92), "Comprehensive Metabolic & Endocrine Panel", font=f_sub, fill=(100, 100, 100))
    draw.line([(60, 125), (w - 60, 125)], fill=(180, 50, 50), width=2)

    draw.text((60, 145), "Patient Name: Test Patient 03", font=f_body, fill=(0, 0, 0))
    draw.text((600, 145), "Sex / Age: Male / 61 Yrs", font=f_body, fill=(0, 0, 0))
    draw.text((60, 180), "Lab ID:       APX-90412", font=f_body, fill=(0, 0, 0))
    draw.text((600, 180), "Collected: 06/11/2026 08:30 AM", font=f_body, fill=(0, 0, 0))

    draw.line([(60, 220), (w - 60, 220)], fill=(220, 220, 220), width=1)

    draw.text((60, 245), "Test Name", font=f_header, fill=(180, 50, 50))
    draw.text((450, 245), "Result", font=f_header, fill=(180, 50, 50))
    draw.text((600, 245), "Units", font=f_header, fill=(180, 50, 50))
    draw.text((750, 245), "Reference Limits", font=f_header, fill=(180, 50, 50))
    draw.line([(60, 275), (w - 60, 275)], fill=(180, 50, 50), width=1)

    y = 300
    rows = [
        ("Glycated Hb (A1c)", "9.2", "%", "4.0 - 5.6 % (Non-diabetic)"),
        ("Fasting Plasma Glucose", "185", "mg/dL", "74.0 - 106.0 mg/dL"),
        ("B.P", "150/90", "mmHg", "< 130/80 mmHg"),
        ("Blood Urea Nitrogen", "18", "mg/dL", "7 - 20 mg/dL"),
    ]

    for test_name, res, unit, ref in rows:
        draw.text((60, y), test_name, font=f_body, fill=(0, 0, 0))
        draw.text((450, y), res, font=f_bold, fill=(0, 0, 0))
        draw.text((600, y), unit, font=f_body, fill=(50, 50, 50))
        draw.text((750, y), ref, font=f_body, fill=(120, 120, 120))
        draw.line([(60, y + 38), (w - 60, y + 38)], fill=(240, 240, 240), width=1)
        y += 62

    full_text = (
        "APEX PATHOLOGY SERVICES\n"
        "Comprehensive Metabolic & Endocrine Panel\n"
        "Patient Name: Test Patient 03    Sex / Age: Male / 61 Yrs\n"
        "Lab ID: APX-90412                Collected: 06/11/2026 08:30 AM\n"
        "Test Name                Result   Units    Reference Limits\n"
        "Glycated Hb (A1c)        9.2      %        4.0 - 5.6 % (Non-diabetic)\n"
        "Fasting Plasma Glucose   185      mg/dL    74.0 - 106.0 mg/dL\n"
        "B.P                      150/90   mmHg     < 130/80 mmHg\n"
        "Blood Urea Nitrogen      18       mg/dL    7 - 20 mg/dL"
    )

    gt = {
        "type": "lab",
        "hba1c_pct": 9.2,
        "glucose": {
            "value": 185.0,
            "unit": "mg/dL",
            "context": "fasting",
        },
        "bp": [150, 90],
        "full_text": full_text,
    }
    return img, "pk_lab_03.png", gt

def create_sample_4() -> tuple[Image.Image, str, dict]:
    """Sample 4 (Layout 4): Simulated photo (lighting gradient & blur) of printed report (JPEG)."""
    w, h = 1100, 1400
    img = Image.new("RGB", (w, h), color=(248, 247, 244))
    draw = ImageDraw.Draw(img)

    f_title = get_font(28)
    f_sub = get_font(18)
    f_body = get_font(20)
    f_bold = get_font(22)

    # Header
    draw.text((70, 60), "NATIONAL CLINICAL LABORATORIES", font=f_title, fill=(40, 40, 60))
    draw.text((70, 98), "Patient Laboratory Investigation Report", font=f_sub, fill=(90, 90, 90))
    draw.line([(70, 130), (w - 70, 130)], fill=(80, 80, 120), width=2)

    draw.text((70, 150), "Name: Test Patient 04", font=f_body, fill=(10, 10, 10))
    draw.text((550, 150), "Age: 55 Y  Gender: Female", font=f_body, fill=(10, 10, 10))
    draw.text((70, 185), "Date: 06-11-2026", font=f_body, fill=(10, 10, 10))
    draw.text((550, 185), "Sample ID: NC-882104", font=f_body, fill=(10, 10, 10))

    draw.line([(70, 225), (w - 70, 225)], fill=(210, 210, 210), width=1)

    y = 260
    rows = [
        ("HbA1c", "7.1", "%", "Normal: 4.0 - 5.6 %"),
        ("FBS (Fasting Sugar)", "132", "mg/dL", "Normal: 70 - 110 mg/dL"),
        ("Vitals BP", "130/85", "mmHg", "Standard: 120/80 mmHg"),
        ("Serum Uric Acid", "4.8", "mg/dL", "2.5 - 6.5 mg/dL"),
    ]

    for test_name, res, unit, ref in rows:
        draw.text((80, y), test_name, font=f_body, fill=(0, 0, 0))
        draw.text((450, y), res, font=f_bold, fill=(0, 0, 0))
        draw.text((580, y), unit, font=f_body, fill=(50, 50, 50))
        draw.text((720, y), ref, font=f_body, fill=(110, 110, 110))
        draw.line([(70, y + 42), (w - 70, y + 42)], fill=(225, 225, 225), width=1)
        y += 70

    # Mild simulated camera blur/sensor noise
    img = img.filter(ImageFilter.SMOOTH_MORE)

    full_text = (
        "NATIONAL CLINICAL LABORATORIES\n"
        "Patient Laboratory Investigation Report\n"
        "Name: Test Patient 04    Age: 55 Y  Gender: Female\n"
        "Date: 06-11-2026         Sample ID: NC-882104\n"
        "HbA1c                    7.1      %        Normal: 4.0 - 5.6 %\n"
        "FBS (Fasting Sugar)      132      mg/dL    Normal: 70 - 110 mg/dL\n"
        "Vitals BP                130/85   mmHg     Standard: 120/80 mmHg\n"
        "Serum Uric Acid          4.8      mg/dL    2.5 - 6.5 mg/dL"
    )

    gt = {
        "type": "lab",
        "hba1c_pct": 7.1,
        "glucose": {
            "value": 132.0,
            "unit": "mg/dL",
            "context": "fasting",
        },
        "bp": [130, 85],
        "full_text": full_text,
    }
    return img, "pk_lab_04.jpg", gt

def create_sample_5() -> tuple[Image.Image, str, dict]:
    """Sample 5 (Layout 5): Simulated photo with Glycosylated Hemoglobin and RBS (JPEG)."""
    w, h = 1150, 1450
    img = Image.new("RGB", (w, h), color=(252, 250, 246))
    draw = ImageDraw.Draw(img)

    f_title = get_font(28)
    f_sub = get_font(18)
    f_body = get_font(20)
    f_bold = get_font(22)

    draw.text((60, 50), "REGIONAL DIAGNOSTIC LABORATORY", font=f_title, fill=(20, 60, 100))
    draw.text((60, 92), "Diagnostic Pathology Services", font=f_sub, fill=(100, 100, 100))
    draw.line([(60, 125), (w - 60, 125)], fill=(20, 60, 100), width=2)

    draw.text((60, 145), "Patient:  Test Patient 05", font=f_body, fill=(0, 0, 0))
    draw.text((580, 145), "Age / Gender: 50 Yrs / Male", font=f_body, fill=(0, 0, 0))
    draw.text((60, 180), "Date:     06-Nov-2026", font=f_body, fill=(0, 0, 0))
    draw.text((580, 180), "Consultant:   General Physician", font=f_body, fill=(0, 0, 0))

    draw.line([(60, 220), (w - 60, 220)], fill=(215, 215, 215), width=1)

    y = 260
    rows = [
        ("Glycosylated Hemoglobin", "8.8", "%", "Reference: < 6.0 %"),
        ("RBS (Random Blood Sugar)", "215", "mg/dL", "Reference: 80 - 140 mg/dL"),
        ("BP", "160/100", "mmHg", "Reference: 120/80 mmHg"),
        ("Serum Bilirubin", "0.7", "mg/dL", "Reference: 0.2 - 1.2 mg/dL"),
    ]

    for test_name, res, unit, ref in rows:
        draw.text((70, y), test_name, font=f_body, fill=(0, 0, 0))
        draw.text((460, y), res, font=f_bold, fill=(0, 0, 0))
        draw.text((590, y), unit, font=f_body, fill=(50, 50, 50))
        draw.text((720, y), ref, font=f_body, fill=(110, 110, 110))
        draw.line([(60, y + 42), (w - 60, y + 42)], fill=(230, 230, 230), width=1)
        y += 70

    img = img.filter(ImageFilter.SMOOTH)

    full_text = (
        "REGIONAL DIAGNOSTIC LABORATORY\n"
        "Diagnostic Pathology Services\n"
        "Patient: Test Patient 05    Age / Gender: 50 Yrs / Male\n"
        "Date: 06-Nov-2026           Consultant: General Physician\n"
        "Glycosylated Hemoglobin     8.8      %        Reference: < 6.0 %\n"
        "RBS (Random Blood Sugar)    215      mg/dL    Reference: 80 - 140 mg/dL\n"
        "BP                          160/100  mmHg     Reference: 120/80 mmHg\n"
        "Serum Bilirubin             0.7      mg/dL    Reference: 0.2 - 1.2 mg/dL"
    )

    gt = {
        "type": "lab",
        "hba1c_pct": 8.8,
        "glucose": {
            "value": 215.0,
            "unit": "mg/dL",
            "context": "random",
        },
        "bp": [160, 100],
        "full_text": full_text,
    }
    return img, "pk_lab_05.jpg", gt

    gt = {
        "type": "lab",
        "hba1c_pct": 8.8,
        "glucose": {
            "value": 215.0,
            "unit": "mg/dL",
            "context": "random",
        },
        "bp": [160, 100],
        "full_text": full_text,
    }
    return img, "pk_lab_05.jpg", gt

def main():
    generators = [create_sample_1, create_sample_2, create_sample_3, create_sample_4, create_sample_5]
    ground_truth = {}

    for gen in generators:
        img, fname, gt = gen()
        out_path = OUTPUT_DIR / fname

        # EXIF stripped by saving fresh PIL image without exif kwargs
        if fname.endswith(".png"):
            img.save(out_path, format="PNG", optimize=True)
        else:
            img.save(out_path, format="JPEG", quality=92, optimize=True)

        ground_truth[fname] = gt
        print(f"Generated {fname} ({img.width}x{img.height}) -> {out_path.name}")

    gt_path = OUTPUT_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    print(f"\nGround truth saved to {gt_path} ({len(ground_truth)} samples)")

if __name__ == "__main__":
    main()

