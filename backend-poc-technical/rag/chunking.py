"""Clinical Guideline Chunking and Text Cleaning Module.

Pure Python standard library implementation for cleaning, segmenting,
and chunking clinical guideline documents into cited chunks for RAG search.
"""

from collections import Counter
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple


def clean_page_text(pages: List[str]) -> List[str]:
    """Clean extracted page texts.

    - Removes running headers/footers appearing on > 50% of pages.
    - Removes isolated page numbers and journal pagination banners.
    - Joins hyphenated words broken across line endings.
    - Drops reference sections (from 'References' to end of section).
    """
    if not pages:
        return []

    num_pages = len(pages)
    threshold = num_pages / 2.0

    # Count line occurrences across pages (stripped of surrounding whitespace)
    page_line_sets = []
    line_page_counts: Counter[str] = Counter()

    for page in pages:
        seen_in_page = set()
        for raw_line in page.splitlines():
            line_str = raw_line.strip()
            # Ignore very short lines for header/footer counting to avoid dropping bullet points or whitespace
            if len(line_str) >= 5 and line_str not in seen_in_page:
                seen_in_page.add(line_str)
                line_page_counts[line_str] += 1
        page_line_sets.append(seen_in_page)

    repeated_headers = set()
    if num_pages >= 2:
        repeated_headers = {
            line for line, count in line_page_counts.items() if count >= 2 and count > threshold
        }

    cleaned_pages: List[str] = []

    # Page number patterns: "12", "Page 12", "S132", "e212", "12 of 105"
    page_num_re = re.compile(
        r"^(?:(?:page\s+)?(?:[se]?\d{1,4}|\d{1,4}\s*(?:/|of)\s*\d{1,4})|s\d{2,4}\s*–\s*s\d{2,4})$",
        re.IGNORECASE,
    )

    for page in pages:
        lines = page.splitlines()
        kept_lines: List[str] = []
        in_references = False

        for line in lines:
            stripped = line.strip()

            # Check if entering reference section
            if re.match(r"^(?:references|bibliography|works cited)\b", stripped, re.IGNORECASE):
                in_references = True
                continue

            if in_references:
                continue

            # Drop running headers/footers repeated on > 50% pages
            if stripped in repeated_headers:
                continue

            # Drop page numbers
            if page_num_re.match(stripped):
                continue

            # Drop Table of Contents lines with dot leaders (e.g. "Section 1. .... 1334")
            if re.search(r"\.{4,}\s*\d+", stripped):
                continue

            kept_lines.append(line)

        page_text = "\n".join(kept_lines)

        # Join hyphenated words split across line breaks: "inter-\nvention" -> "intervention"
        # Match a word char, hyphen, newline, and word char
        page_text = re.sub(r"(\b[A-Za-z]+)-\n\s*([A-Za-z]+\b)", r"\1\2", page_text)

        cleaned_pages.append(page_text.strip())

    return cleaned_pages


def _detect_grade(text: str) -> Optional[str]:
    """Detect recommendation grade from ADA or AHA/ACC text."""
    # AHA style: COR 1, LOE A or Class I, Level A
    aha_match = re.search(
        r"(?:COR\s*[:\s]*([123a-c]+)[,\s]+LOE\s*[:\s]*([A-E](?:-[A-Za-z]+)?)|"
        r"Class\s*[:\s]*([I|V|X]+|1|2a|2b|3)[,\s]+Level\s*(?:of\s+Evidence)?\s*[:\s]*([A-E](?:-[A-Za-z]+)?))",
        text,
        re.IGNORECASE,
    )
    if aha_match:
        groups = [g for g in aha_match.groups() if g]
        if len(groups) >= 2:
            return f"COR {groups[0].upper()}, LOE {groups[1].upper()}"

    # ADA style: Recommendation 6.5 ... A or [Grade A] or (A) at sentence end
    ada_match = re.search(
        r"(?:(?:Recommendation\s+\d+(\.\d+)*.*?|\bGrade\s+)([A-E])\b|\b([A-E])\s*(?:\.|\))\s*$)",
        text.strip(),
        re.MULTILINE,
    )
    if ada_match:
        for g in reversed(ada_match.groups()):
            if g and len(g) == 1 and g.upper() in "ABCDE":
                return g.upper()

    return None


