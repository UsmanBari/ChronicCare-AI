"""
test_red_flags_harmless_answers.py

Regression test suite for Part G1:
Verifies that ordinary, harmless check-in answers never trigger false Red (1122) emergencies.
Includes:
1. At least 60 short ordinary check-in answers (20+ per language: English, Roman Urdu, Urdu script).
2. The specific reviewer test cases (posture-triggered numbness, food-triggered heartburn, 'no breathing trouble').
3. Every answer string from non-emergency personas in tests/sim/personas.json.
"""

import json
import os
import pytest
from agents.red_flag_patterns import match, match_categories

# -----------------------------------------------------------------------------
# 1. Short Ordinary Check-in Answers (English: 25)
# -----------------------------------------------------------------------------
ENGLISH_HARMLESS_ANSWERS = [
    "no",
    "no problem",
    "no breathing trouble",
    "no breathing trouble, no chest pain, feeling fine",
    "feeling fine",
    "doing good",
    "all is well",
    "no chest pain",
    "no shortness of breath",
    "no pain at all",
    "blood sugar is 115",
    "my bp was 120/80 today",
    "i took my medicines",
    "slept well last night",
    "no issues to report",
    "feeling much better than yesterday",
    "none",
    "eating normally",
    "walking 30 minutes every morning",
    "no dizziness or fainting",
    "no nausea or vomiting",
    "hand feels slightly numb when I sleep on it",
    "just mild heartburn after spicy food",
    "everything is normal",
    "thanks, I am alright",
    # Additional broad negation frames (G1b)
    "I don't have any chest pain",
    "I didn't have any shortness of breath",
    "I have no pain in my chest",
    "there is no problem with my breathing",
    "not feeling any dizziness or weakness",
    "no sign of any trouble",
    "I'm not having any chest pressure",
    "free of any symptoms today",
    "I don't have shortness of breath",
    "there is no chest pain at all",
    "I have no difficulty breathing",
    "I'm not having trouble breathing",
    "not feeling any chest discomfort",
    "no sign of vomiting or nausea",
    "I didn't faint or feel dizzy",
    "there is no weakness in my arms",
    "I don't have weakness or numbness",
    "I have no trouble speaking",
    "free of chest tightness",
    "I'm not having any stroke symptoms",
    "no chest pain whatsoever",
    "there is no vomiting today",
    "not feeling breathless",
    "I have no complaints",
    "I don't have any severe headache",
]

# -----------------------------------------------------------------------------
# 2. Short Ordinary Check-in Answers (Roman Urdu: 50)
# -----------------------------------------------------------------------------
ROMAN_URDU_HARMLESS_ANSWERS = [
    "nahi",
    "sab theek hai",
    "koi masla nahi",
    "koi takleef nahi",
    "saans theek hai",
    "seene mein koi dard nahi",
    "theek hoon shukriya",
    "pehle se behtar",
    "dawai le li",
    "120/80",
    "sugar 110 thi",
    "haath thoda sunn ho jata hai jab der tak mobile chalata hoon",
    "seene mein jalan hoti hai tez mirch wala khana kha kar",
    "aaj sugar 125 aayi",
    "sab khairiyat hai",
    "koi dushwari nahi hai",
    "subah nashta kar liya tha",
    "tabiyat bilkul theek hai",
    "dawa waqt par kha raha hoon",
    "chakkar nahi aaye",
    "ulti nahi hui",
    "seene mein koi bojh nahi hai",
    "saans aaram se aa rahi hai",
    "paaon mein koi dard nahi",
    "theek chal raha hai sab",
    # Additional broad negation frames (G1b)
    "mujhe koi seene mein dard nahi",
    "mujhe koi saans ki takleef nahi",
    "seene mein dard bilkul nahi",
    "saans mein koi masla nahi hai",
    "mujhe koi chakkar nahi aaye",
    "kamzori bilkul nahi",
    "mujhe koi ulti nahi aayi",
    "seene par dabao bilkul nahi hai",
    "saans ki tangi bilkul nahi",
    "mujhe koi falij ka asar nahi",
    "hath paon mein koi kamzori nahi hai",
    "mujhe koi takleef nahi hai",
    "dard bilkul nahi hai",
    "seene mein bojh bilkul nahi",
    "saans mein dushwari nahi hai",
    "mujhe koi be hoshi nahi hui",
    "chakkar bilkul nahi aaye",
    "ulti bilkul nahi aayi",
    "mujhe koi jalan nahi hai",
    "saans lene mein koi pareshani nahi",
    "mujhe koi dushwari nahi",
    "seene ka dard nahi hai",
    "falij ka koi masla nahi",
    "bolne mein koi dikkat nahi hai",
    "sab mamool ke mutabiq hai",
]

