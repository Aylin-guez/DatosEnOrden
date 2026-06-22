$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ReflexApp = Join-Path $ProjectRoot "web\reflex_app"

Write-Host "DatosEnOrden Reflex dev runner"
Write-Host "Project root: $ProjectRoot"
Write-Host "Reflex app:   $ReflexApp"
Write-Host ""

Set-Location $ReflexApp

Write-Host "Environment summary"
python (Join-Path $ProjectRoot "scripts\web\check_reflex_environment.py")
Write-Host ""

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:REFLEX_FRONTEND_PORT = "3001"
$env:REFLEX_BACKEND_PORT = "8001"

Write-Host "Starting Reflex with fixed local ports"
Write-Host "Frontend: http://localhost:3001"
Write-Host "Backend:  http://localhost:8001"
Write-Host ""

python -m reflex run --frontend-port 3001 --backend-port 8001
