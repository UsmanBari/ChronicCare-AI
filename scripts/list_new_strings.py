"""
list_new_strings.py - List all Urdu and Roman Urdu strings added or modified since 26 Oct 2026.
Compares app/translations/index.ts and backend-poc-technical/agents/interview_bank/messages.json
against base commit ea6c9a1 (26 Oct 2026).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_COMMIT = "ea6c9a1"  # 26 Oct 2026


def get_file_at_commit(commit: str, rel_path: str) -> str:
    try:
        res = subprocess.run(
            ["git", "show", f"{commit}:{rel_path}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(REPO_ROOT),
            check=True,
        )
        return res.stdout
    except subprocess.CalledProcessError:
        return ""


def parse_messages_json(content: str) -> dict:
    if not content.strip():
        return {}
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return {}


def parse_ts_dict(content: str, section: str) -> dict[str, str]:
    """Parse key-value pairs from either en: { ... } or ur: { ... }."""
    # Find start of section
    start_pat = rf"^\s*{section}:\s*\{{"
    match = re.search(start_pat, content, re.MULTILINE)
    if not match:
        return {}
    
    start_pos = match.end()
    # Find closing brace by bracket counting
    depth = 1
    i = start_pos
    while i < len(content) and depth > 0:
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
        i += 1
    
    block = content[start_pos:i-1]
    
    # Extract keys and values: key: "value" or key: 'value' or multiline strings
    # Regex matching key: string
    entries = {}
    pattern = re.compile(r'^\s*([a-zA-Z0-9_]+)\s*:\s*([\'"`])(.*?)(?<!\\)\2\s*,?', re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(block):
        k = m.group(1)
        v = m.group(3).replace('\\"', '"').replace("\\'", "'").replace('\\n', '\n')
        entries[k] = v
    return entries


def main():
    print("=" * 80)
    print("NEW STRINGS AUDIT SINCE 26 OCT 2026 (BASE COMMIT ea6c9a1)")
    print("=" * 80)

    # 1. messages.json
    rel_msgs = "backend-poc-technical/agents/interview_bank/messages.json"
    old_msgs_raw = get_file_at_commit(BASE_COMMIT, rel_msgs)
    curr_msgs_path = REPO_ROOT / rel_msgs
    curr_msgs_raw = curr_msgs_path.read_text(encoding="utf-8") if curr_msgs_path.exists() else ""

    old_msgs = parse_messages_json(old_msgs_raw)
    curr_msgs = parse_messages_json(curr_msgs_raw)

    print(f"\n--- 1. Backend Messages ({rel_msgs}) ---")
    new_msgs = []
    for k, v in curr_msgs.items():
        if k not in old_msgs:
            new_msgs.append((k, "ADDED", v))
        elif old_msgs[k] != v:
            new_msgs.append((k, "MODIFIED", v))

    print(f"Found {len(new_msgs)} added/modified keys:")
    for k, status, val in new_msgs:
        en = val.get("en", "")
        ur = val.get("ur", "")
        r_ur = val.get("roman_ur", "")
        print(f"[{status}] {k}:")
        print(f"  EN:       {en}")
        print(f"  UR:       {ur}")
        print(f"  ROMAN_UR: {r_ur}")

    # 2. app/translations/index.ts
    rel_trans = "app/translations/index.ts"
    old_trans_raw = get_file_at_commit(BASE_COMMIT, rel_trans)
    curr_trans_path = REPO_ROOT / rel_trans
    curr_trans_raw = curr_trans_path.read_text(encoding="utf-8") if curr_trans_path.exists() else ""

    old_ur = parse_ts_dict(old_trans_raw, "ur")
    curr_ur = parse_ts_dict(curr_trans_raw, "ur")
    curr_en = parse_ts_dict(curr_trans_raw, "en")

    print(f"\n--- 2. Frontend Translations ({rel_trans}) ---")
    new_trans = []
    for k, v in curr_ur.items():
        if k not in old_ur:
            new_trans.append((k, "ADDED", curr_en.get(k, ""), v))
        elif old_ur[k] != v:
            new_trans.append((k, "MODIFIED", curr_en.get(k, ""), v))

    print(f"Found {len(new_trans)} added/modified keys in Urdu translation dictionary:")
    for k, status, en_val, ur_val in new_trans:
        print(f"[{status}] {k}:")
        print(f"  EN: {en_val}")
        print(f"  UR: {ur_val}")

    print(f"\nTotal backend message additions/modifications: {len(new_msgs)}")
    print(f"Total frontend Urdu additions/modifications: {len(new_trans)}")
    print("Audit completed.")


if __name__ == "__main__":
    main()
