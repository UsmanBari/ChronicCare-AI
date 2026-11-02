"""
Download NHANES 1999-2023 (10 cycles) and build one combined file.

Run locally from your dataset folder:
    pip install pandas requests pyarrow
    python get_nhanes.py

Output (in ./nhanes/):
    raw/<cycle>/*.xpt        original CDC files (kept, so re-runs skip downloads)
    nhanes_core.csv          one row per participant, cleaned key columns, all cycles
    nhanes_full.parquet      every column from every file, all cycles (for later)

Safe to re-run: files already downloaded are skipped.
"""
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{table}.xpt"
data_dir_env = os.environ.get("CHRONICCARE_DATA_DIR")
if not data_dir_env:
    print("ERROR: CHRONICCARE_DATA_DIR is not set.", file=sys.stderr)
    sys.exit(1)
OUT = Path(data_dir_env) / "nhanes"
RAW = OUT / "raw"

# cycle label -> (folder year on CDC site, file suffix)
CYCLES = {
    "1999-2000": ("1999", ""),
    "2001-2002": ("2001", "_B"),
    "2003-2004": ("2003", "_C"),
    "2005-2006": ("2005", "_D"),
    "2007-2008": ("2007", "_E"),
    "2009-2010": ("2009", "_F"),
    "2011-2012": ("2011", "_G"),
    "2013-2014": ("2013", "_H"),
    "2015-2016": ("2015", "_I"),
    "2017-2018": ("2017", "_J"),
    "2021-2023": ("2021", "_L"),
}
# 2019-2020 was never released on its own (COVID); its data sits inside the
# 2017-March 2020 "P_" files, which overlap 2017-2018, so we skip it.

# Lab files had different names in the first three cycles.
OLD_LAB = {
    "1999-2000": {"GHB": "LAB10", "GLU": "LAB10AM", "TCHOL": "LAB13"},
    "2001-2002": {"GHB": "L10_B", "GLU": "L10AM_B", "TCHOL": "L13_B"},
    "2003-2004": {"GHB": "L10_C", "GLU": "L10AM_C", "TCHOL": "L13_C"},
}

# What each file gives us
TABLES = [
    "DEMO",   # age, sex, race, income, survey weights
    "BMX",    # height, weight, BMI, waist
    "BPX",    # blood pressure (manual cuff), up to 2017-2018
    "BPXO",   # blood pressure (automatic cuff), 2017-2018 and 2021-2023
    "GHB",    # HbA1c
    "GLU",    # fasting glucose (fasting subsample only)
    "TCHOL",  # total cholesterol
    "DIQ",    # "doctor told you have diabetes", diabetes meds
    "BPQ",    # "doctor told you have high BP", BP meds
    "MCQ",    # medical history incl. family history of diabetes
    "SMQ",    # smoking
]


def file_name(cycle: str, table: str) -> str:
    if cycle in OLD_LAB and table in OLD_LAB[cycle]:
        return OLD_LAB[cycle][table]
    return table + CYCLES[cycle][1]


def download(cycle: str, table: str, session: requests.Session) -> Path | None:
    year = CYCLES[cycle][0]
    name = file_name(cycle, table)
    dest = RAW / cycle / f"{name}.xpt"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    for ext in ("xpt", "XPT"):
        url = BASE.format(year=year, table=name).replace(".xpt", f".{ext}")
        for attempt in range(3):
            try:
                r = session.get(url, timeout=120)
            except requests.RequestException:
                time.sleep(3)
                continue
            # CDC returns an HTML page (not a 404) for missing files
            if r.status_code == 200 and not r.content[:200].lstrip().lower().startswith(b"<"):
                dest.write_bytes(r.content)
                print(f"  OK   {cycle} {name} ({len(r.content) // 1024} KB)")
                return dest
            break  # 404 / HTML page: try the other extension
    print(f"  --   {cycle} {name} not available (normal for some cycles)")
    return None


def load_cycle(cycle: str, session: requests.Session) -> pd.DataFrame | None:
    merged = None
    for table in TABLES:
        path = download(cycle, table, session)
        if path is None:
            continue
        df = pd.read_sas(path, format="xport")
        df["SEQN"] = df["SEQN"].astype("int64")
        # BPX and BPXO share some column names; prefix BPXO to keep both
        if table == "BPXO":
            df = df.rename(columns={c: f"O_{c}" for c in df.columns if c != "SEQN"})
        if merged is None:
            merged = df
        else:
            dup = [c for c in df.columns if c in merged.columns and c != "SEQN"]
            merged = merged.merge(df.drop(columns=dup), on="SEQN", how="left")
    if merged is not None:
        merged.insert(0, "cycle", cycle)
    return merged


