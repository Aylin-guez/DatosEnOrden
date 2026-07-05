from __future__ import annotations

from pathlib import Path

PUBLIC_TEXT_FILES = (
    Path("reflex_app/reflex_app.py"),
    Path("src/datosenorden/web/app_services.py"),
    Path("src/datosenorden/maintenance/source_plugins.py"),
    Path("data/source_population/infolobby_minimal.json"),
    Path("data/connectors/chilecompra_connector.json"),
    Path("data/connectors/infolobby_connector.json"),
    Path("data/connectors/diario_oficial_connector.json"),
    Path("data/sample/diario_oficial_sample.json"),
    Path("assets/site.webmanifest"),
)

BROKEN_TEXT_MARKERS = (
    "\ufffd",
    "\u00c3",
    "\u00c2",
    "qu?",
    "Qu?",
    "p?gina",
    "cronolog?a",
    "?blico",
    "p?blica",
    "reuni?n",
    "m?nima",
    "c?mo",
    "bolet?n",
    "a?n",
)


def test_public_text_files_do_not_contain_mojibake_markers() -> None:
    for path in PUBLIC_TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        for marker in BROKEN_TEXT_MARKERS:
            assert marker not in text, f"{path} contains broken text marker {marker!r}"


def test_public_connector_text_keeps_spanish_accents() -> None:
    text = Path("data/connectors/infolobby_connector.json").read_text(encoding="utf-8")
    assert "Reuni\u00f3n" in text
    assert "Cronolog\u00eda" in text
    assert "Presentaci\u00f3n" in text

    diario = Path("data/connectors/diario_oficial_connector.json").read_text(encoding="utf-8")
    assert "Publicaci\u00f3n" in diario
    assert "Cronolog\u00eda" in diario
    assert "N\u00b0 12.345" in diario

    source_population = Path("data/source_population/infolobby_minimal.json").read_text(encoding="utf-8")
    assert "organismo p\u00fablico" in source_population
    assert "fuente m\u00ednima" in source_population
