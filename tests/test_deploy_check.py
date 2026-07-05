from pathlib import Path
import importlib.util
import sys
from types import SimpleNamespace


def _load_script():
    script_path = Path("scripts") / "deploy_check.py"
    spec = importlib.util.spec_from_file_location("deploy_check", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_deploy_check_documents_required_env_in_example(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    env = tmp_path / ".env.example"
    env.write_text(
        "DATABASE_URL=postgresql://example\n"
        "DATOSENORDEN_ENV=production\n"
        "DATOSENORDEN_PUBLIC_BASE_URL=https://datosenorden.cl\n"
        "DATOSENORDEN_SUPPORT_URL=https://link.mercadopago.cl/datosenorden\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)

    result = module._env_check()

    assert result.ok is True
    assert "DATOSENORDEN_PUBLIC_BASE_URL" in result.detail
    assert "DATOSENORDEN_SUPPORT_URL" in result.detail


def test_deploy_check_requires_go_live_pack_files(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    files = []
    for rel_path in (
        "deployment/production.env.example",
        "deployment/datosenorden.service",
        "deployment/Caddyfile",
        "scripts/server_setup_ubuntu.sh",
        "scripts/healthcheck_public.py",
        "scripts/backup_postgres.sh",
        "docs/VPS_GO_LIVE_STEPS.md",
    ):
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
        files.append(path)

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "DEPLOYMENT_FILES", tuple(files))

    result = module._deployment_pack_check()

    assert result.ok is True
    assert "deployment/production.env.example" in result.detail


def test_deploy_check_requires_published_pdf_asset(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    published = tmp_path / "published"
    published.mkdir()
    for name in ("reading.json", "document_view.json"):
        (published / name).write_text("{}", encoding="utf-8")
    (published / "document.pdf").write_bytes(b"%PDF")
    asset = tmp_path / "assets" / "official_documents" / "senado-docto-9000-mensaje_mocion" / "document.pdf"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF")
    monkeypatch.setattr(module, "PUBLISHED_DIR", published)
    monkeypatch.setattr(module, "ASSET_PDF", asset)

    result = module._document_check()

    assert result.ok is True
    assert "PDF asset ok" in result.detail


def test_deploy_check_calls_prelaunch_public_check(monkeypatch) -> None:
    module = _load_script()
    calls = []

    def fake_run(command, cwd, capture_output, text, check, timeout):  # noqa: ANN001
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="prelaunch_public_check:\n  ok - done", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module._prelaunch_check()

    assert result.ok is True
    assert calls == [[sys.executable, "scripts/prelaunch_public_check.py"]]


def test_deploy_check_requires_public_launch_assets(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    assets = []
    for name in ("favicon.ico", "apple-touch-icon.png", "icon-192.png", "icon-512.png", "og-image.png", "site.webmanifest", "robots.txt", "sitemap.xml"):
        asset = tmp_path / "assets" / name
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text("ok", encoding="utf-8")
        assets.append(asset)

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "PUBLIC_ASSETS", tuple(assets))

    result = module._public_asset_check()

    assert result.ok is True
    assert "manifest" in result.detail


def test_deploy_check_recognizes_multiline_public_routes(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    app = tmp_path / "reflex_app" / "reflex_app.py"
    app.parent.mkdir(parents=True)
    app.write_text(
        "\n\n".join(
            f"""@rx.page(
    route=\"{route}\",
    title=\"x\",
)
def page_{index}():
    return None"""
            for index, route in enumerate(module.PUBLIC_ROUTES, start=1)
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)

    result = module._route_check()

    assert result.ok is True
    assert "/chronology" in result.detail
