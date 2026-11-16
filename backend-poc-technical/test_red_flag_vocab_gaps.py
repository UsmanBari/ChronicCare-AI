"""
backend-poc-technical/test_red_flag_vocab_gaps.py

Tests for Item 4: Red-Flag Vocabulary Gaps.
Validates acute emergency detection and robust negation preservation across 3 categories:
1. Unconscious ("hosh nahi", "behosh pada", "be-hosh", "بے ہوش", "ہوش نہیں")
2. Seizure ("jhatke", "dora", "fit", "mirgi ka dora", "convulsion", "جھٹکے", "دورہ")
3. Breathless can't speak (inability to finish sentences / speak due to respiratory distress)

Across all three supported languages: English, Roman Urdu, and Urdu Script.
Each category has >= 10 positive emergency test phrases per language.
Negation and benign recovery cases are verified for all categories and languages
to ensure false Red does not rise.
"""
import pytest
from agents.red_flag_patterns import match, decide_red


# =============================================================================
# Category 1: Unconscious (Positive Acute Emergency Phrases)
# >= 10 phrases per language
# =============================================================================

UNCONSCIOUS_EN_PHRASES = [
    "he is unconscious and not responding",
    "patient found unconscious on the floor",
    "she became unconscious suddenly",
    "remains unconscious and cannot wake up",
    "has lost consciousness and no response",
    "passed out and still unconscious",
    "he is lying unconscious right now",
    "she has no consciousness at all",
    "unconscious since morning and won't wake",
    "father collapsed and is completely unconscious",
    "mother is unconscious and unresponsive",
]

UNCONSCIOUS_ROMAN_UR_PHRASES = [
    "unko bilkul hosh nahi hai",
    "ammi farsh par behosh padi hain",
    "abba ko koi hosh nahi hai",
    "mariz behosh pada hai aur uth nahi raha",
    "be-hosh pare hain aur aankhein nahi khol rahe",
    "unko hosh nahi aa raha hai",
    "hosh nahi hai bilkul bhi",
    "woh achanak behosh ho gaye aur jawab nahi de rahe",
    "farsh par behosh pada mila",
    "abhi tak hosh nahi aaya aur behosh pade hain",
    "zameen par behosh pari hain",
]

UNCONSCIOUS_URDU_SCRIPT_PHRASES = [
    "انہیں بالکل ہوش نہیں ہے",
    "امی فرش پر بے ہوش پڑی ہیں",
    "ابا کو کوئی ہوش نہیں ہے",
    "مریض بے ہوش پڑا ہے اور اٹھ نہیں رہا",
    "بے ہوش پڑے ہیں اور آنکھیں نہیں کھول رہے",
    "ہوش نہیں آ رہا بالکل بھی",
    "وہ اچانک بے ہوش ہو گئے اور جواب نہیں دے رہے",
    "فرش پر بے ہوش پڑا ملا",
    "ابھی تک ہوش نہیں آیا",
    "زمین پر بے ہوش پڑی ہیں",
    "کوئی ہوش نہیں ہے مریض کو",
]


# =============================================================================
# Category 2: Seizure (Positive Acute Emergency Phrases)
# >= 10 phrases per language
# =============================================================================

SEIZURE_EN_PHRASES = [
    "he is having an active seizure right now",
    "severe convulsions started suddenly",
    "she had an epileptic fit and is shaking",
    "whole body is jerking uncontrollably",
    "uncontrolled shaking and stiffness in limbs",
    "patient is having violent seizures",
    "repeated seizures without stopping",
    "having a severe seizure episode",
    "body convulsing and teeth clenching",
    "sudden onset of convulsions",
    "shaking violently with active seizure",
]

SEIZURE_ROMAN_UR_PHRASES = [
    "achanak mirgi ka dora pad gaya hai",
    "poore jism mein shadeed jhatke lag rahe hain",
    "unko dora pada hai aur jism ainth gaya hai",
    "haath paon mein jhatke shuru ho gaye hain",
    "mirgi ka dora aaya hai",
    "fit pad gaya hai aur hosh nahi hai",
    "jism mein jhatkay aa rahay hain",
    "bar bar dore pad rahe hain",
    "epilepsy ka fit pad gaya",
    "shadeed dora pad gaya hai",
    "jhatke lag rahe hain ruk nahi rahe",
]

