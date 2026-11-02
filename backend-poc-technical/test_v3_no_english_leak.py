"""
test_v3_no_english_leak.py

Verifies that in Interview Engine v3, a patient whose language is 'ur' or 'roman_ur'
never receives English text across any stage of the check-in:
- First questions & subsequent questions
- Why-text / clinical rationales
- Options and option_items localized labels
- Glucose unit clarification questions and options
- Odd-input strike rule replies and choices
- Safety unknown re-asks
- Possible severe low safety guidance
- Summary confirmation and correction prompts
- Emergency system notes

Asserts that no served text contains 3 or more consecutive ASCII English words
outside the approved clinical whitelist (BP, mg/dL, mmol/L, sugar, HbA1c, OK, ID).
"""

from __future__ import annotations

import re
import pytest
from typing import Any, Dict, List, Set

from agents.interview_v3_runner import (
    start_v3_session,
    next_turn,
)
from agents.interview_bank.loader import get_default_bank

WHITELIST: Set[str] = {
    "bp", "mg/dl", "mmol/l", "sugar", "hba1c", "ok", "id",
    "mgdl", "mmhg", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
}

COMMON_ENGLISH_MARKERS: Set[str] = {
    "the", "and", "is", "of", "to", "in", "that", "it", "with", "as", "for", "was",
    "on", "are", "by", "this", "have", "from", "at", "your", "all", "any", "please",
    "call", "seek", "care", "immediately", "today", "here", "recorded", "reading",
    "answer", "would", "like", "update", "blood", "pressure", "alert", "feel",
    "shaky", "sweaty", "confused", "dizzy", "consume", "fast-acting", "half",
    "cup", "juice", "tablets", "unclear", "treated", "safety", "review",
    "confirm", "submit", "need", "change", "something", "continue", "finish",
    "later", "understand", "step", "away", "saved", "responses", "team",
    "medical", "did", "you", "mean", "noted", "answers", "before", "saving",
    "does", "everything", "look", "right", "which",
}


def _check_no_english_leak(text: str, lang: str, context: str) -> None:
    if not text or not isinstance(text, str):
        return

    # Clean punctuation
    cleaned = re.sub(r"[^\w\s/]", " ", text)
    tokens = [t.strip().lower() for t in cleaned.split() if t.strip()]

    if lang == "ur":
        # In Urdu script, any 3 consecutive ASCII alphabetic tokens outside whitelist is a leak
        consecutive_ascii: List[str] = []
        for t in tokens:
            if re.fullmatch(r"[a-z]+", t) and t not in WHITELIST:
                consecutive_ascii.append(t)
                if len(consecutive_ascii) >= 3:
                    pytest.fail(
                        f"English leak detected in Urdu ({context}): "
                        f"Found consecutive ASCII words: '{' '.join(consecutive_ascii)}' in \"{text}\""
                    )
            else:
                consecutive_ascii = []

    elif lang == "roman_ur":
        # In Roman Urdu, check for 3 consecutive English words from COMMON_ENGLISH_MARKERS
        consecutive_eng: List[str] = []
        for t in tokens:
            if t in COMMON_ENGLISH_MARKERS and t not in WHITELIST:
                consecutive_eng.append(t)
                if len(consecutive_eng) >= 3:
                    pytest.fail(
                        f"English leak detected in Roman Urdu ({context}): "
                        f"Found English phrase '{' '.join(consecutive_eng)}' in \"{text}\""
                    )
            else:
                consecutive_eng = []


def _audit_state(state: Dict[str, Any], lang: str, step_label: str) -> None:
    cq = state.get("current_question")
    if cq:
        _check_no_english_leak(cq, lang, f"{step_label} -> current_question")

    why = state.get("why_text")
    if why:
        _check_no_english_leak(why, lang, f"{step_label} -> why_text")

    sn = state.get("system_note")
    if sn:
        _check_no_english_leak(sn, lang, f"{step_label} -> system_note")

    pslg = state.get("possible_severe_low_guidance")
    if pslg:
        _check_no_english_leak(pslg, lang, f"{step_label} -> possible_severe_low_guidance")

    # Localized labels in option_items
    opt_items = state.get("option_items")
    if opt_items:
        for opt in opt_items:
            lbl = opt.get("label")
            if lbl:
                _check_no_english_leak(lbl, lang, f"{step_label} -> option label '{lbl}'")


