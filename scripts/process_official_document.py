from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOCUMENT_ID = "senado-docto-9000-mensaje_mocion"
INCOMING_ROOT = ROOT / "data" / "official_documents" / "incoming"
PROCESSING_ROOT = ROOT / "data" / "official_documents" / "processing"
DEFAULT_INCOMING_DIR = INCOMING_ROOT / DEFAULT_DOCUMENT_ID
FRAGMENT_TARGET_CHARS = 2200
FRAGMENT_MIN_CHARS = 240


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    incoming_dir = Path(args[0]) if args else DEFAULT_INCOMING_DIR
    result = process_official_document(incoming_dir)
    print("official_document_processing: OK")
    print(f"  document_id={result['document_id']}")
    print(f"  processing_dir={result['processing_dir']}")
    print(f"  fragments={result['total_fragments']}")
    print(f"  total_characters={result['total_characters']}")
    print(f"  pages_detected={result['pages_detected']}")
    print("  next_step=manual review: processing -> reading pipeline")
    return 0


def process_official_document(incoming_dir: Path) -> dict[str, object]:
    incoming_dir = incoming_dir.resolve()
    metadata_path = incoming_dir / "metadata.json"
    metadata = _load_json(metadata_path)
    document_id = str(metadata["id"])
    document_path = incoming_dir / str(metadata.get("file_name", "document.doc"))
    if not document_path.exists():
        candidates = [path for path in incoming_dir.iterdir() if path.is_file() and path.name != "metadata.json"]
        if len(candidates) != 1:
            raise FileNotFoundError(f"Could not resolve original document in {incoming_dir}")
        document_path = candidates[0]

    _validate_input(document_path, metadata)
    extraction_date = datetime.now(UTC).date().isoformat()
    text = extract_text(document_path)
    if not text.strip():
        raise ValueError(f"No text extracted from {document_path}")

    fragments = build_fragments(document_id=document_id, text=text)
    processing_dir = PROCESSING_ROOT / document_id
    processing_dir.mkdir(parents=True, exist_ok=True)
    original_path = processing_dir / f"original{document_path.suffix.lower() or '.bin'}"
    shutil.copy2(document_path, original_path)

    extracted_path = processing_dir / "extracted.txt"
    document_json_path = processing_dir / "document.json"
    fragments_json_path = processing_dir / "fragments.json"
    processing_metadata_path = processing_dir / "metadata.json"

    extracted_path.write_text(text, encoding="utf-8")
    total_characters = sum(fragment["character_count"] for fragment in fragments)
    pages_detected = sorted(
        {fragment["page"] for fragment in fragments if fragment.get("page") is not None}
    )
    document_contract = {
        "document_id": document_id,
        "source": str(metadata.get("organization", "")),
        "title": str(metadata.get("title", "")),
        "language": str(metadata.get("language", "es")),
        "mime_type": str(metadata.get("content_type", "")),
        "total_fragments": len(fragments),
        "total_characters": total_characters,
        "pages_detected": len(pages_detected),
        "extraction_date": extraction_date,
        "original_filename": original_path.name,
        "extracted_text_filename": extracted_path.name,
        "fragments_filename": fragments_json_path.name,
    }
    processing_metadata = {
        **metadata,
        "status": "processing",
        "processing_date": extraction_date,
        "processing_stage": "text_extracted",
        "processing_document": document_json_path.name,
        "processing_fragments": fragments_json_path.name,
        "extracted_text": extracted_path.name,
        "original_filename": original_path.name,
        "total_fragments": len(fragments),
        "total_characters": total_characters,
        "pages_detected": len(pages_detected),
        "extraction_method": _extraction_method(document_path),
    }
    document_json_path.write_text(_json(document_contract), encoding="utf-8")
    fragments_json_path.write_text(_json({"fragments": fragments}), encoding="utf-8")
    processing_metadata_path.write_text(_json(processing_metadata), encoding="utf-8")
    return {
        "document_id": document_id,
        "processing_dir": str(processing_dir),
        "total_fragments": len(fragments),
        "total_characters": total_characters,
        "pages_detected": len(pages_detected),
    }


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _extract_docx_text(path)
    if suffix == ".doc":
        return _extract_doc_binary_text(path)
    return _clean_extracted_text(path.read_text(encoding="utf-8", errors="ignore"))


