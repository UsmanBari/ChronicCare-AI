"""
Compute train_core, validation, and test counts, prevalence, complete cases,
and cycle breakdowns for ML risk models in ChronicCare AI.
Outputs strictly aggregated counts, percentages, and markdown tables.
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

    # Hypertension undiagnosed series: measured >= 130/80 among adults NOT told high BP and NOT on BP meds
    htn_pop_mask = (df["told_high_bp"] == 0) & (df["takes_bp_meds"] != 1)
    y_htn_und_130_80 = pd.Series(
        np.where(
            htn_pop_mask & df["sbp"].notna() & df["dbp"].notna(),
            np.where((df["sbp"] >= 130.0) | (df["dbp"] >= 80.0), 1.0, 0.0),
            np.nan,
        ),
        index=df.index,
    )

    y_dm_und = extract_diabetes_undiagnosed(df)

    # 1. Target Label Populations & Prevalence
    targets = [
        (
            "diabetes_undiagnosed (Option 2A)",
            "Adults WITHOUT diagnosed diabetes (told_diabetes == 0)",
            y_dm_und,
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
            y_dm_und,
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

    # 2. Feature Availability Table (% Non-Missing)
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

    # 3. Complete-Case Counts for BASIC and FULL Models
    # Definitions:
    # Diabetes BASIC: age, sex_male, bmi, ever_smoked_100, told_high_bp
    # Diabetes FULL:  BASIC + sbp, dbp, waist_cm
    # Hypertension BASIC: age, sex_male, bmi, ever_smoked_100, told_diabetes
    # Hypertension FULL:  BASIC + hba1c, waist_cm

    dm_basic_cols = ["age", "sex_male", "bmi", "ever_smoked_100", "told_high_bp"]
    dm_full_cols = dm_basic_cols + ["sbp", "dbp", "waist_cm"]

    htn_basic_cols = ["age", "sex_male", "bmi", "ever_smoked_100", "told_diabetes"]
    htn_full_cols = htn_basic_cols + ["hba1c", "waist_cm"]

    cc_configs = [
        ("Diabetes Model", "BASIC", dm_basic_cols, y_dm_und, df["told_diabetes"] == 0, "Adults without diagnosed diabetes"),
        ("Diabetes Model", "FULL", dm_full_cols, y_dm_und, df["told_diabetes"] == 0, "Adults without diagnosed diabetes"),
        ("Diabetes Model (Card)", "BASIC", dm_basic_cols, y_dm_und, (df["told_diabetes"] == 0) & (df["told_high_bp"] == 1), "Card Audience (told_high_bp == 1)"),
        ("Diabetes Model (Card)", "FULL", dm_full_cols, y_dm_und, (df["told_diabetes"] == 0) & (df["told_high_bp"] == 1), "Card Audience (told_high_bp == 1)"),
        ("Hypertension Model", "BASIC", htn_basic_cols, y_htn_und_130_80, htn_pop_mask, "Adults not told high BP & not on meds"),
        ("Hypertension Model", "FULL", htn_full_cols, y_htn_und_130_80, htn_pop_mask, "Adults not told high BP & not on meds"),
        ("Hypertension Model (Card)", "BASIC", htn_basic_cols, y_htn_und_130_80, htn_pop_mask & (df["told_diabetes"] == 1), "Card Audience (told_diabetes == 1)"),
        ("Hypertension Model (Card)", "FULL", htn_full_cols, y_htn_und_130_80, htn_pop_mask & (df["told_diabetes"] == 1), "Card Audience (told_diabetes == 1)"),
    ]

    cc_records = []
    for model_name, tier, feat_list, y_series, pop_filter, pop_desc in cc_configs:
        row = {"Model": model_name, "Tier": tier, "Audience / Population": pop_desc}
        for split_name in ["train_core", "validation", "test"]:
            seqns = splits[split_name]
            mask = df["seqn"].isin(seqns) & pop_filter & y_series.notna()
            # Require all features in feat_list to be non-null
            for c in feat_list:
                mask = mask & df[c].notna()

            sub_y = y_series[mask]
            n_rows = len(sub_y)
            n_pos = int((sub_y == 1.0).sum())
            prev = (n_pos / n_rows * 100.0) if n_rows > 0 else 0.0
            row[f"{split_name} (Pos / Total)"] = f"{n_pos:,} / {n_rows:,} ({prev:.1f}%)"
        cc_records.append(row)

    cc_df = pd.DataFrame(cc_records)
    print("\n=== COMPLETE-CASE COUNTS ACROSS TEMPORAL SPLITS (BASIC vs FULL) ===")
    print(df_to_markdown(cc_df, index=False))

    # 4. Test Split Hypertension Prevalence by NHANES Cycle
    test_seqns = splits["test"]
    test_df = df[df["seqn"].isin(test_seqns)].copy()
    test_y = y_htn_und_130_80[df["seqn"].isin(test_seqns)]

    cycle_records = []
    for cycle_val in sorted(test_df["cycle"].unique()):
        cycle_mask = (test_df["cycle"] == cycle_val)
        sub_y = test_y[cycle_mask]
        n_eval = int(sub_y.notna().sum())
        n_pos = int((sub_y == 1.0).sum())
        prev = (n_pos / n_eval * 100.0) if n_eval > 0 else 0.0
        cycle_records.append({
            "Test Cycle": cycle_val,
            "Eligible (Not told, not on meds)": f"{n_eval:,}",
            "Positives (Measured >= 130/80)": f"{n_pos:,}",
            "Prevalence": f"{prev:.2f}%",
        })

    cycle_df = pd.DataFrame(cycle_records)
    print("\n=== HYPERTENSION LABEL (130/80) TEST SPLIT PREVALENCE BY CYCLE ===")
    print(df_to_markdown(cycle_df, index=False))

    return res_df, feat_df, cc_df, cycle_df


if __name__ == "__main__":
    compute_counts()
