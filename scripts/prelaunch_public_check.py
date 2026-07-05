from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REFLEX_APP = ROOT / "reflex_app" / "reflex_app.py"
ENV_EXAMPLE = ROOT / ".env.example"
PUBLISHED_DOCUMENT_DIR = ROOT / "data" / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion"
PUBLISHED_READING = PUBLISHED_DOCUMENT_DIR / "reading.json"
PUBLISHED_DOCUMENT_VIEW = PUBLISHED_DOCUMENT_DIR / "document_view.json"
PUBLISHED_PDF = PUBLISHED_DOCUMENT_DIR / "document.pdf"
PUBLIC_PDF_ASSET = ROOT / "assets" / "official_documents" / "senado-docto-9000-mensaje_mocion" / "document.pdf"
FAVICON = ROOT / "assets" / "favicon.ico"
REQUIRED_ENV_KEYS = (
    "DATOSENORDEN_ENV",
    "DATABASE_URL",
    "DATOSENORDEN_DATABASE_URL",
    "DATOSENORDEN_PUBLIC_BASE_URL",
    "DATOSENORDEN_SUPPORT_URL",
)
PUBLIC_ROUTES = (
    "/",
    "/topic",
    "/search",
    "/ecosystem",
    "/project",
    "/investigation",
    "/reports",
    "/tracking",
    "/support",
    "/studio",
)
MAX_DEMO_ASSET_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    detail: str


def main() -> int:
    checks = [
        _reflex_compile_check(),
        _asset_check(),
        _published_document_check(),
        _pdf_strategy_check(),
        _document_source_stability_check(),
        _env_example_check(),
        _tracked_cache_check(),
        _large_asset_check(),
        _public_routes_check(),
    ]
    _print_report(checks)
    return 1 if any(not check.ok for check in checks) else 0


def _reflex_compile_check() -> Check:
    result = subprocess.run(
        [sys.executable, "-m", "reflex", "compile", "--dry", "--no-rich"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    lines = (result.stdout or result.stderr or "").strip().splitlines()
    detail = lines[-1] if lines else f"exit={result.returncode}"
    return Check("Reflex compiles", result.returncode == 0, detail)


def _asset_check() -> Check:
    missing = [str(path.relative_to(ROOT)) for path in (FAVICON,) if not path.exists()]
    return Check("required assets exist", not missing, "missing=" + ", ".join(missing) if missing else "favicon ok")


def _published_document_check() -> Check:
    required = (PUBLISHED_READING, PUBLISHED_DOCUMENT_VIEW)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return Check("published official document exists", False, "missing=" + ", ".join(missing))
    return Check("published official document exists", True, "reading.json and document_view.json ok")


def _pdf_strategy_check() -> Check:
    if not PUBLISHED_PDF.exists():
        return Check("official PDF strategy", True, "document.pdf not present; /topic falls back to document_view.json")
    ok = PUBLIC_PDF_ASSET.exists()
    detail = "public asset copy ok" if ok else f"missing public asset copy: {PUBLIC_PDF_ASSET.relative_to(ROOT)}"
    return Check("official PDF strategy", ok, detail)


def _document_source_stability_check() -> Check:
    missing = []
    for path in (PUBLISHED_READING, PUBLISHED_DOCUMENT_VIEW):
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
    if missing:
        return Check("public document source is stable", False, "missing=" + ", ".join(missing))
    detail = "uses published artifacts; incoming/processing not required for public launch"
    if PUBLISHED_PDF.exists() and PUBLIC_PDF_ASSET.exists():
        detail += "; PDF is published and served from assets"
    return Check("public document source is stable", True, detail)


def _env_example_check() -> Check:
    if not ENV_EXAMPLE.exists():
        return Check(".env.example has required variables", False, ".env.example missing")
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [key for key in REQUIRED_ENV_KEYS if f"{key}=" not in text]
    return Check(
        ".env.example has required variables",
        not missing,
        "missing=" + ", ".join(missing) if missing else ", ".join(REQUIRED_ENV_KEYS),
    )


def _tracked_cache_check() -> Check:
    tracked = _git_lines("ls-files")
    blocked = [
        path
        for path in tracked
        if "/__pycache__/" in path.replace("\\", "/")
        or path.endswith(".pyc")
        or path.startswith(".bun-cache/")
        or path.startswith(".pytest_cache/")
    ]
    return Check("no tracked cache artifacts", not blocked, "none" if not blocked else ", ".join(blocked[:8]))


def _large_asset_check() -> Check:
    tracked = _git_lines("ls-files")
    large = []
    for rel in tracked:
        path = ROOT / rel
        if path.is_file() and path.stat().st_size > MAX_DEMO_ASSET_BYTES:
            large.append(f"{rel}={path.stat().st_size} bytes")
    return Check("no oversized tracked assets", not large, "none" if not large else ", ".join(large[:8]))


def _public_routes_check() -> Check:
    if not REFLEX_APP.exists():
        return Check("public routes registered", False, "reflex_app/reflex_app.py missing")
    text = REFLEX_APP.read_text(encoding="utf-8")
    missing = [route for route in PUBLIC_ROUTES if f'@rx.page(route="{route}"' not in text]
    return Check("public routes registered", not missing, "missing=" + ", ".join(missing) if missing else ", ".join(PUBLIC_ROUTES))


def _git_lines(*args: str) -> list[str]:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _print_report(checks: list[Check]) -> None:
    print("prelaunch_public_check:")
    for check in checks:
        print(f"  {'ok' if check.ok else 'FAIL'} - {check.label}: {check.detail}")


if __name__ == "__main__":
    raise SystemExit(main())
