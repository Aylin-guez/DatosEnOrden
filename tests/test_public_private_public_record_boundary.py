from __future__ import annotations

import ast
from pathlib import Path

from datosenorden.application.public_record import PublicRecordGraphPort, PublicRecordPort, public_record_ownership


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_RECORD_APP = ROOT / "src" / "datosenorden" / "application" / "public_record"
PUBLIC_RECORD_FEATURE = ROOT / "reflex_app" / "features" / "public_record"

FORBIDDEN_IMPORT_ROOTS = {
    "deo_core",
    "deo_document_search",
    "deo_document_search_apify_actor",
    "deo_document_finder",
}
PRIVATE_ENGINE_SYMBOLS = {
    "GraphLoader",
    "RelationshipDiscoveryGraph",
    "ContentIngestionService",
    "DocumentSearchService",
    "extract_entities",
    "rank",
    "OCR",
    "RapidAPI",
    "Apify",
    "api_key",
}


def _python_files() -> list[Path]:
    return [
        path
        for root in [PUBLIC_RECORD_APP, PUBLIC_RECORD_FEATURE]
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_public_record_public_modules_do_not_import_private_repositories() -> None:
    offenders: list[str] = []
    for path in _python_files():
        for name in _imports(path):
            if name.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                offenders.append(f"{path.relative_to(ROOT)} imports {name}")

    assert offenders == []


def test_public_record_ports_are_public_contracts_without_engine_details() -> None:
    assert PublicRecordPort.__module__ == "datosenorden.application.public_record.ports"
    assert PublicRecordGraphPort.__module__ == "datosenorden.application.public_record.ports"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_RECORD_APP.glob("*.py"))
    for symbol in PRIVATE_ENGINE_SYMBOLS:
        assert symbol not in combined
    assert "Protocol" in combined


def test_public_record_ownership_documents_private_engine_boundary() -> None:
    ownership = public_record_ownership()

    assert ownership["state"] == "PUBLIC_PRODUCT_UI"
    assert ownership["load_orchestration"] == "PUBLIC_PRODUCT_APPLICATION"
    assert ownership["ports"] == "PUBLIC_CONTRACT"
    assert ownership["graph_engine"] == "CORE_PRIVATE"
    assert ownership["timeline_engine"] == "CORE_PRIVATE"
    assert ownership["evidence_analysis"] == "CORE_PRIVATE"
