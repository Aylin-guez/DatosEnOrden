from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from datosenorden.maintenance.source_plugins import PublicSourcePlugin
from datosenorden.maintenance.source_plugins import SourceStatus
from datosenorden.maintenance.source_plugins import get_source_plugin
from datosenorden.maintenance.source_plugins import get_source_plugins

FORBIDDEN_WORDING = (
    "accusation",
    "corruption",
    "fraud",
    "illegal",
    "risk score",
    "suspicious",
)


@dataclass(frozen=True)
class SourceValidationResult:
    source_id: str
    display_name: str
    status: str
    valid: bool
    critical_failures: tuple[str, ...]
    warnings: tuple[str, ...]
    details: dict[str, bool]


def validate_source_plugin(source_id: str, root: Path = ROOT) -> SourceValidationResult:
    plugin = get_source_plugin(source_id)
    if plugin is None:
        return SourceValidationResult(
            source_id=source_id,
            display_name="",
            status="missing",
            valid=False,
            critical_failures=("plugin_not_registered",),
            warnings=(),
            details={},
        )
    return validate_plugin(plugin, root=root)


def validate_plugin(plugin: PublicSourcePlugin, root: Path = ROOT) -> SourceValidationResult:
    details = {
        "metadata_required": _has_required_metadata(plugin),
        "status_valid": plugin.status in {SourceStatus.ACTIVE, SourceStatus.PROTOTYPE, SourceStatus.PLANNED},
        "sample_file_exists": sample_file_exists(plugin, root=root),
        "loader_script_exists": command_script_exists(plugin, "loader", root=root),
        "summary_script_exists": command_script_exists(plugin, "summary", root=root),
        "test_file_exists": test_file_exists(plugin.id, root=root),
        "docs_file_exists": docs_file_exists(plugin.id, root=root),
        "commands_match_files": commands_match_files(plugin, root=root),
        "neutral_wording": not has_forbidden_wording(plugin),
    }
    critical: list[str] = []
    warnings: list[str] = []

    for key in ("metadata_required", "status_valid", "commands_match_files", "neutral_wording"):
        if not details[key]:
            critical.append(key)

    if plugin.status in {SourceStatus.ACTIVE, SourceStatus.PROTOTYPE}:
        for key in ("sample_file_exists", "loader_script_exists", "summary_script_exists", "test_file_exists", "docs_file_exists"):
            if not details[key]:
                critical.append(key)
    else:
        for key in ("sample_file_exists", "loader_script_exists", "summary_script_exists", "test_file_exists", "docs_file_exists"):
            if not details[key]:
                warnings.append(key)

    return SourceValidationResult(
        source_id=plugin.id,
        display_name=plugin.display_name,
        status=plugin.status.value,
        valid=not critical,
        critical_failures=tuple(critical),
        warnings=tuple(warnings),
        details=details,
    )


def validate_all(root: Path = ROOT) -> tuple[SourceValidationResult, ...]:
    return tuple(validate_plugin(plugin, root=root) for plugin in get_source_plugins())


def command_script_exists(plugin: PublicSourcePlugin, kind: str, root: Path = ROOT) -> bool:
    return any(_command_path(command.command, root=root).exists() for command in plugin.commands if command.kind == kind)


def commands_match_files(plugin: PublicSourcePlugin, root: Path = ROOT) -> bool:
    return all(_command_path(command.command, root=root).exists() for command in plugin.commands)


def sample_file_exists(plugin: PublicSourcePlugin, root: Path = ROOT) -> bool:
    if plugin.status == SourceStatus.PLANNED:
        return False
    candidates = [
        root / "data" / "sample" / f"{plugin.id}_sample.json",
        root / "data" / "sample" / f"{plugin.id.replace('_', '-')}_sample.json",
        root / "data" / "sample" / f"{plugin.id}.json",
        root / "data" / "sample" / f"{_singular_sample_stem(plugin.id)}_sample.json",
    ]
    technical_names = str(plugin.technical_metadata.get("dataset_names", ""))
    for name in [item.strip() for item in technical_names.split(",") if item.strip()]:
        candidates.extend((root / "data" / "sample").glob(f"*{name}*.json"))
    candidates.extend((root / "data" / "sample").glob(f"*{plugin.id.split('_')[0]}*.json"))
    return any(path.exists() for path in candidates) or demo_case_mentions_plugin(plugin, root=root)


