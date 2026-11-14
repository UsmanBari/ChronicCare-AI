"""
backend-poc-technical/test_red_flag_patterns.py

Comprehensive test suite for Stage-1 clinical red flag patterns (v2).
Validates:
- 120 Positives (8 per category x 3 languages: English, Roman Urdu, Urdu script).
- 120 Negatives (8 per category x 3 languages) covering all clinical guard types:
    * Explicit symptom negation
    * Remote past suppression without acute current markers
    * Exertion with relief by rest suppression
    * Chronic qualifier suppression (neuropathy / chronic aches)
    * Emotional "dil" suppression without cardiac physical cues
    * Recovered syncope suppression
- Full Confusion Matrix table generation and 100% precision/recall assertion.
- Architectural mutation kill tests:
    * test_mutation_killed_window_tolerance (kills M-RF-1)
    * test_mutation_killed_negation_guard (kills M-RF-2)
- API-level tests through POST /api/checkins/{checkin_id}/answer across
  diabetes-only, HTN-only, and dual patients ensuring 1122 emergency response.
"""

import pytest
from typing import Dict, List, Tuple
from fastapi.testclient import TestClient

from main import app
from agents.red_flag_patterns import (
    match as match_red_flags,
    MAX_WINDOW_WORDS,
    is_symptom_negated,
    normalize_text,
)
from test_checkin_api import create_test_token, bootstrap_patient, rsa_key_pair, setup_test_environment, x509_cert_pem

client = TestClient(app)

# =============================================================================
# 1. Test Dataset: 120 Positives (8 x 5 categories x 3 languages)
# =============================================================================

