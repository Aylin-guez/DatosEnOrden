from pathlib import Path


def test_public_assets_exist_for_launch() -> None:
    required = [
        Path("assets/favicon.ico"),
        Path("assets/apple-touch-icon.png"),
        Path("assets/icon-192.png"),
        Path("assets/icon-512.png"),
        Path("assets/og-image.png"),
        Path("assets/site.webmanifest"),
        Path("assets/robots.txt"),
        Path("assets/sitemap.xml"),
    ]

    for path in required:
        assert path.exists(), f"missing public asset: {path}"


def test_manifest_and_sitemap_use_public_domain() -> None:
    manifest = Path("assets/site.webmanifest").read_text(encoding="utf-8")
    sitemap = Path("assets/sitemap.xml").read_text(encoding="utf-8")
    robots = Path("assets/robots.txt").read_text(encoding="utf-8")

    assert "DatosEnOrden" in manifest
    assert "cronologías" in manifest
    assert "https://datosenorden.cl/sitemap.xml" in robots
    for route in [
        "https://datosenorden.cl",
        "https://datosenorden.cl/search",
        "https://datosenorden.cl/topic",
        "https://datosenorden.cl/sources",
        "https://datosenorden.cl/official-document",
        "https://datosenorden.cl/chronology",
        "https://datosenorden.cl/support",
        "https://datosenorden.cl/studio",
    ]:
        assert route in sitemap
