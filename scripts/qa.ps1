[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "status", "restart", "open", "help")]
    [string]$Command = "status",
    [string]$ExpedientId,
    [string]$ClusterDataPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$Config = Import-PowerShellDataFile (Join-Path $PSScriptRoot "qa.config.psd1")
$RuntimeRoot = Join-Path $ProjectRoot "data\\tmp\\qa_runtime"
$LogsRoot = Join-Path $RuntimeRoot "logs"
$MetadataPath = Join-Path $RuntimeRoot "launcher.json"
$DatabaseUrl = "postgresql+psycopg://$($Config.RuntimeRole)@$($Config.DatabaseHost):$($Config.DatabasePort)/$($Config.Database)"
$ApiUrl = "http://$($Config.DatabaseHost):$($Config.BackendPort)"
$EventUrl = "ws://$($Config.DatabaseHost):$($Config.BackendPort)/_event"

function Normalize-LauncherProcessEnvironment {
    $pathEntries = @([Environment]::GetEnvironmentVariables("Process").GetEnumerator() |
        Where-Object { [string]$_.Key -ieq "Path" })
    if ($pathEntries.Count -le 1) { return }
    $preferred = $pathEntries | Where-Object { [string]$_.Key -ceq "Path" } | Select-Object -First 1
    if (-not $preferred) { $preferred = $pathEntries | Select-Object -First 1 }
    [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
    [Environment]::SetEnvironmentVariable("Path", [string]$preferred.Value, "Process")
}

Normalize-LauncherProcessEnvironment

function Write-QAHeader {
    Write-Host "DatosEnOrden QA"
    Write-Host ("-" * 15)
}

function Fail-QA([string]$Message) {
    throw "QA launcher: $Message"
}

function Get-PgCtlPath {
    $candidate = "C:\\Program Files\\PostgreSQL\\17\\bin\\pg_ctl.exe"
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    $command = Get-Command pg_ctl.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    Fail-QA "No se encontró pg_ctl.exe de PostgreSQL 17."
}

function Get-PsqlPath {
    $candidate = "C:\\Program Files\\PostgreSQL\\17\\bin\\psql.exe"
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    $command = Get-Command psql.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    Fail-QA "No se encontró psql.exe de PostgreSQL 17."
}

function Get-PgIsReadyPath {
    $candidate = "C:\\Program Files\\PostgreSQL\\17\\bin\\pg_isready.exe"
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    $command = Get-Command pg_isready.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    Fail-QA "pg_isready.exe de PostgreSQL 17 no está disponible."
}

function Get-PostgresPath {
    $candidate = "C:\\Program Files\\PostgreSQL\\17\\bin\\postgres.exe"
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    $command = Get-Command postgres.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    Fail-QA "postgres.exe de PostgreSQL 17 no está disponible."
}

function Get-ConfiguredClusterDataPath {
    $relative = if ($ClusterDataPath) { $ClusterDataPath } else { $Config.QAClusterDataRelativePath }
    $path = [IO.Path]::GetFullPath((Join-Path $ProjectRoot $relative))
    if (-not $path.StartsWith($ProjectRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Fail-QA "El clúster QA debe estar dentro del repositorio."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $path "PG_VERSION"))) {
        Fail-QA "No existe un clúster PostgreSQL QA certificado en '$path'. No se creará uno nuevo."
    }
    return $path
}

function Get-ListenerPid([int]$Port) {
    # Reflex/Vite can bind an IPv6 wildcard that also serves 127.0.0.1.
    # Any listener on a reserved QA port must therefore be inspected, not just
    # a listener reported with an IPv4 local address.
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) { return [int]$listener.OwningProcess }
    # Some Windows sessions cannot query a listener owned by another security
    # context through Get-NetTCPConnection. Netstat is used only to detect the
    # occupied reserved port; subsequent ownership checks still fail closed.
    $escapedPort = [regex]::Escape(":$Port")
    $netstatLine = netstat -ano -p tcp 2>$null |
        Where-Object { $_ -match "^\s*TCP\s+.+$escapedPort\s+.+LISTENING\s+(\d+)\s*$" } |
        Select-Object -First 1
    if ($netstatLine -match "LISTENING\s+(\d+)\s*$") { return [int]$Matches[1] }
    return $null
}

function Get-ProcessInfo([int]$ProcessId) {
    Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
}