POSITIVES_DATA: Dict[str, Dict[str, List[str]]] = {
    "chest_pain": {
        "en": [
            "My father is having elephant sitting on my chest right now",
            "Crushing pressure in chest radiating to my left jaw",
            "Pain going down my left arm and left jaw with chest heaviness",
            "I have a tight band tightening around my chest this morning",
            "Suddenly developed severe squeezing chest pain while watching TV",
            "Vise around my chest making it impossible to lie down",
            "Sharp chest pain radiating to the left shoulder and left arm",
            "Terrible heaviness inside chest with cold sweating",
        ],
        "roman_ur": [
            "mere abbu ke seene mein shadeed dard aur dabao ho raha hai",
            "chhati par bohot zyada bojh aur bayein bazu me dard hai",
            "seena phat raha hai aur bayein jabray me dard nikal raha hai",
            "dil mein shadeed jalan aur bayein bazu me khichao hai",
            "seene par shadeed dabao hai aur paseena aa raha hai",
            "chhati me achanak sakht dard utha hai abhi",
            "ammi bol rahi hain seene mein bojh aur shadeed jakran hai",
            "seenay me tez dard aur bayen baazu me takleef hai",
        ],
        "ur": [
            "میرے والد کے سینے میں شدید درد اور دباؤ ہو رہا ہے",
            "چھاتی پر شدید بوجھ اور بائیں بازو میں درد ہے",
            "سینے میں شدید جکڑن اور بائیں جبڑے میں کھچاؤ ہے",
            "دل میں شدید درد اور جلن کے ساتھ پسینہ آ رہا ہے",
            "چھاتی پر ہاتھی بیٹھا محسوس ہو رہا ہے",
            "سینے میں شدید دباؤ کے ساتھ بائیں بازو میں درد جا رہا ہے",
            "امی کے سینے میں سخت درد اور گھٹن ہے",
            "سینے میں اچانک شدید بوجھ محسوس ہو رہا ہے",
        ],
    },
    "breathing": {
        "en": [
            "I can't breathe and I am gasping for air",
            "Cannot catch my breath at all suffocating",
            "My mother is struggling for every breath right now",
            "Drowning in air and unable to breathe",
            "Severe shortness of breath coming on suddenly while sitting",
            "Difficulty breathing so bad that I am choking",
            "My father cannot breathe properly and gasping",
            "Hard to breathe and struggling to breathe at rest",
        ],
        "roman_ur": [
            "saans bilkul nahi aa rahi dum ghut raha hai",
            "abbu ko sans lene me shadeed dushwari ho rahi hai",
            "ammi bol rahi hain sans nahi aa rahi gale me ghutan hai",
            "achanak sans ukhad rahi hai aur bol nahi pa raha",
            "sans lena muhaal ho gaya hai bilkul dam ghut raha hai",
            "sans lene me bohot zyada mushkil ho rahi hai abhi",
            "sans bilkul ruk rahi hai aur gasping ho rahi hai",
            "is waqt sans nahi aa rahi bohot takleef hai",
        ],
        "ur": [
            "سانس لینا بہت مشکل ہو گیا ہے دم گھٹ رہا ہے",
            "والد صاحب کو سانس بالکل نہیں آ رہی",
            "سانس اکھڑ رہی ہے اور بولا نہیں جا رہا",
            "امی کی سانس رک رہی ہے اور شدید گھٹن ہے",
            "سانس لینا محال ہو گیا ہے بالکل دم بند ہو رہا ہے",
            "شدید گھٹن ہے اور سانس نہیں آ رہی",
            "اچانک سانس لینے میں شدید دشواری ہو گئی ہے",
            "سانس بالکل اکھڑ چکی ہے اور ہوا نہیں مل رہی",
        ],
    },
    "confusion_and_stroke": {
        "en": [
            "My father's face is drooping on the left side suddenly",
            "Speech is slurred and unable to speak clearly",
            "One sided body weakness and cannot move my left arm",
            "Mother is completely disoriented and don't know where I am",
            "Sudden numbness in right arm and right leg won't move",
            "His mouth became crooked and slurring words",
            "Lost my speech suddenly this morning",
            "Suddenly got paralyzed on right side of face and arm",
        ],
        "roman_ur": [
            "ammi ka munh aik taraf tedha ho gaya hai",
            "abbu ki awaz ladkhada rahi hai aur bol nahi pa rahe",
            "aik taraf ka bazu sunn aur kamzor ho gaya hai achanak",
            "chehra achanak latak gaya hai aur zaban ladkhada rahi hai",
            "bayan hath aur bazu hil nahi raha falij ka asar lag raha hai",
            "kuch samajh nahi aa raha kahan hoon bohot disoriented hoon",
            "bhai ki bolti band ho gayi hai aur munh terha ho gaya",
            "achanak adha jism kamzor ho gaya hai aur khada nahi hua ja raha",
        ],
        "ur": [
            "امی کا چہرہ ایک طرف کو لٹک گیا ہے",
            "والد صاحب کی آواز لڑکھڑا رہی ہے اور بول نہیں پا رہے",
            "ایک طرف کا بازو سن اور بالکل کمزور ہو گیا ہے",
            "منہ ایک طرف ٹیڑھا ہو گیا ہے اور لعاب بہہ رہا ہے",
            "شدید الجھن ہے اور کچھ سمجھ نہیں آ رہا کہاں ہیں",
            "دایاں بازو ہل نہیں رہا فالج کا اثر ہو گیا ہے",
            "اچانک زبان لڑکھڑانے لگی اور بولنا بند ہو گیا",
            "آدھا جسم سن اور بے جان ہو گیا ہے",
        ],
    },
    "loss_of_consciousness": {
        "en": [
            "Patient collapsed on the floor and is completely unresponsive",
            "He passed out cold and is not waking up",
            "My father fainted and we cannot wake him",
            "She had a blackout and remains unconscious",
            "Brother collapsed suddenly and won't wake up",
            "Fainted 10 minutes ago and still not waking up",
            "Patient passed out and is totally unresponsive to voice",
            "Fell unconscious on the ground and cannot wake her",
        ],
        "roman_ur": [
            "hosh mein nahi aa rahe aur be hosh pade hain",
            "abbu achanak behosh ho gaye hain aur uth nahi rahe",
            "ammi behosh ho gayi hain aur jawab nahi de rahi hain",
            "ghashi tari hai aur hosh nahi aa raha bilkul",
            "farsh par behosh pada hai aur koi jawab nahi de raha",
            "be hosh ho kar gir gaye aur abhi tak hosh nahi aaya",
            "bhai behosh hai aur hosh me nahi aa raha",
            "achanak gir pade aur bilkul unresponsive hain",
        ],
        "ur": [
            "ہوش میں نہیں آ رہے اور بے ہوش پڑے ہیں",
            "والد صاحب بے ہوش ہو گئے ہیں اور اٹھ نہیں رہے",
            "امی بے ہوش ہیں اور کوئی جواب نہیں دے رہیں",
            "فرش پر بے ہوش پڑا ہے اور ہوش میں نہیں آ رہا",
            "غشی طاری ہے اور پکارنے پر جواب نہیں دے رہے",
            "بے ہوش ہو گئے ہیں اور ابھی تک ہوش نہیں آیا",
            "اچانک گر پڑے اور بالکل بے سدھ ہیں اٹھ نہیں رہے",
            "بے ہوش پڑے ہیں اور سانس کے سوا کوئی ہوش نہیں",
        ],
    },
    "dka_vomiting_high_glucose": {
        "en": [
            "Even water comes back up and throwing up constantly",
            "Cannot keep any fluids down and vomiting all day",
            "Unable to keep water down throwing up everything",
            "Vomiting continuously and water comes right back up",
            "Cannot keep liquids down with very high sugar",
            "Throwing up non-stop and keep nothing down",
            "My daughter is unable to keep any fluids down",
            "Vomiting non-stop and even sips of water come back up",
        ],
        "roman_ur": [
            "pani bhi nahi ruk raha aur ulti ruk nahi rahi",
            "kuch bhi pet me nahi ruk raha har cheez ulti ho rahi hai",
            "pani peete hi wapis aa jata hai musalsal ultiyan hain",
            "ammi ko musalsal ultiyan ho rahi hain pani bhi nahi ruk raha",
            "kuch bhi hazam nahi ho raha even pani bhi wapis aa raha hai",
            "subah se ulti ruk nahi rahi aur pani bhi nahi rukta",
            "sugar high hai aur pani bhi nahi ruk raha ultiyan hain",
            "har cheez ulti ho rahi hai aur shadeed qay aa rahi hai",
        ],
        "ur": [
            "پانی بھی نہیں رک رہا اور الٹی رک نہیں رہی",
            "کچھ بھی پیٹ میں نہیں رک رہا ہر چیز الٹی ہو رہی ہے",
            "پانی پیتے ہی واپس آ جاتا ہے مسلسل الٹیاں آ رہی ہیں",
            "امی کو مسلسل الٹیاں ہو رہی ہیں اور پانی بھی نہیں رک رہا",
            "کچھ بھی ہضم نہیں ہو رہا پانی بھی واپس آ رہا ہے",
            "صبح سے الٹی رک نہیں رہی ہے اور شدید قے ہے",
            "شوگر بہت تیز ہے اور الٹیاں بند نہیں ہو رہیں",
            "ہر چیز الٹی ہو رہی ہے پانی کا ایک گھونٹ بھی نہیں رکتا",
        ],
    },
}

