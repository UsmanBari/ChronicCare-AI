"""
Grounded Explanation Engine for ChronicCare AI RAG.
Explains triage levels already determined by deterministic clinical rules.
Cites guideline evidence, enforces strict validators (V1-V5), supports
English, Urdu, and Roman Urdu, and falls back to pre-verified templates.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable

from rag.query_map import build_query_from_triage
from rag.retriever import BM25Retriever, tokenize
from rag.store import ChunkStore, JsonlChunkStore

logger = logging.getLogger(__name__)

EXPLAINER_VERSION = "1.0.0"

# Banned clinical patterns across languages
BANNED_DIAGNOSIS_PATTERNS = [
    r"\byou have (?:type [12] )?diabetes\b",
    r"\byou have (?:essential )?hypertension\b",
    r"\byou are diagnosed with\b",
    r"\bwe diagnose you\b",
    r"\baap ko (?:sugar|diabetes) (?:ki bimari )?hai\b",
    r"\baap ko blood pressure (?:ki bimari )?hai\b",
    r"آپ کو (?:شوگر|ذیابیطس) ہے",
    r"آپ کو ہائی بلڈ پریشر ہے",
]

BANNED_DOSING_PATTERNS = [
    # Medicine name followed by dose
    r"\b(?:metformin|insulin|amlodipine|lisinopril|losartan|glimepiride|gliclazide|empagliflozin|sitagliptin|atenolol|hydrochlorothiazide)\s+\d+\s*(?:mg|mcg|ml|units?|tablets?)\b",
    # Directive to alter dosage
    r"\b(?:start|stop|increase|decrease|double|halve|skip|change)\s+(?:your\s+)?(?:dose|medication|medicine|tablets?|insulin|pills?)\b",
    r"\b(?:dawa|tablet|goli)\s+(?:shuru|band|kam|zyada)\b",
    r"(?:دوا|گولی)\s*(?:شروع|بند|کم|زیادہ)",
]

BANNED_REASSURANCE_PATTERNS = [
    r"\bnothing to worry\b",
    r"\byou are (?:completely )?fine\b",
    r"\ball is well\b",
    r"\bdon't worry\b",
    r"\bno need to see (?:a )?doctor\b",
    r"\bko(?:i|y) masla nahi\b",
    r"\bpareshan na ho(?:n)?\b",
    r"\bfikr na karein\b",
    r"\bsab theek hai\b",
    r"کوئی مسئلہ نہیں",
    r"پریشان نہ ہوں",
    r"سب ٹھیک ہے",
    r"فکر نہ کریں",
]


def load_templates() -> dict[str, Any]:
    """Load safe fallback templates from templates.json."""
    tmpl_path = Path(__file__).parent / "templates.json"
    if not tmpl_path.exists():
        raise FileNotFoundError(f"Templates file missing: {tmpl_path}")
    with open(tmpl_path, "r", encoding="utf-8") as f:
        return json.load(f)


TEMPLATES = load_templates()


def extract_numbers(text: str) -> set[str]:
    """Extract normalized numbers (integers and decimals) from text."""
    # Find all numeric matches
    raw_nums = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    # Normalize: strip trailing .0 for clean comparison
    clean_nums = set()
    for n in raw_nums:
        try:
            val = float(n)
            if val.is_integer():
                clean_nums.add(str(int(val)))
            else:
                clean_nums.add(str(val))
        except ValueError:
            clean_nums.add(n)
    return clean_nums


def get_allowed_numbers(
    readings: dict[str, Any],
    triage_result: dict[str, Any],
    cited_chunks: list[dict[str, Any]],
) -> set[str]:
    """Collect all allowed numbers from readings, triage thresholds, and cited text."""
    allowed = set()

    # 1. Readings
    for k, v in readings.items():
        if isinstance(v, (int, float)):
            if float(v).is_integer():
                allowed.add(str(int(v)))
            else:
                allowed.add(str(v))
        elif isinstance(v, str):
            allowed.update(extract_numbers(v))

    # 2. Triage result metadata & reasons
    for k, v in triage_result.items():
        if isinstance(v, (int, float)):
            allowed.add(str(int(v)) if float(v).is_integer() else str(v))
        elif isinstance(v, str):
            allowed.update(extract_numbers(v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    allowed.update(extract_numbers(item))

    # 3. Known standard clinical triage thresholds
    standard_thresholds = [
        "180", "120", "140", "90", "70", "54", "250", "300", "400", "60", "20", "5", "15", "1", "2"
    ]
    allowed.update(standard_thresholds)

    # 4. Cited chunk text and section headers
    for chunk in cited_chunks:
        allowed.update(extract_numbers(chunk.get("text", "")))
        allowed.update(extract_numbers(chunk.get("section_path", "")))

    return allowed


def validate_sentence_structure(data: Any) -> list[str]:
    """V1: Check valid JSON, 2-3 sentences, <= 35 words each."""
    errors = []
    if not isinstance(data, dict):
        return ["V1: Output is not a JSON object"]

    sentences = data.get("sentences")
    if not isinstance(sentences, list):
        return ["V1: 'sentences' field is missing or not a list"]

    if len(sentences) < 2 or len(sentences) > 3:
        errors.append(f"V1: Expected 2 to 3 sentences, got {len(sentences)}")

    for idx, s_obj in enumerate(sentences, start=1):
        if not isinstance(s_obj, dict):
            errors.append(f"V1: Sentence {idx} is not an object")
            continue
        text = str(s_obj.get("text", "")).strip()
        if not text:
            errors.append(f"V1: Sentence {idx} is empty")
            continue
        words = text.split()
        if len(words) > 35:
            errors.append(f"V1: Sentence {idx} exceeds 35 words ({len(words)} words)")

    return errors


def validate_citations(
    sentences: list[dict[str, Any]],
    candidate_chunks: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    V2: Every sentence cites >= 1 retrieved passage.
    Maps citation labels [S1], [S2] or direct chunk_ids to real chunk_ids.
    """
    errors = []
    chunk_id_map: dict[str, str] = {}
    valid_cids = {c["chunk_id"] for c in candidate_chunks}

    # Map S1, S2 ...
    for idx, c in enumerate(candidate_chunks, start=1):
        chunk_id_map[f"S{idx}"] = c["chunk_id"]
        chunk_id_map[f"s{idx}"] = c["chunk_id"]
        chunk_id_map[f"[S{idx}]"] = c["chunk_id"]
        chunk_id_map[f"[s{idx}]"] = c["chunk_id"]
        chunk_id_map[c["chunk_id"]] = c["chunk_id"]

    resolved_sentences = []
    for s_idx, s_obj in enumerate(sentences, start=1):
        raw_cites = s_obj.get("cites", [])
        text = str(s_obj.get("text", ""))

        # Also search for embedded [S1], [S2] in text if cites list is empty
        if not raw_cites:
            found_tags = re.findall(r"\[S\d+\]", text, re.IGNORECASE)
            raw_cites = [tag.strip("[]") for tag in found_tags]

        if not raw_cites:
            errors.append(f"V2: Sentence {s_idx} contains no citations")
            continue

        resolved_cites = []
        for c in raw_cites:
            clean_c = str(c).strip()
            if clean_c in chunk_id_map:
                resolved_cites.append(chunk_id_map[clean_c])
            elif clean_c in valid_cids:
                resolved_cites.append(clean_c)

        if not resolved_cites:
            errors.append(f"V2: Sentence {s_idx} cites unretrieved sources ({raw_cites})")
            continue

        resolved_sentences.append({
            "text": text,
            "cites": list(dict.fromkeys(resolved_cites)),  # Deduplicate
        })

    return errors, resolved_sentences


