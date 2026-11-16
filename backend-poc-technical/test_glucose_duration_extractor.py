"""
Tests for P1-3: Glucose extraction with duration qualifier numbers.
Ensures that duration numbers ("2 hours after lunch it was 165") do not
trigger ambiguity rejection or cause missing_reading=True.
Tests 3 languages (EN, Roman Urdu, Urdu script), >= 10 phrasings each.
"""
import pytest
from agents.answer_understanding import parse_number, strip_duration_phrases, detect_glucose_context
from agents.answer_validation import validate_glucose_input
from agents.interview_v3_runner import start_v3_session, next_turn


EN_PHRASINGS = [
    ("2 hours after lunch it was 165", 165.0, "after_meal"),
    ("2 hours after dinner it was 140", 140.0, "after_meal"),
    ("1.5 hours after breakfast 130", 130.0, "after_meal"),
    ("30 mins after meal it was 155", 155.0, "after_meal"),
    ("two hours after eating was 175", 175.0, "after_meal"),
    ("before breakfast was 95", 95.0, "fasting"),
    ("fasting reading was 105", 105.0, "fasting"),
    ("before meal it was 110", 110.0, "fasting"),
    ("45 minutes after lunch 185 mg/dl", 185.0, "after_meal"),
    ("post meal 2 hours 160", 160.0, "after_meal"),
    ("1 hour after dinner 145", 145.0, "after_meal"),
    ("fasting 100 mg/dl", 100.0, "fasting"),
]

ROMAN_URDU_PHRASINGS = [
    ("khane ke 2 ghante baad 165 thi", 165.0, "after_meal"),
    ("nashtay ke 2 ghante baad 180", 180.0, "after_meal"),
    ("do ghante baad 150 thi", 150.0, "after_meal"),
    ("lunch ke 2 ghantay baad 170", 170.0, "after_meal"),
    ("dinner ke baad 140 aai thi", 140.0, "after_meal"),
    ("nashte ke 2 ghante baad 160 mg", 160.0, "after_meal"),
    ("khali pait 110 aayi thi", 110.0, "fasting"),
    ("nahar munh 102 thi", 102.0, "fasting"),
    ("khali pet reading 108 thi", 108.0, "fasting"),
    ("nashte se pehle 95 thi", 95.0, "fasting"),
    ("khane ke aadha ghanta baad 190", 190.0, "after_meal"),
    ("aik ghante baad 155", 155.0, "after_meal"),
]

URDU_SCRIPT_PHRASINGS = [
    ("کھانے کے 2 گھنٹے بعد 165 تھی", 165.0, "after_meal"),
    ("ناشتے کے 2 گھنٹے بعد 180", 180.0, "after_meal"),
    ("دو گھنٹے بعد 150 تھی", 150.0, "after_meal"),
    ("دوپہر کے کھانے کے دو گھنٹے بعد 170", 170.0, "after_meal"),
    ("رات کے کھانے کے 2 گھنٹے بعد 145", 145.0, "after_meal"),
    ("30 منٹ بعد 160 تھی", 160.0, "after_meal"),
    ("خالی پیٹ 110", 110.0, "fasting"),
    ("نہار منہ 105 تھی", 105.0, "fasting"),
    ("ناشتے سے پہلے 98 تھی", 98.0, "fasting"),
    ("کھانے سے پہلے 112 تھی", 112.0, "fasting"),
    ("ایک گھنٹہ بعد 155 آئی تھی", 155.0, "after_meal"),
    ("خالی پیٹ شوگر 100 تھی", 100.0, "fasting"),
]


@pytest.mark.parametrize("text,expected_val,expected_ctx", EN_PHRASINGS)
def test_glucose_duration_extraction_en(text, expected_val, expected_ctx):
    val_res = validate_glucose_input(text)
    assert val_res.valid is True, f"Validation failed for EN: {text}"
    assert val_res.value == expected_val, f"Value mismatch for EN: {text}"
    assert val_res.is_ambiguous is False
    ctx = detect_glucose_context(text)
    assert ctx == expected_ctx, f"Context mismatch for EN: {text} (got {ctx}, expected {expected_ctx})"


