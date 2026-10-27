"""Build Guideline Corpus Manifest.

Inspects guideline PDFs under $CHRONICCARE_DATA_DIR/guidelines/, computes
file metadata, page count, SHA-256, reads the first 2 pages for copyright /
licence restrictions, evaluates allowed_for_rag status, and generates
docs/GUIDELINE_CORPUS.md.
"""

from datetime import datetime
import hashlib
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional
import pypdf

# Ensure utf-8 output
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_DIR = Path(os.getenv("CHRONICCARE_DATA_DIR", r"C:\Users\usmanbari\Desktop\Chronicare-data"))
GUIDELINES_DIR = DATA_DIR / "guidelines"
PERMISSIONS_DIR = GUIDELINES_DIR / "permissions"
LOGS_DIR = DATA_DIR / "rag" / "logs"

CORPUS_SPECS = [
    {
        "filename": "ada2026_sec02_diagnosis.pdf",
        "source_id": "ada_2026_sec02",
        "title": "ADA Standards of Care in Diabetes 2026 - Section 2: Diagnosis and Classification of Diabetes",
        "edition": "2026",
        "publisher": "American Diabetes Association",
        "url": "https://doi.org/10.2337/dc26-S002",
        "priority": 2,
    },
    {
        "filename": "ada2026_sec05_lifestyle.pdf",
        "source_id": "ada_2026_sec05",
        "title": "ADA Standards of Care in Diabetes 2026 - Section 5: Facilitating Positive Health Behaviors and Well-being to Improve Health Outcomes",
        "edition": "2026",
        "publisher": "American Diabetes Association",
        "url": "https://doi.org/10.2337/dc26-S005",
        "priority": 2,
    },
    {
        "filename": "ada2026_sec06_glycemic_goals_hypoglycemia.pdf",
        "source_id": "ada_2026_sec06",
        "title": "ADA Standards of Care in Diabetes 2026 - Section 6: Glycemic Goals, Hypoglycemia, and Hyperglycemic Crises",
        "edition": "2026",
        "publisher": "American Diabetes Association",
        "url": "https://doi.org/10.2337/dc26-S006",
        "priority": 2,
    },
    {
        "filename": "ada2026_sec10_cvd_risk.pdf",
        "source_id": "ada_2026_sec10",
        "title": "ADA Standards of Care in Diabetes 2026 - Section 10: Cardiovascular Disease and Risk Management",
        "edition": "2026",
        "publisher": "American Diabetes Association",
        "url": "https://doi.org/10.2337/dc26-S010",
        "priority": 2,
    },
    {
        "filename": "ada2026_sec11_ckd.pdf",
        "source_id": "ada_2026_sec11",
        "title": "ADA Standards of Care in Diabetes 2026 - Section 11: Chronic Kidney Disease and Risk Management",
        "edition": "2026",
        "publisher": "American Diabetes Association",
        "url": "https://doi.org/10.2337/dc26-S011",
        "priority": 2,
    },
    {
        "filename": "ada2026_sec13_older_adults.pdf",
        "source_id": "ada_2026_sec13",
        "title": "ADA Standards of Care in Diabetes 2026 - Section 13: Older Adults",
        "edition": "2026",
        "publisher": "American Diabetes Association",
        "url": "https://doi.org/10.2337/dc26-S013",
        "priority": 2,
    },
    {
        "filename": "aha_acc_2025_hbp_guideline.pdf",
        "source_id": "aha_acc_2025",
        "title": "2025 AHA/ACC Clinical Practice Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults",
        "edition": "2025",
        "publisher": "American Heart Association / American College of Cardiology",
        "url": "https://doi.org/10.1161/HYP.0000000000000249",
        "priority": 2,
    },
    {
        "filename": "who_2021_htn_pharmacological.pdf",
        "source_id": "who_2021_htn",
        "title": "Guideline for the Pharmacological Treatment of Hypertension in Adults",
        "edition": "2021",
        "publisher": "World Health Organization",
        "url": "https://www.who.int/publications/i/item/9789240033986",
        "priority": 3,
    },
    {
        "filename": "ish_2020_global_htn.pdf",
        "source_id": "ish_2020_htn",
        "title": "2020 International Society of Hypertension Global Hypertension Practice Guidelines",
        "edition": "2020",
        "publisher": "International Society of Hypertension",
        "url": "https://doi.org/10.1161/HYPERTENSIONAHA.120.15026",
        "priority": 3,
    },
    {
        "filename": "idf_dar_ramadan_2021.pdf",
        "source_id": "idf_dar_2021",
        "title": "IDF-DAR Diabetes and Ramadan: Practical Guidelines 2021",
        "edition": "2021",
        "publisher": "International Diabetes Federation & DAR International Alliance",
        "url": "https://www.idf.org/our-activities/education/diabetes-and-ramadan.html",
        "priority": 4,
    },
    {
        "filename": "pk_htn_women_2023.pdf",
        "source_id": "pk_htn_women_2023",
        "title": "Management of Hypertension in Women: Pakistan Hypertension Clinical Practice Guidelines",
        "edition": "2023",
        "publisher": "Pakistan Cardiac Society / Task Force Go Red for Women-Pakistan",
        "url": "http://www.pakheartjournal.com",
        "priority": 4,
    },
    {
        "filename": "aku_diabetes_pakistan_2023.pdf",
        "source_id": "aku_diabetes_pk_2023",
        "title": "Adolopment of Adult Diabetes Mellitus Management Guidelines for a Pakistani Context: Methodology and Challenges",
        "edition": "2023",
        "publisher": "Aga Khan University / Frontiers in Endocrinology",
        "url": "https://doi.org/10.3389/fendo.2022.1081361",
        "priority": 4,
    },
]


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def extract_licence_notice(pdf_path: Path) -> Tuple[str, bool, str]:
    """Inspect first 2 pages of PDF for copyright/license notice.

    Returns: (matched_sentence_max_40_words, is_tdm_prohibited, licence_type)
    """
    reader = pypdf.PdfReader(str(pdf_path))
    num_check = min(2, len(reader.pages))
    combined_text = ""
    for i in range(num_check):
        p_text = reader.pages[i].extract_text() or ""
        combined_text += " " + p_text

    combined_text = re.sub(r"\s+", " ", combined_text).strip()
    sentences = re.split(r"(?<=[.!?]) +", combined_text)

    # Search priorities
    tdm_keywords = ["mining", "machine learning"]
    cc_keywords = ["creative commons", "cc by", "attribution license"]
    general_keywords = ["license", "licence", "permission", "all rights reserved", "copyright", "©"]

    matched_sentence = ""
    is_tdm_prohibited = False
    licence_type = "CHECK"

    # 1. First priority: Check for explicit TDM / ML prohibition
    for s in sentences:
        s_low = s.lower()
        if any(k in s_low for k in tdm_keywords):
            is_tdm_prohibited = True
            licence_type = "TDM_PROHIBITED"
            words = s.split()
            matched_sentence = " ".join(words[:40])
            return matched_sentence, is_tdm_prohibited, licence_type

    # 2. Second priority: Creative Commons / open access
    for s in sentences:
        s_low = s.lower()
        if any(k in s_low for k in cc_keywords):
            licence_type = "CREATIVE_COMMONS"
            words = s.split()
            matched_sentence = " ".join(words[:40])
            return matched_sentence, is_tdm_prohibited, licence_type

    # 3. Third priority: Copyright / Permission notice
    for s in sentences:
        s_low = s.lower()
        if any(k in s_low for k in general_keywords):
            licence_type = "COPYRIGHT_NOTICE"
            words = s.split()
            matched_sentence = " ".join(words[:40])
            return matched_sentence, is_tdm_prohibited, licence_type

    return "No explicit copyright notice found on pages 1-2.", False, "CHECK"