def validate_number_grounding(
    sentences: list[dict[str, Any]],
    allowed_numbers: set[str],
) -> list[str]:
    """V3: Every number in text must exist in readings, triage result, or cited text."""
    errors = []
    for idx, s_obj in enumerate(sentences, start=1):
        text = s_obj.get("text", "")
        # Remove citation markers like [S1] before checking numbers
        clean_text = re.sub(r"\[S\d+\]", "", text, flags=re.IGNORECASE)
        found_nums = extract_numbers(clean_text)
        disallowed = [n for n in found_nums if n not in allowed_numbers]
        if disallowed:
            errors.append(f"V3: Sentence {idx} contains hallucinated/unverified numbers: {disallowed}")
    return errors


def validate_banned_patterns(
    sentences: list[dict[str, Any]],
    level: str,
) -> list[str]:
    """V4: Check for banned diagnosis, dosing, and false reassurance patterns."""
    errors = []
    lvl = level.lower().strip()

    for idx, s_obj in enumerate(sentences, start=1):
        text = s_obj.get("text", "")

        # 1. Banned diagnosis
        for pat in BANNED_DIAGNOSIS_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                errors.append(f"V4: Sentence {idx} contains forbidden diagnostic phrasing: '{pat}'")

        # 2. Banned dosing
        for pat in BANNED_DOSING_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                errors.append(f"V4: Sentence {idx} contains forbidden dosing/prescribing phrasing: '{pat}'")

        # 3. False reassurance when level >= review
        if lvl in ("review", "urgent", "emergency"):
            for pat in BANNED_REASSURANCE_PATTERNS:
                if re.search(pat, text, re.IGNORECASE):
                    errors.append(f"V4: Sentence {idx} contains forbidden reassurance for level '{lvl}': '{pat}'")

    return errors


