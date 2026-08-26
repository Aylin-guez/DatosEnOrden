"""Local, page-addressable OCR extraction for scanned public documents.

This tool never changes its input and never treats OCR output as a source.  Its
manifest links raw extraction to the original file hash and page image.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], *, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    return completed.stdout


def pdf_page_count(pdfinfo: str, document: Path) -> int:
    output = run([pdfinfo, str(document)])
    match = re.search(r"^Pages:\s*(\d+)\s*$", output, re.MULTILINE)
    if not match:
        raise RuntimeError("pdfinfo did not report a page count")
    return int(match.group(1))


def mean_word_confidence(tsv_path: Path) -> float | None:
    values: list[float] = []
    with tsv_path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            if row.get("text", "").strip() and row.get("conf", "-1") not in {"", "-1"}:
                values.append(float(row["conf"]))
    return round(sum(values) / len(values), 4) if values else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--language", default="spa")
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--first-page", type=int, default=1)
    parser.add_argument("--last-page", type=int)
    parser.add_argument("--tesseract", type=Path)
    parser.add_argument("--pdftoppm")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    document = args.document.resolve()
    if not document.is_file():
        raise RuntimeError(f"Document does not exist: {document}")
    actual_sha256 = sha256_file(document)
    if actual_sha256.lower() != args.expected_sha256.lower():
        raise RuntimeError("SHA256 mismatch: extraction refused")

    project_root = Path(__file__).resolve().parent.parent
    tesseract = (args.tesseract or project_root / "data" / "tmp" / "ocr_runtime" / "tesseract" / "tesseract.exe").resolve()
    pdftoppm = args.pdftoppm or shutil.which("pdftoppm")
    pdfinfo = shutil.which("pdfinfo")
    if not tesseract.is_file() or not pdftoppm or not pdfinfo:
        raise RuntimeError("A project-local Tesseract runtime and Poppler pdftoppm/pdfinfo are required")

    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        if prior.get("document_sha256") == actual_sha256:
            print(f"Existing OCR output verified: {manifest_path}")
            return 0
        raise RuntimeError("Output directory already contains OCR for another document")

    page_count = pdf_page_count(pdfinfo, document)
    first_page = args.first_page
    last_page = args.last_page or page_count
    if first_page < 1 or last_page < first_page or last_page > page_count:
        raise RuntimeError("Requested page range is outside the document")

    environment = os.environ.copy()
    environment["TESSDATA_PREFIX"] = str(tesseract.parent / "tessdata")
    engine_version = run([str(tesseract), "--version"], env=environment).splitlines()[0]
    pages: list[dict[str, Any]] = []
    for page_number in range(first_page, last_page + 1):
        base = output / f"page_{page_number:03d}"
        render_prefix = str(base) + "_render"
        run([pdftoppm, "-f", str(page_number), "-l", str(page_number), "-r", str(args.dpi), "-png", str(document), render_prefix])
        rendered_pages = list(output.glob(f"{base.name}_render-*.png"))
        if len(rendered_pages) != 1:
            raise RuntimeError(f"pdftoppm produced {len(rendered_pages)} images for page {page_number}")
        rendered = rendered_pages[0]
        image = output / f"page_{page_number:03d}.png"
        rendered.replace(image)
        try:
            run([str(tesseract), str(image), str(base), "-l", args.language, "--psm", "6"], env=environment)
            run([str(tesseract), str(image), str(base), "-l", args.language, "--psm", "6", "tsv"], env=environment)
            raw_path = Path(f"{base}.txt")
            tsv_path = Path(f"{base}.tsv")
            raw_text = raw_path.read_text(encoding="utf-8")
            pages.append({
                "page_number": page_number,
                "image": image.name,
                "image_sha256": sha256_file(image),
                "raw_text": raw_path.name,
                "tsv": tsv_path.name,
                "mean_word_confidence": mean_word_confidence(tsv_path),
                "extraction_status": "SUCCESS" if raw_text.strip() else "NO_TEXT",
                "verification_status": "UNVERIFIED",
                "normalized_candidate": None,
            })
        except subprocess.CalledProcessError as error:
            pages.append({"page_number": page_number, "image": image.name, "image_sha256": sha256_file(image), "extraction_status": "FAILED", "verification_status": "UNVERIFIED", "error": error.stderr})

    statuses = {page["extraction_status"] for page in pages}
    document_status = "SUCCESS" if statuses <= {"SUCCESS", "NO_TEXT"} else "PARTIAL" if statuses - {"FAILED"} else "FAILED"
    manifest = {
        "document_path": document.name,
        "document_sha256": actual_sha256,
        "engine": "Tesseract",
        "engine_version": engine_version,
        "language": args.language,
        "render": {"renderer": "Poppler pdftoppm", "dpi": args.dpi, "format": "png"},
        "page_count": page_count,
        "extracted_page_range": [first_page, last_page],
        "extraction_status": document_status,
        "provenance_note": "OCR output is extraction only; the official original document remains the sole source authority.",
        "created_at": datetime.now(UTC).isoformat(),
        "pages": pages,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0 if document_status != "FAILED" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # command-line boundary with no silent fallback
        print(f"OCR extraction failed: {error}", file=sys.stderr)
        raise SystemExit(1)
