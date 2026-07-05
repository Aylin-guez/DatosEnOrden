from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ENV = (
    "DATABASE_URL",
    "DATOSENORDEN_ENV",
    "DATOSENORDEN_PUBLIC_BASE_URL",
    "DATOSENORDEN_SUPPORT_URL",
)
PUBLIC_ROUTES = ("/", "/topic", "/official-document", "/search", "/ecosystem", "/project", "/support", "/studio")
PUBLISHED_DIR = ROOT / "data" / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion"
ASSET_PDF = ROOT / "assets" / "official_documents" / "senado-docto-9000-mensaje_mocion" / "document.pdf"


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    detail: str


def main() -> int:
    checks = [
        _env_check(),
        _document_check(),
        _route_check(),
        _prelaunch_check(),
    ]
    print("deploy_check:")
    for check in checks:
        print(f"  {'ok' if check.ok else 'FAIL'} - {check.label}: {check.detail}")
    return 1 if any(not check.ok for check in checks) else 0


def _env_check() -> Check:
    env_example = ROOT / ".env.example"
    example_text = env_example.read_text(encoding="utf-8") if env_example.exists() else ""
    missing_from_example = [key for key in REQUIRED_ENV if f"{key}=" not in example_text]
    configured = [key for key in REQUIRED_ENV if os.getenv(key)]
    if missing_from_example:
        return Check("deployment env documented", False, "missing from .env.example: " + ", ".join(missing_from_example))
    return Check("deployment env documented", True, "documented=" + ", ".join(REQUIRED_ENV) + f"; configured_now={len(configured)}")


def _document_check() -> Check:
    required = (PUBLISHED_DIR / "reading.json", PUBLISHED_DIR / "document_view.json", PUBLISHED_DIR / "document.pdf", ASSET_PDF)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return Check("published document assets", False, "missing=" + ", ".join(missing))
    return Check("published document assets", True, "reading, document_view and PDF asset ok")


def _route_check() -> Check:
    app_path = ROOT / "reflex_app" / "reflex_app.py"
    text = app_path.read_text(encoding="utf-8")
    missing = [route for route in PUBLIC_ROUTES if f'@rx.page(route="{route}"' not in text]
    return Check("public routes registered", not missing, "missing=" + ", ".join(missing) if missing else ", ".join(PUBLIC_ROUTES))


def _prelaunch_check() -> Check:
    result = subprocess.run([sys.executable, "scripts/prelaunch_public_check.py"], cwd=ROOT, capture_output=True, text=True, check=False, timeout=240)
    lines = (result.stdout or result.stderr or "").strip().splitlines()
    detail = lines[-1] if lines else f"exit={result.returncode}"
    return Check("prelaunch public check", result.returncode == 0, detail)


if __name__ == "__main__":
    raise SystemExit(main())