def test_file_exists(source_id: str, root: Path = ROOT) -> bool:
    exact = root / "tests" / f"test_{source_id}_prototype.py"
    if exact.exists():
        return True
    patterns = {source_id.lower(), source_id.lower().replace("_", "-"), source_id.lower().split("_")[0]}
    for path in (root / "tests").glob("test_*.py"):
        name = path.name.lower().replace("-", "_")
        if any(pattern.replace("-", "_") in name for pattern in patterns):
            return True
    return False


def docs_file_exists(source_id: str, root: Path = ROOT) -> bool:
    return (root / "docs" / "sources" / f"{source_id}.md").exists()


def has_forbidden_wording(plugin: PublicSourcePlugin) -> bool:
    haystack = " ".join(
        [
            plugin.description,
            plugin.coverage.description,
            plugin.timeline_contribution,
            " ".join(plugin.search_hints),
            " ".join(plugin.discovery_hints),
        ]
    ).lower()
    return any(re.search(rf"\b{re.escape(term)}\b", haystack) for term in FORBIDDEN_WORDING)


def demo_case_mentions_plugin(plugin: PublicSourcePlugin, root: Path = ROOT) -> bool:
    path = root / "data" / "demo_cases" / "servicio_salud_arauco_complete.json"
    if not path.exists():
        return False
    try:
        payload_text = json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False).lower()
    except Exception:  # noqa: BLE001
        return False
    identifiers = {
        plugin.id.lower(),
        plugin.id.lower().replace("_", "-"),
        plugin.display_name.lower(),
        *(alias.lower() for alias in plugin.aliases),
    }
    technical_names = str(plugin.technical_metadata.get("dataset_names", ""))
    identifiers.update(item.strip().lower() for item in technical_names.split(",") if item.strip())
    return any(identifier and identifier in payload_text for identifier in identifiers)


def _singular_sample_stem(source_id: str) -> str:
    if source_id == "municipalidades":
        return "municipalidad"
    return source_id


def render_validation_results(results: Sequence[SourceValidationResult]) -> str:
    lines = ["source_plugin_validation:"]
    for result in results:
        status = "ok" if result.valid else "FAIL"
        lines.extend(
            [
                f"- {result.source_id}",
                f"  status: {status}",
                f"  source_status: {result.status}",
                f"  critical_failures: {', '.join(result.critical_failures) if result.critical_failures else 'none'}",
                f"  warnings: {', '.join(result.warnings) if result.warnings else 'none'}",
            ]
        )
        for key, value in sorted(result.details.items()):
            lines.append(f"  {key}: {'yes' if value else 'no'}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser(description="Validate DatosEnOrden public source plugin readiness")
    parser.add_argument("source_id", nargs="?", help="Source id to validate")
    parser.add_argument("--all", action="store_true", help="Validate all registered source plugins")
    args = parser.parse_args(argv)

    if args.all:
        results = validate_all()
    elif args.source_id:
        results = (validate_source_plugin(args.source_id),)
    else:
        parser.error("provide a source_id or --all")

    print(render_validation_results(results))
    return 1 if any(not result.valid for result in results) else 0


def _has_required_metadata(plugin: PublicSourcePlugin) -> bool:
    return all(
        [
            plugin.id,
            plugin.display_name,
            plugin.status.value,
            plugin.description,
            plugin.category,
            plugin.coverage.level,
            plugin.coverage.description,
        ]
    )


def _command_path(command: str, root: Path = ROOT) -> Path:
    parts = command.split()
    script = next((part for part in parts if part.startswith("scripts/")), "")
    return root / script if script else root / "__missing_script__"


if __name__ == "__main__":
    raise SystemExit(main())
