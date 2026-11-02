"""
Download BRFSS (CDC telephone survey, ~400k adults per year) and build one
combined, cleaned file.

Years: 2015, 2017, 2019, 2021, 2023 (odd years = the years the high blood
pressure questions are asked; diabetes is asked every year).

Run locally from your dataset folder:
    python get_brfss.py

Output (in ./brfss/):
    zips/LLCPyyyyXPT.zip     original CDC downloads (kept, so re-runs skip them)
    brfss_core.parquet       ~2 million rows, cleaned columns, all years
    brfss_core_sample.csv    50k random rows as CSV, to open/inspect easily

Each zip is ~60-120 MB; the full XPT inside is ~1 GB, so the script reads it
in chunks and keeps only the columns we need (low RAM use). The unzipped XPT
is deleted after each year. Safe to re-run.
"""
import sys
import os
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

YEARS = [2015, 2017, 2019, 2021, 2023]
URL = "https://www.cdc.gov/brfss/annual_data/{y}/files/LLCP{y}XPT.zip"
data_dir_env = os.environ.get("CHRONICCARE_DATA_DIR")
if not data_dir_env:
    print("ERROR: CHRONICCARE_DATA_DIR is not set.", file=sys.stderr)
    sys.exit(1)
OUT = Path(data_dir_env) / "brfss"
ZIPS = OUT / "zips"

# Variable names change across years -> list every known name, first found wins.
CANDIDATES = {
    "diabetes_raw":   ["DIABETE4", "DIABETE3"],
    "high_bp_raw":    ["BPHIGH6", "BPHIGH4"],
    "bp_meds_raw":    ["BPMEDS1", "BPMEDS"],
    "high_chol_raw":  ["TOLDHI3", "TOLDHI2"],
    "sex_raw":        ["_SEX", "SEXVAR", "SEX1", "SEX"],
    "age_group":      ["_AGEG5YR"],
    "age_80":         ["_AGE80"],
    "bmi_x100":       ["_BMI5"],
    "smoker_status":  ["_SMOKER3"],
    "phys_active":    ["_TOTINDA"],
    "heavy_drinker":  ["_RFDRHV8", "_RFDRHV7", "_RFDRHV6", "_RFDRHV5"],
    "gen_health":     ["GENHLTH"],
    "phys_hlth_days": ["PHYSHLTH"],
    "ment_hlth_days": ["MENTHLTH"],
    "heart_disease":  ["CVDCRHD4"],
    "stroke":         ["CVDSTRK3"],
    "kidney_disease": ["CHCKDNY2", "CHCKDNY1", "CHCKIDNY"],
    "education":      ["_EDUCAG"],
    "income_group":   ["_INCOMG1", "_INCOMG"],
    "race":           ["_IMPRACE", "_RACE"],
    "has_insurance":  ["_HLTHPLN", "_HLTHPLN1", "HLTHPLN1", "_HLTHPL1"],
    "weight_final":   ["_LLCPWT"],
}


def download(year: int) -> Path:
    ZIPS.mkdir(parents=True, exist_ok=True)
    dest = ZIPS / f"LLCP{year}XPT.zip"
    if dest.exists() and zipfile.is_zipfile(dest):
        print(f"  zip already here ({dest.stat().st_size // 2**20} MB)")
        return dest

    url = URL.format(y=year)
    tmp = dest.with_suffix(".part")
    for attempt in range(1, 4):
        try:
            with requests.get(url, stream=True, timeout=120,
                              headers={"User-Agent": "Mozilla/5.0"}) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                done, t0 = 0, time.time()
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            sys.stdout.write(
                                f"\r  downloading {done // 2**20}/{total // 2**20} MB "
                                f"({done / max(time.time() - t0, 1) / 2**20:.1f} MB/s)")
                            sys.stdout.flush()
            print()
            tmp.replace(dest)
            if zipfile.is_zipfile(dest):
                return dest
            dest.unlink()
            raise RuntimeError("downloaded file is not a zip (CDC sent an error page?)")
        except Exception as e:  # noqa: BLE001
            print(f"\n  attempt {attempt} failed: {e}")
            time.sleep(5)
    raise SystemExit(f"Could not download {url}. Open it in a browser to check.")


