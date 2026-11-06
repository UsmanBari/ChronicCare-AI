# Pakistani Lab Layouts OCR Benchmark & Hardening Results

**Date**: 06-Nov-2026  
**Branch**: `feat/i3-ocr-hardening`  
**Engine Evaluated**: RapidOCR (`ch_PP-OCRv4` ONNX engine on CPU)  
**Evaluator**: Hassaan (with AI coding assistant)

> [!IMPORTANT]
> **Dataset Attribution & Evaluation Scope**:
> - **Development Set (5 samples)**: 5 script-generated synthetic reports (`scripts/generate_pk_labs.py`); images and ground truth from the same script; 04–05 simulate photos (blur/noise), they are not real photos.
> - **Extractor Tuning**: The extractor was tuned on these same 5 development samples, so 15/15 is accuracy on the development set, not a measured result on new reports.
> - **Held-Out Set (2 samples)**: 2 generated, simulated reports (held_out_01.png generated screenshot, held_out_02.jpg generated, simulated photo) evaluated separately below without modifying `extract_fields.py`.
> - **Clinical Verification**: Clinical verification in practice always requires human confirmation via the patient review screen for all extracted values.

---

## 1. Test Dataset Description

The 5 synthetic development reports simulate typical diagnostic test formats encountered in Pakistani clinical practice with fake patient names ("Test Patient 01" to "05"):

| Sample Filename | Layout Description | Format / Medium | Target Observations (Ground Truth) |
|---|---|---|---|
| `pk_lab_01.png` | **Layout 1: tabular print** | Tabular Digital Print | HbA1c: 8.4 %, Fasting Blood Sugar: 148 mg/dL, BP: 138/88 mmHg |
| `pk_lab_02.png` | **Layout 2: multi-column** | Multi-Column Tabular Print | HbA1c: 7.6 %, Random Blood Sugar: 11.2 mmol/L, BP: 145/95 mmHg |
| `pk_lab_03.png` | **Layout 3: single-column receipt** | Clean Digital Printout | HbA1c: 9.2 %, Fasting Plasma Glucose: 185 mg/dL, BP: 150/90 mmHg |
| `pk_lab_04.jpg` | **Layout 4: blurred photo of print** | Simulated Phone Photo (Blur/Desk Light) | HbA1c: 7.1 %, Fasting Blood Sugar: 132 mg/dL, BP: 130/85 mmHg |
| `pk_lab_05.jpg` | **Layout 5: rotated photo with noise** | Simulated Phone Photo (Angled/Noise) | HbA1c: 8.8 %, Random Blood Sugar: 215 mg/dL, BP: 160/100 mmHg |

---

## 2. Before Hardening Performance (Development Set — Initial Dev Extractor)

Directly measured by running dev's original `extract_fields.py` on the 5 development samples with exact score counting (at most 1 TP per sample per field):

| Field Kind | Expected (GT) | Matched (TP) | False Positives (FP) | Recall | Precision | Diagnostic Finding |
|---|---|---|---|---|---|---|
| **HBA1C** | 5 | 0 | 0 | **0.0% (0/5)** | **0.0% (0/0)** | **FAIL**: Tabular layout separates test name and percentage by multiple lines |
| **GLUCOSE** | 5 | 5 | 22 | **100.0% (5/5)** | **18.5% (5/27)** | **FAIL**: Reference bounds (e.g. `70 - 100`, `< 200`, `4.0 - 7.8`) extracted as patient values |
| **BP** | 5 | 5 | 3 | **100.0% (5/5)** | **62.5% (5/8)** | **FAIL**: Reference range BP thresholds (`< 120/80`, `120/80 mmHg`) extracted as vitals |
| **TOTAL** | 15 | 10 | 25 | **66.7% (10/15)** | **28.6% (10/35)** | **FAIL (Critical Over-Triage & Missing Values)** |

### Diagnostic Failure Root Cause Analysis (Before Hardening)

1. **HbA1c Line Fragmentation**: Multi-column tabular prints transcribe table cells as sequential vertical lines (`HbA1c \n 7.6 \n % \n < 5.7 %`). A 2-line window evaluated `HbA1c` with `7.6` (missing `%`) and `7.6` with `%` (missing keyword `HbA1c`), yielding 0% recall.
2. **Reference Range Contamination**: Range hyphens (`70 - 100 mg/dL`) and inequality operators (`< 200 mg/dL`, `< 5.7 %`) were indiscriminately scanned by numeric regexes, flooding the patient record with healthy reference bounds as false positives.
3. **Reference BP Column Leakage**: Tabular vitals rows contain both observed BP and normal intervals (`B.P | 145/95 | mmHg | 120/80 mmHg`). The regex matched `120/80 mmHg` as an extra patient vital.

