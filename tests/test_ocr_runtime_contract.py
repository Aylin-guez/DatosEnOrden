from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ocr_extract.py"


def test_ocr_extractor_requires_matching_hash_before_any_renderer() -> None:
    staging_root = ROOT / "data" / "tmp" / "ocr_contract_tests"
    staging_root.mkdir(parents=True, exist_ok=True)
    temporary_path = staging_root / uuid.uuid4().hex
    temporary_path.mkdir()
    try:
        original = temporary_path / "official.pdf"
        original.write_bytes(b"official bytes")
        before = original.read_bytes()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--document", str(original), "--expected-sha256", "0" * 64, "--output-directory", str(temporary_path / "output")],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "SHA256 mismatch" in result.stderr
        assert original.read_bytes() == before
    finally:
        shutil.rmtree(temporary_path, ignore_errors=True)


def test_ocr_manifest_contract_keeps_page_identity_and_source_boundary() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"document_sha256"' in source
    assert '"page_number"' in source
    assert '"raw_text"' in source
    assert '"verification_status": "UNVERIFIED"' in source
    assert "official original document remains the sole source authority" in source
    assert hashlib.sha256(b"official bytes").hexdigest() != "0" * 64


def test_ocr_provisioner_is_project_local_and_does_not_use_program_files() -> None:
    provisioner = (ROOT / "scripts" / "provision_ocr.ps1").read_text(encoding="utf-8")
    assert "data\\tmp\\ocr_runtime" in provisioner
    assert "Start-Process -FilePath $installer" not in provisioner
    assert "Program Files\\Tesseract-OCR" not in provisioner
    assert "TESSDATA_PREFIX" in provisioner
