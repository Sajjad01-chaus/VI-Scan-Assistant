param([ValidateSet('live','fixture')][string]$Mode='fixture')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Create .venv and install requirements-lock.txt first; see README.md.'
}
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
    Push-Location frontend
    try { npm.cmd ci --no-audit --no-fund; npm.cmd run build } finally { Pop-Location }
}
$env:AI_MODE=$Mode
& .\.venv\Scripts\python.exe -m backend.bootstrap
if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
