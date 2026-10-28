"""
Compute train_core, validation, and test counts and prevalence
for candidate ML risk labels and card evaluation populations in ChronicCare AI.

Compares:
1. Diabetes:
   - Option 2A (Screening / Undiagnosed): Label diabetes_undiagnosed, trained on adults WITHOUT diagnosed diabetes (told_diabetes == 0).
   - Option 2B (Total Burden): Label diabetes_told_or_measured, trained on all adults.
   - Option 2C (Self-Reported): Label diabetes_told, trained on all adults.
2. Hypertension:
   - Option 2D (Screening / Undiagnosed): Measured BP >= 130/80, trained on adults NOT told they have high BP and NOT on BP meds.
   - Option 2E (Comprehensive / Total Burden): Label hypertension_stage1_or_clinical, trained on all adults.
   - Option 2F (Clinical History): Label hypertension_told_or_meds, trained on all adults.
   - Option 2G (Measured 130/80 on All Adults): Label hypertension_measured_130_80, trained on all adults.
3. Card Populations (for Evaluation):
   - Diabetes Card Population: Evaluates diabetes model strictly on adults with told_high_bp == 1 (the patients who see the diabetes card).
   - Hypertension Card Population: Evaluates hypertension model strictly on adults with told_diabetes == 1 (the patients who see the hypertension card).
4. Feature Missingness:
   - Checks feature presence and non-missing % per split for BASIC and candidate FULL features.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add backend ml folder to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend-poc-technical" / "ml"))

from common import df_to_markdown, load_nhanes_core, load_split
from labels import (
    extract_diabetes_told,
    extract_diabetes_told_or_measured,
    extract_diabetes_undiagnosed,
    extract_hypertension_measured_130_80,
    extract_hypertension_stage1_or_clinical,
    extract_hypertension_told_or_meds,
)


def compute_counts():
    df = load_nhanes_core()
    splits = load_split("nhanes_temporal_v1")

    # Hypertension undiagnosed series
    htn_pop_mask = (df["told_high_bp"] == 0) & (df["takes_bp_meds"] != 1)
    y_htn_und_130_80 = pd.Series(
        np.where(
            htn_pop_mask & df["sbp"].notna() & df["dbp"].notna(),
            np.where((df["sbp"] >= 130.0) | (df["dbp"] >= 80.0), 1.0, 0.0),
            np.nan,
        ),
        index=df.index,
    )

    targets = [
        # (label_name, population_name, y_series, extra_filter_mask)
        (
            "diabetes_undiagnosed (Option 2A)",
            "Adults WITHOUT diagnosed diabetes (told_diabetes == 0)",
            extract_diabetes_undiagnosed(df),
            None,
        ),
        (
            "diabetes_told_or_measured (Option 2B)",
            "All adults",
            extract_diabetes_told_or_measured(df),
            None,
        ),
        (
            "diabetes_told (Option 2C)",
            "All adults",
            extract_diabetes_told(df),
            None,
        ),
        (
            "hypertension_measured_130_80 (Option 2D)",
            "Adults NOT told high BP and NOT on BP meds",
            y_htn_und_130_80,
            None,
        ),
        (
            "hypertension_stage1_or_clinical (Option 2E)",
            "All adults",
            extract_hypertension_stage1_or_clinical(df),
            None,
        ),
        (
            "hypertension_told_or_meds (Option 2F)",
            "All adults",
            extract_hypertension_told_or_meds(df),
            None,
        ),
        (
            "hypertension_measured_130_80 (Option 2G)",
            "All adults",
            extract_hypertension_measured_130_80(df),
            None,
        ),
        # Card evaluation populations
        (
            "Diabetes Card Eval Population",
            "Non-diabetics with told_high_bp == 1 (Card audience)",
            extract_diabetes_undiagnosed(df),
            (df["told_diabetes"] == 0) & (df["told_high_bp"] == 1),
        ),
        (
            "Hypertension Card Eval Population",
            "Diabetics not told high BP & not on meds (Card audience)",
            y_htn_und_130_80,
            htn_pop_mask & (df["told_diabetes"] == 1),
        ),
    ]

    records = []
    for label_name, pop_desc, y_series, extra_mask in targets:
        row = {"Target / Evaluation Group": label_name, "Population": pop_desc}
        for split_name in ["train_core", "validation", "test"]:
            seqns = splits[split_name]
            split_mask = df["seqn"].isin(seqns)
            if extra_mask is not None:
                split_mask = split_mask & extra_mask

            split_y = y_series[split_mask]
            n_eval = int(split_y.notna().sum())
            n_pos = int((split_y == 1.0).sum())
            prev = (n_pos / n_eval * 100.0) if n_eval > 0 else 0.0
            row[f"{split_name} (Pos / Total)"] = f"{n_pos:,} / {n_eval:,} ({prev:.1f}%)"
        records.append(row)

    res_df = pd.DataFrame(records)
    print("=== POPULATION COUNTS AND PREVALENCE ACROSS TEMPORAL SPLITS ===")
    print(df_to_markdown(res_df, index=False))

    # Feature completeness table
    features = [
        "age",
        "sex_male",
        "bmi",
        "ever_smoked_100",
        "told_high_bp",
        "told_diabetes",
        "sbp",
        "dbp",
        "hba1c",
        "fasting_glucose",
        "waist_cm",
        "family_hx_diabetes",
        "phys_active",
    ]

    feat_records = []
    for feat in features:
        in_data = feat in df.columns
        row = {"Feature": feat, "In nhanes_core": "Yes" if in_data else "No"}
        for split_name in ["train_core", "validation", "test"]:
            if in_data:
                sub = df[df["seqn"].isin(splits[split_name])][feat]
                non_miss_pct = sub.notna().mean() * 100.0
                row[f"{split_name} Non-Missing %"] = f"{non_miss_pct:.1f}% ({sub.notna().sum():,}/{len(sub):,})"
            else:
                row[f"{split_name} Non-Missing %"] = "0.0% (Missing from data)"
        feat_records.append(row)

    feat_df = pd.DataFrame(feat_records)
    print("\n=== FEATURE AVAILABILITY AND NON-MISSING % PER SPLIT ===")
    print(df_to_markdown(feat_df, index=False))

    return res_df, feat_df


if __name__ == "__main__":
    compute_counts()
