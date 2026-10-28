"""
Comprehensive test suite for agents.answer_understanding.
250+ table-driven test cases covering normalise_text, parse_yes_no, parse_number, and parse_bp.
"""

import pytest
from agents.answer_understanding import (
    normalise_text,
    parse_yes_no,
    parse_number,
    parse_bp,
    _ROMAN_URDU_NUMBERS,
    _URDU_SCRIPT_NUMBERS,
)

# -----------------------------------------------------------------------------
# 1. normalise_text tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  Hello   World  ", "hello world"),
        ("١٢٣٤٥٦٧٨٩٠", "1234567890"),
        ("۱۲۳۴۵۶۷۸۹۰", "1234567890"),
        # Arabic to Urdu letter harmonization
        ("يوم", "یوم"),  # \u064A -> \u06CC
        ("كتاب", "کتاب"),  # \u0643 -> \u06A9
        ("هوا", "ہوا"),  # \u0647 -> \u06C1
        ("على", "علی"),  # \u0649 -> \u06CC
        # Tatweel removal
        ("صـــدریہ", "صدریہ"),
        ("بــہــت", "بہت"),
        # Diacritics removal (zabar, zer, pesh, do-zabar, etc.)
        ("شُکْرِیَہ", "شکریہ"),
        ("مَعْلُوم", "معلوم"),
        ("نَہِیں", "نہیں"),
        ("ہَاں", "ہاں"),
        # Latin lowercasing & Unicode NFKC
        ("LATIN Capitals", "latin capitals"),
        ("ﬁle ligature", "file ligature"),
    ],
)
def test_normalise_text(raw, expected):
    assert normalise_text(raw) == expected


