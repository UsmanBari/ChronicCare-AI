# ChronicCare AI — Local Full-Stack Evaluation Runbook

> **FYP-1 Evaluation Runbook (17 Nov Demo on Usman's Laptop)**  
> This runbook provides the exact, reproducible, step-by-step instructions to run the entire ChronicCare AI system locally on Windows PowerShell using pure SQLite.
> It requires zero production access and runs 100% hermetically offline on the laptop.

---

### Step 1: Open PowerShell and Navigate to Workspace Root
```powershell
Set-Location "c:\Users\usmanbari\Desktop\Chronicare"
$env:PYTHONIOENCODING = "utf-8"
```

### Step 2: Ensure Isolated Production Safety (Strip MySQL Environment)
Ensure no remote production database credentials can be picked up:
```powershell
$env:DB_BACKEND = "sqlite"
Remove-Item Env:MYSQL_URL -ErrorAction SilentlyContinue
Remove-Item Env:MYSQL_SSL_CA -ErrorAction SilentlyContinue
```

### Step 3: Activate Python 3.11 Virtual Environment
```powershell
.\backend-poc-technical\.venv\Scripts\Activate.ps1
```

### Step 4: Verify OCR & System Dependencies
Ensure all core and optional OCR dependencies are installed:
```powershell
pip install -r backend-poc-technical/requirements.txt
pip install -r backend-poc-technical/requirements-ocr.txt
```

### Step 5: Initialize Local SQLite Database
Run the local schema migration and database setup:
```powershell
python backend-poc-technical/init_local_db.py
```

### Step 6: Load Guideline Knowledge Chunks into Local SQLite
Load the licensed medical guideline chunks into your local database:
```powershell
$env:DB_BACKEND = "sqlite"
python scripts/rag/load_chunks.py --file (Join-Path $env:CHRONICCARE_DATA_DIR "rag\chunks.jsonl")
```

### Step 7: Configure Local Environment (`backend-poc-technical/.env.localdemo`)
1. Create `backend-poc-technical/.env.localdemo` by copying the template from `docs/local_demo.env.example`.
2. Fill in the required keys:
   - `FIREBASE_PROJECT_ID=<your-firebase-project-id>`
   - `GROQ_API_KEY=<your-groq-api-key>`
   - `GROQ_MODEL=llama3-70b-8192` (or current Groq model)
   - `CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`
   - `DEMO_ROLE_MAP=doctor.sana@demo.care:provider,admin.supervisor@demo.care:admin`
   - Feature flags: `RISK_ENABLED=true`, `RISK_CAN_RAISE=true`, `RISK_PATIENT_VISIBLE=true`, `TREND_CAN_RAISE=true`, `EXPLAIN_ENABLED=true`, `EXPLAIN_MODE=background`, `OCR_ENABLED=true`, `DANGER_WORDGROUPS_ENABLED=true`, `ORCHESTRATOR=graph`, `INTERVIEW_ENGINE=v2`.
3. Do **NOT** include `MYSQL_URL` or `MYSQL_SSL_CA`.
4. Note: `backend-poc-technical/.env.localdemo` is git-ignored (verified by `git check-ignore -v`). Never commit it.

### Step 8: Setup Designated Fake Demo Accounts in Firebase
Ensure the following 4 fake demo accounts exist in your Firebase Authentication console (used for evaluation):
1. **Isolated Patient:** `patient.isolated@demo.care` (Role: patient by default; no EHR link)
2. **Connected Patient:** `patient.connected@demo.care` (Role: patient by default; linked to `ehr-sim-001` in demo)
3. **Provider:** `doctor.sana@demo.care` (Email mapped to `provider` in `DEMO_ROLE_MAP`)
4. **Admin:** `admin.supervisor@demo.care` (Email mapped to `admin` in `DEMO_ROLE_MAP`)

Format for `DEMO_ROLE_MAP` (keys by email, parsed in `backend-poc-technical/main.py:1075`):
```text
DEMO_ROLE_MAP=doctor.sana@demo.care:provider,admin.supervisor@demo.care:admin
```
*(Never put passwords in any file; enter them via shell variables or interactive prompt).*

### Step 9: Start the Local Backend API Server
In Terminal 1, run the FastAPI backend on port 8000 using `--env-file`:
```powershell
Set-Location "c:\Users\usmanbari\Desktop\Chronicare\backend-poc-technical"
uvicorn main:app --port 8000 --env-file .env.localdemo
```
Verify the server starts and logs:
`INFO: Uvicorn running on http://127.0.0.1:8000`

### Step 10: Start the Local Next.js Frontend
In Terminal 2, launch Next.js dev server explicitly targeted to the local backend:
```powershell
Set-Location "c:\Users\usmanbari\Desktop\Chronicare"
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000"
$env:NEXT_PUBLIC_AUTH_MODE = "firebase"
npm run dev
```

### Step 11: Verify Frontend DevTools Network Routing
1. Open your browser to `http://localhost:3000`.
2. Open DevTools (F12) -> **Network** tab.
3. Perform a login or navigate to a screen.
4. **Confirm:** All API HTTP requests route to `http://localhost:8000/api/...` and **never** to `onrender.com`.

### Step 12: Run the Automated Local Acceptance Suite (`local_acceptance.py`)
In Terminal 3, run the automated proof script:
```powershell
Set-Location "c:\Users\usmanbari\Desktop\Chronicare"
.\backend-poc-technical\.venv\Scripts\Activate.ps1
$env:FIREBASE_WEB_API_KEY = Read-Host "Paste Firebase Web API Key"
$env:LOCAL_PROVIDER_EMAIL = "doctor.sana@demo.care"
$env:LOCAL_PROVIDER_PASSWORD = Read-Host "Enter local provider password" -AsSecureString
$env:LOCAL_ADMIN_EMAIL = "admin.supervisor@demo.care"
$env:LOCAL_ADMIN_PASSWORD = Read-Host "Enter local admin password" -AsSecureString

python scripts/local_acceptance.py
```
*(The script creates fresh temporary patient accounts for isolated tests and lists them for cleanup).*

### Step 13: Local Database Reset (Between Evaluation Rehearsals)
To reset the local database back to a clean baseline between test runs:
```powershell
# Stop uvicorn in Terminal 1
Remove-Item "backend-poc-technical\local_store.db" -ErrorAction SilentlyContinue
python backend-poc-technical\init_local_db.py
python scripts/rag/load_chunks.py --file (Join-Path $env:CHRONICCARE_DATA_DIR "rag\chunks.jsonl")
# Restart uvicorn in Terminal 1
```

### Step 14: Contingency — Groq LLM Rate Limit or Offline Demonstration
If Groq is rate-limited or Wi-Fi is unstable during the evaluation:
- The system is designed with a **deterministic template fallback**: when Groq is unavailable, `explain_jobs.py` automatically falls back to curated guideline templates in `rag/templates.json`.
- The safety triage level is **never** affected because triage is 100% deterministic ("the model proposes, the rules decide").
- To demonstrate fallback explicitly, set `LLM_PROVIDER=template` in `.env.localdemo` and restart uvicorn. The explanation status will return `ready` using vetted clinical templates.

