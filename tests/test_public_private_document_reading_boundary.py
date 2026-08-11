from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_READING_APP = ROOT / "src" / "datosenorden" / "application" / "document_reading"
DOCUMENT_READING_FEATURE = ROOT / "reflex_app" / "features" / "document_reading"

FORBIDDEN_IMPORT_ROOTS = {
    "deo_core",
    "deo_document_search",
    "deo_document_search_apify_actor",
    "deo_document_finder",
}
PRIVATE_ENGINE_SYMBOLS = {
    "ContentIngestionService",
    "DocumentSearchService",
    "PyMuPDFPdfAdapter",
    "RapidAPIChannelAdapter",
    "SearchMode",
    "Segment",
    "build_timeline",
    "extract_entities",
    "rank",
    "search_segments",
}


def _python_files() -> list[Path]:
    return [
        path
        for root in [DOCUMENT_READING_APP, DOCUMENT_READING_FEATURE]
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


def test_document_reading_public_modules_do_not_import_private_repositories() -> None:
    offenders: list[str] = []
    for path in _python_files():
        for name in _imports(path):
            if name.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                offenders.append(f"{path.relative_to(ROOT)} imports {name}")

    assert offenders == []


def test_document_reading_application_contains_product_orchestration_not_engines() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCUMENT_READING_APP.glob("*.py"))

    assert "build_knowledge_payload" in combined
    assert "build_topic_payload" in combined
    assert "DocumentReadingPort" in combined
    for symbol in PRIVATE_ENGINE_SYMBOLS:
        assert symbol not in combined
    assert "api_key" not in combined.lower()
    assert "rapidapi" not in combined.lower()
    assert "apify" not in combined.lower()


def test_document_reading_feature_state_is_reflex_ui_boundary() -> None:
    source = (DOCUMENT_READING_FEATURE / "state.py").read_text(encoding="utf-8")

    assert "class DocumentReadingState" in source
    assert "build_knowledge_payload" in source
    assert "build_topic_payload" in source
    assert "get_investigation" in source
    assert "build_state_graph" in source
    assert "deo_core" not in source