function Test-OwnedRuntimeProcess([int]$ProcessId, [ValidateSet("backend", "frontend")] [string]$Kind) {
    $process = Get-ProcessInfo $ProcessId
    if (-not $process) { return $false }
    $command = [string]$process.CommandLine
    $root = [regex]::Escape($ProjectRoot)
    if ($Kind -eq "backend") {
        return $command -match $root -and $command -match "reflex" -and $command -match "--backend-only"
    }
    return $command -match $root -and ($command -match "\\.web" -or $command -match "--frontend-only")
}

function Get-DescendantProcessIds([int]$ParentProcessId) {
    $children = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { [int]$_.ParentProcessId -eq $ParentProcessId })
    $result = @()
    foreach ($child in $children) {
        $result += Get-DescendantProcessIds ([int]$child.ProcessId)
        $result += [int]$child.ProcessId
    }
    return $result
}

function Test-OwnedRuntimeDescendant([int]$ProcessId) {
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $process) { return $false }
    $info = Get-ProcessInfo $ProcessId
    if ($info -and [string]$info.CommandLine -match [regex]::Escape($ProjectRoot)) { return $true }
    try {
        return @($process.Modules | Where-Object {
            $_.FileName -like (Join-Path $ProjectRoot ".venv\*")
        }).Count -gt 0
    }
    catch { return $false }
}

function Read-Metadata {
    if (-not (Test-Path -LiteralPath $MetadataPath)) { return $null }
    try { return Get-Content -Raw -LiteralPath $MetadataPath | ConvertFrom-Json }
    catch { Fail-QA "La metadata QA local está dañada; no se adoptarán procesos." }
}

function Test-MetadataMatchesConfig($Metadata) {
    return $Metadata -and
        $Metadata.project_root -eq $ProjectRoot -and
        $Metadata.database -eq $Config.Database -and
        [int]$Metadata.database_port -eq [int]$Config.DatabasePort -and
        $Metadata.runtime_role -eq $Config.RuntimeRole -and
        [int]$Metadata.backend_port -eq [int]$Config.BackendPort -and
        [int]$Metadata.frontend_port -eq [int]$Config.FrontendPort
}

function Save-Metadata([int]$BackendPid, [int]$FrontendPid, [int]$PostgresPid, [string]$ClusterPath) {
    New-Item -ItemType Directory -Force -Path $RuntimeRoot, $LogsRoot | Out-Null
    [ordered]@{
        project_root = $ProjectRoot
        cluster_data_path = $ClusterPath
        database = $Config.Database
        database_port = $Config.DatabasePort
        runtime_role = $Config.RuntimeRole
        backend_port = $Config.BackendPort
        frontend_port = $Config.FrontendPort
        backend_listener_pid = $BackendPid
        frontend_listener_pid = $FrontendPid
        postgres_listener_pid = $PostgresPid
        started_at = (Get-Date).ToString("o")
    } | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $MetadataPath
}

function Invoke-QAPsql([string]$Sql) {
    $psql = Get-PsqlPath
    $output = & $psql -X -q -t -A -h $Config.DatabaseHost -p $Config.DatabasePort -U $Config.RuntimeRole -d $Config.Database -c $Sql 2>&1
    if ($LASTEXITCODE -ne 0) { Fail-QA "No se pudo verificar la DB QA con el rol runtime: $output" }
    return ($output | Out-String).Trim()
}

function Test-QADatabase {
    $sql = 'select current_database() || ''|'' || current_user || ''|'' || has_database_privilege(current_database(), ''CONNECT'') || ''|'' || has_schema_privilege(''public'', ''USAGE'') || ''|'' || has_table_privilege(''real_expedient'', ''SELECT'') || ''|'' || has_table_privilege(''real_expedient'', ''INSERT'');'
    $result = Invoke-QAPsql $sql
    $parts = $result.Split('|')
    if ($parts.Count -ne 6 -or $parts[0] -ne $Config.Database -or $parts[1] -ne $Config.RuntimeRole) {
        Fail-QA "La conexión no acredita la base QA y el rol runtime esperados."
    }
    if ($parts[2] -ne 'true' -or $parts[3] -ne 'true' -or $parts[4] -ne 'true' -or $parts[5] -ne 'false') {
        Fail-QA "El rol QA runtime no tiene los privilegios de sólo lectura esperados."
    }
}

