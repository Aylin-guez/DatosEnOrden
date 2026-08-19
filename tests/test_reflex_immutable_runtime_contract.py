from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_prepare_exports_the_artifacts_required_by_backend_only_runtime() -> None:
    prepare = _text("scripts/deploy_release_ubuntu.sh")

    assert '"$python" -m reflex export --no-zip --env prod --no-ssr' in prepare
    assert '"$target/.web/backend/stateful_pages.json"' in prepare
    assert '"$target/.web/build/client/index.html"' in prepare
    assert "DATOSENORDEN_ENV=local" not in prepare
    assert '. "$ENV_FILE"' in prepare
    assert 'runuser -u "$APP_USER" --preserve-environment' in prepare
    assert 'install -d -o root -g "$APP_USER" -m 0755 "$APP_ROOT/releases"' in prepare
    assert prepare.index("reflex export") < prepare.index('chmod -R go-w "$target"')


def test_runtime_reads_the_immutable_export_and_writes_state_outside_release() -> None:
    service = _text("deployment/datosenorden.service")
    caddy = _text("deployment/Caddyfile")

    assert "WorkingDirectory=/opt/datosenorden/current" in service
    assert "REFLEX_WEB_WORKDIR=/opt/datosenorden/current/.web" in service
    assert "REFLEX_STATES_WORKDIR=/var/lib/datosenorden/reflex-states" in service
    assert "Environment=HOME=/var/lib/datosenorden" in service
    assert "StateDirectory=datosenorden" in service
    assert "--backend-only" in service
    assert "root * /opt/datosenorden/current/.web/build/client" in caddy
    assert caddy.index("handle @reflex_backend") < caddy.index("root * /opt/datosenorden/current/.web/build/client")


def test_readiness_targets_the_backend_health_route_not_static_frontend() -> None:
    smoke = _text("scripts/post_deploy_smoke.sh")

    assert 'READINESS_URL="${READINESS_URL:-http://127.0.0.1:3000/api/_health}"' in smoke
