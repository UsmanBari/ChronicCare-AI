# Deployment & Operations Guide

## 1. Architecture Overview (5-Line Summary)
1. **Frontend**: Next.js 14 static HTML/JS export hosted globally on **Netlify**.
2. **Backend**: Python FastAPI microservice deployed on a **Render** Web Service (root directory `backend-poc-technical`).
3. **Database**: Managed **Aiven MySQL** with TLS encryption for persistent relational data and audit trails.
4. **Authentication**: **Firebase Authentication** verifying client tokens with RS256 JWT validation on the backend.
5. **Continuous Deployment**: GitHub Actions CD triggers Render webhooks on successful main branch builds and executes automated post-deploy smoke tests.

---

## 2. Environment Variables Specification

> **CRITICAL SECURITY RULE:** Never paste, commit, or log real secrets, keys, or credentials. All values must be configured directly in the provider dashboard settings.

### A. Render (Backend Service)

| Variable Name | Required in Production | Description | Where to Obtain |
|---|---|---|---|
| `APP_ENV` | **Yes** | Set to `production` to activate production guards. | Render Dashboard -> Environment. Set value to `production`. |
| `DB_BACKEND` | **Yes** | Database engine selector. Must be set to `mysql`. | Render Dashboard -> Environment. Set value to `mysql`. |
| `MYSQL_URL` | **Yes** | Connection string for Aiven MySQL database. | Aiven Console -> Service Overview -> Connection Details. |
| `MYSQL_SSL_CA` | **Yes** | CA certificate path or content for TLS validation. | Aiven Console -> Download CA Certificate. |
| `FIREBASE_PROJECT_ID` | **Yes** | Firebase Project ID for JWT token verification. | Firebase Console -> Project Settings -> General. |
| `CORS_ALLOWED_ORIGINS` | **Yes** | Comma-separated list of allowed frontend origins (e.g., Netlify domain). | Netlify Dashboard -> Site Overview (e.g., `https://example.netlify.app`). |
| `DEMO_ROLE_MAP` | No | Comma-separated mapping of demo emails to roles (`email:role`). | Administrative setup. |
| `GROQ_API_KEY` | No | API key for live LLM reasoning and Groq Whisper speech-to-text. Never commit; set in Render dashboard only. | Groq Console -> API Keys. |
| `GROQ_MODEL` | No | LLM model name (e.g., `llama-3.3-70b-versatile`). | Groq Documentation. |
| `GROQ_STT_MODEL` | No | Whisper STT model name (defaults to `whisper-large-v3-turbo`). | Groq Documentation. |
| `FHIR_BASE_URL` | No | Optional default FHIR server URL override. | Target hospital or sandbox endpoint. |
| `REQUIRE_INCLUSION` | No | Enforces adult inclusion confirmation on check-in start (`1` or `0`). | Internal policy. |

### B. Netlify (Frontend Site)

| Variable Name | Required in Production | Description | Where to Obtain |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | **Yes** | Full URL of the deployed Render backend API. | Render Dashboard -> Web Service URL (e.g. `https://example.onrender.com`). |
| `NEXT_PUBLIC_AUTH_MODE` | **Yes** | Authentication mode: `firebase` for production, `mock` for local demos. | Set to `firebase`. |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | **Yes** | Web API Key for Firebase Authentication. | Firebase Console -> Project Settings -> General -> Your Apps. |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | **Yes** | Firebase Auth domain. | Firebase Console -> Project Settings. |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | **Yes** | Firebase Project ID. | Firebase Console -> Project Settings. |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | **Yes** | Firebase Storage Bucket. | Firebase Console -> Project Settings. |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | **Yes** | Firebase Messaging Sender ID. | Firebase Console -> Project Settings. |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | **Yes** | Firebase Web App ID. | Firebase Console -> Project Settings. |
| `NEXT_PUBLIC_DEMO_PATIENT_EMAIL` | No | Optional suggested default patient email on login screen. | Optional convenience. |
| `NEXT_PUBLIC_DEMO_PROVIDER_EMAIL` | No | Optional suggested default provider email on login screen. | Optional convenience. |
| `NEXT_PUBLIC_DEMO_ADMIN_EMAIL` | No | Optional suggested default admin email on login screen. | Optional convenience. |

### C. GitHub Repository (Actions & CD)

| Variable / Secret | Type | Description |
|---|---|---|
| `RENDER_DEPLOY_HOOK_URL` | **Secret** | Render Deploy Hook URL to trigger zero-downtime rebuilds on CD. |
| `BACKEND_URL` | **Variable** | Public URL of Render backend (e.g. `https://example.onrender.com`). |
| `FRONTEND_URL` | **Variable** | Public URL of Netlify frontend (e.g. `https://example.netlify.app`). |

