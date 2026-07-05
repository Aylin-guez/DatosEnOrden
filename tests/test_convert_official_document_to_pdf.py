from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace


def _load_script():
    script_path = Path("scripts") / "convert_official_document_to_pdf.py"
    spec = importlib.util.spec_from_file_location("convert_official_document_to_pdf", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_convert_document_to_pdf_reports_missing_libreoffice(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    source = tmp_path / "document.doc"
    source.write_bytes(b"legacy doc")
    output = tmp_path / "published" / "document.pdf"
    public_copy = tmp_path / "assets" / "official_documents" / "document.pdf"

    monkeypatch.setattr(module, "find_soffice", lambda: None)

    result = module.convert_document_to_pdf(source=source, output=output, public_copy=public_copy)

    assert result.ok is False
    assert "LibreOffice Headless" in result.message
    assert result.soffice is None
    assert not output.exists()
    assert not public_copy.exists()


def test_convert_document_to_pdf_uses_soffice_and_writes_expected_pdf(tmp_path: Path, monkeypatch) -> None:
    module = _load_script()
    source = tmp_path / "document.doc"
    source.write_bytes(b"legacy doc")
    output = tmp_path / "published" / "document.pdf"
    public_copy = tmp_path / "assets" / "official_documents" / "document.pdf"
    soffice = tmp_path / "soffice"
    soffice.write_text("fake", encoding="utf-8")
    calls = []

    def fake_run(command, capture_output, text, check):  # noqa: ANN001
        calls.append(command)
        output.write_bytes(b"%PDF-1.4 fake")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    result = module.convert_document_to_pdf(source=source, output=output, public_copy=public_copy, soffice=soffice)

    assert result.ok is True
    assert output.read_bytes().startswith(b"%PDF")
    assert public_copy.read_bytes().startswith(b"%PDF")
    assert calls[0][0] == str(soffice)
    assert "--headless" in calls[0]
    assert "--convert-to" in calls[0]
    assert str(output.parent.resolve()) in calls[0]