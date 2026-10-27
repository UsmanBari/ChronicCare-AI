"""
NHANES Temporal Data Split Generator (v1).
Partitions NHANES adult participants (age >= 18) strictly across time:
- train_core: 1999-2000 through 2011-2012 (7 cycles)
- validation: 2013-2014 and 2015-2016 (2 cycles)
- test:       2017-2018 and 2021-2023 (2 cycles)

Writes SEQN ID lists only to $CHRONICCARE_DATA_DIR/splits/nhanes_temporal_v1.json.
Appends the Temporal Split summary table to docs/DATA_CHECKS.md.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from common import (
    ADULT_MIN_AGE,
    data_dir,
    df_to_markdown,
    load_nhanes_core,
)

TRAIN_CORE_CYCLES = [
    "1999-2000",
    "2001-2002",
    "2003-2004",
    "2005-2006",
    "2007-2008",
    "2009-2010",
    "2011-2012",
]
VALIDATION_CYCLES = ["2013-2014", "2015-2016"]
TEST_CYCLES = ["2017-2018", "2021-2023"]


def get_git_commit_hash() -> str:
    """Retrieve current HEAD commit hash, or 'unknown' if not in git."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


def generate_nhanes_temporal_splits(df: pd.DataFrame) -> dict[str, list[int]]:
    """
    Partition adult NHANES records into train_core, validation, and test sets.
    Performs assertions to ensure:
    - Splits are strictly pairwise disjoint
    - The union of splits equals exactly all adult records (age >= 18)
    - Records in each split strictly belong to the intended cycles
    """
    if "age" not in df.columns or "cycle" not in df.columns or "seqn" not in df.columns:
        raise ValueError("DataFrame must contain 'seqn', 'cycle', and 'age' columns")

    adults = df[df["age"] >= ADULT_MIN_AGE].copy()
    all_adult_seqns = set(adults["seqn"].astype(int))

    train_df = adults[adults["cycle"].isin(TRAIN_CORE_CYCLES)]
    val_df = adults[adults["cycle"].isin(VALIDATION_CYCLES)]
    test_df = adults[adults["cycle"].isin(TEST_CYCLES)]

    train_seqns = [int(s) for s in train_df["seqn"]]
    val_seqns = [int(s) for s in val_df["seqn"]]
    test_seqns = [int(s) for s in test_df["seqn"]]

    train_set = set(train_seqns)
    val_set = set(val_seqns)
    test_set = set(test_seqns)

    # 1. Assert pairwise disjoint
    assert train_set.isdisjoint(val_set), "train_core and validation overlap!"
    assert train_set.isdisjoint(test_set), "train_core and test overlap!"
    assert val_set.isdisjoint(test_set), "validation and test overlap!"

    # 2. Assert union equals all adults
    union_set = train_set | val_set | test_set
    assert union_set == all_adult_seqns, (
        f"Split union ({len(union_set)}) != total adults ({len(all_adult_seqns)})"
    )

    # 3. Assert cycle membership
    assert set(train_df["cycle"].unique()).issubset(set(TRAIN_CORE_CYCLES))
    assert set(val_df["cycle"].unique()).issubset(set(VALIDATION_CYCLES))
    assert set(test_df["cycle"].unique()).issubset(set(TEST_CYCLES))

    return {
        "train_core": train_seqns,
        "validation": val_seqns,
        "test": test_seqns,
    }