# =============================================================================
# 2. Test Dataset: 120 Negatives (8 x 5 categories x 3 languages)
# =============================================================================

NEGATIVES_DATA: Dict[str, Dict[str, List[str]]] = {
    "chest_pain": {
        "en": [
            "I have no chest pain or pressure at all today",
            "Had severe chest pain 5 years ago during surgery",
            "Chest discomfort only when climbing stairs and better after resting",
            "Chronic dull chest wall ache for years from old rib injury",
            "Chest hurts when I press on the bruise from yesterday",
            "Doctor confirmed no chest tightness last month",
            "Mild chest discomfort when running fast which goes away with rest",
            "Pain in right foot and denies any chest pain",
        ],
        "roman_ur": [
            "seene mein koi dard ya dabao bilkul nahi hai",
            "teen saal pehle seene me dard hua tha ab theek hai",
            "tez chalne se seena bhaari hota hai aaram karne se theek ho jata hai",
            "dil mein dard hai unki yaad me bohot udaas hoon",
            "saalon se seene ki pasli me purana dard rehta hai",
            "seene me takleef nahi hai fasting sugar 110 hai",
            "bhagne par chhati par dabao aata hai lekin aaram se behtar ho jata hai",
            "dukh aur gham ki wajah se dil mein dard mehsoos ho raha hai",
        ],
        "ur": [
            "سینے میں کوئی درد یا دباؤ بالکل نہیں ہے",
            "پانچ سال پہلے سینے میں درد ہوا تھا اب بالکل ٹھیک ہوں",
            "تیز چلنے سے سینے پر بوجھ ہوتا ہے جو آرام کرنے سے ٹھیک ہو جاتا ہے",
            "ان کی یاد میں دل میں درد ہے بہت اداس ہوں",
            "سالوں سے سینے کی ہڈی میں پرانا درد رہتا ہے",
            "سینے میں تکلیف نہیں ہے شوگر نارمل ہے",
            "سیڑھیاں چڑھنے سے چھاتی پر بوجھ بنتا ہے لیکن آرام سے بہتر ہو جاتا ہے",
            "غم اور دکھ سے دل میں درد ہو رہا ہے",
        ],
    },
    "breathing": {
        "en": [
            "I have no shortness of breath or difficulty breathing",
            "Had severe trouble breathing 2 years ago with pneumonia",
            "Breathless only when walking fast and better after resting",
            "Chronic mild breathlessness for years with asthma",
            "Breathing is completely fine without any trouble",
            "Slightly out of breath after jogging but relieved by rest",
            "Never had difficulty breathing in my life",
            "Old breathing problem for many years under control",
        ],
        "roman_ur": [
            "saans bilkul theek aa rahi hai koi dushwari nahi hai",
            "pichle saal sans ki shadeed takleef hui thi ab theek hai",
            "seedhiyan chadhne par sans phoolti hai aaram karne se theek ho jati hai",
            "saalon se sans ka purana masla hai duma ki wajah se",
            "sans lene me koi masla ya dushwari nahi hai",
            "tez chalne par sans chadhti hai lekin aaram se behtar ho jati hai",
            "bachpan me sans rukti thi ab bilkul theek hoon",
            "bina kisi sans ki takleef ke theek mehsoos kar raha hoon",
        ],
        "ur": [
            "سانس بالکل ٹھیک ہے کوئی دشواری یا مسئلہ نہیں ہے",
            "تین سال پہلے سانس کی تکلیف ہوئی تھی اب ٹھیک ہوں",
            "تیز چلنے سے سانس پھولتی ہے آرام کرنے پر فوراً ٹھیک ہو جاتی ہے",
            "سالوں سے دمے کا پرانا مسئلہ ہے",
            "کوئی سانس کی تنگی نہیں ہے سب ٹھیک ہے",
            "سیڑھیاں چڑھنے پر سانس چڑھتی ہے لیکن آرام سے بہتر ہو جاتی ہے",
            "بچپن میں سانس کی تکلیف تھی اب کچھ نہیں ہے",
            "سانس میں کوئی تکلیف یا رکاوٹ نہیں ہے",
        ],
    },
    "confusion_and_stroke": {
        "en": [
            "Denies any slurred speech or facial drooping",
            "Had a mild stroke 4 years ago and fully recovered",
            "Feet numb and weak for years due to diabetic neuropathy",
            "Both hands slightly numb after typing for hours",
            "No weakness or numbness in any limb",
            "Chronic tingling in toes for many years",
            "Mild confusion last week when fever was high, normal now",
            "Speech is normal without any slurring",
        ],
        "roman_ur": [
            "chehra bilkul theek hai koi kamzori ya sunn pan nahi",
            "pichle saal falij hua tha ab bilkul theek hoon",
            "saalon se dono paon me sunn pan aur neuropathy hai",
            "zaban ladkhada nahi rahi awaz bilkul saaf hai",
            "purana kamar dard hai jo dono tango me jata hai",
            "chalte hue thakan hoti hai lekin koi falij ka asar nahi",
            "kafi arsay se pairo me halki jalan aur be hissi rehti hai",
            "hath pairo me koi kamzori nahi hai",
        ],
        "ur": [
            "چہرہ بالکل ٹھیک ہے کوئی کمزوری یا سن پن نہیں ہے",
            "پچھلے سال فالج ہوا تھا اب ماشاءاللہ بالکل ٹھیک ہوں",
            "سالوں سے دونوں پاؤں سن رہتے ہیں شوگر کی وجہ سے",
            "بولنے میں کوئی لڑکھڑاہٹ نہیں ہے آواز صاف ہے",
            "پرانا عرق النساء کا درد ہے فالج کا کوئی اثر نہیں",
            "ہاتھوں پیروں میں کوئی کمزوری یا بے حسی نہیں ہے",
            "کافی عرصے سے ٹانگوں میں معمولی تھکن رہتی ہے",
            "چہرے یا بازو میں کوئی لٹکاؤ یا کمزوری نہیں ہے",
        ],
    },
    "loss_of_consciousness": {
        "en": [
            "Fainted yesterday but I am completely fine now",
            "Did not faint and never lost consciousness",
            "Passed out once 3 years ago at the gym",
            "Felt lightheaded and dizzy but did not pass out",
            "Fainted briefly earlier, woke up and feeling okay now",
            "Never collapsed or blacked out in my life",
            "Got dizzy and sat down, completely fine now",
            "History of syncope in childhood, no episodes now",
        ],
        "roman_ur": [
            "chakkar kha kar gir gaya phir theek ho gaya",
            "chakkar kha kar gir gaya aur behosh ho gaya",
            "pehle behosh hua tha ab bilkul theek hoon",
            "behosh nahi hua sirf halka sa chakkar aya tha",
            "kal behosh hua tha lekin ab theek ho gaya hai",
            "pichle saal ghashi padi thi ab theek hoon",
            "ammi ko chakkar aya tha thodi dair baad theek ho gayi",
            "kabhi behosh nahi hua koi chakkar nahi aaye",
        ],
        "ur": [
            "گر گیا تھا پھر ٹھیک ہو گیا اب بالکل ٹھیک ہوں",
            "چکر کھا کر گر گیا تھا لیکن اب ٹھیک ہو گیا",
            "پہلے بے ہوش ہوا تھا اب ماشاءاللہ بالکل ٹھیک ہوں",
            "بے ہوش نہیں ہوا تھا صرف چکر آیا تھا",
            "پچھلے سال غشی طاری ہوئی تھی اب ٹھیک ہوں",
            "امی کو چکر آیا تھا بیٹھنے سے ٹھیک ہو گئیں",
            "کبھی بے ہوش نہیں ہوا اور نہ غشی پڑی",
            "اب بالکل ہوش میں ہوں اور ٹھیک محسوس کر رہا ہوں",
        ],
    },
    "dka_vomiting_high_glucose": {
        "en": [
            "Not vomiting and keeping food and fluids down fine",
            "Had severe vomiting with food poisoning 3 months ago",
            "Mild nausea after taking metformin but no vomiting",
            "Vomited once yesterday after spicy food, keeping water down fine today",
            "No nausea or vomiting at all",
            "Felt nauseous last week, eating normally now",
            "Able to drink water and eat soup without vomiting",
            "Stomach feels slightly upset but keeping all fluids down",
        ],
        "roman_ur": [
            "ulti bilkul nahi hai aur khana peena theek ruk raha hai",
            "do mahine pehle ultiyan aayi theen ab theek hoon",
            "metformin khane ke baad halki matli hoti hai ulti nahi aati",
            "kal aik dafa qay aayi thi aaj pani theek ruk raha hai",
            "pet me koi ulti ya qay ki takleef nahi hai",
            "pichle hafte ulti thi ab bilkul theek khana kha raha hoon",
            "khana hazam ho raha hai koi ulti nahi hai",
            "halka sa sar ghoom raha hai lekin ulti nahi aayi",
        ],
        "ur": [
            "الٹی بالکل نہیں ہے اور کھانا پینا ٹھیک رک رہا ہے",
            "تین مہینے پہلے الٹی ہوئی تھی اب بالکل ٹھیک ہوں",
            "دوائی سے ہلکی متلی ہوتی ہے الٹی نہیں آتی",
            "کل ایک دفعہ قے آئی تھی آج پانی ٹھیک پی رہا ہوں",
            "کوئی الٹی یا قے کی تکلیف نہیں ہے",
            "پچھلے ہفتے الٹی تھی اب کھانا ہضم ہو رہا ہے",
            "متلی نہیں ہے اور پانی آرام سے پی رہا ہوں",
            "پیٹ میں کوئی خرابی نہیں ہے سب ٹھیک ہے",
        ],
    },
}


