# ChronicCare AI — ML Experiment Harness

This directory contains the declarative experiment harness for training, evaluating, and packaging clinical risk stratification models for adults with type 2 diabetes and hypertension.

## Principles & Guardrails
- **Clinical Safety:** The model proposes, the rules decide. Risk models never diagnose, never alter medications, and can never lower triage levels.
- **Hermetic & CPU-Friendly:** Operates purely on CPU using scikit-learn standard models without requiring GPUs or unpinned packages.
- **Reproducibility:** Runs declaratively from validated JSON configs under `ml/experiments/configs/`.
- **Temporal Integrity:** Evaluates models on held-out future cohorts (`test` 2017–2023) following training on historical participants (`train_core` 1999–2012) and threshold locking on validation (`validation` 2013–2016).

---

## How to Run an Experiment

Set the dataset directory environment variable and run `ml/experiments/run.py` from the repository root:

```powershell
$env:CHRONICCARE_DATA_DIR = "C:\Users\usmanbari\Desktop\Chronicare-data"
$env:PYTHONPATH = "backend-poc-technical"
.\backend-poc-technical\.venv\Scripts\python.exe backend-poc-technical/ml/experiments/run.py --config backend-poc-technical/ml/experiments/configs/diabetes_basic_nhanes.json
```

### Running All 6 Baseline & Screening Experiments:

```powershell
$env:CHRONICCARE_DATA_DIR = "C:\Users\usmanbari\Desktop\Chronicare-data"
$env:PYTHONPATH = "backend-poc-technical"

$configs = @(
    "diabetes_basic_nhanes",
    "diabetes_full_nhanes",
    "htn_basic_nhanes",
    "htn_full_nhanes",
    "diabetes_ref_age_sex_bmi",
    "htn_ref_age_sex_bmi"
)

foreach ($cfg in $configs) {
    Write-Host "Running experiment: $cfg"
    .\backend-poc-technical\.venv\Scripts\python.exe backend-poc-technical/ml/experiments/run.py --config "backend-poc-technical/ml/experiments/configs/$cfg.json" | Tee-Object -FilePath "$env:CHRONICCARE_DATA_DIR\logs\day4\$cfg.txt"
}
```

---

## Artifact Outputs
- **Model Pipeline:** `backend-poc-technical/ml/outputs/models/<name>/model.joblib`
- **Model Card:** `backend-poc-technical/ml/outputs/models/<name>/model_card.json`
- **Pure-Python Production Export:** `backend-poc-technical/ml/outputs/models/<name>/export.json`
- **Detailed Evaluation Report:** `docs/ml/experiments/<name>.md`
- **Metrics JSON:** `backend-poc-technical/ml/outputs/reports/<name>/metrics.json`
