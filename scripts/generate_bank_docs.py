"""
Generates docs/INTERVIEW_QUESTION_BANK.md from the modular JSON Question Bank.
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend-poc-technical")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from agents.interview_bank.loader import get_default_bank


def generate_bank_markdown() -> str:
    bank = get_default_bank()
    sources = bank.get_sources()
    items = bank.all_items()

    md = """# Clinical Interview Question Bank Register (Interview Engine v3)

> **STATUS: PROPOSED, NOT REVIEWED BY A CLINICIAN.**
> Every question, template, and clinical rationale in this document is proposed decision support.
> It is **not clinical guidance**. A qualified clinician must review and approve this document before anyone relies on it for real patients.
> All Urdu script and Roman Urdu translations are marked **needs native speaker review**.

---

## 1. Modular Question Inventory

| ID | Module | Slot | Priority | English Template (`template_en`) | Urdu Script (`template_ur`) | Roman Urdu (`template_roman_ur`) | Source Key | Can Raise Level |
|---|---|---|---|---|---|---|---|---|
"""
    for it in sorted(items, key=lambda x: (x.module, x.id)):
        en = it.template_en.replace("|", "\\|")
        ur = it.template_ur.replace("|", "\\|")
        rur = it.template_roman_ur.replace("|", "\\|")
        can_r = f"Yes (`{it.rule_id}`)" if it.can_raise_level else "No"
        md += f"| `{it.id}` | `{it.module}` | `{it.slot}` | `{it.priority_class}` | {en} | {ur} | {rur} | `{it.source}` | {can_r} |\n"

    md += """
---

## 2. Guideline & Literature Sources Register

| Source Key | Official Title / Citation | Verification Status | Clinical Purpose / Note |
|---|---|---|---|
"""
    for s_key, s_data in sorted(sources.items()):
        title = s_data.get("title", "").replace("|", "\\|")
        status = s_data.get("status", "clinician review needed")
        notes = s_data.get("notes", "").replace("|", "\\|")
        md += f"| `{s_key}` | {title} | **{status}** | {notes} |\n"

    md += """
---

## 3. Symptom Drill-Down Probes (Follow-Up Chains)

| Symptom Category | Probe Slot | English Probe Question | Answer Type | Rationale |
|---|---|---|---|---|
"""
    probes = bank.get_probes()
    for cat, p_list in sorted(probes.items()):
        for p in p_list:
            slot = p.get("slot", "")
            en_p = p.get("template_en", "").replace("|", "\\|")
            atype = p.get("answer_type", "yes_no")
            why = p.get("why_text", "").replace("|", "\\|")
            md += f"| `{cat}` | `{slot}` | {en_p} | `{atype}` | {why} |\n"

    return md


def main():
    content = generate_bank_markdown()
    doc_path = os.path.join(REPO_ROOT, "docs", "INTERVIEW_QUESTION_BANK.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Question Bank documentation written to {doc_path}")


if __name__ == "__main__":
    main()