def validate_level_consistency(
    sentences: list[dict[str, Any]],
    level: str,
) -> list[str]:
    """V5: If any level word is mentioned in text, it must match the decided level."""
    errors = []
    lvl = level.lower().strip()
    all_levels = {"emergency", "urgent", "review", "routine"}

    for idx, s_obj in enumerate(sentences, start=1):
        text = s_obj.get("text", "").lower()
        for cand in all_levels:
            if re.search(rf"\b{cand}\b", text):
                if cand != lvl:
                    errors.append(f"V5: Sentence {idx} mentions level '{cand}' conflicting with decided level '{lvl}'")
    return errors


def get_template_explanation(
    trigger_category: str,
    readings: dict[str, Any],
    triage_result: dict[str, Any],
    language: str,
    candidate_chunks: list[dict[str, Any]],
    rejected_reasons: list[str],
) -> dict[str, Any]:
    """Construct safe fallback explanation from pre-verified templates."""
    lang = language if language in ("en", "ur", "roman_ur") else "en"
    cat = trigger_category if trigger_category in TEMPLATES else "routine"

    template_entry = TEMPLATES[cat].get(lang, TEMPLATES[cat]["en"])
    raw_sentences = template_entry.get("sentences", [])

    # Format placeholders
    sbp_val = readings.get("blood_pressure_systolic", triage_result.get("systolic", "---"))
    dbp_val = readings.get("blood_pressure_diastolic", triage_result.get("diastolic", "---"))
    gluc_val = readings.get("glucose", triage_result.get("glucose", "---"))
    lvl_val = triage_result.get("level", "routine")

    top_chunk_id = candidate_chunks[0]["chunk_id"] if candidate_chunks else "ish_2020_htn_c01"

    formatted_sentences = []
    for s in raw_sentences:
        formatted_text = s.format(
            systolic=sbp_val,
            diastolic=dbp_val,
            glucose=gluc_val,
            level=lvl_val,
        )
        formatted_sentences.append({
            "text": formatted_text,
            "cites": [top_chunk_id],
        })

    # Sources metadata
    sources = []
    for c in candidate_chunks[:3]:
        sources.append({
            "chunk_id": c["chunk_id"],
            "title": c.get("title", ""),
            "edition": c.get("edition", ""),
            "section_path": c.get("section_path", ""),
            "page_start": c.get("page_start", 1),
        })

    return {
        "sentences": formatted_sentences,
        "sources": sources,
        "language": lang,
        "mode": "template",
        "rejected_reasons": rejected_reasons,
        "version": EXPLAINER_VERSION,
    }


