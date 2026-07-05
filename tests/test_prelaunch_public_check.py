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
        "DATOSENORDEN_ENV=production\nDATABASE_URL=postgresql://example\nDATOSENORDEN_DATABASE_URL=postgresql://example\n",
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
    app.write_text('\n'.join(f'@rx.page(route="{route}")' for route in module.PUBLIC_ROUTES), encoding="utf-8")
    monkeypatch.setattr(module, "REFLEX_APP", app)

    assert "/support" in module.PUBLIC_ROUTES
    assert "/studio" in module.PUBLIC_ROUTES
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
