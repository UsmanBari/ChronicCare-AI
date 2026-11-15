"""
backend-poc-technical/test_red_flag_r6.py

Exhaustive verification of R6 Red-Flag Robustness Deliverables:
1. F1 Negation Engine (preceding, trailing, passive avoidance, echo questions, failure verbs protected)
2. F2 Remote Past (historical with recovery suppressed; current acute markers never suppressed)
3. F3 Organ-Subject Guards (20 tests verifying generic words 'band', 'ruk', 'phool', 'bhaari', 'sunn', 'kamzor'
   only count for their dedicated target organ)
4. F4 Missing Family Members (explicit named coverage for breath, face droop, vomiting, syncope, stroke, chest)
5. F5 Base-Screen Conservative Downgrade & Mutant M-NRF-1 Killer.
"""

import os
import pytest
from fastapi.testclient import TestClient

from main import app, is_negated_red_flag_to_review_enabled
from agents.red_flag_patterns import (
    match,
    match_categories,
    is_symptom_negated,
    is_remote_past,
    is_echo_question_negation,
    is_symptom_negated_or_remote_past,
)
from agents.input_triage import classify_input
from test_checkin_api import (
    setup_test_environment,
    rsa_key_pair,
    x509_cert_pem,
    bootstrap_patient,
    create_test_token,
)

client = TestClient(app)


def _create_and_auth_patient(rsa_key_pair, user_id: str = "uid-r6-patient-1") -> dict[str, str]:
    token = create_test_token(rsa_key_pair, sub=user_id, email=f"{user_id}@demo.com")
    bootstrap_patient(client, token, conditions=["hypertension"])
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# F3: 20 ORGAN-SUBJECT GUARD TESTS
# =============================================================================

F3_ORGAN_GUARD_CASES = [
    # 1-2. Stuffy nose (naak band) vs breathing
    "saans theek hai, bas naak band hai",
    "naak band hai zukaam ki wajah se",
    # 3-4. Weak eyesight (aankhein / nazar kamzor) vs stroke limb weakness
    "aankhein kamzor ho gayi hain chashma lagana padega",
    "nazar kamzor hai parhai nahi hoti",
    # 5-6. Heavy head (sar bhaari) vs chest heaviness
    "sar bhaari hai tension ki wajah se",
    "sar mein bhaari pan hai neend poori nahi hui",
    # 7-8. Heavy legs after walking (pair / paon bhaari) vs cardiac heaviness
    "pair bhaari ho gaye der tak chalne ke baad",
    "chalte chalte paon bhaari ho jate hain",
    # 9-12. Everyday 'band' usages (shop, phone, road, electricity)
    "dukaan band hai kal aana",
    "phone band ho gaya tha battery khatam thi",
    "raasta band tha traffic ki wajah se",
    "light band ho gayi thi garmi lag rahi hai",
    # 13. Closing eyes to rest (aankhein band)
    "aankhein band karke aaram kar raha hoon",
    # 14-15. Swollen feet / bloated stomach (phool) vs breathing
    "paon phool gaye hain safar ke baad",
    "pet phool gaya hai gas ki wajah se",
    # 16. Car jerking / stopping (ruk ruk kar)
    "subah se gaadi ruk ruk kar chal rahi hai",
    # 17. Cold weather stuffy nose
    "saans bilkul theek hai, thand se naak band ho gayi",
    # 18. Weak eyesight in English
    "eyesight weak hai, koi weakness nahi hai jism mein",
    # 19. Heavy head in English
    "heavy head after long working hours",
    # 20. Blocked nose in English
    "blocked nose from seasonal cold, breathing is fine",
]


@pytest.mark.parametrize("text", F3_ORGAN_GUARD_CASES)
def test_f3_organ_subject_guard_negative_cases(text):
    """F3: Generic words (band, ruk, phool, bhaari, sunn, kamzor) never trigger Red on non-target organs."""
    hit, cat = match(text)
    assert not hit, f"Expected no red flag hit for organ-guard case: '{text}', but got category: {cat}"


F3_POSITIVE_CONTROL_CASES = [
    ("saans band ho rahi hai", "breathing"),
    ("dam band ho raha hai hawa nahi aa rahi", "breathing"),
    ("haath sunn ho gaya aur kaam nahi kar raha", "confusion_and_stroke"),
    ("bazu kamzor ho gaya achanak uth nahi raha", "confusion_and_stroke"),
    ("chehra sunn ho gaya aur munh terha ho gaya", "confusion_and_stroke"),
    ("seene mein bhaari dabao hai", "chest_pain"),
]


