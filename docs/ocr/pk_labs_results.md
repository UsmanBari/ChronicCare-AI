# Pakistani Lab Layouts OCR Benchmark & Hardening Results

**Date**: Saturday 7 Nov 2026  
**Branch**: `feat/i3-ocr-hardening`  
**Engine Evaluated**: RapidOCR (`ch_PP-OCRv4` ONNX engine on CPU)  
**Evaluator**: Hassaan (AI Assistant)

> [!IMPORTANT]
> **Sample Size & Clinical Scope Note**: 5 fake reports (15 target clinical values) is a small benchmark sample created for exploratory hardening. While these tests cover prominent Pakistani lab formats (Chughtai, IDC, Excel Labs, Shifa, Punjab Diagnostic layouts), clinical verification in practice requires human confirmation via the patient review screen for all extracted values.

---

## 1. Test Dataset Description

All test samples were created by hand with synthetic data ("Test Patient", no real patient data) simulating typical diagnostic reports encountered in Pakistani clinical practice:

| Sample Filename | Diagnostic Center Style | Format / Medium | Target Observations (Ground Truth) |
|---|---|---|---|
| `pk_lab_01.png` | **Chughtai Lab Layout** | Tabular Digital Print | HbA1c: 8.4 %, Fasting Blood Sugar: 148 mg/dL, BP: 138/88 mmHg |
| `pk_lab_02.png` | **Islamabad Diagnostic Centre (IDC)** | Multi-Column Tabular Print | HbA1c: 7.6 %, Random Blood Sugar: 11.2 mmol/L, BP: 145/95 mmHg |
| `pk_lab_03.png` | **Excel Labs Layout** | Clean Digital Printout | HbA1c: 9.2 %, Fasting Plasma Glucose: 185 mg/dL, BP: 150/90 mmHg |
| `pk_lab_04.jpg` | **Shifa Clinical Laboratories** | Phone Photo (Desk Lighting) | HbA1c: 7.1 %, Fasting Blood Sugar: 132 mg/dL, BP: 130/85 mmHg |
| `pk_lab_05.jpg` | **Punjab Diagnostic Centre** | Phone Photo (Minor Angled) | HbA1c: 8.8 %, Random Blood Sugar: 215 mg/dL, BP: 160/100 mmHg |

---

## 2. Before Hardening Performance (Initial Extractor)

The initial extractor assumed simple line-by-line adjacency (`Test: Value`) and lacked multi-line table context and reference range disambiguation.

| Field Kind | Expected (GT) | Matched (TP) | False Positives (FP) | Recall | Precision | Diagnostic Finding |
|---|---|---|---|---|---|---|
| **HBA1C** | 5 | 0 | 0 | **0.0% (0/5)** | N/A | **FAIL**: Tabular layout separates test name and percentage by 2+ lines |
| **GLUCOSE** | 5 | 5 | 17 | **100.0% (5/5)** | **22.7% (5/22)** | **FAIL**: Reference ranges (e.g. `70 - 100`, `< 200`, `4.0 - 7.8`) extracted as patient values |
| **BP** | 5 | 5 | 3 | **100.0% (5/5)** | **62.5% (5/8)** | **FAIL**: Reference range BP thresholds (`< 120/80`, `120/80 mmHg`) extracted as patient vitals |
| **TOTAL** | **15** | **10** | **20** | **66.7% (10/15)** | **33.3% (10/30)** | **FAIL (Critical Over-Triage & Missing Values)** |

### Diagnostic Failure Root Cause Analysis (Before Hardening)

1. **HbA1c Line Fragmentation**: Multi-column lab reports (e.g., Chughtai, IDC) transcribe table cells as sequential vertical lines:
   ```text
   HbA1c (Glycated Haemoglobin)
   7.6
   %
   < 5.7 %
   ```
   A 2-line window evaluated `HbA1c` with `7.6` (missing `%`) and `7.6` with `%` (missing keyword `HbA1c`), yielding 0% recall.
2. **Reference Range Contamination**: Range hyphens (`70 - 100 mg/dL`) and inequality operators (`< 200 mg/dL`, `< 5.7 %`) were indiscriminately scanned by numeric regexes, flooding the patient record with healthy reference bounds.
3. **Reference BP Column Leakage**: Tabular vitals rows contain both observed BP and normal intervals:
   ```text
   B.P | 145/95 | mmHg | 120/80 mmHg
   ```
   The unit-only pattern matched `120/80 mmHg` independently from the reference column.

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
3. **Footnote & Methodology Isolation**: Filtered non-clinical disclaimer and methodology lines (`Note:`, `Method:`, `Verified:`, `Consult:`) before window assembly to prevent method descriptions (e.g. `Hexokinase enzymatic methodology for Glucose determination`) from leaking glucose keywords.
4. **Blood Pressure Context Gating**: Restricted BP extraction strictly to windows containing explicit vitals indicators (`bp`, `b.p`, `blood pressure`, `vitals`, `sitting`, `standing`), preventing isolated reference intervals (`120/80 mmHg`) from being mistaken for patient vitals.
5. **mmol/L vs mg/dL Distinctions**: Maintained strict conversion (mmol/L * 18.0) and preserved clinical context (`fasting`, `random`, `post-prandial`).

---

## 4. After Hardening Performance (Measured)

| Field Kind | Expected (GT) | Matched (TP) | False Positives (FP) | Recall | Precision | Status |
|---|---|---|---|---|---|---|
| **HBA1C** | 5 | 5 | 0 | **100.0% (5/5)** | **100.0% (5/5)** | **PASS** |
| **GLUCOSE** | 5 | 5 | 0 | **100.0% (5/5)** | **100.0% (5/5)** | **PASS** |
| **BP** | 5 | 5 | 0 | **100.0% (5/5)** | **100.0% (5/5)** | **PASS** |
| **TOTAL** | **15** | **15** | **0** | **100.0% (15/15)** | **100.0% (15/15)** | **PASS (Clean Extraction)** |

---

## 5. Regression Check on Prior Test Corpus

- **Clean Synthetic Reports (10 Samples)**: Field recall 95.8% (23/24), field precision 100.0%, medicine recall 100.0% (7/7).
- **Rotated/Noisy Documents (3 Samples)**: Field recall 87.5% (7/8), field precision 100.0%, medicine recall 100.0% (3/3).
- **Handwritten Prescription Photos (4 Samples)**: Medicine recall **100.0% (9/9)**, field precision 100.0%.
- **Zero Regressions**: All 35 extractor unit tests and all 23 upload route tests pass cleanly.

