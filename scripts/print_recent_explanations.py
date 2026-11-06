"""
Reviewer Utility: Print Recent Clinical Explanations (Q5).

Designed for Usman's (en) and Hassaan's (ur, roman_ur) human clinical review.
Strict Invariants:
1. Refuses to run unless the database store is the local SQLite file (fails fast on MySQL).
2. Prints check-in id, language, triage level, explanation mode, and each sentence with citations and source ids.
3. Fake data only; strictly omits user IDs, patient IDs, emails, and secret keys.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from data_sources import app_store


def print_recent_explanations(limit: int = 10, db_path: Optional[str] = None) -> int:
    backend = os.environ.get("DB_BACKEND", "sqlite").strip().lower()
    if backend == "mysql":
        print(f"[ERROR] Refusing to run on MySQL backend: '{backend}'. LOCAL SQLite only.", file=sys.stderr)
        return 1

    path = db_path or os.environ.get("LOCAL_DB_PATH") or str(BACKEND_DIR / "app_data.db")
    if not os.path.exists(path):
        print(f"[WARNING] Local SQLite database not found at: {path}")
        return 0

    with app_store.get_db_cursor(backend="sqlite", db_path=path) as (cur, be, ph):
        cur.execute(
            f"SELECT checkin_id, triage_level, intakes_json, explanation_json, created_at "
            f"FROM checkin_results "
            f"WHERE explanation_json IS NOT NULL AND explanation_json != '' "
            f"ORDER BY created_at DESC LIMIT {ph}",
            (limit,),
        )
        rows = cur.fetchall()

    if not rows:
        print(f"No check-in explanations found in {path}.")
        return 0

    print("=" * 95)
    print(f"RECENT CLINICAL EXPLANATIONS (Last {len(rows)} check-ins) - Store: SQLite ({Path(path).name})")
    print("=" * 95)

    for idx, row in enumerate(rows, start=1):
        cid, triage_level_col, intakes_json_str, exp_json_str, created_at = row
        try:
            exp_data = json.loads(exp_json_str) if isinstance(exp_json_str, str) else (exp_json_str or {})
        except Exception:
            exp_data = {}

        try:
            intakes = json.loads(intakes_json_str) if isinstance(intakes_json_str, str) else (intakes_json_str or [])
        except Exception:
            intakes = []

        triage_level = triage_level_col or (intakes[0].get("level") if intakes else "unknown") or "unknown"
        language = exp_data.get("language") or "en"
        mode = exp_data.get("mode") or "unknown"
        reason = exp_data.get("reason") or "none"
        provider = exp_data.get("provider") or "none"

        print(f"\n[{idx}] Check-in ID: {cid}")
        print(f"    Timestamp: {created_at} | Language: {language} | Level: {triage_level.upper()}")
        print(f"    Mode: {mode} | Reason: {reason} | Provider: {provider}")

        sentences: List[Dict[str, Any]] = exp_data.get("sentences", [])
        if sentences:
            print("    Sentences & Sources:")
            for s_idx, s in enumerate(sentences, start=1):
                stext = s.get("text", "")
                cites = s.get("cites", [])
                cite_str = f" [Cites: {', '.join(cites)}]" if cites else ""
                print(f"      {s_idx}. {stext}{cite_str}")
        else:
            print("    (No sentence breakdown present)")

    print("\n" + "=" * 95)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Print recent check-in explanations for clinical review.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of check-ins to print (default: 10)")
    parser.add_argument("--db", "--db-path", dest="db_path", type=str, default=None, help="Custom path to local SQLite database")
    args = parser.parse_args()
    return print_recent_explanations(limit=args.limit, db_path=args.db_path)


if __name__ == "__main__":
    sys.exit(main())
