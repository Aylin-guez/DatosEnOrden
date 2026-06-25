from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

from datosenorden.maintenance.ecosystem_registry import build_ecosystem_registry
from datosenorden.maintenance.guided_questions import get_guided_questions
from datosenorden.maintenance.source_plugins import SourceStatus
from datosenorden.maintenance.source_plugins import get_source_plugin
from datosenorden.maintenance.source_plugins import get_source_plugins
from datosenorden.maintenance.source_plugins import get_sources_by_concept
from datosenorden.maintenance.source_plugins import get_sources_connected_to
from datosenorden.maintenance.source_plugins import list_planned_sources
from datosenorden.maintenance.source_plugins import plugin_status_value

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import source_readiness_report


def test_source_plugin_ids_are_unique() -> None:
    plugins = get_source_plugins()

    assert len({plugin.id for plugin in plugins}) == len(plugins)


def test_source_plugins_have_required_metadata() -> None:
    for plugin in get_source_plugins():
        assert plugin.display_name
        assert plugin_status_value(plugin) in {"active", "prototype", "planned"}
        assert plugin.description
        assert plugin.category


def test_active_and_prototype_sources_have_concepts() -> None:
    for plugin in get_source_plugins():
        if plugin.status in {SourceStatus.ACTIVE, SourceStatus.PROTOTYPE}:
            assert plugin.concepts, plugin.id


def test_registry_lookup_helpers() -> None:
    assert get_source_plugin("ChileCompra").id == "chilecompra"
    assert get_sources_by_concept("Organismo")
    assert get_sources_connected_to("chilecompra")


def test_planned_sources_are_not_active() -> None:
    planned_ids = {plugin.id for plugin in list_planned_sources()}

    assert {"declaraciones_intereses", "sanciones_procedimientos"} <= planned_ids
    assert all(plugin.status == SourceStatus.PLANNED for plugin in list_planned_sources())


def test_current_source_count_matches_expected_registry_count() -> None:
    assert len(get_source_plugins()) == 11


def test_ecosystem_registry_can_be_built_from_plugins(monkeypatch) -> None:
    monkeypatch.setattr(
        "datosenorden.maintenance.ecosystem_registry.list_datasets",
        lambda session: [SimpleNamespace(slug="chilecompra", health="active", source_records=1)],
    )

    registry = build_ecosystem_registry(object())

    assert len(registry.sources) == len(get_source_plugins())
    assert any(source.slug == "chilecompra" and source.status == "active" for source in registry.sources)
    assert any(source.slug == "declaraciones_intereses" and source.status == "planned" for source in registry.sources)


def test_guided_questions_map_to_source_plugins() -> None:
    guided = get_guided_questions()

    for row in [*guided["questions"], *guided["categories"]]:
        assert row["source_plugin_ids"]
        assert all(get_source_plugin(source_id) is not None for source_id in row["source_plugin_ids"])


def test_source_readiness_report_runs_without_mutation(capsys) -> None:
    exit_code = source_readiness_report.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "source_readiness_report:" in captured.out
    assert "- chilecompra" in captured.out