def read_needed_columns(zpath: Path, year: int) -> pd.DataFrame:
    with zipfile.ZipFile(zpath) as z:
        # CDC's XPT names sometimes have a trailing space ("LLCP2015.XPT ")
        member = next(n for n in z.namelist() if n.strip().upper().endswith(".XPT"))
        xpt = OUT / f"_tmp_{year}.xpt"
        with z.open(member) as src, xpt.open("wb") as dst:
            while chunk := src.read(1 << 22):
                dst.write(chunk)

    parts, keep, found = [], None, {}
    reader = pd.read_sas(xpt, format="xport", chunksize=50_000)
    for chunk in reader:
        if keep is None:
            cols = set(chunk.columns)
            for new, options in CANDIDATES.items():
                hit = next((c for c in options if c in cols), None)
                if hit:
                    found[new] = hit
            keep = list(found.values())
            missing = [k for k in CANDIDATES if k not in found]
            if missing:
                print(f"  not in {year}: {', '.join(missing)}")
        parts.append(chunk[keep].rename(columns={v: k for k, v in found.items()}))
        sys.stdout.write(f"\r  reading rows: {sum(len(p) for p in parts):,}")
        sys.stdout.flush()
    print()
    reader.close()
    xpt.unlink()

    df = pd.concat(parts, ignore_index=True)
    for k in CANDIDATES:
        if k not in df.columns:
            df[k] = np.nan
    df.insert(0, "year", year)
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"year": df["year"]})

    # Diabetes: 1 yes, 2 only in pregnancy, 3 no, 4 prediabetes/borderline
    d = df["diabetes_raw"]
    out["diabetes"] = d.map({1: 1, 2: 0, 3: 0, 4: 0})
    out["prediabetes"] = d.map({1: 0, 2: 0, 3: 0, 4: 1})
    out["diabetes_3class"] = d.map({3: 0, 2: 0, 4: 1, 1: 2})  # 0 none, 1 pre, 2 diabetes

    # High BP: 1 yes, 2 only in pregnancy, 3 no, 4 borderline
    b = df["high_bp_raw"]
    out["high_bp"] = b.map({1: 1, 2: 0, 3: 0, 4: 0})
    out["borderline_bp"] = b.map({1: 0, 2: 0, 3: 0, 4: 1})
    out["bp_meds"] = df["bp_meds_raw"].map({1: 1, 2: 0})
    out["high_chol"] = df["high_chol_raw"].map({1: 1, 2: 0})

    out["sex_male"] = df["sex_raw"].map({1: 1, 2: 0})
    out["age_group"] = df["age_group"].where(df["age_group"].between(1, 13))  # 1=18-24 ... 13=80+
    out["age"] = df["age_80"]
    out["bmi"] = df["bmi_x100"] / 100
    out["smoker_status"] = df["smoker_status"].where(df["smoker_status"].between(1, 4))
    out["ever_smoker"] = df["smoker_status"].map({1: 1, 2: 1, 3: 1, 4: 0})
    out["phys_active"] = df["phys_active"].map({1: 1, 2: 0})
    out["heavy_drinker"] = df["heavy_drinker"].map({1: 0, 2: 1})
    out["gen_health"] = df["gen_health"].where(df["gen_health"].between(1, 5))
    for k in ("phys_hlth_days", "ment_hlth_days"):  # 88 = none, 77/99 = unknown
        out[k] = df[k].replace(88, 0).where(lambda s: s.between(0, 30))
    out["heart_disease"] = df["heart_disease"].map({1: 1, 2: 0})
    out["stroke"] = df["stroke"].map({1: 1, 2: 0})
    out["kidney_disease"] = df["kidney_disease"].map({1: 1, 2: 0})
    out["education"] = df["education"].where(df["education"].between(1, 4))
    out["income_group"] = df["income_group"].where(df["income_group"].between(1, 7))
    out["race"] = df["race"]
    out["has_insurance"] = df["has_insurance"].map({1: 1, 2: 0})
    out["survey_weight"] = df["weight_final"]
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    frames = []
    for y in YEARS:
        print(f"\n{y}")
        z = download(y)
        raw = read_needed_columns(z, y)
        frames.append(clean(raw))
        print(f"  -> {len(raw):,} rows")

    core = pd.concat(frames, ignore_index=True)
    core.to_parquet(OUT / "brfss_core.parquet", index=False)
    core.sample(min(50_000, len(core)), random_state=0).to_csv(
        OUT / "brfss_core_sample.csv", index=False)

    print("\n================ SUMMARY ================")
    print(f"Total rows: {len(core):,}")
    print(core.groupby("year").agg(
        rows=("year", "size"),
        diabetes_known=("diabetes", "count"),
        diabetes_rate=("diabetes", "mean"),
        high_bp_known=("high_bp", "count"),
        high_bp_rate=("high_bp", "mean"),
        bmi_known=("bmi", "count"),
    ).round(3).to_string())
    print(f"\nSaved: {OUT / 'brfss_core.parquet'} (+ 50k-row CSV sample)")


if __name__ == "__main__":
    main()
