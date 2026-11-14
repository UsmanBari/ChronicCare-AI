"""
Tests for Stage-1 Red Flags in English, Urdu, and Roman Urdu with inserted words,
plus negations and HTTP API verification across diabetes, hypertension, and dual patients.
Task: Q1 (P0 Safety).
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from agents.input_triage import classify_input
from agents.adaptive_interview_agent import run_stage1_red_flag_screen as rf_screen
from agents.red_flag_patterns import match as match_red_flags
from test_checkin_api import bootstrap_patient, create_test_token, rsa_key_pair, x509_cert_pem, setup_test_environment

client = TestClient(app)

def _is_triage_emergency(text: str) -> bool:
    res = classify_input(text)
    if res.is_emergency or res.is_urgent_safety:
        return True
    hit, _ = match_red_flags(text)
    return hit

# -----------------------------------------------------------------------------
# Test Sentences per Category (>= 6 English, >= 6 Urdu, >= 6 Roman-Urdu)
# -----------------------------------------------------------------------------

CATEGORIES_TEST_DATA = {
    "chest_pain": {
        "en": [
            "I have severe crushing chest pain radiating to left arm",
            "Crushing pain in my chest right now",
            "I feel heavy chest pain and pressure",
            "Severe chest pressure making it hard to move",
            "Sudden sharp pain going down my left arm and jaw",
            "Terrible chest tightness and crushing discomfort",
        ],
        "ur": [
            "مجھے سینے میں شدید درد ہو رہا ہے",
            "سینے میں بہت درد اور بوجھ ہے",
            "سینے پر شدید دباؤ اور کھچاؤ ہے",
            "سینے میں سخت درد محسوس ہو رہا ہے",
            "بائیں بازو میں درد اور چھاتی میں شدید درد ہو رہا ہے",
            "دل میں شدید درد اور جلن ہو رہی ہے",
        ],
        "roman_ur": [
            "mujhe seene mein shadeed dard hai",
            "seene me bohat dard ho raha hai",
            "seene par sakht dabao aur bojh hai",
            "seene mein tez dard mehsoos ho raha hai",
            "bayein bazu mein dard aur seene mein shadeed dard hai",
            "chhati me shadeed dard ho raha hai",
        ],
    },
    "breathing": {
        "en": [
            "I can't breathe and feel suffocating",
            "Cannot breathe properly at rest",
            "Struggling for air and gasping",
            "Severe shortness of breath since morning",
            "Difficulty breathing and suffocating sensation",
            "Trouble breathing and cannot catch my breath",
        ],
        "ur": [
            "سانس لینے میں شدید دشواری ہو رہی ہے",
            "سانس نہیں آ رہی بالکل",
            "دم گھٹ رہا ہے اور سانس بند ہو رہی ہے",
            "سانس لینے میں بہت مشکل ہو رہی ہے",
            "سانس بہت پھول رہی ہے اور سانس نہیں آ رہی",
            "سانس رک رہی ہے بالکل",
        ],
        "roman_ur": [
            "saans lene mein shadeed dushwari ho rahi hai",
            "saans nahi aa rahi bilkul",
            "dum ghut raha hai mera",
            "saans lene mein bohat mushkil ho rahi hai",
            "saans bohat phool rahi hai, saans nahi aa rahi",
            "saans ruk rahi hai achanak",
        ],
    },
    "confusion_and_stroke": {
        "en": [
            "My speech is slurred and I feel confused",
            "My left arm and left side of my face suddenly feel numb and weak",
            "Face is drooping on one side",
            "Can't move my left arm and leg",
            "Don't know where I am and feel totally disoriented",
            "One side of my body is weak and numb",
        ],
        "ur": [
            "زبان لڑکھڑا رہی ہے اور بول نہیں پا رہا",
            "چہرہ ایک طرف لٹک گیا ہے",
            "ایک طرف کی شدید کمزوری ہو گئی ہے",
            "ایک طرف کی شدید کمزوری ہو گئی ہے اور چہرہ لٹک گیا ہے",
            "سمجھ نہیں آ رہا میں کہاں ہوں",
            "چہرہ اور بازو اچانک سن اور کمزور ہو گئے ہیں",
        ],
        "roman_ur": [
            "zabaan ladkhada rahi hai aur bol nahi pa raha",
            "chehra aik taraf latak gaya hai",
            "aik taraf ki kamzori mehsoos ho rahi hai",
            "aik taraf ka bazu aur chehra sunn aur kamzor",
            "samajh nahi aa raha main kahan hoon",
            "bayein bazu aur chehre par sunn aur kamzori hai",
        ],
    },
    "loss_of_consciousness": {
        "en": [
            "I fainted in the kitchen today",
            "Passed out suddenly for a few minutes",
            "Blacked out and fell to the floor",
            "Lost consciousness completely this morning",
            "Collapsed suddenly while standing",
            "I had a fainting episode and collapsed",
        ],
        "ur": [
            "صبح میں بے ہوش ہو گئی تھی",
            "اچانک بے ہوش ہو گیا تھا",
            "غشی پڑ گئی تھی اچانک",
            "بے ہوشی طاری ہو گئی تھی",
            "چکر آ کر بے ہوش ہو گیا",
            "بے ہوش ہو کر گر گئی",
        ],
        "roman_ur": [
            "aaj subah main behosh ho gayi thi",
            "achanak behosh ho gaya tha",
            "ghashi par gayi thi achanak",
            "be hosh ho gaya tha subah",
            "main behosh ho gayi thi kuch dair ke liye",
            "chakkar aaya aur behosh ho gaya tha",
        ],
    },
}

UNABLE_TO_KEEP_FLUIDS_DATA = {
    "en": [
        "can't keep fluids down",
        "cannot keep fluids down",
        "unable to keep fluids down",
        "can't keep anything down",
        "can't keep my medicines down",
        "throwing up everything",
    ],
    "ur": [
        "پانی بھی نہیں رک رہا",
        "پانی بھی نہیں رکتا",
        "دوائی نہیں رک رہی",
        "دوا نہیں رک رہی",
        "پانی بھی نہیں رک رہا",
        "دوائی نہیں رک رہی",
    ],
    "roman_ur": [
        "paani bhi nahi rukta",
        "paani bhi nahi ruk raha",
        "dawa nahi ruk rahi",
        "dawa ulti mein nikal jati hai",
        "dawai nahi ruk rahi",
        "paani bhi nahi ruk raha",
    ],
}

EXACT_OBSERVED_FAILING_SENTENCES = [
    "مجھے سینے میں شدید درد ہو رہا ہے اور سانس لینے میں مشکل ہے",
    "mujhe seene mein shadeed dard hai aur saans lene mein mushkil hai",
]

NEGATIONS_DATA = [
    "seene mein dard nahi",
    "سینے میں درد نہیں",
    "seene mein koi dard nahi hai",
    "سینے میں کوئی درد یا تکلیف نہیں ہے",
    "saans bilkul theek aa rahi hai koi dushwari nahi",
    "سانس بالکل ٹھیک ہے کوئی دشواری نہیں",
    "chakkar nahi aaye aur behosh nahi hua",
    "بے ہوش نہیں ہوا بالکل ٹھیک ہوں",
    "ulti nahi hai sab theek hai",
    "الٹی نہیں ہے سب ٹھیک ہے",
    "I have no chest pain and feel fine",
    "No shortness of breath at all",
    "Denies any slurred speech or weakness",
    "Did not faint and feeling well",
    "Not vomiting and keeping food down fine",
]


# -----------------------------------------------------------------------------
# 1. Unit Tests for Category Sentences -> Emergency
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("category,langs", CATEGORIES_TEST_DATA.items())
def test_all_categories_emergency_unit(category, langs):
    for lang, sentences in langs.items():
        for sentence in sentences:
            is_emerg = _is_triage_emergency(sentence)
            assert is_emerg is True, f"Failed emergency for [{category}][{lang}]: '{sentence}'"


def test_unable_to_keep_fluids_emergency_unit():
    for lang, sentences in UNABLE_TO_KEEP_FLUIDS_DATA.items():
        for sentence in sentences:
            flagged, reason = rf_screen(sentence)
            assert flagged is True, f"Failed to flag: {sentence}"
            assert reason == "unable_to_keep_fluids", f"Expected unable_to_keep_fluids for: {sentence}"


def test_exact_observed_failing_sentences():
    for sentence in EXACT_OBSERVED_FAILING_SENTENCES:
        is_emerg = _is_triage_emergency(sentence)
        assert is_emerg is True, f"Failed emergency for observed sentence: '{sentence}'"


@pytest.mark.parametrize("negation", NEGATIONS_DATA)
def test_negations_not_emergency(negation):
    res = classify_input(negation)
    assert res.is_emergency is False, f"Negation incorrectly flagged as emergency in classify_input: '{negation}'"
    hit, _ = match_red_flags(negation)
    assert hit is False, f"Negation incorrectly flagged as emergency in red_flag_patterns: '{negation}'"


# -----------------------------------------------------------------------------
# 2. HTTP Endpoints Tests Across Patient Conditions: DM-only, HTN-only, Dual
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("condition_set", [
    ["diabetes"],
    ["hypertension"],
    ["diabetes", "hypertension"],
])
def test_http_api_emergency_across_conditions(rsa_key_pair, condition_set):
    token = create_test_token(rsa_key_pair, sub=f"pat-emerg-{'-'.join(condition_set)}")
    bootstrap_patient(client, token, conditions=condition_set)
    headers = {"Authorization": f"Bearer {token}"}

    for test_phrase in EXACT_OBSERVED_FAILING_SENTENCES:
        # Start check-in
        start_res = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
        assert start_res.status_code == 200
        cid = start_res.json()["checkin_id"]

        # Submit emergency answer at greeting
        ans_res = client.post(
            f"/api/checkins/{cid}/answer",
            headers=headers,
            json={"answer": test_phrase, "step": "greeting"},
        )
        assert ans_res.status_code == 200
        data = ans_res.json()
        assert data["emergency"] is True, f"HTTP answer failed emergency for condition {condition_set} on '{test_phrase}'"
        assert data["complete"] is True


@pytest.mark.parametrize("condition_set", [
    ["diabetes"],
    ["hypertension"],
    ["diabetes", "hypertension"],
])
def test_http_api_negation_not_emergency(rsa_key_pair, condition_set):
    token = create_test_token(rsa_key_pair, sub=f"pat-neg-{'-'.join(condition_set)}")
    bootstrap_patient(client, token, conditions=condition_set)
    headers = {"Authorization": f"Bearer {token}"}

    # Start check-in
    start_res = client.post("/api/checkins/start", headers=headers, json={"mode": "isolated"})
    assert start_res.status_code == 200
    cid = start_res.json()["checkin_id"]

    # Submit negation answer at greeting
    ans_res = client.post(
        f"/api/checkins/{cid}/answer",
        headers=headers,
        json={"answer": "seene mein dard nahi hai bilkul theek hoon", "step": "greeting"},
    )
    assert ans_res.status_code == 200
    data = ans_res.json()
    assert data["emergency"] is False
    assert data["complete"] is False
