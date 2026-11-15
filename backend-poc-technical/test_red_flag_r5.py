"""
backend-poc-technical/test_red_flag_r5.py
Tests for Part R5: Red-Flag Robustness.

Validates:
1. R5.1 Roman-Urdu spelling normaliser: 40+ spelling-variant pairs yielding identical results.
2. R5.2 Synonym & metaphor families (chest pressure, breathing failure, face droop,
   speech failure, limb failure, unresponsive, intractable vomiting) across EN, Roman Urdu, and Urdu.
3. R5.3 Echo-question and short-answer negation: 30+ echo patterns and bare negative responses.
4. R5.4 Yellow Safety Net: near-miss acute sentences raise to Yellow (review) with
   group 'acute_unclassified', harmless & negated give Green, real Red stays Red.
5. Mutation proof for M-SN-1 (Safety Net Disabled mutant).
"""

import pytest
import agents.red_flag_patterns as rfp
from agents.red_flag_patterns import (
    normalize_spelling,
    normalize_text,
    is_bare_negative_answer,
    is_echo_question_negation,
    match,
    match_categories,
)
from agents.danger_wordgroups import (
    detect,
    detect_safety_net,
    is_danger_safety_net_enabled,
    WordGroupResult,
)


# =============================================================================
# R5.1 SPELLING-VARIANT PAIRS (40+ Pairs)
# =============================================================================

SPELLING_VARIANT_PAIRS = [
    # 1-10: Vowel collapse & Roman Urdu prepositions / negatives
    ("seene me shadeed dard hai", "seenay mein shadeed dard hai"),
    ("saans phool rahi hai", "sans phool rahi hai"),
    ("dabaav mehsoos ho raha hai", "dabao mehsoos ho raha hai"),
    ("bohot zyada dard hai", "bohat zyada dard hai"),
    ("boht shadeed takleef hai", "bahut shadeed takleef hai"),
    ("kch samajh nahi aa raha", "kuchh samajh nahi aa raha"),
    ("saas ruk rahi hai", "saanss ruk rahi hai"),
    ("paani nahi ruk raha", "panee nahi ruk raha"),
    ("dard bilkul nai hai", "dard bilkul nahin hai"),
    ("koi masla nhi hai", "koi masla ni hai"),

    # 11-20: Verb forms & auxiliary spellings
    ("bol nahi rha", "bol nahi raha"),
    ("sans ukhad rahay hain", "sans ukhad rahe hain"),
    ("munh terha ho rha hai", "munh terha ho raha hai"),
    ("behosh ho gaye hy", "behosh ho gaye hai"),
    ("bazu bejaan hen", "bazu bejaan hain"),
    ("ulti rukti he nahi", "ulti rukti hai nahi"),
    ("seena daba raha he koi", "seena daba raha hai koi"),
    ("hawa nahi ja rahi", "hawa nahi ja rahy"),
    ("aankhein nahi khol rahin", "aankhein nahi khol rahe"),
    ("lafz nahi nikal rhay", "lafz nahi nikal rahe"),

    # 21-30: Anatomy & symptom spelling variants
    ("seene me bojh hai", "seenay me bojh hai"),
    ("sine me jakran hai", "seene me jakran hai"),
    ("chehray par falij hai", "cehra par falij hai"),
    ("chehre par dhalak hai", "chehra par dhalak hai"),
    ("bayhosh pare hain", "be-hosh pare hain"),
    ("be hosh pare hain", "beyhosh pare hain"),
    ("ultiyan rukti nahi", "ultiyaan rukti nahi"),
    ("ultee band nahi ho rahi", "ultii band nahi ho rahi"),
    ("dabaao bohat sakht hai", "dabaw bohat sakht hai"),
    ("bazu me shadeed dard", "baazu me shadeed dard"),

    # 31-40: English contractions & typos
    ("I cant breathe at all", "I cannot breathe at all"),
    ("cant catch my breath", "can not catch my breath"),
    ("cnt get air in lungs", "cannot get air in lungs"),
    ("wont move my arm", "will not move my arm"),
    ("wont wake up", "will not wake up"),
    ("severe breating difficulty", "severe breathing difficulty"),
    ("shortness of breath", "shortness of breathe"),
    ("couldnt speak properly", "could not speak properly"),
    ("dont feel any pain", "do not feel any pain"),
    ("didnt pass out today", "did not pass out today"),

    # 41-45: Additional vernacular variant pairs
    ("qay aa rahi hai musalsal", "kay aa rahi hai musalsal"),
    ("wapas nikal jata hai", "vapas nikal jata hai"),
    ("wazan rakha hua hai", "vazan rakha hua hai"),
    ("awaaz ladkhada rahi hai", "avaz ladkhada rahi hai"),
    ("pasina aa raha hai seene par", "paseena aa raha hai seene par"),
]