def explain(
    triage_result: dict[str, Any],
    readings: dict[str, Any],
    language: str = "en",
    store: ChunkStore | None = None,
    llm: Any = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Generate a grounded clinical explanation for an already decided triage level.
    Guarantees input immutability, full citation grounding, and safety validator checks.
    """
    # C2: Take deep copies of inputs; guarantee inputs remain byte-identical
    triage_copy = copy.deepcopy(triage_result)
    readings_copy = copy.deepcopy(readings)

    target_lang = language if language in ("en", "ur", "roman_ur") else "en"
    decided_level = str(triage_copy.get("level", "routine")).lower().strip()

    # Determine query mapping
    query_mapping = build_query_from_triage(triage_copy, readings_copy)

    # Chunk retrieval
    candidate_chunks: list[dict[str, Any]] = []
    if store is not None:
        retriever = BM25Retriever(store)
        candidate_chunks = retriever.retrieve(
            query=query_mapping.query_text,
            top_k=3,
            condition=query_mapping.condition,
            min_priority=query_mapping.min_priority,
        )
        if len(candidate_chunks) < 2:
            # Fallback without condition filter
            candidate_chunks = retriever.retrieve(
                query=query_mapping.query_text,
                top_k=3,
                min_priority=query_mapping.min_priority,
            )

    rejected_reasons: list[str] = []

    # If LLM is not provided or not configured, return safe template
    if llm is None:
        rejected_reasons.append("No LLM client configured")
        return get_template_explanation(
            query_mapping.trigger_category,
            readings_copy,
            triage_copy,
            target_lang,
            candidate_chunks,
            rejected_reasons,
        )

    # Prepare prompt for LLM
    passages_text = "\n\n".join([
        f"[S{i}] Guideline: {c.get('title', '')} ({c.get('section_path', '')})\nPassage: {c.get('text', '')}"
        for i, c in enumerate(candidate_chunks, start=1)
    ])

    system_prompt = (
        "You are an explainer for ChronicCare AI, a clinical decision-support system for adults with type 2 diabetes and hypertension.\n"
        f"A deterministic clinical rule engine has ALREADY decided the triage level: '{decided_level}'.\n"
        "Your task is to explain this decided level to the patient using ONLY the provided guideline passages.\n"
        "STRICT RULES:\n"
        "1. Write exactly 2 to 3 sentences. Each sentence must be at most 35 words.\n"
        "2. Plain words for a patient; calm, clear, and reassuring without downplaying danger.\n"
        "3. Every sentence must end with citation markers like [S1] or [S2] referencing the provided passages.\n"
        "4. DO NOT introduce any new numbers not present in the patient's readings or guideline text.\n"
        "5. DO NOT mention specific drug dosages (e.g., no 'metformin 500 mg').\n"
        "6. DO NOT tell the patient to start, stop, increase, decrease, or change their medicines.\n"
        "7. DO NOT diagnose any disease (e.g., never say 'you have diabetes').\n"
        "8. NEVER say 'nothing to worry', 'you are fine', or 'no need to see a doctor' if the level is review, urgent, or emergency.\n"
        "9. Output valid JSON only with structure:\n"
        '{"sentences": [{"text": "sentence text with citation [S1].", "cites": ["S1"]}]}'
    )

    user_prompt = (
        f"Patient Readings: {json.dumps(readings_copy)}\n"
        f"Triage Result: Level = '{decided_level}', Trigger = '{query_mapping.trigger_category}'\n\n"
        f"Guideline Passages:\n{passages_text}\n\n"
        "Generate the explanation in English."
    )

    try:
        # LLM Generation (English first, temperature 0, timeout 8s)
        call_kwargs = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 400,
            "timeout": 8.0,
        }
        if model:
            call_kwargs["model"] = model

        # Check if llm is callable function or object
        if callable(llm):
            raw_response = llm(**call_kwargs)
        elif hasattr(llm, "chat"):
            raw_response = llm.chat(**call_kwargs)
        else:
            raise TypeError("Provided LLM instance is neither callable nor possesses a chat method")

        # Parse JSON
        clean_json_str = raw_response.strip()
        if clean_json_str.startswith("```"):
            clean_json_str = re.sub(r"^```(?:json)?\s*", "", clean_json_str)
            clean_json_str = re.sub(r"\s*```$", "", clean_json_str)

        parsed_data = json.loads(clean_json_str)

        # Run Validators V1-V5
        v1_errs = validate_sentence_structure(parsed_data)
        if v1_errs:
            rejected_reasons.extend(v1_errs)

        raw_sentences = parsed_data.get("sentences", [])
        v2_errs, resolved_sentences = validate_citations(raw_sentences, candidate_chunks)
        if v2_errs:
            rejected_reasons.extend(v2_errs)

        allowed_nums = get_allowed_numbers(readings_copy, triage_copy, candidate_chunks)
        v3_errs = validate_number_grounding(resolved_sentences, allowed_nums)
        if v3_errs:
            rejected_reasons.extend(v3_errs)

        v4_errs = validate_banned_patterns(resolved_sentences, decided_level)
        if v4_errs:
            rejected_reasons.extend(v4_errs)

        v5_errs = validate_level_consistency(resolved_sentences, decided_level)
        if v5_errs:
            rejected_reasons.extend(v5_errs)

        if rejected_reasons:
            logger.warning(f"LLM explanation rejected: {rejected_reasons}")
            return get_template_explanation(
                query_mapping.trigger_category,
                readings_copy,
                triage_copy,
                target_lang,
                candidate_chunks,
                rejected_reasons,
            )

        # C5: If target language is Urdu or Roman Urdu, translate validated English
        final_sentences = resolved_sentences
        if target_lang in ("ur", "roman_ur"):
            trans_prompt = (
                f"Translate the following validated medical sentences into {'Urdu (Nastaliq)' if target_lang == 'ur' else 'Roman Urdu (Urdu in Latin script)'}.\n"
                "RULES:\n"
                "1. Keep all numbers, units (mmHg, mg/dL), and citations [S1] EXACTLY intact.\n"
                "2. Maintain identical sentence count.\n"
                '3. Output valid JSON: {"sentences": [{"text": "...", "cites": ["..."]}]}\n\n'
                f"Source English sentences:\n{json.dumps(resolved_sentences, ensure_ascii=False)}"
            )
            trans_call_kwargs = dict(call_kwargs)
            trans_call_kwargs["messages"] = [
                {"role": "system", "content": "You are a professional medical translator for ChronicCare AI."},
                {"role": "user", "content": trans_prompt},
            ]
            if callable(llm):
                trans_raw = llm(**trans_call_kwargs)
            else:
                trans_raw = llm.chat(**trans_call_kwargs)

            clean_trans_str = trans_raw.strip()
            if clean_trans_str.startswith("```"):
                clean_trans_str = re.sub(r"^```(?:json)?\s*", "", clean_trans_str)
                clean_trans_str = re.sub(r"\s*```$", "", clean_trans_str)

            trans_data = json.loads(clean_trans_str)
            trans_v1 = validate_sentence_structure(trans_data)
            trans_v2, trans_resolved = validate_citations(trans_data.get("sentences", []), candidate_chunks)
            trans_v3 = validate_number_grounding(trans_resolved, allowed_nums)
            trans_v4 = validate_banned_patterns(trans_resolved, decided_level)

            if trans_v1 or trans_v2 or trans_v3 or trans_v4:
                rejected_reasons.extend(trans_v1 + trans_v2 + trans_v3 + trans_v4)
                return get_template_explanation(
                    query_mapping.trigger_category,
                    readings_copy,
                    triage_copy,
                    target_lang,
                    candidate_chunks,
                    rejected_reasons,
                )
            final_sentences = trans_resolved

        # Sources metadata list
        sources = []
        for c in candidate_chunks:
            sources.append({
                "chunk_id": c["chunk_id"],
                "title": c.get("title", ""),
                "edition": c.get("edition", ""),
                "section_path": c.get("section_path", ""),
                "page_start": c.get("page_start", 1),
            })

        return {
            "sentences": final_sentences,
            "sources": sources,
            "language": target_lang,
            "mode": "llm",
            "rejected_reasons": [],
            "version": EXPLAINER_VERSION,
        }

    except Exception as exc:
        logger.warning(f"Error generating LLM explanation: {type(exc).__name__}: {exc}")
        rejected_reasons.append(f"LLM execution error: {type(exc).__name__}")
        return get_template_explanation(
            query_mapping.trigger_category,
            readings_copy,
            triage_copy,
            target_lang,
            candidate_chunks,
            rejected_reasons,
        )
