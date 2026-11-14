<#
.SYNOPSIS
    ChronicCare AI — One-Command Local Demo Launcher (17 Nov FYP-1 Evaluation).

.DESCRIPTION
    Launches the entire ChronicCare AI research prototype hermetically on local Windows PowerShell.
    Strictly restricted to local SQLite. Never touches production MySQL or remote clouds.

.PARAMETER Seed
    If specified, re-seeds the local SQLite database with all 17 Nov demo personas and histories.

.EXAMPLE
    .\scripts\start_local_demo.ps1 -Seed
#>

[CmdletBinding()]
param(
    [switch]$Seed
)

# 1. Enforce UTF-8 encoding across PowerShell session
$env:PYTHONIOENCODING = "utf-8"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "CHRONICCARE AI — ONE-COMMAND LOCAL DEMO LAUNCHER (17 NOV EVALUATION)" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# Check if ports 3000 or 8000 are already in use
$busyPorts = @()
foreach ($p in @(3000, 8000)) {
    $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pidItem in $pids) {
            $proc = Get-Process -Id $pidItem -ErrorAction SilentlyContinue
            $procName = if ($proc) { $proc.ProcessName } else { "Unknown" }
            $busyPorts += "Port $p is in use by PID $pidItem ($procName)"
        }
    }
}
if ($busyPorts.Count -gt 0) {
    Write-Error ("REFUSING TO START: Ports 3000/8000 in use:`n" + ($busyPorts -join "`n") + "`nPlease stop existing processes before starting.")
    exit 1
}

# 2. Strict SQLite Guard — Refuse execution if MySQL is configured
$dbBackend = $env:DB_BACKEND
$mysqlUrl = $env:MYSQL_URL
Write-Host "[1/5] Verifying database isolation boundary..."
Write-Host "  DB_BACKEND : $(if ($dbBackend) { $dbBackend } else { 'sqlite (default)' })"
Write-Host "  MYSQL_URL  : $(if ($mysqlUrl) { 'SET' } else { 'NOT SET' })"

if ($dbBackend -eq "mysql" -or ($mysqlUrl -and $mysqlUrl.Trim() -ne "" -and $mysqlUrl.ToLower() -ne "none")) {
    Write-Error "REFUSING TO RUN ON MYSQL: Local demo is strictly restricted to local SQLite store."
    exit 1
}

# Ensure clean SQLite environment without remote credentials
$env:DB_BACKEND = "sqlite"
Remove-Item Env:MYSQL_URL -ErrorAction SilentlyContinue
Remove-Item Env:MYSQL_SSL_CA -ErrorAction SilentlyContinue

# 3. Verify Python 3.11 virtual environment
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $repoRoot "backend-poc-technical\.venv\Scripts\python.exe"
$venvActivate = Join-Path $repoRoot "backend-poc-technical\.venv\Scripts\Activate.ps1"

if (-not (Test-Path $venvPython)) {
    Write-Error "Backend virtual environment python.exe not found at: $venvPython"
    Write-Host "Please create the virtual environment before launching."
    exit 1
}

# 4. Initialize local SQLite schema
Write-Host "`n[2/5] Initializing local SQLite schema and migrations..."
& $venvPython (Join-Path $repoRoot "backend-poc-technical\init_local_db.py")
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to initialize local SQLite schema."
    exit 1
}

# 5. Optionally run seed script
if ($Seed) {
    Write-Host "`n[3/5] Seeding 17 Nov demo personas, check-ins, and OCR records..."
    & $venvPython (Join-Path $repoRoot "scripts\seed_demo_local.py") --reset
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Demo seed script reported errors."
        exit 1
    }
} else {
    Write-Host "`n[3/5] Skipping seed (pass -Seed to re-populate local demo personas)."
}

# 6. Launch Backend API Server in new window
Write-Host "`n[4/5] Starting FastAPI backend API server on port 8000 (new window)..."
$localDemoArg = ""
$cand1 = Join-Path $repoRoot "backend-poc-technical\.env.localdemo"
$cand2 = Join-Path $repoRoot ".env.localdemo"
if (Test-Path $cand1) {
    $localDemoArg = "--env-file .env.localdemo"
} elseif (Test-Path $cand2) {
    $localDemoArg = "--env-file '$cand2'"
}

$backendCmd = @"
`$env:PYTHONIOENCODING = 'utf-8'
`$env:DB_BACKEND = 'sqlite'
Remove-Item Env:MYSQL_URL -ErrorAction SilentlyContinue
Remove-Item Env:MYSQL_SSL_CA -ErrorAction SilentlyContinue
Set-Location '$repoRoot\backend-poc-technical'
Write-Host 'Starting ChronicCare AI FastAPI Backend (Local SQLite)...' -ForegroundColor Green
& '$venvPython' -m uvicorn main:app --port 8000 $localDemoArg --log-level info
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# 7. Launch Next.js Frontend Server in new window
Write-Host "[5/5] Starting Next.js frontend dev server on port 3000 (new window)..."
$frontendCmd = @"
`$env:NEXT_PUBLIC_API_BASE_URL = 'http://localhost:8000'
`$env:NEXT_PUBLIC_AUTH_MODE = 'firebase'
Set-Location '$repoRoot'
Write-Host 'Starting ChronicCare AI Next.js Frontend...' -ForegroundColor Cyan
npm run dev
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# 8. Health check polling
Write-Host "`nWaiting for backend health check at http://127.0.0.1:8000/api/health..."
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($resp.status -eq "ok" -or $resp.database -eq "ok") {
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($healthy) {
    Write-Host "`n================================================================================" -ForegroundColor Green
    Write-Host "LOCAL DEMO ENVIRONMENT READY FOR 17 NOV EVALUATION" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Green
    Write-Host "Patient / Provider Portal : http://localhost:3000"
    Write-Host "FastAPI Interactive Docs  : http://localhost:8000/docs"
    Write-Host "System Admin Config Status: http://localhost:8000/api/admin/config-status"
    Write-Host ""
    Write-Host "DEMO ACCOUNTS (Sign in via Firebase or local authentication):"
    Write-Host "  Provider Portal  : provider.demo@demo.care      (Elevated provider role)"
    Write-Host "  Admin Portal     : admin.demo@demo.care         (Elevated admin role)"
    Write-Host "  HTN Patient      : demo_patient_htn@demo.care   (Rising BP trend -> Yellow, BP chart, OCR med)"
    Write-Host "  DM Patient       : demo_patient_dm@demo.care    (Glucose history, High DM band -> Yellow, SHAP)"
    Write-Host "  Dual Patient     : demo_patient_dual@demo.care  (Both risk models evaluated, SOAP summary)"
    Write-Host "  Urdu Patient     : demo_patient_ur@demo.care    (Vernacular Urdu script checkin & guidance)"
    Write-Host "  Roman Urdu       : demo_patient_roman_ur@demo.care (Roman Urdu checkin & template)"
    Write-Host "  Emergency Bypass : demo_patient_emg@demo.care   (Red-flag acute chest pain -> 1122 screen)"
    Write-Host "  Rule R8 No-Read  : demo_patient_norx@demo.care  (No readings checkin -> Rule R8 wording)"
    Write-Host "  Cold Start (0)   : demo_patient_new@demo.care   (Clean onboarding state, 0 check-ins)"
    Write-Host "================================================================================`n"
} else {
    Write-Warning "Backend health check timed out. Please inspect the backend PowerShell window for logs."
}
