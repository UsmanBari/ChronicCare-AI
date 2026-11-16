"""
backend-poc-technical/test_red_flag_childhood_seizure.py

Tests for childhood and remote-past seizure false-red suppression and
active acute seizure detection across English, Roman Urdu, and Urdu script.

Rule:
Remote-past markers ("as a child", "bachpan mein", "childhood", "years ago", "saal pehle", "in 2010" etc.)
COMBINED WITH a recovery cue ("nothing since", "never again", "ab nahi", "theek hoon tab se", "no seizures since" etc.)
in the same clause mean the seizure / unconsciousness is NOT an emergency.
Active seizure sets (e.g. rf12) must remain Red: "had a seizure 10 minutes ago",
"seizures happening right now", "mirgi ka dora par raha hai" etc.
"""

import pytest
from agents.red_flag_patterns import decide_red, match


# -----------------------------------------------------------------------------
# English Tests (2)
# -----------------------------------------------------------------------------

def test_childhood_seizure_remote_past_recovered_en():
    """
    Childhood seizure with recovery ('nothing since') is NOT an acute Red emergency.
    """
    text = "I had a seizure as a child but nothing since"
    dec = decide_red(text)
    hit, cat = match(text)

    assert dec.is_red is False, f"Expected is_red=False for benign remote past seizure, got {dec}"
    assert dec.category is None
    assert hit is False
    assert cat is None


def test_childhood_seizure_active_recurrence_en():
    """
    Active / acute recurrence after childhood seizure MUST remain Red (loss_of_consciousness).
    """
    text = "I had a seizure as a child and another one 10 minutes ago"
    dec = decide_red(text)
    hit, cat = match(text)

    assert dec.is_red is True, f"Expected is_red=True for active acute seizure recurrence, got {dec}"
    assert dec.category == "loss_of_consciousness"
    assert hit is True
    assert cat == "loss_of_consciousness"


# -----------------------------------------------------------------------------
# Roman Urdu Tests (2)
# -----------------------------------------------------------------------------

def test_childhood_seizure_remote_past_recovered_roman_ur():
    """
    Roman Urdu childhood seizure with recovery ('ab nahi') is NOT an acute Red emergency.
    """
    text = "bachpan mein mirgi ka dora para tha, ab nahi"
    dec = decide_red(text)
    hit, cat = match(text)

    assert dec.is_red is False, f"Expected is_red=False for Roman Urdu remote past seizure, got {dec}"
    assert dec.category is None
    assert hit is False
    assert cat is None


def test_childhood_seizure_active_recurrence_roman_ur():
    """
    Roman Urdu acute seizure recurrence ('abhi dobara par raha hai') MUST remain Red.
    """
    text = "bachpan mein mirgi ka dora para tha aur abhi dobara par raha hai"
    dec = decide_red(text)
    hit, cat = match(text)

    assert dec.is_red is True, f"Expected is_red=True for Roman Urdu acute seizure recurrence, got {dec}"
    assert dec.category == "loss_of_consciousness"
    assert hit is True
    assert cat == "loss_of_consciousness"


# -----------------------------------------------------------------------------
# Urdu Script Tests (2)
# -----------------------------------------------------------------------------

def test_childhood_seizure_remote_past_recovered_ur():
    """
    Urdu script childhood seizure with recovery ('اب نہیں') is NOT an acute Red emergency.
    """
    text = "بچپن میں مرگی کا دورہ پڑا تھا، اب نہیں"
    dec = decide_red(text)
    hit, cat = match(text)

    assert dec.is_red is False, f"Expected is_red=False for Urdu script remote past seizure, got {dec}"
    assert dec.category is None
    assert hit is False
    assert cat is None


def test_childhood_seizure_active_recurrence_ur():
    """
    Urdu script acute seizure recurrence ('ابھی دورہ پڑ رہا ہے') MUST remain Red.
    """
    text = "بچپن میں مرگی کا دورہ پڑا تھا اور ابھی دورہ پڑ رہا ہے"
    dec = decide_red(text)
    hit, cat = match(text)

    assert dec.is_red is True, f"Expected is_red=True for Urdu script acute seizure recurrence, got {dec}"
    assert dec.category == "loss_of_consciousness"
    assert hit is True
    assert cat == "loss_of_consciousness"
