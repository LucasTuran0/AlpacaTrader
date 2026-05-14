# railway-setup.ps1
# Run this from the repo root AFTER running `railway login` in your terminal.
# Usage: .\scripts\railway-setup.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Confirm-Logged-In {
    $result = railway whoami 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Not logged in to Railway. Run `railway login` first, then re-run this script."
        exit 1
    }
    Write-Host "Logged in as: $result" -ForegroundColor Green
}

function Prompt-Secret {
    param([string]$Name, [string]$Hint = "")
    $val = Read-Host "Enter $Name$( if ($Hint) { " ($Hint)" } else { "" } )"
    if (-not $val) { Write-Error "$Name cannot be empty."; exit 1 }
    return $val
}

# ── 1. Auth check ────────────────────────────────────────────────────────────
Write-Host "`n=== Step 1: Verifying Railway auth ===" -ForegroundColor Cyan
Confirm-Logged-In

# ── 2. Project ───────────────────────────────────────────────────────────────
Write-Host "`n=== Step 2: Project setup ===" -ForegroundColor Cyan
$choice = Read-Host "Create a new Railway project, or link an existing one? [new/link]"
if ($choice -eq "link") {
    railway link
} else {
    railway init --name AlpacaTrader
}

# ── 3. Collect secrets ───────────────────────────────────────────────────────
Write-Host "`n=== Step 3: API secrets (from https://app.alpaca.markets and Google Cloud) ===" -ForegroundColor Cyan
$alpacaKey    = Prompt-Secret "ALPACA_API_KEY"    "Alpaca paper/live key"
$alpacaSecret = Prompt-Secret "ALPACA_API_SECRET" "Alpaca paper/live secret"
$alpacaPaper  = Read-Host "ALPACA_PAPER (true/false, default=true)"
if (-not $alpacaPaper) { $alpacaPaper = "true" }
$googleKey    = Prompt-Secret "GOOGLE_API_KEY"    "Google Gemini API key"

# ── 4. Backend service ───────────────────────────────────────────────────────
Write-Host "`n=== Step 4: Creating backend service ===" -ForegroundColor Cyan
railway add --service backend

Write-Host "Setting backend env vars..." -ForegroundColor Yellow
railway variable set "ALPACA_API_KEY=$alpacaKey"       --service backend
railway variable set "ALPACA_API_SECRET=$alpacaSecret" --service backend
railway variable set "ALPACA_PAPER=$alpacaPaper"       --service backend
railway variable set "GOOGLE_API_KEY=$googleKey"       --service backend

# ── 5. Backend domain ────────────────────────────────────────────────────────
Write-Host "`n=== Step 5: Generating backend domain ===" -ForegroundColor Cyan
$backendDomainRaw = railway domain --service backend --json 2>&1
Write-Host "Raw domain output: $backendDomainRaw"
# Also print it non-json so it's visible
railway domain --service backend

$backendDomain = Read-Host "Paste the backend domain printed above (e.g. something.up.railway.app)"
$backendHttps  = "https://$backendDomain"
$backendWss    = "wss://$backendDomain"

# ── 6. Backend volume (SQLite persistence) ───────────────────────────────────
Write-Host "`n=== Step 6: Attaching SQLite volume ===" -ForegroundColor Cyan
railway volume add --mount-path /app/backend --service backend

# ── 7. Deploy backend ────────────────────────────────────────────────────────
Write-Host "`n=== Step 7: Deploying backend ===" -ForegroundColor Cyan
railway up --service backend --detach
Write-Host "Backend deploy triggered. Check logs: railway logs --service backend" -ForegroundColor Yellow

# ── 8. Frontend service ──────────────────────────────────────────────────────
Write-Host "`n=== Step 8: Creating frontend service ===" -ForegroundColor Cyan
railway add --service frontend

Write-Host "Setting frontend env vars..." -ForegroundColor Yellow
railway variable set "VITE_BACKEND_URL=$backendHttps"                  --service frontend
railway variable set "VITE_WS_URL=$backendWss"                         --service frontend
railway variable set "RAILWAY_DOCKERFILE_PATH=/frontend/Dockerfile"    --service frontend

# ── 9. Frontend domain ───────────────────────────────────────────────────────
Write-Host "`n=== Step 9: Generating frontend domain ===" -ForegroundColor Cyan
railway domain --service frontend

$frontendDomain = Read-Host "Paste the frontend domain printed above (e.g. something.up.railway.app)"
$frontendHttps  = "https://$frontendDomain"

# ── 10. Update backend CORS ──────────────────────────────────────────────────
Write-Host "`n=== Step 10: Setting CORS on backend to allow frontend domain ===" -ForegroundColor Cyan
railway variable set "ALLOWED_ORIGINS=$frontendHttps" --service backend

# ── 11. Deploy frontend ──────────────────────────────────────────────────────
Write-Host "`n=== Step 11: Deploying frontend ===" -ForegroundColor Cyan
railway up --service frontend --detach
Write-Host "Frontend deploy triggered. Check logs: railway logs --service frontend" -ForegroundColor Yellow

# ── Done ─────────────────────────────────────────────────────────────────────
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  All Railway services deployed!" -ForegroundColor Green
Write-Host "  Frontend: $frontendHttps" -ForegroundColor Green
Write-Host "  Backend:  $backendHttps" -ForegroundColor Green
Write-Host "  Logs:     railway logs --service backend" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nGitHub Autodeploy is active — every push to main will redeploy both services automatically." -ForegroundColor Cyan