def build_manifest() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    for spec in CORPUS_SPECS:
        filename = spec["filename"]
        source_id = spec["source_id"]
        pdf_path = GUIDELINES_DIR / filename

        if not pdf_path.exists():
            print(f"[MISSING] {filename} not found in {GUIDELINES_DIR}")
            records.append({
                **spec,
                "status": "NOT FOUND",
                "sha256": "N/A",
                "page_count": 0,
                "download_date": "N/A",
                "licence_text": "File missing",
                "allowed_for_rag": False,
                "reason": "File not found",
            })
            continue

        sha256_hash = compute_sha256(pdf_path)
        mtime = datetime.fromtimestamp(pdf_path.stat().st_mtime).strftime("%Y-%m-%d")

        reader = pypdf.PdfReader(str(pdf_path))
        page_count = len(reader.pages)

        licence_text, is_tdm_prohibited, lic_type = extract_licence_notice(pdf_path)

        # Granted override check
        permission_file = PERMISSIONS_DIR / f"{source_id}.granted"
        has_granted_file = permission_file.exists()

        # Evaluation of allowed_for_rag
        # ADA has explicit TDM/ML prohibition.
        # AHA is under copyright / pending written clearance per clinical protocol rules.
        if is_tdm_prohibited or source_id == "aha_acc_2025":
            if has_granted_file:
                allowed_for_rag = True
                status_desc = "ALLOWED (.granted file override)"
            else:
                allowed_for_rag = False
                status_desc = "BLOCKED: licence (ADA/AHA permission pending since 27 Oct 2026)"
        else:
            allowed_for_rag = True
            if lic_type == "CREATIVE_COMMONS":
                status_desc = "ALLOWED (Creative Commons / Open Access)"
            else:
                status_desc = "ALLOWED (CHECK: no TDM prohibition on pages 1-2)"

        records.append({
            **spec,
            "status": "PRESENT",
            "sha256": sha256_hash,
            "page_count": page_count,
            "download_date": mtime,
            "licence_text": licence_text,
            "licence_type": lic_type,
            "allowed_for_rag": allowed_for_rag,
            "status_desc": status_desc,
        })

    return records