SEIZURE_URDU_SCRIPT_PHRASES = [
    "اچانک مرگی کا دورہ پڑ گیا ہے",
    "پورے جسم میں شدید جھٹکے لگ رہے ہیں",
    "ان کو دورہ پڑا ہے اور جسم اینٹھ گیا ہے",
    "ہاتھ پاؤں میں جھٹکے شروع ہو گئے ہیں",
    "مرگی کا دورہ آیا ہے",
    "فٹ پڑ گیا ہے اور ہوش نہیں ہے",
    "جسم میں جھٹکے آ رہے ہیں",
    "بار بار دورے پڑ رہے ہیں",
    "مرگی کا فٹ پڑ گیا",
    "شدید دورہ پڑ گیا ہے",
    "جھٹکے لگ رہے ہیں رک نہیں رہے",
]


# =============================================================================
# Category 3: Breathless Can't Speak (Positive Acute Emergency Phrases)
# >= 10 phrases per language
# =============================================================================

BREATHLESS_CANT_SPEAK_EN_PHRASES = [
    "so breathless can't speak",
    "too breathless to talk to anyone",
    "struggling to speak due to shortness of breath",
    "can't finish a sentence because of breathing",
    "cannot speak in full sentences",
    "can barely talk because of severe breathlessness",
    "breathing so heavy cannot speak a word",
    "cannot get enough air to talk",
    "unable to speak due to breathlessness",
    "too short of breath to finish words",
    "gasping and unable to speak full sentences",
]

BREATHLESS_CANT_SPEAK_ROMAN_UR_PHRASES = [
    "saans itni tez hai ke ek jumla poora nahi bol pa rahin",
    "saans phool rahi hai baat nahi kar pa rahe",
    "saans ki wajah se bol nahi pa raha",
    "saans itni chadh gayi hai ke baat nahi ho rahi",
    "ek lafz bhi bolna mushkil ho raha hai saans ki wajah se",
    "bolte hue saans ukhad rahi hai",
    "saans ruk rahi hai bol nahi sakte",
    "saans lena bilkul na-mumkin ho gaya hai",
    "saans phoolne ki wajah se ek jumla nahi keh sakte",
    "saans ki wajah se baat karna muhaal ho gaya",
    "bolte hue saans phool jati hai lafz nahi nikalta",
]

BREATHLESS_CANT_SPEAK_URDU_SCRIPT_PHRASES = [
    "سانس اتنی تیز ہے کہ ایک جملہ پورا نہیں بول پا رہیں",
    "سانس پھول رہی ہے بات نہیں کر پا رہے",
    "سانس کی وجہ سے بول نہیں پا رہا",
    "سانس اتنی چڑھ گئی ہے کہ بات نہیں ہو رہی",
    "ایک لفظ بھی بولنا مشکل ہو رہا ہے سانس کی وجہ سے",
    "بولتے ہوئے سانس اکھڑ رہی ہے",
    "سانس رک رہی ہے بول نہیں سکتے",
    "سانس لینا بالکل ناممکن ہو گیا ہے",
    "سانس پھولنے کی وجہ سے ایک جملہ نہیں کہہ سکتے",
    "سانس کی وجہ سے بات کرنا محال ہو گیا ہے",
    "سانس کی تنگی کی وجہ سے بات نہیں کر پا رہے",
]


# =============================================================================
# Negation / Benign Cases (Must NOT trigger Red)
# Preserves negation across all categories and languages
# =============================================================================

NEGATED_UNCONSCIOUS_PHRASES = [
    ("en", "he did not lose consciousness at any point"),
    ("en", "never went unconscious, stayed awake the whole time"),
    ("en", "patient is fully conscious and alert"),
    ("en", "I did not pass out or faint"),
    ("roman_ur", "behosh nahi hua tha, hosh mein hoon"),
    ("roman_ur", "ammi bilkul theek hain, behosh nahi huin"),
    ("roman_ur", "hosh mein hai koi masla nahi"),
    ("roman_ur", "hosh nahi khoya tha"),
    ("ur", "بے ہوش نہیں ہوئے، بالکل ہوش میں ہیں"),
    ("ur", "امی ہوش میں ہیں اور باتیں کر رہی ہیں"),
    ("ur", "کوئی بے ہوشی نہیں ہوئی"),
]

NEGATED_SEIZURE_PHRASES = [
    ("en", "no seizures occurred today"),
    ("en", "denies any convulsions or fits"),
    ("en", "patient is completely free of seizures"),
    ("en", "did not have a seizure"),
    ("en", "childhood seizures resolved 15 years ago"),
    ("roman_ur", "koi jhatke nahi lage"),
    ("roman_ur", "mirgi ka dora nahi pada"),
    ("roman_ur", "kisi qism ka dora ya fit nahi aaya"),
    ("roman_ur", "jism mein jhatke nahi hain"),
    ("ur", "کوئی جھٹکے نہیں لگے"),
    ("ur", "دورہ نہیں پڑا ہے"),
    ("ur", "مرگی کا دورہ نہیں آیا"),
    ("ur", "کوئی دورے کی شکایت نہیں ہے"),
]