function Test-QAPostgresOwnership([string]$ClusterPath) {
    $listenerPid = Get-ListenerPid $Config.DatabasePort
    if (-not $listenerPid) { return $false }
    $pidFile = Join-Path $ClusterPath "postmaster.pid"
    if (-not (Test-Path -LiteralPath $pidFile)) { return $false }
    $pidFileLines = @(Get-Content -LiteralPath $pidFile)
    if ($pidFileLines.Count -lt 2 -or [int]$pidFileLines[0] -ne $listenerPid) { return $false }
    if ([IO.Path]::GetFullPath($pidFileLines[1]) -ne [IO.Path]::GetFullPath($ClusterPath)) { return $false }
    $process = Get-Process -Id $listenerPid -ErrorAction SilentlyContinue
    if (-not $process -or [IO.Path]::GetFullPath($process.Path) -ne [IO.Path]::GetFullPath((Get-PostgresPath))) { return $false }
    return $true
}

function Test-QAPostgres([string]$ClusterPath) {
    if (-not (Test-QAPostgresOwnership $ClusterPath)) { return $false }
    $pgIsReady = Get-PgIsReadyPath
    & $pgIsReady -h $Config.DatabaseHost -p $Config.DatabasePort -d $Config.Database *> $null
    return $LASTEXITCODE -eq 0
}

function Start-QAPostgres([string]$ClusterPath) {
    if (Get-ListenerPid $Config.DatabasePort) {
        if (-not (Test-QAPostgres $ClusterPath)) {
            Fail-QA "El puerto $($Config.DatabasePort) está ocupado por un PostgreSQL no certificable."
        }
        return
    }
    New-Item -ItemType Directory -Force -Path $LogsRoot | Out-Null
    # pg_ctl start can fail after a reboot when Windows rejects its restricted token.
    $postgres = Get-PostgresPath
    Start-Process -FilePath $postgres -ArgumentList @("-D", $ClusterPath, "-p", $Config.DatabasePort, "-h", $Config.DatabaseHost) -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $LogsRoot "postgres.out.log") -RedirectStandardError (Join-Path $LogsRoot "postgres.err.log") | Out-Null
    for ($i = 0; $i -lt 20; $i++) {
        if (Test-QAPostgres $ClusterPath) { return }
        Start-Sleep -Milliseconds 500
    }
    Fail-QA "PostgreSQL QA no quedó listo dentro del timeout."
}

function Stop-QAPostgres([string]$ClusterPath) {
    $pgCtl = Get-PgCtlPath
    foreach ($mode in @("fast", "immediate")) {
        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            & $pgCtl stop -D $ClusterPath -m $mode -t 15 2>&1 | Out-Null
        }
        finally {
            $ErrorActionPreference = $previousPreference
        }
        for ($i = 0; $i -lt 20; $i++) {
            if (-not (Get-ListenerPid $Config.DatabasePort)) { return }
            Start-Sleep -Milliseconds 500
        }
    }
    if (Test-QAPostgresOwnership $ClusterPath) {
        $listenerPid = Get-ListenerPid $Config.DatabasePort
        Stop-Process -Id $listenerPid -ErrorAction Stop
        for ($i = 0; $i -lt 20; $i++) {
            if (-not (Get-ListenerPid $Config.DatabasePort)) { return }
            Start-Sleep -Milliseconds 500
        }
    }
    Fail-QA "PostgreSQL QA certificado no se detuvo."
}

function Test-Http([string]$Url) {
    try { return (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 $Url).StatusCode -eq 200 }
    catch { return $false }
}

function Wait-Http([string]$Url, [string]$Name) {
    for ($i = 0; $i -lt 40; $i++) {
        if (Test-Http $Url) { return }
        Start-Sleep -Milliseconds 500
    }
    Fail-QA "$Name no respondió dentro del timeout. Revisa $LogsRoot"
}

function Test-GeneratedEventUrl {
    $envPath = Join-Path $ProjectRoot ".web\\env.json"
    if (-not (Test-Path -LiteralPath $envPath)) { return $false }
    try { return ((Get-Content -Raw -LiteralPath $envPath | ConvertFrom-Json).EVENT -eq $EventUrl) }
    catch { return $false }
}

function Set-QARuntimeEnvironment {
    $env:API_URL = $ApiUrl
    $env:REFLEX_API_URL = $ApiUrl
    $env:DATABASE_URL = $DatabaseUrl
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
}