@pytest.mark.parametrize("text,expected_cat", F3_POSITIVE_CONTROL_CASES)
def test_f3_positive_controls_still_fire(text, expected_cat):
    """F3: Target organs with generic distress words STILL correctly trigger emergency Red."""
    hit, cat = match(text)
    assert hit, f"Expected red flag hit for positive case: '{text}'"
    assert cat == expected_cat, f"Expected {expected_cat}, got {cat}"


# =============================================================================
# F4: NAMED FAMILY MEMBER RECOGNITION TESTS
# =============================================================================

F4_NAMED_CASES = [
    # Breath
    ("saans phansi hui hai hawa nahi aa rahi", "breathing"),
    ("dam atka hua hai sans nahi le pa raha", "breathing"),
    ("hawa andar nahi ja rahi dam ghut raha hai", "breathing"),
    ("cant get air in, struggling for every breath", "breathing"),
    # Face droop
    ("chehra ek taraf jhul gaya hai", "confusion_and_stroke"),
    ("munh dhalak gaya hai aik taraf", "confusion_and_stroke"),
    ("chehra mur gaya achanak se", "confusion_and_stroke"),
    ("mouth is lopsided and drooping to one side", "confusion_and_stroke"),
    # Vomiting & fluids (DKA)
    ("kuch bhi andar nahi tik raha jo khate hain nikal jata hai", "dka_vomiting_high_glucose"),
    ("pani bhi nahi thehar raha bar bar ulti aa rahi hai", "dka_vomiting_high_glucose"),
    ("cant even keep water down, vomiting continuously", "dka_vomiting_high_glucose"),
    ("har ghante ulti ho rahi hai kuch hazam nahi ho raha", "dka_vomiting_high_glucose"),
    ("teen din se ulti rukne ka naam nahi le rahi", "dka_vomiting_high_glucose"),
    # Syncope & Unresponsiveness
    ("syncopal blackout out cold on the floor", "loss_of_consciousness"),
    ("chakkar kha kar behosh ho gaye aur koi harkat nahi", "loss_of_consciousness"),
    ("woh bilkul behosh hain koi jawab nahi de rahe", "loss_of_consciousness"),
    ("hosh kho baithe aur jaag nahi rahe", "loss_of_consciousness"),
    # Stroke / limbs
    ("sudden loss of power in left arm unable to move", "confusion_and_stroke"),
    ("haath se cheez gir jati hai pakar nahi pa raha", "confusion_and_stroke"),
    ("zaban larkhara rahi hai bolti band ho gayi", "confusion_and_stroke"),
    # Chest
    ("seene mein sakht kasav aur dabao hai", "chest_pain"),
    ("dabao bardasht nahi ho raha seene par", "chest_pain"),
]


@pytest.mark.parametrize("text,expected_cat", F4_NAMED_CASES)
def test_f4_missing_family_members_detected(text, expected_cat):
    """F4: Missing family members by name in breath, face, vomiting, syncope, and stroke are recognized."""
    hit, cat = match(text)
    assert hit, f"Expected red flag hit for F4 named case: '{text}'"
    assert cat == expected_cat, f"Expected category {expected_cat}, got {cat}"


# =============================================================================
# F1: UNIFIED NEGATION ENGINE TESTS
# =============================================================================

F1_NEGATION_CASES = [
    # Preceding
    "no breathing trouble at all",
    "koi seene mein dard nahi hai",
    "without any chest pain or tightness",
    "never observed any slurred speech",
    # Trailing
    "Breathing trouble was not an issue today",
    "Suffocation or choking was not experienced",
    "Slurred speech was never observed in the patient",
    "chehra bilkul theek hai, koi terha pan nahi hai",
    "ulti hone wali koi baat nahi hui",
    "chakkar mehsoos nahi ho rahe",
    "Fainting was completely avoided and ruled out",
    # Echo frames
    "chest pain? no",
    "saans ki takleef? nahi",
    "fainting: never",
    "severe chest pressure: not at all",
    "slurred speech? nope",
    "vomiting fluids - did not happen",
    "bolne me dushwari: nahi hui",
]


