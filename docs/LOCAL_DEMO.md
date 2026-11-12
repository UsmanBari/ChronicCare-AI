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
Create `backend-poc-technical/.env.localdemo` by copying the template from `docs/local_demo.env.example` (or copying your Render backend environment).

When copying Render's environment, **CHANGE three critical things**:
1. **`APP_ENV` must NOT be production**: set `APP_ENV=local` (setting `production` causes startup to fail with `"DB_BACKEND must be set to 'mysql'"`).
2. **`CORS_ALLOWED_ORIGINS` must allow local frontend**: set `CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000` (Render's Netlify-only value causes the browser to block all calls and the frontend to display `"waking up the server"`).
3. **`FIREBASE_PROJECT_ID` must be filled**: copy your Firebase project ID from Render/Firebase console (leaving it empty returns `503 Authentication not configured`).

Other local demo settings:
- `DB_BACKEND=sqlite` (never include `MYSQL_URL` or `MYSQL_SSL_CA`).
- `GROQ_API_KEY=<copy from Render>`
- `GROQ_MODEL=<copy from Render>` (copy the exact model configured on Render).
- `DEMO_ROLE_MAP=<copy from Render>` (format: `provider.demo@demo.care:provider,admin.demo@demo.care:admin`).
- Feature flags: `RISK_ENABLED=true`, `RISK_CAN_RAISE=true`, `RISK_PATIENT_VISIBLE=true`, `TREND_CAN_RAISE=true`, `EXPLAIN_ENABLED=true`, `EXPLAIN_MODE=background`, `OCR_ENABLED=true`, `DANGER_WORDGROUPS_ENABLED=true`, `ORCHESTRATOR=graph`, `INTERVIEW_ENGINE=v2`.
- Optional acceptance keys (for unattended runs): `FIREBASE_WEB_API_KEY`, `LOCAL_PROVIDER_EMAIL`, `LOCAL_PROVIDER_PASSWORD`, `LOCAL_ADMIN_EMAIL`, `LOCAL_ADMIN_PASSWORD`.

*Note: `backend-poc-technical/.env.localdemo` is git-ignored (verified by `git check-ignore -v`). Never commit it.*

### Step 8: Demo Role Map & User Roles
Local authentication behaves exactly like the live deployed site:
- Any user who signs up receives the **patient** role by default (no manual account pre-creation needed).
- Elevated roles (provider and admin) are resolved deterministically from `DEMO_ROLE_MAP` using the user's email address.
- Ensure your `DEMO_ROLE_MAP` in `.env.localdemo` matches your Render configuration (e.g. `provider.demo@demo.care:provider,admin.demo@demo.care:admin`).

### Step 9: Verify Environment Keys (Zero-Leak Check)
Run this one-liner to verify all critical environment variable names are populated without printing any secrets:
```powershell
Get-Content backend-poc-technical\.env.localdemo | Where-Object { $_ -match '^[A-Z0-9_]+=' } | ForEach-Object { $k = $_.Split('=')[0]; $v = $_.Substring($k.Length + 1).Trim(); "$k : " + ($(if ($v) { "SET" } else { "EMPTY" })) }
```

### Step 10: Start the Local Backend API Server
In Terminal 1, activate the venv and start uvicorn:
```powershell
Set-Location "c:\Users\usmanbari\Desktop\Chronicare\backend-poc-technical"
.\.venv\Scripts\Activate.ps1
$env:DB_BACKEND = "sqlite"
Remove-Item Env:MYSQL_URL -ErrorAction SilentlyContinue
Remove-Item Env:MYSQL_SSL_CA -ErrorAction SilentlyContinue
python -m uvicorn main:app --port 8000 --env-file .env.localdemo --log-level info
```
Verify the server starts and logs:
`INFO: Uvicorn running on http://127.0.0.1:8000`

### Step 11: Start the Local Next.js Frontend
In Terminal 2, launch Next.js dev server explicitly targeted to the local backend:
```powershell
Set-Location "c:\Users\usmanbari\Desktop\Chronicare"
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000"
$env:NEXT_PUBLIC_AUTH_MODE = "firebase"
npm run dev
```

### Step 12: Verify Frontend DevTools Network Routing
1. Open your browser to `http://localhost:3000`.
2. Open DevTools (F12) -> **Network** tab.
3. Perform a login or navigate to a screen.
4. **Confirm:** All API HTTP requests route to `http://localhost:8000/api/...` and **never** to `onrender.com`.

### Step 13: Run the Automated Local Acceptance Suite (`local_acceptance.py`)
In Terminal 3, run the automated proof script:
```powershell
Set-Location "c:\Users\usmanbari\Desktop\Chronicare"
.\backend-poc-technical\.venv\Scripts\Activate.ps1

$env:FIREBASE_WEB_API_KEY = Read-Host "Firebase web API key"
$env:LOCAL_PROVIDER_EMAIL = Read-Host "Provider email"
$env:LOCAL_PROVIDER_PASSWORD = Read-Host "Provider password"
$env:LOCAL_ADMIN_EMAIL = Read-Host "Admin email"
$env:LOCAL_ADMIN_PASSWORD = Read-Host "Admin password"

python scripts/local_acceptance.py
```
- Note: Use plain `Read-Host` (do **not** use `-AsSecureString`, which stores literal `"System.Security.SecureString"` text).
- `FIREBASE_WEB_API_KEY` is the `NEXT_PUBLIC_FIREBASE_API_KEY` value from your root `.env.local` or Firebase Console -> Project settings -> Web API Key.
- Never type passwords anywhere except the terminal prompt.
- Temporary patient accounts created during the test run are automatically cleaned up via Firebase REST API (`accounts:delete`) at the end of the script.

### Step 14: Local Database Reset (Between Evaluation Rehearsals)
To reset the local database back to a clean baseline between test runs:
```powershell
# Stop uvicorn in Terminal 1
Remove-Item "backend-poc-technical\local_store.db" -ErrorAction SilentlyContinue
python backend-poc-technical\init_local_db.py
python scripts/rag/load_chunks.py --file (Join-Path $env:CHRONICCARE_DATA_DIR "rag\chunks.jsonl")
# Restart uvicorn in Terminal 1
```

### Step 15: Contingency — Groq LLM Rate Limit or Offline Demonstration
If Groq is rate-limited or Wi-Fi is unstable during the evaluation:
- The system is designed with a **deterministic template fallback**: when Groq is unavailable, times out, or encounters rate limits, `explain_jobs.py` automatically falls back to curated guideline templates in `rag/templates.json`.
- The safety triage level is **never** affected because triage is 100% deterministic ("the model proposes, the rules decide").
- To run completely offline without calling Groq, set `EXPLAIN_ENABLED=false` in `.env.localdemo` and restart uvicorn. Explanations will return vetted clinical templates without network dependency.
