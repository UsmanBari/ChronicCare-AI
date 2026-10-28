# ChronicCare AI — ML Data Preparation

This directory contains the reproducible preparation scripts for the public survey datasets used across ChronicCare AI risk models and validation studies:
- **NHANES** (National Health and Nutrition Examination Survey, CDC): 1999–2023 (11 continuous 2-year cycles).
- **BRFSS** (Behavioral Risk Factor Surveillance System, CDC): 2015, 2017, 2019, 2021, 2023 (odd years).

## 1. Environment Configuration

All raw and processed survey data files reside outside the repository to prevent accidental tracking of gigabyte-scale datasets. Before running any script, set CHRONICCARE_DATA_DIR:

`powershell
# Set permanently for your user account:
[Environment]::SetEnvironmentVariable("CHRONICCARE_DATA_DIR", "C:\Users\<user>\Desktop\Chronicare-data", "User")

# Set in your current PowerShell session:
$env:CHRONICCARE_DATA_DIR = "C:\Users\<user>\Desktop\Chronicare-data"
`

The data directory layout must match:
`	ext
$env:CHRONICCARE_DATA_DIR\
  ├── get_nhanes.py
  ├── get_brfss.py
  ├── nhanes\
  │     ├── nhanes_core.csv
  │     ├── nhanes_full.parquet
  │     └── raw\<cycle>\*.xpt (11 cycles)
  ├── brfss\
  │     ├── brfss_core.parquet
  │     ├── brfss_core_sample.csv
  │     └── zips\LLCP20xxXPT.zip (5 files)
  ├── brfss2015_kaggle\
  ├── cardio70k\
  ├── framingham\
  └── pima\
`

## 2. NHANES Data Acquisition & Ingestion (get_nhanes.py)

- **Execution:**
  `powershell
  python backend-poc-technical/ml/data_prep/get_nhanes.py
  `
- **Cycles Processed:** 11 two-year cycles from 1999–2000 through 2021–2023.
- **Cycle Note:** The 2019–2020 cycle was suspended in March 2020 due to COVID-19 and was not released independently; CDC combined it into the 2017–March 2020 pre-pandemic file, which partially overlaps with 2017–2018. To maintain non-overlapping 2-year survey periods with clean survey weights, 2017–March 2020 is skipped, and standard consecutive cycles are utilized.
- **Runtime:** ~10–20 minutes on first download; if raw files exist in 
hanes/raw/, downloads are skipped and core tables are rebuilt deterministically.
- **Expected Outputs:**
  - 
hanes/nhanes_core.csv: 25 core clinical columns (demographics, examination, laboratory, questionnaires, weights).
  - 
hanes/nhanes_full.parquet: unpruned merged frame.
- **Expected Counts:**
  - Total participants: 113,249
  - Adults (age ≥ 18): 67,357
  - Adults with HbA1c: 59,412
  - Adults with measured BP: 60,000
  - Adults with fasting glucose: 29,218

## 3. BRFSS Data Acquisition & Processing (get_brfss.py)

- **Browser Download Required:** CDC servers return HTTP 403 Forbidden to automated python script downloads. Download the 5 odd-year zip files in a web browser directly into $env:CHRONICCARE_DATA_DIR/brfss/zips/:
  - 2015: https://www.cdc.gov/brfss/annual_data/2015/files/LLCP2015XPT.zip
  - 2017: https://www.cdc.gov/brfss/annual_data/2017/files/LLCP2017XPT.zip
  - 2019: https://www.cdc.gov/brfss/annual_data/2019/files/LLCP2019XPT.zip
  - 2021: https://www.cdc.gov/brfss/annual_data/2021/files/LLCP2021XPT.zip
  - 2023: https://www.cdc.gov/brfss/annual_data/2023/files/LLCP2023XPT.zip
  *(Odd years only are chosen because the hypertension/high-BP questions are surveyed in odd years).*

- **Execution:**
  `powershell
  python backend-poc-technical/ml/data_prep/get_brfss.py
  `
- **Candidate Variable Resolution:**
  - kidney_disease: CDC renamed the variable across cycles (CHCKIDNY in 2015/2017; CHCKDNY1/CHCKDNY2 in 2019–2023).
  - has_insurance: CDC updated the calculated insurance flag to _HLTHPL1 in 2023 (_HLTHPLN / _HLTHPLN1 in earlier years).
- **Expected Outputs:**
  - rfss/brfss_core.parquet: cleaned multi-year analytical dataset.
  - rfss/brfss_core_sample.csv: 1,000-row preview sample.
- **Expected Total Rows:** 2,181,756 adults across the 5 odd-year surveys.