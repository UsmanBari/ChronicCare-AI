import json
import subprocess
import sys
from pathlib import Path

# Get commits touching tests/sim/personas.json
cmd = ["git", "log", "--follow", "--format=%H %s", "--", "tests/sim/personas.json"]
out = subprocess.check_output(cmd, encoding="utf-8").strip().splitlines()
commits = [line.split(" ", 1) for line in out]
print("Commits touching personas.json:")
for h, s in commits:
    print(f"  {h[:7]} {s}")

history_by_id = {}

for h, s in reversed(commits):
    content = subprocess.check_output(["git", "show", f"{h}:tests/sim/personas.json"], encoding="utf-8")
    data = json.loads(content)
    print(f"\nCommit {h[:7]} ({s}): Total personas = {len(data)}")
    for p in data:
        pid = p["id"]
        exp_lvl = p.get("expected_level")
        exp_triage = p.get("expected_triage_level")
        author = p.get("author")
        if pid not in history_by_id:
            history_by_id[pid] = []
        history_by_id[pid].append((h[:7], exp_triage, exp_lvl, author, p.get("name"), p.get("archetype")))

print("\n--- Changes across commits for existing personas ---")
changes_found = False
for pid, records in history_by_id.items():
    if len(records) > 1:
        # Check if expected levels changed
        first = records[0]
        for r in records[1:]:
            if r[1] != first[1] or (r[2] is not None and first[2] is not None and r[2] != first[2]):
                print(f"Persona {pid} changed level! {first[0]}: triage={first[1]}, lvl={first[2]} -> {r[0]}: triage={r[1]}, lvl={r[2]}")
                changes_found = True
if not changes_found:
    print("NO persona had its expected level changed between commits!")

# Load current personas.json
with open("tests/sim/personas.json", "r", encoding="utf-8") as f:
    current_personas = json.load(f)

print(f"\nCurrent personas count: {len(current_personas)}")
print("\n" + "=" * 100)
print(f"{'ID':<32} | {'ARCHETYPE':<28} | {'EXPECTED_LEVEL':<15} | {'AUTHOR':<10}")
print("=" * 100)
for p in current_personas:
    pid = p.get("id", "")
    arch = p.get("archetype", "")
    exp = p.get("expected_level", p.get("expected_triage_level", ""))
    auth = p.get("author", "N/A")
    print(f"{pid:<32} | {arch:<28} | {exp:<15} | {auth:<10}")
print("=" * 100)
