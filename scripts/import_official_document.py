from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_DOCUMENTS_ROOT = ROOT / "data" / "official_documents"
INCOMING_DIR = OFFICIAL_DOCUMENTS_ROOT / "incoming"
PROCESSING_DIR = OFFICIAL_DOCUMENTS_ROOT / "processing"
PUBLISHED_DIR = OFFICIAL_DOCUMENTS_ROOT / "published"
ARCHIVED_DIR = OFFICIAL_DOCUMENTS_ROOT / "archived"
REQUIRED_FIELDS = (
    "id",
    "title",
    "organization",
    "source_url",
    "publication_date",
    "retrieval_date",
    "status",
    "document_type",
    "language",
    "version",
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("usage: python scripts/import_official_document.py <document_file> <metadata_json>")
        return 2

    document_path = Path(args[0])
    metadata_path = Path(args[1])
    errors = validate_import(document_path, metadata_path)
    if errors:
        print("official_document_import: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    metadata = _load_metadata(metadata_path)
    print("official_document_import: OK")
    print(f"  id={metadata['id']}")
    print(f"  document={document_path}")
    print(f"  metadata={metadata_path}")
    print("  next_step=manual review: incoming -> processing -> published -> archived")
    return 0


def validate_import(document_path: Path, metadata_path: Path) -> list[str]:
    errors: list[str] = []
    if not document_path.exists() or not document_path.is_file():
        errors.append(f"document file does not exist: {document_path}")
    if not metadata_path.exists() or not metadata_path.is_file():
        errors.append(f"metadata file does not exist: {metadata_path}")
        return errors

    try:
        metadata = _load_metadata(metadata_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"metadata is not valid JSON: {type(exc).__name__}: {exc}")
        return errors

    errors.extend(_validate_metadata(metadata))
    if not errors:
        errors.extend(_validate_unique_id(str(metadata["id"]), metadata_path))
    return errors


def _load_metadata(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("metadata root must be an object")
    return data


def _validate_metadata(metadata: dict) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in metadata:
            errors.append(f"metadata missing required field: {field}")
    if errors:
        return errors

    text_fields = ["id", "title", "organization", "source_url", "publication_date", "retrieval_date", "status", "document_type", "language"]
    for field in text_fields:
        if not str(metadata.get(field, "")).strip():
            errors.append(f"metadata field must not be empty: {field}")

    source_url = str(metadata.get("source_url", ""))
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append("source_url must be an official http(s) URL")

    for field in ("publication_date", "retrieval_date"):
        value = str(metadata.get(field, ""))
        try:
            date.fromisoformat(value)
        except ValueError:
            errors.append(f"{field} must use YYYY-MM-DD format")

    if str(metadata.get("organization", "")).strip() == "":
        errors.append("organization is required")

    try:
        version = int(metadata.get("version"))
        if version < 1:
            errors.append("version must be greater than or equal to 1")
    except (TypeError, ValueError):
        errors.append("version must be an integer")

    if str(metadata.get("language", "")) != "es":
        errors.append("language must be 'es' for the first official reading workflow")
    return errors


def _validate_unique_id(document_id: str, current_metadata: Path) -> list[str]:
    matches: list[Path] = []
    for folder in (INCOMING_DIR, PROCESSING_DIR, PUBLISHED_DIR, ARCHIVED_DIR):
        if not folder.exists():
            continue
        for path in folder.rglob("*.json"):
            if path.resolve() == current_metadata.resolve():
                continue
            try:
                data = _load_metadata(path)
            except Exception:  # noqa: BLE001
                continue
            if str(data.get("id", "")) == document_id:
                matches.append(path)
    return ["metadata id is not unique: " + " | ".join(str(path) for path in matches)] if matches else []


if __name__ == "__main__":
    raise SystemExit(main())
