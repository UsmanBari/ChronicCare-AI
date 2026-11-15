"""
backend-poc-technical/test_red_flag_r8.py

R8 Mini Test Suite: Verification of Clinical Red-Flag Rule Refinements.
Covers 4 core areas across 3 languages (English, Roman Urdu, Urdu script):
1. FALSE RED: 'I don't feel any chest discomfort today' -> preceding-negation frames.
2. FALSE RED: 'haath sunn ho gaya tha sote hue, ab theek' -> past tense + posture trigger + recovery.
3. MISS: 'saans itni tez hai ke ek jumla poora nahi bol pa rahin' -> inability to complete a sentence.
4. MISS: 'saans lena bilkul na-mumkin ho gaya hai' -> breathing impossible,
   AND 'my right hand dropped the glass and my words came out wrong' + suddenly -> stroke FAST deficit.
5. End-to-end API integration tests via POST /api/checkins/{id}/answer asserting 1122 guidance.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from agents.red_flag_patterns import (
    decide_red,
    is_symptom_negated,
    _is_benign_postural_or_chronic_numbness,
    normalize_text,
)
from test_checkin_api import (
    setup_test_environment,
    rsa_key_pair,
    x509_cert_pem,
    bootstrap_patient,
    create_test_token,
)

client = TestClient(app)


def _create_and_auth_patient(rsa_key_pair, user_id: str = "uid-r8-patient") -> dict[str, str]:
    token = create_test_token(rsa_key_pair, sub=user_id, email=f"{user_id}@demo.com")
    bootstrap_patient(client, token, conditions=["hypertension"])
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 1. FALSE RED 1: CHEST DISCOMFORT PRECEDING NEGATION
# =============================================================================

@pytest.mark.parametrize(
    "text",
    [
        # English
        "I don't feel any chest discomfort today",
        "He doesn't feel any chest discomfort",
        "I didn't feel any chest pressure",
        "not feeling any chest discomfort",
        "I am not feeling any chest pain today",
        "Patient does not feel any chest discomfort",
        # Roman Urdu
        "seene mein koi dard mehsoos nahi ho raha",
        "mujhe koi takleef mehsoos nahi ho rahi",
        "koi dabao mehsoos nahi hai",
        "seene me koi masla mehsoos nahi ho raha",
        "dil mein koi dard mehsoos nahi",
        # Urdu Script
        "سینے میں کوئی تکلیف محسوس نہیں ہو رہی",
        "مجھے کوئی درد محسوس نہیں ہو رہا",
        "کوئی دباؤ محسوس نہیں ہو رہا",
        "سینے میں کوئی مسئلہ محسوس نہیں ہو رہا ہے",
    ],
)
def test_r8_chest_discomfort_negation_not_red(text: str):
    """Item 1: 'don't/doesn't/didn't feel any', 'not feeling any', 'koi ... mehsoos nahi' must not be Red."""
    dec = decide_red(text)
    assert dec.is_red is False, f"Expected non-Red for negated chest discomfort: '{text}', got {dec}"
    assert is_symptom_negated(text) is True


# =============================================================================
# 2. FALSE RED 2: BENIGN POSTURAL NUMBNESS WITH RECOVERY
# =============================================================================

@pytest.mark.parametrize(
    "text",
    [
        # Roman Urdu
        "haath sunn ho gaya tha sote hue, ab theek",
        "haath sunn ho gaya tha sone se, ab theek",
        "sote hue baazu sunn tha ab theek hai",
        "sotay hue haath sunn ho gaya tha, theek ab",
        "so kar uthne par haath sunn tha ab bilkul theek hai",
        # English
        "while sleeping my arm went numb, fine now",
        "my hand went numb from sleeping on it, okay now",
        "hand was numb after sleeping, better now",
        "arm went numb during sleep, all good now",
        # Urdu Script
        "سوتے ہوئے ہاتھ سن ہو گیا تھا، اب بالکل ٹھیک ہے",
        "سونے سے ہاتھ سن تھا اب ٹھیک",
        "سو کر اٹھنے پر بازو سن تھا، اب ٹھیک ہے",
    ],
)
def test_r8_postural_numbness_with_recovery_not_red(text: str):
    """Item 2: Past tense + posture trigger (sote hue/sleeping) + recovery (ab theek/fine now) is not stroke."""
    dec = decide_red(text)
    assert dec.is_red is False, f"Expected non-Red for postural numbness with recovery: '{text}', got {dec}"


