# Local Setup Verified

## Backend setup

Working directory: `backend-poc-technical`

| Command | Observed result |
|---|---|
| `python -m venv .venv` | NOT DONE: output was not captured in this report. |
| `.venv\Scripts\Activate.ps1` | NOT DONE: activation output was not captured in this report. |
| `pip install -r requirements.txt` | NOT DONE: the installation output was not captured in this report. |
| `copy .env.example .env` | NOT DONE: the command result was not captured in this report. No secrets were added to this report. |
| `python init_local_db.py` | NOT DONE: the command result was not captured in this report. |
| `python -m pytest -q test_triage_protocol.py` | PASS: 74 tests passed in 0.32 seconds. |
| `uvicorn main:app --reload --port 8000` | The server was running locally on port 8000. |
| `GET http://127.0.0.1:8000/api/health` | PASS: HTTP 200; `{"status":"healthy","service":"chroniccare-backend","version":"0.1.0"}` |
| `GET http://127.0.0.1:8000/health` | FAIL: HTTP 404. The application exposes `/api/health`, not `/health`. |

The browser also requested `/favicon.ico`, which returned HTTP 404. This did not affect the backend health endpoint.

## Environment

- OS: Windows PowerShell
- Python: 3.12.2
- Node: v22.16.0

## Problems

- The planned `/health` URL returned HTTP 404 because the backend route is `/api/health`. Verified the working endpoint at `http://127.0.0.1:8000/api/health`.
- `/favicon.ico` returned HTTP 404 from the browser request. This was unrelated to the API health check.
- Running `npm run dev` from `C:\Users\Dell\Documents` produced `npm error Missing script: "dev"` because the command was outside the repository. Fixed by running it from `C:\Users\Dell\Documents\ChronicCare-AI`.
- Running `npm run dev` from the repository root before installing dependencies produced `'next' is not recognized as an internal or external command, operable program or batch file.` Fixed by running `npm install` from the repository root.
- `npm install` printed deprecation warnings, including `eslint@8.57.1`; setup continued and the frontend and tests ran successfully. The generated `package-lock.json` change was discarded to keep this branch documentation-only.

## Frontend setup

Working directory: repository root, `C:\Users\Dell\Documents\ChronicCare-AI`

| Command | Observed result |
|---|---|
| `npm install` | Completed. npm printed deprecation warnings for several packages, including `eslint@8.57.1`; no secrets were added to this report. |
| `npm run dev` from `C:\Users\Dell\Documents` | FAIL: `npm error Missing script: "dev"` because this was not the repository root. |
| `npm run dev` from the repository root before installation | FAIL: `'next' is not recognized as an internal or external command` because dependencies were not installed. |
| `npm run dev` from the repository root after installation | PASS: the frontend responded with HTTP 200 at `http://127.0.0.1:3000`. |
| `npm test` | PASS: 10 test files and 97 tests passed. |

The dependency installation initially modified `package-lock.json`; that generated change was discarded so this documentation-only branch did not include an unrelated tracked-file change.
