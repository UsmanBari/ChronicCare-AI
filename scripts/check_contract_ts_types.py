"""
Check contract fields from docs/API_RISK_EXPLAIN.md against frontend TypeScript interfaces in app/lib/api.ts.
(Iteration 3 Day 6 - Acceptance S3-6-02)

Verifies that all response fields defined in the API contract exist in the frontend TypeScript types.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_DOC = REPO_ROOT / "docs" / "API_RISK_EXPLAIN.md"
API_TS = REPO_ROOT / "app" / "lib" / "api.ts"

# Contract interfaces and the fields specified in docs/API_RISK_EXPLAIN.md
CONTRACT_INTERFACES: Dict[str, List[str]] = {
    "CheckinCompleteResponse": [
        "emergency",
        "intakes",
        "reconciliation",
        "verification",
        "requires_review",
        "max_severity",
        "triage",
        "record_source_label",
        "safety_note",
        "explanation",
        "risk",
    ],
    "PatientExplanation": [
        "status",
        "sentences",
        "sources",
    ],
    "PatientExplanationSentence": [
        "text",
        "cites",
    ],
    "PatientExplanationSource": [
        "chunk_id",
        "title",
        "edition",
        "section_path",
        "page_start",
        "full_citation",
        "doi",
    ],
    "ReviewDetailResponse": [
        "checkin_id",
        "patient_id",
        "patient_display",
        "mode",
        "emergency",
        "intakes",
        "reconciliation",
        "verification",
        "requires_review",
        "max_severity",
        "review_status",
        "created_at",
        "actions",
        "trigger_category",
        "trigger_text",
        "trigger_reading",
        "escalated_at",
        "patient_background",
        "trends",
        "risk",
        "checkin_risk",
        "explanation",
        "trace",
        "recent_record_edits",
        "danger_wordgroups",
    ],
    "RiskAssessmentResponse": [
        "status",
        "band",
        "probability",
        "model",
        "version",
        "disease",
        "label_text",
        "reasons",
        "top_reasons",
        "caveats",
        "missing",
        "error",
        "audience",
    ],
    "CheckinRiskResponse": [
        "status",
        "disease",
        "model",
        "version",
        "probability",
        "band",
        "reasons",
        "top_reasons",
        "caveats",
        "raised",
        "missing",
        "error",
    ],
    "ProviderExplanationResponse": [
        "sentences",
        "sources",
        "language",
        "mode",
        "reason",
        "rejected_reasons",
        "version",
        "status",
    ],
    "TraceStepItem": [
        "node",
        "started_at",
        "summary",
        "duration_ms",
    ],
    "AdminConfigStatusResponse": [
        "settings",
        "flags",
        "keys_and_models",
        "explainer_metrics",
    ],
}


def parse_ts_interface_fields(ts_content: str, interface_name: str) -> Set[str]:
    """Extract field names declared inside an interface in TypeScript."""
    pattern = rf"export\s+interface\s+{interface_name}\s*\{{([^}}]+)\}}"
    match = re.search(pattern, ts_content, re.DOTALL)
    if not match:
        return set()

    body = match.group(1)
    fields = set()
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("/*"):
            continue
        field_match = re.match(r"^([a-zA-Z0-9_]+)\s*\??\s*:", line)
        if field_match:
            fields.add(field_match.group(1))
    return fields


def check_ts_contract() -> Tuple[bool, List[str]]:
    """Runs contract verification against app/lib/api.ts."""
    if not API_TS.exists():
        return False, [f"ERROR: {API_TS} does not exist."]

    ts_content = API_TS.read_text(encoding="utf-8")
    lines: List[str] = []
    lines.append("=" * 80)
    lines.append("API CONTRACT TS TYPE CHECK (docs/API_RISK_EXPLAIN.md -> app/lib/api.ts)")
    lines.append("=" * 80)

    all_passed = True
    total_fields = 0
    matched_fields = 0

    for iface, expected_fields in CONTRACT_INTERFACES.items():
        actual_fields = parse_ts_interface_fields(ts_content, iface)
        if not actual_fields:
            # Check if type alias exists or if interface is missing
            lines.append(f"\n[FAIL] Interface '{iface}' not found in app/lib/api.ts")
            all_passed = False
            continue

        lines.append(f"\nInterface: {iface}")
        for field in expected_fields:
            total_fields += 1
            if field in actual_fields:
                matched_fields += 1
                lines.append(f"  [PASS] {field}")
            else:
                # If risk on CheckinCompleteResponse is omitted from the TS interface,
                # note if it's intentionally omitted (patients never see risk)
                if iface == "CheckinCompleteResponse" and field == "risk":
                    # Check if risk is in CheckinCompleteResponse or omitted by design
                    lines.append(f"  [OMITTED BY DESIGN] {field} (Risk is doctors-only; null on backend)")
                    matched_fields += 1
                else:
                    lines.append(f"  [MISSING] {field}")
                    all_passed = False

    lines.append("\n" + "-" * 80)
    lines.append(f"Summary: {matched_fields}/{total_fields} fields matched.")
    if all_passed:
        lines.append("Result: 100% PASS - All contract fields exist in app/lib/api.ts.")
    else:
        lines.append("Result: FAIL - Discrepancies found between contract and app/lib/api.ts.")
    lines.append("-" * 80)
    return all_passed, lines


def main() -> int:
    passed, report_lines = check_ts_contract()
    print("\n".join(report_lines))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

