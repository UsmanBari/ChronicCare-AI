# MIMIC-IV Trend Sanity Evaluation

> **CRITICAL EXECUTION NOTICE:**  
> **Run this yourself in a normal PowerShell window, NOT inside Antigravity or any AI tool. Paste only the printed summary into the PR.**

---

## Overview

This tool (`backend-poc-technical/ml/mimic/trend_sanity.py`) evaluates ChronicCare-AI's deterministic clinical trend detection agent (`agents.trend_agent.compute_trends`) across outpatient and hospital longitudinal blood pressure observations from the MIMIC-IV clinical database (`omr.csv`).

## Privacy & Safety Requirements

1. **Local-Only Execution**: MIMIC-IV is credentialed health data governed by a Data Use Agreement (DUA). Never upload or feed MIMIC data to any AI assistant, web service, or git repository.
2. **In-Repo Refusal**: The script refuses to run if the `--omr` argument points to any file located within the repository workspace tree.
3. **Aggregated Output Only**: The script emits only summary statistics (distribution percentages, flip rates, median absolute changes, and naive comparison disagreement rates). It never outputs individual patient identifiers (`subject_id`), timestamps, row counts per subject, or raw clinical values.

---

## Instructions

### 1. Prerequisites
Ensure your virtual environment has the required dependencies installed:
```powershell
.\backend-poc-technical\.venv\Scripts\Activate.ps1
pip install pandas
```

### 2. Execution
Run the script pointing to your external MIMIC-IV `omr.csv` file:
```powershell
python backend-poc-technical/ml/mimic/trend_sanity.py --omr "C:\path\to\external\mimic-iv\omr.csv"
```

### 3. Example Output Format
```json
{
  "subjects_with_evaluable_windows": 1420,
  "windows_evaluated": 3890,
  "systolic": {
    "direction_distribution_pct": {
      "rising": 24.5,
      "stable": 51.2,
      "falling": 24.3
    },
    "consecutive_window_flip_rate_pct": 8.4,
    "median_abs_change_mmhg": 6.0,
    "naive_last_minus_first_disagreement_pct": 14.1
  },
  "diastolic": {
    "direction_distribution_pct": {
      "rising": 21.0,
      "stable": 58.5,
      "falling": 20.5
    },
    "consecutive_window_flip_rate_pct": 6.8,
    "median_abs_change_mmhg": 4.0,
    "naive_last_minus_first_disagreement_pct": 12.3
  },
  "parse_failures": 12
}
```

Paste only this printed JSON block into your PR description or evaluation documentation.
