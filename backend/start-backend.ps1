param([switch]$CheckOnly, [switch]$Migrate)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$backendRoot = $PSScriptRoot
$pythonPath = Join-Path $backendRoot 'venv313\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonPath = Join-Path $backendRoot '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the backend Python environment first; see README.md.'
}
Push-Location $backendRoot
try {
    & $pythonPath -m app.preflight --require-bot --database --allow-pending-migrations
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if ($CheckOnly) { return }
    if ($Migrate) {
        & $pythonPath -m app.db_bootstrap
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    & $pythonPath -m app.preflight --require-bot --database
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8001
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
