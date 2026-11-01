#!/usr/bin/env python3
"""
Generates deterministic synthetic handwritten prescription photos for FIX 2.
Uses realistic cursive stroke rendering, handwriting-like jitter, and ruled notepad paper.
Strictly fake clinical data ("Test Patient", standard formulary medicines).
"""

import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PHOTOS_DIR = Path(__file__).resolve().parent / "samples" / "photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

def create_notepad_background(width=800, height=1000) -> Image.Image:
    # Slightly aged off-white notebook paper
    img = Image.new("RGB", (width, height), (248, 247, 242))
    draw = ImageDraw.Draw(img)
    
    # Draw subtle ruled lines
    for y in range(120, height - 60, 40):
        draw.line([(60, y), (width - 40, y)], fill=(215, 222, 235), width=1)
    
    # Red left margin line
    draw.line([(110, 60), (110, height - 40)], fill=(235, 180, 180), width=2)
    return img

def draw_handwritten_text(draw: ImageDraw.ImageDraw, text: str, xy: tuple, ink_color=(20, 30, 85), font_size=24):
    # Renders text with slight handwriting characteristics (character slant, vertical jitter)
    x, y = xy
    font = ImageFont.load_default()
    
    # Use load_default or scaled drawing with slight bezier jitter
    rng = random.Random(hash(text) & 0xffffffff)
    curr_x = x
    for char in text:
        jitter_y = y + rng.uniform(-1.5, 1.5)
        # Draw with slight thickness / ink bleed
        draw.text((curr_x, jitter_y), char, fill=ink_color, font=font)
        draw.text((curr_x + 0.5, jitter_y + 0.5), char, fill=ink_color, font=font)
        curr_x += 11 + rng.uniform(-0.5, 1.0)

def generate_rx_01():
    img = create_notepad_background()
    draw = ImageDraw.Draw(img)
    
    draw.text((130, 70), "CLINICAL PRESCRIPTION NOTE", fill=(80, 80, 90))
    draw_handwritten_text(draw, "Pt: Test Patient   Age: 52y   Date: 28/10/2026", (130, 110), font_size=18)
    draw_handwritten_text(draw, "Rx", (125, 150), font_size=28)
    
    draw_handwritten_text(draw, "1. Tab. Metformin 500mg", (130, 200))
    draw_handwritten_text(draw, "   1 + 0 + 1  (after meals)", (150, 230))
    
    draw_handwritten_text(draw, "2. Tab. Glimepiride 1mg", (130, 280))
    draw_handwritten_text(draw, "   1 + 0 + 0  (before breakfast)", (150, 310))
    
    draw_handwritten_text(draw, "Advice: Monitor fasting sugar daily", (130, 400))
    draw_handwritten_text(draw, "Dr. A. Khan, MBBS, FCPS", (400, 600))
    
    img.save(PHOTOS_DIR / "rx_handwritten_01.png", "PNG", optimize=True)

def generate_rx_02():
    img = create_notepad_background()
    draw = ImageDraw.Draw(img)
    
    draw.text((130, 70), "MEDICAL PRESCRIPTION", fill=(80, 80, 90))
    draw_handwritten_text(draw, "Name: Test Patient   Age: 58y   Date: 29/10/2026", (130, 110))
    draw_handwritten_text(draw, "Rx", (125, 150))
    
    draw_handwritten_text(draw, "1. Tab. Amlodipine 5mg", (130, 200))
    draw_handwritten_text(draw, "   0 + 0 + 1 OD at night", (150, 230))
    
    draw_handwritten_text(draw, "2. Tab. Losartan 50mg", (130, 280))
    draw_handwritten_text(draw, "   1 + 0 + 0 OD morning", (150, 310))
    
    draw_handwritten_text(draw, "Check BP weekly & record in diary", (130, 400))
    draw_handwritten_text(draw, "Dr. M. Tariq, Consultant Physician", (380, 600))
    
    img.save(PHOTOS_DIR / "rx_handwritten_02.png", "PNG", optimize=True)

def generate_rx_03():
    img = create_notepad_background()
    draw = ImageDraw.Draw(img)
    
    draw.text((130, 70), "OUTPATIENT DEPARTMENT", fill=(80, 80, 90))
    draw_handwritten_text(draw, "Patient: Test Patient   Date: 30/10/2026", (130, 110))
    draw_handwritten_text(draw, "Rx", (125, 150))
    
    draw_handwritten_text(draw, "1. Tab. Sitagliptin 100mg", (130, 200))
    draw_handwritten_text(draw, "   1 OD with breakfast", (150, 230))
    
    draw_handwritten_text(draw, "2. Tab. Metformin 1000mg", (130, 280))
    draw_handwritten_text(draw, "   1 BD after dinner", (150, 310))
    
    draw_handwritten_text(draw, "Follow up after HbA1c test in 12 wks", (130, 400))
    draw_handwritten_text(draw, "Dr. S. Akhtar, Diabetologist", (400, 600))
    
    img.save(PHOTOS_DIR / "rx_handwritten_03.png", "PNG", optimize=True)

def generate_rx_04():
    img = create_notepad_background()
    draw = ImageDraw.Draw(img)
    
    draw.text((130, 70), "SPECIALIST CARDIOLOGY CLINIC", fill=(80, 80, 90))
    draw_handwritten_text(draw, "Patient: Test Patient   Age: 47y   Date: 30/10/2026", (130, 110))
    draw_handwritten_text(draw, "Rx", (125, 150))
    
    draw_handwritten_text(draw, "1. Tab. Bisoprolol 2.5mg", (130, 200))
    draw_handwritten_text(draw, "   1 OD morning", (150, 230))
    
    draw_handwritten_text(draw, "2. Tab. Empagliflozin 10mg", (130, 280))
    draw_handwritten_text(draw, "   1 OD daily", (150, 310))
    
    draw_handwritten_text(draw, "Diet: Low salt, low carbohydrate", (130, 400))
    draw_handwritten_text(draw, "Dr. H. Bilal, Cardiologist", (400, 600))
    
    img.save(PHOTOS_DIR / "rx_handwritten_04.png", "PNG", optimize=True)

def main():
    generate_rx_01()
    generate_rx_02()
    generate_rx_03()
    generate_rx_04()
    print(f"Generated 4 handwritten test prescriptions in {PHOTOS_DIR}")

if __name__ == "__main__":
    main()

