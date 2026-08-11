from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REFLEX_APP = ROOT / "reflex_app" / "reflex_app.py"
ENV_EXAMPLE = ROOT / ".env.example"
PUBLISHED_DOCUMENT_DIR = ROOT / "data" / "official_documents" / "published" / "senado-docto-9000-mensaje_mocion"
SECURITY_HEADERS = ROOT / "deployment" / "Caddyfile"
COMPOSE = ROOT / "docker-compose.yml"
PUBLISHED_READING = PUBLISHED_DOCUMENT_DIR / "reading.json"
PUBLISHED_DOCUMENT_VIEW = PUBLISHED_DOCUMENT_DIR / "document_view.json"
PUBLISHED_PDF = PUBLISHED_DOCUMENT_DIR / "document.pdf"
PUBLIC_PDF_ASSET = ROOT / "assets" / "official_documents" / "senado-docto-9000-mensaje_mocion" / "document.pdf"
FAVICON = ROOT / "assets" / "favicon.ico"
APPLE_TOUCH_ICON = ROOT / "assets" / "apple-touch-icon.png"
ICON_192 = ROOT / "assets" / "icon-192.png"
ICON_512 = ROOT / "assets" / "icon-512.png"
OG_IMAGE = ROOT / "assets" / "og-image.png"
WEBMANIFEST = ROOT / "assets" / "site.webmanifest"
ROBOTS = ROOT / "assets" / "robots.txt"
SITEMAP = ROOT / "assets" / "sitemap.xml"
RXCONFIG = ROOT / "rxconfig.py"
REQUIRED_ENV_KEYS = (
    "DATOSENORDEN_ENV",
    "DATABASE_URL",
    "DATOSENORDEN_DATABASE_URL",
    "DATOSENORDEN_PUBLIC_BASE_URL",
    "DATOSENORDEN_SUPPORT_URL",
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
MAX_DEMO_ASSET_BYTES = 10 * 1024 * 1024
PUBLIC_SITE_URL = "https://datosenorden.cl"
SITEMAP_REQUIRED_ROUTES = ("/", "/search", "/sources", "/official-document", "/laboratory", "/project")


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    detail: str


def main() -> int:
    checks = [
        _reflex_compile_check(),
        _asset_check(),
        _manifest_check(),
        _robots_check(),
        _sitemap_check(),
        _deploy_url_check(),
        _published_document_check(),
        _pdf_strategy_check(),
        _document_source_stability_check(),
        _env_example_check(),
        _security_headers_check(),
        _compose_check(),
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
    required = (FAVICON, APPLE_TOUCH_ICON, ICON_192, ICON_512, OG_IMAGE, WEBMANIFEST, ROBOTS, SITEMAP)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    return Check("required assets exist", not missing, "missing=" + ", ".join(missing) if missing else "favicon, icons, manifest, robots, sitemap and og image ok")



def _manifest_check() -> Check:
    if not WEBMANIFEST.exists():
        return Check("web manifest configured", False, f"missing={WEBMANIFEST.relative_to(ROOT)}")
    payload = json.loads(WEBMANIFEST.read_text(encoding="utf-8"))
    icons = {item.get("src") for item in payload.get("icons", [])}
    ok = payload.get("name") == "DatosEnOrden Ciudadano" and payload.get("theme_color") == "#0f766e" and {"/icon-192.png", "/icon-512.png"}.issubset(icons)
    detail = "manifest ok" if ok else str(payload)
    return Check("web manifest configured", ok, detail)


def _robots_check() -> Check:
    if not ROBOTS.exists():
        return Check("robots.txt configured", False, f"missing={ROBOTS.relative_to(ROOT)}")
    text = ROBOTS.read_text(encoding="utf-8")
    ok = "User-agent: *" in text and "Allow: /" in text and f"Sitemap: {PUBLIC_SITE_URL}/sitemap.xml" in text
    return Check("robots.txt configured", ok, "robots ok" if ok else text.strip())


def _sitemap_check() -> Check:
    if not SITEMAP.exists():
        return Check("sitemap.xml configured", False, f"missing={SITEMAP.relative_to(ROOT)}")
    text = SITEMAP.read_text(encoding="utf-8")
    missing = [route for route in SITEMAP_REQUIRED_ROUTES if (PUBLIC_SITE_URL if route == "/" else f"{PUBLIC_SITE_URL}{route}") not in text]
    return Check("sitemap.xml configured", not missing, "missing=" + ", ".join(missing) if missing else ", ".join(SITEMAP_REQUIRED_ROUTES))


def _deploy_url_check() -> Check:
    if not RXCONFIG.exists():
        return Check("deploy url configured", False, "rxconfig.py missing")
    text = RXCONFIG.read_text(encoding="utf-8")
    deploy_ok = 'DATOSENORDEN_PUBLIC_BASE_URL' in text or 'deploy_url="https://datosenorden.cl"' in text or 'deploy_url=PUBLIC_BASE_URL' in text
    api_ok = "api_url=" in text and ("API_URL" in text or "REFLEX_API_URL" in text or "http://localhost:8000" in text)
    backend_path_ok = "backend_path=" in text and ("REFLEX_BACKEND_PATH" in text or "BACKEND_PATH" in text)
    sitemap_ok = 'SitemapPlugin(trailing_slash="never")' in text
    ok = deploy_ok and api_ok and backend_path_ok and sitemap_ok
    detail = ", ".join(
        [
            "deploy_url ok" if deploy_ok else "deploy_url missing",
            "api_url ok" if api_ok else "api_url missing",
            "backend_path ok" if backend_path_ok else "backend_path missing",
            "sitemap plugin ok" if sitemap_ok else "sitemap plugin missing",
        ]
    )
    return Check("deploy url configured", ok, detail)


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
    if ok:
        detail = "public asset copy ok"
    else:
        try:
            asset_path = PUBLIC_PDF_ASSET.relative_to(ROOT)
        except ValueError:
            asset_path = PUBLIC_PDF_ASSET
        detail = f"missing public asset copy: {asset_path}"
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


def _security_headers_check() -> Check:
    text = SECURITY_HEADERS.read_text(encoding="utf-8") if SECURITY_HEADERS.exists() else ""
    required = ("Content-Security-Policy", "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy", "frame-ancestors")
    missing = [name for name in required if name not in text]
    return Check("security headers configured", not missing, "missing=" + ", ".join(missing) if missing else "CSP and browser protections configured")


def _compose_check() -> Check:
    text = COMPOSE.read_text(encoding="utf-8") if COMPOSE.exists() else ""
    safe = "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD" in text and "127.0.0.1:5432:5432" in text and "not an authorized production" in text
    return Check("compose is local-only and credential-safe", safe, "local-only compose configured" if safe else "compose exposes a fixed credential or public database port")


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
