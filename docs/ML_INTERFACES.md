# DRAFT — Usman approves or changes this before his harness depends on it

# Machine Learning Model Artifact Contract & Interfaces Specification

This document defines the strict contract for serialized machine learning models, model metadata cards (`model_card.json`), evaluation interfaces, and external validation protocols across the ChronicCare-AI ecosystem.

---

## 1. Model Artifact Folder Layout

Every trained clinical risk model artifact must be saved as a self-contained directory within `backend-poc-technical/ml/outputs/models/<model_name>/` (which is strictly git-ignored):

```text
backend-poc-technical/ml/outputs/models/<model_name>/
├── model.joblib          # Full fitted scikit-learn Pipeline (preprocessing + estimator)
└── model_card.json       # Validated schema metadata card describing provenance, target, and metrics
```

### Key Principles:
1. **Raw Feature Ingestion:** `model.joblib` must be a self-contained scikit-learn `Pipeline` (e.g. `StandardScaler` + `LogisticRegression` or `SimpleImputer` + `ColumnTransformer` + classifier) that operates directly on raw DataFrame / 2D array features matching the card's `features` order.
2. **Deterministic Versioning:** The model card links directly to the git commit hash at training time, the installed `sklearn_version`, the dataset split version (`nhanes_temporal_v1`), and the author.
3. **Decoupled Deployment:** Downstream inference engines and external validation scripts (Day 6) load artifacts using `load_model_artifact(dir_path)` without needing access to original training scripts or raw survey datasets.

---

## 2. Model Card (`model_card.json`) Schema Specification

The model card is validated by `ml.artifacts.validate_model_card(card)`. All 16 keys are strictly required:

| Key | Type | Description | Example |
|---|---|---|---|
| `name` | `string` | Unique identifier of the model artifact | `"baseline_temporal_lr"` |
| `owner` | `string` | Author / engineer who trained and saved the model | `"saad"` (or `"usman"`) |
| `created_at` | `string` | ISO 8601 UTC timestamp of creation | `"2026-10-28T14:30:00Z"` |
| `git_commit` | `string` | HEAD git commit SHA at training time | `"22af452..."` |
| `label` | `string` | Target label registered in `ml.labels.LABELS` | `"told_diabetes"` |
| `features` | `list[string]` | Ordered list of candidate input features | `["age", "sex_male", "bmi"]` |
| `threshold` | `float` | Operational decision threshold in range `[0.0, 1.0]` | `0.470` |
| `threshold_policy` | `dict` | Policy dict used to select the threshold on validation | `{"type": "min_sensitivity", "value": 0.80}` |
| `split` | `string` | Dataset partition version name | `"nhanes_temporal_v1"` |
| `model_type` | `string` | Human-readable model architecture descriptor | `"LogisticRegression (balanced)"` |
| `hyperparameters` | `dict` | Key-value mapping of tuned model hyperparameters | `{"max_iter": 1000, "class_weight": "balanced", "random_state": 42}` |
| `sklearn_version` | `string` | Installed `scikit-learn` version at training time | `"1.9.1"` |
| `train_rows` | `integer` | Count of clean training samples fitted | `37827` |
| `val_rows` | `integer` | Count of clean validation samples evaluated | `10967` |
| `val_auroc` | `float` | Validation AUROC performance | `0.7712` |
| `notes` | `string` | Clinical context, limitations, or architecture remarks | `"S-6 features age/sex/BMI on temporal split; reference baseline, not a product model."` |

### Concrete `model_card.json` Example:

```json
{
  "name": "baseline_temporal_lr",
  "owner": "saad",
  "created_at": "2026-10-28T14:30:00Z",
  "git_commit": "22af452e69fa090b830d970e4fbc87ba13876939",
  "label": "told_diabetes",
  "features": [
    "age",
    "sex_male",
    "bmi"
  ],
  "threshold": 0.470,
  "threshold_policy": {
    "type": "min_sensitivity",
    "value": 0.80
  },
  "split": "nhanes_temporal_v1",
  "model_type": "LogisticRegression (balanced)",
  "hyperparameters": {
    "C": 1.0,
    "class_weight": "balanced",
    "max_iter": 1000,
    "random_state": 42
  },
  "sklearn_version": "1.9.1",
  "train_rows": 37827,
  "val_rows": 10967,
  "val_auroc": 0.7712,
  "notes": "S-6 features age/sex/BMI on temporal split; reference point, not a product model."
}
```

---

## 3. Training & Evaluation Pipeline Workflow (Usman's Harness Integration)

Usman's experiment harness (`backend-poc-technical/ml/experiments/`) executes the following sequential steps using the Day 3 toolkit:

```text
 1. Check Target Leakage
    └── ml.evaluation.check_leakage(label_name, feature_list)
        (Raises LeakageError if features leak the target label; halts before data is loaded)

 2. Partition Temporal Dataset
    └── ml.common.load_split("nhanes_temporal_v1")
        (Splits into train_core 1999-2012, validation 2013-2016, test 2017-2023)

 3. Model Training & Pipeline Fitting
    └── pipeline.fit(X_train, y_train)
        (Fitted exclusively on train_core)

 4. Validation Threshold Selection
    └── ml.evaluation.choose_threshold(y_val, p_val, policy)
        (CRITICAL: Run strictly on validation predictions; test data is NEVER passed here)

 5. Held-Out Test Evaluation
    ├── ml.evaluation.auroc(y_test, p_test)
    ├── ml.evaluation.auprc(y_test, p_test)
    ├── ml.evaluation.bootstrap_ci(y_test, p_test, metric_fn)
    ├── ml.evaluation.metrics_at_threshold(y_test, p_test, chosen_threshold)
    ├── ml.evaluation.calibration(y_test, p_test, n_bins=10)
    └── ml.evaluation.subgroup_report(df_test, y_col, p_col, chosen_threshold)

 6. Save Validated Model Artifact
    └── ml.artifacts.save_model_artifact(pipeline, model_card, out_dir)
        (Writes model.joblib and validated model_card.json to outputs/models/<model_name>/)

 7. Generate Standardized Report
    └── ml.evaluation.write_eval_report(report_path, sections_dict)
```

---

## 4. External Validation Protocol (Day 6 Interface)

On Day 6, the external validation suite independently assesses generalization on non-NHANES datasets (BRFSS, Kaggle cohorts, Framingham, Cardio70k, DHS):

1. **Artifact Ingestion:**
   ```python
   from ml.artifacts import load_model_artifact

   pipeline, card = load_model_artifact("backend-poc-technical/ml/outputs/models/baseline_temporal_lr")
   ```
2. **Feature Alignment & Type Verification:**
   - External validation reads `card["features"]` to determine exact expected input columns and ordering.
   - Maps external dataset columns to match feature definitions in `docs/ML_FEATURE_MAP.md`.
3. **Threshold Application:**
   - Evaluates predictions using the pre-calibrated `card["threshold"]` without re-tuning or peeking at external labels.
4. **Generalization Metrics:**
   - Runs `ml.evaluation.metrics_at_threshold` and `ml.evaluation.calibration` on external cohorts to detect distribution shift, calibration drift, and demographic equity variance.
