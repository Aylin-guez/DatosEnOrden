from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PATHS = [ROOT / "src", ROOT / "reflex_app"]
SEARCH_SERVICE = ROOT / "src" / "datosenorden" / "application" / "search" / "service.py"
SEARCH_PORTS = ROOT / "src" / "datosenorden" / "application" / "search" / "ports.py"
DOCUMENT_READING_PORTS = ROOT / "src" / "datosenorden" / "application" / "document_reading" / "ports.py"

FORBIDDEN_IMPORT_ROOTS = {
    "deo_core",
    "deo_document_search",
    "deo_document_search_apify_actor",
    "deo_document_finder",
}
PRIVATE_ENGINE_SYMBOLS = {
    "SearchService",
    "search_segments",
    "InMemorySearchAdapter",
    "_find_match",
    "_find_all_terms_match",
    "_unique_terms",
    "_build_excerpt",
    "_rank",
    "ContentIngestionService",
    "PyMuPDFPdfAdapter",
    "DocumentSearchService",
    "RapidAPIChannelAdapter",
    "UsageRepository",
    "SafeHttpDownloader",
}


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in PUBLIC_PATHS:
        files.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return files


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_public_repository_does_not_import_private_core_or_brick_packages() -> None:
    offenders: list[str] = []
    for path in _python_files():
        for name in _imports(path):
            root = name.split(".", 1)[0]
            if root in FORBIDDEN_IMPORT_ROOTS:
                offenders.append(f"{path.relative_to(ROOT)} imports {name}")

    assert offenders == []


def test_public_application_search_service_stays_product_orchestration_only() -> None:
    source = SEARCH_SERVICE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SEARCH_SERVICE))
    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    assert "run_workspace_search" in function_names
    assert {"format_workspace_matches", "build_guided_questions", "build_guided_categories"} <= function_names
    assert function_names.isdisjoint(PRIVATE_ENGINE_SYMBOLS)
    for private_symbol in PRIVATE_ENGINE_SYMBOLS:
        assert private_symbol not in source
    assert "search_workspace(" in source
    assert "SearchMode" not in source
    assert "rank" not in source.lower()
    assert "fitz" not in source
    assert "pymupdf" not in source.lower()


def test_public_ports_do_not_reveal_private_contracts_or_marketplace_details() -> None:
    combined = SEARCH_PORTS.read_text(encoding="utf-8") + DOCUMENT_READING_PORTS.read_text(encoding="utf-8")

    assert "Protocol" in combined
    for forbidden in [
        "deo_core",
        "deo_document_search",
        "RapidAPI",
        "Apify",
        "metering",
        "api_key",
        "SearchMode",
        "Segment",
        "ContentIngestionService",
    ]:
        assert forbidden not in combined


def test_public_docs_boundary_file_exists_with_push_checklist() -> None:
    doc = ROOT / "docs" / "architecture" / "DEO_PUBLIC_PRIVATE_CODE_BOUNDARY_2026-07-24.md"
    source = doc.read_text(encoding="utf-8")

    assert "PUBLIC_PRODUCT_UI" in source
    assert "CORE_PRIVATE" in source
    assert "BRICK_PRIVATE" in source
    assert "Checklist previo a cualquier push publico" in source