function Invoke-QAFrontendGeneration {
    Set-QARuntimeEnvironment
    New-Item -ItemType Directory -Force -Path $LogsRoot | Out-Null
    $compileLog = Join-Path $LogsRoot "compile.log"
    & (Join-Path $ProjectRoot ".venv\Scripts\reflex.exe") compile --no-rich *> $compileLog
    if ($LASTEXITCODE -ne 0) {
        Fail-QA "La compilación Reflex QA falló. Revisa $compileLog"
    }
    $routePath = Join-Path $ProjectRoot ".web\app\routes\[laboratory].[expedient]._index.jsx"
    if (-not (Test-Path -LiteralPath $routePath)) {
        Fail-QA "La compilación QA no generó la ruta laboratory/expedient esperada."
    }
}

function Start-QAProcess([ValidateSet("backend", "frontend")] [string]$Kind) {
    $port = if ($Kind -eq "backend") { $Config.BackendPort } else { $Config.FrontendPort }
    $existing = Get-ListenerPid $port
    if ($existing) { Fail-QA "El puerto $port está ocupado por un proceso no adoptado. Ejecuta status y resuelve su ownership." }
    Set-QARuntimeEnvironment
    $reflexArgs = if ($Kind -eq "backend") {
        @("run", "--backend-only", "--backend-port", "$port", "--backend-host", $Config.DatabaseHost, "--loglevel", "warning")
    } else {
        @("run", "--frontend-only", "--frontend-port", "$port", "--loglevel", "warning")
    }
    New-Item -ItemType Directory -Force -Path $LogsRoot | Out-Null
    Start-Process -FilePath (Join-Path $ProjectRoot ".venv\\Scripts\\reflex.exe") -ArgumentList $reflexArgs -WorkingDirectory $ProjectRoot -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogsRoot "$Kind.out.log") -RedirectStandardError (Join-Path $LogsRoot "$Kind.err.log") | Out-Null
    $url = if ($Kind -eq "backend") { "$ApiUrl/ping" } else { "http://$($Config.DatabaseHost):$port/" }
    Wait-Http $url $Kind
    $listenerPid = Get-ListenerPid $port
    if (-not $listenerPid -or -not (Test-OwnedRuntimeProcess $listenerPid $Kind)) {
        Fail-QA "No se pudo certificar ownership del proceso $Kind."
    }
    return $listenerPid
}

function Stop-OwnedListener([int]$Port, [ValidateSet("backend", "frontend")] [string]$Kind, $Metadata) {
    $listenerPid = Get-ListenerPid $Port
    if (-not $listenerPid) { return }
    if (-not (Test-MetadataMatchesConfig $Metadata) -or [int]$Metadata."${Kind}_listener_pid" -ne $listenerPid -or -not (Test-OwnedRuntimeProcess $listenerPid $Kind)) {
        Fail-QA "No se detendrá el PID ${listenerPid}: ownership QA no verificable."
    }
    # Stop the certified root first. Granian workers can respawn while their
    # parent remains alive; only persistent, already-known descendants are
    # considered afterwards.
    $descendants = @(Get-DescendantProcessIds $listenerPid)
    if (Get-Process -Id $listenerPid -ErrorAction SilentlyContinue) {
        Stop-Process -Id $listenerPid -ErrorAction Stop
    }
    Start-Sleep -Milliseconds 500
    foreach ($descendantPid in $descendants) {
        if (Get-Process -Id $descendantPid -ErrorAction SilentlyContinue) {
            if (-not (Test-OwnedRuntimeDescendant $descendantPid)) {
                Fail-QA "No se detendrá el hijo persistente ${descendantPid}: ownership QA no verificable."
            }
            Stop-Process -Id $descendantPid -ErrorAction Stop
        }
    }
}