# -----------------------------------------------------------------------------
# 3. Short Ordinary Check-in Answers (Urdu Script: 50)
# -----------------------------------------------------------------------------
URDU_HARMLESS_ANSWERS = [
    "نہیں",
    "سب ٹھیک ہے",
    "کوئی مسئلہ نہیں",
    "کوئی تکلیف نہیں",
    "سانس بالکل ٹھیک ہے",
    "سینے میں کوئی درد نہیں",
    "ٹھیک ہوں شکریہ",
    "پہلے سے بہتر",
    "دوائی وقت پر لے لی",
    "شوگر 110 ہے",
    "بلڈ پریشر 120/80 تھا",
    "سب خیریت ہے",
    "طبیعت بحال ہے",
    "کوئی دشواری نہیں ہوئی",
    "کوئی چکر یا بے ہوشی نہیں",
    "الٹی یا متلی نہیں ہے",
    "رات کو نیند اچھی آئی",
    "کھانا معمول کے مطابق کھایا",
    "صبح سیر کی تھی",
    "سینہ اور سانس بالکل نارمل ہے",
    "ہاتھ پاؤں ٹھیک کام کر رہے ہیں",
    "تیز مرچ والا کھانا کھانے سے تھوڑی جلن ہوتی ہے",
    "دیر تک بیٹھنے سے کبھی کبھی پاؤں سو جاتا ہے",
    "شکریہ میں خیریت سے ہوں",
    "سب کچھ درست ہے",
    # Additional broad negation frames (G1b)
    "مجھے کوئی سینے میں درد نہیں ہے",
    "مجھے کوئی سانس کی تکلیف نہیں",
    "سینے میں درد بالکل نہیں",
    "سانس میں کوئی مسئلہ نہیں ہے",
    "مجھے کوئی چکر نہیں آئے",
    "کمزوری بالکل نہیں ہے",
    "مجھے کوئی الٹی نہیں آئی",
    "سینے پر دباؤ بالکل نہیں ہے",
    "سانس کی تنگی بالکل نہیں",
    "مجھے کوئی فالج کا اثر نہیں",
    "ہاتھ پاؤں میں کوئی کمزوری نہیں ہے",
    "مجھے کوئی تکلیف نہیں ہے",
    "درد بالکل نہیں ہے",
    "سینے میں بوجھ بالکل نہیں",
    "سانس میں دشواری نہیں ہے",
    "مجھے کوئی بے ہوشی نہیں ہوئی",
    "چکر بالکل نہیں آئے",
    "الٹی بالکل نہیں آئی",
    "مجھے کوئی جلن نہیں ہے",
    "سانس لینے میں کوئی پریشانی نہیں ہے",
    "مجھے کوئی دشواری نہیں ہے",
    "سینے کا درد نہیں ہے",
    "فالج کا کوئی مسئلہ نہیں ہے",
    "بولنے میں کوئی دقت نہیں ہے",
    "سب معمول کے مطابق ہے",
]


@pytest.mark.parametrize("answer", ENGLISH_HARMLESS_ANSWERS)
def test_english_harmless_answers_not_red(answer: str):
    is_red, category = match(answer)
    assert not is_red, f"English answer falsely triggered RED ({category}): {answer}"


@pytest.mark.parametrize("answer", ROMAN_URDU_HARMLESS_ANSWERS)
def test_roman_urdu_harmless_answers_not_red(answer: str):
    is_red, category = match(answer)
    assert not is_red, f"Roman Urdu answer falsely triggered RED ({category}): {answer}"


@pytest.mark.parametrize("answer", URDU_HARMLESS_ANSWERS)
def test_urdu_harmless_answers_not_red(answer: str):
    is_red, category = match(answer)
    assert not is_red, f"Urdu script answer falsely triggered RED ({category}): {answer}"