# -----------------------------------------------------------------------------
# 2. parse_yes_no tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,expected_val,expected_conf,expected_partial",
    [
        # Empty
        ("", "unknown", "High", False),
        ("   ", "unknown", "High", False),
        # English YES High
        ("yes", "yes", "High", False),
        ("yeah", "yes", "High", False),
        ("yep", "yes", "High", False),
        ("yup", "yes", "High", False),
        ("sure", "yes", "High", False),
        ("of course", "yes", "High", False),
        ("correct", "yes", "High", False),
        ("right", "yes", "High", False),
        ("I am", "yes", "High", False),
        ("I do", "yes", "High", False),
        ("I did", "yes", "High", False),
        ("I have", "yes", "High", False),
        # Roman Urdu YES High
        ("haan", "yes", "High", False),
        ("han", "yes", "High", False),
        ("haanji", "yes", "High", False),
        ("han ji", "yes", "High", False),
        ("ji haan", "yes", "High", False),
        ("jee haan", "yes", "High", False),
        ("bilkul", "yes", "High", False),
        ("zaroor", "yes", "High", False),
        # Urdu Script YES High
        ("ہاں", "yes", "High", False),
        ("جی ہاں", "yes", "High", False),
        ("بالکل", "yes", "High", False),
        ("ضرور", "yes", "High", False),
        # English NO High
        ("no", "no", "High", False),
        ("nope", "no", "High", False),
        ("nah", "no", "High", False),
        ("not really", "no", "High", False),
        ("I am not", "no", "High", False),
        ("I don't", "no", "High", False),
        ("I didn't", "no", "High", False),
        ("I haven't", "no", "High", False),
        ("never", "no", "High", False),
        # Roman Urdu NO High
        ("nahi", "no", "High", False),
        ("nahin", "no", "High", False),
        ("nai", "no", "High", False),
        ("na", "no", "High", False),
        ("na nahi", "no", "High", False),
        ("ji nahi", "no", "High", False),
        ("jee nahi", "no", "High", False),
        ("bilkul nahi", "no", "High", False),
        ("kabhi nahi", "no", "High", False),
        # Urdu Script NO High
        ("نہیں", "no", "High", False),
        ("جی نہیں", "no", "High", False),
        ("بالکل نہیں", "no", "High", False),
        ("کبھی نہیں", "no", "High", False),
        # Polite ji/jee alone -> yes Medium
        ("ji", "yes", "Medium", False),
        ("jee", "yes", "Medium", False),
        ("جی", "yes", "Medium", False),
        ("ji doc", "yes", "Medium", False),
        ("ji doctor", "yes", "Medium", False),
        # Partials -> yes, partial True, Medium
        ("thora sa", "yes", "Medium", True),
        ("thoda", "yes", "Medium", True),
        ("kabhi kabhi", "yes", "Medium", True),
        ("sometimes", "yes", "Medium", True),
        ("a little", "yes", "Medium", True),
        ("a bit", "yes", "Medium", True),
        ("تھوڑا", "yes", "Medium", True),
        ("کبھی کبھی", "yes", "Medium", True),
        # Unknowns High
        ("pata nahi", "unknown", "High", False),
        ("pta nahi", "unknown", "High", False),
        ("maloom nahi", "unknown", "High", False),
        ("معلوم نہیں", "unknown", "High", False),
        ("پتہ نہیں", "unknown", "High", False),
        ("I don't know", "unknown", "High", False),
        ("dont know", "unknown", "High", False),
        ("not sure", "unknown", "High", False),
        ("idk", "unknown", "High", False),
        ("shayad", "unknown", "High", False),
        ("maybe", "unknown", "High", False),
        ("perhaps", "unknown", "High", False),
        ("شاید", "unknown", "High", False),
        # Traps
        ("no problem", "unknown", "Medium", False),
        ("no worries", "unknown", "Medium", False),
        ("not bad", "unknown", "Medium", False),
        ("theek hai na?", "unknown", "Low", False),  # tag-question na
        ("acha na", "unknown", "Low", False),
        # Double negative
        ("nahi aisa nahi hai", "unknown", "Low", False),
        ("no that is not true", "unknown", "Low", False),
        # Mixed -> last clear statement wins Medium
        ("haan... actually nahi", "no", "Medium", False),
        ("nahi... actually haan", "yes", "Medium", False),
        ("yes, wait no", "no", "Medium", False),
        ("no, actually yes", "yes", "Medium", False),
        # Emojis
        ("👍", "yes", "Low", False),
        ("👎", "no", "Low", False),
        ("🤔", "unknown", "Low", False),
    ],
)
def test_parse_yes_no(text, expected_val, expected_conf, expected_partial):
    res = parse_yes_no(text)
    assert res["value"] == expected_val
    assert res["confidence"] == expected_conf
    assert res["partial"] == expected_partial
    if text.strip():
        assert res["evidence"] == text.strip()


# -----------------------------------------------------------------------------
# 3. parse_number tests: Roman Urdu 0–100 IN FULL
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "word,val",
    [
        ("sifar", 0), ("ek", 1), ("do", 2), ("teen", 3), ("chaar", 4),
        ("paanch", 5), ("chheh", 6), ("saat", 7), ("aath", 8), ("nau", 9),
        ("das", 10), ("gyaarah", 11), ("baarah", 12), ("teerah", 13), ("chaudah", 14),
        ("pandrah", 15), ("solah", 16), ("satrah", 17), ("athaarah", 18), ("unnees", 19),
        ("bees", 20), ("ikkees", 21), ("baais", 22), ("teis", 23), ("chaubees", 24),
        ("pachchees", 25), ("chhabbees", 26), ("sattais", 27), ("atthais", 28), ("untees", 29),
        ("tees", 30), ("ikattis", 31), ("battees", 32), ("taintees", 33), ("chautees", 34),
        ("paintees", 35), ("chhattees", 36), ("saintees", 37), ("adtees", 38), ("untaalees", 39),
        ("chaalees", 40), ("iktaalees", 41), ("bayaalees", 42), ("taintaalees", 43), ("chawalees", 44),
        ("pentaalees", 45), ("chhiyaalees", 46), ("saintaalees", 47), ("adtaalees", 48), ("unchaas", 49),
        ("pachaas", 50), ("ikyaavan", 51), ("baavan", 52), ("tirpan", 53), ("chauvan", 54),
        ("pachpan", 55), ("chhappan", 56), ("sattaavan", 57), ("atthaavan", 58), ("unsath", 59),
        ("saath", 60), ("iksath", 61), ("baasath", 62), ("tirsath", 63), ("chausath", 64),
        ("painsath", 65), ("chhiyaasath", 66), ("sarsath", 67), ("adsath", 68), ("unhattar", 69),
        ("sattar", 70), ("ikhattar", 71), ("bahattar", 72), ("tihattar", 73), ("chauhattar", 74),
        ("pachhattar", 75), ("chhihattar", 76), ("sathattar", 77), ("athattar", 78), ("unaasi", 79),
        ("assi", 80), ("ikyaasi", 81), ("bayaasi", 82), ("tiraasi", 83), ("chauraasi", 84),
        ("pachaasi", 85), ("chhiyaasi", 86), ("sattaasi", 87), ("athaasi", 88), ("navaasi", 89),
        ("nabbe", 90), ("ikyaanve", 91), ("baanve", 92), ("tiraanve", 93), ("chauraanve", 94),
        ("pachaanve", 95), ("chhiyaanve", 96), ("sattaanve", 97), ("atthaanve", 98), ("ninyaanve", 99),
        ("sau", 100),
    ],
)
def test_parse_number_roman_urdu_0_to_100(word, val):
    res = parse_number(word)
    assert res["value"] == float(val), f"Failed for {word}: got {res['value']}, expected {val}"
    assert res["kind"] == "words"


