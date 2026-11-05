#!/usr/bin/env python3
"""
Guideline Chunks Deletion CLI.
Safely purges guideline chunks for expired or unpermitted guideline licences
from the project database `guideline_chunks` table.

Safety rules:
- Dry run by default. Requires explicit `--yes` flag to perform deletion.
- Refuses to run without `--source-id` or `--licence`.
- Prints chunk counts only. Never prints credentials, database URLs, or guideline text.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from data_sources.app_store import get_db_cursor
from rag.licences import get_all_licence_specs

ADA_2026_SOURCE_IDS = {
    "ada_2026_sec02",
    "ada_2026_sec05",
    "ada_2026_sec06",
    "ada_2026_sec10",
    "ada_2026_sec11",
    "ada_2026_sec13",
}


def resolve_target_sources(
    source_id: Optional[str] = None,
    licence: Optional[str] = None,
) -> Set[str]:
    """Resolve target source IDs from CLI arguments."""
    target_ids: Set[str] = set()

    if source_id:
        target_ids.add(str(source_id).strip().lower())

    if licence:
        lic_norm = str(licence).strip().lower()
        if lic_norm in ("ada_2026", "ada"):
            target_ids.update(ADA_2026_SOURCE_IDS)
        else:
            # Query licence specs
            specs = get_all_licence_specs()
            for sid, spec in specs.items():
                if str(spec.get("licence_id", "")).strip().lower() == lic_norm:
                    target_ids.add(sid)

    return target_ids


def delete_guideline_sources(
    target_sources: Set[str],
    execute: bool = False,
    backend: Optional[str] = None,
    db_path: Optional[str] = None,
    mysql_url: Optional[str] = None,
    ssl_ca: Optional[str] = None,
) -> tuple[int, int]:
    """
    Deletes guideline chunks matching target_sources.
    Returns (count_before, count_after).
    """
    if not target_sources:
        raise ValueError("No target sources specified for deletion.")

    with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cur, be, ph):
        placeholders = ", ".join([ph] * len(target_sources))
        source_tuple = tuple(sorted(target_sources))

        # 1. Count before
        count_query = f"SELECT COUNT(*) FROM guideline_chunks WHERE source_id IN ({placeholders})"
        cur.execute(count_query, source_tuple)
        row = cur.fetchone()
        count_before = row[0] if row else 0

        if not execute:
            return count_before, count_before

        # 2. Execute deletion
        delete_query = f"DELETE FROM guideline_chunks WHERE source_id IN ({placeholders})"
        cur.execute(delete_query, source_tuple)

        # 3. Count after
        cur.execute(count_query, source_tuple)
        row_after = cur.fetchone()
        count_after = row_after[0] if row_after else 0

        return count_before, count_after


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Purge guideline chunks by source_id or licence name.")
    parser.add_argument("--source-id", type=str, default=None, help="Specific source_id to delete (e.g. ada_2026_sec02)")
    parser.add_argument("--licence", type=str, default=None, help="Licence name to delete (e.g. ada_2026)")
    parser.add_argument("--yes", action="store_true", help="Execute deletion (dry run if omitted)")
    parser.add_argument("--db-path", type=str, default=None, help="Optional SQLite database path")
    parser.add_argument("--backend", type=str, default=None, help="Database backend (sqlite | mysql)")

    args = parser.parse_args(argv)

    if not args.source_id and not args.licence:
        print("ERROR: Refusing to run without --source-id or --licence.", file=sys.stderr)
        return 1

    target_sources = resolve_target_sources(source_id=args.source_id, licence=args.licence)
    if not target_sources:
        print("ERROR: No valid guideline sources resolved for the specified arguments.", file=sys.stderr)
        return 1

    try:
        count_before, count_after = delete_guideline_sources(
            target_sources=target_sources,
            execute=args.yes,
            backend=args.backend,
            db_path=args.db_path,
        )

        sources_str = ", ".join(sorted(target_sources))
        if not args.yes:
            print(f"[DRY RUN] Found {count_before} chunks for source(s): {sources_str}. No rows deleted. Pass --yes to execute.")
        else:
            deleted_count = count_before - count_after
            print(f"[DELETED] Successfully deleted {deleted_count} chunks for source(s): {sources_str}. Count before: {count_before}, count after: {count_after}.")
        return 0
    except Exception as exc:
        print(f"ERROR: Deletion failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