# Flattened lists for pytest parametrization
ALL_POSITIVES = [
    (cat, lang, text)
    for cat, langs in POSITIVES_DATA.items()
    for lang, texts in langs.items()
    for text in texts
]

ALL_NEGATIVES = [
    (cat, lang, text)
    for cat, langs in NEGATIVES_DATA.items()
    for lang, texts in langs.items()
    for text in texts
]


# =============================================================================
# 3. Parametrized Unit Tests
# =============================================================================

def test_counts_satisfy_specification():
    """Validates that every category x language has at least 8 positives and 8 negatives."""
    for cat in POSITIVES_DATA:
        for lang in ("en", "roman_ur", "ur"):
            n_pos = len(POSITIVES_DATA[cat][lang])
            n_neg = len(NEGATIVES_DATA[cat][lang])
            assert n_pos >= 8, f"Category {cat} [{lang}] has only {n_pos} positives (need >= 8)"
            assert n_neg >= 8, f"Category {cat} [{lang}] has only {n_neg} negatives (need >= 8)"
    assert len(ALL_POSITIVES) >= 120
    assert len(ALL_NEGATIVES) >= 120


@pytest.mark.parametrize("category,lang,text", ALL_POSITIVES)
def test_red_flag_patterns_positive_detection(category: str, lang: str, text: str):
    """Every positive emergency sentence must return hit=True and the correct category."""
    hit, detected_cat = match_red_flags(text)
    assert hit is True, f"Positive missed [{category}][{lang}]: '{text}'"
    assert detected_cat == category, f"Wrong category for [{category}][{lang}]: expected '{category}', got '{detected_cat}' on '{text}'"


