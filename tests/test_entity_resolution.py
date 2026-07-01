from __future__ import annotations

import subprocess
import sys

from datosenorden.maintenance.entity_resolution import EntityRegistry
from datosenorden.maintenance.entity_resolution import entity_registry_from_dict
from datosenorden.maintenance.entity_resolution import get_default_entity_registry
from datosenorden.maintenance.entity_resolution import load_entity_registry
from datosenorden.maintenance.entity_resolution import normalize_entity_key
from datosenorden.maintenance.entity_resolution import resolve_entity
from datosenorden.maintenance.entity_resolution import summarize_entity_registry


CANONICAL_ID = "338d160c-8d5d-47e1-9c37-038ed5043ba1"
CANONICAL_NAME = "SERVICIO DE SALUD ARAUCO HOSPITAL DE ARAUCO"


def test_default_entity_registry_loads() -> None:
    registry = get_default_entity_registry()

    assert isinstance(registry, EntityRegistry)
    assert registry.entities


def test_demo_registry_resolves_aliases_to_same_canonical_entity() -> None:
    registry = load_entity_registry()

    queries = [
        "Servicio Salud Arauco",
        "servicio salud arauco",
        "SSA ARAUCO",
        "Hospital de Arauco",
    ]

    results = [registry.resolve(query) for query in queries]

    assert {result.entity.id for result in results if result.entity is not None} == {CANONICAL_ID}
    assert all(result.found for result in results)
    assert all(result.method == "alias" for result in results)


def test_demo_registry_resolves_identifier() -> None:
    result = resolve_entity(CANONICAL_ID)

    assert result.found is True
    assert result.entity is not None
    assert result.entity.id == CANONICAL_ID
    assert result.method == "identifier"
    assert result.confidence == 1.0


def test_demo_registry_resolves_canonical_with_case_and_accents_normalized() -> None:
    result = resolve_entity("servicio   de salud arauco hospital de araúco")

    assert result.found is True
    assert result.entity is not None
    assert result.entity.canonical_name == CANONICAL_NAME
    assert result.method == "canonical"


def test_normalize_entity_key_ignores_accents_case_and_spacing() -> None:
    assert normalize_entity_key("  ÁREA   Clínica  ") == "area clinica"


def test_entity_registry_summary_is_json_safe() -> None:
    summary = summarize_entity_registry(get_default_entity_registry())

    assert summary["entities"] >= 1
    assert summary["aliases"] >= 4
    assert "demo" in summary["tags"]


def test_registry_from_dict_is_domain_generic() -> None:
    registry = entity_registry_from_dict(
        {
            "entities": [
                {
                    "id": "project-1",
                    "canonical_name": "Project Alpha",
                    "aliases": ["Alpha"],
                    "identifiers": [{"type": "internal_code", "value": "P-001"}],
                    "tags": ["generic"],
                    "metadata": {"domain": "client_example"},
                }
            ]
        }
    )

    result = registry.resolve("P-001")

    assert result.found is True
    assert result.entity is not None
    assert result.entity.id == "project-1"
    assert result.method == "identifier"


def test_entity_resolution_module_compiles() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", "src/datosenorden/maintenance/entity_resolution.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
