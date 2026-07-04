from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT_ID = "senado-docto-9000-mensaje_mocion"
PUBLISHED_ROOT = ROOT / "data" / "official_documents" / "published"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    document_id = args[0] if args else DEFAULT_DOCUMENT_ID
    published_dir = PUBLISHED_ROOT / document_id
    reading = _load_json(published_dir / "reading.json")
    knowledge = _load_json(published_dir / "knowledge.json")
    publication = _load_json(published_dir / "publication.json")
    document = reading.get("document", {})
    fragments = reading.get("fragments", [])
    questions = knowledge.get("citizen_questions", [])
    references = publication.get("references", [])
    document_view = publication.get("document_view", {})
    print("document_reading_verification: OK")
    print(f"  Documento: {document.get('title', '')}")
    print(f"  Fragmentos: {len(fragments)}")
    print(f"  Preguntas: {len(questions)}")
    print(f"  Resumen: {publication.get('citizen_summary', '')}")
    print(f"  Referencias: {len(references)}")
    print(f"  Publication generado: {bool(document_view)}")
    print(f"  Publication artifacts: {len(publication.get('artifacts', []))}")
    print(f"  Limitaciones: {len(publication.get('limitations', []))}")
    return 0 if document_view and fragments and references else 1


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