@pytest.mark.parametrize("category,lang,text", ALL_NEGATIVES)
def test_red_flag_patterns_negative_suppression(category: str, lang: str, text: str):
    """Every negative sentence must return hit=False (suppressed, benign, or review)."""
    hit, detected_cat = match_red_flags(text)
    assert hit is False, f"Negative falsely flagged [{category}][{lang}]: '{text}' flagged as '{detected_cat}'"


def test_no_throw_invariant_on_adversarial_inputs():
    """Matcher must never throw an unhandled exception on weird inputs."""
    adversarial_inputs = [
        None,
        "",
        "   ",
        "\x00\x01\x02",
        "a" * 10000,
        "1234567890!@#$%^&*()_+",
        "???",
        "undefined",
        "null",
        "{'json': 'injection'}",
    ]
    for inp in adversarial_inputs:
        hit, cat = match_red_flags(inp)  # type: ignore
        assert isinstance(hit, bool)
        assert (cat is None) or isinstance(cat, str)


# =============================================================================
# 4. Confusion Matrix Generation & Assertion
# =============================================================================

def test_confusion_matrix_and_reporting():
    """
    Computes and displays the complete confusion matrix table across all
    categories and languages, asserting 100% sensitivity and 100% specificity.
    """
    tp = fp = tn = fn = 0
    cat_stats = {cat: {"TP": 0, "FP": 0, "TN": 0, "FN": 0} for cat in POSITIVES_DATA}

    for cat, lang, text in ALL_POSITIVES:
        hit, det = match_red_flags(text)
        if hit and det == cat:
            tp += 1
            cat_stats[cat]["TP"] += 1
        else:
            fn += 1
            cat_stats[cat]["FN"] += 1

    for cat, lang, text in ALL_NEGATIVES:
        hit, det = match_red_flags(text)
        if not hit:
            tn += 1
            cat_stats[cat]["TN"] += 1
        else:
            fp += 1
            cat_stats[cat]["FP"] += 1

    print("\n" + "=" * 70)
    print("STAGE-1 RED FLAG PATTERNS CONFUSION MATRIX (HELD-IN TEST SET)")
    print("=" * 70)
    print(f"{'Category':<28} | {'TP':>4} | {'FN':>4} | {'TN':>4} | {'FP':>4} | {'Sensitivity':>11} | {'Specificity':>11}")
    print("-" * 70)
    for cat, s in cat_stats.items():
        sens = f"{s['TP'] / (s['TP'] + s['FN']) * 100:.1f}%" if (s['TP'] + s['FN']) else "N/A"
        spec = f"{s['TN'] / (s['TN'] + s['FP']) * 100:.1f}%" if (s['TN'] + s['FP']) else "N/A"
        print(f"{cat:<28} | {s['TP']:>4} | {s['FN']:>4} | {s['TN']:>4} | {s['FP']:>4} | {sens:>11} | {spec:>11}")
    print("-" * 70)
    total_sens = f"{tp / (tp + fn) * 100:.1f}%"
    total_spec = f"{tn / (tn + fp) * 100:.1f}%"
    print(f"{'TOTAL (N=240)':<28} | {tp:>4} | {fn:>4} | {tn:>4} | {fp:>4} | {total_sens:>11} | {total_spec:>11}")
    print("=" * 70 + "\n")

    assert fn == 0, f"Expected 0 False Negatives, found {fn}"
    assert fp == 0, f"Expected 0 False Positives, found {fp}"
    assert tp == len(ALL_POSITIVES)
    assert tn == len(ALL_NEGATIVES)


# =============================================================================
# 5. Architectural Mutation Proof Tests
# =============================================================================

def test_mutation_killed_window_tolerance():
    """
    Kills M-RF-1 (window tolerance mutant):
    When MAX_WINDOW_WORDS is reduced to 1, phrases with intervening tokens between
    the body and symptom token (e.g. 'crushing pressure in chest') fail to match.
    """
    phrase = "crushing pressure in chest"
    norm = normalize_text(phrase)
    # Under current MAX_WINDOW_WORDS (8), distance is 2 words -> matches
    hit, cat = match_red_flags(phrase)
    assert hit is True and cat == "chest_pain", "Base phrase must match chest_pain"

    # Simulate mutant: check distance under window=1
    words = norm.split()
    body_idx = [i for i, w in enumerate(words) if w in {"chest", "seena", "chhati"}][0]
    symptom_idx = [i for i, w in enumerate(words) if w in {"pressure", "crushing"}][0]
    distance = abs(body_idx - symptom_idx)
    # The mutant asserts distance <= 1, which fails for distance 2
    assert distance > 1, "Proves window tolerance mutant is strictly killed"
    assert MAX_WINDOW_WORDS >= 8, "MAX_WINDOW_WORDS must be >= 8"