def test_reviewer_p0_false_positive_cases():
    """Specific reviewer test cases from Part G1 problem description."""
    # 1. 'no breathing trouble'
    assert match("no breathing trouble")[0] is False
    assert match("no breathing trouble, no chest pain, feeling fine")[0] is False

    # 2. Benign posture/activity numb hand
    assert match("haath thoda sunn ho jata hai jab der tak mobile chalata hoon")[0] is False

    # 3. Benign food-triggered jalan
    assert match("seene mein jalan hoti hai tez mirch wala khana kha kar")[0] is False


def test_all_non_emergency_personas_in_personas_json():
    """
    Every answer string in tests/sim/personas.json that belongs to a persona
    whose expected level is NOT emergency must NEVER be Red.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    personas_path = os.path.join(repo_root, "tests", "sim", "personas.json")
    if not os.path.exists(personas_path):
        # Fallback to local dir if running from root
        personas_path = os.path.join("tests", "sim", "personas.json")

    assert os.path.exists(personas_path), f"personas.json not found at {personas_path}"

    with open(personas_path, "r", encoding="utf-8") as f:
        personas = json.load(f)

    non_emergency_count = 0
    checked_answers_count = 0

    for persona in personas:
        pid = persona.get("id") or persona.get("persona_id")
        expected_level = (
            persona.get("expected_triage_level")
            or persona.get("expected_triage")
            or persona.get("expected_level")
            or ""
        ).lower()

        # Skip personas whose ground truth is emergency / red
        if expected_level in ("emergency", "red"):
            continue

        non_emergency_count += 1
        answers = list(persona.get("answers") or [])
        dialogue = (
            persona.get("conversation")
            or persona.get("dialogue")
            or persona.get("turns")
            or []
        )
        for turn in dialogue:
            user_input = turn.get("user") or turn.get("patient") or turn.get("answer") or ""
            if user_input and isinstance(user_input, str):
                answers.append(user_input)

        for user_input in answers:
            if not user_input or not isinstance(user_input, str):
                continue

            checked_answers_count += 1
            is_red, category = match(user_input)
            assert not is_red, (
                f"Persona {pid} (expected: {expected_level}) had answer falsely flagged as RED ({category}): {user_input}"
            )

    assert non_emergency_count > 0, "No non-emergency personas found"
    assert checked_answers_count > 0, "No patient answers checked from personas"


# -----------------------------------------------------------------------------
# 5. Coverage Gap Tests (G1b)
# -----------------------------------------------------------------------------

def test_cyanosis_triggers_breathing_red():
    """Cyanosis words alone count as breathing-Red (G1b)."""
    cases = [
        "lips turning blue",
        "bluish lips",
        "hont neelay par gaye hain",
        "hont neelay ho rahe hain",
        "neelay hont",
        "ہونٹ نیلے پڑ رہے ہیں",
        "نیلے ہونٹ",
    ]
    for text in cases:
        is_red, cat = match(text)
        assert is_red, f"Expected RED for cyanosis: {text}"
        assert cat in ("breathing", "breathing_difficulty"), f"Expected breathing category, got {cat} for {text}"


def test_fluid_failure_triggers_dka_red():
    """Roman Urdu fluid failure triggers dka_vomiting_high_glucose Red (G1b)."""
    cases = [
        "paani bhi nahi tikta",
        "pani nahi rukta",
        "pani andar nahi rehta",
        "nothing stays down",
        "water keeps coming back up",
        "ek ghoont bhi andar nahi rehta",
    ]
    for text in cases:
        is_red, cat = match(text)
        assert is_red, f"Expected RED for fluid failure: {text}"
        assert cat in ("dka_vomiting_high_glucose", "vomiting", "dka"), f"Expected DKA/fluids category, got {cat} for {text}"


def test_stroke_descriptors_trigger_stroke_red():
    """FAST stroke descriptors trigger stroke_fast Red (G1b)."""
    cases = [
        "daayan hissa sunn ho gaya hai",
        "baayan hissa sunn hai",
        "achanak munh se raal nikal rahi hai",
        "sudden drooling from mouth",
        "my left arm is completely useless",
        "speech went weird suddenly",
        "voice became strange all of a sudden",
        "دایاں حصہ سن ہو گیا",
        "اچانک منہ سے رال بہہ رہی ہے",
    ]
    for text in cases:
        is_red, cat = match(text)
        assert is_red, f"Expected RED for stroke: {text}"
        assert cat in ("stroke_fast", "confusion_and_stroke", "stroke"), f"Expected stroke category, got {cat} for {text}"