def split_sections(pages: List[str]) -> List[Dict[str, Any]]:
    """Split cleaned pages into hierarchical sections and recommendation boxes.

    Returns a list of dicts:
      {
        'section_path': str,
        'heading': str,
        'text': str,
        'page_start': int,
        'page_end': int,
        'is_recommendation': bool,
        'grade': Optional[str]
      }
    """
    sections: List[Dict[str, Any]] = []
    current_path: List[str] = ["Document"]
    current_heading: str = "Overview"
    current_lines: List[str] = []
    section_page_start: int = 1
    current_page: int = 1

    # Heading detection patterns
    sec_num_re = re.compile(
        r"^(?:Section\s+)?(\d+(?:\.\d+)*)\.?\s+([A-Z0-9][A-Za-z0-9\s,\-–:;/()]{3,80})$"
    )
    all_caps_re = re.compile(r"^[A-Z0-9\s,\-–:;/()]{6,80}$")
    rec_box_start = re.compile(r"^(?:Recommendations?|RECOMMENDATIONS?)\b", re.IGNORECASE)

    def flush_section(end_page: int):
        nonlocal current_lines, section_page_start, current_heading, current_path
        text = "\n".join(current_lines).strip()
        if text:
            # Check if this entire block is a recommendation block or contains one
            is_rec = bool(
                rec_box_start.search(current_heading)
                or re.search(r"\bRecommendation\s+\d", text, re.IGNORECASE)
                or _detect_grade(text)
            )
            grade = _detect_grade(text)
            sections.append(
                {
                    "section_path": " > ".join(current_path),
                    "heading": current_heading,
                    "text": text,
                    "page_start": section_page_start,
                    "page_end": max(section_page_start, end_page),
                    "is_recommendation": is_rec,
                    "grade": grade,
                }
            )
        current_lines = []

    for page_idx, page_text in enumerate(pages):
        current_page = page_idx + 1
        lines = page_text.splitlines()

        for line in lines:
            stripped = line.strip()
            if not stripped:
                current_lines.append("")
                continue

            # Heading candidate checks
            m_num = sec_num_re.match(stripped)
            m_rec = rec_box_start.match(stripped)
            words_in_line = stripped.split()
            is_all_caps = (
                all_caps_re.match(stripped)
                and 2 <= len(words_in_line) <= 8
                and not stripped.endswith(".")
                and not re.match(r"^(?:TABLE|FIGURE|BOX|AUTHORS?)\b", stripped, re.IGNORECASE)
            )

            if m_num or m_rec or is_all_caps:
                flush_section(current_page)
                section_page_start = current_page

                if m_num:
                    num_str, title_str = m_num.group(1), m_num.group(2).strip()
                    depth = len(num_str.split("."))
                    new_item = f"{num_str} {title_str}"
                    # Keep hierarchy depth aligned
                    if depth == 1:
                        current_path = [new_item]
                    elif depth == 2:
                        current_path = current_path[:1] + [new_item]
                    else:
                        current_path = current_path[:2] + [new_item]
                    current_heading = new_item
                elif m_rec:
                    current_heading = stripped
                    current_path = current_path[:1] + [stripped]
                elif is_all_caps:
                    current_heading = stripped
                    current_path = [stripped]
            else:
                current_lines.append(line)

    flush_section(current_page)
    return sections


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences while keeping table rows intact."""
    lines = text.splitlines()
    sentences: List[str] = []
    buf: List[str] = []

    def flush_buf():
        if buf:
            joined = " ".join(buf).strip()
            # Split sentences on .!? followed by space or end
            raw_sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", joined)
            for s in raw_sents:
                s_strip = s.strip()
                if s_strip:
                    sentences.append(s_strip)
            buf.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Check if table row (starts with | or has markdown table separators)
        if stripped.startswith("|") or stripped.startswith("+--") or "\t" in stripped:
            flush_buf()
            sentences.append(stripped)
        else:
            buf.append(stripped)

    flush_buf()
    return sentences


def chunk_section(
    section: Dict[str, Any],
    min_words: int = 200,
    max_words: int = 400,
    overlap_words: int = 40,
) -> List[Dict[str, Any]]:
    """Chunk a single section into windows of 200-400 words with 40-word overlap.

    - Never crosses section boundaries.
    - Never splits sentences or table rows.
    - Recommendations with grades are kept as distinct chunks.
    """
    text = section["text"]
    is_rec = section.get("is_recommendation", False)
    grade = section.get("grade")
    sentences = _split_into_sentences(text)

    if not sentences:
        return []

    # If section is small, keep as single chunk
    total_words = len(text.split())
    if total_words <= max_words:
        if total_words < 15 and not is_rec:
            return []
        return [
            {
                "section_path": section["section_path"],
                "text": text,
                "page_start": section["page_start"],
                "page_end": section["page_end"],
                "grade": grade,
                "is_recommendation": is_rec,
                "word_count": total_words,
            }
        ]

    chunks: List[Dict[str, Any]] = []
    current_sentences: List[str] = []
    current_count = 0

    sent_word_counts = [len(s.split()) for s in sentences]
    total_remaining = sum(sent_word_counts)

    for idx, sent in enumerate(sentences):
        sent_words = sent_word_counts[idx]
        total_remaining -= sent_words

        # If adding this sentence exceeds max_words and we have met min_words,
        # but only cut if the remaining words can form a viable chunk (>= min_words // 2)
        if (
            current_count + sent_words > max_words
            and current_count >= min_words
            and total_remaining >= (min_words // 2)
        ):
            chunk_text = "\n".join(current_sentences).strip()
            chunks.append(
                {
                    "section_path": section["section_path"],
                    "text": chunk_text,
                    "page_start": section["page_start"],
                    "page_end": section["page_end"],
                    "grade": grade,
                    "is_recommendation": is_rec,
                    "word_count": current_count,
                }
            )

            # Build overlap from the tail of current_sentences
            overlap_sentences: List[str] = []
            overlap_count = 0
            for s in reversed(current_sentences):
                c = len(s.split())
                if overlap_count + c <= overlap_words or not overlap_sentences:
                    overlap_sentences.insert(0, s)
                    overlap_count += c
                else:
                    break

            current_sentences = list(overlap_sentences)
            current_count = overlap_count

        current_sentences.append(sent)
        current_count += sent_words

    if current_sentences:
        chunk_text = "\n".join(current_sentences).strip()
        chunks.append(
            {
                "section_path": section["section_path"],
                "text": chunk_text,
                "page_start": section["page_start"],
                "page_end": section["page_end"],
                "grade": grade,
                "is_recommendation": is_rec,
                "word_count": current_count,
            }
        )

    return chunks


def tag_condition(text: str, source_id: str = "") -> str:
    """Tag condition: 'diabetes', 'hypertension', or 'both'."""
    lower_text = text.lower()
    lower_src = source_id.lower()

    dm_score = (
        lower_text.count("diabetes") * 2
        + lower_text.count("glucose") * 2
        + lower_text.count("insulin") * 2
        + lower_text.count("a1c") * 2
        + lower_text.count("hypoglycemia") * 2
    )
    htn_score = (
        lower_text.count("hypertension") * 2
        + lower_text.count("blood pressure") * 2
        + lower_text.count("systolic") * 2
        + lower_text.count("diastolic") * 2
        + lower_text.count("antihypertensive") * 2
    )

    if "hbp" in lower_src or "htn" in lower_src:
        htn_score += 10
    if "diabetes" in lower_src or "ada" in lower_src or "idf" in lower_src:
        dm_score += 10

    if dm_score > 0 and htn_score > 0 and (min(dm_score, htn_score) / max(dm_score, htn_score) >= 0.3):
        return "both"
    elif htn_score > dm_score:
        return "hypertension"
    else:
        return "diabetes"


def tag_topics(text: str) -> List[str]:
    """Tag clinical topic slugs based on keyword rules."""
    lower = text.lower()
    topics: List[str] = []

    topic_rules = [
        ("hypoglycemia", [r"\bhypo(?:glycemia)?\b", r"\b<70\b", r"\b<54\b", r"shaky", r"sweat", r"rule of 15"]),
        ("glucose_targets", [r"\ba1c\b", r"glycemic goal", r"glycemic target", r"time in range", r"fasting glucose", r"postprandial"]),
        ("bp_targets", [r"bp target", r"blood pressure target", r"blood pressure goal", r"<130/80", r"<140/90", r"threshold"]),
        ("bp_measurement", [r"blood pressure measurement", r"home blood pressure", r"cuff", r"auscultat", r"oscillometr", r"5 minutes rest", r"seated quietly"]),
        ("emergency_signs", [r"hypertensive emergency", r"hypertensive crisis", r"dka\b", r"ketoacidosis", r"target.organ damage", r"chest pain", r"stroke"]),
        ("ramadan_fasting", [r"ramadan", r"\bfast(?:ing)?\b", r"suhoor", r"iftar", r"break(?:ing)? the fast"]),
        ("sick_day", [r"sick.day", r"sick day", r"intercurrent illness", r"vomiting", r"dehydration", r"ketone"]),
        ("older_adults", [r"older adult", r"elderly", r"frailty", r"cognitive impairment", r"dementia", r"geriatric", r"falls?"]),
        ("ckd", [r"chronic kidney", r"\bckd\b", r"egfr", r"albuminuria", r"uacr", r"creatinine"]),
        ("lifestyle", [r"lifestyle", r"dietary", r"physical activity", r"sodium", r"weight loss", r"exercise", r"nutrition"]),
        ("diagnosis_thresholds", [r"diagnosis", r"fasting plasma glucose\s*(?:>=|≥)\s*126", r"a1c\s*(?:>=|≥)\s*6\.5", r"stage 1 hypertension", r"stage 2 hypertension"]),
    ]

    for slug, patterns in topic_rules:
        for p in patterns:
            if re.search(p, lower):
                topics.append(slug)
                break

    return topics


def build_chunk_record(
    chunk_dict: Dict[str, Any],
    source_id: str,
    title: str,
    edition: str,
    priority: int,
) -> Dict[str, Any]:
    """Construct full metadata record for a chunk."""
    text = chunk_dict["text"]
    section_path = chunk_dict["section_path"]
    first_50 = text[:50].strip().replace("\n", " ")

    # Deterministic sha1: source_id + section + first 50 chars
    raw_key = f"{source_id}:{section_path}:{first_50}"
    chunk_id = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()

    condition = tag_condition(text, source_id)
    topics = tag_topics(text)

    return {
        "chunk_id": chunk_id,
        "source_id": source_id,
        "title": title,
        "edition": edition,
        "priority": priority,
        "section_path": section_path,
        "page_start": chunk_dict["page_start"],
        "page_end": chunk_dict["page_end"],
        "grade": chunk_dict.get("grade"),
        "condition": condition,
        "topics": topics,
        "text": text,
        "word_count": len(text.split()),
    }
