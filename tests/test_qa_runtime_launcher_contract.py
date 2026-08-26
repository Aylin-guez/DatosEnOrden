from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = (ROOT / "scripts" / "qa.ps1").read_text(encoding="utf-8-sig")
CONFIG = (ROOT / "scripts" / "qa.config.psd1").read_text(encoding="utf-8-sig")


def test_launcher_uses_only_explicit_isolated_qa_settings() -> None:
    assert 'Database = "datosenorden_pytest_goldenqa"' in CONFIG
    assert 'DatabasePort = 55432' in CONFIG
    assert 'RuntimeRole = "deo_qa_runtime"' in CONFIG
    assert 'FrontendPort = 3003' in CONFIG
    assert 'BackendPort = 8004' in CONFIG
    assert "5432" not in SCRIPT
    assert "real_expedient" in SCRIPT
    assert "Join-Path $PSScriptRoot \"..\"" in SCRIPT
    assert "I:\\DatosEnOrden" not in SCRIPT


def test_launcher_sets_reflex_qa_environment_and_checks_generated_event_url() -> None:
    assert '$env:API_URL = $ApiUrl' in SCRIPT
    assert '$env:REFLEX_API_URL = $ApiUrl' in SCRIPT
    assert '$env:DATABASE_URL = $DatabaseUrl' in SCRIPT
    assert 'ws://$($Config.DatabaseHost):$($Config.BackendPort)/_event' in SCRIPT
    assert "Test-GeneratedEventUrl" in SCRIPT
    assert "$backend -and $frontend -and (Test-GeneratedEventUrl)" in SCRIPT


def test_launcher_generates_frontend_from_current_worktree_before_starting_processes() -> None:
    assert "function Invoke-QAFrontendGeneration" in SCRIPT
    generation_block = SCRIPT.split("function Invoke-QAFrontendGeneration", 1)[1].split("function Start-QAProcess", 1)[0]
    assert "Set-QARuntimeEnvironment" in generation_block
    assert "reflex.exe\") compile --no-rich" in generation_block
    assert "compile.log" in generation_block
    start_block = SCRIPT.split("function Invoke-QAStart", 1)[1].split("function Invoke-QAStop", 1)[0]
    assert start_block.index("Invoke-QAFrontendGeneration") < start_block.index('Start-QAProcess "backend"')


def test_launcher_starts_the_certified_cluster_without_pg_ctl_restricted_token() -> None:
    postgres_block = SCRIPT.split("function Start-QAPostgres", 1)[1].split("function Test-Http", 1)[0]
    assert "Get-PostgresPath" in SCRIPT
    assert "Start-Process -FilePath $postgres" in postgres_block
    assert "& $pgCtl start" not in postgres_block


def test_launcher_certifies_postgres_by_cluster_identity_and_readiness() -> None:
    postgres_block = SCRIPT.split("function Test-QAPostgres", 1)[1].split("function Start-QAPostgres", 1)[0]
    assert "postmaster.pid" in postgres_block
    assert "Get-PgIsReadyPath" in postgres_block
    assert "pg_ctl status" not in postgres_block
    assert "Test-QAPostgresOwnership" in SCRIPT


def test_launcher_uses_certified_fast_then_immediate_postgres_shutdown() -> None:
    stop_block = SCRIPT.split("function Stop-QAPostgres", 1)[1].split("function Test-Http", 1)[0]
    assert '@("fast", "immediate")' in stop_block
    assert "Test-QAPostgresOwnership $ClusterPath" in stop_block
    assert "Get-ListenerPid $Config.DatabasePort" in stop_block
    assert "Stop-Process -Id $listenerPid" in stop_block


def test_launcher_normalizes_duplicate_windows_path_entries_before_launching_children() -> None:
    assert "Normalize-LauncherProcessEnvironment" in SCRIPT
    assert 'SetEnvironmentVariable("PATH", $null, "Process")' in SCRIPT


def test_launcher_has_fail_closed_ownership_and_no_provisioning_path() -> None:
    assert "No se creará uno nuevo" in SCRIPT
    assert "no se adoptará automáticamente" in SCRIPT
    assert "Test-OwnedRuntimeProcess" in SCRIPT
    assert "Stop-OwnedListener" in SCRIPT
    assert "provision" not in SCRIPT.lower()
    assert "migrat" not in SCRIPT.lower()


def test_launcher_exposes_requested_commands_and_read_only_status() -> None:
    for command in ('"start"', '"stop"', '"status"', '"restart"', '"open"'):
        assert command in SCRIPT
    status_block = SCRIPT.split("function Invoke-QAStatus", 1)[1].split("function Invoke-QAStart", 1)[0]
    assert "Start-Process" not in status_block
    assert "Stop-Process" not in status_block


def test_launcher_start_is_idempotent_only_for_verified_metadata() -> None:
    assert "QA ya está corriendo" in SCRIPT
    assert "no se adoptará automáticamente" in SCRIPT


def test_launcher_detects_wildcard_listeners_on_reserved_qa_ports() -> None:
    listener_block = SCRIPT.split("function Get-ListenerPid", 1)[1].split("function Get-ProcessInfo", 1)[0]
    assert "-LocalPort $Port" in listener_block
    assert "-LocalAddress" not in listener_block
    assert "netstat -ano -p tcp" in listener_block


def test_launcher_stops_certified_root_before_only_verified_persistent_descendants() -> None:
    assert "Get-DescendantProcessIds" in SCRIPT
    assert "Test-OwnedRuntimeDescendant" in SCRIPT
    assert "metadata conservada para diagnóstico seguro" in SCRIPT
    stop_block = SCRIPT.split("function Stop-OwnedListener", 1)[1].split("function Invoke-QAStatus", 1)[0]
    assert stop_block.index("Stop-Process -Id $listenerPid") < stop_block.index("Test-OwnedRuntimeDescendant")