def write_manifest_doc(records: List[Dict[str, Any]], output_path: Path):
    doc_lines = [
        "# Clinical Guideline Corpus Manifest",
        "",
        "> **Location Notice:** Guideline PDFs, raw extracted text, and chunks live exclusively outside Git under `$CHRONICCARE_DATA_DIR/guidelines` and `$CHRONICCARE_DATA_DIR/rag`.",
        "> **Licence Status Notice:** The American Diabetes Association (ADA) and American Heart Association / American College of Cardiology (AHA/ACC) guidelines carry text/data mining prohibitions or copyright restrictions. Permission was formally submitted on 27 Oct 2026 and is awaiting written clearance. Ingest skips all blocked sources until a `.granted` token is placed in `$CHRONICCARE_DATA_DIR/guidelines/permissions/<source_id>.granted`.",
        "",
        "## Corpus Inventory & Licence Status",
        "",
        "| Source ID | Title | Ed. | Priority | Pages | Allowed for RAG? | Status / Reason | Download Date | SHA-256 (first 12) | Terms of Use |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in records:
        allowed_str = "**TRUE**" if r["allowed_for_rag"] else "**FALSE**"
        sha_short = r["sha256"][:12] if r["sha256"] != "N/A" else "N/A"
        doc_lines.append(
            f"| `{r['source_id']}` | {r['title']} | {r['edition']} | {r['priority']} | {r['page_count']} | {allowed_str} | {r['status_desc']} | {r['download_date']} | `{sha_short}` | TO FILL BY USMAN |"
        )

    doc_lines.extend([
        "",
        "## Detailed Licence Snippets (First 2 Pages)",
        "",
    ])

    for r in records:
        doc_lines.append(f"### `{r['source_id']}` — {r['filename']}")
        doc_lines.append(f"- **Publisher:** {r['publisher']}")
        doc_lines.append(f"- **URL / DOI:** {r['url']}")
        doc_lines.append(f"- **Allowed for RAG:** {'Yes' if r['allowed_for_rag'] else 'No (BLOCKED)'}")
        doc_lines.append(f"- **Licence Notice:** *\"{r['licence_text']}\"*")
        doc_lines.append(f"- **Full SHA-256:** `{r['sha256']}`")
        doc_lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(doc_lines))

    print(f"Manifest successfully written to: {output_path}")


def main():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "manifest_output.txt"

    records = build_manifest()
    target_doc = Path(r"C:\Users\usmanbari\Desktop\Chronicare\docs\GUIDELINE_CORPUS.md")
    write_manifest_doc(records, target_doc)

    # Print summary table
    out_table = []
    out_table.append(f"{'Source ID':<22} | {'Priority':<8} | {'Pages':<5} | {'Allowed':<7} | {'Status'}")
    out_table.append("-" * 80)
    for r in records:
        out_table.append(
            f"{r['source_id']:<22} | {r['priority']:<8} | {r['page_count']:<5} | {str(r['allowed_for_rag']):<7} | {r['status_desc']}"
        )
    table_str = "\n".join(out_table)
    print(table_str)

    with open(log_file, "w", encoding="utf-8") as lf:
        lf.write(table_str + "\n\n")
        for r in records:
            lf.write(f"Source: {r['source_id']} ({r['filename']})\n")
            lf.write(f"  SHA256: {r['sha256']}\n")
            lf.write(f"  Pages: {r['page_count']}\n")
            lf.write(f"  Allowed: {r['allowed_for_rag']}\n")
            lf.write(f"  Licence: {r['licence_text']}\n\n")


if __name__ == "__main__":
    main()
