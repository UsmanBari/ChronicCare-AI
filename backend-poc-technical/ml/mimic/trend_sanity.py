"""
MIMIC-IV Hospital OMR Longitudinal Trend Sanity Evaluator.

Evaluates ChronicCare-AI's deterministic trend agent against sliding 30-day windows
of real outpatient/hospital blood pressure observations from MIMIC-IV.

SAFETY AND PRIVACY CONSTRAINTS:
1. Pure write-only CLI script for local execution by authorized personnel.
2. Refuses to load files located within the project repository to prevent data leakage.
3. Outputs strictly aggregated summary statistics; NEVER prints subject_id, chartdate,
   row numbers, individual measurements, or value arrays.
4. Uses identical plausibility bounds and direction algorithms as the ChronicCare-AI app.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from agents.trend_agent import (
    DIRECTION_FALLING,
    DIRECTION_RISING,
    DIRECTION_STABLE,
    TREND_THRESHOLDS,
    TYPE_DIASTOLIC,
    TYPE_SYSTOLIC,
    compute_trends,
)


def is_path_in_repo(path: Path) -> bool:
    """Check if the target path resides inside the repository workspace."""
    repo_root = Path(__file__).resolve().parents[3]
    try:
        resolved = path.resolve()
        return repo_root in resolved.parents or resolved == repo_root
    except (RuntimeError, ValueError, OSError):
        return False


def evaluate_mimic_trends(omr_path: str | Path) -> dict[str, Any]:
    """
    Process MIMIC-IV OMR file, sliding 30-day windows across blood pressure measurements.
    Returns aggregated sanity summary metrics only.
    """
    path = Path(omr_path)
    if not path.exists():
        raise FileNotFoundError(f"MIMIC OMR file does not exist at {path}")

    if is_path_in_repo(path):
        raise ValueError("Refusing to read OMR file located inside repository.")

    # Read OMR file (columns: subject_id, chartdate, seq_num, result_name, result_value)
    usecols = ["subject_id", "chartdate", "result_name", "result_value"]
    df = pd.read_csv(path, usecols=usecols, low_memory=False)

    # Filter blood pressure rows
    bp_mask = df["result_name"].astype(str).str.strip().str.lower() == "blood pressure"
    df_bp = df[bp_mask].copy()

    parse_failures = 0
    clean_records: list[dict[str, Any]] = []

    for _, row in df_bp.iterrows():
        raw_val = str(row["result_value"]).strip()
        parts = raw_val.split("/")
        if len(parts) != 2:
            parse_failures += 1
            continue

        try:
            sbp = float(parts[0].strip())
            dbp = float(parts[1].strip())
        except (ValueError, TypeError):
            parse_failures += 1
            continue

        # Check plausibility: sbp 60-260, dbp 30-160, sbp > dbp
        if not (60.0 <= sbp <= 260.0 and 30.0 <= dbp <= 160.0 and sbp > dbp):
            parse_failures += 1
            continue

        chart_str = str(row["chartdate"]).strip()
        try:
            dt = datetime.strptime(chart_str.split()[0], "%Y-%m-%d")
        except ValueError:
            parse_failures += 1
            continue

        clean_records.append({
            "subject_id": row["subject_id"],
            "date": dt,
            "sbp": sbp,
            "dbp": dbp,
        })

    if not clean_records:
        return {
            "subjects_with_evaluable_windows": 0,
            "windows_evaluated": 0,
            "systolic": {
                "direction_distribution_pct": {"rising": 0.0, "stable": 0.0, "falling": 0.0},
                "consecutive_window_flip_rate_pct": 0.0,
                "median_abs_change_mmhg": 0.0,
                "naive_last_minus_first_disagreement_pct": 0.0,
            },
            "diastolic": {
                "direction_distribution_pct": {"rising": 0.0, "stable": 0.0, "falling": 0.0},
                "consecutive_window_flip_rate_pct": 0.0,
                "median_abs_change_mmhg": 0.0,
                "naive_last_minus_first_disagreement_pct": 0.0,
            },
            "parse_failures": parse_failures,
        }

    # Group by subject and sort chronologically
    df_clean = pd.DataFrame(clean_records).sort_values(by=["subject_id", "date"])
    subjects_grouped = df_clean.groupby("subject_id")

    evaluable_subjects = 0
    total_windows_evaluated = 0

    # Systolic tracking
    sys_directions: list[str] = []
    sys_abs_changes: list[float] = []
    sys_flips = 0
    sys_transitions = 0
    sys_naive_disagreements = 0

    # Diastolic tracking
    dia_directions: list[str] = []
    dia_abs_changes: list[float] = []
    dia_flips = 0
    dia_transitions = 0
    dia_naive_disagreements = 0

    for _, group in subjects_grouped:
        unique_dates = sorted(group["date"].unique())
        subject_had_evaluable_window = False
        prev_sys_dir: str | None = None
        prev_dia_dir: str | None = None

        for cur_date in unique_dates:
            window_start = cur_date - timedelta(days=30)
            in_win = group[(group["date"] >= window_start) & (group["date"] <= cur_date)]

            # Trend agent requires at least 3 readings in the window
            if len(in_win) < 3:
                continue

            subject_had_evaluable_window = True
            total_windows_evaluated += 1

            # Format history for compute_trends
            history: list[dict[str, Any]] = []
            for _, r in in_win.iterrows():
                ts_str = f"{r['date'].strftime('%Y-%m-%d')}T12:00:00Z"
                history.append({
                    "observation_type": TYPE_SYSTOLIC,
                    "value": r["sbp"],
                    "timestamp": ts_str,
                })
                history.append({
                    "observation_type": TYPE_DIASTOLIC,
                    "value": r["dbp"],
                    "timestamp": ts_str,
                })

            now_str = f"{cur_date.strftime('%Y-%m-%d')}T23:59:59Z"
            trend_res = compute_trends(history, now=now_str, window_days=30)

            # 1. Systolic Analysis
            sys_t = trend_res["trends"][TYPE_SYSTOLIC]
            sys_dir = sys_t["direction"]
            if sys_dir in (DIRECTION_RISING, DIRECTION_FALLING, DIRECTION_STABLE):
                sys_directions.append(sys_dir)
                if sys_t.get("change") is not None:
                    sys_abs_changes.append(abs(sys_t["change"]))

                # Check consecutive flip
                if prev_sys_dir in (DIRECTION_RISING, DIRECTION_FALLING):
                    sys_transitions += 1
                    if (prev_sys_dir == DIRECTION_RISING and sys_dir == DIRECTION_FALLING) or \
                       (prev_sys_dir == DIRECTION_FALLING and sys_dir == DIRECTION_RISING):
                        sys_flips += 1
                prev_sys_dir = sys_dir

                # Naive "last minus first" comparison
                first_sbp = in_win.iloc[0]["sbp"]
                last_sbp = in_win.iloc[-1]["sbp"]
                delta_sbp = last_sbp - first_sbp
                threshold_sys = TREND_THRESHOLDS[TYPE_SYSTOLIC]
                if delta_sbp >= threshold_sys:
                    naive_sys = DIRECTION_RISING
                elif delta_sbp <= -threshold_sys:
                    naive_sys = DIRECTION_FALLING
                else:
                    naive_sys = DIRECTION_STABLE

                if naive_sys != sys_dir:
                    sys_naive_disagreements += 1

            # 2. Diastolic Analysis
            dia_t = trend_res["trends"][TYPE_DIASTOLIC]
            dia_dir = dia_t["direction"]
            if dia_dir in (DIRECTION_RISING, DIRECTION_FALLING, DIRECTION_STABLE):
                dia_directions.append(dia_dir)
                if dia_t.get("change") is not None:
                    dia_abs_changes.append(abs(dia_t["change"]))

                # Check consecutive flip
                if prev_dia_dir in (DIRECTION_RISING, DIRECTION_FALLING):
                    dia_transitions += 1
                    if (prev_dia_dir == DIRECTION_RISING and dia_dir == DIRECTION_FALLING) or \
                       (prev_dia_dir == DIRECTION_FALLING and dia_dir == DIRECTION_RISING):
                        dia_flips += 1
                prev_dia_dir = dia_dir

                # Naive "last minus first" comparison
                first_dbp = in_win.iloc[0]["dbp"]
                last_dbp = in_win.iloc[-1]["dbp"]
                delta_dbp = last_dbp - first_dbp
                threshold_dia = TREND_THRESHOLDS[TYPE_DIASTOLIC]
                if delta_dbp >= threshold_dia:
                    naive_dia = DIRECTION_RISING
                elif delta_dbp <= -threshold_dia:
                    naive_dia = DIRECTION_FALLING
                else:
                    naive_dia = DIRECTION_STABLE

                if naive_dia != dia_dir:
                    dia_naive_disagreements += 1

        if subject_had_evaluable_window:
            evaluable_subjects += 1

    def calc_dist(directions: list[str]) -> dict[str, float]:
        if not directions:
            return {"rising": 0.0, "stable": 0.0, "falling": 0.0}
        total = len(directions)
        return {
            "rising": round((directions.count(DIRECTION_RISING) / total) * 100.0, 1),
            "stable": round((directions.count(DIRECTION_STABLE) / total) * 100.0, 1),
            "falling": round((directions.count(DIRECTION_FALLING) / total) * 100.0, 1),
        }

    report = {
        "subjects_with_evaluable_windows": evaluable_subjects,
        "windows_evaluated": total_windows_evaluated,
        "systolic": {
            "direction_distribution_pct": calc_dist(sys_directions),
            "consecutive_window_flip_rate_pct": round((sys_flips / sys_transitions) * 100.0, 1) if sys_transitions > 0 else 0.0,
            "median_abs_change_mmhg": round(statistics.median(sys_abs_changes), 1) if sys_abs_changes else 0.0,
            "naive_last_minus_first_disagreement_pct": round((sys_naive_disagreements / len(sys_directions)) * 100.0, 1) if sys_directions else 0.0,
        },
        "diastolic": {
            "direction_distribution_pct": calc_dist(dia_directions),
            "consecutive_window_flip_rate_pct": round((dia_flips / dia_transitions) * 100.0, 1) if dia_transitions > 0 else 0.0,
            "median_abs_change_mmhg": round(statistics.median(dia_abs_changes), 1) if dia_abs_changes else 0.0,
            "naive_last_minus_first_disagreement_pct": round((dia_naive_disagreements / len(dia_directions)) * 100.0, 1) if dia_directions else 0.0,
        },
        "parse_failures": parse_failures,
    }

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MIMIC-IV Hospital OMR Longitudinal Trend Sanity Evaluator"
    )
    parser.add_argument(
        "--omr",
        required=True,
        help="Path to external MIMIC-IV omr.csv (must be located outside repository).",
    )
    args = parser.parse_args()

    try:
        report = evaluate_mimic_trends(args.omr)
        # Output ONLY formatted aggregates JSON (zero row-level disclosures)
        print(json.dumps(report, indent=2))
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