---

## 3. Hardening Improvements Implemented

In `backend-poc-technical/data_sources/ocr/extract_fields.py`:

1. **Multiline Window Expansion**: Expanded sliding evaluation windows up to 4 consecutive clinical lines to capture wide multi-column table wraps (`Test Name \n Value \n Unit \n Reference Range`).
2. **Reference Context Detector (`is_in_reference_context`)**:
   - Detects comparison operators in prefix (`<`, `>`, `≤`, `≥`, `less than`, `greater than`).
   - Detects range hyphens/conjunctions (`-`, `–`, `—`, `to`) in prefix and suffix.
   - Detects explicit reference labels (`reference:`, `ref interval:`, `normal:`, `limits:`).
   - Detects parenthetical qualifiers (`(Normal)`, `(Prediabetes)`).
   - Detects preceding BP readings in the same row/context.
3. **Footnote & Methodology Isolation**: Filtered non-clinical disclaimer and methodology lines (`Note:`, `Method:`, `Verified:`, `Consult:`) before window assembly to prevent method descriptions from leaking false positive keywords.
4. **Blood Pressure Context Gating**: Restricted BP extraction strictly to windows containing explicit vitals indicators (`bp`, `b.p`, `blood pressure`, `vitals`, `sitting`, `standing`), preventing isolated reference intervals (`120/80 mmHg`) from being mistaken for patient vitals.
5. **mmol/L vs mg/dL Distinctions**: Maintained strict conversion (mmol/L * 18.0) and preserved clinical context (`fasting`, `random`, `post-prandial`).

---

## 4. After Hardening Performance (Development Set — Hardened Extractor)

| Field Kind | Expected (GT) | Matched (TP) | False Positives (FP) | Recall | Precision | Status |
|---|---|---|---|---|---|---|
| **HBA1C** | 5 | 5 | 0 | **100.0% (5/5)** | **100.0% (5/5)** | **PASS** |
| **GLUCOSE** | 5 | 5 | 0 | **100.0% (5/5)** | **100.0% (5/5)** | **PASS** |
| **BP** | 5 | 5 | 0 | **100.0% (5/5)** | **100.0% (5/5)** | **PASS** |
| **TOTAL** | 15 | 15 | 0 | **100.0% (15/15)** | **100.0% (15/15)** | **PASS (Clean Extraction)** |

---

## 5. Held-Out Evaluation (Independent Held-Out Set — Zero Extractor Tuning)

To evaluate generalizability, a held-out set of 2 new reports was prepared under `backend-poc-technical/ocr_spike/samples/pk_labs/held_out/` with hand-written ground truth. The hardened extractor was evaluated **WITHOUT ANY MODIFICATIONS** to `extract_fields.py`:

| Sample Filename | Layout Description | Format / Medium | Target Observations (Ground Truth) |
|---|---|---|---|
| `held_out_01.png` | Electronic Portal Export | Generated electronic export screenshot | HbA1c: 7.1 %, Fasting Glucose: 126 mg/dL, BP: 134/86 mmHg |
| `held_out_02.jpg` | Physical Clinic Slip | Generated, simulated photo | HbA1c: 8.9 %, Random Glucose: 225 mg/dL, BP: 148/92 mmHg |

| Field Kind | Expected (GT) | Matched (TP) | False Positives (FP) | Recall | Precision | Status |
|---|---|---|---|---|---|---|
| **HBA1C** | 2 | 2 | 0 | **100.0% (2/2)** | **100.0% (2/2)** | **PASS** |
| **GLUCOSE** | 2 | 2 | 0 | **100.0% (2/2)** | **100.0% (2/2)** | **PASS** |
| **BP** | 2 | 2 | 0 | **100.0% (2/2)** | **100.0% (2/2)** | **PASS** |
| **TOTAL** | 6 | 6 | 0 | **100.0% (6/6)** | **100.0% (6/6)** | **PASS (6/6 on 2 held-out samples; too few to confirm generalisation)** |

---

## 6. Regression Check on Prior Test Corpus

- **Clean Synthetic Reports (10 Samples)**: Field recall 95.8% (23/24), field precision 100.0%, medicine recall 100.0% (7/7).
- **Rotated/Noisy Documents (3 Samples)**: Field recall 87.5% (7/8), field precision 100.0%, medicine recall 100.0% (3/3).
- **Handwritten Prescription Photos (4 Samples)**: Medicine recall **100.0% (9/9)**, field precision 100.0%.
- **Zero Regressions**: All 35 extractor unit tests and all 24 upload route tests pass cleanly.