#!/usr/bin/env python3
"""
Guideline Chunks DB Loader.
Loads guideline chunks from an external JSONL file into the database `guideline_chunks` table.

Safety & Security:
- Refuses to load any file inside the repository tree.
- Uses project database configuration via `data_sources.app_store`.
- Prints chunk counts only. Never prints credentials, database URLs, or guideline text.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from data_sources.app_store import get_db_cursor, _utc_now_iso
    from rag.licences import get_licence_spec, is_source_allowed_for_rag, is_source_expired
except ImportError as e:
    print(f"Error importing dependencies: {e}", file=sys.stderr)
    sys.exit(1)


def is_path_inside_repo(path: Path) -> bool:
    """Checks whether the specified path is inside the git repository."""
    try:
        resolved_path = path.resolve()
        resolved_repo = REPO_ROOT.resolve()
        return resolved_path.is_relative_to(resolved_repo)
    except Exception:
        # Fallback string comparison
        return str(path.resolve()).startswith(str(REPO_ROOT.resolve()))


def load_chunks(
    jsonl_path: Path | str,
    backend: str | None = None,
    db_path: str | None = None,
    mysql_url: str | None = None,
    ssl_ca: str | None = None,
) -> tuple[int, int]:
    """
    Reads chunks from the external JSONL file and upserts them into `guideline_chunks`.
    Returns (inserted_count, updated_count).
    """
    file_path = Path(jsonl_path).resolve()

    # Guard: refuse path inside repository
    if is_path_inside_repo(file_path):
        raise ValueError(f"Refusing to load guideline chunks from inside repository: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"Guideline chunks JSONL file not found: {file_path}")

    now = _utc_now_iso()
    inserted_count = 0
    updated_count = 0
    source_status_cache: dict[str, tuple[bool, str]] = {}
    skipped_counts: dict[str, int] = {}

    with open(file_path, "r", encoding="utf-8") as f:
        with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
            for line_no, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    record = json.loads(raw)
                except Exception as exc:
                    print(f"Skipping malformed JSON at line {line_no}: {exc}", file=sys.stderr)
                    continue

                chunk_id = str(record.get("chunk_id", "")).strip()
                if not chunk_id:
                    continue

                source_id = str(record.get("source_id", "")).strip()

                # X1: Licence and permission token check
                if source_id not in source_status_cache:
                    spec = get_licence_spec(source_id)
                    if spec is not None:
                        is_licensed = source_id.startswith("ada_") or source_id.startswith("aha_")
                        token_ok = True
                        if is_licensed:
                            data_dir_env = os.environ.get("CHRONICCARE_DATA_DIR", "")
                            token_file = Path(data_dir_env) / "guidelines" / "permissions" / f"{source_id}.granted" if data_dir_env else None
                            token_ok = bool(token_file and token_file.exists())

                        if is_licensed and not token_ok:
                            source_status_cache[source_id] = (False, "missing .granted token")
                            print(f"SKIPPED {source_id}: missing .granted token")
                        elif not is_source_allowed_for_rag(source_id):
                            source_status_cache[source_id] = (False, "licence not allowed for RAG")
                            print(f"SKIPPED {source_id}: licence not allowed for RAG")
                        elif is_source_expired(source_id):
                            source_status_cache[source_id] = (False, "licence expired")
                            print(f"SKIPPED {source_id}: licence expired")
                        else:
                            source_status_cache[source_id] = (True, "allowed")
                    else:
                        source_status_cache[source_id] = (True, "allowed")

                is_allowed, skip_reason = source_status_cache[source_id]
                if not is_allowed:
                    skipped_counts[source_id] = skipped_counts.get(source_id, 0) + 1
                    continue
                title = str(record.get("title", "")).strip()
                edition = record.get("edition")
                priority = int(record.get("priority", 1))
                section_path = record.get("section_path")
                page_start = record.get("page_start")
                page_end = record.get("page_end")
                grade = record.get("grade")
                condition = str(record.get("condition", "")).strip()
                topics = record.get("topics", [])
                topics_json = json.dumps(topics) if topics else None
                text = str(record.get("text", "")).strip()

                # Check if chunk exists
                cursor.execute(f"SELECT chunk_id FROM guideline_chunks WHERE chunk_id = {ph}", (chunk_id,))
                exists = cursor.fetchone() is not None

                if be == "sqlite":
                    cursor.execute(
                        f"""
                        INSERT INTO guideline_chunks (
                            chunk_id, source_id, title, edition, priority, section_path,
                            page_start, page_end, grade, condition, topics_json, text, loaded_at
                        ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                        ON CONFLICT(chunk_id) DO UPDATE SET
                            source_id = excluded.source_id,
                            title = excluded.title,
                            edition = excluded.edition,
                            priority = excluded.priority,
                            section_path = excluded.section_path,
                            page_start = excluded.page_start,
                            page_end = excluded.page_end,
                            grade = excluded.grade,
                            condition = excluded.condition,
                            topics_json = excluded.topics_json,
                            text = excluded.text,
                            loaded_at = excluded.loaded_at
                        """,
                        (chunk_id, source_id, title, edition, priority, section_path,
                         page_start, page_end, grade, condition, topics_json, text, now)
                    )
                else:
                    cursor.execute(
                        f"""
                        INSERT INTO guideline_chunks (
                            chunk_id, source_id, title, edition, priority, section_path,
                            page_start, page_end, grade, `condition`, topics_json, text, loaded_at
                        ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                        ON DUPLICATE KEY UPDATE
                            source_id = VALUES(source_id),
                            title = VALUES(title),
                            edition = VALUES(edition),
                            priority = VALUES(priority),
                            section_path = VALUES(section_path),
                            page_start = VALUES(page_start),
                            page_end = VALUES(page_end),
                            grade = VALUES(grade),
                            `condition` = VALUES(`condition`),
                            topics_json = VALUES(topics_json),
                            text = VALUES(text),
                            loaded_at = VALUES(loaded_at)
                        """,
                        (chunk_id, source_id, title, edition, priority, section_path,
                         page_start, page_end, grade, condition, topics_json, text, now)
                    )

                if exists:
                    updated_count += 1
                else:
                    inserted_count += 1

    return inserted_count, updated_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Load guideline chunks into ChronicCare AI database.")
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to chunks.jsonl (defaults to $CHRONICCARE_DATA_DIR/rag/chunks.jsonl)",
    )
    args = parser.parse_args()

    file_arg = args.file
    if not file_arg:
        data_dir = os.environ.get("CHRONICCARE_DATA_DIR", "")
        if not data_dir:
            print("ERROR: Neither --file nor CHRONICCARE_DATA_DIR environment variable is set.", file=sys.stderr)
            return 1
        file_arg = os.path.join(data_dir, "rag", "chunks.jsonl")

    path = Path(file_arg)
    try:
        inserted, updated = load_chunks(path)
        total = inserted + updated
        print(f"[SUCCESS] Loaded {total} guideline chunks into database ({inserted} inserted, {updated} updated).")
        return 0
    except ValueError as val_err:
        print(f"[ERROR] Security check failed: {val_err}", file=sys.stderr)
        return 1
    except FileNotFoundError as fnf_err:
        print(f"[ERROR] File not found: {fnf_err}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[ERROR] Failed to load guideline chunks: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