NEGATED_BREATHLESS_SPEAK_PHRASES = [
    ("en", "can speak in full sentences without trouble"),
    ("en", "breathing is fine and speaking normally"),
    ("en", "no trouble talking or breathing"),
    ("en", "not having trouble speaking from breathlessness"),
    ("roman_ur", "saans theek hai aaram se baat kar rahe hain"),
    ("roman_ur", "bolne mein koi masla nahi saans normal hai"),
    ("roman_ur", "baat karne mein koi takleef nahi"),
    ("ur", "سانس ٹھیک ہے آرام سے بات کر رہے ہیں"),
    ("ur", "بولنے میں کوئی مسئلہ نہیں ہے، سانس بالکل ٹھیک ہے"),
    ("ur", "بات کرنے میں کوئی دشواری نہیں ہے"),
]


# =============================================================================
# Test Execution
# =============================================================================

@pytest.mark.parametrize("text", UNCONSCIOUS_EN_PHRASES)
def test_unconscious_en_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect unconscious emergency in EN: {text}"
    assert cat == "loss_of_consciousness"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for EN: {text}"


@pytest.mark.parametrize("text", UNCONSCIOUS_ROMAN_UR_PHRASES)
def test_unconscious_roman_ur_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect unconscious emergency in Roman Urdu: {text}"
    assert cat == "loss_of_consciousness"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for Roman Urdu: {text}"


@pytest.mark.parametrize("text", UNCONSCIOUS_URDU_SCRIPT_PHRASES)
def test_unconscious_urdu_script_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect unconscious emergency in Urdu script: {text}"
    assert cat == "loss_of_consciousness"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for Urdu script: {text}"


@pytest.mark.parametrize("text", SEIZURE_EN_PHRASES)
def test_seizure_en_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect seizure in EN: {text}"
    assert cat == "loss_of_consciousness"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for EN: {text}"


@pytest.mark.parametrize("text", SEIZURE_ROMAN_UR_PHRASES)
def test_seizure_roman_ur_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect seizure in Roman Urdu: {text}"
    assert cat == "loss_of_consciousness"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for Roman Urdu: {text}"


@pytest.mark.parametrize("text", SEIZURE_URDU_SCRIPT_PHRASES)
def test_seizure_urdu_script_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect seizure in Urdu script: {text}"
    assert cat == "loss_of_consciousness"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for Urdu script: {text}"


@pytest.mark.parametrize("text", BREATHLESS_CANT_SPEAK_EN_PHRASES)
def test_breathless_cant_speak_en_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect breathless can't speak in EN: {text}"
    assert cat == "breathing"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for EN: {text}"


@pytest.mark.parametrize("text", BREATHLESS_CANT_SPEAK_ROMAN_UR_PHRASES)
def test_breathless_cant_speak_roman_ur_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect breathless can't speak in Roman Urdu: {text}"
    assert cat == "breathing"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for Roman Urdu: {text}"


@pytest.mark.parametrize("text", BREATHLESS_CANT_SPEAK_URDU_SCRIPT_PHRASES)
def test_breathless_cant_speak_urdu_script_triggers_red(text: str):
    hit, cat = match(text)
    assert hit is True, f"Failed to detect breathless can't speak in Urdu script: {text}"
    assert cat == "breathing"
    dec = decide_red(text)
    assert dec.is_red is True, f"decide_red failed for Urdu script: {text}"


@pytest.mark.parametrize("lang,text", NEGATED_UNCONSCIOUS_PHRASES)
def test_negated_unconscious_does_not_trigger_red(lang: str, text: str):
    hit, cat = match(text)
    dec = decide_red(text)
    assert dec.is_red is False, f"False Red on negated unconscious ({lang}): '{text}' (hit={hit}, cat={cat})"


@pytest.mark.parametrize("lang,text", NEGATED_SEIZURE_PHRASES)
def test_negated_seizure_does_not_trigger_red(lang: str, text: str):
    hit, cat = match(text)
    dec = decide_red(text)
    assert dec.is_red is False, f"False Red on negated seizure ({lang}): '{text}' (hit={hit}, cat={cat})"


@pytest.mark.parametrize("lang,text", NEGATED_BREATHLESS_SPEAK_PHRASES)
def test_negated_breathless_speak_does_not_trigger_red(lang: str, text: str):
    hit, cat = match(text)
    dec = decide_red(text)
    assert dec.is_red is False, f"False Red on negated breathless speaking ({lang}): '{text}' (hit={hit}, cat={cat})"
