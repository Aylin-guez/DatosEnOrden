from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIRS = [ROOT / "reflex_app", ROOT / "src" / "datosenorden" / "application"]
FORBIDDEN = ("deo_core", "DatosEnOrdenCore", "DatosEnOrdenBricks", "RapidAPI", "Apify")
PRIVATE_URL_MARKERS = ("localhost:", "127.0.0.1:", "10.", "192.168.")


def test_public_frontend_has_no_private_imports_or_repo_paths() -> None:
    offenders: list[str] = []
    for base in PUBLIC_DIRS:
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            if any(marker in source for marker in FORBIDDEN):
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_no_private_urls_in_public_application_or_features() -> None:
    offenders: list[str] = []
    for base in PUBLIC_DIRS:
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            if any(marker in source for marker in PRIVATE_URL_MARKERS):
                offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_laboratory_is_public_feature_without_private_imports_or_secrets() -> None:
    laboratory = ROOT / "reflex_app" / "features" / "laboratory"
    assert (laboratory / "pages.py").exists()
    assert (laboratory / "state.py").exists()
    for path in laboratory.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not any(marker in source for marker in FORBIDDEN)
        assert not any(marker in source for marker in PRIVATE_URL_MARKERS)