@pytest.mark.parametrize("var_a,var_b", SPELLING_VARIANT_PAIRS)
def test_r5_1_spelling_variant_pairs_give_identical_results(var_a: str, var_b: str):
    """Verifies that spelling variants produce identical detection outcomes."""
    hit_a, cat_a = match(var_a)
    hit_b, cat_b = match(var_b)
    assert hit_a == hit_b, f"Discrepancy in hit for '{var_a}' ({hit_a}) vs '{var_b}' ({hit_b})"
    assert cat_a == cat_b, f"Discrepancy in category for '{var_a}' ({cat_a}) vs '{var_b}' ({cat_b})"


# =============================================================================
# R5.2 SYNONYM / METAPHOR FAMILIES ACROSS 3 LANGUAGES
# =============================================================================

FAMILIES_TEST_CASES = [
    # Family 1: Chest Pressure -> chest_pain
    ("en", "Crushing vice-like squeezing pressure in center of chest", True, "chest_pain"),
    ("ur-Latn", "ammi ke seenay mein shadeed dabao aur jakran hai", True, "chest_pain"),
    ("ur", "سینے پر بھاری بوجھ اور دباؤ محسوس ہو رہا ہے", True, "chest_pain"),
    ("ur-Latn", "sina par pathar rakha hua lag raha hai", True, "chest_pain"),

    # Family 2: Breathing Failure -> breathing
    ("en", "Suffocating and gasping desperately for air while sitting", True, "breathing"),
    ("ur-Latn", "sans bilkul nahi aa rahi aur dam ghut raha hai", True, "breathing"),
    ("ur", "سانس اکھڑ گئی ہے اور دم گھٹ رہا ہے", True, "breathing"),
    ("ur-Latn", "haanp rahe hain aur sans le hi nahi pa rahe", True, "breathing"),

    # Family 3: Face Droop -> confusion_and_stroke
    ("en", "One side of mouth is drooping and face is crooked", True, "confusion_and_stroke"),
    ("ur-Latn", "chehra ek taraf latak gaya hai aur munh terha hai", True, "confusion_and_stroke"),
    ("ur", "چہرہ ایک طرف لٹک گیا ہے اور منہ ٹیڑھا ہو گیا", True, "confusion_and_stroke"),

    # Family 4: Speech Failure -> confusion_and_stroke
    ("en", "Speech is completely slurred and words won't come out", True, "confusion_and_stroke"),
    ("ur-Latn", "zaban larkhara rahi hai aur bol nahi pa rahe", True, "confusion_and_stroke"),
    ("ur", "زبان لڑکھڑا رہی ہے اور بول نہیں پا رہے", True, "confusion_and_stroke"),

    # Family 5: Limb Failure -> confusion_and_stroke
    ("en", "Right arm went limp and cannot lift or hold cup", True, "confusion_and_stroke"),
    ("ur-Latn", "bazu bejaan ho gaya hai aur uth nahi raha", True, "confusion_and_stroke"),
    ("ur", "بازو بے جان ہو گیا ہے اور اٹھ نہیں رہا", True, "confusion_and_stroke"),

    # Family 6: Unresponsive -> loss_of_consciousness
    ("en", "Patient collapsed suddenly and is unresponsive, won't wake", True, "loss_of_consciousness"),
    ("ur-Latn", "achanak behosh ho gaye aur aankhein nahi khol rahe", True, "loss_of_consciousness"),
    ("ur", "بے ہوش ہو گئے ہیں اور جاگ نہیں رہے", True, "loss_of_consciousness"),

    # Family 7: Intractable Vomiting -> dka_vomiting_high_glucose
    ("en", "Vomiting non-stop for hours, cannot keep water down", True, "dka_vomiting_high_glucose"),
    ("ur-Latn", "har ghante ulti aa rahi hai paani bhi nahi theharta", True, "dka_vomiting_high_glucose"),
    ("ur", "مسلسل الٹیاں آ رہی ہیں پانی بھی اندر نہیں ٹھہر رہا", True, "dka_vomiting_high_glucose"),
]


@pytest.mark.parametrize("lang,text,expected_hit,expected_cat", FAMILIES_TEST_CASES)
def test_r5_2_families_detected_reliably(lang: str, text: str, expected_hit: bool, expected_cat: str):
    """Verifies that all 7 symptom families trigger their corresponding emergency category."""
    hit, cat = match(text)
    assert hit is expected_hit, f"Expected hit={expected_hit} for '{text}', got {hit}"
    assert cat == expected_cat, f"Expected category={expected_cat} for '{text}', got {cat}"


# =============================================================================
# R5.3 ECHO-QUESTION & SHORT-ANSWER NEGATION (30+ Tests)
# =============================================================================