def build_fragments(document_id: str, text: str) -> list[dict[str, object]]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    fragments: list[dict[str, object]] = []
    buffer: list[str] = []
    current_heading: str | None = None

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        fragment_text = "\n\n".join(buffer).strip()
        order = len(fragments) + 1
        fragments.append(
            {
                "fragment_id": f"{document_id}-fragment-{order:04d}",
                "order": order,
                "text": fragment_text,
                "page": None,
                "heading": current_heading,
                "character_count": len(fragment_text),
            }
        )
        buffer = []

    for paragraph in paragraphs:
        heading = _detect_heading(paragraph)
        pending_size = sum(len(item) for item in buffer) + len(paragraph)
        if buffer and (pending_size > FRAGMENT_TARGET_CHARS or heading):
            flush()
        if heading:
            current_heading = heading
        buffer.append(paragraph)
        if sum(len(item) for item in buffer) >= FRAGMENT_TARGET_CHARS:
            flush()
    flush()

    if len(fragments) > 1 and fragments[-1]["character_count"] < FRAGMENT_MIN_CHARS:
        last = fragments.pop()
        previous = fragments[-1]
        merged_text = f"{previous['text']}\n\n{last['text']}"
        previous["text"] = merged_text
        previous["character_count"] = len(merged_text)
    return fragments


def _extract_docx_text(path: Path) -> str:
    with ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_bytes)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t")).strip()
        if text:
            paragraphs.append(text)
    return _clean_extracted_text("\n\n".join(paragraphs))


def _extract_doc_binary_text(path: Path) -> str:
    data = path.read_bytes()
    decoded = data.decode("cp1252", errors="ignore")
    chunks = []
    pattern = r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü0-9 ,.;:!¿?¡\-_()/º°%$\"'\n\r]{25,}"
    for match in re.finditer(pattern, decoded):
        chunk = _clean_extracted_text(match.group(0))
        if _is_probable_document_text(chunk):
            chunks.append(chunk)
    if not chunks:
        return ""
    chunks = _trim_non_document_edges(chunks)
    return _clean_extracted_text("\n\n".join(chunks))


def _trim_non_document_edges(chunks: list[str]) -> list[str]:
    start = 0
    for index, chunk in enumerate(chunks):
        if "MENSAJE" in chunk.upper() or "HONORABLE" in chunk.upper():
            start = index
            break
    end = len(chunks)
    for index, chunk in enumerate(chunks[start:], start=start):
        upper = chunk.upper()
        if "DOCUMENTO DE MICROSOFT OFFICE" in upper or "CUSTOMXML" in upper:
            end = index
            break
    return chunks[start:end]


def _is_probable_document_text(value: str) -> bool:
    upper = value.upper()
    blocked = (
        "HTTP://",
        "HTTPS://",
        "SCHEMAS.OPENXMLFORMATS",
        "THEME/",
        "CUSTOMXML",
        "DATASTOREITEM",
        "PK",
        "MICROSOFT OFFICE WORD 97-2003",
    )
    if any(item in upper for item in blocked):
        return False
    if re.fullmatch(r"[A-F0-9-]{30,}", upper):
        return False
    letters = sum(1 for char in value if char.isalpha())
    return letters >= 12


def _detect_heading(paragraph: str) -> str | None:
    compact = " ".join(paragraph.split())
    if len(compact) > 120:
        return None
    upper = compact.upper()
    if compact.endswith(".") and upper == compact and any(char.isalpha() for char in compact):
        return compact
    if re.match(r"^\d+\.\s+[A-ZÁÉÍÓÚÑ]", compact):
        return compact
    return None


def _clean_extracted_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _validate_input(document_path: Path, metadata: dict[str, object]) -> None:
    expected_hash = str(metadata.get("content_sha256", ""))
    if expected_hash:
        actual_hash = hashlib.sha256(document_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError("Document hash does not match incoming metadata")


def _extraction_method(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return "python-stdlib-docx-xml"
    if path.suffix.lower() == ".doc":
        return "python-stdlib-doc-binary-text"
    return "python-stdlib-text"


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
