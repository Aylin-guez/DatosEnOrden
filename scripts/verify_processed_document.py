from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT_ID = "senado-docto-9000-mensaje_mocion"
PROCESSING_ROOT = ROOT / "data" / "official_documents" / "processing"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    document_id = args[0] if args else DEFAULT_DOCUMENT_ID
    processing_dir = PROCESSING_ROOT / document_id
    document = _load_json(processing_dir / "document.json")
    fragments_payload = _load_json(processing_dir / "fragments.json")
    metadata = _load_json(processing_dir / "metadata.json")
    fragments = fragments_payload.get("fragments", [])
    if not isinstance(fragments, list):
        raise ValueError("fragments.json must contain a fragments list")
    total_length = sum(int(fragment.get("character_count", 0)) for fragment in fragments)
    pages = sorted({fragment.get("page") for fragment in fragments if fragment.get("page") is not None})
    print("processed_document: OK")
    print(f"  document_id={document.get('document_id', '')}")
    print(f"  estado={metadata.get('status', '')}")
    print(f"  fragmentos={len(fragments)}")
    print(f"  longitud={total_length}")
    print(f"  paginas_detectadas={len(pages)}")
    print(f"  metadata={processing_dir / 'metadata.json'}")
    print(f"  document={processing_dir / 'document.json'}")
    print(f"  fragments={processing_dir / 'fragments.json'}")
    print(f"  titulo={document.get('title', '')}")
    return 0 if fragments and str(metadata.get("status", "")) == "processing" else 1


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