def row_mean(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    have = [c for c in cols if c in df.columns]
    if not have:
        return pd.Series(np.nan, index=df.index)
    vals = df[have].where(df[have] > 0)  # 0 = reading not taken
    return vals.mean(axis=1)


def first_col(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    out = pd.Series(np.nan, index=df.index)
    for c in cols:
        if c in df.columns:
            out = out.fillna(df[c])
    return out


def col(df: pd.DataFrame, name: str) -> pd.Series:
    return df[name] if name in df.columns else pd.Series(np.nan, index=df.index)


def yes_no(s: pd.Series) -> pd.Series:
    """NHANES coding: 1 = yes, 2 = no, 7/9 = refused/don't know -> NaN."""
    return s.map({1: 1, 2: 0})


def build_core(full: pd.DataFrame) -> pd.DataFrame:
    core = pd.DataFrame({
        "seqn": full["SEQN"],
        "cycle": full["cycle"],
        "age": col(full, "RIDAGEYR"),
        "sex_male": col(full, "RIAGENDR").map({1: 1, 2: 0}),
        "race_eth": col(full, "RIDRETH1"),
        "income_poverty_ratio": col(full, "INDFMPIR"),
        "bmi": col(full, "BMXBMI"),
        "waist_cm": col(full, "BMXWAIST"),
        "height_cm": col(full, "BMXHT"),
        "weight_kg": col(full, "BMXWT"),
        # BP: manual cuff where available, else automatic cuff
        "sbp": row_mean(full, ["BPXSY1", "BPXSY2", "BPXSY3", "BPXSY4"]).fillna(
            row_mean(full, ["O_BPXOSY1", "O_BPXOSY2", "O_BPXOSY3"])),
        "dbp": row_mean(full, ["BPXDI1", "BPXDI2", "BPXDI3", "BPXDI4"]).fillna(
            row_mean(full, ["O_BPXODI1", "O_BPXODI2", "O_BPXODI3"])),
        "pulse": first_col(full, ["BPXPLS", "O_BPXOPLS1"]),
        "hba1c": col(full, "LBXGH"),
        "fasting_glucose": col(full, "LBXGLU"),
        "total_chol": col(full, "LBXTC"),
        "told_diabetes": yes_no(col(full, "DIQ010")),
        "takes_insulin": yes_no(col(full, "DIQ050")),
        "takes_diabetes_pills": yes_no(col(full, "DIQ070")),
        "told_high_bp": yes_no(col(full, "BPQ020")),
        "takes_bp_meds": yes_no(first_col(full, ["BPQ050A", "BPQ150"])),
        "family_hx_diabetes": yes_no(col(full, "MCQ300C")),
        "ever_smoked_100": yes_no(col(full, "SMQ020")),
        "exam_weight_2yr": col(full, "WTMEC2YR"),
    })
    # DIQ010 == 3 means "borderline"; keep it as its own flag
    core["borderline_diabetes"] = (col(full, "DIQ010") == 3).astype(int)
    return core


def main() -> None:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (nhanes-download script)"
    frames = []
    for cycle in CYCLES:
        print(f"\n{cycle}")
        df = load_cycle(cycle, session)
        if df is not None:
            frames.append(df)
            print(f"  -> {len(df):,} participants, {df.shape[1]} columns")

    full = pd.concat(frames, ignore_index=True, sort=False)
    OUT.mkdir(exist_ok=True)
    full.to_parquet(OUT / "nhanes_full.parquet", index=False)

    core = build_core(full)
    core.to_csv(OUT / "nhanes_core.csv", index=False)

    adults = core[core["age"] >= 18]
    print("\n================ SUMMARY ================")
    print(f"All participants:          {len(core):,}")
    print(f"Adults (18+):              {len(adults):,}")
    print(f"Adults with HbA1c:         {adults['hba1c'].notna().sum():,}")
    print(f"Adults with BP readings:   {adults['sbp'].notna().sum():,}")
    print(f"Adults with fasting gluc:  {adults['fasting_glucose'].notna().sum():,}")
    print("\nPer cycle (adults with HbA1c / BP):")
    print(adults.groupby("cycle")[["hba1c", "sbp"]].count().to_string())
    print(f"\nSaved: {OUT / 'nhanes_core.csv'} and {OUT / 'nhanes_full.parquet'}")


if __name__ == "__main__":
    main()
