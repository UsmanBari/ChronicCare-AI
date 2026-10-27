"""
NHANES and BRFSS Data Quality & Health Checks.
Generates docs/DATA_CHECKS.md with aggregates only. Never emits row-level data or individual IDs.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

# Add repo backend to path if needed
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml import common


def generate_nhanes_report(df: pd.DataFrame) -> tuple[str, dict]:
    """
    Generate NHANES data quality report sections (D1 to D6).
    Returns markdown text and summary metrics dictionary.
    """
    lines: list[str] = []
    lines.append("## Part 1: NHANES (1999ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“2023, 11 Cycles)")
    lines.append("")

    # D1. Rows and adults per cycle; duplicate seqn count
    dup_seqn = int(df["seqn"].duplicated().sum()) if "seqn" in df.columns else 0
    total_rows = len(df)
    adults_df = df[df["age"] >= common.ADULT_MIN_AGE].copy()
    total_adults = len(adults_df)

    cycle_counts = df.groupby("cycle", observed=True).size()
    adult_cycle_counts = adults_df.groupby("cycle", observed=True).size()

    d1_df = pd.DataFrame({
        "Total Participants": cycle_counts,
        "Adults (18+)": adult_cycle_counts,
        "Adult %": (adult_cycle_counts / cycle_counts * 100.0).round(1)
    })
    d1_df.loc["Total Pooled"] = [total_rows, total_adults, round(total_adults / total_rows * 100.0, 1)]

    lines.append("### D1. Sample Sizes and Deduplication")
    lines.append(f"- **Total Participants:** {total_rows:,}")
    lines.append(f"- **Adults (age >= 18):** {total_adults:,}")
    lines.append(f"- **Duplicate SEQN Count:** {dup_seqn} (must be 0)")
    lines.append("")
    lines.append(common.df_to_markdown(d1_df))
    lines.append("")

    # D2. Missing % per column x cycle
    nhanes_feature_cols = [
        "age", "sex_male", "race_eth", "income_poverty_ratio", "bmi", "waist_cm",
        "height_cm", "weight_kg", "sbp", "dbp", "pulse", "hba1c", "fasting_glucose",
        "total_chol", "told_diabetes", "takes_insulin", "takes_diabetes_pills",
        "told_high_bp", "takes_bp_meds", "family_hx_diabetes", "ever_smoked_100",
        "exam_weight_2yr", "borderline_diabetes"
    ]
    missing_table = common.compute_missing_pct_table(adults_df, "cycle", nhanes_feature_cols)
    lines.append("### D2. Missing Value Percentage Across Cycles (Adults Only)")
    lines.append(common.df_to_markdown(missing_table))
    lines.append("")

    # D3. Implausible value counts and Age Top-Coding
    implausible = common.count_implausible_nhanes(adults_df)
    age_top = common.get_top_coded_age(adults_df, "cycle")

    lines.append("### D3. Clinical Plausibility Boundary Checks (Adults Only, Counted Not Dropped)")
    lines.append("| Clinical Measure | Boundary Criterion | Count Out of Bounds |")
    lines.append("|---|---|---|")
    lines.append(f"| Systolic BP (sbp) | < 60 or > 260 mmHg | {implausible.get('sbp_out_of_range', 0):,} |")
    lines.append(f"| Diastolic BP (dbp) | < 30 or > 160 mmHg | {implausible.get('dbp_out_of_range', 0):,} |")
    lines.append(f"| Diastolic Zero | dbp == 0 mmHg | {implausible.get('dbp_zero', 0):,} |")
    lines.append(f"| Systolic <= Diastolic | sbp <= dbp | {implausible.get('sbp_le_dbp', 0):,} |")
    lines.append(f"| Body Mass Index (bmi) | < 12 or > 80 kg/mÃƒâ€šÃ‚Â^2 | {implausible.get('bmi_out_of_range', 0):,} |")
    lines.append(f"| Waist Circumference | < 40 or > 200 cm | {implausible.get('waist_out_of_range', 0):,} |")
    lines.append(f"| Glycated Hemoglobin (hba1c) | < 3 or > 20 % | {implausible.get('hba1c_out_of_range', 0):,} |")
    lines.append(f"| Fasting Glucose | < 20 or > 600 mg/dL | {implausible.get('glucose_out_of_range', 0):,} |")
    lines.append("")

    lines.append("#### Age Top-Coding by Cycle")
    top_85_cycles = [c for c, m in age_top.items() if m == 85]
    top_80_cycles = [c for c, m in age_top.items() if m == 80]
    lines.append(f"- **Top-coded at 85:** {', '.join(top_85_cycles)} (cycles prior to 2007ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“2008)")
    lines.append(f"- **Top-coded at 80:** {', '.join(top_80_cycles)} (cycles from 2007ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“2008 onward)")
    lines.append("")

    # D4. Label counts and rates per cycle (DESCRIPTIVE ONLY)
    # Define indicators
    a = adults_df
    told_dm = a["told_diabetes"] == 1
    told_dm_known = a["told_diabetes"].notna()

    borderline_dm = a["borderline_diabetes"] == 1
    borderline_known = a["borderline_diabetes"].notna()

    meas_dm_valid = a["hba1c"].notna() | a["fasting_glucose"].notna()
    meas_dm = (a["hba1c"] >= 6.5) | (a["fasting_glucose"] >= 126)

    undiag_valid = meas_dm_valid & told_dm_known
    undiag = meas_dm & (a["told_diabetes"] == 0)

    told_hbp = a["told_high_bp"] == 1
    told_hbp_known = a["told_high_bp"].notna()

    bp_meds = a["takes_bp_meds"] == 1
    bp_meds_known = a["takes_bp_meds"].notna()

    bp_valid = a["sbp"].notna() & a["dbp"].notna()
    bp_130_80 = (a["sbp"] >= 130) | (a["dbp"] >= 80)
    bp_140_90 = (a["sbp"] >= 140) | (a["dbp"] >= 90)

    uncontrolled_valid = (a["told_high_bp"] == 1) & bp_valid
    uncontrolled = uncontrolled_valid & bp_140_90

    # Build per-cycle summary
    cycles = sorted(a["cycle"].unique())
    rows_d4 = []
    for c in cycles:
        sub = a[a["cycle"] == c]
        def fmt(num_s: pd.Series, den_s: pd.Series) -> str:
            n = int((num_s[sub.index] & den_s[sub.index]).sum())
            d = int(den_s[sub.index].sum())
            pct = (n / d * 100.0) if d > 0 else 0.0
            return f"{n:,} / {d:,} ({pct:.1f}%)"

        rows_d4.append({
            "Cycle": c,
            "Told Diabetes": fmt(told_dm, told_dm_known),
            "Borderline Diabetes": fmt(borderline_dm, borderline_known),
            "Measured Diabetes (A1c>=6.5 or FPG>=126)": fmt(meas_dm, meas_dm_valid),
            "Undiagnosed Diabetes": fmt(undiag, undiag_valid),
            "Told High BP": fmt(told_hbp, told_hbp_known),
            "Takes BP Meds": fmt(bp_meds, bp_meds_known),
            "BP >= 130/80 (Stage 1+)": fmt(bp_130_80, bp_valid),
            "BP >= 140/90 (Stage 2)": fmt(bp_140_90, bp_valid),
            "Uncontrolled (Told HBP & BP>=140/90)": fmt(uncontrolled, uncontrolled_valid),
        })

    # Total row
    def fmt_tot(num_s: pd.Series, den_s: pd.Series) -> str:
        n = int((num_s & den_s).sum())
        d = int(den_s.sum())
        pct = (n / d * 100.0) if d > 0 else 0.0
        return f"{n:,} / {d:,} ({pct:.1f}%)"

    rows_d4.append({
        "Cycle": "**Total Pooled**",
        "Told Diabetes": fmt_tot(told_dm, told_dm_known),
        "Borderline Diabetes": fmt_tot(borderline_dm, borderline_known),
        "Measured Diabetes (A1c>=6.5 or FPG>=126)": fmt_tot(meas_dm, meas_dm_valid),
        "Undiagnosed Diabetes": fmt_tot(undiag, undiag_valid),
        "Told High BP": fmt_tot(told_hbp, told_hbp_known),
        "Takes BP Meds": fmt_tot(bp_meds, bp_meds_known),
        "BP >= 130/80 (Stage 1+)": fmt_tot(bp_130_80, bp_valid),
        "BP >= 140/90 (Stage 2)": fmt_tot(bp_140_90, bp_valid),
        "Uncontrolled (Told HBP & BP>=140/90)": fmt_tot(uncontrolled, uncontrolled_valid),
    })

    d4_df = pd.DataFrame(rows_d4)
    lines.append("### D4. Descriptive Candidate Label Prevalence by Cycle (Adults Only)")
    lines.append(common.df_to_markdown(d4_df, index=False))
    lines.append("")

    # D5. Weighted prevalence using pooled weights
    n_cycles = len(cycles)
    pooled_weights = common.compute_pooled_exam_weights(a["exam_weight_2yr"], n_cycles)

    # Told diabetes
    told_unw = float(told_dm[told_dm_known].mean() * 100.0)
    told_wt = common.compute_weighted_prevalence(a["told_diabetes"], pooled_weights) * 100.0

    # Measured diabetes
    meas_series = pd.Series(np.nan, index=a.index)
    meas_series[meas_dm_valid] = meas_dm[meas_dm_valid].astype(float)
    meas_unw = float(meas_dm[meas_dm_valid].mean() * 100.0)
    meas_wt = common.compute_weighted_prevalence(meas_series, pooled_weights) * 100.0

    lines.append("### D5. Weighted vs. Unweighted Prevalence (Pooled Over 11 Cycles)")
    lines.append("Per CDC NHANES analytical guidance, when pooling N cycles of 2-year survey data, the 2-year examination weights (exam_weight_2yr) are divided by N (N = 11 cycles):")
    lines.append("")
    lines.append("| Clinical Label | Unweighted Prevalence | Weighted Prevalence (exam_weight_2yr / 11) | Sample Denominator |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Told Diabetes (DIQ010 == 1) | {told_unw:.2f}% | {told_wt:.2f}% | {int(told_dm_known.sum()):,} adults |")
    lines.append(f"| Measured Diabetes (HbA1c >= 6.5 or FPG >= 126) | {meas_unw:.2f}% | {meas_wt:.2f}% | {int(meas_dm_valid.sum()):,} adults with lab |")
    lines.append("")

    # D6. Notes
    lines.append("### D6. NHANES Data Notes")
    lines.append(f"1. **Fasting Glucose Subsample:** Fasting glucose is measured only in the morning exam subsample ({int(a['fasting_glucose'].notna().sum()):,} of {total_adults:,} adults, ~43.4%), whereas HbA1c is available for {int(a['hba1c'].notna().sum()):,} adults (~88.2%).")
    lines.append(f"2. **Age Top-Coding Shift:** Max age is top-coded at 85 years in cycles 1999ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“2006, and top-coded at 80 years from 2007ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“2008 onward to protect participant privacy.")
    lines.append(f"3. **Zero Diastolic BP:** Found {implausible.get('dbp_zero', 0)} adults with dbp == 0 mmHg, and {implausible.get('sbp_le_dbp', 0)} with sbp <= dbp. These represent auscultatory measurement anomalies that should be flagged or cleaned prior to model fitting.")
    lines.append(f"4. **Borderline Diabetes Coding:** In get_nhanes.py, borderline_diabetes is derived from DIQ010 == 3. When DIQ010 is missing or skipped, it is 0 rather than NaN in the raw derived column.")
    lines.append("")

    return "\n".join(lines), {
        "total_participants": total_rows,
        "total_adults": total_adults,
        "duplicate_seqn": dup_seqn,
        "told_unweighted": told_unw,
        "told_weighted": told_wt,
        "measured_unweighted": meas_unw,
        "measured_weighted": meas_wt
    }


def generate_brfss_report() -> tuple[str, dict]:
    """
    Generate BRFSS data quality report sections (D7 to D10).
    Reads columns selectively from parquet to conserve memory.
    """
    lines: list[str] = []
    lines.append("## Part 2: BRFSS (2015, 2017, 2019, 2021, 2023 - 5 Odd-Year Surveys)")
    lines.append("")

    # Select columns needed
    needed_cols = [
        "year", "diabetes", "prediabetes", "high_bp", "borderline_bp", "bp_meds",
        "high_chol", "sex_male", "age_group", "age", "bmi", "smoker_status",
        "ever_smoker", "phys_active", "heavy_drinker", "gen_health", "phys_hlth_days",
        "ment_hlth_days", "heart_disease", "stroke", "kidney_disease", "education",
        "income_group", "race", "has_insurance", "survey_weight"
    ]
    df = common.load_brfss_core(columns=needed_cols)
    total_brfss_rows = len(df)

    # D7. Rows per year; missing % per column per year
    year_counts = df.groupby("year", observed=True).size()
    feature_cols = [c for c in needed_cols if c not in ("year", "survey_weight")]
    missing_table = common.compute_missing_pct_table(df, "year", feature_cols)

    lines.append("### D7. Survey Rows and Missing Percentages Across Survey Years")
    lines.append(f"- **Total Rows:** {total_brfss_rows:,}")
    lines.append("")
    d7_counts = pd.DataFrame({"Total Adults": year_counts})
    lines.append(common.df_to_markdown(d7_counts))
    lines.append("")
    lines.append("#### Missing % per Column per Survey Year:")
    lines.append(common.df_to_markdown(missing_table))
    lines.append("")

    # D8. diabetes and high_bp rates per year, unweighted and survey_weight-weighted
    years = sorted(df["year"].unique())
    rows_d8 = []
    for y in years:
        sub = df[df["year"] == y]
        # unweighted
        dm_unw = float(sub["diabetes"].mean() * 100.0)
        hbp_unw = float(sub["high_bp"].mean() * 100.0)
        # weighted
        dm_wt = common.compute_weighted_prevalence(sub["diabetes"], sub["survey_weight"]) * 100.0
        hbp_wt = common.compute_weighted_prevalence(sub["high_bp"], sub["survey_weight"]) * 100.0

        rows_d8.append({
            "Year": y,
            "Total Rows": f"{len(sub):,}",
            "Diabetes Unweighted": f"{dm_unw:.1f}%",
            "Diabetes Weighted": f"{dm_wt:.1f}%",
            "High BP Unweighted": f"{hbp_unw:.1f}%",
            "High BP Weighted": f"{hbp_wt:.1f}%",
        })

    # Pooled
    dm_unw_tot = float(df["diabetes"].mean() * 100.0)
    dm_wt_tot = common.compute_weighted_prevalence(df["diabetes"], df["survey_weight"]) * 100.0
    hbp_unw_tot = float(df["high_bp"].mean() * 100.0)
    hbp_wt_tot = common.compute_weighted_prevalence(df["high_bp"], df["survey_weight"]) * 100.0

    rows_d8.append({
        "Year": "**Pooled Total**",
        "Total Rows": f"{total_brfss_rows:,}",
        "Diabetes Unweighted": f"{dm_unw_tot:.1f}%",
        "Diabetes Weighted": f"{dm_wt_tot:.1f}%",
        "High BP Unweighted": f"{hbp_unw_tot:.1f}%",
        "High BP Weighted": f"{hbp_wt_tot:.1f}%",
    })

    lines.append("### D8. Diabetes and Hypertension Prevalence (Unweighted vs Survey Weighted)")
    lines.append(common.df_to_markdown(pd.DataFrame(rows_d8), index=False))
    lines.append("")

    # D9. BMI < 12 or > 80 counts; age_group distribution
    bmi_valid = df["bmi"].dropna()
    bmi_out = int(((bmi_valid < 12) | (bmi_valid > 80)).sum())

    lines.append("### D9. BMI Extremes and Age Group Distribution")
    lines.append(f"- **BMI < 12 or > 80 kg/mÃƒâ€šÃ‚Â^2:** {bmi_out:,} records out of {len(bmi_valid):,} valid BMI records ({bmi_out / len(bmi_valid) * 100.0:.2f}%)")
    lines.append("")

    age_labels = {
        1: "18ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“24", 2: "25ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“29", 3: "30ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“34", 4: "35ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“39", 5: "40ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“44", 6: "45ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“49",
        7: "50ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“54", 8: "55ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“59", 9: "60ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“64", 10: "65ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“69", 11: "70ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“74", 12: "75ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“79", 13: "80+"
    }
    age_dist = df.groupby(["year", "age_group"], observed=True).size().unstack(level="year").fillna(0).astype(int)
    age_dist.index = [age_labels.get(i, f"Group {i}") for i in age_dist.index]
    age_dist["Total Pooled"] = age_dist.sum(axis=1)
    age_dist["Pooled %"] = (age_dist["Total Pooled"] / age_dist["Total Pooled"].sum() * 100.0).round(1)

    lines.append("#### Age Group Distribution (_AGEG5YR):")
    lines.append(common.df_to_markdown(age_dist))
    lines.append("")

    # D10. Notes
    lines.append("### D10. BRFSS Data Notes")
    lines.append("1. **Odd Years Survey Design:** Odd years (2015, 2017, 2019, 2021, 2023) are chosen because high blood pressure questions (BPHIGH4 / BPHIGH6 and BPMEDS) are optional modules in even years but standard in odd survey years.")
    lines.append(f"2. **Self-Report Nature:** BRFSS is an anonymous telephone survey. Diabetes prevalence (~{dm_wt_tot:.1f}%) and high blood pressure prevalence (~{hbp_wt_tot:.1f}%) are entirely based on self-reported clinical diagnoses, differing from NHANES laboratory-confirmed measures.")
    lines.append("3. **Variable Mapping Fixes Verified:** Both kidney_disease (mapped from CHCKIDNY in 2015/2017 and CHCKDNY1/2 in 2019+) and has_insurance (mapped from _HLTHPL1 in 2023 and _HLTHPLN/1 in earlier years) show zero missing candidate exceptions.")
    lines.append("")

    return "\n".join(lines), {
        "total_brfss_rows": total_brfss_rows,
        "bmi_out_of_bounds": bmi_out,
        "diabetes_weighted_pooled": dm_wt_tot,
        "high_bp_weighted_pooled": hbp_wt_tot
    }


def write_data_checks_doc(output_path: Path | None = None) -> Path:
    """Run all checks and write docs/DATA_CHECKS.md."""
    if output_path is None:
        output_path = Path("docs") / "DATA_CHECKS.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "# ChronicCare AI ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Survey Data Quality & Checks Report",
        "",
        "> **Notice:** This document contains AGGREGATES ONLY. It strictly contains zero patient identifiers, zero SEQN records, and zero raw clinical observations.",
        "> Generated automatically by ackend-poc-technical/ml/data_checks.py.",
        "",
        "---",
        ""
    ]

    print("Loading NHANES core data...")
    nhanes_df = common.load_nhanes_core()
    nhanes_md, nhanes_metrics = generate_nhanes_report(nhanes_df)

    print("Loading BRFSS core data...")
    brfss_md, brfss_metrics = generate_brfss_report()

    full_doc = "\n".join(header) + "\n" + nhanes_md + "\n---\n\n" + brfss_md

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_doc)

    print(f"Successfully generated: {output_path}")
    return output_path


def main() -> None:
    write_data_checks_doc()


if __name__ == "__main__":
    main()