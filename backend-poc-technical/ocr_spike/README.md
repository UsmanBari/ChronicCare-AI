# ChronicCare-AI: OCR Spike (Day 5 Correction)

This directory contains the independent research spike for Prescription and Lab Report Optical Character Recognition (OCR) for ChronicCare-AI.

## Architecture Boundary
- **Isolated Module**: This directory is completely isolated from production code. `backend-poc-technical/main.py` and existing agents NEVER import from `ocr_spike`.
- **Own Virtual Environment**: Uses its own isolated `.venv` (`backend-poc-technical/ocr_spike/.venv`) with separate `requirements.txt`.
- **Deterministic Samples**: 13 synthetic medical documents in `samples/synthetic/` + 4 handwritten prescription photos in `samples/photos/` with ground truth in `samples/ground_truth.json`.

---

## 3 Free Options Evaluated

### 1. Tesseract.js (Recommended Architecture)
- **Engine**: In-Browser Web Worker (Benchmark: Node.js v22 engine).
- **Execution**: Runs entirely on the patient's phone/browser.
- **Server Impact**: **0 MB Server RAM**. The raw image never leaves the user's phone.
- **Payload**: Patient device sends plain text only (`max 20,000 characters`) to `POST /api/me/record/uploads`.
- **Language Models**: Bilingual English and Urdu (`eng+urd`, one-time 6.29 MB download cached in IndexedDB).
- **Benchmark Script**: Located in `tesseractjs_bench/bench.mjs`. Results stored in `tesseractjs_results.json`.

### 2. RapidOCR (Server-Side Fallback)
- **Engine**: ONNX Runtime (`rapidocr-onnxruntime`, strictly no PyTorch).
- **Execution**: Python backend in-memory processing.
- **Server Impact**: **108.63 MB Peak RSS** (fits comfortably within Render free tier's 512 MB ceiling alongside backend's ~70 MB).
- **Model Footprint**: 15.44 MB ONNX models (`ch_PP-OCRv4_det_infer.onnx`, `ch_PP-OCRv4_rec_infer.onnx`, `ch_ppocr_mobile_v2.0_cls_infer.onnx`).
- **Limitation**: English and Chinese characters only; no Urdu script support.

### 3. Tesseract Desktop (Reference)
- **Engine**: Local C++ binary (`tesseract`) via `pytesseract`.
- **Status**: Reference engine for the same core Tesseract.js uses. Requires OS-level package (`apt-get install tesseract-ocr`). On Windows, installer requires administrator elevation.

---

## Dropped Options

- **EasyOCR**: Dropped because PyTorch distribution requires ~1.5 GB disk download, and runtime memory (400–700 MB) exceeds Render's 512 MB free tier ceiling, triggering Linux OOM kill (code 137).
- **Groq Vision**: Dropped because provisioned account has no access to vision models and `GROQ_API_KEY` is not configured locally.

---

## Running the Spike

### Step 1: Run Field Extractor Tests
Hermetic regex and dictionary parsing tests (HbA1c, Glucose, Blood Pressure, Medications):
```powershell
pytest backend-poc-technical/ocr_spike/test_extract_fields.py -v
```

### Step 2: Run Tesseract.js Benchmark
```powershell
cd backend-poc-technical/ocr_spike/tesseractjs_bench
node bench.mjs
```

### Step 3: Run Measured Comparison
```powershell
& "backend-poc-technical/ocr_spike/.venv/Scripts/python.exe" backend-poc-technical/ocr_spike/run_compare.py
```
Updates `docs/ocr/compare_results.md` with measured metrics.