def compute_split_summary(df: pd.DataFrame, splits: dict[str, list[int]]) -> pd.DataFrame:
    """
    Compute counts, told_diabetes, measured_diabetes, and BP >= 130/80 prevalence rates
    per split for documentation in docs/DATA_CHECKS.md.
    """
    records = []
    adults = df[df["age"] >= ADULT_MIN_AGE].copy()
    adults["seqn"] = adults["seqn"].astype(int)

    # Indicator columns
    told_diab = adults["told_diabetes"] == 1
    measured_diab = (adults["hba1c"] >= 6.5) | (adults["fasting_glucose"] >= 126.0)
    bp_130_80 = (adults["sbp"] >= 130.0) | (adults["dbp"] >= 80.0)

    for split_name in ["train_core", "validation", "test"]:
        seqn_set = set(splits[split_name])
        mask = adults["seqn"].isin(seqn_set)
        split_df = adults[mask]
        n_adults = len(split_df)

        # Told diabetes
        n_told = int((split_df["told_diabetes"] == 1).sum())
        d_told = int(split_df["told_diabetes"].notna().sum())
        told_str = f"{n_told} / {d_told} ({n_told / d_told * 100:.1f}%)" if d_told > 0 else "0 / 0"

        # Measured diabetes (hba1c >= 6.5 or fasting_glucose >= 126)
        meas_eligible = split_df["hba1c"].notna() | split_df["fasting_glucose"].notna()
        n_meas = int(((split_df["hba1c"] >= 6.5) | (split_df["fasting_glucose"] >= 126.0)).sum())
        d_meas = int(meas_eligible.sum())
        meas_str = f"{n_meas} / {d_meas} ({n_meas / d_meas * 100:.1f}%)" if d_meas > 0 else "0 / 0"

        # BP >= 130/80
        bp_eligible = split_df["sbp"].notna() & split_df["dbp"].notna()
        n_bp = int(((split_df["sbp"] >= 130.0) | (split_df["dbp"] >= 80.0)).sum())
        d_bp = int(bp_eligible.sum())
        bp_str = f"{n_bp} / {d_bp} ({n_bp / d_bp * 100:.1f}%)" if d_bp > 0 else "0 / 0"

        records.append({
            "Split": split_name,
            "Cycles": (
                "1999-2012 (7)" if split_name == "train_core" else
                "2013-2016 (2)" if split_name == "validation" else
                "2017-2023 (2)"
            ),
            "Adults": n_adults,
            "Told Diabetes": told_str,
            "Measured Diabetes": meas_str,
            "BP >= 130/80": bp_str,
        })

    return pd.DataFrame(records)


def main():
    print("Loading NHANES core data for temporal splitting...")
    cols = ["seqn", "cycle", "age", "told_diabetes", "hba1c", "fasting_glucose", "sbp", "dbp"]
    df = load_nhanes_core(cols)

    print("Generating temporal splits (train_core, validation, test)...")
    splits = generate_nhanes_temporal_splits(df)

    out_dir = data_dir() / "splits"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "nhanes_temporal_v1.json"

    payload: dict[str, Any] = {
        "version": "nhanes_temporal_v1",
        "created_with_commit": get_git_commit_hash(),
        "train_core": splits["train_core"],
        "validation": splits["validation"],
        "test": splits["test"],
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    print(f"Saved temporal split JSON to: {out_json}")
    print(f"  train_core: {len(splits['train_core'])} adults")
    print(f"  validation: {len(splits['validation'])} adults")
    print(f"  test:       {len(splits['test'])} adults")
    print(f"  total:      {len(splits['train_core']) + len(splits['validation']) + len(splits['test'])} adults")

    # Generate split summary table for docs/DATA_CHECKS.md
    summary_df = compute_split_summary(df, splits)
    table_md = df_to_markdown(summary_df, index=False)

    doc_path = Path("docs/DATA_CHECKS.md")
    if doc_path.exists():
        existing_doc = doc_path.read_text(encoding="utf-8")
        split_section_title = "\n## Temporal Splits (nhanes_temporal_v1)\n\n"
        if "## Temporal Splits (nhanes_temporal_v1)" in existing_doc:
            # Replace existing section
            parts = existing_doc.split("## Temporal Splits (nhanes_temporal_v1)")
            updated_doc = parts[0] + "## Temporal Splits (nhanes_temporal_v1)\n\n" + table_md + "\n"
        else:
            updated_doc = existing_doc + split_section_title + table_md + "\n"
        doc_path.write_text(updated_doc, encoding="utf-8")
        print(f"Appended temporal split section to {doc_path}")


if __name__ == "__main__":
    main()
