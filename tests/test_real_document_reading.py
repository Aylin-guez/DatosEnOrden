from __future__ import annotations

import json
from pathlib import Path

from scripts import run_document_reading
from datosenorden.web import app_services


def _write_processed_document(root: Path) -> None:
    processing_dir = root / "processing" / "doc-real"
    processing_dir.mkdir(parents=True)
    (processing_dir / "document.json").write_text(
        json.dumps(
            {
                "document_id": "doc-real",
                "source": "Senado",
                "title": "Documento real",
                "language": "es",
                "mime_type": "text/plain",
            }
        ),
        encoding="utf-8",
    )
    (processing_dir / "fragments.json").write_text(
        json.dumps(
            {
                "fragments": [
                    {
                        "fragment_id": "doc-real-fragment-0001",
                        "order": 1,
                        "text": "Texto oficial del primer fragmento.",
                        "page": None,
                        "heading": None,
                        "character_count": 35,
                    },
                    {
                        "fragment_id": "doc-real-fragment-0002",
                        "order": 2,
                        "text": "Texto oficial del segundo fragmento.",
                        "page": None,
                        "heading": "Detalle",
                        "character_count": 36,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (processing_dir / "metadata.json").write_text(
        json.dumps(
            {
                "document_type": "legislative_mensaje_mocion",
                "publication_date": "2026-07-02",
                "source_url": "https://senado.cl/doc",
                "bill_id": "cl-congreso-boletin-1-01",
                "bulletin_id": "1-01",
                "source_document_id": "1",
                "project_url": "https://senado.cl/project",
                "content_sha256": "abc",
            }
        ),
        encoding="utf-8",
    )
    (processing_dir / "extracted.txt").write_text(
        "Texto oficial del primer fragmento.\n\nTexto oficial del segundo fragmento.",
        encoding="utf-8",
    )


def test_run_document_reading_writes_publication_artifacts(tmp_path: Path) -> None:
    _write_processed_document(tmp_path)
    original_processing = run_document_reading.PROCESSING_ROOT
    original_published = run_document_reading.PUBLISHED_ROOT
    try:
        run_document_reading.PROCESSING_ROOT = tmp_path / "processing"
        run_document_reading.PUBLISHED_ROOT = tmp_path / "published"
        result = run_document_reading.run_document_reading("doc-real")
    finally:
        run_document_reading.PROCESSING_ROOT = original_processing
        run_document_reading.PUBLISHED_ROOT = original_published

    published_dir = tmp_path / "published" / "doc-real"
    publication = json.loads((published_dir / "publication.json").read_text(encoding="utf-8"))
    reading = json.loads((published_dir / "reading.json").read_text(encoding="utf-8"))
    assert result["fragments"] == 2
    assert (published_dir / "knowledge.json").exists()
    assert publication["document_view"]
    assert publication["references"][0]["fragment_id"] == "doc-real-fragment-0001"
    assert reading["fragments"][0]["page"] is None


def test_get_knowledge_demo_uses_real_publication_when_available(tmp_path: Path, monkeypatch) -> None:
    publication_path = tmp_path / "publication.json"
    publication_path.write_text(
        json.dumps({"document_view": {"document": {"id": "real-doc"}, "citizen_summary": "Real"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(app_services, "REAL_DOCUMENT_PUBLICATION_PATH", publication_path)

    payload = app_services.get_knowledge_demo()

    assert payload["document"]["id"] == "real-doc"
