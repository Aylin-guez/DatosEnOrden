from __future__ import annotations

import ast
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (ROOT / "reflex_app", ROOT / "src" / "datosenorden" / "application")
PUBLIC_MATERIALS = (
    ROOT / "docs" / "architecture" / "DEO_PUBLIC_PRIVATE_CODE_BOUNDARY_2026-07-24.md",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "deo_core",
    "datosenorden.core",
    "deo_bricks",
    "bricks",
)
FORBIDDEN_LOCAL_MARKERS = (
    "f:\\datosenordencore",
    "f:\\datosenordenbricks",
    "i:\\datosenordencore",
    "i:\\datosenordenbricks",
    "d:\\datos en orden",
    "api_key=",
    "rapidapi",
    "apify",
)


def _imports_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_runtime_surface_has_no_private_core_or_bricks_imports() -> None:
    offenders: list[str] = []
    for root in RUNTIME_ROOTS:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            imports = _imports_in(path)
            private = [
                name
                for name in imports
                if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_IMPORT_PREFIXES)
            ]
            if private:
                offenders.append(f"{path.relative_to(ROOT)}: {private}")
    assert offenders == []


def test_local_release_artifacts_are_absent_and_prevented_from_reappearing() -> None:
    assert not (ROOT / ".sync_state.json").exists()
    assert not (ROOT / "opencode.json").exists()

    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for rule in (
        ".pytest_tmp*/",
        "/.sync_state.json",
        "/opencode.json",
        "/prompt pendiente .txt",
        "*.whl",
        "/docs/release/",
        "/docs/certification/",
        "/docs/implementation/",
        "/docs/reviews/",
        "/Clear-Pytest-Directories.ps1",
    ):
        assert rule in ignored

    tracked = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    forbidden_suffixes = (".env", ".whl", ".sqlite", ".db", ".dump")
    assert not [path for path in tracked if path.lower().endswith(forbidden_suffixes)]
    assert not [path for path in tracked if path.startswith(("dist/", "build/", "wheelhouse/", "wheels/"))]


def test_new_public_materials_do_not_expose_private_paths_or_secrets() -> None:
    for path in PUBLIC_MATERIALS:
        assert path.exists(), path
        content = path.read_text(encoding="utf-8").lower()
        assert [marker for marker in FORBIDDEN_LOCAL_MARKERS if marker in content] == []


def test_public_release_materials_do_not_require_internal_audits() -> None:
    assert PUBLIC_MATERIALS == (
        ROOT / "docs" / "architecture" / "DEO_PUBLIC_PRIVATE_CODE_BOUNDARY_2026-07-24.md",
    )


def test_python_sources_contain_no_literal_private_repo_paths() -> None:
    offenders: list[str] = []
    for root in RUNTIME_ROOTS:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            content = path.read_text(encoding="utf-8").lower()
            matches = [marker for marker in FORBIDDEN_LOCAL_MARKERS[:4] if marker in content]
            if matches:
                offenders.append(f"{path.relative_to(ROOT)}: {matches}")
    assert offenders == []
