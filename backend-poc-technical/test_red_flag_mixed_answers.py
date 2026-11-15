"""
backend-poc-technical/test_red_flag_mixed_answers.py

R7 Test Suite: Comprehensive validation of span- and category-scoped red-flag decisions.
Guarantees that compound answers containing BOTH a negated/remote-past symptom
AND an acute emergency stay strictly RED, preventing dangerous false downgrades (P0 safety bug).

Covers:
1. >= 40 Mixed answers (14 EN, 14 Roman Urdu, 14 Urdu script) across all 5 emergency categories.
2. >= 20 All-negated/past answers confirming clean non-Red decisions.
3. Diagnostic remote past tests ("angiography was normal", "bachpan mein ek dafa behosh hua tha").
4. Reviewer-identified misses as clinical rules (wheezing + speech impairment, Urdu breathlessness, unresponsive failure verbs).
5. 3 API-level checkin answer tests via POST /api/checkins/{id}/answer asserting emergency response with 1122.
6. Kills mutant M-F5-WHOLE (whole-answer negation in decide_red).
"""

import pytest
import jwt
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from main import app
from agents.red_flag_patterns import decide_red, is_remote_past
from test_checkin_api import (
    setup_test_environment,
    rsa_key_pair,
    x509_cert_pem,
    bootstrap_patient,
    create_test_token,
)

client = TestClient(app)


# =============================================================================
# 1. 42 Mixed Answers: One Negated/Past Symptom + One Real Current Emergency
# =============================================================================

