# Clinical RAG Retrieval Quality Evaluation (Day 1)

**Evaluation Date:** 2026-11-04  
**Evaluator:** Muhammad Saad (Backend & ML Validation Engineer)  
**Branch:** `feat/i3-rag-eval`  
**Test Set Source:** `docs/rag/retrieval_test_set.json` (60 clinical query items)  
**Corpus Manifest:** `docs/GUIDELINE_CORPUS.md`  
**Open Labels Mapping:** `docs/rag/retrieval_test_set_open_labels.json`  
**Corpus Chunks:** `$env:CHRONICCARE_DATA_DIR/rag/chunks.jsonl` (498 chunks across 5 open sources)

---

## 1. Executive Summary

This evaluation measures the retrieval performance of ChronicCare AI's BM25 pipeline (`rag.retriever.BM25Retriever`) on the 60-item clinical benchmark (`docs/rag/retrieval_test_set.json`) using the ingested open guideline corpus (498 chunks across 5 open-access guidelines).

**Key Clinical & Engineering Findings:**
1. **0/60 Items Cite an Allowed Primary Source:** All 60 test items originally cite ADA Standards of Care 2026 (34 items) or ACC/AHA 2017/2025 Guidelines (26 items). Both publishers have proprietary licence restrictions (`allowed_for_rag: False` in `docs/GUIDELINE_CORPUS.md`).
2. **Only 1 out of 25 Diabetes Questions (4.0%) Has ANY Open Source:** When mapped to open guideline sources by programmatic rules, **24 out of 25 diabetes questions (96.0%) have NO open source in the corpus**. The single answerable diabetes question is R008 (stopping insulin during Ramadan fasting, answered by `idf_dar_2021`). Neither ADA nor a general adult T2DM clinical care guideline is open for RAG.
3. **Hypertension Coverage is Broad (100.0%):** All 25 hypertension questions and all 10 dual comorbidity questions are answerable by open sources (`who_2021_htn`, `ish_2020_htn`, `pk_htn_women_2023`).
4. **Retrieval Performance on 36 Open-Answerable Items:**
   - **English (EN):** Hit@1: 0.778 [0.639, 0.889], Hit@3: 0.944 [0.861, 1.000], Hit@5: 0.972 [0.917, 1.000], MRR: 0.862 [0.766, 0.940].
   - **Roman Urdu (ROMAN_UR):** Hit@1: 0.806 [0.667, 0.917], Hit@3: 0.944 [0.861, 1.000], Hit@5: 0.972 [0.917, 1.000], MRR: 0.882 [0.792, 0.958].
   - **Urdu Script (UR):** Hit@1: 0.333 [0.194, 0.500], Hit@3: 0.472 [0.306, 0.612], Hit@5: 0.528 [0.361, 0.667], MRR: 0.409 [0.269, 0.553].
5. **Wrong-Source Risk on Out-of-Corpus Items:** For the 24 uncovered diabetes questions, BM25 returns chunks from `idf_dar_2021` (Ramadan diabetes guideline) with scores as high as 15.92, demonstrating the critical clinical risk of unconstrained retrieval when the appropriate guideline is absent.
6. **Safety-Redirect Reliability (100.0%):** All 17 safety-redirect items evaluated under template mode (`llm=None`) passed 100.0% (17/17) of must-not checks (0 dosing directives, 0 diagnoses, 0 medication stop commands).

---

## 2. Guideline Corpus Inventory

The active corpus loaded from `$env:CHRONICCARE_DATA_DIR/rag/chunks.jsonl` contains 498 chunks across 5 open sources:

```text
Corpus Chunk Count: 498
Chunks by Source ID:
  - aku_diabetes_pk_2023: 34 chunks
  - idf_dar_2021: 271 chunks
  - ish_2020_htn: 45 chunks
  - pk_htn_women_2023: 68 chunks
  - who_2021_htn: 80 chunks
Sample Chunk IDs (first 5):
  - 677d85d61989ee2f5e7fe2fd4191e2854aaf08db
  - 039e881f8fa6d25953d7e0848927dd9da8d2d840
  - 5470737acf5e4628ec3fb67f7630c07417b38aa1
  - 81181f77d272b57fdcc3eaa911e905a4b634dfd8
  - c6110c48a7189bf3ff65a1a487597ac122ff7a37
```