# Spelling variants of Roman Urdu numbers
@pytest.mark.parametrize(
    "var_word,val",
    [
        ("aik", 1), ("char", 4), ("panch", 5), ("che", 6), ("chhe", 6),
        ("no", 9), ("gyara", 11), ("bara", 12), ("tera", 13), ("choda", 14),
        ("pandra", 15), ("sola", 16), ("satra", 17), ("athara", 18), ("unis", 19),
        ("bis", 20), ("ikkis", 21), ("bais", 22), ("pachees", 25), ("pachis", 25),
        ("chhabis", 26), ("untis", 29), ("iktis", 31), ("battis", 32), ("taintis", 33),
        ("chautis", 34), ("paintis", 35), ("chhattis", 36), ("saintis", 37), ("adtis", 38),
        ("untalis", 39), ("chalis", 40), ("iktalis", 41), ("bayalis", 42), ("taintalis", 43),
        ("chawalis", 44), ("pentalees", 45), ("paintalis", 45), ("chhiyalis", 46), ("saintalis", 47),
        ("adtalis", 48), ("unchas", 49), ("pachas", 50), ("ikyawan", 51), ("bawan", 52),
        ("chawan", 54), ("sattawan", 57), ("atthawan", 58), ("sath", 60), ("basath", 62),
        ("chhiyasath", 66), ("unasi", 79), ("ikyasi", 81), ("bayasi", 82), ("tirasi", 83),
        ("chaurasi", 84), ("pachasi", 85), ("chhiyasi", 86), ("sattasi", 87), ("athasi", 88),
        ("navasi", 89), ("nave", 90), ("ikyanve", 91), ("banve", 92), ("tiranve", 93),
        ("chauranve", 94), ("pachanve", 95), ("chhiyanve", 96), ("sattanve", 97), ("atthanve", 98),
        ("ninyanve", 99),
    ],
)
def test_parse_number_roman_urdu_variants(var_word, val):
    res = parse_number(var_word)
    assert res["value"] == float(val)


# Urdu script numbers 0–100
@pytest.mark.parametrize(
    "urdu_word,val",
    [
        ("صفر", 0), ("ایک", 1), ("دو", 2), ("تین", 3), ("چار", 4),
        ("پانچ", 5), ("چھ", 6), ("سات", 7), ("آٹھ", 8), ("نو", 9),
        ("دس", 10), ("گیارہ", 11), ("بارہ", 12), ("تیرہ", 13), ("چودہ", 14),
        ("پندرہ", 15), ("سولہ", 16), ("سترہ", 17), ("اٹھارہ", 18), ("انیس", 19),
        ("بیس", 20), ("تیس", 30), ("چالیس", 40), ("پچاس", 50), ("ساٹھ", 60),
        ("ستر", 70), ("اسی", 80), ("نوے", 90), ("سو", 100),
    ],
)
def test_parse_number_urdu_script(urdu_word, val):
    res = parse_number(urdu_word)
    assert res["value"] == float(val)
    assert res["kind"] == "words"