MIXED_ANSWERS = [
    # ---------------- English (14 cases) ----------------
    # Negated first, with contrastive conjunction
    ("no vomiting, but my mother collapsed and is not responding", "loss_of_consciousness"),
    ("breathing is fine but there is severe crushing pressure in my chest spreading to my arm", "chest_pain"),
    ("no chest pain, but I am wheezing and can barely talk, getting worse rapidly", "breathing"),
    ("denies slurred speech, however throwing up uncontrollably and cannot keep fluids down", "dka_vomiting_high_glucose"),
    ("had fainting in 2020 all tests clear, but right arm suddenly went numb and face is drooping", "confusion_and_stroke"),
    # Negated first, without conjunction (punctuation-scoped)
    ("no shortness of breath; severe squeezing chest pressure and sweating", "chest_pain"),
    ("slurred speech was never observed. Patient collapsed and is totally unresponsive", "loss_of_consciousness"),
    ("no vomiting, gasping desperately for air and choking", "breathing"),
    ("fainting was not an issue today, continuous violent vomiting and high sugar", "dka_vomiting_high_glucose"),
    ("no chest tightness, mouth suddenly dropped on one side with slurred speech", "confusion_and_stroke"),
    # Emergency first, with contrastive conjunction
    ("severe crushing chest pain radiating to left jaw, but no vomiting", "chest_pain"),
    ("acute wheezing and cannot speak full sentences, though no fainting occurred", "breathing"),
    ("sudden facial drooping and cannot lift left arm, but no breathing trouble", "confusion_and_stroke"),
    ("throwing up violently and cannot hold water down, but chest pain was not experienced", "dka_vomiting_high_glucose"),

    # ---------------- Roman Urdu (14 cases) ----------------
    # Negated first, with contrastive conjunction
    ("ulti nahi hui, magar abba ki zaban achanak larkhara gayi hai", "confusion_and_stroke"),
    ("behosh nahi hua lekin seene mein shadeed dabao aur paseena hai", "chest_pain"),
    ("seene mein dard nahi hai par saans bilkul nahi aa rahi dam ghut raha hai", "breathing"),
    ("saans theek hai magar jagane par bhi nahi jaag rahe be hosh hain", "loss_of_consciousness"),
    ("chehra theek hai lekin musalsal ultiyan aa rahi hain pani bhi nahi ruk raha", "dka_vomiting_high_glucose"),
    # Negated first, without conjunction
    ("koi dard nahi; bayein bazu aur jabray me shadeed dard aur dabav hai", "chest_pain"),
    ("chhati mein jakran nahi hai. haath pair thande hain aur saans ukhar rahi hai", "breathing"),
    ("zaban nahi ladkhadayi, achanak zameen par gir gaye aur behosh hain", "loss_of_consciousness"),
    ("ulti bilkul nahi hui, adha jism achanak bejan ho gaya aur bolna band hai", "confusion_and_stroke"),
    ("bachpan mein ek dafa behosh hua tha, aaj subah se har ghante ulti aa rahi hai", "dka_vomiting_high_glucose"),
    # Emergency first, with contrastive conjunction
    ("seene par shadeed dabao aur paseena aa raha hai lekin ulti nahi hui", "chest_pain"),
    ("itni takleef hai ke baat nahi ho rahi magar seene me koi dard nahi", "breathing"),
    ("munh terha ho gaya aur awaz nahi nikal rahi par behosh nahi hue", "confusion_and_stroke"),
    ("jag nahi rahe bilkul be hosh hain, waise ulti nahi aayi", "loss_of_consciousness"),

    # ---------------- Urdu Script (14 cases) ----------------
    # Negated first, with contrastive conjunction
    ("الٹی نہیں ہوئی لیکن سینے میں شدید دباؤ اور پسینہ ہے", "chest_pain"),
    ("بے ہوش نہیں ہوئے مگر زبان اچانک لڑکھڑا گئی اور بولنا بند ہے", "confusion_and_stroke"),
    ("سینے میں درد نہیں ہے لیکن اتنی تکلیف ہے کہ بات نہیں ہو رہی", "breathing"),
    ("سانس ٹھیک ہے پر جگانے پر بھی نہیں جاگ رہیں، بالکل بے ہوش ہیں", "loss_of_consciousness"),
    ("چہرہ ٹیڑھا نہیں ہوا لیکن مسلسل الٹیاں آ رہی ہیں پانی بھی اندر نہیں ٹھہر رہا", "dka_vomiting_high_glucose"),
    # Negated first, without conjunction
    ("سینے میں کوئی درد نہیں، سانس اکھڑ رہی ہے اور دم گھٹ رہا ہے", "breathing"),
    ("کوئی الٹی نہیں ہوئی۔ والدہ بے ہوش ہو کر گر پڑیں اور ہوش نہیں آ رہا", "loss_of_consciousness"),
    ("زبان نہیں لڑکھڑائی؛ سینے پر جیسے ہاتھی بیٹھ گیا ہو اور شدید درد ہے", "chest_pain"),
    ("سانس کی کوئی تکلیف نہیں ہے، ایک طرف کا بازو اور ٹانگ بالکل بیکار ہو گئی", "confusion_and_stroke"),
    ("بے ہوشی کا کوئی مسئلہ نہیں، ہر گھونٹ پر الٹی آ جاتی ہے پیٹ میں کچھ نہیں رکتا", "dka_vomiting_high_glucose"),
    # Emergency first, with contrastive conjunction
    ("سینے میں شدید درد اور بائیں بازو میں کھنچاؤ ہے لیکن الٹی نہیں ہوئی", "chest_pain"),
    ("دم گھٹ رہا ہے اور ہوا نہیں مل رہی مگر بے ہوش نہیں ہوئے", "breathing"),
    ("چہرہ ایک طرف لٹک گیا اور آواز بند ہے لیکن سانس بالکل ٹھیک ہے", "confusion_and_stroke"),
    ("مسلسل قے آ رہی ہے اور شوگر بہت زیادہ ہے لیکن سینے میں درد نہیں", "dka_vomiting_high_glucose"),
]


@pytest.mark.parametrize("answer,expected_category", MIXED_ANSWERS)
def test_mixed_answer_remains_red(answer: str, expected_category: str):
    """
    R7: Mixed answers with negated/past symptom + real acute emergency
    must NEVER be downgraded. They must stay RED with the real emergency category.
    """
    decision = decide_red(answer)
    assert decision.is_red is True, f"Mixed answer falsely downgraded to non-Red: {answer}"
    assert decision.category == expected_category, (
        f"Expected category {expected_category}, got {decision.category} for: {answer}"
    )


