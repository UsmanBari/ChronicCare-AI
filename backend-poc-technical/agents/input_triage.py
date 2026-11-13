"""
Deterministic Input Triage & Odd-Input Handler (Interview Engine v3).

Evaluates patient responses in strict, non-negotiable priority order:
1. Stage-1 Red-Flag / Danger-Phrase Screen (Emergency)
2. Self-Harm / Hopelessness Screen (Urgent Safety Alert)
3. Pregnancy Statement (Eligibility Exit)
4. Minor Mention (Adults-Only Excluded)
5. Odd-Input Classes (Rules-based with fixed multilingual response templates)

Odd Input Classes:
- chitchat_joke
- romantic (Polite boundary + offers ONE optional sexual function check)
- abuse
- gibberish_emoji_empty
- medical_advice_dose_request (Logged as question for clinician)
- fear_prognosis (Logged with clinician review flag)
- about_bot
- third_party_report
- prompt_injection
- non_answer
- repeated_answer
- wrong_language
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from agents.adaptive_interview_agent import (
    _CLAUSE_BREAK,
    _is_negated,
    _is_past_event,
    _normalize,
    get_red_flag_level,
    run_stage1_red_flag_screen,
)
from data_sources.validation import detect_pregnancy_statement


# =============================================================================
# Multilingual Danger-Phrase Patterns & Negation Screen (Emergency)
# =============================================================================
MULTILINGUAL_DANGER_CATEGORIES: Dict[str, List[str]] = {
    "chest_pain": [
        "crushing chest pain", "severe chest pressure", "chest hurts badly",
        "heavy chest pain", "chest pain radiating", "pain in my chest", "chest tightness",
        "crushing chest tightness", "crushing pain in my chest",
        "pain going down my left arm", "pain in my left arm and jaw", "left jaw pain with pressure",
        "pain in my left arm", "left arm pain", "left jaw pain",
        "seene mein shadeed dard", "seene me shadeed dard", "chhati me shadeed dard",
        "seene par shadeed bojh", "seene par shadeed dabao", "seene me dard", "chhati me dard",
        "bayein bazu me dard", "bayein bazu mein dard", "bayein bazu aur jabray me dard",
        "bayein jabray me dard", "baayein baazu me dard", "seene me dabao aur bayein bazu me dard",
        "seene mein shadeed dabao aur bayein baazu me dard",
        "mujhe seene mein shadeed dard hai", "mujhe seene me shadeed dard hai",
        "mujhe seene mein shadeed dard", "mujhe seene me shadeed dard",
        "seene mein shadeed dard hai", "seene me shadeed dard hai",
        "seene mein shadeed dard ho raha hai", "seene me shadeed dard ho raha hai",
        "seene mein dard ho raha hai", "seene me dard ho raha hai",
        "seene mein bohat dard hai", "seene me bohat dard hai",
        "seene mein bohat dard ho raha hai", "seene me bohat dard ho raha hai",
        "seene mein bohat dard", "seene me bohat dard",
        "seene mein sakht dard hai", "seene me sakht dard hai",
        "seene mein sakht dard ho raha hai", "seene me sakht dard ho raha hai",
        "seene mein sakht dard", "seene me sakht dard",
        "seene mein tez dard hai", "seene me tez dard hai",
        "seene mein tez dard", "seene me tez dard",
        "seene par shadeed bojh ho raha hai", "seene par bojh ho raha hai",
        "seene par shadeed dabao ho raha hai", "seene par dabao ho raha hai",
        "seene pe shadeed bojh", "seene pe shadeed dabao",
        "seene pe bojh", "seene pe dabao",
        "chhati mein shadeed dard ho raha hai", "chhati me shadeed dard ho raha hai",
        "chhati mein dard ho raha hai", "chhati me dard ho raha hai",
        "dil mein shadeed dard ho raha hai", "dil me shadeed dard ho raha hai",
        "dil mein shadeed dard", "dil me shadeed dard",
        "dil mein sakht dard", "dil me sakht dard",
        "dil mein dard ho raha hai", "dil me dard ho raha hai",
        "dil mein dard", "dil me dard",
        "سینے میں شدید درد", "سینے پر شدید دباؤ", "چھاتی میں درد", "سینے میں درد",
        "بائیں بازو میں درد", "بائیں جبڑے میں درد", "بائیں بازو اور جبڑے میں درد",
        "سینے میں شدید درد اور بائیں بازو میں درد", "سینے پر شدید دباؤ اور بائیں بازو میں درد",
        "مجھے سینے میں شدید درد ہو رہا ہے", "سینے میں شدید درد ہو رہا ہے",
        "سینے میں بہت درد ہو رہا ہے", "سینے میں بہت درد", "سینے میں درد ہو رہا ہے",
        "سینے میں سخت درد ہو رہا ہے", "سینے میں سخت درد",
        "سینے میں تیز درد ہو رہا ہے", "سینے میں تیز درد",
        "سینے پر شدید بوجھ ہو رہا ہے", "سینے پر بوجھ ہو رہا ہے",
        "سینے پر شدید دباؤ ہو رہا ہے", "سینے پر دباؤ ہو رہا ہے",
        "چھاتی میں شدید درد ہو رہا ہے", "چھاتی میں درد ہو رہا ہے",
        "چھاتی پر شدید بوجھ", "چھاتی پر شدید دباؤ",
        "دل میں شدید درد ہو رہا ہے", "دل میں شدید درد",
        "دل میں سخت درد", "دل میں درد ہو رہا ہے", "دل میں درد",
    ],
    "breathing": [
        "can't breathe", "cannot breathe", "struggling for air", "severe shortness of breath",
        "gasping for air", "suffocating", "shortness of breath",
        "hard to breathe", "difficulty breathing", "difficult to breathe", "severe breathlessness",
        "trouble breathing", "struggling to breathe", "shortness of breath at rest",
        "saans lene me shadeed dushwari", "saans lene mein shadeed dushwari",
        "saans lene me dushwari", "saans lene mein dushwari",
        "saans lene me shadeed dushwari ho rahi hai", "saans lene mein shadeed dushwari ho rahi hai",
        "saans lene me dushwari ho rahi hai", "saans lene mein dushwari ho rahi hai",
        "saans lene me shadeed mushkil hai", "saans lene mein shadeed mushkil hai",
        "saans lene me shadeed mushkil", "saans lene mein shadeed mushkil",
        "saans lene me mushkil hai", "saans lene mein mushkil hai",
        "saans lene me mushkil", "saans lene mein mushkil",
        "saans lene me bohat mushkil hai", "saans lene mein bohat mushkil hai",
        "saans lene me bohat mushkil", "saans lene mein bohat mushkil",
        "saans lene me takleef hai", "saans lene mein takleef hai",
        "saans lene me takleef", "saans lene mein takleef",
        "saans bohat phool rahi hai", "saans bohat phool rahi",
        "saans phool rahi hai", "saans phool rahi",
        "sans bohat phool rahi hai", "sans bohat phool rahi",
        "sans phool rahi hai", "sans phool rahi",
        "saans bohat phool raha hai", "saans phool raha hai",
        "saans nahi aa rahi", "saans nahi aa raha", "sans nahi aa rahi", "sans nahi aa raha",
        "dum ghut raha", "dum ghut raha hai", "saans ruk rahi", "saans ruk rahi hai", "saans ukhad rahi hai",
        "سانس لینے میں شدید دشواری", "سانس لینے میں دشواری",
        "سانس لینے میں شدید دشواری ہو رہی ہے", "سانس لینے میں دشواری ہو رہی ہے",
        "سانس لینے میں شدید مشکل ہے", "سانس لینے میں شدید مشکل",
        "سانس لینے میں مشکل ہے", "سانس لینے میں مشکل",
        "سانس لینے میں بہت مشکل ہے", "سانس لینے میں بہت مشکل",
        "سانس لینے میں تکلیف ہے", "سانس لینے میں تکلیف",
        "سانس بہت پھول رہی ہے", "سانس بہت پھول رہی",
        "سانس پھول رہی ہے", "سانس پھول رہی",
        "سانس اکھڑ رہی ہے", "سانس اکھڑ رہی",
        "سانس نہیں آ رہی", "سانس نہیں آ رہا",
        "دم گھٹ رہا", "دم گھٹ رہا ہے", "سانس رک رہی", "سانس رک رہی ہے", "سانس بالکل رک رہی ہے",
    ],
    "confusion_and_stroke": [
        "speech is slurred", "face drooping", "one side of my body is weak",
        "can't move my left arm", "can't move my right arm", "face is drooping", "arm won't move",
        "don't know where i am", "dont know where i am", "do not know where i am",
        "don't know who i am", "dont know who i am", "disoriented",
        "my left arm and left side of my face suddenly feel numb and weak",
        "my left arm and left side of my face feel numb and weak",
        "left arm and left side of my face suddenly feel numb and weak",
        "left arm and left side of my face feel numb and weak",
        "left arm and face feel numb and weak", "left arm and face feel weak and numb",
        "numb and weak", "weak and numb",
        "left arm is numb and weak", "right arm is numb and weak",
        "my speech is slurred and i feel confused", "my speech is slurred and feel confused",
        "speech is slurred and i feel confused", "speech is slurred and feel confused",
        "slurred speech and confused", "slurred speech and feel confused",
        "feel confused and speech is slurred", "confused and slurred speech",
        "one side of my face is numb", "one side of my face is weak",
        "one side of my body is numb", "suddenly feel numb and weak", "suddenly feel weak and numb",
        "lost speech", "unable to speak", "cannot speak",
        "chehra aik taraf larak", "zabaan ladkhara", "aik taraf ki kamzori", "chehra latak",
        "samajh nahi aa raha main kahan hoon", "samajh nahi aa raha kahan hoon", "main kahan hoon",
        "nahi pata kahan hoon",
        "aik taraf ka bazu aur chehra sunn aur kamzor ho gaya hai",
        "aik taraf ka bazu aur chehra sunn aur kamzor",
        "ek taraf ka bazu aur chehra sunn aur kamzor",
        "bazu aur chehra sunn aur kamzor",
        "chehra terha ho gaya hai", "munh terha ho گیا hai", "munh aik taraf terha ho gaya",
        "zuban ladkhada rahi hai aur samajh nahi aa raha",
        "awaz ladkhada rahi hai aur samajh nahi aa raha",
        "zuban ladkhada rahi hai", "awaz ladkhada rahi hai",
        "bol nahi pa raha", "bol nahi pa rahi",
        "awaz band ho gayi hai", "awaz band ho gayi",
        "falij ho gaya hai", "falij ka asar ho gaya",
        "aadha jism sunn ho gaya hai", "adha jism sunn ho gaya hai",
        "aadha jism kamzor ho gaya hai", "adha jism kamzor ho gaya hai",
        "kuch samajh nahi aa raha main kahan hoon", "kuch samajh nahi aa raha",
        "زبان لڑکھڑا", "چہرہ ایک طرف لٹک", "ایک طرف کی شدید کمزوری", "چہرہ لٹک",
        "سمجھ نہیں آ رہا میں کہاں ہوں", "کہاں ہوں",
        "ایک طرف کا بازو اور چہرہ سن اور کمزور ہو گیا ہے",
        "ایک طرف کا بازو اور چہرہ سن اور کمزور", "بازو اور چہرہ سن اور کمزور",
        "ایک طرف کا چہرہ ٹیڑھا ہو گیا ہے", "چہرہ ٹیڑھا ہو گیا ہے", "منہ ٹیڑھا ہو گیا ہے",
        "زبان لڑکھڑا رہی ہے اور کچھ سمجھ نہیں آ رہا",
        "آواز لڑکھڑا رہی ہے اور کچھ سمجھ نہیں آ رہا",
        "زبان لڑکھڑا رہی ہے", "آواز لڑکھڑا رہی ہے",
        "بول نہیں پا رہا", "بول نہیں پا رہی",
        "آواز بند ہو گئی ہے", "آواز بند ہو گئی",
        "فالج ہو گیا ہے", "فالج کا اثر ہو گیا ہے",
        "آدھا جسم سن ہو گیا ہے", "آدھا جسم کمزور ہو گیا ہے",
        "کچھ سمجھ نہیں آ رہا میں کہاں ہوں", "کچھ سمجھ نہیں آ رہا",
    ],
    "loss_of_consciousness": [
        "fainted", "passed out", "blacked out", "lost consciousness", "collapsed",
        "be hosh ho gaya", "behosh ho gaya", "ghashi par gayi", "be hoshi", "ghashi tari",
        "aaj subah main behosh ho gayi thi", "aaj subah main behosh ho gaya tha",
        "aaj subah behosh ho gayi thi", "aaj subah behosh ho gaya tha",
        "main behosh ho gayi thi", "main behosh ho gaya tha",
        "behosh ho gayi thi", "behosh ho gaya tha", "behosh ho gai thi",
        "behosh ho gayi", "behosh ho gai",
        "be hosh ho gayi thi", "be hosh ho gaya tha",
        "be hosh ho gayi", "be hosh ho gai",
        "behosh hui thi", "behosh hua tha", "behosh hui", "behosh hua",
        "chakkar kha kar gir gayi thi", "chakkar kha kar gir gaya tha",
        "chakkar kha kar gir gayi", "chakkar kha kar gir گیا",
        "ghashi par gayi thi", "ghashi tari ho gayi",
        "بے ہوش ہو گیا", "غشی پڑ گئی", "بے ہوشی", "غشی طاری",
        "آج صبح میں بے ہوش ہو گئی تھی", "آج صبح میں بے ہوش ہو گیا تھا",
        "آج صبح بے ہوش ہو گئی تھی", "آج صبح بے ہوش ہو گیا تھا",
        "میں بے ہوش ہو گئی تھی", "میں بے ہوش ہو گیا تھا",
        "بے ہوش ہو گئی تھی", "بے ہوش ہو گیا تھا", "بے ہوش ہو گئی",
        "چکر کھا کر گر گئی تھی", "چکر کھا کر گر گیا تھا",
        "چکر کھا کر گر گئی", "چکر کھا کر گر گیا",
        "غشی پڑ گئی تھی", "غشی طاری ہو گئی",
    ],
    "severe_headache_thunderclap": [
        "worst headache of my life", "worst headache ever", "thunderclap headache",
        "sudden severe headache", "headache like an explosion",
        "zindagi ka shadeed tareen sar dard", "achanak intehai shadeed sar dard", "shadeed tareen sar dard",
        "زندگی کا شدید ترین سر درد", "اچانک شدید ترین سر درد",
    ],
    "vision_loss": [
        "sudden vision loss", "lost my vision", "went blind", "can't see at all", "cannot see anything",
        "achanak nazar chali gayi", "aankhon ke aage andhera", "nazar achanak chali gayi",
        "اچانک بینائی چلی گئی", "آنکھوں کے آگے اچانک اندھیرا", "آنکھوں کی بینائی چلی گئی",
    ],
    "unable_to_keep_fluids": [
        "cannot keep any fluids down", "can't keep any fluids down",
        "cannot keep fluids down", "can't keep fluids down", "unable to keep fluids down",
        "not able to keep fluids down",
        "cannot keep anything down", "can't keep anything down", "unable to keep anything down",
        "not able to keep anything down",
        "can't keep water down", "cannot keep water down", "unable to keep water down",
        "can't keep medicines down", "cannot keep medicines down", "unable to keep medicines down",
        "won't stay down", "wont stay down", "throwing up everything", "keep nothing down",
        "keep vomiting and cannot keep any fluids down", "keep vomiting and can't keep any fluids down",
        "i keep vomiting and cannot keep any fluids down", "i keep vomiting and can't keep any fluids down",
        "vomiting and cannot keep any fluids down", "vomiting and can't keep any fluids down",
        "unable to keep liquids down", "can't keep liquids down", "cannot keep liquids down",
        "paani bhi nahi rukta", "paani bhi nahi ruk raha", "paani bhi nahi ruk raha hai",
        "pani bhi nahi rukta", "pani bhi nahi ruk raha", "pani bhi nahi ruk raha hai",
        "kuch bhi hazam nahi ho raha", "kuch hazam nahi ho raha",
        "kuch bhi nahi ruk raha", "kuch nahi ruk raha",
        "kuch bhi pet mein nahi ruk raha", "kuch bhi pait mein nahi ruk raha",
        "dawa nahi ruk rahi", "dawai nahi ruk rahi",
        "dawa ulti mein nikal jati hai", "dawai ulti mein nikal jati hai",
        "پانی بھی نہیں رک رہا ہے", "پانی بھی نہیں رک رہا", "پانی بھی نہیں رکتا",
        "کچھ بھی نہیں رک رہا ہے", "کچھ بھی نہیں رک رہا",
        "کچھ بھی ہضم نہیں ہو رہا ہے", "کچھ بھی ہضم نہیں ہو رہا",
        "دوائی نہیں رک رہی ہے", "دوائی نہیں رک رہی",
        "دوا نہیں رک رہی ہے", "دوا نہیں رک رہی",
        "الٹی میں دوا نکل جاتی ہے", "الٹی میں دوائی نکل جاتی ہے",
    ],
    "dka_vomiting_high_glucose": [
        "vomiting nonstop", "vomiting non-stop", "can't keep anything down", "can't keep fluids down",
        "cannot keep anything down", "cannot keep fluids down", "unable to keep fluids down",
        "throwing up everything", "keep nothing down", "vomiting all day",
        "vomiting continuously", "vomiting with high sugar",
        "musalsal ultiyan", "ulti ruk nahi rahi", "paani bhi nahi rukta",
        "مسلسل الٹیاں", "الٹی رک نہیں رہی", "مسلسل قے اور الٹی", "پانی بھی نہیں رک رہا",
    ],
}

INABILITY_EXCEPTIONS = [
    "can't breathe", "cannot breathe", "can't move", "can't see", "cannot see", "can't keep",
    "cannot keep", "unable to keep", "won't stay down", "won't move", "unable to drink",
    "saans nahi aa rahi", "saans nahi aa raha", "sans nahi aa rahi", "sans nahi aa raha",
    "bol nahi pa raha", "bol nahi pa rahi", "ulti ruk nahi rahi", "paani bhi nahi rukta",
    "paani bhi nahi ruk raha", "pani bhi nahi rukta", "pani bhi nahi ruk raha",
    "سانس نہیں آ رہی", "سانس نہیں آ رہا", "بول نہیں پا رہا", "بول نہیں پا رہی",
    "الٹی رک نہیں رہی", "پانی بھی نہیں رک رہا", "پانی بھی نہیں رکتا",
    "don't know where i am", "dont know where i am", "do not know where i am",
    "samajh nahi aa raha main kahan hoon", "samajh nahi aa raha kahan hoon",
    "main kahan hoon", "nahi pata kahan hoon",
    "سمجھ نہیں آ رہا میں کہاں ہوں", "کہاں ہوں",
]

_ENGLISH_NEGATION_REGEX = re.compile(
    r"\b(no|not|never|without|denies|denied|none|did not|didn't|is not)\b",
    re.IGNORECASE
)

_URDU_ROMAN_NEGATIONS = [
    "nahi hai", "nahi hua", "nahi thi", "nahi", "nahin", "koi nahi", "kabhi nahi", "baghair", "bina",
    "theek hai", "bilkul theek", "theek chal", "koi takleef nahi", "koi dard nahi",
    "نہیں ہے", "نہیں ہوا", "نہیں تھی", "نہیں", "کوئی نہیں", "کبھی نہیں", "بغیر", "ٹھیک ہے",
    "بالکل ٹھیک", "کوئی تکلیف نہیں", "کوئی پریشانی نہیں", "کوئی درد یا تکلیف نہیں", "کوئی دباؤ نہیں", "کوئی دشواری نہیں", "کوئی لڑکھڑاہٹ نہیں"
]

def screen_multilingual_danger_phrases(text: str) -> Tuple[bool, Optional[str]]:
    """
    Screens for life-threatening danger phrases across English, Urdu, and Roman Urdu.
    Calls run_stage1_red_flag_screen FIRST as authoritative, then checks extra multilingual patterns,
    while ensuring Urdu/Roman Urdu post-negations are respected.
    """
    if not text or not text.strip():
        return False, None

    clean_text = text.strip()
    lowered = clean_text.lower()

    # 1. Direct inability emergencies containing negative words (e.g. 'can't breathe', 'saans nahi aa rahi')
    if not _is_past_event(lowered):
        for inab in INABILITY_EXCEPTIONS:
            if inab in lowered:
                if any(k in inab for k in ["saans", "سانس", "breathe"]):
                    return True, "breathing"
                if any(k in inab for k in ["bol", "بول", "move", "speech", "where i am", "kahan hoon", "کہاں ہوں"]):
                    return True, "confusion_and_stroke"
                if any(k in inab for k in ["see", "بینائی"]):
                    return True, "vision_loss"
                if any(k in inab for k in ["drink", "keep", "paani", "pani", "پانی", "stay down"]):
                    return True, "unable_to_keep_fluids"
                if any(k in inab for k in ["ulti", "الٹی"]):
                    return True, "dka_vomiting_high_glucose"
                return True, "danger_phrase"

    # 2. Authoritative base screen from clinical module FIRST
    base_flagged, base_cat = run_stage1_red_flag_screen(clean_text)
    if base_flagged:
        # Check if there is a Roman Urdu or Urdu negation present in the text that base screen missed
        has_ur_neg = any(neg in lowered for neg in _URDU_ROMAN_NEGATIONS)
        if not has_ur_neg:
            return True, base_cat or "danger_phrase"

    # 3. Multilingual and negation-aware inspection across clauses
    clauses = re.split(r"[,;.\n]+", lowered)

    for clause in clauses:
        clause_clean = clause.strip()
        if not clause_clean:
            continue
        if _is_past_event(clause_clean):
            continue

        for category, patterns in MULTILINGUAL_DANGER_CATEGORIES.items():
            for pat in patterns:
                pat_lower = pat.lower()
                if pat_lower in clause_clean:
                    # Check English negation cues in this clause before the pattern or general
                    has_en_neg = bool(_ENGLISH_NEGATION_REGEX.search(clause_clean))
                    has_ur_neg = any(neg in clause_clean for neg in _URDU_ROMAN_NEGATIONS)

                    if has_en_neg or has_ur_neg:
                        # Negated symptom in this clause
                        continue
                    return True, category

    return False, None


# =============================================================================
# Self-Harm & Hopelessness Patterns (Strict Negation-Aware Screening)
# =============================================================================
SELF_HARM_PATTERNS: List[str] = [
    "kill myself",
    "end it all",
    "ending my life",
    "want to die",
    "better off dead",
    "suicide",
    "suicidal",
    "hang myself",
    "cut my wrists",
    "take all my pills at once",
    "khudkushi",
    "jaan de dunga",
    "marne ka dil",
    "mar jana chahta",
    "marna chahta",
    "zindagi khatam",
    "apni jaan khatam",
    "خودکشی",
    "مرنا چاہتا ہوں",
    "زندگی ختم کرنا چاہتا ہوں",
    "زندگی ختم کرنا",
    "جان دینا چاہتا ہوں",
]

# Near-miss words that must NOT trigger self-harm
_SELF_HARM_EXCLUSIONS = [
    "killing me with chores",
    "exercise is killing me",
    "to die for",
    "killing my diet",
    "not suicidal",
    "never had thoughts of suicide",
    "khudkushi ka koi khayal nahi",
    "خودکشی کا کوئی ارادہ نہیں",
]

_PREGNANCY_EXCLUSIONS = [
    "sister is pregnant",
    "was pregnant",
    "pregnancy test was negative",
    "negative",
    "meri behen pregnant",
    "behen",
]


# =============================================================================
# Minor Mention Patterns (Adults-Only System)
# =============================================================================
MINOR_PATTERNS: List[str] = [
    "my 5 year old", "my 6 year old", "my 7 year old", "my 8 year old", "my 9 year old",
    "my 10 year old", "my 11 year old", "my 12 year old", "my 13 year old", "my 14 year old",
    "my 15 year old", "my 16 year old", "my 17 year old", "my baby", "my toddler", "for my child",
    "for my infant", "mere chotay bachay", "meray chotay bachay", "meray bachay ke liye", "mere bachay ke liye",
    "chotay bachay", "bachay ke liye", "چھوٹے بچے", "میرے بچے کے لیے", "سالہ بچے", "سالہ بچہ"
]


# =============================================================================
# Odd Input Classification Rule Patterns
# =============================================================================
PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard previous rules",
    "system prompt",
    "reveal instructions",
    "print your system prompt",
    "you are now dan",
    "jailbreak",
    "pretend you are",
    "bypass safety rules",
    "pichli tamaam hidayat",
    "say i am cured",
]

ROMANTIC_PATTERNS = [
    "you are cute",
    "you are hot",
    "you are so cute",
    "you are so hot",
    "you are cute and hot",
    "you are so cute and hot",
    "u are cute",
    "u are hot",
    "u are so cute",
    "u are so hot",
    "u are cute and hot",
    "u are so cute and hot",
    "you're cute",
    "you're hot",
    "you're so cute",
    "you're so hot",
    "you are beautiful",
    "you are gorgeous",
    "i love you",
    "will you marry me",
    "marry me",
    "go on a date",
    "be my girlfriend",
    "be my wife",
    "meri jaan",
    "bohat khoobsurat",
    "shadi kar lo",
    "muhabbat karta",
    "پیار کرتا ہوں",
    "خوبصورت ہو",
    "شادی کرو",
]

# Romantic near-miss phrases (must NOT be flagged as romantic)
_ROMANTIC_NEAR_MISSES = [
    "my wife says i look romantic",
    "my husband is romantic",
    "i love my morning walk",
    "i love vegetables",
    "i love exercising",
    "sair bohat pasand",
    "صبح کی سیر بہت پسند",
    "biwi kehti hai",
    "baby is so cute",
    "baby is cute",
    "so hot today",
    "so hot outside",
    "feet feel so hot",
    "it is so hot",
]

CHITCHAT_PATTERNS = [
    "tell me a joke",
    "funny joke",
    "make me laugh",
    "knock knock",
    "what is the weather",
    "what's the weather",
    "how is your day",
    "how was your weekend",
    "what's up",
    "whats up",
    "who is your favorite",
    "kya haal hai bot",
    "lateefa",
    "mausam kaisa",
    "لطیفہ",
    "موسم کیسا ہے",
    "ویک اینڈ",
]

ABUSE_PATTERNS = [
    "you are stupid",
    "you are an idiot",
    "shut up",
    "fuck you",
    "fucking bot",
    "piece of shit",
    "useless bot",
    "bakwaas bot",
    "kuttiya",
    "chup kar",
    "بکواس بند کرو",
    "انتہائی بیکار",
]

ADVICE_PATTERNS = [
    "should i increase my dose",
    "should i double my medicine",
    "should i stop taking",
    "can i stop taking",
    "can i stop my medicine",
    "stop taking metformin",
    "what medicine should i take",
    "prescribe me",
    "what dose should i take",
    "do i have diabetes",
    "do i have kidney failure",
    "kya main dose barha loon",
    "dose barha",
    "band kar doon",
    "kya dawa band kar doon",
    "خوراک بڑھا",
    "دوا بند",
]

FEAR_PATTERNS = [
    "will i die",
    "am i going to die",
    "is my heart going to stop",
    "am i having a heart attack",
    "have a stroke and die",
    "am i going to have a stroke",
    "kya meri maut ho jayegi",
    "kya main mar jaunga",
    "میری موت ہو جائے گی",
    "دل بند ہو جائے گا",
]

ABOUT_BOT_PATTERNS = [
    "are you a human",
    "are you a real human doctor",
    "are you a real doctor",
    "are you a real person",
    "who created you",
    "are you chatgpt",
    "are you an ai",
    "are you a robot",
    "kya tum insan ho",
    "kya tum doctor ho",
    "انسان ہو یا بوٹ",
    "اصلی ڈاکٹر",
]

THIRD_PARTY_PATTERNS = [
    "answering for my father",
    "answering for my mother",
    "filling this check-in for my mother",
    "filling this checkin for my mother",
    "for my mother",
    "for my father",
    "this is for my husband",
    "for my husband",
    "filling this for my husband",
    "filling this for my wife",
    "for my dad",
    "for my mom",
    "mere walid ke liye",
    "meri ammi ke liye",
    "والد کے لیے",
    "والدہ کے لیے",
]


@dataclass
class TriageInputResult:
    category: str  # "danger_phrase", "self_harm", "pregnancy", "minor_mention", "odd_input", "normal_clinical"
    odd_class: Optional[str] = None
    trigger_detail: Optional[str] = None
    response_key: Optional[str] = None
    is_emergency: bool = False
    is_urgent_safety: bool = False
    needs_clinician_flag: bool = False
    is_off_topic: bool = False


def check_self_harm(text: str) -> bool:
    """Detects self-harm or suicidal statements using negation-aware clause parsing."""
    if not text or not text.strip():
        return False
    lowered_full = text.lower()
    if any(ex in lowered_full for ex in _SELF_HARM_EXCLUSIONS):
        return False

    normalized_full = _normalize(text)
    for clause in _CLAUSE_BREAK.split(normalized_full):
        clause_clean = clause.strip()
        if not clause_clean:
            continue
        for pattern in SELF_HARM_PATTERNS:
            for match in re.finditer(re.escape(pattern), clause_clean):
                if not _is_negated(clause_clean, match.start()):
                    return True
    return False


def check_minor_mention(text: str) -> bool:
    """Detects mentions of children/infants as the patient."""
    lowered = text.lower()
    return any(p in lowered for p in MINOR_PATTERNS)


def classify_input(text: str, consecutive_odd_count: int = 0) -> TriageInputResult:
    """
    Classifies any patient response in priority order:
    1. Danger phrases (Emergency)
    2. Self-harm / hopelessness (Urgent Safety)
    3. Pregnancy statement (Eligibility)
    4. Minor mention (Adults Only)
    5. Odd-input classes (Rule-based response)
    6. Normal clinical response
    """
    if not text or not text.strip():
        return TriageInputResult(
            category="odd_input",
            odd_class="gibberish_emoji_empty",
            response_key="gibberish_emoji_empty",
            is_off_topic=True,
        )

    clean_text = text.strip()
    lowered = clean_text.lower()

    # 1. Danger-phrase screen FIRST (Multilingual and negation-aware)
    is_danger, danger_cat = screen_multilingual_danger_phrases(clean_text)
    if is_danger:
        level = get_red_flag_level(danger_cat)
        return TriageInputResult(
            category="danger_phrase",
            trigger_detail=danger_cat,
            is_emergency=(level == "emergency"),
            is_urgent_safety=(level == "urgent"),
        )

    # 2. Self-harm / hopelessness screen SECOND
    if check_self_harm(clean_text):
        return TriageInputResult(
            category="self_harm",
            trigger_detail="self_harm_statement",
            response_key="self_harm",
            is_urgent_safety=True,
            needs_clinician_flag=True,
        )

    # 3. Pregnancy statement THIRD (Check exclusions for past or 3rd party pregnancy)
    if not any(ex in lowered for ex in _PREGNANCY_EXCLUSIONS):
        if detect_pregnancy_statement(clean_text):
            return TriageInputResult(
                category="pregnancy",
                trigger_detail="patient_reported_pregnancy",
            )

    # 4. Minor mention FOURTH
    if check_minor_mention(clean_text):
        return TriageInputResult(
            category="minor_mention",
            trigger_detail="pediatric_mention",
        )

    # 5. Odd Input Classes
    # 5a. Prompt Injection
    if any(p in lowered for p in PROMPT_INJECTION_PATTERNS):
        return TriageInputResult(
            category="odd_input",
            odd_class="prompt_injection",
            response_key="prompt_injection",
            is_off_topic=True,
        )

    # 5b. Romantic / Flirtatious (Check near-miss exclusions)
    if not any(nm in lowered for nm in _ROMANTIC_NEAR_MISSES):
        if any(p in lowered for p in ROMANTIC_PATTERNS):
            return TriageInputResult(
                category="odd_input",
                odd_class="romantic",
                response_key="romantic",
                is_off_topic=True,
            )

    # 5c. Medical Advice / Dose Change Request
    if any(p in lowered for p in ADVICE_PATTERNS):
        return TriageInputResult(
            category="odd_input",
            odd_class="medical_advice_dose_request",
            response_key="medical_advice_dose_request",
            needs_clinician_flag=True,
            is_off_topic=True,
        )

    # 5d. Fear / Prognosis
    if any(p in lowered for p in FEAR_PATTERNS):
        return TriageInputResult(
            category="odd_input",
            odd_class="fear_prognosis",
            response_key="fear_prognosis",
            needs_clinician_flag=True,
            is_off_topic=True,
        )

    # 5e. Abuse / Insult
    if any(p in lowered for p in ABUSE_PATTERNS):
        return TriageInputResult(
            category="odd_input",
            odd_class="abuse",
            response_key="abuse",
            is_off_topic=True,
        )

    # 5f. Chitchat / Jokes
    if any(p in lowered for p in CHITCHAT_PATTERNS):
        return TriageInputResult(
            category="odd_input",
            odd_class="chitchat_joke",
            response_key="chitchat_joke",
            is_off_topic=True,
        )

    # 5g. Questions about the bot
    if any(p in lowered for p in ABOUT_BOT_PATTERNS):
        return TriageInputResult(
            category="odd_input",
            odd_class="about_bot",
            response_key="about_bot",
            is_off_topic=True,
        )

    # 5h. Third-party report
    if any(p in lowered for p in THIRD_PARTY_PATTERNS):
        return TriageInputResult(
            category="odd_input",
            odd_class="third_party_report",
            response_key="third_party_report",
            is_off_topic=True,
        )

    # 5i. Gibberish / Only Emojis / Only Punctuation
    alnums = re.findall(r"[\w\d]+", clean_text)
    if not alnums or re.match(r"^[\W_]+$", clean_text) or re.match(r"^(asdf|qwer|zxcv|1111|0000|###|\?\?\?)+.*$", lowered):
        return TriageInputResult(
            category="odd_input",
            odd_class="gibberish_emoji_empty",
            response_key="gibberish_emoji_empty",
            is_off_topic=True,
        )

    # 5j. Non-answer fillers
    if lowered in ("hmm", "hmmm", "idk", "dunno"):
        return TriageInputResult(
            category="odd_input",
            odd_class="non_answer",
            response_key="non_answer",
            is_off_topic=True,
        )

    return TriageInputResult(
        category="normal_clinical",
    )
