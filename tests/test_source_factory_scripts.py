from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import create_source_plugin
import load_all_prototype_sources
import prototype_sources_summary
import validate_source_plugin

from datosenorden.maintenance.source_plugins import SourceStatus
from datosenorden.maintenance.source_plugins import get_source_plugin


def test_create_source_scaffold_dry_run_lists_expected_files(tmp_path) -> None:
    result = create_source_plugin.create_source_scaffold(
        "sample_source",
        display_name="Sample Source",
        status="prototype",
        root=tmp_path,
        dry_run=True,
    )

    assert any(path.endswith("scripts\\load_sample_source_sample.py") or path.endswith("scripts/load_sample_source_sample.py") for path in result)
    assert all(action == "would_write" for action in result.values())
    assert not (tmp_path / "scripts" / "load_sample_source_sample.py").exists()


def test_create_source_scaffold_does_not_overwrite_without_force(tmp_path) -> None:
    existing = tmp_path / "docs" / "sources" / "sample_source.md"
    existing.parent.mkdir(parents=True)
    existing.write_text("existing", encoding="utf-8")

    result = create_source_plugin.create_source_scaffold(
        "sample_source",
        display_name="Sample Source",
        status="prototype",
        root=tmp_path,
    )

    assert result[str(existing)] == "exists"
    assert existing.read_text(encoding="utf-8") == "existing"


def test_validate_source_plugin_detects_missing_registered_plugin() -> None:
    result = validate_source_plugin.validate_source_plugin("missing_source")

    assert not result.valid
    assert "plugin_not_registered" in result.critical_failures


def test_validate_source_plugin_accepts_declaraciones_intereses() -> None:
    result = validate_source_plugin.validate_source_plugin("declaraciones_intereses")

    assert result.valid
    assert result.status == "prototype"


def test_declaraciones_intereses_registry_status_is_prototype() -> None:
    plugin = get_source_plugin("declaraciones_intereses")

    assert plugin is not None
    assert plugin.status == SourceStatus.PROTOTYPE


def test_load_all_prototype_sources_dry_run_includes_declaraciones() -> None:
    results = load_all_prototype_sources.run_loaders(dry_run=True)

    assert any(source_id == "declaraciones_intereses" for source_id, _, _ in results)
    assert all(code == 0 for _, code, _ in results)


def test_prototype_sources_summary_imports() -> None:
    assert callable(prototype_sources_summary.main)