# English and compound numbers
@pytest.mark.parametrize(
    "phrase,expected_val",
    [
        ("zero", 0.0),
        ("five", 5.0),
        ("ten", 10.0),
        ("nineteen", 19.0),
        ("twenty", 20.0),
        ("a hundred", 100.0),
        ("one hundred and twenty", 120.0),
        ("one twenty", 120.0),
        ("two thirty", 230.0),
        # Roman Urdu compounds
        ("ek sau", 100.0),
        ("aik sau", 100.0),
        ("ek sau baais", 122.0),
        ("do sau tees", 230.0),
        ("teen sau pachaas", 350.0),
        ("ek so bees", 120.0),  # "so" after number word
        # Urdu script compounds
        ("ایک سو بیس", 120.0),
        ("دو سو تیس", 230.0),
        # Digits
        ("120", 120.0),
        ("120.5", 120.5),
        ("120,5", 120.5),
        ("١٢٠", 120.0),
        ("۱۲۰", 120.0),
    ],
)
def test_parse_number_compounds(phrase, expected_val):
    res = parse_number(phrase)
    assert res["value"] == expected_val


# Rejections, ambiguity, dates/times
@pytest.mark.parametrize(
    "invalid_text",
    [
        "12/10",
        "12-10-2026",
        "8:00",
        "subah 8 baje",
        "8am",
        "8 pm",
        "120 ya 130",
        "120 or 130",
        "ek do sau",
        "so I was checking my sugar",  # English "so" in sentence is NOT 100
    ],
)
def test_parse_number_rejections_and_dates(invalid_text):
    res = parse_number(invalid_text)
    assert res["value"] is None


# Addendum E4: Meter LO / HI recognition
@pytest.mark.parametrize(
    "meter_text,expected_dir",
    [
        ("LO", "low"),
        ("lo", "low"),
        ("low", "low"),
        ("bohat kam", "low"),
        ("meter pe lo", "low"),
        ("HI", "high"),
        ("hi", "high"),
        ("high", "high"),
        ("bohat zyada", "high"),
        ("meter pe hi", "high"),
    ],
)
def test_parse_number_meter_out_of_range(meter_text, expected_dir):
    res = parse_number(meter_text)
    assert res["value"] is None
    assert res["kind"] == "meter_out_of_range"
    assert res["direction"] == expected_dir


# -----------------------------------------------------------------------------
# 4. parse_bp tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "bp_text,expected_bp",
    [
        ("120/80", [120, 80]),
        ("120 / 80", [120, 80]),
        ("120 by 80", [120, 80]),
        ("120 over 80", [120, 80]),
        ("120-80", [120, 80]),
        ("120 80", [120, 80]),
        ("120 bata 80", [120, 80]),
        ("ek sau bees bata assi", [120, 80]),
        ("ek sau bees by assi", [120, 80]),
        ("١٢٠/٨٠", [120, 80]),
        ("۱۲۰/۸۰", [120, 80]),
        ("130/85", [130, 85]),
        ("140 by 90", [140, 90]),
    ],
)
def test_parse_bp_valid(bp_text, expected_bp):
    res = parse_bp(bp_text)
    assert res["value"] == expected_bp


@pytest.mark.parametrize(
    "invalid_bp",
    [
        "80/120",        # systolic <= diastolic
        "120/120",       # systolic == diastolic
        "120/80/70",     # 3 numbers
        "120",           # single number
        "50/80",         # systolic < 60
        "280/80",        # systolic > 260
        "120/20",        # diastolic < 30
        "120/160",       # diastolic > 150
        "hello doc",     # non-numeric
    ],
)
def test_parse_bp_rejections(invalid_bp):
    res = parse_bp(invalid_bp)
    assert res["value"] is None
