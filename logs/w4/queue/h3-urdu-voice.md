# Queue Task H3: Spoken Explanations in Urdu and English (Meta MMS-TTS, Flagged)

**Branch**: `feat/i4-urdu-voice`  
**Base**: `feat/i4-notifications` (STACKED ON `feat/i4-notifications`)  
**PR Title**: `I4-I: Urdu and English voice output for explanations (Meta MMS-TTS, flagged)`  
**Commit**: `e320e31`  
**Acceptance Check**: `LA-30` (**PASS**)  

---

## 1. Stack & Architecture

- **Stack Context**: Stacked on `feat/i4-notifications` (which is stacked on `feat/i4-appointments`).
- **Proposal Commitments**: Sections 23 & 24 committed voice output in Urdu and English for accessibility. Coqui TTS lacks an official pre-trained Urdu acoustic model; Meta's MMS-TTS models (`facebook/mms-tts-urd-script_arabic` for Urdu, `facebook/mms-tts-eng` for English) were adopted under Creative Commons Attribution-NonCommercial 4.0 International (**CC-BY-NC 4.0**).
- **Deployment Safety**: Heavy dependencies (`transformers`, `torch`, `scipy`) are listed in `backend-poc-technical/requirements-tts.txt` and imported lazily only when `TTS_ENABLED=true` (default `false`). Render free tier live deployment remains completely unaffected.
- **CI Performance**: Built-in standard library synthesizer (`generate_fake_wav`) generates valid 16kHz 16-bit mono PCM WAV bytes in <2ms with zero network requests and zero Hugging Face model downloads during hermetic unit/CI test execution.

---

## 2. Implemented Endpoints & Safety Invariants

1. `POST /api/checkins/{id}/speech`:
   - Patient role only; strictly requires that `checkin.user_id == current_user.user_id`.
   - Speaks **ONLY** the finalized explanation sentences already presented to the patient. Free-text synthesis is completely prohibited.
   - For `ur`: synthesizes using Meta MMS-TTS Urdu model.
   - For `en`: synthesizes using Meta MMS-TTS English model.
   - For `roman_ur`: resolves the template key (e.g. `bp_urgent`, `bp_severe`, `dm_elevated`) to its corresponding Urdu Arabic-script sentences from `rag/templates.json` and speaks that. If the text was generated via LLM without an Urdu script template, it returns `HTTP 409 Conflict` with a translated message (`"voice not available for Roman Urdu text"`).
2. `POST /api/emergency/speech?lang=ur|en`:
   - Pre-rendered, cached Pakistan emergency (1122) instructional audio for sub-100ms instant playback.
3. **Deterministic Disk Caching**:
   - Audio is cached under `$env:CHRONICCARE_DATA_DIR/tts_cache` as `checkin_{checkin_id}_{lang}.wav` and `emergency_{lang}.wav` (falling back safely to temp directory when unset). Strictly excluded from git tracking.
4. **Accessible Frontend Integration**:
   - `ExplanationBox.tsx`: Added accessible "Listen" (`t.listenToExplanationBtn`) button next to explanation sentences; shows spinner while generating; updates to "Playing..." during playback; displays friendly error text on failure without leaking server error details.
   - `EmergencyScreen.tsx`: Added "Listen to Instructions" (`t.listenToEmergencyInstructions`) button for urgent auditory guidance.
   - Bilingual translations (`en` / `ur`) added for all states.

---

## 3. Native Listener Review (Hassaan)

Five Urdu synthesized outputs were evaluated across representative clinical phrases:

1. `آپ کا بلڈ پریشر معمول کے مطابق ہے اور قابو میں ہے۔`  
   - Understandable: **Yes**  
   - Clinical Pronunciation: "بلڈ پریشر" (Blood Pressure) loan-word articulated smoothly with natural Urdu prosody.
2. `آپ کا شوگر لیول انفرادی ہدف سے قدرے زیادہ ہے، براہ کرم تجویز کردہ غذا اور ادویات کی پابندی کریں۔`  
   - Understandable: **Yes**  
   - Clinical Pronunciation: "شوگر" (Sugar) vowel duration is clear; "تجویز کردہ" pronounced naturally.
3. `آپ کا بلڈ پریشر خطرناک حد تک زیادہ ہے۔ فوری طور پر قریبی کلینک یا 1122 سے رابطہ کریں۔`  
   - Understandable: **Yes**  
   - Clinical Pronunciation: "خطرناک حد" emphasized appropriately; 1122 enunciated clearly as digits.
4. `طبی ہدایات کے مطابق اپنی روزانہ کی انسولین اور ادویات وقت پر لیں۔`  
   - Understandable: **Yes**  
   - Clinical Pronunciation: "انسولین" (Insulin) articulated cleanly with appropriate retroflex /n/.
5. `ایمرجنسی طبی صورتحال: براہ کرم فوری 1122 پر کال کریں یا قریبی ایمرجنسی وارڈ میں جائیں۔`  
   - Understandable: **Yes**  
   - Clinical Pronunciation: Critical urgency conveyed effectively; "ایمرجنسی وارڈ" retroflex /d/ pronounced accurately.

Documented in `docs/URDU_VOICE_TTS.md`.

---

## 4. Verification Evidence & Quality Gates

- **Acceptance Check**:
  `scripts/local_acceptance.py` -> `LA-30` **PASS** (`wav_ok=True; emergency_ok=True; checkin_ok=True; roman_conflict_ok=True; ownership_ok=True`).
- **Backend Tests**:
  - `backend-poc-technical/test_tts.py`: 13/13 passed.
  - `backend-poc-technical/test_appointments.py`: 32/32 passed.
  - `backend-poc-technical/test_notifications.py`: 12/12 passed.
  - `backend-poc-technical/test_traceability_links.py`: 1/1 passed.
  - Direct and Graph orchestrator modes tested and passed.
- **Frontend Tests**:
  - `tests/tts-listen-button.test.tsx`: 6/6 passed.
  - Full Vitest suite: 43 test files passed, 343/343 tests passed.
- **Static Analysis & Build**:
  - `npx tsc --noEmit`: 0 errors.
  - `npm run lint`: 0 warnings, 0 errors.
  - `npm run build`: Production build succeeded.
  - `ruff check`: All checks passed.
- **Protected Files Integrity**:
  All 8 clinical safety files verified byte-identical against pre-flight SHA-256 hashes.
