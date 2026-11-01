"""
Demographic and Health Surveys (DHS) Dataset Loader Skeleton.

DHS household-member (PR) recode files usually hold the biomarker measurements
(blood pressure, blood glucose, anthropometry); confirm this from the dataset's
documentation on arrival.

Supported countries:
- india_nfhs5: India National Family Health Survey 5 (2019-2021)
- bangladesh_2017: Bangladesh Demographic and Health Survey 2017-2018
- nepal_2022: Nepal Demographic and Health Survey 2022

Note:
DHS microdata files are restricted and distributed through the DHS Program
authorization portal (often in Stata .dta, SPSS .sav, or SAS format).
When microdata files are unavailable, DhsDataNotAvailable is raised.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pandas as pd
from ml.common import data_dir

DhsCountry = Literal["india_nfhs5", "bangladesh_2017", "nepal_2022"]

SUPPORTED_COUNTRIES: tuple[str, ...] = ("india_nfhs5", "bangladesh_2017", "nepal_2022")


class DhsDataNotAvailable(FileNotFoundError):
    """Raised when DHS microdata files are not present in the local filesystem."""


# Every variable code is explicitly marked TO CONFIRM per project instructions
EXPECTED_VARIABLES: dict[str, dict[str, str]] = {
    "sbp1": {
        "description": "First systolic blood pressure reading (mmHg)",
        "code": "sh011 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "sbp2": {
        "description": "Second systolic blood pressure reading (mmHg)",
        "code": "sh013 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "sbp3": {
        "description": "Third systolic blood pressure reading (mmHg)",
        "code": "sh015 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "dbp1": {
        "description": "First diastolic blood pressure reading (mmHg)",
        "code": "sh012 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "dbp2": {
        "description": "Second diastolic blood pressure reading (mmHg)",
        "code": "sh014 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "dbp3": {
        "description": "Third diastolic blood pressure reading (mmHg)",
        "code": "sh016 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "random_glucose": {
        "description": "Random blood glucose measurement (mg/dL)",
        "code": "shb21 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "fasting_glucose": {
        "description": "Fasting blood glucose measurement (mg/dL)",
        "code": "shb22 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "age": {
        "description": "Respondent age in completed single years",
        "code": "ha1 / hv105 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "sex": {
        "description": "Respondent sex (1=Male, 2=Female)",
        "code": "hv104 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "height": {
        "description": "Height in centimeters",
        "code": "ha3 / hb3 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "weight": {
        "description": "Weight in kilograms",
        "code": "ha2 / hb2 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
    "current_bp_medication": {
        "description": "Currently taking medication for high blood pressure",
        "code": "sh019 [TO CONFIRM against the DHS recode manual when the files arrive]",
    },
}


def load_dhs(
    country: DhsCountry | str,
    path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Load and parse DHS Stata dataset (.dta).

    Raises
    ------
    ValueError
        If country is not one of the supported countries.
    DhsDataNotAvailable
        If the data file does not exist on disk.
    """
    if country not in SUPPORTED_COUNTRIES:
        raise ValueError(
            f"Unsupported DHS country '{country}'. Supported countries: {list(SUPPORTED_COUNTRIES)}"
        )

    if path is not None:
        target_path = Path(path)
    else:
        try:
            target_path = data_dir() / "dhs" / country / f"{country}.dta"
        except RuntimeError:
            raise DhsDataNotAvailable(
                f"DHS dataset for '{country}' not found (CHRONICCARE_DATA_DIR environment variable is not set). "
                "DHS data requires authorized access from https://dhsprogram.com. "
                "Please obtain approved microdata and place the .dta file at the expected location."
            )

    if not target_path.exists():
        raise DhsDataNotAvailable(
            f"DHS dataset for '{country}' not found at {target_path}. "
            "DHS data requires authorized access from https://dhsprogram.com. "
            "Please obtain approved microdata and place the .dta file at the expected location."
        )

    # When file is present, load via pandas.read_stata
    df = pd.read_stata(target_path)
    report = {
        "dataset": f"dhs_{country}",
        "total_rows": len(df),
        "variables_present": [c for c in EXPECTED_VARIABLES if c in df.columns],
        "variables_expected": list(EXPECTED_VARIABLES.keys()),
    }
    return df, report