function Invoke-QAStatus {
    $cluster = Get-ConfiguredClusterDataPath
    $metadata = Read-Metadata
    $postgres = Test-QAPostgres $cluster
    $db = $false
    if ($postgres) { try { Test-QADatabase; $db = $true } catch { $db = $false } }
    $backend = (Test-Http "$ApiUrl/ping")
    $frontend = (Test-Http "http://$($Config.DatabaseHost):$($Config.FrontendPort)/")
    $event = $backend -and $frontend -and (Test-GeneratedEventUrl)
    Write-QAHeader
    Write-Host ("PostgreSQL   {0} {1}:{2}" -f $(if($postgres){'OK'}else{'FAIL'}), $Config.DatabaseHost, $Config.DatabasePort)
    Write-Host ("Database     {0} {1}" -f $(if($db){'OK'}else{'FAIL'}), $Config.Database)
    Write-Host ("Role         {0} {1}" -f $(if($db){'OK'}else{'FAIL'}), $Config.RuntimeRole)
    Write-Host ("Backend      {0} {1}" -f $(if($backend){'OK'}else{'FAIL'}), $ApiUrl)
    Write-Host ("Frontend     {0} http://$($Config.DatabaseHost):$($Config.FrontendPort)" -f $(if($frontend){'OK'}else{'FAIL'}))
    Write-Host ("Reflex event {0} {1}" -f $(if($event){'OK'}else{'FAIL'}), $(if($event){$EventUrl}else{'no certificado'}))
    return [bool]($postgres -and $db -and $backend -and $frontend -and $event)
}

function Invoke-QAStart {
    $cluster = Get-ConfiguredClusterDataPath
    $metadata = Read-Metadata
    $healthy = Invoke-QAStatus
    if ($healthy) {
        $backendPid = Get-ListenerPid $Config.BackendPort
        $frontendPid = Get-ListenerPid $Config.FrontendPort
        if (Test-MetadataMatchesConfig $metadata -and (Test-OwnedRuntimeProcess $backendPid "backend") -and (Test-OwnedRuntimeProcess $frontendPid "frontend")) {
            Write-Host "`nQA ya está corriendo."
            return
        }
        Fail-QA "Hay un runtime saludable sin metadata QA certificada; no se adoptará automáticamente."
    }
    if ((Get-ListenerPid $Config.BackendPort) -or (Get-ListenerPid $Config.FrontendPort)) {
        Fail-QA "Un puerto QA está ocupado por un proceso no certificable."
    }
    Start-QAPostgres $cluster
    Test-QADatabase
    Invoke-QAFrontendGeneration
    $backendPid = Start-QAProcess "backend"
    $frontendPid = Start-QAProcess "frontend"
    if (-not (Test-GeneratedEventUrl)) { Fail-QA "La configuración Reflex generada no apunta al backend QA esperado ($EventUrl)." }
    Save-Metadata $backendPid $frontendPid (Get-ListenerPid $Config.DatabasePort) $cluster
    Write-Host "`nQA lista.`n"
    Write-Host "Abrir: http://$($Config.DatabaseHost):$($Config.FrontendPort)"
}

function Invoke-QAStop {
    $metadata = Read-Metadata
    if (-not (Test-MetadataMatchesConfig $metadata)) { Fail-QA "No hay metadata QA certificada; no se detendrá ningún proceso." }
    Stop-OwnedListener $Config.FrontendPort "frontend" $metadata
    Stop-OwnedListener $Config.BackendPort "backend" $metadata
    if ((Get-ListenerPid $Config.FrontendPort) -or (Get-ListenerPid $Config.BackendPort)) {
        Fail-QA "Un listener QA persistió después del cierre; metadata conservada para diagnóstico seguro."
    }
    $cluster = Get-ConfiguredClusterDataPath
    if (Test-QAPostgres $cluster) {
        Stop-QAPostgres $cluster
    }
    Remove-Item -LiteralPath $MetadataPath -Force -ErrorAction SilentlyContinue
    Write-Host "QA detenida."
}

function Invoke-QAOpen {
    if (-not (Test-Http "http://$($Config.DatabaseHost):$($Config.FrontendPort)/")) {
        Fail-QA "QA no está corriendo. Ejecuta: .\\scripts\\qa.ps1 start"
    }
    $url = "http://$($Config.DatabaseHost):$($Config.FrontendPort)"
    if ($ExpedientId) {
        $url += "/laboratory/expedient?id=" + [uri]::EscapeDataString($ExpedientId)
    }
    Start-Process $url
    Write-Host "Abierto: $url"
}

switch ($Command) {
    "help" { Write-Host "Uso: .\\scripts\\qa.ps1 {start|stop|status|restart|open} [-ExpedientId ID] [-ClusterDataPath PATH]" }
    "status" { if (-not (Invoke-QAStatus)) { exit 1 } }
    "start" { Invoke-QAStart }
    "stop" { Invoke-QAStop }
    "restart" { Invoke-QAStop; Invoke-QAStart }
    "open" { Invoke-QAOpen }
}