# =============================================================================
# 2. 21 All-Negated / Remote-Past Answers: Must be NOT Red
# =============================================================================

ALL_NEGATED_ANSWERS = [
    # English (7 cases)
    "chest pain? no",
    "breathing trouble was not an issue today",
    "slurred speech was never observed",
    "suffocation or choking was not experienced",
    "no vomiting and no dizziness",
    "severe chest pressure: not at all",
    "had chest pain in 2021, angiography was normal",

    # Roman Urdu (7 cases)
    "seene mein koi dard nahi hai",
    "saans phoolne wali koi baat nahi",
    "chakkar aaye the par behosh nahi hua",
    "chehra bilkul theek hai koi terha pan nahi",
    "ulti nahi hui, sab theek hai",
    "bachpan mein ek dafa behosh hua tha",
    "saans ki takleef? nahi",

    # Urdu Script (7 cases)
    "سینے میں درد؟ نہیں",
    "سینے میں کوئی جکڑن یا بوجھ محسوس نہیں ہوا",
    "سانس لینے میں کوئی دشواری نہیں ہے",
    "چہرہ بالکل ٹھیک ہے منہ ٹیڑھا نہیں ہوا",
    "بے ہوش نہیں ہوا صرف معمولی چکر آئے تھے",
    "الٹی یا قے کی کوئی شکایت نہیں ہے",
    "زبان لڑکھڑانے کا کوئی مسئلہ نہیں ہے",
]


@pytest.mark.parametrize("answer", ALL_NEGATED_ANSWERS)
def test_all_negated_or_past_is_not_red(answer: str):
    """
    R7: Answers where every red-flag mention is negated or remote past
    must NOT trigger Red emergency.
    """
    decision = decide_red(answer)
    assert decision.is_red is False, f"Negated answer incorrectly marked Red: {answer}"


# =============================================================================
# 3. Remote Past Diagnostics
# =============================================================================

def test_remote_past_diagnostics():
    """
    R7 Requirement 4:
    'had chest pain in 2021, angiography was normal' and
    'bachpan mein ek dafa behosh hua tha' must be recognized as remote past
    and return is_red=False (giving Yellow review through F5, never Red).
    """
    ans1 = "had chest pain in 2021, angiography was normal"
    ans2 = "bachpan mein ek dafa behosh hua tha"

    assert is_remote_past(ans1) is True
    assert is_remote_past(ans2) is True

    dec1 = decide_red(ans1)
    assert dec1.is_red is False
    assert len(dec1.cancelled_hits) > 0, "Base hit must be cancelled for F5 downgrade"

    dec2 = decide_red(ans2)
    assert dec2.is_red is False


# =============================================================================
# 4. Reviewer-Identified Misses Fixed as Clinical Rules
# =============================================================================

def test_reviewer_misses_clinical_rules():
    """
    R7 Requirement 5:
    - 'wheezing' + 'can barely talk / getting worse' -> breathing (Red)
    - Urdu 'اتنی تکلیف ... کہ بات نہیں ہو رہی' -> breathing (Red)
    - Urdu/Roman 'جگانے پر بھی نہیں جاگ رہیں / jagane par bhi nahi jaag rahe' -> loss_of_consciousness (Red)
    """
    # 1. Wheezing + speech distress
    dec_wheeze1 = decide_red("wheezing and can barely talk, getting worse")
    assert dec_wheeze1.is_red is True
    assert dec_wheeze1.category == "breathing"

    dec_wheeze2 = decide_red("acute wheezing and cannot speak full sentences")
    assert dec_wheeze2.is_red is True
    assert dec_wheeze2.category == "breathing"

    # 2. Urdu breathlessness speech inability
    dec_urdu_breath = decide_red("اتنی تکلیف ہے کہ بات نہیں ہو رہی")
    assert dec_urdu_breath.is_red is True
    assert dec_urdu_breath.category == "breathing"

    dec_roman_breath = decide_red("itni takleef hai ke baat nahi ho rahi")
    assert dec_roman_breath.is_red is True
    assert dec_roman_breath.category == "breathing"

    # 3. Unresponsive failure verbs (not negations)
    dec_unresp_ur = decide_red("جگانے پر بھی نہیں جاگ رہیں، بالکل بے ہوش ہیں")
    assert dec_unresp_ur.is_red is True
    assert dec_unresp_ur.category == "loss_of_consciousness"

    dec_unresp_ro = decide_red("jagane par bhi nahi jaag rahe be hosh hain")
    assert dec_unresp_ro.is_red is True
    assert dec_unresp_ro.category == "loss_of_consciousness"


