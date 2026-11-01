# ChronicCare-AI — OCR Technical Design Document

**Document ID**: `docs/OCR_DESIGN.md`  
**Iteration**: I2-5 (Day 5 Design & Measured Spike — Correction)  
**Author**: Hassaan Mudassar (AI Assistant Antigravity)  
**Target Milestone**: Day 7 (OCR v1 behind feature flag)  

---

## 1. Measured Benchmarks & Deployability Matrix

### 1.1 Measured Performance Table
All performance and accuracy numbers below are **MEASURED** directly from programmatic benchmark execution on 17 deterministic document samples (10 clean synthetic, 3 rotated/noise/blur, and 4 handwritten prescription photos) using the spike benchmark harness [`backend-poc-technical/ocr_spike/run_compare.py`](file:///C:/Users/Dell/OneDrive/Desktop/ChronicCare-AI/backend-poc-technical/ocr_spike/run_compare.py).

#### Table 1A: Clean Synthetic Reports & Prescriptions (10 Samples)
| Option | Status | Mean Latency (ms) | Field Recall | Field Precision | Medicine Recall | Peak RSS / Overhead |
|---|---|---|---|---|---|---|
| **Option A: Tesseract.js (Client Phone)** | **MEASURED** | 652.1 ms | 29.2% (7/24) | 28.0% | 100.0% (7/7) | **0 MB Server RAM** (Client Peak: 125.58 MB) |
| **Option B: RapidOCR (Server ONNX)** | **MEASURED** | 2,427.3 ms | 29.2% (7/24) | 29.2% | 100.0% (7/7) | **108.63 MB Server RAM** (Fits 512 MB ceiling) |
| **Option C: Tesseract Desktop (v5)** | **NOT RUN** | — | — | — | — | `TesseractNotFoundError: tesseract is not installed or it's not in your PATH (Windows installer requires administrator elevation to install to Program Files)` |

#### Table 1B: Rotated, Blurred & Noisy Documents (3 Samples: lab_08, lab_09, rx_06)
| Option | Status | Mean Latency (ms) | Field Recall | Field Precision | Medicine Recall | Measured Notes |
|---|---|---|---|---|---|---|
| **Option A: Tesseract.js (Client Phone)** | **MEASURED** | 823.7 ms | 37.5% (3/8) | 50.0% | 100.0% (3/3) | Resilient to 90° rotation and moderate sensor noise |
| **Option B: RapidOCR (Server ONNX)** | **MEASURED** | 1,993.5 ms | 37.5% (3/8) | 50.0% | 100.0% (3/3) | Built-in text angle classifier handles rotation |
| **Option C: Tesseract Desktop (v5)** | **NOT RUN** | — | — | — | — | Empty (Option could not be installed/run without admin) |

#### Table 1C: Handwritten Prescription Photos (4 Samples: rx_handwritten_01 to 04)
| Option | Status | Mean Latency (ms) | Field Recall | Field Precision | Medicine Recall | Honest Clinical Assessment |
|---|---|---|---|---|---|---|
| **Option A: Tesseract.js (Client Phone)** | **MEASURED** | 2,353.8 ms | 75.0% (6/8) | 100.0% | 75.0% (6/8) | **Weak on cursive handwriting**: Read 6/8 medications on high-contrast lines; misread dense sigs |
| **Option B: RapidOCR (Server ONNX)** | **MEASURED** | 2,371.0 ms | 37.5% (3/8) | 100.0% | 37.5% (3/8) | **Poor on handwriting**: Segmenter fragments pen ligatures as unsegmented noise |
| **Option C: Tesseract Desktop (v5)** | **NOT RUN** | — | — | — | — | Empty (Option could not be installed/run without admin) |

---

### 1.2 Deployability Matrix (Target: Render Free Tier ~512 MB RAM, Python Native)

| Dimension | Option A: Tesseract.js | Option B: RapidOCR | Dropped: EasyOCR | Dropped: Groq Vision |
|---|---|---|---|---|
| **Execution Host** | **Patient Browser / Phone** | Render Web Service Backend | Render Web Service Backend | Remote Cloud API |
| **Server RAM Footprint** | **0 MB** (MEASURED: in-browser Web Worker) | **108.63 MB Peak** (MEASURED via psutil) | EXPECTED: 400–700 MB — source: [PyTorch/EasyOCR memory specs](https://github.com/JaidedAI/EasyOCR) | EXPECTED: ~15 MB HTTP Client — source: [Groq Python SDK](https://github.com/groq/groq-python) |
| **Fits Render 512 MB Tier?** | **YES** (Zero server impact) | **YES** (108 MB + 70 MB app = 178 MB) | **NO** (Triggers Linux OOM Kill 137) | **YES** (API client only) |
| **Server Binary Dependencies**| **None** (Browser JavaScript) | **None** (Precompiled ONNX wheels) | Requires PyTorch C++ wheels (~1.5 GB) | **None** (Python HTTP client) |
| **Model / Asset Download** | **6.29 MB** (MEASURED: `eng` 4.96MB + `urd` 1.33MB) | **15.44 MB** (MEASURED: 3 ONNX models) | EXPECTED: > 1.5 GB PyTorch distribution | 0 MB (Hosted off-site) |
| **Urdu Script Support** | **YES** (MEASURED: `urd.traineddata` 1.33 MB) | **NO** (English / Chinese only) | Poor on connected Nastaliq | High (LLaMA vision context) |
| **Handwriting Quality** | **Poor (Weak on cursive)** | **Poor (Fails on cursive)** | Moderate on clean block text | High on cursive prescriptions |
| **Image Privacy Boundary** | **Phone-Local** (Image never leaves device) | Processed in Server RAM | Processed in Server RAM | **Leaves Server** (3rd party API) |
| **Operational Cost** | **Free ($0)** | **Free ($0)** | Free ($0) | Paid API Tokens |

---

### 1.3 Architectural Recommendation (Based Strictly on MEASURED Rows)
1. **Selection**: **Tesseract.js running client-side on the patient's device** is selected as the winning architecture for ChronicCare-AI.
2. **Zero Server Footprint & Total Privacy**: Because Tesseract.js executes inside a browser Web Worker, the backend server consumes **0 MB of RAM**, and patient document photos **never leave the user's phone or browser**.
3. **Bilingual Clinical Support**: Tesseract.js supports bilingual English and Urdu (`eng+urd`) with a one-time 6.29 MB cached download, unlike RapidOCR which is strictly limited to Latin and Chinese characters.
4. **Safety Net**: As measured, free local OCR engines struggle with doctor handwriting (relying on clean block print or high-contrast lines). The patient confirmation screen ([`OcrConfirmScreen.tsx`](file:///C:/Users/Dell/OneDrive/Desktop/ChronicCare-AI/app/components/OcrConfirmScreen.tsx)), where patients verify, fix, or manually add unread medicines, is the mandatory clinical safety net.

---

## 2. End-to-End Patient Flow (Client-Side OCR)

```mermaid
sequenceDiagram
    autonumber
    actor Patient
    participant UI as HealthRecordScreen (Browser)
    participant Worker as Tesseract.js (Browser Web Worker)
    participant API as FastAPI (/api/me/record/uploads)
    participant Engine as extract_fields (Server Python)
    participant Memory as UploadStagingStore (30 min TTL)
    participant Store as Local Store / record_edits

    Patient->>UI: Clicks "Upload report or prescription"
    UI->>Patient: Displays On-Device Privacy Notice (en/ur)
    Patient->>UI: Selects Image (Camera or File)
    UI->>Worker: Dispatches image to Web Worker (eng+urd)
    Worker->>Worker: Downscales, binarizes, transcribes text on device
    Worker-->>UI: Returns raw transcribed text string
    UI->>API: POST /api/me/record/uploads {text, document_type_hint, lang}
    API->>Engine: extract_fields(raw_text) -> parsed fields
    API->>Memory: Store extracted fields under upload_id (TTL: 30m)
    API-->>UI: 200 OK {upload_id, document_type_guess, fields, unmatched_lines}
    UI->>Patient: Displays OcrConfirmScreen (Field evidence, values, confidence)
    Patient->>UI: Confirms / Edits / Removes items
    UI->>API: POST /api/me/record/uploads/{upload_id}/confirm {confirm, remove}
    API->>API: Re-validate with check-in validators (ranges, units)
    API->>Store: Save valid items (origin: "ocr", source: "local")
    API->>Store: Write record_edits rows (origin: "ocr", schema v14)
    API->>Memory: Delete temporary upload_id
    API-->>UI: 200 OK {saved: [...], rejected: [...]}
    UI->>Patient: Summary of saved items + provenance badges
```

1. **Upload Initiation**: Patient taps "Upload report or prescription" on `HealthRecordScreen` (visible only in isolated mode when `ocr_enabled: true`).
2. **On-Device OCR Execution**: The image is processed entirely inside a client-side Web Worker using `tesseract.js`. The raw image is resized, transcribed, and immediately discarded from memory.
3. **Text-Only Transmission**: The client sends **only the transcribed plain text** (max 20,000 characters) to `POST /api/me/record/uploads`. The server receives zero image bytes.
4. **Extraction & Staging**: Server-side `extract_fields.py` parses clinical metrics (HbA1c, Glucose, Blood Pressure, Medications) and stages them in memory for 30 minutes under an `upload_id`.
5. **Confirmation UI**: Patient inspects `OcrConfirmScreen`, which displays kind labels, parsed values, units, raw text quotes (evidence snippet), confidence badges (High / Medium / Low with text + icons), and inline Fix/Remove controls.
6. **Persistence**: Confirmed fields are re-validated using production clinical validators and persisted to Local Store with origin `"ocr"` and Schema v14 `record_edits` provenance tracking.

---

## 3. REST API Specification

### 3.1 `POST /api/me/record/uploads`
- **Authorization**: `require_role("patient")`.
- **Pre-Conditions**:
  - `OCR_ENABLED` is `true` (otherwise `503 Service Unavailable: {"code": "ocr_disabled"}`).
  - Isolated mode only (otherwise `409 Conflict: {"detail": "record_managed_by_ehr"}`).
- **Request Body (JSON, max 20,000 characters)**:
```json
{
  "text": "Rx: Metformin 500mg 1+0+1\nTab. Glimepiride 1mg 1+0+0\nAdvice: Monitor fasting sugar daily",
  "document_type_hint": "prescription",
  "lang": "en"
}
```
- **Validation**:
  - Payload text $> 20,000$ characters $\rightarrow$ `413 Request Entity Too Large: {"detail": "text_too_large"}`.
  - Empty or whitespace-only text $\rightarrow$ `422 Unprocessable Entity: {"detail": "empty_text"}`.
- **Processing**:
  - Runs pure stdlib `extract_fields(body.text)`.
  - Stores structured fields in volatile in-memory staging store with 30-minute expiration.
- **Audit Logging**: `append_audit(actor_user_id=user_id, action="ocr_upload_processed", target="ocr_upload", detail={"field_count": len(fields)})`. Zero PHI recorded.
- **Response Payload (200 OK)**:
```json
{
  "upload_id": "up-7b3f9c21-82d1-4a1b-9f12-98e3b1a201d4",
  "document_type_guess": "prescription",
  "fields": [
    {
      "field_id": "fld-1",
      "kind": "medication",
      "name": "Metformin",
      "dosage": "500 mg twice daily",
      "status": "active",
      "confidence": "high",
      "evidence": "Tab. Metformin 500mg 1+0+1"
    },
    {
      "field_id": "fld-2",
      "kind": "medication",
      "name": "Glimepiride",
      "dosage": "1 mg once daily in the morning",
      "status": "active",
      "confidence": "high",
      "evidence": "Tab. Glimepiride 1mg 1+0+0"
    }
  ],
  "unmatched_lines": [
    "Advice: Monitor fasting sugar daily"
  ],
  "expires_at": "2026-10-30T14:30:00Z"
}
```

### 3.2 `POST /api/me/record/uploads/{upload_id}/confirm`
- **Authorization**: `require_role("patient")`.
- **Request Body**:
```json
{
  "confirm": [
    {
      "field_id": "fld-1",
      "value": "500 mg twice daily",
      "unit": null
    }
  ],
  "remove": [
    "fld-2"
  ]
}
```
- **Error Conditions**:
  - Upload not found or expired $\rightarrow$ `404 Not Found` / `410 Gone: {"detail": "upload_expired"}`.
  - Upload belongs to different user $\rightarrow$ `403 Forbidden: {"detail": "access_denied"}`.
  - Already confirmed $\rightarrow$ `409 Conflict: {"detail": "already_confirmed"}`.
- **Validation Strategy**: **Partial Acceptance**. Valid confirmed items are committed to Local Store; invalid items are rejected with clinical error reasons.
- **Audit Logging**: `append_audit(actor_user_id=user_id, action="ocr_upload_confirmed", target="ocr_upload", detail={"saved": len(saved), "rejected": len(rejected)})`.

---

## 4. Provider Interface & Configuration

### 4.1 Python Abstract Protocol (For Testing & Server Fallbacks)
```python
from abc import ABC, abstractmethod

class OcrProvider(ABC):
    @abstractmethod
    def extract_text(self, image_bytes: bytes, lang_hint: str = "en") -> str:
        """Extracts verbatim raw text from an image (used for CI and server evaluation)."""
        pass
```

### 4.2 Implementations
1. `FakeOcrProvider`: Deterministic in-memory mock used for hermetic CI tests. Configurable via canned dictionaries.
2. `RapidOcrProvider`: Server-side fallback provider using `rapidocr-onnxruntime`.

### 4.3 Environment Variables
- `OCR_ENABLED`: `false` (default) or `true`.
- `OCR_PROVIDER`: `tesseractjs` (default for frontend client-side), `rapidocr`, or `fake`.
- Config status endpoint `GET /api/admin/config-status` displays `OCR_ENABLED` and `OCR_PROVIDER` as `SET` or `NOT SET` only.

---

## 5. Image Processing & Privacy Boundary

1. **Zero Server Image Storage**:
   - Because Tesseract.js runs in the client's browser, **no photo is ever sent to or stored on our servers**.
   - The server network layer receives only plain text strings.
2. **On-Device Memory Management**:
   - The client Web Worker loads the image into a local canvas element.
   - Upon completion of recognition, the image buffer is dereferenced and garbage collected.
3. **Zero-PHI Audit Logs**:
   - All audit entries record operation counts only:
     - `ocr_upload_processed`: `{"field_count": 2}`
     - `ocr_upload_confirmed`: `{"saved": 2, "rejected": 0}`

---

## 6. Privacy Notice Copy (On-Device Local Processing)

Because all OCR computation runs on-device on the user's phone, no third-party hosted consent is necessary. A clear, reassuring local-processing notification is displayed:

- **English**:
  > *"Your prescription or report is scanned entirely on your device. Your photo is never uploaded or saved to our servers. Only the text you review and confirm will be added to your record."*
- **Urdu**:
  > *"آپ کا نسخہ یا رپورٹ مکمل طور پر آپ کے فون پر پڑھی جاتی ہے۔ آپ کی تصویر ہمارے سرور پر کبھی نہیں بھیجی جاتی۔ صرف وہی معلومات محفوظ ہوں گی جن کی آپ خود تصدیق کریں گے۔"*
- **Roman Urdu**:
  > *"Aap ka nuskha ya report mukammal tor par aap ke phone par parhi jati hai. Aap ki tasweer server par upload nahi hoti. Sirf wohi maloomat save hongi jin ki aap khud tasdeeq karenge."*

---

## 7. Edge Cases & Patient Error Messaging

| Failure Case | Detection Mechanism | English Message | Urdu Message |
|---|---|---|---|
| **Slow or Old Phone** | Worker progress timer $> 8$ seconds | "Scanning is taking longer than usual on your device. Please wait or cancel." | اسکیننگ میں معمول سے زیادہ وقت لگ رہا ہے۔ براہ کرم انتظار کریں یا منسوخ کریں۔ |
| **Language Model Download Failed** | Worker fetch error for `.traineddata.gz` | "Could not download the reading files. Please check your internet connection and retry." | پڑھنے کی فائلیں ڈاؤن لوڈ نہیں ہو سکیں۔ براہ کرم انٹرنیٹ چیک کر کے دوبارہ کوشش کریں۔ |
| **No Internet on First Use** | IndexedDB empty and navigator.onLine is false | "An internet connection is required the first time you use document scanning." | دستاویز اسکیننگ پہلی بار استعمال کرنے کے لیے انٹرنیٹ ضروری ہے۔ |
| **Blurry or Unfocused Photo** | Low OCR token confidence $(< 40\%)$ | "The photo is too blurry to read clearly. Please retake it in good light." | تصویر واضح نہیں ہے۔ براہ کرم اچھی روشنی میں دوبارہ تصویر لیں۔ |
| **Doctor Cursive Handwriting** | Unmatched lines or low recognition confidence | "Some handwritten notes could not be deciphered. You can add them manually below." | کچھ ہاتھ سے لکھی ہوئی تحریر نہیں پڑھی جا سکی۔ آپ اسے نیچے خود درج کر سکتے ہیں۔ |
| **Unit Ambiguity (mmol/L vs mg/dL)** | Value $< 35$ without explicit unit | "Glucose value is in an ambiguous range. Please confirm whether this is mmol/L or mg/dL." | گلوکوز کی یونٹ واضح نہیں ہے۔ براہ کرم تصدیق کریں کہ یہ mmol/L ہے یا mg/dL۔ |
| **Nothing Found** | 0 fields and 0 unmatched lines | "No medical information could be extracted from this image." | اس تصویر سے کوئی طبی معلومات حاصل نہیں ہو سکیں۔ |

---

## 8. Day 7 Implementation Build Plan

### 8.1 Files to Create
1. `app/lib/ocr/worker.ts`:
   - Dedicated Web Worker wrapping `tesseract.js` with IndexedDB model caching.
2. `app/components/OcrConfirmScreen.tsx`:
   - Screen component with field review, inline edits, RTL Urdu support, and confirm/reject dispatch.
3. `backend-poc-technical/test_ocr_upload.py`:
   - Hermetic test suite covering `POST /api/me/record/uploads` (text payload), validation errors (413, 422, 503), field extraction, and Schema v14 `record_edits` provenance.
4. `tests/ocr-confirm.test.tsx`:
   - Vitest component tests verifying rendering, inline fixes, Urdu text, and accessibility.

### 8.2 Files to Modify
1. `backend-poc-technical/main.py`:
   - Implement `POST /api/me/record/uploads` accepting `{text, document_type_hint, lang}`.
   - Implement `POST /api/me/record/uploads/{upload_id}/confirm`.
   - Expose `ocr_enabled: bool` on `GET /api/me/record`.
2. `app/components/HealthRecordScreen.tsx`:
   - Add "Upload report or prescription" button gated on isolated mode + `ocr_enabled`.
3. `app/lib/api.ts`:
   - Add client methods `uploadRecordText` and `confirmRecordUpload`.
4. `.github/workflows/ci.yml`:
   - Add `backend-poc-technical/test_ocr_upload.py` to hermetic pytest suite.
