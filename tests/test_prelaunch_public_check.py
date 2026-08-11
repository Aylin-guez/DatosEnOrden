from pathlib import Path
import importlib.util
import sys
from types import SimpleNamespace


def _load_script():
    script_path = Path("scripts") / "prelaunch_public_check.py"
    spec = importlib.util.spec_from_file_location("prelaunch_public_check", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_prelaunch_public_check_validates_required_env_and_documents(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    env = tmp_path / ".env.example"
    env.write_text(
        "DATOSENORDEN_ENV=production\n"
        "DATABASE_URL=postgresql://example\n"
        "DATOSENORDEN_DATABASE_URL=postgresql://example\n"
        "DATOSENORDEN_PUBLIC_BASE_URL=https://datosenorden.cl\n"
        "DATOSENORDEN_SUPPORT_URL=https://link.mercadopago.cl/datosenorden\n",
        encoding="utf-8",
    )
    published = tmp_path / "published"
    published.mkdir()
    reading = published / "reading.json"
    document_view = published / "document_view.json"
    reading.write_text("{}", encoding="utf-8")
    document_view.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(module, "ENV_EXAMPLE", env)
    monkeypatch.setattr(module, "PUBLISHED_READING", reading)
    monkeypatch.setattr(module, "PUBLISHED_DOCUMENT_VIEW", document_view)

    assert module._env_example_check().ok is True
    assert module._published_document_check().ok is True


def test_prelaunch_public_check_validates_stable_document_source(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    published = tmp_path / "published"
    published.mkdir()
    reading = published / "reading.json"
    document_view = published / "document_view.json"
    pdf = published / "document.pdf"
    asset = tmp_path / "assets" / "document.pdf"
    reading.write_text("{}", encoding="utf-8")
    document_view.write_text("{}", encoding="utf-8")
    pdf.write_bytes(b"%PDF")
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF")

    monkeypatch.setattr(module, "PUBLISHED_READING", reading)
    monkeypatch.setattr(module, "PUBLISHED_DOCUMENT_VIEW", document_view)
    monkeypatch.setattr(module, "PUBLISHED_PDF", pdf)
    monkeypatch.setattr(module, "PUBLIC_PDF_ASSET", asset)

    result = module._document_source_stability_check()

    assert result.ok is True
    assert "incoming/processing not required" in result.detail
    assert "PDF is published" in result.detail


def test_prelaunch_public_check_pdf_is_optional_but_asset_required_when_present(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    pdf = tmp_path / "document.pdf"
    asset = tmp_path / "assets" / "document.pdf"

    monkeypatch.setattr(module, "PUBLISHED_PDF", pdf)
    monkeypatch.setattr(module, "PUBLIC_PDF_ASSET", asset)

    missing_pdf = module._pdf_strategy_check()
    assert missing_pdf.ok is True
    assert "falls back" in missing_pdf.detail

    pdf.write_bytes(b"%PDF")
    missing_asset = module._pdf_strategy_check()
    assert missing_asset.ok is False
    assert "missing public asset copy" in missing_asset.detail

    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"%PDF")
    assert module._pdf_strategy_check().ok is True


def test_prelaunch_public_check_detects_tracked_cache(monkeypatch) -> None:
    module = _load_script()
    monkeypatch.setattr(module, "_git_lines", lambda *args: ["src/pkg/__pycache__/x.pyc", ".bun-cache/x"])

    result = module._tracked_cache_check()

    assert result.ok is False
    assert "__pycache__" in result.detail
    assert ".bun-cache" in result.detail


def test_prelaunch_public_check_detects_public_routes(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    app = tmp_path / "reflex_app.py"
    app.write_text("from reflex_app.app.bootstrap import create_app\n", encoding="utf-8")
    monkeypatch.setattr(module, "REFLEX_APP", app)
    payload = __import__("json").dumps(list(module.PUBLIC_ROUTES))
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=payload + "\n", stderr=""),
    )

    assert "/support" in module.PUBLIC_ROUTES
    assert "/studio" in module.PUBLIC_ROUTES
    assert "/laboratory/expedient" in module.PUBLIC_ROUTES
    assert module._public_routes_check().ok is True


def test_prelaunch_public_check_reflex_compile_uses_dry_run(monkeypatch) -> None:
    module = _load_script()
    calls = []

    def fake_run(command, cwd, capture_output, text, check, timeout):  # noqa: ANN001
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="Success: App compiled successfully", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module._reflex_compile_check()

    assert result.ok is True
    assert calls == [[sys.executable, "-m", "reflex", "compile", "--dry", "--no-rich"]]


def test_prelaunch_public_check_validates_public_web_assets(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    favicon = tmp_path / "assets" / "favicon.ico"
    apple = tmp_path / "assets" / "apple-touch-icon.png"
    icon_192 = tmp_path / "assets" / "icon-192.png"
    icon_512 = tmp_path / "assets" / "icon-512.png"
    og_image = tmp_path / "assets" / "og-image.png"
    manifest = tmp_path / "assets" / "site.webmanifest"
    robots = tmp_path / "assets" / "robots.txt"
    sitemap = tmp_path / "assets" / "sitemap.xml"
    rxconfig = tmp_path / "rxconfig.py"

    for asset in (favicon, apple, icon_192, icon_512, og_image):
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_text("ok", encoding="utf-8")

    manifest.write_text(
        """{
  "name": "DatosEnOrden Ciudadano",
  "theme_color": "#0f766e",
  "icons": [{"src": "/icon-192.png"}, {"src": "/icon-512.png"}]
}
""",
        encoding="utf-8",
    )
    robots.write_text(
        """User-agent: *
Allow: /
Sitemap: https://datosenorden.cl/sitemap.xml
""",
        encoding="utf-8",
    )
    sitemap.write_text(
        "<urlset><url><loc>https://datosenorden.cl</loc></url><url><loc>https://datosenorden.cl/search</loc></url><url><loc>https://datosenorden.cl/sources</loc></url><url><loc>https://datosenorden.cl/official-document</loc></url><url><loc>https://datosenorden.cl/laboratory</loc></url><url><loc>https://datosenorden.cl/project</loc></url></urlset>",
        encoding="utf-8",
    )
    rxconfig.write_text(
        """import reflex as rx

PUBLIC_BASE_URL = "https://datosenorden.cl"
API_URL = "https://datosenorden.cl"
BACKEND_PATH = "/api"
config = rx.Config(
    app_name="reflex_app",
    deploy_url=PUBLIC_BASE_URL,
    api_url=API_URL,
    backend_path=BACKEND_PATH,
    plugins=[rx.plugins.SitemapPlugin(trailing_slash="never")],
)
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "FAVICON", favicon)
    monkeypatch.setattr(module, "APPLE_TOUCH_ICON", apple)
    monkeypatch.setattr(module, "ICON_192", icon_192)
    monkeypatch.setattr(module, "ICON_512", icon_512)
    monkeypatch.setattr(module, "OG_IMAGE", og_image)
    monkeypatch.setattr(module, "WEBMANIFEST", manifest)
    monkeypatch.setattr(module, "ROBOTS", robots)
    monkeypatch.setattr(module, "SITEMAP", sitemap)
    monkeypatch.setattr(module, "RXCONFIG", rxconfig)

    assert module._asset_check().ok is True
    assert module._manifest_check().ok is True
    assert module._robots_check().ok is True
    assert module._sitemap_check().ok is True
    assert module._deploy_url_check().ok is True