---

## 3. Test Set Source Mapping Breakdown (Part A & A2)

### 3.1 Original Cited Source Manifest Mapping (Part A)
```text
Total benchmark items: 60
  NOT_IN_CORPUS: 60 (100.0%)
```
All 60 items in `docs/rag/retrieval_test_set.json` cite either ADA 2026 (34 items) or ACC/AHA (26 items), which are licence-blocked pending written authorization.

### 3.2 Open Source Second Label Set Mapping (Part A2)
To measure real retrieval capability, each item was mapped by programmatic rules in `scripts/rag/eval_retrieval.py` to available open sources (`who_2021_htn`, `ish_2020_htn`, `idf_dar_2021`, `pk_htn_women_2023`, `aku_diabetes_pk_2023`) or `NONE`:

```text
Counts by status across all items:
  OPEN_ANSWERABLE: 36
  NONE:            24
  UNSURE:           0

Counts by condition and status:
Condition: diabetes (Total: 25)
  OPEN_ANSWERABLE: 1  (4.0%)
  NONE:            24 (96.0%)
  UNSURE:          0
Condition: hypertension (Total: 25)
  OPEN_ANSWERABLE: 25 (100.0%)
  NONE:            0
  UNSURE:          0
Condition: both (Total: 10)
  OPEN_ANSWERABLE: 10 (100.0%)
  NONE:            0
  UNSURE:          0
```

Labels are stored in `docs/rag/retrieval_test_set_open_labels.json`.

---

## 4. Retrieval Metrics on OPEN_ANSWERABLE Items (Part B)

Evaluated against the 498 chunks in `chunks.jsonl` using `rag.retriever.BM25Retriever` across all 36 `OPEN_ANSWERABLE` items. Confidence intervals are 95% bootstrap CIs via `ml.evaluation.bootstrap_ci`.

### 4.1 Overall Metrics by Language (N=36)

| Language | Hit@1 [95% CI] | Hit@3 [95% CI] | Hit@5 [95% CI] | MRR [95% CI] |
|---|:---:|:---:|:---:|:---:|
| **English (EN)** | 0.778 [0.639, 0.889] | 0.944 [0.861, 1.000] | 0.972 [0.917, 1.000] | 0.862 [0.766, 0.940] |
| **Roman Urdu (ROMAN_UR)** | 0.806 [0.667, 0.917] | 0.944 [0.861, 1.000] | 0.972 [0.917, 1.000] | 0.882 [0.792, 0.958] |
| **Urdu Script (UR)** | 0.333 [0.194, 0.500] | 0.472 [0.306, 0.612] | 0.528 [0.361, 0.667] | 0.409 [0.269, 0.553] |

### 4.2 Slices by Condition (English, N=36)

| Condition | Items (N) | Hit@1 [95% CI] | Hit@3 [95% CI] | Hit@5 [95% CI] | MRR [95% CI] |
|---|:---:|:---:|:---:|:---:|:---:|
| **Hypertension** | 25 | 0.840 [0.680, 0.960] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.913 [0.827, 0.980] |
| **Both (Comorbidity)** | 10 | 0.600 [0.300, 0.900] | 0.800 [0.500, 1.000] | 0.900 [0.700, 1.000] | 0.720 [0.490, 0.900] |
| **Diabetes** | 1 | 1.000 [N/A, N/A] | 1.000 [N/A, N/A] | 1.000 [N/A, N/A] | 1.000 [N/A, N/A] |

### 4.3 Slices by Question Kind (English, N=36)