@pytest.mark.parametrize("text", F1_NEGATION_CASES)
def test_f1_symptom_negation_engine(text):
    """F1: Preceding, trailing, passive avoidance, and echo-frame negations are properly recognized."""
    assert is_symptom_negated(text) or is_echo_question_negation(text), f"Expected negation detection for: '{text}'"
    hit, cat = match(text)
    assert not hit, f"Negated utterance must not trigger Red emergency: '{text}', got {cat}"


F1_FAILURE_VERB_CASES = [
    "saans bilkul nahi aa rahi",
    "pani andar nahi ruk raha",
    "aankhein nahi khol rahe",
    "uth nahi raha aur jawab nahi de raha",
    "bol nahi pa raha zaban ladkhada rahi hai",
    "bilkul behosh hain koi harkat nahi",
]


@pytest.mark.parametrize("text", F1_FAILURE_VERB_CASES)
def test_f1_failure_verbs_never_negated(text):
    """F1: Active inability/failure verbs ('nahi aa rahi', 'nahi ruk raha') are NOT treated as negations."""
    assert not is_symptom_negated(text), f"Failure verb must NOT be flagged as negated: '{text}'"
    hit, _ = match(text)
    assert hit, f"Failure verb must trigger emergency Red: '{text}'"


# =============================================================================
# F2: REMOTE PAST SUPPRESSION TESTS
# =============================================================================

def test_f2_remote_past_detection():
    # Fully recovered remote past events
    assert is_remote_past("5 saal pehle dil ka daura pada tha ab bilkul theek hoon")
    assert is_remote_past("had a fainting spell in 2020 but all clear now")
    assert is_remote_past("bachpan mein asthma tha ab theek hai")
    assert is_remote_past("aaj teen saal pehle stroke hua tha ab movement normal hai")

    # Acute present markers override past
    assert not is_remote_past("5 saal pehle stroke hua tha aur abhi dobara haath sunn hai")
    assert not is_remote_past("bachpan mein asthma tha aur aaj subah se saans nahi aa rahi")


# =============================================================================
# F5: BASE-SCREEN CONSERVATIVE DOWNGRADE & M-NRF-1 KILLER
# =============================================================================

def test_f5_negated_base_screen_routes_to_yellow_review(rsa_key_pair):
    """F5: When protected base screen fires on negated input ('chest pain? no'), route to review, not emergency."""
    headers = _create_and_auth_patient(rsa_key_pair, "pat-f5-negated-review")
    start_resp = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start_resp.status_code == 200
    checkin_id = start_resp.json()["checkin_id"]

    # Answer with echo-question negation that protected classify_input would flag as emergency
    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "chest pain? no"},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    # Must NOT be an immediate emergency Red screen
    assert ans_data.get("emergency") is False, "Negated base-screen hit must not trigger Red emergency"
    # Must have a safety note attached
    assert ans_data.get("safety_note") is not None


def test_f5_flag_disabled_retains_base_emergency(monkeypatch, rsa_key_pair):
    """F5: Gating flag NEGATED_RED_FLAG_TO_REVIEW=false preserves baseline behavior (Red emergency)."""
    monkeypatch.setenv("NEGATED_RED_FLAG_TO_REVIEW", "false")
    headers = _create_and_auth_patient(rsa_key_pair, "pat-f5-flag-off")
    start_resp = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    checkin_id = start_resp.json()["checkin_id"]

    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "chest pain? no"},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    # With flag off, protected classify_input fires and is NOT downgraded
    assert ans_data.get("emergency") is True


def test_f5_true_emergency_still_triggers_red(rsa_key_pair):
    """F5: True affirmative emergency ('severe crushing chest pain') always triggers Red emergency."""
    headers = _create_and_auth_patient(rsa_key_pair, "pat-f5-true-emerg")
    start_resp = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    checkin_id = start_resp.json()["checkin_id"]

    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "severe crushing chest pain"},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data.get("emergency") is True


def test_mutation_killed_negated_base_hit_still_red(rsa_key_pair):
    """
    Kills Mutant M-NRF-1: Negated base red-flag hit still triggers Red emergency.
    When mutant disables the downgrade guard in main.py, 'chest pain? no' remains Red emergency,
    causing this test's assertion to fail.
    """
    headers = _create_and_auth_patient(rsa_key_pair, "pat-m-nrf-1")
    start_resp = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    checkin_id = start_resp.json()["checkin_id"]

    ans_resp = client.post(
        f"/api/checkins/{checkin_id}/answer",
        headers=headers,
        json={"answer": "chest pain? no"},
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data.get("emergency") is False, "Negated base hit must be downgraded from Red emergency"