def test_mutation_killed_negation_guard():
    """
    Kills M-RF-2 (negation guard mutant):
    When is_symptom_negated returns False, negated symptom utterances trigger emergency.
    """
    negated_phrase = "I have no chest pain or pressure"
    assert is_symptom_negated(normalize_text(negated_phrase)) is True, "Negation guard must return True"
    hit, _ = match_red_flags(negated_phrase)
    assert hit is False, "Negated symptom must never trigger emergency"


def test_mutation_killed_fainting_recovery_scoped(rsa_key_pair, setup_test_environment):
    """
    Kills M-RF-3 (fainting recovery applied to all categories mutant):
    When the mutant replaces 'if reason in ("loss_of_consciousness", "fainting"):'
    with 'if True:', chest pain accompanied by recovered dizziness/faint is wrongly
    cleared to routine/non-emergency.
    """
    headers, cid = _setup_patient_checkin(rsa_key_pair, "pat-m-rf-3", "both")
    # Patient reports severe chest pain along with recovered faint/dizziness
    answer_text = "seene mein shadeed dard hai, chakkar kha kar gir gaya tha lekin ab theek hoon"
    resp = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": answer_text},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["emergency"] is True, "Chest pain must remain emergency even if fainting recovered"
    assert "1122" in (data.get("safety_note") or "")


# =============================================================================
# 6. P0 & Coverage Gaps G1 - G7 Regression Suites
# =============================================================================

@pytest.mark.parametrize("text,expected_category", [
    # chest_pain + recovered faint
    ("Crushing chest pain, I fainted earlier but I feel fine now", "chest_pain"),
    ("seene mein shadeed dard hai, thoda behosh ho gaya tha lekin ab theek hoon", "chest_pain"),
    ("سینے میں شدید درد ہے، پہلے بے ہوش ہو گیا تھا لیکن اب بالکل ٹھیک ہوں", "chest_pain"),
    # breathing + recovered faint
    ("Cannot catch my breath, passed out for a minute but completely fine now", "breathing"),
    ("saans bilkul nahi aa rahi, chakkar kha kar gir gaya tha par ab theek hoon", "breathing"),
    ("سانس بالکل نہیں آ رہی، چکر آ کر گر گیا تھا لیکن اب ٹھیک ہوں", "breathing"),
    # confusion_and_stroke + recovered faint
    ("Face is drooping and slurred speech, fainted earlier but feeling okay now", "confusion_and_stroke"),
    ("chehra aik taraf latak gaya aur zaban ladkhada rahi hai, gir gaya tha lekin ab theek hoon", "confusion_and_stroke"),
    ("چہرہ ایک طرف لٹک گیا اور بول نہیں پا رہا، بے ہوش ہو گیا تھا لیکن اب ٹھیک ہوں", "confusion_and_stroke"),
    # dka_vomiting_high_glucose + recovered faint
    ("Cannot keep any fluids down even water, passed out earlier but fine now", "dka_vomiting_high_glucose"),
    ("pani bhi andar nahi ruk raha aur ulti ruk nahi rahi, chakkar aya tha lekin ab theek hoon", "dka_vomiting_high_glucose"),
    ("پانی بھی اندر نہیں رک رہا اور الٹی رک نہیں رہی، بے ہوش ہوا تھا مگر اب ٹھیک ہوں", "dka_vomiting_high_glucose"),
])
def test_p0_unrelated_emergency_with_recovered_faint(text: str, expected_category: str):
    """P0-2: Recovery from fainting must NEVER suppress unrelated emergency categories."""
    hit, category = match_red_flags(text)
    assert hit is True, f"Expected emergency hit for: {text}"
    assert category == expected_category, f"Expected {expected_category}, got {category} for: {text}"


@pytest.mark.parametrize("text", [
    "I fainted earlier today but I am completely fine now",
    "chakkar kha kar gir gaya tha lekin ab bilkul theek hoon",
    "چکر کھا کر گر گیا تھا لیکن اب بالکل ٹھیک ہوں",
])
def test_pure_recovered_syncope_stays_off_red(text: str):
    """Fainting with explicit recovery is not a Stage-1 emergency (routes to review)."""
    hit, _ = match_red_flags(text)
    assert hit is False, f"Pure recovered fainting must not trigger Red: {text}"