# =============================================================================
# 5. API-Level Checkin Mixed Answer Tests via POST /api/checkins/{id}/answer
# =============================================================================

def _create_and_auth_patient(rsa_key_pair, user_id: str = "pat-r7-mixed-1") -> dict[str, str]:
    token = create_test_token(rsa_key_pair, sub=user_id, email=f"{user_id}@demo.com")
    bootstrap_patient(client, token, conditions=["hypertension"])
    return {"Authorization": f"Bearer {token}"}


def test_api_mixed_answer_english(rsa_key_pair):
    """
    API Test 1: English mixed answer returns 200 with emergency=True and 1122 guidance.
    """
    headers = _create_and_auth_patient(rsa_key_pair, "pat-r7-mixed-en")
    start = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start.status_code == 200
    cid = start.json()["checkin_id"]

    ans = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "no vomiting, but my mother collapsed and is not responding"},
    )
    assert ans.status_code == 200
    data = ans.json()
    assert data.get("emergency") is True
    assert data.get("emergency_reason") == "loss_of_consciousness"
    note = (data.get("safety_note") or "") + (data.get("guidance") or "") + (data.get("emergency_guidance") or "")
    assert "1122" in note


def test_api_mixed_answer_roman_urdu(rsa_key_pair):
    """
    API Test 2: Roman Urdu mixed answer returns 200 with emergency=True.
    """
    headers = _create_and_auth_patient(rsa_key_pair, "pat-r7-mixed-ro")
    start = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start.status_code == 200
    cid = start.json()["checkin_id"]

    ans = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "ulti nahi hui, magar abba ki zaban achanak larkhara gayi hai"},
    )
    assert ans.status_code == 200
    data = ans.json()
    assert data.get("emergency") is True
    assert data.get("emergency_reason") == "confusion_and_stroke"


def test_api_mixed_answer_urdu_script(rsa_key_pair):
    """
    API Test 3: Urdu script mixed answer returns 200 with emergency=True.
    """
    headers = _create_and_auth_patient(rsa_key_pair, "pat-r7-mixed-ur")
    start = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start.status_code == 200
    cid = start.json()["checkin_id"]

    ans = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "الٹی نہیں ہوئی لیکن سینے میں شدید دباؤ اور پسینہ ہے"},
    )
    assert ans.status_code == 200
    data = ans.json()
    assert data.get("emergency") is True
    assert data.get("emergency_reason") == "chest_pain"


# =============================================================================
# 6. Mutant Killer: M-F5-WHOLE (Whole-Answer Negation in decide_red)
# =============================================================================

def test_mutation_killed_whole_answer_negation():
    """
    Kills Mutant M-F5-WHOLE: Whole-answer negation in decide_red.
    If decide_red checks negation across the whole answer rather than per-clause,
    mixed answers like 'ulti nahi hui, magar abba ki zaban achanak larkhara gayi hai'
    falsely become is_red=False, causing this assertion to fail.
    """
    dec = decide_red("ulti nahi hui, magar abba ki zaban achanak larkhara gayi hai")
    assert dec.is_red is True, "M-F5-WHOLE killed: whole answer negation improperly suppressed real emergency"
    assert dec.category == "confusion_and_stroke"
