"""
Script to add at least 40 near-miss and idiom rows (author: 'engineer')
to tests/sim/odd_input_gold.json and evaluate their classification.
"""

import os
import json
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend-poc-technical")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from agents.input_triage import classify_input

near_misses = [
    # English near-misses
    {"text": "my father died of a heart attack", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "this sugar is killing me", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "I could die for a biryani", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "no chest pain", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "chest pain last year but fine now", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "I felt like crying about my diagnosis but I am okay", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "my uncle had a stroke ten years ago", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "I am dying to see my grandkids", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "no breathing trouble at all", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "no difficulty breathing", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "I do not have any chest tightness", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "never had a seizure in my life", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "no loss of consciousness", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "I had a headache yesterday but it went away", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "feeling a bit stressed with work but coping well", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "eating spicy food makes me sweat", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "no weakness on one side", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "my vision is normal with glasses", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "not confused, feeling completely clear", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "no nausea or vomiting today", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "I walk 30 minutes every morning without pain", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "my blood pressure machine battery died", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},
    {"text": "I was worried at first but now I feel fine", "expected_category": "none", "expected_class": None, "language": "en", "author": "engineer"},

    # Roman Urdu near-misses
    {"text": "chest pain nahi hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "seene me koi dard nahi hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "saans theek se aa rahi hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "koi takleef nahi hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "meri ammi ko heart attack hua tha", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "sugar ne pareshan kiya hua hai lekin ab theek hoon", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "sar dard kal tha aaj theek hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "behosh nahi hua kabhi", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "aankhon ki roshni bilkul theek hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "ulti ya matli nahi ho rahi", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "kamzori mehsoos nahi ho rahi", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "biryani khane ka dil kar raha hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "pehle dard tha ab bilkul aaram hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "saans lene me koi masla nahi hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},
    {"text": "dil ki dhadkan normal hai", "expected_category": "none", "expected_class": None, "language": "ur-Latn", "author": "engineer"},

    # Urdu near-misses
    {"text": "سینے میں کوئی درد نہیں ہے", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "سانس بالکل ٹھیک آ رہی ہے", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "میرے والد کو دل کا دورہ پڑا تھا", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "سر درد کل تھا لیکن اب آرام ہے", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "کوئی الٹی یا متلی نہیں ہے", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "آنکھوں کی بینائی بالکل ٹھیک ہے", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "بے ہوشی کی کوئی شکایت نہیں", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "کمزوری نہیں ہو رہی", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "میں بالکل ٹھیک محسوس کر رہا ہوں", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"},
    {"text": "کوئی تکلیف یا پریشانی نہیں ہے", "expected_category": "none", "expected_class": None, "language": "ur", "author": "engineer"}
]

def main():
    gold_path = os.path.join(REPO_ROOT, "tests", "sim", "odd_input_gold.json")
    with open(gold_path, "r", encoding="utf-8") as f:
        existing = json.load(f)

    existing_texts = {x["text"] for x in existing}
    added = 0
    for nm in near_misses:
        if nm["text"] not in existing_texts:
            existing.append(nm)
            existing_texts.add(nm["text"])
            added += 1

    with open(gold_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"Added {added} near-miss rows to odd_input_gold.json. Total count: {len(existing)}")

    print("\nEvaluating what each near-miss row does under classify_input:")
    print("| Text | Lang | Expected | Classified Category | Odd Class | Emergency? | Safety? | Note |")
    print("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|")
    for nm in near_misses:
        t = nm["text"]
        lang = nm["language"]
        res = classify_input(t)
        note = "OK"
        if res.is_emergency:
            note = "OVER-TRIAGE (idiom/unhandled Urdu negation triggered danger phrase)"
        elif res.is_urgent_safety:
            note = "OVER-TRIAGE (urgent safety triggered)"
        elif res.category != "none":
            note = f"Classified as {res.category}:{res.odd_class}"
        print(f"| {t} | {lang} | none | {res.category} | {res.odd_class} | {res.is_emergency} | {res.is_urgent_safety} | {note} |")

if __name__ == "__main__":
    main()