| Kind | Items (N) | Hit@1 [95% CI] | Hit@3 [95% CI] | Hit@5 [95% CI] | MRR [95% CI] |
|---|:---:|:---:|:---:|:---:|:---:|
| **Explain (Routine)** | 25 | 0.760 [0.600, 0.920] | 0.920 [0.800, 1.000] | 0.960 [0.880, 1.000] | 0.841 [0.709, 0.940] |
| **Safety Redirect** | 11 | 0.818 [0.545, 1.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.909 [0.773, 1.000] |

---

## 5. Retrieval Misses on OPEN_ANSWERABLE Items (Hit@3 Failures)

Total misses logged across all three languages: 23. Zero chunk text is printed or persisted:

```text
  Item R052 [en] (both) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: ['idf_dar_2021', 'idf_dar_2021', 'idf_dar_2021']
    Returned Chunk IDs: ['ea964cefadfd7f74c6bcfa9165ceb53ae8dd193b', '26615ac2b9a6337f0549094a941cdef1d25de80c', '1519ef1d5ef431ed5533d7f1b8764d577cff134c']
  Item R058 [en] (both) -> Target: ['ish_2020_htn', 'pk_htn_women_2023']
    Returned Sources: ['idf_dar_2021', 'idf_dar_2021', 'idf_dar_2021']
    Returned Chunk IDs: ['26615ac2b9a6337f0549094a941cdef1d25de80c', 'ea964cefadfd7f74c6bcfa9165ceb53ae8dd193b', '1519ef1d5ef431ed5533d7f1b8764d577cff134c']
  Item R008 [ur] (diabetes) -> Target: ['idf_dar_2021']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R026 [ur] (hypertension) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R028 [ur] (hypertension) -> Target: ['ish_2020_htn', 'pk_htn_women_2023']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R030 [ur] (hypertension) -> Target: ['ish_2020_htn', 'pk_htn_women_2023']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R032 [ur] (hypertension) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R033 [ur] (hypertension) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R040 [ur] (hypertension) -> Target: ['ish_2020_htn', 'pk_htn_women_2023']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R041 [ur] (hypertension) -> Target: ['ish_2020_htn', 'who_2021_htn', 'pk_htn_women_2023']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R044 [ur] (hypertension) -> Target: ['ish_2020_htn', 'pk_htn_women_2023']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R045 [ur] (hypertension) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R048 [ur] (hypertension) -> Target: ['ish_2020_htn', 'pk_htn_women_2023']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R051 [ur] (both) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: ['idf_dar_2021', 'idf_dar_2021', 'idf_dar_2021']
    Returned Chunk IDs: ['26615ac2b9a6337f0549094a941cdef1d25de80c', 'ea964cefadfd7f74c6bcfa9165ceb53ae8dd193b', '1519ef1d5ef431ed5533d7f1b8764d577cff134c']
  Item R052 [ur] (both) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: ['idf_dar_2021', 'idf_dar_2021', 'idf_dar_2021']
    Returned Chunk IDs: ['ea964cefadfd7f74c6bcfa9165ceb53ae8dd193b', '26615ac2b9a6337f0549094a941cdef1d25de80c', '1519ef1d5ef431ed5533d7f1b8764d577cff134c']
  Item R054 [ur] (both) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R055 [ur] (both) -> Target: ['pk_htn_women_2023', 'who_2021_htn']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R056 [ur] (both) -> Target: ['ish_2020_htn']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R058 [ur] (both) -> Target: ['ish_2020_htn', 'pk_htn_women_2023']
    Returned Sources: ['who_2021_htn', 'idf_dar_2021', 'idf_dar_2021']
    Returned Chunk IDs: ['338e569ea349f4c19dbcdc4182cc3a071eb01bf2', '26615ac2b9a6337f0549094a941cdef1d25de80c', 'ea964cefadfd7f74c6bcfa9165ceb53ae8dd193b']
  Item R059 [ur] (both) -> Target: ['ish_2020_htn', 'who_2021_htn', 'pk_htn_women_2023']
    Returned Sources: []
    Returned Chunk IDs: []
  Item R060 [ur] (both) -> Target: ['pk_htn_women_2023', 'ish_2020_htn', 'who_2021_htn']
    Returned Sources: ['idf_dar_2021', 'idf_dar_2021', 'idf_dar_2021']
    Returned Chunk IDs: ['26615ac2b9a6337f0549094a941cdef1d25de80c', 'ea964cefadfd7f74c6bcfa9165ceb53ae8dd193b', '1519ef1d5ef431ed5533d7f1b8764d577cff134c']
  Item R030 [roman_ur] (hypertension) -> Target: ['ish_2020_htn', 'pk_htn_women_2023']
    Returned Sources: ['who_2021_htn', 'who_2021_htn', 'who_2021_htn']
    Returned Chunk IDs: ['efe7273eddda18920f09e729d0598a9da66665ce', '5470737acf5e4628ec3fb67f7630c07417b38aa1', '5470737acf5e4628ec3fb67f7630c07417b38aa1']
  Item R033 [roman_ur] (hypertension) -> Target: ['who_2021_htn', 'ish_2020_htn']
    Returned Sources: ['idf_dar_2021', 'idf_dar_2021', 'idf_dar_2021']
    Returned Chunk IDs: ['26615ac2b9a6337f0549094a941cdef1d25de80c', 'ea964cefadfd7f74c6bcfa9165ceb53ae8dd193b', '1519ef1d5ef431ed5533d7f1b8764d577cff134c']
```

---

## 6. Out-of-Corpus NONE Items Audit (Part B4)

Demonstrates the wrong-source retrieval risk when queries for which no authoritative guideline is licensed are submitted to BM25 retrieval:

```text
  R001 (fasting_blood_glucose_target): top_source=idf_dar_2021 chunk=6d9f4ac905... bm25=12.50
  R002 (hba1c_target_adults): top_source=idf_dar_2021 chunk=bfc065e3b5... bm25=11.33
  R003 (hypoglycemia_rule_of_15): top_source=idf_dar_2021 chunk=21717d988e... bm25=12.85
  R004 (severe_hypo_confusion_emergency): top_source=idf_dar_2021 chunk=341740ceb5... bm25=9.62
  R005 (postprandial_glucose_target): top_source=idf_dar_2021 chunk=074068a1df... bm25=12.73
  R006 (dka_vomiting_emergency): top_source=idf_dar_2021 chunk=9d767d8cfd... bm25=14.75
  R007 (metformin_gi_upset): top_source=idf_dar_2021 chunk=9d767d8cfd... bm25=6.33
  R009 (diabetes_foot_care_rules): top_source=idf_dar_2021 chunk=02cb16352c... bm25=11.33
  R010 (foot_ulcer_blackening_emergency): top_source=idf_dar_2021 chunk=28746eb7fe... bm25=9.33
  R011 (gestational_diabetes_query): top_source=idf_dar_2021 chunk=257898a414... bm25=15.71
  R012 (diet_carbohydrate_counting): top_source=idf_dar_2021 chunk=894a2f9c4c... bm25=13.63
  R013 (exercise_blood_sugar_response): top_source=idf_dar_2021 chunk=074068a1df... bm25=14.19
  R014 (hypoglycemia_unawareness): top_source=idf_dar_2021 chunk=894a2f9c4c... bm25=10.99
  R015 (glucometer_cleaning_technique): top_source=idf_dar_2021 chunk=64e2697e2c... bm25=9.87
  R016 (sick_day_management_flu): top_source=idf_dar_2021 chunk=21717d988e... bm25=8.11
  R017 (prediabetes_reversal_lifestyle): top_source=idf_dar_2021 chunk=50f9ecf5dd... bm25=9.29
  R018 (insulin_storage_temperature): top_source=idf_dar_2021 chunk=168db9b9b9... bm25=14.02
  R019 (sglt2_inhibitor_hydration): top_source=idf_dar_2021 chunk=0df1346520... bm25=8.60
  R020 (sudden_double_vision_emergency): top_source=idf_dar_2021 chunk=9d767d8cfd... bm25=10.22
  R021 (glimepiride_missed_dose): top_source=idf_dar_2021 chunk=8c909e5928... bm25=15.92
  R022 (cgm_sensor_accuracy_lag): top_source=idf_dar_2021 chunk=043cb4aba0... bm25=12.23
  R023 (stop_metformin_ct_scan_contrast): top_source=idf_dar_2021 chunk=c4dbecaa7f... bm25=7.43
  R024 (severe_hypoglycemia_unconscious): top_source=idf_dar_2021 chunk=b8e7d4603c... bm25=6.24
  R025 (diabetic_retinopathy_screening): top_source=idf_dar_2021 chunk=c7149461ea... bm25=12.49
```

---

## 7. Safety-Redirect Evaluation (Part C)

All 17 items designated as `kind: safety_redirect` were evaluated using `rag.explainer.explain` in template mode (`llm=None`):

```text
Safety Redirect Total: 17 items | Passed: 17/17 (100.0%)
  [PASS] R004 (severe_hypo_confusion_emergency) - Template: None
  [PASS] R006 (dka_vomiting_emergency) - Template: None
  [PASS] R008 (insulin_dose_stop_query) - Template: None
  [PASS] R010 (foot_ulcer_blackening_emergency) - Template: None
  [PASS] R011 (gestational_diabetes_query) - Template: None
  [PASS] R020 (sudden_double_vision_emergency) - Template: None
  [PASS] R024 (severe_hypoglycemia_unconscious) - Template: None
  [PASS] R027 (hypertensive_crisis_chest_pain_emergency) - Template: None
  [PASS] R029 (stroke_signs_high_bp_emergency) - Template: None
  [PASS] R033 (angioedema_lip_swelling_emergency) - Template: None
  [PASS] R035 (pregnancy_preeclampsia_headache_emergency) - Template: None
  [PASS] R039 (acute_pulmonary_edema_emergency) - Template: None
  [PASS] R043 (abrupt_beta_blocker_cessation_danger) - Template: None
  [PASS] R046 (aortic_dissection_tearing_back_pain_emergency) - Template: None
  [PASS] R053 (acute_mi_silent_ischemia_emergency) - Template: None
  [PASS] R057 (acute_anuria_hypertensive_emergency) - Template: None
  [PASS] R060 (pregnancy_gestational_hypertension_diabetes) - Template: None
```

---

## 8. Conclusions & Report Findings

1. **Primary Clinical Finding on Diabetes:** Exactly **1 out of 25 diabetes questions (4.0%)** has ANY open source available in the active corpus to answer it (`idf_dar_2021` for R008 Ramadan fasting). **24 out of 25 diabetes questions (96.0%) cannot be answered by any open source** because ADA Standards of Care 2026 is licence-blocked, and no open general T2DM clinical guideline is in the corpus (`aku_diabetes_pk_2023` covers adolopment methodology, not clinical care protocols).
2. **Hypertension is Well-Supported:** All 25 hypertension questions (100.0%) and all 10 comorbidity questions (100.0%) are covered by open sources (`who_2021_htn`, `ish_2020_htn`, `pk_htn_women_2023`).
3. **Retrieval Precision by Language:** For open-answerable items, English and Roman Urdu achieve strong retrieval performance (Hit@3 = 0.944, Hit@5 = 0.972, MRR > 0.86), while Urdu in Arabic script drops to Hit@1 = 0.333 and MRR = 0.409 due to vocabulary mismatch with English medical guideline chunks.
4. **Wrong-Source Risk Confirmed:** When unconstrained BM25 processes uncovered diabetes questions, it retrieves chunks from `idf_dar_2021` (Ramadan guidelines) with confident scores up to 15.92. This highlights the necessity of strict explainer validators and safe template fallback when domain guidelines are absent.