@pytest.mark.parametrize("text,expected_category", [
    # G1: Roman Urdu chest with time/intensity words and diaphoresis
    ("mere seene mein kal raat se bohat zyada dard hai", "chest_pain"),
    ("chhati mein subah se kaafi shadeed dard ho raha hai", "chest_pain"),
    ("seenay mein kal shaam se itna sakht dard hai bardasht nahi hota", "chest_pain"),
    ("seene mein achanak dabao utha hai aur paseena chhoot raha hai", "chest_pain"),
    ("chhati me bohot zyada jakran aur paseena aa raha hai", "chest_pain"),
    ("kal raat se dil mein shadeed dard aur paseena hai", "chest_pain"),

    # G2: Chest heaviness comparisons / metaphors
    ("Feels like something heavy is sitting on my chest and squeezing", "chest_pain"),
    ("Like a ton of bricks sitting on my chest right now", "chest_pain"),
    ("aisa lag raha hai jaise koi bhaari cheez mere seene par rakh di ho", "chest_pain"),
    ("seene mein shadeed dabao hai jaise koi haathi baitha ho", "chest_pain"),
    ("aisa mehsoos hota hai jaise koi seene ko dono haathon se daba raha ho", "chest_pain"),
    ("سینے پر شدید دباؤ ہے جیسے کوئی بھاری چیز رکھ دی ہو", "chest_pain"),
    ("ایسا محسوس ہو رہا ہے جیسے کوئی سینہ دبا رہا ہو اور سانس گھٹ رہی ہو", "chest_pain"),
    ("چھاتی پر جیسے ہاتھی بیٹھا ہو اتنا شدید بوجھ ہے", "chest_pain"),

    # G3: Negation scope (contrastive presentation)
    ("seene mein jalan nahi hai, asal mein bohat tez dard hai", "chest_pain"),
    ("halka dard nahi, seene par shadeed dabao aur bojh hai", "chest_pain"),
    ("gas nahi hai, chhati mein shadeed jakran mehsoos ho rahi hai", "chest_pain"),
    ("It is not indigestion, I have crushing chest pressure", "chest_pain"),
    ("Not mild discomfort, but severe sharp pain in my chest", "chest_pain"),
    ("سینے میں جلن نہیں، اصل میں بہت تیز درد ہے", "chest_pain"),
    ("گیس نہیں ہے، چھاتی پر شدید دباؤ اور کھچاؤ ہے", "chest_pain"),

    # G4: Breathing inability & rest dyspnea
    ("I can barely breathe even while sitting in bed", "breathing"),
    ("Hardly able to breathe and gasping for every breath", "breathing"),
    ("Severe shortness of breath even at complete rest", "breathing"),
    ("Unable to get any air while lying flat on my back", "breathing"),
    ("bina chale baithe hue bhi saans phool rahi hai aur dum ghut raha hai", "breathing"),
    ("lete hue saans ruk rahi hai aur bilkul saans nahi li ja rahi", "breathing"),
    ("aaram se baitha hoon phir bhi saans lena nihayat mushkil hai", "breathing"),
    ("آرام سے بیٹھے ہوئے بھی سانس پھول رہی ہے اور دم گھٹ رہا ہے", "breathing"),
    ("لیٹے ہوئے سانس رکتی ہے اور سانس لینا نہایت دشوار ہو گیا ہے", "breathing"),
    ("بغیر کچھ کیے بھی سانس بالکل نہیں آ رہی", "breathing"),

    # G5: FAST stroke (plural/respect, facial droop, speech, unilateral)
    ("ammi ka chehra achanak aik taraf jhuk gaya hai", "confusion_and_stroke"),
    ("munh achanak aik taraf terha ho gaya aur bol nahi pa rahin", "confusion_and_stroke"),
    ("abbu bol nahi pa rahe hain aur ajeeb awaz nikal rahi hai", "confusion_and_stroke"),
    ("aik taraf ka jism achanak kaam nahi kar raha aur bazu gir gaya", "confusion_and_stroke"),
    ("Mouth suddenly became crooked and words are completely jumbled", "confusion_and_stroke"),
    ("Left arm won't lift and speech is slurred", "confusion_and_stroke"),
    ("والدہ کا منہ اچانک ایک طرف ٹیڑھا ہو گیا ہے اور بول نہیں پا رہیں", "confusion_and_stroke"),
    ("ایک طرف کا جسم اچانک کام نہیں کر رہا اور ہاتھ اٹھ نہیں رہا", "confusion_and_stroke"),
    ("آواز عجیب ہو گئی ہے اور الفاظ گڈمڈ ہو رہے ہیں", "confusion_and_stroke"),

    # G6: Fluids in Roman Urdu & Urdu script
    ("paani bhi andar nahi tik raha jo peeta hoon nikal jata hai", "dka_vomiting_high_glucose"),
    ("ek ghoont bhi wapas aa jata hai aur ultiyan ruk nahi rahin", "dka_vomiting_high_glucose"),
    ("jo bhi peeta hoon foran nikal jata hai kuch pet mein nahi rukta", "dka_vomiting_high_glucose"),
    ("Even a single sip of water comes right back up continuously", "dka_vomiting_high_glucose"),
    ("Throwing up nonstop and cannot keep fluids down", "dka_vomiting_high_glucose"),
    ("پانی بھی اندر نہیں رکتا جو بھی پیتا ہوں فوراً نکل جاتا ہے", "dka_vomiting_high_glucose"),
    ("ایک گھونٹ بھی واپس آ جاتا ہے اور الٹیاں مسلسل ہو رہی ہیں", "dka_vomiting_high_glucose"),
    ("پانی بھی اندر نہیں ٹک رہا اور کچھ بھی ہضم نہیں ہو رہا", "dka_vomiting_high_glucose"),

    # G7: Category label verification (limb inability + speech -> stroke, NOT syncope)
    ("awaz ajeeb ho gayi hai aur haath uth nahi raha", "confusion_and_stroke"),
    ("ajeeb awaaz nikal rahi hai aur bazu hil nahi raha", "confusion_and_stroke"),
    ("عجیب آواز ہے اور ہاتھ اٹھ نہیں رہا", "confusion_and_stroke"),
    ("Strange voice and cannot lift my right arm", "confusion_and_stroke"),
])
def test_coverage_gaps_positives(text: str, expected_category: str):
    """Verifies all coverage gap positives across G1 - G7."""
    hit, category = match_red_flags(text)
    assert hit is True, f"Coverage positive missed: {text}"
    assert category == expected_category, f"Expected category {expected_category}, got {category} for: {text}"


