from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent / "data"

DEMO_FILE = DATA_DIR / "DEMO_L.xpt"
BMX_FILE = DATA_DIR / "BMX_L.xpt"
DIQ_FILE = DATA_DIR / "DIQ_L.xpt"


def load_nhanes_data():
    required_files = [DEMO_FILE, BMX_FILE, DIQ_FILE]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required NHANES file not found: {file_path}"
            )

    demo = pd.read_sas(DEMO_FILE, format="xport")
    bmx = pd.read_sas(BMX_FILE, format="xport")
    diq = pd.read_sas(DIQ_FILE, format="xport")

    merged = demo.merge(
        bmx[["SEQN", "BMXBMI"]],
        on="SEQN",
        how="inner",
    )

    merged = merged.merge(
        diq[["SEQN", "DIQ010"]],
        on="SEQN",
        how="inner",
    )

    dataset = merged[
        ["SEQN", "RIDAGEYR", "RIAGENDR", "BMXBMI", "DIQ010"]
    ].copy()

    dataset = dataset.rename(
        columns={
            "RIDAGEYR": "age",
            "RIAGENDR": "sex",
            "BMXBMI": "bmi",
            "DIQ010": "diabetes_response",
        }
    )

    # NHANES DIQ010:
    # 1 = Yes
    # 2 = No
    # 3 = Borderline
    #
    # For this simple baseline, keep only definite Yes/No responses.
    dataset = dataset[
        dataset["diabetes_response"].isin([1.0, 2.0])
    ].copy()

    dataset["diabetes"] = (
        dataset["diabetes_response"] == 1.0
    ).astype(int)

    dataset = dataset.dropna(
        subset=["age", "sex", "bmi", "diabetes"]
    )
    # ChronicCare AI is designed for adult patients.
    dataset = dataset[dataset["age"] >= 18].copy()

    dataset = dataset[
        ["SEQN", "age", "sex", "bmi", "diabetes"]
    ].reset_index(drop=True)

    return dataset


if __name__ == "__main__":
    data = load_nhanes_data()

    print(f"Rows loaded: {len(data)}")
    print()
    print(data.head())
    print()
    print("Diabetes target counts:")
    print(data["diabetes"].value_counts())