@pytest.mark.parametrize(
    "text",
    [
        "achanak haath sunn ho gaya hai",
        "sudden numbness in my right hand",
        "اچانک دایاں ہاتھ سن ہو گیا ہے",
    ],
)
def test_r8_acute_numbness_still_red(text: str):
    """Acute unexplained numbness without benign trigger/recovery MUST remain stroke-Red."""
    dec = decide_red(text)
    assert dec.is_red is True, f"Expected Red for acute numbness: '{text}', got {dec}"
    assert dec.category == "confusion_and_stroke"


# =============================================================================
# 3. MISS 1: BREATHLESSNESS INABILITY TO COMPLETE A SENTENCE
# =============================================================================

@pytest.mark.parametrize(
    "text",
    [
        # Roman Urdu
        "saans itni tez hai ke ek jumla poora nahi bol pa rahin",
        "saans phool rahi hai aik jumla bhi poora nahi bol pa raha",
        "sans itni tez hai ke ek jumla pura nahi bol pa rahe",
        # English
        "I am so breathless I can't finish a sentence",
        "can't speak in full sentences",
        "unable to speak in full sentences",
        "cannot finish a sentence due to shortness of breath",
        # Urdu Script
        "سانس اتنی تیز ہے کہ ایک جملہ پورا نہیں بول پا رہے",
        "ایک جملہ بھی پورا نہیں بول پا رہے سانس کی وجہ سے",
        "سانس کی تکلیف سے ایک جملہ پورا نہیں بول پا رہی",
    ],
)
def test_r8_sentence_completion_inability_is_breathing_red(text: str):
    """Item 3: Breathlessness so bad the patient cannot finish a sentence is breathing-Red."""
    dec = decide_red(text)
    assert dec.is_red is True, f"Expected Red for sentence completion breathlessness: '{text}', got {dec}"
    assert dec.category == "breathing"


# =============================================================================
# 4. MISS 2: IMPOSSIBLE BREATHING & STROKE DROPPING OBJECTS + SPEECH DEFICIT
# =============================================================================

@pytest.mark.parametrize(
    "text",
    [
        # Roman Urdu
        "saans lena bilkul na-mumkin ho gaya hai",
        "saans lena namumkin ho gaya hai",
        "sans lena na-mumkin hai",
        # English
        "it is impossible to breathe",
        "breathing has become impossible",
        "breathing is completely impossible right now",
        # Urdu Script
        "سانس لینا بالکل ناممکن ہو گیا ہے",
        "سانس لینا نا ممکن ہو گیا ہے",
    ],
)
def test_r8_impossible_breathing_is_breathing_red(text: str):
    """Item 4a: Impossible to breathe (na-mumkin / namumkin) is breathing-Red."""
    dec = decide_red(text)
    assert dec.is_red is True, f"Expected Red for impossible breathing: '{text}', got {dec}"
    assert dec.category == "breathing"