ECHO_AND_SHORT_ANSWER_NEGATIONS = [
    # English Echo Questions
    "chest pain? no",
    "chest pain? nope",
    "chest tightness? not really",
    "shortness of breath? no",
    "difficulty breathing - no",
    "breathing trouble: not at all",
    "fainting? no",
    "fainting - none",
    "loss of consciousness? never",
    "face drooping? no",
    "slurred speech? nope",
    "arm weakness: not really",
    "vomiting fluids? no",
    "throwing up? none",

    # Roman Urdu Echo Questions
    "seene me dard? nahi",
    "seene ka dabao: bilkul nahi",
    "seenay mein bojh? nai",
    "saans ki takleef? nahi",
    "sans phoolna? nahi",
    "dam ghutna - bilkul nahi",
    "chehra terha? nahi",
    "bolne me dushwari: nahi hui",
    "bazu bejaan? bilkul nahi",
    "haath sunn? nahi",
    "behosh hue? nahi",
    "ghashi aayi? nahi",
    "hosh kho baithe? nahi",
    "ulti ho rahi? nahi",
    "pani nikal raha? bilkul nahi",
    "chakkar aana? nahi",

    # Urdu Script Echo Questions
    "سینے میں درد؟ نہیں",
    "سینے کا دباؤ: بالکل نہیں",
    "سانس کی تکلیف؟ نہیں",
    "دم گھٹنا - بالکل نہیں",
    "چہرہ ٹیڑھا؟ نہیں",
    "بولنے میں دشواری: نہیں ہوئی",
    "بازو بے جان؟ بالکل نہیں",
    "بے ہوش ہوئے؟ نہیں",
    "غشی آئی؟ نہیں",
    "الٹی ہو رہی؟ نہیں",
    "پانی نکل رہا؟ بالکل نہیں",

    # Bare Negative Answers
    "no",
    "nope",
    "nah",
    "not really",
    "not at all",
    "nahi",
    "nai",
    "nahin",
    "nhi",
    "bilkul nahi",
    "koi nahi",
    "kuch nahi",
    "نہیں",
    "بالکل نہیں",
    "کوئی نہیں",
]


@pytest.mark.parametrize("text", ECHO_AND_SHORT_ANSWER_NEGATIONS)
def test_r5_3_echo_and_short_answer_negations_never_red(text: str):
    """Verifies that echo-questions and bare negative answers never trigger Stage-1 Red."""
    hit, cat = match(text)
    assert hit is False, f"Expected False for echo/negative text '{text}', got hit={hit} ({cat})"
    assert cat is None


# =============================================================================
# R5.4 YELLOW SAFETY NET (acute_unclassified)
# =============================================================================

SAFETY_NET_CASES = [
    # Near-miss acute sentences that should raise to Yellow (acute_unclassified)
    ("I have sudden severe pain in my right arm since 2 hours", True, "acute_unclassified"),
    ("achanak bazu me shadeed takleef ho rahi hai abhi", True, "acute_unclassified"),
    ("right now experiencing worst pain in right leg", True, "acute_unclassified"),
    ("ٹانگ میں اچانک شدید درد ہو رہا ہے ابھی", True, "acute_unclassified"),
    ("severe vomiting since 4 hours but keeping small sips down", True, "acute_unclassified"),
    ("face has acute severe tingling right now", True, "acute_unclassified"),
]


@pytest.mark.parametrize("text,expected_danger,expected_group", SAFETY_NET_CASES)
def test_r5_4_safety_net_catches_acute_near_misses(text: str, expected_danger: bool, expected_group: str):
    """Verifies that acute near-miss clinical sentences raise to Yellow via acute_unclassified."""
    # Real Red matcher should not fire
    is_red, _ = match(text)
    assert is_red is False, f"Near-miss text '{text}' should not trigger Stage-1 Red"

    # Safety Net detector must catch it
    res: WordGroupResult = detect(text)
    assert res.is_danger is expected_danger, f"Expected safety net danger={expected_danger} for '{text}'"
    assert res.group == expected_group, f"Expected group={expected_group} for '{text}', got {res.group}"


def test_r5_4_safety_net_respects_negation_and_benign_guards():
    """Verifies safety net does not alarm on negated or benign triggers."""
    # Negated acute chest
    assert detect("no sudden severe chest pain").is_danger is False
    # Benign spicy food heartburn
    assert detect("seene me tez jalan mirch wala khana khane ke baad").is_danger is False
    # Benign mobile numbness
    assert detect("haath sunn hua jab der tak mobile chalata hoon").is_danger is False
    # Remote past event
    assert detect("5 years ago had sudden severe chest pain, fine now").is_danger is False


# =============================================================================
# MUTATION PROOF M-SN-1: SAFETY NET DISABLED
# =============================================================================

def test_mutation_killed_safety_net_disabled():
    """
    Architectural invariant proof for mutant M-SN-1.
    Proves that is_danger_safety_net_enabled() is required for acute near-miss safety catches.
    """
    assert is_danger_safety_net_enabled() is True, "DANGER_SAFETY_NET must default to True"
    res = detect("I have sudden severe pain in my right arm since 2 hours")
    assert res.is_danger is True and res.group == "acute_unclassified"