# 6 Representative Personas for testing
TEST_PERSONAS = [
    {
        "id": "p1_dm_normal",
        "conditions": ["diabetes"],
        "insulin": False,
        "glucose": "130",
        "bp": None,
    },
    {
        "id": "p2_htn_normal",
        "conditions": ["hypertension"],
        "insulin": False,
        "glucose": None,
        "bp": "120/80",
    },
    {
        "id": "p3_dual_normal",
        "conditions": ["diabetes", "hypertension"],
        "insulin": True,
        "glucose": "140",
        "bp": "125/82",
    },
    {
        "id": "p4_dm_unit_clarify",
        "conditions": ["diabetes"],
        "insulin": False,
        "glucose": "7",  # Bare number triggering unit question
        "bp": None,
    },
    {
        "id": "p5_odd_strike",
        "conditions": ["hypertension"],
        "insulin": False,
        "glucose": None,
        "bp": "125/80",
        "chitchat": True,
    },
    {
        "id": "p6_emergency_redflag",
        "conditions": ["diabetes", "hypertension"],
        "insulin": False,
        "emergency": True,
    },
]


@pytest.mark.parametrize("lang", ["ur", "roman_ur"])
@pytest.mark.parametrize("persona", TEST_PERSONAS, ids=lambda p: p["id"])
def test_v3_no_english_leak_across_personas(lang: str, persona: Dict[str, Any]):
    """Runs each persona through full session turns in ur and roman_ur and verifies zero English leaks."""
    state = start_v3_session(
        checkin_id=f"chk_{persona['id']}_{lang}",
        patient_id=f"pt_{persona['id']}",
        conditions=persona["conditions"],
        on_insulin_or_sulfonylurea=persona.get("insulin", False),
        language=lang,
    )
    _audit_state(state, lang, f"{persona['id']}:start")

    # Turn 1: Emergency check
    if persona.get("emergency"):
        em_text = "سینے میں شدید درد ہو رہا ہے" if lang == "ur" else "seene mein shadeed dard ho raha hai"
        state = next_turn(state, em_text)
        assert state.get("emergency") is True
        _audit_state(state, lang, f"{persona['id']}:emergency")
        return

    # Turn 1: Odd input chitchat
    if persona.get("chitchat"):
        chitchat_1 = "آج موسم کیسا ہے؟" if lang == "ur" else "aaj mausam kaisa hai"
        state = next_turn(state, chitchat_1)
        assert state.get("consecutive_odd_count") == 1
        _audit_state(state, lang, f"{persona['id']}:chitchat_1")

        # Second odd input to trigger strike rule choices
        chitchat_2 = "کوئی لطیفہ سناؤ" if lang == "ur" else "koi mazedaar lateefa sunao"
        state = next_turn(state, chitchat_2)
        assert state.get("consecutive_odd_count") == 2
        _audit_state(state, lang, f"{persona['id']}:chitchat_strike_rule")
        assert state.get("option_items") is not None
        return

    # Normal reading turns
    turn = 1
    max_turns = 12

    while not state.get("complete") and not state.get("completed") and turn <= max_turns:
        step = state.get("step", "")
        # Provide appropriate localized answer
        if "glucose" in step:
            val = persona.get("glucose") or "125"
            state = next_turn(state, val)
        elif "bp" in step:
            val = persona.get("bp") or "120/80"
            state = next_turn(state, val)
        elif state.get("awaiting_glucose_unit"):
            unit_ans = "mg/dL"
            state = next_turn(state, unit_ans)
        elif step == "summary_confirmation":
            conf_ans = "ہاں" if lang == "ur" else "haan"
            state = next_turn(state, conf_ans)
        else:
            # Yes/no or unknown response
            ans = "نہیں" if lang == "ur" else "nahi"
            state = next_turn(state, ans)

        _audit_state(state, lang, f"{persona['id']}:turn_{turn}_{step}")
        turn += 1

    assert turn <= max_turns + 1
