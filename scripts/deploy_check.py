from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ENV = (
    "DATABASE_URL",
    "DATOSENORDEN_ENV",
    "DATOSENORDEN_PUBLIC_BASE_URL",
    "DATOSENORDEN_SUPPORT_URL",
    "API_URL",
)
DEPLOYMENT_FILES = (
    ROOT / "deployment" / "production.env.example",
    ROOT / "deployment" / "datosenorden.service",
    ROOT / "deployment" / "Caddyfile",
    ROOT / "scripts" / "server_setup_ubuntu.sh",
    ROOT / "scripts" / "healthcheck_public.py",
    ROOT / "scripts" / "backup_postgres.sh",
    ROOT / "docs" / "VPS_GO_LIVE_STEPS.md",
)
PUBLIC_ROUTES = (
    "404",
    "/",
    "/topic",
    "/knowledge",
    "/library",
    "/demo",
    "/search",
    "/discover",
    "/ecosystem",
    "/sources",
    "/project",
    "/investigation",
    "/official-document",
    "/reports",
    "/tracking",
    "/chronology",
    "/support",
    "/studio",
    "/dashboard",
    "/laboratory",
    "/laboratory/expedient",
)
PUBLISHED_DIR = ROOT / "data" / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion"
ASSET_PDF = ROOT / "assets" / "official_documents" / "senado-docto-9000-mensaje_mocion" / "document.pdf"
PUBLIC_ASSETS = (
    ROOT / "assets" / "favicon.ico",
    ROOT / "assets" / "apple-touch-icon.png",
    ROOT / "assets" / "icon-192.png",
    ROOT / "assets" / "icon-512.png",
    ROOT / "assets" / "og-image.png",
    ROOT / "assets" / "site.webmanifest",
    ROOT / "assets" / "robots.txt",
    ROOT / "assets" / "sitemap.xml",
)


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    detail: str


def main() -> int:
    checks = [
        _env_check(),
        _deployment_pack_check(),
        _public_asset_check(),
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


def _deployment_pack_check() -> Check:
    missing = [path.relative_to(ROOT).as_posix() for path in DEPLOYMENT_FILES if not path.exists()]
    if missing:
        return Check("go-live deployment pack", False, "missing=" + ", ".join(missing))
    return Check("go-live deployment pack", True, ", ".join(path.relative_to(ROOT).as_posix() for path in DEPLOYMENT_FILES))


def _public_asset_check() -> Check:
    missing = [str(path.relative_to(ROOT)) for path in PUBLIC_ASSETS if not path.exists()]
    if missing:
        return Check("public launch assets", False, "missing=" + ", ".join(missing))
    return Check("public launch assets", True, "favicon, manifest, robots, sitemap and share assets ok")


def _document_check() -> Check:
    required = (PUBLISHED_DIR / "reading.json", PUBLISHED_DIR / "document_view.json", PUBLISHED_DIR / "document.pdf", ASSET_PDF)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return Check("published document assets", False, "missing=" + ", ".join(missing))
    return Check("published document assets", True, "reading, document_view and PDF asset ok")


def _route_check() -> Check:
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            (
                "import json; import reflex_app.reflex_app; "
                "from reflex.page import DECORATED_PAGES; "
                "print(json.dumps([kwargs['route'] for _, kwargs in DECORATED_PAGES['reflex_app']]))"
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or f"exit={result.returncode}").strip().splitlines()[-1]
        return Check("public routes registered", False, detail)
    routes = set(json.loads(result.stdout.strip().splitlines()[-1]))
    missing = [route for route in PUBLIC_ROUTES if route not in routes]
    unexpected_count = len(routes) != len(PUBLIC_ROUTES)
    if missing or unexpected_count:
        detail = "missing=" + ", ".join(missing) if missing else f"registered={len(routes)} expected={len(PUBLIC_ROUTES)}"
        return Check("public routes registered", False, detail)
    return Check("public routes registered", True, ", ".join(PUBLIC_ROUTES))


def _prelaunch_check() -> Check:
    result = subprocess.run([sys.executable, "scripts/prelaunch_public_check.py"], cwd=ROOT, capture_output=True, text=True, check=False, timeout=240)
    lines = (result.stdout or result.stderr or "").strip().splitlines()
    detail = lines[-1] if lines else f"exit={result.returncode}"
    return Check("prelaunch public check", result.returncode == 0, detail)


if __name__ == "__main__":
    raise SystemExit(main())
