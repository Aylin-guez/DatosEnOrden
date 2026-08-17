from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_preprovisioning_scripts_use_immutable_release_contracts() -> None:
    deploy = _text("scripts/deploy_release_ubuntu.sh")
    activate = _text("scripts/activate_release_ubuntu.sh")
    rollback = _text("scripts/rollback_release_ubuntu.sh")
    assert "--sha256" in deploy
    assert "ARTIFACT_INTEGRITY_FAILURE" in deploy
    assert "git pull" not in deploy
    assert "git clone" not in deploy
    assert "pip install -e" not in deploy
    assert "Unable to inspect artifact archive" in deploy
    assert "Archive contains unsafe paths" in deploy
    assert "--prepare" in deploy
    assert "--activate" not in deploy
    assert ".deo-release-ready" in deploy
    assert "pip install" not in activate
    assert "mv -Tf" in activate
    assert "restore_old_current" in activate
    assert "post_deploy_smoke.sh" in activate
    assert "alembic" not in activate
    assert "import_production_data" not in activate
    assert "Database state was not changed" in rollback
    assert "activate_release_ubuntu.sh" in rollback


def test_production_reflex_runtime_is_exact_and_uses_current_single_port_contract() -> None:
    project = _text("pyproject.toml")
    service = _text("deployment/datosenorden.service")
    assert '"reflex==0.9.8"' in project
    assert "reflex run --env prod --frontend-port 3000" in service
    assert "--single-port" not in service


def test_preprovisioning_pack_keeps_services_and_database_private() -> None:
    service = _text("deployment/datosenorden.service")
    postgres = _text("scripts/configure_postgres_beta.sh")
    firewall = _text("scripts/configure_ufw.sh")
    smoke = _text("scripts/post_deploy_smoke.sh")
    caddy = _text("deployment/Caddyfile")
    assert "User=datosenorden" in service
    assert "WorkingDirectory=/opt/datosenorden/current" in service
    assert "EnvironmentFile=/etc/datosenorden/beta.env" in service
    assert "--backend-host 127.0.0.1" in service
    assert "PASSWORD_FILE" in postgres
    assert "ALTER SYSTEM SET listen_addresses = '127.0.0.1'" in postgres
    assert "PostgreSQL is publicly bound" in postgres
    assert "--confirmed-ssh" in firewall
    assert "ufw allow 80/tcp" in firewall
    assert "ufw allow 443/tcp" in firewall
    assert "Existing UFW rules reference 3000 or 5432" in firewall
    assert "private_ports" in smoke
    assert "MIN_MEMORY_KIB" in smoke
    assert "MIN_DISK_KIB" in smoke
    assert "beta.datosenorden.cl {" in caddy
    assert "reverse_proxy 127.0.0.1:3000" in caddy
    assert "\ndatosenorden.cl {" not in caddy
    assert "\nwww.datosenorden.cl {" not in caddy
    assert "Strict-Transport-Security" not in caddy


def test_preprovisioning_scripts_are_portable_and_do_not_reference_private_repos() -> None:
    paths = (
        "scripts/host_preflight_ubuntu.sh",
        "scripts/configure_ufw.sh",
        "scripts/configure_postgres_beta.sh",
        "scripts/deploy_release_ubuntu.sh",
        "scripts/activate_release_ubuntu.sh",
        "scripts/rollback_release_ubuntu.sh",
        "scripts/post_deploy_smoke.sh",
        "scripts/server_setup_ubuntu.sh",
    )
    forbidden = ("F:\\\\", "I:\\\\", "DatosEnOrdenCore", "DatosEnOrdenBricks", "git clone", "git pull")
    for path in paths:
        text = _text(path)
        assert not any(marker in text for marker in forbidden), path


def test_bootstrap_does_not_enable_caddy_or_firewall_before_configuration() -> None:
    bootstrap = _text("scripts/server_setup_ubuntu.sh")
    assert "systemctl enable --now postgresql" in bootstrap
    assert "systemctl enable --now caddy" not in bootstrap
    assert "ufw --force enable" not in bootstrap
    assert "INSTALL_LIBREOFFICE=\"${INSTALL_LIBREOFFICE:-0}\"" in bootstrap


def test_host_preflight_separates_minimum_and_recommended_capacity() -> None:
    preflight = _text("scripts/host_preflight_ubuntu.sh")
    assert "minimum_cpu_count=2" in preflight
    assert "recommended_cpu_count=3" in preflight
    assert "minimum_memory_kib=3600000" in preflight
    assert "recommended_memory_kib=7600000" in preflight
    assert "recommended_swap_kib=1048576" in preflight
    assert "fail capacity_blocking_cpu" in preflight
    assert "fail capacity_blocking_memory" in preflight
    assert "warn capacity_cpu_below_recommended" in preflight
    assert "warn capacity_memory_below_recommended" in preflight
    assert "warn capacity_swap_below_recommended" in preflight


def test_public_launch_runbook_uses_verified_artifact_not_a_mutable_checkout() -> None:
    runbook = _text("docs/VPS_GO_LIVE_STEPS.md")
    assert "sha256sum -c" in runbook
    assert "tar -xOf /secure-upload/datosenorden.tar" in runbook
    assert "git clone" not in runbook
    assert "git pull" not in runbook
    assert "git checkout" not in runbook