@pytest.mark.parametrize("text,expected_val,expected_ctx", ROMAN_URDU_PHRASINGS)
def test_glucose_duration_extraction_roman_urdu(text, expected_val, expected_ctx):
    val_res = validate_glucose_input(text)
    assert val_res.valid is True, f"Validation failed for Roman Urdu: {text}"
    assert val_res.value == expected_val, f"Value mismatch for Roman Urdu: {text}"
    assert val_res.is_ambiguous is False
    ctx = detect_glucose_context(text)
    assert ctx == expected_ctx, f"Context mismatch for Roman Urdu: {text} (got {ctx}, expected {expected_ctx})"


@pytest.mark.parametrize("text,expected_val,expected_ctx", URDU_SCRIPT_PHRASINGS)
def test_glucose_duration_extraction_urdu_script(text, expected_val, expected_ctx):
    val_res = validate_glucose_input(text)
    assert val_res.valid is True, f"Validation failed for Urdu: {text}"
    assert val_res.value == expected_val, f"Value mismatch for Urdu: {text}"
    assert val_res.is_ambiguous is False
    ctx = detect_glucose_context(text)
    assert ctx == expected_ctx, f"Context mismatch for Urdu: {text} (got {ctx}, expected {expected_ctx})"


def test_v3_interview_duration_number_not_missing_reading():
    """Verify in v3 interview that typing duration answer saves reading and does NOT mark missing_reading."""
    test_cases = [
        ("en", "2 hours after lunch it was 165", 165.0, "after_meal"),
        ("roman_ur", "khane ke 2 ghante baad 165 thi", 165.0, "after_meal"),
        ("roman_ur", "nashtay ke 2 ghante baad 180", 180.0, "after_meal"),
        ("ur", "کھانے کے 2 گھنٹے بعد 165 تھی", 165.0, "after_meal"),
        ("ur", "خالی پیٹ 110", 110.0, "fasting"),
        ("en", "before breakfast was 95", 95.0, "fasting"),
    ]

    for lang, ans, exp_val, exp_ctx in test_cases:
        st = start_v3_session("chk_1", "p_1", ["diabetes"], language=lang)
        # Advance to glucose question
        if "glucose_reading" not in st.get("step", ""):
            st = next_turn(st, "hello")
        assert "glucose_reading" in st.get("step", "")

        st = next_turn(st, ans)
        known = st.get("known_slots", {})
        assert known.get("glucose_reading") == exp_val, f"Failed for {ans}: known_slots has {known.get('glucose_reading')}"
        assert st.get("readings", {}).get("glucose") == exp_val
        assert known.get("missing_reading") is not True, f"missing_reading was set for {ans}"
        assert known.get("glucose_context") == exp_ctx, f"Context mismatch for {ans}: got {known.get('glucose_context')}"
        # Verify next question is NOT asking about missing readings or missing glucometer
        next_q = (st.get("current_question") or "").lower()
        assert "glucometer" not in next_q, f"Asked about glucometer after valid reading: {next_q}"
        assert "missing" not in next_q, f"Asked about missing data after valid reading: {next_q}"


def test_item_5_glucose_duration_cases():
    """
    Explicit test cases required by FIX4 Item 5:
    - '2 hours after lunch 165' -> valid, 165.0, after_meal
    - '45 hours', '120 hours' -> invalid / no reading / ambiguous
    - '2 ghante pehle 58' -> valid, 58.0
    - 'sugar 45 min ago' -> invalid / no reading
    """
    # 1. "2 hours after lunch 165" -> valid, 165.0, after_meal
    res1 = validate_glucose_input("2 hours after lunch 165")
    assert res1.valid is True
    assert res1.value == 165.0
    assert detect_glucose_context("2 hours after lunch 165") == "after_meal"

    # 2. "45 hours" -> invalid / no reading
    res2 = validate_glucose_input("45 hours")
    assert res2.valid is False or res2.value is None

    # 3. "120 hours" -> invalid / no reading
    res3 = validate_glucose_input("120 hours")
    assert res3.valid is False or res3.value is None

    # 4. "2 ghante pehle 58" -> valid, 58.0
    res4 = validate_glucose_input("2 ghante pehle 58")
    assert res4.valid is True
    assert res4.value == 58.0

    # 5. "sugar 45 min ago" -> invalid / no reading
    res5 = validate_glucose_input("sugar 45 min ago")
    assert res5.valid is False or res5.value is None

