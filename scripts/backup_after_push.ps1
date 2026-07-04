$ErrorActionPreference = "Stop"

$source = "I:\DatosEnOrden"
$backup = "I:\DatosEnOrden_BACKUP_SAFE"

Write-Host "Actualizando backup seguro..." -ForegroundColor Cyan

robocopy $source $backup /MIR `
  /XD .git node_modules .pytest-tmp .pytest_cache __pycache__ .web .states `
  /XF .env .sync_state.json `
  /R:1 /W:1

Write-Host "Backup listo en $backup" -ForegroundColor Green