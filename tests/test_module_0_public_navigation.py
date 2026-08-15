from __future__ import annotations

from pathlib import Path

from reflex.page import DECORATED_PAGES

import reflex_app.reflex_app  # noqa: F401
from reflex_app.navigation.config import PRIMARY_NAVIGATION_ITEMS
from datosenorden.application.search.service import format_workspace_matches
from reflex_app.features.sources.state import _presentation_status


def test_public_navigation_is_reduced_to_module_0_entries() -> None:
    labels = [item.label for item in PRIMARY_NAVIGATION_ITEMS]
    hrefs = [item.href for item in PRIMARY_NAVIGATION_ITEMS]

    assert labels == ["Inicio", "Explorar", "Fuentes", "Laboratorio", "Acerca de"]
    assert hrefs == ["/", "/search", "/sources", "/laboratory", "/project"]
    assert "Lectura" not in labels
    assert "Expediente" not in labels
    assert "Informes" not in labels
    assert "Cronologia" not in labels


def test_contextual_routes_remain_registered_for_direct_access() -> None:
    routes = {kwargs["route"] for _, kwargs in DECORATED_PAGES["reflex_app"]}

    assert {"/topic", "/official-document", "/reports", "/tracking", "/investigation"} <= routes
    assert {"/search", "/discover", "/project"} <= routes
    assert {"/laboratory", "/laboratory/expedient"} <= routes


def test_search_results_do_not_claim_persistent_generation() -> None:
    rows = format_workspace_matches(
        {
            "matches": [
                {
                    "entity_id": "E1",
                    "entity_name": "Hospital Demo",
                    "entity_type": "organization",
                    "datasets": ["ChileCompra"],
                    "evidence_count": 2,
                    "relationship_count": 1,
                },
                {
                    "entity_id": "E2",
                    "entity_name": "Tema sin cobertura",
                    "entity_type": "topic",
                    "datasets": [],
                    "evidence_count": 0,
                    "relationship_count": 0,
                },
            ]
        }
    )

    assert rows[0]["action_label"] == "Abrir expediente actualizado"
    assert rows[1]["action_label"] == "Ver informacion disponible"
    assert all("Generar expediente" not in row["action_label"] for row in rows)


def test_source_presentation_status_is_conservative() -> None:
    assert _presentation_status({"status": "planned"}) == "CONNECTOR_PLANNED"
    assert _presentation_status({"status": "prototype"}) == "CONNECTOR_PROTOTYPE"
    assert _presentation_status({"status": "active"}) == "CATALOGUED"
    assert _presentation_status({"status": "active", "population_records": 2}) == "CATALOGUED"
    assert _presentation_status({"status": "active", "real_available_records": 2}) == "DATA_AVAILABLE"


def test_visible_public_files_do_not_contain_mojibake() -> None:
    roots = [
        Path("reflex_app"),
        Path("src/datosenorden/application"),
        Path("scripts"),
        Path("tests"),
    ]
    mojibake_tokens = tuple(chr(value) for value in (0x00C3, 0x00C2, 0x00E2, 0x00F0))
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if any(token in text for token in mojibake_tokens):
                offenders.append(path.as_posix())

    assert offenders == []
