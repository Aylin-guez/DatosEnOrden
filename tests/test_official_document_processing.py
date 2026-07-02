from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import process_official_document


def test_build_fragments_keeps_required_shape() -> None:
    text = "TITULO GENERAL.\n\n" + "\n\n".join(f"Parrafo {index} con texto oficial." for index in range(80))

    fragments = process_official_document.build_fragments("doc-1", text)

    assert fragments
    assert fragments[0]["fragment_id"] == "doc-1-fragment-0001"
    assert fragments[0]["order"] == 1
    assert fragments[0]["page"] is None
    assert fragments[0]["character_count"] == len(str(fragments[0]["text"]))


def test_process_official_document_writes_processing_contracts(tmp_path: Path) -> None:
    incoming_dir = tmp_path / "incoming" / "doc-1"
    incoming_dir.mkdir(parents=True)
    document = incoming_dir / "document.txt"
    content = "Documento oficial.\n\nArticulo 1.- Texto fiel.\n\nArticulo 2.- Otro texto."
    document.write_text(content, encoding="utf-8")
    metadata = {
        "id": "doc-1",
        "title": "Documento oficial",
        "organization": "Organismo oficial",
        "source_url": "https://example.gob.cl/doc",
        "publication_date": "2026-01-01",
        "retrieval_date": "2026-07-02",
        "status": "incoming",
        "document_type": "test",
        "language": "es",
        "version": 1,
        "content_type": "text/plain",
        "content_sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
        "file_name": "document.txt",
    }
    (incoming_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    original_root = process_official_document.PROCESSING_ROOT
    try:
        process_official_document.PROCESSING_ROOT = tmp_path / "processing"
        result = process_official_document.process_official_document(incoming_dir)
    finally:
        process_official_document.PROCESSING_ROOT = original_root

    processing_dir = tmp_path / "processing" / "doc-1"
    document_json = json.loads((processing_dir / "document.json").read_text(encoding="utf-8"))
    fragments = json.loads((processing_dir / "fragments.json").read_text(encoding="utf-8"))["fragments"]
    processing_metadata = json.loads((processing_dir / "metadata.json").read_text(encoding="utf-8"))
    assert result["document_id"] == "doc-1"
    assert (processing_dir / "original.txt").exists()
    assert document_json["total_fragments"] == len(fragments)
    assert processing_metadata["status"] == "processing"
    assert fragments[0]["page"] is None
