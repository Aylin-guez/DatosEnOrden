from __future__ import annotations

import json
from pathlib import Path

from scripts import import_official_document


def _metadata(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "doc-real-001",
        "title": "Documento oficial de prueba",
        "organization": "Organismo oficial",
        "source_url": "https://example.gob.cl/documento.pdf",
        "publication_date": "2026-01-15",
        "retrieval_date": "2026-07-02",
        "status": "incoming",
        "document_type": "resolucion",
        "language": "es",
        "version": 1,
    }
    data.update(overrides)
    return data


def test_validate_import_accepts_valid_document_and_metadata(tmp_path: Path) -> None:
    document = tmp_path / "documento.pdf"
    metadata = tmp_path / "metadata.json"
    document.write_text("PDF placeholder", encoding="utf-8")
    metadata.write_text(json.dumps(_metadata()), encoding="utf-8")

    assert import_official_document.validate_import(document, metadata) == []


def test_validate_import_reports_missing_document_and_metadata_errors(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps(_metadata(source_url="not-a-url", publication_date="15-01-2026", organization="")), encoding="utf-8")

    errors = import_official_document.validate_import(tmp_path / "missing.pdf", metadata)

    assert any("document file does not exist" in error for error in errors)
    assert "source_url must be an official http(s) URL" in errors
    assert "publication_date must use YYYY-MM-DD format" in errors
    assert "metadata field must not be empty: organization" in errors


def test_validate_import_requires_all_metadata_fields(tmp_path: Path) -> None:
    document = tmp_path / "documento.pdf"
    metadata = tmp_path / "metadata.json"
    document.write_text("PDF placeholder", encoding="utf-8")
    data = _metadata()
    del data["retrieval_date"]
    metadata.write_text(json.dumps(data), encoding="utf-8")

    errors = import_official_document.validate_import(document, metadata)

    assert errors == ["metadata missing required field: retrieval_date"]


def test_main_prints_clear_success(tmp_path: Path, capsys) -> None:
    document = tmp_path / "documento.pdf"
    metadata = tmp_path / "metadata.json"
    document.write_text("PDF placeholder", encoding="utf-8")
    metadata.write_text(json.dumps(_metadata()), encoding="utf-8")

    exit_code = import_official_document.main([str(document), str(metadata)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "official_document_import: OK" in output
    assert "next_step=manual review" in output