---

## 3. Platform Settings

### Render Web Service Settings
- **Root Directory**: `backend-poc-technical`
- **Environment**: Python 3 (Version 3.11 specified in `.python-version`)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/api/health`
- **Auto-Deploy**: **OFF** (Continuous deployment is orchestrated via GitHub Actions CD workflow and deploy hook).

### Netlify Settings
- **Base Directory**: `/` (repository root)
- **Build Command**: `npm run build`
- **Publish Directory**: `out`
- **Node Version**: 20 (configured in `netlify.toml`)

### Firebase Authorized Domains
In Firebase Console -> **Authentication** -> **Settings** -> **Authorized domains**, add your Netlify custom domain or `*.netlify.app` subdomain to allow OAuth and popup authentication.

---

## 4. First Deployment Step-by-Step Order

1. **Step 1: MySQL Pre-flight Check**:
   The human operator runs `scripts/mysql_preflight.py` in their local terminal with the production database settings to apply migrations and verify TLS connectivity:
   ```bash
   # In terminal with environment populated:
   python scripts/mysql_preflight.py
   ```
   *Note: `mysql_preflight.py` is fully idempotent. After any schema change (such as Schema Version 11), it can be re-run safely at any time to assert schema readiness and verify table structures without data loss.*
2. **Step 2: Deploy Backend to Render**:
   - Create Web Service in Render with the environment variables listed above.
   - Manually trigger first deploy.
   - Verify health check: `curl https://<your-render-app>.onrender.com/api/health` -> `{"status":"healthy"}`.
3. **Step 3: Deploy Frontend to Netlify**:
   - Link repository to Netlify with build command `npm run build` and publish directory `out`.
   - Add the `NEXT_PUBLIC_*` environment variables in Netlify site settings.
   - Trigger build and note the live Netlify domain URL.
4. **Step 4: Update CORS on Backend**:
   - In Render Dashboard, add the live Netlify URL (e.g., `https://chroniccare.netlify.app`) to `CORS_ALLOWED_ORIGINS`.
   - Render restarts the backend service with updated CORS origin permissions.
5. **Step 5: Run Post-Deployment Smoke Test**:
   - Execute the smoke test script:
   ```bash
   python scripts/smoke_test.py --backend https://<your-render-app>.onrender.com --frontend https://<your-netlify-app>.netlify.app
   ```

---

## 5. Diagnostic & Monitoring Tools

### Admin Config Status Endpoint
Admins can verify backend environment configuration safely at any time:
- **Endpoint**: `GET /api/admin/config-status`
- **Authorization**: Requires Bearer JWT with `admin` role.
- **Output**: Returns only setting names and booleans (e.g., `groq_configured: true`, `firebase_configured: true`, `mysql_configured: true`). Never returns secrets or connection strings.

### Running Opt-In Tests Against Development MySQL
To run hermetic + opt-in database tests against a dedicated development database (`chroniccare_dev`):
```bash
# Set environment targeting dev database (must end in _dev)
$env:DB_BACKEND="mysql"
$env:MYSQL_URL="mysql://user:pass@host:port/chroniccare_dev"
pytest test_mysql_store.py -v
```

---

## 6. Rollback Procedures

### Render Backend Rollback
1. Open Render Dashboard -> Select `chroniccare-backend` Web Service.
2. Navigate to the **Deploys** tab.
3. Find the last known healthy deployment commit and click **Rollback to this deploy**.

### Netlify Frontend Rollback
1. Open Netlify Dashboard -> Select `chroniccare-ai` Site.
2. Navigate to **Deploys**.
3. Locate the previous successful deploy, click on it, and click **Publish deploy**.

---

## 7. Free-Tier Operational Constraints & Pre-Demo Checklist

### Free-Tier Limits
- **Render Web Service Sleep**: Inactivity for 15 minutes causes the free instance to spin down. The first incoming request will experience cold-start latency of 30 to 60 seconds.
- **Ephemeral Storage**: Render free tier has no persistent local disk. All persistence must go through Aiven MySQL.

### "Before a Demonstration" Checklist
- [ ] **5 Minutes Before**: Open the Netlify frontend in a browser to trigger backend wake-up and warm the instance.
- [ ] **Aiven Database**: Confirm in the Aiven Console that the MySQL instance status is **Running**.
- [ ] **Smoke Test**: Run `python scripts/smoke_test.py --backend <BACKEND_URL> --frontend <FRONTEND_URL> --wait 60` from your console to verify all 5 systems are operational.
