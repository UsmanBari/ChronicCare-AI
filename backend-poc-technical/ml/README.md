# NHANES Diabetes Baseline Model

## Purpose

This folder contains an experimental baseline machine-learning model for
ChronicCare AI.

The model uses logistic regression to classify self-reported diagnosed
diabetes using selected NHANES variables.

This model is NOT wired into the ChronicCare AI triage system and does not
change any triage level.

## Data Source

The data comes from the National Health and Nutrition Examination Survey
(NHANES), August 2021-August 2023 release.

NHANES is a public United States survey conducted by the National Center for
Health Statistics (NCHS), part of the CDC.

The following local SAS Transport (XPT) files are used:

- DEMO_L.xpt - Demographics data
- BMX_L.xpt - Body Measures examination data
- DIQ_L.xpt - Diabetes questionnaire data

NHANES data page:
https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Cycle=2021-2023

The XPT files are stored locally in `ml/data/`.
The `ml/data/` directory is excluded from Git and the raw NHANES data must
not be committed to this repository.

## Variables

The baseline uses three input features:

- `RIDAGEYR` -> age in years
- `RIAGENDR` -> sex code from NHANES
- `BMXBMI` -> body mass index

The target is derived from:

- `DIQ010` -> whether the participant was told by a health professional that
  they have diabetes

Only definite Yes/No DIQ010 responses are retained for this baseline.

Because ChronicCare AI is intended for adults, records with age below 18 are
excluded.

After filtering missing values, definite diabetes responses, and participants
below age 18, 6,014 records were available:

- No diabetes: 5,169
- Diabetes: 845

## Model

The baseline model is logistic regression.

The data is split into training and held-out test sets using:

- Test size: 20%
- Random state: 42
- Stratification by diabetes target

The input features are standardized using `StandardScaler`.

Training rows: 4,811

Held-out test rows: 1,203

## Held-Out Results

The observed results from:

`python ml/train_baseline.py`

were:

- AUROC: 0.7507
- Sensitivity: 0.0355 (3.55%)
- Specificity: 0.9923 (99.23%)

These are the actual observed results from the fixed held-out split.

The low sensitivity is an important limitation. At the default probability
threshold of 0.5, the model misses many participants with a positive diabetes
label. The class distribution is also imbalanced.

These results must not be interpreted as evidence of clinical performance.

## SHAP Explanation

`explain.py` uses SHAP to explain the contribution of each input feature for
one held-out patient.

Run:

`python ml/explain.py`

Positive SHAP values push the model output upward and negative SHAP values
push it downward.

SHAP values explain model behavior. They do not establish medical causality.

## Limitations and Safety

This is an experimental educational baseline only.

- The source is public US survey data.
- The target is based on questionnaire-reported diagnosed diabetes rather
  than future diabetes incidence.
- Therefore, this experiment should not be interpreted as a validated
  prospective diabetes-risk model.
- The model has not been clinically validated.
- The model is not a diagnostic tool.
- The evaluation uses a simple held-out split and does not account for the
  full NHANES complex survey design.
- The reported metrics are not population-level clinical performance
  estimates.
- The model currently uses only age, sex, and BMI.
- The observed sensitivity at the default threshold is low.
- Model outputs are advisory only.
- A model output may only be used to raise attention; it must never lower an
  existing triage or safety level.
- The model is not wired into the current ChronicCare AI triage logic.

## Files

- `load_data.py` - loads and prepares the local NHANES XPT files
- `train_baseline.py` - trains and evaluates the logistic regression baseline
- `explain.py` - produces SHAP values for one held-out patient
- `requirements.txt` - separate Python dependencies for the ML experiment
- `data/` - local NHANES files; ignored by Git