@pytest.mark.parametrize(
    "text",
    [
        # English
        "my right hand dropped the glass and my words came out wrong suddenly",
        "suddenly my right hand dropped the glass and my words came out wrong",
        "hand dropped the cup suddenly and words came out wrong",
        # Roman Urdu
        "achanak haath se glass gir gaya aur alfaaz ghalat nikal rahe hain",
        "achanak haath se cup gir gaya aur zaban se alfaaz galat nikal rahe hain",
        # Urdu Script
        "اچانک ہاتھ سے گلاس گر گیا اور الفاظ غلط نکلنے لگے",
        "اچانک ہاتھ سے کپ گر گیا اور الفاظ غلط نکل رہے ہیں",
    ],
)
def test_r8_dropping_object_speech_deficit_is_stroke_red(text: str):
    """Item 4b: Hand dropped object + words came out wrong / speech change is stroke-Red."""
    dec = decide_red(text)
    assert dec.is_red is True, f"Expected Red for dropping object + speech deficit: '{text}', got {dec}"
    assert dec.category == "confusion_and_stroke"


# =============================================================================
# 5. END-TO-END CHECK-IN API INTEGRATION TESTS
# =============================================================================

def test_api_r8_false_red_chest_discomfort(rsa_key_pair):
    """Item 1 via API: Negated chest discomfort does NOT trigger emergency."""
    headers = _create_and_auth_patient(rsa_key_pair, "pat-r8-chest-neg")
    start = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start.status_code == 200
    cid = start.json()["checkin_id"]

    ans = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "I don't feel any chest discomfort today"},
    )
    assert ans.status_code == 200
    data = ans.json()
    assert data.get("emergency") is not True


def test_api_r8_false_red_postural_numbness(rsa_key_pair):
    """Item 2 via API: Benign postural numbness with recovery does NOT trigger emergency."""
    headers = _create_and_auth_patient(rsa_key_pair, "pat-r8-posture-neg")
    start = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start.status_code == 200
    cid = start.json()["checkin_id"]

    ans = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "haath sunn ho gaya tha sote hue, ab theek"},
    )
    assert ans.status_code == 200
    data = ans.json()
    assert data.get("emergency") is not True


def test_api_r8_miss_sentence_completion_emergency(rsa_key_pair):
    """Item 3 via API: Inability to complete a sentence triggers emergency with 1122."""
    headers = _create_and_auth_patient(rsa_key_pair, "pat-r8-sentence-red")
    start = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start.status_code == 200
    cid = start.json()["checkin_id"]

    ans = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "saans itni tez hai ke ek jumla poora nahi bol pa rahin"},
    )
    assert ans.status_code == 200
    data = ans.json()
    assert data.get("emergency") is True
    assert data.get("emergency_reason") == "breathing"
    note = (data.get("safety_note") or "") + (data.get("guidance") or "") + (data.get("emergency_guidance") or "")
    assert "1122" in note


def test_api_r8_miss_impossible_breathing_emergency(rsa_key_pair):
    """Item 4a via API: Impossible breathing triggers emergency with 1122."""
    headers = _create_and_auth_patient(rsa_key_pair, "pat-r8-breathing-red")
    start = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start.status_code == 200
    cid = start.json()["checkin_id"]

    ans = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "saans lena bilkul na-mumkin ho gaya hai"},
    )
    assert ans.status_code == 200
    data = ans.json()
    assert data.get("emergency") is True
    assert data.get("emergency_reason") == "breathing"
    note = (data.get("safety_note") or "") + (data.get("guidance") or "") + (data.get("emergency_guidance") or "")
    assert "1122" in note


def test_api_r8_miss_dropping_glass_speech_emergency(rsa_key_pair):
    """Item 4b via API: Dropping object + speech change triggers emergency with 1122."""
    headers = _create_and_auth_patient(rsa_key_pair, "pat-r8-stroke-red")
    start = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start.status_code == 200
    cid = start.json()["checkin_id"]

    ans = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "my right hand dropped the glass and my words came out wrong suddenly"},
    )
    assert ans.status_code == 200
    data = ans.json()
    assert data.get("emergency") is True
    assert data.get("emergency_reason") == "confusion_and_stroke"
    note = (data.get("safety_note") or "") + (data.get("guidance") or "") + (data.get("emergency_guidance") or "")
    assert "1122" in note