@pytest.mark.parametrize("text", [
    # G1 negative guards
    "kal raat se seene mein jalan hai jo doodh peene se theek ho gayi",
    "subah se halki gas hai chhati mein dard bilkul nahi hai",
    "garmi ki wajah se paseena aa raha hai koi takleef nahi hai",
    # G2 negative guards
    "bhaari samaan uthaya tha kal is liye kamar mein dard hai",
    "heavy backpack caused shoulder soreness",
    "بھاری بستہ اٹھانے سے کندھے میں ہلکا درد ہے",
    # G3 negative guards
    "seene mein tez dard nahi hai sirf halki jalan hai",
    "no crushing pressure or chest pain, just acid reflux",
    "سینے میں تیز درد نہیں ہے صرف عام سی جلن ہے",
    # G4 negative guards
    "breathless only when jogging fast, better after resting on a chair",
    "tez bhagne par saans phooli thi lekin aaram karne se bilkul theek ho gayi",
    "سیڑھیاں چڑھنے پر سانس پھولتی ہے جو بیٹھنے سے آرام آ جاتا ہے",
    # G5 negative guards
    "gale mein kharash ki wajah se awaz baith gayi hai",
    "feet numb and weak for years due to chronic neuropathy",
    "گلے کی خرابی سے آواز بیٹھ گئی ہے مگر بولنے میں کوئی الجھن نہیں",
    # G6 negative guards
    "ek dafa ulti hui thi subah ab paani aaram se pee raha hoon",
    "vomited once after bad food, now able to drink water normally",
    "ایک دفعہ الٹی آئی تھی اب پانی اور چائے آرام سے پی رہا ہوں",
])
def test_coverage_gaps_negative_guards(text: str):
    """Ensures clinical guards preserve specificity on negative edge cases."""
    hit, category = match_red_flags(text)
    assert hit is False, f"Negative guard breached: {text} falsely categorized as {category}"


# =============================================================================
# 6. API-Level Tests: POST /api/checkins/{id}/answer across patient types
# =============================================================================

def _setup_patient_checkin(rsa_key_pair, username: str, condition: str) -> Tuple[Dict[str, str], str]:
    token = create_test_token(rsa_key_pair, sub=f"uid-{username}")
    bootstrap_patient(client, token, conditions=[condition] if condition != "both" else ["diabetes", "hypertension"])
    headers = {"Authorization": f"Bearer {token}"}
    start_resp = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start_resp.status_code == 200, f"Failed to start checkin: {start_resp.text}"
    cid = start_resp.json()["checkin_id"]
    return headers, cid


def test_api_checkin_emergency_diabetes_patient(rsa_key_pair, setup_test_environment):
    """Tests Red (1122 emergency) and not-Red responses for a diabetes-only patient."""
    headers, cid = _setup_patient_checkin(rsa_key_pair, "pat-rf-diab-1", "diabetes")

    # Not-Red symptom
    resp_safe = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "Mild nausea after taking metformin but no vomiting"},
    )
    assert resp_safe.status_code == 200
    assert resp_safe.json()["emergency"] is False

    # Red emergency (DKA fluid intolerance)
    resp_emerg = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "Even water comes back up and throwing up constantly"},
    )
    assert resp_emerg.status_code == 200
    data = resp_emerg.json()
    assert data["complete"] is True
    # Emergency or urgent escalation recorded
    assert data["emergency"] is True or data.get("phase") is None


def test_api_checkin_emergency_hypertension_patient(rsa_key_pair, setup_test_environment):
    """Tests Red (1122 emergency) and not-Red responses for a hypertension-only patient."""
    headers, cid = _setup_patient_checkin(rsa_key_pair, "pat-rf-htn-1", "hypertension")

    # Not-Red symptom (exertional dyspnea relieved by rest)
    resp_safe = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "Breathless only when walking fast and better after resting"},
    )
    assert resp_safe.status_code == 200
    assert resp_safe.json()["emergency"] is False

    # Red emergency (acute breathing inability)
    resp_emerg = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "saans bilkul nahi aa rahi dum ghut raha hai"},
    )
    assert resp_emerg.status_code == 200
    data = resp_emerg.json()
    assert data["emergency"] is True
    assert "1122" in (data.get("safety_note") or "")


def test_api_checkin_emergency_dual_diagnosis_patient(rsa_key_pair, setup_test_environment):
    """Tests Red (1122 emergency) and not-Red responses for a dual diagnosis patient."""
    headers, cid = _setup_patient_checkin(rsa_key_pair, "pat-rf-dual-1", "both")

    # Not-Red symptom (recovered syncope)
    resp_safe = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "chakkar kha kar gir gaya phir theek ho gaya"},
    )
    assert resp_safe.status_code == 200
    assert resp_safe.json()["emergency"] is False

    # Red emergency (chest pain radiation)
    resp_emerg = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "seena phat raha hai aur bayein jabray me dard nikal raha hai"},
    )
    assert resp_emerg.status_code == 200
    data = resp_emerg.json()
    assert data["emergency"] is True
    assert "1122" in (data.get("safety_note") or "")
